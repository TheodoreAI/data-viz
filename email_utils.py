from flask_mail import Message

_mail = None
_configured = False


def init_mail(mail, configured):
    """Called once at app startup with the Flask-Mail instance and whether
    real SMTP credentials (MAIL_USERNAME/MAIL_PASSWORD) were provided."""
    global _mail, _configured
    _mail = mail
    _configured = configured
    if not configured:
        print(
            'WARNING: MAIL_USERNAME/MAIL_PASSWORD are not set; password reset '
            'links will be printed to the console instead of emailed.'
        )


def send_password_reset_email(user, reset_url):
    if not _configured:
        print(f'[password reset] Send this link to {user.email}: {reset_url}')
        return

    message = Message(
        subject='Reset your password',
        recipients=[user.email],
        body=(
            f'Hi {user.username},\n\n'
            f'Someone requested a password reset for your account. '
            f'If this was you, click the link below to choose a new password:\n\n'
            f'{reset_url}\n\n'
            f"If you didn't request this, you can safely ignore this email.\n"
        ),
    )
    _mail.send(message)
