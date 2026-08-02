from models import Post, SavedItem, db

MAX_BODY_LENGTH = 1000
PAGE_SIZE = 20


def validate_post(body):
    errors = {}
    if not body or not body.strip():
        errors['body'] = 'Post cannot be empty.'
    elif len(body) > MAX_BODY_LENGTH:
        errors['body'] = f'Post cannot be longer than {MAX_BODY_LENGTH} characters.'
    return errors


def create_post(user, body, saved_item_id=None):
    """Returns (post, errors). On success errors is {}; on failure post is None."""
    body = (body or '').strip()
    errors = validate_post(body)

    saved_item = None
    if saved_item_id is not None:
        saved_item = SavedItem.query.filter_by(id=saved_item_id, user_id=user.id).first()
        if not saved_item:
            errors['savedItemId'] = 'Saved item not found.'

    if errors:
        return None, errors

    post = Post(user_id=user.id, body=body, saved_item_id=saved_item.id if saved_item else None)
    db.session.add(post)
    db.session.commit()
    return post, {}


def list_posts(before_id=None, limit=PAGE_SIZE):
    """Newest-first feed, optionally paginated by returning posts older than before_id."""
    query = Post.query.order_by(Post.id.desc())
    if before_id is not None:
        query = query.filter(Post.id < before_id)
    return query.limit(limit).all()


def get_post(post_id):
    return Post.query.get(post_id)


def delete_post(user, post_id):
    """Returns True if deleted, False if not found or not owned by user."""
    post = Post.query.filter_by(id=post_id, user_id=user.id).first()
    if not post:
        return False
    db.session.delete(post)
    db.session.commit()
    return True
