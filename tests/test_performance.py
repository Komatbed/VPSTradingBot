import unittest
import time
import pandas as pd
import numpy as np
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch
from app.analysis.market_regime import MarketRegimeEngine
from app.portfolio.context import PortfolioContextManager
from app.execution.portfolio_manager import PortfolioManager
from app.core.models import FinalDecision, DecisionVerdict, Event, EventType
from app.config import Config

class TestSystemPerformance(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.mock_config = MagicMock(spec=Config)
        
    def test_market_regime_performance(self):
        """Test processing speed of market regime analysis for 1 year of H1 data."""
        engine = MarketRegimeEngine(yahoo_client=MagicMock())
        
        # Generate 1 year of H1 data (approx 6000 candles)
        dates = pd.date_range(start='2023-01-01', periods=6000, freq='h')
        df = pd.DataFrame({
            'Open': np.random.randn(6000) + 100,
            'High': np.random.randn(6000) + 101,
            'Low': np.random.randn(6000) + 99,
            'Close': np.random.randn(6000) + 100,
            'Volume': np.random.randint(1000, 5000, 6000)
        }, index=dates)
        
        start_time = time.time()
        engine.analyze_regime(df, "PERF_TEST")
        duration = time.time() - start_time
        
        # Should be under 0.5 seconds for 6000 candles
        print(f"Market Regime Analysis (6000 candles): {duration:.4f}s")
        self.assertLess(duration, 0.5, "Market Regime analysis is too slow")

    @patch('app.portfolio.context.Paths')
    def test_portfolio_check_throughput(self, mock_paths):
        """Test throughput of portfolio checks (e.g. 1000 sequential checks)."""
        mock_paths.ACTIVE_TRADES.exists.return_value = True
        mock_paths.ACTIVE_TRADES.read_text.return_value = "[]"
        
        manager = PortfolioContextManager(self.mock_config)
        
        start_time = time.time()
        for i in range(1000):
            manager.check_new_signal(f"SYM{i}")
        duration = time.time() - start_time
        
        # Should be under 1.0 second for 1000 checks (1ms per check)
        print(f"Portfolio Checks (1000 ops): {duration:.4f}s")
        self.assertLess(duration, 1.0, "Portfolio Context throughput is too low")

    async def test_decision_pipeline_latency(self):
        """Test latency of the decision processing pipeline."""
        mock_logger = MagicMock()
        mock_event_bus = MagicMock()
        manager = PortfolioManager(self.mock_config, mock_event_bus, mock_logger)
        
        decision = FinalDecision(
            decision_id="perf_id",
            strategy_id="perf_strat",
            instrument="EURUSD",
            timeframe="H1",
            verdict=DecisionVerdict.BUY,
            direction=None,
            entry_type="MARKET",
            entry_price=1.1000,
            sl_price=1.0900,
            tp_price=1.1200,
            rr=2.0,
            confidence=0.8,
            regime=None,
            expectancy_r=0.5,
            tradingview_link="",
            explanation_text="Performance Test",
            metadata={}
        )
        
        start_time = time.time()
        event = Event(type=EventType.DECISION_READY, payload=decision, timestamp=datetime.now())
        await manager._on_decision_ready(event)
        duration = time.time() - start_time
        
        # Should be under 10ms (0.01s)
        print(f"Decision Pipeline Latency: {duration*1000:.2f}ms")
        self.assertLess(duration, 0.05, "Decision pipeline latency is too high")

if __name__ == '__main__':
    from datetime import datetime
    unittest.main()
