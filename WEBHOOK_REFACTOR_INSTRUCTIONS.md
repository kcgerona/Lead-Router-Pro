# Webhook Routes Refactoring Instructions

## Problem Statement
The webhook_routes.py file (3000+ lines) is using outdated mapping modules and doesn't properly implement the centralized data dictionary and service category mapping system that works correctly in the dashboard's "Test Vendor Matching" function.

## Current Issues to Fix

### 1. Wrong Module Usage
**CURRENT (WRONG):**
- Uses `api.services.field_mapper` (old, can't handle GHL nested customFields)
- Uses `api.services.service_mapper` (redirect layer only)
- Doesn't use `api.services.service_dictionary_mapper` (the correct enhanced mapper)
- Doesn't properly use `api.services.service_categories` (central truth)

**SHOULD USE:**
- `api.services.service_dictionary_mapper.ServiceDictionaryMapper`
- `api.services.service_categories` (for service hierarchy)
- Remove dependency on old `field_mapper`

### 2. Custom Fields Extraction Problem
**CURRENT (WRONG):**
```python
# Line ~2989 - Doesn't extract customFields array properly
mapped_payload = field_mapper.map_payload(contact_details, industry="marine")
```

**SHOULD BE:**
```python
# First, extract customFields into a flat dictionary
custom_fields_dict = {}
for field in contact_details.get('customFields', []):
    field_id = field.get('id')
    field_value = field.get('value')
    if field_id:
        custom_fields_dict[field_id] = field_value

# Then use ServiceDictionaryMapper to map the fields properly
from api.services.service_dictionary_mapper import ServiceDictionaryMapper
mapper = ServiceDictionaryMapper()

# Combine standard fields with custom fields for mapping
combined_payload = {
    **contact_details,  # Standard fields like firstName, lastName, email
    **custom_fields_dict  # Flattened custom fields
}

# Map to standardized service structure
mapping_result = mapper.map_payload_to_service(combined_payload)
```

### 3. Service Category Extraction Logic
**CURRENT (WRONG at lines ~3041-3048):**
```python
# Too broad - picks up wrong fields
for field in custom_fields:
    field_name = field.get('name', '').lower().replace(' ', '_')
    if any(name in field_name for name in service_field_names):
        service_category = field_value  # Wrong!
```

**SHOULD BE:**
```python
# Use specific field IDs from field_reference.json for LEAD ROUTING
LEAD_FIELD_IDS = {
    'primary_service_category': 'HRqfv0HnUydNRLKWhk27',  # Level 1 category for routing
    'specific_service_needed': 'FT85QGi0tBq1AfVGNJ9v'    # Level 2/3 specific service
}
# DO NOT USE O84LyhN1QjZ8Zz5mteCM - that's for vendor service capabilities!

# Extract the Level 1 category that originated this lead request
primary_category = custom_fields_dict.get(LEAD_FIELD_IDS['primary_service_category'])

# Extract the specific service requested within that category
specific_service = custom_fields_dict.get(LEAD_FIELD_IDS['specific_service_needed'])
```

### 4. Service Level Hierarchy Understanding
**KEY CONCEPT TO IMPLEMENT:**
```python
from api.services.service_categories import SERVICE_CATEGORIES, LEVEL_3_SERVICES

def determine_specific_service_requested(category, service):
    """
    For categories WITHOUT Level 3 services (like Boat Maintenance),
    the Level 2 service IS the specific_service_requested
    """
    # Check if this category has Level 3 services
    if category in LEVEL_3_SERVICES:
        # This category has Level 3, so Level 2 is subcategory
        return None  # Would need Level 3 for specific_service_requested
    else:
        # No Level 3 for this category, so Level 2 IS the specific service
        if service in SERVICE_CATEGORIES.get(category, []):
            return service  # Level 2 becomes specific_service_requested
    return None
```

### 5. Lead Creation with Proper Fields
**CURRENT (WRONG at line ~3155):**
```python
mapped_payload.get("specific_service_requested", ""),  # Always empty!
```

**SHOULD BE:**
```python
# Use the properly extracted and mapped service
specific_service_value = determine_specific_service_requested(
    primary_category, 
    specific_service
) or specific_service  # From the correctly mapped fields
```

## Reference Implementation to Copy
Look at the dashboard's "Test Vendor Matching" function in `lead_router_pro_dashboard.html`:
1. Find the testVendorMatching() JavaScript function
2. Note how it properly extracts service categories and specific services
3. The backend endpoint it calls likely uses the correct service mapping

## Step-by-Step Refactoring Process

### Phase 1: Create New Functions
1. Create `extract_ghl_custom_fields(contact_details)` function
2. Create `map_ghl_contact_to_lead(contact_details)` function using ServiceDictionaryMapper
3. Create `determine_service_hierarchy(category, service)` function

### Phase 2: Update Imports
Replace:
```python
from api.services.field_mapper import field_mapper
```
With:
```python
from api.services.service_dictionary_mapper import ServiceDictionaryMapper
from api.services.service_categories import (
    SERVICE_CATEGORIES, 
    LEVEL_3_SERVICES,
    service_manager
)
```

### Phase 3: Fix the GHL Contact Processing
In the `process_ghl_new_contact_webhook` function (around line 2920):
1. Replace field_mapper.map_payload() with proper custom field extraction
2. Use ServiceDictionaryMapper for mapping
3. Properly determine primary_service_category vs specific_service_requested

### Phase 4: Fix Vendor Matching Integration
Ensure the lead_routing_service receives:
- `primary_service_category` (Level 1)
- `specific_service_requested` (Level 2 when no Level 3 exists, or Level 3 when it exists)

## Testing Checklist
After refactoring, test with:
1. A "Boat Oil Change" lead - should have specific_service_requested = "Boat Oil Change"
2. A "Hull Crack Repair" lead - should have specific_service_requested = "Hull Crack or Structural Repair"
3. Verify vendor matching works for both Level 2 and Level 3 services
4. Confirm no leads get "Uncategorized" when they have valid service data

## Files to Review for Context
1. `/api/services/service_categories.py` - The truth for service hierarchy
2. `/api/services/service_dictionary_mapper.py` - The correct mapping logic
3. `/api/routes/admin_functions.py` - May have correct implementation
4. `field_reference.json` - For correct GHL field IDs
5. Dashboard HTML - For working reference implementation

## Critical Field IDs from GHL
- `HRqfv0HnUydNRLKWhk27` = "Primary Service Category" (Level 1 category for LEAD routing)
  - This is the Level 1 category that originated the lead request
  - Used to traverse the data dictionary to find applicable Level 2/3 services
  - Example: "Boat Maintenance" or "Boat and Yacht Repair"
- `FT85QGi0tBq1AfVGNJ9v` = "Specific Service Needed" (Level 2 or 3 service requested)
  - The specific service within the category hierarchy
  - Example: "Boat Oil Change" (Level 2) or "Hull Crack or Structural Repair" (Level 3)
- `O84LyhN1QjZ8Zz5mteCM` = "Service Categories" (for VENDOR capabilities, NOT for lead routing!)

## Success Criteria
1. "Boat Oil Change" leads get properly assigned to vendors offering "Oil Change"
2. No more empty specific_service_requested fields when data exists in GHL
3. Service hierarchy correctly understood (Level 2 as specific when no Level 3)
4. Uses centralized service_categories.py as single source of truth