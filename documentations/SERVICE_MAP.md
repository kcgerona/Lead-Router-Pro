# Lead Router Pro - Service Architecture Map

## Overview
This document maps out the service architecture after refactoring (December 2024).
It shows which service handles what functionality to avoid confusion and duplication.

## Core Services

### 1. **api/services/service_mapper.py** ✅ NEW
**Purpose:** Centralized service category and name mappings
- `get_service_category()` - Maps form identifiers to service categories
- `get_specific_service()` - Maps form identifiers to specific service names
- `find_matching_service()` - Fuzzy matching for service names
- Contains all DOCKSIDE_PROS constants and mappings
- **Status:** Active, extracted from webhook_routes.py

### 2. **api/services/ghl_api_v2_optimized.py** 
**Purpose:** GoHighLevel CRM integration using v2 API
- Contact management (CRUD operations)
- Opportunity management
- User creation and management
- Custom field operations
- Pipeline/stage management
- **Status:** Active, primary GHL integration

### 3. **api/services/ghl_api.py**
**Purpose:** Legacy GoHighLevel v1 API integration
- **Status:** DEPRECATED - Migrate to v2_optimized
- Still used in 33 files (needs migration)

### 4. **api/services/field_mapper.py**
**Purpose:** Maps form fields to GHL custom fields
- `map_payload()` - Main mapping function
- Industry-specific field mapping
- Custom field ID resolution
- **Status:** Active, needs enhancement with customData support

### 5. **api/services/lead_routing_service.py**
**Purpose:** Vendor matching and selection logic
- `find_matching_vendors()` - Finds vendors for service/location
- `select_vendor_from_pool()` - Selects best vendor
- ZIP to county matching for vendors
- **Status:** Active

### 6. **api/services/location_service.py**
**Purpose:** Geographic data and conversions
- `zip_to_location()` - Converts ZIP to county/state
- `get_state_counties()` - Lists counties by state
- Location validation
- **Status:** Active

### 7. **api/services/simple_lead_router.py**
**Purpose:** Lead routing business logic
- Lead assignment algorithms
- Round-robin distribution
- Priority-based routing
- **Status:** Active

### 8. **api/services/auth_service.py**
**Purpose:** Authentication and authorization
- JWT token management
- User authentication
- Role-based access control
- **Status:** Active

### 9. **api/services/email_service.py** / **free_email_2fa.py**
**Purpose:** Email notifications and 2FA
- Send email notifications
- 2FA code generation and validation
- SMTP integration
- **Status:** Active

## Route Modules

### 1. **api/routes/webhook_routes.py** (Refactored - 3517 lines, was 4058)
**Purpose:** Webhook processing endpoints
- Elementor form webhooks
- GHL webhooks (new contact, reassignment)
- Vendor creation webhooks
- **Removed:** Service mappings (moved to service_mapper.py)
- **TODO:** Break into smaller modules

### 2. **api/routes/admin_routes.py**
**Purpose:** Admin dashboard endpoints
- System health monitoring
- Statistics and analytics
- Configuration management
- **Status:** Active

### 3. **api/routes/routing_admin.py**
**Purpose:** Lead routing administration
- Routing rule configuration
- Vendor management
- Assignment policies
- **Status:** Active

### 4. **api/routes/auth_routes.py**
**Purpose:** Authentication endpoints
- Login/logout
- 2FA endpoints
- Token refresh
- **Status:** Active

## Database Module

### **database/simple_connection.py**
**Purpose:** Database operations
- Lead CRUD operations
- Vendor management
- Activity logging
- Multi-tenant support
- **Status:** Active

## Deprecated/Duplicate Services (To Be Removed)

1. **api/services/ghl_api_enhanced_v2.py** - Duplicate of v2_optimized
2. **api/services/ai_enhanced_field_mapper_v2.py** - Duplicate of field_mapper
3. **api/services/ai_classifier.py** - Not used, inline classification preferred
4. **api/services/dockside_pros_service_dictionary.py** - Replaced by service_mapper
5. **api/services/service_categories.py** - Replaced by service_mapper
6. **api/services/ai_error_recovery_v2.py** - Not used

## Migration Plan

### Phase 1: ✅ COMPLETED
- [x] Extract service mappings to service_mapper.py
- [x] Remove duplicate code from webhook_routes.py
- [x] Archive backup files

### Phase 2: IN PROGRESS
- [ ] Migrate all ghl_api.py usage to ghl_api_v2_optimized.py
- [ ] Consolidate field_mapper variations
- [ ] Remove deprecated services

### Phase 3: TODO
- [ ] Break webhook_routes.py into:
  - `webhooks/elementor_webhook.py`
  - `webhooks/ghl_webhook.py`
  - `webhooks/vendor_webhook.py`
- [ ] Create processor modules:
  - `processors/lead_processor.py`
  - `processors/opportunity_processor.py`

### Phase 4: TODO
- [ ] Create comprehensive tests
- [ ] Update all imports
- [ ] Remove all deprecated code

## Quick Reference

| Task | Service to Use |
|------|---------------|
| Map form to service category | `service_mapper.get_service_category()` |
| Create/update GHL contact | `ghl_api_v2_optimized.OptimizedGoHighLevelAPI` |
| Map form fields to GHL | `field_mapper.map_payload()` |
| Find vendors for lead | `lead_routing_service.find_matching_vendors()` |
| Convert ZIP to county | `location_service.zip_to_location()` |
| Create lead in database | `simple_connection.db.create_lead()` |
| Authenticate user | `auth_service` methods |
| Send email notification | `email_service` or `free_email_2fa` |

## Notes

1. **webhook_routes.py is still too large** (3517 lines) and needs further modularization
2. **GHL API v1 is still widely used** - migration to v2 is critical
3. **Field mapping needs consolidation** - multiple implementations exist
4. **Test coverage is minimal** - comprehensive tests needed

Last Updated: December 2024