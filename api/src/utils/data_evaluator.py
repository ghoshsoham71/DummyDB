#!/usr/bin/env python3

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from scipy import stats
from scipy.stats import ks_2samp, chi2_contingency
import json
import os

logger = logging.getLogger(__name__)

# Optional imports for enhanced evaluation
try:
    from table_evaluator import TableEvaluator
    TABLE_EVALUATOR_AVAILABLE = True
except ImportError:
    logger.info("table-evaluator not available. Using basic statistical tests only.")
    TABLE_EVALUATOR_AVAILABLE = False

class DataQualityEvaluator:
    """Evaluate synthetic data quality against real data."""
    
    def __init__(self):
        """Initialize the evaluator."""
        self.real_data = {}
        self.synthetic_data = {}
        self.evaluation_results = {}
        
    def load_datasets(self, 
                     real_data_dir: str = 'seed_data',
                     synthetic_data_dir: str = 'synthetic_data') -> bool:
        """Load real and synthetic datasets for comparison."""
        logger.info("Loading datasets for quality evaluation...")
        
        # Load real (seed) data
        real_path = Path(real_data_dir)
        if real_path.exists():
            for csv_file in real_path.glob("*.csv"):
                table_name = csv_file.stem
                try:
                    df = pd.read_csv(csv_file)
                    self.real_data[table_name] = df
                    logger.info(f"  Loaded real data: {table_name} ({len(df)} rows)")
                except Exception as e:
                    logger.error(f"  Error loading real data {csv_file}: {e}")
        
        # Load synthetic data
        synthetic_path = Path(synthetic_data_dir)
        if synthetic_path.exists():
            for csv_file in synthetic_path.glob("*_synthetic.csv"):
                # Extract table name by removing _synthetic suffix
                table_name = csv_file.stem.replace('_synthetic', '')
                try:
                    df = pd.read_csv(csv_file)
                    self.synthetic_data[table_name] = df
                    logger.info(f"  Loaded synthetic data: {table_name} ({len(df)} rows)")
                except Exception as e:
                    logger.error(f"  Error loading synthetic data {csv_file}: {e}")
        
        # Find common tables
        common_tables = set(self.real_data.keys()) & set(self.synthetic_data.keys())
        logger.info(f"Found {len(common_tables)} tables for comparison: {list(common_tables)}")
        
        return len(common_tables) > 0
    
    def kolmogorov_smirnov_test(self, table_name: str) -> Dict[str, Any]:
        """Perform Kolmogorov-Smirnov test for numerical columns."""
        if table_name not in self.real_data or table_name not in self.synthetic_data:
            return {}
        
        real_df = self.real_data[table_name]
        synthetic_df = self.synthetic_data[table_name]
        
        ks_results = {}
        numeric_cols = real_df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            if col in synthetic_df.columns:
                try:
                    # Remove NaN values
                    real_values = real_df[col].dropna()
                    synthetic_values = synthetic_df[col].dropna()
                    
                    if len(real_values) > 0 and len(synthetic_values) > 0:
                        statistic, p_value = ks_2samp(real_values, synthetic_values)
                        ks_results[col] = {
                            'statistic': float(statistic),
                            'p_value': float(p_value),
                            'similar_distribution': float(p_value) > 0.05,  # Not significantly different
                            'interpretation': 'Similar distributions' if float(p_value) > 0.05 else 'Different distributions'
                        }
                except Exception as e:
                    logger.warning(f"KS test failed for {table_name}.{col}: {e}")
        
        return ks_results
    
    def chi_square_test(self, table_name: str) -> Dict[str, Any]:
        """Perform Chi-square test for categorical columns."""
        if table_name not in self.real_data or table_name not in self.synthetic_data:
            return {}
        
        real_df = self.real_data[table_name]
        synthetic_df = self.synthetic_data[table_name]
        
        chi2_results = {}
        categorical_cols = real_df.select_dtypes(include=['object', 'category']).columns
        
        for col in categorical_cols:
            if col in synthetic_df.columns:
                try:
                    # Get value counts
                    real_counts = real_df[col].value_counts()
                    synthetic_counts = synthetic_df[col].value_counts()
                    
                    # Align categories
                    all_categories = set(real_counts.index) | set(synthetic_counts.index)
                    
                    if len(all_categories) > 1:  # Need at least 2 categories
                        real_aligned = [real_counts.get(cat, 0) for cat in all_categories]
                        synthetic_aligned = [synthetic_counts.get(cat, 0) for cat in all_categories]
                        
                        # Create contingency table
                        contingency_table = np.array([real_aligned, synthetic_aligned])
                        
                        if contingency_table.sum() > 0:
                            chi2, p_value, dof, expected = chi2_contingency(contingency_table)
                            chi2_results[col] = {
                                'chi2_statistic': float(chi2),
                                'p_value': float(p_value),
                                'degrees_of_freedom': int(dof),
                                'similar_distribution': float(p_value) > 0.05,
                                'interpretation': 'Similar distributions' if float(p_value) > 0.05 else 'Different distributions'
                            }
                except Exception as e:
                    logger.warning(f"Chi-square test failed for {table_name}.{col}: {e}")
        
        return chi2_results
    
    def correlation_analysis(self, table_name: str) -> Dict[str, Any]:
        """Analyze correlation preservation between real and synthetic data."""
        if table_name not in self.real_data or table_name not in self.synthetic_data:
            return {}
        
        real_df = self.real_data[table_name]
        synthetic_df = self.synthetic_data[table_name]
        
        # Get numeric columns
        numeric_cols = real_df.select_dtypes(include=[np.number]).columns
        common_numeric = [col for col in numeric_cols if col in synthetic_df.columns]
        
        if len(common_numeric) < 2:
            return {'error': 'Not enough numeric columns for correlation analysis'}
        
        try:
            # Calculate correlations
            real_corr = real_df[common_numeric].corr()
            synthetic_corr = synthetic_df[common_numeric].corr()
            
            # Compare correlations
            corr_diff = np.abs(real_corr - synthetic_corr)
            
            # Calculate metrics
            max_diff = corr_diff.max().max()
            mean_diff = corr_diff.mean().mean()
            
            # Correlation preservation quality
            if max_diff < 0.1:
                quality = 'Excellent'
            elif max_diff < 0.2:
                quality = 'Good'
            elif max_diff < 0.3:
                quality = 'Fair'
            else:
                quality = 'Poor'
            
            return {
                'max_correlation_difference': float(max_diff),
                'mean_correlation_difference': float(mean_diff),
                'correlation_preservation_quality': quality,
                'real_correlation_matrix': real_corr.to_dict(),
                'synthetic_correlation_matrix': synthetic_corr.to_dict(),
                'correlation_differences': corr_diff.to_dict()
            }
            
        except Exception as e:
            return {'error': f'Correlation analysis failed: {str(e)}'}
    
    def basic_statistics_comparison(self, table_name: str) -> Dict[str, Any]:
        """Compare basic statistics between real and synthetic data."""
        if table_name not in self.real_data or table_name not in self.synthetic_data:
            return {}
        
        real_df = self.real_data[table_name]
        synthetic_df = self.synthetic_data[table_name]
        
        comparison = {}
        numeric_cols = real_df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            if col in synthetic_df.columns:
                try:
                    real_values = real_df[col].dropna()
                    synthetic_values = synthetic_df[col].dropna()
                    
                    if len(real_values) > 0 and len(synthetic_values) > 0:
                        real_stats = {
                            'mean': float(real_values.mean()),
                            'std': float(real_values.std()),
                            'min': float(real_values.min()),
                            'max': float(real_values.max()),
                            'median': float(real_values.median()),
                            'count': int(len(real_values))
                        }
                        
                        synthetic_stats = {
                            'mean': float(synthetic_values.mean()),
                            'std': float(synthetic_values.std()),
                            'min': float(synthetic_values.min()),
                            'max': float(synthetic_values.max()),
                            'median': float(synthetic_values.median()),
                            'count': int(len(synthetic_values))
                        }
                        
                        # Calculate relative differences
                        mean_diff = abs(real_stats['mean'] - synthetic_stats['mean']) / abs(real_stats['mean']) if real_stats['mean'] != 0 else 0
                        std_diff = abs(real_stats['std'] - synthetic_stats['std']) / abs(real_stats['std']) if real_stats['std'] != 0 else 0
                        
                        comparison[col] = {
                            'real_statistics': real_stats,
                            'synthetic_statistics': synthetic_stats,
                            'relative_mean_difference': float(mean_diff),
                            'relative_std_difference': float(std_diff)
                        }
                        
                except Exception as e:
                    logger.warning(f"Statistics comparison failed for {table_name}.{col}: {e}")
        
        return comparison
    
    def table_evaluator_analysis(self, table_name: str) -> Dict[str, Any]:
        """Use TableEvaluator library for comprehensive analysis."""
        if not TABLE_EVALUATOR_AVAILABLE:
            return {'error': 'table-evaluator not available'}
        
        if table_name not in self.real_data or table_name not in self.synthetic_data:
            return {'error': f'Table {table_name} not found in both datasets'}
        
        try:
            real_df = self.real_data[table_name].copy()
            synthetic_df = self.synthetic_data[table_name].copy()
            
            # Initialize TableEvaluator
            evaluator = TableEvaluator(real_df, synthetic_df)
            
            # Run evaluation - try to find a suitable target column
            target_col = None
            
            # Look for common target column names
            potential_targets = ['id', 'target', 'label', 'class', 'outcome']
            for col in potential_targets:
                if col in real_df.columns:
                    target_col = col
                    break
            
            # If no standard target found, use first column
            if target_col is None and len(real_df.columns) > 0:
                target_col = real_df.columns[0]
            
            if target_col:
                results = evaluator.evaluate(target_col=target_col)
                return {
                    'table_evaluator_results': results,
                    'target_column_used': target_col
                }
            else:
                return {'error': 'No suitable target column found for evaluation'}
                
        except Exception as e:
            return {'error': f'TableEvaluator analysis failed: {str(e)}'}
    
    def evaluate_table_quality(self, table_name: str) -> Dict[str, Any]:
        """Comprehensive quality evaluation for a single table."""
        logger.info(f"Evaluating quality for table: {table_name}")
        
        if table_name not in self.real_data or table_name not in self.synthetic_data:
            return {'error': f'Table {table_name} not found in both datasets'}
        
        evaluation = {
            'table_name': table_name,
            'real_data_rows': len(self.real_data[table_name]),
            'synthetic_data_rows': len(self.synthetic_data[table_name]),
            'generation_ratio': len(self.synthetic_data[table_name]) / len(self.real_data[table_name]),
        }
        
        # Kolmogorov-Smirnov tests
        evaluation['ks_tests'] = self.kolmogorov_smirnov_test(table_name)
        
        # Chi-square tests
        evaluation['chi2_tests'] = self.chi_square_test(table_name)
        
        # Correlation analysis
        evaluation['correlation_analysis'] = self.correlation_analysis(table_name)
        
        # Basic statistics
        evaluation['statistics_comparison'] = self.basic_statistics_comparison(table_name)
        
        # TableEvaluator analysis
        evaluation['table_evaluator'] = self.table_evaluator_analysis(table_name)
        
        # Calculate overall quality score
        evaluation['quality_score'] = self._calculate_quality_score(evaluation)
        
        return evaluation
    
    def _calculate_quality_score(self, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall quality score for a table."""
        scores = []
        
        # KS test score (percentage of columns that pass)
        ks_tests = evaluation.get('ks_tests', {})
        if ks_tests:
            ks_pass_rate = sum(1 for result in ks_tests.values() if result.get('similar_distribution', False)) / len(ks_tests)
            scores.append(('ks_test_pass_rate', ks_pass_rate))
        
        # Chi-square test score
        chi2_tests = evaluation.get('chi2_tests', {})
        if chi2_tests:
            chi2_pass_rate = sum(1 for result in chi2_tests.values() if result.get('similar_distribution', False)) / len(chi2_tests)
            scores.append(('chi2_test_pass_rate', chi2_pass_rate))
        
        # Correlation preservation score
        corr_analysis = evaluation.get('correlation_analysis', {})
        if 'max_correlation_difference' in corr_analysis:
            max_diff = corr_analysis['max_correlation_difference']
            corr_score = max(0, 1 - max_diff)  # 1 - difference, minimum 0
            scores.append(('correlation_preservation_score', corr_score))
        
        # Overall score
        if scores:
            overall_score = np.mean([score for _, score in scores])
            quality_interpretation = self._interpret_quality_score(overall_score)
            
            return {
                'overall_score': float(overall_score),
                'quality_interpretation': quality_interpretation,
                'component_scores': dict(scores)
            }
        else:
            return {
                'overall_score': None,
                'quality_interpretation': 'Unable to calculate quality score',
                'component_scores': {}
            }
    
    def _interpret_quality_score(self, score: float) -> str:
        """Interpret quality score into human-readable form."""
        if score >= 0.9:
            return 'Excellent - Synthetic data closely matches real data'
        elif score >= 0.8:
            return 'Very Good - Minor differences in some distributions'
        elif score >= 0.7:
            return 'Good - Acceptable quality with some notable differences'
        elif score >= 0.6:
            return 'Fair - Significant differences that may impact use cases'
        elif score >= 0.5:
            return 'Poor - Major differences requiring attention'
        else:
            return 'Very Poor - Synthetic data significantly differs from real data'
    
    def evaluate_all_tables(self) -> Dict[str, Any]:
        """Evaluate quality for all available tables."""
        logger.info("Starting comprehensive quality evaluation...")
        
        common_tables = set(self.real_data.keys()) & set(self.synthetic_data.keys())
        
        if not common_tables:
            return {'error': 'No common tables found for evaluation'}
        
        evaluation_results = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'total_tables': len(common_tables),
            'table_evaluations': {},
            'overall_summary': {}
        }
        
        # Evaluate each table
        for table_name in common_tables:
            evaluation_results['table_evaluations'][table_name] = self.evaluate_table_quality(table_name)
        
        # Calculate overall summary
        evaluation_results['overall_summary'] = self._calculate_overall_summary(evaluation_results['table_evaluations'])
        
        # Store results
        self.evaluation_results = evaluation_results
        
        return evaluation_results
    
    def _calculate_overall_summary(self, table_evaluations: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall summary across all tables."""
        total_real_rows = sum(eval_data.get('real_data_rows', 0) for eval_data in table_evaluations.values())
        total_synthetic_rows = sum(eval_data.get('synthetic_data_rows', 0) for eval_data in table_evaluations.values())
        
        # Collect quality scores
        quality_scores = []
        for eval_data in table_evaluations.values():
            if 'quality_score' in eval_data and eval_data['quality_score'].get('overall_score') is not None:
                quality_scores.append(eval_data['quality_score']['overall_score'])
        
        summary = {
            'total_real_rows': total_real_rows,
            'total_synthetic_rows': total_synthetic_rows,
            'overall_generation_ratio': total_synthetic_rows / total_real_rows if total_real_rows > 0 else 0,
            'tables_evaluated': len(table_evaluations)
        }
        
        if quality_scores:
            avg_quality_score = np.mean(quality_scores)
            summary['average_quality_score'] = float(avg_quality_score)
            summary['quality_interpretation'] = self._interpret_quality_score(avg_quality_score)
            summary['quality_score_distribution'] = {
                'min': float(np.min(quality_scores)),
                'max': float(np.max(quality_scores)),
                'std': float(np.std(quality_scores))
            }
        else:
            summary['average_quality_score'] = None
            summary['quality_interpretation'] = 'Unable to calculate overall quality'
        
        return summary
    
    def save_evaluation_report(self, output_path: str = 'evaluation_report.json'):
        """Save evaluation results to JSON file."""
        if not self.evaluation_results:
            logger.warning("No evaluation results to save. Run evaluate_all_tables() first.")
            return
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.evaluation_results, f, indent=2, ensure_ascii=False)
            logger.info(f"Evaluation report saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save evaluation report: {e}")
    
    def print_evaluation_summary(self):
        """Print a summary of the evaluation results."""
        if not self.evaluation_results:
            print("No evaluation results available. Run evaluate_all_tables() first.")
            return
        
        print("\n" + "="*60)
        print("SYNTHETIC DATA QUALITY EVALUATION SUMMARY")
        print("="*60)
        
        summary = self.evaluation_results.get('overall_summary', {})
        
        print(f"Tables evaluated: {summary.get('tables_evaluated', 0)}")
        print(f"Total real rows: {summary.get('total_real_rows', 0):,}")
        print(f"Total synthetic rows: {summary.get('total_synthetic_rows', 0):,}")
        print(f"Generation ratio: {summary.get('overall_generation_ratio', 0):.1f}x")
        
        if summary.get('average_quality_score') is not None:
            print(f"\nAverage quality score: {summary['average_quality_score']:.3f}")
            print(f"Quality assessment: {summary.get('quality_interpretation', 'N/A')}")
        
        print("\nPer-table results:")
        print("-" * 40)
        
        for table_name, evaluation in self.evaluation_results.get('table_evaluations', {}).items():
            quality_score = evaluation.get('quality_score', {})
            if quality_score.get('overall_score') is not None:
                score = quality_score['overall_score']
                interpretation = quality_score.get('quality_interpretation', 'N/A')
                print(f"{table_name}: {score:.3f} - {interpretation}")
            else:
                print(f"{table_name}: Unable to calculate quality score")

def evaluate_synthetic_data_quality(real_data_dir: str = 'seed_data',
                                   synthetic_data_dir: str = 'synthetic_data',
                                   output_report: str = 'evaluation_report.json') -> bool:
    """
    Complete pipeline to evaluate synthetic data quality.
    
    Args:
        real_data_dir: Directory containing real/seed CSV files
        synthetic_data_dir: Directory containing synthetic CSV files
        output_report: Path to save evaluation report
        
    Returns:
        bool: Success status
    """
    try:
        evaluator = DataQualityEvaluator()
        
        # Load datasets
        if not evaluator.load_datasets(real_data_dir, synthetic_data_dir):
            logger.error("Failed to load datasets for evaluation")
            return False
        
        # Run evaluation
        results = evaluator.evaluate_all_tables()
        
        # Save report
        evaluator.save_evaluation_report(output_report)
        
        # Print summary
        evaluator.print_evaluation_summary()
        
        logger.info("Data quality evaluation completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Data quality evaluation failed: {e}")
        return False