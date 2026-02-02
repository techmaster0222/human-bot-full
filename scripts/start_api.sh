#!/bin/bash
# Start API server

set -e
cd "$(dirname "$0")/.."

# Create directories
mkdir -p data logs

# Activate venv
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate

# Install deps
pip install -r requirements.txt -q

# Start server
echo "Starting API on http://localhost:8000"
python -m uvicorn src.api.server:app --host 0.0.0.0 --port 8000
