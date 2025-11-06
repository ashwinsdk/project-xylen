import asyncio
import logging
from typing import Dict, List, Optional
import aiohttp
from datetime import datetime


class EnsembleAggregator:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.model_endpoints = config.get('model_endpoints', [])
        self.ensemble_config = config.get('ensemble', {})
        self.timeout = config.get('timing', {}).get('model_timeout', 5)
        
        self.model_performance = {}
        for endpoint in self.model_endpoints:
            key = f"{endpoint['host']}:{endpoint['port']}"
            self.model_performance[key] = {
                "weight": endpoint.get('weight', 1.0),
                "success_count": 0,
                "failure_count": 0,
                "avg_response_time": 0.0,
                "last_success": None,
                "enabled": endpoint.get('enabled', True)
            }
    
    async def get_model_predictions(self, snapshot: Dict) -> List[Dict]:
        tasks = []
        active_endpoints = [ep for ep in self.model_endpoints if ep.get('enabled', True)]
        
        if not active_endpoints:
            self.logger.warning("No active model endpoints configured")
            return []
        
        for endpoint in active_endpoints:
            tasks.append(self._query_model(endpoint, snapshot))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        predictions = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Model {active_endpoints[i]['name']} error: {result}")
            elif result is not None:
                predictions.append(result)
        
        min_responding = self.ensemble_config.get('min_responding_models', 1)
        if len(predictions) < min_responding:
            self.logger.warning(f"Only {len(predictions)} models responded, minimum is {min_responding}")
        
        return predictions
    
    async def _query_model(self, endpoint: Dict, snapshot: Dict) -> Optional[Dict]:
        url = f"http://{endpoint['host']}:{endpoint['port']}/predict"
        key = f"{endpoint['host']}:{endpoint['port']}"
        
        payload = {
            "symbol": self.config['trading']['symbol'],
            "timeframe": "5m",
            "candles": snapshot.get('candles_5m', []),
            "indicators": snapshot.get('indicators', {}),
            "meta": {
                "utc": datetime.utcnow().isoformat(),
                "candles_1h": snapshot.get('candles_1h', [])
            }
        }
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        response_time = asyncio.get_event_loop().time() - start_time
                        self._update_performance(key, success=True, response_time=response_time)
                        
                        result['model_name'] = endpoint['name']
                        result['model_key'] = key
                        result['response_time'] = response_time
                        
                        return result
                    else:
                        self.logger.error(f"Model {endpoint['name']} returned status {response.status}")
                        self._update_performance(key, success=False)
                        return None
        
        except asyncio.TimeoutError:
            self.logger.error(f"Model {endpoint['name']} timeout after {self.timeout}s")
            self._update_performance(key, success=False)
            return None
        except Exception as e:
            self.logger.error(f"Model {endpoint['name']} error: {e}")
            self._update_performance(key, success=False)
            return None
    
    def _update_performance(self, key: str, success: bool, response_time: float = 0.0):
        if key not in self.model_performance:
            return
        
        perf = self.model_performance[key]
        
        if success:
            perf['success_count'] += 1
            perf['last_success'] = datetime.utcnow()
            
            if perf['avg_response_time'] == 0:
                perf['avg_response_time'] = response_time
            else:
                perf['avg_response_time'] = 0.8 * perf['avg_response_time'] + 0.2 * response_time
        else:
            perf['failure_count'] += 1
    
    def aggregate(self, predictions: List[Dict]) -> Dict:
        if not predictions:
            return {
                "action": "hold",
                "confidence": 0.0,
                "stop": None,
                "take_profit": None,
                "raw_score": 0.0,
                "participating_models": []
            }
        
        method = self.ensemble_config.get('method', 'weighted_vote')
        
        if method == 'weighted_vote':
            return self._weighted_vote(predictions)
        elif method == 'average_confidence':
            return self._average_confidence(predictions)
        elif method == 'majority':
            return self._majority_vote(predictions)
        else:
            self.logger.warning(f"Unknown ensemble method: {method}, using weighted_vote")
            return self._weighted_vote(predictions)
    
    def _weighted_vote(self, predictions: List[Dict]) -> Dict:
        votes = {'long': 0.0, 'short': 0.0, 'hold': 0.0}
        total_weight = 0.0
        
        stops = []
        take_profits = []
        participating_models = []
        
        weight_decay = self.ensemble_config.get('weight_decay', 0.95)
        
        for pred in predictions:
            model_key = pred.get('model_key')
            base_weight = self.model_performance.get(model_key, {}).get('weight', 1.0)
            
            perf = self.model_performance.get(model_key, {})
            success_rate = perf['success_count'] / max(perf['success_count'] + perf['failure_count'], 1)
            performance_weight = base_weight * (success_rate ** weight_decay)
            
            action = pred.get('action', 'hold').lower()
            confidence = pred.get('confidence', 0.0)
            
            vote_value = confidence * performance_weight
            votes[action] += vote_value
            total_weight += performance_weight
            
            if pred.get('stop'):
                stops.append(pred['stop'])
            if pred.get('take_profit'):
                take_profits.append(pred['take_profit'])
            
            participating_models.append({
                "name": pred.get('model_name'),
                "action": action,
                "confidence": confidence,
                "weight": performance_weight
            })
        
        if total_weight == 0:
            final_action = 'hold'
            final_confidence = 0.0
        else:
            final_action = max(votes, key=votes.get)
            final_confidence = votes[final_action] / total_weight
        
        avg_stop = sum(stops) / len(stops) if stops else None
        avg_take_profit = sum(take_profits) / len(take_profits) if take_profits else None
        
        return {
            "action": final_action,
            "confidence": final_confidence,
            "stop": avg_stop,
            "take_profit": avg_take_profit,
            "raw_score": votes[final_action],
            "participating_models": participating_models,
            "votes": votes
        }
    
    def _average_confidence(self, predictions: List[Dict]) -> Dict:
        confidences = {'long': [], 'short': [], 'hold': []}
        stops = []
        take_profits = []
        participating_models = []
        
        for pred in predictions:
            action = pred.get('action', 'hold').lower()
            confidence = pred.get('confidence', 0.0)
            confidences[action].append(confidence)
            
            if pred.get('stop'):
                stops.append(pred['stop'])
            if pred.get('take_profit'):
                take_profits.append(pred['take_profit'])
            
            participating_models.append({
                "name": pred.get('model_name'),
                "action": action,
                "confidence": confidence
            })
        
        avg_confidences = {
            action: sum(conf_list) / len(conf_list) if conf_list else 0.0
            for action, conf_list in confidences.items()
        }
        
        final_action = max(avg_confidences, key=avg_confidences.get)
        final_confidence = avg_confidences[final_action]
        
        avg_stop = sum(stops) / len(stops) if stops else None
        avg_take_profit = sum(take_profits) / len(take_profits) if take_profits else None
        
        return {
            "action": final_action,
            "confidence": final_confidence,
            "stop": avg_stop,
            "take_profit": avg_take_profit,
            "raw_score": final_confidence,
            "participating_models": participating_models
        }
    
    def _majority_vote(self, predictions: List[Dict]) -> Dict:
        votes = {'long': 0, 'short': 0, 'hold': 0}
        stops = []
        take_profits = []
        participating_models = []
        
        for pred in predictions:
            action = pred.get('action', 'hold').lower()
            votes[action] += 1
            
            if pred.get('stop'):
                stops.append(pred['stop'])
            if pred.get('take_profit'):
                take_profits.append(pred['take_profit'])
            
            participating_models.append({
                "name": pred.get('model_name'),
                "action": action,
                "confidence": pred.get('confidence', 0.0)
            })
        
        final_action = max(votes, key=votes.get)
        final_confidence = votes[final_action] / len(predictions)
        
        avg_stop = sum(stops) / len(stops) if stops else None
        avg_take_profit = sum(take_profits) / len(take_profits) if take_profits else None
        
        return {
            "action": final_action,
            "confidence": final_confidence,
            "stop": avg_stop,
            "take_profit": avg_take_profit,
            "raw_score": votes[final_action],
            "participating_models": participating_models,
            "votes": votes
        }
    
    async def send_retrain_feedback(self, feedback_data: Dict):
        tasks = []
        active_endpoints = [ep for ep in self.model_endpoints if ep.get('enabled', True)]
        
        for endpoint in active_endpoints:
            tasks.append(self._send_feedback_to_model(endpoint, feedback_data))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        self.logger.info(f"Sent feedback to {success_count}/{len(active_endpoints)} models")
    
    async def _send_feedback_to_model(self, endpoint: Dict, feedback_data: Dict) -> bool:
        url = f"http://{endpoint['host']}:{endpoint['port']}/retrain"
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=feedback_data) as response:
                    if response.status == 200:
                        self.logger.debug(f"Feedback sent to {endpoint['name']}")
                        return True
                    else:
                        self.logger.warning(f"Feedback to {endpoint['name']} failed: {response.status}")
                        return False
        except Exception as e:
            self.logger.error(f"Error sending feedback to {endpoint['name']}: {e}")
            return False
    
    async def check_model_health(self):
        tasks = []
        active_endpoints = [ep for ep in self.model_endpoints if ep.get('enabled', True)]
        
        for endpoint in active_endpoints:
            tasks.append(self._check_model_health(endpoint))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        healthy_count = sum(1 for r in results if isinstance(r, dict) and r.get('healthy'))
        self.logger.info(f"Health check: {healthy_count}/{len(active_endpoints)} models healthy")
        
        return results
    
    async def _check_model_health(self, endpoint: Dict) -> Dict:
        url = f"http://{endpoint['host']}:{endpoint['port']}/health"
        key = f"{endpoint['host']}:{endpoint['port']}"
        
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        return {
                            "model_name": endpoint['name'],
                            "healthy": True,
                            "data": health_data,
                            "performance": self.model_performance.get(key)
                        }
                    else:
                        return {
                            "model_name": endpoint['name'],
                            "healthy": False,
                            "error": f"Status {response.status}"
                        }
        except Exception as e:
            return {
                "model_name": endpoint['name'],
                "healthy": False,
                "error": str(e)
            }
