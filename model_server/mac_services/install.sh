#!/bin/bash
# Installation script for Project Xylen Model Server on macOS
# This script installs and configures the model server as LaunchDaemons

set -e

echo "=========================================="
echo "Project Xylen Model Server Installation"
echo "macOS LaunchDaemons Setup"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Configuration
INSTALL_DIR="/usr/local/opt/trading_model"
PLIST_DIR="/Library/LaunchDaemons"
SERVICE_USER="$SUDO_USER"

echo ""
echo "Configuration:"
echo "  Install Directory: $INSTALL_DIR"
echo "  Service User: $SERVICE_USER"
echo "  LaunchDaemons: $PLIST_DIR"
echo ""

# Create installation directory
echo "Creating installation directory..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/logs"
mkdir -p "$INSTALL_DIR/models"
mkdir -p "$INSTALL_DIR/training_data"

# Copy files
echo "Copying model server files..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

cp "$SCRIPT_DIR/server.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/model_loader_optimized.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/retrain_optimized.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/continuous_trainer.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/data_collector.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/models.env.example" "$INSTALL_DIR/"

# Create models.env if it doesn't exist
if [ ! -f "$INSTALL_DIR/models.env" ]; then
    echo "Creating models.env configuration file..."
    cp "$INSTALL_DIR/models.env.example" "$INSTALL_DIR/models.env"
fi

# Set up Python virtual environment
echo "Setting up Python virtual environment..."
if [ ! -d "$INSTALL_DIR/venv" ]; then
    python3.10 -m venv "$INSTALL_DIR/venv"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# Set permissions
echo "Setting permissions..."
chown -R "$SERVICE_USER:staff" "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR/logs"
chmod 755 "$INSTALL_DIR/models"
chmod 755 "$INSTALL_DIR/training_data"

# Install LaunchDaemons
echo "Installing LaunchDaemons..."
cp "$SCRIPT_DIR/mac_services/com.projectxylen.modelserver.plist" "$PLIST_DIR/"
cp "$SCRIPT_DIR/mac_services/com.projectxylen.datacollector.plist" "$PLIST_DIR/"
cp "$SCRIPT_DIR/mac_services/com.projectxylen.continuoustrainer.plist" "$PLIST_DIR/"

# Set plist permissions
chmod 644 "$PLIST_DIR/com.projectxylen.modelserver.plist"
chmod 644 "$PLIST_DIR/com.projectxylen.datacollector.plist"
chmod 644 "$PLIST_DIR/com.projectxylen.continuoustrainer.plist"

echo ""
echo "=========================================="
echo "Installation Complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit configuration: sudo nano $INSTALL_DIR/models.env"
echo "2. Add your model file to: $INSTALL_DIR/models/"
echo ""
echo "To start services:"
echo "  sudo launchctl load $PLIST_DIR/com.projectxylen.modelserver.plist"
echo "  sudo launchctl load $PLIST_DIR/com.projectxylen.datacollector.plist"
echo "  sudo launchctl load $PLIST_DIR/com.projectxylen.continuoustrainer.plist"
echo ""
echo "To stop services:"
echo "  sudo launchctl unload $PLIST_DIR/com.projectxylen.modelserver.plist"
echo "  sudo launchctl unload $PLIST_DIR/com.projectxylen.datacollector.plist"
echo "  sudo launchctl unload $PLIST_DIR/com.projectxylen.continuoustrainer.plist"
echo ""
echo "To check service status:"
echo "  sudo launchctl list | grep projectxylen"
echo ""
echo "View logs:"
echo "  tail -f $INSTALL_DIR/logs/model_server.log"
echo "  tail -f $INSTALL_DIR/logs/data_collector.log"
echo "  tail -f $INSTALL_DIR/logs/continuous_trainer.log"
echo ""
