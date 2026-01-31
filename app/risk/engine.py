from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.config import Config
from app.core.models import OrderRequest, StrategySignal, TradeDirection


@dataclass
class PositionSizingInput:
    signal: StrategySignal
    account_balance: float
    stop_loss_price: Optional[float]


class RiskEngine:
    def __init__(self, config: Config) -> None:
        self._config = config

    def calculate_units(self, sizing_input: PositionSizingInput, risk_percent_override: Optional[float] = None) -> float:
        risk_pct = risk_percent_override if risk_percent_override is not None else self._config.risk_per_trade_percent
        risk_fraction = risk_pct / 100.0
        balance = max(sizing_input.account_balance, 1000.0)
        max_loss_amount = balance * risk_fraction
        signal = sizing_input.signal
        if sizing_input.stop_loss_price is None:
            units = max_loss_amount * 10
            return float(int(units))
        price = signal.stop_loss_price
        entry_price = None
        if signal.signal_type.name == "BUY":
            direction = TradeDirection.LONG
        else:
            direction = TradeDirection.SHORT
        direction_sign = 1 if direction == TradeDirection.LONG else -1
        if direction_sign > 0:
            entry_price = sizing_input.stop_loss_price + 0.001
        else:
            entry_price = sizing_input.stop_loss_price - 0.001
        price_distance = abs(entry_price - sizing_input.stop_loss_price)
        if price_distance <= 0:
            units = max_loss_amount * 10
            return float(int(units))
        units = max_loss_amount / price_distance
        return float(int(units))

