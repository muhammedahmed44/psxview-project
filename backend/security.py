"""Password hashing, signed tokens, and authenticator helpers."""
import base64
import hashlib
import hmac
import secrets
import time
from io import BytesIO
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import pyotp
import qrcode
import qrcode.image.svg
from cryptography.fernet import Fernet, InvalidToken

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
    payload = {
        "sub": str(user_id),
        "kind": kind,
        "jti": secrets.token_urlsafe(12),
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
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


def _totp_cipher() -> Fernet:
    """Derive a stable Fernet key from the deployment's JWT secret."""
    digest = hashlib.sha256(f"psxviewai:totp:{JWT_SECRET}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_totp_secret(secret: str) -> str:
    """Encrypt a TOTP seed before storing it in the database."""
    return _totp_cipher().encrypt(secret.encode()).decode()


def decrypt_totp_secret(encrypted: str) -> str:
    """Decrypt a stored TOTP seed, raising ValueError on a key mismatch."""
    try:
        return _totp_cipher().decrypt(encrypted.encode()).decode()
    except (InvalidToken, ValueError) as exc:
        raise ValueError("Stored authenticator secret cannot be decrypted") from exc


def new_totp_secret() -> str:
    """Return a new RFC 6238-compatible base32 authenticator secret."""
    return pyotp.random_base32()


def totp_uri(secret: str, email: str) -> str:
    """Build the standard otpauth URI understood by authenticator apps."""
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="PSXviewAI")


def totp_qr_data_url(uri: str) -> str:
    """Encode an otpauth URI as an inline SVG QR image."""
    image = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage)
    output = BytesIO()
    image.save(output)
    encoded = base64.b64encode(output.getvalue()).decode()
    return f"data:image/svg+xml;base64,{encoded}"


def matching_totp_counter(secret: str, code: str, valid_window: int = 1) -> int | None:
    """Return the matching 30-second counter, allowing modest clock skew."""
    if len(code) != 6 or not code.isdigit():
        return None
    totp = pyotp.TOTP(secret)
    current = int(time.time()) // totp.interval
    for offset in range(-valid_window, valid_window + 1):
        counter = current + offset
        if counter >= 0 and same(totp.generate_otp(counter), code):
            return counter
    return None


def new_recovery_codes(count: int = 8) -> list[str]:
    """Generate one-time recovery codes to show once after enrollment."""
    codes = []
    for _ in range(count):
        raw = secrets.token_hex(5).upper()
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes


def normalize_recovery_code(code: str) -> str:
    return "".join(character for character in code.upper() if character.isalnum())


def hash_recovery_code(code: str) -> str:
    """HMAC a normalized recovery code for safe database storage."""
    normalized = normalize_recovery_code(code)
    return hmac.new(
        JWT_SECRET.encode(),
        f"recovery:{normalized}".encode(),
        hashlib.sha256,
    ).hexdigest()
