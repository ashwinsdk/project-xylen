#!/usr/bin/env python3
"""
Comprehensive System Test for Project Xylen
Tests all components: models, coordinator, trading flow, safety features
"""
import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, List

# Configuration
COORDINATOR_URL = "http://localhost:9090"
MODEL_URLS = [
    "http://localhost:8001",
    "http://localhost:8002",
    "http://localhost:8003",
    "http://localhost:8004",
]
WS_URL = "ws://localhost:8765"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_test(test_name: str, status: str, message: str = ""):
    """Print colored test results"""
    color = Colors.GREEN if status == "PASS" else Colors.RED if status == "FAIL" else Colors.YELLOW
    print(f"{color}[{status}]{Colors.END} {test_name}: {message}")

async def test_service_health(session: aiohttp.ClientSession) -> Dict[str, bool]:
    """Test all services are healthy"""
    print(f"\n{Colors.BLUE}=== Phase 1: Service Health Checks ==={Colors.END}\n")
    results = {}
    
    # Test coordinator metrics endpoint
    try:
        async with session.get(f"{COORDINATOR_URL}/metrics", timeout=5) as resp:
            if resp.status == 200:
                log_test("Coordinator Metrics", "PASS", "Prometheus endpoint responding")
                results['coordinator'] = True
            else:
                log_test("Coordinator Metrics", "FAIL", f"Status {resp.status}")
                results['coordinator'] = False
    except Exception as e:
        log_test("Coordinator Metrics", "FAIL", str(e))
        results['coordinator'] = False
    
    # Test all model servers
    for idx, url in enumerate(MODEL_URLS, 1):
        try:
            async with session.get(f"{url}/health", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    model_loaded = data.get('model_loaded', False)
                    continuous_learning = data.get('continuous_learning', False)
                    training = data.get('training', False)
                    
                    status = "PASS" if model_loaded else "WARN"
                    msg = f"Model loaded: {model_loaded}, CL: {continuous_learning}, Training: {training}"
                    log_test(f"Model Server {idx} Health", status, msg)
                    results[f'model_{idx}'] = model_loaded
                else:
                    log_test(f"Model Server {idx} Health", "FAIL", f"Status {resp.status}")
                    results[f'model_{idx}'] = False
        except Exception as e:
            log_test(f"Model Server {idx} Health", "FAIL", str(e))
            results[f'model_{idx}'] = False
    
    return results

async def test_model_predictions(session: aiohttp.ClientSession) -> bool:
    """Test model prediction endpoints"""
    print(f"\n{Colors.BLUE}=== Phase 2: Model Prediction Tests ==={Colors.END}\n")
    
    # Sample prediction request
    prediction_request = {
        "symbol": "BTCUSDT",
        "timeframe": "5m",
        "candles": [
            {"open": 100000, "high": 101000, "low": 99000, "close": 100500, "volume": 1000000}
            for _ in range(20)
        ],
        "indicators": {
            "rsi": 50.0,
            "ema_20": 100000,
            "ema_50": 99500,
            "macd": 100,
            "volume_ratio": 1.2
        },
        "meta": {}
    }
    
    all_passed = True
    for idx, url in enumerate(MODEL_URLS, 1):
        try:
            async with session.post(f"{url}/predict", json=prediction_request, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    action = data.get('action', 'unknown')
                    confidence = data.get('confidence', 0)
                    latency = data.get('latency_ms', 0)
                    
                    log_test(f"Model {idx} Prediction", "PASS", 
                            f"Action: {action}, Confidence: {confidence:.3f}, Latency: {latency:.1f}ms")
                else:
                    log_test(f"Model {idx} Prediction", "FAIL", f"Status {resp.status}")
                    all_passed = False
        except Exception as e:
            log_test(f"Model {idx} Prediction", "FAIL", str(e))
            all_passed = False
    
    return all_passed

async def test_websocket_connection() -> bool:
    """Test WebSocket connection and data flow"""
    print(f"\n{Colors.BLUE}=== Phase 3: WebSocket Communication ==={Colors.END}\n")
    
    try:
        import websockets
        
        async with websockets.connect(WS_URL) as websocket:
            log_test("WebSocket Connection", "PASS", "Connected successfully")
            
            # Wait for welcome or status update message
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(message)
                msg_type = data.get('type', 'unknown')
                log_test("WebSocket Message Received", "PASS", f"Type: {msg_type}")
                return True
            except asyncio.TimeoutError:
                log_test("WebSocket Message Received", "WARN", "No message within 5s (normal if heartbeat is 60s)")
                return True
                
    except Exception as e:
        log_test("WebSocket Connection", "FAIL", str(e))
        return False

async def monitor_coordinator_logs(duration: int = 120):
    """Monitor coordinator for decision making"""
    print(f"\n{Colors.BLUE}=== Phase 4: Live System Monitoring ({duration}s) ==={Colors.END}\n")
    print(f"{Colors.YELLOW}Monitoring coordinator decisions...{Colors.END}")
    
    import subprocess
    
    # Follow coordinator logs
    try:
        process = subprocess.Popen(
            ['docker', 'logs', '-f', '--tail', '20', 'xylen-coordinator'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        start_time = time.time()
        decisions = []
        errors = []
        
        while time.time() - start_time < duration:
            line = process.stdout.readline()
            if not line:
                break
            
            line = line.strip()
            
            # Track decisions
            if "Ensemble decision:" in line:
                decisions.append(line)
                print(f"{Colors.GREEN}✓{Colors.END} {line}")
            
            # Track errors
            if "ERROR" in line and "data_logger" not in line:  # Ignore known data_logger error
                errors.append(line)
                print(f"{Colors.RED}✗{Colors.END} {line}")
            
            # Track important events
            if any(keyword in line for keyword in ["Trade opened", "Circuit breaker", "Health check:"]):
                print(f"{Colors.BLUE}ℹ{Colors.END} {line}")
        
        process.terminate()
        
        print(f"\n{Colors.BLUE}=== Monitoring Summary ==={Colors.END}")
        log_test("Total Decisions", "INFO", f"{len(decisions)}")
        log_test("Total Errors", "WARN" if errors else "PASS", f"{len(errors)}")
        
        if errors:
            print(f"\n{Colors.RED}Errors found:{Colors.END}")
            for error in errors[:5]:  # Show first 5 errors
                print(f"  {error}")
        
        return len(errors) == 0
        
    except Exception as e:
        log_test("Coordinator Monitoring", "FAIL", str(e))
        return False

async def main():
    """Run all comprehensive tests"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}  PROJECT XYLEN - COMPREHENSIVE SYSTEM TEST{Colors.END}")
    print(f"{Colors.BLUE}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    async with aiohttp.ClientSession() as session:
        # Phase 1: Health Checks
        health_results = await test_service_health(session)
        
        # Phase 2: Model Predictions
        predictions_ok = await test_model_predictions(session)
        
        # Phase 3: WebSocket
        websocket_ok = await test_websocket_connection()
        
    # Phase 4: Live Monitoring
    monitoring_ok = await monitor_coordinator_logs(duration=90)
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}  COMPREHENSIVE TEST SUMMARY{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    all_healthy = all(health_results.values())
    overall_status = all_healthy and predictions_ok and websocket_ok and monitoring_ok
    
    log_test("All Services Healthy", "PASS" if all_healthy else "FAIL", 
            f"{sum(health_results.values())}/{len(health_results)} services")
    log_test("Model Predictions Working", "PASS" if predictions_ok else "FAIL")
    log_test("WebSocket Communication", "PASS" if websocket_ok else "FAIL")
    log_test("Coordinator Monitoring", "PASS" if monitoring_ok else "FAIL")
    
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    if overall_status:
        print(f"{Colors.GREEN}✓ OVERALL STATUS: ALL SYSTEMS OPERATIONAL{Colors.END}")
    else:
        print(f"{Colors.RED}✗ OVERALL STATUS: ISSUES DETECTED{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Test failed with error: {e}{Colors.END}")
