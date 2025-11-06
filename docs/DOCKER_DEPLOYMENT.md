# Project Xylen - Docker Deployment Guide

## Quick Start

1. **Setup Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Binance API credentials
   ```

2. **Build and Start**
   ```bash
   ./docker-manage.sh build
   ./docker-manage.sh start
   ```

3. **Check Status**
   ```bash
   ./docker-manage.sh health
   ```

## Architecture

The system runs 6 containers:
- **coordinator**: Main trading engine (ports 9090, 8765)
- **model-server-1-4**: 4 ML model servers (ports 8001-8004)
- **prometheus**: Metrics collection (port 9091)
- **grafana**: Dashboards (port 3000)

## Services

| Service | Port | Purpose |
|---------|------|---------|
| Coordinator Metrics | 9090 | Prometheus metrics |
| WebSocket | 8765 | Real-time dashboard updates |
| Model Server 1 | 8001 | ML inference |
| Model Server 2 | 8002 | ML inference |
| Model Server 3 | 8003 | ML inference |
| Model Server 4 | 8004 | ML inference |
| Prometheus | 9091 | Metrics aggregation |
| Grafana | 3000 | Dashboards |

## Volume Mounts

- `./data` → Shared SQLite database, feature store
- `./logs/coordinator` → Coordinator logs
- `./logs/model_N` → Model server logs
- `./models/model_N` → Model files (ONNX/LightGBM)
- `./config.yaml` → Configuration (read-only)

## Management Commands

```bash
# Start system
./docker-manage.sh start

# View logs
./docker-manage.sh logs
./docker-manage.sh logs coordinator

# Check health
./docker-manage.sh health

# Restart
./docker-manage.sh restart

# Stop
./docker-manage.sh stop

# Clean up
./docker-manage.sh clean
```

## Monitoring

- **Prometheus**: http://localhost:9091
- **Grafana**: http://localhost:3000 (admin/admin)
- **Coordinator Metrics**: http://localhost:9090/metrics

## Health Checks

Each service has automatic health checks:
- Coordinator: 30s interval, checks metrics endpoint
- Model Servers: 30s interval, checks /health endpoint
- Start period: 40-60s to allow initialization

Unhealthy containers automatically restart.

## Networking

All services run on `xylen-network` bridge network:
- Services communicate by container name
- coordinator → model-server-1:8001
- prometheus → coordinator:9090

## Data Persistence

Persistent volumes:
- `prometheus-data`: Metrics history
- `grafana-data`: Dashboard configs
- Host mounts for logs and models

## Troubleshooting

**Container won't start:**
```bash
docker-compose logs coordinator
```

**Check connectivity:**
```bash
docker-compose exec coordinator ping model-server-1
```

**Reset everything:**
```bash
./docker-manage.sh clean
./docker-manage.sh build
./docker-manage.sh start
```

**View resource usage:**
```bash
docker stats
```

## Production Deployment

1. Use production config.yaml
2. Set testnet=false
3. Configure alerts in Prometheus
4. Setup Nginx reverse proxy
5. Enable SSL/TLS
6. Configure backup scripts
7. Set up log rotation

## Security Notes

- API keys in .env (never commit!)
- Container runs as non-root (TODO)
- Network isolation with bridge
- Read-only mounts where possible
- Health checks prevent zombie containers
