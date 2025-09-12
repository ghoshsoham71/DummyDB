#!/usr/bin/env python3

import pandas as pd
import numpy as np
import json
import os
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from sdv.metadata import SingleTableMetadata, MultiTableMetadata
    from sdv.single_table import GaussianCopulaSynthesizer, CTGANSynthesizer
    from sdv.multi_table import HMASynthesizer
    from sdv.evaluation.single_table import evaluate_quality
    from sdv.evaluation.multi_table import evaluate_quality as evaluate_multi_quality
    SDV_AVAILABLE = True
except ImportError:
    logger.warning("SDV not installed. Synthetic data generation will be limited.")
    SDV_AVAILABLE = False

class SDVSyntheticGenerator:
    """Generate synthetic data using SDV (Synthetic Data Vault)."""
    
    def __init__(self, schema: Dict[str, Any]):
        """Initialize generator with database schema."""
        if not SDV_AVAILABLE:
            raise ImportError("SDV library is required. Install with: pip install sdv")
        
        self.schema = schema
        self.metadata = None
        self.synthesizer = None
        self.real_data = {}
        self.synthetic_data = {}
        
        # SQL to SDV type mapping
        self.type_mapping = {
            'INT': 'numerical',
            'INTEGER': 'numerical',
            'BIGINT': 'numerical',
            'SMALLINT': 'numerical',
            'TINYINT': 'numerical',
            'DECIMAL': 'numerical',
            'FLOAT': 'numerical',
            'DOUBLE': 'numerical',
            'VARCHAR': 'categorical',
            'TEXT': 'categorical',
            'CHAR': 'categorical',
            'TIMESTAMP': 'datetime',
            'DATETIME': 'datetime',
            'DATE': 'datetime',
            'TIME': 'datetime',
            'BOOLEAN': 'boolean',
            'BOOL': 'boolean',
            'ENUM': 'categorical',
            'JSON': 'categorical'
        }
    
    def create_metadata(self) -> MultiTableMetadata:
        """Create SDV metadata from database schema."""
        logger.info("Creating SDV metadata from database schema...")
        
        self.metadata = MultiTableMetadata()
        
        # Process each database and table
        for database in self.schema.get('databases', []):
            db_name = database['name']
            logger.info(f"Processing database: {db_name}")
            
            for table in database['tables']:
                table_name = table['name']
                logger.info(f"  Processing table: {table_name}")
                
                # Add table to metadata
                self.metadata.add_table(table_name)
                
                # Process columns
                primary_key = None
                for attr in table['attributes']:
                    col_name = attr['name']
                    sql_type = attr['type']
                    constraints = attr.get('constraints', [])
                    
                    # Determine SDV column type
                    if 'PRIMARY_KEY' in constraints or 'AUTO_INCREMENT' in constraints:
                        sdv_type = 'id'
                        primary_key = col_name
                    elif any(c.startswith('FOREIGN_KEY_REFERENCES_') for c in constraints):
                        sdv_type = 'id'
                    elif sql_type.upper() in self.type_mapping:
                        sdv_type = self.type_mapping[sql_type.upper()]
                    else:
                        sdv_type = 'categorical'
                    
                    # Add column to metadata
                    self.metadata.add_column(table_name, col_name, sdtype=sdv_type)
                
                # Set primary key if found
                if primary_key:
                    self.metadata.set_primary_key(table_name, primary_key)
        
        # Add relationships (foreign keys)
        self._add_relationships()
        
        return self.metadata
    
    def _add_relationships(self):
        """Add foreign key relationships to metadata."""
        for database in self.schema.get('databases', []):
            for table in database['tables']:
                table_name = table['name']
                
                for attr in table['attributes']:
                    constraints = attr.get('constraints', [])
                    
                    for constraint in constraints:
                        if constraint.startswith('FOREIGN_KEY_REFERENCES_'):
                            ref_info = constraint.replace('FOREIGN_KEY_REFERENCES_', '')
                            if '.' in ref_info:
                                parent_table, parent_col = ref_info.split('.')
                                child_col = attr['name']
                                
                                try:
                                    self.metadata.add_relationship(
                                        parent_table_name=parent_table,
                                        child_table_name=table_name,
                                        parent_primary_key=parent_col,
                                        child_foreign_key=child_col
                                    )
                                    logger.info(f"    Added relationship: {parent_table}.{parent_col} -> {table_name}.{child_col}")
                                except Exception as e:
                                    logger.warning(f"    Could not add relationship {parent_table}.{parent_col} -> {table_name}.{child_col}: {e}")
    
    def load_seed_data(self, seed_data_dir: str = 'seed_data') -> Dict[str, pd.DataFrame]:
        """Load seed data from CSV files."""
        logger.info(f"Loading seed data from {seed_data_dir}...")
        
        self.real_data = {}
        seed_path = Path(seed_data_dir)
        
        if not seed_path.exists():
            raise FileNotFoundError(f"Seed data directory not found: {seed_data_dir}")
        
        # Load CSV files
        for csv_file in seed_path.glob("*.csv"):
            table_name = csv_file.stem
            
            try:
                df = pd.read_csv(csv_file)
                
                # Convert data types based on metadata if available
                if self.metadata and table_name in self.metadata.tables:
                    df = self._convert_data_types(df, table_name)
                
                self.real_data[table_name] = df
                logger.info(f"  Loaded {len(df)} rows for table '{table_name}'")
                
            except Exception as e:
                logger.error(f"  Error loading {csv_file}: {e}")
        
        logger.info(f"Loaded {len(self.real_data)} tables")
        return self.real_data
    
    def _convert_data_types(self, df: pd.DataFrame, table_name: str) -> pd.DataFrame:
        """Convert DataFrame columns to appropriate types based on metadata."""
        if not self.metadata or table_name not in self.metadata.tables:
            return df
        
        table_meta = self.metadata.tables[table_name]
        
        for col_name, col_info in table_meta.columns.items():
            if col_name not in df.columns:
                continue
            
            try:
                sdtype = col_info['sdtype']
                
                if sdtype == 'datetime':
                    df[col_name] = pd.to_datetime(df[col_name], errors='coerce')
                elif sdtype == 'numerical':
                    df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
                elif sdtype == 'boolean':
                    df[col_name] = df[col_name].astype(bool)
                # categorical and id types are handled automatically
                
            except Exception as e:
                logger.warning(f"Could not convert column {table_name}.{col_name}: {e}")
        
        return df
    
    def train_synthesizer(self, synthesizer_type: str = 'HMA') -> Any:
        """Train the SDV synthesizer."""
        if not self.real_data:
            raise ValueError("No seed data loaded. Call load_seed_data() first.")
        
        if not self.metadata:
            raise ValueError("No metadata created. Call create_metadata() first.")
        
        logger.info(f"Training {synthesizer_type} synthesizer...")
        
        try:
            if synthesizer_type.upper() == 'HMA':
                self.synthesizer = HMASynthesizer(metadata=self.metadata)
            elif synthesizer_type.upper() == 'GAUSSIAN':
                # For multi-table, we'll use HMA as fallback
                self.synthesizer = HMASynthesizer(metadata=self.metadata)
            else:
                raise ValueError(f"Unsupported synthesizer type: {synthesizer_type}")
            
            # Fit the synthesizer
            self.synthesizer.fit(self.real_data)
            logger.info("Synthesizer training completed successfully!")
            
            return self.synthesizer
            
        except Exception as e:
            logger.error(f"Failed to train synthesizer: {e}")
            raise
    
    def generate_synthetic_data(self, 
                              scale: float = 2.0,
                              num_rows: Optional[Dict[str, int]] = None) -> Dict[str, pd.DataFrame]:
        """Generate synthetic data."""
        if not self.synthesizer:
            raise ValueError("Synthesizer not trained. Call train_synthesizer() first.")
        
        logger.info("Generating synthetic data...")
        
        try:
            if num_rows:
                # Generate specific number of rows per table
                logger.info(f"Generating specific row counts: {num_rows}")
                self.synthetic_data = self.synthesizer.sample(num_rows=num_rows)
            else:
                # Generate scaled data
                logger.info(f"Generating {scale}x scale synthetic data")
                self.synthetic_data = self.synthesizer.sample(scale=scale)
            
            # Log generation summary
            for table_name, df in self.synthetic_data.items():
                original_count = len(self.real_data.get(table_name, []))
                synthetic_count = len(df)
                ratio = synthetic_count / original_count if original_count > 0 else 0
                logger.info(f"  Generated {synthetic_count} rows for '{table_name}' (original: {original_count}, ratio: {ratio:.1f}x)")
            
            return self.synthetic_data
            
        except Exception as e:
            logger.error(f"Failed to generate synthetic data: {e}")
            raise
    
    def evaluate_quality(self) -> Dict[str, Any]:
        """Evaluate synthetic data quality."""
        if not self.synthetic_data or not self.real_data:
            raise ValueError("Both real and synthetic data required for evaluation.")
        
        logger.info("Evaluating synthetic data quality...")
        
        evaluation_results = {}
        
        try:
            # Multi-table evaluation
            quality_report = evaluate_multi_quality(
                real_data=self.real_data,
                synthetic_data=self.synthetic_data,
                metadata=self.metadata
            )
            
            overall_score = quality_report.get_score()
            evaluation_results['overall_score'] = overall_score
            evaluation_results['property_scores'] = quality_report.get_properties()
            
            logger.info(f"Overall quality score: {overall_score:.3f}")
            
            # Log detailed scores
            for property_name, score in evaluation_results['property_scores'].items():
                logger.info(f"  {property_name}: {score:.3f}")
            
        except Exception as e:
            logger.warning(f"Multi-table evaluation failed: {e}")
            
            # Fall back to single-table evaluations
            logger.info("Performing single-table evaluations...")
            evaluation_results['table_scores'] = {}
            
            for table_name in self.real_data.keys():
                if table_name in self.synthetic_data:
                    try:
                        # Create single table metadata
                        table_df = self.real_data[table_name]
                        single_meta = SingleTableMetadata()
                        single_meta.detect_from_dataframe(table_df)
                        
                        table_quality = evaluate_quality(
                            real_data=table_df,
                            synthetic_data=self.synthetic_data[table_name],
                            metadata=single_meta
                        )
                        
                        table_score = table_quality.get_score()
                        evaluation_results['table_scores'][table_name] = table_score
                        logger.info(f"  {table_name}: {table_score:.3f}")
                        
                    except Exception as table_error:
                        logger.warning(f"  {table_name}: Evaluation failed - {table_error}")
                        evaluation_results['table_scores'][table_name] = None
        
        return evaluation_results
    
    def save_synthetic_data(self, output_dir: str = 'synthetic_data'):
        """Save synthetic data to CSV files."""
        if not self.synthetic_data:
            raise ValueError("No synthetic data to save. Call generate_synthetic_data() first.")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving synthetic data to {output_dir}...")
        
        for table_name, df in self.synthetic_data.items():
            csv_path = output_path / f"{table_name}_synthetic.csv"
            df.to_csv(csv_path, index=False)
            logger.info(f"  Saved {len(df)} rows to {csv_path}")
    
    def get_generation_summary(self) -> Dict[str, Any]:
        """Get summary of the generation process."""
        summary = {
            'schema_tables': len([t for db in self.schema.get('databases', []) for t in db.get('tables', [])]),
            'loaded_tables': len(self.real_data),
            'generated_tables': len(self.synthetic_data),
            'synthesizer_trained': self.synthesizer is not None,
            'metadata_created': self.metadata is not None,
        }
        
        if self.real_data and self.synthetic_data:
            summary['data_summary'] = {}
            for table_name in self.real_data.keys():
                real_rows = len(self.real_data[table_name])
                synthetic_rows = len(self.synthetic_data.get(table_name, []))
                summary['data_summary'][table_name] = {
                    'real_rows': real_rows,
                    'synthetic_rows': synthetic_rows,
                    'generation_ratio': synthetic_rows / real_rows if real_rows > 0 else 0
                }
        
        return summary

def generate_synthetic_data_from_schema(schema_path: str,
                                      seed_data_dir: str = 'seed_data',
                                      output_dir: str = 'synthetic_data',
                                      scale: float = 2.0,
                                      synthesizer_type: str = 'HMA') -> bool:
    """
    Complete pipeline to generate synthetic data from schema.
    
    Args:
        schema_path: Path to JSON schema file
        seed_data_dir: Directory containing seed CSV files
        output_dir: Output directory for synthetic data
        scale: Scale factor for data generation
        synthesizer_type: Type of synthesizer ('HMA', 'GAUSSIAN')
        
    Returns:
        bool: Success status
    """
    try:
        # Load schema
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        # Initialize generator
        generator = SDVSyntheticGenerator(schema)
        
        # Create metadata
        generator.create_metadata()
        
        # Load seed data
        generator.load_seed_data(seed_data_dir)
        
        # Train synthesizer
        generator.train_synthesizer(synthesizer_type)
        
        # Generate synthetic data
        generator.generate_synthetic_data(scale=scale)
        
        # Evaluate quality
        try:
            evaluation = generator.evaluate_quality()
            logger.info("Quality evaluation completed")
            if 'overall_score' in evaluation:
                logger.info(f"Overall quality score: {evaluation['overall_score']:.3f}")
        except Exception as e:
            logger.warning(f"Quality evaluation failed: {e}")
        
        # Save synthetic data
        generator.save_synthetic_data(output_dir)
        
        # Print summary
        summary = generator.get_generation_summary()
        logger.info("Synthetic data generation completed successfully!")
        logger.info(f"Summary: {summary}")
        
        return True
        
    except Exception as e:
        logger.error(f"Synthetic data generation failed: {e}")
        return False