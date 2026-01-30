import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from app.config import Config
from app.core.event_bus import EventBus
from app.core.models import Event, EventType, FinalDecision, DecisionVerdict, TradeDirection, MarketRegime, UserDecisionRecord, UserActionType
from app.execution.portfolio_manager import PortfolioManager

class TestSystemIntegration(unittest.IsolatedAsyncioTestCase):
    """
    Integration tests simulating the interaction between components:
    Strategy -> EventBus -> PortfolioManager -> (Context/Risk) -> Execution
    """

    def setUp(self):
        self.config = Config(
            environment="test",
            mode="backtest",
            telegram_bot_token="test_token",
            telegram_chat_id="test_chat",
            data_source="synthetic",
            instruments=["EURUSD"],
            timeframe="H1",
            data_poll_interval_seconds=60,
            base_currency="USD",
            risk_per_trade_percent=1.0,
            max_trades_per_day=5,
            max_trades_per_instrument_per_day=1,
            ml_base_url="http://localhost:8000",
            educational_mode=False
        )
        self.event_bus = EventBus()
        self.logger = MagicMock()
        
        # Patching Paths inside PortfolioManager dependencies to avoid file I/O
        self.patcher_paths = patch('app.portfolio.context.Paths')
        self.mock_paths = self.patcher_paths.start()
        self.mock_paths.ACTIVE_TRADES.exists.return_value = True
        self.mock_paths.ACTIVE_TRADES.read_text.return_value = "[]"
        
        # Initialize System Components
        self.portfolio_manager = PortfolioManager(self.config, self.event_bus, self.logger)

    def tearDown(self):
        self.patcher_paths.stop()

    async def test_full_signal_processing_flow(self):
        """
        Simulate a Strategy generating a BUY signal, and verify PortfolioManager processes it
        and (mock) executes it.
        """
        # 1. Create a Decision (Simulating Strategy Output)
        decision = FinalDecision(
            decision_id="integration_test_001",
            strategy_id="trend_follower",
            instrument="EURUSD",
            timeframe="H1",
            verdict=DecisionVerdict.BUY,
            direction=TradeDirection.LONG,
            entry_type="MARKET",
            entry_price=1.1050,
            sl_price=1.1000,
            tp_price=1.1150,
            rr=2.0,
            confidence=0.85,
            regime=MarketRegime.TREND,
            expectancy_r=0.6,
            tradingview_link="http://test.com",
            explanation_text="Integration Test Signal",
            metadata={}
        )

        # 2. Publish Event (Simulating Event Loop)
        event = Event(
            type=EventType.DECISION_READY, 
            payload=decision, 
            timestamp=datetime.now()
        )
        
        # 3. Trigger decision ready (caches it)
        await self.portfolio_manager._on_decision_ready(event)
        
        # Verification 1: Check if the decision was cached
        self.assertIn("integration_test_001", self.portfolio_manager._decisions_cache)
        
        # 4. Simulate User Clicking "ENTER"
        user_decision = UserDecisionRecord(
            decision_id="integration_test_001",
            action=UserActionType.ENTER,
            timestamp=datetime.now(),
            chat_id="test_chat",
            message_id=123,
            note="Approving integration test trade"
        )
        
        event_user = Event(
            type=EventType.USER_DECISION,
            payload=user_decision,
            timestamp=datetime.now()
        )
        
        # Patch the internal logger of portfolio_manager to verify logs
        with patch.object(self.portfolio_manager, '_log') as mock_log:
            await self.portfolio_manager._on_user_decision(event_user)
            
            # Verification 2: Check logs for position opening
            log_calls = [call[0][0] for call in mock_log.info.call_args_list]
            self.assertTrue(any("Opened VIRTUAL position" in str(msg) for msg in log_calls), "Logger should indicate position opened")
            self.assertTrue(any("EURUSD" in str(msg) for msg in log_calls), "Logger should mention EURUSD")

    async def test_blocked_signal_flow(self):
        """
        Simulate a Strategy generating a NO_TRADE signal (e.g. filtered by Market Regime),
        and verify PortfolioManager records it as feedback.
        """
        # 1. Create a Decision with NO_TRADE
        decision = FinalDecision(
            decision_id="integration_test_blocked_001",
            strategy_id="trend_follower",
            instrument="GBPUSD",
            timeframe="H1",
            verdict=DecisionVerdict.NO_TRADE,
            direction=None,
            entry_type="MARKET",
            entry_price=0.0,
            sl_price=0.0,
            tp_price=0.0,
            rr=0.0,
            confidence=0.0,
            regime=MarketRegime.RANGE,
            expectancy_r=0.0,
            tradingview_link="",
            explanation_text="Market is ranging, filter applied",
            metadata={}
        )
        # Inject reason as it is expected by PortfolioManager logic (often added dynamically)
        decision.reason = "Market Regime Filter: RANGING"

        # 2. Publish Event
        event = Event(
            type=EventType.DECISION_READY, 
            payload=decision, 
            timestamp=datetime.now()
        )
        
        # 3. Verify Feedback Logging
        with patch.object(self.portfolio_manager, '_log') as mock_log:
            await self.portfolio_manager._on_decision_ready(event)
            
            # Verification: Check logs for feedback
            log_calls = [call[0][0] for call in mock_log.info.call_args_list]
            self.assertTrue(any("Explicit NO-TRADE feedback" in str(msg) for msg in log_calls), "Logger should indicate NO-TRADE feedback")
            self.assertTrue(any("GBPUSD" in str(msg) for msg in log_calls), "Logger should mention GBPUSD")

if __name__ == "__main__":
    unittest.main()
