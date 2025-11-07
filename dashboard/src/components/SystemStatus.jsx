import { Activity, Shield, TrendingUp, Clock, AlertCircle, CheckCircle, Play, Pause, DollarSign, Wifi, Users, Target, Zap } from 'lucide-react';

function SystemStatus({ status = {}, connected = false, metrics = {}, marketData = {} }) {
    const {
        status: coordinatorStatus = 'stopped',
        uptime_seconds = 0,
        open_trades = 0,
        circuit_breaker = 'normal',
        dry_run = true,
        testnet = true,
        symbol = 'BTCUSDT',
        cpu_usage = 0,
        memory_usage = 0,
        websocket_clients = 0
    } = status;

    // Format uptime
    const formatUptime = (seconds) => {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        }
        return `${minutes}m`;
    };

    // Circuit breaker status
    const getCircuitBreakerColor = () => {
        switch (circuit_breaker) {
            case 'normal':
                return 'text-green-400';
            case 'warning':
                return 'text-yellow-400';
            case 'active':
            case 'triggered':
                return 'text-red-400';
            default:
                return 'text-gray-400';
        }
    };

    const getCircuitBreakerIcon = () => {
        switch (circuit_breaker) {
            case 'normal':
                return <CheckCircle className="w-5 h-5 text-green-400" />;
            case 'warning':
                return <AlertCircle className="w-5 h-5 text-yellow-400" />;
            case 'active':
            case 'triggered':
                return <AlertCircle className="w-5 h-5 text-red-400" />;
            default:
                return <Shield className="w-5 h-5 text-gray-400" />;
        }
    };

    return (
        <div className="xylen-card">
            <div className="xylen-card-header">
                <h2 className="text-xl font-bold text-white">System Status</h2>
            </div>
            <div className="xylen-card-body space-y-4">
                {/* Coordinator Status */}
                <div className="flex items-center justify-between p-3 bg-xylen-dark-800 rounded-lg border-l-4" style={{ borderColor: coordinatorStatus === 'running' ? '#10b981' : '#6b7280' }}>
                    <div className="flex items-center space-x-3">
                        {coordinatorStatus === 'running' ? (
                            <Play className="w-5 h-5 text-green-400" />
                        ) : (
                            <Pause className="w-5 h-5 text-gray-400" />
                        )}
                        <span className="text-sm text-gray-300">Coordinator</span>
                    </div>
                    <span className={`text-sm font-semibold uppercase ${coordinatorStatus === 'running' ? 'text-green-400' : 'text-gray-400'}`}>
                        {coordinatorStatus}
                    </span>
                </div>

                {/* Market Price */}
                {marketData && marketData.price > 0 && (
                    <div className="flex items-center justify-between p-3 bg-xylen-dark-800 rounded-lg">
                        <div className="flex items-center space-x-3">
                            <DollarSign className="w-5 h-5 text-yellow-400" />
                            <div>
                                <span className="text-sm text-gray-300">{symbol}</span>
                                {marketData.rsi && (
                                    <span className="block text-xs text-gray-500">RSI: {marketData.rsi?.toFixed(1)}</span>
                                )}
                            </div>
                        </div>
                        <span className="text-sm font-mono font-semibold text-white">
                            ${marketData.price?.toLocaleString()}
                        </span>
                    </div>
                )}

                {/* Uptime */}
                <div className="flex items-center justify-between p-3 bg-xylen-dark-800 rounded-lg">
                    <div className="flex items-center space-x-3">
                        <Clock className="w-5 h-5 text-blue-400" />
                        <span className="text-sm text-gray-300">Uptime</span>
                    </div>
                    <span className="text-sm font-mono font-semibold text-white">
                        {formatUptime(uptime_seconds)}
                    </span>
                </div>

                {/* Active Trades */}
                <div className="flex items-center justify-between p-3 bg-xylen-dark-800 rounded-lg">
                    <div className="flex items-center space-x-3">
                        <Activity className="w-5 h-5 text-purple-400" />
                        <span className="text-sm text-gray-300">Active Trades</span>
                    </div>
                    <span className="text-sm font-mono font-semibold text-white">
                        {open_trades}
                    </span>
                </div>

                {/* Circuit Breaker */}
                <div className="flex items-center justify-between p-3 bg-xylen-dark-800 rounded-lg border-l-4 border-current" style={{ borderColor: circuit_breaker === 'normal' ? '#10b981' : circuit_breaker === 'warning' ? '#f59e0b' : '#ef4444' }}>
                    <div className="flex items-center space-x-3">
                        {getCircuitBreakerIcon()}
                        <span className="text-sm text-gray-300">Circuit Breaker</span>
                    </div>
                    <span className={`text-sm font-semibold uppercase ${getCircuitBreakerColor()}`}>
                        {circuit_breaker}
                    </span>
                </div>

                {/* WebSocket Clients */}
                {websocket_clients > 0 && (
                    <div className="flex items-center justify-between p-2 bg-xylen-dark-800 rounded-lg">
                        <div className="flex items-center space-x-2">
                            <Wifi className="w-4 h-4 text-blue-400" />
                            <span className="text-xs text-gray-300">Dashboard Clients</span>
                        </div>
                        <span className="text-xs font-mono font-semibold text-white">
                            {websocket_clients}
                        </span>
                    </div>
                )}

                {/* Mode Indicator */}
                <div className="pt-4 border-t border-xylen-dark-700 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Mode:</span>
                        <span className={`font-semibold ${testnet ? 'text-yellow-400' : 'text-red-400'}`}>
                            {testnet ? (dry_run ? 'TESTNET (DRY RUN)' : 'TESTNET') : (dry_run ? 'DRY RUN' : 'LIVE TRADING ⚠️')}
                        </span>
                    </div>
                </div>

                {/* System Resources */}
                <div className="pt-4 border-t border-xylen-dark-700 space-y-3">
                    <div className="space-y-1">
                        <div className="flex items-center justify-between">
                            <span className="text-xs text-gray-400">CPU Usage</span>
                            <span className="text-xs font-mono text-white">{cpu_usage.toFixed(1)}%</span>
                        </div>
                        <div className="w-full bg-xylen-dark-800 rounded-full h-1.5">
                            <div
                                className="bg-blue-500 h-1.5 rounded-full transition-all duration-500"
                                style={{ width: `${cpu_usage}%` }}
                            />
                        </div>
                    </div>

                    <div className="space-y-1">
                        <div className="flex items-center justify-between">
                            <span className="text-xs text-gray-400">Memory Usage</span>
                            <span className="text-xs font-mono text-white">{memory_usage.toFixed(1)}%</span>
                        </div>
                        <div className="w-full bg-xylen-dark-800 rounded-full h-1.5">
                            <div
                                className="bg-purple-500 h-1.5 rounded-full transition-all duration-500"
                                style={{ width: `${memory_usage}%` }}
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default SystemStatus;
