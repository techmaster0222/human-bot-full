#!/bin/bash
# Start all services (API + Dashboard)

set -e
cd "$(dirname "$0")/.."

echo "Starting AdsPower Bot Engine..."

# Start API in background
./scripts/start_api.sh &
API_PID=$!

# Wait for API to be ready
echo "Waiting for API..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health > /dev/null; then
        echo "API is ready!"
        break
    fi
    sleep 1
done

# Start dashboard
./scripts/start_dashboard.sh
