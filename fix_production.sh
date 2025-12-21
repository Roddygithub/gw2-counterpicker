#!/bin/bash

# GW2 CounterPicker - Production Fix Script
# This script diagnoses and fixes common production issues

echo "=========================================="
echo "GW2 CounterPicker - Production Diagnostic"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if service exists
echo "1. Checking if gw2-counterpicker service exists..."
if systemctl list-unit-files | grep -q gw2-counterpicker; then
    echo -e "${GREEN}✓ Service exists${NC}"
else
    echo -e "${RED}✗ Service does not exist${NC}"
    echo "Please create the systemd service file first."
    exit 1
fi

# Check service status
echo ""
echo "2. Checking service status..."
if systemctl is-active --quiet gw2-counterpicker; then
    echo -e "${GREEN}✓ Service is running${NC}"
    SERVICE_RUNNING=true
else
    echo -e "${RED}✗ Service is not running${NC}"
    SERVICE_RUNNING=false
fi

# Check if port 8001 is listening
echo ""
echo "3. Checking if port 8001 is listening..."
if ss -tlnp 2>/dev/null | grep -q ":8001"; then
    echo -e "${GREEN}✓ Port 8001 is listening${NC}"
    PORT_LISTENING=true
else
    echo -e "${RED}✗ Port 8001 is not listening${NC}"
    PORT_LISTENING=false
fi

# Show recent logs
echo ""
echo "4. Recent service logs (last 30 lines):"
echo "----------------------------------------"
journalctl -u gw2-counterpicker -n 30 --no-pager

# Check for common issues
echo ""
echo "5. Checking for common issues..."

# Check if Python process is running
if pgrep -f "uvicorn main:app" > /dev/null; then
    echo -e "${GREEN}✓ Python/Uvicorn process is running${NC}"
else
    echo -e "${YELLOW}⚠ No Python/Uvicorn process found${NC}"
fi

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
else
    echo -e "${RED}✗ Virtual environment not found${NC}"
fi

# Check if main.py exists
if [ -f "main.py" ]; then
    echo -e "${GREEN}✓ main.py exists${NC}"
else
    echo -e "${RED}✗ main.py not found${NC}"
fi

# Attempt to fix if service is not running
echo ""
echo "=========================================="
echo "Attempting to fix issues..."
echo "=========================================="
echo ""

if [ "$SERVICE_RUNNING" = false ]; then
    echo "Restarting service..."
    systemctl restart gw2-counterpicker
    sleep 5
    
    if systemctl is-active --quiet gw2-counterpicker; then
        echo -e "${GREEN}✓ Service restarted successfully${NC}"
    else
        echo -e "${RED}✗ Service failed to start${NC}"
        echo ""
        echo "Detailed error logs:"
        journalctl -u gw2-counterpicker -n 50 --no-pager
        exit 1
    fi
fi

# Final verification
echo ""
echo "=========================================="
echo "Final Verification"
echo "=========================================="
echo ""

sleep 3

# Check service status
if systemctl is-active --quiet gw2-counterpicker; then
    echo -e "${GREEN}✓ Service is running${NC}"
else
    echo -e "${RED}✗ Service is still not running${NC}"
fi

# Check port
if ss -tlnp 2>/dev/null | grep -q ":8001"; then
    echo -e "${GREEN}✓ Port 8001 is listening${NC}"
else
    echo -e "${RED}✗ Port 8001 is still not listening${NC}"
fi

# Test health endpoint
echo ""
echo "Testing health endpoint..."
if curl -f http://localhost:8001/health 2>/dev/null; then
    echo ""
    echo -e "${GREEN}✓ Health check passed - Site is accessible!${NC}"
else
    echo ""
    echo -e "${RED}✗ Health check failed${NC}"
    echo "The service may be starting up. Wait 10-15 seconds and try again."
fi

echo ""
echo "=========================================="
echo "Diagnostic complete"
echo "=========================================="
