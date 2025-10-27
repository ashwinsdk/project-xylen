import React from 'react';
import './ModelStatus.css';

function ModelStatus({ models }) {
  const formatUptime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  return (
    <div className="model-status-container">
      {models.map((model, index) => (
        <div key={index} className={`model-card ${model.healthy ? 'healthy' : 'unhealthy'}`}>
          <div className="model-header">
            <h3>{model.name}</h3>
            <span className={`health-badge ${model.healthy ? 'healthy' : 'unhealthy'}`}>
              {model.healthy ? 'HEALTHY' : 'OFFLINE'}
            </span>
          </div>
          
          <div className="model-details">
            <div className="model-detail-item">
              <span className="detail-label">Endpoint:</span>
              <span className="detail-value">{model.host}:{model.port}</span>
            </div>
            
            {model.healthy && (
              <>
                <div className="model-detail-item">
                  <span className="detail-label">Uptime:</span>
                  <span className="detail-value">{formatUptime(model.uptime)}</span>
                </div>
                
                <div className="model-detail-item">
                  <span className="detail-label">Memory:</span>
                  <span className="detail-value">{model.memory_mb} MB</span>
                </div>
                
                <div className="model-detail-item">
                  <span className="detail-label">Success Rate:</span>
                  <span className="detail-value">{(model.success_rate * 100).toFixed(1)}%</span>
                </div>
                
                <div className="model-detail-item">
                  <span className="detail-label">Avg Response:</span>
                  <span className="detail-value">{(model.avg_response_time * 1000).toFixed(0)}ms</span>
                </div>
              </>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default ModelStatus;
