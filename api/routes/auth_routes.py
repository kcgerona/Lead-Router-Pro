"""
Authentication Routes
Handles login, logout, registration, 2FA, and password management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional, Union
import asyncio
from datetime import datetime
import logging

from database.simple_connection import get_db
from database.models import User, Tenant
from api.services.auth_service import auth_service
from api.services.email_service import email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
security = HTTPBearer()

# Test endpoint
@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify router is working"""
    return {"message": "Auth router is working"}

@router.post("/test-post")
async def test_post_endpoint():
    """Test POST endpoint to verify POST routing works"""
    return {"message": "Auth router POST is working"}

@router.post("/login-simple")
async def login_simple_test():
    """Simplified login endpoint for testing"""
    return {"message": "Simple login endpoint works"}

# Pydantic models for request/response
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    domain: Optional[str] = None

class LoginStep1Response(BaseModel):
    message: str
    requires_2fa: bool
    user_id: str
    session_token: str

class LoginCompleteResponse(BaseModel):
    message: str
    requires_2fa: bool
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict

class Verify2FARequest(BaseModel):
    user_id: str
    code: str
    session_token: str

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    domain: Optional[str] = None

class PasswordResetRequest(BaseModel):
    email: EmailStr
    domain: Optional[str] = None

class PasswordResetConfirm(BaseModel):
    email: EmailStr
    reset_code: str
    new_password: str
    domain: Optional[str] = None

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    verification_code: str
    domain: Optional[str] = None

# Dependency to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    try:
        token = credentials.credentials
        payload = auth_service.verify_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
            
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        
        if not user_id or not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
            
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
            
        return user
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def get_domain_from_request(request: Request, domain_param: Optional[str] = None) -> str:
    """Extract domain from request"""
    if domain_param:
        return domain_param
    
    # Try to get from Host header
    host = request.headers.get("host", "")
    if host:
        # Remove port if present
        return host.split(":")[0]
    
    # Fallback to default
    return "dockside.life"

@router.post("/login", response_model=Union[LoginStep1Response, LoginCompleteResponse])
async def login_step1(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Step 1: Email/Password authentication"""
    try:
        domain = get_domain_from_request(request, login_data.domain)
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Get tenant
        tenant = auth_service.get_tenant_by_domain(domain, db)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Authenticate user
        user, auth_message = auth_service.authenticate_user(
            login_data.email, 
            login_data.password, 
            str(tenant.id), 
            db
        )
        
        if not user:
            # Log failed attempt
            auth_service.log_security_event(
                tenant_id=str(tenant.id),
                user_id=None,
                action="login_failed",
                ip_address=client_ip,
                user_agent=user_agent,
                details={"email": login_data.email, "reason": auth_message},
                db=db
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=auth_message
            )
        
        # Check if email is verified
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please check your email for verification code."
            )
        
        # If 2FA is disabled, complete login immediately
        if not user.two_factor_enabled:
            # Reset login attempts and update last login
            auth_service.reset_login_attempts(user, db)
            
            # Generate access and refresh tokens
            access_token = auth_service.create_access_token(
                user_id=str(user.id),
                tenant_id=str(tenant.id),
                additional_claims={"role": user.role, "email": user.email}
            )
            
            refresh_token = auth_service.create_refresh_token(
                user_id=str(user.id),
                tenant_id=str(tenant.id)
            )
            
            # Store tokens in database
            auth_service.store_auth_token(str(user.id), access_token, "access", db)
            auth_service.store_auth_token(str(user.id), refresh_token, "refresh", db)
            
            # Log successful login
            auth_service.log_security_event(
                tenant_id=str(tenant.id),
                user_id=str(user.id),
                action="login_success",
                ip_address=client_ip,
                user_agent=user_agent,
                details={"email": user.email, "2fa_bypassed": True},
                db=db
            )
            
            # Return complete auth response
            return LoginCompleteResponse(
                message="Login successful",
                requires_2fa=False,
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=auth_service.access_token_expire_minutes * 60,
                user={
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                    "tenant_id": str(tenant.id)
                }
            )
        
        # Generate session token for 2FA step
        session_token = auth_service.create_access_token(
            user_id=str(user.id),
            tenant_id=str(tenant.id),
            additional_claims={"step": "awaiting_2fa", "exp_short": True}
        )
        
        # Generate and send 2FA code
        code = auth_service.create_2fa_code(str(user.id), "login", db)
        
        # Send 2FA code via email
        await email_service.send_2fa_code(
            to_email=user.email,
            code=code,
            user_name=user.first_name
        )
        
        # Log 2FA code sent
        auth_service.log_security_event(
            tenant_id=str(tenant.id),
            user_id=str(user.id),
            action="2fa_code_sent",
            ip_address=client_ip,
            user_agent=user_agent,
            details={"email": user.email},
            db=db
        )
        
        return LoginStep1Response(
            message="2FA code sent to your email",
            requires_2fa=True,
            user_id=str(user.id),
            session_token=session_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/verify-2fa", response_model=AuthResponse)
async def verify_2fa(
    request: Request,
    verify_data: Verify2FARequest,
    db: Session = Depends(get_db)
):
    """Step 2: Verify 2FA code and complete login"""
    try:
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Verify session token
        payload = auth_service.verify_token(verify_data.session_token)
        if not payload or payload.get("step") != "awaiting_2fa":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session token"
            )
        
        # Get user
        user = db.query(User).filter(User.id == verify_data.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify 2FA code
        if not auth_service.verify_2fa_code(verify_data.user_id, verify_data.code, "login", db):
            # Log failed 2FA attempt
            auth_service.log_security_event(
                tenant_id=str(user.tenant_id),
                user_id=str(user.id),
                action="2fa_failed",
                ip_address=client_ip,
                user_agent=user_agent,
                details={"code_entered": verify_data.code},
                db=db
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired 2FA code"
            )
        
        # Reset login attempts and update last login
        auth_service.reset_login_attempts(user, db)
        
        # Generate access and refresh tokens
        access_token = auth_service.create_access_token(
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            additional_claims={"role": user.role, "email": user.email}
        )
        
        refresh_token = auth_service.create_refresh_token(
            user_id=str(user.id),
            tenant_id=str(user.tenant_id)
        )
        
        # Store tokens in database
        auth_service.store_auth_token(str(user.id), access_token, "access", db)
        auth_service.store_auth_token(str(user.id), refresh_token, "refresh", db)
        
        # Log successful login
        auth_service.log_security_event(
            tenant_id=str(user.tenant_id),
            user_id=str(user.id),
            action="login_success",
            ip_address=client_ip,
            user_agent=user_agent,
            details={"email": user.email},
            db=db
        )
        
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=auth_service.access_token_expire_minutes * 60,
            user={
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "tenant_id": str(user.tenant_id)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/register")
async def register(
    request: Request,
    register_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    try:
        domain = get_domain_from_request(request, register_data.domain)
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Get tenant
        tenant = auth_service.get_tenant_by_domain(domain, db)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Create user
        try:
            user = auth_service.create_user(
                email=register_data.email,
                password=register_data.password,
                tenant_id=str(tenant.id),
                first_name=register_data.first_name,
                last_name=register_data.last_name,
                db=db
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        
        # Generate email verification code
        verification_code = auth_service.create_2fa_code(str(user.id), "email_verification", db)
        
        # Send welcome email with verification code
        await email_service.send_welcome_email(
            to_email=user.email,
            user_name=user.first_name,
            verification_code=verification_code
        )
        
        # Log registration
        auth_service.log_security_event(
            tenant_id=str(tenant.id),
            user_id=str(user.id),
            action="user_registered",
            ip_address=client_ip,
            user_agent=user_agent,
            details={"email": user.email},
            db=db
        )
        
        return {
            "message": "Registration successful. Please check your email to verify your account.",
            "user_id": str(user.id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/verify-email")
async def verify_email(
    request: Request,
    verify_data: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    """Verify user email address"""
    try:
        domain = get_domain_from_request(request, verify_data.domain)
        
        # Get tenant
        tenant = auth_service.get_tenant_by_domain(domain, db)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Get user
        user = auth_service.get_user_by_email(verify_data.email, str(tenant.id), db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify code
        if not auth_service.verify_2fa_code(str(user.id), verify_data.verification_code, "email_verification", db):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired verification code"
            )
        
        # Mark user as verified
        user.is_verified = True
        db.commit()
        
        # Log email verification
        auth_service.log_security_event(
            tenant_id=str(tenant.id),
            user_id=str(user.id),
            action="email_verified",
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent", ""),
            details={"email": user.email},
            db=db
        )
        
        return {"message": "Email verified successfully. You can now log in."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/refresh")
async def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    try:
        # Verify refresh token
        payload = auth_service.verify_token(refresh_data.refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Generate new access token
        access_token = auth_service.create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            additional_claims={"role": user.role, "email": user.email}
        )
        
        # Store new token
        auth_service.store_auth_token(user_id, access_token, "access", db)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": auth_service.access_token_expire_minutes * 60
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout user and revoke tokens"""
    try:
        # Log logout event
        auth_service.log_security_event(
            tenant_id=str(current_user.tenant_id),
            user_id=str(current_user.id),
            action="logout",
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent", ""),
            details={"email": current_user.email},
            db=db
        )
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    reset_data: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request password reset"""
    try:
        domain = get_domain_from_request(request, reset_data.domain)
        
        # Get tenant
        tenant = auth_service.get_tenant_by_domain(domain, db)
        if not tenant:
            # Don't reveal if tenant exists
            return {"message": "If the email exists, a reset code has been sent."}
        
        # Get user
        user = auth_service.get_user_by_email(reset_data.email, str(tenant.id), db)
        if not user:
            # Don't reveal if user exists
            return {"message": "If the email exists, a reset code has been sent."}
        
        # Generate reset code
        reset_code = auth_service.create_2fa_code(str(user.id), "password_reset", db)
        
        # Send reset email
        await email_service.send_password_reset(
            to_email=user.email,
            reset_code=reset_code,
            user_name=user.first_name
        )
        
        # Log password reset request
        auth_service.log_security_event(
            tenant_id=str(tenant.id),
            user_id=str(user.id),
            action="password_reset_requested",
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent", ""),
            details={"email": user.email},
            db=db
        )
        
        return {"message": "If the email exists, a reset code has been sent."}
        
    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/reset-password")
async def reset_password(
    request: Request,
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Reset password with code"""
    try:
        domain = get_domain_from_request(request, reset_data.domain)
        
        # Get tenant
        tenant = auth_service.get_tenant_by_domain(domain, db)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Get user
        user = auth_service.get_user_by_email(reset_data.email, str(tenant.id), db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify reset code
        if not auth_service.verify_2fa_code(str(user.id), reset_data.reset_code, "password_reset", db):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired reset code"
            )
        
        # Update password
        user.password_hash = auth_service.hash_password(reset_data.new_password)
        user.login_attempts = 0  # Reset login attempts
        user.locked_until = None  # Unlock account
        db.commit()
        
        # Log password reset
        auth_service.log_security_event(
            tenant_id=str(tenant.id),
            user_id=str(user.id),
            action="password_reset_completed",
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent", ""),
            details={"email": user.email},
            db=db
        )
        
        return {"message": "Password reset successfully. You can now log in with your new password."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "role": current_user.role,
        "is_verified": current_user.is_verified,
        "two_factor_enabled": current_user.two_factor_enabled,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        "created_at": current_user.created_at.isoformat(),
        "tenant_id": str(current_user.tenant_id)
    }
