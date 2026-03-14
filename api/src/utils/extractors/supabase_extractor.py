import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SupabaseExtractor:
    """
    Extracts schema, constraints, and RLS policies from a live Supabase PostgreSQL database.
    """
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        
    def extract_schema(self) -> Dict[str, Any]:
        """Coordinator for schema extraction."""
        try:
            conn = psycopg2.connect(self.connection_string)
            conn.autocommit = True
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            meta = self._fetch_metadata(cursor)
            conn.close()
            
            db_schema = {"name": "public", "tables": []}
            for table in meta["tables"]:
                t_name = table["table_name"]
                t_schema = {
                    "name": t_name,
                    "attributes": self._format_attrs(t_name, meta),
                    "rls_policies": self._format_pols(t_name, meta["policies"])
                }
                db_schema["tables"].append(t_schema)
            return {"databases": [db_schema]}
        except Exception as e:
            logger.error(f"Supabase failed: {e}")
            raise Exception(f"Failed: {str(e)}")

    def _fetch_metadata(self, cursor) -> Dict[str, Any]:
        """Fetch all necessary metadata from information_schema."""
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
        tables = cursor.fetchall()
        cursor.execute("SELECT table_name,column_name,data_type,character_maximum_length,column_default,is_nullable FROM information_schema.columns WHERE table_schema='public'")
        cols = cursor.fetchall()
        cursor.execute("SELECT kcu.table_name,kcu.column_name FROM information_schema.table_constraints tco JOIN information_schema.key_column_usage kcu ON kcu.constraint_name=tco.constraint_name WHERE tco.constraint_type='PRIMARY KEY' AND tco.table_schema='public'")
        pks = cursor.fetchall()
        cursor.execute("SELECT tc.table_name,kcu.column_name,ccu.table_name AS ft,ccu.column_name AS fc FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name=tc.constraint_name WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_schema='public'")
        fks = cursor.fetchall()
        cursor.execute("SELECT kcu.table_name,kcu.column_name FROM information_schema.table_constraints tco JOIN information_schema.key_column_usage kcu ON kcu.constraint_name=tco.constraint_name WHERE tco.constraint_type='UNIQUE' AND tco.table_schema='public'")
        uks = cursor.fetchall()
        cursor.execute("SELECT schemaname,tablename,policyname,permissive,roles,cmd,qual,with_check FROM pg_policies WHERE schemaname='public'")
        pols = cursor.fetchall()
        return {"tables": tables, "columns": cols, "pks": pks, "fks": fks, "uks": uks, "policies": pols}

    def _format_attrs(self, t_name: str, meta: dict) -> list:
        """Format attributes with constraints."""
        attrs = []
        for col in [c for c in meta["columns"] if c["table_name"] == t_name]:
            attr = {"name": col["column_name"], "type": col["data_type"].upper(), "constraints": []}
            if col["character_maximum_length"]: attr["type_params"] = str(col["character_maximum_length"])
            if col["is_nullable"] == "NO": attr["constraints"].append("NOT_NULL")
            if col["column_default"]:
                attr["default"] = col["column_default"]
                if "nextval" in str(col["column_default"]).lower(): attr["constraints"].append("AUTO_INCREMENT")
            if any(pk["table_name"]==t_name and pk["column_name"]==col["column_name"] for pk in meta["pks"]): attr["constraints"].append("PRIMARY_KEY")
            if any(uk["table_name"]==t_name and uk["column_name"]==col["column_name"] for uk in meta["uks"]): attr["constraints"].append("UNIQUE")
            for fk in meta["fks"]:
                if fk["table_name"] == t_name and fk["column_name"] == col["column_name"]:
                    attr["constraints"].append(f"FOREIGN_KEY_REFERENCES_{fk['ft']}.{fk['fc']}")
            attrs.append(attr)
        return attrs

    def _format_pols(self, t_name: str, pols: list) -> list:
        """Format policies."""
        return [{"name": p["policyname"], "permissive": p["permissive"], "roles": p["roles"], "cmd": p["cmd"], "qual": p["qual"], "with_check": p["with_check"]} for p in pols if p["tablename"] == t_name]
