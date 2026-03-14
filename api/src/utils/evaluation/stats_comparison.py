import pandas as pd
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def basic_statistics_comparison(real_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> Dict[str, Any]:
    """Compare basic statistics between real and synthetic data."""
    comparison = {}
    numeric_cols = real_df.select_dtypes(include=['number']).columns
    
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
                    
                    mean_diff = abs(real_stats['mean'] - synthetic_stats['mean']) / abs(real_stats['mean']) if real_stats['mean'] != 0 else 0
                    std_diff = abs(real_stats['std'] - synthetic_stats['std']) / abs(real_stats['std']) if real_stats['std'] != 0 else 0
                    
                    comparison[col] = {
                        'real_statistics': real_stats,
                        'synthetic_statistics': synthetic_stats,
                        'relative_mean_difference': float(mean_diff),
                        'relative_std_difference': float(std_diff)
                    }
            except Exception as e:
                logger.warning(f"Statistics comparison failed for {col}: {e}")
    
    return comparison
