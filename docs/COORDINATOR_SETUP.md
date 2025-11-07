# Coordinator Setup

## Installation

### Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- Binance Futures API credentials (testnet or mainnet)
- 2GB RAM minimum for coordinator
- Telegram bot (optional, for alerts)

### Quick Start

1. Clone repository
2. Copy configuration template:
```bash
cp config.yaml.example config.yaml
```

3. Create environment file:
```bash
cat > .env << EOF
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_api_secret
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
EOF
```

4. Start services:
```bash
docker compose up -d
```

## Configuration

### Trading Parameters

```yaml
trading:
  symbol: "BTCUSDT"              # Trading pair
  leverage: 1                    # 1-125x (use 1-3x for safety)
  position_size_fraction: 0.10   # 10% of capital per trade
  max_open_positions: 1          # Limit concurrent positions
  stop_loss_percent: 0.02        # 2% stop loss
  take_profit_percent: 0.05      # 5% take profit
```

**Position Sizing Methods**:
- `fixed_fraction`: Percentage of equity (recommended)
- `kelly`: Kelly Criterion (aggressive)
- `fixed_amount`: Fixed USD amount

### Ensemble Configuration

```yaml
ensemble:
  method: "bayesian_weighted"    # or "weighted_vote", "average_confidence"
  confidence_threshold: 0.70     # Minimum confidence to trade (0-1)
  min_responding_models: 1       # Minimum models required
  weight_decay_halflife: 86400   # 24h performance decay
```

**Methods**:
- `weighted_vote`: Simple weighted majority
- `bayesian_weighted`: Advanced Bayesian aggregation (default)
- `average_confidence`: Average all predictions

### Risk Management

```yaml
safety:
  max_daily_loss_percent: 0.10       # 10% daily loss limit
  max_daily_loss_usd: 500.0          # Absolute dollar limit
  circuit_breaker_consecutive_losses: 5
  circuit_breaker_cooldown_seconds: 3600  # 1 hour
  emergency_shutdown_loss_percent: 0.20   # 20% total drawdown
```

**Circuit Breaker**:
Automatically halts trading when triggered. Requires manual restart or cooldown period.

### Timing Configuration

```yaml
timing:
  heartbeat_interval: 60         # Decision cycle (seconds)
  model_timeout: 5.0            # Per-model response timeout
  health_check_interval: 300     # Model health check (seconds)
  max_retries: 3                # Failed request retries
```

### Model Endpoints

```yaml
model_endpoints:
  - host: "model-server-1"
    port: 8001
    name: "model-1"
    weight: 1.0                  # Ensemble weight
    enabled: true
    timeout: 5.0
```

Add more endpoints to scale ensemble.

## Binance API Setup

### Testnet (Recommended First)

1. Visit https://testnet.binancefuture.com
2. Sign in with GitHub/Google
3. Generate API key and secret
4. Add to `.env` file

**Features**:
- Free test funds (10,000 USDT)
- No real money at risk
- Full API functionality
- Reset balance anytime

### Mainnet (Production)

1. Create Binance account
2. Complete KYC verification
3. Enable Futures trading
4. Generate API key with Futures permissions
5. Restrict API key to specific IP (recommended)

**Security**:
- Never share API keys
- Use IP whitelist
- Enable 2FA on Binance account
- Limit API key permissions (no withdrawal)

### API Configuration

```yaml
binance:
  testnet_base_url: "https://testnet.binancefuture.com"
  production_base_url: "https://fapi.binance.com"
  rate_limit_per_minute: 1200
  websocket_enabled: false       # Use REST for stability
```

## Telegram Alerts

### Bot Setup

1. Message @BotFather on Telegram
2. Create new bot: `/newbot`
3. Copy bot token
4. Get chat ID:
   - Message your bot
   - Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Find `"chat":{"id":123456}`

### Alert Configuration

```yaml
telegram:
  enabled: true
  alert_levels:
    - "TRADE"              # Trade open/close notifications
    - "ERROR"              # System errors
    - "CIRCUIT_BREAKER"    # Trading halted
    - "WARNING"            # Low balance, model offline
    - "DAILY_SUMMARY"      # End-of-day report
  daily_summary_time: "23:59"  # UTC time
```

## Logging

### Log Levels

```yaml
logging:
  level: "INFO"              # DEBUG, INFO, WARNING, ERROR
  format: "json"             # json or text
  file: "./logs/coordinator.log"
  max_bytes: 10485760       # 10MB per file
  backup_count: 10          # Keep 10 rotated files
```

### Component-Specific Levels

```yaml
logging:
  components:
    ensemble: "INFO"
    risk_manager: "INFO"
    binance_client: "WARNING"
    market_data: "DEBUG"
```

## Database

### SQLite Configuration

```yaml
database:
  sqlite_path: "./data/trades.db"
  enable_wal_mode: true        # Write-ahead logging
  backup_enabled: true
  backup_interval_hours: 24
  backup_retention_days: 30
```

### Backup

Manual backup:
```bash
docker exec xylen-coordinator \
    sqlite3 /app/data/trades.db ".backup /app/data/trades_backup.db"
```

Automated backups run daily and keep 30 days of history.

## Monitoring

### Dashboard

Access at: http://localhost:3000

Features:
- Real-time model health
- Live trades and P&L
- System resource usage
- Market data and indicators

### Prometheus Metrics

Access at: http://localhost:9090

Key metrics:
- `coordinator_trades_total`
- `coordinator_pnl_usd`
- `coordinator_ensemble_confidence`
- `coordinator_model_latency_seconds`

### Grafana Dashboards

Access at: http://localhost:3001

Pre-configured dashboards for:
- Trading performance
- Model health
- System resources

## Troubleshooting

### Coordinator Won't Start

Check:
1. Config file valid YAML
2. Environment variables set
3. Model servers accessible
4. Port 8765 not in use

View logs:
```bash
docker logs xylen-coordinator
```

### No Trades Executing

Reasons:
1. Models predicting "hold" (market uncertain)
2. Confidence below threshold
3. Risk checks failing
4. Circuit breaker active
5. Insufficient balance

Check logs for rejection reasons.

### Binance API Errors

Common issues:
- Invalid signature (check API secret)
- Timestamp sync (Docker time drift)
- Rate limit exceeded (reduce frequency)
- Insufficient permissions (check API key settings)

### WebSocket Disconnects

Dashboard disconnects are normal and will auto-reconnect within 5 seconds. If persistent:
- Check coordinator is running
- Verify port 8765 accessible
- Check firewall rules

## Performance Tuning

### Resource Allocation

```yaml
services:
  coordinator:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Heartbeat Optimization

Faster decisions:
```yaml
timing:
  heartbeat_interval: 30    # 30s instead of 60s
```

Trade-off: Higher API usage, more CPU.

### Concurrent Model Queries

Models queried in parallel for low latency. Adjust timeout:
```yaml
timing:
  model_timeout: 3.0       # Faster timeout for responsive models
```

## Security

### API Key Protection

- Never commit `.env` to git
- Use environment variables only
- Rotate keys periodically
- Monitor API key usage on Binance

### Network Security

- Use Docker networks for service isolation
- Expose only necessary ports
- Consider VPN for remote access
- Enable HTTPS for production dashboard

### Data Privacy

- Trade data stored locally only
- No external data transmission except Binance API
- SQLite database encrypted at rest (optional)

## Upgrades

### Update Coordinator

```bash
git pull origin main
docker compose build coordinator
docker compose up -d --force-recreate coordinator
```

### Migration

Database migrations handled automatically on startup. Backup before upgrading:

```bash
./scripts/backup_sqlite.sh
```

## Production Checklist

Before going live with real funds:

- [ ] Tested thoroughly on testnet (minimum 1 week)
- [ ] Verified all trades execute correctly
- [ ] Confirmed P&L calculations accurate
- [ ] Set conservative risk limits
- [ ] Enabled Telegram alerts
- [ ] Configured circuit breakers
- [ ] Backed up database
- [ ] Documented API keys securely
- [ ] Set up monitoring alerts
- [ ] Tested emergency shutdown
- [ ] Reviewed all configuration parameters
- [ ] Started with small position sizes
