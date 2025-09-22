#!/usr/bin/env python3
"""Test script to check vendor sync for closing percentage"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.services.enhanced_db_sync_v2 import EnhancedDatabaseSync
from database.simple_connection import db as simple_db_instance
from config import AppConfig
import json

# Initialize sync service
sync_service = EnhancedDatabaseSync()

# Get the GHL contact
contact_id = 'KGCjsAqXviF31PUbA633'
print(f"Fetching GHL contact: {contact_id}")
ghl_contact = sync_service.ghl_api.get_contact_by_id(contact_id)

if not ghl_contact:
    print("Contact not found!")
    sys.exit(1)

# Show custom fields
print("\nCustom Fields from GHL:")
custom_fields = ghl_contact.get('customFields', [])
for field in custom_fields:
    field_id = field.get('id', '')
    field_value = field.get('value', '') or field.get('fieldValue', '')
    if field_id == 'OwHQipU7xdrHCpVswtnW':  # Lead Close Percentage
        print(f"  Lead Close Percentage (OwHQipU7xdrHCpVswtnW): '{field_value}'")
    elif field_id == 'HXVNT4y8OynNokWAfO2D':  # GHL User ID
        print(f"  GHL User ID (HXVNT4y8OynNokWAfO2D): '{field_value}'")

# Get account
account = simple_db_instance.get_account_by_ghl_location_id(AppConfig.GHL_LOCATION_ID)
if not account:
    print("No account found!")
    sys.exit(1)

# Get existing vendor
vendor_email = ghl_contact.get('email', '')
print(f"\nLooking for vendor with email: {vendor_email}")
existing_vendor = simple_db_instance.get_vendor_by_email_and_account(vendor_email, account['id'])

if existing_vendor:
    print(f"Found vendor: {existing_vendor['name']}")
    print(f"Current lead_close_percentage in DB: {existing_vendor.get('lead_close_percentage', 0)}")
    
    # Extract updates
    print("\nExtracting updates...")
    updates = sync_service._extract_vendor_updates(existing_vendor, ghl_contact)
    
    if updates:
        print(f"\nUpdates to apply: {json.dumps(updates, indent=2)}")
    else:
        print("\nNo updates needed")
else:
    print("Vendor not found in database!")