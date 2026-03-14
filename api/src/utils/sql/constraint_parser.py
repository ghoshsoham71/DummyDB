import re
from typing import List, Dict, Optional

def extract_table_content(statement: str) -> str:
    """Extract content between parentheses in CREATE TABLE statement"""
    start_idx = statement.find('(')
    if start_idx == -1:
        return ""
        
    paren_count = 0
    end_idx = start_idx
    in_string = False
    string_char = None
    
    for i in range(start_idx, len(statement)):
        char = statement[i]
        if not in_string and char in ('"', "'", '`'):
            in_string = True
            string_char = char
        elif in_string and char == string_char:
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

def extract_primary_key_columns(constraint_def: str) -> List[str]:
    """Extract column names from PRIMARY KEY constraint"""
    match = re.search(r'PRIMARY KEY\s*\(([^)]+)\)', constraint_def, re.IGNORECASE)
    if match:
        columns_str = match.group(1)
        columns = [re.sub(r'`([^`]+)`', r'\1', col.strip()) for col in columns_str.split(',')]
        return [col for col in columns if col]
    return []

def extract_foreign_key_info(constraint_def: str) -> Optional[Dict[str, str]]:
    """Extract foreign key information"""
    match = re.search(
        r'FOREIGN KEY\s*\(([^)]+)\)\s+REFERENCES\s+`?(\w+)`?\s*\(([^)]+)\)',
        constraint_def, re.IGNORECASE
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

def apply_constraints_to_attributes(attributes: List[Dict], primary_keys: List[str], foreign_keys: List[Dict]):
    """Apply primary key and foreign key constraints to attributes"""
    attr_map = {attr["name"]: attr for attr in attributes}
    for pk_column in primary_keys:
        if pk_column in attr_map:
            if "PRIMARY_KEY" not in attr_map[pk_column]["constraints"]:
                attr_map[pk_column]["constraints"].append("PRIMARY_KEY")
    for fk_info in foreign_keys:
        column_name = fk_info["column"]
        if column_name in attr_map:
            fk_constraint = f"FOREIGN_KEY_REFERENCES_{fk_info['referenced_table']}.{fk_info['referenced_column']}"
            if fk_constraint not in attr_map[column_name]["constraints"]:
                attr_map[column_name]["constraints"].append(fk_constraint)
