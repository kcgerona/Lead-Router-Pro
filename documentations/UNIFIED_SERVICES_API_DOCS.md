# Unified Services API Documentation

## Overview
The Unified Service Dictionary module (`api/services/unified_service_dictionary.py`) provides a single interface for accessing service categories and hierarchies across the entire Lead Router Pro application.

## Purpose
- **Single Source of Truth**: All service data comes from `dockside_pros_service_dictionary.py`
- **Multiple Format Support**: Provides data in various formats for different consumers
- **Performance Optimized**: Built-in caching with configurable TTL
- **Backwards Compatible**: Supports legacy function calls

## Quick Start

### Import the Module
```python
from api.services.unified_service_dictionary import (
    get_categories,
    get_vendor_app_data,
    get_vendor_matching_data,
    get_api_hierarchy,
    validate_service_selection,
    search_for_service
)
```

### Basic Usage Examples

#### Get All Categories
```python
categories = get_categories()
# Returns: ['Boat Maintenance', 'Boat and Yacht Repair', ...]
```

#### Get Vendor Application Format
```python
vendor_data = get_vendor_app_data()
# Returns: {
#   "Boat Maintenance": {
#     "subcategories": ["Ceramic Coating", "Finsulate", ...],
#     "level3Services": {"Finsulate": ["Installation", "Maintenance", ...]}
#   }
# }
```

#### Validate Service Selection
```python
is_valid, message = validate_service_selection(
    category="Boat Maintenance",
    subcategory="Finsulate",
    specific="Finsulate Installation"
)
```

#### Search for Services
```python
results = search_for_service("finsulate")
# Returns list of matching services with their hierarchy
```

## Available Functions

### Core Access Functions

| Function | Returns | Description |
|----------|---------|-------------|
| `get_categories()` | `List[str]` | List of all Level 1 category names |
| `get_vendor_app_data()` | `Dict` | Vendor application widget format |
| `get_vendor_matching_data()` | `Tuple[Dict, Dict]` | (SERVICE_CATEGORIES, LEVEL_3_SERVICES) |
| `get_api_hierarchy()` | `Dict` | Nested hierarchy for API endpoints |
| `validate_service_selection()` | `Tuple[bool, str]` | Validate service hierarchy |
| `search_for_service()` | `List[Dict]` | Search across all services |

### Advanced Usage with Class Instance

```python
from api.services.unified_service_dictionary import UnifiedServiceDictionary

# Create instance (or use singleton)
ud = UnifiedServiceDictionary()

# Get raw dictionary
raw_data = ud.get_raw_dictionary()

# Get subcategories for specific category
subcats = ud.get_subcategories("Boat Maintenance")

# Get Level 3 services
level3 = ud.get_level3_services("Boat Maintenance", "Finsulate")

# Get statistics
stats = ud.get_service_count_stats()
```

## Format Specifications

### Vendor Application Format
```json
{
  "CategoryName": {
    "subcategories": ["Subcat1", "Subcat2"],
    "level3Services": {
      "Subcat1": ["Service1", "Service2"]
    }
  }
}
```

### Vendor Matching Format
```python
# Tuple of two dictionaries
SERVICE_CATEGORIES = {
  "CategoryName": ["Subcat1", "Subcat2"]
}
LEVEL_3_SERVICES = {
  "CategoryName": {
    "Subcat1": ["Service1", "Service2"]
  }
}
```

### API Hierarchy Format
```json
{
  "CategoryName": {
    "id": "1",
    "name": "CategoryName",
    "subcategories": {
      "SubcatName": {
        "name": "SubcatName",
        "request_a_pro": true,
        "specific_services": ["Service1", "Service2"],
        "hardcoded_vendor": null
      }
    }
  }
}
```

## Migration Guide

### For Vendor Application Widget
```javascript
// OLD: Hardcoded data
const SERVICE_CATEGORIES = { /* hardcoded */ };

// NEW: Fetch from API
async function loadServiceData() {
  const response = await fetch('/api/v1/services/unified/vendor-app');
  const data = await response.json();
  return data.services;
}
```

### For Vendor Matching Routes
```python
# OLD: Import from service_categories.py
from api.services.service_categories import SERVICE_CATEGORIES

# NEW: Import from unified module
from api.services.unified_service_dictionary import get_vendor_matching_data
categories, level3 = get_vendor_matching_data()
```

### For Service Dictionary Routes
```python
# OLD: Direct import
from api.services.dockside_pros_service_dictionary import DOCKSIDE_PROS_SERVICES

# NEW: Use unified module
from api.services.unified_service_dictionary import get_api_hierarchy
hierarchy = get_api_hierarchy()
```

## Performance Considerations

- **Caching**: All format conversions are cached with 1-hour TTL
- **LRU Cache**: Frequently accessed data uses LRU caching
- **Singleton Pattern**: Single instance reduces memory usage
- **Lazy Loading**: Data transformed only when requested

## Testing

Run the comprehensive test suite:
```bash
python test_unified_services.py
```

Tests cover:
- Basic functionality
- All format conversions
- Validation logic
- Search functionality
- Caching performance
- Backwards compatibility

## Future Enhancements

1. **Database Backend**: Move from Python dict to database
2. **Admin UI**: Web interface for managing services
3. **Versioning**: Track changes over time
4. **Webhooks**: Notify consumers of changes
5. **GraphQL API**: More flexible queries

## Backwards Compatibility

Legacy functions are maintained for smooth migration:
```python
# These still work but use unified module internally
get_service_categories_for_vendor_matching()
get_level3_services_for_vendor_matching()
```

## Best Practices

1. **Always use the unified module** instead of direct imports
2. **Cache API responses** on the frontend when appropriate
3. **Validate selections** before processing
4. **Use search** for user-facing autocomplete features
5. **Monitor cache performance** in production

## Support

For issues or questions:
- Check test suite: `test_unified_services.py`
- Review module docstrings
- Check refactoring plan: `REFACTORING_PLAN_SINGLE_SOURCE_TRUTH.md`