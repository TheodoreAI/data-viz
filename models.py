from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.String(280), nullable=False, default='')
    display_name = db.Column(db.String(64), nullable=True)
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
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'lastLoginAt': self.last_login_at.isoformat() if self.last_login_at else None,
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
            'createdAt': self.created_at.isoformat() if self.created_at else None,
        }


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    body = db.Column(db.String(1000), nullable=False)
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
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'author': {
                'id': self.author.id,
                'username': self.author.username,
                'displayName': self.author.display_name,
                'avatarUrl': f'https://api.dicebear.com/9.x/identicon/svg?seed={self.author.username}',
            },
            'sharedItem': self.saved_item.to_dict() if self.saved_item else None,
        }
