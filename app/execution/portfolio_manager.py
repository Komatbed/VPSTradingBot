from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional

from app.config import Config, Paths
from app.core.event_bus import EventBus
from app.core.models import (
    Event,
    EventType,
    TradeDirection,
    UserActionType,
    UserDecisionRecord,
    FinalDecision,
    MarketDataSnapshot,
    TradeRecord,
    OrderResult,
    OrderStatus
)
from app.logging_system.trade_logger import TradeLogger


@dataclass
class ActivePosition:
    trade_id: str
    instrument: str
    direction: TradeDirection
    entry_price: float
    sl: float
    tp: float
    units: float
    opened_at: datetime
    strategy_id: str
    current_profit_r: float = 0.0
    current_price: float = 0.0
    explanation_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> dict:
        return {
            "trade_id": self.trade_id,
            "instrument": self.instrument,
            "direction": self.direction.value,
            "entry_price": self.entry_price,
            "sl": self.sl,
            "tp": self.tp,
            "units": self.units,
            "opened_at": self.opened_at.isoformat(),
            "strategy_id": self.strategy_id,
            "current_profit_r": self.current_profit_r,
            "explanation_data": self.explanation_data,
            "current_price": self.current_price,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> ActivePosition:
        return cls(
            trade_id=data["trade_id"],
            instrument=data["instrument"],
            direction=TradeDirection(data["direction"]),
            entry_price=data["entry_price"],
            sl=data["sl"],
            tp=data["tp"],
            units=data["units"],
            opened_at=datetime.fromisoformat(data["opened_at"]),
            strategy_id=data["strategy_id"],
            current_profit_r=data.get("current_profit_r", 0.0),
            current_price=data.get("current_price", 0.0),
        )


class PortfolioManager:
    """
    Manages active positions in a 'Virtual Broker' mode.
    - Opens positions based on User Decision (ENTER).
    - Monitors prices against SL/TP.
    - Closes positions and logs them to TradeLogger.
    """
    
    def __init__(self, config: Config, event_bus: EventBus, trade_logger: TradeLogger) -> None:
        self._config = config
        self._event_bus = event_bus
        self._trade_logger = trade_logger
        self._log = logging.getLogger("portfolio")
        self._positions: Dict[str, ActivePosition] = {}
        self._decisions_cache: Dict[str, FinalDecision] = {} # Cache decisions to hydrate trades
        
        # Subscriptions
        self._event_bus.subscribe(EventType.DECISION_READY, self._on_decision_ready)
        self._event_bus.subscribe(EventType.USER_DECISION, self._on_user_decision)
        self._event_bus.subscribe(EventType.MARKET_DATA, self._on_market_data)
        self._event_bus.subscribe(EventType.MANUAL_CLOSE_REQUEST, self._on_manual_close_request)
        
        self._load_positions()

    def _load_positions(self) -> None:
        """Loads active positions from JSON file."""
        if not Paths.ACTIVE_TRADES.exists():
            return
            
        try:
            content = Paths.ACTIVE_TRADES.read_text(encoding="utf-8")
            if not content.strip():
                return
                
            data = json.loads(content)
            for item in data:
                try:
                    pos = ActivePosition.from_dict(item)
                    self._positions[pos.trade_id] = pos
                except Exception as e:
                    self._log.error(f"Failed to parse position {item}: {e}")
            
            self._log.info(f"Loaded {len(self._positions)} active positions.")
        except Exception as e:
            self._log.error(f"Error loading active trades: {e}")

    def _save_positions(self) -> None:
        """Saves active positions to JSON file."""
        try:
            data = [p.to_dict() for p in self._positions.values()]
            Paths.ACTIVE_TRADES.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            self._log.error(f"Error saving active trades: {e}")

    def _handle_notrade_feedback(self, decision: FinalDecision, reason: str) -> None:
        """
        Records a NO-TRADE decision as explicit feedback.
        Used for ML negative sampling and user statistics.
        """
        self._log.info(f"Explicit NO-TRADE feedback: {decision.instrument} -> {reason}")
        # TODO: Persist this to a 'rejected_signals.json' for ML training

    async def _on_decision_ready(self, event: Event) -> None:
        """Caches FinalDecision to have details when user clicks ENTER."""
        decision: FinalDecision = event.payload
        self._decisions_cache[decision.decision_id] = decision
        
        # Check if it's a NO_TRADE from the start
        if hasattr(decision, 'verdict') and decision.verdict.value == "no_trade":
            self._handle_notrade_feedback(decision, getattr(decision, 'reason', 'No Trade Verdict'))

    async def _on_manual_close_request(self, event: Event) -> None:
        """Handles manual close request from Telegram/Admin."""
        payload = event.payload
        trade_id = payload.get("trade_id")
        
        if not trade_id or trade_id not in self._positions:
            self._log.warning(f"Manual close requested for unknown trade: {trade_id}")
            return
            
        position = self._positions[trade_id]
        # Use current price if available, else entry (fallback)
        close_price = position.current_price if position.current_price > 0 else position.entry_price
        
        await self._close_position(position, close_price, reason="MANUAL_USER")
        self._log.info(f"Manually closed trade {trade_id} via request.")

    async def _on_user_decision(self, event: Event) -> None:
        """Handles user clicking 'ENTER' -> Opens a Virtual Position."""
        record: UserDecisionRecord = event.payload
        decision = self._decisions_cache.get(record.decision_id)
        
        if not decision:
            self._log.warning(f"Received user decision for unknown ID: {record.decision_id}")
            return

        if record.action == UserActionType.SKIP:
            self._handle_notrade_feedback(decision, "User Skipped")
            return
        
        if record.action == UserActionType.ENTER:
            if not decision.direction:
                 self._log.warning(f"User accepted decision {record.decision_id}, but direction is None.")
                 return

            # Create new position
            # Note: In real world, we would get current price. Here we use decision.entry_price or close
            # Ideally, we should fetch latest price, but for now we trust the decision snapshot or waiting for next tick.
            # We use decision entry price as reference.
            
            position = ActivePosition(
                trade_id=decision.decision_id,
                instrument=decision.instrument,
                direction=decision.direction,
                entry_price=decision.entry_price,
                sl=decision.sl_price,
                tp=decision.tp_price,
                units=1000.0, # Default lots logic to be improved later
                opened_at=datetime.utcnow(),
                strategy_id=decision.strategy_id,
                explanation_data=decision.metadata # Store full metadata including scores
            )
            
            self._positions[position.trade_id] = position
            self._save_positions()
            self._log.info(f"Opened VIRTUAL position: {position.instrument} {position.direction.value} @ {position.entry_price}")

            # Emit ORDER_FILLED event so RiskGuard and other components can update
            order_result = OrderResult(
                order_id=f"virtual_{position.trade_id}",
                status=OrderStatus.FILLED,
                instrument=position.instrument,
                units=position.units,
                direction=position.direction,
                price=position.entry_price,
                executed_at=position.opened_at,
                rejection_reason=None,
                strategy_id=position.strategy_id,
                confidence=decision.confidence
            )
            await self._event_bus.publish(
                Event(
                    type=EventType.ORDER_FILLED,
                    payload=order_result,
                    timestamp=datetime.utcnow()
                )
            )

    async def _on_market_data(self, event: Event) -> None:
        """
        The Core Logic: Checks SL/TP for all active positions against incoming market data.
        """
        snapshot: MarketDataSnapshot = event.payload
        instrument = snapshot.instrument
        
        # Filter positions for this instrument
        active_for_instrument = [p for p in self._positions.values() if p.instrument == instrument]
        
        if not active_for_instrument:
            return
            
        if not snapshot.candles:
            return
            
        # Use the latest candle close as 'current price' for simulation
        # In higher frequency, we would use bid/ask.
        current_price = snapshot.candles[-1].close
        
        for position in active_for_instrument:
            position.current_price = current_price
            
            # Calculate R-Multiple
            dist_sl = abs(position.entry_price - position.sl)
            if dist_sl == 0:
                r_value = 0.0
            else:
                if position.direction == TradeDirection.LONG:
                    raw_profit = current_price - position.entry_price
                else:
                    raw_profit = position.entry_price - current_price
                r_value = raw_profit / dist_sl
            
            position.current_profit_r = round(r_value, 2)
            
            # CHECK SL/TP LOGIC
            close_reason = None
            
            if position.direction == TradeDirection.LONG:
                if current_price >= position.tp:
                    close_reason = "TP_HIT"
                elif current_price <= position.sl:
                    close_reason = "SL_HIT"
            elif position.direction == TradeDirection.SHORT:
                if current_price <= position.tp:
                    close_reason = "TP_HIT"
                elif current_price >= position.sl:
                    close_reason = "SL_HIT"
            
            if close_reason:
                await self._close_position(position, current_price, close_reason)
        
        # Periodic save (or only on change)
        self._save_positions()

    async def _close_position(self, position: ActivePosition, close_price: float, reason: str) -> None:
        """Closes the position and logs the trade."""
        self._log.info(f"Closing position {position.trade_id} ({reason}). Price: {close_price}")
        
        # Calculate final stats
        if position.direction == TradeDirection.LONG:
            profit_loss = (close_price - position.entry_price) * position.units
            # Simplified PnL, ignores exchange rates
        else:
            profit_loss = (position.entry_price - close_price) * position.units
            
        dist_sl = abs(position.entry_price - position.sl)
        r_value = 0.0
        if dist_sl > 0:
             if position.direction == TradeDirection.LONG:
                 r_value = (close_price - position.entry_price) / dist_sl
             else:
                 r_value = (position.entry_price - close_price) / dist_sl
        
        trade_record = TradeRecord(
            trade_id=position.trade_id,
            instrument=position.instrument,
            direction=position.direction,
            opened_at=position.opened_at,
            closed_at=datetime.utcnow(),
            open_price=position.entry_price,
            close_price=close_price,
            units=position.units,
            profit_loss=round(profit_loss, 2),
            profit_loss_r=round(r_value, 2),
            strategy_id=position.strategy_id,
            regime=None, # Could retrieve if stored
            metadata={"close_reason": reason, "source": "virtual_portfolio_manager"}
        )
        
        # Log to permanent history
        await self._trade_logger.log_trade(trade_record)
        
        # Publish completion event for Gamification/Stats
        await self._event_bus.publish(
            Event(
                type=EventType.TRADE_COMPLETED,
                payload=trade_record,
                timestamp=datetime.utcnow()
            )
        )
        
        # Remove from active
        if position.trade_id in self._positions:
            del self._positions[position.trade_id]
        
        self._save_positions()
