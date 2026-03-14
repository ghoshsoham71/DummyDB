import logging
from typing import Dict, Any
try:
    from sdv.metadata import MultiTableMetadata
    SDV_AVAILABLE = True
except ImportError:
    SDV_AVAILABLE = False

logger = logging.getLogger(__name__)

TYPE_MAPPING = {
    'INT': 'numerical', 'INTEGER': 'numerical', 'BIGINT': 'numerical',
    'SMALLINT': 'numerical', 'TINYINT': 'numerical', 'DECIMAL': 'numerical',
    'FLOAT': 'numerical', 'DOUBLE': 'numerical', 'VARCHAR': 'categorical',
    'TEXT': 'categorical', 'CHAR': 'categorical', 'TIMESTAMP': 'datetime',
    'DATETIME': 'datetime', 'DATE': 'datetime', 'TIME': 'datetime',
    'BOOLEAN': 'boolean', 'BOOL': 'boolean', 'ENUM': 'categorical', 'JSON': 'categorical'
}

def create_sdv_metadata(schema: Dict[str, Any]) -> Any:
    """Create SDV metadata from database schema."""
    if not SDV_AVAILABLE: return None
    metadata = MultiTableMetadata()
    
    for database in schema.get('databases', []):
        for table in database['tables']:
            table_name = table['name']
            metadata.add_table(table_name)
            primary_key = None
            for attr in table['attributes']:
                col_name = attr['name']
                sql_type = attr['type'].upper()
                constraints = attr.get('constraints', [])
                
                if 'PRIMARY_KEY' in constraints or 'AUTO_INCREMENT' in constraints:
                    sdv_type, primary_key = 'id', col_name
                elif any(c.startswith('FOREIGN_KEY_REFERENCES_') for c in constraints):
                    sdv_type = 'id'
                else:
                    sdv_type = TYPE_MAPPING.get(sql_type, 'categorical')
                metadata.add_column(table_name, col_name, sdtype=sdv_type)
            if primary_key:
                metadata.set_primary_key(table_name, primary_key)
                
    _add_relationships(metadata, schema)
    return metadata

def _add_relationships(metadata, schema):
    for database in schema.get('databases', []):
        for table in database['tables']:
            table_name = table['name']
            for attr in table['attributes']:
                for constraint in attr.get('constraints', []):
                    if constraint.startswith('FOREIGN_KEY_REFERENCES_'):
                        ref_info = constraint.replace('FOREIGN_KEY_REFERENCES_', '')
                        if '.' in ref_info:
                            parent_table, parent_col = ref_info.split('.')
                            try:
                                metadata.add_relationship(
                                    parent_table_name=parent_table, child_table_name=table_name,
                                    parent_primary_key=parent_col, child_foreign_key=attr['name']
                                )
                            except Exception as e:
                                logger.warning(f"Could not add relationship: {e}")
