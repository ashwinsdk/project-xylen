# Project Xylen - Automated Trading System

Complete automated trading system for BTCUSDT perpetual futures using distributed AI models running on Ubuntu VMs coordinated by a central controller.

## Architecture Overview

This system consists of:

- Coordinator: Python async program that orchestrates trading decisions
- Model Servers: Up to 4 Ubuntu LTS VMs running FastAPI model servers with AI models
- React Dashboard: Real-time monitoring interface
- Binance Testnet Integration: Safe paper trading environment

## Key Features

- Distributed AI model inference across multiple VMs
- Weighted ensemble aggregation with confidence thresholds
- Automated position management with stop-loss and take-profit
- Complete audit trail in SQLite and CSV
- Model retraining pipeline with trade outcome feedback
- VM health monitoring and partial availability support
- Dry-run and paper trading modes

## Quick Start

For detailed setup instructions see docs/QUICKSTART.md.

For VirtualBox VM creation on Windows hosts see docs/VM_SETUP.md.

### Controller Setup

```bash
cd coordinator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../config.yaml.example ../config.yaml
# Edit config.yaml with your settings
export BINANCE_TESTNET_API_KEY="your_key"
export BINANCE_TESTNET_API_SECRET="your_secret"
python coordinator.py
```

### Model Server Setup (on each Ubuntu VM)

```bash
cd model_server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp models.env.example models.env
# Edit models.env with model file path
python server.py
```

### Dashboard Setup

```bash
cd dashboard
npm install
npm run build
npm run preview
```

## Repository Structure

```
project-xylen/
├── README.md
├── config.yaml.example
├── coordinator/
│   ├── coordinator.py
│   ├── ensemble.py
│   ├── binance_client.py
│   ├── data_logger.py
│   ├── market_data.py
│   ├── api_server.py
│   ├── requirements.txt
│   └── tests/
├── model_server/
│   ├── server.py
│   ├── model_loader_optimized.py
│   ├── retrain_optimized.py
│   ├── continuous_trainer.py
│   ├── data_collector.py
│   ├── requirements.txt
│   ├── models.env.example
│   └── linux_services/
├── dashboard/
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/
│   ├── package.json
│   └── vite.config.js
├── docs/
│   ├── QUICKSTART.md
│   └── VM_SETUP.md
└── scripts/
    └── backup_sqlite.sh
```

## Safety and Testing

This project starts in paper trading mode on Binance testnet. Never use real funds until:

1. All integration tests pass
2. System runs successfully for at least 7 days on testnet
3. You understand every configuration parameter
4. You have tested emergency shutdown procedures

See DOCUMENTATION.md section "Pre-Production Checklist" for complete safety requirements.

## Configuration

All configuration is in config.yaml. Key parameters:

- dry_run: Set to true to simulate trades without API calls
- model_endpoints: List of VM host:port addresses
- ensemble_threshold: Minimum confidence to place trade (default 0.7)
- position_size_fraction: Fraction of equity per trade (default 0.1)
- heartbeat_interval: Seconds between snapshots (default 60)

## Model Integration

The system supports any model that can be loaded in Python. To integrate your model:

1. Export model to PyTorch checkpoint, ONNX, or LightGBM format
2. Copy model file to VM at /opt/trading_model/model.onnx
3. Edit models.env to set MODEL_PATH=/opt/trading_model/model.onnx
4. Restart model server: sudo systemctl restart model_server

See docs/QUICKSTART.md section "Model Integration Guide" for detailed instructions.

## Support and Troubleshooting

Check logs:

- Coordinator: ./logs/coordinator.log
- Model servers: journalctl -u model_server -f
- Dashboard: Browser console

Common issues and solutions are documented in docs/QUICKSTART.md.

## License

This project is provided as-is for educational and research purposes. Use at your own risk. Never trade with funds you cannot afford to lose.
