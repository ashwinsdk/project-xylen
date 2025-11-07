#!/usr/bin/env python3
"""Wait for status update from WebSocket"""
import asyncio
import websockets
import json

async def test_ws():
    try:
        async with websockets.connect('ws://localhost:8765') as websocket:
            print("Connected, waiting for status_update message...")
            
            for i in range(10):  # Wait up to 10 messages
                message = await asyncio.wait_for(websocket.recv(), timeout=70)
                data = json.loads(message)
                
                if data.get('type') == 'status_update':
                    print("\n=== Status Update Message ===\n")
                    print(json.dumps(data, indent=2, default=str))
                    
                    if 'models' in data and data['models']:
                        print("\n=== First Model Details ===\n")
                        print(json.dumps(data['models'][0], indent=2))
                    break
                else:
                    print(f"Received {data.get('type')} message, waiting for status_update...")
                
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test_ws())
