#!/bin/bash

# VM Setup Script - Run this on each Ubuntu VM after initial installation
# This script installs all dependencies and sets up the model server

set -e

echo "================================"
echo "TradeProject VM Setup"
echo "================================"
echo ""

if [ "$EUID" -eq 0 ]; then 
    echo "Error: Do not run this script as root"
    echo "Run as regular user with sudo privileges"
    exit 1
fi

echo "Updating system packages..."
sudo apt update
sudo apt upgrade -y

echo ""
echo "Installing required packages..."
sudo apt install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    build-essential \
    git \
    curl \
    net-tools \
    htop

echo ""
echo "Creating model server directory..."
sudo mkdir -p /opt/trading_model
sudo chown $USER:$USER /opt/trading_model

cd /opt/trading_model

echo ""
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo ""
echo "Upgrading pip..."
pip install --upgrade pip

echo ""
echo "Model server files should be copied here:"
echo "  scp -r model_server_template/* $USER@$(hostname -I | awk '{print $1}'):/opt/trading_model/"
echo ""
echo "After copying files, run:"
echo "  cd /opt/trading_model"
echo "  source venv/bin/activate"
echo "  pip install -r requirements.txt"
echo "  cp models.env.example models.env"
echo "  # Edit models.env with your model path"
echo "  sudo cp model_server.service /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable model_server"
echo "  sudo systemctl start model_server"
echo ""

echo "================================"
echo "VM setup base installation complete!"
echo "VM IP: $(hostname -I | awk '{print $1}')"
echo "================================"
