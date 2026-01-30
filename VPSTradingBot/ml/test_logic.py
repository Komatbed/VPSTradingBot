
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from ml.logic import TradeClassifier

def test_ml_logic():
    print("=== Testing ML Advisor Logic (7-Layer Architecture) ===\n")
    
    classifier = TradeClassifier(model_path="ml/model.pkl") # It will fallback to heuristics if no model
    
    test_cases = [
        {
            "name": "Perfect Setup (A+)",
            "features": {
                "rr": 3.0,
                "confidence": 80.0,
                "expectancy_r": 0.7,
                "volatility_percentile": 0.5,
                "htf_bias": 1,
                "direction_sign": 1,
                "news_proximity": 120,
                "regime": "trend"
            },
            "expected_verdict": ["A+", "B"] # Should be high
        },
        {
            "name": "News Blackout (Skip)",
            "features": {
                "rr": 2.0,
                "confidence": 70.0,
                "news_proximity": 15
            },
            "expected_verdict": ["SKIP"]
        },
        {
            "name": "Safety Violation (R:R < 1)",
            "features": {
                "rr": 0.8,
                "confidence": 90.0,
                "news_proximity": 100
            },
            "expected_verdict": ["SKIP"]
        },
        {
            "name": "Liquidity Trap (Dead Market)",
            "features": {
                "rr": 2.0,
                "confidence": 60.0,
                "volatility_percentile": 0.05, # < 0.1
                "news_proximity": 100
            },
            "expected_verdict": ["C", "SKIP"] # Should be penalized heavily
        },
        {
            "name": "High Volatility (Adjustment)",
            "features": {
                "rr": 2.0,
                "confidence": 70.0,
                "volatility_percentile": 0.95, # > 0.9
                "news_proximity": 100
            },
            "expected_check": lambda res: res["parameter_adjustments"].get("min_rr") == 2.5
        }
    ]
    
    for case in test_cases:
        print(f"Testing: {case['name']}...")
        result = classifier.predict(case['features'])
        
        print(f"  -> Score: {result['ml_score']:.1f}")
        print(f"  -> Verdict: {result['verdict']}")
        print(f"  -> Reason: {result['reason']}")
        print(f"  -> Adjustments: {result['parameter_adjustments']}")
        
        passed = True
        if "expected_verdict" in case:
            if result["verdict"] not in case["expected_verdict"]:
                passed = False
                print(f"  [FAIL] Expected {case['expected_verdict']}, got {result['verdict']}")
                
        if "expected_check" in case:
            if not case["expected_check"](result):
                passed = False
                print(f"  [FAIL] Custom check failed")
                
        if passed:
            print("  [PASS]")
        print("-" * 40)

if __name__ == "__main__":
    test_ml_logic()
