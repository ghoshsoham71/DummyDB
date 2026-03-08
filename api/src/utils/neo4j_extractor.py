"""
Neo4j Schema Extractor
Connects to a Neo4j instance (default bolt://localhost:7687) and extracts
node labels, relationship types, and property schemas via Cypher introspection.
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class Neo4jExtractor:
    """Extract graph schema from a running Neo4j instance."""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "",
        database: Optional[str] = None,
    ):
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database  # None → default db

    def extract_schema(self) -> Dict[str, Any]:
        """
        Query Neo4j for labels, relationships, and property types.

        Returns a schema dict in the normalised format:
        ``{databases: [{name, tables: [...]}]}``

        Nodes become "tables", properties become "attributes",
        and relationships are stored as constraints on the source node.
        """
        try:
            from neo4j import GraphDatabase  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError("neo4j driver is required: pip install neo4j")

        auth = (self.username, self.password) if self.password else None
        driver = GraphDatabase.driver(self.uri, auth=auth)

        try:
            with driver.session(database=self.database) as session:
                node_tables = self._extract_nodes(session)
                rel_tables = self._extract_relationships(session)
                stats = self._get_db_stats(session)

            db_name = self.database or "neo4j"
            tables = node_tables + rel_tables

            return {
                "databases": [{
                    "name": db_name,
                    "tables": tables,
                    "statistics": stats,
                }],
                "source": "neo4j",
                "connection": {
                    "uri": self.uri,
                    "http_browser": self.uri.replace("bolt://", "http://").replace("7687", "7474"),
                },
            }

        finally:
            driver.close()

    # ------------------------------------------------------------------
    # Node extraction
    # ------------------------------------------------------------------

    def _extract_nodes(self, session: Any) -> List[Dict[str, Any]]:
        """Get all node labels with their properties and types."""
        tables: List[Dict[str, Any]] = []

        # Get all labels
        result = session.run("CALL db.labels()")
        labels = [record["label"] for record in result]

        for label in labels:
            # Sample properties from nodes with this label
            prop_result = session.run(
                f"MATCH (n:`{label}`) "
                f"WITH n LIMIT 200 "
                f"UNWIND keys(n) AS key "
                f"RETURN DISTINCT key, "
                f"  head(collect(DISTINCT apoc.meta.cypher.type(n[key]))) AS type, "
                f"  count(*) AS occurrences",
            )

            attributes: List[Dict[str, Any]] = []
            try:
                for record in prop_result:
                    neo_type = record.get("type", "STRING")
                    attr = {
                        "name": record["key"],
                        "type": self._map_neo4j_type(neo_type if neo_type else "STRING"),
                        "constraints": [],
                    }
                    attributes.append(attr)
            except Exception:
                # If APOC is not installed, fall back to simpler introspection
                attributes = self._extract_props_simple(session, label)

            # Get constraints for this label
            constraints = self._get_label_constraints(session, label)
            for attr in attributes:
                if attr["name"] in constraints:
                    attr["constraints"].extend(constraints[attr["name"]])

            # Count nodes
            count_result = session.run(f"MATCH (n:`{label}`) RETURN count(n) AS cnt")
            node_count = count_result.single()["cnt"]

            # Get outgoing relationships for this label
            rel_result = session.run(
                f"MATCH (n:`{label}`)-[r]->(m) "
                f"RETURN DISTINCT type(r) AS rel_type, head(labels(m)) AS target_label "
                f"LIMIT 100"
            )
            relationships: List[Dict[str, str]] = []
            for rec in rel_result:
                relationships.append({
                    "type": rec["rel_type"],
                    "target": rec.get("target_label", "Unknown"),
                })
                # Add relationship as a constraint
                for attr in attributes:
                    pass  # relationships stored separately

            tables.append({
                "name": f"Node:{label}",
                "attributes": attributes,
                "node_type": "node",
                "label": label,
                "node_count": node_count,
                "relationships": relationships,
            })

        return tables

    def _extract_props_simple(self, session: Any, label: str) -> List[Dict[str, Any]]:
        """Fallback property extraction without APOC."""
        result = session.run(
            f"MATCH (n:`{label}`) WITH n LIMIT 100 "
            f"UNWIND keys(n) AS key "
            f"RETURN DISTINCT key"
        )
        attributes: List[Dict[str, Any]] = []
        for record in result:
            attributes.append({
                "name": record["key"],
                "type": "VARCHAR",  # can't know without APOC
                "constraints": [],
            })
        return attributes

    # ------------------------------------------------------------------
    # Relationship extraction
    # ------------------------------------------------------------------

    def _extract_relationships(self, session: Any) -> List[Dict[str, Any]]:
        """Extract relationship types as 'tables'."""
        result = session.run("CALL db.relationshipTypes()")
        rel_types = [r["relationshipType"] for r in result]

        tables: List[Dict[str, Any]] = []
        for rtype in rel_types:
            # Get relationship properties
            prop_result = session.run(
                f"MATCH ()-[r:`{rtype}`]->() "
                f"WITH r LIMIT 100 "
                f"UNWIND keys(r) AS key "
                f"RETURN DISTINCT key"
            )
            attributes: List[Dict[str, Any]] = []
            for rec in prop_result:
                attributes.append({
                    "name": rec["key"],
                    "type": "VARCHAR",
                    "constraints": [],
                })

            # Get source → target label pairs
            pair_result = session.run(
                f"MATCH (a)-[r:`{rtype}`]->(b) "
                f"RETURN DISTINCT head(labels(a)) AS src, head(labels(b)) AS tgt "
                f"LIMIT 50"
            )
            pairs = [{"source": r["src"], "target": r["tgt"]} for r in pair_result]

            # Count relationships
            count_result = session.run(
                f"MATCH ()-[r:`{rtype}`]->() RETURN count(r) AS cnt"
            )
            rel_count = count_result.single()["cnt"]

            tables.append({
                "name": f"Rel:{rtype}",
                "attributes": attributes,
                "node_type": "relationship",
                "relationship_type": rtype,
                "relationship_count": rel_count,
                "pairs": pairs,
            })

        return tables

    # ------------------------------------------------------------------
    # Constraints & stats
    # ------------------------------------------------------------------

    def _get_label_constraints(self, session: Any, label: str) -> Dict[str, List[str]]:
        """Get property constraints for a label."""
        constraints: Dict[str, List[str]] = {}
        try:
            result = session.run("SHOW CONSTRAINTS")
            for rec in result:
                rec_dict = dict(rec)
                entity = rec_dict.get("labelsOrTypes", rec_dict.get("entityType", ""))
                props = rec_dict.get("properties", [])
                ctype = rec_dict.get("type", "")
                if isinstance(entity, list) and label in entity:
                    for p in (props if isinstance(props, list) else []):
                        if p not in constraints:
                            constraints[p] = []
                        if "UNIQUE" in ctype.upper():
                            constraints[p].append("UNIQUE")
                        if "NOT NULL" in ctype.upper() or "EXIST" in ctype.upper():
                            constraints[p].append("NOT_NULL")
        except Exception:
            pass  # older Neo4j version without SHOW CONSTRAINTS
        return constraints

    def _get_db_stats(self, session: Any) -> Dict[str, Any]:
        """Get basic database statistics."""
        stats: Dict[str, Any] = {}
        try:
            result = session.run(
                "MATCH (n) RETURN count(n) AS nodes "
                "UNION ALL "
                "MATCH ()-[r]->() RETURN count(r) AS nodes"
            )
            records = list(result)
            stats["total_nodes"] = records[0]["nodes"] if records else 0
            stats["total_relationships"] = records[1]["nodes"] if len(records) > 1 else 0
        except Exception:
            pass
        return stats

    # ------------------------------------------------------------------
    # Type mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _map_neo4j_type(neo_type: str) -> str:
        """Map Neo4j / APOC type names to normalised SQL-like types."""
        mapping: Dict[str, str] = {
            "STRING": "VARCHAR",
            "INTEGER": "INTEGER",
            "LONG": "BIGINT",
            "FLOAT": "DOUBLE",
            "DOUBLE": "DOUBLE",
            "BOOLEAN": "BOOLEAN",
            "DATE": "DATE",
            "LOCAL_DATE_TIME": "TIMESTAMP",
            "DATE_TIME": "TIMESTAMP",
            "ZONED_DATE_TIME": "TIMESTAMP",
            "DURATION": "INTERVAL",
            "POINT": "GEOMETRY",
            "LIST": "ARRAY",
            "MAP": "JSON",
            "NODE": "OBJECT_ID",
            "RELATIONSHIP": "OBJECT_ID",
            "NULL": "NULL",
        }
        return mapping.get(neo_type.upper(), neo_type.upper())
