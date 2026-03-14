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
        finally:
            driver.close()

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

    # ------------------------------------------------------------------
    # Node extraction
    # ------------------------------------------------------------------

    def _extract_nodes(self, session: Any) -> List[Dict[str, Any]]:
        """Get all node labels with their properties and types."""
        labels = [r["label"] for r in session.run("CALL db.labels()")]
        return [self._process_label(session, l) for l in labels]

    def _process_label(self, session: Any, label: str) -> Dict[str, Any]:
        attrs = self._get_node_attrs(session, label)
        cons = self._get_label_constraints(session, label)
        for a in attrs:
            if a["name"] in cons: a["constraints"].extend(cons[a["name"]])
        cnt = session.run(f"MATCH (n:`{label}`) RETURN count(n) AS c").single()["c"]
        rels = self._get_node_rels(session, label)
        return {
            "name": f"Node:{label}", "attributes": attrs, "node_type": "node",
            "label": label, "node_count": cnt, "relationships": rels
        }

    def _get_node_attrs(self, session: Any, label: str) -> List[Dict[str, Any]]:
        try:
            res = session.run(f"MATCH (n:`{label}`) WITH n LIMIT 200 UNWIND keys(n) AS k RETURN DISTINCT k, head(collect(DISTINCT apoc.meta.cypher.type(n[k]))) AS t")
            return [{"name": r["k"], "type": self._map_neo4j_type(r["t"] or "STRING"), "constraints": []} for r in res]
        except Exception:
            return self._extract_props_simple(session, label)

    def _get_node_rels(self, session: Any, label: str) -> List[Dict[str, str]]:
        res = session.run(f"MATCH (n:`{label}`)-[r]->(m) RETURN DISTINCT type(r) AS t, head(labels(m)) AS target LIMIT 100")
        return [{"type": r["t"], "target": r["target"] or "Unknown"} for r in res]

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
                        entry: List[str] = constraints.setdefault(p, [])
                        if "UNIQUE" in ctype.upper():
                            entry.append("UNIQUE")
                        if "NOT NULL" in ctype.upper() or "EXIST" in ctype.upper():
                            entry.append("NOT_NULL")
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
