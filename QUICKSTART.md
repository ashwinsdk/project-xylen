# TradeProject Quick Start Guide

This guide gets you running with TradeProject in under 30 minutes using placeholder models and dry-run mode on Binance testnet.

## Prerequisites Checklist

- [ ] MacBook with macOS and Python 3.10 installed
- [ ] Node.js 18 or later installed
- [ ] Binance testnet account created at testnet.binancefuture.com
- [ ] API key and secret from Binance testnet
- [ ] 1-4 VMs running Ubuntu 22.04 LTS (see VM_SETUP.md) OR use Docker

## Option A: Quick Start with Docker (Easiest)

If you have Docker installed on your Mac, this is the fastest way to get started.

### Step 1: Build and Start Model Servers

```bash
cd docker
docker-compose up -d model_server_1 model_server_2
```

Wait 30 seconds for servers to start, then verify:

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### Step 2: Configure Mac Coordinator

```bash
cd ..
cp config.yaml.example config.yaml
```

Edit config.yaml and update model endpoints to use Docker containers:

```yaml
model_endpoints:
  - host: "localhost"
    port: 8001
    name: "model_docker_1"
    weight: 1.0
    enabled: true
  - host: "localhost"
    port: 8002
    name: "model_docker_2"
    weight: 1.0
    enabled: true
```

Keep dry_run: true and testnet: true.

### Step 3: Setup Mac Coordinator

```bash
cd mac_coordinator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 4: Set Binance API Keys

```bash
export BINANCE_TESTNET_API_KEY="your_testnet_key"
export BINANCE_TESTNET_API_SECRET="your_testnet_secret"
```

### Step 5: Start Coordinator

```bash
python coordinator.py
```

You should see log output showing market data collection, model predictions, and ensemble decisions.

### Step 6: View Dashboard

Open a new terminal:

```bash
cd dashboard
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

## Option B: Quick Start with Single VM

If you have one VM running at 192.168.1.100.

### Step 1: Setup VM Model Server

SSH into your VM:

```bash
ssh ubuntu@192.168.1.100
```

Transfer model server code from your Mac:

```bash
# From Mac terminal
scp -r model_server_template/* ubuntu@192.168.1.100:/opt/trading_model/
```

On VM, install and start:

```bash
cd /opt/trading_model
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp models.env.example models.env
python server.py
```

Test from Mac:

```bash
curl http://192.168.1.100:8000/health
```

### Step 2: Configure and Run Mac Coordinator

```bash
cp config.yaml.example config.yaml
```

Edit config.yaml with your VM IP:

```yaml
model_endpoints:
  - host: "192.168.1.100"
    port: 8000
    name: "model_vm_1"
    weight: 1.0
    enabled: true
```

Set API keys and run:

```bash
cd mac_coordinator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export BINANCE_TESTNET_API_KEY="your_key"
export BINANCE_TESTNET_API_SECRET="your_secret"
python coordinator.py
```

## Verifying Everything Works

You should see in the logs:

```
INFO - Starting Trading Coordinator
INFO - Dry Run Mode: True
INFO - Testnet Mode: True
INFO - Model loaded successfully
INFO - Health check: 1/1 models healthy
INFO - Collected market snapshot: 100 candles
INFO - Ensemble decision: long (confidence: 0.75)
INFO - [DRY RUN] Would place long order
```

Check the dashboard at http://localhost:3000 to see:
- Model status (green healthy indicators)
- Recent simulated trades
- Performance metrics
- System logs

## Next Steps

1. Let the system run for a few hours in dry-run mode
2. Check data/trades.db and data/trades.csv for logged data
3. Review logs/coordinator.log for any errors
4. Once comfortable, proceed to full DOCUMENTATION.md for production setup

## Stopping the System

Mac Coordinator: Press Ctrl+C

Dashboard: Press Ctrl+C

Docker Containers:
```bash
cd docker
docker-compose down
```

VM Model Server:
```bash
ssh ubuntu@192.168.1.100
pkill -f "python server.py"
```

## Troubleshooting Quick Fixes

Cannot connect to model server:
```bash
# Verify server is running
curl http://192.168.1.100:8000/health

# Check VM firewall
ssh ubuntu@192.168.1.100 "sudo ufw status"
```

Binance API errors:
```bash
# Verify keys are set
echo $BINANCE_TESTNET_API_KEY

# Test API directly
curl -H "X-MBX-APIKEY: $BINANCE_TESTNET_API_KEY" https://testnet.binancefuture.com/fapi/v1/time
```

Python package errors:
```bash
# Reinstall in virtual environment
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

Dashboard won't start:
```bash
cd dashboard
rm -rf node_modules package-lock.json
npm install
npm run dev
```

## Getting Help

For detailed setup instructions see DOCUMENTATION.md

For VM setup see VM_SETUP.md

For testing see ci/run_tests.sh
