from datetime import datetime, timezone

from models import UvReading, UvSession, db

MAX_SESSION_HISTORY = 30


def start_session(user):
    session = UvSession(user_id=user.id)
    db.session.add(session)
    db.session.commit()
    return session


def get_open_session(user, session_id):
    """Returns the session if it exists, belongs to the user, and is still open."""
    return UvSession.query.filter_by(id=session_id, user_id=user.id, ended_at=None).first()


def add_reading(session, lat, lon, uv_index):
    reading = UvReading(session_id=session.id, latitude=lat, longitude=lon, uv_index=uv_index)
    db.session.add(reading)
    db.session.commit()
    return reading


def end_session(session):
    session.ended_at = datetime.now(timezone.utc)
    db.session.commit()
    return session


def get_session(user, session_id):
    return UvSession.query.filter_by(id=session_id, user_id=user.id).first()


def list_sessions(user):
    return (
        UvSession.query.filter_by(user_id=user.id)
        .order_by(UvSession.started_at.desc())
        .limit(MAX_SESSION_HISTORY)
        .all()
    )
