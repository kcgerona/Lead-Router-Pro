#!/bin/bash

# Lead Router Pro - Systemd Service Installation Script
# This script installs the Lead Router Pro as a systemd service for automatic startup

echo "🔧 Installing Lead Router Pro as systemd service..."
echo "===================================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run this script as root (use sudo)"
    exit 1
fi

# Configuration
SERVICE_FILE="/etc/systemd/system/lead-router-pro.service"
APP_DIR="/root/Lead-Router-Pro"

# Create the service file
echo "📝 Creating systemd service file..."

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Lead Router Pro FastAPI Application
After=network.target
StartLimitIntervalSec=0

[Service]
Type=exec
User=root
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$APP_DIR/venv/bin/python -m uvicorn main_working_final:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info
Restart=always
RestartSec=10
StandardOutput=append:$APP_DIR/server.log
StandardError=append:$APP_DIR/server_error.log

# Restart conditions
RestartPreventExitStatus=0
SuccessExitStatus=0

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Kill settings
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file created at: $SERVICE_FILE"

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Enable the service
echo "🔌 Enabling service to start on boot..."
systemctl enable lead-router-pro.service

# Start the service
echo "🚀 Starting Lead Router Pro service..."
systemctl start lead-router-pro.service

# Wait for service to start
sleep 5

# Check service status
echo ""
echo "📊 Service Status:"
echo "=================="
systemctl status lead-router-pro.service --no-pager

echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 Useful commands:"
echo "   - Check status:  systemctl status lead-router-pro"
echo "   - View logs:     journalctl -u lead-router-pro -f"
echo "   - Restart:       systemctl restart lead-router-pro"
echo "   - Stop:          systemctl stop lead-router-pro"
echo "   - Disable:       systemctl disable lead-router-pro"
echo ""
echo "🌐 Access points:"
echo "   - Dashboard:     https://dockside.life/admin"
echo "   - API Docs:      https://dockside.life/docs"
echo "   - Health Check:  https://dockside.life/health"