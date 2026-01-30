import unittest
import os
import json
import tempfile
from unittest.mock import MagicMock, patch
from app.config import Config, Paths
from app.risk.guard import RiskGuard

class TestDynamicConfig(unittest.TestCase):
    
    def setUp(self):
        # Setup temporary config file
        self.test_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.test_dir.name, "runtime_config.json")
        
        # Patch Paths.RUNTIME_CONFIG to point to temp file
        self.patcher = patch('app.config.Paths.RUNTIME_CONFIG')
        self.mock_path = self.patcher.start()
        self.mock_path.exists.return_value = False
        self.mock_path.read_text.return_value = "{}"
        self.mock_path.write_text = MagicMock()
        
        # Initialize Config with dummy values
        self.config = Config(
            environment="test",
            telegram_bot_token="dummy_token",
            telegram_chat_id="dummy_chat_id",
            mode="advisor",
            data_source="yahoo",
            instruments=["EURUSD"],
            timeframe="1h",
            data_poll_interval_seconds=60,
            base_currency="USD",
            risk_per_trade_percent=1.0,
            max_trades_per_day=10,
            max_trades_per_instrument_per_day=3,
            ml_base_url="http://localhost:5000",
            educational_mode=True
        )
        self.config.aggressiveness = 5
        self.config.math_confidence = 5

    def tearDown(self):
        self.patcher.stop()
        self.test_dir.cleanup()

    def test_risk_guard_dynamic_profile_cykor(self):
        """Test RiskGuard profile for Low Aggressiveness (Cykor)."""
        self.config.aggressiveness = 1
        guard = RiskGuard(self.config)
        
        profile = guard.get_dynamic_risk_profile()
        
        # Expect conservative values
        self.assertEqual(profile["risk_per_trade_percent"], 0.5)
        self.assertEqual(profile["max_trades_per_day"], 5) # 3 + 1*2
        self.assertEqual(profile["min_rr"], 2.5)

    def test_risk_guard_dynamic_profile_wariat(self):
        """Test RiskGuard profile for High Aggressiveness (Wariat)."""
        self.config.aggressiveness = 10
        guard = RiskGuard(self.config)
        
        profile = guard.get_dynamic_risk_profile()
        
        # Expect aggressive values
        self.assertEqual(profile["risk_per_trade_percent"], 2.75) # 0.5 + 9*0.25
        self.assertEqual(profile["max_trades_per_day"], 23) # 3 + 10*2
        self.assertEqual(profile["min_rr"], 1.15) # 2.5 - 9*0.15 = 2.5 - 1.35 = 1.15

    def test_risk_guard_dynamic_profile_balanced(self):
        """Test RiskGuard profile for Medium Aggressiveness."""
        self.config.aggressiveness = 5
        guard = RiskGuard(self.config)
        
        profile = guard.get_dynamic_risk_profile()
        
        self.assertEqual(profile["risk_per_trade_percent"], 1.5) # 0.5 + 4*0.25
        self.assertEqual(profile["max_trades_per_day"], 13) # 3 + 5*2
        self.assertAlmostEqual(profile["min_rr"], 1.9, places=1) # 2.5 - 4*0.15 = 1.9

    def test_config_save_runtime(self):
        """Test that configuration saves to file correctly."""
        self.config.aggressiveness = 8
        self.config.math_confidence = 3
        self.config.system_paused = True
        
        self.config.save_runtime_config()
        
        # Verify write_text was called with correct JSON
        self.mock_path.write_text.assert_called_once()
        args = self.mock_path.write_text.call_args[0][0]
        saved_data = json.loads(args)
        
        self.assertEqual(saved_data["aggressiveness"], 8)
        self.assertEqual(saved_data["math_confidence"], 3)
        self.assertTrue(saved_data["system_paused"])

    def test_config_load_runtime(self):
        """Test that configuration loads from file correctly."""
        # Mock file existence and content
        self.mock_path.exists.return_value = True
        self.mock_path.read_text.return_value = json.dumps({
            "aggressiveness": 7,
            "math_confidence": 9,
            "system_paused": False
        })
        
        # Re-initialize config to trigger load
        # We need to mock os.environ to avoid Side Effects from real .env files if present,
        # but Config.from_env() handles defaults well.
        with patch.dict(os.environ, {}, clear=True):
             new_config = Config.from_env()
        
        self.assertEqual(new_config.aggressiveness, 7)
        self.assertEqual(new_config.math_confidence, 9)
        self.assertFalse(new_config.system_paused)

if __name__ == '__main__':
    unittest.main()
