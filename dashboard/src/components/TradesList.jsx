import React from 'react';
import './TradesList.css';

function TradesList({ trades }) {
  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  return (
    <div className="trades-list-container">
      <div className="trades-table">
        <div className="table-header">
          <div className="table-cell">Time</div>
          <div className="table-cell">Side</div>
          <div className="table-cell">Entry</div>
          <div className="table-cell">Exit</div>
          <div className="table-cell">PNL</div>
          <div className="table-cell">PNL %</div>
          <div className="table-cell">Status</div>
        </div>
        
        {trades.length === 0 ? (
          <div className="no-trades">No trades yet</div>
        ) : (
          trades.map((trade) => (
            <div key={trade.id} className="table-row">
              <div className="table-cell">{formatTimestamp(trade.timestamp)}</div>
              <div className="table-cell">
                <span className={`side-badge ${trade.side}`}>{trade.side.toUpperCase()}</span>
              </div>
              <div className="table-cell">${trade.entry_price.toFixed(2)}</div>
              <div className="table-cell">
                {trade.exit_price ? `$${trade.exit_price.toFixed(2)}` : '-'}
              </div>
              <div className={`table-cell pnl ${trade.pnl >= 0 ? 'positive' : 'negative'}`}>
                ${trade.pnl ? trade.pnl.toFixed(2) : '0.00'}
              </div>
              <div className={`table-cell pnl ${trade.pnl_percent >= 0 ? 'positive' : 'negative'}`}>
                {trade.pnl_percent ? trade.pnl_percent.toFixed(2) : '0.00'}%
              </div>
              <div className="table-cell">
                <span className={`status-badge ${trade.status.toLowerCase()}`}>
                  {trade.status}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default TradesList;
