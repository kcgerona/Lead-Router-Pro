#!/bin/bash

# Lead Router Pro Quick Restart Script

echo "Stopping Lead Router Pro server..."

# Kill any existing processes
pkill -f "uvicorn main_working_final:app" 2>/dev/null
sleep 2

# Force kill if still running
pkill -9 -f "uvicorn main_working_final:app" 2>/dev/null
sleep 1

echo "Starting Lead Router Pro server..."

# Navigate to project directory
cd /root/Lead-Router-Pro

# Activate virtual environment and start server
source venv/bin/activate

# Start in background with nohup for production
nohup python -m uvicorn main_working_final:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info \
    >> server.log 2>&1 &

echo "Server starting... PID: $!"
echo "Checking server health..."

# Wait for server to start
sleep 5

# Check if server is running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Server is running and healthy!"
    echo "📊 Dashboard: https://dockside.life/admin"
    echo "📝 Logs: tail -f server.log"
else
    echo "⚠️ Server may still be starting. Check logs: tail -f server.log"
fi