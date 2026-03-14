import json
import logging
from typing import List, Any
from faker import Faker

logger = logging.getLogger(__name__)

TYPE_MAP = {
    'INT': 'integer', 'INTEGER': 'integer', 'BIGINT': 'integer', 'SMALLINT': 'integer', 'TINYINT': 'integer',
    'VARCHAR': 'string', 'TEXT': 'text', 'CHAR': 'string', 'DECIMAL': 'decimal', 'FLOAT': 'float', 'DOUBLE': 'float',
    'TIMESTAMP': 'datetime', 'DATETIME': 'datetime', 'DATE': 'date', 'TIME': 'time', 'BOOLEAN': 'boolean',
    'BOOL': 'boolean', 'ENUM': 'enum', 'JSON': 'json'
}

def get_column_strategy(sql_type: str, constraints: List[str]) -> str:
    if 'PRIMARY_KEY' in constraints or 'AUTO_INCREMENT' in constraints: return 'primary_key'
    if any(c.startswith('FOREIGN_KEY_REFERENCES_') for c in constraints): return 'foreign_key'
    return TYPE_MAP.get(sql_type.upper(), 'string')

def generate_column_values(fake: Faker, column_name: str, strategy: str, num_rows: int, constraints: List[str], generated_data: dict) -> List[Any]:
    if strategy == 'primary_key': return list(range(1, num_rows + 1))
    if strategy == 'foreign_key': return _generate_fk(fake, constraints, num_rows, generated_data)
    if strategy == 'integer': return [fake.random_int(min=1, max=1000000) for _ in range(num_rows)]
    if strategy == 'string': return _generate_string(fake, column_name, num_rows)
    if strategy == 'text': return [fake.text() for _ in range(num_rows)]
    if strategy in ['decimal', 'float']: return [round(fake.random.uniform(0, 10000), 2) for _ in range(num_rows)]
    if strategy == 'datetime': return [fake.date_time_between(start_date='-2y', end_date='now').strftime('%Y-%m-%d %H:%M:%S') for _ in range(num_rows)]
    if strategy == 'date': return [fake.date_between(start_date='-2y', end_date='today').strftime('%Y-%m-%d') for _ in range(num_rows)]
    if strategy == 'time': return [fake.time() for _ in range(num_rows)]
    if strategy == 'boolean': return [fake.boolean() for _ in range(num_rows)]
    if strategy == 'enum': return [fake.random.choice(['ACTIVE', 'INACTIVE', 'PENDING', 'COMPLETE']) for _ in range(num_rows)]
    if strategy == 'json': return [json.dumps({'key': fake.word(), 'value': fake.word()}) for _ in range(num_rows)]
    return [fake.word() for _ in range(num_rows)]

def _generate_fk(fake: Faker, constraints: List[str], num_rows: int, generated_data: dict) -> List[Any]:
    for c in constraints:
        if c.startswith('FOREIGN_KEY_REFERENCES_'):
            ref = c.replace('FOREIGN_KEY_REFERENCES_', '')
            if '.' in ref:
                tbl, col = ref.split('.')
                if tbl in generated_data and col in generated_data[tbl].columns:
                    vals = generated_data[tbl][col].tolist()
                    return [fake.random.choice(vals) for _ in range(num_rows)]
    return [fake.random_int(min=1, max=100) for _ in range(num_rows)]

def _generate_string(fake: Faker, name: str, n: int) -> List[Any]:
    l = name.lower()
    if 'name' in l:
        if 'first' in l: return [fake.first_name() for _ in range(n)]
        if 'last' in l: return [fake.last_name() for _ in range(n)]
        return [fake.name() for _ in range(n)]
    if 'email' in l: return [fake.email() for _ in range(n)]
    if 'phone' in l: return [fake.phone_number() for _ in range(n)]
    if 'address' in l: return [fake.address() for _ in range(n)]
    if 'city' in l: return [fake.city() for _ in range(n)]
    if 'country' in l: return [fake.country() for _ in range(n)]
    return [fake.word() for _ in range(n)]
