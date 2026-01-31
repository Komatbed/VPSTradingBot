from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple, List
import pandas as pd
import numpy as np

class MarketRegimeType(Enum):
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    UNCERTAIN = "UNCERTAIN"

@dataclass
class RegimeAnalysis:
    symbol: str
    regime: MarketRegimeType
    volatility_score: float  # 0-100 (based on ATR/price %)
    trend_strength: float    # 0-100 (based on ADX)
    details: Dict[str, float]

class MarketRegimeEngine:
    """
    Detects the current market regime for a given instrument.
    Used to adjust strategy parameters and ML thresholds.
    """
    
    def __init__(self, yahoo_client):
        self._yahoo_client = yahoo_client
        # Thresholds
        self._adx_trend_threshold = 25.0
        self._high_volatility_percent = 1.5  # If ATR is > 1.5% of price, it's high vol (for forex/indices)

    def analyze_regime(self, df: pd.DataFrame, symbol: str) -> RegimeAnalysis:
        """
        Analyzes the provided DataFrame (must have OHLC) to determine market regime.
        """
        if df is None or df.empty or len(df) < 50:
            return RegimeAnalysis(
                symbol=symbol,
                regime=MarketRegimeType.UNCERTAIN,
                volatility_score=0.0,
                trend_strength=0.0,
                details={"reason": "Not enough data"}
            )

        # 1. Calculate Indicators
        # ATR (14)
        df['tr'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(
                abs(df['High'] - df['Close'].shift(1)),
                abs(df['Low'] - df['Close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(window=14).mean()
        
        # ADX (14) - simplified
        # We will use a simplified trend strength proxy if ADX lib not available, 
        # but here let's calculate EMA Slope as a robust proxy.
        df['ema_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        # 2. Determine Volatility
        current_price = df['Close'].iloc[-1]
        current_atr = df['atr'].iloc[-1]
        vol_percent = (current_atr / current_price) * 100
        
        volatility_score = min(100.0, (vol_percent / 2.0) * 100) # Normalized roughly
        
        is_high_volatility = vol_percent > self._high_volatility_percent

        # 3. Determine Trend Strength (ADX Proxy)
        # Using EMA separation and slope
        ema_slope = (df['ema_50'].iloc[-1] - df['ema_50'].iloc[-5]) / 5
        trend_strength = min(100.0, abs(ema_slope / current_price) * 10000) # Arbitrary scaling
        
        is_trending = trend_strength > 2.0 or abs(current_price - df['ema_200'].iloc[-1]) > (2 * current_atr)

        # 4. Classification
        regime = MarketRegimeType.RANGING
        
        if is_high_volatility:
            regime = MarketRegimeType.HIGH_VOLATILITY
        elif is_trending:
            regime = MarketRegimeType.TRENDING
            
        return RegimeAnalysis(
            symbol=symbol,
            regime=regime,
            volatility_score=round(volatility_score, 2),
            trend_strength=round(trend_strength, 2),
            details={
                "vol_percent": round(vol_percent, 3),
                "atr": round(current_atr, 4),
                "ema_gap": round(current_price - df['ema_200'].iloc[-1], 2)
            }
        )

    async def get_regime_async(self, symbol: str, timeframe: str = "H1") -> RegimeAnalysis:
        """Async helper to fetch data and analyze."""
        df = await self._yahoo_client.get_data(symbol, interval=timeframe, period="1mo")
        return self.analyze_regime(df, symbol)
