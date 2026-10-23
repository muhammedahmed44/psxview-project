"""Application configuration loaded from environment variables or backend/.env."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Resolve the local development file relative to this module. Cloud hosts inject
# variables directly, and those values take precedence over this file.
load_dotenv(Path(__file__).with_name(".env"))


def normalize_database_url(value: str) -> str:
    """Select psycopg 3 when a hosting provider supplies a PostgreSQL URL."""
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, value)


# SQLite remains the zero-setup local default. Render supplies PostgreSQL via
# DATABASE_URL and the normalization above selects the installed psycopg driver.
DATABASE_URL = normalize_database_url(
    os.getenv("DATABASE_URL", "sqlite:///./psxviewai.db")
)

# Used to sign login cookies. CHANGE in .env. Generate one with:
#   python -c "import secrets; print(secrets.token_urlsafe(48))"
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-change-me-please-use-a-long-random-string")
JWT_ALG = "HS256"

SESSION_MINUTES = 60 * 8          # how long a logged-in cookie lasts (8 hours)
OTP_MINUTES = 10                  # how long an email code is valid
OTP_MAX_ATTEMPTS = 5              # wrong guesses allowed per code before it is burned
COOKIE_NAME = "psx_session"       # name of the browser cookie that holds the session token
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "0") == "1"   # set 1 when using https

# Extra origins are only needed when the frontend is hosted separately. The
# Vercel proxies /api to Render, so production requests also remain same-origin.
_LOCAL_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:5174,http://127.0.0.1:5174,"
    "http://localhost:4173,http://127.0.0.1:4173"
)
_cors_value = os.getenv("CORS_ORIGINS", "").strip() or _LOCAL_ORIGINS
CORS_ORIGINS = [
    origin.strip()
    for origin in _cors_value.split(",")
    if origin.strip()
]

# Email (optional). If SMTP_HOST is empty, codes are printed in the server log instead of sent.
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@psxviewai.local")

# HTTPS email delivery works on cloud plans where outbound SMTP is blocked.
# RESEND_FROM must use a sender/domain authorized in the Resend account.
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_FROM = os.getenv("RESEND_FROM", "PSXviewAI <onboarding@resend.dev>").strip()

# Google Gemini API key and model name, used for AI valuation explanations.
# Stripped to avoid failures from accidental leading/trailing whitespace in .env.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()

# Live economic-news collection is opt-in so tests and local development do not
# unexpectedly make network requests. The task runs after API startup and keeps
# the previous good snapshot when a refresh fails.
NEWS_PIPELINE_ENABLED = _env_bool("NEWS_PIPELINE_ENABLED", False)
NEWS_PIPELINE_INTERVAL_MINUTES = _env_int("NEWS_PIPELINE_INTERVAL_MINUTES", 60, 15)
NEWS_PIPELINE_TIMEOUT_SECONDS = _env_int("NEWS_PIPELINE_TIMEOUT_SECONDS", 600, 60)
