from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MarketRegime(Enum):
    TREND = "trend"
    RANGE = "range"
    HIGH_VOLATILITY = "high_volatility"
    LOW_LIQUIDITY = "low_liquidity"
    CHAOS = "chaos"


class StrategySignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    FLAT = "flat"


class TradeDirection(Enum):
    LONG = "long"
    SHORT = "short"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    REJECTED = "rejected"


class DecisionVerdict(Enum):
    BUY = "buy"
    SELL = "sell"
    NO_TRADE = "no_trade"


class UserActionType(Enum):
    ENTER = "enter"
    SKIP = "skip"
    REMIND = "remind"
    OPEN_TV = "open_tv"
    VOTE_UP = "vote_up"
    VOTE_DOWN = "vote_down"


class EventType(Enum):
    MARKET_DATA = "market_data"
    STRATEGY_SIGNAL = "strategy_signal"
    ORDER_REQUEST = "order_request"
    ORDER_FILLED = "order_filled"
    ORDER_REJECTED = "order_rejected"
    TELEGRAM_COMMAND = "telegram_command"
    SYSTEM_ALERT = "system_alert"
    EXPLANATION_PRE_TRADE = "explanation_pre_trade"
    DECISION_READY = "decision_ready"
    USER_DECISION = "user_decision"
    ECONOMIC_EVENT_IMMINENT = "economic_event_imminent"
    SYSTEM_PAUSE = "system_pause"
    SYSTEM_RESUME = "system_resume"
    TRADE_COMPLETED = "trade_completed"
    MANUAL_CLOSE_REQUEST = "manual_close_request"


@dataclass
class Candle:
    instrument: str
    timeframe: str
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class SentimentSnapshot:
    mfi: float  # Market Fear Index 0-100
    gti: float  # Global Tension Index 0-100
    mfi_status: str # Low, Moderate, High, Extreme
    gti_status: str # Calm, Tense, Critical
    details: List[str] # Explanation points


@dataclass
class MarketDataSnapshot:
    instrument: str
    timeframe: str
    candles: List[Candle]
    spread: Optional[float]
    regime: Optional[MarketRegime]
    news_impact: Optional[str] = None  # e.g., "High", "Medium"
    time_to_news_min: Optional[float] = None  # Minutes to next event
    sentiment: Optional[SentimentSnapshot] = None


@dataclass
class StrategySignal:
    strategy_id: str
    instrument: str
    signal_type: StrategySignalType
    confidence: float
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    reason: str


@dataclass
class OrderRequest:
    instrument: str
    units: float
    direction: TradeDirection
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    client_tag: str
    strategy_id: str
    confidence: float


@dataclass
class OrderResult:
    order_id: str
    status: OrderStatus
    instrument: str
    units: float
    direction: TradeDirection
    price: Optional[float]
    executed_at: Optional[datetime]
    rejection_reason: Optional[str]
    strategy_id: str
    confidence: float


@dataclass
class TradeRecord:
    trade_id: str
    instrument: str
    direction: TradeDirection
    opened_at: datetime
    closed_at: Optional[datetime]
    open_price: float
    close_price: Optional[float]
    units: float
    profit_loss: Optional[float]
    profit_loss_r: Optional[float]
    strategy_id: str
    regime: Optional[MarketRegime]
    metadata: Dict[str, Any]


@dataclass
class FinalDecision:
    decision_id: str
    instrument: str
    timeframe: str
    verdict: DecisionVerdict
    direction: Optional[TradeDirection]
    entry_type: str
    entry_price: float
    sl_price: float
    tp_price: float
    rr: float
    confidence: float
    strategy_id: str
    regime: Optional[MarketRegime]
    expectancy_r: float
    tradingview_link: str
    explanation_text: str
    metadata: Dict[str, Any]


@dataclass
class UserDecisionRecord:
    decision_id: str
    action: UserActionType
    timestamp: datetime
    chat_id: str
    message_id: Optional[int]
    note: Optional[str]


@dataclass
class Event:
    type: EventType
    payload: Any
    timestamp: datetime
