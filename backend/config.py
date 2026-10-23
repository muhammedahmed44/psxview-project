"""All settings in one place. Values come from backend/.env (see .example.env)."""
import os
from dotenv import load_dotenv

# Load variables from a .env file if present. This must run before any setting is read.
load_dotenv()

# Database connection string. Defaults to a local SQLite file in the backend folder.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./psxviewai.db")

# Used to sign login cookies. CHANGE in .env. Generate one with:
#   python -c "import secrets; print(secrets.token_urlsafe(48))"
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-change-me-please-use-a-long-random-string")
JWT_ALG = "HS256"

SESSION_MINUTES = 60 * 8          # how long a logged-in cookie lasts (8 hours)
OTP_MINUTES = 10                  # how long an email code is valid
OTP_MAX_ATTEMPTS = 5              # wrong guesses allowed per code before it is burned
COOKIE_NAME = "psx_session"       # name of the browser cookie that holds the session token
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "0") == "1"   # set 1 when using https

# Email (optional). If SMTP_HOST is empty, codes are printed in the server log instead of sent.
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@psxviewai.local")

# Google Gemini API key and model name, used for AI valuation explanations.
# Stripped to avoid failures from accidental leading/trailing whitespace in .env.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()