import { Activity, CheckCircle, AlertTriangle, XCircle, Clock, Cpu, Zap, Database, MemoryStick, Gauge } from 'lucide-react';

function ModelHealthCard({ model }) {
    const getStatusIcon = () => {
        if (!model.online) {
            return <XCircle className="w-5 h-5 text-gray-500" />;
        }

        switch (model.status) {
            case 'online':
            case 'healthy':
                return <CheckCircle className="w-5 h-5 text-green-400" />;
            case 'degraded':
                return <AlertTriangle className="w-5 h-5 text-yellow-400" />;
            case 'offline':
            case 'failed':
                return <XCircle className="w-5 h-5 text-red-400" />;
            default:
                return <Activity className="w-5 h-5 text-gray-400" />;
        }
    };

    const getStatusColor = () => {
        if (!model.online) {
            return 'border-gray-700/50 bg-gray-900/10';
        }

        switch (model.status) {
            case 'online':
            case 'healthy':
                return 'border-green-700/50 bg-green-900/10';
            case 'degraded':
                return 'border-yellow-700/50 bg-yellow-900/10';
            case 'offline':
            case 'failed':
                return 'border-red-700/50 bg-red-900/10';
            default:
                return 'border-gray-700/50 bg-gray-900/10';
        }
    };

    const formatUptime = (seconds) => {
        if (!seconds) return 'N/A';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        }
        return `${minutes}m`;
    };

    return (
        <div className={`xylen-card ${getStatusColor()} transition-all duration-300 hover:scale-105`}>
            <div className="xylen-card-header">
                <div className="flex items-center justify-between">
                    <div>
                        <span className="font-semibold text-white">{model.name}</span>
                        {model.model_type && (
                            <span className="block text-xs text-gray-400 mt-0.5">
                                {model.model_type} v{model.version || '1.0'}
                            </span>
                        )}
                    </div>
                    {getStatusIcon()}
                </div>
            </div>
            <div className="xylen-card-body space-y-3">
                {/* Online/Offline Status */}
                <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-400">Status</span>
                    <span className={`text-sm font-semibold ${model.online ? 'text-green-400' : 'text-gray-500'}`}>
                        {model.online ? 'ONLINE' : 'OFFLINE'}
                    </span>
                </div>

                {model.online && (
                    <>
                        {/* Uptime */}
                        {model.uptime_seconds > 0 && (
                            <div className="flex justify-between items-center text-xs">
                                <span className="text-gray-400">Uptime</span>
                                <span className="font-mono text-white">{formatUptime(model.uptime_seconds)}</span>
                            </div>
                        )}

                        {/* Training Status */}
                        {(model.training || model.continuous_learning) && (
                            <div className="space-y-2 p-2 bg-xylen-dark-800 rounded-lg">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center space-x-2">
                                        <Cpu className="w-4 h-4 text-blue-400 animate-pulse" />
                                        <span className="text-xs text-blue-400 font-semibold">
                                            {model.training ? 'TRAINING' : 'CONTINUOUS LEARNING'}
                                        </span>
                                    </div>
                                    {model.samples_trained > 0 && (
                                        <span className="text-xs text-gray-400">
                                            {model.samples_trained.toLocaleString()} samples
                                        </span>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Data Collector Status */}
                        {model.data_collector_active && (
                            <div className="flex items-center justify-between p-2 bg-blue-900/20 rounded-lg border border-blue-700/30">
                                <div className="flex items-center space-x-2">
                                    <Database className="w-4 h-4 text-blue-400" />
                                    <span className="text-xs text-blue-300">Data Collector</span>
                                </div>
                                <span className="text-xs text-green-400 font-semibold">ACTIVE</span>
                            </div>
                        )}

                        {/* Confidence */}
                        <div className="flex justify-between items-center">
                            <span className="text-sm text-gray-400">Confidence</span>
                            <span className="text-sm font-mono font-semibold text-white">
                                {(model.confidence * 100).toFixed(1)}%
                            </span>
                        </div>

                        <div className="w-full bg-xylen-dark-800 rounded-full h-2">
                            <div
                                className="bg-xylen-gradient h-2 rounded-full transition-all duration-500"
                                style={{ width: `${model.confidence * 100}%` }}
                            />
                        </div>

                        {/* Performance Metrics Grid */}
                        <div className="grid grid-cols-2 gap-2 pt-2">
                            {/* Latency */}
                            <div className="flex flex-col space-y-1">
                                <div className="flex items-center space-x-1 text-gray-400">
                                    <Clock className="w-3 h-3" />
                                    <span className="text-xs">Latency</span>
                                </div>
                                <span className="text-xs font-mono text-white">
                                    {model.latency_ms || model.latency || 0}ms
                                </span>
                            </div>

                            {/* Memory Usage */}
                            {model.memory_usage_mb > 0 && (
                                <div className="flex flex-col space-y-1">
                                    <div className="flex items-center space-x-1 text-gray-400">
                                        <MemoryStick className="w-3 h-3" />
                                        <span className="text-xs">Memory</span>
                                    </div>
                                    <span className="text-xs font-mono text-white">
                                        {model.memory_usage_mb?.toFixed(0)}MB
                                    </span>
                                </div>
                            )}

                            {/* CPU Usage */}
                            {model.cpu_percent !== undefined && (
                                <div className="flex flex-col space-y-1">
                                    <div className="flex items-center space-x-1 text-gray-400">
                                        <Gauge className="w-3 h-3" />
                                        <span className="text-xs">CPU</span>
                                    </div>
                                    <span className="text-xs font-mono text-white">
                                        {model.cpu_percent?.toFixed(1)}%
                                    </span>
                                </div>
                            )}

                            {/* Training Samples */}
                            {model.training_samples > 0 && (
                                <div className="flex flex-col space-y-1">
                                    <div className="flex items-center space-x-1 text-gray-400">
                                        <Database className="w-3 h-3" />
                                        <span className="text-xs">Samples</span>
                                    </div>
                                    <span className="text-xs font-mono text-white">
                                        {model.training_samples?.toLocaleString()}
                                    </span>
                                </div>
                            )}
                        </div>
                    </>
                )}

                {/* Status Badge */}
                <div className="pt-2 border-t border-xylen-dark-700">
                    <span className={`status-badge ${model.online && (model.status === 'healthy' || model.status === 'online') ? 'status-success' :
                        model.status === 'degraded' ? 'status-warning' :
                            'status-error'
                        }`}>
                        {model.online ? (model.status || 'ONLINE').toUpperCase() : 'OFFLINE'}
                    </span>

                    {/* Continuous Learning Indicator */}
                    {model.online && model.continuous_learning && !model.training && (
                        <span className="status-badge status-info ml-2">
                            <Zap className="w-3 h-3 inline mr-1" />
                            LEARNING
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}

export default ModelHealthCard;

