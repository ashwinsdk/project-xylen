import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './PerformanceChart.css';

function PerformanceChart({ trades }) {
  const chartData = trades.map((trade, index) => {
    const cumulativePnl = trades
      .slice(0, index + 1)
      .reduce((sum, t) => sum + (t.pnl || 0), 0);
    
    return {
      trade: index + 1,
      pnl: cumulativePnl,
      timestamp: new Date(trade.timestamp).getTime()
    };
  }).reverse();

  return (
    <div className="performance-chart-container">
      {chartData.length === 0 ? (
        <div className="no-data">No performance data available</div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 212, 255, 0.1)" />
            <XAxis 
              dataKey="trade" 
              stroke="#00d4ff"
              label={{ value: 'Trade Number', position: 'insideBottom', offset: -5, fill: '#00d4ff' }}
            />
            <YAxis 
              stroke="#00d4ff"
              label={{ value: 'Cumulative PNL ($)', angle: -90, position: 'insideLeft', fill: '#00d4ff' }}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#1a1a1a', 
                border: '1px solid #00d4ff',
                borderRadius: '4px',
                color: '#e0e0e0'
              }}
              formatter={(value) => [`$${value.toFixed(2)}`, 'PNL']}
            />
            <Line 
              type="monotone" 
              dataKey="pnl" 
              stroke="#00d4ff" 
              strokeWidth={2}
              dot={{ fill: '#00d4ff', r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export default PerformanceChart;
