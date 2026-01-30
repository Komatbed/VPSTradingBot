#!/bin/bash

# install.sh - Clean installation script for VPSTradingBot

echo "🚀 Starting VPSTradingBot Installation..."

# 1. Check Python version
if ! command -v python3.10 &> /dev/null; then
    echo "❌ Python 3.10 is required but not found."
    echo "   Install it: sudo apt install python3.10 python3.10-venv python3.10-dev"
    exit 1
fi

# 2. Setup Virtual Environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment (.venv)..."
    python3.10 -m venv .venv
else
    echo "ℹ️  Virtual environment already exists."
fi

# 3. Install Dependencies
echo "📥 Installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Create .env if missing
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "   Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env with your tokens:"
    echo "   nano .env"
fi

# 5. Setup Systemd Services
echo "⚙️  Setting up Systemd services..."

# Get current directory and user
WORK_DIR=$(pwd)
CURRENT_USER=$(whoami)

echo "   - Working Directory: $WORK_DIR"
echo "   - User: $CURRENT_USER"

# Function to patch and install service
install_service() {
    SERVICE_NAME=$1
    SOURCE_FILE="deploy/$SERVICE_NAME"
    DEST_FILE="/etc/systemd/system/$SERVICE_NAME"
    
    if [ ! -f "$SOURCE_FILE" ]; then
        echo "❌ Service file $SOURCE_FILE not found!"
        return
    fi

    echo "   Installing $SERVICE_NAME..."
    
    # Create temp file with replaced paths
    sed -e "s|User=ubuntu|User=$CURRENT_USER|g" \
        -e "s|WorkingDirectory=/home/ubuntu/VPSTradingBot|WorkingDirectory=$WORK_DIR|g" \
        -e "s|ExecStart=/home/ubuntu/VPSTradingBot/.venv/bin/python|ExecStart=$WORK_DIR/.venv/bin/python|g" \
        "$SOURCE_FILE" > "/tmp/$SERVICE_NAME"

    # Move to systemd (requires sudo)
    sudo mv "/tmp/$SERVICE_NAME" "$DEST_FILE"
    sudo chmod 644 "$DEST_FILE"
}

install_service "tradingbot.service"
install_service "ml_advisor.service"

# 6. Reload Systemd
echo "🔄 Reloading Systemd..."
sudo systemctl daemon-reload

# 7. Setup Permissions
echo "🔐 Setting up permissions..."
chmod +x manage.py

echo "✅ Installation Complete!"
echo ""
echo "👉 To start services:"
echo "   sudo systemctl enable tradingbot ml_advisor"
echo "   sudo systemctl start tradingbot ml_advisor"
echo ""
echo "👉 To check status:"
echo "   sudo systemctl status tradingbot"