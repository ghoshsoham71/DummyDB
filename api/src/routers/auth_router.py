"""
Auth Router — signup, login, logout, and current-user endpoints.
Thin proxy over Supabase Auth so the frontend doesn't need direct Supabase calls for auth.
"""

import os
import logging
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr
from supabase import create_client, Client
from dotenv import load_dotenv

from src.lib.auth import get_current_user
from src.lib.supabase_client import get_supabase_client

load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"], prefix="/auth")


# ── Schemas ───────────────────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict


# ── Helpers ───────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_auth_client() -> Client:
    url = os.getenv("SUPABASE_URL", "")
    anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    if not url or not anon_key:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
    return create_client(url, anon_key)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/signup")
async def signup(payload: AuthRequest):
    """Create a new account with email + password."""
    try:
        client = _get_auth_client()
        result = client.auth.sign_up({
            "email": payload.email,
            "password": payload.password,
        })

        if not result.user:
            raise HTTPException(status_code=400, detail="Signup failed")

        session = result.session
        return {
            "message": "Account created successfully",
            "user": {
                "id": result.user.id,
                "email": result.user.email,
            },
            "access_token": session.access_token if session else None,
            "refresh_token": session.refresh_token if session else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(payload: AuthRequest):
    """Sign in with email + password. Returns session tokens."""
    try:
        client = _get_auth_client()
        result = client.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password,
        })

        if not result.user or not result.session:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return {
            "access_token": result.session.access_token,
            "refresh_token": result.session.refresh_token,
            "expires_in": result.session.expires_in,
            "user": {
                "id": result.user.id,
                "email": result.user.email,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid email or password")


@router.post("/logout")
async def logout(request: Request):
    """Invalidate the current session."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return {"message": "Logged out (no active session)"}

    try:
        token = auth_header.split(" ", 1)[1]
        client = _get_auth_client()
        client.auth.sign_out(token)
    except Exception as e:
        logger.warning(f"Logout error (non-critical): {e}")

    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    """Get the currently authenticated user."""
    return {
        "id": user.id,
        "email": user.email,
        "created_at": str(user.created_at) if user.created_at else None,
    }


@router.delete("/me")
async def delete_me(user=Depends(get_current_user)):
    """Delete the currently authenticated user."""
    try:
        admin_client = get_supabase_client()
        admin_client.auth.admin.delete_user(user.id)
        return {"message": "Account deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete account: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete account")
@router.get("/check-username")
async def check_username(username: str):
    """Check if a username is already taken across all users."""
    try:
        admin_client = get_supabase_client()
        # Note: In a production app with thousands of users, querying the raw users table
        # like this is inefficient. A dedicated public 'profiles' table is recommended.
        # But for this scope, checking auth.users metadata works.
        response = admin_client.auth.admin.list_users()
        
        # list_users() returns a UserList object with a .users attribute
        if hasattr(response, 'users'):
            users = response.users
        else:
            users = response # Fallback if API changes
            
        username_lower = username.lower()
        
        for u in users:
            meta = u.user_metadata or {}
            existing_username = meta.get("username", "")
            if existing_username.lower() == username_lower:
                return {"available": False}
                
        return {"available": True}
    except Exception as e:
        logger.error(f"Failed to check username: {e}")
        # Default to unavailable on error to prevent duplicates accidentally
        return {"available": False}
