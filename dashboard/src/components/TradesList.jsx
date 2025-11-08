import { TrendingUp, TrendingDown, ArrowRight } from 'lucide-react';

function TradesList({ trades }) {
    if (!trades || trades.length === 0) {
        return (
            <div className="xylen-card">
                <div className="xylen-card-header">
                    <h2 className="text-xl font-bold text-white">Recent Trades</h2>
                </div>
                <div className="xylen-card-body">
                    <div className="text-center py-12 text-gray-400">
                        <p>No trades yet. Waiting for trading signals...</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="xylen-card">
            <div className="xylen-card-header">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white">Recent Trades</h2>
                    <span className="text-sm text-gray-400">{trades.length} trades</span>
                </div>
            </div>
            <div className="xylen-card-body p-0">
                <div className="overflow-x-auto custom-scrollbar">
                    <table className="w-full">
                        <thead className="bg-xylen-dark-800 border-b border-xylen-dark-700">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                                    Time
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                                    Symbol
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                                    Side
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">
                                    Entry
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">
                                    Exit
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">
                                    P&L
                                </th>
                                <th className="px-6 py-3 text-center text-xs font-semibold text-gray-400 uppercase tracking-wider">
                                    Status
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-xylen-dark-700">
                            {trades.map((trade, index) => (
                                <tr
                                    key={trade.id || index}
                                    className="hover:bg-xylen-dark-800/50 transition-colors slide-in"
                                >
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                                        {new Date(trade.timestamp).toLocaleTimeString()}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">
                                        {trade.symbol || 'BTCUSDT'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className={`flex items-center space-x-1 ${trade.side === 'long' || trade.side === 'BUY'
                                                ? 'text-green-400'
                                                : 'text-red-400'
                                            }`}>
                                            {trade.side === 'long' || trade.side === 'BUY' ? (
                                                <TrendingUp className="w-4 h-4" />
                                            ) : (
                                                <TrendingDown className="w-4 h-4" />
                                            )}
                                            <span className="text-sm font-semibold">
                                                {(trade.side || 'LONG').toUpperCase()}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-mono text-white">
                                        ${trade.entry_price?.toLocaleString() || '0.00'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-mono text-white">
                                        {trade.exit_price ? `$${trade.exit_price.toLocaleString()}` : '-'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-mono font-semibold">
                                        {trade.pnl !== undefined ? (
                                            <span className={trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                                                {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                                            </span>
                                        ) : (
                                            <span className="text-gray-400">-</span>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-center">
                                        <span className={`status-badge ${trade.status === 'open' ? 'status-info' :
                                                trade.status === 'closed' && trade.pnl >= 0 ? 'status-success' :
                                                    trade.status === 'closed' && trade.pnl < 0 ? 'status-error' :
                                                        'status-warning'
                                            }`}>
                                            {trade.status?.toUpperCase() || 'OPEN'}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

export default TradesList;
