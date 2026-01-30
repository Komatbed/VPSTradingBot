import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import aiohttp
from datetime import datetime

from app.data.yahoo_client import YahooFinanceClient
from .models import RegimeType, MarketSnapshot, AssetContext
from .content import REGIME_TEMPLATES, MACRO_DRIVERS, HISTORICAL_CONTEXT

class MarketRegimeEngine:
    TICKERS = {
        "EQUITIES": "^GSPC", # S&P 500
        "BONDS": "TLT",      # 20+ Year Treasury
        "GOLD": "GC=F",      # Gold
        "VIX": "^VIX",       # Volatility
        "USD": "DX-Y.NYB"    # Dollar Index
    }
    
    REGIONAL_TICKERS = {
        "POLAND": ["WIG20.WA", "WIG20"], # WIG20
        "EUROPE": ["^STOXX50E", "EURO STOXX 50"], # Euro Stoxx 50
        "ASIA": ["^N225", "NIKKEI 225"], # Nikkei 225
        "US": ["^GSPC", "S&P 500"], # S&P 500
        "GLOBAL": ["VT", "GLOBAL (VT)"] # Vanguard Total World Stock
    }

    def __init__(self, yahoo_client: YahooFinanceClient):
        self._yahoo = yahoo_client
        self._log = logging.getLogger("market_regime")

    async def analyze_regime(self) -> str:
        """Analyzes market data and returns a formatted report."""
        try:
            async with aiohttp.ClientSession() as session:
                data = await self._fetch_data(session)
            
            # Even if data is partial, try to produce a result
            if not data:
                return "⚠️ Nie udało się pobrać danych rynkowych do analizy (sprawdź połączenie z Yahoo Finance)."

            snapshot = self._determine_regime(data)
            report = self._format_report(snapshot)
            return report
        except Exception as e:
            self._log.error(f"Error in analyze_regime: {e}", exc_info=True)
            return f"⚠️ Wystąpił błąd podczas analizy rynku: {str(e)}"

    async def _fetch_data(self, session: aiohttp.ClientSession) -> Dict[str, List]:
        results = {}
        # Fetch standard macro tickers
        for key, ticker in self.TICKERS.items():
            candles = await self._yahoo.fetch_candles(session, ticker, "1d", count=300)
            if candles and len(candles) > 200:
                results[key] = candles
            else:
                self._log.warning(f"Insufficient data for {key} ({ticker}). Got {len(candles) if candles else 0} candles.")
        
        # Fetch regional tickers
        for region, (ticker, name) in self.REGIONAL_TICKERS.items():
             candles = await self._yahoo.fetch_candles(session, ticker, "1d", count=300)
             if candles and len(candles) > 10: # We might accept less data for regions just for current price/short trend
                 results[f"REGION_{region}"] = candles
             else:
                 self._log.warning(f"Insufficient data for REGION_{region} ({ticker}).")
                 
        return results

    def _determine_regime(self, data: Dict[str, List]) -> MarketSnapshot:
        # 1. Calculate Trends
        trends = {}
        prices = {}
        
        for key, candles in data.items():
            # Convert to DataFrame for easy rolling calcs
            records = [
                {"close": c.close, "time": c.time} 
                for c in candles
            ]
            df = pd.DataFrame(records)
            if df.empty:
                continue
            
            # Ensure numeric
            df['close'] = pd.to_numeric(df['close'])
            
            current_price = df['close'].iloc[-1]
            sma50 = df['close'].rolling(window=50).mean().iloc[-1]
            sma200 = df['close'].rolling(window=200).mean().iloc[-1]
            
            # Weekly change (5 candles)
            if len(df) >= 6:
                week_ago = df['close'].iloc[-6]
                change_1w = ((current_price - week_ago) / week_ago) * 100
            else:
                change_1w = 0.0

            # Basic Trend Determination
            trends[key] = {
                "price": current_price,
                "sma50": sma50,
                "sma200": sma200,
                "change_1w": change_1w,
                "bullish_long": current_price > sma200 if not np.isnan(sma200) else False,
                "bullish_short": current_price > sma50 if not np.isnan(sma50) else False
            }
            prices[key] = current_price

        # 2. Logic Matrix (Simplified Global Macro)
        # Default to UNCERTAIN if critical data is missing
        regime = RegimeType.UNCERTAIN
        
        # We need at least Equities and Bonds to make a call
        equities_trend = trends.get("EQUITIES")
        bonds_trend = trends.get("BONDS")
        vix_val = prices.get("VIX", 20.0) # Default to 20 if missing

        if equities_trend and bonds_trend:
            eq_bull = equities_trend["bullish_long"]
            bonds_bull = bonds_trend["bullish_long"] # Bullish bonds = Lower Yields
            
            # Heuristic Decision Tree
            if eq_bull and not bonds_bull:
                # Stocks UP, Bonds DOWN (Yields UP) -> Growth is strong, rates staying high
                # This is "Reflation" or "Late Cycle"
                if vix_val < 20:
                    regime = RegimeType.SOFT_LANDING # Optimistic Late Cycle
                else:
                    regime = RegimeType.REFLATION # Overheating
            
            elif eq_bull and bonds_bull:
                # Stocks UP, Bonds UP (Yields DOWN) -> Goldilocks
                regime = RegimeType.SOFT_LANDING
                
            elif not eq_bull and bonds_bull:
                # Stocks DOWN, Bonds UP (Yields DOWN) -> Flight to safety
                regime = RegimeType.RECESSION
                
            elif not eq_bull and not bonds_bull:
                # Stocks DOWN, Bonds DOWN (Yields UP) -> Liquidity Shock / Stagflation
                regime = RegimeType.STAGFLATION

        # 3. Retrieve Template
        template = REGIME_TEMPLATES.get(regime.value, REGIME_TEMPLATES[RegimeType.UNCERTAIN.value])
        
        # 4. Prepare Regional Data for Snapshot
        # Store full trend info for regions to be used in formatting
        regional_trends = {}
        for region in self.REGIONAL_TICKERS.keys():
             k = f"REGION_{region}"
             if k in trends:
                 regional_trends[region] = trends[k]

        snapshot = MarketSnapshot(
            regime=regime,
            drivers=MACRO_DRIVERS,
            baskets=template["baskets"],
            explanation=template["description"],
            metrics={k: f"{v['price']:.2f}" for k, v in trends.items() if not k.startswith("REGION_")}
        )
        # Attach regional trends to snapshot (hacky but effective for now)
        snapshot.regional_trends = regional_trends
        return snapshot

    def _format_report(self, snapshot: MarketSnapshot) -> str:
        r_val = snapshot.regime.value
        template = REGIME_TEMPLATES.get(r_val, REGIME_TEMPLATES[RegimeType.UNCERTAIN.value])
        
        lines = []
        lines.append(f"🌍 **GLOBAL MACRO & MARKET REGIME ANALYSIS**")
        lines.append(f"📅 *{datetime.utcnow().strftime('%Y-%m-%d')}*")
        lines.append(f"🔍 **Detected Regime: {r_val}**")
        lines.append("")
        
        lines.append("1. **CURRENT MARKET REGIME (HIGH-LEVEL)**")
        lines.append(f"{snapshot.explanation}")
        lines.append("")
        
        lines.append("2. **KEY MACRO DRIVERS**")
        for driver in snapshot.drivers:
            lines.append(f"• {driver}")
        lines.append("")
        
        lines.append("3. **REGIONAL MARKET OVERVIEW**")
        if hasattr(snapshot, "regional_trends") and snapshot.regional_trends:
            for region, data in snapshot.regional_trends.items():
                price = data["price"]
                chg = data["change_1w"]
                bull = data["bullish_long"]
                
                # Visuals
                icon = "🟢" if bull else "🔴"
                trend_arrow = "↗️" if chg > 0 else "↘️"
                chg_str = f"{chg:+.2f}%"
                
                # Contextual advice based on region
                advice = ""
                if region == "POLAND":
                    advice = "Check WIG20/mWIG40 strength."
                elif region == "EUROPE":
                    advice = "Watch ECB policy & energy prices."
                elif region == "ASIA":
                    advice = "Watch USDJPY & China stimulus."
                elif region == "US":
                    advice = "Driven by Tech/AI & Fed."
                elif region == "GLOBAL":
                    advice = "Broad market health proxy."
                
                lines.append(f"**{region}** {icon} {trend_arrow} ({chg_str})")
                lines.append(f"   Price: {price:.0f} | Trend: {'BULL' if bull else 'BEAR'} (Long-term)")
                lines.append(f"   💡 *{advice}*")
        else:
            lines.append("⚠️ Regional data unavailable.")
        lines.append("")

        lines.append("4. **MARKET BEHAVIOR EXPLANATION**")
        lines.append(template["behavior"])
        lines.append("")
        
        lines.append("5. **PORTFOLIO BASKETS**")
        for name, tickers in snapshot.baskets.items():
            t_str = ", ".join(tickers)
            lines.append(f"• **{name}:** `{t_str}`")
        lines.append("")
        
        lines.append("6. **WHAT TO BE CAREFUL ABOUT**")
        lines.append(template["caution"])
        lines.append("")
        
        lines.append("7. **HISTORICAL CONTEXT**")
        lines.append(HISTORICAL_CONTEXT.get(r_val, "No direct parallel."))
        
        return "\n".join(lines)
