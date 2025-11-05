import lightgbm as lgb
import numpy as np
import json
import os
import logging
from typing import Dict, List
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class OptimizedRetrainManager:
    def __init__(self, model_loader):
        self.model_loader = model_loader
        self.training_data_path = os.getenv('TRAINING_DATA_PATH', './training_data/samples.jsonl')
        self.min_samples_for_retrain = int(os.getenv('MIN_SAMPLES_FOR_RETRAIN', '50'))
        
        # Memory optimization
        self.max_memory_gb = float(os.getenv('LGBM_MAX_MEMORY_GB', '3.2'))
        self.num_threads = int(os.getenv('LGBM_NUM_THREADS', '4'))
        
        os.makedirs(os.path.dirname(self.training_data_path), exist_ok=True)
        
        self.pending_samples = []
        
        logger.info(f"RetrainManager initialized: data_path={self.training_data_path}")
        logger.info(f"Memory limit: {self.max_memory_gb}GB, Min samples: {self.min_samples_for_retrain}")
    
    def add_training_sample(self, decision: Dict, outcome: Dict, snapshot: Dict = None):
        """Add training sample with memory-efficient storage"""
        sample = {
            'timestamp': datetime.utcnow().isoformat(),
            'decision': decision,
            'outcome': outcome,
            'snapshot': {
                'candles_5m': snapshot.get('candles_5m', [])[-20:] if snapshot else [],
                'indicators': snapshot.get('indicators', {}) if snapshot else {}
            }
        }
        
        self.pending_samples.append(sample)
        
        try:
            with open(self.training_data_path, 'a') as f:
                f.write(json.dumps(sample) + '\n')
            
            logger.debug(f"Training sample added: {len(self.pending_samples)} pending")
            
        except Exception as e:
            logger.error(f"Error saving training sample: {e}")
    
    def get_sample_count(self) -> int:
        if not os.path.exists(self.training_data_path):
            return 0
        
        try:
            with open(self.training_data_path, 'r') as f:
                return sum(1 for _ in f)
        except Exception as e:
            logger.error(f"Error counting samples: {e}")
            return 0
    
    async def retrain(self) -> Dict:
        """Memory-optimized retraining with streaming data loading"""
        sample_count = self.get_sample_count()
        
        if sample_count < self.min_samples_for_retrain:
            return {
                'status': 'skipped',
                'reason': f'Not enough samples ({sample_count}/{self.min_samples_for_retrain})'
            }
        
        logger.info(f"Starting retrain with {sample_count} samples")
        
        try:
            samples = await self._load_training_samples_streaming()
            
            if len(samples) < self.min_samples_for_retrain:
                return {'status': 'insufficient_data', 'sample_count': len(samples)}
            
            result = await self._retrain_lightgbm(samples)
            
            return result
            
        except Exception as e:
            logger.error(f"Retrain failed: {e}", exc_info=True)
            return {'status': 'error', 'error': str(e)}
    
    async def _load_training_samples_streaming(self) -> List[Dict]:
        """Load samples in streaming fashion to minimize memory"""
        if not os.path.exists(self.training_data_path):
            return []
        
        samples = []
        
        try:
            with open(self.training_data_path, 'r') as f:
                for line in f:
                    try:
                        sample = json.loads(line.strip())
                        samples.append(sample)
                    except json.JSONDecodeError:
                        continue
            
            logger.info(f"Loaded {len(samples)} training samples")
            
        except Exception as e:
            logger.error(f"Error loading training samples: {e}")
        
        return samples
    
    async def _retrain_lightgbm(self, samples: List[Dict]) -> Dict:
        """Retrain LightGBM with memory optimization"""
        logger.info("Preparing LightGBM training data")
        
        X = []
        y = []
        
        for sample in samples:
            try:
                snapshot = sample.get('snapshot', {})
                candles = snapshot.get('candles_5m', [])
                indicators = snapshot.get('indicators', {})
                
                if not candles:
                    continue
                
                features = self._extract_features(candles, indicators)
                X.append(features)
                
                # Label: 1 if profitable, 0 otherwise
                outcome = sample.get('outcome', {})
                pnl = outcome.get('pnl', 0.0)
                y.append(1 if pnl > 0 else 0)
                
            except Exception as e:
                logger.warning(f"Error processing sample: {e}")
                continue
        
        if len(X) < 10:
            return {'status': 'insufficient_valid_data', 'valid_samples': len(X)}
        
        X = np.array(X, dtype=np.float32)
        y = np.array(y, dtype=np.int32)
        
        logger.info(f"Training LightGBM with {len(X)} samples, Memory limit: {self.max_memory_gb}GB")
        
        train_data = lgb.Dataset(X, label=y, free_raw_data=True)
        
        params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'max_depth': 5,
            'num_threads': self.num_threads,
            'max_bin': 255,
            'min_data_in_leaf': 20,
            'lambda_l1': 0.1,
            'lambda_l2': 0.1
        }
        
        num_boost_round = 200
        
        logger.info("Starting LightGBM training...")
        
        new_model = await asyncio.to_thread(
            lgb.train,
            params,
            train_data,
            num_boost_round=num_boost_round
        )
        
        # Backup old model
        backup_path = self.model_loader.model_path + '.backup'
        if os.path.exists(self.model_loader.model_path):
            os.replace(self.model_loader.model_path, backup_path)
        
        # Save new model
        new_model.save_model(self.model_loader.model_path)
        
        logger.info("Reloading updated model...")
        self.model_loader.model = new_model
        
        logger.info("Retrain completed successfully")
        
        return {
            'status': 'success',
            'model_type': 'lightgbm',
            'samples_trained': len(X),
            'num_boost_round': num_boost_round,
            'feature_count': X.shape[1],
            'timestamp': datetime.utcnow().isoformat()
        }
    
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
        
        # MACD features - HANDLE BOTH DICT AND FLOAT
        macd_value = indicators.get('macd', {})
        
        if isinstance(macd_value, dict):
            features.append(macd_value.get('macd', 0.0) / current_price)
            features.append(macd_value.get('signal', 0.0) / current_price)
            features.append(macd_value.get('histogram', 0.0) / current_price)
        elif isinstance(macd_value, (int, float)):
            features.append(float(macd_value) / current_price)
            features.append(0.0)
            features.append(0.0)
        else:
            features.append(0.0)
            features.append(0.0)
            features.append(0.0)
        
        # Bollinger Bands - HANDLE BOTH DICT AND FLOAT
        bb = indicators.get('bollinger_bands', {})
        
        if isinstance(bb, dict):
            bb_upper = bb.get('upper', current_price)
            bb_lower = bb.get('lower', current_price)
            bb_width = (bb_upper - bb_lower) / current_price if current_price > 0 else 0
            features.append(min(bb_width, 0.1) * 10)
        else:
            features.append(0.0)
        
        # Volatility
        if len(closes) >= 10:
            volatility = np.std(closes[-10:]) / np.mean(closes[-10:])
            features.append(min(volatility, 0.1) * 10)
        else:
            features.append(0.0)
        
        # ATR
        atr_value = indicators.get('atr', 0.0)
        if isinstance(atr_value, (int, float)):
            features.append(min(float(atr_value) / current_price, 0.05) * 20)
        else:
            features.append(0.0)
        
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
        momentum_value = indicators.get('momentum', 0.0)
        if isinstance(momentum_value, (int, float)):
            features.append(float(momentum_value) / 100.0)
        else:
            features.append(0.0)
        
        return features
