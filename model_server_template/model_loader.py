import os
import logging
import numpy as np
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)


class ModelLoader:
    def __init__(self, model_path: str, model_type: str = 'onnx'):
        self.model_path = model_path
        self.model_type = model_type.lower()
        self.model = None
        self.session = None
        
        logger.info(f"ModelLoader initialized: path={model_path}, type={model_type}")
    
    def load(self):
        if not os.path.exists(self.model_path):
            logger.warning(f"Model file not found: {self.model_path}")
            logger.warning("Server will use placeholder predictions")
            return
        
        try:
            if self.model_type == 'onnx':
                self._load_onnx()
            elif self.model_type == 'pytorch':
                self._load_pytorch()
            elif self.model_type == 'lightgbm':
                self._load_lightgbm()
            else:
                raise ValueError(f"Unsupported model type: {self.model_type}")
            
            logger.info(f"Model loaded successfully: {self.model_type}")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}", exc_info=True)
            raise
    
    def _load_onnx(self):
        import onnxruntime as ort
        
        providers = ['CPUExecutionProvider']
        self.session = ort.InferenceSession(self.model_path, providers=providers)
        
        logger.info(f"ONNX model loaded with providers: {providers}")
    
    def _load_pytorch(self):
        import torch
        
        self.model = torch.jit.load(self.model_path)
        self.model.eval()
        
        logger.info("PyTorch model loaded")
    
    def _load_lightgbm(self):
        import lightgbm as lgb
        
        self.model = lgb.Booster(model_file=self.model_path)
        
        logger.info("LightGBM model loaded")
    
    def is_loaded(self) -> bool:
        if self.model_type == 'onnx':
            return self.session is not None
        else:
            return self.model is not None
    
    def predict(self, candles: List[Dict], indicators: Dict, meta: Dict) -> Dict:
        if not self.is_loaded():
            raise RuntimeError("Model not loaded")
        
        try:
            features = self._prepare_features(candles, indicators, meta)
            
            if self.model_type == 'onnx':
                return self._predict_onnx(features)
            elif self.model_type == 'pytorch':
                return self._predict_pytorch(features)
            elif self.model_type == 'lightgbm':
                return self._predict_lightgbm(features)
            
        except Exception as e:
            logger.error(f"Prediction error: {e}", exc_info=True)
            raise
    
    def _prepare_features(self, candles: List[Dict], indicators: Dict, meta: Dict) -> np.ndarray:
        if not candles:
            return np.zeros((1, 10), dtype=np.float32)
        
        recent_candles = candles[-20:]
        
        features = []
        
        closes = [c['close'] for c in recent_candles]
        if len(closes) >= 2:
            returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
            features.extend([
                np.mean(returns),
                np.std(returns),
                closes[-1]
            ])
        else:
            features.extend([0.0, 0.0, closes[0] if closes else 0.0])
        
        features.append(indicators.get('rsi', 50.0))
        features.append(indicators.get('volume', 0.0))
        features.append(indicators.get('ema_20', closes[-1] if closes else 0.0))
        features.append(indicators.get('ema_50', closes[-1] if closes else 0.0))
        features.append(indicators.get('macd', 0.0))
        features.append(indicators.get('bb_upper', 0.0))
        features.append(indicators.get('bb_lower', 0.0))
        
        features_array = np.array(features, dtype=np.float32).reshape(1, -1)
        
        return features_array
    
    def _predict_onnx(self, features: np.ndarray) -> Dict:
        input_name = self.session.get_inputs()[0].name
        outputs = self.session.run(None, {input_name: features})
        
        raw_output = outputs[0][0]
        
        return self._interpret_output(raw_output)
    
    def _predict_pytorch(self, features: np.ndarray) -> Dict:
        import torch
        
        input_tensor = torch.from_numpy(features)
        
        with torch.no_grad():
            output = self.model(input_tensor)
        
        raw_output = output.numpy()[0]
        
        return self._interpret_output(raw_output)
    
    def _predict_lightgbm(self, features: np.ndarray) -> Dict:
        raw_output = self.model.predict(features)[0]
        
        return self._interpret_output(raw_output)
    
    def _interpret_output(self, raw_output) -> Dict:
        if isinstance(raw_output, np.ndarray):
            if len(raw_output) == 3:
                long_score = float(raw_output[0])
                short_score = float(raw_output[1])
                hold_score = float(raw_output[2])
                
                scores = {'long': long_score, 'short': short_score, 'hold': hold_score}
                action = max(scores, key=scores.get)
                confidence = scores[action]
            else:
                score = float(raw_output[0] if len(raw_output) > 0 else raw_output)
                
                if score > 0.1:
                    action = 'long'
                    confidence = min(abs(score), 1.0)
                elif score < -0.1:
                    action = 'short'
                    confidence = min(abs(score), 1.0)
                else:
                    action = 'hold'
                    confidence = 0.5
        else:
            score = float(raw_output)
            
            if score > 0.1:
                action = 'long'
                confidence = min(abs(score), 1.0)
            elif score < -0.1:
                action = 'short'
                confidence = min(abs(score), 1.0)
            else:
                action = 'hold'
                confidence = 0.5
        
        return {
            'action': action,
            'confidence': confidence,
            'stop': None,
            'take_profit': None,
            'raw_score': float(raw_output[0] if isinstance(raw_output, np.ndarray) else raw_output)
        }
