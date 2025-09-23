# Lead Router Pro - Server Management Guide

## 🚀 Quick Start Commands

### Production Mode (with Auto-Restart Protection)
```bash
# Start server in production mode with auto-restart on crash
./start_production.sh

# Or use systemd for system boot auto-start
sudo ./install_systemd_service.sh
```

### Development Mode (with Auto-Restart Protection)
```bash
# Start in dev mode with auto-reload and crash protection
./restart_devmode_leadrouter.sh

# Disable auto-restart if needed
export AUTO_RESTART=false
./restart_devmode_leadrouter.sh
```

### Quick Restart (Simple)
```bash
# Quick restart without monitoring
./restart_server.sh
```

## 🛡️ Auto-Restart Protection Features

### Production Mode
- **Automatic crash recovery**: Server automatically restarts if it crashes
- **Health monitoring**: Checks `/health` endpoint every 30 seconds
- **Restart limits**: Maximum 10 restart attempts to prevent infinite loops
- **Logging**: All events logged to `monitor.log`

### Development Mode
- **Auto-reload on code changes**: Using uvicorn's `--reload` flag
- **Crash protection**: Automatically restarts on unexpected exits
- **Verbose logging**: Debug level logging for troubleshooting
- **Quick iteration**: Changes detected and server restarted automatically

## 📊 Monitoring & Health Checks

### Health Monitor Script
```bash
# Single health check
python health_monitor.py --once

# Continuous monitoring (runs in background)
python health_monitor.py --interval 30 &

# View health metrics
cat health_metrics.json
```

### Manual Health Check
```bash
# Check if server is responding
curl http://localhost:8000/health

# Check specific endpoints
curl http://localhost:8000/api/v1/webhooks/health
```

## 🔧 Systemd Service Management

### Install as System Service
```bash
# Install and enable systemd service
sudo ./install_systemd_service.sh

# Service will auto-start on system boot
# Service will auto-restart on crash
```

### Manage Systemd Service
```bash
# Check status
systemctl status lead-router-pro

# Start/Stop/Restart
systemctl start lead-router-pro
systemctl stop lead-router-pro
systemctl restart lead-router-pro

# View logs
journalctl -u lead-router-pro -f

# Disable auto-start on boot
systemctl disable lead-router-pro
```

## 📝 Log Files

| File | Purpose | Location |
|------|---------|----------|
| `server.log` | Main application logs | `/root/Lead-Router-Pro/server.log` |
| `server_error.log` | Error logs only | `/root/Lead-Router-Pro/server_error.log` |
| `monitor.log` | Health monitor logs | `/root/Lead-Router-Pro/monitor.log` |
| `health_monitor.log` | Health check detailed logs | `/root/Lead-Router-Pro/health_monitor.log` |
| `devmode.log` | Development mode logs | `/var/log/leadrouter/devmode.log` |

### View Logs
```bash
# Real-time log viewing
tail -f server.log

# Last 100 lines
tail -100 server.log

# Search for errors
grep ERROR server.log
grep -i error server_error.log

# Monitor health checks
tail -f health_monitor.log
```

## 🚨 Troubleshooting

### Server Won't Start
1. Check port 8000 is free:
   ```bash
   lsof -i :8000
   # Kill process if needed
   kill -9 <PID>
   ```

2. Check environment variables:
   ```bash
   cat .env
   # Ensure all required vars are set
   ```

3. Check dependencies:
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

### Server Keeps Crashing
1. Check error logs:
   ```bash
   tail -100 server_error.log
   ```

2. Run in debug mode:
   ```bash
   source venv/bin/activate
   python -m uvicorn main_working_final:app --host 0.0.0.0 --port 8000 --log-level debug
   ```

3. Check system resources:
   ```bash
   free -h  # Memory
   df -h    # Disk space
   top      # CPU usage
   ```

### Auto-Restart Not Working
1. Check if monitoring is enabled:
   ```bash
   ps aux | grep -E "monitor|start_production"
   ```

2. Check systemd service:
   ```bash
   systemctl status lead-router-pro
   journalctl -u lead-router-pro -n 50
   ```

3. Manually restart monitoring:
   ```bash
   ./start_production.sh &
   ```

## 🔄 Recovery Procedures

### After System Reboot
If systemd service is installed:
- Server will auto-start (no action needed)

If not using systemd:
```bash
# Start production server with monitoring
./start_production.sh &
```

### After Code Updates
```bash
# For production
systemctl restart lead-router-pro

# For development
# Just save files - auto-reload will restart

# Or manually restart
./restart_server.sh
```

### After Configuration Changes
```bash
# Restart to load new .env variables
./restart_server.sh

# Or with systemd
systemctl restart lead-router-pro
```

## 🎯 Best Practices

1. **Always use production mode for live site**:
   ```bash
   ./start_production.sh
   ```

2. **Enable systemd for automatic recovery**:
   ```bash
   sudo ./install_systemd_service.sh
   ```

3. **Monitor logs regularly**:
   ```bash
   tail -f server.log
   ```

4. **Set up email alerts** (optional):
   - Add SMTP settings to `.env`
   - Add `ALERT_EMAIL` to receive notifications
   - Run health monitor: `python health_monitor.py &`

5. **Regular health checks**:
   ```bash
   # Add to crontab for regular checks
   */5 * * * * curl -s http://localhost:8000/health || /root/Lead-Router-Pro/restart_server.sh
   ```

## 📋 Environment Variables for Monitoring

Add to `.env` for email alerts:
```env
# Email alerts (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ALERT_EMAIL=admin@dockside.life
```

## 🆘 Emergency Commands

```bash
# Force kill all server processes
pkill -f "uvicorn main_working_final:app"

# Clear all logs and restart fresh
> server.log
> server_error.log
> monitor.log
./restart_server.sh

# Full system restart (nuclear option)
systemctl restart lead-router-pro
# or
./start_production.sh
```

## 📊 Status Checks

```bash
# Quick system status
curl -s http://localhost:8000/health | jq .

# Check if server is running
ps aux | grep uvicorn

# Check systemd service
systemctl status lead-router-pro

# Check port binding
netstat -tlnp | grep 8000

# Check recent activity
tail -20 server.log
```

Remember: The server now has robust auto-restart protection in both production and development modes. It will automatically recover from most crashes without manual intervention.