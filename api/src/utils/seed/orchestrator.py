import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def analyze_relationships(schema: Dict[str, Any]) -> Dict[str, List[Dict]]:
    rels = {}
    for db in schema.get('databases', []):
        for tbl in db.get('tables', []):
            name = tbl['name']
            rels[name] = []
            for attr in tbl.get('attributes', []):
                for c in attr.get('constraints', []):
                    if c.startswith('FOREIGN_KEY_REFERENCES_'):
                        ref = c.replace('FOREIGN_KEY_REFERENCES_', '')
                        if '.' in ref:
                            ref_tbl, ref_col = ref.split('.')
                            rels[name].append({'column': attr['name'], 'references_table': ref_tbl, 'references_column': ref_col})
    return rels

def determine_generation_order(schema: Dict[str, Any]) -> List[str]:
    rels = analyze_relationships(schema)
    visited, temp, result = set(), set(), []
    
    def visit(name: str):
        if name in temp: return # Circular
        if name in visited: return
        temp.add(name)
        for rel in rels.get(name, []):
            if rel['references_table'] in rels: visit(rel['references_table'])
        temp.remove(name)
        visited.add(name)
        result.append(name)

    all_tables = {t['name'] for db in schema.get('databases', []) for t in db.get('tables', [])}
    for name in all_tables:
        if name not in visited: visit(name)
    return result
