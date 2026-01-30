import json
import logging
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from pathlib import Path
from app.config import Paths

@dataclass
class PortfolioContext:
    total_exposure_usd: float = 0.0
    active_positions_count: int = 0
    currency_exposure: Dict[str, float] = field(default_factory=dict) # e.g. "USD": 2.5 (lots) or value
    sector_exposure: Dict[str, float] = field(default_factory=dict)   # e.g. "TECH": 10000.0
    active_symbols: Set[str] = field(default_factory=set)

class PortfolioContextManager:
    """
    Tracks the current state of the portfolio to prevent overexposure and correlation clustering.
    Subscribes to EventBus to update state on trade execution.
    """
    def __init__(self, config):
        self._config = config
        self._log = logging.getLogger("portfolio_context")
        self._context = PortfolioContext()
        self._active_trades_path = Paths.ACTIVE_TRADES
        self._reload_context()

    def _reload_context(self):
        """Re-reads active trades from disk and rebuilds context."""
        if not self._active_trades_path.exists():
            self._context = PortfolioContext()
            return

        try:
            content = self._active_trades_path.read_text(encoding="utf-8")
            if not content.strip():
                self._context = PortfolioContext()
                return

            trades = json.loads(content)
            self._rebuild_from_trades(trades)
        except Exception as e:
            self._log.error(f"Failed to reload portfolio context: {e}")
            self._context = PortfolioContext()

    def _rebuild_from_trades(self, trades: List[Dict]):
        ctx = PortfolioContext()
        ctx.active_positions_count = len(trades)
        
        for t in trades:
            symbol = t.get("symbol", "").upper()
            ctx.active_symbols.add(symbol)
            
            # Simplified currency exposure parsing (e.g. EURUSD -> EUR + USD)
            # Ideally this would use instrument metadata
            if len(symbol) == 6: # Forex assumption
                base = symbol[:3]
                quote = symbol[3:]
                # We just mark presence for now, volume calculation requires lot size standardization
                ctx.currency_exposure[base] = ctx.currency_exposure.get(base, 0) + 1
                ctx.currency_exposure[quote] = ctx.currency_exposure.get(quote, 0) + 1
            
            # TODO: Sector mapping
            
        self._context = ctx

    def check_new_signal(self, symbol: str) -> Dict[str, Any]:
        """
        Evaluates a potential new trade against current portfolio context.
        Returns: { "allowed": bool, "risk_penalty": int, "flags": List[str] }
        """
        self._reload_context() # Ensure fresh data
        
        flags = []
        risk_penalty = 0
        allowed = True
        
        # 1. Symbol Duplication
        if symbol in self._context.active_symbols:
            allowed = False
            flags.append("ALREADY_OPEN")
            return {"allowed": False, "risk_penalty": 100, "flags": flags, "reason": "Position already exists"}

        # 2. Currency Overexposure (Example: Max 3 positions involving USD)
        base = symbol[:3]
        quote = symbol[3:] if len(symbol) == 6 else ""
        
        if self._context.currency_exposure.get(base, 0) >= 3:
            risk_penalty += 30
            flags.append(f"HIGH_{base}_EXPOSURE")
        
        if quote and self._context.currency_exposure.get(quote, 0) >= 3:
            risk_penalty += 30
            flags.append(f"HIGH_{quote}_EXPOSURE")

        # 3. Max Total Positions
        if self._context.active_positions_count >= 10: # Hard limit
            allowed = False
            flags.append("MAX_POSITIONS_REACHED")
            
        return {
            "allowed": allowed,
            "risk_penalty": risk_penalty,
            "flags": flags,
            "reason": "Portfolio context check complete"
        }
