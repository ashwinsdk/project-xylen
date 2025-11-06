"""import asyncio

Project Xylen - Advanced Ensemble Decision Engineimport logging

Python 3.10.12 compatiblefrom typing import Dict, List, Optional

Implements Xylen Adaptive Consensus algorithm with:import aiohttp

- Weighted voting with exponential performance decayfrom datetime import datetime

- Probability calibration (isotonic regression)

- Uncertainty-aware gating

- Bayesian meta-learner fusionclass EnsembleAggregator:

- Trade cost-aware expected value scoring    def __init__(self, config: Dict):

"""        self.config = config

        self.logger = logging.getLogger(__name__)

import logging        self.model_endpoints = config.get('model_endpoints', [])

import time        self.ensemble_config = config.get('ensemble', {})

import math        self.timeout = config.get('timing', {}).get('model_timeout', 5)

import pickle        

from dataclasses import dataclass        self.model_performance = {}

from typing import Dict, List, Optional, Tuple        for endpoint in self.model_endpoints:

from enum import Enum            key = f"{endpoint['host']}:{endpoint['port']}"

import numpy as np            self.model_performance[key] = {

from sklearn.calibration import CalibratedClassifierCV                "weight": endpoint.get('weight', 1.0),

from sklearn.isotonic import IsotonicRegression                "success_count": 0,

try:                "failure_count": 0,

    import lightgbm as lgb                "avg_response_time": 0.0,

except ImportError:                "last_success": None,

    lgb = None                "enabled": endpoint.get('enabled', True)

            }

logger = logging.getLogger(__name__)    

    async def get_model_predictions(self, snapshot: Dict) -> List[Dict]:

        tasks = []

class EnsembleMethod(Enum):        active_endpoints = [ep for ep in self.model_endpoints if ep.get('enabled', True)]

    """Ensemble aggregation methods"""        

    WEIGHTED_VOTE = "weighted_vote"        if not active_endpoints:

    BAYESIAN_WEIGHTED = "bayesian_weighted"            self.logger.warning("No active model endpoints configured")

    STACKED = "stacked"            return []

        

        for endpoint in active_endpoints:

@dataclass            tasks.append(self._query_model(endpoint, snapshot))

class ModelPrediction:        

    """Individual model prediction"""        results = await asyncio.gather(*tasks, return_exceptions=True)

    model_name: str        

    raw_score: float          # Raw model output (-1 to 1 or 0 to 1)        predictions = []

    confidence: float         # Model-reported confidence (0-1)        for i, result in enumerate(results):

    latency_ms: float         # Response time            if isinstance(result, Exception):

    timestamp: float                self.logger.error(f"Model {active_endpoints[i]['name']} error: {result}")

    metadata: Optional[Dict] = None            elif result is not None:

                predictions.append(result)

        

@dataclass        min_responding = self.ensemble_config.get('min_responding_models', 1)

class ModelPerformance:        if len(predictions) < min_responding:

    """Model performance metrics"""            self.logger.warning(f"Only {len(predictions)} models responded, minimum is {min_responding}")

    model_name: str        

    recent_trades: List[bool]  # Win/loss history (True=win)        return predictions

    win_rate: float    

    sharpe: float    async def _query_model(self, endpoint: Dict, snapshot: Dict) -> Optional[Dict]:

    avg_latency_ms: float        url = f"http://{endpoint['host']}:{endpoint['port']}/predict"

    weight: float        key = f"{endpoint['host']}:{endpoint['port']}"

    last_updated: float        

        payload = {

            "symbol": self.config['trading']['symbol'],

@dataclass            "timeframe": "5m",

class EnsembleDecision:            "candles": snapshot.get('candles_5m', []),

    """Final ensemble decision"""            "indicators": snapshot.get('indicators', {}),

    action: str               # 'BUY', 'SELL', 'HOLD'            "meta": {

    confidence: float         # Calibrated probability (0-1)                "utc": datetime.utcnow().isoformat(),

    expected_value: float     # EV after costs                "candles_1h": snapshot.get('candles_1h', [])

    uncertainty: float        # Model disagreement (std dev)            }

    meta_score: Optional[float]  # Meta-learner score        }

    stop_loss: float        

    take_profit: float        start_time = asyncio.get_event_loop().time()

    reasoning: str        

    model_votes: Dict[str, float]        try:

    timestamp: float            timeout = aiohttp.ClientTimeout(total=self.timeout)

            async with aiohttp.ClientSession(timeout=timeout) as session:

                async with session.post(url, json=payload) as response:

class EnsembleEngine:                    if response.status == 200:

    """                        result = await response.json()

    Xylen Adaptive Consensus - Advanced ensemble decision engine                        

                            response_time = asyncio.get_event_loop().time() - start_time

    Features:                        self._update_performance(key, success=True, response_time=response_time)

    1. Exponential decay weighting based on recent performance                        

    2. Isotonic probability calibration                        result['model_name'] = endpoint['name']

    3. Uncertainty-aware gating (reject high disagreement)                        result['model_key'] = key

    4. Bayesian meta-learner for fusion                        result['response_time'] = response_time

    5. Expected value scoring with trade costs                        

    """                        return result

                        else:

    def __init__(self, config: Dict):                        self.logger.error(f"Model {endpoint['name']} returned status {response.status}")

        """                        self._update_performance(key, success=False)

        Initialize ensemble engine                        return None

                

        Args:        except asyncio.TimeoutError:

            config: Configuration dictionary            self.logger.error(f"Model {endpoint['name']} timeout after {self.timeout}s")

        """            self._update_performance(key, success=False)

        self.config = config            return None

        self.ensemble_config = config.get('ensemble', {})        except Exception as e:

        self.trading_config = config.get('trading', {})            self.logger.error(f"Model {endpoint['name']} error: {e}")

                    self._update_performance(key, success=False)

        # Ensemble method            return None

        self.method = EnsembleMethod(self.ensemble_config.get('method', 'bayesian_weighted'))    

            def _update_performance(self, key: str, success: bool, response_time: float = 0.0):

        # Weighting parameters        if key not in self.model_performance:

        self.weight_decay_halflife = self.ensemble_config.get('weight_decay_halflife', 86400)  # 24h            return

        self.performance_window = self.ensemble_config.get('performance_window', 100)        

        self.min_responding_models = self.ensemble_config.get('min_responding_models', 1)        perf = self.model_performance[key]

                

        # Calibration        if success:

        self.calibration_method = self.ensemble_config.get('calibration_method', 'isotonic')            perf['success_count'] += 1

        self.calibration_samples = self.ensemble_config.get('calibration_samples', 1000)            perf['last_success'] = datetime.utcnow()

        self.calibrator: Optional[IsotonicRegression] = None            

        self.calibration_history: List[Tuple[float, bool]] = []  # (raw_score, outcome)            if perf['avg_response_time'] == 0:

                        perf['avg_response_time'] = response_time

        # Decision thresholds            else:

        self.confidence_threshold = self.ensemble_config.get('confidence_threshold', 0.70)                perf['avg_response_time'] = 0.8 * perf['avg_response_time'] + 0.2 * response_time

        self.uncertainty_threshold = self.ensemble_config.get('uncertainty_threshold', 0.30)        else:

        self.expected_value_threshold = self.ensemble_config.get('expected_value_threshold', 0.01)            perf['failure_count'] += 1

            

        # Trade costs    def aggregate(self, predictions: List[Dict]) -> Dict:

        self.slippage_bps = self.ensemble_config.get('estimate_slippage_bps', 5)        if not predictions:

        self.maker_fee_bps = self.ensemble_config.get('maker_fee_bps', 2)            return {

        self.taker_fee_bps = self.ensemble_config.get('taker_fee_bps', 4)                "action": "hold",

                        "confidence": 0.0,

        # Stop/take parameters                "stop": None,

        self.stop_loss_pct = self.trading_config.get('stop_loss_percent', 0.02)                "take_profit": None,

        self.take_profit_pct = self.trading_config.get('take_profit_percent', 0.05)                "raw_score": 0.0,

                        "participating_models": []

        # Meta-learner            }

        self.meta_learner_enabled = self.ensemble_config.get('meta_learner_enabled', True)        

        self.meta_learner_model = self.ensemble_config.get('meta_learner_model', 'lightgbm')        method = self.ensemble_config.get('method', 'weighted_vote')

        self.meta_learner_path = self.ensemble_config.get('meta_learner_path', './data/meta_learner.txt')        

        self.meta_learner: Optional[any] = None        if method == 'weighted_vote':

        self.meta_learner_features = self.ensemble_config.get('meta_learner_features', [])            return self._weighted_vote(predictions)

        self.meta_training_buffer: List[Tuple[np.ndarray, bool]] = []  # (features, outcome)        elif method == 'average_confidence':

                    return self._average_confidence(predictions)

        # Model performance tracking        elif method == 'majority':

        self.model_performance: Dict[str, ModelPerformance] = {}            return self._majority_vote(predictions)

                else:

        # Load meta-learner if exists            self.logger.warning(f"Unknown ensemble method: {method}, using weighted_vote")

        self._load_meta_learner()            return self._weighted_vote(predictions)

            

        logger.info(f"EnsembleEngine initialized: method={self.method.value}, "    def _weighted_vote(self, predictions: List[Dict]) -> Dict:

                   f"confidence_threshold={self.confidence_threshold}, "        votes = {'long': 0.0, 'short': 0.0, 'hold': 0.0}

                   f"meta_learner={'enabled' if self.meta_learner_enabled else 'disabled'}")        total_weight = 0.0

            

    def aggregate_predictions(        stops = []

        self,        take_profits = []

        predictions: List[ModelPrediction],        participating_models = []

        current_price: float        

    ) -> EnsembleDecision:        weight_decay = self.ensemble_config.get('weight_decay', 0.95)

        """        

        Aggregate model predictions into final decision        for pred in predictions:

                    model_key = pred.get('model_key')

        Args:            base_weight = self.model_performance.get(model_key, {}).get('weight', 1.0)

            predictions: List of model predictions            

            current_price: Current market price            perf = self.model_performance.get(model_key, {})

                        success_rate = perf['success_count'] / max(perf['success_count'] + perf['failure_count'], 1)

        Returns:            performance_weight = base_weight * (success_rate ** weight_decay)

            EnsembleDecision object            

        """            action = pred.get('action', 'hold').lower()

        if len(predictions) < self.min_responding_models:            confidence = pred.get('confidence', 0.0)

            return self._create_hold_decision(            

                "Insufficient responding models",            vote_value = confidence * performance_weight

                predictions,            votes[action] += vote_value

                current_price            total_weight += performance_weight

            )            

                    if pred.get('stop'):

        # Update model weights                stops.append(pred['stop'])

        self._update_model_weights(predictions)            if pred.get('take_profit'):

                        take_profits.append(pred['take_profit'])

        # Calculate weighted scores and uncertainty            

        weighted_scores = []            participating_models.append({

        model_votes = {}                "name": pred.get('model_name'),

                        "action": action,

        for pred in predictions:                "confidence": confidence,

            weight = self._get_model_weight(pred.model_name)                "weight": performance_weight

            weighted_score = pred.raw_score * weight            })

            weighted_scores.append(weighted_score)        

            model_votes[pred.model_name] = weighted_score        if total_weight == 0:

                    final_action = 'hold'

        # Aggregate score            final_confidence = 0.0

        if self.method == EnsembleMethod.WEIGHTED_VOTE:        else:

            agg_score = np.mean(weighted_scores)            final_action = max(votes, key=votes.get)

        elif self.method == EnsembleMethod.BAYESIAN_WEIGHTED:            final_confidence = votes[final_action] / total_weight

            agg_score = self._bayesian_aggregate(predictions)        

        else:        avg_stop = sum(stops) / len(stops) if stops else None

            agg_score = np.mean(weighted_scores)        avg_take_profit = sum(take_profits) / len(take_profits) if take_profits else None

                

        # Calculate uncertainty (model disagreement)        return {

        raw_scores = [p.raw_score for p in predictions]            "action": final_action,

        uncertainty = np.std(raw_scores) if len(raw_scores) > 1 else 0.0            "confidence": final_confidence,

                    "stop": avg_stop,

        # Check uncertainty gate            "take_profit": avg_take_profit,

        if uncertainty > self.uncertainty_threshold:            "raw_score": votes[final_action],

            return self._create_hold_decision(            "participating_models": participating_models,

                f"High model disagreement (σ={uncertainty:.3f})",            "votes": votes

                predictions,        }

                current_price    

            )    def _average_confidence(self, predictions: List[Dict]) -> Dict:

                confidences = {'long': [], 'short': [], 'hold': []}

        # Probability calibration        stops = []

        calibrated_prob = self._calibrate_probability(agg_score)        take_profits = []

                participating_models = []

        # Meta-learner fusion        

        meta_score = None        for pred in predictions:

        if self.meta_learner_enabled and self.meta_learner:            action = pred.get('action', 'hold').lower()

            meta_features = self._extract_meta_features(predictions, agg_score, uncertainty)            confidence = pred.get('confidence', 0.0)

            meta_score = self._meta_predict(meta_features)            confidences[action].append(confidence)

            # Blend with ensemble score            

            final_score = 0.7 * calibrated_prob + 0.3 * meta_score            if pred.get('stop'):

        else:                stops.append(pred['stop'])

            final_score = calibrated_prob            if pred.get('take_profit'):

                        take_profits.append(pred['take_profit'])

        # Determine action            

        if final_score > 0.5:            participating_models.append({

            action = "BUY"                "name": pred.get('model_name'),

            confidence = final_score                "action": action,

        elif final_score < 0.5:                "confidence": confidence

            action = "SELL"            })

            confidence = 1 - final_score        

        else:        avg_confidences = {

            action = "HOLD"            action: sum(conf_list) / len(conf_list) if conf_list else 0.0

            confidence = 0.5            for action, conf_list in confidences.items()

                }

        # Check confidence threshold        

        if confidence < self.confidence_threshold:        final_action = max(avg_confidences, key=avg_confidences.get)

            return self._create_hold_decision(        final_confidence = avg_confidences[final_action]

                f"Confidence below threshold ({confidence:.3f} < {self.confidence_threshold})",        

                predictions,        avg_stop = sum(stops) / len(stops) if stops else None

                current_price        avg_take_profit = sum(take_profits) / len(take_profits) if take_profits else None

            )        

                return {

        # Calculate expected value with trade costs            "action": final_action,

        expected_value = self._calculate_expected_value(            "confidence": final_confidence,

            action,            "stop": avg_stop,

            confidence,            "take_profit": avg_take_profit,

            current_price            "raw_score": final_confidence,

        )            "participating_models": participating_models

                }

        # Check EV threshold    

        if expected_value < self.expected_value_threshold:    def _majority_vote(self, predictions: List[Dict]) -> Dict:

            return self._create_hold_decision(        votes = {'long': 0, 'short': 0, 'hold': 0}

                f"Expected value below threshold (EV={expected_value:.4f})",        stops = []

                predictions,        take_profits = []

                current_price        participating_models = []

            )        

                for pred in predictions:

        # Calculate stop/take prices            action = pred.get('action', 'hold').lower()

        if action == "BUY":            votes[action] += 1

            stop_loss = current_price * (1 - self.stop_loss_pct)            

            take_profit = current_price * (1 + self.take_profit_pct)            if pred.get('stop'):

        elif action == "SELL":                stops.append(pred['stop'])

            stop_loss = current_price * (1 + self.stop_loss_pct)            if pred.get('take_profit'):

            take_profit = current_price * (1 - self.take_profit_pct)                take_profits.append(pred['take_profit'])

        else:            

            stop_loss = current_price            participating_models.append({

            take_profit = current_price                "name": pred.get('model_name'),

                        "action": action,

        return EnsembleDecision(                "confidence": pred.get('confidence', 0.0)

            action=action,            })

            confidence=confidence,        

            expected_value=expected_value,        final_action = max(votes, key=votes.get)

            uncertainty=uncertainty,        final_confidence = votes[final_action] / len(predictions)

            meta_score=meta_score,        

            stop_loss=stop_loss,        avg_stop = sum(stops) / len(stops) if stops else None

            take_profit=take_profit,        avg_take_profit = sum(take_profits) / len(take_profits) if take_profits else None

            reasoning=f"{action} signal with {confidence:.1%} confidence (EV={expected_value:.3f})",        

            model_votes=model_votes,        return {

            timestamp=time.time()            "action": final_action,

        )            "confidence": final_confidence,

                "stop": avg_stop,

    def _bayesian_aggregate(self, predictions: List[ModelPrediction]) -> float:            "take_profit": avg_take_profit,

        """Bayesian aggregation with weighted voting"""            "raw_score": votes[final_action],

        weighted_sum = 0.0            "participating_models": participating_models,

        weight_sum = 0.0            "votes": votes

                }

        for pred in predictions:    

            model_weight = self._get_model_weight(pred.model_name)    async def send_retrain_feedback(self, feedback_data: Dict):

            confidence_weight = pred.confidence        tasks = []

            variance = max(1 - pred.confidence, 0.01)        active_endpoints = [ep for ep in self.model_endpoints if ep.get('enabled', True)]

            inv_var_weight = 1.0 / variance        

                    for endpoint in active_endpoints:

            final_weight = model_weight * confidence_weight * inv_var_weight            tasks.append(self._send_feedback_to_model(endpoint, feedback_data))

                    

            weighted_sum += pred.raw_score * final_weight        results = await asyncio.gather(*tasks, return_exceptions=True)

            weight_sum += final_weight        

                success_count = sum(1 for r in results if r is True)

        return weighted_sum / weight_sum if weight_sum > 0 else 0.0        self.logger.info(f"Sent feedback to {success_count}/{len(active_endpoints)} models")

        

    def _get_model_weight(self, model_name: str) -> float:    async def _send_feedback_to_model(self, endpoint: Dict, feedback_data: Dict) -> bool:

        """Get current weight for a model with exponential decay"""        url = f"http://{endpoint['host']}:{endpoint['port']}/retrain"

        if model_name not in self.model_performance:        

            return 1.0        try:

                    timeout = aiohttp.ClientTimeout(total=10)

        perf = self.model_performance[model_name]            async with aiohttp.ClientSession(timeout=timeout) as session:

        base_weight = perf.weight                async with session.post(url, json=feedback_data) as response:

        performance_mult = (perf.win_rate * 0.6 + min(perf.sharpe / 2.0, 1.0) * 0.4)                    if response.status == 200:

                                self.logger.debug(f"Feedback sent to {endpoint['name']}")

        time_since_update = time.time() - perf.last_updated                        return True

        decay_factor = math.exp(-time_since_update / self.weight_decay_halflife)                    else:

                                self.logger.warning(f"Feedback to {endpoint['name']} failed: {response.status}")

        final_weight = base_weight * performance_mult * decay_factor                        return False

        return max(0.1, min(final_weight, 2.0))        except Exception as e:

                self.logger.error(f"Error sending feedback to {endpoint['name']}: {e}")

    def _update_model_weights(self, predictions: List[ModelPrediction]):            return False

        """Update model performance tracking"""    

        for pred in predictions:    async def check_model_health(self):

            if pred.model_name not in self.model_performance:        tasks = []

                self.model_performance[pred.model_name] = ModelPerformance(        active_endpoints = [ep for ep in self.model_endpoints if ep.get('enabled', True)]

                    model_name=pred.model_name,        

                    recent_trades=[],        for endpoint in active_endpoints:

                    win_rate=0.5,            tasks.append(self._check_model_health(endpoint))

                    sharpe=0.0,        

                    avg_latency_ms=pred.latency_ms,        results = await asyncio.gather(*tasks, return_exceptions=True)

                    weight=1.0,        

                    last_updated=time.time()        healthy_count = sum(1 for r in results if isinstance(r, dict) and r.get('healthy'))

                )        self.logger.info(f"Health check: {healthy_count}/{len(active_endpoints)} models healthy")

            else:        

                perf = self.model_performance[pred.model_name]        return results

                perf.avg_latency_ms = 0.9 * perf.avg_latency_ms + 0.1 * pred.latency_ms    

                perf.last_updated = time.time()    async def _check_model_health(self, endpoint: Dict) -> Dict:

            url = f"http://{endpoint['host']}:{endpoint['port']}/health"

    def update_model_performance(self, model_name: str, trade_won: bool):        key = f"{endpoint['host']}:{endpoint['port']}"

        """Update model performance after trade outcome"""        

        if model_name not in self.model_performance:        try:

            return            timeout = aiohttp.ClientTimeout(total=5)

                    async with aiohttp.ClientSession(timeout=timeout) as session:

        perf = self.model_performance[model_name]                async with session.get(url) as response:

        perf.recent_trades.append(trade_won)                    if response.status == 200:

        if len(perf.recent_trades) > self.performance_window:                        health_data = await response.json()

            perf.recent_trades.pop(0)                        return {

                                    "model_name": endpoint['name'],

        if perf.recent_trades:                            "healthy": True,

            perf.win_rate = sum(perf.recent_trades) / len(perf.recent_trades)                            "data": health_data,

                                    "performance": self.model_performance.get(key)

        if len(perf.recent_trades) > 10:                        }

            returns = [1.0 if w else -1.0 for w in perf.recent_trades]                    else:

            avg_return = np.mean(returns)                        return {

            std_return = np.std(returns)                            "model_name": endpoint['name'],

            perf.sharpe = avg_return / std_return if std_return > 0 else 0.0                            "healthy": False,

                                    "error": f"Status {response.status}"

        perf.last_updated = time.time()                        }

            except Exception as e:

    def _calibrate_probability(self, raw_score: float) -> float:            return {

        """Calibrate raw model score to probability"""                "model_name": endpoint['name'],

        if self.calibration_method == 'none' or not self.calibrator:                "healthy": False,

            return (raw_score + 1) / 2                "error": str(e)

                    }

        try:
            score_array = np.array([[raw_score]])
            calibrated = self.calibrator.predict(score_array)[0]
            return np.clip(calibrated, 0.0, 1.0)
        except Exception as e:
            logger.warning(f"Calibration failed: {e}")
            return (raw_score + 1) / 2
    
    def _calculate_expected_value(self, action: str, confidence: float, current_price: float) -> float:
        """Calculate expected value of trade after costs"""
        if action == "HOLD":
            return 0.0
        
        avg_win = self.take_profit_pct
        avg_loss = self.stop_loss_pct
        
        p_win = confidence
        p_loss = 1 - confidence
        expected_return = p_win * avg_win - p_loss * avg_loss
        
        slippage_cost = self.slippage_bps / 10000
        fee_cost = self.taker_fee_bps / 10000
        total_cost = (slippage_cost + fee_cost) * 2
        
        return expected_return - total_cost
    
    def _extract_meta_features(self, predictions: List[ModelPrediction], agg_score: float, uncertainty: float) -> np.ndarray:
        """Extract features for meta-learner"""
        features = []
        
        for pred in predictions:
            features.append(pred.raw_score)
        while len(features) < 5:
            features.append(0.0)
        
        for pred in predictions:
            features.append(pred.confidence)
        while len(features) < 10:
            features.append(0.0)
        
        features.extend([agg_score, uncertainty, len(predictions)])
        
        for pred in predictions:
            if pred.model_name in self.model_performance:
                features.append(self.model_performance[pred.model_name].win_rate)
            else:
                features.append(0.5)
        while len(features) < 18:
            features.append(0.5)
        
        for pred in predictions:
            features.append(pred.latency_ms / 1000.0)
        while len(features) < 23:
            features.append(0.0)
        
        return np.array(features)
    
    def _meta_predict(self, features: np.ndarray) -> float:
        """Get meta-learner prediction"""
        try:
            if self.meta_learner_model == 'lightgbm' and lgb:
                pred = self.meta_learner.predict([features])[0]
                return np.clip(pred, 0.0, 1.0)
            else:
                pred = self.meta_learner.predict_proba([features])[0][1]
                return pred
        except Exception as e:
            logger.warning(f"Meta-learner prediction failed: {e}")
            return 0.5
    
    def _load_meta_learner(self):
        """Load meta-learner from disk"""
        try:
            with open(self.meta_learner_path, 'rb') as f:
                self.meta_learner = pickle.load(f)
            logger.info(f"Meta-learner loaded from {self.meta_learner_path}")
        except FileNotFoundError:
            logger.info("No existing meta-learner found")
        except Exception as e:
            logger.warning(f"Failed to load meta-learner: {e}")
    
    def _create_hold_decision(self, reason: str, predictions: List[ModelPrediction], current_price: float) -> EnsembleDecision:
        """Create a HOLD decision"""
        model_votes = {p.model_name: p.raw_score for p in predictions}
        
        return EnsembleDecision(
            action="HOLD",
            confidence=0.0,
            expected_value=0.0,
            uncertainty=0.0,
            meta_score=None,
            stop_loss=current_price,
            take_profit=current_price,
            reasoning=reason,
            model_votes=model_votes,
            timestamp=time.time()
        )
    
    def get_model_rankings(self) -> List[Dict]:
        """Get ranked list of models by performance"""
        rankings = []
        
        for name, perf in self.model_performance.items():
            weight = self._get_model_weight(name)
            rankings.append({
                'model': name,
                'weight': weight,
                'win_rate': perf.win_rate,
                'sharpe': perf.sharpe,
                'trades': len(perf.recent_trades),
                'avg_latency_ms': perf.avg_latency_ms
            })
        
        rankings.sort(key=lambda x: x['weight'], reverse=True)
        return rankings
