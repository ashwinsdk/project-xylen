import asyncio
import sys
import os
from aiohttp import web
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'mac_coordinator')))

from coordinator import TradingCoordinator


class MockModelServer:
    def __init__(self, port):
        self.port = port
        self.app = web.Application()
        self.app.router.add_post('/predict', self.predict)
        self.app.router.add_post('/retrain', self.retrain)
        self.app.router.add_get('/health', self.health)
        self.runner = None
    
    async def predict(self, request):
        data = await request.json()
        
        response = {
            'action': 'long',
            'confidence': 0.75,
            'stop': 49500.0,
            'take_profit': 51000.0,
            'raw_score': 0.65
        }
        
        return web.json_response(response)
    
    async def retrain(self, request):
        return web.json_response({'status': 'success', 'message': 'Training sample recorded'})
    
    async def health(self, request):
        return web.json_response({
            'status': 'healthy',
            'uptime_seconds': 100,
            'memory_usage_mb': 512,
            'model_loaded': True,
            'model_type': 'mock'
        })
    
    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '127.0.0.1', self.port)
        await site.start()
        print(f"Mock model server started on port {self.port}")
    
    async def stop(self):
        if self.runner:
            await self.runner.cleanup()


async def run_integration_test():
    print("Starting integration test...")
    
    server1 = MockModelServer(8001)
    server2 = MockModelServer(8002)
    
    await server1.start()
    await server2.start()
    
    await asyncio.sleep(1)
    
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml.example')
    
    test_config = os.path.join(os.path.dirname(__file__), 'test_config.yaml')
    
    with open(config_path, 'r') as f:
        config_content = f.read()
    
    config_content = config_content.replace('192.168.1.100', '127.0.0.1')
    config_content = config_content.replace('port: 8000', 'port: 8001', 1)
    config_content = config_content.replace('192.168.1.101', '127.0.0.1')
    config_content = config_content.replace('port: 8000', 'port: 8002', 1)
    config_content = config_content.replace('dry_run: true', 'dry_run: true')
    config_content = config_content.replace('testnet: true', 'testnet: true')
    config_content = config_content.replace('heartbeat_interval: 60', 'heartbeat_interval: 5')
    
    with open(test_config, 'w') as f:
        f.write(config_content)
    
    print("Test configuration created")
    
    coordinator = TradingCoordinator(test_config)
    
    async def run_for_limited_time():
        await coordinator.start()
    
    async def stop_after_delay():
        await asyncio.sleep(15)
        coordinator.is_running = False
    
    try:
        print("Starting coordinator for 15 seconds...")
        
        await asyncio.gather(
            run_for_limited_time(),
            stop_after_delay()
        )
        
        print("Coordinator stopped")
        
        stats = await coordinator.data_logger.get_performance_stats()
        print(f"Performance stats: {stats}")
        
        print("Integration test completed successfully")
        
    except Exception as e:
        print(f"Integration test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await server1.stop()
        await server2.stop()
        
        if os.path.exists(test_config):
            os.remove(test_config)
        
        print("Cleanup completed")


if __name__ == "__main__":
    print("TradeProject Integration Test")
    print("=" * 50)
    
    asyncio.run(run_integration_test())
    
    print("=" * 50)
    print("Test completed")
