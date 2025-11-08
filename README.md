# Project Xylen# Project Xylen - Automated Trading System



Automated cryptocurrency trading system using ensemble machine learning models with real-time market analysis and risk management.Distributed AI trading system for BTCUSDT perpetual futures using multiple model servers coordinated by a central controller.



## System Architecture## Architecture



- **Coordinator**: Central orchestration service managing ensemble decisions, risk, and trade execution- Coordinator: Central orchestration hub for trading decisions

- **Model Servers**: 4x distributed LightGBM inference servers- Model Servers: FastAPI servers running AI models on distributed machines

- **Dashboard**: React-based real-time monitoring interface- Dashboard: Real-time monitoring interface built with React

- **Data Pipeline**: Market data collection, feature engineering, and storage- Binance Integration: Paper trading on testnet



## Quick Start## Features



### Prerequisites- Distributed AI model inference

- Weighted ensemble aggregation

- Docker 20.10+- Automated position management

- Docker Compose 2.0+- Complete audit trail in SQLite and CSV

- Binance Futures Testnet account (for trading)- Continuous model retraining

- 4GB RAM minimum (8GB recommended)- Health monitoring and failover support



### 1. Clone and Configure## Quick Setup



```bash### Step 1: Coordinator Setup

git clone <repository-url>

cd project-xylen```bash

cp config.yaml.example config.yamlcd coordinator

```python3.10 -m venv venv

source venv/bin/activate

### 2. Set Environment Variablespip install -r requirements.txt

cp ../config.yaml.example ../config.yaml

Create `.env` file:nano ../config.yaml

```

```bash

BINANCE_API_KEY=your_testnet_api_keyEdit config.yaml with your Binance testnet credentials and model server endpoints.

BINANCE_API_SECRET=your_testnet_api_secret

TELEGRAM_BOT_TOKEN=your_bot_token  # Optional```bash

TELEGRAM_CHAT_ID=your_chat_id      # Optionalexport BINANCE_TESTNET_API_KEY="your_testnet_api_key"

```export BINANCE_TESTNET_API_SECRET="your_testnet_api_secret"

python coordinator.py

### 3. Configure Trading Parameters```



Edit `config.yaml`:### Step 2: Model Server Setup



```yamlSee docs/MODEL_SERVER_SETUP.md for complete installation instructions:

dry_run: false          # false=execute orders, true=simulation- Linux (Ubuntu 22.04 LTS) with systemd services

testnet: true           # ALWAYS use testnet first- macOS with LaunchDaemon services

trading:- Docker deployment for cross-platform

  leverage: 1           # Conservative leverage

  position_size_fraction: 0.10  # 10% of capital per tradeQuick start for Linux:

ensemble:

  confidence_threshold: 0.70    # Minimum confidence to trade```bash

```sudo apt update

sudo apt install -y python3.10 python3.10-venv python3-pip build-essential

### 4. Start Systemsudo mkdir -p /opt/trading_model

cd /opt/trading_model

```bashcp /path/to/project-xylen/model_server/*.py .

docker compose up -dcp /path/to/project-xylen/model_server/requirements.txt .

```python3.10 -m venv venv

source venv/bin/activate

### 5. Monitorpip install -r requirements.txt

cp models.env.example models.env

- Dashboard: http://localhost:3000nano models.env

- Coordinator logs: `docker logs -f xylen-coordinator````

- Prometheus metrics: http://localhost:9090

Copy your model file and start services:

## Project Structure

```bash

```cp /path/to/model.txt /opt/trading_model/models/trading_model.txt

project-xylen/sudo cp /path/to/project-xylen/model_server/linux_services/*.service /etc/systemd/system/

├── coordinator/          # Ensemble coordinator servicesudo systemctl daemon-reload

├── model_server/         # ML inference servers  sudo systemctl enable model_server data_collector continuous_trainer

├── dashboard/           # React monitoring UIsudo systemctl start model_server data_collector continuous_trainer

├── scripts/             # Utility scripts```

├── tests/               # Test suites

├── docs/                # Documentation### Step 3: Dashboard Setup

├── config.yaml          # Main configuration

└── docker-compose.yml   # Service orchestration```bash

```cd dashboard

npm install

## Documentationnpm run dev

```

- [Architecture](docs/ARCHITECTURE.md) - System design and components

- [API Reference](docs/API.md) - REST and WebSocket APIsFor production:

- [Model Setup](docs/MODEL_SETUP.md) - Training and deployment

- [Coordinator Setup](docs/COORDINATOR_SETUP.md) - Configuration guide```bash

- [About](docs/ABOUT.md) - Project backgroundnpm run build

npm run preview

## Safety and Risk Management```



**CRITICAL**: This system executes real trades. Always:## Directory Structure



1. Start with `testnet: true` and `dry_run: false````

2. Test thoroughly on testnet before mainnetproject-xylen/

3. Use conservative leverage (1-3x maximum)├── coordinator/          # Central trading orchestrator

4. Set appropriate stop losses├── model_server/         # Distributed AI model servers

5. Monitor circuit breakers and daily loss limits├── dashboard/            # React monitoring interface

6. Enable Telegram alerts for critical events├── docs/                 # Documentation

└── scripts/              # Utility scripts

## Monitoring and Alerts```



- Real-time dashboard with model health, trades, and performance## Configuration

- WebSocket streaming for live updates

- Telegram notifications for trades, errors, and circuit breakersEdit config.yaml before starting the coordinator:

- Prometheus metrics for system monitoring

```bash

## Supportnano config.yaml

```

For issues or questions, refer to the documentation in `docs/` directory.

Key parameters:

## License- dry_run: true for simulation, false for testnet trading

- model_endpoints: List of model server URLs

Proprietary - All rights reserved- ensemble_threshold: Minimum confidence (0.0-1.0)

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
