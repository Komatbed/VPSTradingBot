import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from app.config import Paths

class AlertManager:
    """
    Manages user subscriptions for economic event alerts.
    Allows users to subscribe to specific currencies or event categories.
    """
    def __init__(self):
        self._log = logging.getLogger("alert_manager")
        self._alerts: Dict[str, Dict[str, List[str]]] = {} # chat_id -> {"currencies": [], "categories": []}
        self._load_alerts()

    def _load_alerts(self):
        if Paths.ALERTS_CONFIG.exists():
            try:
                content = Paths.ALERTS_CONFIG.read_text(encoding="utf-8")
                if content.strip():
                    self._alerts = json.loads(content)
            except Exception as e:
                self._log.error(f"Failed to load alerts config: {e}")
                self._alerts = {}

    def _save_alerts(self):
        try:
            content = json.dumps(self._alerts, indent=2)
            Paths.ALERTS_CONFIG.write_text(content, encoding="utf-8")
        except Exception as e:
            self._log.error(f"Failed to save alerts config: {e}")

    def add_alert(self, chat_id: str, filter_type: str, value: str) -> bool:
        """
        Adds an alert filter for a user.
        filter_type: 'currency' or 'category'
        value: e.g. 'USD', 'Inflation'
        """
        cid = str(chat_id)
        if cid not in self._alerts:
            self._alerts[cid] = {"currencies": [], "categories": []}
        
        key = "currencies" if filter_type == "currency" else "categories"
        
        # Initialize key if missing (migration)
        if key not in self._alerts[cid]:
            self._alerts[cid][key] = []

        if value not in self._alerts[cid][key]:
            self._alerts[cid][key].append(value)
            self._save_alerts()
            return True
        return False

    def remove_alert(self, chat_id: str, filter_type: str, value: str) -> bool:
        cid = str(chat_id)
        if cid not in self._alerts:
            return False
            
        key = "currencies" if filter_type == "currency" else "categories"
        
        # Initialize key if missing
        if key not in self._alerts[cid]:
            return False

        if value in self._alerts[cid][key]:
            self._alerts[cid][key].remove(value)
            self._save_alerts()
            return True
        return False

    def get_user_alerts(self, chat_id: str) -> Dict[str, List[str]]:
        return self._alerts.get(str(chat_id), {"currencies": [], "categories": []})

    def should_notify(self, chat_id: str, event: Dict) -> bool:
        """Checks if user should be notified about this event."""
        cid = str(chat_id)
        if cid not in self._alerts:
            return False
            
        user_config = self._alerts[cid]
        
        # Check Currency
        event_currency = event.get("currency")
        if event_currency and event_currency in user_config.get("currencies", []):
            return True
            
        # Check Category
        event_category = event.get("category")
        if event_category and event_category in user_config.get("categories", []):
            return True
            
        return False

    def get_recipients_for_event(self, event: Dict) -> List[str]:
        """Returns list of chat_ids that should receive this event."""
        recipients = []
        for chat_id in self._alerts:
            if self.should_notify(chat_id, event):
                recipients.append(chat_id)
        return recipients

    def clear_alerts(self, chat_id: str):
        cid = str(chat_id)
        if cid in self._alerts:
            del self._alerts[cid]
            self._save_alerts()
