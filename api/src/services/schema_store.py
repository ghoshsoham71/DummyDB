"""
Schema Store — in-memory schema storage, validation, and utility functions.

This is the single source of truth for parsed schemas. All routers import
PARSED_SCHEMAS and SchemaManager from here instead of maintaining their
own copies.
"""

import hashlib
import logging
import os
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ── Global state ──────────────────────────────────────────────────────────────

PARSED_SCHEMAS: Dict[str, Dict[str, Any]] = {}
SCHEMA_COUNTER = 0
MAX_SCHEMAS_IN_MEMORY = 100
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


# ── SchemaManager ─────────────────────────────────────────────────────────────

class SchemaManager:
    """Enhanced schema management with cleanup and validation."""

    @staticmethod
    def generate_schema_id(content: str) -> str:
        """Generate deterministic schema ID based on content hash."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"schema_{content_hash}"

    @staticmethod
    def generate_content_hash(content: str) -> str:
        """Generate MD5 hash of content for duplicate detection."""
        return hashlib.md5(content.encode()).hexdigest()

    @staticmethod
    def cleanup_old_schemas() -> None:
        """Remove oldest schemas if memory limit exceeded."""
        if len(PARSED_SCHEMAS) >= MAX_SCHEMAS_IN_MEMORY:
            sorted_schemas = sorted(
                PARSED_SCHEMAS.items(),
                key=lambda x: x[1]["created_at"],
            )
            remove_count = max(1, len(sorted_schemas) // 5)
            for i in range(remove_count):
                schema_id = sorted_schemas[i][0]
                removed = PARSED_SCHEMAS.pop(schema_id, None)
                if removed:
                    logger.info(f"Removed old schema: {schema_id}")

    @staticmethod
    def validate_schema_content(schema: Dict[str, Any]) -> bool:
        """Validate schema structure."""
        if not isinstance(schema, dict):
            return False
        databases = schema.get("databases", [])
        if not isinstance(databases, list):
            return False
        for db in databases:
            if not isinstance(db, dict) or "name" not in db:
                return False
            tables = db.get("tables", [])
            if not isinstance(tables, list):
                return False
            for table in tables:
                if not isinstance(table, dict) or "name" not in table:
                    return False
        return True


schema_manager = SchemaManager()


# ── Utility functions ─────────────────────────────────────────────────────────

def get_schema_by_id(schema_id: str) -> Optional[Dict[str, Any]]:
    """Get schema data by ID."""
    schema_data = PARSED_SCHEMAS.get(schema_id)
    if schema_data:
        logger.debug(f"Retrieved schema: {schema_id}")
    else:
        logger.warning(f"Schema not found: {schema_id}")
    return schema_data


def get_all_schemas() -> Dict[str, Dict[str, Any]]:
    """Get all schemas (shallow copy)."""
    return {k: v.copy() for k, v in PARSED_SCHEMAS.items()}


def get_latest_schema() -> Optional[Dict[str, Any]]:
    """Get the most recently parsed schema."""
    if not PARSED_SCHEMAS:
        return None
    latest_id = max(PARSED_SCHEMAS.keys(), key=lambda x: PARSED_SCHEMAS[x]["created_at"])
    return PARSED_SCHEMAS[latest_id]["schema"]


def search_schemas_by_table(table_name: str) -> Dict[str, Dict[str, Any]]:
    """Search for schemas containing a specific table name (case-insensitive)."""
    matching: Dict[str, Dict[str, Any]] = {}
    for schema_id, schema_data in PARSED_SCHEMAS.items():
        for db in schema_data["schema"].get("databases", []):
            for table in db.get("tables", []):
                if table.get("name", "").lower() == table_name.lower():
                    matching[schema_id] = schema_data
                    break
            if schema_id in matching:
                break
    logger.info(f"Found {len(matching)} schemas containing table '{table_name}'")
    return matching


def search_schemas_by_column(column_name: str) -> Dict[str, List[Dict[str, Any]]]:
    """Search for schemas containing a specific column name."""
    results: Dict[str, List[Dict[str, Any]]] = {}
    for schema_id, schema_data in PARSED_SCHEMAS.items():
        matches: List[Dict[str, Any]] = []
        for db in schema_data["schema"].get("databases", []):
            for table in db.get("tables", []):
                for attr in table.get("attributes", []):
                    if attr.get("name", "").lower() == column_name.lower():
                        matches.append({
                            "database": db["name"],
                            "table": table["name"],
                            "column": attr,
                        })
        if matches:
            results[schema_id] = matches
    logger.info(f"Found column '{column_name}' in {len(results)} schemas")
    return results


def get_schema_statistics() -> Dict[str, Any]:
    """Get comprehensive statistics for all stored schemas."""
    if not PARSED_SCHEMAS:
        return {
            "total_schemas": 0, "total_databases": 0,
            "total_tables": 0, "total_attributes": 0, "total_storage_bytes": 0,
        }

    total_databases = total_tables = total_attributes = total_storage = 0
    constraint_stats: Dict[str, int] = {}
    data_type_stats: Dict[str, int] = {}

    for schema_data in PARSED_SCHEMAS.values():
        schema = schema_data["schema"]
        databases = schema.get("databases", [])
        total_storage += schema_data.get("file_size", 0)
        total_databases += len(databases)

        for db in databases:
            tables = db.get("tables", [])
            total_tables += len(tables)
            for table in tables:
                attributes = table.get("attributes", [])
                total_attributes += len(attributes)
                for attr in attributes:
                    dt = attr.get("type", "UNKNOWN")
                    data_type_stats[dt] = data_type_stats.get(dt, 0) + 1
                    for c in attr.get("constraints", []):
                        constraint_stats[c] = constraint_stats.get(c, 0) + 1

    return {
        "total_schemas": len(PARSED_SCHEMAS),
        "total_databases": total_databases,
        "total_tables": total_tables,
        "total_attributes": total_attributes,
        "total_storage_bytes": total_storage,
        "constraint_distribution": constraint_stats,
        "data_type_distribution": data_type_stats,
        "memory_usage": {
            "current_schemas": len(PARSED_SCHEMAS),
            "max_schemas_limit": MAX_SCHEMAS_IN_MEMORY,
            "usage_percentage": (len(PARSED_SCHEMAS) / MAX_SCHEMAS_IN_MEMORY) * 100,
        },
    }
