#!/usr/bin/env python3
"""
Enhanced Database Sync Module for Lead Router Pro
Synchronizes specific fields between GoHighLevel and local database
Only updates existing records with targeted field synchronization

Author: Lead Router Pro Team
Created: 2025
"""

import json
import logging
import sys
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import time

# Add project root to path (going up two directories from api/services/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import project modules
from config import AppConfig
from api.services.ghl_api import GoHighLevelAPI
from api.services.ghl_api_v2_optimized import OptimizedGoHighLevelAPI
from api.services.location_service import location_service
from database.simple_connection import db as simple_db_instance

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedDatabaseSync:
    """
    Enhanced sync service that updates existing database records
    with current data from GoHighLevel
    """
    
    # GHL Field Mappings for Vendors
    VENDOR_GHL_FIELDS = {
        # Database Field: GHL Custom Field ID
        'ghl_user_id': 'HXVNT4y8OynNokWAfO2D',          # GHL User ID
        'name': ['firstName', 'lastName'],               # Standard GHL fields
        'email': 'email',                                # Standard field
        'phone': 'phone',                                # Standard field
        'company_name': 'JexVrg2VNhnwIX7YlyJV',         # Vendor Company Name
        'service_categories': ['72qwwzy4AUfTCBJvBIEf', 'O84LyhN1QjZ8Zz5mteCM'],   # Try both: Service Categories Selections OR Service Category
        'services_offered': 'pAq9WBsIuFUAZuwz3YY4',     # Services Provided
        'service_zip_codes': 'yDcN0FmwI3xacyxAuTWs',    # Service Zip Codes (contains coverage data)
        'taking_new_work': 'bTFOs5zXYt85AvDJJUAb',      # Taking New Work?
        'last_lead_assigned': 'NbsJTMv3EkxqNfwx8Jh4',   # Last Lead Assigned
        'lead_close_percentage': 'OwHQipU7xdrHCpVswtnW', # Lead Close %
        'primary_service_category': 'HRqfv0HnUydNRLKWhk27' # Primary Service Category
        # NOTE: coverage_type, coverage_states, coverage_counties are derived from service_zip_codes
    }
    
    # GHL Field Mappings for Leads
    LEAD_GHL_FIELDS = {
        # Database Field: GHL Custom Field ID
        'customer_name': ['firstName', 'lastName'],      # Standard fields
        'customer_email': 'email',                       # Standard field
        'customer_phone': 'phone',                       # Standard field
        'primary_service_category': 'HRqfv0HnUydNRLKWhk27', # Primary Service Category
        'specific_service_requested': 'FT85QGi0tBq1AfVGNJ9v', # Specific Service Needed
        'customer_zip_code': 'RmAja1dnU0u42ECXhCo9',   # ZIP Code of Service
        'service_county': None,  # Derived from ZIP
        'service_state': None    # Derived from ZIP
    }
    
    def __init__(self):
        """Initialize the enhanced sync service"""
        try:
            # Load environment variables
            from dotenv import load_dotenv
            load_dotenv()
            import os
            
            # Initialize GHL API with environment variables
            # Use optimized v2 API for better performance
            self.ghl_api = OptimizedGoHighLevelAPI(
                private_token=os.getenv('GHL_PRIVATE_TOKEN') or AppConfig.GHL_PRIVATE_TOKEN,
                location_id=os.getenv('GHL_LOCATION_ID') or AppConfig.GHL_LOCATION_ID,
                agency_api_key=os.getenv('GHL_AGENCY_API_KEY') or AppConfig.GHL_AGENCY_API_KEY,
                location_api_key=os.getenv('GHL_LOCATION_API') or AppConfig.GHL_LOCATION_API  # Keep for fallback
            )
            
            # Track sync statistics
            self.stats = {
                'vendors_checked': 0,
                'vendors_updated': 0,
                'vendors_skipped': 0,
                'vendors_errors': 0,
                'leads_checked': 0,
                'leads_updated': 0,
                'leads_skipped': 0,
                'leads_errors': 0,
                'fields_updated': 0,
                'start_time': None,
                'end_time': None
            }
            
            logger.info("✅ Enhanced Database Sync initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Enhanced Sync: {e}")
            raise
    
    def sync_single_vendor(self, ghl_contact_id: str) -> Dict[str, Any]:
        """
        Sync a single vendor by GHL contact ID
        Designed to be called from GHL automation/webhook
        
        Args:
            ghl_contact_id: The GHL contact ID to sync (required)
            
        Returns:
            Dict with success status and details
        """
        logger.info(f"🔄 Single vendor sync requested for contact: {ghl_contact_id}")
        
        if not ghl_contact_id:
            return {
                'success': False,
                'error': 'ghl_contact_id is required'
            }
        
        try:
            # Get vendor from database using GHL contact ID
            vendor = simple_db_instance.get_vendor_by_ghl_contact_id(ghl_contact_id)
            
            if not vendor:
                return {
                    'success': False,
                    'error': f'Vendor not found in database for contact ID: {ghl_contact_id}'
                }
            
            # Get contact from GHL
            logger.info(f"📡 Fetching GHL contact {ghl_contact_id}")
            ghl_contact = self.ghl_api.get_contact_by_id(ghl_contact_id)
            
            if not ghl_contact:
                return {
                    'success': False,
                    'error': 'Could not fetch contact from GHL'
                }
            
            # Extract updates
            updates = self._extract_vendor_updates(vendor, ghl_contact)
            
            if updates:
                # Apply updates
                success = self._update_vendor_record(vendor['id'], updates)
                if success:
                    logger.info(f"✅ Updated vendor {vendor.get('name')}: {len(updates)} fields")
                    return {
                        'success': True,
                        'vendor_id': vendor['id'],
                        'vendor_name': vendor.get('name'),
                        'fields_updated': len(updates),
                        'updates': list(updates.keys())
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to update database'
                    }
            else:
                logger.info(f"ℹ️ No updates needed for vendor {vendor.get('name')}")
                return {
                    'success': True,
                    'vendor_id': vendor['id'],
                    'vendor_name': vendor.get('name'),
                    'fields_updated': 0,
                    'message': 'Already in sync'
                }
            
        except Exception as e:
            logger.error(f"❌ Single vendor sync failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def sync_all(self) -> Dict[str, Any]:
        """
        Main sync function that updates both vendors and leads
        Returns comprehensive statistics about the sync operation
        """
        logger.info("🔄 Starting Enhanced Database Sync")
        logger.info("=" * 60)
        
        self.stats['start_time'] = datetime.now()
        
        try:
            # Step 1: Sync Vendors
            logger.info("\n📊 STEP 1: Syncing Vendor Records")
            vendor_results = self._sync_vendors()
            
            # Step 2: Sync Leads
            logger.info("\n📊 STEP 2: Syncing Lead Records")
            lead_results = self._sync_leads()
            
            self.stats['end_time'] = datetime.now()
            
            # Calculate duration
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            # Generate summary
            logger.info("\n" + "=" * 60)
            logger.info("🎉 ENHANCED SYNC COMPLETED")
            logger.info(f"⏱️  Duration: {duration:.2f} seconds")
            logger.info(f"\n📈 VENDOR SYNC RESULTS:")
            logger.info(f"   Checked: {self.stats['vendors_checked']}")
            logger.info(f"   Updated: {self.stats['vendors_updated']}")
            logger.info(f"   Skipped: {self.stats['vendors_skipped']}")
            logger.info(f"   Errors: {self.stats['vendors_errors']}")
            logger.info(f"\n📈 LEAD SYNC RESULTS:")
            logger.info(f"   Checked: {self.stats['leads_checked']}")
            logger.info(f"   Updated: {self.stats['leads_updated']}")
            logger.info(f"   Skipped: {self.stats['leads_skipped']}")
            logger.info(f"   Errors: {self.stats['leads_errors']}")
            logger.info(f"\n✏️  Total Fields Updated: {self.stats['fields_updated']}")
            
            return {
                'success': True,
                'stats': self.stats,
                'duration': duration,
                'message': f"Successfully synced {self.stats['vendors_updated']} vendors and {self.stats['leads_updated']} leads"
            }
            
        except Exception as e:
            logger.error(f"❌ Sync failed: {e}")
            self.stats['end_time'] = datetime.now()
            return {
                'success': False,
                'stats': self.stats,
                'error': str(e),
                'message': f"Sync failed: {str(e)}"
            }
    
    def _sync_vendors(self) -> Dict[str, int]:
        """Sync vendor records with targeted field updates"""
        
        try:
            # Get all vendors from database
            vendors = simple_db_instance.get_vendors()
            logger.info(f"Found {len(vendors)} vendors in database")
            
            # Filter to only active vendors with GHL User IDs
            active_vendors = []
            for vendor in vendors:
                if vendor.get('ghl_user_id'):
                    active_vendors.append(vendor)
                else:
                    logger.debug(f"⏭️ Skipping inactive vendor {vendor.get('name', 'Unknown')} - no GHL User ID")
            
            logger.info(f"🎯 Processing {len(active_vendors)} active vendors (with GHL User IDs)")
            
            for vendor in active_vendors:
                self.stats['vendors_checked'] += 1
                
                # Must have GHL contact ID to sync
                ghl_contact_id = vendor.get('ghl_contact_id')
                if not ghl_contact_id:
                    logger.warning(f"⚠️ Active vendor {vendor.get('name', 'Unknown')} has GHL User ID but no GHL contact ID")
                    self.stats['vendors_skipped'] += 1
                    continue
                
                try:
                    # Get contact from GHL
                    logger.info(f"📊 Processing vendor: {vendor.get('name', 'Unknown')} (Company: {vendor.get('company_name', 'N/A')})")
                    logger.debug(f"   GHL Contact ID: {ghl_contact_id}")
                    logger.debug(f"   Current status: {vendor.get('status')}")
                    logger.debug(f"   Current coverage: {vendor.get('coverage_type')}")
                    
                    ghl_contact = self.ghl_api.get_contact_by_id(ghl_contact_id)
                    
                    if not ghl_contact:
                        logger.warning(f"⚠️ No GHL contact found for ID: {ghl_contact_id}")
                        self.stats['vendors_skipped'] += 1
                        continue
                    
                    # Extract and compare fields
                    updates = self._extract_vendor_updates(vendor, ghl_contact)
                    
                    if updates:
                        # Update vendor in database
                        success = self._update_vendor_record(vendor['id'], updates)
                        if success:
                            self.stats['vendors_updated'] += 1
                            self.stats['fields_updated'] += len(updates)
                            logger.info(f"✅ Updated vendor {vendor.get('name')}: {len(updates)} fields")
                        else:
                            self.stats['vendors_errors'] += 1
                    else:
                        self.stats['vendors_skipped'] += 1
                        logger.debug(f"⏭️  No updates needed for vendor {vendor.get('name')}")
                    
                    # Small delay to avoid API rate limits
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing vendor {vendor.get('name')}: {e}")
                    self.stats['vendors_errors'] += 1
            
            return {
                'checked': self.stats['vendors_checked'],
                'updated': self.stats['vendors_updated'],
                'errors': self.stats['vendors_errors']
            }
            
        except Exception as e:
            logger.error(f"❌ Error in vendor sync: {e}")
            return {'checked': 0, 'updated': 0, 'errors': 1}
    
    def _sync_leads(self) -> Dict[str, int]:
        """Sync lead records with targeted field updates"""
        
        try:
            # Get all leads from database
            conn = simple_db_instance._get_raw_conn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, ghl_contact_id, customer_name, customer_email, 
                       customer_phone, primary_service_category, 
                       specific_service_requested, customer_zip_code,
                       service_county, service_state
                FROM leads 
                WHERE ghl_contact_id IS NOT NULL
            """)
            
            leads = []
            for row in cursor.fetchall():
                leads.append({
                    'id': row[0],
                    'ghl_contact_id': row[1],
                    'customer_name': row[2],
                    'customer_email': row[3],
                    'customer_phone': row[4],
                    'primary_service_category': row[5],
                    'specific_service_requested': row[6],
                    'customer_zip_code': row[7],
                    'service_county': row[8],
                    'service_state': row[9]
                })
            
            conn.close()
            
            logger.info(f"Found {len(leads)} leads with GHL contact IDs")
            
            for lead in leads:
                self.stats['leads_checked'] += 1
                
                try:
                    # Get contact from GHL
                    logger.debug(f"Fetching GHL data for lead: {lead.get('customer_name', 'Unknown')}")
                    ghl_contact = self.ghl_api.get_contact_by_id(lead['ghl_contact_id'])
                    
                    if not ghl_contact:
                        logger.warning(f"⚠️ No GHL contact found for lead ID: {lead['ghl_contact_id']}")
                        self.stats['leads_skipped'] += 1
                        continue
                    
                    # Extract and compare fields
                    updates = self._extract_lead_updates(lead, ghl_contact)
                    
                    if updates:
                        # Update lead in database
                        success = self._update_lead_record(lead['id'], updates)
                        if success:
                            self.stats['leads_updated'] += 1
                            self.stats['fields_updated'] += len(updates)
                            logger.info(f"✅ Updated lead {lead.get('customer_name')}: {len(updates)} fields")
                        else:
                            self.stats['leads_errors'] += 1
                    else:
                        self.stats['leads_skipped'] += 1
                        logger.debug(f"⏭️  No updates needed for lead {lead.get('customer_name')}")
                    
                    # Small delay to avoid API rate limits
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing lead {lead.get('customer_name')}: {e}")
                    self.stats['leads_errors'] += 1
            
            return {
                'checked': self.stats['leads_checked'],
                'updated': self.stats['leads_updated'],
                'errors': self.stats['leads_errors']
            }
            
        except Exception as e:
            logger.error(f"❌ Error in lead sync: {e}")
            return {'checked': 0, 'updated': 0, 'errors': 1}
    
    def _extract_vendor_updates(self, vendor: Dict, ghl_contact: Dict) -> Dict[str, Any]:
        """Extract fields that need updating for a vendor"""
        updates = {}
        
        # Extract custom fields from GHL contact
        custom_fields = {}
        for field in ghl_contact.get('customFields', []):
            field_id = field.get('id', '')
            field_value = field.get('value', '') or field.get('fieldValue', '')
            if field_id:
                custom_fields[field_id] = field_value
        
        # CRITICAL: Check for GHL User ID and activate vendor if found
        ghl_user_id_from_contact = custom_fields.get('HXVNT4y8OynNokWAfO2D', '').strip()
        if ghl_user_id_from_contact:
            # If vendor has a GHL user ID in GHL but not in DB, update it
            if not vendor.get('ghl_user_id'):
                updates['ghl_user_id'] = ghl_user_id_from_contact
                logger.info(f"   ✅ Found GHL User ID in contact: {ghl_user_id_from_contact}")
            
            # If vendor has GHL user ID but status is not active, activate them
            if vendor.get('status') != 'active':
                updates['status'] = 'active'
                logger.info(f"   ✅ Activating vendor - GHL User ID present: {ghl_user_id_from_contact}")
        
        # Process service_zip_codes to derive coverage fields
        service_zip_codes_value = custom_fields.get('yDcN0FmwI3xacyxAuTWs', '').strip()
        derived_coverage_type = None
        derived_coverage_states = None
        derived_coverage_counties = None
        
        if service_zip_codes_value:
            logger.info(f"   📍 Processing service_zip_codes: {service_zip_codes_value[:100]}...")
            
            # Normalize the value for comparison
            normalized_value = service_zip_codes_value.upper().strip()
            
            # Determine coverage type based on the format of service_zip_codes
            if 'GLOBAL' in normalized_value:
                derived_coverage_type = 'global'
                derived_coverage_states = []
                derived_coverage_counties = []
                logger.info(f"   🌍 Detected GLOBAL coverage")
            elif 'NATIONAL' in normalized_value or normalized_value in ['USA', 'UNITED STATES']:
                derived_coverage_type = 'national'
                derived_coverage_states = []
                derived_coverage_counties = []
                logger.info(f"   🇺🇸 Detected NATIONAL coverage")
            elif ';' in service_zip_codes_value:
                # Semi-colon separated list - likely counties
                items = [s.strip() for s in service_zip_codes_value.split(';') if s.strip()]
                
                # Check if items look like counties (contain comma and state code)
                if items and ', ' in items[0]:
                    derived_coverage_type = 'county'
                    derived_coverage_counties = items
                    
                    # Extract unique states from counties
                    states_set = set()
                    for county in derived_coverage_counties:
                        if ', ' in county:
                            state_part = county.split(', ')[-1].strip()
                            # Validate it's a 2-letter state code
                            if len(state_part) == 2 and state_part.isupper():
                                states_set.add(state_part)
                    derived_coverage_states = sorted(list(states_set))
                    logger.info(f"   📍 Detected COUNTY coverage: {len(derived_coverage_counties)} counties in {len(derived_coverage_states)} states")
            elif ',' in service_zip_codes_value:
                # Comma separated - could be states or counties
                items = [s.strip() for s in service_zip_codes_value.split(',') if s.strip()]
                
                # Check if all items are 2-letter state codes
                if all(len(item) == 2 and item.isupper() for item in items):
                    derived_coverage_type = 'state'
                    derived_coverage_states = items
                    derived_coverage_counties = []
                    logger.info(f"   📍 Detected STATE coverage: {len(derived_coverage_states)} states")
                # Check if items contain state suffixes (like "Broward County, FL")
                elif any(', ' in item for item in items):
                    derived_coverage_type = 'county'
                    derived_coverage_counties = items
                    
                    # Extract states
                    states_set = set()
                    for county in items:
                        if ', ' in county:
                            state_part = county.split(', ')[-1].strip()
                            if len(state_part) == 2 and state_part.isupper():
                                states_set.add(state_part)
                    derived_coverage_states = sorted(list(states_set))
                    logger.info(f"   📍 Detected COUNTY coverage: {len(derived_coverage_counties)} counties")
                else:
                    # Could be ZIP codes - check if they're numeric
                    if all(item.isdigit() and len(item) == 5 for item in items[:3] if item):
                        logger.info(f"   📍 Detected ZIP codes - preserving as-is")
                    else:
                        logger.debug(f"   ❓ Could not determine coverage type from: {service_zip_codes_value[:50]}...")
        
        # Check each mapped field
        for db_field, ghl_field in self.VENDOR_GHL_FIELDS.items():
            # Skip fields that are handled separately (like service_zip_codes which becomes coverage fields)
            if db_field == 'service_zip_codes':
                continue
                
            current_value = vendor.get(db_field)
            new_value = None
            
            # Handle different field types
            if db_field == 'name' and ghl_field == ['firstName', 'lastName']:
                # Special case: Combine firstName and lastName for name field
                first = ghl_contact.get('firstName', '').strip()
                last = ghl_contact.get('lastName', '').strip()
                new_value = f"{first} {last}".strip()
            elif ghl_field in ['email', 'phone']:
                # Standard contact fields
                new_value = ghl_contact.get(ghl_field, '').strip()
            elif isinstance(ghl_field, list):
                # Handle multiple possible field IDs (e.g., service_categories)
                # Try each field ID until we find one with a value
                new_value = ''
                for field_id in ghl_field:
                    temp_value = custom_fields.get(field_id, '').strip()
                    if temp_value:
                        new_value = temp_value
                        logger.info(f"   📋 Found {db_field} in field ID {field_id}: {temp_value[:50]}...")
                        break
                if not new_value:
                    logger.debug(f"   ⚠️ No value found for {db_field} in any of the field IDs: {ghl_field}")
            else:
                # Custom field (single field ID)
                new_value = custom_fields.get(ghl_field, '').strip()
                if new_value:
                    logger.debug(f"   📋 Found {db_field}: {new_value[:50]}...")
            
            # Skip if GHL has no value for optional fields
            if not new_value and db_field not in ['lead_close_percentage', 'service_categories', 'services_offered']:
                logger.debug(f"   Skipping {db_field}: No value in GHL")
                continue
            
            # Special handling for certain fields
            if db_field in ['service_categories', 'services_offered']:
                # Convert comma-separated to JSON array
                if new_value:
                    # Parse the comma-separated values into a list
                    parsed_list = [s.strip() for s in new_value.split(',') if s.strip()]
                    new_value = json.dumps(parsed_list)
                    logger.info(f"   🔄 Parsed {db_field}: {len(parsed_list)} items")
                else:
                    # For empty values, set as empty array
                    new_value = json.dumps([])
                    logger.debug(f"   🔄 Setting {db_field} to empty array")
            
            elif db_field == 'lead_close_percentage':
                # Convert percentage to float
                if new_value:
                    try:
                        new_value = float(new_value.replace('%', '').strip())
                    except:
                        new_value = 0.0
                else:
                    new_value = 0.0
            
            elif db_field == 'taking_new_work':
                # Normalize Yes/No values to boolean
                if new_value:
                    normalized = new_value.strip().lower()
                    if normalized in ['yes', 'true', '1']:
                        new_value = 'Yes'
                    elif normalized in ['no', 'false', '0']:
                        new_value = 'No'
                    else:
                        new_value = new_value.strip().title()
            
            elif db_field == 'primary_service_category':
                # Keep as string - it's a single category
                if new_value:
                    logger.info(f"   🎯 Primary service category: {new_value}")
            
            elif db_field == 'last_lead_assigned':
                # Keep timestamp as-is from GHL
                if new_value:
                    logger.debug(f"   📅 Last lead assigned: {new_value}")
            
            # Compare and add to updates if different
            if new_value is not None and self._values_differ(current_value, new_value, db_field):
                updates[db_field] = new_value
                logger.debug(f"   {db_field}: '{current_value}' → '{new_value}'")
        
        # Add derived coverage fields ONLY if we successfully determined them
        if derived_coverage_type:
            # Update coverage_type if different or empty
            if vendor.get('coverage_type') != derived_coverage_type:
                updates['coverage_type'] = derived_coverage_type
                logger.info(f"   ✅ Updated coverage_type: {vendor.get('coverage_type')} → {derived_coverage_type}")
            
            # Update states if we have them
            if derived_coverage_states is not None:
                states_json = json.dumps(derived_coverage_states)
                if self._values_differ(vendor.get('coverage_states'), states_json, 'coverage_states'):
                    updates['coverage_states'] = states_json
                    logger.info(f"   ✅ Updated coverage_states: {len(derived_coverage_states)} states")
            
            # Update counties if we have them  
            if derived_coverage_counties is not None:
                counties_json = json.dumps(derived_coverage_counties)
                if self._values_differ(vendor.get('coverage_counties'), counties_json, 'coverage_counties'):
                    updates['coverage_counties'] = counties_json
                    logger.info(f"   ✅ Updated coverage_counties: {len(derived_coverage_counties)} counties")
        else:
            # No valid coverage type determined - log but don't update
            if service_zip_codes_value:
                logger.debug(f"   ⚠️ Could not parse coverage from service_zip_codes, keeping existing values")
        
        return updates
    
    def _extract_lead_updates(self, lead: Dict, ghl_contact: Dict) -> Dict[str, Any]:
        """Extract fields that need updating for a lead"""
        updates = {}
        
        # Extract custom fields from GHL contact
        custom_fields = {}
        for field in ghl_contact.get('customFields', []):
            field_id = field.get('id', '')
            field_value = field.get('value', '') or field.get('fieldValue', '')
            if field_id:
                custom_fields[field_id] = field_value
        
        # Check each mapped field
        for db_field, ghl_field in self.LEAD_GHL_FIELDS.items():
            current_value = lead.get(db_field)
            
            # Handle standard fields
            if isinstance(ghl_field, list):
                # Combine firstName and lastName for name field
                if db_field == 'customer_name' and ghl_field == ['firstName', 'lastName']:
                    first = ghl_contact.get('firstName', '').strip()
                    last = ghl_contact.get('lastName', '').strip()
                    new_value = f"{first} {last}".strip()
                else:
                    continue
            elif ghl_field in ['email', 'phone']:
                # Map to customer_ prefixed fields
                if db_field == 'customer_email':
                    new_value = ghl_contact.get('email', '').strip()
                elif db_field == 'customer_phone':
                    new_value = ghl_contact.get('phone', '').strip()
                else:
                    new_value = ghl_contact.get(ghl_field, '').strip()
            elif ghl_field is None:
                # Skip derived fields (will handle separately)
                continue
            else:
                # Custom field
                new_value = custom_fields.get(ghl_field, '').strip()
            
            # Compare and add to updates if different
            if self._values_differ(current_value, new_value, db_field):
                updates[db_field] = new_value
                logger.debug(f"   {db_field}: '{current_value}' → '{new_value}'")
        
        # Handle derived fields (county and state from ZIP)
        zip_code = custom_fields.get(self.LEAD_GHL_FIELDS['customer_zip_code'], '').strip()
        if zip_code and zip_code != lead.get('customer_zip_code'):
            updates['customer_zip_code'] = zip_code
            
            # Get county and state from ZIP
            location_data = location_service.zip_to_location(zip_code)
            if not location_data.get('error'):
                county = location_data.get('county', '')
                state = location_data.get('state', '')
                
                if county != lead.get('service_county'):
                    updates['service_county'] = county
                if state != lead.get('service_state'):
                    updates['service_state'] = state
        
        return updates
    
    def _values_differ(self, current: Any, new: Any, field_name: str) -> bool:
        """Check if two values are different, handling various data types"""
        
        # Handle None values
        if current is None and new == '':
            return False
        if current == '' and new is None:
            return False
        
        # Handle JSON fields
        if field_name in ['service_categories', 'services_offered', 'coverage_states', 'coverage_counties']:
            try:
                current_list = json.loads(current) if current else []
                new_list = json.loads(new) if new else []
                return set(current_list) != set(new_list)
            except:
                return str(current) != str(new)
        
        # Handle numeric fields
        if field_name == 'lead_close_percentage':
            try:
                current_float = float(current) if current else 0.0
                new_float = float(new) if new else 0.0
                return abs(current_float - new_float) > 0.01
            except:
                return str(current) != str(new)
        
        # Default string comparison
        return str(current or '').strip() != str(new or '').strip()
    
    def _update_vendor_record(self, vendor_id: str, updates: Dict[str, Any]) -> bool:
        """Update vendor record in database"""
        try:
            if not updates:
                return True
            
            # Build UPDATE query
            set_clauses = []
            values = []
            
            for field, value in updates.items():
                set_clauses.append(f"{field} = ?")
                values.append(value)
            
            # Add updated_at
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            
            # Add vendor_id for WHERE clause
            values.append(vendor_id)
            
            # Execute update
            conn = simple_db_instance._get_raw_conn()
            cursor = conn.cursor()
            
            query = f"""
                UPDATE vendors 
                SET {', '.join(set_clauses)}
                WHERE id = ?
            """
            
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating vendor {vendor_id}: {e}")
            return False
    
    def _update_lead_record(self, lead_id: str, updates: Dict[str, Any]) -> bool:
        """Update lead record in database"""
        try:
            if not updates:
                return True
            
            # Build UPDATE query
            set_clauses = []
            values = []
            
            for field, value in updates.items():
                set_clauses.append(f"{field} = ?")
                values.append(value)
            
            # Add updated_at
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            
            # Add lead_id for WHERE clause
            values.append(lead_id)
            
            # Execute update
            conn = simple_db_instance._get_raw_conn()
            cursor = conn.cursor()
            
            query = f"""
                UPDATE leads 
                SET {', '.join(set_clauses)}
                WHERE id = ?
            """
            
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating lead {lead_id}: {e}")
            return False


# Main function for standalone testing
if __name__ == "__main__":
    """Test the enhanced sync module directly"""
    
    print("🚀 ENHANCED DATABASE SYNC - STANDALONE TEST")
    print("=" * 60)
    print("This will sync specific fields from GoHighLevel to your database")
    print("Only existing records with GHL contact IDs will be updated")
    print("")
    
    try:
        # Initialize and run sync
        sync_service = EnhancedDatabaseSync()
        results = sync_service.sync_all()
        
        if results['success']:
            print("\n✅ Sync completed successfully!")
        else:
            print(f"\n❌ Sync failed: {results.get('error', 'Unknown error')}")
        
        # Display results
        print(f"\nDetailed Statistics:")
        print(json.dumps(results['stats'], indent=2))
        
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        logger.exception("Sync test failed")