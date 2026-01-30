from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from ml.logic import TradeClassifier
import logging
import uvicorn

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ml_server")

app = FastAPI(
    title="Trading ML Advisor API",
    description="Advanced Event-Driven Trading Assistant Module",
    version="2.0.0"
)

classifier = TradeClassifier(model_path="ml/model.pkl")

# --- Feature Engineering Models ---

class MarketContext(BaseModel):
    regime: str = Field(..., description="Market regime: trending/ranging/unknown")
    volatility_percentile: float = Field(..., ge=0.0, le=1.0, description="ATR percentile rank (0-1)")
    htf_bias: int = Field(default=0, description="Higher Timeframe Bias: 1 (Bull), -1 (Bear), 0 (Neutral)")
    news_proximity: int = Field(default=999, description="Minutes to next High Impact news")
    session: Optional[str] = Field(default=None, description="Current market session (e.g., 'london')")

class SetupFeatures(BaseModel):
    strategy_type: str
    direction_sign: int = Field(..., description="1 for Long, -1 for Short")
    rr: float = Field(..., description="Risk to Reward Ratio")
    confidence: float = Field(..., description="Base Strategy Confidence (0-100)")
    expectancy_r: float = Field(default=0.0, description="Historical R-expectancy for this strategy/instrument")
    sl_distance_atr: Optional[float] = Field(default=None, description="Stop Loss distance in ATR multiples")

class EvaluationPayload(BaseModel):
    instrument: str
    timeframe: str
    strategy_id: str
    features: Dict[str, Any] 
    # Note: We use flexible Dict for 'features' in the payload to allow easy expansion 
    # without breaking strict validation, but logic will look for keys defined above.

class EvaluationResponse(BaseModel):
    ml_score: float
    verdict: str
    blacklisted: bool
    reason: str
    parameter_adjustments: Dict[str, Any]

@app.get("/health")
def health():
    return {
        "status": "ok", 
        "model_loaded": classifier.model is not None,
        "mode": "ML + Heuristics" if classifier.model else "Expert Heuristics Only"
    }

@app.post("/reload")
def reload_model():
    """
    Forces the classifier to reload the model from disk.
    """
    logger.info("Reloading model request received...")
    success = classifier.load_model()
    mode = "ML + Heuristics" if classifier.model else "Expert Heuristics Only"
    
    if success:
        return {"status": "success", "message": "Model reloaded successfully", "mode": mode}
    else:
        return {"status": "warning", "message": "Model load failed or file missing (using heuristics)", "mode": mode}

@app.post("/evaluate_setup", response_model=EvaluationResponse)
def evaluate_setup(payload: EvaluationPayload):
    """
    Evaluates a trading setup using the 7-Layer ML Architecture.
    """
    logger.info(f"Evaluating {payload.instrument} [{payload.timeframe}] Strategy: {payload.strategy_id}")
    
    # Flatten/Normalize features if needed
    # (The logic class expects a flat dictionary)
    features = payload.features.copy()
    features["instrument"] = payload.instrument
    features["strategy_id"] = payload.strategy_id
    
    result = classifier.predict(features)
    
    log_level = logging.INFO if not result["blacklisted"] else logging.WARNING
    logger.log(log_level, f"Result: {result['verdict']} ({result['ml_score']}) - {result['reason']}")
    
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
