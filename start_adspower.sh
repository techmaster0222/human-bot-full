#!/bin/bash
# Start AdsPower on VPS with virtual display

export DISPLAY=:99

# Kill existing Xvfb if any
pkill -f Xvfb 2>/dev/null
sleep 1

# Start Xvfb
Xvfb :99 -screen 0 1920x1080x24 &
sleep 2
echo "[OK] Xvfb started on DISPLAY=:99"

# Kill existing AdsPower if any
pkill -f adspower_global 2>/dev/null
sleep 2

# Try different AdsPower locations
if [ -f "/opt/AdsPower Global/adspower_global" ]; then
    cd "/opt/AdsPower Global"
    nohup ./adspower_global --no-sandbox --headless=new > /tmp/adspower.log 2>&1 &
elif [ -f "/opt/ads/adspower" ]; then
    /opt/ads/adspower --no-sandbox --headless=new &
elif [ -f "/opt/AdsGlobal/adspower" ]; then
    /opt/AdsGlobal/adspower --no-sandbox --headless=new &
elif [ -f "/usr/bin/adspower" ]; then
    /usr/bin/adspower --no-sandbox --headless=new &
else
    echo "[ERROR] AdsPower not found - checking..."
    find /opt -name "adspower*" -type f 2>/dev/null
    exit 1
fi

echo "Waiting for AdsPower to start..."
sleep 15

# Check if API is running
response=$(curl -s http://127.0.0.1:50325/status 2>/dev/null)
if echo "$response" | grep -q '"code":0'; then
    echo "[OK] AdsPower API is running"
else
    echo "[ERROR] AdsPower API not responding"
    echo "Check log: tail -f /tmp/adspower.log"
    exit 1
fi

