import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict

from app.analysis.sentiment_engine import SentimentEngine
from app.data.news_client import NewsClient
from app.data.yahoo_client import YahooFinanceClient

class BriefingService:
    def __init__(self, sentiment_engine: SentimentEngine, news_client: NewsClient, yahoo_client: YahooFinanceClient):
        self._sentiment = sentiment_engine
        self._news = news_client
        self._yahoo = yahoo_client
        self._log = logging.getLogger("briefing")

    async def generate_briefing(self) -> str:
        self._log.info("Generating world briefing...")
        
        # 1. Gather Data in Parallel
        # We need a session for yahoo calls
        async with aiohttp.ClientSession() as session:
            sentiment_task = self._sentiment.get_sentiment()
            
            # Key Markets Fetch
            # S&P500, NASDAQ, GOLD, BITCOIN, EURUSD
            tickers = ["^GSPC", "^IXIC", "GC=F", "BTC-USD", "EURUSD=X"]
            market_tasks = []
            
            for t in tickers:
                market_tasks.append(self._yahoo.fetch_candles(session, t, "1d", count=2))
            
            # Execute all
            # Note: get_sentiment handles its own session if needed, but here we call it directly.
            # Wait... SentimentEngine.get_sentiment creates its own session. That's fine.
            
            # We wrap yahoo calls in a list
            results = await asyncio.gather(sentiment_task, *market_tasks, return_exceptions=True)
            
        sentiment_snap = results[0]
        market_data = results[1:] # List of lists of candles (or exceptions)
        
        # 2. Format Sentiment
        sent_text = ""
        if isinstance(sentiment_snap, Exception) or not sentiment_snap:
             sent_text = "⚠️ Nie udało się pobrać sentymentu.\n"
             self._log.error(f"Sentiment error: {sentiment_snap}")
        else:
            mfi_icon = "🟢" if sentiment_snap.mfi < 40 else ("🟡" if sentiment_snap.mfi < 70 else "🔴")
            gti_icon = "🟢" if sentiment_snap.gti < 40 else ("🟡" if sentiment_snap.gti < 70 else "🔴")
            
            sent_text = (
                f"{mfi_icon} **MFI (Strach):** `{sentiment_snap.mfi:.0f}/100` ({sentiment_snap.mfi_status})\n"
                f"{gti_icon} **GTI (Napięcie):** `{sentiment_snap.gti:.0f}/100` ({sentiment_snap.gti_status})\n"
            )
            if sentiment_snap.details:
                # Take only first 2 details to keep it short
                details_short = sentiment_snap.details[:2]
                sent_text += f"_{'; '.join(details_short)}_\n"

        # 3. Format Markets
        market_text = ""
        names = ["S&P500", "NASDAQ", "GOLD", "BITCOIN", "EUR/USD"]
        
        for i, candles in enumerate(market_data):
            name = names[i]
            if isinstance(candles, list) and len(candles) >= 2:
                prev = candles[-2].close
                curr = candles[-1].close
                pct = ((curr - prev) / prev) * 100
                icon = "🟢" if pct > 0 else "🔴"
                market_text += f"{icon} **{name}:** `{pct:+.2f}%`\n"
            else:
                market_text += f"⚪ **{name}:** `n/a`\n"

        # 4. Format News
        events = self._news.get_upcoming_events(limit=3, min_impact="High")
        news_text = ""
        if events:
            news_text = "\n📅 **Kalendarz (High Impact):**\n"
            for e in events:
                news_text += f"🔸 `{e['time_str']}` {e['country']} - {e['title']}\n"
        else:
            news_text = "\n📅 **Kalendarz:**\n🔸 Brak danych High Impact na dziś.\n"

        # 5. Assemble
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        msg = (
            f"🌍 **WORLD BRIEFING** | {now_str}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{sent_text}\n"
            f"📊 **Rynki (24h):**\n"
            f"{market_text}"
            f"{news_text}\n"
            "💡 _Wpisz /fear aby zobaczyć szczegóły sentymentu._"
        )
        
        return msg