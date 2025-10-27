# TradeProject - Automated Paper Trading System

Complete automated trading coordinator for BTCUSDT perpetual futures using distributed AI models running on Ubuntu VMs coordinated by a MacBook Air M2 controller.

## Architecture Overview

This system consists of:

- Mac Coordinator: Python async program that orchestrates trading decisions
- Model VMs: Up to 4 Ubuntu LTS VMs running FastAPI model servers with AI models
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

For detailed setup instructions see DOCUMENTATION.md.

For VirtualBox VM creation on Windows hosts see VM_SETUP.md.

### Mac Controller Setup

```bash
cd mac_coordinator
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
cd model_server_template
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
TradeProject/
├── README.md
├── DOCUMENTATION.md
├── VM_SETUP.md
├── config.yaml.example
├── mac_coordinator/
│   ├── coordinator.py
│   ├── ensemble.py
│   ├── binance_client.py
│   ├── data_logger.py
│   ├── requirements.txt
│   └── tests/
├── model_server_template/
│   ├── server.py
│   ├── model_loader.py
│   ├── retrain.py
│   ├── convert_to_onnx.py
│   ├── requirements.txt
│   ├── models.env.example
│   └── model_server.service
├── dashboard/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
├── scripts/
│   ├── vbox_create_vm.ps1
│   ├── backup_sqlite.sh
│   └── setup_vm_ssh.sh
├── ci/
│   ├── test_integration.py
│   └── run_tests.sh
├── examples/
│   ├── sample_snapshot.json
│   ├── curl_predict.sh
│   └── curl_retrain.sh
└── docker/
    └── Dockerfile.model_server
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

See DOCUMENTATION.md section "Model Integration Guide" for detailed instructions.

## Support and Troubleshooting

Check logs:

- Mac coordinator: ./logs/coordinator.log
- Model servers: journalctl -u model_server -f
- Dashboard: Browser console

Common issues and solutions are documented in DOCUMENTATION.md.

## License

This project is provided as-is for educational and research purposes. Use at your own risk. Never trade with funds you cannot afford to lose.
