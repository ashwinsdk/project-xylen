from aiohttp import web
import json
import logging
from datetime import datetime


logger = logging.getLogger(__name__)


class DashboardAPIServer:
    def __init__(self, coordinator, port=5500, host='0.0.0.0'):
        self.coordinator = coordinator
        self.port = port
        self.host = host
        self.app = web.Application()
        self.runner = None
        
        self._setup_routes()
    
    def _setup_routes(self):
        self.app.router.add_get('/api/models', self.get_models)
        self.app.router.add_get('/api/trades', self.get_trades)
        self.app.router.add_get('/api/performance', self.get_performance)
        self.app.router.add_get('/api/logs', self.get_logs)
        self.app.router.add_get('/api/status', self.get_status)
        
        self.app.router.add_options('/api/{path:.*}', self.handle_options)
        
        self.app.middlewares.append(self.cors_middleware)
    
    @web.middleware
    async def cors_middleware(self, request, handler):
        if request.method == 'OPTIONS':
            response = web.Response()
        else:
            try:
                response = await handler(request)
            except Exception as e:
                logger.error(f"Handler error: {e}")
                response = web.json_response({'error': str(e)}, status=500)
        
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        
        return response
    
    async def handle_options(self, request):
        return web.Response()
    
    async def get_models(self, request):
        try:
            models_data = []
            
            for endpoint in self.coordinator.ensemble.model_endpoints:
                if not endpoint.get('enabled', True):
                    continue
                
                key = f"{endpoint['host']}:{endpoint['port']}"
                perf = self.coordinator.ensemble.model_performance.get(key, {})
                
                success_count = perf.get('success_count', 0)
                failure_count = perf.get('failure_count', 0)
                total_requests = success_count + failure_count
                success_rate = success_count / total_requests if total_requests > 0 else 0
                
                model_data = {
                    'name': endpoint['name'],
                    'host': endpoint['host'],
                    'port': endpoint['port'],
                    'healthy': success_count > 0 or failure_count == 0,
                    'uptime': 0,
                    'memory_mb': 0,
                    'success_rate': success_rate,
                    'avg_response_time': perf.get('avg_response_time', 0),
                    'success_count': success_count,
                    'failure_count': failure_count,
                    'last_success': perf.get('last_success').isoformat() if perf.get('last_success') else None
                }
                
                models_data.append(model_data)
            
            return web.json_response(models_data)
        
        except Exception as e:
            logger.error(f"Error getting models data: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_trades(self, request):
        try:
            limit = int(request.query.get('limit', 50))
            
            trades = await self.coordinator.data_logger.get_recent_trades(limit=limit)
            
            return web.json_response(trades)
        
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_performance(self, request):
        try:
            stats = await self.coordinator.data_logger.get_performance_stats()
            
            return web.json_response(stats)
        
        except Exception as e:
            logger.error(f"Error getting performance: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_logs(self, request):
        try:
            limit = int(request.query.get('limit', 100))
            
            import os
            logs = []
            
            log_file = self.coordinator.config.get('logging', {}).get('file', './logs/coordinator.log')
            
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    
                    for line in lines[-limit:]:
                        parts = line.strip().split(' - ')
                        if len(parts) >= 3:
                            timestamp = parts[0]
                            level = parts[2] if len(parts) > 2 else 'INFO'
                            message = ' - '.join(parts[3:]) if len(parts) > 3 else line.strip()
                            
                            logs.append({
                                'timestamp': timestamp,
                                'level': level,
                                'message': message
                            })
            
            return web.json_response(logs)
        
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_status(self, request):
        try:
            # Convert daily_stats datetime to ISO format
            daily_stats = self.coordinator.daily_stats.copy()
            if 'start_time' in daily_stats and isinstance(daily_stats['start_time'], datetime):
                daily_stats['start_time'] = daily_stats['start_time'].isoformat()
            
            status = {
                'is_running': self.coordinator.is_running,
                'dry_run': self.coordinator.config.get('dry_run', True),
                'testnet': self.coordinator.config.get('testnet', True),
                'current_position': self.coordinator.current_position is not None,
                'daily_stats': daily_stats,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return web.json_response(status)
        
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()
        
        logger.info(f"Dashboard API server started at http://{self.host}:{self.port}")
    
    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
            logger.info("Dashboard API server stopped")
