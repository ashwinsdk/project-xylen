#!/bin/bash

# Test script to call model server /retrain endpoint
# Usage: ./curl_retrain.sh [MODEL_SERVER_IP] [PORT]

MODEL_IP=${1:-"192.168.1.100"}
MODEL_PORT=${2:-"8000"}
URL="http://${MODEL_IP}:${MODEL_PORT}/retrain"

echo "Sending training sample to: $URL"
echo ""

FEEDBACK_DATA='{
  "decision": {
    "action": "long",
    "confidence": 0.75,
    "raw_score": 0.65
  },
  "outcome": {
    "pnl": 500.0,
    "pnl_percent": 1.0,
    "success": true
  },
  "snapshot": {
    "symbol": "BTCUSDT",
    "indicators": {
      "rsi": 55.2,
      "volume": 167.89,
      "ema_20": 50150.0,
      "ema_50": 49980.0
    }
  }
}'

echo "$FEEDBACK_DATA" | jq .
echo ""

curl -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d "$FEEDBACK_DATA" \
  --silent \
  --show-error \
  --write-out "\n\nHTTP Status: %{http_code}\nTime: %{time_total}s\n"

if [ $? -eq 0 ]; then
    echo ""
    echo "Feedback sent successfully!"
else
    echo ""
    echo "Failed to send feedback!"
    exit 1
fi

echo ""
echo "To trigger retraining:"
echo "curl -X POST http://${MODEL_IP}:${MODEL_PORT}/retrain/trigger"
