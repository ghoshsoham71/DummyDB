"""
Centralized Supabase client — singleton via @lru_cache.

Every module that needs Supabase should import `get_supabase_client` from here
instead of calling `create_client()` directly.
"""

import os
import logging
from functools import lru_cache

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Return a cached Supabase client using the service-role key."""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env"
        )
    logger.info("Creating Supabase client (service-role)")
    return create_client(url, key)
