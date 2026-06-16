import smtplib
from email.message import EmailMessage

from app.core.config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    FROM_EMAIL,
    BASE_URL,
)

def send_email(to_email: str, subject: str, body: str):
    message = EmailMessage()
    message["From"] = FROM_EMAIL
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP_SSL(SMTP_HOST, int(SMTP_PORT)) as server:
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(message)

def send_verification_email(to_email: str, token: str):
    verification_url = f"{BASE_URL}/auth/verify-email?token={token}"

    body = f"""Здравствуйте!

Для подтверждения регистрации в TeamBox перейдите по ссылке:

{verification_url}

Если вы не регистрировались в TeamBox, проигнорируйте это письмо.
"""

    send_email(to_email, "Подтверждение регистрации TeamBox", body)

def send_password_reset_email(to_email: str, token: str):
    reset_url = f"{BASE_URL}/auth/reset-password?token={token}"

    body = f"""Здравствуйте!

Для восстановления пароля перейдите по ссылке:

{reset_url}

Если вы не запрашивали восстановление пароля, проигнорируйте это письмо.
"""

    send_email(to_email, "Восстановление пароля TeamBox", body)