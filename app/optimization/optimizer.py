import time
import random
import json
import tracemalloc
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import logging

from fpdf import FPDF
from app.config import Config

# Setup logging
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    iteration: int
    execution_time_ms: float
    memory_peak_kb: float
    success: bool
    score: float
    error: Optional[str] = None

@dataclass
class SuiteResult:
    timestamp: str
    config_snapshot: Dict[str, Any]
    results: List[TestResult]
    avg_execution_time: float
    avg_memory_peak: float
    success_rate: float
    total_score: float

class OptimizationEngine:
    def __init__(self, base_config: Config):
        self.base_config = base_config
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)

    def _simulate_strategy_logic(self, config: Config, data_seed: int) -> float:
        """
        Simulates strategy execution logic influenced by config parameters.
        Returns a 'score' (simulated profit/loss or quality metric).
        """
        random.seed(data_seed)
        
        # Simulate market conditions (0-100)
        market_volatility = random.uniform(0, 100)
        market_trend = random.uniform(0, 100)
        signal_strength = random.uniform(0, 100)
        
        # Config parameters
        sensitivity = config.algo_sensitivity
        threshold = config.threshold_value
        reaction = config.reaction_time
        detail = config.detail_level
        
        # Logic simulation
        # Higher sensitivity = more signals but more noise
        detected_signal = signal_strength * (sensitivity / 50.0)
        
        # Noise factor (higher sensitivity = more noise)
        noise = random.uniform(-10, 10) * (sensitivity / 50.0)
        final_signal = detected_signal + noise
        
        # Threshold check
        if final_signal > threshold:
            # Trade executed
            # Higher detail level = better execution quality but slower (simulated elsewhere)
            execution_quality = min(1.0, (detail / 100.0) + 0.5)
            
            # Reaction time penalty: lower reaction time (faster) is better?
            # Let's assume 'reaction_time' param 0=fastest, 100=slowest? 
            # Or 0-100 is "speed score" where 100 is best. Let's assume 100 is best (fastest).
            speed_bonus = (reaction / 100.0) * 10
            
            # Outcome
            # If market trend aligns with signal, win.
            win_prob = 0.5 + (signal_strength - 50) / 200.0 + (detail / 200.0)
            is_win = random.random() < win_prob
            
            if is_win:
                return 10.0 * execution_quality + speed_bonus
            else:
                return -5.0 # Loss
        
        return 0.0 # No trade

    def run_test_suite(self, config_overrides: Dict[str, int]) -> SuiteResult:
        """
        Runs 20 unit tests/simulations for the given configuration.
        """
        # Apply overrides
        temp_config = Config.from_env() # Start fresh
        temp_config.update_from_dict(config_overrides)
        
        results = []
        
        logger.info(f"Starting test suite for config: {config_overrides}")
        
        for i in range(20):
            tracemalloc.start()
            start_time = time.perf_counter()
            
            try:
                # Run simulation
                score = self._simulate_strategy_logic(temp_config, data_seed=i)
                success = score > 0
                error = None
            except Exception as e:
                score = 0
                success = False
                error = str(e)
            
            end_time = time.perf_counter()
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            results.append(TestResult(
                iteration=i + 1,
                execution_time_ms=(end_time - start_time) * 1000,
                memory_peak_kb=peak / 1024,
                success=success,
                score=score,
                error=error
            ))
            
        # Aggregate
        avg_time = sum(r.execution_time_ms for r in results) / len(results)
        avg_mem = sum(r.memory_peak_kb for r in results) / len(results)
        success_rate = sum(1 for r in results if r.success) / len(results) * 100
        total_score = sum(r.score for r in results)
        
        # Check for regressions/alerts
        if success_rate < 30:
            self._send_email_alert(
                "Critical Performance Regression",
                f"Success rate dropped to {success_rate}%. Config: {config_overrides}"
            )

        return SuiteResult(
            timestamp=datetime.now().isoformat(),
            config_snapshot=config_overrides,
            results=results,
            avg_execution_time=avg_time,
            avg_memory_peak=avg_mem,
            success_rate=success_rate,
            total_score=total_score
        )

    def generate_pdf_report(self, suite_result: SuiteResult) -> str:
        """
        Generates a PDF report for the test suite.
        Returns the path to the generated file.
        """
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Raport Wydajności Strategii", ln=True, align="C")
        
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 10, f"Data: {suite_result.timestamp}", ln=True, align="R")
        pdf.ln(10)
        
        # Configuration Section
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "1. Konfiguracja Testowa", ln=True)
        pdf.set_font("Courier", "", 10)
        config_str = json.dumps(suite_result.config_snapshot, indent=2)
        pdf.multi_cell(0, 5, config_str)
        pdf.ln(5)
        
        # Summary Stats
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "2. Podsumowanie Wyników (20 testów)", ln=True)
        pdf.set_font("Arial", "", 10)
        
        pdf.cell(100, 8, f"Średni czas wykonania: {suite_result.avg_execution_time:.3f} ms", ln=True)
        pdf.cell(100, 8, f"Średnie zużycie pamięci: {suite_result.avg_memory_peak:.2f} KB", ln=True)
        pdf.cell(100, 8, f"Wskaźnik sukcesu: {suite_result.success_rate:.1f}%", ln=True)
        pdf.cell(100, 8, f"Całkowity wynik (Score): {suite_result.total_score:.2f}", ln=True)
        pdf.ln(5)
        
        # Detailed Table
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "3. Szczegóły Iteracji", ln=True)
        
        # Table Header
        pdf.set_font("Arial", "B", 9)
        pdf.cell(20, 8, "Iter #", 1)
        pdf.cell(40, 8, "Czas (ms)", 1)
        pdf.cell(40, 8, "Pamiec (KB)", 1)
        pdf.cell(40, 8, "Wynik", 1)
        pdf.cell(30, 8, "Status", 1)
        pdf.ln()
        
        # Table Rows
        pdf.set_font("Arial", "", 9)
        for r in suite_result.results:
            pdf.cell(20, 8, str(r.iteration), 1)
            pdf.cell(40, 8, f"{r.execution_time_ms:.3f}", 1)
            pdf.cell(40, 8, f"{r.memory_peak_kb:.2f}", 1)
            pdf.cell(40, 8, f"{r.score:.2f}", 1)
            status = "OK" if r.success else "FAIL"
            pdf.cell(30, 8, status, 1)
            pdf.ln()
            
        # Recommendation
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "4. Rekomendacja", ln=True)
        pdf.set_font("Arial", "I", 10)
        
        rec_text = "Konfiguracja stabilna."
        if suite_result.success_rate < 50:
            rec_text = "OSTRZEŻENIE: Niska skuteczność. Zalecane zwiększenie progu (Threshold) lub czułości."
        elif suite_result.avg_execution_time > 100:
            rec_text = "OSTRZEŻENIE: Wysoki czas wykonania. Zmniejsz poziom szczegółowości (Detail Level)."
            
        pdf.multi_cell(0, 5, rec_text)
        
        # Save
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = self.reports_dir / filename
        pdf.output(str(filepath))
        
        return str(filepath)

    def _send_email_alert(self, subject: str, body: str) -> None:
        """
        Mocks sending an email alert.
        In production, this would use smtplib or an API like SendGrid.
        """
        logger.warning(f"[EMAIL ALERT] Subject: {subject} | Body: {body}")
        # Placeholder for real implementation
        pass

    def genetic_algorithm_tune(self, iterations: int = 5) -> Dict[str, Any]:
        """
        Runs a simple genetic algorithm to find optimal parameters.
        """
        population_size = 5
        population = []
        
        # Init population
        for _ in range(population_size):
            gene = {
                "algo_sensitivity": random.randint(10, 90),
                "threshold_value": random.randint(10, 90),
                "reaction_time": random.randint(10, 90),
                "detail_level": random.randint(10, 90),
                "criteria_weight": random.randint(10, 90)
            }
            population.append(gene)
            
        best_gene = None
        best_score = -float('inf')
        
        for generation in range(iterations):
            scored_pop = []
            for gene in population:
                res = self.run_test_suite(gene)
                scored_pop.append((res.total_score, gene))
                
                if res.total_score > best_score:
                    best_score = res.total_score
                    best_gene = gene
            
            # Selection (Top 2)
            scored_pop.sort(key=lambda x: x[0], reverse=True)
            parents = [x[1] for x in scored_pop[:2]]
            
            # Crossover & Mutation
            new_pop = list(parents) # Elitism
            while len(new_pop) < population_size:
                p1, p2 = parents[0], parents[1]
                child = {}
                for k in p1.keys():
                    # Crossover
                    child[k] = p1[k] if random.random() > 0.5 else p2[k]
                    # Mutation (10% chance)
                    if random.random() < 0.1:
                        child[k] = max(0, min(100, child[k] + random.randint(-10, 10)))
                new_pop.append(child)
            
            population = new_pop
            
        return best_gene

if __name__ == "__main__":
    # Test run
    cfg = Config.from_env()
    opt = OptimizationEngine(cfg)
    
    # Run single suite
    res = opt.run_test_suite({
        "algo_sensitivity": 60,
        "threshold_value": 40
    })
    print(f"Single Run Score: {res.total_score}")
    
    # PDF
    path = opt.generate_pdf_report(res)
    print(f"Report saved: {path}")
    
    # GA
    best = opt.genetic_algorithm_tune(iterations=3)
    print(f"Best Config found: {best}")
