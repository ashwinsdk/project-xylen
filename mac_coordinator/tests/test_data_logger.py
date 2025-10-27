import pytest
import sys
import os
import tempfile
import shutil
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_logger import DataLogger


@pytest.fixture
async def temp_data_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def config(temp_data_dir):
    return {
        'trading': {
            'symbol': 'BTCUSDT'
        },
        'database': {
            'sqlite_path': os.path.join(temp_data_dir, 'trades.db'),
            'csv_path': os.path.join(temp_data_dir, 'trades.csv')
        },
        'logging': {
            'level': 'INFO',
            'file': os.path.join(temp_data_dir, 'test.log')
        }
    }


@pytest.mark.asyncio
async def test_data_logger_initialize(config):
    logger = DataLogger(config)
    await logger.initialize()
    
    assert os.path.exists(config['database']['sqlite_path'])
    assert os.path.exists(config['database']['csv_path'])
    
    await logger.close()


@pytest.mark.asyncio
async def test_log_trade(config):
    logger = DataLogger(config)
    await logger.initialize()
    
    position = {
        'side': 'long',
        'entry_price': 50000.0,
        'quantity': 0.1,
        'entry_time': datetime.utcnow(),
        'order': {'orderId': 12345},
        'decision': {'action': 'long', 'confidence': 0.75}
    }
    
    await logger.log_trade(position)
    
    trades = await logger.get_recent_trades(limit=10)
    assert len(trades) > 0
    assert trades[0]['side'] == 'long'
    
    await logger.close()


@pytest.mark.asyncio
async def test_performance_stats(config):
    logger = DataLogger(config)
    await logger.initialize()
    
    stats = await logger.get_performance_stats()
    
    assert 'total_trades' in stats
    assert 'win_rate' in stats
    assert 'total_pnl' in stats
    
    await logger.close()


@pytest.mark.asyncio
async def test_log_analysis(config):
    logger = DataLogger(config)
    await logger.initialize()
    
    snapshot = {
        'symbol': 'BTCUSDT',
        'timestamp': datetime.utcnow().isoformat(),
        'current_price': 50000.0
    }
    
    model_responses = [
        {'model_name': 'model1', 'action': 'long', 'confidence': 0.8}
    ]
    
    decision = {
        'action': 'long',
        'confidence': 0.8
    }
    
    await logger.log_analysis(snapshot, model_responses, decision)
    
    await logger.close()
