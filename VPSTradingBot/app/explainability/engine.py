from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from app.core.models import MarketDataSnapshot, StrategySignal, Candle
from app.data.tradingview_mapping import to_tradingview_symbol


@dataclass
class Explanation:
    title: str
    pre_trade: str
    post_trade: str
    invalidation: str


class ExplainabilityEngine:
    def build_pre_trade_explanation(
        self,
        snapshot: MarketDataSnapshot,
        signal: StrategySignal,
        expectancy_r: float,
    ) -> Explanation:
        regime_text = snapshot.regime.value if snapshot.regime else "unknown"
        tv_symbol = to_tradingview_symbol(snapshot.instrument)
        tv_link = f"https://www.tradingview.com/chart/?symbol={tv_symbol}"
        
        # S/R
        supports, resistances = self._find_support_resistance(snapshot.candles or [])
        sr_text = ""
        if supports:
            sr_text += f"Wsparcie: {', '.join([f'{s:.2f}' for s in supports])}. "
        if resistances:
            sr_text += f"Opór: {', '.join([f'{r:.2f}' for r in resistances])}."
            
        pre = (
            f"{signal.reason} "
            f"(Strategia: {signal.strategy_id}, Oczekiwany wynik: {expectancy_r:.2f}R). "
            f"{sr_text} "
            f"Wykres: {tv_link}"
        )
        invalidation = (
            f"Setup zostaje unieważniony, jeśli świeca zamknie się wyraźnie po stronie SL "
            f"lub jeśli reżim rynku zmieni się na chaos."
        )
        return Explanation(
            title="Pre-trade",
            pre_trade=pre,
            post_trade="",
            invalidation=invalidation,
        )

    def _find_support_resistance(self, candles: List[Candle], window: int = 10) -> Tuple[List[float], List[float]]:
        if len(candles) < window * 2:
            return [], []
        
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        
        supports = []
        resistances = []
        
        # Analyze
        for i in range(window, len(candles) - window):
            # Local min
            window_lows = lows[i-window : i+window+1]
            if lows[i] == min(window_lows):
                supports.append(lows[i])
                
            # Local max
            window_highs = highs[i-window : i+window+1]
            if highs[i] == max(window_highs):
                resistances.append(highs[i])
                
        current_price = candles[-1].close
        
        # Filter
        valid_supports = sorted(list(set([s for s in supports if s < current_price])))
        valid_resistances = sorted(list(set([r for r in resistances if r > current_price])))
        
        return valid_supports[-3:], valid_resistances[:3]
