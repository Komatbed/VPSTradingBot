from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, Dict
from dateutil import parser
import aiohttp
import json

from app.config import NewsConstants, Paths
from app.core.event_bus import EventBus
from app.core.models import Event, EventType

class NewsClient:
    def __init__(self, event_bus: EventBus) -> None:
        self._log = logging.getLogger("news_client")
        self._event_bus = event_bus
        self._events: List[Dict] = []
        self._last_update = datetime.min.replace(tzinfo=timezone.utc)
        self._update_interval = timedelta(hours=NewsConstants.UPDATE_INTERVAL_HOURS)
        self._running = False
        
        # Cache for emitted alerts to avoid spam (event_title -> timestamp)
        self._emitted_alerts: Dict[str, datetime] = {}

        # Try to load calendar immediately on startup (sync)
        self._load_local_calendar_sync()

    def _load_local_calendar_sync(self) -> None:
        """Synchronous load of local calendar file for immediate availability."""
        try:
            if Paths.ECONOMIC_CALENDAR.exists():
                content = Paths.ECONOMIC_CALENDAR.read_text(encoding="utf-8")
                if content.strip():
                    data = json.loads(content)
                    if isinstance(data, list):
                        self._events = data
                        # Set update time to now to avoid immediate re-fetch
                        self._last_update = datetime.now(timezone.utc)
                        self._log.info(f"Loaded {len(self._events)} events from {Paths.ECONOMIC_CALENDAR} (sync init)")
        except Exception as e:
            self._log.warning(f"Failed to load calendar from file (sync init): {e}")
        
    def _get_currencies_for_symbol(self, symbol: Optional[str]) -> List[str]:
        if not symbol:
            return ["USD", "EUR"]
        
        # Simple parsing for standard pairs like EURUSD, GBPUSD
        base = symbol[:3]
        # For 6-letter pairs, quote is the last 3. For others (like commodities), default to USD.
        quote = symbol[3:] if len(symbol) == 6 else "USD"
        
        # Handle Yahoo symbols like EURUSD=X
        if symbol.endswith("=X") and len(symbol) >= 5:
             # EURUSD=X -> EUR, USD
            return [symbol[:3], symbol[3:6]]
        
        return [base, quote]

    async def start(self) -> None:
        """Starts the background monitoring task."""
        self._running = True
        self._log.info("NewsClient background monitoring started.")
        while self._running:
            try:
                await self.update_calendar()
                await self._check_imminent_events()
            except Exception as e:
                self._log.error(f"Error in NewsClient loop: {e}", exc_info=True)
            
            # Check every minute for alerts, but update calendar less frequently
            await asyncio.sleep(60)

    async def stop(self) -> None:
        self._running = False

    async def update_calendar(self) -> None:
        now = datetime.now(timezone.utc)
        # Update if older than interval or no events
        if now - self._last_update < self._update_interval and self._events:
            return

        self._log.info("Updating economic calendar from external source...")
        
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, list):
                            self._events = self._filter_and_process_events(data)
                            self._last_update = now
                            self._save_calendar_to_file()
                            self._log.info(f"Calendar updated: {len(self._events)} events fetched.")
                            return
                    else:
                        self._log.warning(f"Failed to fetch calendar. Status: {response.status}")
        except Exception as e:
            self._log.error(f"Error fetching calendar: {e}")

    def _update_history(self, new_events: List[Dict]) -> None:
        """Updates the historical events archive with new data."""
        try:
            history = []
            if Paths.ECONOMIC_HISTORY.exists():
                content = Paths.ECONOMIC_HISTORY.read_text(encoding="utf-8")
                if content.strip():
                    history = json.loads(content)
            
            # Create a set of existing event IDs to avoid duplicates
            # ID = title + date + country
            existing_ids = {
                f"{e.get('title')}_{e.get('date')}_{e.get('country')}" for e in history
            }
            
            added_count = 0
            now = datetime.now(timezone.utc)
            
            for event in new_events:
                # Archive only past events
                try:
                    ed = parser.parse(event["date"])
                    if ed.tzinfo is None: ed = ed.replace(tzinfo=timezone.utc)
                    else: ed = ed.astimezone(timezone.utc)
                    
                    if ed < now:
                        eid = f"{event.get('title')}_{event.get('date')}_{event.get('country')}"
                        if eid not in existing_ids:
                            history.append(event)
                            existing_ids.add(eid)
                            added_count += 1
                except:
                    continue
            
            if added_count > 0:
                # Sort by date
                history.sort(key=lambda x: x["date"])
                
                # Write back
                Paths.ECONOMIC_HISTORY.write_text(json.dumps(history, indent=2), encoding="utf-8")
                self._log.info(f"Archived {added_count} past events to history.")
                
        except Exception as e:
            self._log.error(f"Failed to update history: {e}")

    def _filter_and_process_events(self, raw_events: List[Dict]) -> List[Dict]:
        """Filters events and standardizes format."""
        
        # Mapping for countries that might appear as names instead of currency codes
        country_map = {
            "Poland": "PLN",
            "European Monetary Union": "EUR",
            "Germany": "EUR",
            "France": "EUR",
            "Italy": "EUR",
            "Spain": "EUR",
            "United Kingdom": "GBP",
            "Great Britain": "GBP",
            "United States": "USD",
            "Japan": "JPY",
            "Switzerland": "CHF",
            "Canada": "CAD",
            "Australia": "AUD",
            "New Zealand": "NZD",
            "China": "CNY",
        }

        processed = []
        for item in raw_events:
            # ForexFactory JSON keys: title, country, date, impact, forecast, previous
            # Date format: "2024-06-25T14:00:00-04:00"
            try:
                # Filter by impact if needed, but we keep all and filter later
                impact = item.get("impact", "Low")
                if impact not in ["High", "Medium", "Low"]:
                    continue

                event_date_str = item.get("date")
                if not event_date_str:
                    continue
                
                # Parse date
                event_date = parser.parse(event_date_str)
                # Ensure UTC
                if event_date.tzinfo is None:
                    event_date = event_date.replace(tzinfo=timezone.utc)
                else:
                    event_date = event_date.astimezone(timezone.utc)

                raw_country = item.get("country", "")
                # Map country/currency code to standardized currency code
                # If raw_country is already a code (e.g. "USD"), map.get returns it (if not in keys) or we assume it's valid
                # But wait, if raw_country is "USD", map.get("USD") -> None.
                # So we use map.get(raw_country, raw_country)
                currency = country_map.get(raw_country, raw_country)
                
                # Special fix for Poland/PLN if not covered
                if "poland" in raw_country.lower():
                    currency = "PLN"

                title = item.get("title", "")
                category = self._classify_event_category(title)
                is_fear_inducing = self._is_fear_inducing(title, impact)
                
                # Generate link
                # Link to daily calendar view on ForexFactory
                # date format in item: "2024-06-25T14:00:00-04:00"
                # FF calendar url: https://www.forexfactory.com/calendar?day=jun25.2024
                # We need to format date to mmmdd.yyyy
                url = ""
                try:
                    day_str = event_date.strftime("%b%d.%Y").lower()
                    url = f"https://www.forexfactory.com/calendar?day={day_str}"
                except:
                    url = "https://www.forexfactory.com/calendar"

                processed.append({
                    "title": title,
                    "country": raw_country,
                    "currency": currency, 
                    "impact": impact,
                    "date": event_date.isoformat(),
                    "forecast": item.get("forecast", ""),
                    "previous": item.get("previous", ""),
                    "category": category,
                    "is_fear": is_fear_inducing,
                    "url": url
                })
            except Exception as e:
                continue
        
        # Sort by date
        processed.sort(key=lambda x: x["date"])
        return processed

    def _classify_event_category(self, title: str) -> str:
        """Classifies event based on title keywords."""
        t = title.lower()
        if any(x in t for x in ["cpi", "ppi", "pce", "inflation"]):
            return "Inflation"
        if any(x in t for x in ["employment", "unemployment", "payrolls", "jobless", "nfp"]):
            return "Employment"
        if any(x in t for x in ["rate", "fomc", "ecb", "boe", "rba", "rbnz", "boc", "boj", "statement", "minutes", "speech"]):
            return "Central Bank"
        if any(x in t for x in ["gdp", "growth"]):
            return "Growth"
        if any(x in t for x in ["confidence", "sentiment", "zew", "ifo", "pmi"]):
            return "Sentiment"
        if any(x in t for x in ["sales", "retail"]):
            return "Retail"
        return "Other"

    def _is_fear_inducing(self, title: str, impact: str) -> bool:
        """Determines if event is likely to cause market fear/volatility."""
        if impact != "High":
            return False
        
        t = title.lower()
        # Key fear drivers: Central Banks, NFP, CPI, Geopolitics (hard to detect from calendar)
        fear_keywords = ["fomc", "fed ", "federal funds", "nfp", "non-farm", "cpi", "inflation", "gdp", "rate decision"]
        return any(k in t for k in fear_keywords)

    def get_events(self, 
                   start_date: Optional[datetime] = None, 
                   end_date: Optional[datetime] = None, 
                   currency: Optional[str] = None,
                   impact: Optional[str] = None,
                   category: Optional[str] = None) -> List[Dict]:
        """
        Retrieves events filtered by criteria.
        Dates should be timezone-aware (UTC) or will be assumed UTC.
        """
        filtered = []
        for event in self._events:
            try:
                # Parse event date again (or we could store as datetime in memory, but JSON requires string)
                # To optimize, we could store datetime in memory struct and convert only for JSON.
                # For now, parse.
                ed = parser.parse(event["date"])
                if ed.tzinfo is None: ed = ed.replace(tzinfo=timezone.utc)
                else: ed = ed.astimezone(timezone.utc)
                
                if start_date and ed < start_date:
                    continue
                if end_date and ed > end_date:
                    continue
                
                if currency and currency.upper() != event["currency"]:
                    continue
                
                if impact and impact.lower() != event["impact"].lower():
                    continue
                    
                if category and category.lower() != event["category"].lower():
                    continue
                    
                filtered.append(event)
            except:
                continue
                
        return filtered

    def get_fear_events(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict]:
        """Retrieves events marked as fear-inducing."""
        filtered = []
        for event in self._events:
            if not event.get("is_fear", False):
                continue
                
            try:
                ed = parser.parse(event["date"])
                if ed.tzinfo is None: ed = ed.replace(tzinfo=timezone.utc)
                else: ed = ed.astimezone(timezone.utc)
                
                if start_date and ed < start_date:
                    continue
                if end_date and ed > end_date:
                    continue
                
                filtered.append(event)
            except:
                continue
        return filtered

    def _save_calendar_to_file(self) -> None:
        try:
            content = json.dumps(self._events, indent=2)
            Paths.ECONOMIC_CALENDAR.write_text(content, encoding="utf-8")
        except Exception as e:
            self._log.error(f"Failed to save calendar cache: {e}")

    async def _check_imminent_events(self) -> None:
        """Checks for high impact events in the next 15-30 minutes and emits alerts."""
        now = datetime.now(timezone.utc)
        
        for event in self._events:
            # Parse date
            try:
                # ForexFactory dates are usually like "2024-05-30T08:30:00-04:00"
                event_date = parser.parse(event.get("date"))
                # Ensure UTC
                if event_date.tzinfo is None:
                    event_date = event_date.replace(tzinfo=timezone.utc)
                else:
                    event_date = event_date.astimezone(timezone.utc)
            except Exception:
                continue

            # Only check High impact
            impact = event.get("impact")
            if impact != "High":
                continue

            time_to_event = (event_date - now).total_seconds() / 60.0
            
            # Alert window: 15 minutes before
            if 0 < time_to_event <= 15:
                event_id = f"{event.get('title')}_{event.get('date')}"
                if event_id not in self._emitted_alerts:
                    self._log.info(f"Imminent High Impact Event: {event.get('title')} ({event.get('country')})")
                    
                    payload = {
                        "title": event.get("title"),
                        "country": event.get("country"),
                        "currency": event.get("currency"),
                        "category": event.get("category"),
                        "impact": impact,
                        "minutes": time_to_event,
                        "timestamp": event_date.isoformat(),
                        "url": event.get("url", "https://www.forexfactory.com/calendar")
                    }
                    
                    await self._event_bus.publish(Event(
                        type=EventType.ECONOMIC_EVENT_IMMINENT,
                        payload=payload,
                        timestamp=now
                    ))
                    
                    self._emitted_alerts[event_id] = now

        # Cleanup old alerts from cache
        for eid in list(self._emitted_alerts.keys()):
            if (now - self._emitted_alerts[eid]).total_seconds() > 3600:
                del self._emitted_alerts[eid]

    def get_impact_for_symbol(self, symbol: str) -> Tuple[Optional[str], Optional[float]]:
        """
        Returns (highest_impact, minutes_to_event) for a symbol.
        Considers events within T-30 to T+15 minutes window.
        """
        currencies = self._get_currencies_for_symbol(symbol)
        now = datetime.now(timezone.utc)
        
        highest_impact = None
        min_minutes = None
        
        impact_priority = {"High": 3, "Medium": 2, "Low": 1}
        
        for event in self._events:
            event_currency = event.get("currency")
            if event_currency not in currencies:
                continue
                
            try:
                event_date = parser.parse(event.get("date"))
                if event_date.tzinfo is None:
                    event_date = event_date.replace(tzinfo=timezone.utc)
                else:
                    event_date = event_date.astimezone(timezone.utc)
            except:
                continue
                
            diff_min = (event_date - now).total_seconds() / 60.0
            
            # Check window: -30 (before) to +15 (after)
            # Actually, "T-30 / T+15 min" usually means from 30 min before to 15 min after.
            # So diff_min should be between -15 (past) and +30 (future)?
            # Wait, "Za 15 min: NFP" means T-15.
            # The rule says: "-10 do -30 punktów, jeśli ... T-30 / T+15 min"
            # This implies if we are in the window [Event-30min, Event+15min].
            # So: -15 <= diff_min <= 30 ? No.
            # If event is at 12:00.
            # At 11:30 (T-30), diff is +30.
            # At 12:15 (T+15), diff is -15.
            # So window is: -15 <= diff_min <= 30.
            
            if -15 <= diff_min <= 30:
                impact = event.get("impact")
                current_prio = impact_priority.get(impact, 0)
                highest_prio = impact_priority.get(highest_impact, 0)
                
                if current_prio > highest_prio:
                    highest_impact = impact
                    min_minutes = diff_min
                elif current_prio == highest_prio:
                    # If same impact, take the one closer to 0 (event time)
                    if min_minutes is None or abs(diff_min) < abs(min_minutes):
                        min_minutes = diff_min
                        
        return highest_impact, min_minutes
