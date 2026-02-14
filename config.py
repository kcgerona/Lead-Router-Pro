# config.py - Configuration management for Lead Router Pro

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class AppConfig:
    """
    Centralized configuration management for the application
    """
    
    # GHL API Configuration
    GHL_PRIVATE_TOKEN: str = os.getenv("GHL_PRIVATE_TOKEN", "")
    GHL_LOCATION_API: str = os.getenv("GHL_LOCATION_API", "")
    GHL_LOCATION_ID: str = os.getenv("GHL_LOCATION_ID", "")
    GHL_AGENCY_API_KEY: str = os.getenv("GHL_AGENCY_API_KEY", "")
    GHL_COMPANY_ID: str = os.getenv("GHL_COMPANY_ID", "")  # For V2 user creation API
    
    # Pipeline Configuration
    PIPELINE_ID: Optional[str] = os.getenv("PIPELINE_ID")
    NEW_LEAD_STAGE_ID: Optional[str] = os.getenv("NEW_LEAD_STAGE_ID")
    
    # Security Configuration
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")
    GHL_WEBHOOK_API_KEY: str = os.getenv("GHL_WEBHOOK_API_KEY", "")
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Domain Configuration
    DOMAIN: str = os.getenv("DOMAIN", "localhost")
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    WEBHOOK_BASE_URL: str = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000/api/v1/webhooks/elementor")
    
    # Authentication Configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "default_secret_key")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # Email Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "")
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./smart_lead_router.db")
    
    # App data directory (writable; avoid writing to repo root)
    FIELD_REFERENCE_PATH: str = os.getenv("FIELD_REFERENCE_PATH", "data/field_reference.json")
    
    @classmethod
    def validate_config(cls) -> bool:
        """
        Validate that required configuration is present
        """
        required_fields = [
            "GHL_PRIVATE_TOKEN",
            "GHL_LOCATION_ID",
            "GHL_WEBHOOK_API_KEY"
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(cls, field):
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ Missing required configuration: {', '.join(missing_fields)}")
            return False
        
        return True
    
    @classmethod
    def get_security_config(cls) -> dict:
        """
        Get security-related configuration
        """
        return {
            "webhook_secret": cls.WEBHOOK_SECRET,
            "ghl_webhook_api_key": cls.GHL_WEBHOOK_API_KEY,
            "environment": cls.ENVIRONMENT,
            "debug": cls.DEBUG
        }
