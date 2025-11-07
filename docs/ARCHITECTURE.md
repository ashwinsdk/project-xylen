# System Architecture

## Overview

Project Xylen is a distributed trading system built on microservices architecture with ensemble machine learning for decision-making.

## Core Components

### 1. Coordinator Service

**Purpose**: Orchestrates trading decisions using ensemble of ML models

**Responsibilities**:
- Collect market data from Binance Futures API
- Query model servers for predictions
- Aggregate predictions using weighted voting or Bayesian methods
- Execute risk management checks
- Place and manage orders
- Broadcast system status via WebSocket
- Log trades and system events

**Key Modules**:
- `coordinator.py`: Main orchestration loop
- `ensemble.py`: Model aggregation logic
- `risk_manager.py`: Position sizing and safety limits
- `binance_client.py`: Exchange API wrapper
- `market_data.py`: Feature engineering pipeline
- `data_logger.py`: SQLite persistence layer

**Decision Cycle** (60s default):
1. Fetch market data (OHLCV + indicators)
2. Query all active model servers
3. Aggregate predictions with confidence weighting
4. Apply risk management validation
5. Execute approved trades
6. Update performance metrics

### 2. Model Servers

**Purpose**: Provide ML inference as HTTP microservices

**Architecture**:
- FastAPI REST API
- LightGBM models (ONNX optimized)
- Independent scaling and deployment
- Health monitoring and metrics

**Endpoints**:
- `POST /predict`: Returns action (long/short/hold) with confidence
- `GET /health`: System metrics (CPU, memory, uptime, model status)
- `POST /feedback`: Receive trade outcomes for retraining
- `POST /retrain`: Trigger model retraining

**Features**:
- Model versioning
- Continuous learning pipeline
- Data collection for incremental training
- Performance monitoring

### 3. Dashboard

**Technology**: React 18 + Vite + Tailwind CSS

**Features**:
- Real-time WebSocket updates (60s intervals)
- Model health cards with detailed metrics
- Live trade list with P&L tracking
- Performance charts and statistics
- System status indicators

**Components**:
- `ModelHealthCard`: Display model metrics (confidence, latency, CPU, memory)
- `SystemStatus`: Coordinator health and market data
- `TradesList`: Recent trades with outcomes
- `PerformanceChart`: P&L over time

### 4. Data Pipeline

**Market Data Collection**:
- Binance Futures REST API
- Multi-timeframe candles (5m, 15m, 1h)
- 29+ technical indicators (RSI, MACD, Bollinger Bands, ATR, etc.)
- Volume analysis and price momentum

**Feature Engineering**:
- Normalized price movements
- Rate of change calculations
- Multi-timeframe alignment
- Candle pattern recognition

**Storage**:
- SQLite for trades and system events
- Parquet files for feature store (compressed)
- CSV exports for analysis

## Communication Protocols

### REST APIs

**Coordinator → Model Servers**:
```json
POST /predict
{
  "symbol": "BTCUSDT",
  "timeframe": "5m",
  "candles": [...],
  "indicators": {...}
}

Response:
{
  "action": "long",
  "confidence": 0.82,
  "stop_loss": 101500,
  "take_profit": 102500
}
```

**Coordinator → Binance**:
- Account balance queries
- Order placement (LIMIT/MARKET)
- Position management
- Order status polling

### WebSocket

**Coordinator → Dashboard**:
```json
{
  "type": "status_update",
  "timestamp": "2025-11-07T...",
  "coordinator": {...},
  "models": [...],
  "market": {...},
  "decision": {...},
  "performance": {...}
}
```

Update frequency: 60 seconds

## Ensemble Decision Logic

### 1. Weighted Voting

Each model vote weighted by:
- Base weight (configured per model)
- Historical accuracy (success rate)
- Response time (penalize slow models)

```python
vote_weight = base_weight * (success_rate ** decay_factor)
final_action = argmax(sum(votes * weights))
final_confidence = max_votes / total_weight
```

### 2. Bayesian Weighted (Default)

Advanced aggregation using:
- Prior model performance
- Prediction uncertainty
- Inter-model agreement

Confidence threshold: 0.70 (configurable)

### 3. Risk Validation

Before execution, check:
- Position size within limits
- Sufficient account balance
- Daily loss limits not exceeded
- Circuit breaker not active
- Minimum confidence threshold met

## Deployment Architecture

### Docker Compose Stack

```
┌─────────────────────┐
│   Dashboard (3000)  │
└──────────┬──────────┘
           │ WebSocket
┌──────────▼──────────┐
│  Coordinator (8765) │◄──────┐
└──────────┬──────────┘       │
           │ HTTP              │ Health Checks
     ┌─────┴─────┬────────┬───┴───┐
     │           │        │       │
┌────▼────┐ ┌───▼────┐ ┌─▼─────┐ ┌▼──────┐
│ Model 1 │ │ Model 2│ │Model 3│ │Model 4│
│  :8001  │ │  :8002 │ │ :8003 │ │ :8004 │
└─────────┘ └────────┘ └───────┘ └───────┘
```

All services in isolated Docker network with persistent volumes for data.

## Monitoring Stack

- Prometheus: Metrics collection (9090)
- Grafana: Visualization dashboards (3001)
- Coordinator exports: trades, decisions, model health
- Model servers export: predictions, latency, resource usage

## Safety Mechanisms

### Circuit Breakers

Automatically halt trading if:
- 5 consecutive losses
- Daily loss exceeds 10%
- Total drawdown exceeds 20%

Cooldown: 1 hour before resuming

### Position Limits

- Maximum 1 open position
- Maximum 20 trades per day
- Minimum 5 minutes between trades
- Leverage capped at configured limit

### Risk Checks

Every trade validated for:
- Sufficient margin
- Position size calculations
- Stop loss placement
- Take profit targets
- Balance buffer (10% reserved)

## Configuration Management

Single `config.yaml` controls:
- Trading parameters (leverage, position sizing)
- Ensemble settings (method, thresholds)
- Risk limits (stop loss, circuit breakers)
- Data collection (indicators, timeframes)
- API credentials (via environment variables)

Hot-reloadable for certain parameters.

## Logging and Observability

### Log Levels

- DEBUG: Market data, feature calculations
- INFO: Decisions, trades, health checks
- WARNING: Risk warnings, model offline
- ERROR: Trade failures, API errors

### Structured Logging

JSON format with:
- Timestamp
- Component name
- Log level
- Message
- Context (trade ID, model name, etc.)

### Event Tracking

SQLite database records:
- All trades with entry/exit details
- Ensemble decisions with model breakdown
- System events (startup, shutdown, errors)
- Performance metrics snapshots

## Scalability Considerations

**Horizontal Scaling**:
- Add more model servers to ensemble
- Distribute models across multiple hosts
- Load balance via Docker Swarm or Kubernetes

**Performance Optimization**:
- ONNX model inference (5-15ms latency)
- Async I/O throughout stack
- Connection pooling for API calls
- Efficient data structures (NumPy arrays)

**Resource Requirements**:
- Coordinator: 512MB RAM, 1 CPU core
- Model Server: 256MB RAM, 0.5 CPU core each
- Dashboard: Negligible (served as static files in production)
