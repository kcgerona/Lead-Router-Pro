#!/usr/bin/env python3
"""
Update User Password Script
Updates an existing user's password using Argon2 hashing
"""

import os
import sys
from sqlalchemy.orm import Session
from database.simple_connection import get_db_session, auth_engine
from database.models import User, Tenant
from api.services.auth_service import AuthService

def update_user_password(email: str, new_password: str, domain: str = "dockside.local"):
    """Update user password with Argon2 hashing"""
    
    # Initialize auth service
    auth_service = AuthService()
    
    # Get database session
    db = get_db_session()
    
    try:
        # Get tenant
        tenant = db.query(Tenant).filter(Tenant.domain == domain).first()
        if not tenant:
            print(f"Tenant with domain '{domain}' not found")
            return False
        
        # Get user
        user = db.query(User).filter(
            User.email == email,
            User.tenant_id == tenant.id
        ).first()
        
        if not user:
            print(f"User '{email}' not found in tenant '{domain}'")
            return False
        
        # Hash the new password using Argon2
        new_password_hash = auth_service.hash_password(new_password)
        
        # Update user password
        user.password_hash = new_password_hash
        user.is_active = True
        user.is_verified = True
        
        # Reset login attempts if any
        user.login_attempts = 0
        user.locked_until = None
        
        db.commit()
        db.refresh(user)
        
        print(f"✅ Password updated successfully for user: {email}")
        print(f"   Tenant: {tenant.name} ({domain})")
        print(f"   User ID: {user.id}")
        print(f"   Role: {user.role}")
        print(f"   New password hash: {new_password_hash[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating password: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def main():
    """Main function"""
    print("🔐 Update User Password Script")
    print("=" * 50)
    
    # ===== CONFIGURE THESE VALUES =====
    email = "kirbydevz@gmail.com"  # User email to update
    new_password = "exTraVagantxxx"  # New password
    domain = "dockside.life"  # Tenant domain
    # ==================================
    
    print(f"🔄 Updating password for: {email}")
    print(f"   Domain: {domain}")
    print(f"   New password length: {len(new_password)}")
    
    # Update password
    success = update_user_password(email, new_password, domain)
    
    if success:
        print("\n✅ Password update completed successfully!")
        print("📝 The user can now login with the new password.")
    else:
        print("\n❌ Password update failed!")
        print("📝 Please check the error messages above.")

if __name__ == "__main__":
    main()
