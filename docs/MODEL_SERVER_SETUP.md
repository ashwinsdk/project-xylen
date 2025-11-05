# Model Server Setup Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Linux Installation](#linux-installation)
3. [macOS Installation](#macos-installation)
4. [Docker Deployment](#docker-deployment)
5. [Configuration](#configuration)
6. [Service Management](#service-management)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

**Hardware Requirements:**
- 8GB RAM minimum (10GB recommended)
- 50GB available disk space
- Multi-core CPU (4+ cores recommended)

**Software Requirements:**
- Python 3.10.12
- Linux: Ubuntu 22.04 LTS or macOS Monterey+
- Docker: 20.10+ (for Docker deployment)

## Linux Installation

### Step 1: Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip build-essential
```

### Step 2: Create Installation Directory

```bash
sudo mkdir -p /opt/trading_model/{logs,models,training_data}
sudo chown -R $USER:$USER /opt/trading_model
```

### Step 3: Copy Files and Setup Environment

```bash
cd /opt/trading_model
cp /path/to/project-xylen/model_server/*.py .
cp /path/to/project-xylen/model_server/requirements.txt .
cp /path/to/project-xylen/model_server/models.env.example models.env
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment

```bash
nano models.env
```

Required settings:
```bash
MODEL_PATH=/opt/trading_model/models/trading_model.txt
MODEL_TYPE=lightgbm
PORT=8000
HOST=0.0.0.0
TRAINING_DATA_PATH=/opt/trading_model/training_data/live_samples.jsonl
COLLECTION_INTERVAL=60
LOOKBACK_PERIODS=100
TRAINING_INTERVAL=1800
MIN_SAMPLES_FOR_RETRAIN=100
TRAINING_BATCH_SIZE=1000
LGBM_MAX_MEMORY_GB=7.2
LGBM_NUM_THREADS=6
LGBM_MAX_BIN=511
LOG_LEVEL=INFO
```

### Step 5: Add Model File

```bash
cp /path/to/your/model.txt /opt/trading_model/models/trading_model.txt
```

### Step 6: Install System Services

```bash
sudo cp /path/to/project-xylen/model_server/linux_services/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable model_server data_collector continuous_trainer
sudo systemctl start model_server data_collector continuous_trainer
```

### Step 7: Verify Installation

```bash
sudo systemctl status model_server
curl http://localhost:8000/health
sudo journalctl -u model_server -f
```

## macOS Installation

### Step 1: Install Homebrew and Python

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.10
```

### Step 2: Run Installation Script

```bash
cd /path/to/project-xylen/model_server/mac_services
sudo ./install.sh
```

### Step 3: Configure Environment

```bash
sudo nano /usr/local/opt/trading_model/models.env
```

Use same configuration as Linux installation.

### Step 4: Add Model File

```bash
sudo cp /path/to/your/model.txt /usr/local/opt/trading_model/models/trading_model.txt
```

### Step 5: Start Services

```bash
sudo launchctl load /Library/LaunchDaemons/com.projectxylen.modelserver.plist
sudo launchctl load /Library/LaunchDaemons/com.projectxylen.datacollector.plist
sudo launchctl load /Library/LaunchDaemons/com.projectxylen.continuoustrainer.plist
```

### Step 6: Verify Installation

```bash
sudo launchctl list | grep projectxylen
curl http://localhost:8000/health
tail -f /usr/local/opt/trading_model/logs/model_server.log
```

## Docker Deployment

### Prerequisites

```bash
docker --version
docker-compose --version
```

### Step 1: Build Image

```bash
cd /path/to/project-xylen/model_server
docker-compose build
```

Dockerfile contents:

```dockerfile
FROM python:3.10.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY server.py .
COPY model_loader_optimized.py .
COPY retrain_optimized.py .
COPY continuous_trainer.py .
COPY data_collector.py .
COPY models.env.example .

# Create necessary directories
RUN mkdir -p /app/logs /app/models /app/training_data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run server
CMD ["python", "server.py"]
```

### Step 2: Configure Environment

Create .env file:

```bash
nano .env
```

Contents:
```bash
MEM_LIMIT=8g
CPU_LIMIT=4.0
MEM_LIMIT_COLLECTOR=2g
CPU_LIMIT_COLLECTOR=1.0
MEM_LIMIT_TRAINER=6g
CPU_LIMIT_TRAINER=4.0
LGBM_MAX_MEMORY_GB=7.2
LGBM_NUM_THREADS=6
LGBM_MAX_BIN=511
```

### Step 3: Add Model File

```bash
mkdir -p models
cp /path/to/your/model.txt models/trading_model.txt
```

### Step 4: Start Services

```bash
docker-compose up -d
```

### Step 5: Verify Deployment

```bash
docker-compose ps
docker-compose logs -f model_server
curl http://localhost:8000/health
docker stats
```

### Scaling to Multiple Machines

```bash
docker-compose pull
docker-compose up -d
```

Update coordinator config.yaml with each machine's IP:port.

## Configuration

Environment variables in models.env or Docker .env:

| Variable | Default | Description |
|----------|---------|-------------|
| MODEL_PATH | /app/models/trading_model.txt | Model file path |
| MODEL_TYPE | lightgbm | Model type |
| PORT | 8000 | Server port |
| HOST | 0.0.0.0 | Server host |
| TRAINING_DATA_PATH | /app/training_data/live_samples.jsonl | Training data path |
| COLLECTION_INTERVAL | 60 | Data collection interval (seconds) |
| TRAINING_INTERVAL | 1800 | Training interval (seconds) |
| MIN_SAMPLES_FOR_RETRAIN | 100 | Minimum samples for retraining |
| TRAINING_BATCH_SIZE | 1000 | Training batch size |
| LGBM_MAX_MEMORY_GB | 7.2 | LightGBM memory limit (GB) |
| LGBM_NUM_THREADS | 6 | LightGBM threads |
| LGBM_MAX_BIN | 511 | LightGBM max bins |
| LOG_LEVEL | INFO | Logging level |

RAM-specific configurations:

**8GB RAM:**
```bash
LGBM_MAX_MEMORY_GB=6.5
LGBM_NUM_THREADS=4
LGBM_MAX_BIN=383
```

**16GB RAM:**
```bash
LGBM_MAX_MEMORY_GB=14.0
LGBM_NUM_THREADS=8
LGBM_MAX_BIN=511
```

**32GB RAM:**
```bash
LGBM_MAX_MEMORY_GB=28.0
LGBM_NUM_THREADS=16
LGBM_MAX_BIN=1023
```

## Service Management

### Linux Commands

```bash
sudo systemctl start model_server
sudo systemctl stop model_server
sudo systemctl restart model_server
sudo systemctl status model_server
sudo journalctl -u model_server -f
sudo systemctl enable model_server
```

### macOS Commands

```bash
sudo launchctl load /Library/LaunchDaemons/com.projectxylen.modelserver.plist
sudo launchctl unload /Library/LaunchDaemons/com.projectxylen.modelserver.plist
sudo launchctl list | grep projectxylen
tail -f /usr/local/opt/trading_model/logs/model_server.log
```

### Docker Commands

```bash
docker-compose up -d
docker-compose down
docker-compose restart model_server
docker-compose logs -f model_server
docker-compose ps
docker-compose pull
```

## Troubleshooting

### Port Already in Use

```bash
lsof -i :8000
kill -9 <PID>
```

Or edit models.env:
```bash
PORT=8001
```

### Model File Not Found

```bash
ls -la /opt/trading_model/models/
cat /opt/trading_model/models.env | grep MODEL_PATH
cp /path/to/model.txt /opt/trading_model/models/trading_model.txt
```

### Out of Memory

```bash
free -h
```

Edit models.env:
```bash
LGBM_MAX_MEMORY_GB=4.0
TRAINING_BATCH_SIZE=500
```

Restart:
```bash
sudo systemctl restart model_server
```

### Package Errors

```bash
cd /opt/trading_model
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
sudo systemctl restart model_server
```

### Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "uptime_seconds": 12345.67,
  "memory_usage_mb": 2048.5,
  "model_loaded": true,
  "model_type": "lightgbm"
}
```

### Test Prediction

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTCUSDT", "timeframe": "5m", "candles": [], "indicators": {}, "meta": {}}'
```

### Log Monitoring

Linux:
```bash
sudo journalctl -u model_server --since "1 hour ago"
sudo journalctl -u model_server -f
```

macOS:
```bash
tail -f /usr/local/opt/trading_model/logs/model_server.log
```

Docker:
```bash
docker-compose logs --tail=100 -f model_server
```

### System Resources

```bash
htop
top
df -h
docker stats
```

### Data Collection Status

```bash
du -sh /opt/trading_model/training_data/
wc -l /opt/trading_model/training_data/live_samples.jsonl
```
