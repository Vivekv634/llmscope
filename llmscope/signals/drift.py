from __future__ import annotations

import math
from collections import Counter

from llmscope.types.signals import DriftResult

_SIGNIFICANCE_THRESHOLD: float = 0.15


def cosine_drift(
    run_a_id: str,
    run_a_tokens: list[str],
    run_b_id: str,
    run_b_tokens: list[str],
) -> DriftResult:
    if not run_a_tokens and not run_b_tokens:
        return DriftResult(
            run_a_id=run_a_id,
            run_b_id=run_b_id,
            cosine_drift=0.0,
            is_significant=False,
        )

    counter_a: Counter[str] = Counter(run_a_tokens)
    counter_b: Counter[str] = Counter(run_b_tokens)
    vocab: set[str] = set(counter_a.keys()) | set(counter_b.keys())

    dot: float = sum(counter_a[t] * counter_b[t] for t in vocab)
    norm_a: float = math.sqrt(sum(v * v for v in counter_a.values()))
    norm_b: float = math.sqrt(sum(v * v for v in counter_b.values()))

    if norm_a == 0.0 or norm_b == 0.0:
        similarity: float = 0.0
    else:
        similarity = dot / (norm_a * norm_b)

    drift: float = max(0.0, min(1.0, round(1.0 - similarity, 6)))

    return DriftResult(
        run_a_id=run_a_id,
        run_b_id=run_b_id,
        cosine_drift=drift,
        is_significant=drift > _SIGNIFICANCE_THRESHOLD,
    )
