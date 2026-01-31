from __future__ import annotations

from datetime import datetime

from app.config import Config
from app.core.event_bus import EventBus
from app.core.models import Event, EventType, OrderRequest, OrderResult, OrderStatus, TradeDirection, TradeRecord
from app.logging_system.trade_logger import TradeLogger


class ExecutionEngine:
    def __init__(
        self,
        config: Config,
        event_bus: EventBus,
        trade_logger: TradeLogger,
    ) -> None:
        self._config = config
        self._event_bus = event_bus
        self._trade_logger = trade_logger
        self._event_bus.subscribe(EventType.ORDER_REQUEST, self._on_order_request)

    async def _on_order_request(self, event: Event) -> None:
        order_request: OrderRequest = event.payload
        await self._handle_paper_trade(order_request)

    async def _handle_paper_trade(self, order_request: OrderRequest) -> None:
        price = 1.0
        now = datetime.utcnow()
        result = OrderResult(
            order_id=f"paper_{int(now.timestamp())}",
            status=OrderStatus.FILLED,
            instrument=order_request.instrument,
            units=order_request.units,
            direction=order_request.direction,
            price=price,
            executed_at=now,
            rejection_reason=None,
            strategy_id=order_request.strategy_id,
            confidence=order_request.confidence,
        )
        await self._handle_result(result)

    async def _handle_result(self, result: OrderResult) -> None:
        if result.status == OrderStatus.FILLED:
            event_type = EventType.ORDER_FILLED
        else:
            event_type = EventType.ORDER_REJECTED
        await self._event_bus.publish(
            Event(
                type=event_type,
                payload=result,
                timestamp=datetime.utcnow(),
            )
        )
        if result.status == OrderStatus.FILLED and result.executed_at and result.price:
            direction = result.direction
            units = result.units
            trade = TradeRecord(
                trade_id=result.order_id,
                instrument=result.instrument,
                direction=direction,
                opened_at=result.executed_at,
                closed_at=None,
                open_price=result.price,
                close_price=None,
                units=units,
                profit_loss=None,
                profit_loss_r=None,
                strategy_id=result.strategy_id,
                regime=None,
                metadata={"confidence": result.confidence},
            )
            await self._trade_logger.log_trade(trade)

