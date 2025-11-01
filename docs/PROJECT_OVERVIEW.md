# TradeProject - Complete System Overview

This document provides a high-level overview of the entire TradeProject system architecture, components, and workflows.

## System Purpose

TradeProject is an automated paper trading system that uses distributed AI models to make trading decisions for BTCUSDT perpetual futures on Binance testnet. The system coordinates predictions from multiple models running on separate VMs, aggregates them using ensemble logic, and executes trades while maintaining complete audit trails.

## Architecture Components

### 1. Mac Coordinator (Central Controller)

Location: mac_coordinator/

The brain of the operation running on MacBook Air M2. Written in Python using asyncio for concurrent operations.

Key Modules:
- coordinator.py: Main orchestration loop, manages trading lifecycle
- ensemble.py: Aggregates model predictions using weighted voting, confidence averaging, or majority vote
- binance_client.py: Interfaces with Binance API for order placement and monitoring
- market_data.py: Collects candlestick data and calculates technical indicators using CCXT
- data_logger.py: Persists all data to SQLite and CSV for audit and retraining

Responsibilities:
- Capture market snapshots every 1-3 minutes (configurable heartbeat)
- Send snapshots to all active model VMs in parallel
- Wait for responses with configurable timeout
- Aggregate predictions using ensemble method
- Apply confidence threshold and risk rules
- Place trades if threshold exceeded and no open positions
- Monitor open positions until closure
- Send trade outcomes to models for retraining
- Enforce safety limits (daily loss, max trades, circuit breaker)

### 2. Model VMs (Inference Servers)

Location: model_server_template/

Up to 4 Ubuntu LTS VMs running on Windows hosts via VirtualBox, each with 12 GB RAM and 120 GB storage. Can also run as Docker containers.

Key Modules:
- server.py: FastAPI application exposing /predict, /retrain, and /health endpoints
- model_loader.py: Loads ONNX, PyTorch, or LightGBM models and performs inference
- retrain.py: Manages online retraining using trade outcome feedback
- convert_to_onnx.py: Utility to convert PyTorch models to ONNX for efficient CPU inference

Responsibilities:
- Expose plain HTTP API (no auth as specified)
- Accept market snapshots and return predictions
- Support any pluggable model (user provides model file)
- Accept trade outcome feedback via /retrain endpoint
- Store training samples and trigger retraining when threshold reached
- Report health and uptime via /health endpoint
- Run as systemd service with automatic restart

### 3. React Dashboard (Monitoring UI)

Location: dashboard/

Single-page React application with electric blue on black aesthetic.

Components:
- ModelStatus: Displays health, uptime, memory, and performance of each model VM
- TradesList: Shows recent trades with entry/exit prices and P&L
- PerformanceChart: Cumulative P&L line chart using Recharts
- SystemLogs: Real-time log stream with color-coded severity levels

Features:
- Auto-refresh every 5 seconds
- Responsive grid layout
- Performance metrics summary cards
- No backend required (can fetch from coordinator API or use mock data)

### 4. Documentation Suite

- README.md: Project overview and quick reference
- DOCUMENTATION.md: Complete step-by-step setup instructions for all components
- VM_SETUP.md: Detailed VirtualBox VM creation guide for Windows hosts
- QUICKSTART.md: 30-minute fast setup guide for immediate testing
- docker/README.md: Docker deployment alternative to VMs

## Data Flow

1. Market Data Collection
   - Coordinator fetches 5m and 1h candlesticks from Binance via CCXT
   - Calculates indicators: RSI, EMA, MACD, Bollinger Bands, volume
   - Packages as JSON snapshot

2. Model Inference
   - Coordinator sends snapshot to all enabled model VMs in parallel
   - Each VM extracts features, runs model inference, returns prediction
   - Predictions include action (long/short/hold), confidence, stop, take_profit

3. Ensemble Aggregation
   - Coordinator collects responses within timeout window
   - Applies ensemble method (weighted_vote by default)
   - Adjusts weights based on recent model performance
   - Produces final decision with confidence score

4. Trade Execution
   - If confidence >= threshold and no open positions, place order
   - Set stop-loss and take-profit levels
   - Monitor order status every 10 seconds
   - When filled/closed, calculate P&L

5. Logging and Feedback
   - Log snapshot, predictions, decision, trade to SQLite and CSV
   - Send trade outcome back to model VMs for retraining
   - Models append to training data and retrain when enough samples

6. Risk Management
   - Check daily trade limit, loss limit, consecutive losses
   - Pause trading if limits exceeded
   - Emergency shutdown at 20% daily loss (configurable)

## Configuration

Single config.yaml controls entire system:

- dry_run: true/false (simulate trades without API calls)
- testnet: true/false (use Binance testnet or mainnet)
- model_endpoints: list of VM host:port with weights
- ensemble.threshold: minimum confidence to trade (default 0.7)
- trading.position_size_fraction: equity percentage per trade (default 0.1)
- timing.heartbeat_interval: seconds between snapshots (default 60)
- safety limits: max daily trades, loss limits, circuit breaker

## Testing Infrastructure

Unit Tests:
- test_ensemble.py: Tests ensemble aggregation methods
- test_data_logger.py: Tests database operations

Integration Test:
- test_integration.py: Spins up mock model servers, runs full coordinator cycle

Test Runner:
- ci/run_tests.sh: Executes all tests with single command

## Deployment Options

### Option 1: VirtualBox VMs (Production)
- Full isolation on separate physical hosts
- 12 GB RAM per VM, 120 GB storage
- Systemd service for auto-restart
- VirtualBox autostart on host boot
- Complete setup in VM_SETUP.md

### Option 2: Docker Containers (Development)
- Faster setup, lower overhead
- All 4 containers on single Mac (requires 48 GB RAM total)
- Docker Compose for easy management
- Shared network for coordinator access
- Complete setup in docker/README.md

## Model Integration

System is model-agnostic. To integrate your model:

1. Export to ONNX (recommended), PyTorch TorchScript, or LightGBM format
2. Copy model file to VM at /opt/trading_model/models/
3. Update models.env with MODEL_PATH and MODEL_TYPE
4. Restart model server

Model must accept 10 features (returns, RSI, volume, EMAs, MACD, Bollinger Bands) and output action + confidence. The model_loader.py handles feature extraction and output interpretation.

For custom features, modify _prepare_features in model_loader.py.

## Retraining Pipeline

Automatic retraining loop:

1. Trade closes, P&L calculated
2. Coordinator sends outcome to model VMs via /retrain endpoint
3. VM appends sample to training_data/samples.jsonl
4. When MIN_SAMPLES_FOR_RETRAIN reached (default 50), retrain triggered
5. Retrain loads samples, extracts features, trains new model
6. Backs up old model, saves new model, reloads

Supports incremental updates (LightGBM, online learning) or periodic full retraining (PyTorch).

Schedule nightly retraining via cron on VMs for offline processing.

## Safety Features

Multiple layers of protection:

- Dry-run mode: Simulates all trades without API calls
- Testnet mode: Uses Binance testnet with fake funds
- Position limits: Max 1 concurrent position (configurable)
- Stop-loss: Automatic 2% stop (configurable)
- Daily trade limit: Max 20 trades per day (configurable)
- Daily loss limit: Pauses at 10% daily loss (configurable)
- Circuit breaker: Pauses after 5 consecutive losses (configurable)
- Emergency shutdown: Kills system at 20% daily loss (configurable)
- Rate limiting: Respects Binance API limits with exponential backoff

## Persistence and Backup

All data persisted to:

- SQLite: data/trades.db (trades, analysis_log, model_performance tables)
- CSV: data/trades.csv (human-readable audit trail)
- Logs: logs/coordinator.log (rotating log files)

Backup script: scripts/backup_sqlite.sh

Creates timestamped backups, cleans up old backups (30 day retention).

## Performance Characteristics

Resource Usage:
- Mac coordinator: ~200 MB RAM, <5% CPU
- Each model VM: 2-4 GB RAM (varies by model size), 50-80% CPU during inference
- Dashboard: ~50 MB RAM in browser

Latency:
- Market data fetch: ~500ms
- Model inference: 100-500ms per model (parallel)
- Ensemble aggregation: <10ms
- Order placement: ~200ms
- Total snapshot-to-decision: 1-2 seconds with 4 models

Throughput:
- 1 snapshot per minute default (configurable to 30 seconds minimum)
- Handles up to 10 models with proper timeout configuration
- Binance API allows 1200 requests/minute, 50 orders/10sec

## Security Considerations

As specified, internal APIs use plain HTTP without authentication. Security measures:

- Keep VMs on private network isolated from internet
- Use firewall rules to restrict port 8000 access
- Never expose model servers to public networks
- Store Binance API keys in environment variables or macOS keychain
- Never commit API keys to git (.gitignore configured)
- Use testnet for all initial testing
- Regular security updates on Ubuntu VMs

## Production Readiness Checklist

Before enabling real trading:

- [ ] System runs 7+ days on testnet without errors
- [ ] All integration tests pass
- [ ] Win rate and risk/reward validated on testnet
- [ ] Backup procedures tested
- [ ] Emergency shutdown tested
- [ ] All safety limits configured appropriately
- [ ] Position sizing appropriate for account size
- [ ] Documentation reviewed and understood
- [ ] Never risk more than you can afford to lose

## Extensibility Points

Easy to customize:

1. Add new indicators: Modify market_data.py _calculate_indicators
2. Change ensemble logic: Add method to ensemble.py
3. Implement new model type: Extend model_loader.py with new loader
4. Add trading pairs: Update config.yaml symbol (code supports any Binance futures pair)
5. Multi-timeframe strategies: Use meta.candles_1h in model input
6. Custom position sizing: Modify _place_trade in coordinator.py
7. Add new risk rules: Extend _should_pause_trading in coordinator.py

## File Structure Summary

```
TradeProject/
├── README.md                    # Project overview
├── DOCUMENTATION.md             # Complete setup guide
├── VM_SETUP.md                  # VirtualBox VM creation
├── QUICKSTART.md                # 30-minute quick start
├── PROJECT_OVERVIEW.md          # This file
├── config.yaml.example          # Configuration template
├── .gitignore                   # Prevents committing secrets
│
├── mac_coordinator/             # Main trading controller
│   ├── coordinator.py           # Orchestration loop
│   ├── ensemble.py              # Model aggregation
│   ├── binance_client.py        # Exchange API
│   ├── market_data.py           # Data collection
│   ├── data_logger.py           # Persistence
│   ├── requirements.txt         # Python dependencies
│   └── tests/                   # Unit tests
│
├── model_server_template/       # VM inference server
│   ├── server.py                # FastAPI application
│   ├── model_loader.py          # Model inference
│   ├── retrain.py               # Online learning
│   ├── convert_to_onnx.py       # Model conversion
│   ├── requirements.txt         # Python dependencies
│   ├── models.env.example       # Environment template
│   └── model_server.service     # Systemd service file
│
├── dashboard/                   # React monitoring UI
│   ├── src/
│   │   ├── App.jsx              # Main application
│   │   ├── components/          # UI components
│   │   └── index.css            # Styles
│   ├── package.json             # Node dependencies
│   └── vite.config.js           # Build configuration
│
├── scripts/                     # Utility scripts
│   ├── backup_sqlite.sh         # Database backup
│   ├── setup_vm_ssh.sh          # VM setup helper
│   └── vbox_create_vm.ps1       # VirtualBox automation
│
├── ci/                          # Testing infrastructure
│   ├── test_integration.py      # Full system test
│   └── run_tests.sh             # Test runner
│
├── examples/                    # Usage examples
│   ├── sample_snapshot.json     # Example market data
│   ├── curl_predict.sh          # Test model endpoint
│   └── curl_retrain.sh          # Test retrain endpoint
│
└── docker/                      # Container deployment
    ├── Dockerfile.model_server  # Model server image
    ├── docker-compose.yml       # Multi-container setup
    └── README.md                # Docker guide
```

## Next Steps

1. Read QUICKSTART.md for immediate hands-on testing
2. Review DOCUMENTATION.md for production deployment
3. Follow VM_SETUP.md to create model VMs
4. Run tests with ci/run_tests.sh
5. Deploy your models following model integration guide
6. Monitor via dashboard at http://localhost:3000
7. Iterate on models using retraining feedback loop
8. Graduate from testnet to mainnet only after validation

## Support

This is a complete, self-contained project. All information needed to deploy and operate the system is contained in the documentation files. Review troubleshooting sections in DOCUMENTATION.md for common issues.

## Disclaimer

This software is provided as-is for educational purposes. Trading involves substantial risk of loss. Never trade with funds you cannot afford to lose. The authors assume no responsibility for trading losses. Always test thoroughly on testnet before considering real funds.
