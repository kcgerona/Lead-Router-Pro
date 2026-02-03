from sqlalchemy import create_engine, Column, String, DateTime, JSON, Integer, Float, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import uuid
import os
from datetime import datetime, timedelta

Base = declarative_base()

# Use String for UUID fields in SQLite, UUID for PostgreSQL
def get_uuid_column():
    """Return appropriate UUID column type based on database URL"""
    database_url = os.getenv("DATABASE_URL", "sqlite:///./smart_lead_router.db")
    if "postgresql" in database_url:
        from sqlalchemy.dialects.postgresql import UUID
        return UUID(as_uuid=True)
    else:
        # Use String for SQLite
        return String(36)

class Tenant(Base):
    """Multi-tenant support - each tenant represents a company/organization"""
    __tablename__ = "tenants"
    
    id = Column(get_uuid_column(), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=False)  # e.g., dockside.life
    subdomain = Column(String(100), unique=True)  # e.g., dockside
    settings = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    subscription_tier = Column(String(50), default="starter")
    max_users = Column(Integer, default=10)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="tenant")
    accounts = relationship("Account", back_populates="tenant")

class User(Base):
    """User authentication with multi-tenant support"""
    __tablename__ = "users"
    
    id = Column(get_uuid_column(), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(get_uuid_column(), ForeignKey("tenants.id"), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    role = Column(String(50), default="user")  # admin, user, viewer
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    two_factor_enabled = Column(Boolean, default=True)
    last_login = Column(DateTime)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    auth_tokens = relationship("AuthToken", back_populates="user")
    two_factor_codes = relationship("TwoFactorCode", back_populates="user")
    
    # Unique constraint: email must be unique within tenant
    __table_args__ = (
        UniqueConstraint('tenant_id', 'email', name='unique_tenant_user_email'),
    )

class AuthToken(Base):
    """JWT tokens for authentication"""
    __tablename__ = "auth_tokens"
    
    id = Column(get_uuid_column(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(get_uuid_column(), ForeignKey("users.id"), nullable=False)
    token_type = Column(String(50), nullable=False)  # access, refresh, reset_password
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="auth_tokens")

class TwoFactorCode(Base):
    """2FA codes sent via email"""
    __tablename__ = "two_factor_codes"
    
    id = Column(get_uuid_column(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(get_uuid_column(), ForeignKey("users.id"), nullable=False)
    code = Column(String(10), nullable=False)
    purpose = Column(String(50), default="login")  # login, password_reset, email_verification
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="two_factor_codes")

class AuditLog(Base):
    """Security audit log"""
    __tablename__ = "audit_logs"
    
    id = Column(get_uuid_column(), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(get_uuid_column(), ForeignKey("tenants.id"))
    user_id = Column(get_uuid_column(), ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    resource = Column(String(100))
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    details = Column(JSON, default={})
    timestamp = Column(DateTime, default=datetime.utcnow)

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(get_uuid_column(), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(get_uuid_column(), ForeignKey("tenants.id"), nullable=False)
    ghl_location_id = Column(String(255), unique=True, nullable=False)
    company_name = Column(String(255), nullable=False)
    industry = Column(String(100), default="general")
    settings = Column(JSON, default={})
    subscription_tier = Column(String(50), default="starter")
    ghl_api_token = Column(String(500))  # Encrypted
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="accounts")
    vendors = relationship("Vendor", back_populates="account")
    leads = relationship("Lead", back_populates="account")

class Vendor(Base):
    __tablename__ = "vendors"
    
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))  # Changed to TEXT to match simple_connection.py
    account_id = Column(get_uuid_column(), ForeignKey("accounts.id"), nullable=False)
    ghl_contact_id = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    company_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    services_provided = Column(JSON, default=[])
    service_areas = Column(JSON, default=[])
    performance_score = Column(Float, default=0.0)
    total_leads_received = Column(Integer, default=0)
    total_leads_closed = Column(Integer, default=0)
    avg_response_time_hours = Column(Float, default=24.0)
    customer_rating = Column(Float, default=5.0)
    status = Column(String(50), default="active")
    taking_new_work = Column(Boolean, default=True)
    last_lead_assigned = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    account = relationship("Account", back_populates="vendors")
    # leads = relationship("Lead", back_populates="vendor")  # Temporarily disabled due to missing FK
    # performance_metrics = relationship("PerformanceMetric", back_populates="vendor")  # Temporarily disabled due to missing FK

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))  # Changed to TEXT to match simple_connection.py
    account_id = Column(get_uuid_column(), ForeignKey("accounts.id"), nullable=False)
    vendor_id = Column(Text)  # Changed to TEXT to match vendors.id
    ghl_contact_id = Column(String(255), nullable=False)
    service_category = Column(String(100))
    service_details = Column(JSON, default={})
    location_data = Column(JSON, default={})
    estimated_value = Column(Float, default=0.0)
    priority_score = Column(Float, default=0.0)
    status = Column(String(50), default="new")
    assignment_history = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    assigned_at = Column(DateTime)
    first_response_at = Column(DateTime)
    closed_at = Column(DateTime)
    outcome = Column(String(50))  # won, lost, qualified_out
    
    # Relationships
    account = relationship("Account", back_populates="leads")
    # vendor = relationship("Vendor", back_populates="leads")  # Temporarily disabled due to missing FK
    # feedback = relationship("Feedback", back_populates="lead")  # Temporarily disabled due to missing FK

class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"
    
    id = Column(get_uuid_column(), primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor_id = Column(Text, nullable=False)  # Changed from UUID to TEXT to match vendors.id
    lead_id = Column(Text)  # Changed from UUID to TEXT to match leads.id
    metric_type = Column(String(50), nullable=False)  # response_time, conversion, rating
    metric_value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    # vendor = relationship("Vendor", back_populates="performance_metrics")  # Temporarily disabled due to missing FK

class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(get_uuid_column(), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Text, nullable=False)  # Changed from UUID to TEXT to match leads.id
    vendor_id = Column(Text, nullable=False)  # Changed from UUID to TEXT to match vendors.id
    rating = Column(Integer)  # 1-5 scale
    comments = Column(Text)
    feedback_type = Column(String(50), default="post_service")
    submitted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    # lead = relationship("Lead", back_populates="feedback")  # Temporarily disabled due to missing FK
    # vendor = relationship("Vendor")  # Temporarily disabled due to missing FK
