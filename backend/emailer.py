
"""Send the 2FA code. No SMTP configured -> print to the server log (dev mode)."""
import logging
import smtplib
from email.message import EmailMessage

import config

# Logger for this module, labeled so backend logs show "psxviewai.email".
log = logging.getLogger("psxviewai.email")


def send_otp(to_email: str, code: str) -> None:
    """
    Send the 6-digit OTP to the user by email.

    If SMTP_HOST is not configured, the code is printed in the server log instead
    (useful for local development).
    """
    # No SMTP host configured: log the code instead of sending.
    if not config.SMTP_HOST:
        log.warning("DEV MODE - 2FA code for %s is %s", to_email, code)
        return

    # Build a simple plain-text email with the code and expiry time.
    msg = EmailMessage()
    msg["Subject"] = "Your PSXviewAI verification code"
    msg["From"] = config.SMTP_FROM
    msg["To"] = to_email
    msg.set_content(f"Your code is {code}. It expires in {config.OTP_MINUTES} minutes.")

    # Connect to the SMTP server, upgrade to TLS, authenticate if credentials exist,
    # and send the message.
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as s:
        s.starttls()
        if config.SMTP_USER:
            s.login(config.SMTP_USER, config.SMTP_PASSWORD)
        s.send_message(msg)