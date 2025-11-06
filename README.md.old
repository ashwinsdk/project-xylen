# Project Xylen - Automated Trading System

Distributed AI trading system for BTCUSDT perpetual futures using multiple model servers coordinated by a central controller.

## Architecture

- Coordinator: Central orchestration hub for trading decisions
- Model Servers: FastAPI servers running AI models on distributed machines
- Dashboard: Real-time monitoring interface built with React
- Binance Integration: Paper trading on testnet

## Features

- Distributed AI model inference
- Weighted ensemble aggregation
- Automated position management
- Complete audit trail in SQLite and CSV
- Continuous model retraining
- Health monitoring and failover support

## Quick Setup

### Step 1: Coordinator Setup

```bash
cd coordinator
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../config.yaml.example ../config.yaml
nano ../config.yaml
```

Edit config.yaml with your Binance testnet credentials and model server endpoints.

```bash
export BINANCE_TESTNET_API_KEY="your_testnet_api_key"
export BINANCE_TESTNET_API_SECRET="your_testnet_api_secret"
python coordinator.py
```

### Step 2: Model Server Setup

See docs/MODEL_SERVER_SETUP.md for complete installation instructions:
- Linux (Ubuntu 22.04 LTS) with systemd services
- macOS with LaunchDaemon services
- Docker deployment for cross-platform

Quick start for Linux:

```bash
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip build-essential
sudo mkdir -p /opt/trading_model
cd /opt/trading_model
cp /path/to/project-xylen/model_server/*.py .
cp /path/to/project-xylen/model_server/requirements.txt .
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp models.env.example models.env
nano models.env
```

Copy your model file and start services:

```bash
cp /path/to/model.txt /opt/trading_model/models/trading_model.txt
sudo cp /path/to/project-xylen/model_server/linux_services/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable model_server data_collector continuous_trainer
sudo systemctl start model_server data_collector continuous_trainer
```

### Step 3: Dashboard Setup

```bash
cd dashboard
npm install
npm run dev
```

For production:

```bash
npm run build
npm run preview
```

## Directory Structure

```
project-xylen/
├── coordinator/          # Central trading orchestrator
├── model_server/         # Distributed AI model servers
├── dashboard/            # React monitoring interface
├── docs/                 # Documentation
└── scripts/              # Utility scripts
```

## Configuration

Edit config.yaml before starting the coordinator:

```bash
nano config.yaml
```

Key parameters:
- dry_run: true for simulation, false for testnet trading
- model_endpoints: List of model server URLs
- ensemble_threshold: Minimum confidence (0.0-1.0)
- position_size_fraction: Trade size as fraction of equity
- stop_loss_pct: Stop loss percentage
- take_profit_pct: Take profit percentage

## Model Integration

Supported formats: LightGBM, ONNX, PyTorch

```bash
cp your_model.txt /opt/trading_model/models/trading_model.txt
nano /opt/trading_model/models.env
```

Set MODEL_TYPE and MODEL_PATH in models.env, then restart:

```bash
sudo systemctl restart model_server
```

## Logs and Monitoring

Coordinator logs:
```bash
tail -f coordinator/logs/coordinator.log
```

Model server logs (Linux):
```bash
sudo journalctl -u model_server -f
```

Model server logs (macOS):
```bash
tail -f /usr/local/opt/trading_model/logs/model_server.log
```

Dashboard: http://localhost:5173

## Testing

Always test on Binance testnet before production:

1. Run coordinator with dry_run: true
2. Verify all model servers respond
3. Monitor logs for 24+ hours
4. Test emergency shutdown

## Documentation

- docs/MODEL_SERVER_SETUP.md - Complete model server setup guide
- docs/QUICKSTART.md - Quick start guide

## License

Proprietary software. All rights reserved. See LICENSE file for terms.
