from app.core.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM_EMAIL


def send_verification_email(to_email: str, token: str):
    verification_url = f"http://localhost:8000/auth/verify-email?token={token}"

    print(f"\n{'=' * 60}")
    print(f"Письмо для подтверждения email: {to_email}")
    print(f"Ссылка: {verification_url}")
    print(f"{'=' * 60}\n")


def send_password_reset_email(to_email: str, token: str):
    reset_url = f"http://localhost:8000/auth/reset-password?token={token}"

    print(f"\n{'=' * 60}")
    print(f"Письмо для восстановления пароля: {to_email}")
    print(f"Ссылка для сброса пароля: {reset_url}")
    print(f"Токен действителен 1 час")
    print(f"{'=' * 60}\n")