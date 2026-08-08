from models import Essay, SavedItem, db

MAX_BODY_LENGTH = 3000
PAGE_SIZE = 20


def validate_essay(body):
    errors = {}
    if not body or not body.strip():
        errors['body'] = 'Essay cannot be empty.'
    elif len(body) > MAX_BODY_LENGTH:
        errors['body'] = f'Essay cannot be longer than {MAX_BODY_LENGTH} characters.'
    return errors


def create_essay(user, body, saved_item_id=None, image_url=None):
    """Returns (essay, errors). On success errors is {}; on failure essay is None."""
    body = (body or '').strip()
    errors = validate_essay(body)

    saved_item = None
    if saved_item_id is not None:
        saved_item = SavedItem.query.filter_by(id=saved_item_id, user_id=user.id).first()
        if not saved_item:
            errors['savedItemId'] = 'Saved item not found.'

    if errors:
        return None, errors

    essay = Essay(
        user_id=user.id,
        body=body,
        saved_item_id=saved_item.id if saved_item else None,
        image_url=image_url or None,
    )
    db.session.add(essay)
    db.session.commit()
    return essay, {}


def list_essays(before_id=None, limit=PAGE_SIZE):
    """Newest-first feed, optionally paginated by returning essays older than before_id."""
    query = Essay.query.order_by(Essay.id.desc())
    if before_id is not None:
        query = query.filter(Essay.id < before_id)
    return query.limit(limit).all()


def get_essay(essay_id):
    return Essay.query.get(essay_id)


def delete_essay(user, essay_id):
    """Returns True if deleted, False if not found or not owned by user."""
    essay = Essay.query.filter_by(id=essay_id, user_id=user.id).first()
    if not essay:
        return False
    db.session.delete(essay)
    db.session.commit()
    return True
