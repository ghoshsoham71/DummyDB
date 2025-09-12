#!/usr/bin/env python3

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import random
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from faker import Faker
import json

logger = logging.getLogger(__name__)

class SeedDataGenerator:
    """Generate realistic seed data based on database schema."""
    
    def __init__(self, schema: Dict[str, Any], locale: str = 'en_US'):
        """Initialize generator with schema and locale."""
        self.schema = schema
        self.fake = Faker(locale)
        self.generated_data = {}
        self.foreign_key_map = {}
        
    def _analyze_schema_relationships(self) -> Dict[str, List[Dict]]:
        """Analyze foreign key relationships in schema."""
        relationships = {}
        
        for database in self.schema.get('databases', []):
            for table in database.get('tables', []):
                table_name = table['name']
                relationships[table_name] = []
                
                for attr in table.get('attributes', []):
                    for constraint in attr.get('constraints', []):
                        if constraint.startswith('FOREIGN_KEY_REFERENCES_'):
                            ref_info = constraint.replace('FOREIGN_KEY_REFERENCES_', '')
                            if '.' in ref_info:
                                ref_table, ref_column = ref_info.split('.')
                                relationships[table_name].append({
                                    'column': attr['name'],
                                    'references_table': ref_table,
                                    'references_column': ref_column
                                })
        
        return relationships
    
    def _determine_generation_order(self) -> List[str]:
        """Determine table generation order based on dependencies."""
        relationships = self._analyze_schema_relationships()
        
        # Simple topological sort
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(table_name: str):
            if table_name in temp_visited:
                # Circular dependency - handle gracefully
                return
            if table_name in visited:
                return
                
            temp_visited.add(table_name)
            
            # Visit dependencies first
            for rel in relationships.get(table_name, []):
                ref_table = rel['references_table']
                if ref_table in relationships:  # Only if table exists in schema
                    visit(ref_table)
            
            temp_visited.remove(table_name)
            visited.add(table_name)
            result.append(table_name)
        
        # Get all table names
        all_tables = set()
        for database in self.schema.get('databases', []):
            for table in database.get('tables', []):
                all_tables.add(table['name'])
        
        # Visit all tables
        for table_name in all_tables:
            if table_name not in visited:
                visit(table_name)
                
        return result
    
    def _get_column_type_mapping(self, sql_type: str, constraints: List[str]) -> str:
        """Map SQL type to data generation strategy."""
        sql_type = sql_type.upper()
        
        # Primary key handling
        if 'PRIMARY_KEY' in constraints or 'AUTO_INCREMENT' in constraints:
            return 'primary_key'
        
        # Foreign key handling
        for constraint in constraints:
            if constraint.startswith('FOREIGN_KEY_REFERENCES_'):
                return 'foreign_key'
        
        # Type-based mapping
        type_map = {
            'INT': 'integer',
            'INTEGER': 'integer', 
            'BIGINT': 'integer',
            'SMALLINT': 'integer',
            'TINYINT': 'integer',
            'VARCHAR': 'string',
            'TEXT': 'text',
            'CHAR': 'string',
            'DECIMAL': 'decimal',
            'FLOAT': 'float',
            'DOUBLE': 'float',
            'TIMESTAMP': 'datetime',
            'DATETIME': 'datetime',
            'DATE': 'date',
            'TIME': 'time',
            'BOOLEAN': 'boolean',
            'BOOL': 'boolean',
            'ENUM': 'enum',
            'JSON': 'json'
        }
        
        return type_map.get(sql_type, 'string')
    
    def _generate_column_data(self, 
                            column_name: str, 
                            column_type: str, 
                            constraints: List[str], 
                            num_rows: int,
                            table_name: str) -> List[Any]:
        """Generate data for a specific column."""
        
        data_type = self._get_column_type_mapping(column_type, constraints)
        
        if data_type == 'primary_key':
            return list(range(1, num_rows + 1))
        
        elif data_type == 'foreign_key':
            # Find referenced table and column
            ref_table = None
            ref_column = None
            
            for constraint in constraints:
                if constraint.startswith('FOREIGN_KEY_REFERENCES_'):
                    ref_info = constraint.replace('FOREIGN_KEY_REFERENCES_', '')
                    if '.' in ref_info:
                        ref_table, ref_column = ref_info.split('.')
                        break
            
            if ref_table and ref_table in self.generated_data:
                ref_data = self.generated_data[ref_table]
                if ref_column in ref_data.columns:
                    available_values = ref_data[ref_column].tolist()
                    return [self.fake.random.choice(available_values) for _ in range(num_rows)]
            
            # Fallback to integers if reference not found
            return [self.fake.random_int(min=1, max=100) for _ in range(num_rows)]
        
        elif data_type == 'integer':
            return [self.fake.random_int(min=1, max=1000000) for _ in range(num_rows)]
        
        elif data_type == 'string':
            # Context-aware string generation
            col_lower = column_name.lower()
            if 'name' in col_lower:
                if 'first' in col_lower:
                    return [self.fake.first_name() for _ in range(num_rows)]
                elif 'last' in col_lower:
                    return [self.fake.last_name() for _ in range(num_rows)]
                elif 'user' in col_lower:
                    return [self.fake.user_name() for _ in range(num_rows)]
                elif 'company' in col_lower:
                    return [self.fake.company() for _ in range(num_rows)]
                else:
                    return [self.fake.name() for _ in range(num_rows)]
            elif 'email' in col_lower:
                return [self.fake.email() for _ in range(num_rows)]
            elif 'phone' in col_lower:
                return [self.fake.phone_number() for _ in range(num_rows)]
            elif 'address' in col_lower:
                return [self.fake.address() for _ in range(num_rows)]
            elif 'city' in col_lower:
                return [self.fake.city() for _ in range(num_rows)]
            elif 'country' in col_lower:
                return [self.fake.country() for _ in range(num_rows)]
            elif 'description' in col_lower:
                return [self.fake.text(max_nb_chars=200) for _ in range(num_rows)]
            elif 'title' in col_lower:
                return [self.fake.job() for _ in range(num_rows)]
            else:
                return [self.fake.word() for _ in range(num_rows)]
        
        elif data_type == 'text':
            return [self.fake.text() for _ in range(num_rows)]
        
        elif data_type == 'decimal' or data_type == 'float':
            return [round(self.fake.random.uniform(0, 10000), 2) for _ in range(num_rows)]
        
        elif data_type == 'datetime':
            return [self.fake.date_time_between(start_date='-2y', end_date='now').strftime('%Y-%m-%d %H:%M:%S') for _ in range(num_rows)]
        
        elif data_type == 'date':
            return [self.fake.date_between(start_date='-2y', end_date='today').strftime('%Y-%m-%d') for _ in range(num_rows)]
        
        elif data_type == 'time':
            return [self.fake.time() for _ in range(num_rows)]
        
        elif data_type == 'boolean':
            return [self.fake.boolean() for _ in range(num_rows)]
        
        elif data_type == 'enum':
            # Default enum values - could be enhanced to parse actual enum values
            enum_values = ['ACTIVE', 'INACTIVE', 'PENDING', 'COMPLETE']
            return [self.fake.random.choice(enum_values) for _ in range(num_rows)]
        
        elif data_type == 'json':
            return [json.dumps({'key': self.fake.word(), 'value': self.fake.word()}) for _ in range(num_rows)]
        
        else:
            # Default to string
            return [self.fake.word() for _ in range(num_rows)]
    
    def generate_table_data(self, table_schema: Dict[str, Any], num_rows: int = 10) -> pd.DataFrame:
        """Generate data for a single table."""
        table_name = table_schema['name']
        attributes = table_schema.get('attributes', [])
        
        if not attributes:
            logger.warning(f"No attributes found for table {table_name}")
            return pd.DataFrame()
        
        table_data = {}
        
        for attr in attributes:
            column_name = attr['name']
            column_type = attr['type']
            constraints = attr.get('constraints', [])
            
            try:
                column_data = self._generate_column_data(
                    column_name, column_type, constraints, num_rows, table_name
                )
                table_data[column_name] = column_data
            except Exception as e:
                logger.error(f"Error generating data for {table_name}.{column_name}: {e}")
                # Fallback to simple strings
                table_data[column_name] = [f"{column_name}_{i}" for i in range(num_rows)]
        
        return pd.DataFrame(table_data)
    
    def generate_all_seed_data(self, output_dir: str = 'seed_data', base_rows: int = 10) -> Dict[str, pd.DataFrame]:
        """Generate seed data for all tables in proper order."""
        os.makedirs(output_dir, exist_ok=True)
        
        # Determine generation order
        generation_order = self._determine_generation_order()
        
        logger.info(f"Generating seed data in order: {generation_order}")
        
        generated_datasets = {}
        
        for database in self.schema.get('databases', []):
            for table_schema in database.get('tables', []):
                table_name = table_schema['name']
                
                if table_name not in generation_order:
                    continue
                
                # Determine number of rows (could be customized per table)
                num_rows = base_rows
                
                # Generate table data
                logger.info(f"Generating {num_rows} rows for table: {table_name}")
                table_df = self.generate_table_data(table_schema, num_rows)
                
                if not table_df.empty:
                    # Store for foreign key references
                    self.generated_data[table_name] = table_df
                    generated_datasets[table_name] = table_df
                    
                    # Save to CSV
                    output_path = os.path.join(output_dir, f"{table_name}.csv")
                    table_df.to_csv(output_path, index=False)
                    logger.info(f"Saved {len(table_df)} rows to {output_path}")
                else:
                    logger.warning(f"No data generated for table {table_name}")
        
        return generated_datasets
    
    def get_generation_summary(self) -> Dict[str, Any]:
        """Get summary of generated data."""
        summary = {
            'total_tables': len(self.generated_data),
            'total_rows': sum(len(df) for df in self.generated_data.values()),
            'tables': {}
        }
        
        for table_name, df in self.generated_data.items():
            summary['tables'][table_name] = {
                'rows': len(df),
                'columns': len(df.columns),
                'column_names': list(df.columns)
            }
        
        return summary

def create_seed_data_from_schema(schema_path: str, 
                                output_dir: str = 'seed_data',
                                base_rows: int = 10) -> bool:
    """
    Create seed data from schema file.
    
    Args:
        schema_path: Path to JSON schema file
        output_dir: Output directory for CSV files
        base_rows: Base number of rows per table
        
    Returns:
        bool: Success status
    """
    try:
        # Load schema
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        # Generate seed data
        generator = SeedDataGenerator(schema)
        datasets = generator.generate_all_seed_data(output_dir, base_rows)
        
        # Print summary
        summary = generator.get_generation_summary()
        logger.info(f"Seed data generation completed:")
        logger.info(f"  Total tables: {summary['total_tables']}")
        logger.info(f"  Total rows: {summary['total_rows']}")
        
        for table_name, table_info in summary['tables'].items():
            logger.info(f"  {table_name}: {table_info['rows']} rows, {table_info['columns']} columns")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate seed data: {e}")
        return False