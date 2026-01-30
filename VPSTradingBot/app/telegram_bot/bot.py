import asyncio
import logging
import sys
import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List
from dateutil import parser

import aiohttp

from app.config import Config, GamificationConstants
from app.core.event_bus import EventBus
from app.core.models import Event, EventType, FinalDecision, UserActionType, UserDecisionRecord, TradeRecord
from app.data.instrument_universe import FAVORITES, INSTRUMENT_METADATA, add_favorite, remove_favorite
from app.data.tradingview_mapping import get_display_name, to_tradingview_symbol
from app.backtest_runner import BacktestEngine, run_backtest
from app.data.yahoo_client import YahooFinanceClient
from app.learning.engine import LearningEngine
from app.ml.client import MlAdvisorClient
from app.knowledge.lexicon import LEXICON, TRADING_TIPS
from app.knowledge.instruments import get_instrument_info, INSTRUMENT_CATALOG
from app.data.news_client import NewsClient
from app.analysis.sentiment_engine import SentimentEngine
from app.analysis.community_sentiment import CommunitySentimentManager
from app.analysis.briefing import BriefingService
from app.instrument_stats_builder import InstrumentStatsBuilder
from app.knowledge.dekalog import DEKALOG
from app.knowledge.manual import USER_MANUAL
from app.knowledge.info_hub import InfoHub
from app.knowledge.cards import KnowledgeDeck
from app.gamification.engine import GamificationEngine
from app.analysis.market_regime import MarketRegimeEngine
from app.diagnostics import DiagnosticsEngine
from app.notifications.alert_manager import AlertManager
import random





class TelegramBot:
    def __init__(
        self,
        config: Config,
        event_bus: EventBus,
        news_client: Optional[NewsClient] = None,
    ) -> None:
        self._config = config
        self._event_bus = event_bus
        self._news_client = news_client or NewsClient()
        self._community_sentiment = CommunitySentimentManager()
        self._info_hub = InfoHub()
        self._cards = KnowledgeDeck()
        self._log = logging.getLogger("telegram")
        self._offset: Optional[int] = None
        self._last_explanation: Optional[str] = None
        # self._event_bus.subscribe(EventType.EXPLANATION_PRE_TRADE, self._on_explanation_event)
        self._event_bus.subscribe(EventType.DECISION_READY, self._on_decision_ready)
        self._event_bus.subscribe(EventType.TELEGRAM_COMMAND, self._on_telegram_command)
        self._event_bus.subscribe(EventType.USER_DECISION, self._on_user_decision)
        self._event_bus.subscribe(EventType.ECONOMIC_EVENT_IMMINENT, self._on_economic_event)
        self._event_bus.subscribe(EventType.TRADE_COMPLETED, self._on_trade_completed)
        
        # Cache for throttling messages: key=(instrument, direction), value=timestamp
        self._last_sent: Dict[str, float] = {}

        # Cache for top3 command: instrument -> (FinalDecision, timestamp)
        self._decision_cache: Dict[str, Tuple[FinalDecision, datetime]] = {}
        
        # Debug stats: "NO_TRADE" reasons
        # Key: instrument, Value: (count, last_reason, timestamp)
        self._rejection_stats: Dict[str, Dict[str, Any]] = {}
        
        # self._news_client is already set in line 48
        yahoo_client = YahooFinanceClient()
        self._sentiment_engine = SentimentEngine(yahoo_client, self._news_client)
        self._briefing_service = BriefingService(self._sentiment_engine, self._news_client, yahoo_client)
        self._stats_builder = InstrumentStatsBuilder(config)
        
        # Gamification engine (XP, profile, rewards)
        self._gamification = GamificationEngine()
        
        # Market Regime Engine
        self._market_regime = MarketRegimeEngine(yahoo_client)
        
        # Alerts
        self._alert_manager = AlertManager()
        
        # Diagnostics
        self._diagnostics = DiagnosticsEngine(
            config, 
            self._news_client, 
            self._sentiment_engine, 
            self._gamification
        )
        
        # Updater
        self._updater = UpdateManager()


    def _get_rank_flavor(self, chat_id: str) -> str:
        try:
            profile = self._gamification.get_profile(chat_id)
            level = getattr(profile, "level", 1)
        except Exception:
            level = 1
        
        for threshold, msg in GamificationConstants.MOTIVATIONAL_MESSAGES:
            if level < threshold:
                return msg
        
        return "" # Masters don't need fluff

    async def _handle_debug_command(self, session: aiohttp.ClientSession, chat_id: str) -> None:
        """Shows why trades are being rejected."""
        if not self._rejection_stats:
            await self._send_message(session, chat_id, "🐛 Brak danych diagnostycznych (bot dopiero wystartował?).")
            return

        lines = ["🐛 **DEBUG REPORT** | Ostatnie odrzucenia", ""]
        
        # Sort by timestamp DESC
        sorted_stats = sorted(
            self._rejection_stats.items(), 
            key=lambda x: x[1]['timestamp'], 
            reverse=True
        )[:15] # Show last 15
        
        for instrument, data in sorted_stats:
            age = (datetime.utcnow() - data['timestamp']).total_seconds() / 60
            lines.append(f"🔸 **{instrument}** | {int(age)} min temu")
            lines.append(f"   ❓ **Powód:** {data['reason']}")
            lines.append(f"   🔢 **Seria:** {data['count']}")
            
        await self._send_message(session, chat_id, "\n".join(lines))

    def _api_url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self._config.telegram_bot_token}/{method}"

    async def _send_message(self, session: aiohttp.ClientSession, chat_id: str, text: str, reply_markup: Optional[Dict] = None) -> None:
        url = self._api_url("sendMessage")
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            async with session.post(url, json=payload, timeout=10) as resp:
                if resp.status >= 400:
                    try:
                        body = await resp.text()
                    except Exception:
                        body = "<no body>"
                    self._log.warning("sendMessage failed with status %s body=%s", resp.status, body)
        except Exception as exc:
            self._log.warning("sendMessage error %s", exc)

    async def send_system_message(self, text: str) -> None:
        if not self._config.telegram_bot_token or not self._config.telegram_chat_id:
            return
        async with aiohttp.ClientSession() as session:
            await self._send_message(session, self._config.telegram_chat_id, text)

    async def _on_explanation_event(self, event: Event) -> None:
        if not isinstance(event.payload, str):
            return
        self._last_explanation = event.payload
        if not self._config.telegram_bot_token or not self._config.telegram_chat_id:
            return
        async with aiohttp.ClientSession() as session:
            await self._send_message(session, self._config.telegram_chat_id, event.payload)

    async def _handle_alerts_command(self, session: aiohttp.ClientSession, chat_id: str, args: List[str]) -> None:
        """
        Manage alerts:
        /alerts - list
        /alerts add currency USD
        /alerts remove category Inflation
        /alerts clear
        """
        if not args:
            # List alerts
            alerts = self._alert_manager.get_user_alerts(chat_id)
            curs = alerts.get("currencies", [])
            cats = alerts.get("categories", [])
            
            lines = ["🔔 **TWOJE ALERTY**", ""]
            if not curs and not cats:
                lines.append("🔕 Brak aktywnych alertów.")
                lines.append("Aby dodać: `/alerts add currency USD` lub `/alerts add category Inflation`")
            else:
                if curs:
                    lines.append(f"💱 **Waluty:** {', '.join(curs)}")
                if cats:
                    lines.append(f"🏷️ **Kategorie:** {', '.join(cats)}")
                lines.append("")
                lines.append("Aby usunąć: `/alerts remove currency USD`")
            
            await self._send_message(session, chat_id, "\n".join(lines))
            return

        action = args[0].lower()
        
        if action == "clear":
            self._alert_manager.clear_alerts(chat_id)
            await self._send_message(session, chat_id, "🔕 Wszystkie alerty zostały usunięte.")
            return
            
        if len(args) < 3:
            await self._send_message(session, chat_id, "⚠️ Użycie: `/alerts add|remove currency|category VALUE`")
            return
            
        target_type = args[1].lower() # currency / category
        value = args[2] # USD / Inflation
        
        # Normalize value if needed (e.g. uppercase currency)
        if target_type == "currency":
            value = value.upper()
        elif target_type == "category":
            value = value.capitalize() # e.g. inflation -> Inflation
            
        if action == "add":
            if self._alert_manager.add_alert(chat_id, target_type, value):
                await self._send_message(session, chat_id, f"✅ Dodano alert: {target_type} **{value}**")
            else:
                await self._send_message(session, chat_id, f"ℹ️ Alert już istnieje: {target_type} **{value}**")
                
        elif action == "remove":
            if self._alert_manager.remove_alert(chat_id, target_type, value):
                await self._send_message(session, chat_id, f"🗑️ Usunięto alert: {target_type} **{value}**")
            else:
                await self._send_message(session, chat_id, f"⚠️ Nie znaleziono alertu: {target_type} **{value}**")
        else:
             await self._send_message(session, chat_id, "⚠️ Nieznana akcja. Użyj: add, remove, clear")

    async def _handle_portfolio_command(self, chat_id: str) -> None:
        """Displays active positions from PortfolioManager as individual cards."""
        from app.config import Paths
        import json
        
        if not Paths.ACTIVE_TRADES.exists():
             async with aiohttp.ClientSession() as session:
                await self._send_message(session, chat_id, "📭 Twój portfel jest pusty.")
                return
        
        try:
            content = Paths.ACTIVE_TRADES.read_text(encoding="utf-8")
            if not content.strip():
                 async with aiohttp.ClientSession() as session:
                    await self._send_message(session, chat_id, "📭 Twój portfel jest pusty.")
                    return
            
            positions = json.loads(content)
            if not positions:
                async with aiohttp.ClientSession() as session:
                    await self._send_message(session, chat_id, "📭 Twój portfel jest pusty.")
                    return
            
            # Calculate Total Stats
            total_profit_r = 0.0
            total_positions = len(positions)
            
            for p in positions:
                total_profit_r += p.get("current_profit_r", 0.0)
            
            total_color = "🟢" if total_profit_r >= 0 else "🔴"
            
            # 1. Send Summary Header with Legend
            summary_msg = (
                f"💼 **TWÓJ PORTFEL (Wirtualny)**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 **Razem:** {total_color} {total_profit_r:+.2f}R\n"
                f"🔢 **Pozycje:** {total_positions}\n\n"
                f"ℹ️ **Legenda:**\n"
                f"❌ - Zamknij pozycję manualnie\n"
                f"📊 - Otwórz wykres TradingView\n"
            )
            
            # Add footer with balance
            profile = self._gamification.get_profile(chat_id)
            balance = getattr(profile, "balance", 10000.0)
            summary_msg += f"\n💳 Saldo konta: ${balance:,.2f}"
            
            async with aiohttp.ClientSession() as session:
                await self._send_message(session, chat_id, summary_msg)
                
                # 2. Send individual cards
                for p in positions:
                    symbol = p.get("instrument")
                    trade_id = p.get("trade_id")
                    direction = p.get("direction", "long").upper()
                    entry = p.get("entry_price")
                    curr = p.get("current_price", entry) # Fallback if 0
                    if curr == 0: curr = entry
                    
                    sl = p.get("sl")
                    tp = p.get("tp")
                    profit_r = p.get("current_profit_r", 0.0)
                    
                    # Icon logic
                    emoji = "🟢" if profit_r >= 0 else "🔴"
                    dir_icon = "📈" if direction == "LONG" else "📉"
                    
                    card_text = (
                        f"{dir_icon} **{symbol}** | {direction}\n"
                        f"💰 **Wynik:** {emoji} {profit_r:+.2f}R\n"
                        f"💲 Cena: {curr:.5f} (Wejście: {entry:.5f})\n"
                        f"🛑 SL: {sl:.5f} | 🎯 TP: {tp:.5f}"
                    )
                    
                    keyboard = {
                        "inline_keyboard": [
                            [
                                {"text": "❌ Zamknij", "callback_data": f"port_close:{symbol}:{trade_id}"},
                                {"text": "📊 Wykres", "callback_data": f"port_chart:{symbol}"}
                            ]
                        ]
                    }
                    
                    await self._send_message(session, chat_id, card_text, reply_markup=keyboard)
                    # Small delay to ensure order (though await helps)
                    await asyncio.sleep(0.05)

        except Exception as e:
            self._log.error(f"Error displaying portfolio: {e}")
            async with aiohttp.ClientSession() as session:
                await self._send_message(session, chat_id, "⚠️ Błąd podczas ładowania portfela.")

    async def _on_trade_completed(self, event: Event) -> None:
        """Handles TRADE_COMPLETED event to notify user and update Gamification."""
        trade: TradeRecord = event.payload
        chat_id = self._config.telegram_chat_id
        
        # 1. Notify User
        emoji = "✅" if (trade.profit_loss_r or 0) > 0 else "❌"
        msg = f"{emoji} **ZAMKNIĘTO POZYCJĘ**\n\n"
        msg += f"Instrument: **{trade.instrument}**\n"
        msg += f"Wynik: **{trade.profit_loss_r:+.2f}R** (${trade.profit_loss:+.2f})\n"
        msg += f"Powód: {trade.metadata.get('close_reason', 'Unknown')}\n"
        
        async with aiohttp.ClientSession() as session:
            await self._send_message(session, chat_id, msg)
            
        # 2. Update Gamification (Balance & Streak)
        # We assume profit_loss is the raw PnL amount
        streak_msg = self._gamification.process_trade_result(trade.profit_loss or 0.0)
        
        if streak_msg:
             async with aiohttp.ClientSession() as session:
                await self._send_message(session, chat_id, streak_msg)

    async def _on_user_decision(self, event: Event) -> None:
        """Awards XP for user actions (enter/skip/remind/tv)."""
        record = event.payload
        if not isinstance(record, UserDecisionRecord):
            return
        chat_id = record.chat_id or self._config.telegram_chat_id
        if not self._config.telegram_bot_token or not chat_id:
            return
        
        # Map UserActionType to GamificationConfig event keys
        # XP_TABLE keys: action_enter, action_skip, action_remind, action_tv
        event_key = f"action_{record.action.value}"
        
        xp_msg = self._gamification.register_event(event_key)
        
        if xp_msg:
             async with aiohttp.ClientSession() as session:
                await self._send_message(session, str(chat_id), xp_msg)

    async def _on_economic_event(self, event: Event) -> None:
        """Handles high impact economic news alerts."""
        payload = event.payload
        title = payload.get("title")
        country = payload.get("country")
        currency = payload.get("currency") or country # Fallback to country if currency missing
        minutes = payload.get("minutes")
        url = payload.get("url", "")
        
        link_line = f"🔗 [Szczegóły]({url})\n" if url else ""
        
        msg = (
            f"🚨 **HIGH IMPACT NEWS** 🚨\n\n"
            f"⏰ **Za {int(minutes)} min:** {title} ({country})\n"
            f"{link_line}"
            f"⛔ **Handel {currency} wstrzymany**\n"
            f"⚠️ **Powód:** Niestabilność, rozszerzenie spreadów\n\n"
            f"🎓 _Dla początkujących: W tym czasie algorytmy głupieją, a rynek szarpie. Lepiej stać z boku._"
        )
        
        # Determine recipients
        recipients = set()
        
        # 1. Admin (Always receive High Impact)
        if self._config.telegram_chat_id:
            recipients.add(self._config.telegram_chat_id)
            
        # 2. Subscribed Users
        subscribed = self._alert_manager.get_recipients_for_event(payload)
        recipients.update(subscribed)
        
        if recipients and self._config.telegram_bot_token:
            try:
                async with aiohttp.ClientSession() as session:
                    for chat_id in recipients:
                        await self._send_message(session, str(chat_id), msg)
            except Exception as e:
                self._log.error(f"Failed to send news alert: {e}")


    def _get_throttle_duration(self, timeframe: str) -> float:
        """Returns throttle duration in seconds based on timeframe."""
        tf = timeframe.lower()
        if tf in ("1h", "h1", "60m"):
            return 1800.0  # 30 minutes for H1
        if tf in ("4h", "h4", "240m"):
            return 7200.0  # 2 hours for H4
        if tf in ("1d", "d1", "day"):
            return 21600.0  # 6 hours for D1
        if tf.startswith("m"):
            try:
                minutes = int(tf[1:])
                return minutes * 60.0 * 0.8  # 80% of candle time
            except ValueError:
                pass
        return 300.0  # Default 5 mins

    async def send_message(self, text: str) -> None:
        """Public method to send a message to the default chat."""
        if not self._config.telegram_bot_token or not self._config.telegram_chat_id:
            return
            
        async with aiohttp.ClientSession() as session:
            await self._send_message(session, self._config.telegram_chat_id, text)

    async def _on_decision_ready(self, event: Event) -> None:
        """
        Handles the DECISION_READY event.
        Filters decisions, throttles messages, formats content, and sends to Telegram.
        """
        decision: FinalDecision = event.payload
        instrument = decision.instrument
        if not self._config.telegram_bot_token or not self._config.telegram_chat_id:
            return
        
        # Update cache (used by /top3)
        self._decision_cache[instrument] = (decision, datetime.utcnow())

        if decision.verdict.value == "no_trade":
            # Track rejections for /debug command
            reason = decision.explanation_text or "Brak setupu"
            if instrument in self._rejection_stats:
                last_entry = self._rejection_stats[instrument]
                # If reason is same, increment count
                if last_entry["reason"] == reason:
                     last_entry["count"] += 1
                     last_entry["timestamp"] = datetime.utcnow()
                else:
                    self._rejection_stats[instrument] = {"count": 1, "reason": reason, "timestamp": datetime.utcnow()}
            else:
                self._rejection_stats[instrument] = {"count": 1, "reason": reason, "timestamp": datetime.utcnow()}
            return
        
        direction_val = decision.direction.value if decision.direction else "neutral"

        
        # --- SMART FILTERING ---
        # Only send messages if:
        # 1. Instrument is in FAVORITES and score >= 70
        # 2. Instrument is NOT in FAVORITES and score >= 80 (higher threshold for noise reduction)
        is_favorite = instrument in FAVORITES
        threshold = 70.0 if is_favorite else 80.0
        
        if decision.confidence < threshold:
            self._log.debug(
                "Skipping Telegram message for %s (score %.0f < %.0f, favorite=%s)", 
                instrument, decision.confidence, threshold, is_favorite
            )
            return
        # -----------------------
        
        # --- THROTTLING LOGIC ---
        key = f"{instrument}_{direction_val}"
        last_time = self._last_sent.get(key, 0)
        now = datetime.utcnow().timestamp()
        throttle_duration = self._get_throttle_duration(decision.timeframe)
        
        if now - last_time < throttle_duration:
            self._log.debug(
                "Throttling Telegram message for %s (last sent %.0fs ago, limit %.0fs)", 
                key, now - last_time, throttle_duration
            )
            return
        
        self._last_sent[key] = now
        # ------------------------

        text = await self._format_decision_message(decision)
        keyboard = self._create_decision_keyboard(decision)
        
        async with aiohttp.ClientSession() as session:
            url = self._api_url("sendMessage")
            payload = {
                "chat_id": self._config.telegram_chat_id,
                "text": text,
                "reply_markup": keyboard,
            }
            try:
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status >= 400:
                        try:
                            body = await resp.text()
                        except Exception:
                            body = "<no body>"
                        self._log.warning("sendMessage (decision) failed with status %s body=%s", resp.status, body)
            except Exception as exc:
                self._log.warning("sendMessage (decision) error %s", exc)

    async def _format_decision_message(self, decision: FinalDecision) -> str:
        """Formats the decision message for Telegram."""
        instrument = decision.instrument
        timeframe = decision.timeframe
        
        # Simple direction and emoji
        if decision.direction and decision.direction.value == "long":
            direction_icon = "🟢"
            direction_text = "LONG"
        elif decision.direction and decision.direction.value == "short":
            direction_icon = "🔴"
            direction_text = "SHORT"
        else:
            direction_icon = "⚪"
            direction_text = "NEUTRAL"

        # Confidence color/emoji
        conf = decision.confidence
        conf_icon = "🔥" if conf >= 85 else ("✨" if conf >= 75 else "⚠️")

        tv_link = decision.tradingview_link
        
        self._log.info(
            "Decision ready for Telegram: instrument=%s timeframe=%s direction=%s rr=%.3f confidence=%.0f",
            instrument,
            timeframe,
            direction_text,
            decision.rr,
            decision.confidence,
        )

        # Concise message format
        # {ICON} {DIRECTION} #{SYMBOL} ({NAME}) | {TIMEFRAME}
        display_symbol = get_display_name(instrument)
        inst_info = get_instrument_info(instrument)
        
        # Only add name from inst_info if it's not already in display_symbol
        if inst_info and inst_info.name and "(" not in display_symbol:
             display_symbol = f"{display_symbol} ({inst_info.name})"
        
        header = f"{direction_icon} **{direction_text}** #{display_symbol} | {timeframe}"
        score_line = f"🎯 **Score:** {conf_icon} {decision.confidence:.0f}/100"
        
        # Levels line
        # Entry: ... | SL: ... | TP: ...
        levels = (
            f"📉 **Poziomy:**\n"
            f"   🔹 **Entry:** {decision.entry_price:.2f}\n"
            f"   🛑 **SL:** {decision.sl_price:.2f}\n"
            f"   🚀 **TP:** {decision.tp_price:.2f}"
        )
        
        # RR line
        rr_line = f"⚖️ **R:R:** {decision.rr:.2f}R"
        
        # MFI/GTI Snapshot
        mfi_snap = await self._sentiment_engine.get_sentiment()
        sentiment_line = (
            f"📊 **Sentyment:**\n"
            f"   😨 Fear: {mfi_snap.mfi}\n"
            f"   ⚡ Tension: {mfi_snap.gti}"
        )

        text_lines = [
            header,
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            score_line,
            rr_line,
            "",
            levels,
            "",
            sentiment_line,
            "",
            f"ℹ️ **Uzasadnienie:**\n{decision.explanation_text}",
        ]

        if self._config.educational_mode:
            text_lines.append("")
            text_lines.append("🎓 **ANALIZA EDUKACYJNA**")
            # Add simplified analysis if available in metadata or reconstruction
            
            # Example: Check if specific terms are in explanation and link them
            keywords = ["RSI", "MACD", "EMA", "TREND", "KONSOLIDACJA", "RISK", "REWARD"]
            found_keywords = []
            for kw in keywords:
                if kw in decision.explanation_text.upper():
                    found_keywords.append(kw)
            
            if found_keywords:
                text_lines.append("🔸 **Słowa kluczowe:** " + ", ".join([f"{k}" for k in found_keywords]))
            
            # Instrument Info Injection
            # inst_info already fetched above
            if inst_info:
                text_lines.append(f"\n📘 **Instrument: {inst_info.name}**")
                text_lines.append(f"ℹ️ **Czym jest:** {inst_info.description}")
            
            tip = random.choice(list(TRADING_TIPS.values()))
            text_lines.append(f"\n💡 *Porada:* {tip}")
        
        # User requested removal of the second TradingView link (redundant with button/header)
        # if tv_link:
        #    text_lines.append("")
        #    text_lines.append(f"📊 [TradingView]({tv_link})")

        return "\n".join(text_lines)

    def _create_decision_keyboard(self, decision: FinalDecision) -> Dict[str, Any]:
        """Creates the inline keyboard for the decision message."""
        return {
            "inline_keyboard": [
                [
                    {"text": "✅ WCHODZĘ", "callback_data": f"action:enter:{decision.decision_id}"},
                    {"text": "❌ POMIJAM", "callback_data": f"action:skip:{decision.decision_id}"},
                ],
                [
                    {"text": "👍", "callback_data": f"vote:up:{decision.instrument}"},
                    {"text": "👎", "callback_data": f"vote:down:{decision.instrument}"},
                ],
                [
                    {"text": "🕒 WRÓĆ DO TEGO", "callback_data": f"action:remind:{decision.decision_id}"},
                    {"text": "📊 POKAŻ NA TRADINGVIEW", "callback_data": f"action:tv:{decision.decision_id}"},
                ],
            ]
        }

    async def _on_telegram_command(self, event: Event) -> None:
        command = event.payload
        if not isinstance(command, dict):
            return
        command_type = command.get("type")
        chat_id = command.get("chat_id") or self._config.telegram_chat_id
        if not chat_id:
            return
        if not self._config.telegram_bot_token:
            return
        async with aiohttp.ClientSession() as session:
            if command_type == "why_last_trade":
                text = f"📜 **Wyjaśnienie ostatniej decyzji:**\n\n{self._last_explanation}" if self._last_explanation else "ℹ️ **Info:** Brak zarejestrowanego ostatniego trade’u."
                await self._send_message(session, str(chat_id), text)
            elif command_type == "restartml":
                await self._send_message(session, str(chat_id), "🧠 **System ML:** Przeładowuję model...")
                result = await self._ml_client.reload_model()
                await self._send_message(session, str(chat_id), f"✅ **System ML:** {result}")

            elif command_type == "restart":
                await self._send_message(session, str(chat_id), "🔄 **System:** Restartuję serwer... (wrócę za ok. 15-30s)")
                await asyncio.sleep(1)
                self._log.info("Restart requested via Telegram. Exiting process.")
                sys.exit(0)
            elif command_type == "pause":
                await self._send_message(session, str(chat_id), "Pauza systemu nie jest jeszcze zaimplementowana.")
            elif command_type == "resume":
                await self._send_message(session, str(chat_id), "Wznawianie systemu nie jest jeszcze zaimplementowane.")
            elif command_type == "risk":
                value = command.get("value")
                await self._send_message(
                    session,
                    str(chat_id),
                    f"Zmiana ryzyka nie jest jeszcze w pełni zaimplementowana (wartość={value}).",
                )
            elif command_type == "result":
                value_r = command.get("value_r")
                note = command.get("note")
                if value_r is None:
                    await self._send_message(
                        session,
                        str(chat_id),
                        "Użycie: /result <wynik_w_R> [notatka].",
                    )
                else:
                    # Logic for XP and Penalties
                    xp_msg = None
                    penalty_msg = None
                    
                    note_lower = note.lower() if note else ""
                    
                    is_bad = any(k in note_lower for k in GamificationConstants.JOURNAL_KEYWORDS_BAD)
                    is_good = any(k in note_lower for k in GamificationConstants.JOURNAL_KEYWORDS_GOOD)
                    
                    if is_bad:
                        # Penalty
                        penalty_msg = self._gamification.add_penalty("bad_habit", note)
                        # Still award small XP for logging (Process > Outcome), but flagged
                        xp_msg = self._gamification.register_event("journal_short")
                    elif is_good:
                        xp_msg = self._gamification.register_event("journal_full")
                    else:
                        # Default check
                        event = "journal_full" if note and len(note) > 10 else "journal_short"
                        xp_msg = self._gamification.register_event(event)
                    
                    response = f"Zapisuję wynik trade'u: {value_r}R. Notatka: {note or '-'}"
                    
                    if penalty_msg:
                        response += f"\n\n{penalty_msg}"
                    if xp_msg:
                        response += f"\n\n{xp_msg}"
                    
                    response += self._get_rank_flavor(str(chat_id))
                        
                    await self._send_message(session, str(chat_id), response)
            elif command_type == "result_invalid":
                await self._send_message(
                    session,
                    str(chat_id),
                    "Niepoprawny format. Użyj: /result <wynik_w_R> [notatka].",
                )
            elif command_type == "stats":
                symbol = command.get("symbol")
                if symbol:
                    report = await self._stats_builder.get_stats_for_instrument(symbol)
                    await self._send_message(session, str(chat_id), report)
                else:
                    summary = await self._stats_builder.get_total_summary()
                    await self._send_message(session, str(chat_id), summary)
            elif command_type == "dekalog":
                msg = "📜 **DEKALOG TRADERA**\n\n" + "\n\n".join(DEKALOG)
                await self._send_message(session, str(chat_id), msg)
            elif command_type == "gamify":
                msg = self._gamification.get_progress()
                await self._send_message(session, str(chat_id), msg)
            elif command_type == "alerts":
                args = command.get("args", [])
                await self._handle_alerts_command(session, str(chat_id), args)
            elif command_type in ("diag", "status"):
                await self._send_message(session, str(chat_id), "🚑 **Diagnostyka:** Rozpoczynam pełne sprawdzanie systemu...")
                report = await self._diagnostics.run_full_diagnostics()
                await self._send_message(session, str(chat_id), report)
            elif command_type == "briefing":
                await self._send_message(session, str(chat_id), "📝 **Briefing:** Generuję raport rynkowy...")
                report = await self._briefing_service.generate_briefing()
                
                # Award XP
                xp_msg = self._gamification.register_event("edu_briefing")
                if xp_msg:
                    report += f"\n\n{xp_msg}"
                
                await self._send_message(session, str(chat_id), report)
            elif command_type in ("marketregime", "regime", "macro"):
                await self._send_message(session, str(chat_id), "🌍 **Macro:** Analizuję reżim rynkowy... (to może potrwać chwilę)")
                report = await self._market_regime.analyze_regime()
                await self._send_message(session, str(chat_id), report)
                
                # Optional: Award XP for checking macro
                try:
                    self._gamification.award_xp(str(chat_id), 10, reason="macro_analysis")
                except Exception:
                    pass
            elif command_type == "favorites_add":
                symbols = command.get("symbols") or []
                added = []
                existing = []
                for symbol in symbols:
                    if symbol in FAVORITES:
                        existing.append(symbol)
                    else:
                        add_favorite(symbol)
                        added.append(symbol)
                lines = ["⭐ **ZARZĄDZANIE ULUBIONYMI**", ""]
                if added:
                    lines.append(f"✅ **Dodano:** {', '.join([f'`{s}`' for s in added])}")
                if existing:
                    lines.append(f"ℹ️ **Już na liście:** {', '.join([f'`{s}`' for s in existing])}")
                if not lines[2:]:
                    lines.append("⚠️ Brak symboli do dodania.")
                await self._send_message(session, str(chat_id), "\n".join(lines))
            elif command_type == "favorites_remove":
                symbols = command.get("symbols") or []
                removed = []
                missing = []
                for symbol in symbols:
                    if symbol in FAVORITES:
                        remove_favorite(symbol)
                        removed.append(symbol)
                    else:
                        missing.append(symbol)
                lines = ["⭐ **ZARZĄDZANIE ULUBIONYMI**", ""]
                if removed:
                    lines.append(f"🗑️ **Usunięto:** {', '.join([f'`{s}`' for s in removed])}")
                if missing:
                    lines.append(f"⚠️ **Nie znaleziono:** {', '.join([f'`{s}`' for s in missing])}")
                if not lines[2:]:
                    lines.append("⚠️ Brak symboli do usunięcia.")
                await self._send_message(session, str(chat_id), "\n".join(lines))
            elif command_type == "favorites_list":
                if not FAVORITES:
                    await self._send_message(session, str(chat_id), "📭 **Twoja lista ulubionych jest pusta.**\nUżyj `/fav_add SYMBOL` aby dodać instrumenty.")
                else:
                    lines = [f"⭐ **TWOJE ULUBIONE** ({len(FAVORITES)})", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
                    for symbol in FAVORITES:
                        # Use INSTRUMENT_METADATA directly instead of static FAVORITE_DESCRIPTIONS
                        desc = INSTRUMENT_METADATA.get(symbol, {}).get("name")
                        if desc:
                            lines.append(f"🔸 `{symbol}` - {desc}")
                        else:
                            lines.append(f"🔸 `{symbol}`")
                    await self._send_message(session, str(chat_id), "\n".join(lines))
            elif command_type == "favorites_clear":
                if FAVORITES:
                    # Remove all one by one to trigger save, or clear and save once.
                    # Since we don't have clear_favorites(), we'll copy list and remove.
                    # Or simpler:
                    for s in list(FAVORITES):
                        remove_favorite(s)
                    await self._send_message(session, str(chat_id), "🗑️ **Wyczyszczono listę ulubionych.**")
                else:
                    await self._send_message(session, str(chat_id), "Lista ulubionych jest już pusta.")
            elif command_type == "favorites_invalid":
                await self._send_message(
                    session,
                    str(chat_id),
                    "Użycie: /fav_add SYMBOL1 SYMBOL2 lub /fav_remove SYMBOL1 SYMBOL2.",
                )
            elif command_type == "config":
                c = self._config
                lines = [
                    "⚙️ **Konfiguracja**",
                    f"Tryb: {c.mode}",
                    f"Timeframe: {c.timeframe}",
                    f"Instrumenty: {len(c.instruments)}",
                    f"Edukacja: {'TAK' if c.educational_mode else 'NIE'}",
                    f"Interwał danych: {c.data_poll_interval_seconds}s",
                ]
                await self._send_message(session, str(chat_id), "\n".join(lines))
            elif command_type == "backtest":
                symbol = command.get("symbol")
                timeframe = command.get("timeframe") or self._config.timeframe
                count = command.get("count") or 500
                if not symbol:
                    await self._send_message(
                        session,
                        str(chat_id),
                        "Użycie: /backtest SYMBOL [TIMEFRAME] [LICZBA_ŚWIEC].",
                    )
                else:
                    await self._send_message(
                        session,
                        str(chat_id),
                        f"Uruchamiam backtest dla {symbol} {timeframe} na ostatnich {count} świecach. To może chwilę potrwać.",
                    )
                    summary = await self._run_backtest_for_symbol(symbol, timeframe, int(count))
                    await self._send_message(session, str(chat_id), summary)
                    try:
                        xp_msg = self._gamification.register_event("edu_backtest")
                        if xp_msg:
                            await self._send_message(session, str(chat_id), xp_msg)
                    except Exception as e:
                        self._log.warning("Gamification error (backtest): %s", e)
            elif command_type == "backtest_all":
                # Check Level Gating (Level 5+)
                try:
                    profile = self._gamification.get_profile(chat_id)
                    level = getattr(profile, "level", 1)
                except Exception:
                    level = 1
                
                if level < 5:
                    await self._send_message(
                        session,
                        str(chat_id),
                        f"🔒 **Funkcja zablokowana!**\nBacktest wszystkich instrumentów dostępny od poziomu 5 (Apprentice).\nAktualny poziom: {level}."
                    )
                    return

                timeframe = command.get("timeframe") or "1d"
                await self._send_message(
                    session,
                    str(chat_id),
                    f"Uruchamiam backtest dla wszystkich instrumentów ({timeframe}). To może potrwać kilka minut.",
                )
                symbols = list(dict.fromkeys(self._config.instruments)) if self._config.instruments else []
                if not symbols:
                    await self._send_message(
                        session,
                        str(chat_id),
                        "Brak instrumentów w konfiguracji (Config.instruments).",
                    )
                else:
                    os.environ["BACKTEST_SYMBOLS"] = ",".join(symbols)
                    os.environ["BACKTEST_TIMEFRAME"] = timeframe
                    try:
                        await run_backtest()
                    except Exception as exc:
                        self._log.error("Backtest_all error: %s", exc, exc_info=True)
                        await self._send_message(
                            session,
                            str(chat_id),
                            "Błąd podczas wykonywania backtestu (szczegóły w logach).",
                        )
                    else:
                        out_dir = Path("backtests")
                        summary_path = out_dir / f"summary_{timeframe}.json"
                        if summary_path.exists():
                            try:
                                data = json.loads(summary_path.read_text(encoding="utf-8"))
                            except Exception:
                                await self._send_message(
                                    session,
                                    str(chat_id),
                                    f"Backtest zakończony. Wyniki zapisano w {summary_path}.",
                                )
                            else:
                                lines = [
                                    f"✅ Backtest wszystkich instrumentów ({timeframe}) zakończony.",
                                    "",
                                    "Top 5 wg expectancy:",
                                ]
                                top = [row for row in data if row.get("expectancy_timeframe") is not None][:5]
                                for row in top:
                                    lines.append(
                                        f"{row['instrument']}: expectancy={row['expectancy_timeframe']:.3f}R"
                                    )
                                lines.append("")
                                lines.append(f"Szczegóły zapisano w: {summary_path}")
                                await self._send_message(session, str(chat_id), "\n".join(lines))
                        else:
                            await self._send_message(
                                session,
                                str(chat_id),
                                "Backtest zakończony, ale nie znaleziono pliku podsumowania.",
                            )
                    try:
                        self._gamification.award_xp(chat_id, 5, reason="backtest_all")
                    except Exception as e:
                        self._log.warning("Gamification error (backtest_all): %s", e)
            elif command_type == "menu":
                # USER MENU (Advanced Variant)
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "🔥 Top 3", "callback_data": "cmd:top3"},
                            {"text": "🚀 Sygnały", "callback_data": "cmd:trade"},
                            {"text": "💼 Portfel", "callback_data": "cmd:portfolio"},
                        ],
                        [
                            {"text": "📅 Kalendarz", "callback_data": "cmd:calendar"},
                            {"text": "😱 Fear", "callback_data": "cmd:fear"},
                            {"text": "🗞️ News", "callback_data": "cmd:events"},
                        ],
                        [
                            {"text": "🧮 Calc", "callback_data": "cmd:calc_menu"},
                            {"text": "🔔 Alerty", "callback_data": "cmd:alerts_menu"},
                            {"text": "⚙️ Admin", "callback_data": "cmd:admin"},
                        ],
                        [
                            {"text": "📚 Edukacja", "callback_data": "cmd:learn_menu"},
                            {"text": "👤 Profil", "callback_data": "cmd:profile"},
                        ]
                    ]
                }
                url = self._api_url("sendMessage")
                payload = {
                    "chat_id": str(chat_id),
                    "text": "📱 **Menu Główne**\nPanel inwestora:",
                    "reply_markup": keyboard,
                }
                try:
                    async with session.post(url, json=payload, timeout=10) as resp:
                        if resp.status >= 400:
                            try:
                                body = await resp.text()
                            except Exception:
                                body = "<no body>"
                            self._log.warning("sendMessage (menu) failed with status %s body=%s", resp.status, body)
                except Exception as exc:
                    self._log.warning("sendMessage (menu) error %s", exc)
            elif command_type == "instruments_summary":
                instruments = self._config.instruments
                favorites_in_config = [i for i in instruments if i in FAVORITES]
                others_in_config = [i for i in instruments if i not in FAVORITES]
                lines = [
                    f"Instrumenty w konfiguracji: {len(instruments)}",
                    f"Ulubione w konfiguracji: {len(favorites_in_config)}",
                    f"Pozostałe: {len(others_in_config)}",
                ]
                if favorites_in_config:
                    lines.append("")
                    lines.append("Ulubione (pierwsze 10):")
                    lines.append(", ".join(favorites_in_config[:10]))
                await self._send_message(session, str(chat_id), "\n".join(lines))
            elif command_type == "help":
                lines = [
                    "🤖 **VPS Companion - Komendy**",
                    "",
                    "🚀 **Trading**",
                    "/top3 - 3 najlepsze okazje (z ostatnich 24h)",
                    "/trade - Lista wszystkich aktywnych sygnałów",
                    "/fear - Wskaźniki Strachu (MFI / GTI)",
                    "/why - Analiza ostatniej decyzji (dlaczego TAK/NIE)",
                    "/menu - Główne menu interaktywne",
                    "",
                    "📚 **Edukacja**",
                    "/learn - Leksykon pojęć tradingowych",
                    "/learn <hasło> - Definicja (np. /learn RSI)",
                    "/tips - Losowa porada tradingowa",
                    "",
                    "⭐ **Ulubione**",
                    "/fav_list - Lista ulubionych instrumentów",
                    "/fav_add <SYMBOL> - Dodaj do ulubionych",
                    "/fav_remove <SYMBOL> - Usuń z ulubionych",
                    "",
                    "📊 **Analiza i Wyniki**",
                    "/stats - Statystyki skuteczności bota",
                    "/result <R> [opis] - Zapisz wynik manualny (np. /result 2.5)",
                    "/backtest <SYM> [TF] [N] - Szybki backtest",
                    "/backtest_all [TF] - Backtest wszystkich instrumentów z konfiguracji",
                    "",
                    "⚙️ **System**",
                    "/config - Podgląd konfiguracji",
                    "/instruments - Lista obserwowanych rynków",
                    "/diag - Autodiagnostyka systemu",
                    "/restartml - Przeładowanie modelu ML",
                    "/restart - Restart procesu bota",
                    "/help - Ta lista komend",
                    "",
                    "🎮 **Gamifikacja**",
                    "/profile - Profil i poziom",
                    "/rewards - Lista nagród",
                ]
                await self._send_message(session, str(chat_id), "\n".join(lines))
            elif command_type == "trade":
                await self._handle_trade_command(session, str(chat_id))
            elif command_type == "admin":
                # SYSTEM MENU (Context / Admin)
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "🖥️ Stan Serwera", "callback_data": "cmd:diag"},
                            {"text": "📝 Logi", "callback_data": "cmd:debug"},
                        ],
                        [
                            {"text": "🔄 Restart", "callback_data": "cmd:restart"},
                            {"text": "⚠️ PANIC BUTTON", "callback_data": "cmd:panic_menu"},
                        ],
                        [
                            {"text": "🔙 Powrót", "callback_data": "menu:menu"},
                        ]
                    ]
                }
                await self._send_message(session, str(chat_id), "🛠️ **Menu Systemowe**", reply_markup=keyboard)
            elif command_type == "learn":
                term = command.get("term")
                if term:
                    definition = LEXICON.get(term.upper())
                    if definition:
                        await self._send_message(session, str(chat_id), definition)
                        try:
                            xp_msg = self._gamification.register_event("edu_learn")
                            if xp_msg:
                                await self._send_message(session, str(chat_id), xp_msg)
                        except Exception as e:
                            self._log.warning("Gamification error (learn): %s", e)
                    else:
                        # Try partial match
                        matches = [k for k in LEXICON.keys() if term.upper() in k]
                        if matches:
                            suggestions = ", ".join(matches)
                            await self._send_message(session, str(chat_id), f"Nie znaleziono '{term}'. Czy chodziło o: {suggestions}?\nSpróbuj /learn <hasło>.")
                        else:
                            await self._send_message(session, str(chat_id), f"Nie znaleziono definicji dla: {term}.\nDostępne hasła: {', '.join(LEXICON.keys())}")
                else:
                    # Show index
                    await self._send_message(session, str(chat_id), LEXICON["SŁOWNIK"])
            elif command_type == "tips":
                tip = random.choice(list(TRADING_TIPS.values()))
                await self._send_message(session, str(chat_id), f"💡 **Porada Dnia:**\n\n_{tip}_")
                try:
                    xp_msg = self._gamification.register_event("edu_tips")
                    if xp_msg:
                        await self._send_message(session, str(chat_id), xp_msg)
                except Exception as e:
                    self._log.warning("Gamification error (tips): %s", e)
            elif command_type == "card":
                card = self._cards.draw_card()
                msg = (
                    f"🃏 **KNOWLEDGE CARD** | {card.topic}\n\n"
                    f"📖 _Definicja:_\n{card.definition}\n\n"
                    f"⚠️ **Dlaczego to ważne?**\n{card.importance}\n\n"
                    f"🔍 **Przykład:**\n{card.example}"
                )
                await self._send_message(session, str(chat_id), msg)
                try:
                    xp_msg = self._gamification.register_event("edu_learn")
                    if xp_msg:
                        await self._send_message(session, str(chat_id), xp_msg)
                except Exception as e:
                    self._log.warning("Gamification error (card): %s", e)
            elif command_type == "info":
                bit = self._info_hub.get_random_bit()
                msg = (
                    f"🌍 **INFO HUB** | {bit.category}\n\n"
                    f"📌 **{bit.title}**\n"
                    f"{bit.content}"
                )
                await self._send_message(session, str(chat_id), msg)
                try:
                    xp_msg = self._gamification.register_event("edu_learn")
                    if xp_msg:
                        await self._send_message(session, str(chat_id), xp_msg)
                except Exception as e:
                    self._log.warning("Gamification error (info): %s", e)
            elif command_type == "cheatsheet":
                await self._send_message(session, str(chat_id), USER_MANUAL)
            elif command_type == "debug":
                await self._handle_debug_command(session, str(chat_id))
            elif command_type == "diag":
                await self._send_message(session, str(chat_id), "🕵️‍♂️ Rozpoczynam autodiagnostykę...")
                report = await self._diagnostics.run_full_diagnostics()
                await self._send_message(session, str(chat_id), report)
            elif command_type == "portfolio":
                await self._handle_portfolio_command(str(chat_id))
            elif command_type == "instrument":
                symbol = command.get("symbol")
                if symbol:
                    info = get_instrument_info(symbol)
                    if info:
                        await self._send_message(session, str(chat_id), info.to_telegram_markdown())
                    else:
                        await self._send_message(session, str(chat_id), f"Nie znaleziono instrumentu: {symbol}. Spróbuj wpisać pełną nazwę lub ticker (np. NASDAQ, AAPL).")
                else:
                    keyboard = {"inline_keyboard": [
                        [{"text": "📈 Indeksy", "callback_data": "inst_cat:Indeksy"}, {"text": "🏢 Akcje", "callback_data": "inst_cat:Akcje"}],
                        [{"text": "💱 Forex", "callback_data": "inst_cat:Forex"}, {"text": "₿ Krypto", "callback_data": "inst_cat:Krypto"}],
                    ]}
                    await self._send_message(session, str(chat_id), "📘 **Katalog Instrumentów**\nWybierz kategorię:", reply_markup=keyboard)
            elif command_type == "top3":
                await self._handle_top3_command(session, str(chat_id))
            elif command_type == "fear":
                await self._handle_fear_command(session, str(chat_id))
            elif command_type == "news" or command_type == "calendar":
                await self._handle_calendar_command(session, str(chat_id))
            elif command_type == "events":
                args = command.get("args", [])
                await self._handle_events_command(session, str(chat_id), args)
            elif command_type == "alerts":
                args = command.get("args", [])
                await self._handle_alerts_command(session, str(chat_id), args)
            elif command_type == "calc":
                await self._handle_calc_command(session, command)
                try:
                    self._gamification.award_xp(chat_id, 1, reason="calc")
                except Exception as e:
                    self._log.warning("Gamification error (calc): %s", e)
            elif command_type == "calc_invalid":
                 keyboard = {"inline_keyboard": [
                     [{"text": "🇪🇺 EURUSD", "callback_data": "calc_tmpl:EURUSD"}, {"text": "🇬🇧 GBPUSD", "callback_data": "calc_tmpl:GBPUSD"}],
                     [{"text": "🇩🇪 DAX", "callback_data": "calc_tmpl:DAX"}, {"text": "🇺🇸 SPX", "callback_data": "calc_tmpl:SPX"}],
                     [{"text": "🥇 GOLD", "callback_data": "calc_tmpl:XAUUSD"}, {"text": "₿ BTC", "callback_data": "calc_tmpl:BTC"}],
                 ]}
                 await self._send_message(
                    session, 
                    str(chat_id), 
                    "⚠️ **Kalkulator Ryzyka**\n"
                    "Wpisz komendę ręcznie lub wybierz instrument poniżej, aby otrzymać gotowy szablon:\n\n"
                    "`/calc SYMBOL entry=CENA sl=CENA risk=1%`",
                    reply_markup=keyboard
                )
            elif command_type == "mode":
                target = command.get("target")
                if target in ["edu", "live"]:
                    self._config.educational_mode = (target == "edu")
                    mode_str = "🎓 EDU" if self._config.educational_mode else "⚡ LIVE"
                    await self._send_message(session, str(chat_id), f"Tryb zmieniony na: **{mode_str}**")
                else:
                    current = "🎓 EDU" if self._config.educational_mode else "⚡ LIVE"
                    await self._send_message(session, str(chat_id), f"Aktualny tryb: **{current}**\nZmień komendą: `/mode edu` lub `/mode live`")
            elif command_type == "profile":
                try:
                    profile = self._gamification.get_profile(chat_id)
                except Exception:
                    profile = None
                lines = [
                    "🎮 **Profil Użytkownika**",
                    f"Poziom: {getattr(profile, 'level', '?')}",
                    f"XP: {getattr(profile, 'xp', 0)}/{getattr(profile, 'next_level_xp', '?')}",
                ]
                badges = getattr(profile, 'badges', []) if profile else []
                if badges:
                    lines.append("")
                    lines.append("🏅 Odznaki:")
                    for b in badges:
                        lines.append(f"• {b}")
                await self._send_message(session, str(chat_id), "\n".join(lines))
            elif command_type == "xp":
                try:
                    profile = self._gamification.get_profile(chat_id)
                except Exception:
                    profile = None
                await self._send_message(
                    session,
                    str(chat_id),
                    f"🎮 XP: {getattr(profile, 'xp', 0)}/{getattr(profile, 'next_level_xp', '?')} | Poziom: {getattr(profile, 'level', '?')}"
                )
            elif command_type == "rewards":
                try:
                    rewards = self._gamification.get_rewards(chat_id) or []
                except Exception:
                    rewards = []
                if not rewards:
                    await self._send_message(session, str(chat_id), "🎁 Brak dostępnych nagród.")
                else:
                    lines = ["🎁 **Twoje Nagrody**", ""]
                    for r in rewards:
                        lines.append(f"• {r}")
                    await self._send_message(session, str(chat_id), "\n".join(lines))
            elif command_type == "unknown":
                raw = command.get("raw", "")
                await self._send_message(session, str(chat_id), f"Nieznana komenda: {raw}")

    async def _run_backtest_for_symbol(self, symbol: str, timeframe: str, count: int) -> str:
        client = YahooFinanceClient()
        learning_engine = LearningEngine()
        learning_engine.refresh()
        ml_client = MlAdvisorClient(self._config)
        candles = await client.fetch_candles(None, symbol=symbol, timeframe=timeframe, count=count)
        if not candles:
            return f"Brak świec dla {symbol} {timeframe}."
        engine = BacktestEngine(
            candles=candles,
            instrument=symbol,
            timeframe=timeframe,
            learning_engine=learning_engine,
            ml_client=ml_client,
        )
        trades = await engine.run(risk_per_trade_percent=self._config.risk_per_trade_percent)
        if not trades:
            return "Brak wygenerowanych trade’ów."
        wins = [t for t in trades if t.r > 0]
        losses = [t for t in trades if t.r < 0]
        flats = [t for t in trades if t.r == 0]
        sum_r = sum(t.r for t in trades)
        expectancy = sum_r / len(trades)
        winrate = (len(wins) / len(trades)) * 100.0
        out_dir = Path("backtests")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{symbol}_{timeframe}.json"
        payload = [
            {
                "instrument": t.instrument,
                "timeframe": t.timeframe,
                "strategy_id": t.strategy_id,
                "direction": t.direction.value,
                "entry_time": t.entry_time.isoformat(),
                "exit_time": t.exit_time.isoformat(),
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "r": t.r,
                "reason": t.reason,
                "expectancy_r": t.expectancy_r,
                "ml_score": t.ml_score,
                "confidence": t.confidence,
                "rr": t.rr,
                "ml_reason": t.ml_reason,
            }
            for t in trades
        ]
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return (
            f"Wyniki backtestu {symbol} {timeframe} na {len(trades)} trade’ach:\n"
            f"Wygrane: {len(wins)}, Przegrane: {len(losses)}, Remisy: {len(flats)}\n"
            f"Suma R: {sum_r:.3f}, Expectancy: {expectancy:.3f}R, Winrate: {winrate:.1f}%\n"
            f"Szczegóły zapisano w pliku: {out_path}"
        )

    async def _handle_top3_command(self, session: aiohttp.ClientSession, chat_id: str) -> None:
        """Finds and sends the top 3 best active trades (up to 24h)."""
        now = datetime.utcnow()
        candidates_with_age = []
        
        # 1. Filter candidates (Relaxed window: 24h to ensure we show something)
        for instrument, (decision, timestamp) in self._decision_cache.items():
            age_minutes = (now - timestamp).total_seconds() / 60
            if age_minutes > 1440:  # 24 hours
                continue
            
            # Show everything, even if rejected or score 0 (to show activity)
            # if decision.confidence <= 0:
            #    continue
            pass
                
            candidates_with_age.append((decision, age_minutes))
        
        if not candidates_with_age:
            checked_count = len(self._decision_cache)
            await self._send_message(session, chat_id, f"📭 Brak silnych sygnałów (score > 0) w ciągu ostatnich 24h.\nPrzeskanowano instrumentów: {checked_count}.")
            return

        # 2. Sort by Confidence DESC
        sorted_candidates = sorted(
            candidates_with_age,
            key=lambda x: x[0].confidence,
            reverse=True
        )
        
        top3 = sorted_candidates[:3]
        
        lines = ["🔥 **TOP 3 NAJLEPSZE OKAZJE (24h)** 🔥", ""]
        
        for i, (decision, age_min) in enumerate(top3):
            rank_icon = ["🥇", "🥈", "🥉"][i] if i < 3 else "🔸"
            display_symbol = get_display_name(decision.instrument)
            
            if decision.verdict.value == "no_trade":
                direction_text = "IGNORE"
                direction_icon = "❌"
                levels_line = f"Powód: {decision.explanation_text}"
            else:
                direction_text = "LONG" if decision.direction.value == "long" else "SHORT"
                direction_icon = "🟢" if decision.direction.value == "long" else "🔴"
                levels_line = f"Wejście: {decision.entry_price:.2f} | SL: {decision.sl_price:.2f} | TP: {decision.tp_price:.2f}"
            
            # Format age string
            if age_min < 60:
                age_str = f"{int(age_min)} min temu"
            else:
                hours = int(age_min / 60)
                age_str = f"{hours}h temu"
            
            line = (
                f"{rank_icon} **{display_symbol}** ({decision.timeframe})\n"
                f"   {direction_icon} {direction_text} | Score: {decision.confidence:.0f}/100"
            )
            
            if decision.verdict.value != "no_trade":
                line += f" | RR: {decision.rr:.2f}R"
            
            line += f"\n   {levels_line} | 🕒 {age_str}"
            
            if i == 0 and decision.confidence >= 70:
                line += "\n   ✨ **SUGEROWANY WYBÓR**"
            
            lines.append(line)
            lines.append("")  # Empty line separator
            
        await self._send_message(session, chat_id, "\n".join(lines))

    async def _handle_panic_menu(self, session: aiohttp.ClientSession, chat_id: str) -> None:
        """Displays the Panic Button menu."""
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "⏹️ ZATRZYMAJ WSZYSTKO (Pauza)", "callback_data": "cmd:pause"},
                ],
                [
                    {"text": "☠️ ZAMKNIJ WSZYSTKIE POZYCJE", "callback_data": "cmd:panic_close_all_confirm"},
                ],
                [
                    {"text": "🔙 Anuluj", "callback_data": "menu:admin"},
                ]
            ]
        }
        await self._send_message(
            session, 
            chat_id, 
            "⚠️ **PANIC BUTTON** ⚠️\n\nTo menu służy do sytuacji awaryjnych.\nWybierz działanie ostrożnie.", 
            reply_markup=keyboard
        )

    async def _handle_trade_command(self, session: aiohttp.ClientSession, chat_id: str) -> None:
        """Displays all valid trade candidates from the last 24h."""
        now = datetime.utcnow()
        candidates = []
        
        # Filter from decision cache
        for instrument, (decision, timestamp) in self._decision_cache.items():
            age_minutes = (now - timestamp).total_seconds() / 60
            if age_minutes > 1440:  # 24h
                continue
            
            # Show all decisions with positive confidence
            if decision.confidence > 0:
                candidates.append((decision, age_minutes))
        
        if not candidates:
            await self._send_message(session, chat_id, "📭 Brak aktywnych sygnałów w ciągu ostatnich 24h.")
            return

        # Sort by confidence DESC
        candidates.sort(key=lambda x: x[0].confidence, reverse=True)
        
        lines = ["📋 **LISTA SYGNAŁÓW (24h)**", ""]
        
        for decision, age_min in candidates:
            display_symbol = get_display_name(decision.instrument)
            
            # Icons
            if decision.verdict.value == "no_trade":
                icon = "❌"
                direction = "SKIP"
            elif decision.direction and decision.direction.value == "long":
                icon = "🟢"
                direction = "LONG"
            elif decision.direction and decision.direction.value == "short":
                icon = "🔴"
                direction = "SHORT"
            else:
                icon = "⚪"
                direction = "NEUTRAL"
                
            age_str = f"{int(age_min)}m" if age_min < 60 else f"{int(age_min/60)}h"
            
            line = f"{icon} **{display_symbol}** | {decision.timeframe} | {direction}\n   🎯 {decision.confidence:.0f}% | 🕒 {age_str}"
            lines.append(line)
            lines.append("") # Separator
            
        await self._send_message(session, chat_id, "\n".join(lines))



    async def _handle_calendar_command(self, session: aiohttp.ClientSession, chat_id: str) -> None:
        """Displays economic calendar for today and tomorrow."""
        await self._send_message(session, chat_id, "⏳ Pobieram dane kalendarza...")
        await self._news_client.update_calendar()
        
        now = datetime.now(timezone.utc)
        today_end = now.replace(hour=23, minute=59, second=59)
        tomorrow_end = today_end + timedelta(days=1)
        
        # Get events for next 48h roughly
        events = self._news_client.get_events(start_date=now, end_date=tomorrow_end)
        
        if not events:
             await self._send_message(session, chat_id, "📭 Brak nadchodzących wydarzeń w kalendarzu na najbliższe 24-48h.")
             return

        lines = ["📅 **KALENDARZ EKONOMICZNY**", ""]
        
        # Group by day
        today_events = []
        tomorrow_events = []
        
        for ev in events:
            ev_date = parser.parse(ev["date"])
            if ev_date.tzinfo is None: ev_date = ev_date.replace(tzinfo=timezone.utc)
            
            if ev_date.date() == now.date():
                today_events.append(ev)
            elif ev_date.date() == (now + timedelta(days=1)).date():
                tomorrow_events.append(ev)
        
        def format_event(ev):
            dt = parser.parse(ev["date"])
            time_str = dt.strftime("%H:%M")
            impact_icon = "🔴" if ev["impact"] == "High" else "🟠" if ev["impact"] == "Medium" else "🟡"
            return f"`{time_str}` {impact_icon} {ev['currency']} **{ev['title']}**"

        if today_events:
            lines.append("📆 **DZISIAJ:**")
            for ev in today_events[:15]: 
                lines.append(format_event(ev))
            if len(today_events) > 15:
                lines.append(f"... i {len(today_events)-15} więcej")
            lines.append("")
            
        if tomorrow_events:
            lines.append("📆 **JUTRO:**")
            for ev in tomorrow_events[:15]:
                lines.append(format_event(ev))
            if len(tomorrow_events) > 15:
                lines.append(f"... i {len(tomorrow_events)-15} więcej")
                
        await self._send_message(session, chat_id, "\n".join(lines))

    async def _handle_events_command(self, session: aiohttp.ClientSession, chat_id: str, args: List[str]) -> None:
        """Search for events."""
        # Args: [currency/category/date]
        
        currency = None
        category = None
        target_date = None
        
        now = datetime.now(timezone.utc)
        
        for arg in args:
            arg_u = arg.upper()
            arg_l = arg.lower()
            
            # Check Currency
            if arg_u in ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "NZD", "CHF", "PLN"]:
                currency = arg_u
                continue
                
            # Check Keywords (Date)
            if arg_l in ["today", "dzisiaj", "dziś"]:
                target_date = now.date()
                continue
            if arg_l in ["tomorrow", "jutro"]:
                target_date = (now + timedelta(days=1)).date()
                continue
                
            # Check specific date YYYY-MM-DD or DD.MM
            try:
                # parser.parse might be too aggressive (e.g. "inflation" -> error, but "may" -> date)
                # Let's try only if it looks like a date
                if any(c in arg for c in "-./") or arg_l in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
                     parsed = parser.parse(arg)
                     # If successful
                     target_date = parsed.date()
                     # Fix year if needed (parser defaults to current year usually)
                     continue
            except:
                pass
            
            # Check Category (last resort)
            cat_map = {
                "inflation": "Inflation", "inflacja": "Inflation",
                "cpi": "Inflation",
                "rates": "Central Bank", "stopy": "Central Bank",
                "bank": "Central Bank",
                "jobs": "Employment", "praca": "Employment",
                "nfp": "Employment",
                "gdp": "Growth", "pkb": "Growth"
            }
            if arg_l in cat_map:
                category = cat_map[arg_l]

        # Determine date range
        if target_date:
            start_date = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            end_date = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        else:
            # Default 7 days
            start_date = now
            end_date = now + timedelta(days=7)
        
        events = self._news_client.get_events(
            currency=currency, 
            category=category,
            start_date=start_date,
            end_date=end_date
        )
        
        if not events:
            await self._send_message(session, chat_id, f"📭 Brak wydarzeń dla filtrów: {args}")
            return
            
        lines = [f"🔎 **WYNIKI WYSZUKIWANIA** ({len(events)})", ""]
        for ev in events[:15]:
            dt = parser.parse(ev["date"])
            date_str = dt.strftime("%d.%m %H:%M")
            impact_icon = "🔴" if ev["impact"] == "High" else "🟠" if ev["impact"] == "Medium" else "🟡"
            lines.append(f"`{date_str}` {impact_icon} {ev['currency']} {ev['title']}")
            
        await self._send_message(session, chat_id, "\n".join(lines))

    async def _handle_fear_command(self, session: aiohttp.ClientSession, chat_id: str) -> None:
        """Shows Market Fear Index (MFI) and Global Tension Index (GTI)."""
        await self._send_message(session, chat_id, "⏳ Analizuję sentyment rynkowy... (może to zająć chwilę)")
        
        try:
            snapshot = await self._sentiment_engine.get_sentiment()
        except Exception as exc:
            self._log.error("Error getting sentiment: %s", exc, exc_info=True)
            await self._send_message(session, chat_id, "❌ Błąd pobierania danych sentymentu.")
            return

        lines = ["😨 **WSKAŹNIKI STRACHU**", ""]
        
        # MFI
        mfi_icon = "🟢"
        if snapshot.mfi >= 75: mfi_icon = "🔴"
        elif snapshot.mfi >= 50: mfi_icon = "🟠"
        elif snapshot.mfi >= 25: mfi_icon = "🟡"
        
        lines.append(f"{mfi_icon} **Market Fear Index (MFI):** `{snapshot.mfi:.0f}/100`")
        lines.append(f"   📉 **Status:** {snapshot.mfi_status}")
        lines.append("   🧠 _(Zmienność, VIX, awersja do ryzyka)_")
        lines.append("")

        # GTI
        gti_icon = "🟢"
        if snapshot.gti >= 75: gti_icon = "🔴"
        elif snapshot.gti >= 50: gti_icon = "🟠"
        elif snapshot.gti >= 30: gti_icon = "🟡"
        
        lines.append(f"{gti_icon} **Global Tension Index (GTI):** `{snapshot.gti:.0f}/100`")
        lines.append(f"   🌍 **Status:** {snapshot.gti_status}")
        lines.append("   📰 _(Newsy, ropa, złoto, geopolityka)_")
        lines.append("")
        
        if snapshot.details:
            lines.append("🔎 **Szczegóły:**")
            for det in snapshot.details:
                lines.append(f"🔸 {det}")
        
        lines.append("")
        
        # Add Fear Events
        fear_events = self._news_client.get_fear_events(start_date=datetime.now(timezone.utc))
        if fear_events:
            lines.append("📅 **NADCHODZĄCE EVENTY 'STRACHU' (Volatylność):**")
            for ev in fear_events[:5]:
                dt = parser.parse(ev["date"])
                time_str = dt.strftime("%d.%m %H:%M")
                url = ev.get("url", "")
                link_part = f" [Info]({url})" if url else ""
                lines.append(f"🔴 `{time_str}` **{ev['title']}** ({ev['currency']}){link_part}")
                
        await self._send_message(session, chat_id, "\n".join(lines))

    async def _handle_news_command(self, session: aiohttp.ClientSession, command: Dict[str, Any]) -> None:
        chat_id = command["chat_id"]
        
        await self._news_client.update_calendar()
        
        # Display upcoming high impact events for major pairs (USD, EUR, GBP, JPY)
        # Or just generic top events
        
        # We'll fetch upcoming for "EURUSD", "GBPUSD", "USDJPY" to cover main bases
        currencies_to_check = ["USD", "EUR", "GBP", "JPY"]
        
        events = self._news_client._events # Access internal list for overview
        if not events:
            await self._send_message(session, str(chat_id), "📭 Kalendarz jest pusty.")
            return

        # Filter next 24h high/medium impact
        now = datetime.now(timezone.utc)
        upcoming = []
        
        from dateutil import parser
        
        for ev in events:
            try:
                date_str = ev.get("date")
                event_dt = parser.parse(date_str)
                if event_dt.tzinfo is None:
                    event_dt = event_dt.replace(tzinfo=timezone.utc)
                else:
                    event_dt = event_dt.astimezone(timezone.utc)
                
                if ev.get("impact") not in ["High", "Medium"]:
                    continue
                    
                diff_hours = (event_dt - now).total_seconds() / 3600.0
                
                if 0 <= diff_hours <= 24:
                    upcoming.append((event_dt, ev))
            except:
                continue
                
        upcoming.sort(key=lambda x: x[0])
        
        if not upcoming:
             await self._send_message(session, str(chat_id), "📭 Brak ważnych danych w ciągu 24h.")
             return

        lines = ["📅 **Kalendarz Ekonomiczny (24h)**", ""]
        
        for dt, ev in upcoming[:10]: # Limit to 10
            time_str = dt.strftime("%H:%M")
            impact_icon = "🔴" if ev.get("impact") == "High" else "🟠"
            url = ev.get("url", "")
            link_part = f" [Info]({url})" if url else ""
            lines.append(f"{time_str} {impact_icon} {ev.get('country')} - {ev.get('title')}{link_part}")
            
        await self._send_message(session, str(chat_id), "\n".join(lines))

    async def _handle_calc_command(self, session: aiohttp.ClientSession, command: Dict[str, Any]) -> None:
        chat_id = command["chat_id"]
        symbol = command["symbol"]
        entry = command["entry"]
        sl = command["sl"]
        risk_pct = command["risk_pct"]
        
        if entry <= 0 or sl <= 0:
             await self._send_message(session, str(chat_id), "❌ Ceny Entry i SL muszą być większe od 0.")
             return
             
        capital = 10000.0 # Placeholder, should come from account/config
        risk_amount = capital * (risk_pct / 100.0)
        
        # Determine pip size (simplified)
        is_jpy = "JPY" in symbol
        pip_size = 0.01 if is_jpy else 0.0001
        
        dist_pips = abs(entry - sl) / pip_size
        
        if dist_pips == 0:
             await self._send_message(session, str(chat_id), "❌ Entry i SL są takie same!")
             return

        # Calculate position size (lots)
        # Formula: Risk / (SL_dist_points * TickValue)
        # Simplified assumption: 1 Lot = 100,000 units. Tick value approx $10 per pip for EURUSD standard lot.
        # This is an ESTIMATION.
        
        # Approximate pip value for standard lot (100k)
        # If quote currency is USD, pip value is ~$10
        # If quote is JPY, pip value is ~$1000 / USDJPY rate
        # We will use a simplified generic $10 per pip per lot for non-JPY, and adjusted for JPY.
        # Ideally this comes from ExecutionEngine or Broker API.
        
        base_pip_value_usd = 10.0
        if is_jpy:
             # Very rough approximation if we don't have current price
             # Assuming USDJPY ~ 150
             base_pip_value_usd = 1000.0 / 150.0 
        
        # Position size in lots
        # Risk = Lots * Pips * PipValue
        # Lots = Risk / (Pips * PipValue)
        
        lots = risk_amount / (dist_pips * base_pip_value_usd)
        
        # Round to 2 decimals
        lots = round(lots, 2)
        
        lines = [
            "📐 **Kalkulator Ryzyka**",
            f"Instrument: {symbol}",
            f"Kapitał (symulowany): {capital:,.0f} $",
            f"Ryzyko: {risk_pct}% ({risk_amount:.2f} $)",
            f"SL: {dist_pips:.1f} pips",
            "",
            f"➡️ **Wielkość pozycji: {lots} lot**",
            "",
            "🧠 *Edukacja:*",
            f"Jeśli SL zostanie trafiony, stracisz ok. {risk_amount:.2f} $.",
            "To jest koszt prowadzenia biznesu. Zaakceptuj to przed otwarciem."
        ]
        
        await self._send_message(session, str(chat_id), "\n".join(lines))

    async def _answer_callback_query(self, callback_id: str, text: str = "") -> None:
        url = self._api_url("answerCallbackQuery")
        payload = {"callback_query_id": callback_id, "text": text}
        async with aiohttp.ClientSession() as session:
            try:
                await session.post(url, json=payload, timeout=5)
            except Exception as exc:
                self._log.warning("answerCallbackQuery error %s", exc)

    async def _handle_callback(self, callback: Dict[str, Any]) -> None:
        callback_id = str(callback.get("id"))
        callback_data = callback.get("data")
        message = callback.get("message")
        chat = message.get("chat", {})
        chat_id = str(chat.get("id"))
        
        if not callback_data:
            return

        # Acknowledge the callback to stop loading animation
        await self._answer_callback_query(callback_id)
        
        if callback_data.startswith("menu:"):
            action = callback_data.split(":")[1]
            command_map = {
                "top3": "top3",
                "stats": "stats",
                "learn": "learn",
                "tips": "tips",
                "favorites": "favorites_list",
                "config": "config",
                "instruments": "instruments_summary",
                "help": "help",
                "gamify": "profile",
                "admin": "admin",
                "menu": "menu",
            }
            cmd_type = command_map.get(action)
            if cmd_type:
                # Dispatch as if it was a text command
                await self._event_bus.publish(
                    Event(
                        type=EventType.TELEGRAM_COMMAND,
                        payload={"type": cmd_type, "chat_id": chat_id},
                        timestamp=datetime.utcnow(),
                    )
                )

        elif callback_data.startswith("cmd:"):
            # "cmd:pause", "cmd:resume", "cmd:restart", "cmd:diag", "cmd:gamify", "cmd:hot", "cmd:portfolio", "cmd:risk_status"
            cmd_name = callback_data.split(":")[1]
            
            command = None
            if cmd_name == "pause":
                command = {"type": "pause", "chat_id": chat_id}
            elif cmd_name == "resume":
                command = {"type": "resume", "chat_id": chat_id}
            elif cmd_name == "restart":
                command = {"type": "restart", "chat_id": chat_id}
            elif cmd_name == "restartml":
                command = {"type": "restartml", "chat_id": chat_id}
            elif cmd_name == "diag":
                command = {"type": "diag", "chat_id": chat_id}
            elif cmd_name == "debug":
                command = {"type": "debug", "chat_id": chat_id}
            elif cmd_name == "gamify" or cmd_name == "profile":
                command = {"type": "profile", "chat_id": chat_id}
            elif cmd_name == "hot" or cmd_name == "top3":
                command = {"type": "top3", "chat_id": chat_id}
            elif cmd_name == "portfolio":
                command = {"type": "portfolio", "chat_id": chat_id}
            elif cmd_name == "risk_status" or cmd_name == "fear":
                command = {"type": "fear", "chat_id": chat_id} 
            elif cmd_name == "trade":
                command = {"type": "trade", "chat_id": chat_id}
            elif cmd_name == "calc_menu":
                command = {"type": "calc_invalid", "chat_id": chat_id}
            elif cmd_name == "learn_menu":
                command = {"type": "learn", "chat_id": chat_id}
            elif cmd_name == "calendar":
                command = {"type": "calendar", "chat_id": chat_id}
            elif cmd_name == "events":
                command = {"type": "events", "chat_id": chat_id}
            elif cmd_name == "alerts_menu":
                command = {"type": "alerts", "chat_id": chat_id}
            # Updater Handlers
            elif cmd_name == "check_update":
                has_update, msg = self._updater.check_for_updates()
                resp = f"🔍 **Status Aktualizacji**\n{msg}"
                async with aiohttp.ClientSession() as session:
                    await self._send_message(session, chat_id, resp)
                return
            elif cmd_name == "update_git":
                # Confirm update? No, direct action as requested.
                async with aiohttp.ClientSession() as session:
                    await self._send_message(session, chat_id, "⏳ Rozpoczynam procedurę aktualizacji...")
                    # Update process is blocking for git but should be fast.
                    # Ideally we run in executor.
                    # For simplicity, calling sync method.
                    result = self._updater.perform_update(chat_id)
                    await self._send_message(session, chat_id, f"📝 {result}")
                return
            elif cmd_name == "update_status":
                status = self._updater.get_status()
                async with aiohttp.ClientSession() as session:
                    await self._send_message(session, chat_id, f"ℹ️ **System Status**\n{status}")
                return
            elif cmd_name == "rollback":
                 result = self._updater.rollback()
                 async with aiohttp.ClientSession() as session:
                    await self._send_message(session, chat_id, f"🔙 {result}")
                 return
            elif cmd_name == "clear_cache":
                self._updater.guard.cleanup_cache()
                async with aiohttp.ClientSession() as session:
                    await self._send_message(session, chat_id, "🧹 Cache wyczyszczony.")
                return
            elif cmd_name == "clear_backtests":
                self._updater.guard.cleanup_backtests()
                async with aiohttp.ClientSession() as session:
                    await self._send_message(session, chat_id, "🧹 Wyniki backtestów wyczyszczone.")
                return
            elif cmd_name == "clear_ml":
                self._updater.guard.cleanup_ml()
                async with aiohttp.ClientSession() as session:
                    await self._send_message(session, chat_id, "🧹 Modele ML wyczyszczone.")
                return
            elif cmd_name == "admin":
                command = {"type": "admin", "chat_id": chat_id}
            elif cmd_name == "panic_menu":
                async with aiohttp.ClientSession() as session:
                   await self._handle_panic_menu(session, chat_id)
                return
            elif cmd_name == "panic_close_all_confirm":
                # Show confirmation dialog
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "🔥 TAK, ZAMKNIJ WSZYSTKO 🔥", "callback_data": "cmd:panic_close_all_execute"},
                        ],
                        [
                            {"text": "🔙 NIE, ANULUJ", "callback_data": "menu:admin"},
                        ]
                    ]
                }
                async with aiohttp.ClientSession() as session:
                    await self._send_message(session, chat_id, "‼️ **POTWIERDZENIE** ‼️\nCzy na pewno chcesz zamknąć WSZYSTKIE pozycje rynkowe?", reply_markup=keyboard)
                return
            elif cmd_name == "panic_close_all_execute":
                # Publish event to close all
                await self._event_bus.publish(
                    Event(
                        type=EventType.MANUAL_CLOSE_REQUEST,
                        payload={"trade_id": "ALL", "symbol": "ALL", "chat_id": chat_id},
                        timestamp=datetime.utcnow(),
                    )
                )
                async with aiohttp.ClientSession() as session:
                    await self._send_message(session, chat_id, "☠️ **WYSŁANO ŻĄDANIE ZAMKNIĘCIA WSZYSTKICH POZYCJI** ☠️")
                return
            else:
                 # Fallback for simple commands
                 command = {"type": cmd_name, "chat_id": chat_id}

            if command:
                await self._event_bus.publish(
                    Event(
                        type=EventType.TELEGRAM_COMMAND,
                        payload=command,
                        timestamp=datetime.utcnow(),
                    )
                )

        elif callback_data.startswith("action:"):
            # action:TYPE:DECISION_ID
            parts = callback_data.split(":")
            if len(parts) >= 3:
                action_type_str = parts[1]
                decision_id = parts[2]
                
                try:
                    action_type = UserActionType(action_type_str)
                except ValueError:
                    return

                # Publish User Decision Event
                record = UserDecisionRecord(
                    decision_id=decision_id,
                    action=action_type,
                    timestamp=datetime.utcnow(),
                    chat_id=chat_id,
                    message_id=message.get("message_id") if message else None,
                    note=None
                )
                
                await self._event_bus.publish(
                    Event(
                        type=EventType.USER_DECISION,
                        payload=record,
                        timestamp=datetime.utcnow(),
                    )
                )
                
                # Immediate feedback
                feedback_map = {
                    UserActionType.ENTER: "✅ Powodzenia!",
                    UserActionType.SKIP: "❌ Pominięto.",
                    UserActionType.REMIND: "⏰ Przypomnienie ustawione (wkrótce).",
                    UserActionType.OPEN_TV: "📊 Otwieram wykres..."
                }
                fb_text = feedback_map.get(action_type, "👍")
                await self._answer_callback_query(callback_id, text=fb_text)

        elif callback_data.startswith("port_close:"):
            # port_close:SYMBOL:TRADE_ID
            parts = callback_data.split(":")
            if len(parts) >= 3:
                symbol = parts[1]
                trade_id = parts[2]
                
                # Publish Manual Close Request
                await self._event_bus.publish(
                    Event(
                        type=EventType.MANUAL_CLOSE_REQUEST,
                        payload={"trade_id": trade_id, "symbol": symbol, "chat_id": chat_id},
                        timestamp=datetime.utcnow(),
                    )
                )
                
                # Update message to show processing
                async with aiohttp.ClientSession() as session:
                    # We can't easily edit the message to "Closed" immediately without confirmation, 
                    # but we can acknowledge the click.
                    await self._answer_callback_query(callback_id, text="🔒 Zamykanie pozycji...")

        elif callback_data.startswith("port_chart:"):
            symbol = callback_data.split(":")[1]
            tv_symbol = to_tradingview_symbol(symbol)
            # For now just text, in future maybe generate chart image
            async with aiohttp.ClientSession() as session:
                await self._send_message(session, chat_id, f"📊 Wykres dla {symbol}: https://www.tradingview.com/chart/?symbol={tv_symbol}")

        elif callback_data.startswith("inst_cat:"):
            category_key = callback_data.split(":")[1]
            # Filter catalog
            # Mapping keys to asset_type substrings
            filter_map = {
                "Indeksy": "Indeks",
                "Akcje": "Akcja",
                "Forex": "Forex",
                "Krypto": "Kryptowaluta"
            }
            search_term = filter_map.get(category_key, category_key)
            
            matched = []
            for key, info in INSTRUMENT_CATALOG.items():
                if search_term.lower() in info.asset_type.lower():
                    matched.append(f"• /instrument {key} ({info.name})")
            
            if matched:
                text = f"📂 **Kategoria: {category_key}**\n\n" + "\n".join(matched)
            else:
                text = f"Brak instrumentów w kategorii {category_key}."
                
            async with aiohttp.ClientSession() as session:
                await self._send_message(session, chat_id, text)

        elif callback_data.startswith("calc_tmpl:"):
            symbol = callback_data.split(":")[1]
            # We want the user to copy-paste this
            cmd_text = f"/calc {symbol} entry=0.0 sl=0.0 risk=1%"
            async with aiohttp.ClientSession() as session:
                await self._send_message(session, chat_id, f"📋 Skopiuj i uzupełnij:\n`{cmd_text}`")

    async def _handle_update(self, update: Dict[str, Any]) -> None:
        callback = update.get("callback_query")
        if callback:
            await self._handle_callback(callback)
            return
        message = update.get("message")
        if not message:
            return
        text = message.get("text", "")
        chat = message.get("chat", {})
        chat_id = str(chat.get("id"))
        if text.startswith("/restart"):
            command = {"type": "restart", "chat_id": chat_id}
        elif text.startswith("/pause"):
            command = {"type": "pause", "chat_id": chat_id}
        elif text.startswith("/resume"):
            command = {"type": "resume", "chat_id": chat_id}
        elif text.startswith("/risk"):
            parts = text.split()
            value = float(parts[1]) if len(parts) > 1 else None
            command = {"type": "risk", "value": value, "chat_id": chat_id}
        elif text.startswith("/stats"):
            parts = text.split(maxsplit=1)
            symbol = parts[1] if len(parts) > 1 else None
            command = {"type": "stats", "symbol": symbol, "chat_id": chat_id}
        elif text.startswith("/result"):
            parts = text.split(maxsplit=2)
            if len(parts) < 2:
                command = {"type": "result_invalid", "raw": text, "chat_id": chat_id}
            else:
                try:
                    value_r = float(parts[1])
                except ValueError:
                    command = {"type": "result_invalid", "raw": text, "chat_id": chat_id}
                else:
                    note = parts[2] if len(parts) > 2 else None
                    command = {"type": "result", "value_r": value_r, "note": note, "chat_id": chat_id}
        elif text.startswith("/why"):
            command = {"type": "why_last_trade", "chat_id": chat_id}
        elif text.startswith("/fav_add"):
            tail = text[len("/fav_add") :].strip()
            if not tail:
                command = {"type": "favorites_invalid", "raw": text, "chat_id": chat_id}
            else:
                raw_symbols = tail.replace(",", " ").split()
                symbols = [s.upper() for s in raw_symbols if s]
                command = {"type": "favorites_add", "symbols": symbols, "chat_id": chat_id}
        elif text.startswith("/fav_remove"):
            tail = text[len("/fav_remove") :].strip()
            if not tail:
                command = {"type": "favorites_invalid", "raw": text, "chat_id": chat_id}
            else:
                raw_symbols = tail.replace(",", " ").split()
                symbols = [s.upper() for s in raw_symbols if s]
                command = {"type": "favorites_remove", "symbols": symbols, "chat_id": chat_id}
        elif text.startswith("/fav_list"):
            command = {"type": "favorites_list", "chat_id": chat_id}
        elif text.startswith("/menu") or text.startswith("/start"):
            command = {"type": "menu", "chat_id": chat_id}
        elif text.startswith("/fav_clear"):
            command = {"type": "favorites_clear", "chat_id": chat_id}
        elif text.startswith("/portfolio"):
            command = {"type": "portfolio", "chat_id": chat_id}
        elif text.startswith("/config"):
            command = {"type": "config", "chat_id": chat_id}
        elif text.startswith("/backtest_all"):
            tail = text[len("/backtest_all") :].strip()
            timeframe = tail if tail else None
            command = {"type": "backtest_all", "timeframe": timeframe, "chat_id": chat_id}
        elif text.startswith("/backtest"):
            tail = text[len("/backtest") :].strip()
            if not tail:
                command = {"type": "backtest", "symbol": None, "timeframe": None, "count": None, "chat_id": chat_id}
            else:
                parts = tail.split()
                symbol = parts[0].upper()
                timeframe = parts[1] if len(parts) > 1 else None
                count = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
                command = {"type": "backtest", "symbol": symbol, "timeframe": timeframe, "count": count, "chat_id": chat_id}
        elif text.startswith("/calc"):
            # /calc SYMBOL entry=... sl=... [risk=...]
            if len(text.strip()) <= 5:
                 command = {"type": "calc_invalid", "raw": text, "chat_id": chat_id}
            else:
                 try:
                    parts = text.split()
                    symbol = parts[1].upper()
                    entry = None
                    sl = None
                    risk_pct = 1.0
                    for p in parts[2:]:
                        if p.lower().startswith("entry="):
                            entry = float(p.split("=")[1])
                        elif p.lower().startswith("sl="):
                            sl = float(p.split("=")[1])
                        elif p.lower().startswith("risk="):
                            risk_str = p.split("=")[1].replace("%", "")
                            risk_pct = float(risk_str)
                    
                    if entry is not None and sl is not None:
                        command = {"type": "calc", "symbol": symbol, "entry": entry, "sl": sl, "risk_pct": risk_pct, "chat_id": chat_id}
                    else:
                         command = {"type": "calc_invalid", "raw": text, "chat_id": chat_id}
                 except Exception:
                     command = {"type": "calc_invalid", "raw": text, "chat_id": chat_id}

        elif text.startswith("/learn") or text.startswith("/wiedza"):
            term = text.replace("/learn", "").replace("/wiedza", "").strip()
            command = {"type": "learn", "term": term, "chat_id": chat_id}
        elif text.startswith("/tips"):
            command = {"type": "tips", "chat_id": chat_id}
        elif text.startswith("/instrument"):
            symbol = text.replace("/instrument", "").strip()
            command = {"type": "instrument", "symbol": symbol, "chat_id": chat_id}
        elif text.startswith("/top3"):
            command = {"type": "top3", "chat_id": chat_id}
        elif text.startswith("/hot"):
            command = {"type": "hot", "chat_id": chat_id}
        elif text.startswith("/fear") or text.startswith("/strach"):
            command = {"type": "fear", "chat_id": chat_id}
        elif text.startswith("/kalendarz") or text.startswith("/calendar"):
            command = {"type": "calendar", "chat_id": chat_id}
        elif text.startswith("/wydarzenia") or text.startswith("/events"):
            args = text.replace("/wydarzenia", "").replace("/events", "").strip().split()
            command = {"type": "events", "args": args, "chat_id": chat_id}
        elif text.startswith("/news"):
            command = {"type": "news", "chat_id": chat_id}
        elif text.startswith("/mode"):
            target = text.replace("/mode", "").strip().lower()
            command = {"type": "mode", "target": target, "chat_id": chat_id}
        elif text.startswith("/briefing"):
            command = {"type": "briefing", "chat_id": chat_id}
        elif text.startswith("/dekalog"):
            command = {"type": "dekalog", "chat_id": chat_id}
        elif text.startswith("/profile") or text.startswith("/level"):
            command = {"type": "profile", "chat_id": chat_id}
        elif text.startswith("/cheatsheet") or text.startswith("/manual"):
            command = {"type": "cheatsheet", "chat_id": chat_id}
        elif text.startswith("/help") or text.startswith("/pomoc"):
            command = {"type": "help", "chat_id": chat_id}
        elif text.startswith("/rewards") or text.startswith("/nagrody"):
            command = {"type": "rewards", "chat_id": chat_id}
        elif text.startswith("/xp"):
            command = {"type": "xp", "chat_id": chat_id}
        elif text.startswith("/card"):
            command = {"type": "card", "chat_id": chat_id}
        elif text.startswith("/info"):
            command = {"type": "info", "chat_id": chat_id}
        elif text.startswith("/debug"):
            command = {"type": "debug", "chat_id": chat_id}
        elif text.startswith("/diag") or text.startswith("/status"):
            command = {"type": "diag", "chat_id": chat_id}
        elif text.startswith("/alerts"):
            args = text.replace("/alerts", "").strip().split()
            command = {"type": "alerts", "args": args, "chat_id": chat_id}
        # Updater Commands
        elif text.startswith("/check_update"):
            command = {"type": "check_update", "chat_id": chat_id}
        elif text.startswith("/update_git"):
            command = {"type": "update_git", "chat_id": chat_id}
        elif text.startswith("/update_status"):
            command = {"type": "update_status", "chat_id": chat_id}
        elif text.startswith("/rollback"):
            command = {"type": "rollback", "chat_id": chat_id}
        elif text.startswith("/clear_cache"):
            command = {"type": "clear_cache", "chat_id": chat_id}
        elif text.startswith("/clear_backtests"):
            command = {"type": "clear_backtests", "chat_id": chat_id}
        elif text.startswith("/clear_ml"):
            command = {"type": "clear_ml", "chat_id": chat_id}
        else:
            command = {"type": "unknown", "raw": text, "chat_id": chat_id}

        if command:
            await self._event_bus.publish(
                Event(
                    type=EventType.TELEGRAM_COMMAND,
                    payload=command,
                    timestamp=message.get("date"),
                )
            )

    async def _set_bot_commands(self) -> None:
        """Sets the bot's command menu (burger menu) via Telegram API."""
        commands = [
            {"command": "menu", "description": "📱 Panel Główny"},
            {"command": "top3", "description": "🔥 Top 3 Okazje"},
            {"command": "trade", "description": "🚀 Aktywne Sygnały"},
            {"command": "portfolio", "description": "💼 Twój Portfel"},
            {"command": "calc", "description": "🧮 Kalkulator Ryzyka"},
            {"command": "fear", "description": "😱 Indeks Strachu"},
            {"command": "profile", "description": "👤 Profil Tradera"},
            {"command": "learn", "description": "📚 Leksykon Wiedzy"},
            {"command": "tips", "description": "💡 Porada Dnia"},
            {"command": "help", "description": "❓ Pomoc"},
        ]
        
        url = self._api_url("setMyCommands")
        async with aiohttp.ClientSession() as session:
            try:
                # setMyCommands replaces the existing list
                await session.post(url, json={"commands": commands}, timeout=10)
                self._log.info("Bot commands menu updated successfully.")
            except Exception as e:
                self._log.warning("Failed to set bot commands: %s", e)

    async def run(self) -> None:
        self._log.info("Starting Telegram bot polling...")
        
        # Setup commands menu
        await self._set_bot_commands()
        
        # Check for update status
        upd_msg, upd_chat_id = self._updater.check_post_update()
        if upd_msg and upd_chat_id:
             async with aiohttp.ClientSession() as session:
                await self._send_message(session, upd_chat_id, upd_msg)
        
        # Send startup message
        await self.send_system_message("🚀 System Tradingowy wystartował. Wpisz /menu aby zacząć.")
        
        url = self._api_url("getUpdates")
        async with aiohttp.ClientSession() as session:
            while True:
                params = {"timeout": 10}
                if self._offset:
                    params["offset"] = self._offset
                try:
                    async with session.get(url, params=params, timeout=20) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("ok"):
                                for result in data.get("result", []):
                                    self._offset = result["update_id"] + 1
                                    await self._handle_update(result)
                        else:
                            self._log.warning("getUpdates failed: %s", resp.status)
                            await asyncio.sleep(5)
                except asyncio.TimeoutError:
                    continue
                except Exception as exc:
                    self._log.error("Telegram polling error: %s", exc)
                    await asyncio.sleep(5)