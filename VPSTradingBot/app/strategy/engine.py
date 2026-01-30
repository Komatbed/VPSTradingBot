from __future__ import annotations

from datetime import datetime
from typing import List

from app.config import Config
import logging
from app.core.event_bus import EventBus
from app.core.models import (
    Candle,
    DecisionVerdict,
    Event,
    EventType,
    FinalDecision,
    OrderRequest,
    StrategySignal,
    TradeDirection,
)
from app.data.news_client import NewsClient
from app.data.tradingview_mapping import get_tv_link
from app.explainability.engine import ExplainabilityEngine
from app.learning.engine import LearningEngine
from app.ml.client import MlAdvisorClient
from app.risk.engine import PositionSizingInput, RiskEngine
from app.risk.guard import RiskGuard
from app.strategy.base import Strategy, StrategyContext


from app.scoring.engine import ScoringEngine
from app.scoring.models import TradeScore

class StrategyEngine:
    def __init__(
        self,
        config: Config,
        event_bus: EventBus,
        strategies: List[Strategy],
        explain_engine: ExplainabilityEngine,
        learning_engine: LearningEngine,
        news_client: NewsClient,
    ) -> None:
        """
        Initializes the StrategyEngine.

        Args:
            config: System configuration.
            event_bus: Event bus for publishing/subscribing to events.
            strategies: List of trading strategies to execute.
            explain_engine: Engine for explaining decisions.
            learning_engine: Engine for reinforcement learning/stats.
            news_client: Client for checking economic calendar events.
        """
        self._config = config
        self._event_bus = event_bus
        self._strategies = strategies
        self._context = StrategyContext(max_risk_per_trade_percent=config.risk_per_trade_percent)
        self._risk_engine = RiskEngine(config)
        self._account_balance = 10000.0
        self._explain_engine = explain_engine
        self._learning_engine = learning_engine
        self._learning_engine.refresh()
        self._risk_guard = RiskGuard(config)
        self._ml_client = MlAdvisorClient(config)
        self._news_client = news_client
        self._scoring_engine = ScoringEngine()  # Initialize ScoringEngine
        self._log = logging.getLogger("strategy")
        self._seen_instruments = set()
        self._volatility_history: Dict[str, List[float]] = {}
        self._event_bus.subscribe(EventType.MARKET_DATA, self._on_market_data)
        self._event_bus.subscribe(EventType.ORDER_FILLED, self._on_order_filled)
        self._event_bus.subscribe(EventType.SYSTEM_PAUSE, self._on_pause)
        self._event_bus.subscribe(EventType.SYSTEM_RESUME, self._on_resume)
        self._paused = False

    async def _on_pause(self, event: Event) -> None:
        self._paused = True
        self._log.info("System PAUSED via command.")

    async def _on_resume(self, event: Event) -> None:
        """Handles SYSTEM_RESUME event to resume trading."""
        self._paused = False
        self._log.info("System RESUMED via command.")

    async def _on_order_filled(self, event: Event) -> None:
        """Updates RiskGuard when a trade is executed."""
        order_result = event.payload
        if getattr(order_result, "status", None) == "FILLED": # Check status just in case
             self._risk_guard.register_trade(order_result.instrument)
             self._log.info(f"RiskGuard updated: Trade executed for {order_result.instrument}")

    async def _on_market_data(self, event: Event) -> None:
        if self._paused:
            return
        snapshot = event.payload
        self._log.debug(
            "MARKET_DATA received instrument=%s timeframe=%s candles=%d regime=%s",
            snapshot.instrument,
            snapshot.timeframe,
            len(snapshot.candles) if snapshot.candles else 0,
            getattr(snapshot.regime, "value", "unknown"),
        )
        
        # --- NEWS CHECK ---
        impact, time_to = self._news_client.get_impact_for_symbol(snapshot.instrument)
        snapshot.news_impact = impact
        snapshot.time_to_news_min = time_to
        if impact == "High":
            self._log.info(f"NEWS CHECK: {snapshot.instrument} -> Impact: {impact}, Time: {time_to:.1f}min")
        # ------------------
        
        signals: List[tuple[Strategy, StrategySignal, float, TradeScore]] = []
        for strategy in self._strategies:
            signal = await strategy.on_market_data(snapshot, self._context)
            if not signal:
                continue
            
            # --- SCORING SYSTEM INTEGRATION ---
            trade_score = self._scoring_engine.evaluate(snapshot, signal)
            self._log.info(
                "Scoring for %s %s: %.1f/100 (%s)", 
                snapshot.instrument, 
                strategy.id, 
                trade_score.total_score, 
                trade_score.verdict
            )
            
            # Update signal confidence with real score
            signal.confidence = trade_score.total_score
            signal.reason = f"{signal.reason} | Score: {trade_score.total_score:.0f} ({trade_score.verdict})"
            
            # We no longer drop IGNORE signals here. We collect them to find the best one.
            
            expectancy_r = self._learning_engine.get_expectancy(
                strategy_id=strategy.id,
                instrument=snapshot.instrument,
                regime=snapshot.regime,
            )
            signals.append((strategy, signal, expectancy_r, trade_score))
            
        if not signals:
            self._log.debug("No strategies produced signals for instrument=%s timeframe=%s", snapshot.instrument, snapshot.timeframe)
            # Emit NO_TRADE even in continuous mode so Telegram Bot can track "why"
            await self._emit_no_trade(snapshot)
            return

        # Sort by score descending
        signals.sort(key=lambda x: x[3].total_score, reverse=True)
        best_strategy, best_signal, best_expectancy, best_score = signals[0]

        if best_score.verdict == "IGNORE":
             self._log.debug("Best signal rejected by ScoringEngine (score %.1f)", best_score.total_score)
             # Emit explicit NO_TRADE with score details so Bot knows about it
             await self._emit_no_trade_with_score(snapshot, best_score, best_strategy.id)
             return

        self._log.debug(
            "Collected %d strategy signals for instrument=%s timeframe=%s",
            len(signals),
            snapshot.instrument,
            snapshot.timeframe,
        )
        
        # Pass only the best signal (or filtered list) to _emit_best_decision
        # Since we already found the best one and it is NOT IGNORE, we can proceed.
        # However, _emit_best_decision expects a list of (Strategy, Signal, Expectancy)
        # We will pass just the best one to ensure it is the one executed.
        await self._emit_best_decision(snapshot, [(best_strategy, best_signal, best_expectancy)])

    async def _emit_no_trade_with_score(self, snapshot, trade_score, strategy_id: str) -> None:
        self._log.info("Emitting NO_TRADE (IGNORE) for instrument=%s score=%.1f", snapshot.instrument, trade_score.total_score)
        decision_id = f"no_trade_{snapshot.instrument}_{snapshot.timeframe}_{int(datetime.utcnow().timestamp())}"
        tv_link = get_tv_link(snapshot.instrument)
        
        # Build explanation from score components
        reasons = [f"{c.name}: {c.score:.1f}/10 ({c.reason})" for c in trade_score.components if c.score < 5.0]
        reason_text = "Słabe punkty: " + ", ".join(reasons) if reasons else "Niski wynik ogólny"
        
        decision = FinalDecision(
            decision_id=decision_id,
            instrument=snapshot.instrument,
            timeframe=snapshot.timeframe,
            verdict=DecisionVerdict.NO_TRADE,
            direction=None,
            entry_type="none",
            entry_price=0.0,
            sl_price=0.0,
            tp_price=0.0,
            rr=0.0,
            confidence=trade_score.total_score, # Pass the real score!
            strategy_id=strategy_id,
            regime=snapshot.regime,
            expectancy_r=0.0,
            tradingview_link=tv_link,
            explanation_text=f"Wynik: {trade_score.total_score:.0f}/100 (IGNORE). {reason_text}",
            metadata={"verdict": "IGNORE", "raw_score": trade_score.raw_score},
        )
        await self._event_bus.publish(
            Event(
                type=EventType.DECISION_READY,
                payload=decision,
                timestamp=datetime.utcnow(),
            )
        )
        if self._startup_mode and not risk_blocked:
            self._startup_mode = False

    async def _emit_no_trade(self, snapshot) -> None:
        """Emits a NO_TRADE decision when no strategy produces a valid signal."""
        self._log.info("Emitting NO_TRADE for instrument=%s timeframe=%s", snapshot.instrument, snapshot.timeframe)
        decision_id = f"no_trade_{snapshot.instrument}_{snapshot.timeframe}_{int(datetime.utcnow().timestamp())}"
        tv_link = get_tv_link(snapshot.instrument)
        decision = FinalDecision(
            decision_id=decision_id,
            instrument=snapshot.instrument,
            timeframe=snapshot.timeframe,
            verdict=DecisionVerdict.NO_TRADE,
            direction=None,
            entry_type="none",
            entry_price=0.0,
            sl_price=0.0,
            tp_price=0.0,
            rr=0.0,
            confidence=0.0,
            strategy_id="",
            regime=snapshot.regime,
            expectancy_r=0.0,
            tradingview_link=tv_link,
            explanation_text="Brak setupu spełniającego kryteria.",
            metadata={},
        )
        await self._event_bus.publish(
            Event(
                type=EventType.DECISION_READY,
                payload=decision,
                timestamp=datetime.utcnow(),
            )
        )

    def _get_current_session(self) -> str:
        """
        Determines the current trading session (UTC based).
        """
        hour = datetime.utcnow().hour
        if 22 <= hour or hour < 8:
            return "Asian"
        elif 8 <= hour < 13:
            return "London"
        elif 13 <= hour < 16:
            return "London/NY"
        elif 16 <= hour < 21:
            return "New York"
        else:
            return "Late NY"

    def _calculate_atr(self, candles: List[Candle], period: int = 14) -> float:
        """
        Calculates the Average True Range (ATR) for volatility estimation.
        
        Args:
            candles: List of Candle objects.
            period: The period for ATR calculation (default: 14).
            
        Returns:
            float: The ATR value.
        """
        if len(candles) < period + 1:
            return 0.0
            
        tr_list = []
        for i in range(1, len(candles)):
            curr = candles[i]
            prev = candles[i-1]
            hl = curr.high - curr.low
            h_pc = abs(curr.high - prev.close)
            l_pc = abs(curr.low - prev.close)
            tr = max(hl, h_pc, l_pc)
            tr_list.append(tr)
            
        if not tr_list:
            return 0.0
            
        atr = sum(tr_list[:period]) / period
        for i in range(period, len(tr_list)):
            atr = (atr * (period - 1) + tr_list[i]) / period
            
        return atr

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """
        Calculates the Relative Strength Index (RSI).
        
        Args:
            prices: List of closing prices.
            period: The period for RSI calculation (default: 14).
            
        Returns:
            float: The RSI value (0-100).
        """
        if len(prices) < period + 1:
            return 50.0
            
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        gains = [max(0, c) for c in changes]
        losses = [max(0, -c) for c in changes]
        
        if not gains:
            return 50.0
            
        # Simple Moving Average for first step
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # Smooth
        for i in range(period, len(changes)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _is_pinbar(self, candle: Candle, direction: str) -> bool:
        """
        Checks if a candle is a pinbar (long wick rejection).

        Args:
            candle: The candle to analyze.
            direction: 'long' (bullish pinbar) or 'short' (bearish pinbar).

        Returns:
            bool: True if pinbar pattern is detected.
        """
        body = abs(candle.close - candle.open)
        total_len = candle.high - candle.low
        if total_len == 0:
            return False
            
        lower_wick = min(candle.close, candle.open) - candle.low
        upper_wick = candle.high - max(candle.close, candle.open)
        
        # Bullish Pinbar: Long lower wick
        if direction == "long":
            return lower_wick > 2 * body and lower_wick > 2 * upper_wick
            
        # Bearish Pinbar: Long upper wick
        if direction == "short":
            return upper_wick > 2 * body and upper_wick > 2 * lower_wick
            
        return False

    def _calculate_volatility_percentile(self, instrument: str, current_volatility: float) -> float:
        """
        Calculates the percentile of the current volatility against historical values.
        Returns a float between 0.0 and 1.0.
        """
        if instrument not in self._volatility_history:
            self._volatility_history[instrument] = []
        
        history = self._volatility_history[instrument]
        history.append(current_volatility)
        
        # Keep last 500 samples (~2 days of M5 candles)
        if len(history) > 500:
            history.pop(0)
            
        if len(history) < 20:
            return 0.5  # Not enough data, assume average
            
        # Calculate percentile
        # Count how many samples are less than current
        count_below = sum(1 for v in history if v < current_volatility)
        return count_below / len(history)

    async def _emit_best_decision(
        self,
        snapshot,
        signals: List[tuple[Strategy, StrategySignal, float]],
    ) -> None:
        # --- RISK GUARD CHECK ---
        if not self._risk_guard.can_open_trade(snapshot.instrument):
             self._log.warning(f"RiskGuard blocked trade for {snapshot.instrument} (Daily limit reached)")
             
             decision_id = f"no_trade_risk_{snapshot.instrument}_{snapshot.timeframe}_{int(datetime.utcnow().timestamp())}"
             tv_link = get_tv_link(snapshot.instrument)
             
             decision = FinalDecision(
                decision_id=decision_id,
                instrument=snapshot.instrument,
                timeframe=snapshot.timeframe,
                verdict=DecisionVerdict.NO_TRADE,
                direction=None,
                entry_type="none",
                entry_price=0.0,
                sl_price=0.0,
                tp_price=0.0,
                rr=0.0,
                confidence=0.0,
                strategy_id="risk_guard",
                regime=snapshot.regime,
                expectancy_r=0.0,
                tradingview_link=tv_link,
                explanation_text="🛡️ Blokada RiskGuard: Osiągnięto dzienny limit transakcji.",
                metadata={"reason": "daily_limit_reached"},
            )
             await self._event_bus.publish(
                Event(
                    type=EventType.DECISION_READY,
                    payload=decision,
                    timestamp=datetime.utcnow(),
                )
            )
             return

        candles = snapshot.candles
        if not candles:
            return
        last_close = candles[-1].close
        regime_value = snapshot.regime.value if getattr(snapshot, "regime", None) else "unknown"
        window = candles[-20:] if len(candles) > 20 else candles
        closes = [c.close for c in window]
        avg = sum(closes) / len(closes)
        variance = sum((x - avg) ** 2 for x in closes) / len(closes)
        volatility = variance**0.5
        
        # Calculate Volatility Percentile & News Proximity
        vol_pct = self._calculate_volatility_percentile(snapshot.instrument, volatility)
        news_min = snapshot.time_to_news_min
        
        scored: List[tuple[float, Strategy, StrategySignal, float, str, dict]] = []
        for strategy, signal, expectancy_r in signals:
            if signal.stop_loss_price is None or signal.take_profit_price is None:
                continue
            sl = signal.stop_loss_price
            tp = signal.take_profit_price
            rr = abs(tp - last_close) / max(abs(last_close - sl), 1e-6)
            
            # Prepare extended ML Payload (Feature Engineering)
            direction = TradeDirection.LONG if signal.signal_type.name == "BUY" else TradeDirection.SHORT
            
            atr_val = self._calculate_atr(window, 14)
            sl_dist = abs(last_close - sl)
            sl_dist_atr = sl_dist / atr_val if atr_val > 0 else 0.0
            
            current_session = self._get_current_session()
            
            # Simple Trend Bias (using SMA50 on current timeframe as proxy if HTF not available)
            sma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else avg
            trend_bias = 1 if last_close > sma50 else -1
            
            ml_payload = {
                "instrument": snapshot.instrument,
                "timeframe": snapshot.timeframe,
                "strategy_id": strategy.id,
                "features": {
                    "strategy_type": strategy.id, # Map or use ID
                    "direction_sign": 1 if direction == TradeDirection.LONG else -1,
                    "rr": rr,
                    "confidence": signal.confidence,
                    "expectancy_r": expectancy_r,
                    "sl_distance_atr": sl_dist_atr,
                    "regime": regime_value,
                    "volatility_percentile": vol_pct,
                    "htf_bias": trend_bias, # Using current TF trend as proxy
                    "news_proximity": news_min,
                    "session": current_session
                },
            }
            
            ml_result = await self._ml_client.evaluate_setup(ml_payload)
            if ml_result.get("blacklisted", False):
                self._log.info(f"ML Blacklisted {strategy.id}: {ml_result.get('reason')}")
                continue
                
            adjustments = ml_result.get("parameter_adjustments") or {}
            min_confidence = adjustments.get("min_confidence")
            min_rr = adjustments.get("min_rr")
            
            if isinstance(min_confidence, (int, float)) and signal.confidence < float(min_confidence):
                continue
            if isinstance(min_rr, (int, float)) and rr < float(min_rr):
                continue
                
            ml_score = float(ml_result.get("ml_score", 0.0))
            ml_reason = ml_result.get("reason", "")
            
            # Base score from signal confidence (usually 70)
            score = signal.confidence
            score_reasons = []
            
            # If ML provided a score, blend it? 
            # Current logic: Add bonuses. But ML score is 0-100.
            # Let's use ML score as a major factor if available (>0).
            # If ML mode is active, ml_score is the authority?
            # For now, let's keep the hybrid approach but include ML feedback.
            
            if ml_score > 0:
                # If ML gives a score, maybe we average it with confidence?
                # Or just use it as a bonus?
                # Let's add (ml_score - 50) * 0.5 as adjustment
                adjustment = (ml_score - 50) * 0.5
                score += adjustment
                score_reasons.append(f"ML Adjustment ({adjustment:+.1f})")

            # --- OLD HEURISTICS (Still useful if ML is simple) ---
            if rr >= 2.0:
                bonus = 5.0
                score += bonus
                score_reasons.append(f"Wysoki R:R (>2.0, +{bonus:.0f}pkt)")


            if rr >= 3.0:
                bonus = 5.0
                score += bonus
                score_reasons.append(f"Bardzo dobry R:R (>3.0, +{bonus:.0f}pkt)")
            
            if volatility >= 0.02:
                bonus = 5.0
                score += bonus
                score_reasons.append(f"Wysoka zmienność rynku (+{bonus:.0f}pkt)")
            
            if expectancy_r >= 0.5:
                bonus = 10.0
                score += bonus
                score_reasons.append(f"Bardzo wysoka historyczna skuteczność (+{bonus:.0f}pkt)")
            elif expectancy_r >= 0.2:
                bonus = 5.0
                score += bonus
                score_reasons.append(f"Dobra historyczna skuteczność (+{bonus:.0f}pkt)")
                
            if ml_score >= 0.7:
                bonus = 10.0
                score += bonus
                score_reasons.append(f"Potwierdzenie przez AI (+{bonus:.0f}pkt)")

            # RSI Analysis
            rsi = self._calculate_rsi(closes)
            is_long = signal.signal_type.name == "BUY"
            
            if is_long:
                if 40 <= rsi <= 60:
                    bonus = 5.0
                    score += bonus
                    score_reasons.append(f"RSI idealne pod wzrosty ({rsi:.1f}, +{bonus:.0f}pkt)")
                elif rsi < 70:
                    bonus = 2.0
                    score += bonus
                    score_reasons.append(f"RSI bezpieczne ({rsi:.1f}, +{bonus:.0f}pkt)")
                elif rsi >= 70:
                    score -= 5.0
                    score_reasons.append(f"RSI wykupione ({rsi:.1f}, -5pkt)")
            else:
                if 40 <= rsi <= 60:
                    bonus = 5.0
                    score += bonus
                    score_reasons.append(f"RSI idealne pod spadki ({rsi:.1f}, +{bonus:.0f}pkt)")
                elif rsi > 30:
                    bonus = 2.0
                    score += bonus
                    score_reasons.append(f"RSI bezpieczne ({rsi:.1f}, +{bonus:.0f}pkt)")
                elif rsi <= 30:
                    score -= 5.0
                    score_reasons.append(f"RSI wyprzedane ({rsi:.1f}, -5pkt)")

            # Price Action Bonus (Simple Pinbar)
            last_candle = candles[-1]
            if self._is_pinbar(last_candle, "long" if is_long else "short"):
                bonus = 5.0
                score += bonus
                score_reasons.append(f"Price Action: Pinbar zgodny z kierunkiem (+{bonus:.0f}pkt)")
            
            # Cap at 99
            score = min(score, 99.0)
            
            # Combine reasons for explanation
            reason_text = ", ".join(score_reasons) if score_reasons else "Standardowy setup"
            
            scored.append((score, strategy, signal, expectancy_r, ml_result.get("reason", ""), adjustments, reason_text))
        if not scored:
            self._log.debug("All candidate signals filtered out by ML/parameters for instrument=%s timeframe=%s", snapshot.instrument, snapshot.timeframe)
            await self._emit_no_trade(snapshot)
            return
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_strategy, best_signal, best_expectancy, ml_reason, best_adjustments, score_reason_text = scored[0]
        self._log.info(
            "Best signal score=%.2f instrument=%s timeframe=%s strategy=%s rr=%.2f conf=%.0f",
            best_score,
            snapshot.instrument,
            snapshot.timeframe,
            best_strategy.id,
            abs(best_signal.take_profit_price - best_signal.take_profit_price) if best_signal.take_profit_price and best_signal.take_profit_price else 0.0,
            best_signal.confidence,
        )
        instrument = snapshot.instrument
        first_time = instrument not in self._seen_instruments
        if first_time:
            self._seen_instruments.add(instrument)
        min_score = 70.0 if first_time else 50.0
        if best_score < min_score:
            self._log.debug("Best score below threshold (%.2f<%.2f) -> NO_TRADE for instrument=%s timeframe=%s", best_score, min_score, snapshot.instrument, snapshot.timeframe)
            await self._emit_no_trade(snapshot)
            return
        risk_blocked = not self._risk_guard.can_open_trade(snapshot.instrument)
        if risk_blocked:
            self._log.info("RiskGuard blocked trade for instrument=%s (max trades reached)", snapshot.instrument)
        explanation = self._explain_engine.build_pre_trade_explanation(snapshot, best_signal, best_expectancy)
        
        # Append score reasons to explanation
        final_explanation = explanation.pre_trade
        if score_reason_text and score_reason_text != "Standardowy setup":
            final_explanation += f"\nDodatkowe atuty: {score_reason_text}."
            
        sl = best_signal.stop_loss_price
        tp = best_signal.take_profit_price
        if sl is None or tp is None:
            await self._emit_no_trade(snapshot)
            return
        rr = abs(tp - last_close) / max(abs(last_close - sl), 1e-6)
        
        direction = TradeDirection.LONG if best_signal.signal_type.name == "BUY" else TradeDirection.SHORT
        tv_link = get_tv_link(snapshot.instrument)
        decision_id = f"{best_strategy.id}_{snapshot.instrument}_{snapshot.timeframe}_{int(datetime.utcnow().timestamp())}"
        if not risk_blocked:
            self._risk_guard.register_trade(snapshot.instrument)
        sizing_input = PositionSizingInput(
            signal=best_signal,
            account_balance=self._account_balance,
            stop_loss_price=best_signal.stop_loss_price,
        )
        suggested_units = self._risk_engine.calculate_units(sizing_input)
        metadata = {"suggested_units": suggested_units}
        if ml_reason:
            metadata["ml_reason"] = ml_reason
        if best_adjustments:
            metadata["ml_parameter_adjustments"] = best_adjustments
        if risk_blocked:
            metadata["risk_blocked"] = True
            
        # Cap confidence at 99
        final_confidence = min(best_score, 99.0)
        
        decision = FinalDecision(
            decision_id=decision_id,
            instrument=snapshot.instrument,
            timeframe=snapshot.timeframe,
            verdict=DecisionVerdict.BUY if direction == TradeDirection.LONG else DecisionVerdict.SELL,
            direction=direction,
            entry_type="market",
            entry_price=last_close,
            sl_price=sl,
            tp_price=tp,
            rr=rr,
            confidence=final_confidence,
            strategy_id=best_strategy.id,
            regime=snapshot.regime,
            expectancy_r=best_expectancy,
            tradingview_link=tv_link,
            explanation_text=final_explanation, # Simplified explanation with reasons
            metadata=metadata,
        )
        await self._event_bus.publish(
            Event(
                type=EventType.DECISION_READY,
                payload=decision,
                timestamp=datetime.utcnow(),
            )
        )

    async def _emit_order(self, signal: StrategySignal) -> None:
        direction = TradeDirection.LONG if signal.signal_type.name == "BUY" else TradeDirection.SHORT
        sizing_input = PositionSizingInput(
            signal=signal,
            account_balance=self._account_balance,
            stop_loss_price=signal.stop_loss_price,
        )
        units = self._risk_engine.calculate_units(sizing_input)
        order = OrderRequest(
            instrument=signal.instrument,
            units=units,
            direction=direction,
            stop_loss_price=signal.stop_loss_price,
            take_profit_price=signal.take_profit_price,
            client_tag=f"{signal.strategy_id}_{int(datetime.utcnow().timestamp())}",
            strategy_id=signal.strategy_id,
            confidence=signal.confidence,
        )
        await self._event_bus.publish(
            Event(
                type=EventType.ORDER_REQUEST,
                payload=order,
                timestamp=datetime.utcnow(),
            )
        )