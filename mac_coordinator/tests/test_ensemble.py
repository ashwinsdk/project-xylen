import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ensemble import EnsembleAggregator


@pytest.fixture
def config():
    return {
        'model_endpoints': [
            {'host': '192.168.1.100', 'port': 8000, 'name': 'model1', 'weight': 1.0, 'enabled': True},
            {'host': '192.168.1.101', 'port': 8000, 'name': 'model2', 'weight': 1.0, 'enabled': True}
        ],
        'ensemble': {
            'method': 'weighted_vote',
            'threshold': 0.7,
            'weight_decay': 0.95,
            'min_responding_models': 1
        },
        'timing': {
            'model_timeout': 5
        },
        'trading': {
            'symbol': 'BTCUSDT'
        }
    }


@pytest.fixture
def ensemble(config):
    return EnsembleAggregator(config)


def test_weighted_vote_long(ensemble):
    predictions = [
        {'model_name': 'model1', 'model_key': '192.168.1.100:8000', 'action': 'long', 'confidence': 0.8},
        {'model_name': 'model2', 'model_key': '192.168.1.101:8000', 'action': 'long', 'confidence': 0.75}
    ]
    
    result = ensemble.aggregate(predictions)
    
    assert result['action'] == 'long'
    assert result['confidence'] > 0.7
    assert len(result['participating_models']) == 2


def test_weighted_vote_mixed(ensemble):
    predictions = [
        {'model_name': 'model1', 'model_key': '192.168.1.100:8000', 'action': 'long', 'confidence': 0.6},
        {'model_name': 'model2', 'model_key': '192.168.1.101:8000', 'action': 'short', 'confidence': 0.8}
    ]
    
    result = ensemble.aggregate(predictions)
    
    assert result['action'] in ['long', 'short', 'hold']
    assert 'confidence' in result


def test_empty_predictions(ensemble):
    predictions = []
    
    result = ensemble.aggregate(predictions)
    
    assert result['action'] == 'hold'
    assert result['confidence'] == 0.0


def test_average_confidence_method(ensemble, config):
    config['ensemble']['method'] = 'average_confidence'
    ensemble = EnsembleAggregator(config)
    
    predictions = [
        {'model_name': 'model1', 'model_key': '192.168.1.100:8000', 'action': 'long', 'confidence': 0.8},
        {'model_name': 'model2', 'model_key': '192.168.1.101:8000', 'action': 'long', 'confidence': 0.6}
    ]
    
    result = ensemble.aggregate(predictions)
    
    assert result['action'] == 'long'
    assert result['confidence'] == 0.7


def test_majority_vote_method(ensemble, config):
    config['ensemble']['method'] = 'majority'
    ensemble = EnsembleAggregator(config)
    
    predictions = [
        {'model_name': 'model1', 'model_key': '192.168.1.100:8000', 'action': 'long', 'confidence': 0.5},
        {'model_name': 'model2', 'model_key': '192.168.1.101:8000', 'action': 'long', 'confidence': 0.5},
        {'model_name': 'model3', 'model_key': '192.168.1.102:8000', 'action': 'short', 'confidence': 0.9}
    ]
    
    result = ensemble.aggregate(predictions)
    
    assert result['action'] == 'long'
