#!/bin/bash

# Lead Router Pro - Production Mode with Auto-Restart Protection
# This script starts the server in production mode with crash recovery

echo "🚀 Lead Router Pro - Production Mode with Auto-Restart"
echo "======================================================="
echo "Timestamp: $(date)"

# Configuration
APP_DIR="/root/Lead-Router-Pro"
LOG_FILE="/root/Lead-Router-Pro/server.log"
ERROR_LOG="/root/Lead-Router-Pro/server_error.log"
MONITOR_LOG="/root/Lead-Router-Pro/monitor.log"
PID_FILE="/root/Lead-Router-Pro/leadrouter.pid"
AUTO_RESTART=${AUTO_RESTART:-"true"}
MAX_RESTARTS=10
RESTART_DELAY=10

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$MONITOR_LOG"
}

# Function to kill existing processes
kill_existing() {
    log_message "Stopping any existing Lead Router Pro processes..."
    
    # Kill by PID file if exists
    if [ -f "$PID_FILE" ]; then
        old_pid=$(cat "$PID_FILE")
        if kill -0 "$old_pid" 2>/dev/null; then
            log_message "   Stopping process $old_pid..."
            kill -TERM "$old_pid" 2>/dev/null || true
            sleep 2
            if kill -0 "$old_pid" 2>/dev/null; then
                kill -KILL "$old_pid" 2>/dev/null || true
            fi
        fi
        rm -f "$PID_FILE"
    fi
    
    # Kill any uvicorn processes
    pkill -f "uvicorn main_working_final:app" 2>/dev/null || true
    
    # Kill processes on port 8000
    local pids=$(lsof -ti :8000 2>/dev/null || true)
    if [ -n "$pids" ]; then
        for pid in $pids; do
            kill -TERM $pid 2>/dev/null || true
        done
        sleep 2
        for pid in $pids; do
            if kill -0 $pid 2>/dev/null; then
                kill -KILL $pid 2>/dev/null || true
            fi
        done
    fi
    
    sleep 2
}

# Function to check server health
check_health() {
    curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://localhost:8000/health 2>/dev/null
}

# Function to start server
start_server() {
    log_message "Starting Lead Router Pro server..."
    
    cd "$APP_DIR" || {
        log_message "ERROR: Failed to change to application directory"
        return 1
    }
    
    # Activate virtual environment
    if [ ! -d "venv" ]; then
        log_message "ERROR: Virtual environment not found!"
        return 1
    fi
    
    source venv/bin/activate
    
    # Start the server in background
    nohup python -m uvicorn main_working_final:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 1 \
        --log-level info \
        >> "$LOG_FILE" 2>> "$ERROR_LOG" &
    
    local server_pid=$!
    echo $server_pid > "$PID_FILE"
    
    log_message "   Server started with PID: $server_pid"
    
    # Wait for server to be ready
    local wait_count=0
    while [ $wait_count -lt 30 ]; do
        if [ "$(check_health)" == "200" ]; then
            log_message "✅ Server is running and healthy!"
            return 0
        fi
        sleep 1
        wait_count=$((wait_count + 1))
    done
    
    log_message "⚠️ Server started but health check failed"
    return 1
}

# Function to monitor and restart server
monitor_server() {
    local restart_count=0
    local consecutive_failures=0
    
    while [ "$AUTO_RESTART" = "true" ]; do
        # Check if server is healthy
        if [ "$(check_health)" == "200" ]; then
            consecutive_failures=0
        else
            consecutive_failures=$((consecutive_failures + 1))
            log_message "⚠️ Health check failed ($consecutive_failures consecutive failures)"
            
            # If multiple failures, restart
            if [ $consecutive_failures -ge 3 ]; then
                restart_count=$((restart_count + 1))
                
                if [ $restart_count -gt $MAX_RESTARTS ]; then
                    log_message "❌ Maximum restart attempts ($MAX_RESTARTS) exceeded!"
                    log_message "   Server appears to be in a crash loop."
                    log_message "   Manual intervention required."
                    exit 1
                fi
                
                log_message "🔄 Attempting restart #$restart_count..."
                
                # Kill existing process
                kill_existing
                
                # Try to restart
                if start_server; then
                    log_message "✅ Server restarted successfully"
                    consecutive_failures=0
                else
                    log_message "❌ Failed to restart server"
                    sleep $RESTART_DELAY
                fi
            fi
        fi
        
        # Check every 30 seconds
        sleep 30
    done
}

# Main execution
main() {
    log_message "=" 
    log_message "Starting Lead Router Pro Production Server"
    log_message "Auto-restart: $AUTO_RESTART"
    log_message ""
    
    # Kill any existing processes
    kill_existing
    
    # Start the server
    if ! start_server; then
        log_message "❌ Failed to start server"
        exit 1
    fi
    
    log_message ""
    log_message "📊 Dashboard: https://dockside.life/admin"
    log_message "📝 Server logs: $LOG_FILE"
    log_message "❌ Error logs: $ERROR_LOG"
    log_message "🔍 Monitor logs: $MONITOR_LOG"
    log_message ""
    
    if [ "$AUTO_RESTART" = "true" ]; then
        log_message "🛡️ Monitoring server health (auto-restart enabled)..."
        log_message "   To stop: kill $(cat $PID_FILE) or run: pkill -f 'uvicorn main_working_final:app'"
        monitor_server
    else
        log_message "✅ Server started (auto-restart disabled)"
        log_message "   PID: $(cat $PID_FILE)"
        log_message "   To stop: kill $(cat $PID_FILE)"
    fi
}

# Trap signals for clean shutdown
trap 'log_message "Received shutdown signal"; kill_existing; exit 0' SIGTERM SIGINT

# Run main function
main