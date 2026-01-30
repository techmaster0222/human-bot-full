#!/bin/bash
# Start API server and dashboard

set -e
cd "$(dirname "$0")/.."

echo "Starting AdsPower Bot Engine..."

# Start API
echo "Starting API server..."
./scripts/start_api.sh &
API_PID=$!

# Wait for API
echo "Waiting for API..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "API is ready"
        break
    fi
    sleep 1
done

# Start dashboard
echo "Starting dashboard..."
./scripts/start_dashboard.sh &

echo ""
echo "Services running:"
echo "  API: http://localhost:8000"
echo "  Dashboard: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop"

wait
