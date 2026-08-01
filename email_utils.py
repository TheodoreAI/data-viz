def send_password_reset_email(user, reset_url):
    """Placeholder email 'delivery' — logs the link instead of sending real mail.

    Swap this out for a real provider (SES, SendGrid, SMTP via Flask-Mail, etc.)
    before this matters for anyone but the developer testing locally.
    """
    print(f'[password reset] Send this link to {user.email}: {reset_url}')
