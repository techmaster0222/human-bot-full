#!/bin/bash
# Start React dashboard

set -e
cd "$(dirname "$0")/../dashboard"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start dev server
echo "Starting dashboard on http://localhost:5173"
npm run dev
