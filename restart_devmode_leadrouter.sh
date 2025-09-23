#!/bin/bash
# Lead Router Pro - Quick Restart Script (Dev Mode) with Auto-Restart Protection
# Automatically stops service, checks dependencies, and restarts in dev mode with crash recovery

set -e  # Exit on error

echo "🔄 Lead Router Pro - Restart Script (Dev Mode with Auto-Restart)"
echo "================================================================"
echo "Timestamp: $(date)"

# Configuration
APP_DIR="/root/Lead-Router-Pro"
LOG_DIR="/var/log/leadrouter"
LOG_FILE="$LOG_DIR/devmode.log"
PYTHON_EXEC="/root/Lead-Router-Pro/venv/bin/python"
AUTO_RESTART=${AUTO_RESTART:-"true"}  # Enable auto-restart by default

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# DISABLE AUTOMATED MONITORING FOR DEV MODE
echo "🔧 Configuring monitoring for development mode..."

# Stop the systemd service if it's running
if systemctl is-active --quiet leadrouter; then
    echo "   Stopping leadrouter systemd service..."
    systemctl stop leadrouter || true
    systemctl disable leadrouter || true
    echo "   ✅ Systemd service disabled"
fi

# Temporarily disable the cron monitor
if crontab -l 2>/dev/null | grep -q "monitor_leadrouter.sh"; then
    echo "   Disabling cron monitor..."
    # Save current crontab and comment out the monitor line
    crontab -l | sed 's|^\(.*monitor_leadrouter.sh.*\)|#DEVMODE_DISABLED: \1|' | crontab -
    echo "   ✅ Cron monitor disabled for dev mode"
fi

echo ""
echo "🛡️ AUTO-RESTART PROTECTION: $AUTO_RESTART"
echo ""

# Function to log messages
log_message() {
    echo "$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [DEV] $1" >> "$LOG_FILE"
}

# Function to kill process on port
kill_port_process() {
    local port=$1
    log_message "⏹️  Stopping any process on port $port..."
    
    # Kill any uvicorn processes first
    pkill -f "uvicorn main_working_final:app" 2>/dev/null || true
    
    # Get PIDs of processes on the port
    local pids=$(lsof -ti :$port 2>/dev/null || true)
    
    if [ -n "$pids" ]; then
        for pid in $pids; do
            log_message "   Killing process $pid on port $port"
            kill -TERM $pid 2>/dev/null || true
        done
        sleep 2
        
        # Force kill if still running
        for pid in $pids; do
            if kill -0 $pid 2>/dev/null; then
                log_message "   Force killing process $pid"
                kill -KILL $pid 2>/dev/null || true
            fi
        done
    else
        log_message "   No process found on port $port"
    fi
}

# Stop any existing process
kill_port_process 8000

# Wait for clean shutdown
log_message "⏳ Waiting for clean shutdown..."
sleep 3

# Change to app directory
cd "$APP_DIR" || {
    log_message "❌ Failed to change to application directory: $APP_DIR"
    exit 1
}

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    log_message "❌ Virtual environment not found!"
    log_message "🔧 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    log_message "✅ Virtual environment created and dependencies installed"
else
    source venv/bin/activate
fi

# Verify Python environment
log_message "🔍 Python environment check:"
log_message "   Python: $(which python)"
log_message "   Pip: $(which pip)"
log_message "   Uvicorn: $(which uvicorn || echo 'Not found - will install')"

# Install uvicorn if not present
if ! command -v uvicorn &> /dev/null; then
    log_message "📦 Installing uvicorn..."
    pip install uvicorn[standard]
fi

# Check for .env file
if [ ! -f ".env" ]; then
    log_message "⚠️  Warning: .env file not found. Application may not work correctly."
    log_message "   Please create .env file with required configuration."
fi

# Run dependency check
log_message ""
log_message "🛡️ CHECKING DEPENDENCIES..."
log_message "============================="

# Run the dependency management system
python -c "
import sys
sys.path.insert(0, '.')

try:
    from utils.dependency_manager import print_startup_report, can_start_application, dependency_manager
    
    # Print comprehensive startup report
    can_start = print_startup_report()
    
    if not can_start:
        print('')
        print('💥 CANNOT START APPLICATION')
        print('===========================')
        print('Critical dependencies are missing. Application cannot start.')
        print('')
        print('🔧 AUTO-INSTALLATION SCRIPT:')
        print('=============================')
        script = dependency_manager.get_installation_script()
        print(script)
        print('')
        
        # Ask user if they want to auto-install missing critical dependencies
        import subprocess
        response = input('❓ Would you like to auto-install missing critical dependencies? (y/n): ').strip().lower()
        
        if response in ['y', 'yes']:
            print('📦 Installing missing dependencies...')
            
            # Get missing critical dependencies
            missing_critical = dependency_manager._get_missing_critical()
            for dep_name in missing_critical:
                dep_info = next(d for d in dependency_manager.dependency_map.values() if d.name == dep_name)
                print(f'Installing {dep_name}...')
                try:
                    result = subprocess.run(dep_info.install_command.split(), check=True, capture_output=True, text=True)
                    print(f'✅ {dep_name} installed successfully')
                except subprocess.CalledProcessError as e:
                    print(f'❌ Failed to install {dep_name}: {e}')
            
            # Re-check dependencies after installation
            print('')
            print('🔄 RE-CHECKING DEPENDENCIES AFTER INSTALLATION...')
            print('=============================================')
            
            # Reload the dependency manager
            from importlib import reload
            import utils.dependency_manager
            reload(utils.dependency_manager)
            from utils.dependency_manager import print_startup_report, can_start_application
            
            can_start = print_startup_report()
            
            if not can_start:
                print('❌ Still missing critical dependencies. Cannot start application.')
                sys.exit(1)
        else:
            print('❌ User chose not to install dependencies. Cannot start application.')
            sys.exit(1)
    
    print('✅ All critical dependencies available. Ready to start application!')
    
except ImportError as e:
    print('⚠️ Dependency management system not available.')
    print(f'   Error: {e}')
    print('   Proceeding with basic startup (may encounter issues)...')
except Exception as e:
    print(f'⚠️ Error during dependency check: {e}')
    print('   Proceeding with basic startup...')
"

# Check if dependency check passed
DEPENDENCY_CHECK=$?
if [ $DEPENDENCY_CHECK -ne 0 ]; then
    log_message ""
    log_message "❌ Dependency check failed. Cannot start application."
    log_message "   Please resolve dependency issues and try again."
    exit 1
fi

log_message ""
log_message "🚀 Starting Lead Router Pro in Development Mode..."
log_message "   - Server will be available at http://localhost:8000"
log_message "   - Admin dashboard: http://localhost:8000/dashboard"
log_message "   - API docs: http://localhost:8000/docs"
log_message "   - Health check: http://localhost:8000/health"
log_message "   - Auto-reload is ENABLED (changes will restart server)"
log_message "   - Press Ctrl+C to stop"
log_message ""

# Function to run server with auto-restart on crash
run_with_autorestart() {
    local restart_count=0
    local max_restart_attempts=10
    local restart_delay=5
    
    while [ "$AUTO_RESTART" = "true" ]; do
        log_message "🔥 Starting server (attempt $((restart_count + 1)))..."
        
        # Create a wrapper script for better process management
        cat > /tmp/leadrouter_dev_runner.sh << 'EOF'
#!/bin/bash
cd /root/Lead-Router-Pro
source venv/bin/activate
exec python -m uvicorn main_working_final:app --host 0.0.0.0 --port 8000 --log-level debug --reload
EOF
        chmod +x /tmp/leadrouter_dev_runner.sh
        
        # Start the server and capture exit code
        /tmp/leadrouter_dev_runner.sh 2>&1 | tee -a "$LOG_FILE"
        EXIT_CODE=${PIPESTATUS[0]}
        
        # Clean up
        rm -f /tmp/leadrouter_dev_runner.sh
        
        # Check exit code
        if [ $EXIT_CODE -eq 0 ]; then
            log_message "✅ Server stopped normally (exit code 0)"
            break
        elif [ $EXIT_CODE -eq 130 ]; then
            log_message "🛑 Server stopped by user (Ctrl+C)"
            break
        else
            restart_count=$((restart_count + 1))
            log_message "❌ Server crashed with exit code: $EXIT_CODE"
            
            if [ $restart_count -ge $max_restart_attempts ]; then
                log_message "⚠️ Maximum restart attempts ($max_restart_attempts) reached!"
                log_message "   Server appears to be in a crash loop."
                log_message "   Please check the logs and fix the issue."
                break
            fi
            
            log_message "🔄 Auto-restarting in $restart_delay seconds..."
            log_message "   (Press Ctrl+C to cancel auto-restart)"
            
            # Allow interruption during wait
            for i in $(seq $restart_delay -1 1); do
                echo -ne "\r   Restarting in $i seconds... "
                sleep 1
            done
            echo ""
        fi
    done
}

# Start the application in dev mode with auto-restart protection
log_message "🔥 Starting with auto-reload and crash protection (development mode)..."
log_message "📋 Logs are being written to: $LOG_FILE"
log_message "   - Auto-restart on crash: $AUTO_RESTART"
log_message "   - To disable auto-restart: export AUTO_RESTART=false"
log_message ""

# Run with auto-restart protection
if [ "$AUTO_RESTART" = "true" ]; then
    run_with_autorestart
else
    # Single run without auto-restart
    cd /root/Lead-Router-Pro
    source venv/bin/activate
    exec python -m uvicorn main_working_final:app --host 0.0.0.0 --port 8000 --log-level debug --reload 2>&1 | tee -a "$LOG_FILE"
fi

# If we get here, the server was stopped
log_message ""
log_message "🛑 Development server stopped."
log_message "   To restart, run this script again."