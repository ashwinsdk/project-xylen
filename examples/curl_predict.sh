#!/bin/bash

# Test script to call model server /predict endpoint
# Usage: ./curl_predict.sh [MODEL_SERVER_IP] [PORT]

MODEL_IP=${1:-"100.108.252.74"}
MODEL_PORT=${2:-"8000"}
URL="http://${MODEL_IP}:${MODEL_PORT}/predict"

echo "Testing model server at: $URL"
echo ""

curl -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d @sample_snapshot.json \
  --silent \
  --show-error \
  --write-out "\n\nHTTP Status: %{http_code}\nTime: %{time_total}s\n" | jq .

if [ $? -eq 0 ]; then
    echo ""
    echo "Test successful!"
else
    echo ""
    echo "Test failed!"
    exit 1
fi
