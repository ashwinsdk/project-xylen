"""
Project Xylen - Binance Futures Client
Python 3.10.12 compatible
Production-grade Binance Futures API client with:
- Order state machine with SQLite persistence
- Rate limiting with token bucket algorithm
- Exponential backoff with tenacity
- Testnet and production endpoint support
- Margin mode configuration (CROSSED/ISOLATED)
"""

import os
import logging
import time
import hmac
import hashlib
import aiosqlite
from typing import Dict, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass
import asyncio
import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)


class OrderStatus(Enum):
    """Order status states"""
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderSide(Enum):
    """Order side"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"


@dataclass
class OrderState:
    """Order state for persistence"""
    order_id: int
    symbol: str
    side: str
    type: str
    quantity: float
    price: Optional[float]
    status: str
    filled_qty: float
    avg_price: float
    timestamp: float
    stop_loss_order_id: Optional[int] = None
    take_profit_order_id: Optional[int] = None


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, rate_per_minute: int, burst: int = None):
        self.rate = rate_per_minute / 60.0
        self.burst = burst or rate_per_minute
        self.tokens = self.burst
        self.last_update = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire a token, waiting if necessary"""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


class BinanceClient:
    """
    Production-grade Binance Futures API client
    
    Features:
    - Rate limiting with token bucket
    - Exponential backoff for transient errors
    - Order state persistence in SQLite
    - Testnet and production support
    - Margin mode configuration
    - Order monitoring and status tracking
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.testnet = config.get('testnet', True)
        self.dry_run = config.get('dry_run', False)
        
        binance_config = config.get('binance', {})
        trading_config = config.get('trading', {})
        
        # API endpoints
        if self.testnet:
            self.base_url = binance_config.get('testnet_base_url', 'https://testnet.binancefuture.com')
        else:
            self.base_url = binance_config.get('production_base_url', 'https://fapi.binance.com')
        
        # API credentials from environment
        api_key_env = binance_config.get('api_key_env', 'qbbZMu6CwZnInHjyYbUXHZF4u1blm9bYhvsD13QMJFVrmrA1pCZ6cAlJcCvoVmMM')
        api_secret_env = binance_config.get('api_secret_env', 'tSWmZfFY29psYznJgmhDTMQhUBlXSoo58uu41rdxew66SmI6haaPMqzmt415GDND')
        
        self.api_key = os.getenv(api_key_env)
        self.api_secret = os.getenv(api_secret_env)
        
        if not self.dry_run:
            if not self.api_key or not self.api_secret:
                raise ValueError(f"API credentials not found in environment: {api_key_env}, {api_secret_env}")
        
        # Rate limiting
        rate_limit = binance_config.get('rate_limit_per_minute', 1200)
        buffer = binance_config.get('rate_limit_buffer', 0.8)
        self.rate_limiter = RateLimiter(int(rate_limit * buffer))
        self.order_rate_limiter = RateLimiter(
            binance_config.get('rate_limit_orders_per_10s', 50) * 6
        )
        
        # Trading parameters
        self.symbol = trading_config.get('symbol', 'BTCUSDT')
        self.leverage = trading_config.get('leverage', 1)
        self.margin_mode = trading_config.get('margin_mode', 'CROSSED')
        
        # State
        self.session: Optional[aiohttp.ClientSession] = None
        self.symbol_info: Optional[Dict] = None
        self.order_db_path = './data/orders.db'
        
        self.logger.info(f"BinanceClient initialized: testnet={self.testnet}, "
                        f"dry_run={self.dry_run}, symbol={self.symbol}")
    
    async def initialize(self):
        """Initialize client, fetch symbol info, setup leverage and margin"""
        if self.dry_run:
            self.logger.info("Binance client in DRY RUN mode")
            return
        
        # Create aiohttp session
        self.session = aiohttp.ClientSession(headers={
            'X-MBX-APIKEY': self.api_key
        })
        
        # Initialize order database
        await self._init_order_db()
        
        # Fetch symbol info
        await self._fetch_symbol_info()
        
        # Set leverage and margin mode
        await self._set_leverage(self.symbol, self.leverage)
        await self._set_margin_mode(self.symbol, self.margin_mode)
        
        # Test connection
        await self._ping()
        
        self.logger.info(f"Connected to Binance {'TESTNET' if self.testnet else 'PRODUCTION'}")
    
    async def _init_order_db(self):
        """Initialize SQLite database for order state persistence"""
        os.makedirs(os.path.dirname(self.order_db_path), exist_ok=True)
        
        async with aiosqlite.connect(self.order_db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    order_id INTEGER PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    type TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL,
                    status TEXT NOT NULL,
                    filled_qty REAL DEFAULT 0,
                    avg_price REAL DEFAULT 0,
                    timestamp REAL NOT NULL,
                    stop_loss_order_id INTEGER,
                    take_profit_order_id INTEGER
                )
            ''')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_orders_timestamp ON orders(timestamp)')
            await db.commit()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        signed: bool = False,
        **kwargs
    ) -> Dict:
        """Make HTTP request with rate limiting and retries"""
        await self.rate_limiter.acquire()
        
        url = f"{self.base_url}{endpoint}"
        
        if signed:
            # Add timestamp and signature
            timestamp = int(time.time() * 1000)
            params = kwargs.get('params', {})
            params['timestamp'] = timestamp
            
            query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            params['signature'] = signature
            kwargs['params'] = params
        
        async with self.session.request(method, url, **kwargs) as response:
            data = await response.json()
            
            if response.status != 200:
                self.logger.error(f"API error {response.status}: {data}")
                raise Exception(f"Binance API error: {data.get('msg', 'Unknown error')}")
            
            return data
    
    async def _ping(self):
        """Test API connectivity"""
        await self._request('GET', '/fapi/v1/ping')
        self.logger.info("API connectivity verified")
    
    async def _fetch_symbol_info(self):
        """Fetch and cache symbol information"""
        data = await self._request('GET', '/fapi/v1/exchangeInfo')
        
        for symbol_data in data['symbols']:
            if symbol_data['symbol'] == self.symbol:
                self.symbol_info = symbol_data
                break
        
        if not self.symbol_info:
            raise ValueError(f"Symbol {self.symbol} not found")
        
        self.logger.info(f"Symbol info loaded for {self.symbol}")
    
    async def _set_leverage(self, symbol: str, leverage: int):
        """Set leverage for symbol"""
        try:
            await self._request(
                'POST',
                '/fapi/v1/leverage',
                signed=True,
                params={'symbol': symbol, 'leverage': leverage}
            )
            self.logger.info(f"Leverage set to {leverage}x for {symbol}")
        except Exception as e:
            self.logger.warning(f"Failed to set leverage: {e}")
    
    async def _set_margin_mode(self, symbol: str, margin_type: str):
        """Set margin mode (CROSSED or ISOLATED)"""
        try:
            await self._request(
                'POST',
                '/fapi/v1/marginType',
                signed=True,
                params={'symbol': symbol, 'marginType': margin_type}
            )
            self.logger.info(f"Margin mode set to {margin_type} for {symbol}")
        except Exception as e:
            # May fail if already set
            self.logger.debug(f"Margin mode set failed (may already be set): {e}")
    
    def _round_quantity(self, quantity: float) -> float:
        """Round quantity to symbol precision"""
        if not self.symbol_info:
            return round(quantity, 3)
        
        for filter_data in self.symbol_info.get('filters', []):
            if filter_data['filterType'] == 'LOT_SIZE':
                step_size = float(filter_data['stepSize'])
                precision = len(str(step_size).rstrip('0').split('.')[-1])
                return round(quantity - (quantity % step_size), precision)
        
        return round(quantity, 3)
    
    def _round_price(self, price: float) -> float:
        """Round price to symbol precision"""
        if not self.symbol_info:
            return round(price, 2)
        
        for filter_data in self.symbol_info.get('filters', []):
            if filter_data['filterType'] == 'PRICE_FILTER':
                tick_size = float(filter_data['tickSize'])
                precision = len(str(tick_size).rstrip('0').split('.')[-1])
                return round(price - (price % tick_size), precision)
        
        return round(price, 2)
    
    async def get_account_balance(self) -> Dict:
        """Get account balance and available margin"""
        if self.dry_run:
            return {
                'total_equity': 10000.0,
                'available_margin': 10000.0,
                'unrealized_pnl': 0.0
            }
        
        data = await self._request('GET', '/fapi/v2/account', signed=True)
        
        return {
            'total_equity': float(data['totalWalletBalance']),
            'available_margin': float(data['availableBalance']),
            'unrealized_pnl': float(data['totalUnrealizedProfit'])
        }
    
    async def get_current_price(self, symbol: str) -> float:
        """Get current market price"""
        if self.dry_run:
            return 50000.0
        
        data = await self._request('GET', '/fapi/v1/ticker/price', params={'symbol': symbol})
        return float(data['price'])
    
    async def place_order(
        self,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        reduce_only: bool = False
    ) -> Optional[OrderState]:
        """
        Place order with stop loss and take profit
        
        Args:
            side: BUY or SELL
            quantity: Order quantity
            order_type: MARKET, LIMIT, etc
            price: Limit price (required for LIMIT orders)
            stop_loss: Stop loss price
            take_profit: Take profit price
            reduce_only: Reduce only flag
        
        Returns:
            OrderState if successful, None otherwise
        """
        await self.order_rate_limiter.acquire()
        
        quantity = self._round_quantity(quantity)
        
        if self.dry_run:
            order_id = int(time.time() * 1000)
            self.logger.info(
                f"[DRY RUN] {side.value} {quantity} {self.symbol} @ MARKET"
            )
            
            order_state = OrderState(
                order_id=order_id,
                symbol=self.symbol,
                side=side,
                type=order_type,
                quantity=quantity,
                price=price or 0.0,
                status=OrderStatus.FILLED,
                filled_qty=quantity,
                avg_price=price or 50000.0,
                timestamp=time.time()
            )
            
            await self._save_order_state(order_state)
            return order_state
        
        try:
            params = {
                'symbol': self.symbol,
                'side': side.value,
                'type': order_type.value,
                'quantity': quantity
            }
            
            if reduce_only:
                params['reduceOnly'] = 'true'
            
            if order_type == OrderType.LIMIT:
                if price is None:
                    raise ValueError("Price required for LIMIT orders")
                params['price'] = self._round_price(price)
                params['timeInForce'] = 'GTC'
            
            data = await self._request('POST', '/fapi/v1/order', signed=True, params=params)
            
            order_state = OrderState(
                order_id=int(data['orderId']),
                symbol=data['symbol'],
                side=OrderSide[data['side']],
                type=OrderType[data['type']],
                quantity=float(data['origQty']),
                price=float(data.get('price', 0)),
                status=OrderStatus[data['status']],
                filled_qty=float(data.get('executedQty', 0)),
                avg_price=float(data.get('avgPrice', 0)),
                timestamp=time.time()
            )
            
            await self._save_order_state(order_state)
            
            self.logger.info(
                f"Order placed: {order_state.order_id} - {side.value} {quantity} {self.symbol}"
            )
            
            # Place stop loss and take profit if specified
            if stop_loss:
                sl_order = await self._place_stop_loss(order_state, stop_loss)
                if sl_order:
                    order_state.stop_loss_order_id = sl_order.order_id
                    await self._save_order_state(order_state)
            
            if take_profit:
                tp_order = await self._place_take_profit(order_state, take_profit)
                if tp_order:
                    order_state.take_profit_order_id = tp_order.order_id
                    await self._save_order_state(order_state)
            
            return order_state
            
        except Exception as e:
            self.logger.error(f"Failed to place order: {e}", exc_info=True)
            return None
    
    async def _place_stop_loss(
        self,
        parent_order: OrderState,
        stop_price: float
    ) -> Optional[OrderState]:
        """Place stop loss order"""
        try:
            side = OrderSide.SELL if parent_order.side == OrderSide.BUY else OrderSide.BUY
            
            params = {
                'symbol': self.symbol,
                'side': side.value,
                'type': 'STOP_MARKET',
                'quantity': parent_order.quantity,
                'stopPrice': self._round_price(stop_price),
                'reduceOnly': 'true'
            }
            
            data = await self._request('POST', '/fapi/v1/order', signed=True, params=params)
            
            order_state = OrderState(
                order_id=int(data['orderId']),
                symbol=data['symbol'],
                side=OrderSide[data['side']],
                type=OrderType.STOP_MARKET,
                quantity=float(data['origQty']),
                price=float(data.get('stopPrice', 0)),
                status=OrderStatus[data['status']],
                timestamp=time.time()
            )
            
            await self._save_order_state(order_state)
            self.logger.info(f"Stop loss placed: {stop_price}")
            
            return order_state
            
        except Exception as e:
            self.logger.error(f"Failed to place stop loss: {e}")
            return None
    
    async def _place_take_profit(
        self,
        parent_order: OrderState,
        tp_price: float
    ) -> Optional[OrderState]:
        """Place take profit order"""
        try:
            side = OrderSide.SELL if parent_order.side == OrderSide.BUY else OrderSide.BUY
            
            params = {
                'symbol': self.symbol,
                'side': side.value,
                'type': 'TAKE_PROFIT_MARKET',
                'quantity': parent_order.quantity,
                'stopPrice': self._round_price(tp_price),
                'reduceOnly': 'true'
            }
            
            data = await self._request('POST', '/fapi/v1/order', signed=True, params=params)
            
            order_state = OrderState(
                order_id=int(data['orderId']),
                symbol=data['symbol'],
                side=OrderSide[data['side']],
                type=OrderType.TAKE_PROFIT_MARKET,
                quantity=float(data['origQty']),
                price=float(data.get('stopPrice', 0)),
                status=OrderStatus[data['status']],
                timestamp=time.time()
            )
            
            await self._save_order_state(order_state)
            self.logger.info(f"Take profit placed: {tp_price}")
            
            return order_state
            
        except Exception as e:
            self.logger.error(f"Failed to place take profit: {e}")
            return None
    
    async def get_order_status(self, order_id: int) -> Optional[OrderState]:
        """Get current status of an order"""
        if self.dry_run:
            return await self._load_order_state(order_id)
        
        try:
            data = await self._request(
                'GET',
                '/fapi/v1/order',
                signed=True,
                params={'symbol': self.symbol, 'orderId': order_id}
            )
            
            order_state = OrderState(
                order_id=int(data['orderId']),
                symbol=data['symbol'],
                side=OrderSide[data['side']],
                type=OrderType[data['type']],
                quantity=float(data['origQty']),
                price=float(data.get('price', 0)),
                status=OrderStatus[data['status']],
                filled_qty=float(data.get('executedQty', 0)),
                avg_price=float(data.get('avgPrice', 0)),
                timestamp=time.time()
            )
            
            await self._save_order_state(order_state)
            return order_state
            
        except Exception as e:
            self.logger.error(f"Failed to get order status: {e}")
            return None
    
    async def cancel_order(self, order_id: int) -> bool:
        """Cancel an open order"""
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Cancel order {order_id}")
            return True
        
        try:
            await self._request(
                'DELETE',
                '/fapi/v1/order',
                signed=True,
                params={'symbol': self.symbol, 'orderId': order_id}
            )
            
            self.logger.info(f"Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cancel order: {e}")
            return False
    
    async def monitor_orders(self) -> List[OrderState]:
        """Get all open orders"""
        if self.dry_run:
            return []
        
        try:
            data = await self._request(
                'GET',
                '/fapi/v1/openOrders',
                signed=True,
                params={'symbol': self.symbol}
            )
            
            orders = []
            for order_data in data:
                order_state = OrderState(
                    order_id=int(order_data['orderId']),
                    symbol=order_data['symbol'],
                    side=OrderSide[order_data['side']],
                    type=OrderType[order_data['type']],
                    quantity=float(order_data['origQty']),
                    price=float(order_data.get('price', 0)),
                    status=OrderStatus[order_data['status']],
                    filled_qty=float(order_data.get('executedQty', 0)),
                    avg_price=float(order_data.get('avgPrice', 0)),
                    timestamp=time.time()
                )
                orders.append(order_state)
                await self._save_order_state(order_state)
            
            return orders
            
        except Exception as e:
            self.logger.error(f"Failed to monitor orders: {e}")
            return []
    
    async def _save_order_state(self, order: OrderState):
        """Save order state to database"""
        async with aiosqlite.connect(self.order_db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO orders
                (order_id, symbol, side, type, quantity, price, status, 
                 filled_qty, avg_price, timestamp, stop_loss_order_id, take_profit_order_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order.order_id, order.symbol, order.side.value, order.type.value,
                order.quantity, order.price, order.status.value,
                order.filled_qty, order.avg_price, order.timestamp,
                order.stop_loss_order_id, order.take_profit_order_id
            ))
            await db.commit()
    
    async def _load_order_state(self, order_id: int) -> Optional[OrderState]:
        """Load order state from database"""
        async with aiosqlite.connect(self.order_db_path) as db:
            async with db.execute(
                'SELECT * FROM orders WHERE order_id = ?',
                (order_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                
                return OrderState(
                    order_id=row[0],
                    symbol=row[1],
                    side=OrderSide[row[2]],
                    type=OrderType[row[3]],
                    quantity=row[4],
                    price=row[5],
                    status=OrderStatus[row[6]],
                    filled_qty=row[7],
                    avg_price=row[8],
                    timestamp=row[9],
                    stop_loss_order_id=row[10],
                    take_profit_order_id=row[11]
                )
    
    async def close(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        self.logger.info("BinanceClient closed")
    
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
        """Legacy method for backward compatibility - use get_order_status(order_id) instead"""
        self.logger.warning("Deprecated method called: get_order_status(symbol, order_id)")
        return await self.get_order_status(order_id)
    
    async def close(self):
        """Legacy method for backward compatibility"""
        self.logger.info("Closing Binance client")

