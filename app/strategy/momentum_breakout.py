from __future__ import annotations

from typing import Optional

from app.core.models import MarketDataSnapshot, MarketRegime, StrategySignal, StrategySignalType
from app.strategy.base import Strategy, StrategyContext


class MomentumBreakoutStrategy(Strategy):
    id = "momentum_breakout_simple"

    def __init__(self, lookback: int = 20, breakout_factor: float = 1.2) -> None:
        self._lookback = lookback
        self._breakout_factor = breakout_factor

    def _calculate_ema(self, prices: list[float], period: int) -> list[float]:
        if len(prices) < period:
            return []
        ema_values = []
        multiplier = 2 / (period + 1)
        sma = sum(prices[:period]) / period
        ema_values.append(sma)
        for price in prices[period:]:
            prev_ema = ema_values[-1]
            new_ema = (price - prev_ema) * multiplier + prev_ema
            ema_values.append(new_ema)
        return ema_values

    async def on_market_data(
        self,
        snapshot: MarketDataSnapshot,
        context: StrategyContext,
    ) -> Optional[StrategySignal]:
        if snapshot.regime not in (MarketRegime.TREND, MarketRegime.HIGH_VOLATILITY):
            # Relaxed: Allow scoring to penalize
            pass
        candles = snapshot.candles
        if len(candles) < self._lookback + 1:
            return None
            
        closes = [c.close for c in candles]
        
        # Trend Filter: EMA 200 (or 50)
        trend_period = 200 if len(closes) >= 200 else 50
        emas = self._calculate_ema(closes, trend_period)
        trend_ema = emas[-1] if emas else None
        
        recent = candles[-self._lookback - 1 :]
        highs = [c.high for c in recent]
        lows = [c.low for c in recent]
        
        # Calculate ATR for dynamic threshold
        atr_window = min(14, len(candles))
        atr_highs = [c.high for c in candles[-atr_window:]]
        atr_lows = [c.low for c in candles[-atr_window:]]
        atr_ranges = [h - l for h, l in zip(atr_highs, atr_lows)]
        atr = sum(atr_ranges) / len(atr_ranges)

        last = recent[-1]
        last_range = last.high - last.low
        prev_highs = highs[:-1]
        prev_lows = lows[:-1]
        
        # New Logic: Breakout of N-period High/Low
        # Relaxed: Removed hard > 1.0 ATR filter (moved to scoring/confidence)
        is_breakout_high = last.close > max(prev_highs)
        is_breakout_low = last.close < min(prev_lows)
        is_significant = last_range > 0.6 * atr # Lower threshold to catch more candidates

        if is_breakout_high and is_significant:
            # Relaxed: Removed hard trend filter
            signal_type = StrategySignalType.BUY
        elif is_breakout_low and is_significant:
            # Relaxed: Removed hard trend filter
            signal_type = StrategySignalType.SELL
        else:
            return None

        last_close = last.close
        confidence = 70.0
        score_reasons = []
        
        # Base confidence logic
        breakout_strength = last_range / atr
        if breakout_strength > 2.0:
            confidence += 10.0
            score_reasons.append(f"bardzo silna świeca (x{breakout_strength:.1f} ATR)")
        if snapshot.regime == MarketRegime.HIGH_VOLATILITY:
            confidence += 10.0
            score_reasons.append("reżim wysokiej zmienności")
        if trend_ema:
            if signal_type == StrategySignalType.BUY and last_close > trend_ema:
                confidence += 5.0
                score_reasons.append(f"zgodność z EMA{trend_period}")
            elif signal_type == StrategySignalType.SELL and last_close < trend_ema:
                confidence += 5.0
                score_reasons.append(f"zgodność z EMA{trend_period}")
            
        if confidence > 95.0:
            confidence = 95.0
            
        reason = f"Wybicie z konsolidacji. {', '.join(score_reasons) if score_reasons else 'Standardowe wybicie momentum'}."

        if signal_type == StrategySignalType.BUY:
            sl = last_close - 2.0 * atr
            tp = last_close + 4.0 * atr
        else:
            sl = last_close + 2.0 * atr
            tp = last_close - 4.0 * atr

        return StrategySignal(
            strategy_id=self.id,
            instrument=snapshot.instrument,
            signal_type=signal_type,
            confidence=confidence,
            stop_loss_price=sl,
            take_profit_price=tp,
            reason=reason,
        )

