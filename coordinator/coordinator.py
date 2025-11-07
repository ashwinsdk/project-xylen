import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yaml
import signal
import time
import psutil

from binance_client import BinanceClient, OrderSide, OrderType
from ensemble import EnsembleAggregator
from risk_manager import RiskManager
from data_logger import DataLogger
from market_data import MarketDataCollector

try:
    from telegram_alerts import initialize_alerter, get_alerter, close_alerter
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.warning("telegram_alerts not available")

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("prometheus_client not installed, metrics disabled")

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logging.warning("websockets not installed, WebSocket server disabled")


class TradingCoordinator:
    """
    Production-grade trading coordinator with async heartbeat
    
    Features:
    - Async 60-second heartbeat loop
    - Ensemble aggregation with Bayesian fusion
    - Risk management with Kelly criterion
    - Circuit breaker and position limits
    - Prometheus metrics export
    - WebSocket server for dashboard
    - Graceful shutdown with cleanup
    - Complete data logging with schema v2
    """
    
    def __init__(self, config_path: str = "config.yaml", config_dict: Optional[Dict] = None):
        """
        Initialize coordinator with either config file path or config dict
        
        Args:
            config_path: Path to YAML config file (default: "config.yaml")
            config_dict: Config dictionary (overrides config_path if provided)
        """
        if config_dict is not None:
            self.config = config_dict
        else:
            self.config = self._load_config(config_path)
        
        self._setup_logging()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Trading Coordinator")
        
        # Core components
        self.binance_client = BinanceClient(self.config)
        self.ensemble = EnsembleAggregator(self.config)
        self.risk_manager = RiskManager(self.config)
        self.data_logger = DataLogger(self.config)
        self.market_data = MarketDataCollector(self.config)
        
        # State management
        self.is_running = False
        self.current_position = None
        self.open_trades = {}  # trade_id -> trade_info
        self.circuit_breaker_alerted = False  # Track if we've alerted about circuit breaker
        
        # Metrics
        self._init_metrics()
        
        # WebSocket clients
        self.ws_clients = set()
        
        self.logger.info("Trading Coordinator initialized")
    
    def _init_metrics(self):
        """Initialize Prometheus metrics"""
        if not PROMETHEUS_AVAILABLE:
            self.metrics = None
            return
        
        self.metrics = {
            'snapshots_collected': Counter('xylen_snapshots_total', 'Total market snapshots collected'),
            'model_predictions': Counter('xylen_predictions_total', 'Total model predictions', ['model', 'action']),
            'ensemble_decisions': Counter('xylen_decisions_total', 'Total ensemble decisions', ['action', 'result']),
            'orders_placed': Counter('xylen_orders_total', 'Total orders placed', ['side', 'status']),
            'trades_pnl': Histogram('xylen_trade_pnl', 'Trade PNL distribution', buckets=[-1000, -500, -100, 0, 100, 500, 1000, 5000]),
            'decision_latency': Histogram('xylen_decision_latency_seconds', 'Decision cycle latency'),
            'account_equity': Gauge('xylen_account_equity', 'Current account equity'),
            'position_size': Gauge('xylen_position_size', 'Current position size'),
            'risk_exposure': Gauge('xylen_risk_exposure', 'Current risk exposure'),
            'circuit_breaker_active': Gauge('xylen_circuit_breaker', 'Circuit breaker status'),
        }
        
        # Start Prometheus HTTP server
        metrics_port = self.config.get('monitoring', {}).get('prometheus_port', 9090)
        try:
            start_http_server(metrics_port)
            self.logger.info(f"Prometheus metrics server started on port {metrics_port}")
        except Exception as e:
            self.logger.warning(f"Failed to start Prometheus server: {e}")
        
    def _load_config(self, config_path: str) -> Dict:
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config
    
    def _setup_logging(self):
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        log_file = log_config.get('file', './logs/coordinator.log')
        
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    async def start(self):
        """Start coordinator with all subsystems"""
        self.logger.info("Starting Trading Coordinator")
        self.logger.info(f"Dry Run Mode: {self.config.get('dry_run', True)}")
        self.logger.info(f"Testnet Mode: {self.config.get('testnet', True)}")
        
        # Log system event
        await self.data_logger.log_system_event(
            event_type='STARTUP',
            severity='INFO',
            component='coordinator',
            message='Trading Coordinator starting',
            details={
                'dry_run': self.config.get('dry_run', True),
                'testnet': self.config.get('testnet', True),
                'symbol': self.config.get('trading', {}).get('symbol', 'BTCUSDT')
            }
        )
        
        # Initialize components
        try:
            await self.market_data.initialize()
            await self.data_logger.initialize()
            await self.binance_client.initialize()
            # RiskManager doesn't need async initialization
            
            # Initialize telegram alerts
            if TELEGRAM_AVAILABLE:
                await initialize_alerter(self.config)
            
            self.logger.info("All components initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}", exc_info=True)
            await self.data_logger.log_system_event(
                event_type='INIT_ERROR',
                severity='CRITICAL',
                component='coordinator',
                message=f'Initialization failed: {e}'
            )
            return
        
        self.is_running = True
        self.start_time = time.time()  # Track uptime
        
        # Start async tasks
        tasks = [
            asyncio.create_task(self._main_loop(), name="main_loop"),
            asyncio.create_task(self._health_check_loop(), name="health_check"),
        ]
        
        # Start WebSocket server if available
        if WEBSOCKETS_AVAILABLE and self.config.get('dashboard', {}).get('websocket_enabled', True):
            tasks.append(asyncio.create_task(self._websocket_server(), name="websocket"))
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            self.logger.info("Coordinator tasks cancelled")
        except Exception as e:
            self.logger.error(f"Error in coordinator: {e}", exc_info=True)
            await self.data_logger.log_system_event(
                event_type='RUNTIME_ERROR',
                severity='ERROR',
                component='coordinator',
                message=f'Runtime error: {e}'
            )
        finally:
            await self.shutdown()
    
    async def _main_loop(self):
        """Main heartbeat loop - executes every 60 seconds"""
        heartbeat_interval = self.config.get('timing', {}).get('heartbeat_interval', 60)
        
        self.logger.info(f"Main loop started with {heartbeat_interval}s heartbeat")
        
        while self.is_running:
            cycle_start = time.time()
            
            try:
                # Check circuit breaker
                if self.risk_manager.circuit_breaker_active():
                    self.logger.warning("Circuit breaker active, skipping trading cycle")
                    if self.metrics:
                        self.metrics['circuit_breaker_active'].set(1)
                    
                    # Send alert on first detection
                    if not self.circuit_breaker_alerted and TELEGRAM_AVAILABLE:
                        try:
                            alerter = get_alerter()
                            if alerter:
                                await alerter.alert_circuit_breaker(
                                    reason='Consecutive losses exceeded threshold',
                                    details={
                                        'consecutive_losses': self.risk_manager.consecutive_losses,
                                        'daily_loss': self.risk_manager.daily_loss,
                                        'circuit_breaker_threshold': self.risk_manager.circuit_breaker_threshold
                                    }
                                )
                                self.circuit_breaker_alerted = True
                        except Exception as e:
                            self.logger.warning(f"Failed to send circuit breaker alert: {e}")
                    
                    await asyncio.sleep(heartbeat_interval)
                    continue
                
                # Reset alert flag when circuit breaker clears
                if self.circuit_breaker_alerted:
                    self.circuit_breaker_alerted = False
                
                if self.metrics:
                    self.metrics['circuit_breaker_active'].set(0)
                
                # Execute decision cycle
                await self._decision_cycle()
                
                # Record cycle latency
                cycle_duration = time.time() - cycle_start
                if self.metrics:
                    self.metrics['decision_latency'].observe(cycle_duration)
                
                self.logger.debug(f"Decision cycle completed in {cycle_duration:.2f}s")
                
                # Wait for next heartbeat
                await asyncio.sleep(heartbeat_interval)
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}", exc_info=True)
                await self.data_logger.log_system_event(
                    event_type='MAIN_LOOP_ERROR',
                    severity='ERROR',
                    component='main_loop',
                    message=f'Main loop error: {e}'
                )
                await asyncio.sleep(heartbeat_interval)
    
    async def _decision_cycle(self):
        """
        Complete decision cycle:
        1. Collect market snapshot
        2. Query model servers
        3. Aggregate ensemble decision
        4. Validate with risk manager
        5. Execute trade if approved
        6. Log all data
        """
        try:
            # Step 1: Collect market snapshot
            snapshot = await self.market_data.get_snapshot()
            
            if self.metrics:
                self.metrics['snapshots_collected'].inc()
            
            # Log snapshot to database
            snapshot_id = await self.data_logger.log_snapshot(snapshot)
            
            self.logger.info(f"Snapshot collected: price={snapshot.get('current_price'):.2f}, "
                           f"RSI={snapshot.get('indicators', {}).get('rsi', 0):.1f}")
            
            # Step 2: Query model servers
            model_responses = await self.ensemble.get_model_predictions(snapshot)
            
            if not model_responses:
                self.logger.warning("No model responses received")
                return
            
            # Log individual predictions
            for response in model_responses:
                model_name = response.get('model_name', 'unknown')
                action = response.get('action', 'hold')
                confidence = response.get('confidence', 0)
                
                await self.data_logger.log_model_prediction(
                    model_name=model_name,
                    snapshot_id=snapshot_id,
                    action=action,
                    confidence=confidence,
                    probability=response.get('probability'),
                    expected_return=response.get('expected_return'),
                    latency_ms=response.get('latency_ms'),
                    raw_response=response
                )
                
                if self.metrics:
                    self.metrics['model_predictions'].labels(
                        model=model_name,
                        action=action
                    ).inc()
            
            # Step 3: Aggregate ensemble decision
            decision = self.ensemble.aggregate(model_responses)
            
            self.logger.info(f"Ensemble decision: {decision['action']} "
                           f"(confidence={decision['confidence']:.3f}, "
                           f"expected_value={decision.get('expected_value', 0):.4f})")
            
            # Step 4: Validate with risk manager
            # Build risk metrics from current state
            from risk_manager import RiskMetrics
            risk_metrics = RiskMetrics(
                total_equity=10000.0,  # TODO: Get from binance account
                available_margin=10000.0,  # TODO: Get from binance account
                total_exposure=0.0,  # TODO: Calculate from open positions
                open_positions=len(self.open_trades),
                daily_pnl=0.0,  # TODO: Calculate from today's trades
                daily_trades=0,  # TODO: Count from today's trades
                consecutive_losses=self.risk_manager.consecutive_losses,
                win_rate=0.5  # TODO: Calculate from historical trades
            )
            
            # Calculate position size
            current_price = float(snapshot.get('current_price', 0))
            position_size_obj = self.risk_manager.calculate_position_size(
                current_price=current_price,
                account_balance=risk_metrics.available_margin,
                leverage=self.config.get('trading', {}).get('leverage', 1)
            )
            
            # Validate trade
            is_valid, rejection_reason = self.risk_manager.validate_trade(
                risk_metrics, 
                position_size_obj.size_usd
            )
            
            # Build risk_check dict for compatibility
            risk_check = {
                'approved': is_valid,
                'reason': rejection_reason,
                'position_size': position_size_obj.size_usd if is_valid else 0
            }
            
            # Log ensemble decision
            await self.data_logger.log_ensemble_decision(
                snapshot_id=snapshot_id,
                final_action=decision['action'],
                final_confidence=decision['confidence'],
                expected_value=decision.get('expected_value', 0),
                aggregation_method=decision.get('method', 'bayesian'),
                model_count=len(model_responses),
                model_agreement=decision.get('agreement', 0),
                uncertainty=decision.get('uncertainty', 0),
                risk_check_passed=risk_check['approved'],
                position_size=risk_check.get('position_size'),
                rejected=not risk_check['approved'],
                rejection_reason=risk_check.get('reason')
            )
            
            if self.metrics:
                self.metrics['ensemble_decisions'].labels(
                    action=decision['action'],
                    result='approved' if risk_check['approved'] else 'rejected'
                ).inc()
            
            # Step 5: Execute trade if approved
            if risk_check['approved'] and decision['action'] in ['long', 'short']:
                await self._execute_trade(decision, risk_check, snapshot, snapshot_id)
            else:
                if not risk_check['approved']:
                    self.logger.info(f"Trade rejected by risk manager: {risk_check.get('reason')}")
                else:
                    self.logger.debug(f"No trade signal (action={decision['action']})")
            
            # Broadcast comprehensive update to WebSocket clients
            await self._broadcast_status_update(snapshot, decision, risk_check)
            
        except Exception as e:
            self.logger.error(f"Error in decision cycle: {e}", exc_info=True)
            await self.data_logger.log_system_event(
                event_type='DECISION_ERROR',
                severity='ERROR',
                component='decision_cycle',
                message=f'Decision cycle error: {e}'
            )
    
    async def _execute_trade(
        self,
        decision: Dict,
        risk_check: Dict,
        snapshot: Dict,
        snapshot_id: int
    ):
        """Execute approved trade with position management"""
        try:
            # Check if already have open position
            max_positions = self.config.get('trading', {}).get('max_open_positions', 1)
            if len(self.open_trades) >= max_positions:
                self.logger.info(f"Already have {len(self.open_trades)} open positions (max={max_positions})")
                return
            
            # Get position size from risk manager
            position_size = risk_check.get('position_size', 0)
            if position_size <= 0:
                self.logger.warning("Invalid position size from risk manager")
                return
            
            # Calculate quantity
            current_price = float(snapshot.get('current_price', 0))
            if current_price <= 0:
                self.logger.error("Invalid current price")
                return
            
            quantity = position_size / current_price
            
            # Determine order side
            side = OrderSide.BUY if decision['action'] == 'long' else OrderSide.SELL
            
            # Calculate stop loss and take profit
            stop_loss = decision.get('stop_loss')
            take_profit = decision.get('take_profit')
            
            # Place order
            self.logger.info(f"Placing {side.value} order: qty={quantity:.6f}, "
                           f"SL={stop_loss}, TP={take_profit}")
            
            order_state = await self.binance_client.place_order(
                side=side,
                quantity=quantity,
                order_type=OrderType.MARKET,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            if not order_state:
                self.logger.error("Order placement failed")
                if self.metrics:
                    self.metrics['orders_placed'].labels(
                        side=side.value,
                        status='failed'
                    ).inc()
                return
            
            # Log order
            await self.data_logger.log_order(
                order_id=order_state.order_id,
                trade_id=None,  # Will be updated after trade creation
                symbol=order_state.symbol,
                side=order_state.side.value,
                order_type=order_state.type.value,
                quantity=order_state.quantity,
                price=order_state.price,
                status=order_state.status.value,
                order_type_label='ENTRY'
            )
            
            # Create trade record
            trade_id = await self.data_logger.log_trade_open(
                symbol=self.config.get('trading', {}).get('symbol', 'BTCUSDT'),
                side=decision['action'],
                entry_price=order_state.avg_price if order_state.avg_price > 0 else current_price,
                quantity=quantity,
                entry_order_id=order_state.order_id,
                snapshot_id=snapshot_id,
                decision_confidence=decision['confidence'],
                decision_expected_value=decision.get('expected_value', 0),
                risk_exposure=position_size
            )
            
            # Track open trade
            self.open_trades[trade_id] = {
                'trade_id': trade_id,
                'order_state': order_state,
                'decision': decision,
                'snapshot_id': snapshot_id,
                'entry_time': datetime.utcnow(),
                'entry_price': order_state.avg_price if order_state.avg_price > 0 else current_price,
                'quantity': quantity,
                'side': decision['action']
            }
            
            # Update metrics
            if self.metrics:
                self.metrics['orders_placed'].labels(
                    side=side.value,
                    status='success'
                ).inc()
                self.metrics['position_size'].set(position_size)
                self.metrics['risk_exposure'].set(risk_check.get('total_exposure', 0))
            
            # Update risk manager state
            self.risk_manager.record_trade_entry(
                symbol=self.config.get('trading', {}).get('symbol', 'BTCUSDT'),
                side=decision['action'],
                quantity=quantity,
                entry_price=order_state.avg_price if order_state.avg_price > 0 else current_price
            )
            
            self.logger.info(f"Trade executed successfully: trade_id={trade_id}, "
                           f"order_id={order_state.order_id}")
            
            # Send Telegram alert for trade opened
            if TELEGRAM_AVAILABLE:
                try:
                    alerter = get_alerter()
                    if alerter:
                        await alerter.alert_trade_opened({
                            'trade_id': trade_id,
                            'symbol': self.config.get('trading', {}).get('symbol', 'BTCUSDT'),
                            'side': decision['action'],
                            'quantity': quantity,
                            'entry_price': order_state.avg_price if order_state.avg_price > 0 else current_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'confidence': decision['confidence'],
                            'expected_value': decision.get('expected_value', 0)
                        })
                except Exception as e:
                    self.logger.warning(f"Failed to send trade opened alert: {e}")
            
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}", exc_info=True)
            await self.data_logger.log_system_event(
                event_type='TRADE_ERROR',
                severity='ERROR',
                component='execute_trade',
                message=f'Trade execution error: {e}'
            )
            
            # Send Telegram alert for error
            if TELEGRAM_AVAILABLE:
                try:
                    alerter = get_alerter()
                    if alerter:
                        await alerter.alert_error(
                            error_type='TRADE_EXECUTION',
                            message=f'Trade execution failed: {str(e)}',
                            details={'exception': str(e)}
                        )
                except Exception as alert_err:
                    self.logger.warning(f"Failed to send error alert: {alert_err}")
    
    async def _health_check_loop(self):
        """Periodic health checks for model servers and system"""
        health_check_interval = self.config.get('timing', {}).get('health_check_interval', 300)
        
        self.logger.info(f"Health check loop started with {health_check_interval}s interval")
        
        while self.is_running:
            try:
                # Check model server health
                health_status_list = await self.ensemble.check_model_health()
                
                # Convert list to dict for easier processing
                health_status = {}
                for health_item in health_status_list:
                    if isinstance(health_item, dict):
                        model_name = health_item.get('model_name', 'unknown')
                        health_status[model_name] = health_item
                
                # Log health check (convert datetime objects to strings)
                health_log = {}
                for model, status in health_status.items():
                    health_log[model] = {
                        'healthy': status.get('healthy', False),
                        'error': status.get('error', None)
                    }
                
                await self.data_logger.log_system_event(
                    event_type='HEALTH_CHECK',
                    severity='INFO',
                    component='health_check',
                    message='Health check completed',
                    details=health_log
                )
                
                # Check for unhealthy models
                unhealthy_models = [
                    model for model, status in health_status.items()
                    if not status.get('healthy', False)
                ]
                
                if unhealthy_models:
                    self.logger.warning(f"Unhealthy models detected: {unhealthy_models}")
                    await self.data_logger.log_system_event(
                        event_type='MODEL_UNHEALTHY',
                        severity='WARNING',
                        component='health_check',
                        message=f'Unhealthy models: {unhealthy_models}',
                        details=health_log
                    )
                
                # Update account equity metric
                if self.metrics:
                    try:
                        balance = await self.binance_client.get_account_balance()
                        self.metrics['account_equity'].set(balance.get('total_equity', 0))
                    except Exception as e:
                        self.logger.debug(f"Failed to update equity metric: {e}")
                
                # Broadcast comprehensive status update to dashboard
                await self._broadcast_status_update()
                
                await asyncio.sleep(health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}", exc_info=True)
                await asyncio.sleep(health_check_interval)
    
    async def _websocket_server(self):
        """WebSocket server for real-time dashboard updates"""
        if not WEBSOCKETS_AVAILABLE:
            return
        
        ws_config = self.config.get('dashboard', {})
        host = ws_config.get('websocket_host', '0.0.0.0')
        port = ws_config.get('websocket_port', 8765)
        
        async def handle_client(websocket, path):
            """Handle individual WebSocket client"""
            self.ws_clients.add(websocket)
            self.logger.info(f"WebSocket client connected: {websocket.remote_address}")
            
            try:
                # Send initial welcome message
                await websocket.send(json.dumps({
                    'type': 'welcome',
                    'timestamp': datetime.utcnow().isoformat(),
                    'message': 'Connected to Xylen Trading Coordinator'
                }))
                
                # Send initial comprehensive status
                await self._broadcast_status_update()
                
                # Keep connection alive
                async for message in websocket:
                    # Handle client messages (e.g., subscribe to specific updates)
                    try:
                        data = json.loads(message)
                        self.logger.debug(f"WebSocket message received: {data}")
                    except json.JSONDecodeError:
                        self.logger.warning(f"Invalid JSON from client: {message}")
                        
            except websockets.exceptions.ConnectionClosed:
                self.logger.info(f"WebSocket client disconnected: {websocket.remote_address}")
            finally:
                self.ws_clients.discard(websocket)
        
        try:
            import json
            server = await websockets.serve(handle_client, host, port)
            self.logger.info(f"WebSocket server started on ws://{host}:{port}")
            
            await asyncio.Future()  # Run forever
            
        except Exception as e:
            self.logger.error(f"WebSocket server error: {e}", exc_info=True)
    
    async def _broadcast_update(self, update: Dict):
        """Broadcast update to all connected WebSocket clients"""
        if not self.ws_clients:
            return
        
        try:
            import json
            message = json.dumps(update)
            
            # Send to all clients (remove disconnected ones)
            disconnected = set()
            for client in self.ws_clients:
                try:
                    await client.send(message)
                except Exception:
                    disconnected.add(client)
            
            # Clean up disconnected clients
            self.ws_clients -= disconnected
            
        except Exception as e:
            self.logger.debug(f"Error broadcasting update: {e}")
    
    async def _broadcast_status_update(self, snapshot=None, decision=None, risk_check=None):
        """Broadcast comprehensive status update including models, coordinator, and system status"""
        try:
            # Get model health status
            model_health = await self.ensemble.check_model_health()
            
            # Build comprehensive status
            status = {
                'type': 'status_update',
                'timestamp': datetime.utcnow().isoformat(),
                
                # Coordinator status
                'coordinator': {
                    'status': 'running' if self.is_running else 'stopped',
                    'dry_run': self.config.get('dry_run', True),
                    'testnet': self.config.get('testnet', True),
                    'symbol': self.config.get('trading', {}).get('symbol', 'BTCUSDT'),
                    'uptime_seconds': int(time.time() - self.start_time) if hasattr(self, 'start_time') else 0,
                    'websocket_clients': len(self.ws_clients),
                    'open_trades': len(self.open_trades),
                    'circuit_breaker': 'active' if self.risk_manager.circuit_breaker_active() else 'normal',
                    'cpu_usage': round(psutil.Process().cpu_percent(interval=0.1), 1),
                    'memory_usage': round(psutil.Process().memory_info().rss / 1024 / 1024, 1)
                },
                
                # Model server status
                'models': self._format_model_health(model_health),
                
                # Market snapshot (if available)
                'market': {
                    'price': snapshot.get('current_price') if snapshot else None,
                    'rsi': snapshot.get('indicators', {}).get('rsi') if snapshot else None,
                    'volume_24h': snapshot.get('volume_24h') if snapshot else None,
                } if snapshot else {},
                
                # Latest decision (if available)
                'decision': {
                    'action': decision.get('action') if decision else 'hold',
                    'confidence': decision.get('confidence') if decision else 0,
                    'risk_approved': risk_check.get('approved') if risk_check else None,
                } if decision else {},
                
                # Performance metrics
                'performance': {
                    'total_pnl': 0,  # TODO: Get from data logger
                    'daily_pnl': 0,
                    'win_rate': 0,
                    'total_trades': 0,
                }
            }
            
            await self._broadcast_update(status)
            
        except Exception as e:
            self.logger.debug(f"Error broadcasting status update: {e}")
    
    def _format_model_health(self, health_status):
        """Format model health status for dashboard"""
        models = []
        
        # Handle both dict and list responses
        if isinstance(health_status, dict):
            for model_name, status in health_status.items():
                # Extract health data from nested 'data' field
                health_data = status.get('data', {})
                perf_data = status.get('performance', {})
                last_pred = perf_data.get('last_prediction', {})
                
                models.append({
                    'name': model_name,
                    'status': 'online' if status.get('healthy', False) else 'offline',
                    'online': status.get('healthy', False),
                    'training': health_data.get('training', False),
                    'continuous_learning': health_data.get('continuous_learning', False),
                    'data_collector_active': health_data.get('data_collector_active', False),
                    'confidence': last_pred.get('confidence', 0),
                    'latency_ms': round(perf_data.get('avg_response_time', 0) * 1000, 1),
                    'last_prediction': last_pred.get('timestamp'),
                    'version': health_data.get('model_version'),
                    'model_type': health_data.get('model_type'),
                    'samples_trained': status.get('samples_trained', 0),
                    'training_samples': health_data.get('training_samples', 0),
                    'uptime_seconds': health_data.get('uptime_seconds', 0),
                    'memory_usage_mb': health_data.get('memory_usage_mb', 0),
                    'cpu_percent': health_data.get('cpu_percent', 0)
                })
        elif isinstance(health_status, list):
            for idx, status in enumerate(health_status, 1):
                # Extract health data from nested 'data' field
                health_data = status.get('data', {})
                perf_data = status.get('performance', {})
                last_pred = perf_data.get('last_prediction', {})
                
                models.append({
                    'name': status.get('model_name', f'Model {idx}'),
                    'status': 'online' if status.get('healthy', False) else 'offline',
                    'online': status.get('healthy', False),
                    'training': health_data.get('training', False),
                    'continuous_learning': health_data.get('continuous_learning', False),
                    'data_collector_active': health_data.get('data_collector_active', False),
                    'confidence': last_pred.get('confidence', 0),
                    'latency_ms': round(perf_data.get('avg_response_time', 0) * 1000, 1),
                    'last_prediction': last_pred.get('timestamp'),
                    'version': health_data.get('model_version'),
                    'model_type': health_data.get('model_type'),
                    'samples_trained': status.get('samples_trained', 0),
                    'training_samples': health_data.get('training_samples', 0),
                    'uptime_seconds': health_data.get('uptime_seconds', 0),
                    'memory_usage_mb': health_data.get('memory_usage_mb', 0),
                    'cpu_percent': health_data.get('cpu_percent', 0)
                })
        
        return models
    
    async def shutdown(self):
        """Graceful shutdown with cleanup"""
        self.logger.info("Shutting down Trading Coordinator")
        self.is_running = False
        
        # Log shutdown event
        await self.data_logger.log_system_event(
            event_type='SHUTDOWN',
            severity='INFO',
            component='coordinator',
            message='Coordinator shutting down gracefully'
        )
        
        # Close open positions if configured
        if self.open_trades:
            self.logger.warning(f"Shutting down with {len(self.open_trades)} open positions")
            
            if self.config.get('safety', {}).get('close_positions_on_shutdown', False):
                self.logger.info("Closing all open positions")
                for trade_id, trade_info in list(self.open_trades.items()):
                    try:
                        # Cancel any open orders
                        order_state = trade_info.get('order_state')
                        if order_state:
                            await self.binance_client.cancel_order(order_state.order_id)
                            self.logger.info(f"Cancelled order {order_state.order_id}")
                    except Exception as e:
                        self.logger.error(f"Failed to cancel order: {e}")
        
        # Close WebSocket connections
        if self.ws_clients:
            self.logger.info(f"Closing {len(self.ws_clients)} WebSocket connections")
            for client in list(self.ws_clients):
                try:
                    await client.close()
                except Exception:
                    pass
            self.ws_clients.clear()
        
        # Close components
        try:
            await self.market_data.close()
            await self.data_logger.close()
            await self.binance_client.close()
            
            # Close telegram alerter
            if TELEGRAM_AVAILABLE:
                try:
                    await close_alerter()
                    self.logger.info("Telegram alerter closed")
                except Exception as e:
                    self.logger.warning(f"Failed to close telegram alerter: {e}")
            
            self.logger.info("All components closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing components: {e}")
        
        self.logger.info("Trading Coordinator shutdown complete")
    
    def get_status(self) -> Dict:
        """Get current coordinator status for API/dashboard"""
        return {
            'is_running': self.is_running,
            'open_trades': len(self.open_trades),
            'circuit_breaker_active': self.risk_manager.circuit_breaker_active() if self.risk_manager else False,
            'websocket_clients': len(self.ws_clients),
            'config': {
                'dry_run': self.config.get('dry_run', True),
                'testnet': self.config.get('testnet', True),
                'symbol': self.config.get('trading', {}).get('symbol', 'BTCUSDT'),
                'heartbeat_interval': self.config.get('timing', {}).get('heartbeat_interval', 60)
            }
        }


def signal_handler(coordinator):
    def handler(signum, frame):
        logging.info(f"Received signal {signum}, shutting down...")
        coordinator.is_running = False
    return handler


async def main():
    config_path = os.getenv('CONFIG_PATH', 'config.yaml')
    
    if not os.path.exists(config_path):
        config_path = '../config.yaml'
    
    coordinator = TradingCoordinator(config_path)
    
    signal.signal(signal.SIGINT, signal_handler(coordinator))
    signal.signal(signal.SIGTERM, signal_handler(coordinator))
    
    await coordinator.start()


if __name__ == "__main__":
    asyncio.run(main())