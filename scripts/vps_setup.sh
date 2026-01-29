#!/bin/bash
#=====================================================
# VPS Setup Script for Human-like Bot System
# Run this on your VPS after uploading the project
#=====================================================

set -e

echo "=========================================="
echo "VPS SETUP - Human-like Bot System"
echo "=========================================="

# Update system
echo "[1/8] Updating system packages..."
apt update && apt upgrade -y

# Install dependencies
echo "[2/8] Installing system dependencies..."
apt install -y python3 python3-pip python3-venv unzip wget curl git xvfb

# Install Chrome dependencies for headless
echo "[3/8] Installing Chrome dependencies..."
apt install -y libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2

# Create project directory
echo "[4/8] Setting up project directory..."
cd /root
if [ -f "ads_project_deploy.zip" ]; then
    mkdir -p /opt/ads_project
    unzip -o ads_project_deploy.zip -d /opt/ads_project
    cd /opt/ads_project
else
    echo "ERROR: ads_project_deploy.zip not found in /root"
    exit 1
fi

# Create virtual environment
echo "[5/8] Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "[6/8] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install playwright

# Install Playwright browsers (for testing without AdsPower)
echo "[7/8] Installing Playwright browsers..."
playwright install chromium
playwright install-deps chromium

# Create directories
echo "[8/8] Creating necessary directories..."
mkdir -p logs screenshots data config

# Create .env file template
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "=========================================="
    echo "IMPORTANT: Edit /opt/ads_project/.env"
    echo "=========================================="
    echo "Add your credentials:"
    echo "  - ADSPOWER_API_URL"
    echo "  - ADSPOWER_API_KEY"
    echo "  - IPROYAL_USERNAME"
    echo "  - IPROYAL_PASSWORD"
fi

echo ""
echo "=========================================="
echo "SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "Project location: /opt/ads_project"
echo ""
echo "Next steps:"
echo "1. Install AdsPower on VPS (see below)"
echo "2. Edit .env with your credentials"
echo "3. Run: source venv/bin/activate && python my_test.py"
echo ""
echo "=========================================="
echo "ADSPOWER INSTALLATION (Linux)"
echo "=========================================="
echo ""
echo "Option 1: Download from AdsPower website"
echo "  wget https://version.adspower.net/download/AdsPower-Global-5.9.18-x64.deb"
echo "  dpkg -i AdsPower-Global-*.deb"
echo "  apt --fix-broken install -y"
echo ""
echo "Option 2: If using GUI (VNC/RDP)"
echo "  - Download from: https://www.adspower.com/download"
echo "  - Install the .deb package"
echo ""
echo "To start AdsPower:"
echo "  /opt/AdsGlobal/adspower --args --headless=new"
echo ""
