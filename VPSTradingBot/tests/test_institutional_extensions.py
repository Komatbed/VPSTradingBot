import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import asyncio
import json
from datetime import datetime

# Import modules to test
from app.analysis.market_regime import MarketRegimeEngine, MarketRegimeType
from app.portfolio.context import PortfolioContextManager
from app.risk.equity_guard import EquityGuard
from app.ml.explainability import ExplainabilityEngine
from app.execution.portfolio_manager import PortfolioManager
from app.core.models import FinalDecision, TradeDirection, DecisionVerdict, Event, EventType
from app.core.event_bus import EventBus
from app.config import Config

class TestInstitutionalExtensions(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mock_config = MagicMock(spec=Config)
        self.mock_event_bus = MagicMock(spec=EventBus)

    # --- Market Regime Engine Tests ---
    def test_market_regime_trending(self):
        engine = MarketRegimeEngine(yahoo_client=MagicMock())
        
        # Create synthetic trending data
        dates = pd.date_range(start='2023-01-01', periods=100, freq='H')
        df = pd.DataFrame({
            'Open': np.linspace(100, 150, 100),
            'High': np.linspace(101, 151, 100),
            'Low': np.linspace(99, 149, 100),
            'Close': np.linspace(100, 150, 100),
            'Volume': np.random.randint(1000, 5000, 100)
        }, index=dates)
        
        analysis = engine.analyze_regime(df, "TEST")
        # With a strong linear upward trend, it should be TRENDING
        self.assertEqual(analysis.regime, MarketRegimeType.TRENDING)

    def test_market_regime_insufficient_data(self):
        engine = MarketRegimeEngine(yahoo_client=MagicMock())
        df = pd.DataFrame() # Empty
        analysis = engine.analyze_regime(df, "TEST")
        self.assertEqual(analysis.regime, MarketRegimeType.UNCERTAIN)

    # --- Portfolio Context Tests ---
    @patch('app.portfolio.context.Paths')
    def test_portfolio_context_duplication(self, mock_paths):
        # Mock file operations
        mock_paths.ACTIVE_TRADES.exists.return_value = True
        mock_paths.ACTIVE_TRADES.read_text.return_value = json.dumps([
            {"symbol": "EURUSD", "direction": "BUY"}
        ])
        
        manager = PortfolioContextManager(self.mock_config)
        
        result = manager.check_new_signal("EURUSD")
        self.assertFalse(result["allowed"])
        self.assertIn("ALREADY_OPEN", result["flags"])

    @patch('app.portfolio.context.Paths')
    def test_portfolio_context_currency_exposure(self, mock_paths):
        mock_paths.ACTIVE_TRADES.exists.return_value = True
        # Create 3 trades involving USD (e.g. 3 x EURUSD) or mix
        mock_paths.ACTIVE_TRADES.read_text.return_value = json.dumps([
            {"symbol": "EURUSD", "direction": "BUY"},
            {"symbol": "GBPUSD", "direction": "BUY"},
            {"symbol": "USDJPY", "direction": "BUY"}
        ])
        
        manager = PortfolioContextManager(self.mock_config)
        
        result = manager.check_new_signal("AUDUSD")
        # Should be allowed but with penalty
        self.assertTrue(result["allowed"])
        self.assertIn("HIGH_USD_EXPOSURE", result["flags"])
        self.assertGreater(result["risk_penalty"], 0)

    # --- Equity Guard Tests ---
    def test_equity_guard_streak(self):
        mock_gamification = MagicMock()
        guard = EquityGuard(self.mock_config, mock_gamification)
        
        # Simulate losing streak
        mock_profile = MagicMock()
        mock_profile.current_streak = -4
        mock_gamification.get_profile.return_value = mock_profile
        
        adj = guard.get_risk_adjustment("12345")
        self.assertEqual(adj["multiplier"], 0.5)
        self.assertIn("Cool-down", adj["reason"])

    # --- Explainability Engine Tests ---
    def test_explainability(self):
        engine = ExplainabilityEngine()
        
        # Case 1: High Score + Good RSI
        features = {"rsi": 55, "atr_percent": 0.1, "regime_val": 1}
        explanations = engine.explain_score(85.0, features)
        
        self.assertTrue(any("RSI" in e for e in explanations))
        self.assertTrue(any("Zgodność z trendem" in e for e in explanations))

    # --- Explicit No-Trade Feedback Tests ---
    @patch('app.execution.portfolio_manager.Paths')
    async def test_no_trade_feedback(self, mock_paths):
        # Setup PortfolioManager
        mock_paths.ACTIVE_TRADES.exists.return_value = False
        mock_logger = MagicMock()
        
        manager = PortfolioManager(self.mock_config, self.mock_event_bus, mock_logger)
        
        # Create a NO_TRADE decision
        decision = FinalDecision(
            decision_id="test_id",
            strategy_id="test_strat",
            instrument="EURUSD",
            timeframe="H1",
            verdict=DecisionVerdict.NO_TRADE,
            direction=None,
            entry_type="MARKET",
            entry_price=0.0,
            sl_price=0.0,
            tp_price=0.0,
            rr=0.0,
            confidence=0.0,
            regime=None,
            expectancy_r=0.0,
            tradingview_link="",
            explanation_text="Market Regime Filter",
            metadata={}
        )
        # Inject reason attribute as expected by PortfolioManager logic
        decision.reason = "Market Regime Filter"
        
        # Trigger event handling
        event = Event(type=EventType.DECISION_READY, payload=decision, timestamp=datetime.now())
        await manager._on_decision_ready(event)
        
        # Verify logger was called with explicit feedback
        # We look for the log call in the mock_logger or internal logger?
        # The PortfolioManager uses logging.getLogger("portfolio"). 
        # Since we mocked trade_logger passed in init, but the log message is via self._log.
        # However, _handle_notrade_feedback uses self._log.info.
        # We should patch the logger class or verify logic side effects.
        # But wait, `manager._log` is created in `__init__`.
        # We can inspect `manager._log`.
        
        with patch.object(manager, '_log') as mock_internal_log:
            await manager._on_decision_ready(event)
            mock_internal_log.info.assert_called()
            # Check if one of the calls contains "Explicit NO-TRADE feedback"
            found = False
            for call in mock_internal_log.info.call_args_list:
                if "Explicit NO-TRADE feedback" in call[0][0]:
                    found = True
                    break
            self.assertTrue(found, "Did not find explicit no-trade feedback log")

if __name__ == '__main__':
    unittest.main()
