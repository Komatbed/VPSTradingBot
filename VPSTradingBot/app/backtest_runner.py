from __future__ import annotations

import asyncio
import json
import os
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from app.config import Config
from app.core.models import Candle, MarketDataSnapshot, TradeDirection
from app.data.yahoo_client import YahooFinanceClient
from app.learning.engine import LearningEngine
from app.ml.client import MlAdvisorClient
from app.regime.engine import MarketRegimeEngine
from app.strategy.base import StrategyContext
from app.strategy.momentum_breakout import MomentumBreakoutStrategy
from app.strategy.range_reversion import RangeReversionStrategy
from app.strategy.trend_following import TrendFollowingStrategy


@dataclass
class BacktestTrade:
    instrument: str
    timeframe: str
    strategy_id: str
    direction: TradeDirection
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    r: float
    reason: str
    expectancy_r: float
    ml_score: float
    confidence: float
    rr: float
    ml_reason: str
    features: Optional[dict] = None


class BacktestEngine:
    def __init__(
        self,
        candles: List[Candle],
        instrument: str,
        timeframe: str,
        strategies=None,
        learning_engine: Optional[LearningEngine] = None,
        ml_client: Optional[MlAdvisorClient] = None,
    ) -> None:
        self._candles = candles
        self._instrument = instrument
        self._timeframe = timeframe
        self._regime_engine = MarketRegimeEngine()
        if strategies is None:
            strategies = [
                TrendFollowingStrategy(),
                RangeReversionStrategy(),
                MomentumBreakoutStrategy(),
            ]
        self._strategies = strategies
        self._learning_engine = learning_engine or LearningEngine()
        if learning_engine is None:
            self._learning_engine.refresh()
        self._ml_client = ml_client
        self.training_samples = [] # List to store (features, target) tuples

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [max(0, c) for c in changes]
        losses = [max(0, -c) for c in changes]
        if not gains:
            return 50.0
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        for i in range(period, len(changes)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _is_pinbar(self, candle, direction: str) -> bool:
        body = abs(candle.close - candle.open)
        total_len = candle.high - candle.low
        if total_len == 0:
            return False
        lower_wick = min(candle.close, candle.open) - candle.low
        upper_wick = candle.high - max(candle.close, candle.open)
        if direction == "long":
            return lower_wick > 2 * body and lower_wick > 2 * upper_wick
        if direction == "short":
            return upper_wick > 2 * body and upper_wick > 2 * lower_wick
        return False

    def _calculate_atr(self, candles: List[Candle], period: int = 14) -> float:
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

    def _get_session(self, timestamp: datetime) -> str:
        hour = timestamp.hour
        sessions = []
        if 0 <= hour < 9:
            sessions.append("asia")
        if 8 <= hour < 17:
            sessions.append("london")
        if 13 <= hour < 22:
            sessions.append("ny")
        if not sessions:
            return "quiet"
        return "_".join(sessions)

    async def run(self, risk_per_trade_percent: float) -> List[BacktestTrade]:
        trades: List[BacktestTrade] = []
        context = StrategyContext(max_risk_per_trade_percent=risk_per_trade_percent)
        open_trade: Optional[dict] = None
        candles = self._candles
        htf_window_size_str = os.environ.get("BACKTEST_HTF_WINDOW", "100")
        try:
            htf_window_size = max(int(htf_window_size_str), 1)
        except ValueError:
            htf_window_size = 100
        if len(candles) < 50:
            return trades
        ml_enabled = self._ml_client is not None and self._ml_client.is_enabled()
        score_threshold = 50.0 if ml_enabled else 30.0
        for idx in range(50, len(candles)):
            candle = candles[idx]
            regime = self._regime_engine.infer_regime(candles[: idx + 1])
            snapshot = MarketDataSnapshot(
                instrument=self._instrument,
                timeframe=self._timeframe,
                candles=candles[: idx + 1],
                spread=None,
                regime=regime,
            )
            if open_trade is not None:
                closed = self._try_close_trade(open_trade, candle)
                if closed is not None:
                    trades.append(closed)
                    open_trade = None
            if open_trade is not None:
                continue
            signals_info = []
            for strategy in self._strategies:
                signal = await strategy.on_market_data(snapshot, context)
                if signal is None:
                    continue
                if signal.stop_loss_price is None or signal.take_profit_price is None:
                    continue
                expectancy_r = self._learning_engine.get_expectancy(
                    strategy_id=strategy.id,
                    instrument=self._instrument,
                    regime=regime,
                )
                signals_info.append((strategy, signal, expectancy_r))
            if not signals_info:
                continue
            last_close = candle.close
            window = candles[max(0, idx - 20) : idx + 1]
            closes = [c.close for c in window]
            avg = sum(closes) / len(closes)
            variance = sum((x - avg) ** 2 for x in closes) / len(closes)
            volatility = variance**0.5
            htf_window = candles[max(0, idx - htf_window_size) : idx + 1]
            htf_closes = [c.close for c in htf_window]
            if len(htf_closes) > 1:
                htf_avg = sum(htf_closes) / len(htf_closes)
                htf_variance = sum((x - htf_avg) ** 2 for x in htf_closes) / len(htf_closes)
                htf_volatility = htf_variance**0.5
                htf_trend = (htf_closes[-1] - htf_closes[0]) / max(abs(htf_closes[0]), 1e-6)
            else:
                htf_volatility = volatility
                htf_trend = 0.0
            regime_value = regime.value if regime else "unknown"
            scored = []
            for strategy, signal, expectancy_r in signals_info:
                sl = signal.stop_loss_price
                tp = signal.take_profit_price
                rr = abs(tp - last_close) / max(abs(last_close - sl), 1e-6)
                ml_score = 0.0
                ml_reason = ""
                
                # Features for ML
                is_long = signal.signal_type.name == "BUY"
                direction = TradeDirection.LONG if is_long else TradeDirection.SHORT
                
                atr_window = candles[max(0, idx - 50) : idx + 1]
                atr = self._calculate_atr(atr_window)
                sl_dist = abs(candle.close - sl)
                sl_dist_atr = sl_dist / atr if atr > 0 else 0.0
                
                current_session = self._get_session(candle.time)

                features = {
                    "strategy_type": strategy.id,
                    "direction_sign": 1 if direction == TradeDirection.LONG else -1,
                    "rr": rr,
                    "confidence": signal.confidence,
                    "expectancy_r": expectancy_r,
                    "sl_distance_atr": sl_dist_atr,
                    "regime": regime_value,
                    "volatility_percentile": volatility,
                    "htf_bias": htf_trend,
                    "news_proximity": 999,
                    "session": current_session
                }

                if ml_enabled:
                    ml_payload = {
                        "instrument": self._instrument,
                        "timeframe": self._timeframe,
                        "strategy_id": strategy.id,
                        "features": features,
                    }
                    ml_result = await self._ml_client.evaluate_setup(ml_payload)  # type: ignore[union-attr]
                    if ml_result.get("blacklisted", False):
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
                
                # --- SCORING LOGIC MATCHING StrategyEngine ---
                # Base score from signal confidence (usually 70)
                score = signal.confidence
                
                # Add bonuses based on quality factors
                score_reasons = []
                
                if rr >= 2.0:
                    score += 5.0
                    score_reasons.append("High RR")
                if rr >= 3.0:
                    score += 5.0
                    score_reasons.append("Very High RR")
                
                if volatility >= 0.02:
                    score += 5.0
                    score_reasons.append("High Volatility")
                
                if expectancy_r >= 0.5:
                    score += 10.0
                    score_reasons.append("High Expectancy")
                elif expectancy_r >= 0.2:
                    score += 5.0
                    score_reasons.append("Good Expectancy")
                    
                if ml_score >= 0.7:
                    score += 10.0
                    score_reasons.append("AI Confirmation")

                # RSI Analysis
                rsi = self._calculate_rsi(closes)
                is_long = signal.signal_type.name == "BUY"
                
                if is_long:
                    if 40 <= rsi <= 60:
                        score += 5.0
                        score_reasons.append(f"RSI Ideal Buy ({rsi:.1f})")
                    elif rsi < 70:
                        score += 2.0
                        score_reasons.append(f"RSI Safe Buy ({rsi:.1f})")
                    elif rsi >= 70:
                        score -= 5.0
                        score_reasons.append(f"RSI Overbought ({rsi:.1f})")
                else:
                    if 40 <= rsi <= 60:
                        score += 5.0
                        score_reasons.append(f"RSI Ideal Sell ({rsi:.1f})")
                    elif rsi > 30:
                        score += 2.0
                        score_reasons.append(f"RSI Safe Sell ({rsi:.1f})")
                    elif rsi <= 30:
                        score -= 5.0
                        score_reasons.append(f"RSI Oversold ({rsi:.1f})")

                # Price Action Bonus (Simple Pinbar)
                if self._is_pinbar(candle, "long" if is_long else "short"):
                    score += 5.0
                    score_reasons.append("Pinbar")

                scored.append((score, strategy, signal, expectancy_r, ml_score, ml_reason, rr, features))
            if not scored:
                continue
            scored.sort(key=lambda x: x[0], reverse=True)
            best_score, best_strategy, best_signal, best_expectancy, best_ml_score, best_ml_reason, best_rr, best_features = scored[0]
            if best_score < score_threshold:
                continue
            direction = TradeDirection.LONG if best_signal.signal_type.name == "BUY" else TradeDirection.SHORT
            entry_price = candle.close
            open_trade = {
                "instrument": self._instrument,
                "timeframe": self._timeframe,
                "strategy_id": best_signal.strategy_id,
                "direction": direction,
                "entry_time": candle.time,
                "entry_price": entry_price,
                "sl": best_signal.stop_loss_price,
                "tp": best_signal.take_profit_price,
                "reason": best_signal.reason,
                "expectancy_r": best_expectancy,
                "ml_score": best_ml_score,
                "ml_reason": best_ml_reason,
                "confidence": best_signal.confidence,
                "rr": best_rr,
                "features": best_features,
            }
        if open_trade is not None:
            last_candle = candles[-1]
            closed = self._force_close_at_end(open_trade, last_candle)
            trades.append(closed)
        return trades

    def _try_close_trade(self, trade: dict, candle: Candle) -> Optional[BacktestTrade]:
        direction: TradeDirection = trade["direction"]
        sl = trade["sl"]
        tp = trade["tp"]
        entry_price = trade["entry_price"]
        low = candle.low
        high = candle.high
        if direction == TradeDirection.LONG:
            hit_sl = low <= sl
            hit_tp = high >= tp
            if hit_sl and hit_tp:
                exit_price = sl
            elif hit_sl:
                exit_price = sl
            elif hit_tp:
                exit_price = tp
            else:
                return None
        else:
            hit_sl = high >= sl
            hit_tp = low <= tp
            if hit_sl and hit_tp:
                exit_price = sl
            elif hit_sl:
                exit_price = sl
            elif hit_tp:
                exit_price = tp
            else:
                return None
        r_value = self._compute_r(direction, entry_price, exit_price, sl)

        # Collect training data
        if "features" in trade:
            sample = trade["features"].copy()
            sample["target"] = 1 if r_value >= 0.5 else 0
            self.training_samples.append(sample)

        return BacktestTrade(
            instrument=trade["instrument"],
            timeframe=trade["timeframe"],
            strategy_id=trade["strategy_id"],
            direction=direction,
            entry_time=trade["entry_time"],
            exit_time=candle.time,
            entry_price=entry_price,
            exit_price=exit_price,
            r=r_value,
            reason=trade["reason"],
            expectancy_r=trade.get("expectancy_r", 0.0),
            ml_score=trade.get("ml_score", 0.0),
            confidence=trade.get("confidence", 0.0),
            rr=trade.get("rr", 0.0),
            ml_reason=trade.get("ml_reason", ""),
        )

    def _force_close_at_end(self, trade: dict, candle: Candle) -> BacktestTrade:
        direction: TradeDirection = trade["direction"]
        entry_price = trade["entry_price"]
        exit_price = candle.close
        sl = trade["sl"]
        r_value = self._compute_r(direction, entry_price, exit_price, sl)
        return BacktestTrade(
            instrument=trade["instrument"],
            timeframe=trade["timeframe"],
            strategy_id=trade["strategy_id"],
            direction=direction,
            entry_time=trade["entry_time"],
            exit_time=candle.time,
            entry_price=entry_price,
            exit_price=exit_price,
            r=r_value,
            reason=trade["reason"],
            expectancy_r=trade.get("expectancy_r", 0.0),
            ml_score=trade.get("ml_score", 0.0),
            confidence=trade.get("confidence", 0.0),
            rr=trade.get("rr", 0.0),
            ml_reason=trade.get("ml_reason", ""),
        )

    def _compute_r(self, direction: TradeDirection, entry: float, exit: float, sl: float) -> float:
        if direction == TradeDirection.LONG:
            risk_per_unit = max(entry - sl, 1e-6)
            pnl_per_unit = exit - entry
        else:
            risk_per_unit = max(sl - entry, 1e-6)
            pnl_per_unit = entry - exit
        return pnl_per_unit / risk_per_unit


async def run_backtest() -> None:
    config = Config.from_env()
    symbols_env = os.environ.get("BACKTEST_SYMBOLS", "")
    if symbols_env.strip():
        symbols = [s.strip() for s in symbols_env.split(",") if s.strip()]
    else:
        symbols = list(dict.fromkeys(config.instruments)) if config.instruments else []
    if not symbols:
        print("Brak instrumentów do backtestu (sprawdź BACKTEST_SYMBOLS lub Config.instruments).")
        return
    timeframe = os.environ.get("BACKTEST_TIMEFRAME", config.timeframe)
    client = YahooFinanceClient()
    learning_engine = LearningEngine()
    learning_engine.refresh()
    ml_client = MlAdvisorClient(config)
    min_expect_1d = float(os.environ.get("BACKTEST_MIN_EXPECTANCY_1D", "0.0"))
    summary = {}
    max_1d_count_str = os.environ.get("BACKTEST_1D_COUNT", "10000")
    try:
        max_1d_count = max(int(max_1d_count_str), 1)
    except ValueError:
        max_1d_count = 10000

    all_training_samples = []
    for symbol in symbols:
        try:
            expectancy_1d = None
            if timeframe != "1d":
                tf_long = "1d"
                print(f"== Backtest {symbol} {tf_long} ==")
                candles = await client.fetch_candles(None, symbol=symbol, timeframe=tf_long, count=max_1d_count)
                if not candles:
                    print(f"Brak świec dla {symbol}, pomijam.")
                    continue
                else:
                    engine = BacktestEngine(
                        candles=candles,
                        instrument=symbol,
                        timeframe=tf_long,
                        learning_engine=learning_engine,
                        ml_client=ml_client,
                    )
                    trades = await engine.run(risk_per_trade_percent=config.risk_per_trade_percent)
                    print(f"DEBUG: Engine 1d samples: {len(engine.training_samples)}")
                    all_training_samples.extend(engine.training_samples)
                    if not trades:
                        print("Brak wygenerowanych trade’ów.")
                    else:
                        wins = [t for t in trades if t.r > 0]
                        losses = [t for t in trades if t.r < 0]
                        flats = [t for t in trades if t.r == 0]
                        sum_r = sum(t.r for t in trades)
                        expectancy_1d = sum_r / len(trades)
                        winrate = (len(wins) / len(trades)) * 100.0
                        print(f"Liczba trade’ów: {len(trades)}")
                        print(f"Wygrane: {len(wins)}, Przegrane: {len(losses)}, Remisy: {len(flats)}")
                        print(f"Suma R: {sum_r:.3f}, Expectancy: {expectancy_1d:.3f}R, Winrate: {winrate:.1f}%")
                        out_dir = Path("backtests")
                        out_dir.mkdir(parents=True, exist_ok=True)
                        out_path = out_dir / f"{symbol}_{tf_long}.json"
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
                        print(f"Zapisano trade’y do {out_path}")
                        stats = summary.setdefault(symbol, {})
                        stats["expectancy_1d"] = expectancy_1d
                        stats["trades_1d"] = len(trades)
                        stats["wins_1d"] = len(wins)
                        stats["losses_1d"] = len(losses)
                        stats["flats_1d"] = len(flats)
                        stats["sum_r_1d"] = sum_r
                        stats["winrate_1d"] = winrate
            if expectancy_1d is not None and expectancy_1d < min_expect_1d:
                print(f"Odrzucam {symbol} dla {timeframe} z powodu expectancy 1d.")
                continue

            print(f"== Backtest {symbol} {timeframe} ==")
            if timeframe in ("1d", "d1", "1day"):
                count = max_1d_count
            else:
                count = 1000
            candles = await client.fetch_candles(None, symbol=symbol, timeframe=timeframe, count=count)
            if not candles:
                print(f"Brak świec dla {symbol}, pomijam.")
                continue
            engine = BacktestEngine(
                candles=candles,
                instrument=symbol,
                timeframe=timeframe,
                learning_engine=learning_engine,
                ml_client=ml_client,
            )
            trades = await engine.run(risk_per_trade_percent=config.risk_per_trade_percent)
            all_training_samples.extend(engine.training_samples)
            
            if not trades:
                print(f"Brak trade’ów dla {symbol} {timeframe}.")
                continue
                
            wins = [t for t in trades if t.r > 0]
            losses = [t for t in trades if t.r < 0]
            sum_r = sum(t.r for t in trades)
            expectancy = sum_r / len(trades)
            winrate = (len(wins) / len(trades)) * 100.0
            
            print(f"Wynik {symbol} {timeframe}: {len(trades)} trades, R: {sum_r:.2f}, Exp: {expectancy:.2f}R")
            
            stats_tf = summary.setdefault(symbol, {})
            key = f"expectancy_{timeframe}"
            stats_tf[key] = expectancy
            stats_tf["trades_timeframe"] = len(trades)
            stats_tf["wins_timeframe"] = len(wins)
            stats_tf["losses_timeframe"] = len(losses)
            stats_tf["flats_timeframe"] = len(flats)
            stats_tf["sum_r_timeframe"] = sum_r
            stats_tf["winrate_timeframe"] = winrate
            
        except Exception as e:
            print(f"BŁĄD KRYTYCZNY przy przetwarzaniu {symbol}: {e}")
            continue

    if summary:
        out_dir = Path("backtests")
        out_dir.mkdir(parents=True, exist_ok=True)
        ranking = []
        for symbol, values in summary.items():
            e1d = values.get("expectancy_1d")
            einf = values.get(f"expectancy_{timeframe}")
            ranking.append(
                {
                    "instrument": symbol,
                    "expectancy_1d": e1d,
                    "trades_1d": values.get("trades_1d"),
                    "wins_1d": values.get("wins_1d"),
                    "losses_1d": values.get("losses_1d"),
                    "flats_1d": values.get("flats_1d"),
                    "sum_r_1d": values.get("sum_r_1d"),
                    "winrate_1d": values.get("winrate_1d"),
                    "expectancy_timeframe": einf,
                    "trades_timeframe": values.get("trades_timeframe"),
                    "wins_timeframe": values.get("wins_timeframe"),
                    "losses_timeframe": values.get("losses_timeframe"),
                    "flats_timeframe": values.get("flats_timeframe"),
                    "sum_r_timeframe": values.get("sum_r_timeframe"),
                    "winrate_timeframe": values.get("winrate_timeframe"),
                }
            )
        ranking.sort(key=lambda x: (x["expectancy_timeframe"] is None, -(x["expectancy_timeframe"] or -1e9)))
        summary_path = out_dir / f"summary_{timeframe}.json"
        summary_path.write_text(json.dumps(ranking, ensure_ascii=False, indent=2), encoding="utf-8")
        csv_lines = [
            "instrument,expectancy_1d,trades_1d,wins_1d,losses_1d,flats_1d,sum_r_1d,winrate_1d,expectancy_timeframe,trades_timeframe,wins_timeframe,losses_timeframe,flats_timeframe,sum_r_timeframe,winrate_timeframe"
        ]
        for row in ranking:
            csv_lines.append(
                ",".join(
                    [
                        row["instrument"],
                        str(row["expectancy_1d"] if row["expectancy_1d"] is not None else ""),
                        str(row["trades_1d"] if row["trades_1d"] is not None else ""),
                        str(row["wins_1d"] if row["wins_1d"] is not None else ""),
                        str(row["losses_1d"] if row["losses_1d"] is not None else ""),
                        str(row["flats_1d"] if row["flats_1d"] is not None else ""),
                        str(row["sum_r_1d"] if row["sum_r_1d"] is not None else ""),
                        str(row["winrate_1d"] if row["winrate_1d"] is not None else ""),
                        str(row["expectancy_timeframe"] if row["expectancy_timeframe"] is not None else ""),
                        str(row["trades_timeframe"] if row["trades_timeframe"] is not None else ""),
                        str(row["wins_timeframe"] if row["wins_timeframe"] is not None else ""),
                        str(row["losses_timeframe"] if row["losses_timeframe"] is not None else ""),
                        str(row["flats_timeframe"] if row["flats_timeframe"] is not None else ""),
                        str(row["sum_r_timeframe"] if row["sum_r_timeframe"] is not None else ""),
                        str(row["winrate_timeframe"] if row["winrate_timeframe"] is not None else ""),
                    ]
                )
            )
        csv_path = out_dir / f"summary_{timeframe}.csv"
        csv_path.write_text("\n".join(csv_lines), encoding="utf-8")

    if all_training_samples:
        train_data_dir = Path("ml")
        train_data_dir.mkdir(parents=True, exist_ok=True)
        train_data_path = train_data_dir / "training_data.csv"
        
        # Get keys from the first sample
        fieldnames = list(all_training_samples[0].keys())
        
        with open(train_data_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_training_samples)
        print(f"Zapisano dane treningowe ({len(all_training_samples)} próbek) do {train_data_path}")


if __name__ == "__main__":
    asyncio.run(run_backtest())
