import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5500/api';

function App() {
  const [models, setModels] = useState([]);
  const [trades, setTrades] = useState([]);
  const [performance, setPerformance] = useState({});
  const [status, setStatus] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchAllData = async () => {
    try {
      const [modelsRes, tradesRes, perfRes, statusRes] = await Promise.all([
        fetch(`${API_BASE_URL}/models`),
        fetch(`${API_BASE_URL}/trades?limit=20`),
        fetch(`${API_BASE_URL}/performance`),
        fetch(`${API_BASE_URL}/status`)
      ]);

      if (modelsRes.ok) setModels(await modelsRes.json());
      if (tradesRes.ok) setTrades(await tradesRes.json());
      if (perfRes.ok) setPerformance(await perfRes.json());
      if (statusRes.ok) setStatus(await statusRes.json());

      setError(null);
      setLoading(false);
    } catch (err) {
      setError(`Failed to connect to API: ${err.message}`);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="app">
        <div className="loading">Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app">
        <div className="error">
          <h2>Connection Error</h2>
          <p>{error}</p>
          <p>Make sure the coordinator is running with API server enabled.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="header">
        <h1>TradeProject Dashboard</h1>
        <div className="status-badge">
          <span className={status.is_running ? 'status-active' : 'status-inactive'}>
            {status.is_running ? '● Active' : '○ Inactive'}
          </span>
          {status.dry_run && <span className="badge">DRY RUN</span>}
          {status.testnet && <span className="badge">TESTNET</span>}
        </div>
      </header>

      <div className="dashboard-grid">
        {/* Models Section */}
        <section className="card models-section">
          <h2>Model Servers</h2>
          <div className="models-grid">
            {models.map((model, idx) => (
              <div key={idx} className={`model-card ${model.healthy ? 'healthy' : 'unhealthy'}`}>
                <div className="model-header">
                  <span className="model-name">{model.name}</span>
                  <span className={`status-dot ${model.healthy ? 'green' : 'red'}`}></span>
                </div>
                <div className="model-stats">
                  <div>Success: {model.success_count || 0}</div>
                  <div>Failed: {model.failure_count || 0}</div>
                  <div>Rate: {((model.success_rate || 0) * 100).toFixed(1)}%</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Performance Section */}
        <section className="card performance-section">
          <h2>Performance</h2>
          <div className="performance-grid">
            <div className="stat-box">
              <div className="stat-label">Total Trades</div>
              <div className="stat-value">{performance.total_trades || 0}</div>
            </div>
            <div className="stat-box">
              <div className="stat-label">Win Rate</div>
              <div className="stat-value">
                {((performance.win_rate || 0) * 100).toFixed(1)}%
              </div>
            </div>
            <div className="stat-box">
              <div className="stat-label">Total P&L</div>
              <div className={`stat-value ${(performance.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                ${(performance.total_pnl || 0).toFixed(2)}
              </div>
            </div>
            <div className="stat-box">
              <div className="stat-label">Avg P&L</div>
              <div className={`stat-value ${(performance.avg_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                ${(performance.avg_pnl || 0).toFixed(2)}
              </div>
            </div>
          </div>
        </section>

        {/* Trades Section */}
        <section className="card trades-section">
          <h2>Recent Trades</h2>
          <div className="trades-table-container">
            {trades.length === 0 ? (
              <p className="no-data">No trades yet</p>
            ) : (
              <table className="trades-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Side</th>
                    <th>Entry</th>
                    <th>Exit</th>
                    <th>P&L</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.map((trade, idx) => (
                    <tr key={idx}>
                      <td>{new Date(trade.timestamp).toLocaleString()}</td>
                      <td className={trade.side === 'long' ? 'side-long' : 'side-short'}>
                        {trade.side?.toUpperCase()}
                      </td>
                      <td>${trade.entry_price?.toFixed(2)}</td>
                      <td>${trade.exit_price?.toFixed(2) || '-'}</td>
                      <td className={trade.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}>
                        ${trade.pnl?.toFixed(2) || '-'}
                      </td>
                      <td>
                        <span className={`status-badge ${trade.status?.toLowerCase()}`}>
                          {trade.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>

        {/* Daily Stats */}
        <section className="card daily-stats-section">
          <h2>Daily Statistics</h2>
          <div className="daily-stats">
            <div className="stat-item">
              <span className="label">Trades Today:</span>
              <span className="value">{status.daily_stats?.trades || 0}</span>
            </div>
            <div className="stat-item">
              <span className="label">Daily P&L:</span>
              <span className={`value ${(status.daily_stats?.pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                ${(status.daily_stats?.pnl || 0).toFixed(2)}
              </span>
            </div>
            <div className="stat-item">
              <span className="label">Consecutive Losses:</span>
              <span className="value">{status.daily_stats?.consecutive_losses || 0}</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default App;
