# Dashboard Integration Guide

The TradeProject dashboard displays real-time data from the Mac coordinator via a built-in API server.

## How It Works

1. **Mac Coordinator** runs the trading logic and collects data (trades, model health, logs)
2. **API Server** (part of coordinator) exposes HTTP endpoints with real-time data
3. **React Dashboard** fetches data from API server every 5 seconds and displays it

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────┐
│  React          │  HTTP   │  Mac Coordinator │  HTTP   │  Model VMs  │
│  Dashboard      │◄────────┤  + API Server    │◄────────┤  (1-5)      │
│  (Port 3000)    │         │  (Port 5500)     │         │             │
└─────────────────┘         └──────────────────┘         └─────────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │  SQLite + CSV   │
                            │  Data Storage   │
                            └─────────────────┘
```

## Setup Instructions

### Step 1: Enable API Server in Config

Edit `config.yaml`:

```yaml
dashboard:
  enabled: true
  port: 5500
  host: "0.0.0.0"
```

### Step 2: Start Coordinator with API Server

```bash
cd mac_coordinator
source venv/bin/activate
python coordinator.py
```

You should see:

```
INFO - Dashboard API server started at http://0.0.0.0:5500
```

### Step 3: Configure Dashboard

```bash
cd dashboard
cp .env.example .env.local
```

If coordinator is on a different machine, edit `.env.local`:

```
REACT_APP_API_URL=http://192.168.1.100:5500/api
```

### Step 4: Start Dashboard

```bash
npm install  # First time only
npm run dev
```

Open http://localhost:3000 in your browser.

## API Endpoints

The coordinator exposes these endpoints:

### GET /api/models

Returns health and performance of all model VMs.

**Response:**
```json
[
  {
    "name": "model_vm_1",
    "host": "192.168.1.100",
    "port": 8000,
    "healthy": true,
    "uptime": 0,
    "memory_mb": 0,
    "success_rate": 0.85,
    "avg_response_time": 0.12,
    "success_count": 100,
    "failure_count": 15,
    "last_success": "2024-01-01T12:00:00"
  }
]
```

### GET /api/trades?limit=50

Returns recent trades from SQLite database.

**Query Parameters:**
- `limit` (optional): Number of trades to return (default: 50)

**Response:**
```json
[
  {
    "id": 1,
    "timestamp": "2024-01-01T12:00:00",
    "symbol": "BTCUSDT",
    "side": "long",
    "entry_price": 55000.0,
    "exit_price": 50500.0,
    "quantity": 0.1,
    "pnl": 50.0,
    "pnl_percent": 1.0,
    "status": "CLOSED"
  }
]
```

### GET /api/performance

Returns aggregate performance statistics.

**Response:**
```json
{
  "total_trades": 100,
  "winning_trades": 65,
  "losing_trades": 35,
  "win_rate": 0.65,
  "total_pnl": 5500.0,
  "avg_pnl": 50.0,
  "max_win": 500.0,
  "max_loss": -200.0
}
```

### GET /api/logs?limit=100

Returns recent log entries from coordinator log file.

**Query Parameters:**
- `limit` (optional): Number of log lines to return (default: 100)

**Response:**
```json
[
  {
    "timestamp": "2024-01-01 12:00:00,123",
    "level": "INFO",
    "message": "Trade placed: LONG BTCUSDT"
  }
]
```

### GET /api/status

Returns current coordinator status.

**Response:**
```json
{
  "is_running": true,
  "dry_run": true,
  "testnet": true,
  "current_position": false,
  "daily_stats": {
    "trades": 5,
    "pnl": 250.0,
    "consecutive_losses": 0,
    "start_time": "2024-01-01T00:00:00"
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

## Testing the API

### Test from Command Line

```bash
# Health check
curl http://localhost:5500/api/status

# Get models
curl http://localhost:5500/api/models

# Get recent trades
curl http://localhost:5500/api/trades?limit=10

# Get performance
curl http://localhost:5500/api/performance

# Get logs
curl http://localhost:5500/api/logs?limit=50
```

### Test from Browser

Open these URLs in your browser:

- http://localhost:5500/api/status
- http://localhost:5500/api/models
- http://localhost:5500/api/trades
- http://localhost:5500/api/performance

## Dashboard Features

### Model Health Status

Displays real-time status of each model VM:

- Green indicator: Model responding and healthy
- Red indicator: Model offline or failing
- Response time, success rate, and request counts
- Last successful response timestamp

### Recent Trades

Shows trades from SQLite database:

- Entry and exit prices
- P&L in dollars and percentage
- Trade side (long/short)
- Status (OPEN/CLOSED)
- Timestamp

### Performance Metrics

Summary cards showing:

- Total trades executed
- Win rate percentage
- Total P&L
- Average P&L per trade

### Performance Chart

Line chart showing cumulative P&L over time using Recharts library.

### System Logs

Real-time log viewer with:

- Color-coded severity levels (INFO/WARNING/ERROR)
- Timestamp for each entry
- Auto-scrolling for latest logs

## Customization

### Change Refresh Rate

Edit `dashboard/src/App.jsx`:

```javascript
const [refreshInterval, setRefreshInterval] = useState(3000); // 3 seconds
```

### Change API Server Port

Edit `config.yaml`:

```yaml
dashboard:
  port: 8080  # Change from 5500
```

Then update `dashboard/.env.local`:

```
REACT_APP_API_URL=http://localhost:8080/api
```

### Add New Data to Dashboard

1. Add new endpoint in `mac_coordinator/api_server.py`:

```python
async def get_custom_data(self, request):
    data = {"custom": "value"}
    return web.json_response(data)

# Register route
self.app.router.add_get('/api/custom', self.get_custom_data)
```

2. Fetch in `dashboard/src/App.jsx`:

```javascript
const customRes = await fetch(`${API_BASE_URL}/custom`);
const custom = await customRes.json();
```

3. Pass to component and display

## Troubleshooting

### Dashboard Shows "Disconnected"

**Cause:** Cannot reach API server

**Solutions:**
1. Verify coordinator is running: `ps aux | grep coordinator.py`
2. Check API server started: `grep "API server started" logs/coordinator.log`
3. Test API directly: `curl http://localhost:5500/api/status`
4. Check firewall not blocking port 5500

### CORS Errors in Browser Console

**Cause:** Cross-origin request blocked

**Solutions:**
- API server already includes CORS headers
- Ensure you're using the correct API URL in `.env.local`
- Check browser console for actual error details

### Empty Data or No Trades Showing

**Cause:** No data collected yet

**Solutions:**
1. Let coordinator run for a few minutes to collect data
2. Check SQLite database exists: `ls -la mac_coordinator/data/trades.db`
3. Verify data being logged: `sqlite3 data/trades.db "SELECT COUNT(*) FROM trades;"`

### Dashboard Not Updating

**Cause:** Fetch interval too long or failed

**Solutions:**
1. Check browser console for fetch errors
2. Reduce refresh interval in App.jsx
3. Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+R)

### API Server Won't Start

**Cause:** Port already in use or permission issue

**Solutions:**
1. Check port 5500 is free: `lsof -i :5500`
2. Change port in config.yaml if needed
3. Check coordinator logs for startup errors

## Production Deployment

### Serve Dashboard as Static Files

```bash
cd dashboard
npm run build
```

Serve the `dist/` folder with:

```bash
# Option 1: Simple HTTP server
python3 -m http.server 3000 --directory dist

# Option 2: Nginx
# Copy dist/ contents to nginx web root
```

### Configure Reverse Proxy

Use nginx to proxy API requests:

```nginx
server {
    listen 80;
    
    # Serve dashboard
    location / {
        root /path/to/dashboard/dist;
        try_files $uri /index.html;
    }
    
    # Proxy API to coordinator
    location /api/ {
        proxy_pass http://localhost:5500;
        proxy_set_header Host $host;
    }
}
```

### Security Considerations

**For development:** API server has no authentication (as specified for internal APIs)

**For production:**
1. Run on private network only
2. Use VPN or SSH tunnel for remote access
3. Consider adding authentication if exposing publicly
4. Use HTTPS with reverse proxy

## Dashboard Color Theme

Electric blue on black aesthetic:

```css
--electric-blue: #00d4ff
--dark-blue: #0088cc
--black: #000000
--dark-gray: #1a1a1a
--light-gray: #e0e0e0
--success-green: #00ff88
--warning-yellow: #ffaa00
--error-red: #ff3366
```

## Summary

The dashboard provides real-time monitoring of your trading system with:

- Live model health tracking
- Trade history and P&L
- Performance analytics
- System logs

All data comes directly from the coordinator via HTTP API, with no mock data. The system auto-refreshes every 5 seconds to keep information current.
