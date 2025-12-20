#!/bin/bash
# GW2 CounterPicker - Production Deployment Script
# This script deploys the application to the production server

set -e  # Exit on error

echo "=== GW2 CounterPicker Deployment ==="
echo "Starting deployment at $(date)"

# Configuration
APP_DIR="/home/syff/gw2-counterpicker"
SERVICE_NAME="gw2-counterpicker"
VENV_DIR="$APP_DIR/venv"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    print_error "main.py not found. Are you in the correct directory?"
    exit 1
fi

print_status "Pulling latest changes from git..."
git fetch origin
git checkout main

# Stash local changes (especially data files) before pulling
if ! git diff-index --quiet HEAD --; then
    print_warning "Local changes detected, stashing..."
    git stash push -m "Auto-stash before deployment $(date)"
fi

git pull origin main

# Restore stashed changes if any
if git stash list | grep -q "Auto-stash before deployment"; then
    print_status "Restoring local data changes..."
    git stash pop || print_warning "Could not restore stash (conflicts possible)"
fi

print_status "Activating virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    print_warning "Virtual environment not found, creating one..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

print_status "Installing/updating dependencies..."
pip install -r requirements.txt --upgrade --quiet

print_status "Running database migrations (if any)..."
# Add migration commands here if needed in the future

print_status "Restarting application service..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    sudo systemctl restart "$SERVICE_NAME"
    print_status "Service restarted successfully"
else
    print_warning "Service not running, starting it..."
    sudo systemctl start "$SERVICE_NAME"
fi

# Wait a moment for the service to start
sleep 3

print_status "Checking service status..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    print_status "Service is running"
else
    print_error "Service failed to start"
    sudo systemctl status "$SERVICE_NAME" --no-pager
    exit 1
fi

print_status "Running health check..."
if curl -f http://localhost:8001/health > /dev/null 2>&1; then
    print_status "Health check passed"
else
    print_error "Health check failed"
    exit 1
fi

print_status "Deployment completed successfully at $(date)"
echo ""
echo "=== Deployment Summary ==="
echo "Branch: $(git branch --show-current)"
echo "Commit: $(git rev-parse --short HEAD)"
echo "Service: $SERVICE_NAME"
echo "Status: $(systemctl is-active $SERVICE_NAME)"
echo ""
