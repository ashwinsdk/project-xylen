# Docker Deployment for TradeProject

This directory contains Docker configurations for running model servers as containers instead of VMs.

## Advantages of Docker Deployment

- Faster setup than full VMs
- Easier to replicate and deploy
- Lower resource overhead
- Simpler backup and restore
- Works on Mac, Windows, and Linux hosts

## Prerequisites

Install Docker Desktop:
- Mac: https://docs.docker.com/desktop/install/mac-install/
- Windows: https://docs.docker.com/desktop/install/windows-install/

## Quick Start

Build and start all four model servers:

```bash
docker-compose up -d
```

This creates four containers listening on:
- model_server_1: localhost:8001
- model_server_2: localhost:8002
- model_server_3: localhost:8003
- model_server_4: localhost:8004

Check status:

```bash
docker-compose ps
```

View logs:

```bash
docker-compose logs -f model_server_1
```

## Deploying Your Models

Create directories for each server's models:

```bash
mkdir -p models_vm1 models_vm2 models_vm3 models_vm4
```

Copy your model files:

```bash
cp /path/to/your/model.onnx models_vm1/
cp /path/to/your/model.onnx models_vm2/
```

Restart containers to load new models:

```bash
docker-compose restart
```

## Configuration

Each container is limited to 12 GB RAM and 2 CPUs to match VM specifications.

To adjust resources, edit docker-compose.yml:

```yaml
mem_limit: 12g
cpus: 2
```

## Connecting Mac Coordinator

Update config.yaml with Docker container endpoints:

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

If running coordinator on a different machine, replace localhost with the Docker host IP.

## Managing Containers

Start all containers:
```bash
docker-compose up -d
```

Stop all containers:
```bash
docker-compose down
```

Restart a specific container:
```bash
docker-compose restart model_server_1
```

View container logs:
```bash
docker-compose logs -f model_server_1
```

Execute command in container:
```bash
docker exec -it trading_model_1 bash
```

## Health Checks

Test individual containers:

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
```

## Persisting Training Data

Training data is stored in volumes mapped to local directories:
- models_vm1/
- training_data_vm1/
- models_vm2/
- training_data_vm2/
- etc.

These directories persist between container restarts.

## Backing Up Container Data

Backup all model and training data:

```bash
tar czf docker_backup_$(date +%Y%m%d).tar.gz models_vm* training_data_vm*
```

Restore from backup:

```bash
tar xzf docker_backup_20240101.tar.gz
docker-compose restart
```

## Building Custom Images

Build a single image:

```bash
docker build -f Dockerfile.model_server -t trading-model-server:latest ..
```

Build all images via compose:

```bash
docker-compose build
```

## Resource Monitoring

Monitor container resources:

```bash
docker stats
```

Check container memory usage:

```bash
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

## Scaling Beyond 4 Containers

To add more model servers, copy a service block in docker-compose.yml:

```yaml
  model_server_5:
    build:
      context: ..
      dockerfile: docker/Dockerfile.model_server
    container_name: trading_model_5
    ports:
      - "8005:8000"
    volumes:
      - ./models_vm5:/opt/trading_model/models
      - ./training_data_vm5:/opt/trading_model/training_data
    environment:
      - MODEL_PATH=/opt/trading_model/models/model.onnx
    restart: unless-stopped
    mem_limit: 12g
    cpus: 2
```

Then create the volume directory and start:

```bash
mkdir -p models_vm5 training_data_vm5
docker-compose up -d model_server_5
```

## Troubleshooting

Container won't start:
```bash
docker-compose logs model_server_1
docker inspect trading_model_1
```

Port already in use:
```bash
lsof -i :8001
# Change port in docker-compose.yml
```

Out of memory:
```bash
# Check Docker Desktop settings
# Increase available RAM to Docker
# Or reduce mem_limit in docker-compose.yml
```

Container crashes on model load:
```bash
# Check model file exists
ls -lh models_vm1/
# Check container logs
docker logs trading_model_1
# Verify model format matches MODEL_TYPE environment variable
```

## Docker vs VMs

Docker Advantages:
- Faster startup
- Lower resource overhead
- Easier management
- Better for development

VM Advantages:
- Complete isolation
- Can run on separate physical hosts
- More suitable for production
- Easier network configuration for remote access

For production deployment across multiple physical hosts, VMs are recommended. For development and testing on a single machine, Docker is more convenient.
