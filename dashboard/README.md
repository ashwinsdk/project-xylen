# TradeProject Dashboard

Real-time React dashboard for monitoring the TradeProject trading system.

## Setup

### Install Dependencies

```bash
npm install
```

### Configure API Connection

```bash
cp .env.example .env.local
```

Edit `.env.local` if your coordinator is running on a different host:

```
REACT_APP_API_URL=http://localhost:5000/api
```

### Development Mode

```bash
npm run dev
```

Dashboard will be available at http://localhost:3000

### Production Build

```bash
npm run build
npm run preview
```

## Requirements

The dashboard requires the Mac coordinator to be running with the API server enabled.

### Start Coordinator with API Server

```bash
cd ../mac_coordinator
source venv/bin/activate
python coordinator.py
```

The coordinator will automatically start the API server on port 5000 (configurable in config.yaml).

## Features

- **Model Health Status**: Real-time health monitoring of all model VMs
- **Recent Trades**: Live trade history with P&L tracking
- **Performance Metrics**: Win rate, total trades, cumulative P&L
- **Performance Chart**: Visual cumulative P&L over time
- **System Logs**: Real-time coordinator logs with color-coded severity

## API Endpoints

The dashboard connects to these coordinator API endpoints:

- `GET /api/models` - Model VM health and performance
- `GET /api/trades?limit=50` - Recent trades
- `GET /api/performance` - Performance statistics
- `GET /api/logs?limit=100` - Recent log entries
- `GET /api/status` - Coordinator status

## Troubleshooting

### Dashboard shows "Disconnected"

Make sure the coordinator is running with API server enabled:

```bash
# Check coordinator is running
ps aux | grep coordinator.py

# Check API server is responding
curl http://localhost:5000/api/status
```

### CORS Errors

The API server includes CORS headers. If you still see CORS errors:

1. Ensure coordinator is running
2. Check API_BASE_URL in App.jsx matches your coordinator
3. Restart both coordinator and dashboard

### No Data Showing

1. Verify coordinator has been running and collecting data
2. Check SQLite database exists: `ls -la ../mac_coordinator/data/trades.db`
3. View coordinator logs: `tail -f ../mac_coordinator/logs/coordinator.log`

## Development

### File Structure

```
dashboard/
├── src/
│   ├── App.jsx              # Main application with API calls
│   ├── App.css              # Application styles
│   ├── components/          # Dashboard components
│   │   ├── ModelStatus.jsx  # Model health display
│   │   ├── TradesList.jsx   # Recent trades table
│   │   ├── PerformanceChart.jsx  # P&L chart
│   │   └── SystemLogs.jsx   # Log viewer
│   └── index.css            # Global styles
├── package.json
└── vite.config.js
```

### Adding New API Endpoints

1. Add endpoint in `mac_coordinator/api_server.py`
2. Add fetch call in `dashboard/src/App.jsx`
3. Pass data to appropriate component

### Customizing Refresh Rate

Edit `App.jsx`:

```javascript
const [refreshInterval, setRefreshInterval] = useState(5000); // 5 seconds
```

## Color Theme

The dashboard uses an electric blue on black theme:

- Primary: #00d4ff (Electric Blue)
- Background: #000000 (Black)
- Cards: #1a1a1a (Dark Gray)
- Success: #00ff88 (Green)
- Error: #ff3366 (Red)
- Warning: #ffaa00 (Yellow)
