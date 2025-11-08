# Project Xylen - Trading Coordinator Dockerfile
# Python 3.10.12 production deployment

FROM python:3.10.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py ./
COPY tests/ ./tests/

# Create data directories
RUN mkdir -p /app/data/feature_store /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose Prometheus metrics port
EXPOSE 9090

# Expose WebSocket port
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:9090/metrics || exit 1

# Run coordinator
CMD ["python", "coordinator.py"]
