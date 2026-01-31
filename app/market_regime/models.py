from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional

class RegimeType(Enum):
    SOFT_LANDING = "LATE CYCLE / SOFT LANDING"
    REFLATION = "REFLATION / OVERHEATING"
    STAGFLATION = "STAGFLATION"
    RECESSION = "RECESSION / HARD LANDING"
    UNCERTAIN = "TRANSITIONAL / MIXED SIGNALS"

@dataclass
class AssetContext:
    ticker: str
    price: float
    change_percent_5d: float  # Weekly change
    trend_short: str # Up/Down/Flat (based on SMA50 or similar)
    trend_long: str  # Up/Down/Flat (based on SMA200)
    volatility: str  # High/Low (based on ATR or relative range)

@dataclass
class MarketSnapshot:
    regime: RegimeType
    drivers: List[str]
    baskets: Dict[str, List[str]] # Basket Name -> List of Tickers
    explanation: str
    # Specific metric values for display
    metrics: Dict[str, str] = field(default_factory=dict) 
