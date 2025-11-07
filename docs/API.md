# API Reference

## REST APIs

### Model Server API

**Base URL**: `http://localhost:800[1-4]`

#### POST /predict

Make trading prediction from market data.

**Request**:
```json
{
  "symbol": "BTCUSDT",
  "timeframe": "5m",
  "candles": [
    {
      "open": 101700.0,
      "high": 101800.0,
      "low": 101600.0,
      "close": 101750.0,
      "volume": 1000000.0,
      "timestamp": 1699300000
    }
  ],
  "indicators": {
    "rsi": 42.5,
    "macd": 150.0,
    "bb_upper": 102000.0,
    ...
  },
  "meta": {}
}
```

**Response**:
```json
{
  "model_name": "model_1",
  "action": "long",
  "confidence": 0.82,
  "probability": 0.85,
  "expected_return": 0.015,
  "stop_loss": 101500.0,
  "take_profit": 102500.0,
  "raw_score": 0.65,
  "latency_ms": 8.5
}
```

**Fields**:
- `action`: "long", "short", or "hold"
- `confidence`: 0.0-1.0 prediction confidence
- `stop_loss`: Recommended stop loss price
- `take_profit`: Recommended take profit price
- `latency_ms`: Inference time in milliseconds

#### GET /health

Get model server health and metrics.

**Response**:
```json
{
  "status": "healthy",
  "uptime_seconds": 3600.5,
  "memory_usage_mb": 145.2,
  "cpu_percent": 12.5,
  "model_loaded": true,
  "model_type": "lightgbm",
  "model_version": "1.0",
  "training_samples": 50000,
  "continuous_learning": false,
  "training": false,
  "data_collector_active": false
}
```

#### POST /feedback

Send trade outcome for model retraining.

**Request**:
```json
{
  "trade_id": "12345",
  "entry_price": 101750.0,
  "exit_price": 102500.0,
  "pnl": 750.0,
  "outcome": "win",
  "duration_seconds": 1800
}
```

#### POST /retrain

Trigger model retraining (requires samples).

**Response**:
```json
{
  "status": "started",
  "samples_count": 1000,
  "estimated_duration": "5 minutes"
}
```

### Coordinator Internal Endpoints

The coordinator does not expose REST API (uses WebSocket for dashboard communication).

## WebSocket API

**URL**: `ws://localhost:8765`

### Connection

```javascript
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => {
  console.log('Connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  handleUpdate(data);
};
```

### Message Types

#### 1. Welcome Message

Sent immediately upon connection.

```json
{
  "type": "welcome",
  "timestamp": "2025-11-07T12:00:00.000Z",
  "message": "Connected to Xylen Coordinator"
}
```

#### 2. Status Update

Broadcast every 60 seconds with complete system state.

```json
{
  "type": "status_update",
  "timestamp": "2025-11-07T12:01:00.000Z",
  "coordinator": {
    "status": "running",
    "dry_run": false,
    "testnet": true,
    "symbol": "BTCUSDT",
    "uptime_seconds": 3600,
    "websocket_clients": 2,
    "open_trades": 1,
    "circuit_breaker": "normal",
    "cpu_usage": 15.2,
    "memory_usage": 85.4
  },
  "models": [
    {
      "name": "model-1",
      "status": "online",
      "online": true,
      "training": false,
      "continuous_learning": false,
      "data_collector_active": false,
      "confidence": 0.82,
      "latency_ms": 12.5,
      "last_prediction": "2025-11-07T12:00:55.000Z",
      "version": "1.0",
      "model_type": "lightgbm",
      "samples_trained": 50000,
      "training_samples": 0,
      "uptime_seconds": 7200,
      "memory_usage_mb": 145.2,
      "cpu_percent": 8.5
    }
  ],
  "market": {
    "price": 101750.0,
    "rsi": 42.5,
    "volume_24h": 50000000.0
  },
  "decision": {
    "action": "long",
    "confidence": 0.78,
    "risk_approved": true
  },
  "performance": {
    "total_pnl": 1250.50,
    "daily_pnl": 85.25,
    "win_rate": 0.65,
    "total_trades": 48
  }
}
```

**Field Descriptions**:

Coordinator:
- `status`: "running" or "stopped"
- `circuit_breaker`: "normal" or "active"
- `websocket_clients`: Number of connected dashboards
- `cpu_usage`: Coordinator process CPU %
- `memory_usage`: Coordinator memory in MB

Models (array):
- `status`: "online" or "offline"
- `confidence`: Latest prediction confidence (0-1)
- `latency_ms`: Average response time
- `last_prediction`: ISO timestamp of last prediction
- `uptime_seconds`: Model server uptime
- `memory_usage_mb`: Model process memory
- `cpu_percent`: Model process CPU %

Market:
- `price`: Current BTC price
- `rsi`: Relative Strength Index
- `volume_24h`: 24h trading volume

Decision:
- `action`: Latest ensemble decision
- `confidence`: Ensemble confidence
- `risk_approved`: Whether risk checks passed

Performance:
- `total_pnl`: Cumulative profit/loss
- `daily_pnl`: Today's P&L
- `win_rate`: Percentage of winning trades
- `total_trades`: Total trades executed

## Prometheus Metrics

**Coordinator Metrics** (`http://localhost:9090`):

- `coordinator_heartbeat_total`: Total decision cycles
- `coordinator_trades_total{action="long|short|hold"}`: Trade counts by action
- `coordinator_pnl_usd`: Current P&L in USD
- `coordinator_model_latency_seconds`: Model response time
- `coordinator_ensemble_confidence`: Decision confidence
- `coordinator_errors_total`: Error count
- `coordinator_balance_usd`: Account balance

**Model Server Metrics** (`http://localhost:800[1-4]/metrics`):

- `model_predictions_total{action="long|short|hold"}`: Prediction counts
- `model_prediction_latency_seconds`: Inference latency histogram
- `model_prediction_confidence`: Confidence histogram
- `model_retrains_total`: Retrain count
- `model_training_samples`: Samples collected
- `model_score`: Model performance score

## Binance API Integration

The coordinator uses Binance Futures Testnet/Mainnet API:

**Authentication**: HMAC SHA256 signatures
**Rate Limits**: 1200 requests/minute (testnet), higher for mainnet
**Endpoints Used**:
- `/fapi/v2/balance`: Get account balance
- `/fapi/v1/order`: Place order
- `/fapi/v1/openOrders`: Query open orders
- `/fapi/v1/allOrders`: Get order history
- `/fapi/v1/positionRisk`: Get position information
- `/fapi/v1/leverage`: Set leverage
- `/fapi/v1/marginType`: Set margin mode

**Error Handling**:
- Automatic retry with exponential backoff
- Signature validation
- Rate limit respect
- Connection pooling

## Data Schemas

### Trade Record (SQLite)

```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    symbol TEXT,
    side TEXT,  -- 'LONG' or 'SHORT'
    entry_price REAL,
    exit_price REAL,
    quantity REAL,
    pnl REAL,
    status TEXT,  -- 'OPEN', 'CLOSED', 'CANCELLED'
    ensemble_confidence REAL,
    model_count INTEGER
);
```

### System Event (SQLite)

```sql
CREATE TABLE system_events (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    event_type TEXT,
    severity TEXT,
    component TEXT,
    message TEXT
);
```

## Configuration File Schema

See `config.yaml.example` for full annotated configuration.

**Key sections**:
- `trading`: Position sizing, leverage, symbol
- `ensemble`: Aggregation method, confidence thresholds
- `safety`: Circuit breakers, loss limits
- `timing`: Heartbeat intervals, timeouts
- `binance`: API endpoints and credentials
- `telegram`: Alert configuration
