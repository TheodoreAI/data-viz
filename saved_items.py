from models import SavedItem, db

VALID_ITEM_TYPES = {'painting', 'article'}
MAX_TITLE_LENGTH = 255
MAX_SUBTITLE_LENGTH = 255


def validate_saved_item(item_type, title, source_url):
    errors = {}
    if item_type not in VALID_ITEM_TYPES:
        errors['itemType'] = 'Unknown item type.'
    if not title or len(title) > MAX_TITLE_LENGTH:
        errors['title'] = 'Title is required.'
    if not source_url:
        errors['sourceUrl'] = 'Source URL is required.'
    return errors


def save_item(user, item_type, title, subtitle, image_url, source_url):
    """Returns (item, errors). On success errors is {}; on failure item is None."""
    errors = validate_saved_item(item_type, title, source_url)
    if errors:
        return None, errors

    existing = SavedItem.query.filter_by(
        user_id=user.id, item_type=item_type, source_url=source_url
    ).first()
    if existing:
        return existing, {}

    item = SavedItem(
        user_id=user.id,
        item_type=item_type,
        title=title[:MAX_TITLE_LENGTH],
        subtitle=(subtitle or '')[:MAX_SUBTITLE_LENGTH] or None,
        image_url=image_url or None,
        source_url=source_url,
    )
    db.session.add(item)
    db.session.commit()
    return item, {}


def list_saved_items(user, item_type=None):
    query = SavedItem.query.filter_by(user_id=user.id)
    if item_type:
        query = query.filter_by(item_type=item_type)
    return query.order_by(SavedItem.created_at.desc()).all()


def delete_saved_item(user, item_id):
    """Returns True if deleted, False if not found or not owned by user."""
    item = SavedItem.query.filter_by(id=item_id, user_id=user.id).first()
    if not item:
        return False
    db.session.delete(item)
    db.session.commit()
    return True
