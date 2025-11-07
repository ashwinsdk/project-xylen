import logging
import os
import csv
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import aiosqlite


class DataLogger:
    """
    Production-grade data logger with SQLite schema v2
    
    Schema v2 Features:
    - Separate tables for trades, orders, snapshots, model predictions
    - Indexed queries for performance
    - Trade lifecycle tracking (open -> filled -> closed)
    - Model prediction history for backtesting calibration
    - Feature snapshots at decision time
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        db_config = config.get('database', {})
        self.sqlite_path = db_config.get('sqlite_path', './data/xylen.db')
        self.csv_path = db_config.get('csv_path', './data/trades.csv')
        
        os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        
        self.db = None
    
    async def initialize(self):
        """Initialize database with schema v2"""
        self.db = await aiosqlite.connect(self.sqlite_path)
        
        # === TRADES TABLE ===
        # Complete trade lifecycle from open to close
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity REAL NOT NULL,
                pnl REAL,
                pnl_percent REAL,
                status TEXT NOT NULL,
                entry_order_id INTEGER,
                exit_order_id INTEGER,
                entry_time REAL NOT NULL,
                exit_time REAL,
                hold_duration REAL,
                decision_confidence REAL,
                decision_expected_value REAL,
                risk_exposure REAL,
                max_drawdown REAL,
                snapshot_id INTEGER,
                FOREIGN KEY(snapshot_id) REFERENCES snapshots(snapshot_id)
            )
        """)
        
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
        
        # === ORDERS TABLE ===
        # Individual order tracking (entry, exit, stop loss, take profit)
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY,
                trade_id INTEGER,
                timestamp REAL NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                type TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL,
                filled_qty REAL DEFAULT 0,
                avg_fill_price REAL DEFAULT 0,
                status TEXT NOT NULL,
                order_type_label TEXT,
                created_at REAL NOT NULL,
                updated_at REAL,
                FOREIGN KEY(trade_id) REFERENCES trades(trade_id)
            )
        """)
        
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_orders_timestamp ON orders(timestamp)")
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_orders_trade_id ON orders(trade_id)")
        
        # === SNAPSHOTS TABLE ===
        # Market snapshots at decision time with all 29+ features
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                symbol TEXT NOT NULL,
                current_price REAL NOT NULL,
                bid REAL,
                ask REAL,
                spread REAL,
                volume_24h REAL,
                price_change_24h REAL,
                features TEXT NOT NULL,
                raw_data TEXT
            )
        """)
        
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON snapshots(timestamp)")
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_symbol ON snapshots(symbol)")
        
        # === MODEL_PREDICTIONS TABLE ===
        # Individual model predictions for ensemble analysis
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS model_predictions (
                prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                snapshot_id INTEGER,
                model_name TEXT NOT NULL,
                model_endpoint TEXT,
                action TEXT NOT NULL,
                confidence REAL NOT NULL,
                probability REAL,
                expected_return REAL,
                latency_ms REAL,
                raw_response TEXT,
                outcome_pnl REAL,
                outcome_correct INTEGER,
                FOREIGN KEY(snapshot_id) REFERENCES snapshots(snapshot_id)
            )
        """)
        
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON model_predictions(timestamp)")
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_predictions_model ON model_predictions(model_name)")
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_predictions_snapshot ON model_predictions(snapshot_id)")
        
        # === ENSEMBLE_DECISIONS TABLE ===
        # Final ensemble decisions with metadata
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS ensemble_decisions (
                decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                snapshot_id INTEGER,
                final_action TEXT NOT NULL,
                final_confidence REAL NOT NULL,
                expected_value REAL,
                aggregation_method TEXT,
                model_count INTEGER,
                model_agreement REAL,
                uncertainty REAL,
                risk_check_passed INTEGER,
                position_size REAL,
                rejected INTEGER DEFAULT 0,
                rejection_reason TEXT,
                FOREIGN KEY(snapshot_id) REFERENCES snapshots(snapshot_id)
            )
        """)
        
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON ensemble_decisions(timestamp)")
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_decisions_action ON ensemble_decisions(final_action)")
        
        # === SYSTEM_EVENTS TABLE ===
        # System events (startup, shutdown, errors, circuit breaker trips)
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS system_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                component TEXT,
                message TEXT,
                details TEXT
            )
        """)
        
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON system_events(timestamp)")
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON system_events(event_type)")
        
        await self.db.commit()
        
        self.logger.info(f"Database schema v2 initialized at {self.sqlite_path}")
        
        # Initialize CSV file if it doesn't exist
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'symbol', 'side', 'entry_price', 'exit_price',
                    'quantity', 'pnl', 'pnl_percent', 'status', 'confidence',
                    'entry_time', 'exit_time', 'hold_duration'
                ])
    
    # ============================================================
    # LOGGING METHODS - SCHEMA V2
    # ============================================================
    
    async def log_snapshot(self, snapshot: Dict) -> int:
        """
        Log market snapshot with all features
        
        Returns:
            snapshot_id for foreign key references
        """
        try:
            timestamp = datetime.utcnow().timestamp()
            
            indicators = snapshot.get('indicators', {})
            spread = snapshot.get('ask', 0) - snapshot.get('bid', 0)
            
            cursor = await self.db.execute("""
                INSERT INTO snapshots (
                    timestamp, symbol, current_price, bid, ask, spread,
                    volume_24h, price_change_24h, features, raw_data
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                snapshot['symbol'],
                snapshot.get('current_price', 0),
                snapshot.get('bid', 0),
                snapshot.get('ask', 0),
                spread,
                snapshot.get('volume_24h', 0),
                snapshot.get('price_change_24h', 0),
                json.dumps(indicators),
                json.dumps(snapshot)
            ))
            
            await self.db.commit()
            snapshot_id = cursor.lastrowid
            
            self.logger.debug(f"Snapshot logged: {snapshot_id}")
            return snapshot_id
            
        except Exception as e:
            self.logger.error(f"Error logging snapshot: {e}", exc_info=True)
            return -1
    
    async def log_model_prediction(
        self,
        model_name: str,
        snapshot_id: int,
        action: str,
        confidence: float,
        probability: Optional[float] = None,
        expected_return: Optional[float] = None,
        latency_ms: Optional[float] = None,
        raw_response: Optional[Dict] = None
    ) -> int:
        """Log individual model prediction"""
        try:
            timestamp = datetime.utcnow().timestamp()
            
            cursor = await self.db.execute("""
                INSERT INTO model_predictions (
                    timestamp, snapshot_id, model_name, action, confidence,
                    probability, expected_return, latency_ms, raw_response
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                snapshot_id,
                model_name,
                action,
                confidence,
                probability,
                expected_return,
                latency_ms,
                json.dumps(raw_response) if raw_response else None
            ))
            
            await self.db.commit()
            prediction_id = cursor.lastrowid
            
            self.logger.debug(f"Prediction logged: {model_name} -> {action}")
            return prediction_id
            
        except Exception as e:
            self.logger.error(f"Error logging prediction: {e}", exc_info=True)
            return -1
    
    async def log_ensemble_decision(
        self,
        snapshot_id: int,
        final_action: str,
        final_confidence: float,
        expected_value: float,
        aggregation_method: str,
        model_count: int,
        model_agreement: float,
        uncertainty: float,
        risk_check_passed: bool,
        position_size: Optional[float] = None,
        rejected: bool = False,
        rejection_reason: Optional[str] = None
    ) -> int:
        """Log ensemble decision"""
        try:
            timestamp = datetime.utcnow().timestamp()
            
            cursor = await self.db.execute("""
                INSERT INTO ensemble_decisions (
                    timestamp, snapshot_id, final_action, final_confidence,
                    expected_value, aggregation_method, model_count, model_agreement,
                    uncertainty, risk_check_passed, position_size, rejected, rejection_reason
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                snapshot_id,
                final_action,
                final_confidence,
                expected_value,
                aggregation_method,
                model_count,
                model_agreement,
                uncertainty,
                1 if risk_check_passed else 0,
                position_size,
                1 if rejected else 0,
                rejection_reason
            ))
            
            await self.db.commit()
            decision_id = cursor.lastrowid
            
            self.logger.debug(f"Ensemble decision logged: {final_action} (confidence={final_confidence:.3f})")
            return decision_id
            
        except Exception as e:
            self.logger.error(f"Error logging ensemble decision: {e}", exc_info=True)
            return -1
    
    async def log_trade_open(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        entry_order_id: int,
        snapshot_id: int,
        decision_confidence: float,
        decision_expected_value: float,
        risk_exposure: float
    ) -> int:
        """Log trade opening"""
        try:
            timestamp = datetime.utcnow().timestamp()
            
            cursor = await self.db.execute("""
                INSERT INTO trades (
                    timestamp, symbol, side, entry_price, quantity, status,
                    entry_order_id, entry_time, snapshot_id, decision_confidence,
                    decision_expected_value, risk_exposure
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                symbol,
                side,
                entry_price,
                quantity,
                'OPEN',
                entry_order_id,
                timestamp,
                snapshot_id,
                decision_confidence,
                decision_expected_value,
                risk_exposure
            ))
            
            await self.db.commit()
            trade_id = cursor.lastrowid
            
            self.logger.info(f"Trade opened: {trade_id} - {side} {quantity} {symbol} @ {entry_price}")
            return trade_id
            
        except Exception as e:
            self.logger.error(f"Error logging trade open: {e}", exc_info=True)
            return -1
    
    async def log_trade_close(
        self,
        trade_id: int,
        exit_price: float,
        exit_order_id: int,
        pnl: float,
        pnl_percent: float,
        status: str = 'CLOSED'
    ):
        """Log trade closing"""
        try:
            timestamp = datetime.utcnow().timestamp()
            
            # Get entry time to calculate hold duration
            cursor = await self.db.execute(
                "SELECT entry_time FROM trades WHERE trade_id = ?",
                (trade_id,)
            )
            row = await cursor.fetchone()
            entry_time = row[0] if row else timestamp
            hold_duration = timestamp - entry_time
            
            await self.db.execute("""
                UPDATE trades
                SET exit_price = ?, exit_order_id = ?, exit_time = ?,
                    pnl = ?, pnl_percent = ?, status = ?, hold_duration = ?
                WHERE trade_id = ?
            """, (
                exit_price,
                exit_order_id,
                timestamp,
                pnl,
                pnl_percent,
                status,
                hold_duration,
                trade_id
            ))
            
            await self.db.commit()
            
            # Also log to CSV
            cursor = await self.db.execute(
                "SELECT * FROM trades WHERE trade_id = ?",
                (trade_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                with open(self.csv_path, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        datetime.utcfromtimestamp(row[1]).isoformat(),  # timestamp
                        row[2],  # symbol
                        row[3],  # side
                        row[4],  # entry_price
                        row[5],  # exit_price
                        row[6],  # quantity
                        row[7],  # pnl
                        row[8],  # pnl_percent
                        row[9],  # status
                        row[15],  # decision_confidence
                        datetime.utcfromtimestamp(row[12]).isoformat(),  # entry_time
                        datetime.utcfromtimestamp(row[13]).isoformat() if row[13] else '',  # exit_time
                        row[14]  # hold_duration
                    ])
            
            self.logger.info(f"Trade closed: {trade_id} - PNL={pnl:.2f} ({pnl_percent:.2f}%), duration={hold_duration:.1f}s")
            
        except Exception as e:
            self.logger.error(f"Error logging trade close: {e}", exc_info=True)
    
    async def log_order(
        self,
        order_id: int,
        trade_id: Optional[int],
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float],
        status: str,
        order_type_label: str = 'ENTRY'
    ):
        """Log individual order"""
        try:
            timestamp = datetime.utcnow().timestamp()
            
            await self.db.execute("""
                INSERT OR REPLACE INTO orders (
                    order_id, trade_id, timestamp, symbol, side, type,
                    quantity, price, status, order_type_label, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                trade_id,
                timestamp,
                symbol,
                side,
                order_type,
                quantity,
                price,
                status,
                order_type_label,
                timestamp,
                timestamp
            ))
            
            await self.db.commit()
            self.logger.debug(f"Order logged: {order_id} ({order_type_label})")
            
        except Exception as e:
            self.logger.error(f"Error logging order: {e}", exc_info=True)
    
    async def log_system_event(
        self,
        event_type: str,
        severity: str,
        component: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        """Log system event"""
        try:
            timestamp = datetime.utcnow().timestamp()
            
            await self.db.execute("""
                INSERT INTO system_events (
                    timestamp, event_type, severity, component, message, details
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                event_type,
                severity,
                component,
                message,
                json.dumps(details) if details else None
            ))
            
            await self.db.commit()
            self.logger.debug(f"System event logged: {event_type} ({severity})")
            
        except Exception as e:
            self.logger.error(f"Error logging system event: {e}", exc_info=True)
    
    # ============================================================
    # QUERY METHODS - ANALYTICS & REPORTING
    # ============================================================
    
    async def get_recent_trades(self, limit: int = 100) -> List[Dict]:
        """Get recent trades with all details"""
        try:
            cursor = await self.db.execute("""
                SELECT trade_id, timestamp, symbol, side, entry_price, exit_price,
                       quantity, pnl, pnl_percent, status, entry_time, exit_time,
                       hold_duration, decision_confidence
                FROM trades
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            rows = await cursor.fetchall()
            
            trades = []
            for row in rows:
                trades.append({
                    'trade_id': row[0],
                    'timestamp': datetime.utcfromtimestamp(row[1]).isoformat() if row[1] else None,
                    'symbol': row[2],
                    'side': row[3],
                    'entry_price': row[4],
                    'exit_price': row[5],
                    'quantity': row[6],
                    'pnl': row[7],
                    'pnl_percent': row[8],
                    'status': row[9],
                    'entry_time': datetime.utcfromtimestamp(row[10]).isoformat() if row[10] else None,
                    'exit_time': datetime.utcfromtimestamp(row[11]).isoformat() if row[11] else None,
                    'hold_duration': row[12],
                    'confidence': row[13]
                })
            
            return trades
            
        except Exception as e:
            self.logger.error(f"Error getting recent trades: {e}", exc_info=True)
            return []
    
    async def get_model_performance_stats(self, model_name: Optional[str] = None, days: int = 7) -> Dict:
        """Get model prediction accuracy stats"""
        try:
            cutoff_timestamp = (datetime.utcnow() - timedelta(days=days)).timestamp()
            
            if model_name:
                cursor = await self.db.execute("""
                    SELECT
                        model_name,
                        COUNT(*) as total_predictions,
                        SUM(CASE WHEN outcome_correct = 1 THEN 1 ELSE 0 END) as correct_predictions,
                        AVG(confidence) as avg_confidence,
                        AVG(latency_ms) as avg_latency_ms
                    FROM model_predictions
                    WHERE model_name = ? AND timestamp >= ? AND outcome_correct IS NOT NULL
                    GROUP BY model_name
                """, (model_name, cutoff_timestamp))
            else:
                cursor = await self.db.execute("""
                    SELECT
                        model_name,
                        COUNT(*) as total_predictions,
                        SUM(CASE WHEN outcome_correct = 1 THEN 1 ELSE 0 END) as correct_predictions,
                        AVG(confidence) as avg_confidence,
                        AVG(latency_ms) as avg_latency_ms
                    FROM model_predictions
                    WHERE timestamp >= ? AND outcome_correct IS NOT NULL
                    GROUP BY model_name
                """, (cutoff_timestamp,))
            
            rows = await cursor.fetchall()
            
            stats = {}
            for row in rows:
                model = row[0]
                total = row[1]
                correct = row[2] or 0
                accuracy = correct / total if total > 0 else 0
                
                stats[model] = {
                    'total_predictions': total,
                    'correct_predictions': correct,
                    'accuracy': accuracy,
                    'avg_confidence': row[3],
                    'avg_latency_ms': row[4]
                }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting model performance stats: {e}", exc_info=True)
            return {}
    
    async def get_performance_stats(self) -> Dict:
        try:
            cursor = await self.db.execute("""
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    MAX(pnl) as max_win,
                    MIN(pnl) as max_loss
                FROM trades
                WHERE status != 'OPEN'
            """)
            
            row = await cursor.fetchone()
            
            if row and row[0] > 0:
                return {
                    'total_trades': row[0],
                    'winning_trades': row[1] or 0,
                    'losing_trades': row[2] or 0,
                    'win_rate': (row[1] or 0) / row[0] if row[0] > 0 else 0,
                    'total_pnl': row[3] or 0,
                    'avg_pnl': row[4] or 0,
                    'max_win': row[5] or 0,
                    'max_loss': row[6] or 0
                }
            else:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'total_pnl': 0,
                    'avg_pnl': 0,
                    'max_win': 0,
                    'max_loss': 0
                }
            
        except Exception as e:
            self.logger.error(f"Error getting performance stats: {e}")
            return {}
    
    async def close(self):
        if self.db:
            await self.db.close()
            self.logger.info("Database connection closed")
