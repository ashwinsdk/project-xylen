# Model Server Setup

## Overview

Model servers provide ML inference as independent microservices. Each server runs a LightGBM model optimized with ONNX for low-latency predictions.

## Initial Model Training

### Requirements

- Python 3.10+
- 8GB RAM minimum
- Historical market data (Binance Vision)

### Training Script

Located in `model_server/initial_model_training_scripts/`

```bash
cd model_server/initial_model_training_scripts
python train_lightgbm_m4.py
```

**Configuration**:
- `LOOKBACK_PERIODS`: Historical candles for features (default: 100)
- `FEATURES`: List of indicators to calculate
- `TRAIN_START_DATE`: Start of training data
- `TRAIN_END_DATE`: End of training data

**Output**:
- `lightgbm_model.txt`: Trained model file
- Feature importance scores
- Validation metrics (accuracy, precision, recall)

### Model Files

Place trained model in `model_server/models/`:

```
model_server/
└── models/
    └── lightgbm_model.txt
```

## Docker Deployment

### Build Image

```bash
docker compose build model-server-1
```

### Run Standalone

```bash
docker run -d \
  -p 8001:8001 \
  -v $(pwd)/model_server/models:/app/models \
  -e MODEL_NAME=model_1 \
  project-xylen-model-server
```

### Multi-Server Setup

Docker Compose automatically deploys 4 servers:

```yaml
services:
  model-server-1:
    ports: ["8001:8001"]
  model-server-2:
    ports: ["8002:8002"]
  model-server-3:
    ports: ["8003:8003"]
  model-server-4:
    ports: ["8004:8004"]
```

## Configuration

### Environment Variables

```bash
MODEL_NAME=model_1           # Model identifier
MODEL_PATH=./models/         # Model directory
ONNX_ENABLED=true           # Use ONNX optimization
LOG_LEVEL=INFO              # Logging verbosity
```

### Model Types

Supported: `lightgbm`, `xgboost`, `catboost`

**LightGBM** (recommended):
- Fast inference (5-15ms)
- Low memory footprint
- ONNX compatible
- Excellent for tabular data

## Continuous Learning

### Data Collection

Enable in `config.yaml`:

```yaml
retraining:
  enabled: true
  send_feedback_to_models: true
  feedback_delay_seconds: 3600
```

Coordinator sends trade outcomes to models via `/feedback` endpoint.

### Automatic Retraining

Triggered when:
- Minimum samples collected (configurable)
- Performance degrades below threshold
- Manual trigger via `/retrain` endpoint

**Process**:
1. Collect trade outcomes and features
2. Label outcomes (profit/loss)
3. Incremental training on new data
4. Model validation
5. Hot-swap updated model

### Data Storage

Samples stored in `model_server/data/training_samples.parquet`

Format: Parquet with Snappy compression

## Performance Optimization

### ONNX Runtime

Convert LightGBM to ONNX for faster inference:

```bash
cd model_server
python convert_to_onnx.py
```

**Benefits**:
- 2-3x faster inference
- Lower memory usage
- Hardware acceleration support

### Resource Tuning

**CPU Optimization**:
```yaml
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 256M
```

**Scaling**:
Add more model servers in `docker-compose.yml` and update `config.yaml`:

```yaml
model_endpoints:
  - host: "model-server-5"
    port: 8005
    name: "model-5"
    weight: 1.0
    enabled: true
```

## Health Monitoring

### Metrics

Access at `http://localhost:800[1-4]/metrics`:

- Prediction latency
- Memory usage
- CPU utilization
- Model version
- Training status

### Alerts

Configure Prometheus alerts for:
- High latency (>100ms)
- Memory usage >80%
- Model offline
- Training failures

## Troubleshooting

### Model Not Loading

Check:
1. Model file exists at configured path
2. File format correct (LightGBM .txt)
3. Sufficient memory available
4. Python dependencies installed

Logs: `docker logs xylen-model-1`

### High Latency

Causes:
- Large feature set (reduce indicators)
- CPU throttling (increase resources)
- Network issues (check Docker networking)

Solution: Enable ONNX, reduce features, scale horizontally

### Training Failures

Check:
- Sufficient training samples (minimum 100)
- Valid labels (not all same class)
- Feature consistency
- Memory available for training

## Distributed Deployment

### Remote Servers

Update `config.yaml` to point to remote hosts:

```yaml
model_endpoints:
  - host: "192.168.1.100"
    port: 8001
    name: "remote-model-1"
    weight: 1.0
    enabled: true
```

**Requirements**:
- Network connectivity
- Firewall rules allow coordinator access
- Docker installed on remote hosts

### Load Balancing

Use nginx or HAProxy for model server load balancing:

```nginx
upstream model_servers {
    server model-1:8001;
    server model-2:8002;
    server model-3:8003;
    server model-4:8004;
}
```

## Model Versioning

Track model versions in health endpoint:

```json
{
  "model_version": "1.0",
  "model_type": "lightgbm",
  "training_samples": 50000,
  "trained_at": "2025-11-01T00:00:00Z"
}
```

Update version on retrain for audit trail.

## Backup and Restore

### Backup Model

```bash
docker cp xylen-model-1:/app/models/lightgbm_model.txt \
    ./backups/model_1_$(date +%Y%m%d).txt
```

### Restore Model

```bash
docker cp ./backups/model_1_20251107.txt \
    xylen-model-1:/app/models/lightgbm_model.txt
docker restart xylen-model-1
```

## Advanced Configuration

### Custom Features

Edit `model_loader_optimized.py` to add custom feature engineering:

```python
def extract_features(candles, indicators):
    features = []
    # Add custom features here
    features.append(calculate_custom_indicator(candles))
    return features
```

Retrain model with new features.

### Ensemble of Ensembles

Run multiple model types (LightGBM, XGBoost) and let coordinator aggregate:

```yaml
model_endpoints:
  - name: "lightgbm-1"
    weight: 1.0
  - name: "xgboost-1"
    weight: 0.8
```

Different weights allow experimenting with model combinations.
