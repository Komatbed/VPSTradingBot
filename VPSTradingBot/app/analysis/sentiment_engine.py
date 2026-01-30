import logging
import asyncio
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from dateutil import parser

import aiohttp
import numpy as np

from app.data.yahoo_client import YahooFinanceClient
from app.data.news_client import NewsClient
from app.core.models import SentimentSnapshot

from app.config import SentimentConstants

class SentimentEngine:
    def __init__(self, yahoo_client: YahooFinanceClient, news_client: NewsClient):
        self._yahoo = yahoo_client
        self._news = news_client
        self._log = logging.getLogger("sentiment")
        self._last_snapshot: Optional[SentimentSnapshot] = None
        self._last_update = datetime.min
        self._config = SentimentConstants

    async def get_sentiment(self) -> SentimentSnapshot:
        # Cache check
        if (datetime.utcnow() - self._last_update).total_seconds() < self._config.CACHE_DURATION_SECONDS and self._last_snapshot:
            return self._last_snapshot

        self._log.info("Calculating new sentiment snapshot...")
        
        # 1. Fetch Data
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._yahoo.fetch_candles(session, "^VIX", "1d", count=50),
                self._yahoo.fetch_candles(session, "^GSPC", "1d", count=50),
                self._yahoo.fetch_candles(session, "GC=F", "1d", count=50),
                self._yahoo.fetch_candles(session, "CL=F", "1d", count=50),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
        vix_data = results[0] if isinstance(results[0], list) else []
        spx_data = results[1] if isinstance(results[1], list) else []
        gold_data = results[2] if isinstance(results[2], list) else []
        oil_data = results[3] if isinstance(results[3], list) else []
        
        # 2. Calculate MFI (Market Fear Index)
        mfi_score = 0.0
        mfi_reasons = []
        
        # A. VIX Component
        current_vix = 15.0
        if vix_data:
            current_vix = vix_data[-1].close
            if current_vix < 12:
                mfi_score += self._config.VIX_WEIGHTS["low"]
                mfi_reasons.append(f"VIX bardzo niski ({current_vix:.1f}) - rynek spokojny")
            elif current_vix < 20:
                mfi_score += self._config.VIX_WEIGHTS["normal"]
                mfi_reasons.append(f"VIX w normie ({current_vix:.1f})")
            elif current_vix < 30:
                mfi_score += self._config.VIX_WEIGHTS["fear"]
                mfi_reasons.append(f"VIX podwyższony ({current_vix:.1f}) - rośnie strach")
            else:
                mfi_score += self._config.VIX_WEIGHTS["panic"]
                mfi_reasons.append(f"VIX PANIKA ({current_vix:.1f})!")
        else:
            mfi_score += 30
            mfi_reasons.append("Brak danych VIX")
            
        # B. SPX Momentum
        if spx_data and len(spx_data) > 20:
            closes = [c.close for c in spx_data]
            sma20 = sum(closes[-20:]) / 20
            current_spx = closes[-1]
            if current_spx < sma20:
                mfi_score += 15
                mfi_reasons.append("S&P500 poniżej średniej miesięcznej (korekta)")
            if len(closes) >= 3:
                pct_chg = (closes[-1] - closes[-3]) / closes[-3]
                if pct_chg < -0.02:
                    mfi_score += 20
                    mfi_reasons.append("Gwałtowne spadki na giełdzie USA")
                    
        mfi_score = min(100.0, max(0.0, mfi_score))
        
        # 3. Calculate GTI (Global Tension Index)
        gti_score = 0.0
        gti_reasons = []
        
        # A. News Component
        high_impact_events = []
        if hasattr(self._news, "_events") and self._news._events:
            for ev in self._news._events:
                try:
                    if ev.get("impact") == "High":
                        high_impact_events.append(ev)
                except Exception as e:
                    self._log.warning("Error processing news event for GTI: %s", e)
        
        high_impact_count = len(high_impact_events)
        
        if high_impact_count > 0:
            gti_score += min(40, high_impact_count * 10)
            gti_reasons.append(f"{high_impact_count} wydarzeń High Impact w kalendarzu:")
            
            for ev in high_impact_events[:5]:
                try:
                    dt = parser.parse(ev["date"])
                    time_str = dt.strftime("%H:%M")
                    date_str = dt.strftime("%d.%m")
                    
                    title = ev.get("title", "")
                    currency = ev.get("currency", "")
                    url = ev.get("url", "")
                    
                    link_part = f" [Info]({url})" if url else ""
                    gti_reasons.append(f"`{date_str} {time_str}` {currency} *{title}*{link_part}")
                except Exception:
                    continue
            
            if high_impact_count > 5:
                gti_reasons.append(f"... i {high_impact_count - 5} więcej")
            
        # B. Safe Haven Flows
        if gold_data and len(gold_data) > 5:
            g_closes = [c.close for c in gold_data]
            g_return_5d = (g_closes[-1] - g_closes[-5]) / g_closes[-5]
            if g_return_5d > 0.03:
                gti_score += 20
                gti_reasons.append("Złoto dynamicznie zyskuje (ucieczka do bezpiecznych przystani)")
                
        if oil_data and len(oil_data) > 5:
            o_closes = [c.close for c in oil_data]
            o_return_5d = (o_closes[-1] - o_closes[-5]) / o_closes[-5]
            if o_return_5d > 0.05:
                gti_score += 20
                gti_reasons.append("Ropa drożeje (możliwe napięcia podażowe/geopolityka)")

        gti_score += 20 # Base tension
        gti_score = min(100.0, max(0.0, gti_score))
        
        # 4. Determine Status
        mfi_status = "Niski"
        if mfi_score >= self._config.MFI_THRESHOLDS["extreme"]: mfi_status = "Ekstremalny"
        elif mfi_score >= self._config.MFI_THRESHOLDS["high"]: mfi_status = "Wysoki"
        elif mfi_score >= self._config.MFI_THRESHOLDS["medium"]: mfi_status = "Umiarkowany"
        
        gti_status = "Spokój"
        if gti_score >= self._config.GTI_THRESHOLDS["extreme"]: gti_status = "Krytyczny"
        elif gti_score >= self._config.GTI_THRESHOLDS["high"]: gti_status = "Napięty"
        elif gti_score >= self._config.GTI_THRESHOLDS["medium"]: gti_status = "Podwyższony"
        
        details = mfi_reasons + gti_reasons
        
        snapshot = SentimentSnapshot(
            mfi=mfi_score,
            gti=gti_score,
            mfi_status=mfi_status,
            gti_status=gti_status,
            details=details
        )
        
        self._last_snapshot = snapshot
        self._last_update = datetime.utcnow()
        return snapshot