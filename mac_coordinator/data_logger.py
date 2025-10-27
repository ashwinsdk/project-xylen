import logging
import os
import csv
import json
from typing import Dict
from datetime import datetime
import aiosqlite


class DataLogger:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        db_config = config.get('database', {})
        self.sqlite_path = db_config.get('sqlite_path', './data/trades.db')
        self.csv_path = db_config.get('csv_path', './data/trades.csv')
        
        os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        
        self.db = None
    
    async def initialize(self):
        self.db = await aiosqlite.connect(self.sqlite_path)
        
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity REAL NOT NULL,
                pnl REAL,
                pnl_percent REAL,
                status TEXT,
                order_id INTEGER,
                entry_time TEXT,
                exit_time TEXT,
                decision_data TEXT,
                snapshot_data TEXT
            )
        """)
        
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS analysis_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                snapshot_data TEXT NOT NULL,
                model_responses TEXT NOT NULL,
                ensemble_decision TEXT NOT NULL
            )
        """)
        
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS model_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                model_name TEXT NOT NULL,
                prediction_data TEXT NOT NULL,
                outcome_data TEXT,
                correct INTEGER
            )
        """)
        
        await self.db.commit()
        
        self.logger.info(f"Database initialized at {self.sqlite_path}")
        
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'symbol', 'side', 'entry_price', 'exit_price',
                    'quantity', 'pnl', 'pnl_percent', 'status', 'confidence',
                    'entry_time', 'exit_time'
                ])
    
    async def log_analysis(self, snapshot: Dict, model_responses: list, decision: Dict):
        try:
            timestamp = datetime.utcnow().isoformat()
            
            await self.db.execute("""
                INSERT INTO analysis_log (timestamp, snapshot_data, model_responses, ensemble_decision)
                VALUES (?, ?, ?, ?)
            """, (
                timestamp,
                json.dumps(snapshot),
                json.dumps(model_responses),
                json.dumps(decision)
            ))
            
            await self.db.commit()
            
            self.logger.debug(f"Analysis logged at {timestamp}")
            
        except Exception as e:
            self.logger.error(f"Error logging analysis: {e}")
    
    async def log_trade(self, position: Dict):
        try:
            timestamp = datetime.utcnow().isoformat()
            order = position.get('order', {})
            decision = position.get('decision', {})
            
            await self.db.execute("""
                INSERT INTO trades (
                    timestamp, symbol, side, entry_price, quantity, status,
                    order_id, entry_time, decision_data
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                self.config['trading']['symbol'],
                position['side'],
                position['entry_price'],
                position['quantity'],
                'OPEN',
                order.get('orderId'),
                position['entry_time'].isoformat(),
                json.dumps(decision)
            ))
            
            await self.db.commit()
            
            self.logger.info(f"Trade logged: {position['side']} at {position['entry_price']}")
            
        except Exception as e:
            self.logger.error(f"Error logging trade: {e}")
    
    async def log_trade_result(self, result: Dict):
        try:
            position = result['position']
            order = position.get('order', {})
            
            cursor = await self.db.execute("""
                UPDATE trades
                SET exit_price = ?, exit_time = ?, pnl = ?, pnl_percent = ?, status = ?
                WHERE order_id = ?
            """, (
                result['exit_price'],
                result['exit_time'].isoformat(),
                result['pnl'],
                result['pnl_percent'],
                result['status'],
                order.get('orderId')
            ))
            
            await self.db.commit()
            
            with open(self.csv_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.utcnow().isoformat(),
                    self.config['trading']['symbol'],
                    position['side'],
                    position['entry_price'],
                    result['exit_price'],
                    position['quantity'],
                    result['pnl'],
                    result['pnl_percent'],
                    result['status'],
                    position.get('decision', {}).get('confidence', 0.0),
                    position['entry_time'].isoformat(),
                    result['exit_time'].isoformat()
                ])
            
            self.logger.info(f"Trade result logged: PNL={result['pnl']:.2f} ({result['pnl_percent']:.2f}%)")
            
        except Exception as e:
            self.logger.error(f"Error logging trade result: {e}")
    
    async def log_model_performance(self, model_name: str, prediction: Dict, outcome: Dict = None):
        try:
            timestamp = datetime.utcnow().isoformat()
            
            correct = None
            if outcome:
                predicted_direction = prediction.get('action')
                actual_profit = outcome.get('pnl', 0)
                
                if predicted_direction == 'long' and actual_profit > 0:
                    correct = 1
                elif predicted_direction == 'short' and actual_profit > 0:
                    correct = 1
                elif predicted_direction == 'hold':
                    correct = None
                else:
                    correct = 0
            
            await self.db.execute("""
                INSERT INTO model_performance (timestamp, model_name, prediction_data, outcome_data, correct)
                VALUES (?, ?, ?, ?, ?)
            """, (
                timestamp,
                model_name,
                json.dumps(prediction),
                json.dumps(outcome) if outcome else None,
                correct
            ))
            
            await self.db.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging model performance: {e}")
    
    async def get_recent_trades(self, limit: int = 100) -> list:
        try:
            cursor = await self.db.execute("""
                SELECT * FROM trades
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            rows = await cursor.fetchall()
            
            trades = []
            for row in rows:
                trades.append({
                    'id': row[0],
                    'timestamp': row[1],
                    'symbol': row[2],
                    'side': row[3],
                    'entry_price': row[4],
                    'exit_price': row[5],
                    'quantity': row[6],
                    'pnl': row[7],
                    'pnl_percent': row[8],
                    'status': row[9]
                })
            
            return trades
            
        except Exception as e:
            self.logger.error(f"Error getting recent trades: {e}")
            return []
    
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
