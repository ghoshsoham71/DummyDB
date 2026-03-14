#!/usr/bin/env python3

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any
from pathlib import Path
import json

from src.utils.evaluation.statistical_tests import kolmogorov_smirnov_test, chi_square_test
from src.utils.evaluation.correlation_analysis import correlation_analysis
from src.utils.evaluation.stats_comparison import basic_statistics_comparison
from src.utils.evaluation.scoring import calculate_quality_score, interpret_quality_score

logger = logging.getLogger(__name__)

# Optional imports for enhanced evaluation
try:
    from table_evaluator import TableEvaluator
    TABLE_EVALUATOR_AVAILABLE = True
except ImportError:
    TABLE_EVALUATOR_AVAILABLE = False

class DataQualityEvaluator:
    """Evaluate synthetic data quality against real data."""
    
    def __init__(self):
        self.real_data = {}
        self.synthetic_data = {}
        self.evaluation_results = {}
        
    def load_datasets(self, real_data_dir: str = 'seed_data', synthetic_data_dir: str = 'synthetic_data') -> bool:
        """Load real and synthetic datasets for comparison."""
        real_path = Path(real_data_dir)
        if real_path.exists():
            for csv_file in real_path.glob("*.csv"):
                try:
                    self.real_data[csv_file.stem] = pd.read_csv(csv_file)
                except Exception as e:
                    logger.error(f"Error loading real data {csv_file}: {e}")
        
        synthetic_path = Path(synthetic_data_dir)
        if synthetic_path.exists():
            for csv_file in synthetic_path.glob("*_synthetic.csv"):
                table_name = csv_file.stem.replace('_synthetic', '')
                try:
                    self.synthetic_data[table_name] = pd.read_csv(csv_file)
                except Exception as e:
                    logger.error(f"Error loading synthetic data {csv_file}: {e}")
        
        common_tables = set(self.real_data.keys()) & set(self.synthetic_data.keys())
        return len(common_tables) > 0

    def evaluate_table_quality(self, table_name: str) -> Dict[str, Any]:
        """Comprehensive quality evaluation for a single table."""
        if table_name not in self.real_data or table_name not in self.synthetic_data:
            return {'error': f'Table {table_name} not found in both datasets'}
        
        real_df = self.real_data[table_name]
        synthetic_df = self.synthetic_data[table_name]
        
        evaluation = {
            'table_name': table_name,
            'real_data_rows': len(real_df),
            'synthetic_data_rows': len(synthetic_df),
            'generation_ratio': len(synthetic_df) / len(real_df) if len(real_df) > 0 else 0,
            'ks_tests': kolmogorov_smirnov_test(real_df, synthetic_df),
            'chi2_tests': chi_square_test(real_df, synthetic_df),
            'correlation_analysis': correlation_analysis(real_df, synthetic_df),
            'statistics_comparison': basic_statistics_comparison(real_df, synthetic_df),
        }
        
        if TABLE_EVALUATOR_AVAILABLE:
            evaluation['table_evaluator'] = self._run_table_evaluator(real_df, synthetic_df)
            
        evaluation['quality_score'] = calculate_quality_score(evaluation)
        return evaluation

    def _run_table_evaluator(self, real_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> Dict[str, Any]:
        """Run TableEvaluator if available."""
        try:
            evaluator = TableEvaluator(real_df.copy(), synthetic_df.copy())
            target_col = next((c for c in ['id', 'target', 'label'] if c in real_df.columns), real_df.columns[0] if len(real_df.columns) > 0 else None)
            if target_col:
                return {'table_evaluator_results': evaluator.evaluate(target_col=target_col), 'target_column_used': target_col}
        except Exception as e:
            return {'error': str(e)}
        return {'error': 'No target column'}

    def evaluate_all_tables(self) -> Dict[str, Any]:
        """Evaluate quality for all available tables."""
        common_tables = set(self.real_data.keys()) & set(self.synthetic_data.keys())
        if not common_tables:
            return {'error': 'No common tables found for evaluation'}
        
        results = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'total_tables': len(common_tables),
            'table_evaluations': {t: self.evaluate_table_quality(t) for t in common_tables},
        }
        
        results['overall_summary'] = self._calculate_overall_summary(results['table_evaluations'])
        self.evaluation_results = results
        return results

    def _calculate_overall_summary(self, table_evals: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall summary across all tables."""
        total_real = sum(e.get('real_data_rows', 0) for e in table_evals.values())
        total_syn = sum(e.get('synthetic_data_rows', 0) for e in table_evals.values())
        scores = [e['quality_score']['overall_score'] for e in table_evals.values() if e.get('quality_score', {}).get('overall_score') is not None]
        
        summary = {
            'total_real_rows': total_real,
            'total_synthetic_rows': total_syn,
            'overall_generation_ratio': total_syn / total_real if total_real > 0 else 0,
            'tables_evaluated': len(table_evals),
            'average_quality_score': float(np.mean(scores)) if scores else None,
        }
        if summary['average_quality_score'] is not None:
            summary['quality_interpretation'] = interpret_quality_score(summary['average_quality_score'])
        return summary

    def save_evaluation_report(self, output_path: str = 'evaluation_report.json'):
        """Save results to JSON."""
        if self.evaluation_results:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.evaluation_results, f, indent=2)