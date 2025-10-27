import React from 'react';
import './SystemLogs.css';

function SystemLogs({ logs }) {
  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const getLevelClass = (level) => {
    return level.toLowerCase();
  };

  return (
    <div className="system-logs-container">
      <div className="logs-content">
        {logs.length === 0 ? (
          <div className="no-logs">No logs available</div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="log-entry">
              <span className="log-timestamp">{formatTimestamp(log.timestamp)}</span>
              <span className={`log-level ${getLevelClass(log.level)}`}>{log.level}</span>
              <span className="log-message">{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default SystemLogs;
