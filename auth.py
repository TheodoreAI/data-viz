import re

from models import User, db

USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{3,32}$')
EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MIN_PASSWORD_LENGTH = 8


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
