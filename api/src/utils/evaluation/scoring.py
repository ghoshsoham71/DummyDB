import numpy as np
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def interpret_quality_score(score: float) -> str:
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

def calculate_quality_score(evaluation: Dict[str, Any]) -> Dict[str, Any]:
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
        corr_score = max(0, 1 - max_diff)
        scores.append(('correlation_preservation_score', corr_score))
    
    if scores:
        overall_score = np.mean([score for _, score in scores])
        interpretation = interpret_quality_score(overall_score)
        
        return {
            'overall_score': float(overall_score),
            'quality_interpretation': interpretation,
            'component_scores': dict(scores)
        }
    else:
        return {
            'overall_score': None,
            'quality_interpretation': 'Unable to calculate quality score',
            'component_scores': {}
        }
