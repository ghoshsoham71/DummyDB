import pandas as pd
import numpy as np
from scipy.stats import ks_2samp
from typing import Dict, Any, List

class QualityEngine:
    @staticmethod
    def calculate_tvd(real: pd.Series, synth: pd.Series) -> float:
        """Total Variation Distance for categorical columns."""
        p = real.value_counts(normalize=True)
        q = synth.value_counts(normalize=True)
        
        # Align indexes
        all_cats = p.index.union(q.index)
        p = p.reindex(all_cats, fill_value=0)
        q = q.reindex(all_cats, fill_value=0)
        
        return 0.5 * np.sum(np.abs(p - q))

    @staticmethod
    def calculate_ks_test(real: pd.Series, synth: pd.Series) -> float:
        """Kolmogorov-Smirnov test for numerical columns."""
        if real.dtype == 'object' or synth.dtype == 'object':
            return 1.0 # Not applicable
        
        stat, p_val = ks_2samp(real.dropna(), synth.dropna())
        return stat

    def audit_quality(self, real_df: pd.DataFrame, synth_df: pd.DataFrame) -> Dict[str, Any]:
        """Perform full quality audit."""
        results = {"columns": {}, "overall_score": 0.0}
        scores = []
        
        for col in real_df.columns:
            if col not in synth_df.columns: continue
            
            if real_df[col].dtype == 'object':
                score = self.calculate_tvd(real_df[col], synth_df[col])
                metric = "TVD"
            else:
                score = self.calculate_ks_test(real_df[col], synth_df[col])
                metric = "KS-Stat"
            
            results["columns"][col] = {"metric": metric, "score": float(score)}
            scores.append(score)
            
        if scores:
            results["overall_score"] = 1.0 - float(np.mean(scores))
            
        return results

class PrivacyEngine:
    @staticmethod
    def calculate_dcr(real_df: pd.DataFrame, synth_df: pd.DataFrame) -> float:
        """Distance to Closest Record (DCR) to detect data leakage."""
        # Simple implementation for row-wise exact matches
        # In production use nearest neighbors on normalized data
        intersection = pd.merge(real_df, synth_df, how='inner').drop_duplicates()
        leakage_rate = len(intersection) / len(synth_df) if len(synth_df) > 0 else 0
        return float(leakage_rate)

    def audit_privacy(self, real_df: pd.DataFrame, synth_df: pd.DataFrame) -> Dict[str, Any]:
        """Perform privacy audit."""
        leakage = self.calculate_dcr(real_df, synth_df)
        return {
            "leakage_rate": leakage,
            "status": "safe" if leakage < 0.05 else "risk",
            "recommendation": "Use Differential Privacy" if leakage >= 0.05 else "Proceed"
        }
