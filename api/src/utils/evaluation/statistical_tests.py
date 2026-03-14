import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, chi2_contingency
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def kolmogorov_smirnov_test(real_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> Dict[str, Any]:
    """Perform Kolmogorov-Smirnov test for numerical columns."""
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
                        'similar_distribution': float(p_value) > 0.05,
                        'interpretation': 'Similar distributions' if float(p_value) > 0.05 else 'Different distributions'
                    }
            except Exception as e:
                logger.warning(f"KS test failed for {col}: {e}")
    
    return ks_results

def chi_square_test(real_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> Dict[str, Any]:
    """Perform Chi-square test for categorical columns."""
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
                
                if len(all_categories) > 1:
                    real_aligned = [real_counts.get(cat, 0) for cat in all_categories]
                    synthetic_aligned = [synthetic_counts.get(cat, 0) for cat in all_categories]
                    
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
                logger.warning(f"Chi-square test failed for {col}: {e}")
    
    return chi2_results
