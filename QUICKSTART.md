# Project Xylen Revamp - Quick Start Guide

**For Developers Continuing This Work**

## Current Status

Branch `xylen/revamp` contains Phase 1 implementation (25% complete):
- ✅ Production configuration system
- ✅ Risk manager with Kelly criterion
- ✅ Xylen Adaptive Consensus ensemble
- ✅ Pinned dependencies for Python 3.10.12
- ⏳ Binance client (needs implementation)
- ⏳ Market data (needs expansion)
- ⏳ Coordinator main loop (needs rewrite)
- ⏳ Model server (needs implementation)

## Setup in 5 Minutes

```bash
# 1. Clone and checkout
cd /Users/ashwinsudhakar/Documents/Code/Projects/project-xylen
git checkout xylen/revamp

# 2. Set up coordinator environment
cd coordinator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Copy configuration
cd ..
cp config.yaml.example config.yaml

# 4. Set environment variables
export BINANCE_API_KEY="your_testnet_api_key"
export BINANCE_API_SECRET="your_testnet_api_secret"

# 5. Test components
python3 -c "from coordinator.risk_manager import RiskManager; print('✅ Risk manager loaded')"
python3 -c "from coordinator.ensemble import EnsembleEngine; print('✅ Ensemble engine loaded')"
```

## What to Build Next

**Priority 1: Coordinator Infrastructure (18 hours)**

1. `coordinator/binance_client.py` - Order execution (6h)
   - Order state machine
   - Rate limiting
   - Testnet support

2. `coordinator/market_data.py` - Feature engineering (4h)
   - 29+ indicators
   - Parquet storage

3. `coordinator/coordinator.py` - Main loop (8h)
   - Wire all components
   - Async heartbeat
   - Metrics export

**Priority 2: Model Server (12 hours)**

4. `model_server/server.py` - FastAPI (6h)
   - /predict endpoint
   - /retrain endpoint
   - /health endpoint

5. `model_server/convert_to_onnx.py` - ONNX conversion (2h)

6. Integration test (4h)

**After 30 hours**: Working testnet-ready system

## Key Files to Review

**Understand the Architecture**:
1. `IMPLEMENTATION_PLAN.md` - Full roadmap (READ THIS FIRST)
2. `SESSION_SUMMARY.md` - What was done and why
3. `config.yaml.example` - All configuration options
4. `coordinator/risk_manager.py` - Position sizing logic
5. `coordinator/ensemble.py` - Decision algorithm

**Code Examples**:

### Using Risk Manager
```python
from coordinator.risk_manager import RiskManager
import yaml

with open('config.yaml') as f:
    config = yaml.safe_load(f)

rm = RiskManager(config)

# Calculate position size
position = rm.calculate_position_size(
    current_price=50000.0,
    account_balance=10000.0,
    leverage=1,
    win_rate=0.55,
    avg_win=0.05,
    avg_loss=0.02
)

print(f"Position size: {position.quantity} BTC (${position.size_usd:.2f})")
print(f"Method: {position.method}, Risk: {position.risk_percent:.1%}")
```

### Using Ensemble Engine
```python
from coordinator.ensemble import EnsembleEngine, ModelPrediction
import yaml

with open('config.yaml') as f:
    config = yaml.safe_load(f)

ensemble = EnsembleEngine(config)

# Simulate model predictions
predictions = [
    ModelPrediction(
        model_name="model_1",
        raw_score=0.65,
        confidence=0.75,
        latency_ms=45.2,
        timestamp=time.time()
    ),
    ModelPrediction(
        model_name="model_2",
        raw_score=0.72,
        confidence=0.80,
        latency_ms=52.1,
        timestamp=time.time()
    )
]

# Get ensemble decision
decision = ensemble.aggregate_predictions(predictions, current_price=50000.0)

print(f"Action: {decision.action}")
print(f"Confidence: {decision.confidence:.1%}")
print(f"Expected Value: {decision.expected_value:.3f}")
print(f"Reasoning: {decision.reasoning}")
```

## Development Workflow

### 1. Implement a Component
```bash
# Create feature branch (optional)
git checkout -b feature/binance-client

# Edit files
nano coordinator/binance_client.py

# Test manually
python3 -c "from coordinator.binance_client import BinanceClient; print('OK')"
```

### 2. Write Tests
```bash
# Create test file
nano coordinator/tests/test_binance_client.py

# Run tests
pytest coordinator/tests/test_binance_client.py -v
```

### 3. Commit Changes
```bash
git add coordinator/binance_client.py coordinator/tests/test_binance_client.py
git commit -m "Implement binance_client with order state machine"
git checkout xylen/revamp
git merge feature/binance-client
```

## Common Commands

### Run Full Test Suite
```bash
cd coordinator
source venv/bin/activate
pytest tests/ -v --cov=coordinator
```

### Check Code Quality
```bash
# Install linters (if not already)
pip install flake8 black

# Format code
black coordinator/

# Check style
flake8 coordinator/ --max-line-length=120
```

### Deploy to Remote Model Server
```bash
# Sync code
rsync -av --exclude='venv/' --exclude='data/' --exclude='logs/' \
  model_server/ user@100.108.252.74:/opt/trading_model/model_server/

# SSH and restart
ssh user@100.108.252.74
cd /opt/trading_model
source venv/bin/activate
pip install -r model_server/requirements.txt --upgrade
sudo systemctl restart projectxylen-modelserver
```

### View Logs
```bash
# Coordinator
tail -f coordinator/logs/coordinator.log

# Model server (remote)
ssh user@100.108.252.74 "sudo journalctl -u projectxylen-modelserver -f"
```

### Database Queries
```bash
# View recent trades
sqlite3 coordinator/data/trades.db "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10;"

# Check daily P&L
sqlite3 coordinator/data/trades.db "SELECT DATE(timestamp, 'unixepoch'), SUM(pnl) FROM trades WHERE closed=1 GROUP BY DATE(timestamp, 'unixepoch');"
```

## Testing Checklist

Before considering a component "done":

- [ ] Code written and follows style guide
- [ ] Unit tests written (pytest)
- [ ] Tests pass locally
- [ ] Manual testing completed
- [ ] Error handling implemented
- [ ] Logging added at appropriate levels
- [ ] Documentation strings added
- [ ] Configuration options added to config.yaml if needed
- [ ] Integration test updated if applicable
- [ ] Code committed with descriptive message

## Critical Path to Working System

To get a testable system fastest:

**Day 1 (8 hours)**:
- Morning: Implement `coordinator/binance_client.py` (6h)
- Afternoon: Write unit tests (2h)

**Day 2 (8 hours)**:
- Morning: Implement `coordinator/market_data.py` (4h)
- Afternoon: Update `coordinator/data_logger.py` (4h)

**Day 3 (8 hours)**:
- All day: Implement `coordinator/coordinator.py` main loop (8h)

**Day 4 (6 hours)**:
- Morning: Implement `model_server/server.py` (6h)

**Day 5 (4 hours)**:
- Morning: Write integration test (4h)
- Afternoon: Test on testnet, fix bugs

**Result**: Working system by end of Day 5 (34 hours)

## When You Get Stuck

1. **Read the plan**: `IMPLEMENTATION_PLAN.md` has detailed requirements
2. **Check examples**: Look at existing code (risk_manager.py, ensemble.py)
3. **Review config**: Many behaviors are configurable in config.yaml
4. **Check dependencies**: Make sure requirements.txt is installed
5. **Enable debug logging**: Set `logging.level: DEBUG` in config.yaml
6. **Test incrementally**: Don't write everything before testing
7. **Use git**: Commit working code frequently

## Useful Resources

**Code Reference**:
- `coordinator/risk_manager.py` - Example of production-grade module
- `coordinator/ensemble.py` - Example of complex algorithm implementation
- `config.yaml.example` - All available configuration options

**External Documentation**:
- Binance Futures API: https://binance-docs.github.io/apidocs/futures/en/
- LightGBM: https://lightgbm.readthedocs.io/
- FastAPI: https://fastapi.tiangolo.com/
- River: https://riverml.xyz/

**Testing**:
- pytest: https://docs.pytest.org/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/

## Pre-Production Checklist

Before enabling real trading:

1. Complete all CRITICAL priority items
2. Run integration tests for 7+ days on testnet
3. Verify no errors in logs
4. Confirm circuit breakers work
5. Test emergency shutdown manually
6. Backup all databases
7. Review and adjust risk parameters
8. Double-check API credentials (production vs testnet)
9. Set `use_real_account: true` only after above complete
10. Monitor first live trade very closely

## Getting Help

**Documentation**:
- `IMPLEMENTATION_PLAN.md` - Detailed task breakdown
- `SESSION_SUMMARY.md` - Context on what was built
- Inline code comments in `.py` files

**Code Review**:
- Risk manager implements 3 position sizing methods
- Ensemble implements Bayesian aggregation with meta-learning
- Both modules are heavily commented

**Testing**:
- Run existing tests: `pytest coordinator/tests/ -v`
- Check test coverage: `pytest --cov=coordinator --cov-report=html`
- View coverage report: `open htmlcov/index.html`

## Deployment Overview

**Development (Mac M2)**:
```
coordinator/ (local development)
├── venv/
├── config.yaml
└── Run: python3 coordinator.py
```

**Production (Ubuntu VMs)**:
```
/opt/trading_model/
├── venv/
├── model_server/
├── models/
└── Systemd service: projectxylen-modelserver.service
```

**Docker (Testing)**:
```
docker-compose up --build
Access: http://localhost:5173 (dashboard)
```

## Success Criteria

You'll know the implementation is working when:

1. Coordinator starts without errors
2. Model servers respond on `/health`
3. Ensemble produces decisions every 60s
4. Orders execute on Binance testnet
5. Database records trades
6. Metrics export to Prometheus
7. Dashboard displays real-time data
8. Logs are clean (no errors)

## Final Tips

- **Start simple**: Get basic functionality working before optimization
- **Test early**: Don't wait until everything is complete
- **Use testnet**: Never develop against production API
- **Commit often**: Small commits are easier to debug
- **Read the code**: risk_manager.py and ensemble.py are good examples
- **Follow the plan**: IMPLEMENTATION_PLAN.md has all the details
- **Ask questions**: Leave comments in code for future reference

---

**Ready to start?**
```bash
cd /Users/ashwinsudhakar/Documents/Code/Projects/project-xylen
git checkout xylen/revamp
cat IMPLEMENTATION_PLAN.md | grep "CRITICAL" -A 5
```

**Next step**: Implement `coordinator/binance_client.py` (see IMPLEMENTATION_PLAN.md section 1.1)

Good luck! The hard algorithmic work is done. Now it's time to build the plumbing.
