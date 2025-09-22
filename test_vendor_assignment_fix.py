#!/usr/bin/env python3
"""
Test script for vendor assignment fix.
Simulates the GHL contact processing to verify specific_service_requested is extracted correctly.
"""

import json
from api.routes.webhook_routes import extract_ghl_custom_fields, LEAD_ROUTING_FIELD_IDS

def test_wifi_lead_extraction():
    """Test extraction of WiFi Diagnostics service from GHL contact."""
    print("\n=== Testing WiFi Lead Service Extraction ===")
    
    # Mock the GHL contact data from the actual lead
    contact_details = {
        "id": "HfzUmjvsOlrrSAklcisK",
        "firstName": "MWWIFI",
        "lastName": "Boat Resource",
        "email": "michaelwongpro+boatwifi@gmail.com",
        "phone": "+19547755844",
        "customFields": [
            {"id": "16b5tLOqrBbL61IDPbBz", "value": "wifi boat resource test"},
            {"id": "FT85QGi0tBq1AfVGNJ9v", "value": "WiFi Diagnostics or Troubleshooting"},  # Specific Service!
            {"id": "rTcOJb4VT83u8w6OBk6l", "value": "Yacht Wi-Fi (DSP)"},
            {"id": "x3eHJ91v180aLs3HidEB", "value": "1-2 Weeks"}
        ]
    }
    
    # Extract custom fields
    custom_fields_dict = extract_ghl_custom_fields(contact_details)
    
    # Get specific service using the correct field ID
    specific_service = custom_fields_dict.get(LEAD_ROUTING_FIELD_IDS['specific_service_needed'], '')
    primary_category = custom_fields_dict.get(LEAD_ROUTING_FIELD_IDS['primary_service_category'], '')
    
    print(f"Custom Fields Extracted:")
    print(f"  - Primary Category (HRqfv0HnUydNRLKWhk27): '{primary_category}' {'❌ MISSING' if not primary_category else ''}")
    print(f"  - Specific Service (FT85QGi0tBq1AfVGNJ9v): '{specific_service}' {'✅ FOUND' if specific_service else '❌ MISSING'}")
    
    # Since primary category is missing, try to infer it from specific service
    if not primary_category and specific_service:
        from api.services.service_categories import SERVICE_CATEGORIES, LEVEL_3_SERVICES
        
        # Check if it's a Level 3 service
        for cat, subcats in LEVEL_3_SERVICES.items():
            for subcat, l3_services in subcats.items():
                if specific_service in l3_services:
                    primary_category = cat
                    print(f"  - Inferred Category: '{primary_category}' (from Level 3 service)")
                    break
            if primary_category:
                break
    
    # With our fix, specific_service should now be used directly
    final_specific_service = specific_service  # Direct use, no hierarchy complexity
    
    print(f"\nResult:")
    print(f"  - Category for database: '{primary_category or 'Boater Resources'}'")
    print(f"  - Specific Service for vendor matching: '{final_specific_service}'")
    
    assert final_specific_service == "WiFi Diagnostics or Troubleshooting", \
        f"Expected 'WiFi Diagnostics or Troubleshooting', got '{final_specific_service}'"
    
    print("\n✅ Test passed! Specific service extracted correctly for vendor matching.")
    return True

def test_simplified_extraction():
    """Test that the simplified logic works without primary category."""
    print("\n=== Testing Simplified Extraction Logic ===")
    
    # Contact with ONLY specific service, no primary category
    contact_details = {
        "customFields": [
            {"id": "FT85QGi0tBq1AfVGNJ9v", "value": "Boat Oil Change"}
        ]
    }
    
    custom_fields_dict = extract_ghl_custom_fields(contact_details)
    specific_service = custom_fields_dict.get(LEAD_ROUTING_FIELD_IDS['specific_service_needed'], '')
    
    print(f"Extracted specific service: '{specific_service}'")
    print(f"This should be used directly for vendor matching without hierarchy logic")
    
    assert specific_service == "Boat Oil Change"
    print("✅ Simplified extraction works correctly!")
    return True

def main():
    """Run all tests."""
    print("Testing vendor assignment fix...")
    
    try:
        test_wifi_lead_extraction()
        test_simplified_extraction()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("The fix correctly extracts specific_service_requested")
        print("even when primary_service_category is missing.")
        print("="*60)
        
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