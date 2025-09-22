#!/usr/bin/env python3
"""
Test script for webhook_routes refactoring.
Tests the new GHL custom fields extraction and service hierarchy determination.
"""

import json
from api.routes.webhook_routes import (
    extract_ghl_custom_fields,
    map_ghl_contact_to_lead,
    determine_service_hierarchy,
    LEAD_ROUTING_FIELD_IDS
)

def test_custom_fields_extraction():
    """Test extraction of GHL custom fields."""
    print("\n=== Testing Custom Fields Extraction ===")
    
    # Mock GHL contact with custom fields
    contact_details = {
        "firstName": "John",
        "lastName": "Doe",
        "email": "john@example.com",
        "customFields": [
            {"id": "HRqfv0HnUydNRLKWhk27", "value": "Boat Maintenance"},  # Primary Service Category
            {"id": "FT85QGi0tBq1AfVGNJ9v", "value": "Boat Oil Change"},    # Specific Service Needed
            {"id": "O84LyhN1QjZ8Zz5mteCM", "value": "Engine Services"},    # Vendor capability (should ignore)
            {"id": "someOtherId", "value": "Some Value"}
        ]
    }
    
    custom_fields_dict = extract_ghl_custom_fields(contact_details)
    print(f"Extracted fields: {json.dumps(custom_fields_dict, indent=2)}")
    
    # Verify correct extraction
    assert custom_fields_dict[LEAD_ROUTING_FIELD_IDS['primary_service_category']] == "Boat Maintenance"
    assert custom_fields_dict[LEAD_ROUTING_FIELD_IDS['specific_service_needed']] == "Boat Oil Change"
    print("✅ Custom fields extracted correctly")
    return True

def test_service_hierarchy_level2():
    """Test service hierarchy for Level 2 services (no Level 3)."""
    print("\n=== Testing Service Hierarchy - Level 2 ===")
    
    # Test Boat Maintenance -> Boat Oil Change (Level 2 service)
    result = determine_service_hierarchy("Boat Maintenance", "Boat Oil Change")
    print(f"Result for Boat Maintenance -> Boat Oil Change: {json.dumps(result, indent=2)}")
    
    assert result['primary_service_category'] == "Boat Maintenance"
    assert result['specific_service_requested'] == "Boat Oil Change"
    assert result['service_level'] == 'level2'
    print("✅ Level 2 service correctly identified as specific service")
    return True

def test_service_hierarchy_level3():
    """Test service hierarchy for Level 3 services."""
    print("\n=== Testing Service Hierarchy - Level 3 ===")
    
    # Test Boat and Yacht Repair -> Hull Crack or Structural Repair (Level 3 service)
    result = determine_service_hierarchy("Boat and Yacht Repair", "Hull Crack or Structural Repair")
    print(f"Result for Boat and Yacht Repair -> Hull Crack: {json.dumps(result, indent=2)}")
    
    assert result['primary_service_category'] == "Boat and Yacht Repair"
    assert result['specific_service_requested'] == "Hull Crack or Structural Repair"
    assert result['service_level'] == 'level3'
    print("✅ Level 3 service correctly identified")
    return True

def test_full_mapping_flow():
    """Test the complete mapping flow with ServiceDictionaryMapper."""
    print("\n=== Testing Full Mapping Flow ===")
    
    # Mock GHL contact with custom fields
    contact_details = {
        "firstName": "Jane",
        "lastName": "Smith",
        "email": "jane@example.com",
        "phone": "555-1234",
        "customFields": [
            {"id": "HRqfv0HnUydNRLKWhk27", "value": "Boat Maintenance"},
            {"id": "FT85QGi0tBq1AfVGNJ9v", "value": "Boat Oil Change"},
        ]
    }
    
    # Test the full mapping function
    mapping_result = map_ghl_contact_to_lead(contact_details)
    print(f"Mapping result: {json.dumps(mapping_result, indent=2)}")
    
    standardized_fields = mapping_result.get('standardized_fields', {})
    service_classification = mapping_result.get('service_classification', {})
    
    print(f"\nStandardized fields: {list(standardized_fields.keys())}")
    print(f"Service classification: {service_classification}")
    
    print("✅ Full mapping flow completed")
    return True

def main():
    """Run all tests."""
    print("Starting webhook refactoring tests...")
    
    try:
        test_custom_fields_extraction()
        test_service_hierarchy_level2()
        test_service_hierarchy_level3()
        test_full_mapping_flow()
        
        print("\n" + "="*50)
        print("✅ ALL TESTS PASSED!")
        print("="*50)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())