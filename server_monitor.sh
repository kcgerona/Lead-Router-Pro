#!/bin/bash

# Lead Router Pro Server Monitor Script
# This script monitors the FastAPI server and restarts it if needed

LOG_FILE="/root/Lead-Router-Pro/monitor.log"
SERVER_URL="http://localhost:8000/health"
RESTART_SCRIPT="/root/Lead-Router-Pro/restart_server.sh"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Function to check if server is running
check_server() {
    # Try to hit the health endpoint
    response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$SERVER_URL" 2>/dev/null)
    
    if [ "$response" == "200" ]; then
        return 0  # Server is healthy
    else
        return 1  # Server is not responding
    fi
}

# Function to restart server
restart_server() {
    log_message "Server health check failed. Attempting restart..."
    
    # Kill any existing Python/Uvicorn processes
    pkill -f "uvicorn main_working_final:app" 2>/dev/null
    sleep 2
    
    # Force kill if still running
    pkill -9 -f "uvicorn main_working_final:app" 2>/dev/null
    sleep 1
    
    # Start the server
    cd /root/Lead-Router-Pro
    source venv/bin/activate
    nohup python -m uvicorn main_working_final:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info >> server.log 2>&1 &
    
    sleep 10  # Give server time to start
    
    # Check if restart was successful
    if check_server; then
        log_message "Server restarted successfully"
        return 0
    else
        log_message "Failed to restart server"
        return 1
    fi
}

# Main monitoring loop
main() {
    log_message "Starting server monitor"
    
    while true; do
        if ! check_server; then
            log_message "Server health check failed"
            
            # Try to restart
            if restart_server; then
                log_message "Recovery successful"
            else
                log_message "Recovery failed - manual intervention may be needed"
                # Could send an alert here if email/notification system is set up
            fi
        fi
        
        # Wait before next check (60 seconds)
        sleep 60
    done
}

# Run the monitor
main