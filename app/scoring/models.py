from dataclasses import dataclass, field
from typing import List

@dataclass
class ScoreComponent:
    name: str
    score: float  # 0-10
    weight: float
    reason: str
    details: dict = field(default_factory=dict)

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight

@dataclass
class TradeScore:
    total_score: float  # 0-100 (normalized)
    raw_score: float    # Sum of weighted scores
    max_possible_score: float
    components: List[ScoreComponent]
    verdict: str  # "TRADE", "WATCHLIST", "IGNORE"