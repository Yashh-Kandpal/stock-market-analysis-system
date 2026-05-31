"""
Auth utilities.
- Verifies Google ID tokens using google-auth library
- Creates and verifies our own JWTs
- Provides get_current_user dependency for protected routes
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db, User

# ── config ────────────────────────────────────────────────────────────────────
def _secret():
    return os.getenv("JWT_SECRET", "change-this-to-a-long-random-secret-in-production")
ALGORITHM       = "HS256"
TOKEN_EXPIRE_DAYS = 30
GOOGLE_CLIENT_ID  = os.getenv("GOOGLE_CLIENT_ID", "")

bearer_scheme = HTTPBearer(auto_error=False)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_jwt(user_id: int, email: str) -> str:
    payload = {
        "sub":   str(user_id),
        "email": email,
        "exp":   datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS),
        "iat":   datetime.utcnow(),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


# ── Google token verification ─────────────────────────────────────────────────

def verify_google_token(google_token: str) -> dict:
    """
    Verifies a Google ID token and returns the user info payload.
    Raises HTTPException if the token is invalid.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")
    try:
        info = id_token.verify_oauth2_token(
            google_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10,
        )
        return info
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")


# ── FastAPI dependency ────────────────────────────────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency for protected routes.
    Extracts JWT from Authorization header, verifies it, returns User object.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_jwt(credentials.credentials)
    user_id = int(payload.get("sub", 0))

    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of raising if not logged in."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
