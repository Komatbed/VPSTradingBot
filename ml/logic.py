from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import joblib
import pandas as pd
from pathlib import Path
import logging

# --- Data Models for Internal Logic ---

@dataclass
class EvaluationResult:
    score: float
    verdict: str  # "A+", "B", "C" (Skip)
    is_blacklisted: bool
    reasons: List[str]
    adjustments: Dict[str, Any]

class TradeClassifier:
    def __init__(self, model_path: str = "model.pkl"):
        self.model_path = Path(model_path)
        self.model = None
        self.logger = logging.getLogger("ml_logic")
        self.load_model()

    def load_model(self) -> bool:
        if self.model_path.exists():
            try:
                self.model = joblib.load(self.model_path)
                self.logger.info(f"Loaded ML model from {self.model_path}")
                return True
            except Exception as e:
                self.logger.error(f"Failed to load model: {e}")
                self.model = None
                return False
        else:
            self.logger.warning(f"No model found at {self.model_path}. Running in Heuristic Mode.")
            self.model = None
            return False

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main pipeline executing all layers of the ML Advisor architecture.
        """
        reasons = []
        adjustments = {}
        
        # --- Layer 1: Market Playability (The "Can we play?" check) ---
        # Checks for external blocking factors like News or Holidays.
        # (Assuming news_proximity is passed in features, or 999 if unknown)
        news_dist = features.get("news_proximity", 999)
        if news_dist < 30:
            return self._build_response(0, "SKIP", True, [f"News Blackout: High Impact event in {news_dist}min"], adjustments)

        # --- Layer 2: Safety & Risk (The "Must Haves") ---
        rr = features.get("rr", 0.0)
        confidence = features.get("confidence", 0.0)
        
        if rr < 1.0:
            return self._build_response(0, "SKIP", True, ["Safety: R:R < 1.0 is mathematically ruinous"], adjustments)
        
        if confidence < 50.0:
            return self._build_response(0, "SKIP", True, ["Safety: Confidence < 50%"], adjustments)

        # --- Layer 3: AI Prediction (The "Brain") ---
        ai_score_component = 0.0
        if self.model:
            try:
                # Prepare features DataFrame matching training data
                df_input = pd.DataFrame([features])
                
                # Ensure all required columns exist (fill missing with defaults/None)
                required_cols = [
                    'direction_sign', 'rr', 'confidence', 'expectancy_r', 
                    'sl_distance_atr', 'volatility_percentile', 'htf_bias', 
                    'news_proximity', 'session', 'strategy_type', 'regime'
                ]
                
                for col in required_cols:
                    if col not in df_input.columns:
                        df_input[col] = None # Transformer handles missing/None
                
                # Predict probability of class 1 (Profitable)
                prob = self.model.predict_proba(df_input)[0][1]
                ai_score_component = prob * 100.0
                reasons.append(f"AI Model Confidence: {ai_score_component:.1f}%")
                
            except Exception as e:
                self.logger.error(f"AI Prediction failed: {e}")
                reasons.append("AI Model Error (Skipped)")

        # --- Layer 4: Rule / Heuristic Layer (The "Pro Wisdom") ---
        # Fallback or Augmentation if Model is present
        heuristic_score = 0.0
        
        # 4.1 Expectancy
        exp_r = features.get("expectancy_r", 0.0)
        if exp_r > 0.6:
            heuristic_score += 15
            reasons.append("High Expectancy (+15)")
        elif exp_r < 0.3:
            heuristic_score -= 10
            reasons.append("Low Expectancy (-10)")

        # 4.2 Volatility Context
        vol_pct = features.get("volatility_percentile", 0.5)
        if 0.2 <= vol_pct <= 0.8:
            heuristic_score += 10
            reasons.append("Healthy Volatility (+10)")
        elif vol_pct < 0.1:
            heuristic_score -= 15
            reasons.append("Dead Market/Liquidity Trap (-15)")
        elif vol_pct > 0.9:
            heuristic_score -= 5
            reasons.append("Extreme Volatility Risk (-5)")

        # 4.3 Trend Alignment
        htf_bias = features.get("htf_bias", 0) # 1=Bull, -1=Bear
        strategy_dir = features.get("direction_sign", 0) # 1=Long, -1=Short
        if htf_bias != 0 and strategy_dir != 0:
            if htf_bias == strategy_dir:
                heuristic_score += 15
                reasons.append("HTF Trend Aligned (+15)")
            else:
                heuristic_score -= 10
                reasons.append("Counter-Trend HTF (-10)")

        # --- Layer 5: Feedback & Adaptation (The "Coach") ---
        # Dynamic parameter adjustment suggestions
        
        # If volatility is extreme, demand higher R:R
        if vol_pct > 0.85:
            adjustments["min_rr"] = 2.5
            reasons.append("High Volatility -> Adjusted Min RR to 2.5")
            
        # If market is ranging (low ADX/trend), demand higher confidence for breakout strategies
        regime = features.get("regime", "unknown")
        if regime == "ranging":
            adjustments["min_confidence"] = 80.0
            reasons.append("Ranging Market -> Stricter Confidence Required")

        # --- Combine Scores ---
        # If model exists, weight it 70% / 30% rules. If not, 100% rules + Base Confidence.
        base_score = confidence
        
        if self.model:
            final_score = (ai_score_component * 0.6) + (heuristic_score * 0.4)
        else:
            final_score = base_score + heuristic_score

        # Clamp 0-100
        final_score = min(max(final_score, 0.0), 100.0)

        # --- Layer 6: Classification (The "Grade") ---
        if final_score >= 85:
            verdict = "A+"
        elif final_score >= 60:
            verdict = "B"
        else:
            verdict = "C"
            reasons.append("Score below threshold (<60)")

        # Auto-blacklist C-grade setups
        is_blacklisted = (verdict == "C")

        # --- Layer 7: Explainability (The "Why") ---
        # Formatting reasons for user
        explanation = f"Verdict {verdict} ({final_score:.1f}). " + "; ".join(reasons)

        return self._build_response(final_score, verdict, is_blacklisted, explanation, adjustments)

    def _build_response(self, score, verdict, blacklisted, reason_or_list, adjustments):
        if isinstance(reason_or_list, list):
            reason_str = "; ".join(reason_or_list)
        else:
            reason_str = reason_or_list
            
        return {
            "ml_score": float(score),
            "verdict": verdict,
            "blacklisted": blacklisted,
            "reason": reason_str,
            "parameter_adjustments": adjustments
        }
