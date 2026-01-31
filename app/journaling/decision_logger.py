from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from app.core.event_bus import EventBus
from app.core.models import Event, EventType, FinalDecision, TradeRecord, UserActionType, UserDecisionRecord
from app.logging_system.trade_logger import TradeLogger


class DecisionLogger:
    def __init__(self, event_bus: EventBus, trade_logger: TradeLogger) -> None:
        self._lock = asyncio.Lock()
        self._event_bus = event_bus
        self._trade_logger = trade_logger
        self._decisions: Dict[str, FinalDecision] = {}
        self._last_enter_for_chat: Dict[str, str] = {}
        self._event_bus.subscribe(EventType.DECISION_READY, self._on_decision)
        self._event_bus.subscribe(EventType.USER_DECISION, self._on_user_decision)
        self._event_bus.subscribe(EventType.TELEGRAM_COMMAND, self._on_telegram_command)

    def _dir(self) -> Path:
        path = Path("journal")
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def _append_line(self, path: Path, data: dict) -> None:
        async with self._lock:
            line = json.dumps(data, ensure_ascii=False)
            path.write_text(
                (path.read_text(encoding="utf-8") if path.exists() else "") + line + "\n",
                encoding="utf-8",
            )

    async def _on_decision(self, event: Event) -> None:
        decision: FinalDecision = event.payload
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        path = self._dir() / f"{date_str}_decisions.jsonl"
        data = {
            "decision_id": decision.decision_id,
            "instrument": decision.instrument,
            "timeframe": decision.timeframe,
            "verdict": decision.verdict.value,
            "direction": decision.direction.value if decision.direction else None,
            "entry_type": decision.entry_type,
            "entry_price": decision.entry_price,
            "sl_price": decision.sl_price,
            "tp_price": decision.tp_price,
            "rr": decision.rr,
            "confidence": decision.confidence,
            "strategy_id": decision.strategy_id,
            "regime": decision.regime.value if decision.regime else None,
            "expectancy_r": decision.expectancy_r,
            "tradingview_link": decision.tradingview_link,
            "explanation_text": decision.explanation_text,
            "metadata": decision.metadata,
            "timestamp": event.timestamp.isoformat(),
        }
        await self._append_line(path, data)
        self._decisions[decision.decision_id] = decision

    async def _on_user_decision(self, event: Event) -> None:
        record: UserDecisionRecord = event.payload
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        path = self._dir() / f"{date_str}_user_actions.jsonl"
        data = {
            "decision_id": record.decision_id,
            "action": record.action.value,
            "timestamp": record.timestamp.isoformat(),
            "chat_id": record.chat_id,
            "message_id": record.message_id,
            "note": record.note,
        }
        await self._append_line(path, data)
        if record.action == UserActionType.ENTER:
            self._last_enter_for_chat[record.chat_id] = record.decision_id

    async def _on_telegram_command(self, event: Event) -> None:
        command = event.payload
        if not isinstance(command, dict):
            return
        if command.get("type") != "result":
            return
        chat_id_value = command.get("chat_id")
        if chat_id_value is None:
            return
        chat_id = str(chat_id_value)
        value_r = command.get("value_r")
        if value_r is None:
            return
        try:
            r_value = float(value_r)
        except (TypeError, ValueError):
            return
        decision_id = self._last_enter_for_chat.get(chat_id)
        if not decision_id:
            return
        decision = self._decisions.get(decision_id)
        if not decision or decision.direction is None:
            return
        now = datetime.utcnow()
        trade = TradeRecord(
            trade_id=decision_id,
            instrument=decision.instrument,
            direction=decision.direction,
            opened_at=now,
            closed_at=now,
            open_price=decision.entry_price,
            close_price=None,
            units=1.0,
            profit_loss=None,
            profit_loss_r=r_value,
            strategy_id=decision.strategy_id,
            regime=decision.regime,
            metadata={
                "source": "manual_result",
                "timeframe": decision.timeframe,
                "chat_id": chat_id,
            },
        )
        await self._trade_logger.log_trade(trade)
