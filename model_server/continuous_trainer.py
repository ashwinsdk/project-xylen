import asyncio
import lightgbm as lgb
import numpy as np
import json
import os
import logging
from typing import List, Dict
from datetime import datetime
import shutil

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class ContinuousTrainer:
    """Background training service that doesn't interrupt predictions"""
    
    def __init__(self, model_loader):
        self.model_loader = model_loader
        self.data_path = os.getenv('TRAINING_DATA_PATH', './training_data/live_samples.jsonl')
        self.training_interval = int(os.getenv('TRAINING_INTERVAL', '1800'))  # 30 minutes
        self.min_samples = int(os.getenv('MIN_SAMPLES_FOR_RETRAIN', '100'))
        self.batch_size = int(os.getenv('TRAINING_BATCH_SIZE', '1000'))
        
        self.max_memory_gb = float(os.getenv('LGBM_MAX_MEMORY_GB', '6.5'))
        self.num_threads = int(os.getenv('LGBM_NUM_THREADS', '6'))
        
        self.last_trained_count = 0
        
        logger.info(f"ContinuousTrainer initialized: interval={self.training_interval}s, min_samples={self.min_samples}")
    
    async def start_training_loop(self):
        """Main loop for continuous background training"""
        logger.info("Starting continuous training loop...")
        
        while True:
            try:
                sample_count = await self._count_samples()
                new_samples = sample_count - self.last_trained_count
                
                logger.info(f"Training check: {sample_count} total samples, {new_samples} new samples")
                
                if new_samples >= self.min_samples:
                    await self.train_model()
                    self.last_trained_count = sample_count
                else:
                    logger.info(f"Waiting for more samples ({new_samples}/{self.min_samples})")
                
                await asyncio.sleep(self.training_interval)
                
            except Exception as e:
                logger.error(f"Training loop error: {e}", exc_info=True)
                await asyncio.sleep(60)
    
    async def train_model(self):
        """Train model without interrupting predictions"""
        logger.info("=" * 60)
        logger.info("STARTING BACKGROUND TRAINING SESSION")
        logger.info("=" * 60)
        
        try:
            # Load training data
            samples = await self._load_recent_samples()
            
            if len(samples) < self.min_samples:
                logger.warning(f"Insufficient samples: {len(samples)}/{self.min_samples}")
                return
            
            # Prepare training data
            X, y = await self._prepare_training_data(samples)
            
            if len(X) < 50:
                logger.warning(f"Insufficient valid samples: {len(X)}")
                return
            
            # Train new model
            new_model = await self._train_lightgbm(X, y)
            
            # Save new model with versioning
            await self._save_model_versioned(new_model)
            
            # Hot-swap model (atomic operation)
            await self._swap_model(new_model)
            
            logger.info("=" * 60)
            logger.info("TRAINING COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
    
    async def _count_samples(self) -> int:
        """Count available training samples"""
        if not os.path.exists(self.data_path):
            return 0
        
        try:
            with open(self.data_path, 'r') as f:
                return sum(1 for _ in f)
        except Exception as e:
            logger.error(f"Error counting samples: {e}")
            return 0
    
    async def _load_recent_samples(self) -> List[Dict]:
        """Load most recent samples (streaming to save memory)"""
        if not os.path.exists(self.data_path):
            return []
        
        samples = []
        
        try:
            with open(self.data_path, 'r') as f:
                # Load last N samples only
                all_lines = f.readlines()
                recent_lines = all_lines[-self.batch_size:]
                
                for line in recent_lines:
                    try:
                        sample = json.loads(line.strip())
                        samples.append(sample)
                    except json.JSONDecodeError:
                        continue
            
            logger.info(f"Loaded {len(samples)} training samples")
            return samples
            
        except Exception as e:
            logger.error(f"Error loading samples: {e}")
            return []
    
    async def _prepare_training_data(self, samples: List[Dict]) -> tuple:
        """Extract features and labels from samples"""
        X = []
        y = []
        
        for sample in samples:
            try:
                candles = sample.get('candles_5m', [])
                indicators = sample.get('indicators', {})
                label = sample.get('label', 0)
                
                if not candles:
                    continue
                
                features = self._extract_features(candles, indicators)
                X.append(features)
                y.append(label)
                
            except Exception as e:
                logger.warning(f"Error processing sample: {e}")
                continue
        
        X = np.array(X, dtype=np.float32)
        y = np.array(y, dtype=np.int32)
        
        logger.info(f"Prepared {len(X)} training samples with {X.shape[1]} features")
        
        return X, y
    
    def _extract_features(self, candles: List[Dict], indicators: Dict) -> List[float]:
        """Extract same 15 features as model loader"""
        if not candles:
            return [0.0] * 15
        
        recent_candles = candles[-20:]
        closes = [c['close'] for c in recent_candles]
        volumes = [c['volume'] for c in recent_candles]
        highs = [c['high'] for c in recent_candles]
        lows = [c['low'] for c in recent_candles]
        
        features = []
        
        # Price momentum
        if len(closes) >= 5:
            features.append((closes[-1] - closes[-5]) / closes[-5])
        else:
            features.append(0.0)
        
        if len(closes) >= 10:
            features.append((closes[-1] - closes[-10]) / closes[-10])
        else:
            features.append(0.0)
        
        # Technical indicators
        features.append(indicators.get('rsi', 50.0) / 100.0)
        features.append(min(indicators.get('volume_ratio', 1.0), 5.0) / 5.0)
        
        current_price = closes[-1]
        features.append((current_price - indicators.get('ema_20', current_price)) / current_price)
        features.append((current_price - indicators.get('ema_50', current_price)) / current_price)
        
        # MACD
        features.append(indicators.get('macd', 0.0) / current_price)
        features.append(indicators.get('macd_signal', 0.0) / current_price)
        features.append(indicators.get('macd_histogram', 0.0) / current_price)
        
        # Bollinger Bands
        bb_upper = indicators.get('bollinger_upper', current_price)
        bb_lower = indicators.get('bollinger_lower', current_price)
        bb_width = (bb_upper - bb_lower) / current_price if current_price > 0 else 0
        features.append(min(bb_width, 0.1) * 10)
        
        # Volatility
        if len(closes) >= 10:
            volatility = np.std(closes[-10:]) / np.mean(closes[-10:])
            features.append(min(volatility, 0.1) * 10)
        else:
            features.append(0.0)
        
        # ATR
        features.append(min(indicators.get('atr', 0.0) / current_price, 0.05) * 20)
        
        # Price position in range
        if len(highs) >= 10 and len(lows) >= 10:
            high_10 = max(highs[-10:])
            low_10 = min(lows[-10:])
            if high_10 > low_10:
                features.append((current_price - low_10) / (high_10 - low_10))
            else:
                features.append(0.5)
        else:
            features.append(0.5)
        
        # Volume trend
        if len(volumes) >= 10:
            vol_ma = np.mean(volumes[-10:])
            features.append(min(volumes[-1] / vol_ma, 3.0) / 3.0 if vol_ma > 0 else 1.0)
        else:
            features.append(1.0)
        
        # Momentum
        features.append(indicators.get('momentum', 0.0) / 100.0)
        
        return features
    
    async def _train_lightgbm(self, X: np.ndarray, y: np.ndarray) -> lgb.Booster:
        """Train LightGBM model with optimized parameters for 8GB RAM"""
        logger.info(f"Training LightGBM with {len(X)} samples...")
        
        train_data = lgb.Dataset(X, label=y, free_raw_data=True)
        
        # Optimized parameters for 8GB RAM
        params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 63,  # Increased for 8GB
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'max_depth': 7,  # Increased for 8GB
            'num_threads': self.num_threads,
            'max_bin': 511,  # Increased for 8GB
            'min_data_in_leaf': 20,
            'lambda_l1': 0.1,
            'lambda_l2': 0.1
        }
        
        num_boost_round = 300  # Increased for 8GB
        
        new_model = await asyncio.to_thread(
            lgb.train,
            params,
            train_data,
            num_boost_round=num_boost_round
        )
        
        logger.info(f"Training completed: {num_boost_round} rounds")
        
        return new_model
    
    async def _save_model_versioned(self, model: lgb.Booster):
        """Save model with timestamp version"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        versioned_path = self.model_loader.model_path.replace('.txt', f'_{timestamp}.txt')
        
        model.save_model(versioned_path)
        logger.info(f"Model saved with version: {versioned_path}")
    
    async def _swap_model(self, new_model: lgb.Booster):
        """Atomically swap the active model"""
        # Backup current model
        backup_path = self.model_loader.model_path + '.backup'
        if os.path.exists(self.model_loader.model_path):
            shutil.copy2(self.model_loader.model_path, backup_path)
        
        # Save new model
        new_model.save_model(self.model_loader.model_path)
        
        # Hot-swap in memory (atomic)
        self.model_loader.model = new_model
        
        logger.info("✅ Model hot-swapped successfully - predictions continue uninterrupted")


async def main():
    from model_loader_optimized import OptimizedModelLoader
    
    model_path = os.getenv('MODEL_PATH', './models/trading_model.txt')
    model_loader = OptimizedModelLoader(model_path, 'lightgbm')
    model_loader.load()
    
    trainer = ContinuousTrainer(model_loader)
    await trainer.start_training_loop()


if __name__ == "__main__":
    asyncio.run(main())