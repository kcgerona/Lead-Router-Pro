# api/security/middleware.py

import time
import logging
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from api.security.ip_security import security_manager

logger = logging.getLogger(__name__)

class IPSecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware that provides IP-based security for all endpoints
    """
    
    def __init__(self, app, enable_silent_blocking: bool = True):
        super().__init__(app)
        self.enable_silent_blocking = enable_silent_blocking
        
    async def dispatch(self, request: Request, call_next):
        """Process request through security checks"""
        start_time = time.time()
        
        # Get client IP
        client_ip = security_manager.get_client_ip(request)
        
        # Update request stats
        security_manager.stats["total_requests"] += 1
        
        # Skip security for health checks and admin endpoints from localhost
        if self._should_skip_security(request, client_ip):
            response = await call_next(request)
            return response
        
        # Check Elementor endpoint whitelist
        if not self._check_elementor_whitelist(request, client_ip):
            security_manager.stats["blocked_requests"] += 1
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Access denied",
                    "message": "Only whitelisted IPs can access Elementor webhook endpoints"
                }
            )
        
        # Check if IP is blocked
        block_status = security_manager.is_blocked(client_ip)
        if block_status["blocked"]:
            security_manager.stats["blocked_requests"] += 1
            
            # Log the blocked attempt
            logger.warning(f"🚫 Blocked request from {client_ip} to {request.url.path} - {block_status['reason']}")
            
            if self.enable_silent_blocking:
                # Return no response - makes it appear server is down
                return StarletteResponse(content="", status_code=444)  # Nginx-style "No Response"
            else:
                # Return explicit block message
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "IP temporarily blocked",
                        "reason": block_status["reason"],
                        "retry_after": block_status["remaining_seconds"]
                    },
                    headers={"Retry-After": str(block_status["remaining_seconds"])}
                )
        
        # Check rate limiting (only for non-whitelisted IPs)
        if not security_manager.is_whitelisted(client_ip):
            rate_limit_result = security_manager.check_rate_limit(client_ip)
            
            if not rate_limit_result["allowed"]:
                # Log rate limit violation
                logger.warning(f"⚡ Rate limit exceeded for {client_ip}: {rate_limit_result['current_count']}/{rate_limit_result['limit']}")
                
                # Record as suspicious activity but don't block immediately for rate limiting
                security_manager.record_error(client_ip, 429)
                
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "limit": rate_limit_result["limit"],
                        "window_seconds": rate_limit_result["window_seconds"],
                        "retry_after": rate_limit_result["retry_after"]
                    },
                    headers={
                        "X-RateLimit-Limit": str(rate_limit_result["limit"]),
                        "X-RateLimit-Window": str(rate_limit_result["window_seconds"]),
                        "Retry-After": str(rate_limit_result["retry_after"])
                    }
                )
        
        # Process the request
        try:
            response = await call_next(request)
            
            # Record error if status code indicates an error
            if response.status_code >= 400:
                security_manager.record_error(client_ip, response.status_code)
                
                # Special logging for 404s
                if response.status_code == 404:
                    logger.info(f"📄 404 from {client_ip} for {request.url.path}")
            
            # Add security headers
            self._add_security_headers(response, client_ip)
            
            # Log processing time for monitoring
            processing_time = time.time() - start_time
            if processing_time > 5.0:  # Log slow requests
                logger.warning(f"🐌 Slow request from {client_ip}: {processing_time:.2f}s for {request.url.path}")
            
            return response
            
        except Exception as e:
            # Log exceptions and record as server errors
            logger.error(f"💥 Exception processing request from {client_ip}: {e}")
            security_manager.record_error(client_ip, 500)
            
            # Re-raise the exception to be handled by FastAPI
            raise
    
    def _should_skip_security(self, request: Request, client_ip: str) -> bool:
        """Determine if security checks should be skipped for this request"""
        path = request.url.path
        
        # Skip for localhost accessing admin/health endpoints
        if client_ip in ["127.0.0.1", "::1", "localhost"]:
            if any(path.startswith(prefix) for prefix in ["/api/v1/admin", "/api/v1/auth", "/health", "/docs", "/openapi.json"]):
                return True
        
        # Skip for whitelisted IPs accessing health checks
        if security_manager.is_whitelisted(client_ip) and path in ["/health", "/api/v1/webhooks/health"]:
            return True
        
        # Skip IP security for GHL webhook endpoints - relies on X-Webhook-API-Key header validation instead
        # This allows GoHighLevel webhooks from any AWS IP to reach the endpoint's own authorization validation
        if path in ["/api/v1/webhooks/ghl/vendor-user-creation", "/api/v1/webhooks/ghl/process-new-contact"]:
            return True
        
        return False
    
    def _check_elementor_whitelist(self, request: Request, client_ip: str) -> bool:
        """Check if IP is allowed to access Elementor endpoints"""
        path = request.url.path
        
        # Check if this is an Elementor webhook endpoint
        if path.startswith("/api/v1/webhooks/elementor/"):
            
            # EXEMPTION: Allow public access to vendor application endpoints
            vendor_application_paths = [
                "/api/v1/webhooks/elementor/vendor_application",
                "/api/v1/webhooks/elementor/vendor_application_general",
                "/api/v1/webhooks/elementor/vendor_application_v2"
            ]
            
            if path in vendor_application_paths:
                # Allow public access to vendor applications - no IP restriction
                logger.info(f"✅ Allowing public access to vendor application endpoint: {path} from {client_ip}")
                return True
            
            # For all other Elementor endpoints, require IP whitelisting
            if not security_manager.is_whitelisted(client_ip):
                logger.warning(f"🚫 Blocked non-whitelisted IP {client_ip} from accessing Elementor endpoint: {path}")
                return False
        
        return True
    
    def _add_security_headers(self, response: Response, client_ip: str):
        """Add security-related headers to response"""
        
        # Add rate limit headers for tracking
        rate_limit_result = security_manager.check_rate_limit(client_ip)
        if "remaining" in rate_limit_result:
            response.headers["X-RateLimit-Remaining"] = str(rate_limit_result["remaining"])
            response.headers["X-RateLimit-Limit"] = str(rate_limit_result["limit"])
        
        # Add general security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Allow iframe embedding from docksidepros.com
        response.headers["X-Frame-Options"] = "ALLOW-FROM https://docksidepros.com"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'self' https://docksidepros.com https://*.docksidepros.com"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Don't add HSTS for local development
        if not client_ip.startswith("127.0.0.1"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"


class SecurityCleanupMiddleware(BaseHTTPMiddleware):
    """
    Lightweight middleware to periodically clean up expired security data
    """
    
    def __init__(self, app, cleanup_interval: int = 3600):  # Default 1 hour
        super().__init__(app)
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next):
        """Check if cleanup is needed before processing request"""
        current_time = time.time()
        
        # Perform cleanup if enough time has passed
        if current_time - self.last_cleanup > self.cleanup_interval:
            try:
                security_manager.cleanup_expired_data()
                self.last_cleanup = current_time
                logger.info("🧹 Performed security data cleanup")
            except Exception as e:
                logger.error(f"❌ Error during security cleanup: {e}")
        
        # Continue with normal request processing
        response = await call_next(request)
        return response
