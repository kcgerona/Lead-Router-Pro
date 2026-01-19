# Lead Router Pro - Main Application Entry Point
import sys  
from utils.dependency_manager import print_startup_report, can_start_application

# Print startup report
if not print_startup_report():
    print("💥 Cannot start application due to missing critical dependencies")
    sys.exit(1)

# Load environment variables FIRST (before any other imports that use config)
from dotenv import load_dotenv
load_dotenv()  # This loads the .env file

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from pathlib import Path # os was not used, Path is already imported

# Define the base directory for the application (directory of this main.py file)
BASE_DIR = Path(__file__).resolve().parent

# Import your existing routes
from api.routes.webhook_routes import router as webhook_router, location_router
from api.routes.admin_routes import router as admin_router
from api.routes.simple_admin import router as simple_admin_router
from api.routes.field_mapping_routes import router as field_mapping_router
from api.routes.security_admin import router as security_admin_router
from api.routes.auth_routes import router as auth_router
from api.routes.routing_admin import router as routing_admin_router
from api.routes.vendor_toggle import router as vendor_toggle_router
from api.routes.lead_reassignment import router as lead_reassignment_router
# from api.routes.lead_reassignment_fixed import router as lead_reassignment_fixed_router  # Temporarily disabled
from api.routes.admin_functions import router as admin_functions_router
from api.routes.vendor_matching_enhanced import router as vendor_matching_router
from api.routes.service_dictionary_routes import router as service_dictionary_router
from api.routes.services_api import router as services_api_router

# Import security middleware
from api.security.middleware import IPSecurityMiddleware, SecurityCleanupMiddleware
from api.security.auth_middleware import auth_middleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events"""
    # Startup
    logger.info("🚀 DocksidePros Lead Router Pro starting up...")
    
    # Import and validate configuration
    from config import AppConfig
    
    # Log environment variable loading status
    logger.info("🔧 Configuration Status:")
    logger.info(f"   📍 GHL_LOCATION_ID: {'✅ Loaded' if AppConfig.GHL_LOCATION_ID else '❌ Missing'}")
    logger.info(f"   🔑 GHL_PRIVATE_TOKEN: {'✅ Loaded' if AppConfig.GHL_PRIVATE_TOKEN else '❌ Missing'}")
    logger.info(f"   🔐 GHL_WEBHOOK_API_KEY: {'✅ Loaded' if AppConfig.GHL_WEBHOOK_API_KEY else '❌ Missing'} (length: {len(AppConfig.GHL_WEBHOOK_API_KEY)})")
    logger.info(f"   🏢 GHL_AGENCY_API_KEY: {'✅ Loaded' if AppConfig.GHL_AGENCY_API_KEY else '❌ Missing'}")
    logger.info(f"   🏭 GHL_COMPANY_ID: {'✅ Loaded' if AppConfig.GHL_COMPANY_ID else '❌ Missing'}")
    
    # Validate required configuration
    config_valid = AppConfig.validate_config()
    if config_valid:
        logger.info("✅ All required configuration loaded successfully")
    else:
        logger.error("❌ Configuration validation failed - check environment variables")
    
    logger.info("✅ Enhanced webhook system loaded")
    logger.info("✅ Admin dashboard available at /admin")
    logger.info("✅ System health page available at /system-health")
    logger.info("✅ Service categories page available at /service-categories")
    logger.info("✅ API documentation available at /docs")
    logger.info("🎯 Ready to process form submissions!")
    
    yield
    
    # Shutdown (if needed)
    logger.info("🛑 DocksidePros Lead Router Pro shutting down...")

# Create FastAPI app with lifespan
app = FastAPI(
    title="DocksidePros Smart Lead Router Pro",
    description="Advanced lead routing system with admin dashboard",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add IP Security Middleware (BEFORE CORS)
app.add_middleware(IPSecurityMiddleware, enable_silent_blocking=True)
app.add_middleware(SecurityCleanupMiddleware, cleanup_interval=3600)

# CORS middleware for admin dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(webhook_router)
app.include_router(location_router)
app.include_router(admin_router)
app.include_router(simple_admin_router)
app.include_router(field_mapping_router)
app.include_router(security_admin_router)
app.include_router(auth_router)
app.include_router(routing_admin_router)
app.include_router(vendor_toggle_router)
app.include_router(lead_reassignment_router)
# app.include_router(lead_reassignment_fixed_router)  # Fixed endpoints with proper flow - temporarily disabled for debugging
app.include_router(admin_functions_router)
app.include_router(vendor_matching_router, prefix="/api/v1/vendor-matching", tags=["vendor-matching"])
app.include_router(service_dictionary_router)
app.include_router(services_api_router)

# Include unified services router
from api.routes.unified_services_routes import router as unified_services_router
app.include_router(unified_services_router)

# Create static and templates directories if they don't exist relative to BASE_DIR
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
templates_dir = BASE_DIR / "templates"
templates_dir.mkdir(exist_ok=True)

# Serve static files (for admin dashboard assets) from BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

def read_html_file(file_path: Path) -> str: # Changed type hint to Path
    """Read HTML file with error handling"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"HTML file not found: {file_path}")
        return f"<html><body><h1>Error: Template {file_path} not found</h1></body></html>"
    except Exception as e:
        logger.error(f"Error reading HTML file {file_path}: {e}")
        return f"<html><body><h1>Error loading template: {e}</h1></body></html>"

# Login page route
@app.get("/login", response_class=HTMLResponse)
@app.get("/auth", response_class=HTMLResponse)
async def login_page():
    """Serve the login page"""
    return HTMLResponse(content=read_html_file(BASE_DIR / "templates" / "login.html"))

# Main admin dashboard route - now protected
@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Serve the main admin dashboard - requires authentication"""
    # Check if user is authenticated
    authorization = request.headers.get("authorization")
    if not authorization:
        # Redirect to login if no auth header
        return HTMLResponse(content="""
        <script>
        if (!localStorage.getItem('access_token')) {
            window.location.href = '/login';
        } else {
            // User has token, load dashboard
            fetch('/admin-content', {
                headers: {
                    'Authorization': 'Bearer ' + localStorage.getItem('access_token')
                }
            })
            .then(response => {
                if (response.status === 401) {
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    window.location.href = '/login';
                } else {
                    return response.text();
                }
            })
            .then(html => {
                if (html) document.body.innerHTML = html;
            });
        }
        </script>
        """)
    
    return HTMLResponse(content=read_html_file(BASE_DIR / "lead_router_pro_dashboard.html"))

# Protected admin content route
@app.get("/admin-content", response_class=HTMLResponse)
async def admin_content(request: Request):
    """Serve admin dashboard content - protected route"""
    # This will be called with authentication
    return HTMLResponse(content=read_html_file(BASE_DIR / "lead_router_pro_dashboard.html"))

# Protected Service Categories page
@app.get("/service-categories", response_class=HTMLResponse)
@app.get("/categories", response_class=HTMLResponse)
async def service_categories_page(request: Request):
    """Serve the service categories page - requires authentication"""
    authorization = request.headers.get("authorization")
    if not authorization:
        return HTMLResponse(content="""
        <script>
        if (!localStorage.getItem('access_token')) {
            window.location.href = '/login';
        } else {
            fetch('/service-categories-content', {
                headers: { 'Authorization': 'Bearer ' + localStorage.getItem('access_token') }
            }).then(response => {
                if (response.status === 401) {
                    localStorage.removeItem('access_token');
                    window.location.href = '/login';
                } else {
                    return response.text();
                }
            }).then(html => {
                if (html) document.open(); document.write(html); document.close();
            });
        }
        </script>
        """)
    return HTMLResponse(content=read_html_file(BASE_DIR / "templates" / "service_categories.html"))

# Protected System Health page
@app.get("/system-health", response_class=HTMLResponse)
@app.get("/health-check", response_class=HTMLResponse)
async def system_health_page(request: Request):
    """Serve the system health page - requires authentication"""
    authorization = request.headers.get("authorization")
    if not authorization:
        return HTMLResponse(content="""
        <script>
        if (!localStorage.getItem('access_token')) {
            window.location.href = '/login';
        } else {
            fetch('/system-health-content', {
                headers: { 'Authorization': 'Bearer ' + localStorage.getItem('access_token') }
            }).then(response => {
                if (response.status === 401) {
                    localStorage.removeItem('access_token');
                    window.location.href = '/login';
                } else {
                    return response.text();
                }
            }).then(html => {
                if (html) document.open(); document.write(html); document.close();
            });
        }
        </script>
        """)
    return HTMLResponse(content=read_html_file(BASE_DIR / "templates" / "system_health.html"))

# Protected Enhanced Form Tester page
@app.get("/form-tester", response_class=HTMLResponse)
@app.get("/test-forms", response_class=HTMLResponse)
async def enhanced_form_tester_page(request: Request):
    """Serve the enhanced form tester page - requires authentication"""
    authorization = request.headers.get("authorization")
    if not authorization:
        return HTMLResponse(content="""
        <script>
        if (!localStorage.getItem('access_token')) {
            window.location.href = '/login';
        } else {
            fetch('/form-tester-content', {
                headers: { 'Authorization': 'Bearer ' + localStorage.getItem('access_token') }
            }).then(response => {
                if (response.status === 401) {
                    localStorage.removeItem('access_token');
                    window.location.href = '/login';
                } else {
                    return response.text();
                }
            }).then(html => {
                if (html) document.open(); document.write(html); document.close();
            });
        }
        </script>
        """)
    return HTMLResponse(content=read_html_file(BASE_DIR / "templates" / "enhanced_form_tester.html"))

# Protected content routes
@app.get("/service-categories-content", response_class=HTMLResponse)
async def service_categories_content():
    return HTMLResponse(content=read_html_file(BASE_DIR / "templates" / "service_categories.html"))

@app.get("/system-health-content", response_class=HTMLResponse)
async def system_health_content():
    return HTMLResponse(content=read_html_file(BASE_DIR / "templates" / "system_health.html"))

@app.get("/form-tester-content", response_class=HTMLResponse)
async def form_tester_content():
    return HTMLResponse(content=read_html_file(BASE_DIR / "templates" / "enhanced_form_tester.html"))

# Protected main dashboard route - now the root
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Protected main dashboard - requires authentication"""
    # Check if user is authenticated
    authorization = request.headers.get("authorization")
    if not authorization:
        # Redirect to login if no auth header
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>DocksidePros - Redirecting...</title>
        </head>
        <body>
        <script>
        if (!localStorage.getItem('access_token')) {
            window.location.href = '/login';
        } else {
            // User has token, load dashboard content
            fetch('/dashboard-content', {
                headers: {
                    'Authorization': 'Bearer ' + localStorage.getItem('access_token')
                }
            })
            .then(response => {
                if (response.status === 401) {
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    window.location.href = '/login';
                } else {
                    return response.text();
                }
            })
            .then(html => {
                if (html) document.open(); document.write(html); document.close();
            });
        }
        </script>
        </body>
        </html>
        """)
    
    return HTMLResponse(content=read_html_file(BASE_DIR / "lead_router_pro_dashboard.html"))

# Protected dashboard content route
@app.get("/dashboard-content", response_class=HTMLResponse)
async def dashboard_content(request: Request):
    """Serve main dashboard content - protected route"""
    return HTMLResponse(content=read_html_file(BASE_DIR / "lead_router_pro_dashboard.html"))

# Admin User Guide Route - Public Access (read-only documentation)
@app.get("/admin_user_guide.html", response_class=HTMLResponse)
@app.get("/user-guide", response_class=HTMLResponse)
async def admin_user_guide():
    """Serve the admin user guide - no authentication required for documentation"""
    user_guide_path = BASE_DIR / "admin_user_guide.html"
    return HTMLResponse(content=read_html_file(user_guide_path))

# Vendor Widget Route - Public Access
@app.get("/vendor-widget", response_class=HTMLResponse)
@app.get("/vendor-application", response_class=HTMLResponse)
async def vendor_widget_page():
    """Serve the vendor application widget - no authentication required"""
    vendor_widget_path = BASE_DIR / "vendor_application_final.html"
    return HTMLResponse(content=read_html_file(vendor_widget_path))

@app.get("/vendor-application-new", response_class=HTMLResponse)
async def vendor_application_new():
    """Serve the NEW enhanced vendor application with Level 3 services - for GUI approval"""
    vendor_app_new_path = BASE_DIR / "vendor_application_new.html"
    return HTMLResponse(content=read_html_file(vendor_app_new_path))

@app.get("/vendor-application-api", response_class=HTMLResponse)
async def vendor_application_api():
    """Serve the API-driven vendor application - fetches data from services API"""
    vendor_app_api_path = BASE_DIR / "vendor_application_api.html"
    return HTMLResponse(content=read_html_file(vendor_app_api_path))

@app.get("/vendor-application-api-fixed", response_class=HTMLResponse)
async def vendor_application_api_fixed():
    """Serve the FIXED API-driven vendor application"""
    vendor_app_fixed_path = BASE_DIR / "vendor_application_api_fixed.html"
    return HTMLResponse(content=read_html_file(vendor_app_fixed_path))

@app.get("/vendor-application-api-v2", response_class=HTMLResponse)
async def vendor_application_api_v2():
    """Serve the V2 API-driven vendor application - complete working version"""
    vendor_app_v2_path = BASE_DIR / "vendor_application_api_v2.html"
    return HTMLResponse(content=read_html_file(vendor_app_v2_path))

@app.get("/vendor-application-working", response_class=HTMLResponse)
async def vendor_application_working():
    """Serve the WORKING vendor application with all fixes"""
    vendor_app_working_path = BASE_DIR / "vendor_application_working.html"
    return HTMLResponse(content=read_html_file(vendor_app_working_path))

@app.get("/vendor-application-unified", response_class=HTMLResponse)
async def vendor_application_unified():
    """Serve the UNIFIED vendor application that uses the unified services API"""
    vendor_app_unified_path = BASE_DIR / "vendor_application_unified.html"
    return HTMLResponse(content=read_html_file(vendor_app_unified_path))

@app.get("/vendor-application-compare", response_class=HTMLResponse)
async def vendor_application_compare():
    """Serve the comparison page for testing original vs unified vendor applications"""
    vendor_app_compare_path = BASE_DIR / "vendor_application_compare.html"
    return HTMLResponse(content=read_html_file(vendor_app_compare_path))

# Health check endpoint
@app.get("/health")
async def health_check():
    """Global health check"""
    return {
        "status": "healthy",
        "service": "DocksidePros Lead Router Pro",
        "version": "2.0.0",
        "features": [
            "Enhanced webhook processing",
            "Dynamic form handling", 
            "Admin dashboard",
            "Field management",
            "Service classification",
            "Vendor routing"
        ]
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return HTMLResponse(
        content="""
        <html>
            <head>
                <title>404 - Not Found</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; margin-top: 100px; background: #f8f9fa; }
                    .container { max-width: 600px; margin: 0 auto; padding: 40px 20px; background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                    h1 { color: #dc3545; margin-bottom: 20px; }
                    p { color: #6c757d; margin-bottom: 30px; }
                    a { color: #007bff; text-decoration: none; margin: 0 10px; }
                    a:hover { text-decoration: underline; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>404 - Page Not Found</h1>
                    <p>The requested resource was not found on this server.</p>
                    <div>
                        <a href="/">← Back to Home</a> | 
                        <a href="/admin">Admin Dashboard</a> |
                        <a href="/docs">API Docs</a> |
                        <a href="/system-health">System Health</a>
                    </div>
                </div>
            </body>
        </html>
        """,
        status_code=404
    )


if __name__ == "__main__":
    import uvicorn
    import signal
    import sys
    
    def signal_handler(signum, frame):
        logger.info("🛑 DocksidePros Lead Router Pro shutting down...")
        sys.exit(0)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        logger.info("🛑 DocksidePros Lead Router Pro shutting down...")
    except Exception as e:
        logger.error(f"❌ Application crashed: {e}")
        raise