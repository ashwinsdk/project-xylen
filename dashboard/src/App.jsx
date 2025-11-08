import { useState, useEffect } from 'react';
import {
    Activity,
    TrendingUp,
    TrendingDown,
    DollarSign,
    Zap,
    AlertCircle,
    CheckCircle,
    BarChart3,
    Settings
} from 'lucide-react';
import ModelHealthCard from './components/ModelHealthCard';
import TradesList from './components/TradesList';
import PerformanceChart from './components/PerformanceChart';
import SystemStatus from './components/SystemStatus';

function App() {
    const [ws, setWs] = useState(null);
    const [connected, setConnected] = useState(false);
    const [coordinatorStatus, setCoordinatorStatus] = useState({
        status: 'stopped',
        dry_run: true,
        testnet: true,
        symbol: 'BTCUSDT',
        uptime_seconds: 0,
        open_trades: 0,
        circuit_breaker: 'normal'
    });
    const [metrics, setMetrics] = useState({
        totalPnL: 0,
        dailyPnL: 0,
        winRate: 0,
        totalTrades: 0,
        activeTrades: 0,
    });
    const [models, setModels] = useState([
        { id: 1, name: 'Model 1', status: 'offline', online: false, training: false, continuous_learning: false, confidence: 0, latency_ms: 0 },
        { id: 2, name: 'Model 2', status: 'offline', online: false, training: false, continuous_learning: false, confidence: 0, latency_ms: 0 },
        { id: 3, name: 'Model 3', status: 'offline', online: false, training: false, continuous_learning: false, confidence: 0, latency_ms: 0 },
        { id: 4, name: 'Model 4', status: 'offline', online: false, training: false, continuous_learning: false, confidence: 0, latency_ms: 0 },
    ]);
    const [trades, setTrades] = useState([]);
    const [performanceData, setPerformanceData] = useState([]);
    const [marketData, setMarketData] = useState({ price: 0, rsi: 0, volume_24h: 0 });
    const [settingsOpen, setSettingsOpen] = useState(false);

    // WebSocket connection
    useEffect(() => {
        const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8765';

        const connectWebSocket = () => {
            const websocket = new WebSocket(wsUrl);

            websocket.onopen = () => {
                console.log('WebSocket connected');
                setConnected(true);
            };

            websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleWebSocketMessage(data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                setConnected(false);
            };

            websocket.onclose = () => {
                console.log('WebSocket disconnected');
                setConnected(false);
                // Attempt to reconnect after 5 seconds
                setTimeout(connectWebSocket, 5000);
            };

            setWs(websocket);
        };

        connectWebSocket();

        return () => {
            if (ws) {
                ws.close();
            }
        };
    }, []);

    const handleWebSocketMessage = (data) => {
        switch (data.type) {
            case 'status_update':
                // Comprehensive status update from coordinator
                if (data.coordinator) {
                    setCoordinatorStatus(data.coordinator);
                }
                if (data.models && data.models.length > 0) {
                    setModels(data.models.map((model, idx) => ({
                        ...model,
                        id: idx + 1,
                        latency: model.latency_ms || 0
                    })));
                }
                if (data.market) {
                    setMarketData(data.market);
                }
                if (data.performance) {
                    setMetrics({
                        totalPnL: data.performance.total_pnl || 0,
                        dailyPnL: data.performance.daily_pnl || 0,
                        winRate: data.performance.win_rate || 0,
                        totalTrades: data.performance.total_trades || 0,
                        activeTrades: data.coordinator?.open_trades || 0
                    });
                }
                break;
            case 'metrics_update':
                setMetrics(data.metrics);
                break;
            case 'model_health':
                setModels(data.models);
                break;
            case 'trade_update':
                setTrades(prev => [data.trade, ...prev.slice(0, 49)]); // Keep last 50 trades
                break;
            case 'performance_data':
                setPerformanceData(data.data);
                break;
            case 'welcome':
                console.log('Connected:', data.message);
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    };

    return (
        <div className="min-h-screen bg-black">
            {/* Header */}
            <header className="bg-xylen-dark-900 border-b border-xylen-dark-700 sticky top-0 z-50">
                <div className="max-w-[1920px] mx-auto px-6 py-4">
                    <div className="flex items-center justify-between">
                        {/* Logo */}
                        <div className="flex items-center space-x-4">
                            <img
                                src="/assets/svg/xylen-logo-transparent.svg"
                                alt="Project Xylen"
                                className="h-10 w-auto"
                            />
                            <div>
                                <h1 className="text-2xl font-bold text-gradient">Project Xylen</h1>
                                <p className="text-xs text-gray-400">AI Trading System v2.0</p>
                            </div>
                        </div>

                        {/* Connection & Coordinator Status */}
                        <div className="flex items-center space-x-4">
                            {/* Coordinator Mode Badge */}
                            {(coordinatorStatus.testnet || coordinatorStatus.dry_run) && (
                                <div className="px-3 py-1.5 rounded-full bg-yellow-900/30 border border-yellow-700/50">
                                    <span className="text-xs font-semibold text-yellow-400">
                                        {coordinatorStatus.testnet ? (coordinatorStatus.dry_run ? 'TESTNET (DRY RUN)' : 'TESTNET') : 'DRY RUN'}
                                    </span>
                                </div>
                            )}

                            {/* Live Trading Warning */}
                            {!coordinatorStatus.testnet && !coordinatorStatus.dry_run && (
                                <div className="px-3 py-1.5 rounded-full bg-red-900/30 border border-red-700/50 pulse-glow">
                                    <span className="text-xs font-semibold text-red-400">
                                        LIVE TRADING ⚠️
                                    </span>
                                </div>
                            )}                            {/* Circuit Breaker Warning */}
                            {coordinatorStatus.circuit_breaker === 'active' && (
                                <div className="px-3 py-1.5 rounded-full bg-red-900/30 border border-red-700/50 pulse-glow">
                                    <span className="text-xs font-semibold text-red-400">
                                        CIRCUIT BREAKER
                                    </span>
                                </div>
                            )}

                            {/* Connection Status */}
                            <div className={`flex items-center space-x-2 px-4 py-2 rounded-full ${connected ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'
                                }`}>
                                {connected ? (
                                    <>
                                        <CheckCircle className="w-4 h-4" />
                                        <span className="text-sm font-medium">
                                            {coordinatorStatus.status === 'running' ? 'Live' : 'Connected'}
                                        </span>
                                    </>
                                ) : (
                                    <>
                                        <AlertCircle className="w-4 h-4" />
                                        <span className="text-sm font-medium">Disconnected</span>
                                    </>
                                )}
                            </div>

                            <button
                                className="xylen-btn xylen-btn-ghost"
                                onClick={() => setSettingsOpen(!settingsOpen)}
                                title="Settings"
                            >
                                <Settings className="w-5 h-5" />
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-[1920px] mx-auto px-6 py-6 space-y-6">
                {/* Metrics Overview */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                    <MetricCard
                        label="Total P&L"
                        value={`$${metrics.totalPnL.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                        icon={<DollarSign className="w-6 h-6" />}
                        trend={metrics.totalPnL >= 0 ? 'up' : 'down'}
                    />
                    <MetricCard
                        label="Daily P&L"
                        value={`$${metrics.dailyPnL.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                        icon={<TrendingUp className="w-6 h-6" />}
                        trend={metrics.dailyPnL >= 0 ? 'up' : 'down'}
                    />
                    <MetricCard
                        label="Win Rate"
                        value={`${(metrics.winRate * 100).toFixed(1)}%`}
                        icon={<BarChart3 className="w-6 h-6" />}
                    />
                    <MetricCard
                        label="Total Trades"
                        value={metrics.totalTrades.toString()}
                        icon={<Activity className="w-6 h-6" />}
                    />
                    <MetricCard
                        label="Active Trades"
                        value={metrics.activeTrades.toString()}
                        icon={<Zap className="w-6 h-6" />}
                        highlight={metrics.activeTrades > 0}
                    />
                </div>

                {/* Model Health Cards */}
                <div>
                    <h2 className="text-xl font-bold mb-4 flex items-center">
                        <Activity className="w-5 h-5 mr-2 text-xylen-red-800" />
                        Model Health Status
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        {models.map(model => (
                            <ModelHealthCard key={model.id} model={model} />
                        ))}
                    </div>
                </div>

                {/* Charts and Trades */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Performance Chart */}
                    <div className="lg:col-span-2">
                        <PerformanceChart data={performanceData} />
                    </div>

                    {/* System Status */}
                    <div>
                        <SystemStatus
                            status={coordinatorStatus}
                            connected={connected}
                            metrics={metrics}
                            marketData={marketData}
                        />
                    </div>
                </div>

                {/* Recent Trades */}
                <TradesList trades={trades} />
            </main>

            {/* Settings Modal */}
            {settingsOpen && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={() => setSettingsOpen(false)}>
                    <div className="xylen-card max-w-2xl w-full m-4" onClick={(e) => e.stopPropagation()}>
                        <div className="xylen-card-body">
                            <div className="flex items-center justify-between mb-6">
                                <h2 className="text-2xl font-bold">Dashboard Settings</h2>
                                <button onClick={() => setSettingsOpen(false)} className="text-gray-400 hover:text-white">
                                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </button>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <h3 className="text-lg font-semibold mb-2">WebSocket Connection</h3>
                                    <p className="text-sm text-gray-400">
                                        URL: {import.meta.env.VITE_WS_URL || 'ws://localhost:8765'}
                                    </p>
                                    <p className="text-sm text-gray-400">
                                        Status: {connected ? <span className="text-green-400">Connected</span> : <span className="text-red-400">Disconnected</span>}
                                    </p>
                                </div>

                                <div>
                                    <h3 className="text-lg font-semibold mb-2">System Information</h3>
                                    <p className="text-sm text-gray-400">Mode: {status.testnet ? 'TESTNET' : 'LIVE TRADING'}</p>
                                    <p className="text-sm text-gray-400">Symbol: {status.symbol || 'BTCUSDT'}</p>
                                    <p className="text-sm text-gray-400">Dry Run: {status.dry_run ? 'Yes' : 'No'}</p>
                                </div>

                                <div>
                                    <h3 className="text-lg font-semibold mb-2">About</h3>
                                    <p className="text-sm text-gray-400">Project Xylen Dashboard v2.0</p>
                                    <p className="text-sm text-gray-400">Real-time trading bot monitoring interface</p>
                                </div>
                            </div>

                            <div className="mt-6 flex justify-end">
                                <button
                                    className="xylen-btn xylen-btn-primary"
                                    onClick={() => setSettingsOpen(false)}
                                >
                                    Close
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// Metric Card Component
function MetricCard({ label, value, icon, trend, highlight }) {
    return (
        <div className={`xylen-card ${highlight ? 'pulse-glow' : ''}`}>
            <div className="xylen-card-body">
                <div className="flex items-start justify-between mb-2">
                    <span className="metric-label">{label}</span>
                    <div className={trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : 'text-gray-400'}>
                        {icon}
                    </div>
                </div>
                <div className="flex items-end justify-between">
                    <span className="metric-value">{value}</span>
                    {trend && (
                        <div className={`flex items-center space-x-1 ${trend === 'up' ? 'text-green-400' : 'text-red-400'
                            }`}>
                            {trend === 'up' ? (
                                <TrendingUp className="w-4 h-4" />
                            ) : (
                                <TrendingDown className="w-4 h-4" />
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default App;
