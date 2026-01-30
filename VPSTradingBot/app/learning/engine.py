from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from app.core.models import MarketRegime


@dataclass
class ExpectancyStats:
    count: int
    sum_r: float


class LearningEngine:
    def __init__(self) -> None:
        self._stats: Dict[Tuple[str, str, Optional[str]], ExpectancyStats] = {}

    def refresh(self) -> None:
        self._stats.clear()
        self._load_from_dir(Path("trades"), "profit_loss_r")
        self._load_from_dir(Path("backtests"), "r")

    def _load_from_dir(self, directory: Path, r_key: str) -> None:
        if not directory.exists():
            return
        for path in directory.glob("*.json"):
            content = path.read_text(encoding="utf-8").strip()
            if not content:
                continue
            try:
                records = json.loads(content)
            except Exception:
                continue
            for record in records:
                r = record.get(r_key)
                if r is None:
                    continue
                strategy_id = record.get("strategy_id", "")
                instrument = record.get("instrument", "")
                regime = record.get("regime")
                
                # Normalize regime key if needed (backtests might save string)
                if isinstance(regime, dict): # Should not happen based on json
                    pass
                
                key = (strategy_id, instrument, regime)
                stats = self._stats.get(key)
                if stats is None:
                    self._stats[key] = ExpectancyStats(count=1, sum_r=float(r))
                else:
                    stats.count += 1
                    stats.sum_r += float(r)

    def get_expectancy(
        self,
        strategy_id: str,
        instrument: str,
        regime: Optional[MarketRegime],
    ) -> float:
        regime_key = regime.value if regime else None
        key = (strategy_id, instrument, regime_key)
        stats = self._stats.get(key)
        if not stats or stats.count == 0:
            return 0.42
        return stats.sum_r / stats.count

