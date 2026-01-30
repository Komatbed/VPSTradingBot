import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List

from app.core.models import TradeRecord
from app.config import Paths


class TradeLogger:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    def _file_path(self) -> Path:
        trades_dir = Paths.TRADES_DIR
        trades_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        return trades_dir / f"{date_str}_trades.json"

    async def log_trade(self, trade: TradeRecord) -> None:
        path = self._file_path()
        async with self._lock:
            records: List[dict]
            if path.exists():
                content = path.read_text(encoding="utf-8")
                if content.strip():
                    records = json.loads(content)
                else:
                    records = []
            else:
                records = []
            record = {
                "trade_id": trade.trade_id,
                "instrument": trade.instrument,
                "direction": trade.direction.value,
                "opened_at": trade.opened_at.isoformat(),
                "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
                "open_price": trade.open_price,
                "close_price": trade.close_price,
                "units": trade.units,
                "profit_loss": trade.profit_loss,
                "profit_loss_r": trade.profit_loss_r,
                "strategy_id": trade.strategy_id,
                "regime": trade.regime.value if trade.regime else None,
                "metadata": trade.metadata,
            }
            records.append(record)
            path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

