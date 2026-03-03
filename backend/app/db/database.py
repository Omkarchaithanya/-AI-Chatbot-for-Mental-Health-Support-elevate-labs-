"""MindEase PRO — Database Initialization"""
import logging
from sqlalchemy import text

logger = logging.getLogger("mindease.db")


def init_db(app) -> None:
    """Create all tables and enable WAL mode for SQLite."""
    from app.extensions import db
    from app.db import models  # noqa: F401 — ensure models are registered

    db.create_all()

    # Enable WAL mode for better concurrent access on SQLite
    try:
        db.session.execute(text("PRAGMA journal_mode=WAL"))
        db.session.execute(text("PRAGMA synchronous=NORMAL"))
        db.session.commit()
        logger.info("SQLite WAL mode enabled ✓")
    except Exception as exc:
        logger.warning(f"WAL mode not available (non-SQLite DB?): {exc}")


def get_or_create_user(session_id: str):
    """Return existing User or create a new one."""
    from app.db.models import User
    from app.extensions import db
    from datetime import datetime, timezone

    user = User.query.filter_by(session_id=session_id).first()
    if not user:
        user = User(session_id=session_id)
        db.session.add(user)
        db.session.commit()
        logger.debug(f"Created new user session: {session_id}")
    else:
        user.last_active = datetime.now(timezone.utc)
        db.session.commit()
    return user
