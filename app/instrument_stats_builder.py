from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp

from app.config import Config, Paths


def _parse_datetime(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return datetime.utcnow()


@dataclass(frozen=True)
class InstrumentKey:
    instrument: str
    timeframe: str


@dataclass
class TradePoint:
    opened_at: datetime
    r: float


@dataclass
class InstrumentStats:
    trades: int
    wins: int
    losses: int
    flats: int
    sum_r: float
    expectancy_r: float
    best_r: float
    worst_r: float
    max_drawdown_r: float
    from_date: Optional[datetime]
    to_date: Optional[datetime]


class InstrumentStatsBuilder:
    def __init__(self, config: Config):
        self._config = config
        self._log = logging.getLogger("stats_builder")

    def _load_trades(self) -> Dict[InstrumentKey, List[TradePoint]]:
        trades_dir = Paths.TRADES_DIR
        result: Dict[InstrumentKey, List[TradePoint]] = {}
        if not trades_dir.exists():
            return result
        for path in trades_dir.glob("*.json"):
            content = path.read_text(encoding="utf-8").strip()
            if not content:
                continue
            try:
                records = json.loads(content)
            except Exception as e:
                self._log.warning(f"Failed to parse JSON from {path}: {e}")
                continue
            if not isinstance(records, list):
                continue
            for record in records:
                if not isinstance(record, dict):
                    continue
                r_val = record.get("profit_loss_r")
                if r_val is None:
                    continue
                try:
                    r = float(r_val)
                except (TypeError, ValueError) as e:
                    self._log.warning(f"Invalid profit_loss_r value '{r_val}' in {path}: {e}")
                    continue
                instrument = record.get("instrument")
                if not instrument:
                    continue
                metadata = record.get("metadata") or {}
                timeframe = metadata.get("timeframe") or "unknown"
                opened_at_raw = record.get("opened_at")
                opened_at = _parse_datetime(str(opened_at_raw)) if opened_at_raw else None
                if opened_at is None:
                    opened_at = datetime.utcnow()
                key = InstrumentKey(instrument=instrument, timeframe=timeframe)
                points = result.setdefault(key, [])
                points.append(TradePoint(opened_at=opened_at, r=r))
        return result

    def _compute_stats(self, points: List[TradePoint]) -> InstrumentStats:
        if not points:
            return InstrumentStats(
                trades=0,
                wins=0,
                losses=0,
                flats=0,
                sum_r=0.0,
                expectancy_r=0.0,
                best_r=0.0,
                worst_r=0.0,
                max_drawdown_r=0.0,
                from_date=None,
                to_date=None,
            )
        points_sorted = sorted(points, key=lambda p: p.opened_at)
        total = 0
        wins = 0
        losses = 0
        flats = 0
        sum_r = 0.0
        best_r = float("-inf")
        worst_r = float("inf")
        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        for p in points_sorted:
            r = p.r
            total += 1
            sum_r += r
            if r > 0:
                wins += 1
            elif r < 0:
                losses += 1
            else:
                flats += 1
            if r > best_r:
                best_r = r
            if r < worst_r:
                worst_r = r
            equity += r
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
        expectancy = sum_r / total if total > 0 else 0.0
        from_date = points_sorted[0].opened_at
        to_date = points_sorted[-1].opened_at
        if best_r == float("-inf"):
            best_r = 0.0
        if worst_r == float("inf"):
            worst_r = 0.0
        return InstrumentStats(
            trades=total,
            wins=wins,
            losses=losses,
            flats=flats,
            sum_r=sum_r,
            expectancy_r=expectancy,
            best_r=best_r,
            worst_r=worst_r,
            max_drawdown_r=max_dd,
            from_date=from_date,
            to_date=to_date,
        )

    async def get_stats_for_instrument(self, symbol: str) -> str:
        """Generates a text report for a specific instrument."""
        trades_by_key = self._load_trades()
        
        # Aggregate across all timeframes for this symbol
        all_points = []
        found = False
        
        for key, points in trades_by_key.items():
            if key.instrument.upper() == symbol.upper():
                all_points.extend(points)
                found = True
                
        if not found:
            return f"Brak danych historycznych dla {symbol}."
            
        stats = self._compute_stats(all_points)
        
        winrate = (stats.wins / stats.trades * 100) if stats.trades > 0 else 0
        
        msg = (
            f"📊 **STATYSTYKI** | {symbol.upper()}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔸 Liczba zagrań: {stats.trades}\n"
            f"🔸 Skuteczność: {winrate:.1f}%\n"
            f"🔸 Wynik całkowity: {stats.sum_r:.2f}R\n"
            f"🔸 Oczekiwana wartość (Exp): {stats.expectancy_r:.2f}R\n"
            f"🔸 Max Drawdown: {stats.max_drawdown_r:.2f}R\n"
            f"🔸 Najlepszy trade: {stats.best_r:.2f}R\n"
            f"🔸 Najgorszy trade: {stats.worst_r:.2f}R\n"
        )
        return msg

    async def get_total_summary(self) -> str:
        trades_by_key = self._load_trades()
        total_trades = 0
        sum_r = 0.0
        wins = 0
        losses = 0
        flats = 0

        for points in trades_by_key.values():
            stats = self._compute_stats(points)
            total_trades += stats.trades
            sum_r += stats.sum_r
            wins += stats.wins
            losses += stats.losses
            flats += stats.flats

        winrate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0

        lines = [
            "📊 **STATYSTYKI OGÓLNE**",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"🔸 Liczba zagrań: {total_trades}",
            f"🔸 Skuteczność: {winrate:.1f}%",
            f"🔸 Wynik całkowity: {sum_r:.2f}R",
            f"🔸 Wygrane: {wins} | Przegrane: {losses} | Zero: {flats}",
        ]
        return "\n".join(lines)
