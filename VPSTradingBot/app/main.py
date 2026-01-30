import asyncio
import logging

from app.config import Config
from app.core.event_bus import EventBus
from app.data.data_engine import DataEngine
from app.data.news_client import NewsClient
from app.execution.portfolio_manager import PortfolioManager
from app.execution.oanda_execution import ExecutionEngine
from app.explainability.engine import ExplainabilityEngine
from app.learning.engine import LearningEngine
from app.logging_system.logging_setup import setup_logging
from app.logging_system.trade_logger import TradeLogger
from app.journaling.decision_logger import DecisionLogger
from app.strategy.engine import StrategyEngine
from app.strategy.momentum_breakout import MomentumBreakoutStrategy
from app.strategy.range_reversion import RangeReversionStrategy
from app.strategy.trend_following import TrendFollowingStrategy
from app.telegram_bot.bot import TelegramBot
from app.diagnostics import ConnectivityTester


async def run_loop() -> None:
    """
    Main asynchronous loop for the trading system.
    
    Initializes:
    - Configuration and Logging
    - Event Bus
    - Data Engine & News Client
    - Strategy Engine & Strategies
    - Telegram Bot
    
    Runs concurrent tasks:
    - Telegram Bot polling
    - Market Data loop
    - News updates
    - Startup checks
    """
    config = Config.from_env()
    setup_logging()
    log = logging.getLogger("main")
    log.info(
        "Starting trading system (Continuous Mode) mode=%s data_source=%s instruments=%d timeframe=%s poll_interval=%.0fs",
        config.mode,
        getattr(config, "data_source", "unknown"),
        len(getattr(config, "instruments", [])),
        config.timeframe,
        config.data_poll_interval_seconds,
    )
    
    event_bus = EventBus()
    # Bus task must run in background
    bus_task = asyncio.create_task(event_bus.run())
    
    news_client = NewsClient(event_bus)
    
    data_engine = DataEngine(config, event_bus, news_client)
    trade_logger = TradeLogger()
    
    if config.mode != "signal_only":
        execution_engine = ExecutionEngine(config, event_bus, trade_logger)
        
    strategies = [
        TrendFollowingStrategy(),
        RangeReversionStrategy(),
        MomentumBreakoutStrategy(),
    ]
    
    explain_engine = ExplainabilityEngine()
    learning_engine = LearningEngine()
    learning_engine.refresh()
    
    # Shared RiskGuard instance
    risk_guard = RiskGuard(config)
    
    StrategyEngine(config, event_bus, strategies, explain_engine, learning_engine, news_client, risk_guard)
    DecisionLogger(event_bus, trade_logger)
    PortfolioManager(config, event_bus, trade_logger)
    telegram_bot = TelegramBot(config, event_bus, news_client, risk_guard)
    
    # Task 1: Telegram Bot (Long running)
    telegram_task = asyncio.create_task(telegram_bot.run())
    
    # Task 2: News Client (Background monitoring)
    news_task = asyncio.create_task(news_client.start())
    
    # Task 3: Market Data Loop
    async def market_loop():
        log.info("Market loop started")
        while True:
            try:
                log.info("Running market scan...")
                await data_engine.run_once()
                log.info("Market scan finished. Waiting %.0fs", config.data_poll_interval_seconds)
            except Exception as e:
                log.error("Error in market loop: %s", e, exc_info=True)
            
            await asyncio.sleep(config.data_poll_interval_seconds)

    market_task = asyncio.create_task(market_loop())
    
    # Task 4: Startup Connectivity Check
    async def run_startup_checks() -> None:
        await asyncio.sleep(5)  # Allow other services to stabilize
        log.info("Running startup connectivity checks...")
        try:
            report = await ConnectivityTester.run_startup_check()
            await telegram_bot.send_message(report)
            log.info("Startup connectivity report sent.")
        except Exception as e:
            log.error("Failed to run startup checks: %s", e)

    startup_task = asyncio.create_task(run_startup_checks())

    try:
        await asyncio.gather(telegram_task, market_task, startup_task)
    except asyncio.CancelledError:
        log.info("Tasks cancelled")
    finally:
        telegram_task.cancel()
        news_task.cancel()
        market_task.cancel()
        startup_task.cancel()
        bus_task.cancel()
        log.info("System shutdown complete")


def main() -> None:
    try:
        asyncio.run(run_loop())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
