from __future__ import annotations

from statistics import mean
from typing import Optional

from app.core.models import MarketDataSnapshot, MarketRegime, StrategySignal, StrategySignalType
from app.strategy.base import Strategy, StrategyContext


class RangeReversionStrategy(Strategy):
    id = "range_reversion_simple"

    def __init__(self, lookback: int = 30, band_ratio: float = 0.001) -> None:
        self._lookback = lookback
        self._band_ratio = band_ratio

    def _calculate_rsi(self, prices: list[float], period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [max(0, c) for c in changes]
        losses = [max(0, -c) for c in changes]
        if not gains: return 50.0
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        for i in range(period, len(changes)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0: return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    async def on_market_data(
        self,
        snapshot: MarketDataSnapshot,
        context: StrategyContext,
    ) -> Optional[StrategySignal]:
        if snapshot.regime != MarketRegime.RANGE:
            # Relaxed: Allow scoring to penalize instead of hard block
            pass
        candles = snapshot.candles
        if len(candles) < self._lookback:
            return None
        closes = [c.close for c in candles]
        
        # Calculate RSI for confirmation
        rsi = self._calculate_rsi(closes)
        
        # Use subset for Band calculation
        subset_closes = closes[-self._lookback :]
        last_close = subset_closes[-1]
        m = mean(subset_closes)
        band = abs(m) * self._band_ratio
        upper = m + band
        lower = m - band
        score_reasons = []
        confidence = 70.0
        
        if last_close > upper:
            # Filter: Ensure we are overbought (reversion likely)
            # Relaxed: Removed hard RSI < 60 filter
                
            signal_type = StrategySignalType.SELL
            if last_close > upper + (band * 0.2):
                confidence += 10.0
                score_reasons.append("cena wyraźnie powyżej górnej bandy")
            if snapshot.regime == MarketRegime.RANGE:
                confidence += 10.0
                score_reasons.append("potwierdzona konsolidacja")
            if rsi > 70:
                confidence += 5.0
                score_reasons.append("RSI wykupione")
                
            reason = f"Cena przebiła górną bandę. {', '.join(score_reasons) if score_reasons else 'Sygnał powrotu do średniej'}."
            
        elif last_close < lower:
            # Filter: Ensure we are oversold (reversion likely)
            # Relaxed: Removed hard RSI > 40 filter
                
            signal_type = StrategySignalType.BUY
            if last_close < lower - (band * 0.2):
                confidence += 10.0
                score_reasons.append("cena wyraźnie poniżej dolnej bandy")
            if snapshot.regime == MarketRegime.RANGE:
                confidence += 10.0
                score_reasons.append("potwierdzona konsolidacja")
            if rsi < 30:
                confidence += 5.0
                score_reasons.append("RSI wyprzedane")
                
            reason = f"Cena przebiła dolną bandę. {', '.join(score_reasons) if score_reasons else 'Sygnał powrotu do średniej'}."
            
        else:
            return None
            
        if confidence > 95.0:
            confidence = 95.0
        highs = [c.high for c in candles[-14:]]
        lows = [c.low for c in candles[-14:]]
        ranges = [h - l for h, l in zip(highs, lows)]
        atr = sum(ranges) / len(ranges)
        if signal_type == StrategySignalType.BUY:
            sl = last_close - 1.5 * atr
            tp = last_close + 2.0 * atr
        else:
            sl = last_close + 1.5 * atr
            tp = last_close - 2.0 * atr

        return StrategySignal(
            strategy_id=self.id,
            instrument=snapshot.instrument,
            signal_type=signal_type,
            confidence=confidence,
            stop_loss_price=sl,
            take_profit_price=tp,
            reason=reason,
        )

