import re
import sqlparse
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from src.lib.schemas import (
    SchemaCollection, DatabaseSchema, TableSchema, ColumnAttribute,
    ColumnConstraint, ConstraintType, DataType
)

class SQLSchemaParser:
    def __init__(self):
        self.data_type_patterns = {
            r'(VAR)?CHAR\((\d+)\)': ('VARCHAR', 'length'),
            r'(DECIMAL|NUMERIC)\((\d+),(\d+)\)': ('DECIMAL', 'precision_scale'),
            r'(DECIMAL|NUMERIC)\((\d+)\)': ('DECIMAL', 'precision'),
            r'(FLOAT|REAL)\((\d+),(\d+)\)': ('FLOAT', 'precision_scale'),
            r'(FLOAT|REAL)\((\d+)\)': ('FLOAT', 'precision'),
            r'ENUM\((.*?)\)': ('ENUM', 'enum_values'),
        }
        
    async def parse_sql_content(self, sql_content: str, database_name: Optional[str] = None) -> SchemaCollection:
        """Parse SQL DDL content and return structured schema"""
        databases = {}
        current_db = database_name or "default"
        
        # Split SQL content into statements
        statements = sqlparse.split(sql_content)
        
        for stmt in statements:
            if not stmt.strip():
                continue
                
            parsed = sqlparse.parse(stmt)[0]
            
            # Extract database name if USE statement
            db_match = re.search(r'USE\s+(\w+)', stmt, re.IGNORECASE)
            if db_match:
                current_db = db_match.group(1)
                continue
                
            # Check if it's a CREATE TABLE statement
            if self._is_create_table(parsed):
                table_schema = await self._parse_create_table(stmt)
                if table_schema:
                    if current_db not in databases:
                        databases[current_db] = DatabaseSchema(
                            name=current_db,
                            tables={}
                        )
                    databases[current_db].tables[table_schema.name] = table_schema
        
        # Calculate statistics
        total_tables = sum(len(db.tables) for db in databases.values())
        
        return SchemaCollection(
            databases=databases,
            generated_at=datetime.now().isoformat(),
            total_databases=len(databases),
            total_tables=total_tables
        )
    
    def _is_create_table(self, parsed_stmt) -> bool:
        """Check if the statement is a CREATE TABLE"""
        tokens = [t for t in parsed_stmt.flatten() if not t.is_whitespace]
        return (len(tokens) >= 3 and 
                tokens[0].ttype is sqlparse.tokens.Keyword and
                tokens[0].value.upper() == 'CREATE' and
                tokens[1].ttype is sqlparse.tokens.Keyword and
                tokens[1].value.upper() == 'TABLE')
    
    async def _parse_create_table(self, stmt: str) -> Optional[TableSchema]:
        """Parse CREATE TABLE statement"""
        # Extract table name
        table_match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)', stmt, re.IGNORECASE)
        if not table_match:
            return None
            
        table_name = table_match.group(1)
        
        # Extract column definitions
        columns_match = re.search(r'\((.*)\)', stmt, re.DOTALL)
        if not columns_match:
            return None
            
        columns_def = columns_match.group(1)
        columns = {}
        primary_keys = []
        foreign_keys = {}
        unique_constraints = []
        check_constraints = []
        
        # Split by commas (considering nested parentheses)
        column_parts = self._split_column_definitions(columns_def)
        
        for part in column_parts:
            part = part.strip()
            if not part:
                continue
                
            # Check for table-level constraints
            if part.upper().startswith('PRIMARY KEY'):
                pk_match = re.search(r'PRIMARY\s+KEY\s*\((.*?)\)', part, re.IGNORECASE)
                if pk_match:
                    primary_keys.extend([col.strip() for col in pk_match.group(1).split(',')])
                continue
                
            if part.upper().startswith('FOREIGN KEY'):
                fk_match = re.search(r'FOREIGN\s+KEY\s*\((.*?)\)\s*REFERENCES\s+(\w+)\s*\((.*?)\)', part, re.IGNORECASE)
                if fk_match:
                    local_col = fk_match.group(1).strip()
                    ref_table = fk_match.group(2).strip()
                    ref_col = fk_match.group(3).strip()
                    foreign_keys[local_col] = {"table": ref_table, "column": ref_col}
                continue
                
            if part.upper().startswith('UNIQUE'):
                unique_match = re.search(r'UNIQUE\s*\((.*?)\)', part, re.IGNORECASE)
                if unique_match:
                    unique_constraints.append([col.strip() for col in unique_match.group(1).split(',')])
                continue
                
            if part.upper().startswith('CHECK'):
                check_constraints.append(part)
                continue
                
            # Parse column definition
            column = await self._parse_column_definition(part)
            if column:
                columns[column.name] = column
                
        return TableSchema(
            name=table_name,
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            unique_constraints=unique_constraints,
            check_constraints=check_constraints
        )
    
    def _split_column_definitions(self, columns_def: str) -> List[str]:
        """Split column definitions considering nested parentheses"""
        parts = []
        current = ""
        paren_count = 0
        
        for char in columns_def:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == ',' and paren_count == 0:
                parts.append(current.strip())
                current = ""
                continue
            current += char
            
        if current.strip():
            parts.append(current.strip())
            
        return parts
    
    async def _parse_column_definition(self, col_def: str) -> Optional[ColumnAttribute]:
        """Parse individual column definition"""
        parts = col_def.split()
        if len(parts) < 2:
            return None
            
        col_name = parts[0]
        data_type_str = parts[1]
        
        # Parse data type
        data_type, length, precision, scale, enum_values = self._parse_data_type(data_type_str)
        
        # Parse constraints
        constraints = []
        nullable = True
        default_value = None
        auto_increment = False
        
        col_def_upper = col_def.upper()
        
        if 'NOT NULL' in col_def_upper:
            nullable = False
            constraints.append(ColumnConstraint(
                type=ConstraintType.NOT_NULL,
                definition="NOT NULL"
            ))
            
        if 'PRIMARY KEY' in col_def_upper:
            constraints.append(ColumnConstraint(
                type=ConstraintType.PRIMARY_KEY,
                definition="PRIMARY KEY"
            ))
            
        if 'UNIQUE' in col_def_upper:
            constraints.append(ColumnConstraint(
                type=ConstraintType.UNIQUE,
                definition="UNIQUE"
            ))
            
        if 'AUTO_INCREMENT' in col_def_upper or 'AUTOINCREMENT' in col_def_upper:
            auto_increment = True
            
        # Extract default value
        default_match = re.search(r'DEFAULT\s+(.*?)(?:\s|$)', col_def, re.IGNORECASE)
        if default_match:
            default_value = default_match.group(1).strip()
            constraints.append(ColumnConstraint(
                type=ConstraintType.DEFAULT,
                definition=f"DEFAULT {default_value}"
            ))
            
        # Extract foreign key reference
        fk_match = re.search(r'REFERENCES\s+(\w+)\s*\((\w+)\)', col_def, re.IGNORECASE)
        if fk_match:
            constraints.append(ColumnConstraint(
                type=ConstraintType.FOREIGN_KEY,
                definition=f"REFERENCES {fk_match.group(1)}({fk_match.group(2)})",
                referenced_table=fk_match.group(1),
                referenced_column=fk_match.group(2)
            ))
            
        return ColumnAttribute(
            name=col_name,
            data_type=data_type,
            length=length,
            precision=precision,
            scale=scale,
            nullable=nullable,
            default_value=default_value,
            auto_increment=auto_increment,
            constraints=constraints,
            enum_values=enum_values
        )
    
    def _parse_data_type(self, data_type_str: str) -> Tuple[str, Optional[int], Optional[int], Optional[int], Optional[List[str]]]:
        """Parse data type string and extract type, length, precision, scale, enum values"""
        data_type_upper = data_type_str.upper()
        
        # Check patterns
        for pattern, (dtype, param_type) in self.data_type_patterns.items():
            match = re.match(pattern, data_type_upper)
            if match:
                if param_type == 'length':
                    return dtype, int(match.group(2)), None, None, None
                elif param_type == 'precision':
                    return dtype, None, int(match.group(2)), None, None
                elif param_type == 'precision_scale':
                    return dtype, None, int(match.group(2)), int(match.group(3)), None
                elif param_type == 'enum_values':
                    enum_vals = [val.strip().strip("'\"") for val in match.group(1).split(',')]
                    return dtype, None, None, None, enum_vals
                    
        # Default mapping
        type_mapping = {
            'INT': 'INTEGER',
            'TINYINT': 'INTEGER',
            'SMALLINT': 'SMALLINT',
            'MEDIUMINT': 'INTEGER',
            'BIGINT': 'BIGINT',
            'FLOAT': 'FLOAT',
            'DOUBLE': 'DOUBLE',
            'REAL': 'REAL',
            'DECIMAL': 'DECIMAL',
            'NUMERIC': 'NUMERIC',
            'VARCHAR': 'VARCHAR',
            'CHAR': 'CHAR',
            'TEXT': 'TEXT',
            'MEDIUMTEXT': 'TEXT',
            'LONGTEXT': 'TEXT',
            'DATE': 'DATE',
            'TIME': 'TIME',
            'DATETIME': 'TIMESTAMP',
            'TIMESTAMP': 'TIMESTAMP',
            'BOOLEAN': 'BOOLEAN',
            'BOOL': 'BOOLEAN',
            'BLOB': 'BLOB',
            'JSON': 'JSON',
            'UUID': 'UUID'
        }
        
        base_type = data_type_upper.split('(')[0]
        return type_mapping.get(base_type, base_type), None, None, None, None