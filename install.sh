#!/bin/bash

# install.sh - Clean installation script for VPSTradingBot

echo "🚀 Starting VPSTradingBot Installation..."

# 1. Determine Python Interpreter (3.10+)
PYTHON_EXEC=""

if command -v python3 &>/dev/null; then
    # Check version >= 3.10 using python one-liner
    if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)'; then
        PYTHON_EXEC="python3"
    fi
fi

# Fallback to explicit versions if default python3 is too old or checking failed
if [ -z "$PYTHON_EXEC" ]; then
    for ver in "python3.10" "python3.11" "python3.12"; do
        if command -v $ver &>/dev/null; then
            PYTHON_EXEC=$ver
            break
        fi
    done
fi

if [ -z "$PYTHON_EXEC" ]; then
    echo "❌ Python 3.10+ is required but not found."
    echo "   Current 'python3' is too old or missing."
    echo "   Install Python 3.10:"
    echo "     sudo apt update"
    echo "     sudo apt install software-properties-common"
    echo "     sudo add-apt-repository ppa:deadsnakes/ppa"
    echo "     sudo apt install python3.10 python3.10-venv python3.10-dev"
    exit 1
fi

echo "✅ Using Python interpreter: $PYTHON_EXEC"

# 2. Setup Virtual Environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment (.venv)..."
    if ! $PYTHON_EXEC -m venv .venv; then
        echo "❌ Failed to create virtual environment!"
        echo "   It seems you are missing the python3-venv package."
        echo "   Please try running:"
        echo "     sudo apt update"
        echo "     sudo apt install ${PYTHON_EXEC}-venv"
        echo "   Then run this script again."
        exit 1
    fi
else
    echo "ℹ️  Virtual environment already exists."
fi

# 3. Install Dependencies
echo "📥 Installing dependencies..."
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo "❌ Failed to activate virtual environment. Aborting."
    exit 1
fi

pip install --upgrade pip
if [ $? -ne 0 ]; then
    echo "❌ Failed to upgrade pip. Aborting."
    exit 1
fi

pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Failed to install requirements. Aborting."
    exit 1
fi

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