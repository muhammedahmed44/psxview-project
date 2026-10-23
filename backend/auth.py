"""Register, login, authenticator-based 2FA, session, and logout routes."""
import json
from datetime import timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

import config
from db import get_db
from models import OtpCode, User, utcnow
from security import (
    decrypt_totp_secret,
    encrypt_totp_secret,
    hash_otp,
    hash_password,
    hash_recovery_code,
    make_token,
    matching_totp_counter,
    new_recovery_codes,
    new_totp_secret,
    normalize_recovery_code,
    read_token,
    same,
    totp_qr_data_url,
    totp_uri,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class AuthenticatorIn(BaseModel):
    challenge_token: str
    code: str = Field(min_length=6, max_length=32)


class ChallengeIn(BaseModel):
    challenge_token: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str


class TotpSetupOut(BaseModel):
    qr_code_data_url: str
    manual_key: str
    issuer: str = "PSXviewAI"


class ChallengeOut(BaseModel):
    challenge_token: str
    requires_setup: bool
    setup: TotpSetupOut | None = None


class AuthOut(UserOut):
    # Present exactly once, when authenticator enrollment is confirmed.
    recovery_codes: list[str] | None = None


def _aware(dt):
    """SQLite returns naive datetimes; treat those values as UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _set_no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


def _secret_for(user: User, *, allow_regenerate: bool) -> str:
    """Return the user's decrypted seed, creating one during enrollment."""
    if user.totp_secret:
        try:
            return decrypt_totp_secret(user.totp_secret)
        except ValueError:
            if not allow_regenerate:
                raise HTTPException(
                    status_code=500,
                    detail="Authenticator configuration is unavailable; contact support",
                )

    secret = new_totp_secret()
    user.totp_secret = encrypt_totp_secret(secret)
    user.totp_enabled = False
    user.totp_last_counter = None
    user.recovery_codes_hashes = None
    return secret


def _setup_payload(db: Session, user: User) -> TotpSetupOut:
    secret = _secret_for(user, allow_regenerate=not user.totp_enabled)
    db.commit()
    uri = totp_uri(secret, user.email)
    return TotpSetupOut(
        qr_code_data_url=totp_qr_data_url(uri),
        manual_key=secret,
    )


def _issue_challenge(db: Session, user: User) -> str:
    """Create a single-use, attempt-limited challenge after password entry."""
    for old in db.scalars(
        select(OtpCode).where(OtpCode.user_id == user.id, OtpCode.used == False)  # noqa: E712
    ):
        old.used = True

    token = make_token(user.id, "challenge", config.OTP_MINUTES)
    db.add(
        OtpCode(
            user_id=user.id,
            code_hash=hash_otp(token),
            expires_at=utcnow() + timedelta(minutes=config.OTP_MINUTES),
        )
    )
    db.commit()
    return token


def _start_authenticator_challenge(db: Session, user: User) -> ChallengeOut:
    setup = None if user.totp_enabled else _setup_payload(db, user)
    return ChallengeOut(
        challenge_token=_issue_challenge(db, user),
        requires_setup=not user.totp_enabled,
        setup=setup,
    )


def _active_challenge(db: Session, user: User, token: str) -> OtpCode:
    challenge = db.scalar(
        select(OtpCode)
        .where(OtpCode.user_id == user.id, OtpCode.used == False)  # noqa: E712
        .order_by(OtpCode.id.desc())
    )
    if not challenge or not same(challenge.code_hash, hash_otp(token)):
        raise HTTPException(status_code=401, detail="Login step expired, start again")
    if _aware(challenge.expires_at) < utcnow():
        challenge.used = True
        db.commit()
        raise HTTPException(status_code=401, detail="Login step expired, start again")
    if challenge.attempts >= config.OTP_MAX_ATTEMPTS:
        challenge.used = True
        db.commit()
        raise HTTPException(status_code=429, detail="Too many wrong codes, start login again")
    return challenge


def _reject_code(db: Session, challenge: OtpCode, detail: str = "Wrong code") -> None:
    challenge.attempts += 1
    db.commit()
    raise HTTPException(status_code=400, detail=detail)


def _stored_recovery_hashes(user: User) -> list[str]:
    try:
        value = json.loads(user.recovery_codes_hashes or "[]")
    except json.JSONDecodeError:
        return []
    return [item for item in value if isinstance(item, str)]


def _verify_authenticator(
    body: AuthenticatorIn,
    response: Response,
    db: Session,
) -> AuthOut:
    uid = read_token(body.challenge_token, "challenge")
    user = db.get(User, uid) if uid else None
    if not user:
        raise HTTPException(status_code=401, detail="Login step expired, start again")

    challenge = _active_challenge(db, user, body.challenge_token)
    code = body.code.strip()
    recovery_codes: list[str] | None = None

    if code.isdigit() and len(code) == 6:
        secret = _secret_for(user, allow_regenerate=False)
        counter = matching_totp_counter(secret, code)
        if counter is None:
            _reject_code(db, challenge)
        if user.totp_last_counter is not None and counter <= user.totp_last_counter:
            _reject_code(db, challenge, "Code already used; wait for the next code")

        user.totp_last_counter = counter
        if not user.totp_enabled:
            recovery_codes = new_recovery_codes()
            user.recovery_codes_hashes = json.dumps(
                [hash_recovery_code(item) for item in recovery_codes]
            )
            user.totp_enabled = True
    else:
        if not user.totp_enabled or len(normalize_recovery_code(code)) != 10:
            _reject_code(db, challenge)
        candidate = hash_recovery_code(code)
        stored = _stored_recovery_hashes(user)
        matching_index = next(
            (index for index, item in enumerate(stored) if same(item, candidate)),
            None,
        )
        if matching_index is None:
            _reject_code(db, challenge, "Invalid or already-used recovery code")
        stored.pop(matching_index)
        user.recovery_codes_hashes = json.dumps(stored)

    challenge.used = True
    db.commit()
    response.set_cookie(
        config.COOKIE_NAME,
        make_token(user.id, "session", config.SESSION_MINUTES),
        max_age=config.SESSION_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=config.COOKIE_SECURE,
        path="/",
    )
    _set_no_store(response)
    return AuthOut(
        id=user.id,
        name=user.name,
        email=user.email,
        recovery_codes=recovery_codes,
    )


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(config.COOKIE_NAME)
    uid = read_token(token, "session") if token else None
    user = db.get(User, uid) if uid else None
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return user


@router.post("/register", status_code=201, response_model=ChallengeOut)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    """Create an account and return its Google Authenticator enrollment QR."""
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=email,
        name=body.name.strip(),
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    result = _start_authenticator_challenge(db, user)
    _set_no_store(response)
    return result


@router.post("/login", response_model=ChallengeOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    """Validate the password and start authenticator setup or verification."""
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    result = _start_authenticator_challenge(db, user)
    _set_no_store(response)
    return result


@router.post("/verify-totp", response_model=AuthOut)
def verify_totp(body: AuthenticatorIn, response: Response, db: Session = Depends(get_db)):
    """Verify a Google Authenticator code (or one-time recovery code)."""
    return _verify_authenticator(body, response, db)


@router.post("/verify-otp", response_model=AuthOut, include_in_schema=False)
def verify_otp_compat(body: AuthenticatorIn, response: Response, db: Session = Depends(get_db)):
    """Compatibility alias for a frontend cached during rolling deployment."""
    return _verify_authenticator(body, response, db)


@router.post("/resend-otp", include_in_schema=False)
def resend_otp_compat(body: ChallengeIn):
    """Explain the removed email action to an older cached frontend."""
    del body
    raise HTTPException(
        status_code=410,
        detail="Authenticator codes refresh automatically every 30 seconds",
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(id=user.id, name=user.name, email=user.email)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(config.COOKIE_NAME, path="/")
    return {"ok": True}
