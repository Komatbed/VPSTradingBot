from __future__ import annotations

import asyncio
from datetime import datetime

import aiohttp
import logging
import json
import os

from app.config import Config
from app.core.event_bus import EventBus
from app.core.models import Event, EventType, MarketDataSnapshot
from app.data.yahoo_client import YahooFinanceClient
from app.data.instrument_universe import FAVORITES
from app.regime.engine import MarketRegimeEngine
from app.data.news_client import NewsClient


class DataEngine:
    def __init__(
        self,
        config: Config,
        event_bus: EventBus,
        news_client: NewsClient,
    ) -> None:
        self._config = config
        self._event_bus = event_bus
        self._news_client = news_client
        self._yahoo_client = YahooFinanceClient()
        self._regime_engine = MarketRegimeEngine()
        self._log = logging.getLogger("data")
        self._min_expect_1d = float(os.environ.get("LIVE_MIN_EXPECTANCY_1D", "0.0"))
        self._expectancy_1d = {}
        if self._min_expect_1d > 0.0:
            summary_path = os.path.join("backtests", "summary_1d.json")
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    items = json.load(f)
                for item in items:
                    symbol = item.get("instrument")
                    value = item.get("expectancy_1d")
                    if symbol is not None and isinstance(value, (int, float)):
                        self._expectancy_1d[symbol] = float(value)
                self._log.info(
                    "Loaded expectancy_1d for %d instruments from %s",
                    len(self._expectancy_1d),
                    summary_path,
                )
            except Exception:
                self._log.warning("Could not load summary_1d.json for live expectancy filter.")

    async def run_once(self) -> None:
        instruments = self._config.instruments
        timeframe = self._config.timeframe
        data_source = getattr(self._config, "data_source", "yahoo")
        self._log.info(
            "Running data engine once: data_source=%s instruments=%d timeframe=%s",
            data_source,
            len(instruments),
            timeframe,
        )
        if data_source != "yahoo":
            self._log.warning("Unsupported data_source=%s, only 'yahoo' is supported.", data_source)
            return
        favorites_set = set(FAVORITES)
        favorite_instruments = [i for i in instruments if i in favorites_set]
        other_instruments = [i for i in instruments if i not in favorites_set]
        if self._min_expect_1d > 0.0 and self._expectancy_1d:
            filtered_fav = [
                i for i in favorite_instruments if self._expectancy_1d.get(i, 0.0) >= self._min_expect_1d
            ]
            filtered_other = [
                i for i in other_instruments if self._expectancy_1d.get(i, 0.0) >= self._min_expect_1d
            ]
            
            # Fallback logic: If filtering kills everything, revert to original
            if not filtered_fav and not filtered_other:
                self._log.warning(
                    "Expectancy filter (min=%.2f) removed ALL instruments! Falling back to full list.", 
                    self._min_expect_1d
                )
            else:
                favorite_instruments = filtered_fav
                other_instruments = filtered_other
        max_per_run = 20
        favorite_instruments = favorite_instruments[:max_per_run]
        remaining = max_per_run - len(favorite_instruments)
        if remaining > 0:
            other_instruments = other_instruments[:remaining]
        else:
            other_instruments = []
        self._log.info(
            "Yahoo instruments split into favorites=%d and others=%d",
            len(favorite_instruments),
            len(other_instruments),
        )

        # Update news calendar once per cycle
        await self._news_client.update_calendar()

        async with aiohttp.ClientSession() as session:
            for instrument in favorite_instruments:
                self._log.debug(
                    "Fetching Yahoo candles [FAVORITE] for instrument=%s timeframe=%s",
                    instrument,
                    timeframe,
                )
                candles = await self._yahoo_client.fetch_candles(
                    session=session,
                    symbol=instrument,
                    timeframe=timeframe,
                    count=200,
                )
                if not candles:
                    self._log.debug(
                        "No candles from Yahoo for favorite instrument=%s timeframe=%s - skipping",
                        instrument,
                        timeframe,
                    )
                    continue
                self._log.debug(
                    "Received %d candles from Yahoo for favorite instrument=%s timeframe=%s",
                    len(candles),
                    instrument,
                    timeframe,
                )
                
                # News Impact
                impact, time_to = self._news_client.get_impact_for_symbol(instrument)

                regime = self._regime_engine.infer_regime(candles)
                snapshot = MarketDataSnapshot(
                    instrument=instrument,
                    timeframe=timeframe,
                    candles=candles,
                    spread=None,
                    regime=regime,
                    news_impact=impact,
                    time_to_news_min=time_to
                )
                event = Event(type=EventType.MARKET_DATA, payload=snapshot, timestamp=datetime.utcnow())
                await self._event_bus.publish(event)
                self._log.debug(
                    "Published MARKET_DATA snapshot for favorite instrument=%s timeframe=%s",
                    instrument,
                    timeframe,
                )
                await asyncio.sleep(2.0)
            for instrument in other_instruments:
                self._log.debug(
                    "Fetching Yahoo candles [OTHER] for instrument=%s timeframe=%s",
                    instrument,
                    timeframe,
                )
                candles = await self._yahoo_client.fetch_candles(
                    session=session,
                    symbol=instrument,
                    timeframe=timeframe,
                    count=200,
                )
                if not candles:
                    self._log.debug(
                        "No candles from Yahoo for other instrument=%s timeframe=%s - skipping",
                        instrument,
                        timeframe,
                    )
                    continue
                self._log.debug(
                    "Received %d candles from Yahoo for other instrument=%s timeframe=%s",
                    len(candles),
                    instrument,
                    timeframe,
                )
                
                # News Impact
                impact, time_to = self._news_client.get_impact_for_symbol(instrument)

                regime = self._regime_engine.infer_regime(candles)
                snapshot = MarketDataSnapshot(
                    instrument=instrument,
                    timeframe=timeframe,
                    candles=candles,
                    spread=None,
                    regime=regime,
                    news_impact=impact,
                    time_to_news_min=time_to
                )
                event = Event(type=EventType.MARKET_DATA, payload=snapshot, timestamp=datetime.utcnow())
                await self._event_bus.publish(event)
                self._log.debug(
                    "Published MARKET_DATA snapshot for other instrument=%s timeframe=%s",
                    instrument,
                    timeframe,
                )
                await asyncio.sleep(4.0)

    async def run(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self._config.data_poll_interval_seconds)
