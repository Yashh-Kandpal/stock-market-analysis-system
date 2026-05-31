"""
Auth Router — /api/auth/...

POST /api/auth/google   — receive Google ID token, return JWT + user info
GET  /api/auth/me       — return current user info
POST /api/auth/logout   — client-side only (just returns 200)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from datetime import datetime

from database import get_db, User
from auth import verify_google_token, create_jwt, get_current_user

router = APIRouter()


class GoogleAuthRequest(BaseModel):
    token: str   # Google ID token from frontend


@router.post("/google")
async def google_login(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """
    1. Verify the Google ID token
    2. Find or create the user in DB
    3. Return our JWT + user info
    """
    info = verify_google_token(body.token)

    google_id = info.get("sub")
    email     = info.get("email")
    name      = info.get("name", "")
    avatar    = info.get("picture", "")

    if not google_id or not email:
        raise HTTPException(status_code=400, detail="Invalid Google token payload")

    # Find existing user
    result = await db.execute(select(User).where(User.google_id == google_id))
    user   = result.scalar()

    if user:
        # Update last login + name/avatar in case they changed
        user.last_login = datetime.utcnow()
        user.name       = name
        user.avatar_url = avatar
        await db.commit()
        await db.refresh(user)
    else:
        # Create new user
        user = User(
            google_id  = google_id,
            email      = email,
            name       = name,
            avatar_url = avatar,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_jwt(user.id, user.email)

    return {
        "access_token": token,
        "token_type":   "bearer",
        "user": {
            "id":         user.id,
            "email":      user.email,
            "name":       user.name,
            "avatar_url": user.avatar_url,
        },
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Return current authenticated user's info."""
    return {
        "id":         current_user.id,
        "email":      current_user.email,
        "name":       current_user.name,
        "avatar_url": current_user.avatar_url,
        "created_at": current_user.created_at.isoformat(),
        "last_login": current_user.last_login.isoformat(),
    }


@router.post("/logout")
async def logout():
    """
    JWT is stateless — logout is handled client-side by deleting the token.
    This endpoint exists for completeness / future token blacklisting.
    """
    return {"message": "Logged out successfully"}
