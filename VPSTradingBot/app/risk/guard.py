from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Dict

from app.config import Config, Paths


class RiskGuard:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._current_date = date.today()
        self._trades_total_for_day = 0
        self._trades_per_instrument_for_day: Dict[str, int] = defaultdict(int)
        
        # Try to restore state on init
        self.restore_state_from_files()

    def _ensure_today(self) -> None:
        today = date.today()
        if today != self._current_date:
            self._current_date = today
            self._trades_total_for_day = 0
            self._trades_per_instrument_for_day.clear()

    def restore_state_from_files(self) -> None:
        """Restores trade counts from today's log file."""
        self._ensure_today()
        date_str = self._current_date.strftime("%Y-%m-%d")
        file_path = Paths.TRADES_DIR / f"{date_str}_trades.json"
        
        if not file_path.exists():
            return
            
        try:
            content = file_path.read_text(encoding="utf-8")
            if not content.strip():
                return
            trades = json.loads(content)
            
            count = 0
            per_instrument = defaultdict(int)
            
            for t in trades:
                # Count only opened trades (or all? Usually we limit entries)
                # Assuming the file contains one record per trade.
                # If we have 'direction' it's a trade.
                inst = t.get("instrument")
                if inst:
                    count += 1
                    per_instrument[inst] += 1
            
            self._trades_total_for_day = count
            self._trades_per_instrument_for_day.update(per_instrument)
            
        except Exception:
            pass # Fail silently, start from 0 is better than crash

    def can_open_trade(self, instrument: str) -> bool:
        self._ensure_today()
        if self._trades_total_for_day >= self._config.max_trades_per_day:
            return False
        if self._trades_per_instrument_for_day[instrument] >= self._config.max_trades_per_instrument_per_day:
            return False
        return True

    def register_trade(self, instrument: str) -> None:
        self._ensure_today()
        self._trades_total_for_day += 1
        self._trades_per_instrument_for_day[instrument] += 1

