
import unittest
import json
import shutil
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from app.data.news_client import NewsClient
from app.notifications.alert_manager import AlertManager
from app.config import Paths
from app.core.event_bus import EventBus

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)

class TestCalendarIntegration(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        # Create temporary directory for test data
        self.test_dir = Path("tests/temp_data")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Patch Paths in the modules where it is used
        self.paths_patcher_nc = patch('app.data.news_client.Paths')
        self.mock_paths_nc = self.paths_patcher_nc.start()
        
        self.paths_patcher_am = patch('app.notifications.alert_manager.Paths')
        self.mock_paths_am = self.paths_patcher_am.start()
        
        # Setup the paths on the mocks
        for mock in [self.mock_paths_nc, self.mock_paths_am]:
            mock.ECONOMIC_CALENDAR = self.test_dir / "economic_calendar.json"
            mock.ECONOMIC_HISTORY = self.test_dir / "economic_history.json"
            mock.ALERTS_CONFIG = self.test_dir / "alerts_config.json"
            mock.NEWS_CACHE = self.test_dir / "news_cache.json"
        
        # Initialize EventBus
        self.event_bus = EventBus()
        
    def tearDown(self):
        self.paths_patcher_nc.stop()
        self.paths_patcher_am.stop()
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    async def test_news_client_categorization_and_fear(self):
        """Test event categorization and fear detection logic."""
        client = NewsClient(self.event_bus)
        
        # Test Cases
        cases = [
            ("CPI m/m", "High", "Inflation", True), # CPI + High = Fear
            ("Unemployment Rate", "High", "Employment", False), # Employment + High = Not strictly fear (unless NFP)
            ("Non-Farm Employment Change", "High", "Employment", True), # NFP = Fear
            ("FOMC Statement", "High", "Central Bank", True), # FOMC = Fear
            ("Retail Sales", "Medium", "Retail", False),
            ("German Ifo Business Climate", "Medium", "Sentiment", False)
        ]
        
        for title, impact, expected_cat, expected_fear in cases:
            cat = client._classify_event_category(title)
            is_fear = client._is_fear_inducing(title, impact)
            
            self.assertEqual(cat, expected_cat, f"Category mismatch for {title}")
            self.assertEqual(is_fear, expected_fear, f"Fear mismatch for {title}")

    async def test_news_client_filtering(self):
        """Test get_events filtering capabilities."""
        client = NewsClient(self.event_bus)
        
        # Setup mock events
        now = datetime.now(timezone.utc)
        events = [
            {
                "title": "USD Event", "currency": "USD", "impact": "High", "category": "Inflation",
                "date": now.isoformat()
            },
            {
                "title": "EUR Event", "currency": "EUR", "impact": "Medium", "category": "Growth",
                "date": (now + timedelta(days=1)).isoformat()
            },
            {
                "title": "JPY Event", "currency": "JPY", "impact": "Low", "category": "Other",
                "date": (now + timedelta(days=2)).isoformat()
            }
        ]
        client._events = events
        
        # Test Currency Filter
        res = client.get_events(currency="USD")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["currency"], "USD")
        
        # Test Category Filter
        res = client.get_events(category="Growth")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["currency"], "EUR")
        
        # Test Date Filter
        res = client.get_events(end_date=now + timedelta(hours=1))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["currency"], "USD")

    async def test_history_archiving(self):
        """Test that past events are archived correctly."""
        client = NewsClient(self.event_bus)
        
        # Create some events
        now = datetime.now(timezone.utc)
        past_event = {
            "title": "Past Event", "country": "US", "date": (now - timedelta(hours=2)).isoformat(),
            "currency": "USD", "impact": "High", "category": "Test"
        }
        future_event = {
            "title": "Future Event", "country": "US", "date": (now + timedelta(hours=2)).isoformat(),
            "currency": "USD", "impact": "High", "category": "Test"
        }
        
        # Run update_history
        client._update_history([past_event, future_event])
        
        # Verify file created
        history_file = self.test_dir / "economic_history.json"
        self.assertTrue(history_file.exists())
        
        # Verify content
        content = json.loads(history_file.read_text(encoding="utf-8"))
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["title"], "Past Event")
        
        # Run again with same events (duplicate check)
        client._update_history([past_event, future_event])
        content = json.loads(history_file.read_text(encoding="utf-8"))
        self.assertEqual(len(content), 1, "Should not duplicate events")

    async def test_alert_manager(self):
        """Test AlertManager subscription logic."""
        manager = AlertManager()
        chat_id = "12345"
        
        # Add Alerts
        manager.add_alert(chat_id, "currency", "USD")
        manager.add_alert(chat_id, "category", "Inflation")
        
        # Verify Persistence
        alerts_file = self.test_dir / "alerts_config.json"
        self.assertTrue(alerts_file.exists())
        data = json.loads(alerts_file.read_text(encoding="utf-8"))
        self.assertIn(chat_id, data)
        self.assertIn("USD", data[chat_id]["currencies"])
        
        # Test Matching
        event_usd = {"currency": "USD", "category": "Growth"}
        event_eur_inf = {"currency": "EUR", "category": "Inflation"}
        event_eur_other = {"currency": "EUR", "category": "Other"}
        
        self.assertTrue(manager.should_notify(chat_id, event_usd))
        self.assertTrue(manager.should_notify(chat_id, event_eur_inf))
        self.assertFalse(manager.should_notify(chat_id, event_eur_other))
        
        # Remove Alert
        manager.remove_alert(chat_id, "currency", "USD")
        self.assertFalse(manager.should_notify(chat_id, event_usd))
        
        # Clear Alerts
        manager.clear_alerts(chat_id)
        self.assertFalse(manager.should_notify(chat_id, event_eur_inf))

if __name__ == '__main__':
    unittest.main()
