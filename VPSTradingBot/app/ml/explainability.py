from typing import Dict, List, Any

class ExplainabilityEngine:
    """
    Provides heuristic explanations for ML model scores.
    Since we use a RandomForest, we can look at feature importance globally, 
    but for local explanation (per signal) we compare input values to 'ideal' ranges.
    """
    
    def explain_score(self, ml_score: float, features: Dict[str, float]) -> List[str]:
        """
        Returns a list of human-readable strings explaining the score.
        e.g. ["+ RSI Divergence detected", "- High Volatility penalty"]
        """
        explanations = []
        
        # Heuristic rules mapping features to explanations
        
        # 1. Technical Alignment
        rsi = features.get("rsi", 50)
        if ml_score > 70:
            if 40 < rsi < 60:
                explanations.append("✅ RSI w strefie momentum")
            elif rsi < 30 or rsi > 70:
                explanations.append("⚠️ Ryzyko odwrócenia (RSI skrajne)")
                
        # 2. Volatility
        atr_percent = features.get("atr_percent", 0.5)
        if atr_percent < 0.2:
            explanations.append("✅ Niska zmienność (bezpiecznie)")
        elif atr_percent > 1.0:
            explanations.append("⚠️ Wysoka zmienność (szeroki SL)")
            
        # 3. Market Regime (if passed in features)
        regime = features.get("regime_val", 0) # e.g. 1=Trending
        if regime == 1:
            explanations.append("🌊 Zgodność z trendem")
            
        # Default if empty
        if not explanations:
            if ml_score > 80:
                explanations.append("✨ Silny sygnał techniczny")
            elif ml_score < 50:
                explanations.append("❄️ Słabe potwierdzenie w historii")
                
        return explanations
