from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

import asyncio
import json
import logging
from pathlib import Path

import yfinance as yf

from app.core.models import Candle


class YahooFinanceClient:
    def __init__(self) -> None:
        self._log = logging.getLogger("yahoo")
        self._cache_dir = Path("cache") / "yahoo"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_ttl = timedelta(hours=6)

    def _cache_path(self, symbol: str, timeframe: str) -> Path:
        safe_symbol = symbol.replace("/", "_")
        return self._cache_dir / f"{safe_symbol}_{timeframe}.json"

    def _load_from_cache(self, symbol: str, timeframe: str) -> List[Candle]:
        path = self._cache_path(symbol, timeframe)
        if not path.exists():
            return []
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
        except Exception:
            return []
        ts_str = data.get("timestamp")
        if not ts_str:
            return []
        try:
            ts = datetime.fromisoformat(ts_str)
        except Exception:
            return []
        if datetime.utcnow() - ts > self._cache_ttl:
            return []
        items = data.get("candles") or []
        candles: List[Candle] = []
        for item in items:
            try:
                t = datetime.fromisoformat(item["time"])
                o = float(item["open"])
                h = float(item["high"])
                l = float(item["low"])
                c = float(item["close"])
                v = float(item["volume"])
            except Exception:
                continue
            candles.append(
                Candle(
                    instrument=symbol,
                    timeframe=timeframe,
                    time=t,
                    open=o,
                    high=h,
                    low=l,
                    close=c,
                    volume=v,
                )
            )
        return candles

    def _save_to_cache(self, symbol: str, timeframe: str, candles: List[Candle]) -> None:
        path = self._cache_path(symbol, timeframe)
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "timeframe": timeframe,
            "candles": [
                {
                    "time": c.time.isoformat(),
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                }
                for c in candles
            ],
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload), encoding="utf-8")
        except Exception:
            return

    def _get_value(self, row, key: str, default: float = 0.0) -> float:
        try:
            val = row[key]
        except KeyError:
            return default
            
        if hasattr(val, "iloc"):
            return float(val.iloc[0])
        return float(val)

    async def fetch_candles(
        self,
        session,
        symbol: str,
        timeframe: str,
        count: int = 200,
    ) -> List[Candle]:
        interval = self._map_timeframe_to_interval(timeframe)
        cache_candles = self._load_from_cache(symbol, timeframe)
        if cache_candles:
            return cache_candles
        period = self._map_interval_to_period(interval)
        
        # Retry mechanism for Yahoo Finance flakiness
        df = None
        last_error = None
        for attempt in range(3):
            try:
                df = await asyncio.to_thread(
                    yf.download,
                    symbol,
                    period=period,
                    interval=interval,
                    progress=False,
                    threads=False,
                )
                if df is not None and not df.empty:
                    break
            except Exception as exc:
                last_error = exc
                self._log.warning("yfinance retry %d/3 failed for %s: %s", attempt + 1, symbol, exc)
                await asyncio.sleep(2)
        
        if df is None or df.empty:
            if last_error:
                 self._log.error("yfinance download failed for %s after 3 attempts: %s", symbol, last_error)
            else:
                 self._log.info("yfinance returned empty data for symbol=%s timeframe=%s", symbol, timeframe)
            return []
        candles: List[Candle] = []
        try:
            df = df.tail(count)
            for ts, row in df.iterrows():
                try:
                    time = ts.to_pydatetime().replace(tzinfo=None)
                    o = self._get_value(row, "Open")
                    h = self._get_value(row, "High")
                    l = self._get_value(row, "Low")
                    c = self._get_value(row, "Close")
                    v = self._get_value(row, "Volume", 0.0)
                except Exception:
                    continue
                candles.append(
                    Candle(
                        instrument=symbol,
                        timeframe=timeframe,
                        time=time,
                        open=o,
                        high=h,
                        low=l,
                        close=c,
                        volume=v,
                    )
                )
        except Exception as exc:
            self._log.warning("yfinance parse error symbol=%s timeframe=%s error=%s", symbol, timeframe, exc)
            return cache_candles
        if not candles:
            return []
        
        # Don't cache if we have very few candles (likely error or partial data)
        if len(candles) < 10:
             self._log.warning("Fetched only %d candles for %s, skipping cache save", len(candles), symbol)
             return candles
             
        self._save_to_cache(symbol, timeframe, candles)
        return candles

    def _map_timeframe_to_interval(self, timeframe: str) -> str:
        tf = timeframe.lower()
        if tf.startswith("m") and tf[1:].isdigit():
            minutes = int(tf[1:])
            if minutes in (1, 2, 5, 15, 30, 60):
                return f"{minutes}m"
        if tf in ("1h", "h1"):
            return "60m"
        if tf in ("1d", "d1", "1day"):
            return "1d"
        return "1d"

    def _map_interval_to_period(self, interval: str) -> str:
        if interval.endswith("m"):
            try:
                minutes = int(interval[:-1])
            except ValueError:
                return "6mo"
            if minutes == 1:
                return "7d"
            if minutes in (2, 5, 15, 30):
                return "60d"
            if minutes >= 60:
                # Yahoo allows up to ~730 days for 1h data
                return "730d"
        if interval == "1d":
            return "max"
        return "6mo"
