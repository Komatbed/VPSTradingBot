import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
import json

# Add project root to path
sys.path.append(os.getcwd())

from app.telegram_bot.bot import TelegramBot
from app.config import Config
from app.core.event_bus import EventBus
from app.core.models import Event, EventType

async def run_tests():
    print("🚀 Starting Telegram Command Tests...")
    
    # 1. Setup Mocks
    config = MagicMock() # Removed spec=Config to avoid attribute issues with dataclass
    config.telegram_bot_token = "TEST_TOKEN"
    config.telegram_chat_id = "123456"
    config.educational_mode = True
    config.instruments = ["EURUSD", "GBPUSD"]
    config.max_trades_per_day = 10
    
    event_bus = MagicMock(spec=EventBus)
    event_bus.subscribe = MagicMock()
    
    # Mock dependencies
    news_client = MagicMock()
    risk_guard = MagicMock()
    risk_guard.get_dynamic_risk_profile.return_value = {
        "aggressiveness_level": 5,
        "risk_per_trade_percent": 1.0,
        "max_trades_per_day": 5,
        "multiplier": 1.0
    }
    
    # Patch internal components initialized in __init__
    with patch('app.telegram_bot.bot.YahooFinanceClient'), \
         patch('app.telegram_bot.bot.SentimentEngine'), \
         patch('app.telegram_bot.bot.BriefingService'), \
         patch('app.telegram_bot.bot.PerformanceReportGenerator'), \
         patch('app.telegram_bot.bot.InstrumentStatsBuilder'), \
         patch('app.telegram_bot.bot.GamificationEngine'), \
         patch('app.telegram_bot.bot.MarketRegimeEngine'), \
         patch('app.telegram_bot.bot.AlertManager'), \
         patch('app.telegram_bot.bot.DiagnosticsEngine'), \
         patch('app.telegram_bot.bot.UpdateManager'), \
         patch('app.telegram_bot.bot.MlAdvisorClient'), \
         patch('app.telegram_bot.bot.InfoHub'), \
         patch('app.telegram_bot.bot.KnowledgeDeck'):
         
        bot = TelegramBot(config, event_bus, news_client, risk_guard)
        
        # Mock _send_message to capture output
        bot._send_message = AsyncMock()
        
        # Mock specific component methods called by commands
        bot._diagnostics.run_full_diagnostics = AsyncMock(return_value="Diag Report OK")
        bot._briefing_service.generate_briefing = AsyncMock(return_value="Market Briefing OK")
        bot._market_regime.analyze_regime = AsyncMock(return_value="Regime Analysis OK")
        bot._report_generator.generate_html_report = MagicMock(return_value="/path/to/report.html")
        bot._stats_builder.get_total_summary = AsyncMock(return_value="Stats Summary OK")
        bot._gamification.get_profile.return_value = MagicMock(level=10, xp=1000)
        bot._gamification.get_rewards.return_value = ["Reward 1"]
        bot._alert_manager.get_user_alerts.return_value = {"currencies": ["USD"], "categories": []}
        bot._alert_manager.add_alert.return_value = True
        bot._alert_manager.remove_alert.return_value = True
        bot._updater.check_for_updates.return_value = (False, "No updates")
        
        # Define Test Cases
        test_cases = [
            {"type": "admin", "desc": "Admin Menu"},
            {"type": "admin_server", "desc": "Admin Server Menu"},
            {"type": "admin_ml", "desc": "Admin ML Menu"},
            {"type": "help", "desc": "Help Command"},
            {"type": "check_update", "desc": "Check Update"},
            {"type": "diag", "desc": "Diagnostics"},
            {"type": "briefing", "desc": "Briefing"},
            {"type": "marketregime", "desc": "Market Regime"},
            {"type": "report", "desc": "Performance Report"},
            {"type": "stats", "desc": "Stats"},
            {"type": "gamify", "desc": "Gamification Progress"},
            {"type": "profile", "desc": "User Profile"},
            {"type": "rewards", "desc": "Rewards"},
            {"type": "alerts", "desc": "List Alerts"},
            {"type": "alerts", "args": ["add", "currency", "EUR"], "desc": "Add Alert"},
            {"type": "alerts", "args": ["remove", "currency", "EUR"], "desc": "Remove Alert"},
            {"type": "risk", "desc": "Risk Status"},
            {"type": "risk", "value": "off", "desc": "Risk Off"},
            {"type": "risk", "value": "on", "desc": "Risk On"},
            {"type": "dekalog", "desc": "Dekalog"},
            {"type": "tips", "desc": "Trading Tips"},
            {"type": "learn", "term": "RSI", "desc": "Learn Term"},
            {"type": "calc_invalid", "desc": "Calc Invalid"},
            {"type": "unknown", "raw": "/foobar", "desc": "Unknown Command"},
        ]
        
        print(f"📋 Running {len(test_cases)} test cases...")
        
        failed_tests = []
        
        for case in test_cases:
            print(f"Testing: {case['desc']}...", end=" ")
            try:
                # Reset mock
                bot._send_message.reset_mock()
                
                # Simulate event
                event = Event(EventType.TELEGRAM_COMMAND, payload=case, timestamp=datetime.utcnow())
                await bot._on_telegram_command(event)
                
                # Verify call
                if bot._send_message.called:
                    args, kwargs = bot._send_message.call_args
                    # args[2] is 'text'
                    msg_text = args[2]
                    print(f"✅ OK")
                    # print(f"   Response: {msg_text[:50]}...") 
                else:
                    print(f"❌ FAILED (No response sent)")
                    failed_tests.append(case['desc'])
            except Exception as e:
                print(f"❌ ERROR: {e}")
                failed_tests.append(f"{case['desc']} ({e})")
                
        # Test Menu Registration (Static Check)
        print("\n🔍 Checking for set_my_commands implementation...")
        if hasattr(bot, "_set_bot_commands"):
            print("✅ _set_bot_commands method found.")
        else:
            print("❌ _set_bot_commands method NOT found (Missing functionality).")
            failed_tests.append("Menu Registration Missing")

        # Summary
        print("\n📊 Test Summary:")
        if failed_tests:
            print(f"❌ {len(failed_tests)} tests failed:")
            for t in failed_tests:
                print(f"   - {t}")
        else:
            print("✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(run_tests())
