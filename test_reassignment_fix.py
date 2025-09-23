#!/usr/bin/env python3
"""
Test script to verify lead reassignment with fixed location data
"""

import asyncio
import sys
sys.path.append('/root/Lead-Router-Pro')

from api.services.lead_reassignment_core import lead_reassignment_core

async def test_reassignment():
    """Test lead reassignment for the WiFi diagnostics lead"""
    
    print("Testing lead reassignment for contact: 25srGWhdam4nNRlqzGfJ")
    print("Lead email: joem@testwifi.com")
    print("Service: WiFi Diagnostics or Troubleshooting")
    print("Location: 33109 (Miami-Dade, FL)")
    print("-" * 50)
    
    try:
        # Test reassignment
        result = await lead_reassignment_core.reassign_lead(
            contact_id="25srGWhdam4nNRlqzGfJ",
            opportunity_id=None,
            exclude_previous=True,
            reason="manual_test",
            preserve_source=True
        )
        
        if result.get("success"):
            print("✅ Reassignment successful!")
            print(f"   Lead ID: {result.get('lead_id')}")
            print(f"   New Vendor: {result.get('vendor_name')} (ID: {result.get('new_vendor_id')})")
            print(f"   Previous Vendor ID: {result.get('previous_vendor_id')}")
            print(f"   Opportunity ID: {result.get('opportunity_id')}")
            print(f"   Message: {result.get('message')}")
        else:
            print(f"❌ Reassignment failed: {result.get('error')}")
            print(f"   Contact ID: {result.get('contact_id')}")
            print(f"   Lead ID: {result.get('lead_id')}")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_reassignment())