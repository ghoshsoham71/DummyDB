import re
import json
import sys
from typing import Dict, List, Optional, Any
from pathlib import Path

from src.utils.sql.cleaner import clean_sql_content, split_sql_statements
from src.utils.sql.column_parser import split_column_definitions, parse_column_definition
from src.utils.sql.constraint_parser import (
    extract_table_content, 
    extract_primary_key_columns, 
    extract_foreign_key_info, 
    apply_constraints_to_attributes
)

class SQLSchemaParser:
    def __init__(self):
        self.databases = {}
        self.current_database = None
        self.parsed_schema = None
        
    def parse_sql_file(self, sql_file_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        sql_path = Path(sql_file_path)
        if not sql_path.exists():
            raise FileNotFoundError(f"SQL file not found: {sql_file_path}")
            
        try:
            with open(sql_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
        except UnicodeDecodeError:
            with open(sql_path, 'r', encoding='latin-1') as f:
                sql_content = f.read()
            
        schema = self._parse_sql_content(sql_content)
        output_path = Path(output_dir) if output_dir else sql_path.parent
        output_path.mkdir(parents=True, exist_ok=True)
        
        json_file_path = output_path / f"{sql_path.stem}_schema.json"
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
            
        self.parsed_schema = schema
        return schema
    
    def _parse_sql_content(self, sql_content: str) -> Dict[str, Any]:
        self.databases = {}
        self.current_database = None
        
        sql_content = clean_sql_content(sql_content)
        statements = split_sql_statements(sql_content)
        
        for statement in statements:
            stmt = statement.strip()
            if not stmt: continue
            stmt_upper = stmt.upper()
            
            if stmt_upper.startswith('USE '):
                self._parse_use_statement(stmt)
            elif stmt_upper.startswith('CREATE TABLE'):
                self._parse_create_table_statement(stmt)
            elif stmt_upper.startswith(('CREATE DATABASE', 'CREATE SCHEMA')):
                self._parse_create_database_statement(stmt)
                
        if not self.databases:
            self.databases["default"] = {"name": "default", "tables": []}
            
        return {"databases": list(self.databases.values())}
    
    def _parse_create_database_statement(self, statement: str):
        match = re.search(r'CREATE\s+(DATABASE|SCHEMA)\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?', statement, re.IGNORECASE)
        if match:
            db_name = match.group(2)
            if db_name not in self.databases:
                self.databases[db_name] = {"name": db_name, "tables": []}
    
    def _parse_use_statement(self, statement: str):
        match = re.search(r'USE\s+`?(\w+)`?', statement, re.IGNORECASE)
        if match:
            db_name = match.group(1)
            self.current_database = db_name
            if db_name not in self.databases:
                self.databases[db_name] = {"name": db_name, "tables": []}
    
    def _parse_create_table_statement(self, statement: str):
        table_match = re.search(r'CREATE TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:`?(\w+)`?\.)?`?(\w+)`?\s*\(', statement, re.IGNORECASE)
        if not table_match: return
            
        database_name, table_name = table_match.groups()
        target_db = database_name or self.current_database or "default"
        
        if target_db not in self.databases:
            self.databases[target_db] = {"name": target_db, "tables": []}
        
        table_content = extract_table_content(statement)
        if not table_content: return
            
        attributes = self._parse_table_attributes(table_content)
        self.databases[target_db]["tables"].append({"name": table_name, "attributes": attributes})
    
    def _parse_table_attributes(self, table_content: str) -> List[Dict[str, Any]]:
        attributes = []
        column_definitions = split_column_definitions(table_content)
        primary_keys, foreign_keys = [], []
        
        for col_def in column_definitions:
            col_def = col_def.strip()
            if not col_def: continue
            upper = col_def.upper()
            
            if upper.startswith('PRIMARY KEY'):
                primary_keys.extend(extract_primary_key_columns(col_def))
            elif upper.startswith('FOREIGN KEY'):
                fk_info = extract_foreign_key_info(col_def)
                if fk_info: foreign_keys.append(fk_info)
            elif not upper.startswith(('INDEX', 'KEY', 'UNIQUE KEY', 'UNIQUE INDEX', 'CONSTRAINT')):
                attribute = parse_column_definition(col_def)
                if attribute: attributes.append(attribute)
        
        apply_constraints_to_attributes(attributes, primary_keys, foreign_keys)
        return attributes
    
    def get_parsed_schema(self) -> Optional[Dict[str, Any]]:
        return self.parsed_schema
    
    def print_schema_summary(self):
        if not self.parsed_schema:
            print("No schema has been parsed yet."); return
        
        print("\n=== Schema Summary ===")
        for db in self.parsed_schema.get("databases", []):
            print(f"\nDatabase: {db['name']}")
            for table in db.get("tables", []):
                print(f"    - {table['name']} ({len(table.get('attributes', []))} columns)")

def main():
    if len(sys.argv) < 2:
        print("Usage: python schema_parse.py <sql_file_path> [output_directory]"); sys.exit(1)
    
    try:
        parser = SQLSchemaParser()
        parser.parse_sql_file(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
        print("\nSchema parsing completed successfully!")
        parser.print_schema_summary()
    except Exception as e:
        print(f"Error: {e}"); sys.exit(1)

if __name__ == "__main__":
    main()