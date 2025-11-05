# Project Xylen Model Server v0.0.1-alpha

## Release Information

**Version:** v0.0.1-alpha  
**Release Date:** November 5, 2025  
**Status:** Alpha Release  
**License:** Proprietary - See LICENSE file

## Overview

Initial alpha release of the Project Xylen Model Server, a production-ready FastAPI-based inference server designed for distributed AI trading systems. This release provides core functionality for model serving, continuous training, and market data collection.

## Package Contents

This release includes the complete model server implementation with support for multiple deployment platforms:

### Core Components

- **server.py** - FastAPI application with /predict, /retrain, and /health endpoints
- **model_loader_optimized.py** - Optimized model inference engine supporting LightGBM, ONNX, and PyTorch
- **continuous_trainer.py** - Background service for continuous model training and hot-swapping
- **data_collector.py** - Market data collection daemon for Binance integration
- **retrain_optimized.py** - Online learning manager with memory-efficient training
- **requirements.txt** - Python dependencies specification
- **models.env.example** - Environment configuration template

### Platform Support

**Linux Services** (linux_services/):
- model_server.service
- data_collector.service
- continuous_trainer.service

**macOS Services** (mac_services/):
- com.projectxylen.modelserver.plist
- com.projectxylen.datacollector.plist
- com.projectxylen.continuoustrainer.plist
- install.sh (automated installation script)
- README.md (service management guide)

**Docker Deployment**:
- Dockerfile (Python 3.10.12-slim base)
- docker-compose.yml (multi-container orchestration)
- .env (resource configuration template)

### Initial Training Scripts

Training scripts for various hardware configurations (initial_model_training_scripts/):
- train_lightgbm_m1.py - Optimized for Apple M1 chips
- train_lightgbm_m4.py - Optimized for Apple M4 chips  
- train_lightgbm_7GB.py - For 8GB RAM systems
- train_lightgbm_10gb.py - For 16GB+ RAM systems

## Key Features

### Model Inference
- Multi-format support: LightGBM, ONNX, PyTorch
- Hot-swapping for zero-downtime model updates
- Concurrent request handling with async operations
- Health monitoring with resource usage metrics

### Continuous Learning
- Automated retraining based on new market data
- Configurable sample thresholds and batch sizes
- Memory-efficient training pipeline
- Automatic model versioning and backup

### Data Collection
- Real-time market data fetching from Binance
- Configurable collection intervals and lookback periods
- JSONL format for efficient storage and streaming
- Automatic feature engineering pipeline

### Production Ready
- Systemd service files for Linux
- LaunchDaemon plists for macOS
- Docker containerization with resource limits
- Comprehensive logging and error handling
- Graceful shutdown and signal handling

## System Requirements

### Minimum Requirements
- Python 3.10.12
- 8GB RAM
- 50GB available disk space
- Ubuntu 22.04 LTS / macOS Monterey+ / Docker 20.10+

### Recommended Configuration
- 10GB+ RAM
- Multi-core CPU (4+ cores)
- SSD storage
- Stable network connection

## Installation

### Quick Start (Linux)

```bash
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip build-essential
sudo mkdir -p /opt/trading_model/{logs,models,training_data}
cd /opt/trading_model
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp models.env.example models.env
nano models.env
```

### Quick Start (macOS)

```bash
cd mac_services
sudo ./install.sh
```

### Quick Start (Docker)

```bash
docker-compose build
docker-compose up -d
```

For detailed installation instructions, refer to the included documentation.

## Configuration

### Essential Environment Variables

```bash
MODEL_PATH=/opt/trading_model/models/trading_model.txt
MODEL_TYPE=lightgbm
PORT=8000
HOST=0.0.0.0
LGBM_MAX_MEMORY_GB=7.2
LGBM_NUM_THREADS=6
TRAINING_INTERVAL=1800
```

### Resource Optimization

Pre-configured profiles for different hardware:
- 8GB RAM: LGBM_MAX_MEMORY_GB=6.5, LGBM_NUM_THREADS=4
- 16GB RAM: LGBM_MAX_MEMORY_GB=14.0, LGBM_NUM_THREADS=8
- 32GB+ RAM: LGBM_MAX_MEMORY_GB=28.0, LGBM_NUM_THREADS=16

## API Endpoints

### POST /predict
Perform model inference on market data.

**Request:**
```json
{
  "symbol": "BTCUSDT",
  "timeframe": "5m",
  "candles": [],
  "indicators": {},
  "meta": {}
}
```

**Response:**
```json
{
  "prediction": 1,
  "confidence": 0.85,
  "model_version": "20250105_120000"
}
```

### POST /retrain
Trigger manual model retraining.

**Response:**
```json
{
  "status": "success",
  "message": "Retraining completed",
  "samples_used": 1500
}
```

### GET /health
Health check endpoint with resource metrics.

**Response:**
```json
{
  "status": "healthy",
  "uptime_seconds": 12345.67,
  "memory_usage_mb": 2048.5,
  "model_loaded": true,
  "model_type": "lightgbm"
}
```

## Known Limitations

This is an alpha release with the following known limitations:

1. **Model Format Support:** While LightGBM, ONNX, and PyTorch are supported, only LightGBM has been extensively tested in production
2. **Data Collection:** Currently limited to Binance exchange only
3. **Persistence:** Training data stored in JSONL format may require periodic cleanup for long-running deployments
4. **Monitoring:** Basic health metrics provided; external monitoring tools recommended for production
5. **Authentication:** No built-in authentication; should be deployed behind a firewall or VPN

## Breaking Changes

As this is the first alpha release, no breaking changes apply. Future releases may introduce breaking changes to configuration format, API endpoints, or deployment structure.

## Security Considerations

1. Deploy behind a firewall or VPN for remote access
2. Secure models.env file with appropriate permissions (chmod 600)
3. Do not expose port 8000 publicly without authentication
4. Regularly update Python dependencies for security patches
5. Use Docker secrets or environment variables for sensitive configuration

## Performance Notes

Benchmark results on reference hardware (Ubuntu 22.04, 8GB RAM, 4-core CPU):
- Average inference latency: 15-25ms
- Concurrent request handling: 50+ requests/second
- Memory footprint: 1.5-2GB per model server instance
- Training cycle: 2-5 minutes for 1000 samples

## Migration and Compatibility

This release is compatible with:
- Project Xylen Coordinator v1.0+
- Python 3.10.12 (required)
- FastAPI 0.104.0+
- LightGBM 4.1.0+

## Support and Feedback

This is proprietary software. For support inquiries:
- Review included documentation
- Check logs for error messages
- Contact: Through authorized channels only

## Roadmap

Future releases may include:
- Multi-exchange support (Coinbase, Kraken, Bybit)
- Advanced monitoring and metrics (Prometheus integration)
- Authentication and authorization layer
- Model ensemble serving within single server instance
- GPU acceleration for inference
- Advanced feature engineering pipeline
- WebSocket support for real-time predictions

## License and Legal

This software is proprietary and confidential. See LICENSE file for complete terms.

**IMPORTANT:** Trading cryptocurrencies involves substantial risk of loss. This software is provided for educational and research purposes. You are solely responsible for all trading decisions and financial outcomes. Never trade with funds you cannot afford to lose.

## Acknowledgments

Built with:
- FastAPI - Modern web framework
- LightGBM - Gradient boosting framework
- ONNX Runtime - Cross-platform inference
- PyTorch - Deep learning framework
- Uvicorn - ASGI server implementation

## Verification

**Package:** model_server_v0.0.1-alpha.zip  
**Release Date:** November 5, 2025  
**Maintainer:** Ashwin Sudhakar  

For licensing inquiries or permission requests, contact the copyright holder through official channels.

---

**This is alpha software. Use in production environments at your own risk. Always test thoroughly in a testnet environment before deploying with real funds.**
