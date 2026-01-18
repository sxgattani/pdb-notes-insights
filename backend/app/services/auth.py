import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from app.config import get_settings

# In-memory session store (simple approach for small team)
# In production, consider Redis or database-backed sessions
_sessions: dict[str, dict] = {}

SESSION_DURATION_HOURS = 24


def verify_credentials(username: str, password: str) -> bool:
    """Verify username and password against configured credentials."""
    settings = get_settings()
    return (
        username == settings.auth_username and
        password == settings.auth_password
    )


def create_session(username: str) -> str:
    """Create a new session and return the session token."""
    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "username": username,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS),
    }
    return token


def validate_session(token: str) -> Optional[dict]:
    """Validate a session token and return session data if valid."""
    session = _sessions.get(token)
    if not session:
        return None

    if datetime.utcnow() > session["expires_at"]:
        # Session expired, remove it
        del _sessions[token]
        return None

    return session


def invalidate_session(token: str) -> bool:
    """Invalidate (logout) a session. Returns True if session existed."""
    if token in _sessions:
        del _sessions[token]
        return True
    return False


def get_current_user(token: str) -> Optional[str]:
    """Get username for a valid session token."""
    session = validate_session(token)
    if session:
        return session["username"]
    return None
