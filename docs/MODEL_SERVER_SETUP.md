# Model Server Setup Guide

Complete setup guide for deploying the Project Xylen model server on Linux, macOS, or as Docker containers. This guide covers both traditional installation and Docker-based deployment for scalable, production-ready environments.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Option A: Traditional Installation](#option-a-traditional-installation)
4. [Option B: Docker Deployment](#option-b-docker-deployment)
5. [Configuration](#configuration)
6. [Service Management](#service-management)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The model server provides:
- FastAPI-based prediction endpoint
- Real-time market data collection from Binance
- Continuous model training with hot-swapping
- Health monitoring and metrics

Components:
- `server.py` - Main FastAPI application
- `model_loader_optimized.py` - Model inference engine
- `retrain_optimized.py` - Online learning manager
- `continuous_trainer.py` - Background training service
- `data_collector.py` - Market data collection daemon

---

## Prerequisites

### For Traditional Installation

**Linux (Ubuntu 22.04 LTS recommended):**
- Python 3.10.12
- 8GB+ RAM (10GB+ recommended)
- 50GB+ available disk space

**macOS (Monterey or later):**
- Python 3.10.12
- 8GB+ RAM
- 50GB+ available disk space
- Homebrew package manager

### For Docker Deployment

- Docker Engine 20.10+
- Docker Compose 2.0+ (optional but recommended)
- 8GB+ RAM per container
- 20GB+ available disk space per container

---

## Option A: Traditional Installation

### Linux Setup (Ubuntu 22.04 LTS)

#### 1. Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip build-essential
```

#### 2. Create Installation Directory

```bash
sudo mkdir -p /opt/trading_model
sudo mkdir -p /opt/trading_model/logs
sudo mkdir -p /opt/trading_model/models
sudo mkdir -p /opt/trading_model/training_data
sudo chown -R $USER:$USER /opt/trading_model
```

#### 3. Copy Model Server Files

```bash
cd /opt/trading_model
# Copy files from your repository
cp /path/to/project-xylen/model_server/*.py .
cp /path/to/project-xylen/model_server/requirements.txt .
cp /path/to/project-xylen/model_server/models.env.example models.env
```

#### 4. Setup Python Virtual Environment

```bash
cd /opt/trading_model
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 5. Configure Environment Variables

```bash
nano models.env
```

Update these critical settings:
```bash
# Model Configuration
MODEL_PATH=/opt/trading_model/models/trading_model.txt
MODEL_TYPE=lightgbm

# Server Configuration
PORT=8000
HOST=0.0.0.0

# Training Data
TRAINING_DATA_PATH=/opt/trading_model/training_data/live_samples.jsonl

# Data Collection
COLLECTION_INTERVAL=60
LOOKBACK_PERIODS=100

# Training Settings
TRAINING_INTERVAL=1800
MIN_SAMPLES_FOR_RETRAIN=100
TRAINING_BATCH_SIZE=1000

# LightGBM Settings (adjust for your RAM)
LGBM_MAX_MEMORY_GB=7.2
LGBM_NUM_THREADS=6
LGBM_MAX_BIN=511

# Logging
LOG_LEVEL=INFO
```

#### 6. Add Your Model File

Place your trained model in the models directory:
```bash
cp /path/to/your/model.txt /opt/trading_model/models/trading_model.txt
```

#### 7. Install as System Services

```bash
# Copy service files
sudo cp /path/to/project-xylen/model_server/linux_services/*.service /etc/systemd/system/

# Update WorkingDirectory in service files if needed
sudo nano /etc/systemd/system/model_server.service
sudo nano /etc/systemd/system/data_collector.service
sudo nano /etc/systemd/system/continuous_trainer.service

# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable model_server.service
sudo systemctl enable data_collector.service
sudo systemctl enable continuous_trainer.service

# Start services
sudo systemctl start model_server.service
sudo systemctl start data_collector.service
sudo systemctl start continuous_trainer.service
```

#### 8. Verify Installation

```bash
# Check service status
sudo systemctl status model_server.service

# Test health endpoint
curl http://localhost:8000/health

# View logs
sudo journalctl -u model_server -f
```

### macOS Setup

#### 1. Install Homebrew (if not installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. Install Python 3.10

```bash
brew install python@3.10
```

#### 3. Run Installation Script

```bash
cd /path/to/project-xylen/model_server/mac_services
sudo ./install.sh
```

This script automatically:
- Creates `/usr/local/opt/trading_model` directory
- Copies all necessary files
- Sets up Python virtual environment
- Installs dependencies
- Configures LaunchDaemons

#### 4. Configure Environment

```bash
sudo nano /usr/local/opt/trading_model/models.env
```

Update the same settings as Linux (adjust paths for macOS).

#### 5. Add Your Model

```bash
sudo cp /path/to/your/model.txt /usr/local/opt/trading_model/models/trading_model.txt
```

#### 6. Start Services

```bash
sudo launchctl load /Library/LaunchDaemons/com.projectxylen.modelserver.plist
sudo launchctl load /Library/LaunchDaemons/com.projectxylen.datacollector.plist
sudo launchctl load /Library/LaunchDaemons/com.projectxylen.continuoustrainer.plist
```

#### 7. Verify Installation

```bash
# Check services
sudo launchctl list | grep projectxylen

# Test health endpoint
curl http://localhost:8000/health

# View logs
tail -f /usr/local/opt/trading_model/logs/model_server.log
```

---

## Option B: Docker Deployment

Docker deployment ensures consistent environments across all platforms and simplifies scaling to multiple devices.

### 1. Create Dockerfile

Create `Dockerfile` in the `model_server` directory:

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

### 2. Create Docker Compose Configuration

Create `docker-compose.yml` in the `model_server` directory:

```yaml
version: '3.8'

services:
  model_server:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: projectxylen_model_server
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - MODEL_PATH=/app/models/trading_model.txt
      - MODEL_TYPE=lightgbm
      - PORT=8000
      - HOST=0.0.0.0
      - TRAINING_DATA_PATH=/app/training_data/live_samples.jsonl
      - COLLECTION_INTERVAL=60
      - LOOKBACK_PERIODS=100
      - TRAINING_INTERVAL=1800
      - MIN_SAMPLES_FOR_RETRAIN=100
      - TRAINING_BATCH_SIZE=1000
      - LGBM_MAX_MEMORY_GB=${LGBM_MAX_MEMORY_GB:-7.2}
      - LGBM_NUM_THREADS=${LGBM_NUM_THREADS:-6}
      - LGBM_MAX_BIN=${LGBM_MAX_BIN:-511}
      - LOG_LEVEL=INFO
    volumes:
      - ./models:/app/models
      - ./training_data:/app/training_data
      - ./logs:/app/logs
    mem_limit: ${MEM_LIMIT:-8g}
    cpus: ${CPU_LIMIT:-4.0}
    networks:
      - projectxylen_network

  data_collector:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: projectxylen_data_collector
    restart: unless-stopped
    command: python data_collector.py
    environment:
      - TRAINING_DATA_PATH=/app/training_data/live_samples.jsonl
      - COLLECTION_INTERVAL=60
      - LOOKBACK_PERIODS=100
      - LOG_LEVEL=INFO
    volumes:
      - ./training_data:/app/training_data
      - ./logs:/app/logs
    mem_limit: ${MEM_LIMIT_COLLECTOR:-2g}
    cpus: ${CPU_LIMIT_COLLECTOR:-1.0}
    networks:
      - projectxylen_network
    depends_on:
      - model_server

  continuous_trainer:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: projectxylen_continuous_trainer
    restart: unless-stopped
    command: python continuous_trainer.py
    environment:
      - MODEL_PATH=/app/models/trading_model.txt
      - MODEL_TYPE=lightgbm
      - TRAINING_DATA_PATH=/app/training_data/live_samples.jsonl
      - TRAINING_INTERVAL=1800
      - MIN_SAMPLES_FOR_RETRAIN=100
      - TRAINING_BATCH_SIZE=1000
      - LGBM_MAX_MEMORY_GB=${LGBM_MAX_MEMORY_GB:-7.2}
      - LGBM_NUM_THREADS=${LGBM_NUM_THREADS:-6}
      - LGBM_MAX_BIN=${LGBM_MAX_BIN:-511}
      - LOG_LEVEL=INFO
    volumes:
      - ./models:/app/models
      - ./training_data:/app/training_data
      - ./logs:/app/logs
    mem_limit: ${MEM_LIMIT_TRAINER:-6g}
    cpus: ${CPU_LIMIT_TRAINER:-4.0}
    networks:
      - projectxylen_network
    depends_on:
      - model_server

networks:
  projectxylen_network:
    driver: bridge
```

### 3. Create Environment Configuration

Create `.env` file for Docker Compose customization:

```bash
# Resource Limits (adjust based on your system)
MEM_LIMIT=8g
CPU_LIMIT=4.0
MEM_LIMIT_COLLECTOR=2g
CPU_LIMIT_COLLECTOR=1.0
MEM_LIMIT_TRAINER=6g
CPU_LIMIT_TRAINER=4.0

# LightGBM Configuration
LGBM_MAX_MEMORY_GB=7.2
LGBM_NUM_THREADS=6
LGBM_MAX_BIN=511
```

### 4. Build and Run

```bash
cd /path/to/project-xylen/model_server

# Build the image
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f model_server

# Check status
docker-compose ps
```

### 5. Verify Docker Deployment

```bash
# Test health endpoint
curl http://localhost:8000/health

# Check container logs
docker logs projectxylen_model_server

# Check resource usage
docker stats
```

### 6. Scaling with Docker

To deploy on multiple machines:

```bash
# On each machine, pull the image
docker-compose pull

# Or build locally
docker-compose build

# Start with custom port (if needed)
PORT=8001 docker-compose up -d

# Coordinator config.yaml should reference each machine's IP and port
```

### Docker Production Best Practices

1. **Use Docker Registry**: Push images to a private registry
   ```bash
   docker tag projectxylen_model_server:latest registry.example.com/projectxylen:latest
   docker push registry.example.com/projectxylen:latest
   ```

2. **Version Your Images**: Use semantic versioning
   ```bash
   docker build -t projectxylen_model_server:1.0.0 .
   ```

3. **Persistent Volumes**: Use named volumes for important data
   ```yaml
   volumes:
     models_data:
       driver: local
   ```

4. **Resource Monitoring**: Use Prometheus and Grafana for metrics

5. **Automated Updates**: Use Watchtower or similar tools
   ```bash
   docker run -d \
     --name watchtower \
     -v /var/run/docker.sock:/var/run/docker.sock \
     containrrr/watchtower \
     projectxylen_model_server
   ```

---

## Configuration

### Environment Variables

All configuration is done through `models.env` file or Docker environment variables.

#### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PATH` | `/app/models/trading_model.txt` | Path to model file |
| `MODEL_TYPE` | `lightgbm` | Model type (lightgbm, onnx, pytorch) |
| `PORT` | `8000` | Server port |
| `HOST` | `0.0.0.0` | Server host |

#### Training Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `TRAINING_DATA_PATH` | `/app/training_data/live_samples.jsonl` | Training data location |
| `COLLECTION_INTERVAL` | `60` | Data collection interval (seconds) |
| `TRAINING_INTERVAL` | `1800` | Training check interval (seconds) |
| `MIN_SAMPLES_FOR_RETRAIN` | `100` | Minimum samples before retraining |
| `TRAINING_BATCH_SIZE` | `1000` | Max samples per training batch |

#### LightGBM Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LGBM_MAX_MEMORY_GB` | `7.2` | Maximum memory for LightGBM (GB) |
| `LGBM_NUM_THREADS` | `6` | Number of threads |
| `LGBM_MAX_BIN` | `511` | Maximum bins for histogram |

#### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Adjusting for Different RAM Configurations

**For 8GB RAM systems:**
```bash
LGBM_MAX_MEMORY_GB=6.5
LGBM_NUM_THREADS=4
LGBM_MAX_BIN=383
```

**For 16GB RAM systems:**
```bash
LGBM_MAX_MEMORY_GB=14.0
LGBM_NUM_THREADS=8
LGBM_MAX_BIN=511
```

**For 32GB+ RAM systems:**
```bash
LGBM_MAX_MEMORY_GB=28.0
LGBM_NUM_THREADS=16
LGBM_MAX_BIN=1023
```

---

## Service Management

### Linux (systemd)

```bash
# Start services
sudo systemctl start model_server
sudo systemctl start data_collector
sudo systemctl start continuous_trainer

# Stop services
sudo systemctl stop model_server
sudo systemctl stop data_collector
sudo systemctl stop continuous_trainer

# Restart services
sudo systemctl restart model_server

# Check status
sudo systemctl status model_server

# View logs
sudo journalctl -u model_server -f
sudo journalctl -u data_collector -f
sudo journalctl -u continuous_trainer -f

# Enable/disable autostart
sudo systemctl enable model_server
sudo systemctl disable model_server
```

### macOS (launchd)

```bash
# Start services
sudo launchctl load /Library/LaunchDaemons/com.projectxylen.modelserver.plist
sudo launchctl load /Library/LaunchDaemons/com.projectxylen.datacollector.plist
sudo launchctl load /Library/LaunchDaemons/com.projectxylen.continuoustrainer.plist

# Stop services
sudo launchctl unload /Library/LaunchDaemons/com.projectxylen.modelserver.plist
sudo launchctl unload /Library/LaunchDaemons/com.projectxylen.datacollector.plist
sudo launchctl unload /Library/LaunchDaemons/com.projectxylen.continuoustrainer.plist

# Check status
sudo launchctl list | grep projectxylen

# View logs
tail -f /usr/local/opt/trading_model/logs/model_server.log
tail -f /usr/local/opt/trading_model/logs/data_collector.log
tail -f /usr/local/opt/trading_model/logs/continuous_trainer.log
```

### Docker

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart model_server

# View logs
docker-compose logs -f model_server
docker-compose logs -f data_collector
docker-compose logs -f continuous_trainer

# Check status
docker-compose ps

# Update and restart
docker-compose pull
docker-compose up -d
```

---

## Troubleshooting

### Common Issues

#### Port Already in Use

**Symptom**: Server fails to start with "Address already in use" error

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000
# or
netstat -tulpn | grep 8000

# Kill the process
kill -9 <PID>

# Or change port in models.env
PORT=8001
```

#### Model File Not Found

**Symptom**: "Model file not found" error in logs

**Solution**:
```bash
# Check model file exists
ls -la /opt/trading_model/models/

# Verify MODEL_PATH in models.env
cat /opt/trading_model/models.env | grep MODEL_PATH

# Copy your model file
cp /path/to/model.txt /opt/trading_model/models/trading_model.txt
```

#### Out of Memory Errors

**Symptom**: Service crashes with memory errors

**Solution**:
```bash
# Check available memory
free -h

# Reduce memory settings in models.env
LGBM_MAX_MEMORY_GB=4.0
TRAINING_BATCH_SIZE=500

# Restart services
sudo systemctl restart model_server continuous_trainer
```

#### Python Package Errors

**Symptom**: Import errors or missing dependencies

**Solution**:
```bash
# Reinstall dependencies
cd /opt/trading_model
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall

# Restart services
sudo systemctl restart model_server
```

#### Docker Container Exits Immediately

**Symptom**: Container starts but exits immediately

**Solution**:
```bash
# Check container logs
docker logs projectxylen_model_server

# Run container in interactive mode for debugging
docker run -it --rm projectxylen_model_server /bin/bash

# Check environment variables
docker-compose config
```

### Performance Optimization

#### Slow Inference

```bash
# Use ONNX for faster inference
MODEL_TYPE=onnx

# Increase threads
LGBM_NUM_THREADS=8

# Enable CPU optimizations (Linux)
export OMP_NUM_THREADS=8
```

#### High Memory Usage

```bash
# Reduce batch size
TRAINING_BATCH_SIZE=500

# Lower memory limit
LGBM_MAX_MEMORY_GB=4.0

# Increase training interval
TRAINING_INTERVAL=3600
```

#### Disk Space Issues

```bash
# Check disk usage
df -h

# Clean old training data
find /opt/trading_model/training_data -name "*.jsonl" -mtime +30 -delete

# Clean old model versions
find /opt/trading_model/models -name "*.txt.backup" -delete

# Rotate logs
sudo journalctl --vacuum-time=7d
```

### Health Checks

```bash
# Test health endpoint
curl http://localhost:8000/health | jq

# Expected response:
{
  "status": "healthy",
  "uptime_seconds": 12345.67,
  "memory_usage_mb": 2048.5,
  "model_loaded": true,
  "model_type": "lightgbm"
}

# Test prediction endpoint
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "timeframe": "5m",
    "candles": [],
    "indicators": {},
    "meta": {}
  }' | jq
```

### Monitoring

#### System Resources

```bash
# Linux
htop
iotop
vmstat 1

# macOS
top -o cpu
fs_usage

# Docker
docker stats
```

#### Service Logs

```bash
# Linux
sudo journalctl -u model_server --since "1 hour ago"
sudo journalctl -u model_server --follow --lines=100

# macOS
tail -f /usr/local/opt/trading_model/logs/model_server.log

# Docker
docker-compose logs --tail=100 --follow model_server
```

#### Data Collection

```bash
# Check training data growth
du -sh /opt/trading_model/training_data/

# Count samples
wc -l /opt/trading_model/training_data/live_samples.jsonl

# View latest samples
tail /opt/trading_model/training_data/live_samples.jsonl | jq
```

---

## Production Deployment Checklist

Before deploying to production:

- [ ] Model file is present and tested
- [ ] Environment variables are configured
- [ ] Services start successfully
- [ ] Health endpoint responds correctly
- [ ] Prediction endpoint returns valid results
- [ ] Logs are being written
- [ ] Training data is being collected
- [ ] Disk space monitoring is set up
- [ ] Backups are configured
- [ ] Firewall rules are configured (allow port 8000)
- [ ] Services are enabled to start on boot
- [ ] Resource limits are appropriate
- [ ] Documentation is updated

---

## Security Considerations

1. **Network Security**
   - Run behind a firewall
   - Use VPN for remote access
   - Consider adding authentication to API endpoints

2. **File Permissions**
   ```bash
   # Linux
   chmod 700 /opt/trading_model
   chmod 600 /opt/trading_model/models.env
   
   # macOS
   sudo chmod 700 /usr/local/opt/trading_model
   sudo chmod 600 /usr/local/opt/trading_model/models.env
   ```

3. **Docker Security**
   - Run containers as non-root user
   - Use read-only file systems where possible
   - Scan images for vulnerabilities

4. **Regular Updates**
   - Keep Python packages updated
   - Update base OS regularly
   - Monitor for security advisories

---

## Next Steps

After successful installation:

1. Test the model server with the coordinator
2. Monitor logs for the first 24 hours
3. Verify training data collection
4. Check model retraining triggers correctly
5. Document any custom configurations
6. Set up monitoring and alerting
7. Configure automated backups

For coordinator setup and integration, see the main project README.md.
