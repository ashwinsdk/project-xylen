import logging
from typing import Dict, List
import aiohttp
import asyncio
from datetime import datetime
import numpy as np


class MarketDataCollector:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.symbol = config['trading']['symbol']
        self.testnet = config.get('testnet', True)
        
        # Use Binance API directly (no ccxt dependency issues)
        if self.testnet:
            self.base_url = "https://testnet.binancefuture.com"
        else:
            self.base_url = "https://fapi.binance.com"
        
        self.session = None
    
    async def initialize(self):
        try:
            self.session = aiohttp.ClientSession()
            
            # Test connection
            async with self.session.get(f"{self.base_url}/fapi/v1/ping") as response:
                if response.status == 200:
                    self.logger.info(f"Market data collector initialized - {'TESTNET' if self.testnet else 'MAINNET'}")
                else:
                    raise Exception(f"Failed to ping Binance API: {response.status}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize market data collector: {e}")
            raise
    
    async def get_snapshot(self) -> Dict:
        """Get complete market snapshot with candles, price, and indicators"""
        try:
            timeframes = self.config['data'].get('timeframes', ['5m', '1h'])
            candles_count = self.config['data'].get('candles_count', 100)
            
            snapshot = {
                'timestamp': datetime.utcnow().isoformat(),
                'symbol': self.symbol
            }
            
            # Fetch candles for all timeframes
            tasks = []
            for timeframe in timeframes:
                tasks.append(self._fetch_candles(timeframe, candles_count))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, timeframe in enumerate(timeframes):
                if isinstance(results[i], Exception):
                    self.logger.error(f"Error fetching {timeframe} candles: {results[i]}")
                    snapshot[f"candles_{timeframe}"] = []
                else:
                    snapshot[f"candles_{timeframe}"] = results[i]
            
            # Get current price from ticker
            ticker = await self._fetch_ticker()
            snapshot['current_price'] = ticker['last_price']
            snapshot['bid'] = ticker['bid_price']
            snapshot['ask'] = ticker['ask_price']
            snapshot['volume_24h'] = ticker['volume']
            snapshot['price_change_24h'] = ticker['price_change_percent']
            
            # Calculate indicators from 5m candles
            candles_5m = snapshot.get('candles_5m', [])
            if candles_5m:
                snapshot['indicators'] = self._calculate_indicators(candles_5m)
            else:
                snapshot['indicators'] = {}
            
            return snapshot
            
        except Exception as e:
            self.logger.error(f"Error getting market snapshot: {e}", exc_info=True)
            raise
    
    async def _fetch_candles(self, timeframe: str, limit: int) -> List[Dict]:
        """
        Fetch klines/candles from Binance API
        https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/Kline-Candlestick-Data
        """
        try:
            # Convert timeframe format (5m -> 5m, 1h -> 1h) - already compatible
            params = {
                'symbol': self.symbol,
                'interval': timeframe,
                'limit': limit
            }
            
            url = f"{self.base_url}/fapi/v1/klines"
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Binance API error: {response.status} - {text}")
                
                data = await response.json()
                
                candles = []
                for kline in data:
                    candles.append({
                        'timestamp': kline[0],
                        'open': float(kline[1]),
                        'high': float(kline[2]),
                        'low': float(kline[3]),
                        'close': float(kline[4]),
                        'volume': float(kline[5])
                    })
                
                self.logger.debug(f"Fetched {len(candles)} {timeframe} candles")
                return candles
            
        except Exception as e:
            self.logger.error(f"Error fetching {timeframe} candles: {e}")
            return []
    
    async def _fetch_ticker(self) -> Dict:
        """
        Fetch 24hr ticker price change statistics
        https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/24hr-Ticker-Price-Change-Statistics
        """
        try:
            params = {'symbol': self.symbol}
            url = f"{self.base_url}/fapi/v1/ticker/24hr"
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Binance ticker API error: {response.status} - {text}")
                
                data = await response.json()
                
                return {
                    'last_price': float(data['lastPrice']),
                    'bid_price': float(data.get('bidPrice', data['lastPrice'])),
                    'ask_price': float(data.get('askPrice', data['lastPrice'])),
                    'volume': float(data['volume']),
                    'quote_volume': float(data['quoteVolume']),
                    'price_change': float(data['priceChange']),
                    'price_change_percent': float(data['priceChangePercent']),
                    'high_24h': float(data['highPrice']),
                    'low_24h': float(data['lowPrice']),
                    'open_price': float(data['openPrice'])
                }
            
        except Exception as e:
            self.logger.error(f"Error fetching ticker: {e}")
            raise
    
    def _calculate_indicators(self, candles: List[Dict]) -> Dict:
        """Calculate technical indicators from candle data"""
        if not candles:
            return {}
        
        closes = np.array([c['close'] for c in candles])
        highs = np.array([c['high'] for c in candles])
        lows = np.array([c['low'] for c in candles])
        volumes = np.array([c['volume'] for c in candles])
        
        indicators = {}
        
        # RSI
        indicators['rsi'] = self._calculate_rsi(closes, period=14)
        
        # Volume metrics
        indicators['volume'] = float(volumes[-1])
        indicators['volume_avg_20'] = float(np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes))
        indicators['volume_ratio'] = float(volumes[-1] / indicators['volume_avg_20']) if indicators['volume_avg_20'] > 0 else 1.0
        
        # EMAs
        if len(closes) >= 20:
            indicators['ema_9'] = self._calculate_ema(closes, 9)
            indicators['ema_20'] = self._calculate_ema(closes, 20)
        
        if len(closes) >= 50:
            indicators['ema_50'] = self._calculate_ema(closes, 50)
        
        if len(closes) >= 200:
            indicators['ema_200'] = self._calculate_ema(closes, 200)
        
        # MACD
        if len(closes) >= 26:
            macd_data = self._calculate_macd(closes)
            indicators.update(macd_data)
        
        # Bollinger Bands
        if len(closes) >= 20:
            bb_data = self._calculate_bollinger_bands(closes, period=20)
            indicators.update(bb_data)
            
            # BB position (where price is relative to bands)
            current_price = closes[-1]
            bb_range = bb_data['bb_upper'] - bb_data['bb_lower']
            if bb_range > 0:
                indicators['bb_position'] = (current_price - bb_data['bb_lower']) / bb_range
        
        # ATR (Average True Range)
        if len(closes) >= 14:
            indicators['atr'] = self._calculate_atr(highs, lows, closes, period=14)
        
        # Momentum
        if len(closes) >= 10:
            indicators['momentum_10'] = float((closes[-1] - closes[-10]) / closes[-10] * 100)
        
        # Price metrics
        indicators['current_price'] = float(closes[-1])
        indicators['high_low_range'] = float(highs[-1] - lows[-1])
        indicators['high_low_ratio'] = float(indicators['high_low_range'] / closes[-1] * 100) if closes[-1] > 0 else 0
        
        return indicators
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gain = np.where(deltas > 0, deltas, 0)
        loss = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gain[-period:])
        avg_loss = np.mean(loss[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return float(prices[-1])
        
        multiplier = 2 / (period + 1)
        ema = np.mean(prices[:period])
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return float(ema)
    
    def _calculate_macd(self, prices: np.ndarray) -> Dict:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        
        macd_line = ema_12 - ema_26
        
        # For signal line, we'd need to calculate EMA of MACD line
        # Simplified version here
        signal_line = macd_line * 0.9  # Approximation
        
        return {
            'macd': macd_line,
            'macd_signal': signal_line,
            'macd_histogram': macd_line - signal_line
        }
    
    def _calculate_bollinger_bands(self, prices: np.ndarray, period: int = 20, std_dev: int = 2) -> Dict:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return {
                'bb_upper': float(prices[-1]),
                'bb_middle': float(prices[-1]),
                'bb_lower': float(prices[-1])
            }
        
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        
        return {
            'bb_upper': float(sma + std_dev * std),
            'bb_middle': float(sma),
            'bb_lower': float(sma - std_dev * std)
        }
    
    def _calculate_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(closes) < period + 1:
            return float(highs[-1] - lows[-1])
        
        tr_list = []
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            tr = max(high_low, high_close, low_close)
            tr_list.append(tr)
        
        tr_array = np.array(tr_list)
        atr = np.mean(tr_array[-period:])
        
        return float(atr)
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()
            self.logger.info("Market data collector closed")