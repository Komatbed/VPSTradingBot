from __future__ import annotations

from statistics import mean
from typing import Optional

from app.core.models import MarketDataSnapshot, MarketRegime, StrategySignal, StrategySignalType
from app.strategy.base import Strategy, StrategyContext


class TrendFollowingStrategy(Strategy):
    id = "trend_following_simple"

    def __init__(self, lookback: int = 40, trigger_ratio: float = 0.0005) -> None:
        self._lookback = lookback
        self._trigger_ratio = trigger_ratio

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
        candles = snapshot.candles
        if len(candles) < self._lookback:
            return None
        closes = [c.close for c in candles]
        last_close = closes[-1]
        
        # Trend Filter: EMA 200 (or 50 if history is short)
        trend_period = 200 if len(closes) >= 200 else 50
        emas = self._calculate_ema(closes, trend_period)
        trend_ema = emas[-1] if emas else None

        # RSI Check
        rsi = self._calculate_rsi(closes)
        
        # Use simple moving average for deviation check
        ma_subset = closes[-self._lookback:]
        ma = mean(ma_subset)
        diff = last_close - ma
        threshold = abs(ma) * self._trigger_ratio

        if snapshot.regime not in (MarketRegime.TREND, MarketRegime.HIGH_VOLATILITY):
            # Relaxed: Allow scoring to penalize regime instead of hard block
            # return None 
            pass

        if diff > threshold:
            # Removed strict RSI filter: if rsi > 70: return None
            # Removed strict trend filter: if trend_ema and last_close < trend_ema: return None
                
            signal_type = StrategySignalType.BUY
            # Dynamic confidence - will be overridden/enhanced by ScoringEngine
            confidence = 50.0 # Base confidence
            score_reasons = []
            if diff > 1.5 * threshold:
                confidence += 10.0
                score_reasons.append("silne odchylenie od średniej")
            if snapshot.regime == MarketRegime.TREND:
                confidence += 10.0
                score_reasons.append("potwierdzony trend")
            if trend_ema and last_close > trend_ema:
                confidence += 5.0
                score_reasons.append(f"zgodność z EMA{trend_period}")
            if confidence > 95.0:
                confidence = 95.0
            
            reason = f"Cena powyżej średniej. {', '.join(score_reasons) if score_reasons else 'Standardowy sygnał trendowy'}."

        elif diff < -threshold:
            # Removed strict RSI filter: if rsi < 30: return None
            # Removed strict trend filter: if trend_ema and last_close > trend_ema: return None
            
            signal_type = StrategySignalType.SELL
            # Dynamic confidence - will be overridden/enhanced by ScoringEngine
            confidence = 50.0 # Base confidence
            score_reasons = []
            if abs(diff) > 1.5 * threshold:
                confidence += 10.0
                score_reasons.append("silne odchylenie od średniej")
            if snapshot.regime == MarketRegime.TREND:
                confidence += 10.0
                score_reasons.append("potwierdzony trend")
            if trend_ema and last_close < trend_ema:
                confidence += 5.0
                score_reasons.append(f"zgodność z EMA{trend_period}")
            if confidence > 95.0:
                confidence = 95.0
            
            reason = f"Cena poniżej średniej. {', '.join(score_reasons) if score_reasons else 'Standardowy sygnał trendowy'}."
        else:
            return None
        # ATR Calculation (True Range)
        atr_window = 14
        if len(candles) < atr_window + 1:
            # Fallback to simple range if not enough history for TR
            current_window_candles = candles[-min(len(candles), atr_window):]
            trs = [c.high - c.low for c in current_window_candles]
            atr = sum(trs) / len(trs) if trs else 0.0
        else:
            # Calculate True Range properly
            # We need previous close, so we look at window + 1 candle back
            relevant_candles = candles[-(atr_window + 1):]
            trs = []
            for i in range(1, len(relevant_candles)):
                curr = relevant_candles[i]
                prev = relevant_candles[i-1]
                tr = max(
                    curr.high - curr.low,
                    abs(curr.high - prev.close),
                    abs(curr.low - prev.close)
                )
                trs.append(tr)
            atr = sum(trs) / len(trs) if trs else 0.0

        if signal_type == StrategySignalType.BUY:
            stop_loss_price = last_close - 2.0 * atr
            take_profit_price = last_close + 4.0 * atr
        else:
            stop_loss_price = last_close + 2.0 * atr
            take_profit_price = last_close - 4.0 * atr
        
        return StrategySignal(
            strategy_id=self.id,
            instrument=snapshot.instrument,
            signal_type=signal_type,
            confidence=confidence,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            reason=reason,
        )

