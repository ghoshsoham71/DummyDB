import re
from typing import List, Dict, Any, Optional

def split_column_definitions(content: str) -> List[str]:
    """Split column definitions by commas, handling nested parentheses and strings"""
    definitions = []
    current_def = []
    paren_count = 0
    in_string = False
    string_char = None
    
    i = 0
    while i < len(content):
        char = content[i]
        if not in_string and char in ('"', "'", '`'):
            in_string = True
            string_char = char
            current_def.append(char)
        elif in_string and char == string_char:
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
    
    if current_def:
        definition = ''.join(current_def).strip()
        if definition:
            definitions.append(definition)
    return definitions

def parse_column_definition(col_def: str) -> Optional[Dict[str, Any]]:
    """Parse individual column definition"""
    col_def = re.sub(r'`([^`]+)`', r'\1', col_def)
    parts = col_def.split()
    if len(parts) < 2:
        return None
        
    column_name = parts[0]
    data_type_full = parts[1]
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
    if type_params:
        attribute["type_params"] = type_params
        
    remaining_parts = ' '.join(parts[2:]).upper()
    if 'NOT NULL' in remaining_parts:
        attribute["constraints"].append("NOT_NULL")
    if 'AUTO_INCREMENT' in remaining_parts or 'AUTOINCREMENT' in remaining_parts:
        attribute["constraints"].append("AUTO_INCREMENT")
    if 'UNIQUE' in remaining_parts:
        attribute["constraints"].append("UNIQUE")
    if 'DEFAULT' in remaining_parts:
        default_match = re.search(r'DEFAULT\s+([^\s,]+)', remaining_parts)
        if default_match:
            attribute["default"] = default_match.group(1)
    return attribute
