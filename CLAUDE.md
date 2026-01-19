# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Starting the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Development mode (starts on port 8000 with auto-reload)
python main_working_final.py

# Production mode with monitoring
./start_production.sh

# Restart production server
./restart_leadrouter.sh

# Restart in development mode
./restart_devmode_leadrouter.sh
```

### Testing

```bash
# The project uses standalone test scripts (not pytest framework)
# Each test file tests a specific component

# Test GHL integration and contact creation
python test_ghl_contact_trigger.py

# Test field mapping functionality
python test_field_mapping.py

# Test vendor matching and assignment
python test_vendor_assignment_fix.py

# Test service category lookup
python test_service_lookup.py

# Test unified services API
python test_unified_services.py

# Comprehensive lead routing test
python test_lead_routing_comprehensive.py

# Test API endpoints directly
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/webhooks/health
curl http://localhost:8000/api/v1/admin/health
```

### Database Operations

```bash
# Access SQLite database directly
sqlite3 smart_lead_router.db

# Common queries
sqlite3 smart_lead_router.db "SELECT * FROM webhook_logs ORDER BY created_at DESC LIMIT 10;"
sqlite3 smart_lead_router.db "SELECT COUNT(*) FROM leads;"
sqlite3 smart_lead_router.db "SELECT * FROM vendors WHERE status='active';"

# Backup database
cp smart_lead_router.db "smart_lead_router_backup_$(date +%Y%m%d_%H%M%S).db"

# Create database copy for viewing (non-production)
python create_db_copy_for_viewing.py
```

### Monitoring and Logs

```bash
# View real-time application logs
tail -f server.log

# View error logs
tail -f server_error.log

# Check monitoring status
./check_monitoring_status.sh

# Monitor server health
./monitor_server.sh

# Install systemd service for production
sudo ./install_systemd_service.sh
```

### Admin User Management

```bash
# Create initial admin user
python create_admin_user.py
```

## High-Level Architecture

### System Overview

Lead Router Pro is a FastAPI-based lead routing system for marine services that:
1. Receives webhook submissions from WordPress/Elementor forms
2. Classifies services using a 3-level hierarchy (60+ marine service categories)
3. Creates/updates contacts in GoHighLevel CRM
4. Routes leads to qualified vendors based on service type and geographic coverage

**Critical Flow:**
```
Elementor Form → Webhook Endpoint → Field Mapping → Service Classification
→ GHL Contact Creation → Lead Storage → Vendor Matching → Assignment
```

### Three-Level Service Hierarchy

The system uses a sophisticated 3-level service taxonomy defined in [api/services/service_categories.py](api/services/service_categories.py):

- **Level 1 (Primary Category):** Broad service areas (e.g., "Boat Maintenance", "Marine Systems")
- **Level 2 (Subcategory):** Specific service types (e.g., "Ceramic Coating", "Boat Detailing")
- **Level 3 (Specific Service):** Granular service details for precise vendor matching

**Example:**
```
Level 1: "Marine Systems"
  Level 2: "Yacht AC Sales"
    Level 3: "Air Conditioning Installation", "AC Unit Replacement"
```

Vendors select services at Level 3 granularity to receive only relevant leads. This prevents misrouting and ensures quality matches.

### Service Architecture: Single Source of Truth

**IMPORTANT:** The codebase is undergoing refactoring to establish a unified service architecture. Always use these authoritative sources:

1. **Service Data:** [api/services/unified_service_dictionary.py](api/services/unified_service_dictionary.py)
   - Single source of truth for all service categories
   - Wraps [dockside_pros_service_dictionary.py](api/services/dockside_pros_service_dictionary.py)
   - Provides cached, validated service data
   - **Use this:** `UnifiedServiceDictionary()` class

2. **Service Categories:** [api/services/service_categories.py](api/services/service_categories.py)
   - Defines `SERVICE_CATEGORIES` (Level 1 → Level 2 mappings)
   - Defines `SPECIFIC_SERVICES` (Level 2 → Level 3 mappings)
   - Contains fuzzy matching logic

**Deprecated/Avoid:**
- `api/services/ghl_api.py` - Use `ghl_api_v2_optimized.py` instead
- `api/services/ai_classifier.py` - Inline classification preferred
- Direct access to service dictionaries - Use UnifiedServiceDictionary

See [SERVICE_MAP.md](SERVICE_MAP.md) for complete service architecture details.

### Core Components

1. **Entry Point:** [main_working_final.py](main_working_final.py)
   - FastAPI application setup
   - Middleware configuration (IP security, CORS, auth)
   - Router registration
   - Static file serving
   - Lifespan events (startup validation)

2. **Configuration:** [config.py](config.py)
   - `AppConfig` class with all environment variables
   - `validate_config()` method checks required settings
   - Centralized access to GHL credentials, SMTP, JWT settings

3. **Database Models:** [database/models.py](database/models.py)
   - Multi-tenant architecture: `Tenant`, `User`, `Account`
   - Authentication: `AuthToken`, `TwoFactorCode`, `AuditLog`
   - Core entities: `Vendor`, `Lead`, `PerformanceMetric`, `Feedback`
   - Uses SQLAlchemy ORM with SQLite (supports PostgreSQL)

4. **Database Operations:** [database/simple_connection.py](database/simple_connection.py)
   - `db` singleton for all database operations
   - Lead CRUD: `create_lead()`, `update_lead()`, `get_leads()`
   - Vendor management: `get_vendors()`, `update_vendor()`
   - Webhook logging: `log_webhook_request()`
   - Multi-tenant queries with proper isolation

5. **API Routes:**

   **Webhook Processing:** [api/routes/webhook_routes.py](api/routes/webhook_routes.py)
   - **Main endpoint:** `/api/v1/webhooks/elementor/{form_identifier}` (POST)
   - Form field validation and normalization
   - Service classification and mapping
   - GHL contact creation/update with custom fields
   - Lead database storage
   - Vendor assignment when enabled
   - **Note:** Large file (3500+ lines) - use specific functions rather than reading entire file

   **Admin Dashboard:** [api/routes/admin_routes.py](api/routes/admin_routes.py)
   - System health: `/api/v1/admin/health`
   - GHL connection test: `/api/v1/admin/test-ghl-connection`
   - Statistics and analytics endpoints

   **Vendor Routing:** [api/routes/routing_admin.py](api/routes/routing_admin.py)
   - Vendor management endpoints
   - Routing rule configuration
   - Lead reassignment

   **Authentication:** [api/routes/auth_routes.py](api/routes/auth_routes.py)
   - Login: `/api/v1/auth/login`
   - 2FA verification: `/api/v1/auth/verify-2fa`
   - JWT token management

   **Unified Services:** [api/routes/unified_services_routes.py](api/routes/unified_services_routes.py)
   - Standardized service category API
   - Used by vendor application forms

6. **Services Layer:**

   **GHL Integration:** [api/services/ghl_api_v2_optimized.py](api/services/ghl_api_v2_optimized.py) (PREFERRED)
   - `OptimizedGoHighLevelAPI` class
   - Contact CRUD operations
   - Opportunity management
   - Custom field handling
   - User creation for vendors

   **Field Mapping:** [api/services/field_mapper.py](api/services/field_mapper.py)
   - Maps form fields to GHL custom fields
   - Uses `field_reference.json` (auto-generated from GHL)
   - Uses `field_mappings.json` (manual field ID mappings)
   - `map_payload()` is the main function

   **Lead Routing:** [api/services/lead_routing_service.py](api/services/lead_routing_service.py)
   - `find_matching_vendors()`: Geographic and service matching
   - `select_vendor_from_pool()`: Best vendor selection
   - Supports Global, National, State, County, ZIP coverage levels

   **Service Classification:** [api/services/service_categories.py](api/services/service_categories.py)
   - `get_service_category()`: Form ID → Level 1 category
   - `get_subcategory()`: Form ID → Level 2 subcategory
   - `get_specific_service_name()`: Form ID → Level 3 service
   - Fuzzy matching for flexible classification

7. **Security:**
   - **Middleware:** [api/security/middleware.py](api/security/middleware.py)
     - IP whitelisting via `IPSecurityMiddleware`
     - Reads from `security_data.json`
   - **Auth Middleware:** [api/security/auth_middleware.py](api/security/auth_middleware.py)
     - JWT validation on protected routes
   - **2FA:** [api/services/free_email_2fa.py](api/services/free_email_2fa.py)
     - Email-based 2FA code generation/validation

### Critical Files

- **`field_reference.json`**: Auto-generated list of all GHL custom fields for the location. Generate via admin dashboard "Generate Field Reference" button.
- **`field_mappings.json`**: Manual mapping of form field names to GHL custom field IDs. Updated when new fields are added.
- **`security_data.json`**: IP whitelist and security settings for API access control.
- **`.env`**: Environment variables for GHL credentials, SMTP, JWT secrets (never commit!)

### Key Workflows

#### 1. Form Submission Processing

When an Elementor form is submitted to `/api/v1/webhooks/elementor/{form_identifier}`:

1. **Validation:** Webhook API key checked, IP validated
2. **Field Extraction:** Form data parsed and normalized (handles both Elementor and GHL webhook formats)
3. **Service Classification:**
   - Form identifier mapped to service categories (L1, L2, L3)
   - Multiple services supported via `get_services_from_payload()`
4. **GHL Contact Creation:**
   - Check if contact exists (by email or phone)
   - Create new or update existing contact
   - Set custom fields using field mapper
   - Add tags based on service category
5. **Lead Storage:** Create lead record in local database
6. **Vendor Routing (if enabled):**
   - Find vendors matching service type and geographic area
   - Select best vendor using round-robin or performance-based selection
   - Assign lead to vendor in GHL

#### 2. Vendor Application Flow

Multi-step vendor application form collects:

1. **Basic Info:** Name, company, contact details
2. **Service Selection:**
   - Select Level 1 category
   - Select Level 2 subcategories
   - Select specific Level 3 services (critical for precise matching)
3. **Coverage Area:** Global, National, State, County, or ZIP-based coverage
4. **Approval:** Admin reviews and approves in dashboard
5. **GHL User Creation:** Vendor provisioned as GHL user with access to their leads

#### 3. Field Reference Synchronization

To sync GHL custom fields:

1. Admin dashboard → "Generate Field Reference" button
2. System calls GHL API to fetch all custom fields
3. Generates `field_reference.json` with field IDs and metadata
4. Use this reference when updating `field_mappings.json`

## Common Development Patterns

### Adding a New Form Identifier

1. **Choose or add form ID:** In [webhook_routes.py](api/routes/webhook_routes.py), find `FORM_IDENTIFIERS` mapping
2. **Map to service:** Update service classification functions in [service_categories.py](api/services/service_categories.py)
3. **Test webhook:** Use Swagger UI at `/docs` or curl to POST sample data
4. **Verify in GHL:** Check contact created with correct fields and tags

### Adding a New GHL Custom Field

1. **Create field in GHL:** Use GHL UI to add custom field to location
2. **Regenerate field reference:** Admin dashboard → "Generate Field Reference"
3. **Update field mappings:** Edit `field_mappings.json` to map form field name to GHL field ID
4. **Test mapping:** Submit test form and verify field populated in GHL contact

### Modifying Vendor Matching Logic

1. **Edit:** [api/services/lead_routing_service.py](api/services/lead_routing_service.py)
2. **Key function:** `find_matching_vendors(service_category, location_data)`
3. **Consider:** Service-level match (L1/L2/L3), geographic coverage, vendor capacity
4. **Test:** Use [test_vendor_assignment_fix.py](test_vendor_assignment_fix.py)

### Adding a New Service Category

1. **Update taxonomy:** [api/services/service_categories.py](api/services/service_categories.py)
   - Add to `SERVICE_CATEGORIES` (L1 → L2)
   - Add to `SPECIFIC_SERVICES` (L2 → L3)
2. **Update dictionary:** [api/services/dockside_pros_service_dictionary.py](api/services/dockside_pros_service_dictionary.py)
3. **Update forms:** Vendor application and admin dashboards
4. **Test classification:** Ensure new services route correctly

## Environment Setup

Create `.env` file with:

```env
# GHL Configuration (REQUIRED)
GHL_LOCATION_ID=your_location_id
GHL_PRIVATE_TOKEN=your_private_token
GHL_AGENCY_API_KEY=your_agency_key
GHL_COMPANY_ID=your_company_id
GHL_WEBHOOK_API_KEY=secure_random_string

# Database
DATABASE_URL=sqlite:///smart_lead_router.db

# Security (generate secure random strings)
SECRET_KEY=your_secret_key_min_32_chars
JWT_SECRET_KEY=your_jwt_secret_min_32_chars
JWT_ALGORITHM=HS256

# Email (for 2FA - Gmail recommended)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password

# Optional
PIPELINE_ID=your_pipeline_id
NEW_LEAD_STAGE_ID=your_stage_id
```

**Gmail Setup:** Follow [GMAIL_SETUP_GUIDE.md](GMAIL_SETUP_GUIDE.md) to create app password.

## Debugging Tips

1. **Check logs first:**
   ```bash
   tail -50 server.log          # Last 50 lines
   grep "ERROR" server_error.log # All errors
   ```

2. **Test GHL connection:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/admin/test-ghl-connection \
     -H "Content-Type: application/json" \
     -d '{"locationId":"xxx", "privateToken":"yyy"}'
   ```

3. **Verify environment variables loaded:**
   - Check startup logs for "✅ Loaded" or "❌ Missing" indicators
   - Application validates config on startup via `AppConfig.validate_config()`

4. **Test webhook endpoint:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/webhooks/elementor/test-form \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your_webhook_api_key" \
     -d '{"name":"Test User","email":"test@example.com","phone":"1234567890"}'
   ```

5. **Check webhook logs in database:**
   ```bash
   sqlite3 smart_lead_router.db "SELECT * FROM webhook_logs ORDER BY created_at DESC LIMIT 5;"
   ```

6. **Admin dashboard diagnostics:**
   - Visit `/admin` and check "System Status" section
   - Green indicators = healthy, red = issues

7. **Review field mappings:**
   - Ensure `field_reference.json` exists and is recent
   - Verify `field_mappings.json` has correct field IDs
   - Check logs for "Field mapping" messages

## Production Deployment

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   nano .env  # Add production credentials
   ```

3. **Create admin user:**
   ```bash
   python create_admin_user.py
   ```

4. **Start with systemd (recommended):**
   ```bash
   sudo ./install_systemd_service.sh
   sudo systemctl start lead-router-pro
   sudo systemctl enable lead-router-pro
   ```

5. **Or use production script:**
   ```bash
   ./start_production.sh
   ```

6. **Monitor:**
   ```bash
   ./monitor_leadrouter.sh
   tail -f server.log
   ```

## Additional Documentation

- **[README.md](README.md)**: Overview, features, architecture diagrams
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)**: Detailed installation and configuration
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)**: 8-phase testing checklist
- **[API_REFERENCE.md](API_REFERENCE.md)**: Complete API endpoint documentation
- **[SERVICE_MAP.md](SERVICE_MAP.md)**: Service architecture and migration plan
- **[DATABASE_STRUCTURE_AND_FIELD_MAPPINGS.md](DATABASE_STRUCTURE_AND_FIELD_MAPPINGS.md)**: Database schema details
- **[ELEMENTOR_WEBHOOK_GUIDE.md](ELEMENTOR_WEBHOOK_GUIDE.md)**: Setting up WordPress webhooks
- **[VENDOR_SUBMISSION_GUIDE.md](VENDOR_SUBMISSION_GUIDE.md)**: Vendor onboarding process
- **[2FA_SETUP_GUIDE.md](2FA_SETUP_GUIDE.md)**: Two-factor authentication setup
- **[SERVER_MANAGEMENT_GUIDE.md](SERVER_MANAGEMENT_GUIDE.md)**: Production server operations
