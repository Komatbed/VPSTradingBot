import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
import glob

from app.config import Paths

class PerformanceReportGenerator:
    """
    Generuje raporty wydajności w HTML na podstawie historii transakcji i decyzji.
    Uwzględnia zarówno zrealizowane transakcje, jak i odrzucone sygnały (Transparency).
    """
    def __init__(self):
        self._log = logging.getLogger("PerformanceReport")
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
        self.journal_dir = Path("journal")
        
    def generate_html_report(self, days: int = 7) -> str:
        """
        Generuje raport HTML i zwraca ścieżkę do pliku.
        Analizuje dane z ostatnich `days` dni.
        """
        trades = self._load_trade_history(days)
        decisions = self._load_decision_history(days)
        
        stats = self._calculate_stats(trades)
        rejection_stats = self._analyze_rejections(decisions)
        
        html_content = self._build_html(stats, rejection_stats, trades, decisions)
        
        filename = f"raport_wydajnosci_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.html"
        file_path = self.reports_dir / filename
        file_path.write_text(html_content, encoding="utf-8")
        
        self._log.info("Wygenerowano raport wydajności: %s", file_path)
        return str(file_path)

    def _load_trade_history(self, days: int) -> List[Dict[str, Any]]:
        """Ładuje historię transakcji (aktywne + zakończone) z ostatnich dni."""
        trades = []
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 1. Active Trades (bieżące pozycje)
        if Paths.ACTIVE_TRADES.exists():
            try:
                data = json.loads(Paths.ACTIVE_TRADES.read_text(encoding="utf-8"))
                for t in data.values():
                    t['status'] = 'ACTIVE'
                    trades.append(t)
            except Exception:
                pass
        
        # 2. Completed Trades (z plików dziennych)
        # Szukamy plików YYYY-MM-DD_trades.json
        if Paths.TRADES_DIR.exists():
            for file_path in Paths.TRADES_DIR.glob("*_trades.json"):
                # Sprawdź datę pliku po nazwie
                try:
                    date_str = file_path.name.split('_')[0]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if file_date < cutoff_date:
                        continue
                        
                    content = file_path.read_text(encoding="utf-8")
                    if not content.strip():
                        continue
                        
                    day_trades = json.loads(content)
                    for t in day_trades:
                        t['status'] = 'CLOSED'
                        trades.append(t)
                except Exception:
                    continue
                    
        return trades

    def _load_decision_history(self, days: int) -> List[Dict[str, Any]]:
        """Ładuje historię wszystkich decyzji (w tym odrzuconych) z dziennika."""
        decisions = []
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        if self.journal_dir.exists():
            for file_path in self.journal_dir.glob("*_decisions.jsonl"):
                try:
                    date_str = file_path.name.split('_')[0]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if file_date < cutoff_date:
                        continue
                        
                    content = file_path.read_text(encoding="utf-8")
                    for line in content.splitlines():
                        if not line.strip():
                            continue
                        decisions.append(json.loads(line))
                except Exception:
                    continue
        
        return decisions

    def _calculate_stats(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Oblicza statystyki handlowe."""
        total_trades = len(trades)
        if total_trades == 0:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_pnl_r": 0.0,
                "active_count": 0,
                "closed_count": 0
            }
            
        wins = 0
        losses = 0
        total_pnl = 0.0
        active_count = 0
        closed_count = 0
        
        for t in trades:
            if t.get('status') == 'ACTIVE':
                active_count += 1
            else:
                closed_count += 1
                
            pnl = t.get("current_profit_r", t.get("profit_loss_r", 0.0)) or 0.0
            # Ensure pnl is float
            try:
                pnl = float(pnl)
            except:
                pnl = 0.0
                
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1
            total_pnl += pnl
            
        # Win rate liczony tylko dla zamkniętych, chyba że brak zamkniętych
        denom = (wins + losses) if (wins + losses) > 0 else 1
        win_rate = (wins / denom) * 100
        
        return {
            "total_trades": total_trades,
            "active_count": active_count,
            "closed_count": closed_count,
            "win_rate": win_rate,
            "total_pnl_r": total_pnl
        }

    def _analyze_rejections(self, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analizuje przyczyny odrzuceń transakcji."""
        total_decisions = len(decisions)
        rejections = [d for d in decisions if d.get('verdict') in ('IGNORE', 'NO_TRADE', 'WATCHLIST')]
        
        reasons = {}
        for r in rejections:
            # Próbujemy wyciągnąć główny powód
            reason = "Nieznany"
            metadata = r.get('metadata', {})
            
            if metadata.get('reason') == 'risk_guard':
                reason = f"RiskGuard: {metadata.get('risk_details', 'Limit')}"
            elif metadata.get('ml_reason'):
                reason = f"ML: {metadata.get('ml_reason')}"
            elif 'raw_score' in metadata:
                score = metadata['raw_score']
                reason = f"Niski Wynik ({score:.0f} pkt)"
            else:
                # Parsowanie explanation_text jako fallback
                expl = r.get('explanation_text', '')
                if 'News Risk' in expl:
                    reason = "Ryzyko Newsowe"
                elif 'Spread' in expl:
                    reason = "Wysoki Spread"
                else:
                    reason = "Inny (Scoring)"
            
            reasons[reason] = reasons.get(reason, 0) + 1
            
        return {
            "total_decisions": total_decisions,
            "rejected_count": len(rejections),
            "reasons": reasons
        }

    def _build_html(self, stats: Dict[str, Any], rejections: Dict[str, Any], 
                   trades: List[Dict[str, Any]], decisions: List[Dict[str, Any]]) -> str:
        """Generuje kod HTML raportu."""
        
        # Sekcja Transakcji
        trade_rows = ""
        for t in sorted(trades, key=lambda x: x.get('opened_at', ''), reverse=True):
            pnl = float(t.get("current_profit_r", t.get("profit_loss_r", 0.0)) or 0.0)
            color = "green" if pnl > 0 else "red" if pnl < 0 else "black"
            status = t.get('status', '?')
            
            trade_rows += f"""
            <tr>
                <td>{t.get('instrument')}</td>
                <td>{t.get('direction')}</td>
                <td>{t.get('opened_at', '')[:16]}</td>
                <td>{status}</td>
                <td style="color: {color}; font-weight: bold;">{pnl:.2f}R</td>
            </tr>
            """
            
        # Sekcja Odrzuceń
        rejection_rows = ""
        # Sortuj powody malejąco
        sorted_reasons = sorted(rejections['reasons'].items(), key=lambda x: x[1], reverse=True)
        for reason, count in sorted_reasons:
            rejection_rows += f"""
            <tr>
                <td>{reason}</td>
                <td>{count}</td>
                <td>{count / rejections['rejected_count'] * 100:.1f}%</td>
            </tr>
            """

        return f"""
        <!DOCTYPE html>
        <html lang="pl">
        <head>
            <meta charset="UTF-8">
            <title>Raport Wydajności VPS Bot</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f7fa; color: #333; }}
                h1, h2 {{ color: #2c3e50; }}
                .container {{ max_width: 1200px; margin: 0 auto; }}
                .card {{ background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }}
                .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
                .metric-box {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 6px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #2980b9; }}
                .metric-label {{ font-size: 14px; color: #7f8c8d; margin-top: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
                th {{ background-color: #f8f9fa; font-weight: 600; color: #2c3e50; }}
                tr:hover {{ background-color: #f1f1f1; }}
                .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
                .badge-success {{ background: #d4edda; color: #155724; }}
                .badge-danger {{ background: #f8d7da; color: #721c24; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📈 Raport Wydajności VPS Bot</h1>
                <p>Wygenerowano: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                
                <div class="card">
                    <h2>Podsumowanie</h2>
                    <div class="grid">
                        <div class="metric-box">
                            <div class="metric-value">{stats['total_trades']}</div>
                            <div class="metric-label">Wszystkie Transakcje</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-value">{stats['win_rate']:.1f}%</div>
                            <div class="metric-label">Win Rate</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-value" style="color: {'green' if stats['total_pnl_r'] >= 0 else 'red'}">
                                {stats['total_pnl_r']:.2f}R
                            </div>
                            <div class="metric-label">Całkowity PnL</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-value">{rejections['rejected_count']}</div>
                            <div class="metric-label">Odrzucone Sygnały</div>
                        </div>
                    </div>
                </div>
                
                <div class="grid">
                    <div class="card">
                        <h2>🚫 Analiza Odrzuceń</h2>
                        <p>Dlaczego bot nie zawiera transakcji?</p>
                        <table>
                            <thead>
                                <tr>
                                    <th>Powód</th>
                                    <th>Liczba</th>
                                    <th>Udział</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rejection_rows}
                            </tbody>
                        </table>
                        {f'<p><i>Przeanalizowano {rejections["total_decisions"]} decyzji.</i></p>' if rejections["total_decisions"] > 0 else ''}
                    </div>
                    
                    <div class="card">
                        <h2>📜 Ostatnie Transakcje</h2>
                        <table>
                            <thead>
                                <tr>
                                    <th>Instrument</th>
                                    <th>Kierunek</th>
                                    <th>Czas</th>
                                    <th>Status</th>
                                    <th>Wynik (R)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {trade_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
