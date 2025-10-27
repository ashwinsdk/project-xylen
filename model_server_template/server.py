from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import uvicorn
import logging
import os
import psutil
import time
from datetime import datetime

from model_loader import ModelLoader
from retrain import RetrainManager


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Trading Model Server", version="1.0.0")

model_loader = None
retrain_manager = None
start_time = time.time()


class PredictionRequest(BaseModel):
    symbol: str
    timeframe: str
    candles: List[Dict]
    indicators: Dict
    meta: Dict


class PredictionResponse(BaseModel):
    action: str
    confidence: float
    stop: Optional[float] = None
    take_profit: Optional[float] = None
    raw_score: float


class RetrainRequest(BaseModel):
    snapshot: Optional[Dict] = None
    decision: Dict
    outcome: Dict


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    memory_usage_mb: float
    model_loaded: bool
    model_type: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    global model_loader, retrain_manager
    
    logger.info("Starting model server...")
    
    model_path = os.getenv('MODEL_PATH', './models/model.onnx')
    model_type = os.getenv('MODEL_TYPE', 'onnx')
    
    model_loader = ModelLoader(model_path, model_type)
    
    try:
        model_loader.load()
        logger.info(f"Model loaded successfully: {model_path}")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        logger.warning("Server will run with placeholder model")
    
    retrain_manager = RetrainManager(model_loader)
    
    logger.info("Model server ready")


@app.get("/health")
async def health_check() -> HealthResponse:
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    uptime = time.time() - start_time
    
    return HealthResponse(
        status="healthy",
        uptime_seconds=uptime,
        memory_usage_mb=memory_mb,
        model_loaded=model_loader.is_loaded() if model_loader else False,
        model_type=model_loader.model_type if model_loader else None
    )


@app.post("/predict")
async def predict(request: PredictionRequest) -> PredictionResponse:
    try:
        if not model_loader or not model_loader.is_loaded():
            logger.warning("Model not loaded, using placeholder prediction")
            return _placeholder_prediction(request)
        
        prediction = model_loader.predict(
            candles=request.candles,
            indicators=request.indicators,
            meta=request.meta
        )
        
        return prediction
        
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/retrain")
async def retrain(request: RetrainRequest):
    try:
        if not retrain_manager:
            raise HTTPException(status_code=503, detail="Retrain manager not initialized")
        
        retrain_manager.add_training_sample(
            decision=request.decision,
            outcome=request.outcome,
            snapshot=request.snapshot
        )
        
        logger.info(f"Training sample added: outcome_pnl={request.outcome.get('pnl', 0):.2f}")
        
        return {"status": "success", "message": "Training sample recorded"}
        
    except Exception as e:
        logger.error(f"Retrain error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/retrain/trigger")
async def trigger_retrain():
    try:
        if not retrain_manager:
            raise HTTPException(status_code=503, detail="Retrain manager not initialized")
        
        result = await retrain_manager.retrain()
        
        return result
        
    except Exception as e:
        logger.error(f"Retrain trigger error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _placeholder_prediction(request: PredictionRequest) -> PredictionResponse:
    logger.debug("Generating placeholder prediction")
    
    if not request.candles:
        return PredictionResponse(
            action="hold",
            confidence=0.5,
            stop=None,
            take_profit=None,
            raw_score=0.0
        )
    
    recent_candles = request.candles[-10:]
    closes = [c['close'] for c in recent_candles]
    
    trend = (closes[-1] - closes[0]) / closes[0]
    
    rsi = request.indicators.get('rsi', 50)
    
    if trend > 0.01 and rsi < 70:
        action = "long"
        confidence = min(0.65, 0.5 + abs(trend) * 10)
        current_price = closes[-1]
        stop = current_price * 0.98
        take_profit = current_price * 1.05
    elif trend < -0.01 and rsi > 30:
        action = "short"
        confidence = min(0.65, 0.5 + abs(trend) * 10)
        current_price = closes[-1]
        stop = current_price * 1.02
        take_profit = current_price * 0.95
    else:
        action = "hold"
        confidence = 0.6
        stop = None
        take_profit = None
    
    return PredictionResponse(
        action=action,
        confidence=confidence,
        stop=stop,
        take_profit=take_profit,
        raw_score=trend
    )


if __name__ == "__main__":
    port = int(os.getenv('PORT', '8000'))
    host = os.getenv('HOST', '0.0.0.0')
    
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        log_level="info",
        reload=False
    )
