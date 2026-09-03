from typing import List, Optional
import numpy as np


class ConfidenceEvaluator:
    """
    Evaluates confidence score across multi-modal evidence.
    Returns float score ONLY if real model logits or probability maps are available.
    Otherwise returns None.
    Never fabricates random or synthetic confidence numbers.
    """
    @staticmethod
    def evaluate(
        model_scores: List[Optional[float]],
        mask_probabilities: Optional[np.ndarray] = None
    ) -> Optional[float]:
        valid_scores = [s for s in model_scores if s is not None and np.isfinite(s)]

        if mask_probabilities is not None and mask_probabilities.size > 0:
            # Average probability over positive change/grounding region
            high_prob = mask_probabilities[mask_probabilities >= 0.5]
            if high_prob.size > 0:
                valid_scores.append(float(np.mean(high_prob)))

        if not valid_scores:
            return None

        return round(float(np.mean(valid_scores)), 4)
