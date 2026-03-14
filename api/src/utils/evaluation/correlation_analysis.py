import numpy as np
import pandas as pd
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def correlation_analysis(real_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze correlation preservation between real and synthetic data."""
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
