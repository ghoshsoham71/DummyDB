"""
Auth dependency — verifies Supabase JWT tokens on protected routes.
"""

import os
import logging
from functools import lru_cache

from fastapi import HTTPException, Request
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_anon_client() -> Client:
    """Supabase client using the anon key (for verifying user JWTs)."""
    url = os.getenv("SUPABASE_URL", "")
    anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    if not url or not anon_key:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
    return create_client(url, anon_key)


def get_current_user(request: Request):
    """
    FastAPI dependency — extracts and verifies the Bearer token.
    Returns the Supabase User object or raises 401.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.split(" ", 1)[1]

    try:
        client = _get_anon_client()
        user_response = client.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_response.user
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Auth verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
