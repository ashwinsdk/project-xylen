import logging
from typing import Dict, List
import ccxt.async_support as ccxt
import asyncio
from datetime import datetime
import numpy as np


class MarketDataCollector:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.exchange = None
        self.symbol = config['trading']['symbol']
        self.testnet = config.get('testnet', True)
    
    async def initialize(self):
        try:
            if self.testnet:
                self.exchange = ccxt.binance({
                    'options': {'defaultType': 'future'},
                    'urls': {
                        'api': {
                            'public': 'https://testnet.binancefuture.com/fapi/v1',
                            'private': 'https://testnet.binancefuture.com/fapi/v1',
                        }
                    }
                })
            else:
                self.exchange = ccxt.binance({
                    'options': {'defaultType': 'future'}
                })
            
            await self.exchange.load_markets()
            self.logger.info("Market data collector initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize market data collector: {e}")
            raise
    
    async def get_snapshot(self) -> Dict:
        try:
            timeframes = self.config['data'].get('timeframes', ['5m', '1h'])
            candles_count = self.config['data'].get('candles_count', 100)
            
            snapshot = {
                'timestamp': datetime.utcnow().isoformat(),
                'symbol': self.symbol
            }
            
            tasks = []
            for timeframe in timeframes:
                tasks.append(self._fetch_candles(timeframe, candles_count))
            
            results = await asyncio.gather(*tasks)
            
            for i, timeframe in enumerate(timeframes):
                key = f"candles_{timeframe}"
                snapshot[key] = results[i]
            
            ticker = await self.exchange.fetch_ticker(self.symbol)
            snapshot['current_price'] = ticker['last']
            
            candles_5m = snapshot.get('candles_5m', [])
            if candles_5m:
                snapshot['indicators'] = self._calculate_indicators(candles_5m)
            else:
                snapshot['indicators'] = {}
            
            return snapshot
            
        except Exception as e:
            self.logger.error(f"Error getting market snapshot: {e}")
            raise
    
    async def _fetch_candles(self, timeframe: str, limit: int) -> List[Dict]:
        try:
            ohlcv = await self.exchange.fetch_ohlcv(
                self.symbol,
                timeframe=timeframe,
                limit=limit
            )
            
            candles = []
            for candle in ohlcv:
                candles.append({
                    'timestamp': candle[0],
                    'open': candle[1],
                    'high': candle[2],
                    'low': candle[3],
                    'close': candle[4],
                    'volume': candle[5]
                })
            
            return candles
            
        except Exception as e:
            self.logger.error(f"Error fetching {timeframe} candles: {e}")
            return []
    
    def _calculate_indicators(self, candles: List[Dict]) -> Dict:
        if not candles:
            return {}
        
        closes = np.array([c['close'] for c in candles])
        highs = np.array([c['high'] for c in candles])
        lows = np.array([c['low'] for c in candles])
        volumes = np.array([c['volume'] for c in candles])
        
        indicators = {}
        
        indicators['rsi'] = self._calculate_rsi(closes, period=14)
        
        indicators['volume'] = float(volumes[-1])
        indicators['volume_avg_20'] = float(np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes))
        
        if len(closes) >= 20:
            indicators['ema_20'] = self._calculate_ema(closes, 20)
        
        if len(closes) >= 50:
            indicators['ema_50'] = self._calculate_ema(closes, 50)
        
        if len(closes) >= 26:
            macd_data = self._calculate_macd(closes)
            indicators.update(macd_data)
        
        if len(closes) >= 20:
            bb_data = self._calculate_bollinger_bands(closes, period=20)
            indicators.update(bb_data)
        
        return indicators
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
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
        if len(prices) < period:
            return float(prices[-1])
        
        multiplier = 2 / (period + 1)
        ema = np.mean(prices[:period])
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return float(ema)
    
    def _calculate_macd(self, prices: np.ndarray) -> Dict:
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        
        macd_line = ema_12 - ema_26
        
        return {
            'macd': macd_line,
            'macd_signal': 0.0,
            'macd_histogram': macd_line
        }
    
    def _calculate_bollinger_bands(self, prices: np.ndarray, period: int = 20, std_dev: int = 2) -> Dict:
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
    
    async def close(self):
        if self.exchange:
            await self.exchange.close()
            self.logger.info("Market data collector closed")
