import os
import logging
from typing import Dict, Optional
from binance.client import Client
from binance.exceptions import BinanceAPIException
import asyncio


class BinanceClient:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.testnet = config.get('testnet', True)
        self.dry_run = config.get('dry_run', True)
        
        binance_config = config.get('binance', {})
        api_key_env = binance_config.get('api_key_env', 'BINANCE_TESTNET_API_KEY')
        api_secret_env = binance_config.get('api_secret_env', 'BINANCE_TESTNET_API_SECRET')
        
        self.api_key = os.getenv(api_key_env)
        self.api_secret = os.getenv(api_secret_env)
        
        if not self.dry_run and (not self.api_key or not self.api_secret):
            raise ValueError(f"Binance API credentials not found in environment variables: {api_key_env}, {api_secret_env}")
        
        self.client = None
        self.symbol_info = None
    
    async def initialize(self):
        if self.dry_run:
            self.logger.info("Binance client in DRY RUN mode, no actual API calls will be made")
            return
        
        try:
            if self.testnet:
                self.client = Client(
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                    testnet=True
                )
                self.logger.info("Connected to Binance TESTNET")
            else:
                self.client = Client(
                    api_key=self.api_key,
                    api_secret=self.api_secret
                )
                self.logger.warning("Connected to Binance MAINNET - REAL FUNDS AT RISK")
            
            symbol = self.config['trading']['symbol']
            exchange_info = await asyncio.to_thread(self.client.futures_exchange_info)
            
            self.symbol_info = next(
                (s for s in exchange_info['symbols'] if s['symbol'] == symbol),
                None
            )
            
            if not self.symbol_info:
                raise ValueError(f"Symbol {symbol} not found on Binance Futures")
            
            self.logger.info(f"Symbol info loaded for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Binance client: {e}", exc_info=True)
            raise
    
    async def get_account_equity(self) -> float:
        if self.dry_run:
            return 10000.0
        
        try:
            account = await asyncio.to_thread(self.client.futures_account)
            equity = float(account['totalWalletBalance'])
            return equity
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error getting equity: {e}")
            return 10000.0
        except Exception as e:
            self.logger.error(f"Error getting account equity: {e}")
            return 10000.0
    
    def round_quantity(self, quantity: float) -> float:
        if not self.symbol_info:
            return round(quantity, 3)
        
        for filter_info in self.symbol_info['filters']:
            if filter_info['filterType'] == 'LOT_SIZE':
                step_size = float(filter_info['stepSize'])
                precision = len(str(step_size).rstrip('0').split('.')[-1])
                return round(quantity - (quantity % step_size), precision)
        
        return round(quantity, 3)
    
    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict:
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would place {side} order: {quantity} {symbol}")
            return {
                "orderId": 99999,
                "symbol": symbol,
                "status": "NEW",
                "side": side,
                "type": "MARKET",
                "origQty": str(quantity)
            }
        
        try:
            leverage = self.config['trading'].get('leverage', 1)
            await asyncio.to_thread(
                self.client.futures_change_leverage,
                symbol=symbol,
                leverage=leverage
            )
            
            order = await asyncio.to_thread(
                self.client.futures_create_order,
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            
            self.logger.info(f"Order placed: {order['orderId']}")
            
            if stop_loss:
                await self._place_stop_loss(symbol, side, quantity, stop_loss)
            
            if take_profit:
                await self._place_take_profit(symbol, side, quantity, take_profit)
            
            return order
            
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error placing order: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            raise
    
    async def _place_stop_loss(self, symbol: str, side: str, quantity: float, stop_price: float):
        try:
            stop_side = 'SELL' if side == 'BUY' else 'BUY'
            
            order = await asyncio.to_thread(
                self.client.futures_create_order,
                symbol=symbol,
                side=stop_side,
                type='STOP_MARKET',
                stopPrice=stop_price,
                quantity=quantity
            )
            
            self.logger.info(f"Stop loss placed at {stop_price}: {order['orderId']}")
            
        except Exception as e:
            self.logger.error(f"Error placing stop loss: {e}")
    
    async def _place_take_profit(self, symbol: str, side: str, quantity: float, take_profit_price: float):
        try:
            tp_side = 'SELL' if side == 'BUY' else 'BUY'
            
            order = await asyncio.to_thread(
                self.client.futures_create_order,
                symbol=symbol,
                side=tp_side,
                type='TAKE_PROFIT_MARKET',
                stopPrice=take_profit_price,
                quantity=quantity
            )
            
            self.logger.info(f"Take profit placed at {take_profit_price}: {order['orderId']}")
            
        except Exception as e:
            self.logger.error(f"Error placing take profit: {e}")
    
    async def get_order_status(self, symbol: str, order_id: int) -> Dict:
        if self.dry_run:
            return {
                "orderId": order_id,
                "symbol": symbol,
                "status": "FILLED",
                "avgPrice": "50000.0"
            }
        
        try:
            order = await asyncio.to_thread(
                self.client.futures_get_order,
                symbol=symbol,
                orderId=order_id
            )
            return order
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error getting order status: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting order status: {e}")
            raise
    
    async def close(self):
        self.logger.info("Closing Binance client")
        if self.client:
            await asyncio.to_thread(self.client.close_connection)
