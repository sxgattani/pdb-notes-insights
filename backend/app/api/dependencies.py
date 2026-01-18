from fastapi import Cookie, HTTPException, Depends
from typing import Optional

from app.services.auth import get_current_user

SESSION_COOKIE_NAME = "session_token"


def get_session_token(
    session_token: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME)
) -> Optional[str]:
    """Extract session token from cookie."""
    return session_token


def require_auth(token: Optional[str] = Depends(get_session_token)) -> str:
    """Dependency that requires a valid session. Returns username."""
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = get_current_user(token)
    if not username:
        raise HTTPException(
            status_code=401,
            detail="Session expired or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return username


def optional_auth(token: Optional[str] = Depends(get_session_token)) -> Optional[str]:
    """Dependency that optionally checks auth. Returns username or None."""
    if not token:
        return None
    return get_current_user(token)
