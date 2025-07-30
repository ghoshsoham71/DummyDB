import re
import json
import sys
import os
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

class SQLSchemaParser:
    def __init__(self):
        self.databases = {}
        self.current_database = None
        self.parsed_schema = None
        
    def parse_sql_file(self, sql_file_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse SQL file and generate JSON schema
        
        Args:
            sql_file_path: Path to SQL file
            output_dir: Directory to save JSON file (default: same as SQL file)
            
        Returns:
            Dict containing parsed schema
        """
        # Convert to Path objects for better path handling
        sql_path = Path(sql_file_path)
        
        if not sql_path.exists():
            raise FileNotFoundError(f"SQL file not found: {sql_file_path}")
            
        try:
            with open(sql_path, 'r', encoding='utf-8') as file:
                sql_content = file.read()
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            with open(sql_path, 'r', encoding='latin-1') as file:
                sql_content = file.read()
            
        # Parse the SQL content
        schema = self._parse_sql_content(sql_content)
        
        # Determine output path
        if output_dir is None:
            output_path = sql_path.parent
        else:
            output_path = Path(output_dir)
            
        # Ensure output directory exists
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create JSON file path
        json_file_path = output_path / f"{sql_path.stem}_schema.json"
        
        # Save to JSON file
        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(schema, json_file, indent=2, ensure_ascii=False)
            
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
                
            # Handle different statement types
            statement_upper = statement.upper()
            if statement_upper.startswith('USE '):
                self._parse_use_statement(statement)
            elif statement_upper.startswith('CREATE TABLE'):
                self._parse_create_table_statement(statement)
            elif statement_upper.startswith('CREATE DATABASE') or statement_upper.startswith('CREATE SCHEMA'):
                self._parse_create_database_statement(statement)
                
        # If no databases were found, create a default one
        if not self.databases:
            self.databases["default"] = {
                "name": "default",
                "tables": []
            }
            
        return {"databases": list(self.databases.values())}
    
    def _clean_sql_content(self, content: str) -> str:
        """Clean SQL content by removing comments"""
        # Remove single-line comments (-- style)
        content = re.sub(r'--.*$', '', content, flags=re.MULTILINE)
        
        # Remove multi-line comments (/* */ style)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # Remove hash comments (# style, used in MySQL)
        content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
        
        return content
    
    def _split_sql_statements(self, content: str) -> List[str]:
        """Split SQL content into individual statements"""
        statements = []
        current_statement = []
        in_string = False
        string_char = None
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Handle string literals to avoid splitting on semicolons inside strings
            i = 0
            while i < len(line):
                char = line[i]
                if not in_string and char in ('"', "'", '`'):
                    in_string = True
                    string_char = char
                elif in_string and char == string_char:
                    # Check for escaped quotes
                    if i == 0 or line[i-1] != '\\':
                        in_string = False
                        string_char = None
                i += 1
            
            current_statement.append(line)
            
            # Only split on semicolon if we're not inside a string
            if not in_string and line.rstrip().endswith(';'):
                statement_text = ' '.join(current_statement)
                if statement_text.strip():
                    statements.append(statement_text)
                current_statement = []
                
        # Add any remaining statement
        if current_statement:
            statement_text = ' '.join(current_statement)
            if statement_text.strip():
                statements.append(statement_text)
            
        return statements
    
    def _parse_create_database_statement(self, statement: str):
        """Parse CREATE DATABASE or CREATE SCHEMA statement"""
        # Match CREATE DATABASE or CREATE SCHEMA
        match = re.search(r'CREATE\s+(DATABASE|SCHEMA)\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?', 
                         statement, re.IGNORECASE)
        if match:
            db_name = match.group(2)
            if db_name not in self.databases:
                self.databases[db_name] = {
                    "name": db_name,
                    "tables": []
                }
    
    def _parse_use_statement(self, statement: str):
        """Parse USE statement to set current database"""
        match = re.search(r'USE\s+`?(\w+)`?', statement, re.IGNORECASE)
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
        # Extract table name, handling backticks and database prefixes
        table_match = re.search(r'CREATE TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:`?(\w+)`?\.)?`?(\w+)`?\s*\(', 
                               statement, re.IGNORECASE)
        if not table_match:
            return
            
        database_name = table_match.group(1)
        table_name = table_match.group(2)
        
        # Use specified database or current/default database
        if database_name:
            target_db = database_name
        elif self.current_database:
            target_db = self.current_database
        else:
            target_db = "default"
        
        # Ensure database exists
        if target_db not in self.databases:
            self.databases[target_db] = {
                "name": target_db,
                "tables": []
            }
        
        # Extract table definition content
        table_content = self._extract_table_content(statement)
        if not table_content:
            return
            
        attributes = self._parse_table_attributes(table_content)
        
        table_schema = {
            "name": table_name,
            "attributes": attributes
        }
        
        self.databases[target_db]["tables"].append(table_schema)
    
    def _extract_table_content(self, statement: str) -> str:
        """Extract content between parentheses in CREATE TABLE statement"""
        # Find the opening parenthesis after CREATE TABLE
        start_idx = statement.find('(')
        if start_idx == -1:
            return ""
            
        # Find the matching closing parenthesis
        paren_count = 0
        end_idx = start_idx
        in_string = False
        string_char = None
        
        for i in range(start_idx, len(statement)):
            char = statement[i]
            
            # Handle string literals
            if not in_string and char in ('"', "'", '`'):
                in_string = True
                string_char = char
            elif in_string and char == string_char:
                # Check for escaped quotes
                if i == 0 or statement[i-1] != '\\':
                    in_string = False
                    string_char = None
            elif not in_string:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        end_idx = i
                        break
                        
        return statement[start_idx + 1:end_idx].strip()
    
    def _parse_table_attributes(self, table_content: str) -> List[Dict[str, Any]]:
        """Parse table attributes from table content"""
        attributes = []
        
        # Split by commas, but be careful with nested parentheses and strings
        column_definitions = self._split_column_definitions(table_content)
        
        primary_keys = []
        foreign_keys = []
        
        for col_def in column_definitions:
            col_def = col_def.strip()
            if not col_def:
                continue
                
            col_def_upper = col_def.upper()
            
            # Check if it's a constraint definition
            if col_def_upper.startswith('PRIMARY KEY'):
                primary_keys.extend(self._extract_primary_key_columns(col_def))
                continue
            elif col_def_upper.startswith('FOREIGN KEY'):
                fk_info = self._extract_foreign_key_info(col_def)
                if fk_info:
                    foreign_keys.append(fk_info)
                continue
            elif col_def_upper.startswith(('INDEX', 'KEY', 'UNIQUE KEY', 'UNIQUE INDEX', 'CONSTRAINT')):
                continue
                
            # Parse column definition
            attribute = self._parse_column_definition(col_def)
            if attribute:
                attributes.append(attribute)
        
        # Apply primary key and foreign key constraints
        self._apply_constraints_to_attributes(attributes, primary_keys, foreign_keys)
        
        return attributes
    
    def _split_column_definitions(self, content: str) -> List[str]:
        """Split column definitions by commas, handling nested parentheses and strings"""
        definitions = []
        current_def = []
        paren_count = 0
        in_string = False
        string_char = None
        
        i = 0
        while i < len(content):
            char = content[i]
            
            # Handle string literals
            if not in_string and char in ('"', "'", '`'):
                in_string = True
                string_char = char
                current_def.append(char)
            elif in_string and char == string_char:
                # Check for escaped quotes
                if i == 0 or content[i-1] != '\\':
                    in_string = False
                    string_char = None
                current_def.append(char)
            elif not in_string:
                if char == '(':
                    paren_count += 1
                    current_def.append(char)
                elif char == ')':
                    paren_count -= 1
                    current_def.append(char)
                elif char == ',' and paren_count == 0:
                    definition = ''.join(current_def).strip()
                    if definition:
                        definitions.append(definition)
                    current_def = []
                else:
                    current_def.append(char)
            else:
                current_def.append(char)
            
            i += 1
        
        # Add the last definition
        if current_def:
            definition = ''.join(current_def).strip()
            if definition:
                definitions.append(definition)
            
        return definitions
    
    def _parse_column_definition(self, col_def: str) -> Optional[Dict[str, Any]]:
        """Parse individual column definition"""
        # Remove backticks and extra whitespace
        col_def = re.sub(r'`([^`]+)`', r'\1', col_def)
        parts = col_def.split()
        
        if len(parts) < 2:
            return None
            
        column_name = parts[0]
        data_type_full = parts[1]
        
        # Handle data types with parameters like VARCHAR(100)
        data_type = data_type_full
        type_params = None
        if '(' in data_type_full:
            type_match = re.match(r'(\w+)\(([^)]*)\)', data_type_full)
            if type_match:
                data_type = type_match.group(1)
                type_params = type_match.group(2)
        
        attribute = {
            "name": column_name,
            "type": data_type.upper(),
            "constraints": []
        }
        
        # Add type parameters if present
        if type_params:
            attribute["type_params"] = type_params
        
        # Parse additional constraints from the column definition
        remaining_parts = ' '.join(parts[2:]).upper()
        
        if 'NOT NULL' in remaining_parts:
            attribute["constraints"].append("NOT_NULL")
        if 'AUTO_INCREMENT' in remaining_parts or 'AUTOINCREMENT' in remaining_parts:
            attribute["constraints"].append("AUTO_INCREMENT")
        if 'UNIQUE' in remaining_parts:
            attribute["constraints"].append("UNIQUE")
        if 'DEFAULT' in remaining_parts:
            # Extract default value
            default_match = re.search(r'DEFAULT\s+([^\s,]+)', remaining_parts)
            if default_match:
                attribute["default"] = default_match.group(1)
        
        return attribute
    
    def _extract_primary_key_columns(self, constraint_def: str) -> List[str]:
        """Extract column names from PRIMARY KEY constraint"""
        match = re.search(r'PRIMARY KEY\s*\(([^)]+)\)', constraint_def, re.IGNORECASE)
        if match:
            columns_str = match.group(1)
            # Remove backticks and split by comma
            columns = [re.sub(r'`([^`]+)`', r'\1', col.strip()) for col in columns_str.split(',')]
            return [col for col in columns if col]
        return []
    
    def _extract_foreign_key_info(self, constraint_def: str) -> Optional[Dict[str, str]]:
        """Extract foreign key information"""
        # Pattern: FOREIGN KEY (column) REFERENCES table(column)
        match = re.search(
            r'FOREIGN KEY\s*\(([^)]+)\)\s+REFERENCES\s+`?(\w+)`?\s*\(([^)]+)\)',
            constraint_def,
            re.IGNORECASE
        )
        
        if match:
            local_column = re.sub(r'`([^`]+)`', r'\1', match.group(1).strip())
            referenced_table = match.group(2).strip()
            referenced_column = re.sub(r'`([^`]+)`', r'\1', match.group(3).strip())
            
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
                if "PRIMARY_KEY" not in attr_map[pk_column]["constraints"]:
                    attr_map[pk_column]["constraints"].append("PRIMARY_KEY")
        
        # Apply foreign key constraints
        for fk_info in foreign_keys:
            column_name = fk_info["column"]
            if column_name in attr_map:
                fk_constraint = f"FOREIGN_KEY_REFERENCES_{fk_info['referenced_table']}.{fk_info['referenced_column']}"
                if fk_constraint not in attr_map[column_name]["constraints"]:
                    attr_map[column_name]["constraints"].append(fk_constraint)
    
    def get_parsed_schema(self) -> Optional[Dict[str, Any]]:
        """Get the last parsed schema"""
        return self.parsed_schema
    
    def print_schema_summary(self):
        """Print a summary of the parsed schema"""
        if not self.parsed_schema:
            print("No schema has been parsed yet.")
            return
        
        print("\n=== Schema Summary ===")
        databases = self.parsed_schema.get("databases", [])
        print(f"Found {len(databases)} database(s)")
        
        for db in databases:
            print(f"\nDatabase: {db['name']}")
            tables = db.get("tables", [])
            print(f"  Tables: {len(tables)}")
            
            for table in tables:
                print(f"    - {table['name']} ({len(table.get('attributes', []))} columns)")
                for attr in table.get("attributes", []):
                    constraints_str = ", ".join(attr.get("constraints", [])) if attr.get("constraints") else "None"
                    type_info = attr["type"]
                    if "type_params" in attr:
                        type_info += f"({attr['type_params']})"
                    print(f"      * {attr['name']}: {type_info} [{constraints_str}]")

def main():
    """Main function for command-line usage"""
    if len(sys.argv) < 2:
        print("Usage: python schema_parse.py <sql_file_path> [output_directory]")
        print("Example: python schema_parse.py database.sql ./output/")
        sys.exit(1)
    
    sql_file_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        parser = SQLSchemaParser()
        schema = parser.parse_sql_file(sql_file_path, output_dir)
        
        print("\nSchema parsing completed successfully!")
        parser.print_schema_summary()
        
    except FileNotFoundError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing SQL file: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()