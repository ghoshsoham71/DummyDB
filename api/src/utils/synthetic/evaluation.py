import logging
from typing import Dict, Any
try:
    from sdv.evaluation.multi_table import evaluate_quality as evaluate_multi_quality
    from sdv.evaluation.single_table import evaluate_quality
    from sdv.metadata import SingleTableMetadata
except ImportError:
    pass

logger = logging.getLogger(__name__)

def evaluate_synthetic_quality(real_data, synthetic_data, metadata) -> Dict[str, Any]:
    """Evaluate synthetic data quality."""
    results = {}
    try:
        report = evaluate_multi_quality(real_data=real_data, synthetic_data=synthetic_data, metadata=metadata)
        results['overall_score'] = report.get_score()
        results['property_scores'] = report.get_properties()
    except Exception as e:
        logger.warning(f"Multi-table evaluation failed: {e}")
        results['table_scores'] = {}
        for table_name, df in real_data.items():
            if table_name in synthetic_data:
                try:
                    sm = SingleTableMetadata()
                    sm.detect_from_dataframe(df)
                    score = evaluate_quality(real_data=df, synthetic_data=synthetic_data[table_name], metadata=sm).get_score()
                    results['table_scores'][table_name] = score
                except Exception:
                    results['table_scores'][table_name] = None
    return results
