#!/bin/bash

# Test runner script for TradeProject
# Runs unit tests and integration tests

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "================================"
echo "TradeProject Test Suite"
echo "================================"
echo ""

cd "$PROJECT_DIR/mac_coordinator"

if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

source venv/bin/activate

echo "Python version:"
python --version
echo ""

echo "Installing test dependencies..."
pip install pytest pytest-asyncio pytest-mock --quiet

echo ""
echo "================================"
echo "Running Unit Tests"
echo "================================"
echo ""

if [ -d "tests" ]; then
    pytest tests/ -v
    UNIT_TEST_EXIT=$?
else
    echo "No unit tests found"
    UNIT_TEST_EXIT=0
fi

echo ""
echo "================================"
echo "Running Integration Test"
echo "================================"
echo ""

cd "$PROJECT_DIR"
python ci/test_integration.py
INTEGRATION_TEST_EXIT=$?

echo ""
echo "================================"
echo "Test Summary"
echo "================================"
echo ""

if [ $UNIT_TEST_EXIT -eq 0 ] && [ $INTEGRATION_TEST_EXIT -eq 0 ]; then
    echo "All tests passed!"
    exit 0
else
    echo "Some tests failed:"
    [ $UNIT_TEST_EXIT -ne 0 ] && echo "  - Unit tests failed"
    [ $INTEGRATION_TEST_EXIT -ne 0 ] && echo "  - Integration test failed"
    exit 1
fi
