from __future__ import annotations

from typing import List, Optional

from app.core.models import Candle, MarketRegime


class MarketRegimeEngine:
    def infer_regime(self, candles: List[Candle]) -> Optional[MarketRegime]:
        if not candles:
            return None
        closes = [c.close for c in candles]
        if len(closes) < 50:
            # Not enough data for meaningful analysis
            return MarketRegime.CHAOS
            
        avg = sum(closes) / len(closes)
        variance = sum((x - avg) ** 2 for x in closes) / len(closes)
        volatility = variance**0.5
        
        # 1. Volatility Checks
        if volatility > 0.02: # Adjusted threshold for "High Volatility"
            return MarketRegime.HIGH_VOLATILITY
        if volatility < 0.0003:
            return MarketRegime.LOW_LIQUIDITY
            
        # 2. Trend Detection via EMA
        # We need at least 200 candles for EMA200, but let's try with what we have.
        # If we have < 200, fallback to EMA20/50
        
        use_long_term = len(closes) >= 200
        fast_period = 50 if use_long_term else 20
        slow_period = 200 if use_long_term else 50
        
        ema_fast = self._calculate_ema(closes, fast_period)
        ema_slow = self._calculate_ema(closes, slow_period)
        
        if ema_fast and ema_slow:
            last_fast = ema_fast[-1]
            last_slow = ema_slow[-1]
            
            # Check separation
            diff = abs(last_fast - last_slow)
            threshold = last_slow * 0.001 # 0.1% separation required to call it a TREND
            
            if diff > threshold:
                return MarketRegime.TREND
                
        return MarketRegime.RANGE

    def _calculate_ema(self, prices: List[float], period: int) -> List[float]:
        if len(prices) < period:
            return []
        
        ema_values = []
        multiplier = 2 / (period + 1)
        
        # Initial SMA
        sma = sum(prices[:period]) / period
        ema_values.append(sma)
        
        # Calculate EMA
        for price in prices[period:]:
            prev_ema = ema_values[-1]
            new_ema = (price - prev_ema) * multiplier + prev_ema
            ema_values.append(new_ema)
            
        return ema_values