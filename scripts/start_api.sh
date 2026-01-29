#!/bin/bash
# Start API server

set -e
cd "$(dirname "$0")/.."

# Activate venv
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Create directories
mkdir -p data logs

# Start server
echo "Starting API server on http://localhost:8000"
python -m uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
