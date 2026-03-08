import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)

class SupabaseExtractor:
    """
    Extracts schema, constraints, and RLS policies from a live Supabase PostgreSQL database.
    """
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        
    def extract_schema(self) -> Dict[str, Any]:
        """
        Connects to the Supabase database and extracts table schemas, constraints,
        and RLS policies, formatting them identically to SQLSchemaParser output.
        """
        try:
            conn = psycopg2.connect(self.connection_string)
            conn.autocommit = True
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # 1. Fetch tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
            """)
            tables = cursor.fetchall()
            
            # 2. Fetch columns and data types
            cursor.execute("""
                SELECT table_name, column_name, data_type, character_maximum_length, column_default, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public';
            """)
            columns = cursor.fetchall()
            
            # 3. Fetch primary keys
            cursor.execute("""
                SELECT kcu.table_name, kcu.column_name
                FROM information_schema.table_constraints tco
                JOIN information_schema.key_column_usage kcu 
                  ON kcu.constraint_name = tco.constraint_name
                  AND kcu.constraint_schema = tco.constraint_schema
                WHERE tco.constraint_type = 'PRIMARY KEY' AND tco.table_schema = 'public';
            """)
            primary_keys = cursor.fetchall()
            
            # 4. Fetch foreign keys
            cursor.execute("""
                SELECT
                    tc.table_name, 
                    kcu.column_name, 
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name 
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema='public';
            """)
            foreign_keys = cursor.fetchall()
            
            # 5. Fetch unique constraints
            cursor.execute("""
                SELECT kcu.table_name, kcu.column_name
                FROM information_schema.table_constraints tco
                JOIN information_schema.key_column_usage kcu 
                  ON kcu.constraint_name = tco.constraint_name
                  AND kcu.constraint_schema = tco.constraint_schema
                WHERE tco.constraint_type = 'UNIQUE' AND tco.table_schema = 'public';
            """)
            unique_keys = cursor.fetchall()
            
            # 6. Fetch RLS Policies
            cursor.execute("""
                SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
                FROM pg_policies
                WHERE schemaname = 'public';
            """)
            policies = cursor.fetchall()
            
            conn.close()
            
            # Build schema dictionary
            database_schema: Dict[str, Any] = {
                "name": "public",
                "tables": []
            }
            
            for table in tables:
                t_name = table["table_name"]
                t_schema: Dict[str, Any] = {
                    "name": t_name,
                    "attributes": [],
                    "rls_policies": []
                }
                
                # Add columns
                table_cols = [c for c in columns if c["table_name"] == t_name]
                for col in table_cols:
                    c_name = col["column_name"]
                    c_type = col["data_type"].upper()
                    
                    attr = {
                        "name": c_name,
                        "type": c_type,
                        "constraints": []
                    }
                    if col["character_maximum_length"]:
                        attr["type_params"] = str(col["character_maximum_length"])
                    
                    if col["is_nullable"] == "NO":
                        attr["constraints"].append("NOT_NULL")
                    
                    if col["column_default"]:
                        attr["default"] = col["column_default"]
                        if "nextval" in str(col["column_default"]).lower():
                            attr["constraints"].append("AUTO_INCREMENT")
                    
                    # Primary key constraint
                    if any(pk["table_name"] == t_name and pk["column_name"] == c_name for pk in primary_keys):
                        attr["constraints"].append("PRIMARY_KEY")
                        
                    # Unique constraint
                    if any(uk["table_name"] == t_name and uk["column_name"] == c_name for uk in unique_keys):
                        attr["constraints"].append("UNIQUE")
                        
                    # Foreign key constraint
                    for fk in foreign_keys:
                        if fk["table_name"] == t_name and fk["column_name"] == c_name:
                            attr["constraints"].append(f"FOREIGN_KEY_REFERENCES_{fk['foreign_table_name']}.{fk['foreign_column_name']}")
                            
                    t_schema["attributes"].append(attr)
                    
                # Add RLS policies
                table_policies = [p for p in policies if p["tablename"] == t_name]
                for p in table_policies:
                    t_schema["rls_policies"].append({
                        "name": p["policyname"],
                        "permissive": p["permissive"],
                        "roles": p["roles"],
                        "cmd": p["cmd"],
                        "qual": p["qual"],
                        "with_check": p["with_check"]
                    })
                    
                database_schema["tables"].append(t_schema)
                
            return {
                "databases": [database_schema]
            }
            
        except Exception as e:
            logger.error(f"Error extracting Supabase schema: {e}")
            raise Exception(f"Failed to extract schema from Supabase: {str(e)}")
