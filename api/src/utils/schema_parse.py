import re
import json
import sys
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

class SQLSchemaParser:
    def __init__(self):
        self.databases = {}
        self.current_database = None
        self.parsed_schema = None
        
    def parse_sql_file(self, sql_file_path: str, output_dir: str) -> Dict[str, Any]:
        """
        Parse SQL file and generate JSON schema
        
        Args:
            sql_file_path: Path to SQL file
            output_dir: Directory to save JSON file (default: same as SQL file)
            
        Returns:
            Dict containing parsed schema
        """
        if not os.path.exists(sql_file_path):
            raise FileNotFoundError(f"SQL file not found: {sql_file_path}")
            
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_content = file.read()
            
        # Parse the SQL content
        schema = self._parse_sql_content(sql_content)
        
        # Determine output path
        if output_dir is None:
            output_dir = os.path.dirname(sql_file_path)
            
        sql_filename = Path(sql_file_path).stem
        json_file_path = os.path.join(output_dir, f"{sql_filename}_schema.json")
        
        # Save to JSON file
        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(schema, json_file, indent=2)
            
        print(f"Schema parsed and saved to: {json_file_path}")
        
        # Store parsed schema for access throughout codebase
        self.parsed_schema = schema
        
        return schema
    
    def _parse_sql_content(self, sql_content: str) -> Dict[str, Any]:
        """Parse SQL content and return structured schema"""
        self.databases = {}
        self.current_database = None
        
        # Clean and split SQL content
        sql_content = self._clean_sql_content(sql_content)
        statements = self._split_sql_statements(sql_content)
        
        for statement in statements:
            statement = statement.strip()
            if not statement:
                continue
                
            if statement.upper().startswith('USE '):
                self._parse_use_statement(statement)
            elif statement.upper().startswith('CREATE TABLE'):
                self._parse_create_table_statement(statement)
                
        return {"databases": list(self.databases.values())}
    
    def _clean_sql_content(self, content: str) -> str:
        """Clean SQL content by removing comments"""
        # Remove single-line comments
        content = re.sub(r'--.*$', '', content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        return content
    
    def _split_sql_statements(self, content: str) -> List[str]:
        """Split SQL content into individual statements"""
        statements = []
        current_statement = []
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            current_statement.append(line)
            
            if line.endswith(';'):
                statements.append(' '.join(current_statement))
                current_statement = []
                
        if current_statement:
            statements.append(' '.join(current_statement))
            
        return statements
    
    def _parse_use_statement(self, statement: str):
        """Parse USE statement to set current database"""
        match = re.search(r'USE\s+(\w+)', statement, re.IGNORECASE)
        if match:
            db_name = match.group(1)
            self.current_database = db_name
            if db_name not in self.databases:
                self.databases[db_name] = {
                    "name": db_name,
                    "tables": []
                }
    
    def _parse_create_table_statement(self, statement: str):
        """Parse CREATE TABLE statement"""
        # Extract table name
        table_match = re.search(r'CREATE TABLE\s+(\w+)\s*\(', statement, re.IGNORECASE)
        if not table_match:
            return
            
        table_name = table_match.group(1)
        
        # Use default database if none specified
        if self.current_database is None:
            self.current_database = "default"
            self.databases[self.current_database] = {
                "name": self.current_database,
                "tables": []
            }
        
        # Extract table definition content
        table_content = self._extract_table_content(statement)
        attributes = self._parse_table_attributes(table_content)
        
        table_schema = {
            "name": table_name,
            "attributes": attributes
        }
        
        self.databases[self.current_database]["tables"].append(table_schema)
    
    def _extract_table_content(self, statement: str) -> str:
        """Extract content between parentheses in CREATE TABLE statement"""
        # Find the opening parenthesis after CREATE TABLE
        start_idx = statement.find('(')
        if start_idx == -1:
            return ""
            
        # Find the matching closing parenthesis
        paren_count = 0
        end_idx = start_idx
        
        for i in range(start_idx, len(statement)):
            if statement[i] == '(':
                paren_count += 1
            elif statement[i] == ')':
                paren_count -= 1
                if paren_count == 0:
                    end_idx = i
                    break
                    
        return statement[start_idx + 1:end_idx]
    
    def _parse_table_attributes(self, table_content: str) -> List[Dict[str, Any]]:
        """Parse table attributes from table content"""
        attributes = []
        
        # Split by commas, but be careful with nested parentheses
        column_definitions = self._split_column_definitions(table_content)
        
        primary_keys = []
        foreign_keys = []
        
        for col_def in column_definitions:
            col_def = col_def.strip()
            if not col_def:
                continue
                
            # Check if it's a constraint definition
            if col_def.upper().startswith('PRIMARY KEY'):
                primary_keys.extend(self._extract_primary_key_columns(col_def))
                continue
            elif col_def.upper().startswith('FOREIGN KEY'):
                fk_info = self._extract_foreign_key_info(col_def)
                if fk_info:
                    foreign_keys.append(fk_info)
                continue
            elif col_def.upper().startswith(('INDEX', 'KEY', 'UNIQUE KEY')):
                continue
                
            # Parse column definition
            attribute = self._parse_column_definition(col_def)
            if attribute:
                attributes.append(attribute)
        
        # Apply primary key and foreign key constraints
        self._apply_constraints_to_attributes(attributes, primary_keys, foreign_keys)
        
        return attributes
    
    def _split_column_definitions(self, content: str) -> List[str]:
        """Split column definitions by commas, handling nested parentheses"""
        definitions = []
        current_def = []
        paren_count = 0
        
        i = 0
        while i < len(content):
            char = content[i]
            
            if char == '(':
                paren_count += 1
                current_def.append(char)
            elif char == ')':
                paren_count -= 1
                current_def.append(char)
            elif char == ',' and paren_count == 0:
                definitions.append(''.join(current_def).strip())
                current_def = []
            else:
                current_def.append(char)
            
            i += 1
        
        if current_def:
            definitions.append(''.join(current_def).strip())
            
        return definitions
    
    def _parse_column_definition(self, col_def: str) -> Optional[Dict[str, Any]]:
        """Parse individual column definition"""
        # Basic pattern: column_name data_type [constraints...]
        parts = col_def.split()
        if len(parts) < 2:
            return None
            
        column_name = parts[0]
        data_type = parts[1]
        
        # Handle data types with parameters like VARCHAR(100)
        if '(' in data_type:
            type_match = re.match(r'(\w+)\([^)]*\)', data_type)
            if type_match:
                data_type = type_match.group(1)
        
        attribute = {
            "name": column_name,
            "type": data_type.upper(),
            "constraints": []
        }
        
        return attribute
    
    def _extract_primary_key_columns(self, constraint_def: str) -> List[str]:
        """Extract column names from PRIMARY KEY constraint"""
        match = re.search(r'PRIMARY KEY\s*\(([^)]+)\)', constraint_def, re.IGNORECASE)
        if match:
            columns_str = match.group(1)
            columns = [col.strip() for col in columns_str.split(',')]
            return columns
        return []
    
    def _extract_foreign_key_info(self, constraint_def: str) -> Optional[Dict[str, str]]:
        """Extract foreign key information"""
        # Pattern: FOREIGN KEY (column) REFERENCES table(column)
        match = re.search(
            r'FOREIGN KEY\s*\(([^)]+)\)\s+REFERENCES\s+(\w+)\s*\(([^)]+)\)',
            constraint_def,
            re.IGNORECASE
        )
        
        if match:
            local_column = match.group(1).strip()
            referenced_table = match.group(2).strip()
            referenced_column = match.group(3).strip()
            
            return {
                "column": local_column,
                "referenced_table": referenced_table,
                "referenced_column": referenced_column
            }
        return None
    
    def _apply_constraints_to_attributes(self, attributes: List[Dict], primary_keys: List[str], foreign_keys: List[Dict]):
        """Apply primary key and foreign key constraints to attributes"""
        # Create a mapping for quick lookup
        attr_map = {attr["name"]: attr for attr in attributes}
        
        # Apply primary key constraints
        for pk_column in primary_keys:
            if pk_column in attr_map:
                attr_map[pk_column]["constraints"].append("PRIMARY_KEY")
        
        # Apply foreign key constraints
        for fk_info in foreign_keys:
            column_name = fk_info["column"]
            if column_name in attr_map:
                fk_constraint = f"FOREIGN_KEY_REFERENCES_{fk_info['referenced_table']}.{fk_info['referenced_column']}"
                attr_map[column_name]["constraints"].append(fk_constraint)
    
    def get_parsed_schema(self) -> Optional[Dict[str, Any]]:
        """Get the last parsed schema"""
        return self.parsed_schema

def main():
    """Main function for command-line usage"""
    if len(sys.argv) < 2:
        print("Usage: python schema_parse.py <sql_file_path> [output_directory]")
        sys.exit(1)
    
    sql_file_path = sys.argv[1]
    output_dir = sys.argv[2] 
    
    try:
        parser = SQLSchemaParser()
        schema = parser.parse_sql_file(sql_file_path, output_dir)
        
        print("Schema parsing completed successfully!")
        print(f"Found {len(schema['databases'])} database(s)")
        
        for db in schema['databases']:
            print(f"  Database: {db['name']} ({len(db['tables'])} tables)")
            
    except Exception as e:
        print(f"Error parsing SQL file: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()