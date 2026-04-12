from __future__ import annotations

import math
from collections import Counter

from llmscope.types.signals import QualityResult


def output_entropy(token_texts: list[str]) -> QualityResult:
    token_count: int = len(token_texts)
    if token_count == 0:
        return QualityResult(entropy_score=0.0, token_count=0)

    counts: Counter[str] = Counter(token_texts)
    total: int = sum(counts.values())
    entropy: float = 0.0
    for count in counts.values():
        p: float = count / total
        entropy -= p * math.log2(p)

    vocab_size: int = len(counts)
    max_entropy: float = math.log2(vocab_size) if vocab_size > 1 else 1.0
    normalized: float = min(entropy / max_entropy, 1.0) if max_entropy > 0 else 0.0

    return QualityResult(
        entropy_score=round(normalized, 6),
        token_count=token_count,
    )
