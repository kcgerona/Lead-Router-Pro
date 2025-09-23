#!/usr/bin/env python3
"""
Lead Router Pro - Health Monitoring System
Monitors application health and can send alerts when issues are detected
"""

import asyncio
import aiohttp
import logging
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/Lead-Router-Pro/health_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HealthMonitor:
    """Monitors the health of Lead Router Pro application"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.health_endpoint = f"{self.base_url}/health"
        self.last_alert_time = None
        self.alert_cooldown = timedelta(minutes=15)  # Don't spam alerts
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3
        
        # Email configuration (optional)
        self.smtp_enabled = bool(os.getenv('SMTP_HOST'))
        self.smtp_host = os.getenv('SMTP_HOST', '')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.alert_email = os.getenv('ALERT_EMAIL', '')
        
        # Health metrics
        self.metrics = {
            'uptime_start': datetime.now(),
            'total_checks': 0,
            'successful_checks': 0,
            'failed_checks': 0,
            'last_check': None,
            'last_success': None,
            'last_failure': None,
            'current_status': 'unknown'
        }
    
    async def check_health(self) -> bool:
        """Check if the application is healthy"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.health_endpoint,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    self.metrics['total_checks'] += 1
                    self.metrics['last_check'] = datetime.now()
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check detailed health status
                        if data.get('status') == 'healthy':
                            self.consecutive_failures = 0
                            self.metrics['successful_checks'] += 1
                            self.metrics['last_success'] = datetime.now()
                            self.metrics['current_status'] = 'healthy'
                            
                            # Log success periodically
                            if self.metrics['total_checks'] % 10 == 0:
                                logger.info(f"✅ Health check #{self.metrics['total_checks']}: System healthy")
                            
                            return True
                    
                    # Non-200 response
                    self.handle_failure(f"HTTP {response.status}")
                    return False
                    
        except asyncio.TimeoutError:
            self.handle_failure("Timeout")
            return False
        except aiohttp.ClientError as e:
            self.handle_failure(f"Connection error: {e}")
            return False
        except Exception as e:
            self.handle_failure(f"Unexpected error: {e}")
            return False
    
    def handle_failure(self, reason: str):
        """Handle health check failure"""
        self.consecutive_failures += 1
        self.metrics['failed_checks'] += 1
        self.metrics['last_failure'] = datetime.now()
        self.metrics['current_status'] = 'unhealthy'
        
        logger.warning(f"⚠️ Health check failed: {reason} (failure #{self.consecutive_failures})")
        
        # Send alert if threshold reached
        if self.consecutive_failures >= self.max_consecutive_failures:
            self.send_alert(f"Lead Router Pro is DOWN - {reason}")
    
    def send_alert(self, message: str):
        """Send alert notification"""
        now = datetime.now()
        
        # Check cooldown period
        if self.last_alert_time and (now - self.last_alert_time) < self.alert_cooldown:
            logger.info("Alert suppressed due to cooldown period")
            return
        
        self.last_alert_time = now
        
        # Log critical alert
        logger.critical(f"🚨 ALERT: {message}")
        
        # Send email alert if configured
        if self.smtp_enabled and self.alert_email:
            try:
                self.send_email_alert(message)
            except Exception as e:
                logger.error(f"Failed to send email alert: {e}")
    
    def send_email_alert(self, message: str):
        """Send email alert"""
        if not all([self.smtp_host, self.smtp_username, self.smtp_password, self.alert_email]):
            return
        
        msg = MIMEMultipart()
        msg['From'] = self.smtp_username
        msg['To'] = self.alert_email
        msg['Subject'] = '🚨 Lead Router Pro Health Alert'
        
        body = f"""
Lead Router Pro Health Alert
=============================

{message}

Metrics:
- Total Checks: {self.metrics['total_checks']}
- Successful: {self.metrics['successful_checks']}
- Failed: {self.metrics['failed_checks']}
- Current Status: {self.metrics['current_status']}
- Last Success: {self.metrics['last_success']}
- Last Failure: {self.metrics['last_failure']}
- Consecutive Failures: {self.consecutive_failures}

Please check the application immediately.

Server: https://dockside.life
Dashboard: https://dockside.life/admin
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
        
        logger.info(f"📧 Email alert sent to {self.alert_email}")
    
    async def monitor_loop(self, interval: int = 30):
        """Main monitoring loop"""
        logger.info("🔍 Starting health monitoring...")
        logger.info(f"   - Check interval: {interval} seconds")
        logger.info(f"   - Alert threshold: {self.max_consecutive_failures} failures")
        logger.info(f"   - Email alerts: {'Enabled' if self.smtp_enabled else 'Disabled'}")
        
        while True:
            try:
                is_healthy = await self.check_health()
                
                # Log status changes
                if is_healthy and self.consecutive_failures == 0 and self.metrics['failed_checks'] > 0:
                    logger.info("✅ Service recovered and is now healthy")
                    if self.smtp_enabled:
                        self.send_alert("Lead Router Pro has RECOVERED and is now healthy")
                
                # Save metrics periodically
                if self.metrics['total_checks'] % 100 == 0:
                    self.save_metrics()
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
            
            await asyncio.sleep(interval)
    
    def save_metrics(self):
        """Save metrics to file"""
        metrics_file = Path('/root/Lead-Router-Pro/health_metrics.json')
        try:
            # Convert datetime objects to strings
            save_metrics = self.metrics.copy()
            for key in ['uptime_start', 'last_check', 'last_success', 'last_failure']:
                if save_metrics.get(key):
                    save_metrics[key] = save_metrics[key].isoformat()
            
            with open(metrics_file, 'w') as f:
                json.dump(save_metrics, f, indent=2)
            
            logger.info(f"📊 Metrics saved: {self.metrics['total_checks']} checks, "
                       f"{self.metrics['successful_checks']} successful, "
                       f"{self.metrics['failed_checks']} failed")
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

async def main():
    """Main entry point"""
    monitor = HealthMonitor()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--once':
            # Single health check
            is_healthy = await monitor.check_health()
            print(f"Health Status: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")
            sys.exit(0 if is_healthy else 1)
        elif sys.argv[1] == '--interval':
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            await monitor.monitor_loop(interval)
    else:
        # Default: continuous monitoring every 30 seconds
        await monitor.monitor_loop(30)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Health monitor stopped by user")
    except Exception as e:
        logger.error(f"❌ Health monitor crashed: {e}")
        sys.exit(1)