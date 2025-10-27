import React, { useState, useEffect } from 'react';
import './App.css';
import ModelStatus from './components/ModelStatus';
import TradesList from './components/TradesList';
import PerformanceChart from './components/PerformanceChart';
import SystemLogs from './components/SystemLogs';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

function App() {
  const [systemData, setSystemData] = useState({
    models: [],
    trades: [],
    performance: {},
    logs: [],
    status: 'disconnected'
  });

  const [refreshInterval, setRefreshInterval] = useState(5000);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchSystemData();
    
    const interval = setInterval(() => {
      fetchSystemData();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [refreshInterval]);

  const fetchSystemData = async () => {
    try {
      const [modelsRes, tradesRes, performanceRes, logsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/models`).catch(() => ({ ok: false })),
        fetch(`${API_BASE_URL}/trades`).catch(() => ({ ok: false })),
        fetch(`${API_BASE_URL}/performance`).catch(() => ({ ok: false })),
        fetch(`${API_BASE_URL}/logs`).catch(() => ({ ok: false }))
      ]);

      const models = modelsRes.ok ? await modelsRes.json() : [];
      const trades = tradesRes.ok ? await tradesRes.json() : [];
      const performance = performanceRes.ok ? await performanceRes.json() : {};
      const logs = logsRes.ok ? await logsRes.json() : [];

      setSystemData({
        models,
        trades,
        performance,
        logs,
        status: modelsRes.ok || tradesRes.ok ? 'connected' : 'disconnected'
      });
      setError(null);
    } catch (error) {
      console.error('Error fetching system data:', error);
      setError('Failed to connect to coordinator');
      setSystemData(prev => ({ ...prev, status: 'disconnected' }));
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>TradeProject Dashboard</h1>
        <div className="status-indicator">
          <span className={`status-dot ${systemData.status === 'connected' ? 'connected' : 'disconnected'}`}></span>
          <span>{systemData.status === 'connected' ? 'Connected' : 'Disconnected'}</span>
        </div>
      </header>

      <main className="app-main">
        {error && (
          <div className="error-banner">
            {error} - Make sure coordinator is running with API server enabled
          </div>
        )}
        <section className="dashboard-section">
          <h2>Model Health Status</h2>
          <ModelStatus models={systemData.models} />
        </section>

        <section className="dashboard-section">
          <h2>Performance Summary</h2>
          <div className="performance-summary">
            <div className="stat-card">
              <div className="stat-label">Total Trades</div>
              <div className="stat-value">{systemData.performance.total_trades || 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Win Rate</div>
              <div className="stat-value">
                {((systemData.performance.win_rate || 0) * 100).toFixed(1)}%
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Total PNL</div>
              <div className={`stat-value ${(systemData.performance.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                ${(systemData.performance.total_pnl || 0).toFixed(2)}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Avg PNL</div>
              <div className={`stat-value ${(systemData.performance.avg_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                ${(systemData.performance.avg_pnl || 0).toFixed(2)}
              </div>
            </div>
          </div>
        </section>

        <section className="dashboard-section">
          <h2>Recent Trades</h2>
          <TradesList trades={systemData.trades} />
        </section>

        <section className="dashboard-section">
          <h2>Performance Chart</h2>
          <PerformanceChart trades={systemData.trades} />
        </section>

        <section className="dashboard-section">
          <h2>System Logs</h2>
          <SystemLogs logs={systemData.logs} />
        </section>
      </main>

      <footer className="app-footer">
        <p>TradeProject v1.0.0 - Paper Trading Mode</p>
      </footer>
    </div>
  );
}

export default App;
