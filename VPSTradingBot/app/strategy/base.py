from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.models import MarketDataSnapshot, StrategySignal


@dataclass
class StrategyContext:
    max_risk_per_trade_percent: float


class Strategy:
    id: str

    async def on_market_data(
        self,
        snapshot: MarketDataSnapshot,
        context: StrategyContext,
    ) -> Optional[StrategySignal]:
        raise NotImplementedError

