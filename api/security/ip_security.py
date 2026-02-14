# api/security/ip_security.py

import time
import logging
from typing import Dict, List, Optional, Set
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json
import os
from threading import Lock
from fastapi import Request, HTTPException
from fastapi.responses import Response

logger = logging.getLogger(__name__)
# Prefer path beside DB so same volume/permissions apply in Docker
_SECURITY_DIR = os.getenv("SECURITY_DATA_DIR", "/app/data/security")
SECURITY_FILE = os.getenv("SECURITY_FILE", os.path.join(_SECURITY_DIR, "security_data.json"))

class IPSecurityManager:
    """
    Advanced IP-based security manager with rate limiting and automatic blocking
    """
    
    def __init__(self):
        # Rate limiting configuration
        self.rate_limit_window = 60  # seconds
        self.max_requests_per_window = 120  # requests per minute per IP (increased for dashboard)
        
        # 404 blocking configuration
        self.max_404_errors = 5  # consecutive 404s before blocking
        self.block_duration = 3600  # 1 hour in seconds
        
        # Suspicious activity thresholds
        self.max_errors_per_window = 10  # any errors per minute
        self.suspicious_block_duration = 300  # 5 minutes for suspicious activity
        
        # Data structures with thread safety
        self._lock = Lock()
        self._request_counts = defaultdict(deque)  # IP -> deque of timestamps
        self._error_counts = defaultdict(lambda: {"404": deque(), "errors": deque()})
        self._blocked_ips = {}  # IP -> {"reason": str, "blocked_until": timestamp, "blocked_at": timestamp}
        self._whitelist = set()  # IPs that should never be blocked
        self._trusted_networks = set()  # CIDR ranges for trusted networks
        
        # Load persistent data
        self._load_persistent_data()
        
        # Add DocksidePros.com server IP to whitelist
        self.add_to_whitelist("34.174.15.163")
        
        # Add requested IP to whitelist
        self.add_to_whitelist("34.174.132.172")
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "ips_blocked": 0,
            "attacks_prevented": 0
        }
    
    def _load_persistent_data(self):
        """Load blocked IPs and whitelist from persistent storage"""
        load_paths = [SECURITY_FILE, os.path.join("/tmp", "security_data.json")]
        for path in load_paths:
            try:
                if os.path.exists(path):
                    with open(path, "r") as f:
                        data = json.load(f)
                    current_time = time.time()
                    for ip, block_info in data.get("blocked_ips", {}).items():
                        if block_info.get("blocked_until", 0) > current_time:
                            self._blocked_ips[ip] = block_info
                    self._whitelist = set(data.get("whitelist", []))
                    self._trusted_networks = set(data.get("trusted_networks", []))
                    logger.info("🔒 Loaded %s blocked IPs, %s whitelisted IPs from %s",
                                len(self._blocked_ips), len(self._whitelist), path)
                    return
            except Exception as e:
                logger.debug("Could not load security data from %s: %s", path, e)
                continue
    
    def _save_persistent_data(self):
        """Save blocked IPs and whitelist to persistent storage"""
        data = {
            "blocked_ips": self._blocked_ips,
            "whitelist": list(self._whitelist),
            "trusted_networks": list(self._trusted_networks),
            "saved_at": time.time()
        }
        for path in [SECURITY_FILE, os.path.join("/tmp", "security_data.json")]:
            try:
                d = os.path.dirname(path)
                if d:
                    os.makedirs(d, exist_ok=True)
                with open(path, "w") as f:
                    json.dump(data, f, indent=2)
                return
            except (OSError, PermissionError) as e:
                if path == SECURITY_FILE:
                    logger.debug("Could not save security data to %s: %s; will try fallback", path, e)
                else:
                    logger.warning("Could not save security data: %s", e)
                continue
        logger.error("❌ Could not save security data to any path")
    
    def get_client_ip(self, request: Request) -> str:
        """Extract the real client IP from request, handling proxies"""
        # Check for common proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain (original client)
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        forwarded = request.headers.get("Forwarded")
        if forwarded:
            # Parse Forwarded header: for=192.0.2.60;proto=http;by=203.0.113.43
            for part in forwarded.split(";"):
                if part.strip().startswith("for="):
                    return part.split("=")[1].strip()
        
        # Fall back to direct connection
        return request.client.host if request.client else "unknown"
    
    def is_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted"""
        if ip in self._whitelist:
            return True
        
        # Check against trusted networks (basic CIDR support)
        for network in self._trusted_networks:
            if ip.startswith(network.split("/")[0]):  # Simple prefix match
                return True
        
        # Always whitelist localhost
        if ip in ["127.0.0.1", "::1", "localhost"]:
            return True
        
        return False
    
    def is_blocked(self, ip: str) -> Dict[str, any]:
        """Check if IP is currently blocked"""
        current_time = time.time()
        
        if ip in self._blocked_ips:
            block_info = self._blocked_ips[ip]
            
            # Check if block has expired
            if current_time > block_info.get("blocked_until", 0):
                # Block expired, remove it
                del self._blocked_ips[ip]
                self._save_persistent_data()
                return {"blocked": False}
            
            # Still blocked
            return {
                "blocked": True,
                "reason": block_info.get("reason", "Unknown"),
                "blocked_until": block_info.get("blocked_until"),
                "remaining_seconds": int(block_info.get("blocked_until", 0) - current_time)
            }
        
        return {"blocked": False}
    
    def check_rate_limit(self, ip: str) -> Dict[str, any]:
        """Check if IP is within rate limits"""
        current_time = time.time()
        window_start = current_time - self.rate_limit_window
        
        with self._lock:
            # Clean old entries
            while self._request_counts[ip] and self._request_counts[ip][0] < window_start:
                self._request_counts[ip].popleft()
            
            # Check current count
            current_count = len(self._request_counts[ip])
            
            if current_count >= self.max_requests_per_window:
                return {
                    "allowed": False,
                    "reason": "Rate limit exceeded",
                    "current_count": current_count,
                    "limit": self.max_requests_per_window,
                    "window_seconds": self.rate_limit_window,
                    "retry_after": int(self.rate_limit_window - (current_time - self._request_counts[ip][0]))
                }
            
            # Add current request
            self._request_counts[ip].append(current_time)
            
            return {
                "allowed": True,
                "current_count": current_count + 1,
                "limit": self.max_requests_per_window,
                "remaining": self.max_requests_per_window - current_count - 1
            }
    
    def record_error(self, ip: str, status_code: int):
        """Record an error for IP and check for blocking conditions"""
        if self.is_whitelisted(ip):
            return
        
        current_time = time.time()
        window_start = current_time - self.rate_limit_window
        
        with self._lock:
            # Record 404 errors separately
            if status_code == 404:
                self._error_counts[ip]["404"].append(current_time)
                
                # Clean old 404 entries
                while (self._error_counts[ip]["404"] and 
                       self._error_counts[ip]["404"][0] < window_start):
                    self._error_counts[ip]["404"].popleft()
                
                # Check for consecutive 404s (within a reasonable time window)
                recent_404s = len(self._error_counts[ip]["404"])
                if recent_404s >= self.max_404_errors:
                    self._block_ip(ip, f"Consecutive 404 errors ({recent_404s})", self.block_duration)
                    logger.warning(f"🚫 Blocked IP {ip} for {recent_404s} consecutive 404 errors")
                    return
            
            # Record all errors
            if status_code >= 400:
                self._error_counts[ip]["errors"].append(current_time)
                
                # Clean old error entries
                while (self._error_counts[ip]["errors"] and 
                       self._error_counts[ip]["errors"][0] < window_start):
                    self._error_counts[ip]["errors"].popleft()
                
                # Check for excessive errors
                total_errors = len(self._error_counts[ip]["errors"])
                if total_errors >= self.max_errors_per_window:
                    self._block_ip(ip, f"Excessive errors ({total_errors} in {self.rate_limit_window}s)", 
                                 self.suspicious_block_duration)
                    logger.warning(f"🚫 Blocked IP {ip} for excessive errors ({total_errors})")
                    return
    
    def _block_ip(self, ip: str, reason: str, duration: int):
        """Block an IP address"""
        if self.is_whitelisted(ip):
            logger.info(f"⚪ Skipping block for whitelisted IP: {ip}")
            return
        
        current_time = time.time()
        block_until = current_time + duration
        
        self._blocked_ips[ip] = {
            "reason": reason,
            "blocked_at": current_time,
            "blocked_until": block_until,
            "duration": duration
        }
        
        self.stats["ips_blocked"] += 1
        self.stats["attacks_prevented"] += 1
        
        # Save to persistent storage
        self._save_persistent_data()
        
        logger.warning(f"🚫 BLOCKED IP: {ip} for {duration}s - Reason: {reason}")
    
    def add_to_whitelist(self, ip: str):
        """Add IP to whitelist"""
        self._whitelist.add(ip)
        self._save_persistent_data()
        logger.info(f"⚪ Added IP to whitelist: {ip}")
    
    def remove_from_whitelist(self, ip: str):
        """Remove IP from whitelist"""
        self._whitelist.discard(ip)
        self._save_persistent_data()
        logger.info(f"🔴 Removed IP from whitelist: {ip}")
    
    def unblock_ip(self, ip: str):
        """Manually unblock an IP"""
        if ip in self._blocked_ips:
            del self._blocked_ips[ip]
            self._save_persistent_data()
            logger.info(f"✅ Manually unblocked IP: {ip}")
            return True
        return False
    
    def get_security_stats(self) -> Dict:
        """Get security statistics"""
        current_time = time.time()
        
        # Count currently blocked IPs
        active_blocks = sum(1 for block_info in self._blocked_ips.values() 
                          if block_info.get("blocked_until", 0) > current_time)
        
        return {
            **self.stats,
            "currently_blocked_ips": active_blocks,
            "total_known_ips": len(self._request_counts),
            "whitelist_size": len(self._whitelist),
            "trusted_networks": len(self._trusted_networks),
            "rate_limit_window": self.rate_limit_window,
            "max_requests_per_window": self.max_requests_per_window,
            "max_404_errors": self.max_404_errors,
            "block_duration": self.block_duration
        }
    
    def get_blocked_ips(self) -> Dict:
        """Get list of currently blocked IPs"""
        current_time = time.time()
        active_blocks = {}
        
        for ip, block_info in self._blocked_ips.items():
            if block_info.get("blocked_until", 0) > current_time:
                active_blocks[ip] = {
                    **block_info,
                    "remaining_seconds": int(block_info.get("blocked_until", 0) - current_time),
                    "blocked_at_formatted": datetime.fromtimestamp(block_info.get("blocked_at", 0)).isoformat(),
                    "blocked_until_formatted": datetime.fromtimestamp(block_info.get("blocked_until", 0)).isoformat()
                }
        
        return active_blocks
    
    def cleanup_expired_data(self):
        """Clean up expired blocks and old tracking data"""
        current_time = time.time()
        cleanup_threshold = current_time - (self.rate_limit_window * 10)  # Keep 10 windows of data
        
        with self._lock:
            # Remove expired blocks
            expired_ips = [ip for ip, block_info in self._blocked_ips.items() 
                          if block_info.get("blocked_until", 0) <= current_time]
            
            for ip in expired_ips:
                del self._blocked_ips[ip]
            
            # Clean old request tracking data
            for ip in list(self._request_counts.keys()):
                while (self._request_counts[ip] and 
                       self._request_counts[ip][0] < cleanup_threshold):
                    self._request_counts[ip].popleft()
                
                # Remove empty entries
                if not self._request_counts[ip]:
                    del self._request_counts[ip]
            
            # Clean old error tracking data
            for ip in list(self._error_counts.keys()):
                for error_type in ["404", "errors"]:
                    while (self._error_counts[ip][error_type] and 
                           self._error_counts[ip][error_type][0] < cleanup_threshold):
                        self._error_counts[ip][error_type].popleft()
                
                # Remove empty entries
                if (not self._error_counts[ip]["404"] and 
                    not self._error_counts[ip]["errors"]):
                    del self._error_counts[ip]
        
        if expired_ips:
            self._save_persistent_data()
            logger.info(f"🧹 Cleaned up {len(expired_ips)} expired IP blocks")

# Global security manager instance
security_manager = IPSecurityManager()
