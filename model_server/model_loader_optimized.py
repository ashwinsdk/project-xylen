import lightgbm as lgb
import numpy as np
import logging
import os
from typing import Dict, List

logger = logging.getLogger(__name__)


class OptimizedModelLoader:
    def __init__(self, model_path: str, model_type: str = 'lightgbm'):
        self.model_path = model_path
        self.model_type = model_type.lower()
        self.model = None
        
        # Memory-optimized LightGBM parameters
        self.max_memory_gb = float(os.getenv('LGBM_MAX_MEMORY_GB', '3.2'))
        self.num_threads = int(os.getenv('LGBM_NUM_THREADS', '4'))
        
        logger.info(f"ModelLoader initialized: path={model_path}, type={model_type}")
        logger.info(f"Memory limit: {self.max_memory_gb}GB, Threads: {self.num_threads}")
    
    def load(self):
        if not os.path.exists(self.model_path):
            logger.warning(f"Model file not found: {self.model_path}")
            logger.info("Creating initial placeholder model...")
            self._create_initial_model()
            return
        
        try:
            if self.model_type == 'lightgbm':
                self.model = lgb.Booster(model_file=self.model_path)
                logger.info("LightGBM model loaded successfully")
            else:
                raise ValueError(f"Unsupported model type: {self.model_type}")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}", exc_info=True)
            logger.info("Creating new model...")
            self._create_initial_model()
    
    def _create_initial_model(self):
        """Create a minimal trained model for cold start"""
        logger.info("Creating initial LightGBM model...")
        
        # Generate synthetic training data
        np.random.seed(42)
        X_train = np.random.randn(100, 15)  # 100 samples, 15 features
        y_train = np.random.randint(0, 2, 100)  # Binary classification
        
        train_data = lgb.Dataset(X_train, label=y_train)
        
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
            'max_bin': 255
        }
        
        self.model = lgb.train(params, train_data, num_boost_round=50)
        
        # Save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        self.model.save_model(self.model_path)
        
        logger.info(f"Initial model created and saved to {self.model_path}")
    
    def is_loaded(self) -> bool:
        return self.model is not None
    
    def predict(self, candles: List[Dict], indicators: Dict, meta: Dict) -> Dict:
        if not self.is_loaded():
            raise RuntimeError("Model not loaded")
        
        try:
            features = self._prepare_features(candles, indicators, meta)
            raw_output = self.model.predict(features)[0]
            
            return self._interpret_output(raw_output)
            
        except Exception as e:
            logger.error(f"Prediction error: {e}", exc_info=True)
            raise
    
    def _prepare_features(self, candles: List[Dict], indicators: Dict, meta: Dict) -> np.ndarray:
        """Extract 15 critical features for trading"""
        if not candles:
            return np.zeros((1, 15), dtype=np.float32)
        
        recent_candles = candles[-20:]
        closes = [c['close'] for c in recent_candles]
        volumes = [c['volume'] for c in recent_candles]
        highs = [c['high'] for c in recent_candles]
        lows = [c['low'] for c in recent_candles]
        
        features = []
        
        # Price momentum features
        if len(closes) >= 5:
            features.append((closes[-1] - closes[-5]) / closes[-5])  # 5-period return
        else:
            features.append(0.0)
        
        if len(closes) >= 10:
            features.append((closes[-1] - closes[-10]) / closes[-10])  # 10-period return
        else:
            features.append(0.0)
        
        # Technical indicators
        features.append(indicators.get('rsi', 50.0) / 100.0)  # Normalized RSI
        features.append(min(indicators.get('volume_ratio', 1.0), 5.0) / 5.0)  # Capped volume ratio
        
        # Moving averages
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
        
        # ATR (volatility indicator)
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
        
        # Momentum indicator
        momentum_value = indicators.get('momentum', 0.0)
        if isinstance(momentum_value, (int, float)):
            features.append(float(momentum_value) / 100.0)
        else:
            features.append(0.0)
        
        features_array = np.array(features, dtype=np.float32).reshape(1, -1)
        
        return features_array
    
    def _interpret_output(self, raw_output: float) -> Dict:
        """Convert model output to trading decision"""
        probability = 1.0 / (1.0 + np.exp(-raw_output))  # Sigmoid
        
        # Confidence-based thresholding
        if probability > 0.65:
            action = "long"
            confidence = probability
        elif probability < 0.35:
            action = "short"
            confidence = 1.0 - probability
        else:
            action = "hold"
            confidence = 1.0 - abs(probability - 0.5) * 2
        
        return {
            'action': action,
            'confidence': float(confidence),
            'stop': None,
            'take_profit': None,
            'raw_score': float(raw_output)
        }
