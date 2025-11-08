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

# Set default port (can be overridden by docker-compose)
ENV PORT=8000

# Expose port
EXPOSE 8000

# Health check (use PORT variable)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run server
CMD ["python", "server.py"]
