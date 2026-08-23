from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


def _isoformat_utc(dt):
    """SQLite drops tzinfo on read-back, so a value stored as UTC comes back
    naive; isoformat() on a naive datetime omits the offset, and JS then
    parses that string as local time instead of UTC. Stamp 'Z' explicitly
    for any naive datetime so JSON consumers always parse it as UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + 'Z'
    return dt.isoformat()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.String(280), nullable=False, default='')
    display_name = db.Column(db.String(64), nullable=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login_at = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'bio': self.bio,
            'displayName': self.display_name,
            'avatarUrl': f'https://api.dicebear.com/9.x/identicon/svg?seed={self.username}',
            'isAdmin': self.is_admin,
            'createdAt': _isoformat_utc(self.created_at),
            'lastLoginAt': _isoformat_utc(self.last_login_at),
        }


class SavedItem(db.Model):
    __table_args__ = (
        db.UniqueConstraint('user_id', 'item_type', 'source_url', name='uq_saved_item_per_user'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    item_type = db.Column(db.String(16), nullable=False)  # 'painting' or 'article'
    title = db.Column(db.String(255), nullable=False)
    subtitle = db.Column(db.String(255), nullable=True)
    image_url = db.Column(db.String(1024), nullable=True)
    source_url = db.Column(db.String(1024), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'itemType': self.item_type,
            'title': self.title,
            'subtitle': self.subtitle,
            'imageUrl': self.image_url,
            'sourceUrl': self.source_url,
            'createdAt': _isoformat_utc(self.created_at),
        }


class UvSession(db.Model):
    """A single tracked jog/walk: a run of UvReadings from start to stop."""
    __tablename__ = 'uv_session'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = db.Column(db.DateTime, nullable=True)

    readings = db.relationship(
        'UvReading', backref='session', order_by='UvReading.recorded_at', cascade='all, delete-orphan'
    )

    def to_dict(self, include_readings=False):
        duration_minutes = None
        if self.ended_at and self.started_at:
            duration_minutes = round((self.ended_at - self.started_at).total_seconds() / 60, 1)
        uv_values = [r.uv_index for r in self.readings]
        data = {
            'id': self.id,
            'startedAt': _isoformat_utc(self.started_at),
            'endedAt': _isoformat_utc(self.ended_at),
            'durationMinutes': duration_minutes,
            'readingCount': len(uv_values),
            'avgUvIndex': round(sum(uv_values) / len(uv_values), 2) if uv_values else None,
            'maxUvIndex': max(uv_values) if uv_values else None,
            # UV-index-minutes: sum of (uv * minutes since the previous reading) across the
            # session — a rough proxy for cumulative UV exposure, not a clinical dose unit.
            'exposureScore': self._exposure_score(),
        }
        if include_readings:
            data['readings'] = [r.to_dict() for r in self.readings]
        return data

    def _exposure_score(self):
        if len(self.readings) < 2:
            return None
        total = 0.0
        for prev, curr in zip(self.readings, self.readings[1:]):
            minutes = (curr.recorded_at - prev.recorded_at).total_seconds() / 60
            total += prev.uv_index * minutes
        return round(total, 1)


class UvReading(db.Model):
    __tablename__ = 'uv_reading'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('uv_session.id'), nullable=False, index=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    uv_index = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'lat': self.latitude,
            'lon': self.longitude,
            'uvIndex': self.uv_index,
            'recordedAt': _isoformat_utc(self.recorded_at),
        }


class Essay(db.Model):
    __tablename__ = 'essay'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    body = db.Column(db.String(3000), nullable=False)
    saved_item_id = db.Column(db.Integer, db.ForeignKey('saved_item.id'), nullable=True)
    image_url = db.Column(db.String(1024), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    author = db.relationship('User')
    saved_item = db.relationship('SavedItem')

    def to_dict(self):
        return {
            'id': self.id,
            'body': self.body,
            'imageUrl': self.image_url,
            'createdAt': _isoformat_utc(self.created_at),
            'author': {
                'id': self.author.id,
                'username': self.author.username,
                'displayName': self.author.display_name,
                'avatarUrl': f'https://api.dicebear.com/9.x/identicon/svg?seed={self.author.username}',
            },
            'sharedItem': self.saved_item.to_dict() if self.saved_item else None,
        }
