#!/usr/bin/env python3
"""
Test Binance Testnet API Connection
Loads credentials from coordinator/.env and tests connection
"""

import os
import time
import hmac
import hashlib
import requests
from pathlib import Path

def load_env_file(env_path):
    """Load environment variables from .env file"""
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

def create_signature(params, secret):
    """Create HMAC SHA256 signature for Binance API (matches binance_client.py)"""
    # Sort params and create query string exactly like binance_client.py
    query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
    signature = hmac.new(
        secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def test_binance_testnet():
    """Test connection to Binance Futures Testnet"""
    
    # Load credentials from coordinator/.env
    env_path = Path(__file__).parent / 'coordinator' / '.env'
    env_vars = load_env_file(env_path)
    
    api_key = env_vars.get('BINANCE_TESTNET_API_KEY')
    api_secret = env_vars.get('BINANCE_TESTNET_API_SECRET')
    
    if not api_key or not api_secret:
        print('❌ API keys not found in coordinator/.env')
        print(f'   Looking for: {env_path}')
        return False
    
    print('✅ API keys loaded from .env file')
    print(f'   API Key: {api_key[:10]}...')
    
    # Test 1: Server time (no authentication required)
    print('\n🔍 Test 1: Checking server connection...')
    try:
        resp = requests.get('https://testnet.binancefuture.com/fapi/v1/time', timeout=10)
        if resp.status_code == 200:
            server_time = resp.json()['serverTime']
            print(f'✅ Server reachable - Server time: {server_time}')
        else:
            print(f'❌ Server unreachable - Status: {resp.status_code}')
            return False
    except Exception as e:
        print(f'❌ Connection error: {e}')
        return False
    
    # Test 2: Account info (authentication required)
    print('\n🔍 Test 2: Testing API authentication...')
    try:
        timestamp = int(time.time() * 1000)
        params = {
            'timestamp': timestamp
        }
        
        # Create signature
        signature = create_signature(params, api_secret)
        params['signature'] = signature
        
        # Debug output
        print(f'   Timestamp: {timestamp}')
        print(f'   Signature: {signature[:20]}...')
        
        headers = {'X-MBX-APIKEY': api_key}
        
        resp = requests.get(
            'https://testnet.binancefuture.com/fapi/v2/account',
            headers=headers,
            params=params,
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            balance = float(data.get('totalWalletBalance', 0))
            available = float(data.get('availableBalance', 0))
            
            print('✅ Authentication successful!')
            print(f'\n💰 Account Balance:')
            print(f'   Total Wallet: {balance:,.2f} USDT')
            print(f'   Available:    {available:,.2f} USDT')
            
            # Show positions if any
            positions = [p for p in data.get('positions', []) if float(p.get('positionAmt', 0)) != 0]
            if positions:
                print(f'\n📊 Open Positions: {len(positions)}')
                for pos in positions:
                    symbol = pos['symbol']
                    amt = float(pos['positionAmt'])
                    entry = float(pos['entryPrice'])
                    pnl = float(pos.get('unrealizedProfit', 0))
                    print(f'   {symbol}: {amt:+.4f} @ ${entry:,.2f} (P&L: ${pnl:+.2f})')
            else:
                print('\n📊 Open Positions: None')
            
            return True
            
        elif resp.status_code == 401:
            print('❌ Authentication failed - Invalid API keys')
            print(f'   Error: {resp.json()}')
            return False
        else:
            print(f'❌ API error - Status: {resp.status_code}')
            print(f'   Response: {resp.text}')
            return False
            
    except Exception as e:
        print(f'❌ Request error: {e}')
        return False

if __name__ == '__main__':
    print('=' * 60)
    print('Binance Futures Testnet Connection Test')
    print('=' * 60)
    
    success = test_binance_testnet()
    
    print('\n' + '=' * 60)
    if success:
        print('✅ ALL TESTS PASSED - Ready for testnet trading!')
        print('\nNext steps:')
        print('1. Update config.yaml with testnet settings')
        print('2. Set dry_run=false, testnet=true')
        print('3. Restart coordinator to start testnet trading')
    else:
        print('❌ TESTS FAILED - Please check configuration')
        print('\nTroubleshooting:')
        print('1. Verify API keys at https://testnet.binancefuture.com/')
        print('2. Check .env file has correct keys (no extra spaces)')
        print('3. Ensure network connection is working')
    print('=' * 60)
