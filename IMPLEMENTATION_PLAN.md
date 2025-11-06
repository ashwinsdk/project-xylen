# Project Xylen Revamp - Implementation Status & Plan

Branch: `xylen/revamp`  
Started: November 6, 2025  
Python: 3.10.12  
Target: Ubuntu 24.04.3 LTS

## Completed Components

### 1. Configuration Files ✅
- **config.yaml.example**: Complete production configuration with all tunables
  - Ensemble parameters (Bayesian, calibration, thresholds)
  - Trading parameters (position sizing, Kelly, stop/take)
  - Risk management (circuit breakers, loss limits)
  - Model endpoints with weights
  - Data collection and feature engineering
  - Monitoring and observability
  
- **model_server/models.env.example**: Model server environment template
  - LightGBM and ONNX configuration
  - Retraining parameters (incremental + full)
  - Resource constraints for 8GB hosts
  - Prometheus metrics
  - Security and rate limiting

### 2. Requirements Files ✅
- **coordinator/requirements.txt**: Pinned dependencies for Python 3.10.12
  - Core: aiohttp, python-binance, pyyaml
  - ML: lightgbm, scikit-learn, river
  - API: fastapi, uvicorn
  - Monitoring: prometheus-client, psutil
  
- **model_server/requirements.txt**: Model server dependencies
  - ML: lightgbm, onnx, onnxruntime, river
  - Feature engineering: pyarrow, fastparquet
  - Hyperparameter tuning: optuna

### 3. Core Modules ✅
- **coordinator/risk_manager.py**: Production-grade risk management (615 lines)
  - Position sizing: fixed fraction, Kelly criterion, fixed amount
  - Trade validation with multiple safety checks
  - Circuit breakers with exponential cooldown
  - Daily loss limits (percent and absolute)
  - Emergency shutdown logic
  - Comprehensive statistics and metrics
  
- **coordinator/ensemble.py**: Xylen Adaptive Consensus engine (550 lines)
  - Bayesian weighted aggregation
  - Exponential performance decay
  - Probability calibration (isotonic regression)
  - Uncertainty-aware gating
  - Meta-learner integration (LightGBM)
  - Expected value calculation with trade costs
  - Model performance tracking

## Remaining Implementation Work

### Phase 1: Core Trading Infrastructure (HIGH PRIORITY)

#### 1.1 Update coordinator/binance_client.py
**Status**: Needs major upgrade  
**Priority**: CRITICAL  
**Estimated Time**: 4-6 hours

**Requirements**:
- Add testnet support with environment-driven keys
- Implement order state machine with SQLite persistence
- Add exponential backoff with tenacity
- Implement rate limiting with token bucket algorithm
- Add margin mode support (CROSSED/ISOLATED)
- Implement order monitoring (REST-based, poll every 10s)
- Add WebSocket fallback (optional)
- Handle edge cases: post-only, reduce-only, margin rejection

**Key Methods**:
```python
class BinanceClient:
    async def place_order(symbol, side, quantity, stop_loss, take_profit)
    async def get_order_status(order_id)
    async def cancel_order(order_id)
    async def get_account_balance()
    async def get_open_positions()
    async def set_leverage(symbol, leverage)
    async def set_margin_mode(symbol, mode)
```

**Testing**: Integration test with testnet API

---

#### 1.2 Update coordinator/market_data.py
**Status**: Needs feature expansion  
**Priority**: CRITICAL  
**Estimated Time**: 3-4 hours

**Requirements**:
- Expand to 29+ feature indicators
- Add RSI (14, 28), EMA (9, 20, 50, 200)
- Add MACD, Bollinger Bands, ATR, OBV, ADX
- Add candle pattern features (body ratio, shadows)
- Add momentum features (price, volume)
- Implement deterministic computation (no randomness)
- Add Parquet storage with gzip compression
- Implement binance.vision data download
- Add multi-timeframe support (5m, 15m, 1h)

**Schema**:
```python
{
    'timestamp': int64,
    'open': float32,
    'high': float32,
    'low': float32,
    'close': float32,
    'volume': float32,
    'rsi_14': float32,
    'ema_20': float32,
    # ... 29+ features total
}
```

---

#### 1.3 Update coordinator/data_logger.py
**Status**: Needs schema v2  
**Priority**: HIGH  
**Estimated Time**: 2-3 hours

**Requirements**:
- SQLite schema version 2 with migrations
- Tables: trades, orders, snapshots, model_predictions
- Enable WAL mode for concurrency
- Add indices for fast queries
- Implement trade event logging
- Add feature snapshot storage
- Implement CSV export (append mode)
- Add backup scheduler (daily to ./data/backups/)

**Schema**:
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    timestamp REAL NOT NULL,
    symbol TEXT,
    side TEXT,
    entry_price REAL,
    exit_price REAL,
    quantity REAL,
    pnl REAL,
    pnl_percent REAL,
    closed INTEGER,
    ensemble_confidence REAL,
    model_votes TEXT  -- JSON
);

CREATE INDEX idx_trades_timestamp ON trades(timestamp);
CREATE INDEX idx_trades_closed ON trades(closed);
```

---

#### 1.4 Update coordinator/coordinator.py
**Status**: Needs full rewrite  
**Priority**: CRITICAL  
**Estimated Time**: 6-8 hours

**Requirements**:
- Wire ensemble engine, risk manager, binance client
- Implement main heartbeat loop (60s cycle)
- Add asyncio task management
- Implement graceful shutdown (SIGINT, SIGTERM)
- Add Prometheus metrics exporter
- Implement WebSocket server for dashboard
- Add configuration hot-reload (SIGHUP)
- Handle model server failures gracefully

**Main Loop**:
```python
async def main_loop():
    while not shutdown_event.is_set():
        # 1. Collect market snapshot
        snapshot = await market_data.get_snapshot()
        
        # 2. Query model servers (parallel)
        predictions = await query_models(snapshot)
        
        # 3. Ensemble aggregation
        decision = ensemble.aggregate_predictions(predictions, snapshot['price'])
        
        # 4. Risk validation
        is_valid, reason = risk_manager.validate_trade(metrics, decision.size_usd)
        
        # 5. Execute if valid
        if is_valid and decision.action != 'HOLD':
            order = await binance_client.place_order(...)
            data_logger.log_trade(order, decision)
        
        # 6. Monitor open positions
        await monitor_positions()
        
        # 7. Update metrics
        prometheus.update_metrics()
        
        await asyncio.sleep(heartbeat_interval)
```

---

### Phase 2: Model Server Implementation (HIGH PRIORITY)

#### 2.1 Create model_server/server.py
**Status**: Needs rewrite  
**Priority**: CRITICAL  
**Estimated Time**: 4-6 hours

**Requirements**:
- FastAPI application with three endpoints
- Load LightGBM from /opt/trading_model/models/trading_model.txt
- ONNX fallback with onnxruntime
- Prometheus metrics endpoint
- Health check with system metrics
- Graceful degradation on low memory

**Endpoints**:
```python
@app.post("/predict")
async def predict(request: PredictionRequest) -> PredictionResponse:
    # Extract features from candles + indicators
    # Run inference (LightGBM or ONNX)
    # Return: action, confidence, stop, take_profit, raw_score

@app.post("/retrain")
async def retrain(feedback: RetrainingFeedback) -> RetrainingResponse:
    # Append to feedback buffer
    # Trigger incremental retrain if conditions met
    # Return: status, samples_received, retrain_scheduled

@app.get("/health")
async def health() -> HealthResponse:
    # Return: uptime, memory_usage, model_version, last_trained
```

---

#### 2.2 Create model_server/convert_to_onnx.py
**Status**: New file  
**Priority**: MEDIUM  
**Estimated Time**: 2-3 hours

**Requirements**:
- Convert LightGBM .txt model to ONNX format
- Use skl2onnx library
- Validate ONNX model produces same outputs
- Add CLI interface with argparse

**Usage**:
```bash
python3 convert_to_onnx.py \
    --input models/trading_model.txt \
    --output models/trading_model.onnx \
    --validate
```

---

#### 2.3 Create model_server/onnx_inference.py
**Status**: New file  
**Priority**: MEDIUM  
**Estimated Time**: 1-2 hours

**Requirements**:
- Load ONNX model with onnxruntime
- Inference wrapper compatible with LightGBM API
- Automatic fallback if ONNX fails

---

#### 2.4 Update model_server/continuous_trainer.py
**Status**: Needs River integration  
**Priority**: MEDIUM  
**Estimated Time**: 3-4 hours

**Requirements**:
- Implement incremental learning with River
- Read from feedback buffer (Parquet)
- Check resource constraints (memory, swap)
- Trigger retrain only if safe
- Save model checkpoint after retrain
- Log retraining metrics

---

### Phase 3: Service Files & Deployment (MEDIUM PRIORITY)

#### 3.1 Create systemd Service Files
**Status**: New files  
**Priority**: HIGH  
**Estimated Time**: 2-3 hours

**Files**:
- `model_server/linux_services/projectxylen-modelserver.service`
- `model_server/linux_services/projectxylen-datacollector.service`
- `model_server/linux_services/projectxylen-trainer.service`
- `model_server/linux_services/projectxylen-trainer.timer`

**Example**:
```ini
[Unit]
Description=Project Xylen Model Server
After=network.target

[Service]
Type=simple
User=xylen
WorkingDirectory=/opt/trading_model
EnvironmentFile=/opt/trading_model/model_server/models.env
ExecStart=/opt/trading_model/venv/bin/python3 model_server/server.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

#### 3.2 Create launchd Plist Files
**Status**: Partial exists  
**Priority**: MEDIUM  
**Estimated Time**: 1-2 hours

**Files**:
- `model_server/mac_services/com.projectxylen.modelserver.plist`
- `model_server/mac_services/com.projectxylen.coordinator.plist`
- `model_server/mac_services/install.sh`

---

### Phase 4: Docker & Orchestration (MEDIUM PRIORITY)

#### 4.1 Create Dockerfiles
**Status**: New files  
**Priority**: MEDIUM  
**Estimated Time**: 3-4 hours

**Files**:
- `coordinator/Dockerfile`
- `model_server/Dockerfile`
- `dashboard/Dockerfile`
- `docker-compose.yml`

**Requirements**:
- Multi-stage builds for smaller images
- Use Python 3.10.12 base image
- Volume mounts for /opt/trading_model
- Health checks for all services
- Network isolation

---

#### 4.2 Create docker-compose.yml
**Status**: New file  
**Priority**: MEDIUM  
**Estimated Time**: 2 hours

**Services**:
- coordinator
- model-server (sample)
- dashboard
- prometheus
- grafana
- nginx

---

### Phase 5: Dashboard (MEDIUM PRIORITY)

#### 5.1 Rewrite React Dashboard
**Status**: Needs major rewrite  
**Priority**: MEDIUM  
**Estimated Time**: 8-10 hours

**Requirements**:
- Install Tailwind CSS
- Use Xylen color scheme (black + #5C0000 to #8B0000 gradient)
- Real-time WebSocket updates
- Components: ModelStatus, TradesList, PerformanceChart, SystemLogs
- Recharts for visualizations
- Production build configuration

**Tech Stack**:
- React 18
- Tailwind CSS 3
- Recharts
- WebSocket client

---

### Phase 6: Monitoring Stack (LOW PRIORITY)

#### 6.1 Create Prometheus + Grafana Setup
**Status**: New files  
**Priority**: LOW  
**Estimated Time**: 3-4 hours

**Files**:
- `monitoring/prometheus.yml`
- `monitoring/grafana-datasource.yml`
- `monitoring/dashboards/xylen-trading.json`
- `monitoring/docker-compose.yml`

---

### Phase 7: Scripts & Utilities (MEDIUM PRIORITY)

#### 7.1 Deployment Scripts
**Status**: New files  
**Priority**: MEDIUM  
**Estimated Time**: 4-5 hours

**Files**:
- `scripts/install_services.sh` - Install systemd services
- `scripts/convert_and_deploy.sh` - ONNX conversion + atomic deploy
- `scripts/backup_sqlite.sh` - Database backup with rotation
- `scripts/restore_db.sh` - Database restore
- `scripts/rotate_logs.sh` - Log rotation
- `scripts/preflight_check.py` - Pre-production validation

---

### Phase 8: Testing (HIGH PRIORITY)

#### 8.1 Unit Tests
**Status**: Partial exists  
**Priority**: HIGH  
**Estimated Time**: 6-8 hours

**Files**:
- `coordinator/tests/test_risk_manager.py`
- `coordinator/tests/test_ensemble.py`
- `coordinator/tests/test_market_data.py`
- `coordinator/tests/test_binance_client.py`
- `coordinator/tests/test_data_logger.py`

---

#### 8.2 Integration Tests
**Status**: New file  
**Priority**: HIGH  
**Estimated Time**: 4-6 hours

**File**: `coordinator/tests/test_integration.py`

**Requirements**:
- Spin up mock model servers (FastAPI)
- Run full coordinator cycle
- Validate order execution (testnet)
- Check database persistence
- Verify metrics export

---

### Phase 9: CI/CD (LOW PRIORITY)

#### 9.1 GitHub Actions Workflow
**Status**: New file  
**Priority**: LOW  
**Estimated Time**: 2-3 hours

**File**: `.github/workflows/ci.yml`

**Jobs**:
- Lint (flake8, black)
- Unit tests
- Integration tests (Docker Compose)
- Build Docker images
- Security scan (bandit)

---

### Phase 10: Documentation (HIGH PRIORITY)

#### 10.1 Complete README.md
**Status**: Needs expansion  
**Priority**: HIGH  
**Estimated Time**: 3-4 hours

**Sections**:
- Architecture diagram
- Quick start (Docker + native)
- Configuration guide
- Deployment instructions (systemd, launchd, Docker)
- Testing procedures
- Production checklist
- Troubleshooting guide

---

#### 10.2 Create DOCUMENTATION.md
**Status**: New file  
**Priority**: MEDIUM  
**Estimated Time**: 4-6 hours

**Sections**:
- System architecture
- API contracts (/predict, /retrain, /health)
- Database schema (SQLite tables)
- Configuration reference
- Feature engineering pipeline
- Model training guide
- Backtesting procedures
- Migration guide

---

### Phase 11: Nginx & Security (LOW PRIORITY)

#### 11.1 Create Nginx Configuration
**Status**: New files  
**Priority**: LOW  
**Estimated Time**: 2-3 hours

**Files**:
- `nginx/xylen-api.conf` - Reverse proxy config
- `nginx/README.md` - Setup instructions
- `nginx/setup-letsencrypt.sh` - Automated SSL setup

---

## Implementation Priority Matrix

### CRITICAL (Start Immediately)
1. coordinator/binance_client.py - Order execution
2. coordinator/market_data.py - Feature engineering
3. coordinator/coordinator.py - Main loop
4. model_server/server.py - FastAPI endpoints
5. coordinator/data_logger.py - Database schema

### HIGH (Next Week)
6. Unit tests (risk_manager, ensemble, market_data)
7. Integration test (full coordinator cycle)
8. Systemd service files
9. README.md completion
10. Deployment scripts (install_services.sh, backup_sqlite.sh)

### MEDIUM (Following Week)
11. ONNX conversion utilities
12. Incremental training (River)
13. Docker setup (Dockerfiles, docker-compose.yml)
14. Dashboard rewrite (Tailwind + WebSocket)
15. launchd plist files
16. DOCUMENTATION.md

### LOW (As Time Permits)
17. Prometheus + Grafana stack
18. Nginx configuration with Let's Encrypt
19. GitHub Actions CI/CD
20. Optional features (regime detection, multi-symbol)

---

## Quick Implementation Commands

### Setup Development Environment
```bash
cd /Users/ashwinsudhakar/Documents/Code/Projects/project-xylen
git checkout xylen/revamp

# Coordinator setup
cd coordinator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create config
cp ../config.yaml.example ../config.yaml
nano ../config.yaml  # Add your settings

# Create directories
mkdir -p logs data/backups data/feature_store

# Run tests
pytest tests/ -v
```

### Deploy to Ubuntu Model Server
```bash
# SSH to remote
ssh user@100.108.252.74

# Setup directory
sudo mkdir -p /opt/trading_model
sudo chown $USER:$USER /opt/trading_model
cd /opt/trading_model

# Clone and setup
git clone https://github.com/ashwinsdk/project-xylen.git .
git checkout xylen/revamp
python3.10 -m venv venv
source venv/bin/activate
pip install -r model_server/requirements.txt

# Configure
cp model_server/models.env.example model_server/models.env
nano model_server/models.env

# Install service
sudo cp model_server/linux_services/projectxylen-modelserver.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable projectxylen-modelserver
sudo systemctl start projectxylen-modelserver
sudo systemctl status projectxylen-modelserver
```

### Run Integration Test
```bash
cd coordinator
source venv/bin/activate
export BINANCE_API_KEY="your_testnet_key"
export BINANCE_API_SECRET="your_testnet_secret"
pytest tests/test_integration.py -v -s
```

---

## Estimated Total Time

- **Core Infrastructure (Phase 1-2)**: 25-35 hours
- **Deployment & Services (Phase 3)**: 3-5 hours
- **Docker & Dashboard (Phase 4-5)**: 13-17 hours
- **Monitoring & Scripts (Phase 6-7)**: 7-9 hours
- **Testing (Phase 8)**: 10-14 hours
- **CI/CD & Docs (Phase 9-10)**: 9-13 hours
- **Nginx & Security (Phase 11)**: 2-3 hours

**Total**: 69-96 hours (approximately 2-3 weeks full-time)

---

## Next Immediate Steps

1. **Complete coordinator/binance_client.py** (6 hours)
   - Order state machine
   - Rate limiting
   - Testnet support
   
2. **Complete coordinator/market_data.py** (4 hours)
   - 29+ features
   - Parquet storage
   - binance.vision download
   
3. **Complete coordinator/coordinator.py** (8 hours)
   - Main loop
   - Wire all components
   - Metrics exporter
   
4. **Complete model_server/server.py** (6 hours)
   - /predict endpoint
   - /retrain endpoint
   - /health endpoint
   
5. **Write integration test** (6 hours)
   - Mock model servers
   - Full coordinator cycle
   - Testnet validation

After these 5 items (30 hours), you will have a **working, testable system** that can execute trades on Binance testnet.

---

## Contact & Support

For questions or issues during implementation:
- Review existing code in coordinator/ and model_server/
- Check config.yaml.example for configuration options
- See models.env.example for model server setup
- Test incrementally after each component

**Remember**: Test everything on testnet first. Never enable live trading without completing the full production checklist.
