import os
import unittest
from unittest.mock import patch
from app.config import Config

class TestConfig(unittest.TestCase):

    @patch.dict(os.environ, {
        "ENVIRONMENT": "test_env",
        "MODE": "test_mode",
        "TELEGRAM_BOT_TOKEN": "123:ABC",
        "TELEGRAM_CHAT_ID": "123456",
        "DATA_SOURCE": "yahoo",
        "INSTRUMENTS": "AAPL,MSFT",
        "TIMEFRAME": "M15",
        "DATA_POLL_INTERVAL_SECONDS": "30",
        "RISK_PER_TRADE_PERCENT": "2.0",
        "MAX_TRADES_PER_DAY": "5"
    })
    def test_load_from_env(self):
        config = Config.from_env()
        self.assertEqual(config.environment, "test_env")
        self.assertEqual(config.mode, "test_mode")
        self.assertEqual(config.telegram_bot_token, "123:ABC")
        self.assertEqual(config.telegram_chat_id, "123456")
        self.assertEqual(config.data_source, "yahoo")
        self.assertEqual(config.instruments, ["AAPL", "MSFT"])
        self.assertEqual(config.timeframe, "M15")
        self.assertEqual(config.data_poll_interval_seconds, 30.0)
        self.assertEqual(config.risk_per_trade_percent, 2.0)
        self.assertEqual(config.max_trades_per_day, 5)

    @patch.dict(os.environ, {
        "INSTRUMENT_SECTIONS": "TECH_GIANTS",
        "INSTRUMENTS": ""
    })
    def test_instrument_sections_parsing(self):
        # Note: We need to mock INSTRUMENT_SECTIONS in app.config if we want to be pure,
        # but here we rely on the actual import. Assuming TECH_GIANTS is not in the map by default 
        # unless we check what's in instrument_universe.py. 
        # Let's rely on a known section if possible or mock the dict.
        
        # Checking logic: if INSTRUMENTS is empty, it looks at INSTRUMENT_SECTIONS.
        # Let's mock the dictionary in app.config to be safe.
        with patch("app.config.INSTRUMENT_SECTIONS", {"MY_SECTION": ["TEST1", "TEST2"]}):
             with patch.dict(os.environ, {"INSTRUMENT_SECTIONS": "MY_SECTION", "INSTRUMENTS": ""}):
                config = Config.from_env()
                self.assertEqual(config.instruments, ["TEST1", "TEST2"])

    def test_default_values(self):
        # Unset env vars to test defaults
        # We must also mock load_dotenv so it doesn't read .env file
        with patch("app.config.load_dotenv"):
            with patch.dict(os.environ, {}, clear=True):
                config = Config.from_env()
                self.assertEqual(config.environment, "practice")
                self.assertEqual(config.timeframe, "H1")
                self.assertEqual(config.risk_per_trade_percent, 1.0)

if __name__ == "__main__":
    unittest.main()
