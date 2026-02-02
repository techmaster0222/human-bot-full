#!/bin/bash
# Start dashboard

set -e
cd "$(dirname "$0")/../dashboard"

# Check Node
if ! command -v node &> /dev/null; then
    echo "Error: Node.js not installed"
    exit 1
fi

# Install deps
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start
echo "Starting dashboard on http://localhost:3000"
npm run dev -- --port 3000
