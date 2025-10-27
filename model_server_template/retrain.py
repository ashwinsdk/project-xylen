import os
import logging
import json
import asyncio
from typing import Dict, List
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


class RetrainManager:
    def __init__(self, model_loader):
        self.model_loader = model_loader
        self.training_data_path = os.getenv('TRAINING_DATA_PATH', './training_data/samples.jsonl')
        self.min_samples_for_retrain = int(os.getenv('MIN_SAMPLES_FOR_RETRAIN', '50'))
        
        os.makedirs(os.path.dirname(self.training_data_path), exist_ok=True)
        
        self.pending_samples = []
        
        logger.info(f"RetrainManager initialized: data_path={self.training_data_path}")
    
    def add_training_sample(self, decision: Dict, outcome: Dict, snapshot: Dict = None):
        sample = {
            'timestamp': datetime.utcnow().isoformat(),
            'decision': decision,
            'outcome': outcome,
            'snapshot': snapshot
        }
        
        self.pending_samples.append(sample)
        
        try:
            with open(self.training_data_path, 'a') as f:
                f.write(json.dumps(sample) + '\n')
            
            logger.debug(f"Training sample saved: pnl={outcome.get('pnl', 0):.2f}")
            
        except Exception as e:
            logger.error(f"Error saving training sample: {e}")
    
    def get_sample_count(self) -> int:
        if not os.path.exists(self.training_data_path):
            return 0
        
        try:
            with open(self.training_data_path, 'r') as f:
                return sum(1 for line in f if line.strip())
        except Exception as e:
            logger.error(f"Error counting samples: {e}")
            return 0
    
    async def retrain(self) -> Dict:
        sample_count = self.get_sample_count()
        
        if sample_count < self.min_samples_for_retrain:
            return {
                'status': 'skipped',
                'reason': f'Not enough samples: {sample_count}/{self.min_samples_for_retrain}',
                'sample_count': sample_count
            }
        
        logger.info(f"Starting retrain with {sample_count} samples")
        
        try:
            samples = self._load_training_samples()
            
            if not samples:
                return {
                    'status': 'failed',
                    'reason': 'No samples loaded',
                    'sample_count': 0
                }
            
            logger.info(f"Loaded {len(samples)} samples for training")
            
            if self.model_loader.model_type == 'lightgbm':
                result = await self._retrain_lightgbm(samples)
            elif self.model_loader.model_type == 'pytorch':
                result = await self._retrain_pytorch(samples)
            else:
                return {
                    'status': 'not_supported',
                    'reason': f'Retraining not implemented for {self.model_loader.model_type}',
                    'sample_count': sample_count
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Retrain error: {e}", exc_info=True)
            return {
                'status': 'failed',
                'reason': str(e),
                'sample_count': sample_count
            }
    
    def _load_training_samples(self) -> List[Dict]:
        if not os.path.exists(self.training_data_path):
            return []
        
        samples = []
        
        try:
            with open(self.training_data_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        sample = json.loads(line)
                        samples.append(sample)
        except Exception as e:
            logger.error(f"Error loading training samples: {e}")
        
        return samples
    
    async def _retrain_lightgbm(self, samples: List[Dict]) -> Dict:
        import lightgbm as lgb
        
        logger.info("Preparing LightGBM training data")
        
        X = []
        y = []
        
        for sample in samples:
            snapshot = sample.get('snapshot', {})
            outcome = sample.get('outcome', {})
            
            if not snapshot or 'indicators' not in snapshot:
                continue
            
            candles = snapshot.get('candles_5m', [])
            indicators = snapshot.get('indicators', {})
            
            if not candles:
                continue
            
            features = self._extract_features(candles, indicators)
            
            pnl = outcome.get('pnl', 0)
            success = 1 if pnl > 0 else 0
            
            X.append(features)
            y.append(success)
        
        if len(X) < 10:
            return {
                'status': 'failed',
                'reason': 'Not enough valid samples after feature extraction',
                'valid_samples': len(X)
            }
        
        X = np.array(X)
        y = np.array(y)
        
        logger.info(f"Training LightGBM with {len(X)} samples")
        
        train_data = lgb.Dataset(X, label=y)
        
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
            'max_depth': 5
        }
        
        num_boost_round = 100
        
        logger.info("Starting LightGBM training...")
        
        new_model = await asyncio.to_thread(
            lgb.train,
            params,
            train_data,
            num_boost_round=num_boost_round
        )
        
        backup_path = self.model_loader.model_path + '.backup'
        if os.path.exists(self.model_loader.model_path):
            os.rename(self.model_loader.model_path, backup_path)
        
        new_model.save_model(self.model_loader.model_path)
        
        logger.info("Reloading updated model...")
        self.model_loader.load()
        
        logger.info("Retrain completed successfully")
        
        return {
            'status': 'success',
            'model_type': 'lightgbm',
            'samples_trained': len(X),
            'num_boost_round': num_boost_round,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _retrain_pytorch(self, samples: List[Dict]) -> Dict:
        logger.warning("PyTorch retraining not fully implemented, using placeholder")
        
        return {
            'status': 'not_implemented',
            'reason': 'PyTorch retraining requires custom training loop',
            'sample_count': len(samples)
        }
    
    def _extract_features(self, candles: List[Dict], indicators: Dict) -> List[float]:
        features = []
        
        if candles:
            recent_candles = candles[-20:]
            closes = [c['close'] for c in recent_candles]
            
            if len(closes) >= 2:
                returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
                features.extend([
                    np.mean(returns),
                    np.std(returns),
                    closes[-1]
                ])
            else:
                features.extend([0.0, 0.0, closes[0]])
        else:
            features.extend([0.0, 0.0, 0.0])
        
        features.append(indicators.get('rsi', 50.0))
        features.append(indicators.get('volume', 0.0))
        features.append(indicators.get('ema_20', 0.0))
        features.append(indicators.get('ema_50', 0.0))
        features.append(indicators.get('macd', 0.0))
        features.append(indicators.get('bb_upper', 0.0))
        features.append(indicators.get('bb_lower', 0.0))
        
        return features
