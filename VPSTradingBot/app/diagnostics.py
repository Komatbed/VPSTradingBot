import asyncio
import logging
import aiohttp
import os
import shutil
import time
import sys
import ast
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from app.config import Config
from app.data.news_client import NewsClient
from app.data.yahoo_client import YahooFinanceClient
from app.analysis.sentiment_engine import SentimentEngine
from app.gamification.engine import GamificationEngine
from app.knowledge.lexicon import LEXICON
from app.knowledge.instruments import INSTRUMENT_CATALOG
from app.data.instrument_universe import FAVORITES

class ConnectivityTester:
    """
    Handles startup connectivity checks for external services.
    """
    
    SOURCES = [
        {
            "name": "Yahoo Finance", 
            "url": "https://query1.finance.yahoo.com/v7/finance/quote?symbols=EURUSD=X", 
            "type": "get",
            "expect_status": 200
        },
        {
            "name": "Forex Factory (Kalendarz)", 
            "url": "https://nfs.faireconomy.media/ff_calendar_thisweek.json", 
            "type": "get",
            "expect_status": 200
        },
        {
            "name": "Google (Internet)", 
            "url": "https://www.google.com", 
            "type": "head",
            "expect_status": 200
        },
        {
            "name": "Telegram API",
            "url": "https://api.telegram.org",
            "type": "head", 
            "expect_status": 200 # usually 200 or 404 is fine for connectivity check, but root gives 200 OK
        }
    ]

    @staticmethod
    async def test_connection(source: Dict[str, Any]) -> Dict[str, Any]:
        """Tests connection to a single source."""
        url = source["url"]
        method = source.get("type", "get")
        timeout = 10
        
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                if method == "head":
                    async with session.head(url, timeout=timeout) as resp:
                        status = resp.status
                else:
                    async with session.get(url, timeout=timeout) as resp:
                        status = resp.status
                        # Read a bit to ensure data flows
                        await resp.read()
                        
                latency_ms = (time.time() - start_time) * 1000
                
                # Check criteria
                expected = source.get("expect_status", 200)
                # Telegram root might return something else, but if we get a response it's "connected"
                # For Yahoo/FF we expect 200.
                
                success = (status == expected) or (source["name"] == "Telegram API" and status in [200, 302, 404])
                
                if success:
                    return {
                        "name": source["name"],
                        "success": True,
                        "latency_ms": latency_ms,
                        "details": f"Status {status}"
                    }
                else:
                    return {
                        "name": source["name"],
                        "success": False,
                        "latency_ms": latency_ms,
                        "details": f"Status {status} (oczekiwano {expected})"
                    }
                    
        except asyncio.TimeoutError:
            return {
                "name": source["name"],
                "success": False,
                "latency_ms": (time.time() - start_time) * 1000,
                "details": f"Timeout po {timeout}s"
            }
        except Exception as e:
            return {
                "name": source["name"],
                "success": False,
                "latency_ms": 0,
                "details": str(e)
            }

    @classmethod
    async def run_startup_check(cls) -> str:
        """Runs checks for all sources and returns formatted report."""
        results = []
        tasks = [cls.test_connection(src) for src in cls.SOURCES]
        results = await asyncio.gather(*tasks)
        
        lines = ["[System] 📡 Test połączeń po restarcie:"]
        
        for res in results:
            if res["success"]:
                icon = "✅"
                latency = f"{res['latency_ms']:.0f}ms"
                lines.append(f"{icon} {res['name']}: Prawidłowe ({latency})")
            else:
                icon = "❌"
                lines.append(f"{icon} {res['name']}: Nieudane ({res['details']})")
                
        return "\n".join(lines)


class DiagnosticsEngine:
    """
    Performs detailed self-diagnostics of the application components.
    """
    
    def __init__(
        self, 
        config: Config,
        news_client: Optional[NewsClient] = None,
        sentiment_engine: Optional[SentimentEngine] = None,
        gamification_engine: Optional[GamificationEngine] = None
    ):
        self._config = config
        self._log = logging.getLogger("diagnostics")
        
        # Components to check
        self._news_client = news_client
        self._sentiment_engine = sentiment_engine
        self._gamification_engine = gamification_engine
        
        # Dedicated Yahoo Client for checks if needed (but Sentiment has one too)
        self._yahoo_client = YahooFinanceClient()

    async def check_ml_server(self) -> Dict[str, Any]:
        if not self._config.ml_base_url:
            return {"status": "SKIPPED", "details": "ML URL not configured"}
            
        url = f"{self._config.ml_base_url.rstrip('/')}/health"
        try:
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                async with session.get(url, timeout=3) as resp:
                    latency_ms = (time.time() - start_time) * 1000
                    if resp.status == 200:
                        data = await resp.json()
                        return {"status": "OK", "details": data, "latency_ms": latency_ms}
                    return {"status": "ERROR", "details": f"HTTP {resp.status}"}
        except Exception as e:
            return {"status": "ERROR", "details": f"Connection failed: {str(e)}"}

    async def check_yahoo_connection(self) -> Dict[str, Any]:
        """Checks if Yahoo Finance is reachable by fetching 1 candle of EURUSD."""
        try:
            start_time = time.time()
            # Try fetching a major pair that should always be available
            symbol = "EURUSD=X"
            # Fetch enough candles to pass the "min 10 for cache" check in YahooClient
            candles = await self._yahoo_client.fetch_candles(None, symbol, "1d", count=15)
            latency_ms = (time.time() - start_time) * 1000
            
            if candles and len(candles) > 0:
                last_candle = candles[-1]
                return {
                    "status": "OK", 
                    "latency_ms": latency_ms,
                    "last_price": last_candle.close,
                    "last_date": last_candle.time.strftime("%Y-%m-%d")
                }
            else:
                return {"status": "WARNING", "details": "No data returned (empty)"}
        except Exception as e:
            return {"status": "ERROR", "details": str(e)}

    async def check_sentiment_engine(self) -> Dict[str, Any]:
        if not self._sentiment_engine:
            return {"status": "SKIPPED", "details": "Engine not initialized"}
        
        try:
            snapshot = await self._sentiment_engine.get_sentiment()
            return {
                "status": "OK",
                "mfi": snapshot.mfi,
                "gti": snapshot.gti,
                "details": f"{len(snapshot.details)} factors"
            }
        except Exception as e:
            return {"status": "ERROR", "details": str(e)}

    def check_news_client(self) -> Dict[str, Any]:
        if not self._news_client:
            return {"status": "SKIPPED", "details": "Client not initialized"}
        
        try:
            # NewsClient doesn't have async methods for status, it loads on init
            events = getattr(self._news_client, "_events", [])
            last_update = getattr(self._news_client, "_last_update", datetime.min.replace(tzinfo=timezone.utc))
            
            status = "OK" if events else "WARNING"
            
            # Calculate age safely (handle timezone awareness)
            now_utc = datetime.now(timezone.utc)
            if last_update.tzinfo is None:
                last_update = last_update.replace(tzinfo=timezone.utc)
                
            age = (now_utc - last_update).total_seconds() / 60
            
            return {
                "status": status,
                "events_count": len(events),
                "last_update_age_min": int(age)
            }
        except Exception as e:
            return {"status": "ERROR", "details": str(e)}

    def check_system_resources(self) -> Dict[str, Any]:
        try:
            # Disk Usage
            total, used, free = shutil.disk_usage(".")
            free_gb = free / (1024**3)
            
            return {
                "disk_free_gb": f"{free_gb:.1f}",
                "status": "OK" if free_gb > 1.0 else "WARNING (Low Disk)"
            }
        except Exception as e:
            return {"status": "ERROR", "details": str(e)}

    def check_files(self) -> Dict[str, str]:
        paths = {
            "Economic Calendar": Path("app/data/economic_calendar.json"),
            "User Profile": Path("app/data/user_profile.json"),
            "ML Model": Path("ml/model.pkl"),
            "Config (.env)": Path(".env")
        }
        
        results = {}
        for name, path in paths.items():
            if path.exists():
                size_kb = path.stat().st_size / 1024
                results[name] = f"OK ({size_kb:.1f} KB)"
            else:
                results[name] = "MISSING ❌"
        return results

    def check_modules(self) -> Dict[str, str]:
        return {
            "Lexicon": f"Loaded ({len(LEXICON)} terms)",
            "Instrument Catalog": f"Loaded ({len(INSTRUMENT_CATALOG)} items)",
            "Configured Instruments": f"{len(self._config.instruments)} symbols",
            "Favorites": f"{len(FAVORITES)} symbols",
            "Mode": self._config.mode.upper(),
            "Timeframe": self._config.timeframe
        }
        
    def check_codebase_integrity(self) -> Dict[str, Any]:
        """Scans all .py files in app/ directory for syntax errors and load status."""
        root_dir = Path("app")
        results = {
            "total_files": 0,
            "syntax_errors": [],
            "loaded_modules": 0,
            "unloaded_modules": [],
            "scanned_files": []
        }
        
        try:
            for file_path in root_dir.rglob("*.py"):
                # Skip __init__.py files as requested
                if file_path.name == "__init__.py":
                    continue

                results["total_files"] += 1
                
                # Check 1: Syntax
                try:
                    content = file_path.read_text(encoding="utf-8")
                    ast.parse(content)
                except SyntaxError as e:
                    results["syntax_errors"].append(f"{file_path.name}: {e.msg} (Line {e.lineno})")
                    continue
                except Exception as e:
                    results["syntax_errors"].append(f"{file_path.name}: Read Error {str(e)}")
                    continue
                
                # Check 2: Loaded in sys.modules
                # Construct module path: app/data/file.py -> app.data.file
                parts = file_path.with_suffix("").parts
                module_name = ".".join(parts)
                
                is_loaded = module_name in sys.modules
                
                # Special handling for entry point
                if not is_loaded and module_name == "app.main":
                    # app.main is usually loaded as __main__
                    if "__main__" in sys.modules:
                        is_loaded = True

                if is_loaded:
                    results["loaded_modules"] += 1
                else:
                    results["unloaded_modules"].append(module_name)
                    
                results["scanned_files"].append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "loaded": is_loaded
                })
                
            return results
        except Exception as e:
            self._log.error(f"Codebase check failed: {e}")
            return {"error": str(e)}

    async def run_full_diagnostics(self) -> str:
        """Runs all checks and returns a formatted report string."""
        self._log.info("Running full system diagnostics...")
        
        # Run checks in parallel where possible
        ml_status, yahoo_status, sentiment_status = await asyncio.gather(
            self.check_ml_server(),
            self.check_yahoo_connection(),
            self.check_sentiment_engine()
        )
        
        news_status = self.check_news_client()
        system_status = self.check_system_resources()
        files_status = self.check_files()
        modules_status = self.check_modules()
        codebase_status = await asyncio.to_thread(self.check_codebase_integrity)
        
        # Build Report
        lines = ["🚑 **RAPORT DIAGNOSTYCZNY**", ""]
        
        # 1. System & Resources
        lines.append("🖥️ **SYSTEM**")
        lines.append(f"• Mode: {modules_status['Mode']} ({modules_status['Timeframe']})")
        lines.append(f"• Disk Free: {system_status.get('disk_free_gb', '?')} GB")
        if system_status.get("status") != "OK":
            lines.append(f"• Alert: {system_status.get('status')}")
        lines.append("")

        # 2. Connectivity & Data
        lines.append("🌐 **DANE RYNKOWE**")
        
        # Yahoo
        y_icon = "✅" if yahoo_status["status"] == "OK" else "❌"
        lines.append(f"{y_icon} **Yahoo Finance**")
        if yahoo_status["status"] == "OK":
            lines.append(f"   Ping: {yahoo_status['latency_ms']:.0f}ms")
            lines.append(f"   Data: {yahoo_status['last_date']} ({yahoo_status['last_price']})")
        else:
            lines.append(f"   Error: {yahoo_status.get('details')}")
            
        # Sentiment
        s_icon = "✅" if sentiment_status["status"] == "OK" else "❌"
        lines.append(f"{s_icon} **Sentiment Engine**")
        if sentiment_status["status"] == "OK":
            lines.append(f"   MFI: {sentiment_status['mfi']:.0f} | GTI: {sentiment_status['gti']:.0f}")
        else:
            lines.append(f"   Error: {sentiment_status.get('details')}")

        # News
        n_icon = "✅" if news_status["status"] == "OK" else "⚠️"
        lines.append(f"{n_icon} **News Client**")
        if news_status["status"] == "ERROR":
            lines.append(f"   Error: {news_status.get('details')}")
        else:
            lines.append(f"   Events: {news_status.get('events_count', 0)}")
            lines.append(f"   Age: {news_status.get('last_update_age_min', 0)} min")
        lines.append("")

        # 3. AI & ML
        lines.append("🧠 **ML ADVISOR**")
        if ml_status["status"] == "OK":
            details = ml_status["details"]
            model_loaded = "✅" if details.get("model_loaded") else "❌"
            mode = details.get("mode", "Unknown")
            lines.append(f"• Status: ONLINE ✅ ({ml_status.get('latency_ms', 0):.0f}ms)")
            lines.append(f"• Model Loaded: {model_loaded}")
            lines.append(f"• Logic Mode: {mode}")
        else:
            lines.append(f"• Status: OFFLINE ❌")
            lines.append(f"• Error: {ml_status.get('details')}")
        lines.append("")

        # 4. Integrity
        lines.append("📂 **INTEGRALNOŚĆ**")
        for name, status in files_status.items():
            icon = "✅" if "OK" in status else "❌"
            lines.append(f"• {name}: {status}")
        lines.append("")
        
        # Codebase Integrity
        lines.append("🐍 **KOD ŹRÓDŁOWY (.py)**")
        if "error" in codebase_status:
             lines.append(f"⚠️ Scan Failed: {codebase_status['error']}")
        else:
            total = codebase_status.get("total_files", 0)
            loaded = codebase_status.get("loaded_modules", 0)
            errors = codebase_status.get("syntax_errors", [])
            
            status_icon = "✅" if not errors else "❌"
            lines.append(f"{status_icon} **Integrity Check**")
            lines.append(f"   Files Scanned: {total}")
            lines.append(f"   Loaded Modules: {loaded}/{total}")
            
            unloaded = codebase_status.get("unloaded_modules", [])
            if unloaded:
                lines.append(f"   ⚠️ Unloaded Modules ({len(unloaded)}):")
                for mod in unloaded[:10]:
                    lines.append(f"     - {mod}")
                if len(unloaded) > 10:
                    lines.append(f"     ... +{len(unloaded)-10} more")

            if errors:
                lines.append(f"   ⚠️ SYNTAX ERRORS ({len(errors)}):")
                for err in errors[:5]:  # Show max 5 errors
                    lines.append(f"     - {err}")
                if len(errors) > 5:
                    lines.append(f"     ... and {len(errors)-5} more")
            else:
                lines.append("   Syntax: OK (All files)")

        return "\n".join(lines)

if __name__ == "__main__":
    # Allow running diagnostics from CLI
    async def main():
        from app.config import Config
        from app.data.news_client import NewsClient
        from app.analysis.sentiment_engine import SentimentEngine
        from app.data.yahoo_client import YahooFinanceClient
        from app.gamification.engine import GamificationEngine
        from app.core.event_bus import EventBus

        print("🚑 Uruchamianie diagnostyki CLI...")
        cfg = Config.from_env()
        event_bus = EventBus()
        news = NewsClient(event_bus)
        yahoo = YahooFinanceClient()
        sentiment = SentimentEngine(yahoo, news)
        gamification = GamificationEngine()
        
        diag = DiagnosticsEngine(cfg, news, sentiment, gamification)
        report = await diag.run_full_diagnostics()
        print("\n" + report)

    asyncio.run(main())
