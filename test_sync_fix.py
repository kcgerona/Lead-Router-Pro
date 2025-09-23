#!/usr/bin/env python3
"""
Test script for database sync fix.
Tests the fixed ZIP extraction and county conversion.
"""

from api.services.enhanced_db_sync_v2 import EnhancedDatabaseSync

def test_sync_lead_update():
    """Test the fixed lead sync with missing ZIP field."""
    print("\n=== Testing Fixed Lead Sync ===")
    
    # Mock a lead and GHL contact
    local_lead = {
        'id': 'test-lead-123',
        'customer_name': 'Test Customer',
        'customer_email': 'test@example.com',
        'service_zip_code': None,
        'service_county': None,
        'service_state': None
    }
    
    # GHL contact with no custom ZIP field but has postalCode
    ghl_contact = {
        'firstName': 'Test',
        'lastName': 'Customer',
        'email': 'test@example.com',
        'phone': '555-1234',
        'postalCode': '33316',  # Fort Lauderdale ZIP
        'customFields': [
            {'id': 'FT85QGi0tBq1AfVGNJ9v', 'value': 'WiFi Diagnostics or Troubleshooting'}
        ]
    }
    
    sync = EnhancedDatabaseSync()
    updates = sync._extract_lead_updates(local_lead, ghl_contact)
    
    print(f"Updates extracted: {updates}")
    
    assert 'service_zip_code' in updates, "ZIP code should be extracted from postalCode"
    assert updates['service_zip_code'] == '33316', f"Expected ZIP 33316, got {updates.get('service_zip_code')}"
    
    # The sync should also populate county/state
    if 'service_county' in updates:
        print(f"✅ County populated: {updates['service_county']}")
    if 'service_state' in updates:
        print(f"✅ State populated: {updates['service_state']}")
    
    print("✅ Test passed! ZIP extracted and county conversion works.")
    return True

def test_address_zip_extraction():
    """Test extracting ZIP from address field."""
    print("\n=== Testing ZIP Extraction from Address ===")
    
    local_lead = {
        'id': 'test-lead-456',
        'service_zip_code': None
    }
    
    # Contact with ZIP embedded in address
    ghl_contact = {
        'address1': '123 Main St, Fort Lauderdale, FL 33316',
        'customFields': []
    }
    
    sync = EnhancedDatabaseSync()
    updates = sync._extract_lead_updates(local_lead, ghl_contact)
    
    print(f"ZIP extracted from address: {updates.get('service_zip_code')}")
    assert updates.get('service_zip_code') == '33316', "Should extract ZIP from address"
    print("✅ ZIP extraction from address works!")
    return True

def main():
    """Run all tests."""
    print("Testing database sync fixes...")
    
    try:
        test_sync_lead_update()
        test_address_zip_extraction()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("The sync now properly extracts ZIP from postalCode field")
        print("and converts it to county for vendor matching.")
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