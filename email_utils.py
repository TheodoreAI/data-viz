import smtplib
import threading
from email.mime.text import MIMEText

SMTP_TIMEOUT_SECONDS = 10

_config = None
_configured = False


def init_mail(config, configured):
    """Called once at app startup with the SMTP config dict (server, port,
    username, password) and whether real credentials were provided."""
    global _config, _configured
    _config = config
    _configured = configured
    if not configured:
        print(
            'WARNING: MAIL_USERNAME/MAIL_PASSWORD are not set; password reset '
            'links will be printed to the console instead of emailed.'
        )


def _send_smtp(to_email, subject, body):
    message = MIMEText(body)
    message['Subject'] = subject
    message['From'] = _config['username']
    message['To'] = to_email
    try:
        with smtplib.SMTP(_config['server'], _config['port'], timeout=SMTP_TIMEOUT_SECONDS) as smtp:
            smtp.starttls()
            smtp.login(_config['username'], _config['password'])
            smtp.sendmail(_config['username'], [to_email], message.as_string())
    except Exception as error:
        # This runs on a background thread after the request has already
        # returned, so there's no request to fail — just log it.
        print(f'[email] failed to send to {to_email}: {error}')


def send_password_reset_email(user, reset_url):
    if not _configured:
        print(f'[password reset] Send this link to {user.email}: {reset_url}')
        return

    subject = 'Reset your password'
    body = (
        f'Hi {user.username},\n\n'
        f'Someone requested a password reset for your account. '
        f'If this was you, click the link below to choose a new password:\n\n'
        f'{reset_url}\n\n'
        f"If you didn't request this, you can safely ignore this email.\n"
    )
    # Never block the request on an external SMTP call — smtplib has no
    # connect timeout of its own by default and a slow/blocked connection
    # can hang long enough to trip the gunicorn worker timeout.
    threading.Thread(target=_send_smtp, args=(user.email, subject, body), daemon=True).start()
