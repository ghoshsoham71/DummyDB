"""
MongoDB Schema Extractor
Connects to a MongoDB instance and extracts collection schemas by sampling documents.
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Type mapping from Python/BSON types to a normalized type string
_BSON_TYPE_MAP = {
    "str": "VARCHAR",
    "int": "INTEGER",
    "float": "DOUBLE",
    "bool": "BOOLEAN",
    "list": "ARRAY",
    "dict": "JSON",
    "ObjectId": "OBJECT_ID",
    "datetime": "TIMESTAMP",
    "NoneType": "NULL",
    "bytes": "BINARY",
    "Decimal128": "DECIMAL",
    "Regex": "REGEX",
}


def _python_type_name(val: Any) -> str:
    """Get the normalized type string for a Python value."""
    t = type(val).__name__
    return _BSON_TYPE_MAP.get(t, t.upper())


class MongoDBExtractor:
    """Extract schema information from a running MongoDB instance."""

    def __init__(self, connection_string: str, database_name: Optional[str] = None):
        self.connection_string = connection_string
        self.database_name = database_name

    def extract_schema(self, sample_size: int = 100) -> Dict[str, Any]:
        """
        Connect to MongoDB, sample documents and infer schema.

        Returns a schema dict in the same normalised format used by
        the SQL parser: ``{databases: [{name, tables: [{name, attributes}]}]}``.
        """
        try:
            from pymongo import MongoClient  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError("pymongo is required: pip install pymongo")

        client: Any = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)

        try:
            # If a specific database was requested, use it; otherwise list all non-system dbs
            if self.database_name:
                db_names = [self.database_name]
            else:
                db_names = [
                    n for n in client.list_database_names()
                    if n not in ("admin", "local", "config")
                ]

            databases: List[Dict[str, Any]] = []

            for db_name in db_names:
                db = client[db_name]
                collections = db.list_collection_names()
                tables: List[Dict[str, Any]] = []

                for coll_name in collections:
                    if coll_name.startswith("system."):
                        continue

                    coll = db[coll_name]
                    docs = list(coll.find().limit(sample_size))

                    attributes = self._infer_fields(docs)

                    # Extract index info as constraints
                    indexes = coll.index_information()
                    for idx_name, idx_info in indexes.items():
                        keys = [k for k, _ in idx_info.get("key", [])]
                        is_unique = idx_info.get("unique", False)
                        for key in keys:
                            for attr in attributes:
                                if attr["name"] == key:
                                    if is_unique:
                                        attr["constraints"].append("UNIQUE")
                                    if idx_name == "_id_":
                                        if "PRIMARY_KEY" not in attr["constraints"]:
                                            attr["constraints"].append("PRIMARY_KEY")
                                    else:
                                        if "INDEXED" not in attr["constraints"]:
                                            attr["constraints"].append("INDEXED")

                    # Detect validation rules
                    try:
                        coll_info = db.command("collMod", coll_name, validator={})
                    except Exception:
                        coll_info = None

                    tables.append({
                        "name": coll_name,
                        "attributes": attributes,
                        "document_count": coll.estimated_document_count(),
                    })

                databases.append({"name": db_name, "tables": tables})

            return {"databases": databases, "source": "mongodb"}

        finally:
            client.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _infer_fields(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Infer field names, types and nullability from a sample of documents."""
        if not docs:
            return []

        field_types: Dict[str, Dict[str, int]] = {}  # field -> {type: count}
        field_count: Dict[str, int] = {}

        for doc in docs:
            self._collect_fields(doc, "", field_types, field_count)

        total_docs = len(docs)
        attributes: List[Dict[str, Any]] = []
        for field, types in sorted(field_types.items()):
            # Pick the most common type
            dominant_type = max(types, key=types.get)  # type: ignore[arg-type]
            constraints: List[str] = []
            if field == "_id":
                constraints.append("PRIMARY_KEY")
            # If the field doesn't appear in every doc, it's nullable
            if field_count.get(field, 0) < total_docs:
                constraints.append("NULLABLE")
            else:
                constraints.append("NOT_NULL")

            attributes.append({
                "name": field,
                "type": dominant_type,
                "constraints": constraints,
            })

        return attributes

    def _collect_fields(
        self,
        doc: Dict[str, Any],
        prefix: str,
        field_types: Dict[str, Dict[str, int]],
        field_count: Dict[str, int],
    ) -> None:
        """Recursively collect field names and types."""
        for key, val in doc.items():
            full_key = f"{prefix}.{key}" if prefix else key
            type_str = _python_type_name(val)

            if full_key not in field_types:
                field_types[full_key] = {}
            field_types[full_key][type_str] = field_types[full_key].get(type_str, 0) + 1
            field_count[full_key] = field_count.get(full_key, 0) + 1

            # Recurse into nested dicts (but not too deep)
            if isinstance(val, dict) and prefix.count(".") < 3:
                self._collect_fields(val, full_key, field_types, field_count)
