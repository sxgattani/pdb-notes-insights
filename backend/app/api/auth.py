from fastapi import APIRouter, HTTPException, Response, Request, Cookie
from pydantic import BaseModel
from typing import Optional

from app.config import get_settings
from app.services.auth import (
    verify_credentials,
    create_session,
    validate_session,
    invalidate_session,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE_NAME = "session_token"


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    message: str
    username: str


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, response: Response):
    """Authenticate and create a session."""
    if not verify_credentials(request.username, request.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_session(request.username)
    settings = get_settings()

    # Set session cookie (httponly for security)
    # Use SameSite=None for secure cookies to work with API requests
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.secure_cookies,  # True for HTTPS (production)
        samesite="none" if settings.secure_cookies else "lax",
        path="/",
        max_age=60 * 60 * 24,  # 24 hours
    )

    return LoginResponse(message="Login successful", username=request.username)


@router.post("/logout")
def logout(
    response: Response,
    session_token: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
):
    """Logout and invalidate the session."""
    if session_token:
        invalidate_session(session_token)

    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"message": "Logged out successfully"}


@router.get("/me")
def get_me(session_token: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME)):
    """Get current authenticated user."""
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    username = get_current_user(session_token)
    if not username:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    return {"username": username, "authenticated": True}
