"""
Authentication Service
Handles user authentication, JWT tokens, password hashing, and 2FA
"""

import os
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.models import User, AuthToken, TwoFactorCode, Tenant, AuditLog
from database.simple_connection import get_db_session


class AuthService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", "fallback-secret-key")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.refresh_token_expire_days = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
        self.two_factor_code_length = int(os.getenv("TWO_FACTOR_CODE_LENGTH", "6"))
        self.two_factor_expire_minutes = int(os.getenv("TWO_FACTOR_CODE_EXPIRE_MINUTES", "10"))
        self.max_login_attempts = int(os.getenv("ACCOUNT_LOCKOUT_THRESHOLD", "5"))
        self.lockout_duration_minutes = int(os.getenv("ACCOUNT_LOCKOUT_DURATION_MINUTES", "30"))

    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        # Truncate password to 72 characters for bcrypt compatibility
        if len(plain_password) > 72:
            plain_password = plain_password[:72]
        return self.pwd_context.verify(plain_password, hashed_password)

    def generate_2fa_code(self) -> str:
        """Generate a random 2FA code"""
        return ''.join(secrets.choice(string.digits) for _ in range(self.two_factor_code_length))

    def create_access_token(self, user_id: str, tenant_id: str, additional_claims: Dict[str, Any] = None) -> str:
        """Create a JWT access token"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        if additional_claims:
            to_encode.update(additional_claims)
            
        return jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)

    def create_refresh_token(self, user_id: str, tenant_id: str) -> str:
        """Create a JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        return jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except JWTError:
            return None

    def get_tenant_by_domain(self, domain: str, db: Session) -> Optional[Tenant]:
        """Get tenant by domain"""
        return db.query(Tenant).filter(
            and_(
                Tenant.domain == domain,
                Tenant.is_active == True
            )
        ).first()

    def get_user_by_email(self, email: str, tenant_id: str, db: Session) -> Optional[User]:
        """Get user by email within tenant"""
        return db.query(User).filter(
            and_(
                User.email == email,
                User.tenant_id == tenant_id,
                User.is_active == True
            )
        ).first()

    def is_user_locked(self, user: User) -> bool:
        """Check if user account is locked"""
        if user.locked_until and user.locked_until > datetime.utcnow():
            return True
        return False

    def increment_login_attempts(self, user: User, db: Session) -> None:
        """Increment login attempts and lock account if threshold reached"""
        user.login_attempts += 1
        
        if user.login_attempts >= self.max_login_attempts:
            user.locked_until = datetime.utcnow() + timedelta(minutes=self.lockout_duration_minutes)
            
        db.commit()

    def reset_login_attempts(self, user: User, db: Session) -> None:
        """Reset login attempts on successful login"""
        user.login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        db.commit()

    def create_2fa_code(self, user_id: str, purpose: str, db: Session) -> str:
        """Create a new 2FA code"""
        # Invalidate existing codes for this user and purpose
        db.query(TwoFactorCode).filter(
            and_(
                TwoFactorCode.user_id == user_id,
                TwoFactorCode.purpose == purpose,
                TwoFactorCode.is_used == False
            )
        ).update({"is_used": True})
        
        # Generate new code
        code = self.generate_2fa_code()
        expires_at = datetime.utcnow() + timedelta(minutes=self.two_factor_expire_minutes)
        
        two_factor_code = TwoFactorCode(
            user_id=user_id,
            code=code,
            purpose=purpose,
            expires_at=expires_at
        )
        
        db.add(two_factor_code)
        db.commit()
        
        return code

    def verify_2fa_code(self, user_id: str, code: str, purpose: str, db: Session) -> bool:
        """Verify a 2FA code"""
        two_factor_code = db.query(TwoFactorCode).filter(
            and_(
                TwoFactorCode.user_id == user_id,
                TwoFactorCode.code == code,
                TwoFactorCode.purpose == purpose,
                TwoFactorCode.is_used == False,
                TwoFactorCode.expires_at > datetime.utcnow()
            )
        ).first()
        
        if not two_factor_code:
            return False
            
        # Increment attempts
        two_factor_code.attempts += 1
        
        # Check if max attempts exceeded
        if two_factor_code.attempts > int(os.getenv("TWO_FACTOR_MAX_ATTEMPTS", "3")):
            two_factor_code.is_used = True
            db.commit()
            return False
            
        # Mark as used
        two_factor_code.is_used = True
        db.commit()
        
        return True

    def create_user(self, email: str, password: str, tenant_id: str, first_name: str = None, 
                   last_name: str = None, role: str = "user", db: Session = None) -> User:
        """Create a new user"""
        if not db:
            db = get_db_session()
            should_close = True
        else:
            should_close = False
        
        try:
            # Check if user already exists
            existing_user = self.get_user_by_email(email, tenant_id, db)
            if existing_user:
                raise ValueError("User with this email already exists")
                
            # Hash password
            password_hash = self.hash_password(password)
            
            # Create user
            user = User(
                tenant_id=tenant_id,
                email=email,
                password_hash=password_hash,
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_verified=False,  # Require email verification
                two_factor_enabled=True
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            return user
        finally:
            if should_close:
                db.close()

    def authenticate_user(self, email: str, password: str, tenant_id: str, db: Session) -> Tuple[Optional[User], str]:
        """Authenticate user with email and password"""
        user = self.get_user_by_email(email, tenant_id, db)
        
        if not user:
            return None, "Invalid email or password"
            
        if self.is_user_locked(user):
            return None, f"Account is locked. Try again after {user.locked_until.strftime('%Y-%m-%d %H:%M:%S')} UTC"
            
        if not self.verify_password(password, user.password_hash):
            self.increment_login_attempts(user, db)
            return None, "Invalid email or password"
            
        return user, "success"

    def store_auth_token(self, user_id: str, token: str, token_type: str, db: Session) -> None:
        """Store authentication token in database"""
        # Hash the token for security
        token_hash = self.pwd_context.hash(token)
        
        # Calculate expiration
        if token_type == "access":
            expires_at = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        elif token_type == "refresh":
            expires_at = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        else:
            expires_at = datetime.utcnow() + timedelta(hours=1)
            
        auth_token = AuthToken(
            user_id=user_id,
            token_type=token_type,
            token_hash=token_hash,
            expires_at=expires_at
        )
        
        db.add(auth_token)
        db.commit()

    def revoke_token(self, token_hash: str, db: Session) -> bool:
        """Revoke a token"""
        auth_token = db.query(AuthToken).filter(
            AuthToken.token_hash == token_hash
        ).first()
        
        if auth_token:
            auth_token.is_revoked = True
            db.commit()
            return True
            
        return False

    def log_security_event(self, tenant_id: str, user_id: str, action: str, 
                          ip_address: str, user_agent: str, details: Dict[str, Any], 
                          db: Session) -> None:
        """Log security events for audit"""
        audit_log = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        
        db.add(audit_log)
        db.commit()

    def cleanup_expired_tokens(self, db: Session) -> int:
        """Clean up expired tokens and 2FA codes"""
        now = datetime.utcnow()
        
        # Clean up expired tokens
        expired_tokens = db.query(AuthToken).filter(
            AuthToken.expires_at < now
        ).delete()
        
        # Clean up expired 2FA codes
        expired_codes = db.query(TwoFactorCode).filter(
            TwoFactorCode.expires_at < now
        ).delete()
        
        db.commit()
        
        return expired_tokens + expired_codes


# Global instance
auth_service = AuthService()
