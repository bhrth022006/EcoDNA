"""
Real diversity-index math (no mocking) applied to whatever abundance
counts are stored for a dataset's species observations.
"""
import math
from typing import List


def shannon_index(counts: List[int]) -> float:
    total = sum(counts)
    if total == 0:
        return 0.0
    h = 0.0
    for c in counts:
        if c == 0:
            continue
        p = c / total
        h -= p * math.log(p)
    return round(h, 4) + 0.0  # + 0.0 normalises -0.0 (single-species case) to 0.0


def simpson_index(counts: List[int]) -> float:
    """Returns Simpson's Diversity Index (1 - D), where D is the probability
    two random individuals belong to the same species. Ranges 0 (no diversity)
    to ~1 (infinite diversity)."""
    total = sum(counts)
    if total <= 1:
        return 0.0
    d = sum((c * (c - 1)) for c in counts) / (total * (total - 1))
    return round(1 - d, 4)


def pielou_evenness(counts: List[int]) -> float:
    """Shannon evenness: H / ln(S), where S is species richness."""
    richness = len([c for c in counts if c > 0])
    if richness <= 1:
        return 0.0
    h = shannon_index(counts)
    return round(h / math.log(richness), 4)


def species_richness(counts: List[int]) -> int:
    return len([c for c in counts if c > 0])
