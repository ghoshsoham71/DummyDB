import re
from typing import List

def clean_sql_content(content: str) -> str:
    """Clean SQL content by removing comments"""
    # Remove single-line comments (-- style)
    content = re.sub(r'--.*$', '', content, flags=re.MULTILINE)
    # Remove multi-line comments (/* */ style)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # Remove hash comments (# style, used in MySQL)
    content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
    return content

def split_sql_statements(content: str) -> List[str]:
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
        
        # Handle string literals
        i = 0
        while i < len(line):
            char = line[i]
            if not in_string and char in ('"', "'", '`'):
                in_string = True
                string_char = char
            elif in_string and char == string_char:
                if i == 0 or line[i-1] != '\\':
                    in_string = False
                    string_char = None
            i += 1
        
        current_statement.append(line)
        if not in_string and line.rstrip().endswith(';'):
            statement_text = ' '.join(current_statement)
            if statement_text.strip():
                statements.append(statement_text)
            current_statement = []
            
    if current_statement:
        statement_text = ' '.join(current_statement)
        if statement_text.strip():
            statements.append(statement_text)
    return statements
