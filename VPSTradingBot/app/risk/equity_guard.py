import logging
from typing import Dict, Any, List

class EquityGuard:
    """
    Monitors account equity and performance to adjust risk parameters dynamically.
    Implements a feedback loop: Bad Performance -> Lower Risk.
    """
    def __init__(self, config, gamification_engine):
        self._config = config
        self._gamification = gamification_engine
        self._log = logging.getLogger("equity_guard")
        
        # Thresholds
        self._max_daily_drawdown_percent = 5.0
        self._consecutive_loss_threshold = 3
        
    def get_risk_adjustment(self, chat_id: str) -> Dict[str, Any]:
        """
        Calculates risk multiplier based on recent performance.
        Returns: { "multiplier": float, "reason": str }
        """
        profile = self._gamification.get_profile(chat_id)
        
        # 1. Check Drawdown
        current_balance = getattr(profile, "balance", 10000.0)
        # Assuming we track starting balance of the day somewhere, 
        # for now simplified:
        
        # 2. Check Streak
        streak = getattr(profile, "current_streak", 0)
        
        multiplier = 1.0
        reason = "Normal risk"
        
        if streak <= -self._consecutive_loss_threshold:
            multiplier = 0.5
            reason = f"Cool-down: {abs(streak)} consecutive losses"
            
        elif streak >= 5:
            # Prevent overconfidence
            multiplier = 0.8
            reason = "Confidence check: Winning streak throttling"
            
        return {
            "multiplier": multiplier,
            "reason": reason
        }

    def check_daily_lockout(self, chat_id: str) -> bool:
        """Returns True if trading should be locked for the day."""
        # TODO: Implement daily P&L tracking
        return False
