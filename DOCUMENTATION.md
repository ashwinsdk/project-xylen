# TradeProject Complete Documentation

This document provides comprehensive step-by-step instructions to set up and run the TradeProject automated trading system from scratch.

## System Architecture

The system consists of three main components:

1. Mac Coordinator: Python async program running on MacBook Air M2 that orchestrates trading
2. Model VMs: Up to 4 Ubuntu LTS VMs running FastAPI model servers with AI models
3. React Dashboard: Web interface for monitoring system status and performance

Data flows: Mac coordinator captures market data, sends to model VMs, receives predictions, aggregates via ensemble logic, places trades on Binance testnet, monitors positions, and logs all data to SQLite and CSV.

## Prerequisites

### Mac Requirements

- MacBook Air M2 with 8 GB RAM
- macOS Ventura or Monterey
- Python 3.10 or later
- Node.js 18 or later and npm
- Homebrew package manager
- Internet connection for API access

### Windows Host Requirements (for VMs)

- Windows 10 or 11
- 16 GB RAM minimum (to run one 12 GB VM)
- 64 GB RAM recommended (to run four 12 GB VMs)
- 500 GB available disk space
- VirtualBox 7.0 or later
- Network with DHCP

### Binance Account

- Binance testnet account (sign up at testnet.binancefuture.com)
- API key and secret from testnet (never use mainnet keys initially)

## Part 1: VM Setup on Windows Hosts

Follow VM_SETUP.md to create and configure Ubuntu VMs on your Windows hosts. Complete this before proceeding to Mac setup.

Summary of VM setup:
- Create VMs with 12 GB RAM and 120 GB disk
- Install Ubuntu 22.04 LTS Server
- Enable SSH and configure static or reserved DHCP IPs
- Install model server code and dependencies
- Configure systemd service for automatic startup
- Test model server responds on port 8000

After VM setup, you should have:
- 1 to 4 VMs running and accessible via SSH
- Each VM has a known IP address (e.g., 192.168.1.100, 192.168.1.101, etc.)
- Model server running on each VM and responding to health checks

## Part 2: Mac Coordinator Setup

### Install Homebrew (if not installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Install Python 3.10

```bash
brew install python@3.10
```

Verify installation:

```bash
python3 --version
```

### Install Node.js and npm

```bash
brew install node
```

Verify installation:

```bash
node --version
npm --version
```

### Clone or Download Repository

If you have this repository, navigate to it. Otherwise, create the TradeProject directory structure as shown in README.md.

```bash
cd TradeProject
```

### Install TA-Lib

TA-Lib is required for technical indicators. Install via Homebrew:

```bash
brew install ta-lib
```

### Setup Mac Coordinator Python Environment

```bash
cd mac_coordinator
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If TA-Lib installation fails, you may need to set compiler flags:

```bash
export TA_INCLUDE_PATH="$(brew --prefix ta-lib)/include"
export TA_LIBRARY_PATH="$(brew --prefix ta-lib)/lib"
pip install ta-lib
```

### Configure System

Copy example configuration:

```bash
cd ..
cp config.yaml.example config.yaml
```

Edit config.yaml:

```bash
nano config.yaml
```

Update the following sections:

1. Set dry_run to true initially
2. Set testnet to true
3. Update model_endpoints with your VM IP addresses:

```yaml
model_endpoints:
  - host: "192.168.1.100"
    port: 8000
    name: "model_vm_1"
    weight: 1.0
    enabled: true
  - host: "192.168.1.101"
    port: 8000
    name: "model_vm_2"
    weight: 1.0
    enabled: true
```

Save and exit (Ctrl+X, Y, Enter).

### Setup Binance Testnet API Keys

Sign up for Binance testnet at https://testnet.binancefuture.com

Generate API keys from your testnet account dashboard.

Store keys in environment variables. Add to your ~/.zshrc or ~/.bash_profile:

```bash
echo 'export BINANCE_TESTNET_API_KEY="your_testnet_api_key_here"' >> ~/.zshrc
echo 'export BINANCE_TESTNET_API_SECRET="your_testnet_api_secret_here"' >> ~/.zshrc
source ~/.zshrc
```

For secure storage using macOS Keychain:

```bash
security add-generic-password -a "$USER" -s "binance_testnet_api_key" -w "your_testnet_api_key_here"
security add-generic-password -a "$USER" -s "binance_testnet_api_secret" -w "your_testnet_api_secret_here"
```

To retrieve from keychain in your scripts:

```bash
export BINANCE_TESTNET_API_KEY=$(security find-generic-password -a "$USER" -s "binance_testnet_api_key" -w)
export BINANCE_TESTNET_API_SECRET=$(security find-generic-password -a "$USER" -s "binance_testnet_api_secret" -w)
```

### Test Coordinator in Dry Run Mode

```bash
cd mac_coordinator
source venv/bin/activate
python coordinator.py
```

You should see log output indicating:
- Coordinator starting in dry run mode
- Connections to model VMs
- Market data collection
- Model predictions received
- Ensemble decisions made
- Simulated trades (not actually placed)

Press Ctrl+C to stop.

### Check Logs and Data

Logs are written to:

```bash
cat logs/coordinator.log
```

Database and CSV files are in:

```bash
ls -la data/
```

## Part 3: Dashboard Setup

### Install Dashboard Dependencies

```bash
cd dashboard
npm install
```

### Run Dashboard in Development Mode

```bash
npm run dev
```

The dashboard will start at http://localhost:3000

Open in your browser to view the interface with mock data.

### Build Dashboard for Production

```bash
npm run build
```

Preview production build:

```bash
npm run preview
```

The dashboard displays:
- Model VM health status
- Recent trades and P&L
- Performance charts
- System logs

## Part 4: Model Integration Guide

The system supports any model that can be loaded in Python. Follow these steps to integrate your model.

### Supported Model Formats

- ONNX (.onnx) - Recommended for CPU inference
- PyTorch (.pt, .pth, TorchScript)
- LightGBM (.txt, .model)

### Converting PyTorch Models to ONNX

If you have a PyTorch model, convert it to ONNX for better CPU performance:

```bash
cd model_server_template
source venv/bin/activate
python convert_to_onnx.py /path/to/model.pt /path/to/model.onnx --input-size 10
```

The input size should match the number of features your model expects. The default feature extractor creates 10 features.

### Deploying Model to VM

Copy your model file to the VM:

```bash
scp model.onnx ubuntu@192.168.1.100:/opt/trading_model/models/
```

SSH into the VM:

```bash
ssh ubuntu@192.168.1.100
```

Update the environment configuration:

```bash
cd /opt/trading_model
nano models.env
```

Set MODEL_PATH to your model file:

```
MODEL_PATH=/opt/trading_model/models/model.onnx
MODEL_TYPE=onnx
```

Restart the model server:

```bash
sudo systemctl restart model_server
```

Check logs to verify model loaded:

```bash
sudo journalctl -u model_server -n 20
```

### Model Input/Output Schema

The model server sends this JSON structure to your model via the /predict endpoint:

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "5m",
  "candles": [
    {
      "timestamp": 1234567890,
      "open": 50000.0,
      "high": 50100.0,
      "low": 49900.0,
      "close": 50050.0,
      "volume": 123.45
    }
  ],
  "indicators": {
    "rsi": 55.2,
    "volume": 123.45,
    "ema_20": 50000.0,
    "ema_50": 49800.0,
    "macd": 50.0,
    "bb_upper": 51000.0,
    "bb_middle": 50000.0,
    "bb_lower": 49000.0
  },
  "meta": {
    "utc": "2024-01-01T00:00:00",
    "candles_1h": []
  }
}
```

Expected model output:

```json
{
  "action": "long",
  "confidence": 0.85,
  "stop": 49500.0,
  "take_profit": 51000.0,
  "raw_score": 0.75
}
```

Action must be one of: "long", "short", "hold"
Confidence should be between 0 and 1
Stop and take_profit are optional price levels

### Custom Feature Extraction

If your model requires different features, modify model_loader.py in the _prepare_features method to extract the features your model expects.

### Inference Settings for 12 GB RAM

Recommended settings for CPU inference on 12 GB RAM VMs:

- Batch size: 1 (sequential inference)
- Use ONNX with CPUExecutionProvider
- Limit model size to under 2 GB
- Use quantized models if available (INT8 quantization)
- Set OMP_NUM_THREADS=2 for CPU parallelism

Add to models.env:

```
OMP_NUM_THREADS=2
ONNX_NUM_THREADS=2
```

### Testing Model Predictions

Test your model endpoint manually:

```bash
curl -X POST http://192.168.1.100:8000/health
```

Send a test prediction request:

```bash
curl -X POST http://192.168.1.100:8000/predict \
  -H "Content-Type: application/json" \
  -d @../examples/sample_snapshot.json
```

## Part 5: Running the System

### Pre-Flight Checklist

Before starting the system:

- [ ] All VMs are running and accessible
- [ ] Model servers are running on all VMs (check systemctl status)
- [ ] Config.yaml is properly configured with correct VM IPs
- [ ] Binance testnet API keys are set in environment
- [ ] dry_run is set to true in config.yaml
- [ ] testnet is set to true in config.yaml
- [ ] Dashboard dependencies are installed
- [ ] Logs and data directories exist and are writable

### Start the System

Open three terminal windows or tabs.

Terminal 1 - Mac Coordinator:

```bash
cd mac_coordinator
source venv/bin/activate
python coordinator.py
```

Terminal 2 - Dashboard:

```bash
cd dashboard
npm run dev
```

Terminal 3 - Log Monitoring:

```bash
tail -f mac_coordinator/logs/coordinator.log
```

### Monitor Operation

Watch the coordinator logs for:
- Market data collection every heartbeat interval (default 60 seconds)
- Model predictions received from VMs
- Ensemble decisions
- Simulated trades (in dry run mode)
- Any errors or warnings

Open dashboard at http://localhost:3000 to view:
- Model health status
- Recent trades
- Performance metrics
- System logs

### Stopping the System

Stop coordinator: Press Ctrl+C in Terminal 1
Stop dashboard: Press Ctrl+C in Terminal 2

The system will shut down gracefully. Any open positions will be logged.

## Part 6: Model Retraining

The system includes automatic retraining capabilities that use trade outcomes to improve models.

### Retraining Pipeline

Trade outcomes are automatically sent to model VMs via the /retrain endpoint when retraining is enabled in config.yaml.

Training samples are stored on each VM at:

```
/opt/trading_model/training_data/samples.jsonl
```

Each line is a JSON object with:
- decision: The model's original prediction
- outcome: The actual P&L result
- snapshot: Market data at prediction time

### Manual Retraining

SSH into a VM and trigger retraining manually:

```bash
curl -X POST http://localhost:8000/retrain/trigger
```

The retraining process:
1. Loads all training samples
2. Extracts features and labels (profit/loss)
3. Trains a new model (currently supports LightGBM)
4. Backs up the old model
5. Saves and loads the new model
6. Returns training results

### Scheduled Retraining

Set up a cron job on the VM for nightly retraining:

```bash
crontab -e
```

Add this line to retrain at 2 AM daily:

```
0 2 * * * curl -X POST http://localhost:8000/retrain/trigger >> /opt/trading_model/retrain.log 2>&1
```

### Offline Retraining with PyTorch

For PyTorch models, implement custom training logic in retrain.py. Example workflow:

1. Export training data from SQLite:

```bash
sqlite3 data/trades.db "SELECT * FROM trades WHERE status='CLOSED'" > training_data.csv
```

2. Create a training script that:
   - Loads training_data.csv
   - Prepares features and labels
   - Trains model with your architecture
   - Saves checkpoint
   - Converts to ONNX

3. Transfer updated model to VMs
4. Restart model servers

### Monitoring GPU/CPU Usage During Training

On VM during training:

```bash
htop
```

For GPU monitoring (if GPU is available):

```bash
nvidia-smi -l 1
```

Limit CPU usage during training to avoid affecting inference:

```bash
taskset -c 0,1 python retrain_script.py
```

### Incremental Updates with River

For online learning, use River library for incremental updates:

```bash
pip install river
```

Update retrain.py to use River's streaming models for continuous learning from each trade.

## Part 7: Production Deployment Checklist

Do NOT enable real trading until all items are verified:

### Testing Phase (Minimum 7 Days)

- [ ] System runs successfully on Binance testnet for 7 consecutive days
- [ ] No runtime errors or crashes
- [ ] All model VMs remain healthy and responsive
- [ ] Ensemble logic produces sensible decisions
- [ ] Position management works correctly (stop loss, take profit)
- [ ] All trades are logged correctly to database and CSV
- [ ] Dashboard displays accurate real-time data
- [ ] Retraining completes successfully
- [ ] Backup and restore procedures tested

### Integration Tests Passed

- [ ] Run all unit tests: cd mac_coordinator && pytest tests/
- [ ] Run integration test: python ci/test_integration.py
- [ ] Test with simulated model servers
- [ ] Test network failure scenarios (VM goes offline)
- [ ] Test API rate limiting and backoff
- [ ] Test emergency shutdown procedures

### Risk Management Verified

- [ ] Position sizing fraction is appropriate (default 0.1 = 10%)
- [ ] Stop loss percentage is set (default 0.02 = 2%)
- [ ] Take profit percentage is set (default 0.05 = 5%)
- [ ] Max open positions limit is enforced
- [ ] Daily trade limit is configured
- [ ] Daily loss limit is configured
- [ ] Circuit breaker (consecutive losses) is configured
- [ ] Emergency shutdown threshold is set

### Security and Safety

- [ ] Binance API keys are stored securely (environment or keychain)
- [ ] Never commit API keys to git
- [ ] VM network is isolated from public internet
- [ ] Model server endpoints are not publicly accessible
- [ ] Regular backups are configured
- [ ] Log rotation is enabled
- [ ] Emergency stop procedure documented and tested

### Performance Validation

- [ ] Testnet results show positive expectancy over 7+ days
- [ ] Win rate is acceptable (target 55%+)
- [ ] Risk/reward ratio is favorable
- [ ] Drawdown is within acceptable limits
- [ ] System handles market volatility appropriately
- [ ] No overfitting to specific market conditions

### Going Live Procedure

Only after ALL checklist items are complete:

1. Set testnet to false in config.yaml
2. Update Binance API keys to mainnet keys (via environment variables)
3. Set dry_run to false in config.yaml
4. Start with minimum position sizes
5. Monitor closely for first 24 hours
6. Gradually increase position sizes if performance is acceptable

Warning: Real trading involves risk of loss. Only trade with funds you can afford to lose. This system is provided as-is with no guarantees.

## Part 8: Troubleshooting

### Coordinator Won't Start

Check Python version:
```bash
python3 --version
```

Check dependencies:
```bash
pip list
```

Reinstall requirements:
```bash
pip install -r requirements.txt --force-reinstall
```

### Cannot Connect to Model VMs

Test connectivity:
```bash
ping 192.168.1.100
```

Test model server:
```bash
curl http://192.168.1.100:8000/health
```

Check VM firewall:
```bash
ssh ubuntu@192.168.1.100
sudo ufw status
```

### Binance API Errors

Verify API keys are set:
```bash
echo $BINANCE_TESTNET_API_KEY
echo $BINANCE_TESTNET_API_SECRET
```

Test API access:
```bash
curl -H "X-MBX-APIKEY: $BINANCE_TESTNET_API_KEY" https://testnet.binancefuture.com/fapi/v1/time
```

Check rate limits in logs and adjust timing.heartbeat_interval if needed.

### Model Server Crashes

Check memory usage:
```bash
ssh ubuntu@192.168.1.100
free -h
```

Check logs:
```bash
sudo journalctl -u model_server -n 100
```

Restart service:
```bash
sudo systemctl restart model_server
```

### Database Locked Errors

SQLite can lock with concurrent access. Ensure only one coordinator instance is running.

Check for lock file:
```bash
ls -la data/trades.db*
```

### Dashboard Not Loading

Check Node.js version:
```bash
node --version
```

Reinstall dependencies:
```bash
cd dashboard
rm -rf node_modules package-lock.json
npm install
```

Check for port conflicts:
```bash
lsof -i :3000
```

### High CPU Usage

Check coordinator process:
```bash
top -pid $(pgrep -f coordinator.py)
```

Increase heartbeat_interval in config.yaml to reduce frequency.

Check model inference time in logs. If too slow, optimize model or use ONNX format.

### Memory Leaks

Monitor coordinator memory over time:
```bash
ps aux | grep coordinator.py
```

Restart coordinator daily via cron if memory grows unbounded:
```bash
0 0 * * * pkill -f coordinator.py && cd /path/to/mac_coordinator && source venv/bin/activate && python coordinator.py &
```

## Part 9: Backup and Recovery

### Automated Backup Script

Create backup script:

```bash
nano scripts/backup_sqlite.sh
```

Add content from scripts/backup_sqlite.sh in repository. Make executable:

```bash
chmod +x scripts/backup_sqlite.sh
```

Run backup:

```bash
./scripts/backup_sqlite.sh
```

Schedule daily backups via cron:

```bash
crontab -e
```

Add:
```
0 3 * * * /path/to/TradeProject/scripts/backup_sqlite.sh
```

### Manual Backup

Backup database:
```bash
cp data/trades.db backups/trades_$(date +%Y%m%d).db
```

Backup CSV:
```bash
cp data/trades.csv backups/trades_$(date +%Y%m%d).csv
```

Backup config:
```bash
cp config.yaml backups/config_$(date +%Y%m%d).yaml
```

### Backup Model Files on VMs

From Mac, backup all VM model files:

```bash
for ip in 192.168.1.100 192.168.1.101; do
  ssh ubuntu@$ip "cd /opt/trading_model && tar czf model_backup.tar.gz models/ training_data/"
  scp ubuntu@$ip:/opt/trading_model/model_backup.tar.gz backups/vm_${ip}_$(date +%Y%m%d).tar.gz
done
```

### Restore Procedure

Restore database:
```bash
cp backups/trades_20240101.db data/trades.db
```

Restore model to VM:
```bash
scp backups/vm_192.168.1.100_20240101.tar.gz ubuntu@192.168.1.100:/opt/trading_model/
ssh ubuntu@192.168.1.100 "cd /opt/trading_model && tar xzf model_backup.tar.gz"
```

## Part 10: Advanced Configuration

### Ensemble Methods

Three ensemble methods are available in config.yaml:

1. weighted_vote: Votes weighted by model performance and confidence (recommended)
2. average_confidence: Simple average of confidences
3. majority: Majority vote ignoring confidence

### Weight Decay

weight_decay parameter controls how recent performance affects model weights. Higher values (closer to 1.0) give more weight to recent performance.

### Custom Indicators

Add custom indicators by modifying market_data.py _calculate_indicators method. Ensure model feature extraction matches.

### Multiple Timeframes

The system collects both 5m and 1h candles. Models can use both timeframes in meta.candles_1h.

### Position Sizing Strategies

Current implementation uses fixed fraction. For advanced strategies, modify _place_trade in coordinator.py to implement:
- Kelly Criterion sizing
- Volatility-adjusted sizing
- Account balance-based scaling

### Risk Management Rules

Customize safety limits in config.yaml safety section. All limits are enforced in _should_pause_trading method.

## Part 11: Performance Optimization

### Reduce Latency

- Decrease heartbeat_interval (minimum 30 seconds to avoid rate limits)
- Deploy VMs closer to exchange (cloud VMs in same region)
- Use ONNX models with optimized inference
- Reduce candles_count if not needed by model

### Reduce Resource Usage

- Increase heartbeat_interval
- Reduce number of active models
- Use smaller models
- Disable retraining if not needed

### Scale to More Models

The system supports up to 4 VMs by default. To add more:
1. Create additional VMs
2. Add endpoints to config.yaml
3. Adjust ensemble weights
4. Consider weighted sampling instead of querying all models

## Support and Community

This is a self-contained project. For issues:
1. Check logs for specific error messages
2. Review troubleshooting section
3. Verify all prerequisites are met
4. Test components individually

## License and Disclaimer

This software is provided as-is for educational and research purposes. No warranty of any kind. Trading cryptocurrencies involves substantial risk of loss. Never trade with funds you cannot afford to lose. Past performance does not guarantee future results. The authors assume no responsibility for trading losses.
