import json
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, date

from app.config import GamificationConstants, Paths

class GamificationEngine:
    def __init__(self):
        self._profile_path = Paths.USER_PROFILE
        self._log = logging.getLogger("gamification")
        self._config = GamificationConstants
        self._profile = self._load_profile()

    def _load_profile(self) -> Dict[str, Any]:
        if not self._profile_path.exists():
            return self._create_default_profile()
        try:
            data = json.loads(self._profile_path.read_text(encoding="utf-8"))
            # Migration/Safety check for new fields
            if "daily_counts" not in data: data["daily_counts"] = {}
            if "streaks" not in data: data["streaks"] = {}
            if "penalties" not in data: data["penalties"] = []
            return data
        except Exception as e:
            self._log.error(f"Failed to load profile: {e}")
            return self._create_default_profile()

    def _create_default_profile(self) -> Dict[str, Any]:
        return {
            "xp": 0,
            "level": 1,
            "balance": 10000.0, # Initial virtual capital
            "title": self._config.RANKS[0][1],
            "achievements": [],
            "stats": {
                "trades_logged": 0,
                "manual_reads": 0,
                "briefings_read": 0,
                "close_tp_count": 0,
                "close_sl_count": 0,
                "close_manual_count": 0,
                "close_panic_count": 0,
                "wins": 0,
                "losses": 0,
                "current_streak": 0 # Positive for wins, negative for losses
            },
            "daily_counts": {}, 
            "streaks": {
                "journal_current": 0,
                "journal_last_date": "",
                "discipline_current": 0
            },
            "penalties": []
        }

    def _save_profile(self):
        try:
            # Ensure directory exists
            if not self._profile_path.parent.exists():
                self._profile_path.parent.mkdir(parents=True, exist_ok=True)
                
            self._profile_path.write_text(json.dumps(self._profile, indent=2), encoding="utf-8")
        except Exception as e:
            self._log.error(f"Failed to save profile: {e}")

    def _check_daily_limit(self, action_key: str) -> bool:
        """Returns True if action is within daily limit or no limit exists."""
        limit = self._config.DAILY_LIMITS.get(action_key)
        if limit is None:
            return True
            
        today = date.today().isoformat()
        if today not in self._profile["daily_counts"]:
            self._profile["daily_counts"] = {today: {}} # Reset/Init for today
            
        current = self._profile["daily_counts"][today].get(action_key, 0)
        return current < limit

    def _increment_daily(self, action_key: str):
        today = date.today().isoformat()
        if today not in self._profile["daily_counts"]:
            self._profile["daily_counts"] = {today: {}}
        
        current = self._profile["daily_counts"][today].get(action_key, 0)
        self._profile["daily_counts"][today][action_key] = current + 1

    def add_xp(self, amount: int, reason: str) -> str:
        """Adds XP and returns a message if level up occurred."""
        if amount <= 0:
            return ""

        old_level = self._profile["level"]
        self._profile["xp"] += amount
        
        # Calculate Level
        # Level = 1 + (XP // XP_PER_LEVEL)
        new_level = 1 + (self._profile["xp"] // self._config.XP_PER_LEVEL)
        
        self._profile["level"] = new_level
        
        msg = f"🌟 +{amount} XP ({reason})"
        
        if new_level > old_level:
            msg += f"\n\n🎉 **AWANS!** Jesteś teraz na poziomie {new_level}!"
            # Check for new title
            new_title = self._get_title_for_level(new_level)
            current_title = self._profile.get("title", "")
            
            if new_title != current_title:
                self._profile["title"] = new_title
                msg += f"\n🏆 Nowy tytuł: **{new_title}**"
                # Find description
                desc = next((r[2] for r in self._config.RANKS if r[1] == new_title), "")
                if desc:
                    msg += f"\n_{desc}_"
        
        self._save_profile()
        return msg

    def _get_title_for_level(self, level: int) -> str:
        # Ranks are sorted by level ascending
        # Find the highest rank where rank_level <= user_level
        selected = self._config.RANKS[0][1]
        for rank_lvl, rank_title, _ in self._config.RANKS:
            if level >= rank_lvl:
                selected = rank_title
            else:
                break
        return selected

    def get_profile(self, chat_id: str) -> SimpleNamespace:
        """Returns the profile as an object for easy attribute access."""
        # Note: chat_id argument is kept for compatibility, but currently we use a single global profile
        # In multi-user system, we would load profile by chat_id
        
        # Calculate next level XP
        level = self._profile["level"]
        next_level_xp = level * self._config.XP_PER_LEVEL
        
        data = self._profile.copy()
        data["next_level_xp"] = next_level_xp
        
        return SimpleNamespace(**data)

    def add_penalty(self, penalty_type: str, note: str = "") -> str:
        """Adds a penalty flag without deducting XP and returns a warning message."""
        timestamp = datetime.now().isoformat()
        penalty_record = {
            "type": penalty_type,
            "note": note,
            "timestamp": timestamp
        }
        self._profile["penalties"].append(penalty_record)
        self._save_profile()
        return f"⚠️ **FLAGA KARNA:** {penalty_type} ({note})"

    def process_trade_result(self, profit_amount: float) -> str:
        """Updates balance, win/loss stats, and streaks based on trade result."""
        # Update Balance
        old_balance = self._profile.get("balance", 10000.0)
        self._profile["balance"] = old_balance + profit_amount
        
        # Update Stats
        stats = self._profile["stats"]
        if "wins" not in stats: stats["wins"] = 0
        if "losses" not in stats: stats["losses"] = 0
        if "current_streak" not in stats: stats["current_streak"] = 0
        
        msg = ""
        streak_bonus = 0
        
        if profit_amount > 0:
            stats["wins"] += 1
            if stats["current_streak"] < 0:
                stats["current_streak"] = 1
            else:
                stats["current_streak"] += 1
            
            # Combo Bonus
            streak = stats["current_streak"]
            if streak >= 3:
                msg = f"\n🔥 **COMBO x{streak}!** Jesteś w gazie!"
                streak_bonus = streak * 10
                self.add_xp(streak_bonus, f"Win Streak x{streak}")
                
        elif profit_amount < 0:
            stats["losses"] += 1
            if stats["current_streak"] > 0:
                stats["current_streak"] = -1
            else:
                stats["current_streak"] -= 1
            
            streak = abs(stats["current_streak"])
            if streak >= 3:
                msg = f"\n❄️ **COLD STREAK x{streak}**... Może czas na przerwę?"
        
        self._save_profile()
        return msg

    def register_event(self, event_type: str, **kwargs) -> Optional[str]:
        """
        Registers an event, checks limits, awards XP, handles streaks.
        event_type: Key from XP_TABLE (e.g., 'close_tp', 'edu_learn')
        """
        if event_type not in self._config.XP_TABLE:
            return None # Unknown event
            
        # 1. Check Daily Limit
        if not self._check_daily_limit(event_type):
            return None # Limit reached, no XP
            
        # 2. Update Stats & Daily Counts
        self._increment_daily(event_type)
        self._update_stats(event_type)
        
        # 3. Handle Streaks
        streak_msg = self._update_streaks(event_type)
        
        # 4. Award XP
        xp_amount = self._config.XP_TABLE[event_type]
        xp_msg = self.add_xp(xp_amount, event_type.replace("_", " ").upper())
        
        # 5. Check Achievements
        ach_msg = self._check_achievements()
        
        # Combine messages
        messages = []
        if xp_msg: messages.append(xp_msg)
        if streak_msg: messages.append(streak_msg)
        if ach_msg: messages.append(ach_msg)
        
        return "\n\n".join(messages) if messages else None

    def _update_stats(self, event_type: str):
        # General mapping
        if event_type == "edu_learn": self._profile["stats"]["manual_reads"] += 1
        elif event_type == "edu_briefing": self._profile["stats"]["briefings_read"] += 1
        elif event_type.startswith("close_"): 
            self._profile["stats"]["trades_logged"] += 1
            key = f"{event_type}_count" # close_tp_count
            self._profile["stats"][key] = self._profile["stats"].get(key, 0) + 1

    def _update_streaks(self, event_type: str) -> Optional[str]:
        msg = None
        today = date.today().isoformat()
        
        # A. Journal Streak
        if event_type in ["journal_full", "journal_short"]:
            last_date = self._profile["streaks"].get("journal_last_date")
            current = self._profile["streaks"].get("journal_current", 0)
            
            if last_date == today:
                pass # Already counted today
            else:
                # Check if consecutive day (simple check: if last was yesterday or today)
                # For simplicity, we just increment if it's a new day. 
                # Real implementation would check date diff.
                # Here we assume user is consistent if they do it.
                # Proper way:
                if last_date:
                    last_dt = date.fromisoformat(last_date)
                    delta = (date.today() - last_dt).days
                    if delta == 1:
                        current += 1
                    elif delta > 1:
                        current = 1 # Streak broken
                    else:
                        pass # Same day
                else:
                    current = 1
                
                self._profile["streaks"]["journal_current"] = current
                self._profile["streaks"]["journal_last_date"] = today
                
                # Check Bonus
                conf = self._config.STREAKS["journal_streak"]
                if current in conf["thresholds"]:
                    idx = conf["thresholds"].index(current)
                    bonus = conf["bonus_xp"][idx]
                    self.add_xp(bonus, f"STREAK: {current} dni dziennika")
                    msg = f"🔥 **STREAK!** Prowadzisz dziennik od {current} dni! (+{bonus} XP)"

        # B. Discipline Streak
        if event_type in ["close_tp", "close_sl"]:
            current = self._profile["streaks"].get("discipline_current", 0) + 1
            self._profile["streaks"]["discipline_current"] = current
            
            conf = self._config.STREAKS["discipline_streak"]
            if current in conf["thresholds"]:
                idx = conf["thresholds"].index(current)
                bonus = conf["bonus_xp"][idx]
                self.add_xp(bonus, f"STREAK: {current} trade'ów wg planu")
                msg = f"🛡️ **DYSCYPLINA!** {current} trade'ów zamkniętych wg planu z rzędu! (+{bonus} XP)"
        elif event_type in ["close_panic", "close_manual"]:
             # Break streak
             if self._profile["streaks"].get("discipline_current", 0) > 0:
                 self._profile["streaks"]["discipline_current"] = 0
                 msg = "💔 **Streak Dyscypliny przerwany.**"

        return msg

    def _check_achievements(self) -> Optional[str]:
        new_unlocks = []
        for ach in self._config.ACHIEVEMENTS:
            aid = ach["id"]
            if aid in self._profile["achievements"]:
                continue
                
            # Check condition
            unlocked = False
            if ach["condition_type"] == "count":
                val = self._profile["stats"].get(ach["condition_key"], 0)
                if val >= ach["threshold"]:
                    unlocked = True
            
            if unlocked:
                self._profile["achievements"].append(aid)
                self.add_xp(ach["xp_reward"], f"Achievement: {ach['title']}")
                new_unlocks.append(f"🏆 **ODBLOKOWANO OSIĄGNIĘCIE:** {ach['title']}\n_{ach['description']}_ (+{ach['xp_reward']} XP)")
        
        return "\n\n".join(new_unlocks) if new_unlocks else None


    def get_progress(self) -> str:
        xp = self._profile["xp"]
        level = self._profile["level"]
        title = self._profile["title"]
        next_level_xp = level * self._config.XP_PER_LEVEL
        prev_level_xp = (level - 1) * self._config.XP_PER_LEVEL
        
        # XP in current level
        current_level_xp = xp - prev_level_xp
        needed_xp = self._config.XP_PER_LEVEL
        
        # Percentage
        pct = min(1.0, max(0.0, current_level_xp / needed_xp))
        bar_len = 15
        filled = int(pct * bar_len)
        bar = "▓" * filled + "░" * (bar_len - filled)
        
        stats = self._profile["stats"]
        win_rate = 0
        total_closed = stats.get("close_tp_count", 0) + stats.get("close_sl_count", 0) + stats.get("close_manual_count", 0)
        if total_closed > 0:
            # Assuming TP is win, SL is loss (simplified)
            # Or use close_tp as win
            win_rate = (stats.get("close_tp_count", 0) / total_closed) * 100

        lines = [
            f"👤 **PROFIL TRADERA** | {title}",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"⭐ **Poziom {level}** | {xp} XP",
            f"📊 `{bar}` {int(current_level_xp)}/{needed_xp} XP",
            "",
            "📈 **Statystyki Gry:**",
            f"🔸 Trade'y zalogowane: {stats.get('trades_logged', 0)}",
            f"🔸 Dyscyplina (TP+SL): {stats.get('close_tp_count', 0) + stats.get('close_sl_count', 0)}",
            f"🔸 Manualne wyjścia: {stats.get('close_manual_count', 0)}",
            f"🔸 Panika/Błędy: {stats.get('close_panic_count', 0)}",
            "",
            "🔥 **Serie (Streaks):**",
            f"⚡ Dziennik: {self._profile['streaks'].get('journal_current', 0)} dni",
            f"🛡️ Żelazna Dyscyplina: {self._profile['streaks'].get('discipline_current', 0)} trade'ów"
        ]
        
        if self._profile["penalties"]:
            lines.append("")
            lines.append(f"⚠️ **Aktywne Flagi Karne:** {len(self._profile['penalties'])}")
            
        return "\n".join(lines)

    # Compat methods for existing calls
    def award_xp(self, user_id: str, amount: int, reason: str) -> SimpleNamespace:
        self.add_xp(amount, reason)
        return self.get_profile(user_id)
        
    def get_profile(self, user_id: str) -> SimpleNamespace:
        # Convert dict to Namespace for compatibility
        p = self._profile
        return SimpleNamespace(
            level=p["level"],
            xp=p["xp"],
            next_level_xp=p["level"] * self._config.XP_PER_LEVEL,
            title=p.get("title", "Novice"),
            badges=p.get("achievements", [])
        )
    
    def get_rewards(self, user_id: str) -> List[str]:
        return self._profile.get("achievements", [])
