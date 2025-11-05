import asyncio
import aiohttp
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class BinanceDataCollector:
    """Continuously collects live market data from Binance for training"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.symbol = "BTCUSDT"
        self.data_path = os.getenv('TRAINING_DATA_PATH', './training_data/live_samples.jsonl')
        self.collection_interval = int(os.getenv('COLLECTION_INTERVAL', '60'))  # seconds
        self.lookback_periods = int(os.getenv('LOOKBACK_PERIODS', '100'))
        
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        
        logger.info(f"DataCollector initialized: interval={self.collection_interval}s")
    
    async def start_collection(self):
        """Main loop for continuous data collection"""
        logger.info("Starting continuous data collection from Binance...")
        
        while True:
            try:
                sample = await self.collect_sample()
                
                if sample:
                    await self.save_sample(sample)
                    logger.info(f"Sample collected: price={sample['price']:.2f}, rsi={sample['indicators']['rsi']:.2f}")
                
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Collection error: {e}", exc_info=True)
                await asyncio.sleep(10)  # Wait before retry
    
    async def collect_sample(self) -> Dict:
        """Collect a single training sample with full market data"""
        try:
            async with aiohttp.ClientSession() as session:
                # Fetch 5-minute candles
                candles_5m = await self._fetch_klines(session, '5m', self.lookback_periods)
                
                # Fetch 1-hour candles
                candles_1h = await self._fetch_klines(session, '1h', 50)
                
                # Fetch current ticker
                ticker = await self._fetch_ticker(session)
                
                # Calculate indicators
                indicators = self._calculate_indicators(candles_5m, candles_1h)
                
                # Generate label (for supervised learning)
                # Look ahead 15 minutes to see if price increased
                future_candles = await self._fetch_klines(session, '1m', 15)
                label = self._generate_label(candles_5m[-1], future_candles)
                
                sample = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'symbol': self.symbol,
                    'price': ticker['last_price'],
                    'candles_5m': candles_5m[-20:],  # Keep last 20 candles
                    'candles_1h': candles_1h[-20:],
                    'indicators': indicators,
                    'ticker': ticker,
                    'label': label  # 1 for up, 0 for down/hold
                }
                
                return sample
                
        except Exception as e:
            logger.error(f"Error collecting sample: {e}")
            return None
    
    async def _fetch_klines(self, session: aiohttp.ClientSession, interval: str, limit: int) -> List[Dict]:
        """Fetch candlestick data from Binance"""
        url = f"{self.base_url}/klines"
        params = {
            'symbol': self.symbol,
            'interval': interval,
            'limit': limit
        }
        
        async with session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"Binance API error: {response.status}")
            
            data = await response.json()
            
            candles = []
            for k in data:
                candles.append({
                    'timestamp': k[0],
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5])
                })
            
            return candles
    
    async def _fetch_ticker(self, session: aiohttp.ClientSession) -> Dict:
        """Fetch 24h ticker statistics"""
        url = f"{self.base_url}/ticker/24hr"
        params = {'symbol': self.symbol}
        
        async with session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"Binance API error: {response.status}")
            
            data = await response.json()
            
            return {
                'last_price': float(data['lastPrice']),
                'volume': float(data['volume']),
                'quote_volume': float(data['quoteVolume']),
                'price_change_percent': float(data['priceChangePercent'])
            }
    
    def _calculate_indicators(self, candles_5m: List[Dict], candles_1h: List[Dict]) -> Dict:
        """Calculate technical indicators"""
        if not candles_5m:
            return {}
        
        closes = [c['close'] for c in candles_5m]
        highs = [c['high'] for c in candles_5m]
        lows = [c['low'] for c in candles_5m]
        volumes = [c['volume'] for c in candles_5m]
        
        indicators = {}
        
        # RSI
        if len(closes) >= 14:
            indicators['rsi'] = self._calculate_rsi(closes, 14)
        else:
            indicators['rsi'] = 50.0
        
        # EMAs
        if len(closes) >= 20:
            indicators['ema_20'] = self._calculate_ema(closes, 20)
        else:
            indicators['ema_20'] = closes[-1]
        
        if len(closes) >= 50:
            indicators['ema_50'] = self._calculate_ema(closes, 50)
        else:
            indicators['ema_50'] = closes[-1]
        
        # MACD (12, 26, 9)
        if len(closes) >= 26:
            macd_line, signal_line = self._calculate_macd(closes)
            indicators['macd'] = macd_line
            indicators['macd_signal'] = signal_line
            indicators['macd_histogram'] = macd_line - signal_line
        else:
            indicators['macd'] = 0.0
            indicators['macd_signal'] = 0.0
            indicators['macd_histogram'] = 0.0
        
        # Bollinger Bands
        if len(closes) >= 20:
            bb_upper, bb_lower, bb_middle = self._calculate_bollinger_bands(closes, 20)
            indicators['bollinger_upper'] = bb_upper
            indicators['bollinger_lower'] = bb_lower
            indicators['bollinger_middle'] = bb_middle
        else:
            indicators['bollinger_upper'] = closes[-1]
            indicators['bollinger_lower'] = closes[-1]
            indicators['bollinger_middle'] = closes[-1]
        
        # ATR
        if len(highs) >= 14:
            indicators['atr'] = self._calculate_atr(highs, lows, closes, 14)
        else:
            indicators['atr'] = 0.0
        
        # Volume ratio
        if len(volumes) >= 20:
            vol_ma = np.mean(volumes[-20:])
            indicators['volume_ratio'] = volumes[-1] / vol_ma if vol_ma > 0 else 1.0
        else:
            indicators['volume_ratio'] = 1.0
        
        # Momentum
        if len(closes) >= 10:
            indicators['momentum'] = ((closes[-1] - closes[-10]) / closes[-10]) * 100
        else:
            indicators['momentum'] = 0.0
        
        return indicators
    
    def _calculate_rsi(self, prices: List[float], period: int) -> float:
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1]
        
        prices_array = np.array(prices[-period:])
        weights = np.exp(np.linspace(-1., 0., period))
        weights /= weights.sum()
        
        ema = np.convolve(prices_array, weights, mode='full')[:len(prices_array)]
        return float(ema[-1])
    
    def _calculate_macd(self, prices: List[float]) -> tuple:
        """Calculate MACD indicator"""
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        macd_line = ema_12 - ema_26
        
        # Signal line (9-period EMA of MACD)
        macd_values = [ema_12 - ema_26]  # Simplified
        signal_line = macd_line * 0.9  # Approximation
        
        return macd_line, signal_line
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int) -> tuple:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return prices[-1], prices[-1], prices[-1]
        
        prices_array = np.array(prices[-period:])
        middle = np.mean(prices_array)
        std = np.std(prices_array)
        
        upper = middle + (2 * std)
        lower = middle - (2 * std)
        
        return float(upper), float(lower), float(middle)
    
    def _calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int) -> float:
        """Calculate Average True Range"""
        if len(highs) < period + 1:
            return 0.0
        
        tr_list = []
        for i in range(1, min(period + 1, len(highs))):
            h_l = highs[i] - lows[i]
            h_c = abs(highs[i] - closes[i-1])
            l_c = abs(lows[i] - closes[i-1])
            tr = max(h_l, h_c, l_c)
            tr_list.append(tr)
        
        atr = np.mean(tr_list)
        return float(atr)
    
    def _generate_label(self, current_candle: Dict, future_candles: List[Dict]) -> int:
        """Generate training label based on future price movement"""
        if not future_candles or len(future_candles) < 5:
            return 0  # Hold
        
        current_price = current_candle['close']
        future_price = future_candles[-1]['close']
        
        price_change_pct = ((future_price - current_price) / current_price) * 100
        
        # Label as 1 (long) if price increases by >0.2%
        # Label as 0 otherwise
        if price_change_pct > 0.2:
            return 1
        else:
            return 0
    
    async def save_sample(self, sample: Dict):
        """Save sample to disk"""
        try:
            with open(self.data_path, 'a') as f:
                f.write(json.dumps(sample) + '\n')
        except Exception as e:
            logger.error(f"Error saving sample: {e}")


async def main():
    collector = BinanceDataCollector()
    await collector.start_collection()


if __name__ == "__main__":
    asyncio.run(main())