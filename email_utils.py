import threading

import requests

RESEND_API_URL = 'https://api.resend.com/emails'
REQUEST_TIMEOUT_SECONDS = 10

_config = None
_configured = False


def init_mail(config, configured):
    """Called once at app startup with the Resend config dict (api_key,
    from_email) and whether a real API key was provided."""
    global _config, _configured
    _config = config
    _configured = configured
    if not configured:
        print(
            'WARNING: RESEND_API_KEY is not set; password reset links will '
            'be printed to the console instead of emailed.'
        )


def _send_via_resend(to_email, subject, body):
    try:
        response = requests.post(
            RESEND_API_URL,
            headers={'Authorization': f"Bearer {_config['api_key']}"},
            json={
                'from': _config['from_email'],
                'to': [to_email],
                'subject': subject,
                'text': body,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if not response.ok:
            print(f'[email] Resend rejected send to {to_email}: {response.status_code} {response.text}')
    except requests.RequestException as error:
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
    # Send on a background thread with a hard timeout so a slow/unreachable
    # provider can never block the request or trip the gunicorn worker
    # timeout — this is what actually broke with raw SMTP on Render.
    threading.Thread(target=_send_via_resend, args=(user.email, subject, body), daemon=True).start()
