"""Register / login / 2FA / me / logout."""
from datetime import timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

import config
import emailer
from db import get_db
from models import OtpCode, User, utcnow
from security import (hash_otp, hash_password, make_token, new_otp, read_token,
                      same, verify_password)

# All auth routes live under /api/auth.
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------- request / response shapes ----------
class RegisterIn(BaseModel):
    """Body for /api/auth/register."""
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)   # 72 = bcrypt limit


class LoginIn(BaseModel):
    """Body for /api/auth/login."""
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class OtpIn(BaseModel):
    """Body for /api/auth/verify-otp."""
    challenge_token: str
    code: str = Field(pattern=r"^\d{6}$")


class ChallengeIn(BaseModel):
    """Body for /api/auth/resend-otp."""
    challenge_token: str


class UserOut(BaseModel):
    """Public user information returned by /me and verify-otp."""
    id: int
    name: str
    email: str


# ---------- helpers ----------
def _issue_otp(db: Session, user: User) -> str:
    """
    Create a new OTP for a user and email it.

    Older pending codes are invalidated first so only the newest code is valid.
    Returns a short-lived challenge token used in /verify-otp.
    """
    for old in db.scalars(select(OtpCode).where(OtpCode.user_id == user.id, OtpCode.used == False)):  # noqa: E712
        old.used = True
    code = new_otp()
    db.add(OtpCode(user_id=user.id, code_hash=hash_otp(code),
                   expires_at=utcnow() + timedelta(minutes=config.OTP_MINUTES)))
    db.commit()
    emailer.send_otp(user.email, code)
    return make_token(user.id, "challenge", config.OTP_MINUTES)


def _aware(dt):
    """
    Ensure a datetime is timezone-aware.

    SQLite returns naive datetimes from the DB; this treats them as UTC.
    """
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Dependency: read the session cookie, validate it, and return the User row.

    Raises 401 if there is no cookie, it is invalid/expired, or the user no longer exists.
    """
    token = request.cookies.get(config.COOKIE_NAME)
    uid = read_token(token, "session") if token else None
    user = db.get(User, uid) if uid else None
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return user


# ---------- routes ----------
@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    """
    Create a new account and start the 2FA email flow.

    Returns a challenge token; the front end then calls /verify-otp with the 6-digit code.
    """
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=email, name=body.name.strip(), password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    return {"challenge_token": _issue_otp(db, user)}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    """
    Check credentials and start the 2FA email flow.

    Returns the same challenge-token shape as register.
    """
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    # Same error for "no such user" and "wrong password" so attackers learn nothing.
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"challenge_token": _issue_otp(db, user)}


@router.post("/resend-otp")
def resend_otp(body: ChallengeIn, db: Session = Depends(get_db)):
    """
    Send a new OTP for an existing challenge token.

    Useful when the code email is delayed or lost.
    """
    uid = read_token(body.challenge_token, "challenge")
    user = db.get(User, uid) if uid else None
    if not user:
        raise HTTPException(status_code=401, detail="Login step expired, start again")
    return {"challenge_token": _issue_otp(db, user)}


@router.post("/verify-otp", response_model=UserOut)
def verify_otp(body: OtpIn, response: Response, db: Session = Depends(get_db)):
    """
    Verify the emailed 6-digit code and upgrade the challenge to a session.

    On success, sets an HttpOnly session cookie and returns public user info.
    """
    uid = read_token(body.challenge_token, "challenge")
    user = db.get(User, uid) if uid else None
    if not user:
        raise HTTPException(status_code=401, detail="Login step expired, start again")

    # Fetch the newest unused OTP row for this user.
    otp = db.scalar(select(OtpCode).where(OtpCode.user_id == user.id, OtpCode.used == False)  # noqa: E712
                    .order_by(OtpCode.id.desc()))
    if not otp or _aware(otp.expires_at) < utcnow():
        raise HTTPException(status_code=400, detail="Code expired, request a new one")
    if otp.attempts >= config.OTP_MAX_ATTEMPTS:
        otp.used = True
        db.commit()
        raise HTTPException(status_code=429, detail="Too many wrong codes, request a new one")

    # Increment attempts on mismatch so brute force is limited.
    if not same(otp.code_hash, hash_otp(body.code)):
        otp.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Wrong code")

    # Code is correct: mark it used and issue the session cookie.
    otp.used = True
    db.commit()
    response.set_cookie(
        config.COOKIE_NAME, make_token(user.id, "session", config.SESSION_MINUTES),
        max_age=config.SESSION_MINUTES * 60, httponly=True, samesite="lax",
        secure=config.COOKIE_SECURE, path="/",
    )
    return UserOut(id=user.id, name=user.name, email=user.email)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    """Return the currently logged-in user's public info."""
    return UserOut(id=user.id, name=user.name, email=user.email)


@router.post("/logout")
def logout(response: Response):
    """Clear the session cookie."""
    response.delete_cookie(config.COOKIE_NAME, path="/")
    return {"ok": True}