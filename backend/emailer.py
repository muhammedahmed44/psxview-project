
"""Send 2FA codes through Resend HTTPS, SMTP, or the local development log."""
import logging
import smtplib
from email.message import EmailMessage

import httpx

import config

# Logger for this module, labeled so backend logs show "psxviewai.email".
log = logging.getLogger("psxviewai.email")


def send_otp(to_email: str, code: str) -> None:
    """
    Send the 6-digit OTP to the user by email.

    Resend is preferred when configured because HTTPS works on cloud hosts that
    block outbound SMTP. SMTP remains available for local or compatible hosts.
    """
    content = f"Your code is {code}. It expires in {config.OTP_MINUTES} minutes."

    if config.RESEND_API_KEY:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {config.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": config.RESEND_FROM,
                "to": [to_email],
                "subject": "Your PSXviewAI verification code",
                "text": content,
            },
            timeout=15,
        )
        response.raise_for_status()
        log.info("Sent 2FA code to %s through Resend", to_email)
        return

    if config.SMTP_HOST:
        msg = EmailMessage()
        msg["Subject"] = "Your PSXviewAI verification code"
        msg["From"] = config.SMTP_FROM
        msg["To"] = to_email
        msg.set_content(content)

        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as server:
            server.starttls()
            if config.SMTP_USER:
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
        return

    log.warning("DEV MODE - 2FA code for %s is %s", to_email, code)
