#!/usr/bin/env python3
"""
Comprehensive Dependency Management System
Handles graceful loading of all dependencies with clear feedback about missing packages
"""

import sys
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class DependencyLevel(Enum):
    CRITICAL = "critical"      # App can't run without these
    CORE = "core"             # Major features disabled without these  
    OPTIONAL = "optional"     # Nice-to-have features
    DEVELOPMENT = "dev"       # Only needed for development/testing

@dataclass
class DependencyInfo:
    name: str
    level: DependencyLevel
    purpose: str
    install_command: str
    fallback_message: str = ""
    version_check: Optional[str] = None

class DependencyManager:
    """Central dependency management with graceful fallbacks"""
    
    def __init__(self):
        self.available_deps = {}
        self.missing_deps = {}
        self.dependency_map = self._define_dependency_map()
        self.load_all_dependencies()
    
    def _define_dependency_map(self) -> Dict[str, DependencyInfo]:
        """Define all project dependencies with metadata"""
        return {
            # ===== CRITICAL DEPENDENCIES =====
            "fastapi": DependencyInfo(
                name="fastapi",
                level=DependencyLevel.CRITICAL,
                purpose="Web framework - core application functionality",
                install_command="pip install fastapi==0.115.12"
            ),
            "uvicorn": DependencyInfo(
                name="uvicorn",
                level=DependencyLevel.CRITICAL,
                purpose="ASGI server for running the application",
                install_command="pip install uvicorn==0.24.0"
            ),
            "sqlalchemy": DependencyInfo(
                name="sqlalchemy",
                level=DependencyLevel.CRITICAL,
                purpose="Database ORM - core data operations",
                install_command="pip install sqlalchemy==2.0.23"
            ),
            "pydantic": DependencyInfo(
                name="pydantic",
                level=DependencyLevel.CRITICAL,
                purpose="Data validation - API request/response handling",
                install_command="pip install pydantic==2.5.0"
            ),
            "requests": DependencyInfo(
                name="requests",
                level=DependencyLevel.CRITICAL,
                purpose="HTTP client - GoHighLevel API communication",
                install_command="pip install requests==2.31.0"
            ),
            "python-dotenv": DependencyInfo(
                name="dotenv",
                level=DependencyLevel.CRITICAL,
                purpose="Environment configuration loading",
                install_command="pip install python-dotenv==1.0.0"
            ),
            
            # ===== CORE DEPENDENCIES =====
            "psycopg2": DependencyInfo(
                name="psycopg2",
                level=DependencyLevel.CORE,
                purpose="PostgreSQL database driver",
                install_command="pip install psycopg2-binary==2.9.7",
                fallback_message="Database features limited to SQLite"
            ),
            "pgeocode": DependencyInfo(
                name="pgeocode",
                level=DependencyLevel.CORE,
                purpose="ZIP code to geographic location conversion",
                install_command="pip install pgeocode==0.4.0",
                fallback_message="Location services will return error messages"
            ),
            "pandas": DependencyInfo(
                name="pandas",
                level=DependencyLevel.CORE,
                purpose="Data processing for location services",
                install_command="pip install pandas==2.0.3",
                fallback_message="Geographic data processing limited"
            ),
            "passlib": DependencyInfo(
                name="passlib",
                level=DependencyLevel.CORE,
                purpose="Password hashing for authentication",
                install_command="pip install passlib[bcrypt]==1.7.4",
                fallback_message="Authentication system disabled"
            ),
            "bcrypt": DependencyInfo(
                name="bcrypt",
                level=DependencyLevel.CORE,
                purpose="Secure password hashing",
                install_command="pip install bcrypt==4.1.2",
                fallback_message="Password security reduced"
            ),
            "argon2": DependencyInfo(
                name="argon2",
                level=DependencyLevel.CORE,
                purpose="Argon2 password hashing (auth default)",
                install_command="pip install argon2-cffi==23.1.0",
                fallback_message="Argon2 hashing unavailable - auth may fall back or fail"
            ),
            
            # ===== OPTIONAL DEPENDENCIES =====
            "redis": DependencyInfo(
                name="redis",
                level=DependencyLevel.OPTIONAL,
                purpose="Caching and session storage",
                install_command="pip install redis==5.0.1",
                fallback_message="Caching disabled - performance may be slower"
            ),
            "celery": DependencyInfo(
                name="celery",
                level=DependencyLevel.OPTIONAL,
                purpose="Background task processing",
                install_command="pip install celery==5.3.4",
                fallback_message="Background tasks will run synchronously"
            ),
            "anthropic": DependencyInfo(
                name="anthropic",
                level=DependencyLevel.OPTIONAL,
                purpose="AI service classification",
                install_command="pip install anthropic==0.7.8",
                fallback_message="AI classification disabled - using rule-based fallback"
            ),
            "openai": DependencyInfo(
                name="openai",
                level=DependencyLevel.OPTIONAL,
                purpose="OpenAI API integration",
                install_command="pip install openai==1.3.5",
                fallback_message="OpenAI features disabled"
            ),
            "stripe": DependencyInfo(
                name="stripe",
                level=DependencyLevel.OPTIONAL,
                purpose="Payment processing",
                install_command="pip install stripe==7.8.0",
                fallback_message="Payment features disabled"
            ),
            "sentry_sdk": DependencyInfo(
                name="sentry_sdk",
                level=DependencyLevel.OPTIONAL,
                purpose="Error monitoring and logging",
                install_command="pip install sentry-sdk==1.38.0",
                fallback_message="Error monitoring disabled - using local logging only"
            ),
            "fastapi_mail": DependencyInfo(
                name="fastapi_mail",
                level=DependencyLevel.OPTIONAL,
                purpose="Email sending for notifications and 2FA",
                install_command="pip install fastapi-mail==1.4.1",
                fallback_message="Email notifications disabled"
            ),
            "aiosmtplib": DependencyInfo(
                name="aiosmtplib",
                level=DependencyLevel.OPTIONAL,
                purpose="Async SMTP for email sending",
                install_command="pip install aiosmtplib>=2.0,<3.0",
                fallback_message="Email features limited"
            ),
            "jinja2": DependencyInfo(
                name="jinja2",
                level=DependencyLevel.OPTIONAL,
                purpose="Template engine for email templates",
                install_command="pip install Jinja2==3.1.2",
                fallback_message="Email templates will use plain text"
            ),
            
            # ===== DEVELOPMENT DEPENDENCIES =====
            "pytest": DependencyInfo(
                name="pytest",
                level=DependencyLevel.DEVELOPMENT,
                purpose="Testing framework",
                install_command="pip install pytest==7.4.3",
                fallback_message="Testing tools not available"
            ),
            "pytest_asyncio": DependencyInfo(
                name="pytest_asyncio",
                level=DependencyLevel.DEVELOPMENT,
                purpose="Async testing support",
                install_command="pip install pytest-asyncio==0.21.1",
                fallback_message="Async testing not available"
            ),
        }
    
    def load_all_dependencies(self):
        """Load all dependencies with graceful fallbacks"""
        logger.info("🔍 Loading project dependencies...")
        
        for dep_key, dep_info in self.dependency_map.items():
            success, module = self._safe_import(dep_info.name, dep_info.level)
            
            if success:
                self.available_deps[dep_key] = {
                    'module': module,
                    'info': dep_info,
                    'available': True
                }
            else:
                self.missing_deps[dep_key] = {
                    'info': dep_info,
                    'available': False
                }
                
                # Log appropriate message based on dependency level
                if dep_info.level == DependencyLevel.CRITICAL:
                    logger.error(f"❌ CRITICAL: {dep_info.name} not available - {dep_info.purpose}")
                elif dep_info.level == DependencyLevel.CORE:
                    logger.warning(f"⚠️ CORE: {dep_info.name} not available - {dep_info.fallback_message}")
                elif dep_info.level == DependencyLevel.OPTIONAL:
                    logger.info(f"💡 OPTIONAL: {dep_info.name} not available - {dep_info.fallback_message}")
                else:  # DEVELOPMENT
                    logger.debug(f"🔧 DEV: {dep_info.name} not available - {dep_info.fallback_message}")
    
    def _safe_import(self, module_name: str, level: DependencyLevel) -> Tuple[bool, Optional[Any]]:
        """Safely import a module with error handling"""
        try:
            # Handle special cases for module names that don't match import names
            import_name = self._get_import_name(module_name)
            module = __import__(import_name)
            return True, module
        except ImportError as e:
            if level == DependencyLevel.CRITICAL:
                # For critical dependencies, we might want to fail fast
                logger.critical(f"💥 CRITICAL dependency {module_name} missing: {e}")
            return False, None
    
    def _get_import_name(self, module_name: str) -> str:
        """Convert package name to import name for special cases"""
        name_mapping = {
            "python-dotenv": "dotenv",
            "psycopg2-binary": "psycopg2",
            "fastapi-mail": "fastapi_mail",
            "pytest-asyncio": "pytest_asyncio"
        }
        return name_mapping.get(module_name, module_name)
    
    def get_module(self, dep_key: str) -> Optional[Any]:
        """Get a loaded module if available"""
        if dep_key in self.available_deps:
            return self.available_deps[dep_key]['module']
        return None
    
    def is_available(self, dep_key: str) -> bool:
        """Check if a dependency is available"""
        return dep_key in self.available_deps
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        total_deps = len(self.dependency_map)
        available_count = len(self.available_deps)
        missing_count = len(self.missing_deps)
        
        # Count by level
        level_stats = {}
        for level in DependencyLevel:
            level_deps = [d for d in self.dependency_map.values() if d.level == level]
            level_available = [k for k, v in self.available_deps.items() 
                             if self.dependency_map[k].level == level]
            
            level_stats[level.value] = {
                'total': len(level_deps),
                'available': len(level_available),
                'missing': len(level_deps) - len(level_available)
            }
        
        return {
            'total_dependencies': total_deps,
            'available': available_count,
            'missing': missing_count,
            'availability_percentage': (available_count / total_deps) * 100,
            'level_breakdown': level_stats,
            'critical_missing': self._get_missing_critical(),
            'can_start': self._can_application_start()
        }
    
    def _get_missing_critical(self) -> List[str]:
        """Get list of missing critical dependencies"""
        return [
            self.dependency_map[k].name 
            for k in self.missing_deps 
            if self.dependency_map[k].level == DependencyLevel.CRITICAL
        ]
    
    def _can_application_start(self) -> bool:
        """Determine if application can start with current dependencies"""
        missing_critical = self._get_missing_critical()
        return len(missing_critical) == 0
    
    def print_startup_report(self):
        """Print comprehensive startup dependency report"""
        status = self.get_system_status()
        
        print("\n" + "="*80)
        print("🛡️ DEPENDENCY MANAGEMENT SYSTEM - STARTUP REPORT")
        print("="*80)
        
        print(f"\n📊 OVERALL STATUS:")
        print(f"   Total Dependencies: {status['total_dependencies']}")
        print(f"   Available: {status['available']} ({status['availability_percentage']:.1f}%)")
        print(f"   Missing: {status['missing']}")
        
        # Status by level
        for level_name, stats in status['level_breakdown'].items():
            if stats['total'] > 0:
                percentage = (stats['available'] / stats['total']) * 100
                emoji = self._get_level_emoji(level_name)
                print(f"   {emoji} {level_name.upper()}: {stats['available']}/{stats['total']} ({percentage:.0f}%)")
        
        # Critical dependencies check
        if status['critical_missing']:
            print(f"\n🚨 CRITICAL DEPENDENCIES MISSING:")
            for dep in status['critical_missing']:
                dep_info = next(d for d in self.dependency_map.values() if d.name == dep)
                print(f"   ❌ {dep}: {dep_info.install_command}")
            print(f"\n💥 APPLICATION CANNOT START - Install critical dependencies first!")
            return False
        else:
            print(f"\n✅ All critical dependencies available - Application can start!")
        
        # Missing optional dependencies
        missing_optional = [
            self.dependency_map[k] 
            for k in self.missing_deps 
            if self.dependency_map[k].level in [DependencyLevel.CORE, DependencyLevel.OPTIONAL]
        ]
        
        if missing_optional:
            print(f"\n💡 OPTIONAL FEATURES DISABLED:")
            for dep_info in missing_optional:
                print(f"   ⚠️ {dep_info.name}: {dep_info.fallback_message}")
                print(f"      Install with: {dep_info.install_command}")
        
        print(f"\n🎯 SYSTEM READY: {status['availability_percentage']:.1f}% functionality available")
        print("="*80 + "\n")
        
        return status['can_start']
    
    def _get_level_emoji(self, level_name: str) -> str:
        """Get emoji for dependency level"""
        emojis = {
            'critical': '🚨',
            'core': '⚡',
            'optional': '💡',
            'development': '🔧'
        }
        return emojis.get(level_name, '📦')
    
    def get_installation_script(self) -> str:
        """Generate installation script for all missing dependencies"""
        missing_deps = [self.dependency_map[k] for k in self.missing_deps]
        if not missing_deps:
            return "# All dependencies are already installed!"
        
        script_lines = [
            "#!/bin/bash",
            "# Auto-generated dependency installation script",
            "",
            "echo '📦 Installing missing dependencies...'",
            ""
        ]
        
        # Group by level
        for level in [DependencyLevel.CRITICAL, DependencyLevel.CORE, DependencyLevel.OPTIONAL]:
            level_deps = [d for d in missing_deps if d.level == level]
            if level_deps:
                script_lines.append(f"# {level.value.upper()} dependencies")
                for dep in level_deps:
                    script_lines.append(f"echo 'Installing {dep.name}...'")
                    script_lines.append(dep.install_command)
                script_lines.append("")
        
        script_lines.append("echo '✅ Installation complete!'")
        return "\n".join(script_lines)

# Global instance
dependency_manager = DependencyManager()

# Convenience functions for easy access
def get_module(dep_key: str):
    """Get a dependency module if available"""
    return dependency_manager.get_module(dep_key)

def is_available(dep_key: str) -> bool:
    """Check if a dependency is available"""
    return dependency_manager.is_available(dep_key)

def require_module(dep_key: str, fallback_error: str = None):
    """Require a module or raise helpful error"""
    if not is_available(dep_key):
        dep_info = dependency_manager.dependency_map.get(dep_key)
        error_msg = fallback_error or f"{dep_key} not available. Install with: {dep_info.install_command}"
        raise ImportError(error_msg)
    return get_module(dep_key)

def print_startup_report():
    """Print startup report"""
    return dependency_manager.print_startup_report()

def can_start_application() -> bool:
    """Check if application can start"""
    return dependency_manager._can_application_start()