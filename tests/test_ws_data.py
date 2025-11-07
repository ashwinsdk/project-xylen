#!/usr/bin/env python3
"""Quick test to see WebSocket data structure"""
import asyncio
import websockets
import json

async def test_ws():
    try:
        async with websockets.connect('ws://localhost:8765') as websocket:
            message = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(message)
            print("\n=== WebSocket Message Structure ===\n")
            print(json.dumps(data, indent=2))
            
            if 'models' in data and data['models']:
                print("\n=== First Model Details ===\n")
                print(json.dumps(data['models'][0], indent=2))
                
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test_ws())
