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
        """Coordinator for MongoDB schema extraction."""
        try:
            from pymongo import MongoClient
        except ImportError:
            raise ImportError("pymongo is required: pip install pymongo")
        client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
        try:
            db_names = self._get_db_names(client)
            dbs = []
            for name in db_names:
                db = client[name]
                tables = []
                for c_name in [c for c in db.list_collection_names() if not c.startswith("system.")]:
                    tables.append(self._extract_collection(db, c_name, sample_size))
                dbs.append({"name": name, "tables": tables})
            return {"databases": dbs, "source": "mongodb"}
        finally:
            client.close()

    def _get_db_names(self, client) -> List[str]:
        if self.database_name: return [self.database_name]
        return [n for n in client.list_database_names() if n not in ("admin", "local", "config")]

    def _extract_collection(self, db, c_name: str, sample_size: int) -> Dict[str, Any]:
        coll = db[c_name]
        docs = list(coll.find().limit(sample_size))
        attrs = self._infer_fields(docs)
        self._apply_indexes(coll.index_information(), attrs)
        return {"name": c_name, "attributes": attrs, "document_count": coll.estimated_document_count()}

    def _apply_indexes(self, index_info: dict, attrs: list):
        for idx_name, info in index_info.items():
            keys = [k for k, _ in info.get("key", [])]
            unique = info.get("unique", False)
            for k in keys:
                for a in attrs:
                    if a["name"] == k:
                        if unique: a["constraints"].append("UNIQUE")
                        if idx_name == "_id_":
                            if "PRIMARY_KEY" not in a["constraints"]: a["constraints"].append("PRIMARY_KEY")
                        elif "INDEXED" not in a["constraints"]: a["constraints"].append("INDEXED")

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
