import hashlib
import json
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

from src.lib.supabase_client import get_supabase_client


def insert_schema(schema_data: Dict[str, Any], filename: str, content_hash: str, file_size: int) -> bool:
    """
    Insert schema into database with filename and content hash for duplicate prevention.
    """
    try:
        supabase = get_supabase_client()

        insert_data = {
            "filename": filename,
            "content_hash": content_hash,
            "file_size": file_size,
            "schema_data": schema_data,
            "created_at": "now()",
        }

        result = supabase.table("schema_parse").insert(insert_data).execute()

        if result.data:
            logger.info(f"Successfully inserted schema with hash {content_hash} into database")
            return True
        else:
            logger.error(f"Failed to insert schema into database: {result}")
            return False

    except Exception as e:
        logger.error(f"Error inserting schema into database: {str(e)}")
        return False


def check_schema_exists_by_hash(content_hash: str) -> bool:
    """Check if a schema with the given content hash already exists in the database."""
    try:
        supabase = get_supabase_client()

        result = supabase.table("schema_parse").select("id").eq("content_hash", content_hash).execute()

        if result.data and len(result.data) > 0:
            logger.info(f"Schema with content hash {content_hash} already exists in database")
            return True
        else:
            logger.debug(f"Schema with content hash {content_hash} does not exist in database")
            return False

    except Exception as e:
        logger.error(f"Error checking schema existence in database: {str(e)}")
        return False


def get_schema_by_hash(content_hash: str) -> Optional[Dict[str, Any]]:
    """Retrieve schema data by content hash."""
    try:
        supabase = get_supabase_client()

        result = supabase.table("schema_parse").select("*").eq("content_hash", content_hash).execute()

        if result.data and len(result.data) > 0:
            logger.info(f"Retrieved schema with content hash {content_hash} from database")
            return result.data[0]
        else:
            logger.debug(f"Schema with content hash {content_hash} not found in database")
            return None

    except Exception as e:
        logger.error(f"Error retrieving schema from database: {str(e)}")
        return None


def delete_schema_by_hash(content_hash: str) -> bool:
    """Delete schema by content hash."""
    try:
        supabase = get_supabase_client()

        result = supabase.table("schema_parse").delete().eq("content_hash", content_hash).execute()

        if result.data:
            logger.info(f"Successfully deleted schema with content hash {content_hash} from database")
            return True
        else:
            logger.warning(f"No schema found with content hash {content_hash} to delete")
            return False

    except Exception as e:
        logger.error(f"Error deleting schema from database: {str(e)}")
        return False


def get_all_schemas_from_db(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Retrieve all schemas from database with pagination."""
    try:
        supabase = get_supabase_client()

        result = supabase.table("schema_parse").select("*").range(offset, offset + limit - 1).execute()

        if result.data:
            logger.info(f"Retrieved {len(result.data)} schemas from database")
            return result.data
        else:
            logger.info("No schemas found in database")
            return []

    except Exception as e:
        logger.error(f"Error retrieving schemas from database: {str(e)}")
        return []


def update_schema_data(content_hash: str, new_schema_data: Dict[str, Any], filename: str = None, file_size: int = None) -> bool:
    """Update schema data for existing content hash."""
    try:
        supabase = get_supabase_client()

        update_data = {
            "schema_data": new_schema_data,
            "updated_at": "now()"
        }
        if filename is not None:
            update_data["filename"] = filename
        if file_size is not None:
            update_data["file_size"] = file_size

        result = supabase.table("schema_parse").update(update_data).eq("content_hash", content_hash).execute()

        if result.data:
            logger.info(f"Successfully updated schema with content hash {content_hash}")
            return True
        else:
            logger.error(f"Failed to update schema with content hash {content_hash}")
            return False

    except Exception as e:
        logger.error(f"Error updating schema in database: {str(e)}")
        return False