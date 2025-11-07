from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import uvicorn
import logging
import os
import psutil
import time
import numpy as np
from datetime import datetime

from model_loader_optimized import OptimizedModelLoader as ModelLoader
from retrain_optimized import OptimizedRetrainManager as RetrainManager
from continuous_trainer import ContinuousTrainer

try:
    from prometheus_client import Counter, Gauge, Histogram, make_asgi_app, REGISTRY, CollectorRegistry
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("prometheus_client not installed, metrics disabled")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Xylen Model Server",
    version="2.0.0",
    description="Production-grade trading model inference server with LightGBM and ONNX support"
)

model_loader = None
retrain_manager = None
continuous_trainer = None
start_time = time.time()

# Prometheus metrics - use try/except to handle re-registration on reload
if PROMETHEUS_AVAILABLE:
    try:
        metrics = {
            'predictions_total': Counter('model_predictions_total', 'Total predictions', ['action']),
            'prediction_latency': Histogram('model_prediction_latency_seconds', 'Prediction latency'),
            'prediction_confidence': Histogram('model_prediction_confidence', 'Prediction confidence', buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]),
            'retrains_total': Counter('model_retrains_total', 'Total retrains'),
            'training_samples': Gauge('model_training_samples', 'Training samples collected'),
            'model_score': Gauge('model_score', 'Current model performance score'),
        }
    except ValueError as e:
        # Metrics already registered, retrieve existing ones
        logger.warning(f"Metrics already registered, reusing existing: {e}")
        from prometheus_client import REGISTRY
        metrics = {
            'predictions_total': REGISTRY._names_to_collectors.get('model_predictions_total'),
            'prediction_latency': REGISTRY._names_to_collectors.get('model_prediction_latency_seconds'),
            'prediction_confidence': REGISTRY._names_to_collectors.get('model_prediction_confidence'),
            'retrains_total': REGISTRY._names_to_collectors.get('model_retrains_total'),
            'training_samples': REGISTRY._names_to_collectors.get('model_training_samples'),
            'model_score': REGISTRY._names_to_collectors.get('model_score'),
        }
    
    # Add Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    logger.info("Prometheus metrics enabled at /metrics")
else:
    metrics = None


class PredictionRequest(BaseModel):
    """Request for model prediction with features"""
    symbol: str
    timeframe: str
    candles: List[Dict]
    indicators: Dict
    meta: Optional[Dict] = {}


class PredictionResponse(BaseModel):
    """Model prediction response"""
    model_name: str
    action: str  # long, short, hold
    confidence: float
    probability: Optional[float] = None
    expected_return: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    raw_score: float
    latency_ms: float


class RetrainRequest(BaseModel):
    """Request to add training sample"""
    snapshot: Optional[Dict] = None
    decision: Dict
    outcome: Dict


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    uptime_seconds: float
    memory_usage_mb: float
    cpu_percent: float
    model_loaded: bool
    model_type: Optional[str] = None
    model_version: Optional[str] = None
    training_samples: int
    continuous_learning: bool = False
    training: bool = False
    data_collector_active: bool = False

@app.on_event("startup")
async def startup_event():
    global model_loader, retrain_manager, continuous_trainer
    
    logger.info("Starting model server...")
    
    model_path = os.getenv('MODEL_PATH', './models/model.txt')
    model_type = os.getenv('MODEL_TYPE', 'lightgbm')
    
    model_loader = ModelLoader(model_path, model_type)
    
    try:
        model_loader.load()
        logger.info(f"Model loaded successfully: {model_path}")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        logger.warning("Server will run with placeholder model")
    
    retrain_manager = RetrainManager(model_loader)
    
    # Initialize continuous trainer (runs in background)
    continuous_trainer = ContinuousTrainer(model_loader)
    
    logger.info("Model server ready with continuous training support")


@app.get("/health")
async def health_check() -> HealthResponse:
    """Health check with detailed system metrics"""
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    cpu_percent = process.cpu_percent(interval=0.1)
    uptime = time.time() - start_time
    
    training_samples_count = 0
    if retrain_manager and hasattr(retrain_manager, 'sample_count'):
        training_samples_count = retrain_manager.sample_count
    
    # Check continuous learning status
    continuous_learning_active = False
    training_active = False
    if continuous_trainer:
        continuous_learning_active = getattr(continuous_trainer, 'is_running', False)
        training_active = getattr(continuous_trainer, 'is_training', False)
    
    # Check data collector status (placeholder - would need actual data collector instance)
    data_collector_active = False  # TODO: Integrate with actual data collector
    
    return HealthResponse(
        status="healthy",
        uptime_seconds=uptime,
        memory_usage_mb=memory_mb,
        cpu_percent=cpu_percent,
        model_loaded=model_loader.is_loaded() if model_loader else False,
        model_type=model_loader.model_type if model_loader else None,
        model_version=os.getenv('MODEL_VERSION', '1.0'),
        training_samples=training_samples_count,
        continuous_learning=continuous_learning_active,
        training=training_active,
        data_collector_active=data_collector_active
    )


@app.post("/predict")
async def predict(request: PredictionRequest) -> PredictionResponse:
    """
    Make prediction from market data
    
    Extracts features from candles and indicators, runs inference,
    and returns trading signal with confidence and stop loss/take profit levels.
    """
    start_time = time.time()
    
    try:
        if not model_loader or not model_loader.is_loaded():
            logger.warning("Model not loaded, using placeholder prediction")
            response = _placeholder_prediction(request)
        else:
            # Extract features
            features = _extract_features(request.candles, request.indicators)
            
            # Make prediction (returns dict)
            prediction = model_loader.predict(
                candles=request.candles,
                indicators=request.indicators,
                meta=request.meta
            )
            
            # Calculate stop loss and take profit
            current_price = request.candles[-1]['close'] if request.candles else 0
            stop_loss, take_profit = _calculate_sl_tp(
                action=prediction['action'],
                current_price=current_price,
                confidence=prediction['confidence']
            )
            
            response = PredictionResponse(
                model_name=os.getenv('MODEL_NAME', 'lightgbm_model'),
                action=prediction['action'],
                confidence=prediction['confidence'],
                probability=prediction.get('probability'),
                expected_return=prediction.get('expected_return'),
                stop_loss=stop_loss,
                take_profit=take_profit,
                raw_score=prediction['raw_score'],
                latency_ms=(time.time() - start_time) * 1000
            )
        
        # Update metrics
        if metrics:
            metrics['predictions_total'].labels(action=response.action).inc()
            metrics['prediction_latency'].observe(time.time() - start_time)
            metrics['prediction_confidence'].observe(response.confidence)
        
        logger.info(f"Prediction: {response.action} (conf={response.confidence:.3f}, "
                   f"latency={response.latency_ms:.1f}ms)")
        
        return response
        
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/retrain")
async def retrain(request: RetrainRequest):
    """
    Add training sample for future model retraining
    
    Collects outcome data for periodic model updates
    """
    try:
        if not retrain_manager:
            raise HTTPException(status_code=503, detail="Retrain manager not initialized")
        
        retrain_manager.add_training_sample(
            decision=request.decision,
            outcome=request.outcome,
            snapshot=request.snapshot
        )
        
        # Update metrics
        if metrics and hasattr(retrain_manager, 'sample_count'):
            metrics['training_samples'].set(retrain_manager.sample_count)
        
        logger.info(f"Training sample added: outcome_pnl={request.outcome.get('pnl', 0):.2f}, "
                   f"action={request.decision.get('action')}")
        
        return {
            "status": "success",
            "message": "Training sample recorded",
            "samples_collected": getattr(retrain_manager, 'sample_count', 0)
        }
        
    except Exception as e:
        logger.error(f"Retrain error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/retrain/trigger")
async def trigger_retrain():
    """
    Manually trigger model retraining
    
    Retrains model on collected samples and reloads if successful
    """
    try:
        if not retrain_manager:
            raise HTTPException(status_code=503, detail="Retrain manager not initialized")
        
        logger.info("Manual retrain triggered")
        result = await retrain_manager.retrain()
        
        # Update metrics
        if metrics:
            metrics['retrains_total'].inc()
            if result.get('success'):
                metrics['model_score'].set(result.get('score', 0))
        
        return result
        
    except Exception as e:
        logger.error(f"Retrain trigger error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_status():
    """Get detailed model server status"""
    return {
        "server": "Xylen Model Server",
        "version": "2.0.0",
        "model_name": os.getenv('MODEL_NAME', 'lightgbm_model'),
        "model_type": model_loader.model_type if model_loader else None,
        "model_loaded": model_loader.is_loaded() if model_loader else False,
        "uptime_seconds": time.time() - start_time,
        "endpoints": {
            "/health": "Health check",
            "/predict": "Make prediction",
            "/retrain": "Add training sample",
            "/retrain/trigger": "Trigger model retraining",
            "/status": "Get server status",
            "/metrics": "Prometheus metrics" if PROMETHEUS_AVAILABLE else "Not available"
        }
    }


def _extract_features(candles: List[Dict], indicators: Dict) -> np.ndarray:
    """
    Extract feature vector from candles and indicators
    
    Features:
    - Price momentum (multiple periods)
    - Volume ratios
    - Technical indicators (RSI, MACD, BBands, ATR, etc.)
    - Candle patterns
    """
    if not candles:
        return np.zeros(50)  # Placeholder feature vector
    
    features = []
    
    # Extract recent closes
    closes = np.array([c['close'] for c in candles[-100:]])
    volumes = np.array([c['volume'] for c in candles[-100:]])
    
    # Price momentum features
    if len(closes) >= 5:
        features.append((closes[-1] - closes[-5]) / closes[-5])  # 5-period momentum
    else:
        features.append(0.0)
    
    if len(closes) >= 10:
        features.append((closes[-1] - closes[-10]) / closes[-10])  # 10-period momentum
    else:
        features.append(0.0)
    
    if len(closes) >= 20:
        features.append((closes[-1] - closes[-20]) / closes[-20])  # 20-period momentum
    else:
        features.append(0.0)
    
    # Volume features
    if len(volumes) >= 20:
        features.append(volumes[-1] / np.mean(volumes[-20:]))  # Volume ratio
    else:
        features.append(1.0)
    
    # Technical indicators from pre-computed dict
    features.append(indicators.get('rsi', 50) / 100.0)  # Normalize RSI
    features.append(indicators.get('rsi_14', 50) / 100.0)
    features.append(indicators.get('rsi_28', 50) / 100.0)
    
    # MACD features
    features.append(indicators.get('macd', 0))
    features.append(indicators.get('macd_signal', 0))
    features.append(indicators.get('macd_hist', 0))
    
    # Bollinger Bands
    current_price = closes[-1] if len(closes) > 0 else 0
    bb_upper = indicators.get('bb_upper', current_price)
    bb_lower = indicators.get('bb_lower', current_price)
    bb_width = indicators.get('bb_width', 0)
    
    features.append((current_price - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5)
    features.append(bb_width)
    
    # ATR and volatility
    features.append(indicators.get('atr_percent', 0))
    
    # Volume indicators
    features.append(indicators.get('obv', 0) / 1e6)  # Scale OBV
    features.append(indicators.get('volume_momentum', 0))
    
    # Trend strength
    features.append(indicators.get('adx', 0) / 100.0)
    
    # Candle patterns
    features.append(indicators.get('candle_body_ratio', 0))
    features.append(indicators.get('candle_upper_shadow', 0))
    features.append(indicators.get('candle_lower_shadow', 0))
    
    # EMA ratios
    ema_9 = indicators.get('ema_9', current_price)
    ema_20 = indicators.get('ema_20', current_price)
    ema_50 = indicators.get('ema_50', current_price)
    
    features.append((current_price - ema_9) / ema_9 if ema_9 > 0 else 0)
    features.append((current_price - ema_20) / ema_20 if ema_20 > 0 else 0)
    features.append((current_price - ema_50) / ema_50 if ema_50 > 0 else 0)
    features.append((ema_9 - ema_20) / ema_20 if ema_20 > 0 else 0)
    
    return np.array(features, dtype=np.float32)


def _calculate_sl_tp(action: str, current_price: float, confidence: float) -> tuple:
    """
    Calculate stop loss and take profit based on action and confidence
    
    Higher confidence = tighter stops, wider targets
    """
    if action == 'hold':
        return None, None
    
    # Base risk (ATR-based or percentage)
    base_risk_percent = 0.02  # 2% base risk
    
    # Adjust based on confidence
    risk_multiplier = 1.0 + (1.0 - confidence)  # Lower confidence = wider stops
    stop_distance_percent = base_risk_percent * risk_multiplier
    
    # Risk-reward ratio based on confidence
    reward_ratio = 1.5 + confidence  # 1.5 to 2.5 RR
    tp_distance_percent = stop_distance_percent * reward_ratio
    
    if action == 'long':
        stop_loss = current_price * (1 - stop_distance_percent)
        take_profit = current_price * (1 + tp_distance_percent)
    else:  # short
        stop_loss = current_price * (1 + stop_distance_percent)
        take_profit = current_price * (1 - tp_distance_percent)
    
    return stop_loss, take_profit


def _placeholder_prediction(request: PredictionRequest) -> PredictionResponse:
    """
    Placeholder prediction when model not loaded
    
    Uses simple technical rules for demonstration
    """
    logger.debug("Generating placeholder prediction")
    
    model_name = os.getenv('MODEL_NAME', 'placeholder_model')
    start_time = time.time()
    
    if not request.candles:
        return PredictionResponse(
            model_name=model_name,
            action="hold",
            confidence=0.5,
            stop_loss=None,
            take_profit=None,
            raw_score=0.0,
            latency_ms=(time.time() - start_time) * 1000
        )
    
    # Simple trend-following logic
    recent_candles = request.candles[-10:]
    closes = [c['close'] for c in recent_candles]
    
    trend = (closes[-1] - closes[0]) / closes[0]
    rsi = request.indicators.get('rsi', 50)
    current_price = closes[-1]
    
    if trend > 0.01 and rsi < 70:
        action = "long"
        confidence = min(0.7, 0.5 + abs(trend) * 10)
        stop_loss = current_price * 0.98
        take_profit = current_price * 1.05
    elif trend < -0.01 and rsi > 30:
        action = "short"
        confidence = min(0.7, 0.5 + abs(trend) * 10)
        stop_loss = current_price * 1.02
        take_profit = current_price * 0.95
    else:
        action = "hold"
        confidence = 0.6
        stop_loss = None
        take_profit = None
    
    return PredictionResponse(
        model_name=model_name,
        action=action,
        confidence=confidence,
        stop_loss=stop_loss,
        take_profit=take_profit,
        raw_score=trend,
        latency_ms=(time.time() - start_time) * 1000
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
