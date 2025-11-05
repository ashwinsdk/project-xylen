import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yaml
import signal

from binance_client import BinanceClient
from ensemble import EnsembleAggregator
from data_logger import DataLogger
from market_data import MarketDataCollector
from api_server import DashboardAPIServer


class TradingCoordinator:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Trading Coordinator")
        
        self.binance_client = BinanceClient(self.config)
        self.ensemble = EnsembleAggregator(self.config)
        self.data_logger = DataLogger(self.config)
        self.market_data = MarketDataCollector(self.config)
        
        dashboard_config = self.config.get('dashboard', {})
        if dashboard_config.get('enabled', True):
            self.api_server = DashboardAPIServer(
                coordinator=self,
                port=dashboard_config.get('port', 5500),
                host=dashboard_config.get('host', '0.0.0.0')
            )
        else:
            self.api_server = None
        
        self.is_running = False
        self.current_position = None
        self.daily_stats = {
            "trades": 0,
            "pnl": 0.0,
            "consecutive_losses": 0,
            "start_time": datetime.utcnow()
        }
        
    def _load_config(self, config_path: str) -> Dict:
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config
    
    def _setup_logging(self):
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        log_file = log_config.get('file', './logs/coordinator.log')
        
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    async def start(self):
        self.logger.info("Starting Trading Coordinator")
        self.logger.info(f"Dry Run Mode: {self.config.get('dry_run', True)}")
        self.logger.info(f"Testnet Mode: {self.config.get('testnet', True)}")
        
        # CRITICAL FIX: Initialize market data collector first
        await self.market_data.initialize()
        await self.data_logger.initialize()
        await self.binance_client.initialize()
        
        if self.api_server:
            await self.api_server.start()
        
        self.is_running = True
        
        try:
            await asyncio.gather(
                self._main_loop(),
                self._health_check_loop(),
                self._daily_reset_loop()
            )
        except asyncio.CancelledError:
            self.logger.info("Coordinator tasks cancelled")
        except Exception as e:
            self.logger.error(f"Error in coordinator: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def _main_loop(self):
        heartbeat_interval = self.config.get('timing', {}).get('heartbeat_interval', 60)
        
        while self.is_running:
            try:
                if self._should_pause_trading():
                    self.logger.warning("Trading paused due to safety limits")
                    await asyncio.sleep(heartbeat_interval)
                    continue
                
                if self.current_position:
                    await self._monitor_open_position()
                else:
                    await self._analyze_and_trade()
                
                await asyncio.sleep(heartbeat_interval)
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(heartbeat_interval)
    
    async def _analyze_and_trade(self):
        try:
            snapshot = await self.market_data.get_snapshot()
            
            self.logger.info(f"Market snapshot - Price: {snapshot.get('current_price')}, "
                           f"5m candles: {len(snapshot.get('candles_5m', []))}, "
                           f"1h candles: {len(snapshot.get('candles_1h', []))}")
            
            # Log key indicators
            indicators = snapshot.get('indicators', {})
            if indicators:
                self.logger.info(f"Indicators - RSI: {indicators.get('rsi', 'N/A'):.2f}, "
                               f"Volume: {indicators.get('volume', 0):.2f}, "
                               f"EMA20: {indicators.get('ema_20', 'N/A')}")
            
            model_responses = await self.ensemble.get_model_predictions(snapshot)
            
            if not model_responses:
                self.logger.warning("No model responses received")
                return
            
            decision = self.ensemble.aggregate(model_responses)
            
            await self.data_logger.log_analysis(snapshot, model_responses, decision)
            
            self.logger.info(f"Ensemble decision: {decision['action']} (confidence: {decision['confidence']:.2f})")
            
            if decision['action'] in ['long', 'short'] and decision['confidence'] >= self.config['ensemble']['threshold']:
                await self._place_trade(decision, snapshot)
            
        except Exception as e:
            self.logger.error(f"Error in analyze_and_trade: {e}", exc_info=True)
    
    async def _place_trade(self, decision: Dict, snapshot: Dict):
        try:
            if self.config.get('dry_run', True):
                self.logger.info(f"[DRY RUN] Would place {decision['action']} order")
                return
            
            max_positions = self.config['trading'].get('max_open_positions', 1)
            if self.current_position:
                self.logger.info("Already have open position, skipping trade")
                return
            
            equity = await self.binance_client.get_account_equity()
            position_size_fraction = self.config['trading'].get('position_size_fraction', 0.1)
            position_value = equity * position_size_fraction
            
            current_price = float(snapshot['current_price'])
            quantity = position_value / current_price
            
            quantity = self.binance_client.round_quantity(quantity)
            
            order = await self.binance_client.place_order(
                symbol=self.config['trading']['symbol'],
                side=decision['action'].upper(),
                quantity=quantity,
                stop_loss=decision.get('stop'),
                take_profit=decision.get('take_profit')
            )
            
            self.current_position = {
                "order": order,
                "decision": decision,
                "entry_time": datetime.utcnow(),
                "entry_price": current_price,
                "quantity": quantity,
                "side": decision['action']
            }
            
            await self.data_logger.log_trade(self.current_position)
            
            self.logger.info(f"Placed {decision['action']} order: {order}")
            
        except Exception as e:
            self.logger.error(f"Error placing trade: {e}", exc_info=True)
    
    async def _monitor_open_position(self):
        try:
            if not self.current_position:
                return
            
            order_check_interval = self.config.get('timing', {}).get('order_check_interval', 10)
            
            order_id = self.current_position['order'].get('orderId')
            symbol = self.config['trading']['symbol']
            
            order_status = await self.binance_client.get_order_status(symbol, order_id)
            
            if order_status['status'] in ['FILLED', 'CLOSED', 'CANCELED', 'EXPIRED']:
                await self._close_position(order_status)
            
            await asyncio.sleep(order_check_interval)
            
        except Exception as e:
            self.logger.error(f"Error monitoring position: {e}", exc_info=True)
    
    async def _close_position(self, order_status: Dict):
        try:
            exit_price = float(order_status.get('avgPrice', self.current_position['entry_price']))
            entry_price = self.current_position['entry_price']
            quantity = self.current_position['quantity']
            side = self.current_position['side']
            
            if side == 'long':
                pnl = (exit_price - entry_price) * quantity
            else:
                pnl = (entry_price - exit_price) * quantity
            
            pnl_percent = (pnl / (entry_price * quantity)) * 100
            
            result = {
                "position": self.current_position,
                "exit_time": datetime.utcnow(),
                "exit_price": exit_price,
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "status": order_status['status']
            }
            
            await self.data_logger.log_trade_result(result)
            
            self.daily_stats['trades'] += 1
            self.daily_stats['pnl'] += pnl
            
            if pnl < 0:
                self.daily_stats['consecutive_losses'] += 1
            else:
                self.daily_stats['consecutive_losses'] = 0
            
            self.logger.info(f"Position closed: PNL={pnl:.2f} ({pnl_percent:.2f}%)")
            
            if self.config.get('retraining', {}).get('send_feedback_to_models', True):
                await self._send_feedback_to_models(result)
            
            self.current_position = None
            
        except Exception as e:
            self.logger.error(f"Error closing position: {e}", exc_info=True)
    
    async def _send_feedback_to_models(self, result: Dict):
        try:
            feedback_data = {
                "snapshot": result['position'].get('snapshot'),
                "decision": result['position']['decision'],
                "outcome": {
                    "pnl": result['pnl'],
                    "pnl_percent": result['pnl_percent'],
                    "success": result['pnl'] > 0
                }
            }
            
            await self.ensemble.send_retrain_feedback(feedback_data)
            
        except Exception as e:
            self.logger.error(f"Error sending feedback to models: {e}", exc_info=True)
    
    async def _health_check_loop(self):
        health_check_interval = self.config.get('timing', {}).get('health_check_interval', 300)
        
        while self.is_running:
            try:
                await self.ensemble.check_model_health()
                await asyncio.sleep(health_check_interval)
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}", exc_info=True)
                await asyncio.sleep(health_check_interval)
    
    async def _daily_reset_loop(self):
        while self.is_running:
            try:
                now = datetime.utcnow()
                next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                sleep_seconds = (next_reset - now).total_seconds()
                
                await asyncio.sleep(sleep_seconds)
                
                self.logger.info(f"Daily reset: trades={self.daily_stats['trades']}, pnl={self.daily_stats['pnl']:.2f}")
                
                self.daily_stats = {
                    "trades": 0,
                    "pnl": 0.0,
                    "consecutive_losses": 0,
                    "start_time": datetime.utcnow()
                }
                
            except Exception as e:
                self.logger.error(f"Error in daily reset loop: {e}", exc_info=True)
                await asyncio.sleep(3600)
    
    def _should_pause_trading(self) -> bool:
        safety = self.config.get('safety', {})
        
        if self.daily_stats['trades'] >= safety.get('max_daily_trades', 20):
            return True
        
        if self.daily_stats['pnl'] < 0:
            equity = 10000
            loss_percent = abs(self.daily_stats['pnl']) / equity
            
            if loss_percent >= safety.get('emergency_shutdown_loss_percent', 0.2):
                self.logger.critical(f"EMERGENCY SHUTDOWN: Daily loss {loss_percent*100:.1f}%")
                self.is_running = False
                return True
            
            if loss_percent >= safety.get('max_daily_loss_percent', 0.1):
                return True
        
        if self.daily_stats['consecutive_losses'] >= safety.get('circuit_breaker_consecutive_losses', 5):
            return True
        
        return False
    
    async def shutdown(self):
        self.logger.info("Shutting down Trading Coordinator")
        self.is_running = False
        
        if self.current_position:
            self.logger.warning("Shutting down with open position")
        
        if self.api_server:
            await self.api_server.stop()
        
        await self.market_data.close()
        await self.data_logger.close()
        await self.binance_client.close()


def signal_handler(coordinator):
    def handler(signum, frame):
        logging.info(f"Received signal {signum}, shutting down...")
        coordinator.is_running = False
    return handler


async def main():
    config_path = os.getenv('CONFIG_PATH', 'config.yaml')
    
    if not os.path.exists(config_path):
        config_path = '../config.yaml'
    
    coordinator = TradingCoordinator(config_path)
    
    signal.signal(signal.SIGINT, signal_handler(coordinator))
    signal.signal(signal.SIGTERM, signal_handler(coordinator))
    
    await coordinator.start()


if __name__ == "__main__":
    asyncio.run(main())