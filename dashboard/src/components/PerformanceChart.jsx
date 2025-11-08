import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

function PerformanceChart({ data }) {
    // Default data if none provided
    const chartData = data && data.length > 0 ? data : [
        { time: '00:00', pnl: 0 },
        { time: '04:00', pnl: 0 },
        { time: '08:00', pnl: 0 },
        { time: '12:00', pnl: 0 },
        { time: '16:00', pnl: 0 },
        { time: '20:00', pnl: 0 },
        { time: '24:00', pnl: 0 },
    ];

    // Custom tooltip
    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const value = payload[0].value;
            return (
                <div className="bg-xylen-dark-900 border border-xylen-dark-700 rounded-lg p-3 shadow-lg">
                    <p className="text-xs text-gray-400 mb-1">{payload[0].payload.time}</p>
                    <p className={`text-lg font-mono font-bold ${value >= 0 ? 'text-green-400' : 'text-red-400'
                        }`}>
                        {value >= 0 ? '+' : ''}${value.toFixed(2)}
                    </p>
                </div>
            );
        }
        return null;
    };

    // Determine if we're in profit or loss
    const latestPnL = chartData[chartData.length - 1]?.pnl || 0;
    const isProfit = latestPnL >= 0;

    return (
        <div className="xylen-card col-span-2">
            <div className="xylen-card-header">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white">Performance</h2>
                    <div className="flex items-center space-x-2">
                        <span className="text-sm text-gray-400">Cumulative P&L:</span>
                        <span className={`text-lg font-mono font-bold ${isProfit ? 'text-green-400' : 'text-red-400'
                            }`}>
                            {isProfit ? '+' : ''}${latestPnL.toFixed(2)}
                        </span>
                    </div>
                </div>
            </div>
            <div className="xylen-card-body">
                <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={chartData}>
                        <defs>
                            <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
                                <stop
                                    offset="5%"
                                    stopColor={isProfit ? "#10b981" : "#ef4444"}
                                    stopOpacity={0.3}
                                />
                                <stop
                                    offset="95%"
                                    stopColor={isProfit ? "#10b981" : "#ef4444"}
                                    stopOpacity={0}
                                />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#2A2A2A" />
                        <XAxis
                            dataKey="time"
                            stroke="#6B7280"
                            style={{ fontSize: '12px' }}
                        />
                        <YAxis
                            stroke="#6B7280"
                            style={{ fontSize: '12px' }}
                            tickFormatter={(value) => `$${value}`}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Area
                            type="monotone"
                            dataKey="pnl"
                            stroke={isProfit ? "#10b981" : "#ef4444"}
                            strokeWidth={2}
                            fill="url(#colorPnl)"
                            animationDuration={1000}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}

export default PerformanceChart;
