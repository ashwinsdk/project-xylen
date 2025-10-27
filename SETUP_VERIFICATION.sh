#!/bin/bash

# TradeProject Setup Verification Script
# Run this to check if your environment is ready

echo "================================"
echo "TradeProject Setup Verification"
echo "================================"
echo ""

CHECKS_PASSED=0
CHECKS_FAILED=0

# Function to check command
check_command() {
    if command -v $1 &> /dev/null; then
        echo "[PASS] $1 is installed: $(command -v $1)"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
        return 0
    else
        echo "[FAIL] $1 is not installed"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        return 1
    fi
}

# Function to check version
check_version() {
    local cmd=$1
    local expected=$2
    local version=$($cmd 2>&1)
    echo "[INFO] $cmd version: $version"
    if [[ $version == *"$expected"* ]] || [[ $version > $expected ]]; then
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
        return 0
    else
        echo "[WARN] Expected version $expected or higher"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        return 1
    fi
}

echo "Checking Required Software..."
echo "-----------------------------"

check_command python3
if [ $? -eq 0 ]; then
    python3 --version
fi

check_command pip3
check_command node
if [ $? -eq 0 ]; then
    node --version
fi

check_command npm
if [ $? -eq 0 ]; then
    npm --version
fi

check_command git
check_command curl

echo ""
echo "Checking Optional Software..."
echo "-----------------------------"

check_command docker
if [ $? -eq 0 ]; then
    docker --version
fi

echo ""
echo "Checking Project Structure..."
echo "-----------------------------"

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

check_file() {
    if [ -f "$PROJECT_DIR/$1" ]; then
        echo "[PASS] Found: $1"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        echo "[FAIL] Missing: $1"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
    fi
}

check_dir() {
    if [ -d "$PROJECT_DIR/$1" ]; then
        echo "[PASS] Found directory: $1"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        echo "[FAIL] Missing directory: $1"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
    fi
}

check_file "config.yaml.example"
check_file "README.md"
check_file "DOCUMENTATION.md"
check_dir "mac_coordinator"
check_dir "model_server_template"
check_dir "dashboard"
check_file "mac_coordinator/coordinator.py"
check_file "mac_coordinator/requirements.txt"
check_file "dashboard/package.json"

echo ""
echo "Checking Environment Variables..."
echo "--------------------------------"

if [ -z "$BINANCE_TESTNET_API_KEY" ]; then
    echo "[WARN] BINANCE_TESTNET_API_KEY not set"
    echo "       Set with: export BINANCE_TESTNET_API_KEY='your_key'"
else
    echo "[PASS] BINANCE_TESTNET_API_KEY is set"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
fi

if [ -z "$BINANCE_TESTNET_API_SECRET" ]; then
    echo "[WARN] BINANCE_TESTNET_API_SECRET not set"
    echo "       Set with: export BINANCE_TESTNET_API_SECRET='your_secret'"
else
    echo "[PASS] BINANCE_TESTNET_API_SECRET is set"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
fi

echo ""
echo "Checking Configuration..."
echo "------------------------"

if [ -f "$PROJECT_DIR/config.yaml" ]; then
    echo "[PASS] config.yaml exists"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
    
    if grep -q "dry_run: true" "$PROJECT_DIR/config.yaml"; then
        echo "[PASS] dry_run is enabled (safe mode)"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        echo "[WARN] dry_run is not enabled - will place real orders!"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
    fi
    
    if grep -q "testnet: true" "$PROJECT_DIR/config.yaml"; then
        echo "[PASS] testnet mode is enabled (safe mode)"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        echo "[WARN] testnet mode is disabled - will use real funds!"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
    fi
else
    echo "[INFO] config.yaml not found (use config.yaml.example as template)"
    echo "       Run: cp config.yaml.example config.yaml"
fi

echo ""
echo "Checking Python Virtual Environment..."
echo "-------------------------------------"

if [ -d "$PROJECT_DIR/mac_coordinator/venv" ]; then
    echo "[PASS] Virtual environment exists"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo "[INFO] Virtual environment not created yet"
    echo "       Run: cd mac_coordinator && python3 -m venv venv"
fi

echo ""
echo "Checking Network Connectivity..."
echo "-------------------------------"

if curl -s --max-time 5 https://testnet.binancefuture.com/fapi/v1/time > /dev/null; then
    echo "[PASS] Can reach Binance testnet"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo "[FAIL] Cannot reach Binance testnet"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
fi

echo ""
echo "================================"
echo "Verification Summary"
echo "================================"
echo "Checks passed: $CHECKS_PASSED"
echo "Checks failed/warning: $CHECKS_FAILED"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo "[SUCCESS] Your environment looks good!"
    echo ""
    echo "Next steps:"
    echo "1. If not done, run: cp config.yaml.example config.yaml"
    echo "2. Edit config.yaml with your VM IPs"
    echo "3. Set up VMs following VM_SETUP.md"
    echo "4. Run coordinator: cd mac_coordinator && source venv/bin/activate && python coordinator.py"
    echo "5. Run dashboard: cd dashboard && npm install && npm run dev"
    exit 0
else
    echo "[ACTION REQUIRED] Please address the issues above"
    echo ""
    echo "Quick fixes:"
    echo "- Install missing software using Homebrew or official installers"
    echo "- Create config.yaml from config.yaml.example"
    echo "- Set Binance testnet API keys in environment variables"
    echo "- Create Python virtual environment in mac_coordinator/"
    echo ""
    echo "See DOCUMENTATION.md for detailed setup instructions"
    exit 1
fi
