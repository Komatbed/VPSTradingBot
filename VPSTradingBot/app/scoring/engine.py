from typing import List
from app.core.models import MarketDataSnapshot, StrategySignal
from app.scoring.models import TradeScore
from app.scoring.stages import (
    ScoringStage, DataSanityStage, RiskRewardStage, MarketRegimeStage,
    TrendBiasStage, MomentumStage, MeanReversionStage, VolatilityContextStage,
    ConfluenceStage, ExpectancyStage, TimingStage, NewsRiskStage
)

class ScoringEngine:
    def __init__(self):
        self.stages: List[ScoringStage] = [
            DataSanityStage(),
            RiskRewardStage(),
            MarketRegimeStage(),
            TrendBiasStage(),
            MomentumStage(),
            MeanReversionStage(),
            VolatilityContextStage(),
            ConfluenceStage(),
            ExpectancyStage(),
            TimingStage(),
            NewsRiskStage(),
        ]

    def evaluate(self, snapshot: MarketDataSnapshot, signal: StrategySignal) -> TradeScore:
        components = []
        raw_score = 0.0
        max_possible = sum(10.0 * stage.weight for stage in self.stages)
        veto_triggered = False

        for stage in self.stages:
            component = stage.evaluate(snapshot, signal)
            components.append(component)
            raw_score += component.weighted_score
            
            if stage.is_critical and component.score == 0.0:
                veto_triggered = True
            
        normalized_score = (raw_score / max_possible) * 100.0 if max_possible > 0 else 0.0

        if veto_triggered:
            verdict = "IGNORE"
            # Optional: penalize score further visually?
            # normalized_score = 0.0 
        elif normalized_score >= 70.0:
            verdict = "TRADE"
        elif normalized_score >= 45.0:
            verdict = "WATCHLIST"
        else:
            verdict = "IGNORE"

        return TradeScore(
            total_score=normalized_score,
            raw_score=raw_score,
            max_possible_score=max_possible,
            components=components,
            verdict=verdict
        )