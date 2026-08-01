import re

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from models import User, db

USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{3,32}$')
EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MIN_PASSWORD_LENGTH = 8
MAX_BIO_LENGTH = 280
MAX_DISPLAY_NAME_LENGTH = 64
RESET_TOKEN_SALT = 'password-reset'
RESET_TOKEN_MAX_AGE_SECONDS = 3600


def validate_registration(username, email, password):
    errors = {}
    if not username or not USERNAME_PATTERN.match(username):
        errors['username'] = 'Username must be 3-32 characters: letters, numbers, or underscores.'
    if not email or not EMAIL_PATTERN.match(email):
        errors['email'] = 'Enter a valid email address.'
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        errors['password'] = f'Password must be at least {MIN_PASSWORD_LENGTH} characters.'
    return errors


def register_user(username, email, password):
    """Returns (user, errors). On success errors is {}; on failure user is None."""
    errors = validate_registration(username, email, password)
    if errors:
        return None, errors

    if User.query.filter_by(username=username).first():
        return None, {'username': 'That username is already taken.'}
    if User.query.filter_by(email=email).first():
        return None, {'email': 'An account with that email already exists.'}

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user, {}


def authenticate_user(identifier, password):
    """identifier may be a username or an email. Returns the User or None."""
    if not identifier or not password:
        return None
    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()
    if user and user.check_password(password):
        return user
    return None


def update_bio(user, bio):
    """Returns errors dict; {} on success. Updates and commits in place."""
    if len(bio) > MAX_BIO_LENGTH:
        return {'bio': f'Bio must be {MAX_BIO_LENGTH} characters or fewer.'}
    user.bio = bio
    db.session.commit()
    return {}


def update_display_name(user, display_name):
    """Returns errors dict; {} on success. Updates and commits in place."""
    if len(display_name) > MAX_DISPLAY_NAME_LENGTH:
        return {'displayName': f'Display name must be {MAX_DISPLAY_NAME_LENGTH} characters or fewer.'}
    user.display_name = display_name or None
    db.session.commit()
    return {}


def change_password(user, current_password, new_password):
    """Returns errors dict; {} on success. Updates and commits in place."""
    if not user.check_password(current_password):
        return {'currentPassword': 'Current password is incorrect.'}
    if not new_password or len(new_password) < MIN_PASSWORD_LENGTH:
        return {'newPassword': f'Password must be at least {MIN_PASSWORD_LENGTH} characters.'}
    user.set_password(new_password)
    db.session.commit()
    return {}


def delete_account(user, password):
    """Returns errors dict; {} on success, in which case the user is deleted."""
    if not user.check_password(password):
        return {'password': 'Incorrect password.'}
    db.session.delete(user)
    db.session.commit()
    return {}


def _reset_token_serializer(secret_key):
    return URLSafeTimedSerializer(secret_key, salt=RESET_TOKEN_SALT)


def generate_reset_token(secret_key, user):
    """Signed, expiring, DB-free reset token. Embeds a password-hash fragment
    so it's automatically invalidated the moment the password changes."""
    serializer = _reset_token_serializer(secret_key)
    return serializer.dumps({'user_id': user.id, 'pw': user.password_hash[-16:]})


def verify_reset_token(secret_key, token):
    """Returns the User the token was issued for, or None if invalid/expired/stale."""
    serializer = _reset_token_serializer(secret_key)
    try:
        data = serializer.loads(token, max_age=RESET_TOKEN_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None

    user = db.session.get(User, data.get('user_id'))
    if not user or user.password_hash[-16:] != data.get('pw'):
        return None
    return user


def reset_password(user, new_password):
    """Returns errors dict; {} on success. Updates and commits in place."""
    if not new_password or len(new_password) < MIN_PASSWORD_LENGTH:
        return {'newPassword': f'Password must be at least {MIN_PASSWORD_LENGTH} characters.'}
    user.set_password(new_password)
    db.session.commit()
    return {}
