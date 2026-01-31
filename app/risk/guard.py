from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, Tuple

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

    def get_dynamic_risk_profile(self) -> Dict[str, float]:
        """
        Calculates risk parameters based on the Aggressiveness Level (1-10).
        
        Aggressiveness (A):
        - A=1 (Cykor): Low risk (0.5%), High R:R req (2.5), Few trades
        - A=10 (Wariat): High risk (3.0%), Low R:R req (1.0), Many trades
        """
        a = self._config.aggressiveness
        # Clamp between 1 and 10
        a = max(1, min(10, a))
        
        # 1. Risk Per Trade (%)
        # Level 1: 0.5%, Level 5: 1.0%, Level 10: 2.5%
        # Formula: 0.5 + (a-1) * 0.22 (approx)
        # Let's simplify: 0.5, 0.7, 0.9, 1.1, 1.3, 1.5, ...
        risk_pct = 0.5 + (a - 1) * 0.25
        
        # 2. Max Trades Per Day (Global)
        # Base config is safety net, but this tightens it
        # Level 1: 3 trades, Level 10: 20 trades
        max_trades = 3 + (a * 2)
        
        # 3. Min R:R
        # Level 1: 2.5, Level 10: 1.0
        min_rr = max(1.0, 2.5 - ((a - 1) * 0.15))
        
        return {
            "risk_per_trade_percent": round(risk_pct, 2),
            "max_trades_per_day": int(max_trades),
            "min_rr": round(min_rr, 2)
        }

    def can_open_trade(self, instrument: str) -> Tuple[bool, str]:
        # If RiskGuard is disabled via config, allow all trades
        if not self._config.risk_guard_enabled:
            return True, "RiskGuard Disabled"

        self._ensure_today()
        
        # 1. Global Daily Limit
        # Get dynamic limit if applicable
        profile = self.get_dynamic_risk_profile()
        dynamic_max_trades = profile["max_trades_per_day"]
        
        # Use stricter of the two (Config vs Dynamic) - usually Dynamic is derived from config but let's be safe
        # Actually, let's just use the dynamic one as it respects aggressiveness
        limit_global = min(self._config.max_trades_per_day, dynamic_max_trades)
        
        if self._trades_total_for_day >= limit_global:
            return False, f"Daily Limit Reached ({self._trades_total_for_day}/{limit_global})"
            
        # 2. Per-Instrument Daily Limit
        if self._trades_per_instrument_for_day[instrument] >= self._config.max_trades_per_instrument_per_day:
            return False, f"Instrument Limit Reached ({self._trades_per_instrument_for_day[instrument]}/{self._config.max_trades_per_instrument_per_day})"
            
        return True, "OK"

    def register_trade(self, instrument: str) -> None:
        self._ensure_today()
        self._trades_total_for_day += 1
        self._trades_per_instrument_for_day[instrument] += 1
