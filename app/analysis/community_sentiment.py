import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio

from app.config import Paths

class CommunitySentimentManager:
    """
    Manages community voting (sentiment) for instruments.
    Votes are stored in a JSON file and expire after a configurable duration.
    """
    def __init__(self, storage_path: Path = None):
        self._storage_path = storage_path or (Paths.DATA_DIR / "community_votes.json")
        self._log = logging.getLogger("community_sentiment")
        self._data: Dict[str, Any] = {}
        self._vote_ttl_hours = 24
        self._lock = asyncio.Lock()
        self._load()

    def _load(self):
        if self._storage_path.exists():
            try:
                content = self._storage_path.read_text(encoding="utf-8")
                self._data = json.loads(content)
            except Exception as e:
                self._log.error(f"Failed to load community votes: {e}")
                self._data = {}
        else:
            self._data = {}

    async def _save(self):
        try:
            # Atomic write pattern could be better, but simple write is okay for now
            self._storage_path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except Exception as e:
            self._log.error(f"Failed to save community votes: {e}")

    def _cleanup_expired(self):
        """Removes votes older than TTL."""
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=self._vote_ttl_hours)
        
        changed = False
        for symbol in list(self._data.keys()):
            votes = self._data[symbol].get("votes", {})
            new_votes = {}
            symbol_changed = False
            
            for user_id, vote_info in votes.items():
                ts = datetime.fromisoformat(vote_info["timestamp"])
                if ts > cutoff:
                    new_votes[user_id] = vote_info
                else:
                    symbol_changed = True
            
            if symbol_changed:
                if not new_votes:
                    del self._data[symbol]
                else:
                    self._data[symbol]["votes"] = new_votes
                    self._recalculate_score(symbol)
                changed = True
                
        return changed

    def _recalculate_score(self, symbol: str):
        if symbol not in self._data:
            return
        votes = self._data[symbol].get("votes", {})
        score = 0
        for v in votes.values():
            if v["type"] == "up":
                score += 1
            elif v["type"] == "down":
                score -= 1
        self._data[symbol]["score"] = score

    async def register_vote(self, symbol: str, user_id: str, vote_type: str) -> Dict[str, Any]:
        """
        Registers a vote. 
        vote_type: 'up' or 'down'.
        Returns updated stats for the symbol.
        """
        async with self._lock:
            self._cleanup_expired()
            
            symbol = symbol.upper()
            now_iso = datetime.utcnow().isoformat()
            
            if symbol not in self._data:
                self._data[symbol] = {"votes": {}, "score": 0}
            
            # Update vote
            self._data[symbol]["votes"][user_id] = {
                "type": vote_type,
                "timestamp": now_iso
            }
            
            self._recalculate_score(symbol)
            await self._save()
            
            return {
                "score": self._data[symbol]["score"],
                "total_votes": len(self._data[symbol]["votes"])
            }

    async def get_hot_list(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Returns top scored symbols."""
        async with self._lock:
            self._cleanup_expired()
            
            items = []
            for symbol, data in self._data.items():
                items.append({
                    "symbol": symbol,
                    "score": data["score"],
                    "votes": len(data["votes"])
                })
            
            # Sort by score desc, then votes desc
            items.sort(key=lambda x: (x["score"], x["votes"]), reverse=True)
            return items[:limit]

    def get_symbol_score(self, symbol: str) -> int:
        symbol = symbol.upper()
        if symbol in self._data:
            return self._data[symbol]["score"]
        return 0
