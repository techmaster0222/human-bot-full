#!/bin/bash
cd /opt/project/ads_project
source venv/bin/activate
export DISPLAY=:99

# Start Xvfb if not running
pgrep Xvfb || (Xvfb :99 -screen 0 1920x1080x24 & sleep 2)

# Run test
python my_test.py

