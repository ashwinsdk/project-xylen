#!/bin/bash

# Project Xylen - Test Runner
# Runs integration tests for the coordinator

set -e

echo "=================================="
echo "Project Xylen - Test Runner"
echo "=================================="
echo ""

# Check if in correct directory
if [ ! -f "coordinator/tests/test_integration.py" ]; then
    echo "ERROR: Must run from project root directory"
    exit 1
fi

# Check if dependencies are installed
echo "Checking dependencies..."
python -c "import pytest" 2>/dev/null || {
    echo "ERROR: pytest not installed. Run: pip install -r coordinator/requirements.txt"
    exit 1
}

python -c "import aiohttp" 2>/dev/null || {
    echo "ERROR: aiohttp not installed. Run: pip install -r coordinator/requirements.txt"
    exit 1
}

echo "Dependencies OK"
echo ""

# Run tests
echo "Running integration tests..."
echo ""

cd coordinator
pytest tests/test_integration.py -v -s --tb=short --color=yes

TEST_EXIT_CODE=$?

cd ..

echo ""
echo "=================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✓ All tests passed!"
else
    echo "✗ Some tests failed (exit code: $TEST_EXIT_CODE)"
fi
echo "=================================="

exit $TEST_EXIT_CODE
