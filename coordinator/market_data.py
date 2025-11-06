import logging
from typing import Dict, List, Optional
import aiohttp
import asyncio
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import os
from pathlib import Path


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
        """
        Calculate all 29+ technical indicators from config.yaml
        
        Features computed:
        - Price momentum & trend (RSI, EMAs, MACD)
        - Volatility (ATR, Bollinger Bands)
        - Volume analysis (OBV, volume ratios)
        - Candle patterns (body ratio, shadows)
        - Strength indicators (ADX)
        """
        if not candles:
            return {}
        
        closes = np.array([c['close'] for c in candles])
        highs = np.array([c['high'] for c in candles])
        lows = np.array([c['low'] for c in candles])
        opens = np.array([c['open'] for c in candles])
        volumes = np.array([c['volume'] for c in candles])
        
        indicators = {}
        
        # === RSI (Multiple periods) ===
        indicators['rsi'] = self._calculate_rsi(closes, period=14)
        indicators['rsi_14'] = indicators['rsi']
        indicators['rsi_28'] = self._calculate_rsi(closes, period=28)
        
        # === Volume Metrics ===
        indicators['volume'] = float(volumes[-1])
        indicators['volume_sma_20'] = float(np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes))
        indicators['volume_ratio'] = float(volumes[-1] / indicators['volume_sma_20']) if indicators['volume_sma_20'] > 0 else 1.0
        
        # === EMAs (Multiple periods) ===
        if len(closes) >= 9:
            indicators['ema_9'] = self._calculate_ema(closes, 9)
        if len(closes) >= 20:
            indicators['ema_20'] = self._calculate_ema(closes, 20)
        if len(closes) >= 50:
            indicators['ema_50'] = self._calculate_ema(closes, 50)
        if len(closes) >= 200:
            indicators['ema_200'] = self._calculate_ema(closes, 200)
        
        # === MACD ===
        if len(closes) >= 26:
            macd_data = self._calculate_macd(closes)
            indicators['macd'] = macd_data['macd']
            indicators['macd_signal'] = macd_data['macd_signal']
            indicators['macd_hist'] = macd_data['macd_histogram']
        
        # === Bollinger Bands ===
        if len(closes) >= 20:
            bb_data = self._calculate_bollinger_bands(closes, period=20)
            indicators['bb_upper'] = bb_data['bb_upper']
            indicators['bb_middle'] = bb_data['bb_middle']
            indicators['bb_lower'] = bb_data['bb_lower']
            
            # BB width (volatility indicator)
            bb_range = bb_data['bb_upper'] - bb_data['bb_lower']
            indicators['bb_width'] = float(bb_range / bb_data['bb_middle'] * 100) if bb_data['bb_middle'] > 0 else 0
            
            # BB position (where price is relative to bands)
            current_price = closes[-1]
            if bb_range > 0:
                indicators['bb_position'] = (current_price - bb_data['bb_lower']) / bb_range
        
        # === ATR (Average True Range) ===
        if len(closes) >= 14:
            atr_value = self._calculate_atr(highs, lows, closes, period=14)
            indicators['atr'] = atr_value
            indicators['atr_percent'] = float(atr_value / closes[-1] * 100) if closes[-1] > 0 else 0
        
        # === OBV (On-Balance Volume) ===
        if len(closes) >= 2:
            indicators['obv'] = self._calculate_obv(closes, volumes)
        
        # === ADX (Average Directional Index) ===
        if len(closes) >= 14:
            indicators['adx'] = self._calculate_adx(highs, lows, closes, period=14)
        
        # === Candle Pattern Features ===
        if len(candles) >= 1:
            last_candle = candles[-1]
            body = abs(last_candle['close'] - last_candle['open'])
            high_low_range = last_candle['high'] - last_candle['low']
            
            # Body ratio (body size vs full range)
            indicators['candle_body_ratio'] = float(body / high_low_range) if high_low_range > 0 else 0
            
            # Upper shadow (wick above body)
            upper_shadow = last_candle['high'] - max(last_candle['open'], last_candle['close'])
            indicators['candle_upper_shadow'] = float(upper_shadow / high_low_range) if high_low_range > 0 else 0
            
            # Lower shadow (wick below body)
            lower_shadow = min(last_candle['open'], last_candle['close']) - last_candle['low']
            indicators['candle_lower_shadow'] = float(lower_shadow / high_low_range) if high_low_range > 0 else 0
        
        # === Momentum Indicators ===
        if len(closes) >= 10:
            indicators['price_momentum'] = float((closes[-1] - closes[-10]) / closes[-10] * 100)
        
        if len(volumes) >= 10:
            indicators['volume_momentum'] = float((volumes[-1] - np.mean(volumes[-10:])) / np.mean(volumes[-10:]) * 100) if np.mean(volumes[-10:]) > 0 else 0
        
        # === Basic Price Metrics ===
        indicators['current_price'] = float(closes[-1])
        indicators['high_low_range'] = float(highs[-1] - lows[-1])
        indicators['high_low_ratio'] = float(indicators['high_low_range'] / closes[-1] * 100) if closes[-1] > 0 else 0
        
        return indicators
    
    def _calculate_obv(self, closes: np.ndarray, volumes: np.ndarray) -> float:
        """Calculate On-Balance Volume"""
        obv = 0
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                obv += volumes[i]
            elif closes[i] < closes[i-1]:
                obv -= volumes[i]
        return float(obv)
    
    def _calculate_adx(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """
        Calculate Average Directional Index (ADX)
        Measures trend strength (0-100, >25 = strong trend)
        """
        if len(closes) < period + 1:
            return 0.0
        
        # Calculate +DM and -DM
        plus_dm = []
        minus_dm = []
        
        for i in range(1, len(highs)):
            high_diff = highs[i] - highs[i-1]
            low_diff = lows[i-1] - lows[i]
            
            if high_diff > low_diff and high_diff > 0:
                plus_dm.append(high_diff)
                minus_dm.append(0)
            elif low_diff > high_diff and low_diff > 0:
                plus_dm.append(0)
                minus_dm.append(low_diff)
            else:
                plus_dm.append(0)
                minus_dm.append(0)
        
        # Calculate ATR for normalization
        atr_values = []
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            tr = max(high_low, high_close, low_close)
            atr_values.append(tr)
        
        # Smooth +DI and -DI
        plus_dm_arr = np.array(plus_dm)
        minus_dm_arr = np.array(minus_dm)
        atr_arr = np.array(atr_values)
        
        if len(atr_arr) < period:
            return 0.0
        
        plus_di = np.mean(plus_dm_arr[-period:]) / np.mean(atr_arr[-period:]) * 100 if np.mean(atr_arr[-period:]) > 0 else 0
        minus_di = np.mean(minus_dm_arr[-period:]) / np.mean(atr_arr[-period:]) * 100 if np.mean(atr_arr[-period:]) > 0 else 0
        
        # Calculate DX and ADX
        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0
        
        # ADX is smoothed DX (simplified as single value here)
        return float(dx)
    
    
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
    
    # ============================================================
    # PARQUET STORAGE & HISTORICAL DATA
    # ============================================================
    
    async def save_snapshot(self, snapshot: Dict):
        """
        Save snapshot to Parquet file with daily sharding
        
        Storage structure:
        data/feature_store/YYYYMMDD/snapshots_YYYYMMDD.parquet.gzip
        """
        try:
            storage_config = self.config.get('data', {})
            storage_path = storage_config.get('storage_path', './data/feature_store')
            compression = storage_config.get('compression', 'gzip')
            
            # Create date-based shard directory
            timestamp = datetime.fromisoformat(snapshot['timestamp'])
            date_str = timestamp.strftime('%Y%m%d')
            shard_dir = Path(storage_path) / date_str
            shard_dir.mkdir(parents=True, exist_ok=True)
            
            # Parquet file path
            parquet_file = shard_dir / f"snapshots_{date_str}.parquet.{compression}"
            
            # Flatten snapshot for DataFrame
            flat_data = {
                'timestamp': timestamp,
                'symbol': snapshot['symbol'],
                'current_price': snapshot.get('current_price', 0),
                'bid': snapshot.get('bid', 0),
                'ask': snapshot.get('ask', 0),
                'volume_24h': snapshot.get('volume_24h', 0),
                'price_change_24h': snapshot.get('price_change_24h', 0)
            }
            
            # Add all indicators
            if 'indicators' in snapshot:
                for key, value in snapshot['indicators'].items():
                    flat_data[f'ind_{key}'] = value
            
            # Create DataFrame
            df = pd.DataFrame([flat_data])
            
            # Append to existing file or create new
            if parquet_file.exists():
                existing_df = pd.read_parquet(parquet_file)
                df = pd.concat([existing_df, df], ignore_index=True)
            
            # Write with compression
            df.to_parquet(
                parquet_file,
                engine='pyarrow',
                compression=compression,
                index=False
            )
            
            self.logger.debug(f"Snapshot saved to {parquet_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save snapshot: {e}", exc_info=True)
    
    async def load_historical_snapshots(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        symbol: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load historical snapshots from Parquet shards
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive), defaults to today
            symbol: Filter by symbol, defaults to configured symbol
        
        Returns:
            DataFrame with historical snapshots
        """
        try:
            storage_config = self.config.get('data', {})
            storage_path = Path(storage_config.get('storage_path', './data/feature_store'))
            compression = storage_config.get('compression', 'gzip')
            
            if end_date is None:
                end_date = datetime.utcnow()
            
            if symbol is None:
                symbol = self.symbol
            
            # Collect all shard files in date range
            dataframes = []
            current_date = start_date
            
            while current_date <= end_date:
                date_str = current_date.strftime('%Y%m%d')
                parquet_file = storage_path / date_str / f"snapshots_{date_str}.parquet.{compression}"
                
                if parquet_file.exists():
                    df = pd.read_parquet(parquet_file)
                    
                    # Filter by symbol if specified
                    if symbol:
                        df = df[df['symbol'] == symbol]
                    
                    dataframes.append(df)
                    self.logger.debug(f"Loaded {len(df)} snapshots from {parquet_file}")
                
                current_date += timedelta(days=1)
            
            if not dataframes:
                self.logger.warning(f"No snapshots found for {start_date} to {end_date}")
                return pd.DataFrame()
            
            # Concatenate all shards
            result = pd.concat(dataframes, ignore_index=True)
            result = result.sort_values('timestamp').reset_index(drop=True)
            
            self.logger.info(f"Loaded {len(result)} historical snapshots from {len(dataframes)} shards")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to load historical snapshots: {e}", exc_info=True)
            return pd.DataFrame()
    
    async def download_historical_klines(
        self,
        symbol: str,
        interval: str,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Download historical klines from Binance Vision
        
        Binance Vision provides free historical data:
        https://data.binance.vision/data/futures/um/daily/klines/{SYMBOL}/{INTERVAL}/
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            interval: Timeframe (1m, 5m, 15m, 1h, etc.)
            start_date: Start date
            end_date: End date (defaults to today)
        
        Returns:
            DataFrame with OHLCV data
        """
        try:
            if end_date is None:
                end_date = datetime.utcnow()
            
            data_config = self.config.get('data', {})
            download_url = data_config.get('download_url', 'https://data.binance.vision')
            
            all_klines = []
            current_date = start_date
            
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                zip_filename = f"{symbol}-{interval}-{date_str}.zip"
                
                # Binance Vision URL structure
                url = f"{download_url}/data/futures/um/daily/klines/{symbol}/{interval}/{zip_filename}"
                
                self.logger.debug(f"Downloading {url}")
                
                try:
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            # Download and extract ZIP
                            # Note: This is simplified - production would handle ZIP extraction
                            self.logger.info(f"Downloaded {date_str} klines for {symbol}")
                        else:
                            self.logger.warning(f"No data for {date_str}: HTTP {response.status}")
                
                except Exception as e:
                    self.logger.warning(f"Failed to download {date_str}: {e}")
                
                current_date += timedelta(days=1)
            
            # TODO: Implement ZIP extraction and CSV parsing
            # For now, return empty DataFrame
            self.logger.info(f"Historical download complete (extraction not yet implemented)")
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"Failed to download historical klines: {e}", exc_info=True)
            return pd.DataFrame()
    
    async def get_funding_rate(self) -> Dict:
        """Get current and predicted funding rate"""
        try:
            url = f"{self.base_url}/fapi/v1/fundingRate"
            params = {
                'symbol': self.symbol,
                'limit': 1
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return {'current_funding_rate': 0.0, 'next_funding_time': 0}
                
                data = await response.json()
                if data:
                    latest = data[0]
                    return {
                        'current_funding_rate': float(latest['fundingRate']),
                        'next_funding_time': int(latest['fundingTime'])
                    }
                
                return {'current_funding_rate': 0.0, 'next_funding_time': 0}
                
        except Exception as e:
            self.logger.error(f"Failed to get funding rate: {e}")
            return {'current_funding_rate': 0.0, 'next_funding_time': 0}
    
    async def get_open_interest(self) -> float:
        """Get current open interest"""
        try:
            url = f"{self.base_url}/fapi/v1/openInterest"
            params = {'symbol': self.symbol}
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return 0.0
                
                data = await response.json()
                return float(data.get('openInterest', 0))
                
        except Exception as e:
            self.logger.error(f"Failed to get open interest: {e}")
            return 0.0