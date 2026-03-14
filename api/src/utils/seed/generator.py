#!/usr/bin/env python3

import pandas as pd
import os
import logging
import json
from typing import Dict, Any
from faker import Faker

from .strategies import get_column_strategy, generate_column_values
from .orchestrator import determine_generation_order

logger = logging.getLogger(__name__)

class SeedDataGenerator:
    """Generate realistic seed data based on database schema."""
    
    def __init__(self, schema: Dict[str, Any], locale: str = 'en_US'):
        self.schema = schema
        self.fake = Faker(locale)
        self.generated_data = {}
        
    def generate_table_data(self, table_schema: Dict[str, Any], num_rows: int = 10) -> pd.DataFrame:
        table_name = table_schema['name']
        attributes = table_schema.get('attributes', [])
        if not attributes: return pd.DataFrame()
        
        table_data = {}
        for attr in attributes:
            col_name, col_type = attr['name'], attr['type']
            constraints = attr.get('constraints', [])
            strategy = get_column_strategy(col_type, constraints)
            try:
                table_data[col_name] = generate_column_values(self.fake, col_name, strategy, num_rows, constraints, self.generated_data)
            except Exception as e:
                logger.error(f"Error in {table_name}.{col_name}: {e}")
                table_data[col_name] = [f"{col_name}_{i}" for i in range(num_rows)]
        return pd.DataFrame(table_data)
    
    def generate_all_seed_data(self, output_dir: str = 'seed_data', base_rows: int = 10) -> Dict[str, pd.DataFrame]:
        os.makedirs(output_dir, exist_ok=True)
        order = determine_generation_order(self.schema)
        datasets = {}
        
        for db in self.schema.get('databases', []):
            for tbl_schema in db.get('tables', []):
                name = tbl_schema['name']
                if name not in order: continue
                df = self.generate_table_data(tbl_schema, base_rows)
                if not df.empty:
                    self.generated_data[name] = df
                    datasets[name] = df
                    df.to_csv(os.path.join(output_dir, f"{name}.csv"), index=False)
        return datasets
    
    def get_generation_summary(self) -> Dict[str, Any]:
        return {
            'total_tables': len(self.generated_data),
            'total_rows': sum(len(df) for df in self.generated_data.values()),
            'tables': {n: {'rows': len(df), 'cols': len(df.columns)} for n, df in self.generated_data.items()}
        }

def create_seed_data_from_schema(schema_path: str, output_dir: str = 'seed_data', base_rows: int = 10) -> bool:
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        gen = SeedDataGenerator(schema)
        gen.generate_all_seed_data(output_dir, base_rows)
        return True
    except Exception as e:
        logger.error(f"Failed: {e}"); return False