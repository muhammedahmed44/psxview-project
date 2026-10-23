"""Password hashing, signed tokens, OTP helpers."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from config import JWT_ALG, JWT_SECRET


def hash_password(plain: str) -> str:
    """
    Hash a plain-text password with bcrypt.

    bcrypt is intentionally slow to resist brute-force attacks.
    """
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """
    Check a plain-text password against a stored bcrypt hash.

    Returns False if the hash is malformed.
    """
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


def make_token(user_id: int, kind: str, minutes: int) -> str:
    """
    Sign a JWT for a user.

    kind = 'challenge' (password OK, waiting for 2FA) or 'session' (fully logged in).
    minutes = token lifetime before expiration.
    """
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "kind": kind, "iat": now, "exp": now + timedelta(minutes=minutes)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def read_token(token: str, kind: str) -> int | None:
    """
    Validate a JWT and return the user id if valid AND of the expected kind.

    Returns None on any signature, expiry, kind mismatch, or missing subject error.
    """
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        return None
    if data.get("kind") != kind:
        return None
    try:
        return int(data["sub"])
    except (KeyError, ValueError):
        return None


def new_otp() -> str:
    """
    Generate a 6-digit OTP string with leading zeros if needed.

    Uses cryptographically secure randomness.
    """
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(code: str) -> str:
    """
    Hash an OTP using HMAC-SHA256 with the JWT secret as the key.

    Never store the plain OTP; store this hash for comparison.
    """
    return hmac.new(JWT_SECRET.encode(), code.encode(), hashlib.sha256).hexdigest()


def same(a: str, b: str) -> bool:
    """
    Compare two strings in constant time to avoid timing attacks.
    """
    return hmac.compare_digest(a, b)