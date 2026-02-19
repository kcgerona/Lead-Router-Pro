#!/usr/bin/env python3
"""
Enhanced Database Sync V2 - Complete Bi-directional Sync
Replacement for enhanced_db_sync.py with full bi-directional capabilities

Handles:
- Vendor sync (both directions with ALL fields)
- Lead sync (both directions)
- Deleted record detection
- New record discovery from GHL
"""

import json
import logging
import sys
import os
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import AppConfig
from api.services.ghl_api_v2_optimized import OptimizedGoHighLevelAPI
from database.simple_connection import db as simple_db_instance

logger = logging.getLogger(__name__)


class EnhancedDatabaseSync:
    """
    Enhanced V2 sync service with bi-directional capabilities
    Drop-in replacement for original enhanced_db_sync.py
    """
    
    # GHL Field Mappings for Vendors (from original)
    VENDOR_GHL_FIELDS = {
        'ghl_user_id': 'HXVNT4y8OynNokWAfO2D',
        'name': ['firstName', 'lastName'],
        'email': 'email',
        'phone': 'phone',
        'company_name': 'JexVrg2VNhnwIX7YlyJV',
        'service_categories': ['72qwwzy4AUfTCBJvBIEf', 'O84LyhN1QjZ8Zz5mteCM'],
        'services_offered': 'pAq9WBsIuFUAZuwz3YY4',
        'service_zip_codes': 'yDcN0FmwI3xacyxAuTWs',
        'taking_new_work': 'bTFOs5zXYt85AvDJJUAb',
        'last_lead_assigned': 'NbsJTMv3EkxqNfwx8Jh4',
        'lead_close_percentage': 'OwHQipU7xdrHCpVswtnW',
        'primary_service_category': 'HRqfv0HnUydNRLKWhk27'
    }
    
    # GHL Field Mappings for Leads
    LEAD_GHL_FIELDS = {
        'customer_name': ['firstName', 'lastName'],
        'customer_email': 'email',
        'customer_phone': 'phone',
        'primary_service_category': 'HRqfv0HnUydNRLKWhk27',
        'specific_service_requested': 'FT85QGi0tBq1AfVGNJ9v',
        # Note: No standard ZIP field in GHL custom fields - need to check postalCode
    }
    
    def __init__(self):
        """Initialize the bi-directional sync service"""
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            self.ghl_api = OptimizedGoHighLevelAPI(
                private_token=os.getenv('GHL_PRIVATE_TOKEN') or AppConfig.GHL_PRIVATE_TOKEN,
                location_id=os.getenv('GHL_LOCATION_ID') or AppConfig.GHL_LOCATION_ID,
                agency_api_key=os.getenv('GHL_AGENCY_API_KEY') or AppConfig.GHL_AGENCY_API_KEY,
                location_api_key=os.getenv('GHL_LOCATION_API') or AppConfig.GHL_LOCATION_API
            )
            
            self.stats = {
                'vendors_checked': 0,
                'vendors_updated': 0,
                'vendors_created': 0,
                'vendors_deleted': 0,
                'vendors_deactivated': 0,
                'leads_checked': 0,
                'leads_updated': 0,
                'leads_created': 0,
                'leads_deleted': 0,
                'ghl_contacts_fetched': 0,
                'errors': []
            }
            
            logger.info("✅ Bi-directional Sync initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Bi-directional Sync: {e}")
            raise
    
    def sync_all(self) -> Dict[str, Any]:
        """
        Complete bi-directional sync process:
        1. Fetch ALL contacts from GHL (with vendor tags)
        2. Update existing local records
        3. Create new local records for new GHL contacts
        4. Handle deleted GHL contacts
        """
        logger.info("🔄 Starting Bi-directional Database Sync")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Step 1: Get ALL vendor contacts from GHL
            logger.info("\n📊 STEP 1: Fetching ALL vendor contacts from GHL")
            ghl_vendors = self._fetch_all_ghl_vendors()
            
            # Step 2: Get ALL local vendors
            logger.info("\n📊 STEP 2: Fetching local vendor records")
            local_vendors = self._get_local_vendors()
            
            # Step 3: Process sync
            logger.info("\n📊 STEP 3: Processing bi-directional sync")
            self._process_vendor_sync(ghl_vendors, local_vendors)
            
            # Step 4: Process lead sync
            logger.info("\n📊 STEP 4: Processing lead sync")
            ghl_leads = self._fetch_all_ghl_leads()
            local_leads = self._get_local_leads()
            self._process_lead_sync(ghl_leads, local_leads)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # Generate summary
            logger.info("\n" + "=" * 60)
            logger.info("🎉 BI-DIRECTIONAL SYNC COMPLETED")
            logger.info(f"⏱️  Duration: {duration:.2f} seconds")
            logger.info(f"\n📈 VENDOR SYNC RESULTS:")
            logger.info(f"   GHL Contacts Fetched: {self.stats['ghl_contacts_fetched']}")
            logger.info(f"   Vendors Updated: {self.stats['vendors_updated']}")
            logger.info(f"   Vendors Created (NEW): {self.stats['vendors_created']}")
            logger.info(f"   Vendors Deactivated: {self.stats['vendors_deactivated']}")
            logger.info(f"   Vendors Deleted: {self.stats['vendors_deleted']}")
            logger.info(f"\n📈 LEAD SYNC RESULTS:")
            logger.info(f"   Leads Updated: {self.stats['leads_updated']}")
            logger.info(f"   Leads Created (NEW): {self.stats['leads_created']}")
            logger.info(f"   Leads Deleted: {self.stats['leads_deleted']}")
            
            if self.stats['errors']:
                logger.warning(f"\n⚠️  Errors encountered: {len(self.stats['errors'])}")
                for error in self.stats['errors'][:5]:  # Show first 5 errors
                    logger.warning(f"   - {error}")
            
            # Generate summary message
            message = (f"Sync completed in {duration:.2f}s. "
                      f"Vendors: {self.stats['vendors_updated']} updated, "
                      f"{self.stats['vendors_created']} created, "
                      f"{self.stats['vendors_deactivated']} deactivated. "
                      f"Leads: {self.stats['leads_updated']} updated, "
                      f"{self.stats['leads_created']} created, "
                      f"{self.stats['leads_deleted']} deleted.")
            
            return {
                'success': True,
                'message': message,
                'stats': self.stats,
                'duration': duration
            }
            
        except Exception as e:
            logger.error(f"❌ Sync failed: {e}")
            return {
                'success': False,
                'message': f"Sync failed: {str(e)}",
                'stats': self.stats,
                'error': str(e)
            }
    
    def _fetch_all_ghl_vendors(self) -> Dict[str, Dict]:
        """
        Fetch vendor contacts from GHL by matching with local vendor database
        Returns dict keyed by contact ID for fast lookup
        """
        all_vendors = {}
        
        try:
            # First, get all local vendor GHL contact IDs and emails
            conn = simple_db_instance._get_raw_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ghl_contact_id, email, name 
                FROM vendors 
                WHERE ghl_contact_id IS NOT NULL OR email IS NOT NULL
            """)
            
            local_vendor_identifiers = {}
            for row in cursor.fetchall():
                if row[0]:  # Has GHL contact ID
                    local_vendor_identifiers[row[0]] = {'type': 'contact_id', 'name': row[2]}
                if row[1]:  # Has email
                    local_vendor_identifiers[row[1].lower()] = {'type': 'email', 'name': row[2]}
            
            conn.close()
            
            logger.info(f"   Found {len(local_vendor_identifiers)} vendor identifiers to match")
            
            # Now fetch contacts from GHL and match against our vendor identifiers
            limit = 100
            offset = 0
            matched_count = 0
            total_fetched = 0
            
            while True:
                logger.info(f"   Fetching GHL contacts (offset: {offset}, limit: {limit})")
                
                params = {
                    'locationId': self.ghl_api.location_id,
                    'limit': limit,
                    'skip': offset,
                }
                
                # Make API call
                url = f"{self.ghl_api.v2_base_url}/contacts/"
                headers = {
                    "Authorization": f"Bearer {self.ghl_api.private_token}",
                    "Version": "2021-07-28"
                }
                
                import requests
                response = requests.get(url, headers=headers, params=params)
                
                if response.status_code != 200:
                    logger.error(f"❌ Failed to fetch GHL contacts: {response.status_code}")
                    break
                
                data = response.json()
                contacts = data.get('contacts', [])
                
                if not contacts:
                    logger.info(f"   No more contacts to fetch")
                    break
                
                # Process each contact
                for contact in contacts:
                    contact_id = contact.get('id')
                    contact_email = contact.get('email', '').lower()
                    
                    # Check if this contact matches a vendor by ID or email
                    is_vendor = False
                    vendor_match = None
                    
                    # Priority 1: Match by GHL contact ID
                    if contact_id in local_vendor_identifiers:
                        is_vendor = True
                        vendor_match = local_vendor_identifiers[contact_id]
                        logger.debug(f"   Matched vendor by contact ID: {vendor_match['name']}")
                    
                    # Priority 2: Match by email
                    elif contact_email and contact_email in local_vendor_identifiers:
                        is_vendor = True
                        vendor_match = local_vendor_identifiers[contact_email]
                        logger.debug(f"   Matched vendor by email: {vendor_match['name']}")
                    
                    if is_vendor:
                        all_vendors[contact_id] = contact
                        matched_count += 1
                
                total_fetched += len(contacts)
                self.stats['ghl_contacts_fetched'] = total_fetched
                
                # Check if we got all contacts
                if len(contacts) < limit:
                    break
                
                offset += limit
                time.sleep(0.2)  # Rate limiting
            
            logger.info(f"✅ Fetched {len(all_vendors)} vendor contacts from GHL")
            return all_vendors
            
        except Exception as e:
            logger.error(f"❌ Error fetching GHL vendors: {e}")
            self.stats['errors'].append(f"GHL fetch error: {str(e)}")
            return {}
    
    def _get_local_vendors(self) -> Dict[str, Dict]:
        """
        Get all local vendors - returns tuple of:
        1. Dict keyed by GHL contact ID
        2. Dict keyed by email (for vendors without GHL ID)
        """
        local_vendors_by_ghl_id = {}
        local_vendors_by_email = {}
        
        try:
            vendors = simple_db_instance.get_vendors()
            
            for vendor in vendors:
                ghl_contact_id = vendor.get('ghl_contact_id')
                email = vendor.get('email', '').lower()
                
                if ghl_contact_id:
                    local_vendors_by_ghl_id[ghl_contact_id] = vendor
                elif email:  # No GHL ID but has email
                    local_vendors_by_email[email] = vendor
            
            logger.info(f"✅ Found {len(local_vendors_by_ghl_id)} vendors with GHL IDs")
            logger.info(f"   Found {len(local_vendors_by_email)} vendors without GHL IDs (by email)")
            
            return local_vendors_by_ghl_id, local_vendors_by_email
            
        except Exception as e:
            logger.error(f"❌ Error fetching local vendors: {e}")
            self.stats['errors'].append(f"Local fetch error: {str(e)}")
            return {}, {}
    
    def _process_vendor_sync(self, ghl_vendors: Dict, local_vendors_tuple: tuple):
        """
        Process the bi-directional sync:
        1. Update existing vendors
        2. Create new vendors from GHL
        3. Handle deleted vendors
        """
        local_vendors_by_ghl_id, local_vendors_by_email = local_vendors_tuple
        
        # Track processed vendor IDs (local DB IDs)
        processed_vendor_ids = set()
        
        # PART 1: Process vendors that exist in GHL
        for ghl_id, ghl_contact in ghl_vendors.items():
            contact_email = ghl_contact.get('email', '').lower()
            matched_vendor = None
            
            # Try to match by GHL contact ID first
            if ghl_id in local_vendors_by_ghl_id:
                matched_vendor = local_vendors_by_ghl_id[ghl_id]
            # If no match by ID, try email
            elif contact_email and contact_email in local_vendors_by_email:
                matched_vendor = local_vendors_by_email[contact_email]
                # Important: Update the vendor with the GHL contact ID
                logger.info(f"   Matched vendor by email, adding GHL contact ID: {ghl_id}")
            
            if matched_vendor:
                # UPDATE existing vendor
                processed_vendor_ids.add(matched_vendor['id'])
                # Ensure GHL contact ID is set
                if not matched_vendor.get('ghl_contact_id'):
                    matched_vendor['ghl_contact_id'] = ghl_id
                self._update_local_vendor(matched_vendor, ghl_contact)
            else:
                # CREATE new vendor in local DB (shouldn't happen if our matching works)
                logger.warning(f"   Creating new vendor - not found by ID or email: {ghl_contact.get('email')}")
                self._create_local_vendor(ghl_contact)
        
        # PART 2: Handle vendors that exist locally but not in GHL (deleted/missing)
        all_local_vendors = list(local_vendors_by_ghl_id.values()) + list(local_vendors_by_email.values())
        missing_vendors = [v for v in all_local_vendors if v['id'] not in processed_vendor_ids]
        
        if missing_vendors:
            logger.info(f"📊 Found {len(missing_vendors)} vendors not in GHL sync results")
            logger.info("These will be flagged as 'missing_in_ghl' for admin review")
            
            # Flag all missing vendors for review (not deleting)
            for local_vendor in missing_vendors:
                self._handle_missing_ghl_vendor(local_vendor)
    
    def _update_local_vendor(self, local_vendor: Dict, ghl_contact: Dict):
        """Update existing local vendor with ALL GHL data fields"""
        try:
            updates = self._extract_vendor_updates(local_vendor, ghl_contact)
            
            # IMPORTANT: Ensure GHL contact ID is set if it wasn't before
            if not local_vendor.get('ghl_contact_id') and ghl_contact.get('id'):
                updates['ghl_contact_id'] = ghl_contact.get('id')
                logger.info(f"   Setting GHL contact ID: {ghl_contact.get('id')}")
            
            if updates:
                success = self._update_vendor_record(local_vendor['id'], updates)
                if success:
                    self.stats['vendors_updated'] += 1
                    logger.info(f"✅ Updated vendor: {local_vendor.get('name')} ({len(updates)} fields)")
            
        except Exception as e:
            logger.error(f"❌ Error updating vendor {local_vendor.get('id')}: {e}")
            self.stats['errors'].append(f"Update error: {str(e)}")
    
    def _extract_vendor_updates(self, vendor: Dict, ghl_contact: Dict) -> Dict[str, Any]:
        """Extract ALL vendor fields that need updating - from original enhanced_db_sync"""
        updates = {}
        
        # Extract custom fields from GHL contact
        custom_fields = {}
        for field in ghl_contact.get('customFields', []):
            field_id = field.get('id', '')
            field_value = field.get('value', '') or field.get('fieldValue', '')
            if field_id:
                custom_fields[field_id] = field_value
        
        # Check for GHL User ID and set if found
        ghl_user_id_from_contact = custom_fields.get('HXVNT4y8OynNokWAfO2D', '').strip()
        if ghl_user_id_from_contact and not vendor.get('ghl_user_id'):
            updates['ghl_user_id'] = ghl_user_id_from_contact
            logger.info(f"   ✅ Found GHL User ID: {ghl_user_id_from_contact}")

        # Status from tags: "manually approved" -> active, else -> pending
        tag_based_status = self._get_vendor_status_from_tags(ghl_contact)
        if vendor.get('status') != tag_based_status:
            updates['status'] = tag_based_status
            logger.info(f"   ✅ Setting vendor status to {tag_based_status} (from tags)")
        
        # Process service_zip_codes to derive coverage fields
        service_zip_codes_value = custom_fields.get('yDcN0FmwI3xacyxAuTWs', '').strip()
        if service_zip_codes_value:
            coverage_info = self._parse_coverage_from_zip_codes(service_zip_codes_value)
            if coverage_info['type']:
                if vendor.get('coverage_type') != coverage_info['type']:
                    updates['coverage_type'] = coverage_info['type']
                if coverage_info['states']:
                    updates['coverage_states'] = json.dumps(coverage_info['states'])
                if coverage_info['counties']:
                    updates['coverage_counties'] = json.dumps(coverage_info['counties'])
        
        # Check each mapped field
        for db_field, ghl_field in self.VENDOR_GHL_FIELDS.items():
            if db_field == 'service_zip_codes':
                continue
                
            current_value = vendor.get(db_field)
            new_value = None
            
            if db_field == 'name' and ghl_field == ['firstName', 'lastName']:
                first = ghl_contact.get('firstName', '').strip()
                last = ghl_contact.get('lastName', '').strip()
                new_value = f"{first} {last}".strip()
            elif ghl_field in ['email', 'phone']:
                new_value = ghl_contact.get(ghl_field, '').strip()
            elif isinstance(ghl_field, list):
                for field_id in ghl_field:
                    temp_value = custom_fields.get(field_id, '').strip()
                    if temp_value:
                        new_value = temp_value
                        break
            else:
                # Handle both string and numeric values from GHL
                raw_value = custom_fields.get(ghl_field, '')
                if isinstance(raw_value, str):
                    new_value = raw_value.strip()
                else:
                    new_value = str(raw_value) if raw_value else ''
            
            # Special handling for certain fields
            if db_field in ['service_categories', 'services_offered']:
                if new_value:
                    parsed_list = [s.strip() for s in new_value.split(',') if s.strip()]
                    new_value = json.dumps(parsed_list)
            elif db_field == 'lead_close_percentage':
                if new_value:
                    try:
                        # Log the raw value from GHL
                        logger.info(f"   📊 Processing lead_close_percentage: raw value = '{new_value}'")
                        new_value = float(new_value.replace('%', '').strip())
                        logger.info(f"   📊 Parsed lead_close_percentage: {new_value}")
                    except Exception as e:
                        logger.warning(f"   ⚠️ Failed to parse lead_close_percentage '{new_value}': {e}")
                        new_value = 0.0
                else:
                    logger.info(f"   📊 No lead_close_percentage value from GHL")
                    new_value = 0.0
            elif db_field == 'taking_new_work':
                if new_value:
                    normalized = new_value.strip().lower()
                    new_value = 'Yes' if normalized in ['yes', 'true', '1'] else 'No'
            
            # Compare and add to updates if different
            if new_value and self._values_differ(current_value, new_value, db_field):
                updates[db_field] = new_value
                logger.info(f"   🔄 Field '{db_field}' will update: '{current_value}' → '{new_value}'")
        
        if updates:
            logger.info(f"   📝 Total updates to apply: {len(updates)} fields")
        else:
            logger.info(f"   ✅ No updates needed - vendor is up to date")
        
        return updates
    
    def _parse_coverage_from_zip_codes(self, service_zip_codes_value: str) -> Dict:
        """Parse service_zip_codes field to determine coverage type"""
        normalized_value = service_zip_codes_value.upper().strip()
        
        if 'GLOBAL' in normalized_value:
            return {'type': 'global', 'states': [], 'counties': []}
        elif 'NATIONAL' in normalized_value or normalized_value in ['USA', 'UNITED STATES']:
            return {'type': 'national', 'states': [], 'counties': []}
        elif ';' in service_zip_codes_value:
            items = [s.strip() for s in service_zip_codes_value.split(';') if s.strip()]
            if items and ', ' in items[0]:
                counties = items
                states = list({county.split(', ')[-1].strip() for county in counties if ', ' in county})
                return {'type': 'county', 'states': states, 'counties': counties}
        elif ',' in service_zip_codes_value:
            items = [s.strip() for s in service_zip_codes_value.split(',') if s.strip()]
            if all(len(item) == 2 and item.isupper() for item in items):
                return {'type': 'state', 'states': items, 'counties': []}
        
        return {'type': None, 'states': None, 'counties': None}
    
    def _get_vendor_status_from_tags(self, ghl_contact: Dict) -> str:
        """Determine vendor status from GHL contact tags: 'manually approved' -> active, else -> pending"""
        tags_raw = ghl_contact.get('tags') or []
        if isinstance(tags_raw, str):
            tags_list = [t.strip().lower() for t in tags_raw.split(',') if t.strip()]
        elif isinstance(tags_raw, list):
            tags_list = []
            for t in tags_raw:
                if isinstance(t, str):
                    tags_list.append(t.strip().lower())
                elif isinstance(t, dict):
                    tag_name = (t.get('name') or t.get('tag') or '').strip().lower()
                    if tag_name:
                        tags_list.append(tag_name)
                else:
                    tags_list.append(str(t).strip().lower())
        else:
            tags_list = []
        return "active" if "manually approved" in tags_list else "pending"

    def _values_differ(self, current: Any, new: Any, field_name: str) -> bool:
        """Check if two values are different"""
        if current is None and new == '':
            return False
        if current == '' and new is None:
            return False
        
        if field_name in ['service_categories', 'services_offered', 'coverage_states', 'coverage_counties']:
            try:
                current_list = json.loads(current) if current else []
                new_list = json.loads(new) if new else []
                return set(current_list) != set(new_list)
            except:
                return str(current) != str(new)
        
        return str(current or '').strip() != str(new or '').strip()
    
    def _create_local_vendor(self, ghl_contact: Dict):
        """Create new vendor in local DB from GHL contact"""
        try:
            # Extract custom fields
            custom_fields = {cf['id']: cf.get('value', '') 
                           for cf in ghl_contact.get('customFields', [])}
            
            # Get account ID
            account = simple_db_instance.get_account_by_ghl_location_id(
                os.getenv('GHL_LOCATION_ID') or AppConfig.GHL_LOCATION_ID
            )
            if not account:
                logger.error("❌ No account found for location")
                return
            
            # Create vendor data - status from tags: "manually approved" -> active, else -> pending
            tag_based_status = self._get_vendor_status_from_tags(ghl_contact)
            vendor_data = {
                'account_id': account['id'],
                'ghl_contact_id': ghl_contact.get('id'),
                'ghl_user_id': custom_fields.get('HXVNT4y8OynNokWAfO2D', ''),
                'name': f"{ghl_contact.get('firstName', '')} {ghl_contact.get('lastName', '')}".strip(),
                'email': ghl_contact.get('email', ''),
                'phone': ghl_contact.get('phone', ''),
                'company_name': custom_fields.get('JexVrg2VNhnwIX7YlyJV', ''),
                'status': tag_based_status,
                # Add other fields...
            }
            
            # Create vendor in database (create_vendor expects positional/keyword args, not a dict)
            vendor_id = simple_db_instance.create_vendor(
                account_id=vendor_data['account_id'],
                name=vendor_data['name'],
                email=vendor_data['email'],
                company_name=vendor_data.get('company_name', ''),
                phone=vendor_data.get('phone', ''),
                ghl_contact_id=vendor_data.get('ghl_contact_id'),
                status=vendor_data.get('status', 'pending'),
                taking_new_work=vendor_data.get('taking_new_work', True),
            )
            if vendor_id:
                self.stats['vendors_created'] += 1
                logger.info(f"✅ Created NEW vendor from GHL: {vendor_data['name']}")
            
        except Exception as e:
            logger.error(f"❌ Error creating vendor from GHL: {e}")
            self.stats['errors'].append(f"Create error: {str(e)}")
    
    def _handle_missing_ghl_vendor(self, local_vendor: Dict):
        """
        Handle vendor that exists locally but not in GHL.
        Instead of deleting, flag as 'missing_in_ghl' for admin review.
        Admin can then bulk delete through the dashboard.
        """
        try:
            vendor_name = local_vendor.get('name', 'Unknown')
            logger.warning(f"⚠️  Vendor exists locally but not found in GHL sync: {vendor_name}")
            
            # Flag as missing instead of deleting
            updates = {'status': 'missing_in_ghl'}
            success = self._update_vendor_record(local_vendor['id'], updates)
            
            if success:
                self.stats['vendors_missing_in_ghl'] = self.stats.get('vendors_missing_in_ghl', 0) + 1
                logger.info(f"🔍 Flagged vendor as missing in GHL: {vendor_name} (admin review needed)")
            
            # DO NOT auto-delete or deactivate
            # Admin will review and decide through dashboard
            
        except Exception as e:
            logger.error(f"❌ Error handling missing vendor: {e}")
            self.stats['errors'].append(f"Missing vendor error: {str(e)}")
    
    def _update_vendor_record(self, vendor_id: str, updates: Dict) -> bool:
        """Update vendor in database"""
        try:
            if not updates:
                return True
            
            # Build UPDATE query (use raw connection for cursor)
            conn = simple_db_instance._get_raw_conn()
            cursor = conn.cursor()
            
            set_clauses = []
            values = []
            
            for field, value in updates.items():
                set_clauses.append(f"{field} = ?")
                values.append(value)
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(vendor_id)
            
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
    
    def _fetch_all_ghl_leads(self) -> Dict[str, Dict]:
        """
        Fetch GHL contacts that match existing leads in our database
        
        IMPORTANT: We should NOT create new leads during sync!
        Leads are created by webhook form submissions only.
        This sync only updates existing leads with latest GHL data.
        
        Matching strategy:
        1. Match by GHL contact ID (most reliable)
        2. Match by email address (fallback)
        3. Check GHL opportunity ID if available
        """
        all_leads = {}
        
        try:
            # Get all local lead identifiers for matching
            conn = simple_db_instance._get_raw_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT ghl_contact_id, customer_email, ghl_opportunity_id, id
                FROM leads 
                WHERE (ghl_contact_id IS NOT NULL AND ghl_contact_id != '')
                   OR (customer_email IS NOT NULL AND customer_email != '')
            """)
            
            local_lead_contact_ids = set()
            local_lead_emails = {}
            local_lead_opportunity_ids = {}
            lead_id_map = {}  # Map to track which local lead each GHL contact matches
            
            for row in cursor.fetchall():
                if row[0]:  # Has GHL contact ID
                    local_lead_contact_ids.add(row[0])
                    lead_id_map[row[0]] = row[3]  # Map GHL ID to local lead ID
                if row[1]:  # Has email
                    email_lower = row[1].lower()
                    local_lead_emails[email_lower] = row[3]  # Map email to local lead ID
                if row[2]:  # Has GHL opportunity ID
                    local_lead_opportunity_ids[row[2]] = row[3]  # Map opportunity ID to local lead ID
            
            conn.close()
            
            logger.info(f"   Found {len(local_lead_contact_ids)} leads with GHL contact IDs")
            logger.info(f"   Found {len(local_lead_emails)} leads with emails")
            logger.info(f"   Found {len(local_lead_opportunity_ids)} leads with opportunity IDs")
            
            if not local_lead_contact_ids and not local_lead_emails:
                logger.info("   No leads with identifiers found - skipping lead sync")
                return {}
            
            # Step 1: Fetch each lead's contact by ID when we have ghl_contact_id (avoids 10k
            # pagination limit and ensures we find all leads regardless of GHL contact list order)
            if local_lead_contact_ids:
                logger.info(f"   Fetching {len(local_lead_contact_ids)} lead contacts by ID from GHL...")
                for contact_id in local_lead_contact_ids:
                    try:
                        contact = self.ghl_api.get_contact_by_id(contact_id)
                        if contact:
                            all_leads[contact_id] = contact
                    except Exception as e:
                        logger.debug(f"   Could not fetch contact {contact_id}: {e}")
                    time.sleep(0.12)  # rate limit
                logger.info(f"   Found {len(all_leads)} leads via fetch-by-ID")
            
            # Step 2: Batch-scan GHL contacts to match leads by email (for leads without ghl_contact_id
            # or to catch any not found by ID)
            limit = 100
            offset = 0
            matched_count = len(all_leads)
            emails_still_needed = set(local_lead_emails.keys()) - {
                c.get('email', '').lower() for c in all_leads.values() if c.get('email')
            }
            
            logger.info("   Fetching GHL contacts in batches to match by email...")
            
            while True:
                logger.debug(f"   Fetching GHL contacts batch (offset: {offset}, limit: {limit})")
                
                url = f"{self.ghl_api.v2_base_url}/contacts/"
                headers = {
                    "Authorization": f"Bearer {self.ghl_api.private_token}",
                    "Version": "2021-07-28"
                }
                
                params = {
                    'locationId': self.ghl_api.location_id,
                    'limit': limit,
                    'skip': offset
                }
                
                import requests
                response = requests.get(url, headers=headers, params=params)
                
                if response.status_code != 200:
                    logger.error(f"❌ Failed to fetch GHL contacts: {response.status_code}")
                    break
                
                data = response.json()
                contacts = data.get('contacts', [])
                
                if not contacts:
                    logger.debug(f"   No more contacts to fetch")
                    break
                
                # Check each contact to see if it matches our leads (by email or opportunity; ID already done above)
                for contact in contacts:
                    contact_id = contact.get('id')
                    contact_email = contact.get('email', '').lower() if contact.get('email') else ''
                    matched = False
                    match_type = ""
                    
                    # Skip if already fetched by ID
                    if contact_id in all_leads:
                        continue
                    
                    # Match by email (for leads without ghl_contact_id or not yet found)
                    if contact_email and contact_email in local_lead_emails:
                        all_leads[contact_id] = contact
                        matched = True
                        match_type = "by email"
                        emails_still_needed.discard(contact_email)
                        logger.info(f"   Found lead by email, updating GHL contact ID: {contact_id}")
                    
                    # Match by opportunity ID in custom fields
                    if not matched:
                        custom_fields = contact.get('customFields', [])
                        for field in custom_fields:
                            field_value = field.get('value', '')
                            if field_value in local_lead_opportunity_ids:
                                all_leads[contact_id] = contact
                                matched = True
                                match_type = f"by opportunity ID: {field_value}"
                                break
                    
                    if matched:
                        matched_count += 1
                        contact_name = f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip()
                        logger.debug(f"   Matched lead {match_type}: {contact_name} ({contact_email})")
                
                # Early exit if we've matched all emails we needed from batch scan
                if not emails_still_needed:
                    logger.info("   Matched all leads by email - stopping batch scan")
                    break
                
                offset += limit
                
                # Safety limit - don't scan more than 15k contacts in batch (ID fetch already got most)
                if offset > 15000:
                    logger.warning("   Reached 15,000 contact batch limit - stopping search")
                    break
                
                time.sleep(0.2)  # Rate limiting
            
            # Calculate total expected leads (some may be matched by email/opportunity)
            total_expected = len(set(list(lead_id_map.values()) + list(local_lead_emails.values())))
            logger.info(f"✅ Fetched {len(all_leads)} lead contacts from GHL out of {total_expected} local leads")
            
            # Check which local leads weren't matched
            matched_local_ids = set()
            for ghl_id in all_leads.keys():
                if ghl_id in lead_id_map:
                    matched_local_ids.add(lead_id_map[ghl_id])
            
            # Also check for leads matched by email
            for contact in all_leads.values():
                email = contact.get('email', '').lower() if contact.get('email') else ''
                if email in local_lead_emails:
                    matched_local_ids.add(local_lead_emails[email])
            
            # Find unmatched leads
            all_local_ids = set(list(lead_id_map.values()) + list(local_lead_emails.values()))
            unmatched_local_ids = all_local_ids - matched_local_ids
            
            if unmatched_local_ids:
                logger.warning(f"⚠️ {len(unmatched_local_ids)} local leads not found in GHL")
                # Get details of first 5 unmatched leads for debugging
                conn = simple_db_instance._get_raw_conn()
                cursor = conn.cursor()
                for lead_id in list(unmatched_local_ids)[:5]:
                    cursor.execute("SELECT customer_email, ghl_contact_id FROM leads WHERE id = ?", (lead_id,))
                    row = cursor.fetchone()
                    if row:
                        logger.info(f"   Not found: Email: {row[0]}, GHL ID: {row[1]}")
                conn.close()
            
            return all_leads
            
        except Exception as e:
            logger.error(f"❌ Error fetching GHL leads: {e}")
            return {}
    
    def _get_local_leads(self) -> Dict[str, Dict]:
        """
        Get all local leads - returns both:
        1. Dict keyed by GHL contact ID
        2. Dict keyed by email (for leads without GHL ID)
        """
        local_leads_by_ghl_id = {}
        local_leads_by_email = {}
        
        try:
            conn = simple_db_instance._get_raw_conn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, ghl_contact_id, customer_name, customer_email, 
                       customer_phone, primary_service_category, 
                       specific_service_requested, customer_zip_code,
                       service_county, service_state, status, vendor_id,
                       ghl_opportunity_id
                FROM leads
            """)
            
            for row in cursor.fetchall():
                lead = {
                    'id': row[0],
                    'ghl_contact_id': row[1],
                    'customer_name': row[2],
                    'customer_email': row[3],
                    'customer_phone': row[4],
                    'primary_service_category': row[5],
                    'specific_service_requested': row[6],
                    'customer_zip_code': row[7],
                    'service_county': row[8],
                    'service_state': row[9],
                    'status': row[10],
                    'vendor_id': row[11],
                    'ghl_opportunity_id': row[12] if len(row) > 12 else None
                }
                
                # Index by GHL contact ID if available
                if lead['ghl_contact_id']:
                    local_leads_by_ghl_id[lead['ghl_contact_id']] = lead
                
                # Also index by email for fallback matching
                if lead['customer_email']:
                    email_lower = lead['customer_email'].lower()
                    local_leads_by_email[email_lower] = lead
            
            conn.close()
            
            logger.info(f"✅ Found {len(local_leads_by_ghl_id)} leads with GHL IDs")
            logger.info(f"   Found {len(local_leads_by_email)} leads with emails")
            
            # Return combined dict - GHL ID takes precedence
            combined = {}
            combined.update(local_leads_by_email)  # Add email-indexed leads first
            combined.update(local_leads_by_ghl_id)  # Override with GHL-ID indexed (more reliable)
            
            return combined
            
        except Exception as e:
            logger.error(f"❌ Error fetching local leads: {e}")
            return {}
    
    def _process_lead_sync(self, ghl_leads: Dict, local_leads: Dict):
        """
        Process lead sync - ONLY updates existing leads
        
        IMPORTANT: We do NOT create new leads during sync!
        Leads are only created through webhook form submissions.
        This prevents duplicate leads from being created.
        """
        # Track which local lead IDs were processed (found in GHL and updated).
        # local_leads is keyed by both ghl_contact_id and email, so we must use
        # local lead id to decide "missing", not the dict key (email keys are never in processed_ghl_ids).
        processed_local_lead_ids = set()
        
        # Process leads that exist in both GHL and local DB
        for ghl_id, ghl_contact in ghl_leads.items():
            # Match by GHL contact ID first, then by email (lead may be keyed only by email locally)
            local_lead = local_leads.get(ghl_id)
            if not local_lead and ghl_contact.get('email'):
                email_lower = ghl_contact.get('email', '').lower()
                local_lead = local_leads.get(email_lower)
            if local_lead:
                self._update_local_lead(local_lead, ghl_contact)
                processed_local_lead_ids.add(local_lead['id'])
            else:
                logger.warning(f"⚠️ GHL contact {ghl_id} fetched but not found in local leads - skipping")
        
        # Build set of unique local leads by id (local_leads has duplicate entries keyed by email and ghl_id)
        all_local_lead_ids = set(lead['id'] for lead in local_leads.values())
        # Handle leads that exist locally but were never found in GHL
        for local_lead_id in all_local_lead_ids:
            if local_lead_id not in processed_local_lead_ids:
                # Find the lead dict (any key is fine)
                local_lead = next(lead for lead in local_leads.values() if lead['id'] == local_lead_id)
                self._handle_missing_lead(local_lead)
    
    def _handle_missing_lead(self, local_lead: Dict):
        """
        Handle leads that exist locally but not in GHL.
        Similar to vendor handling - mark as inactive rather than delete.
        """
        try:
            lead_name = local_lead.get('customer_name', 'Unknown')
            lead_id = local_lead.get('id')
            
            logger.warning(f"⚠️ Lead exists locally but not in GHL: {lead_name}")
            
            # Mark as inactive/deleted (safer than hard delete)
            updates = {'status': 'inactive_ghl_deleted'}
            success = self._update_lead_record(lead_id, updates)
            
            if success:
                self.stats['leads_deleted'] += 1
                logger.info(f"🔴 Deactivated lead (deleted from GHL): {lead_name}")
            
            # Option 2: Actually delete (more aggressive)
            # conn = self._get_conn()
            # cursor = conn.cursor()
            # cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            # conn.commit()
            # self.stats['leads_deleted'] += 1
            # logger.info(f"🗑️ Deleted lead: {lead_name}")
            
        except Exception as e:
            logger.error(f"❌ Error handling missing lead: {e}")
            self.stats['errors'].append(f"Missing lead error: {str(e)}")
    
    def _update_local_lead(self, local_lead: Dict, ghl_contact: Dict):
        """Update existing local lead with GHL data"""
        try:
            updates = self._extract_lead_updates(local_lead, ghl_contact)
            
            if updates:
                success = self._update_lead_record(local_lead['id'], updates)
                if success:
                    self.stats['leads_updated'] += 1
                    logger.info(f"✅ Updated lead: {local_lead.get('customer_name')}")
        except Exception as e:
            logger.error(f"❌ Error updating lead: {e}")
    
    def _extract_lead_updates(self, lead: Dict, ghl_contact: Dict) -> Dict[str, Any]:
        """Extract lead fields that need updating"""
        updates = {}
        
        custom_fields = {cf['id']: cf.get('value', '') 
                        for cf in ghl_contact.get('customFields', [])}
        
        for db_field, ghl_field in self.LEAD_GHL_FIELDS.items():
            current_value = lead.get(db_field)
            new_value = None
            
            if db_field == 'customer_name' and ghl_field == ['firstName', 'lastName']:
                first = ghl_contact.get('firstName', '').strip()
                last = ghl_contact.get('lastName', '').strip()
                new_value = f"{first} {last}".strip()
            elif ghl_field in ['email', 'phone']:
                if db_field == 'customer_email':
                    new_value = ghl_contact.get('email', '').strip()
                elif db_field == 'customer_phone':
                    new_value = ghl_contact.get('phone', '').strip()
            else:
                # Handle both string and numeric values from GHL
                raw_value = custom_fields.get(ghl_field, '')
                if isinstance(raw_value, str):
                    new_value = raw_value.strip()
                else:
                    new_value = str(raw_value) if raw_value else ''
            
            if new_value and current_value != new_value:
                updates[db_field] = new_value
        
        # Try to extract ZIP from standard GHL contact fields (not custom fields)
        zip_code = None
        
        # Check standard postalCode field first
        if ghl_contact.get('postalCode'):
            zip_code = str(ghl_contact.get('postalCode'))
        # Check address field for embedded ZIP (last 5 digits)
        elif ghl_contact.get('address1'):
            import re
            zip_match = re.search(r'\b(\d{5})\b', ghl_contact.get('address1', ''))
            if zip_match:
                zip_code = zip_match.group(1)
        
        # Update ZIP if found and different
        if zip_code and lead.get('service_zip_code') != zip_code:
            updates['service_zip_code'] = zip_code
            
        # Handle ZIP to county/state conversion
        zip_to_convert = updates.get('service_zip_code') or lead.get('service_zip_code')
        if zip_to_convert and len(str(zip_to_convert)) == 5:
            from api.services.location_service import location_service
            location_data = location_service.zip_to_location(str(zip_to_convert))
            if not location_data.get('error'):
                county = location_data.get('county', '')
                state = location_data.get('state', '')
                if county and not lead.get('service_county'):
                    updates['service_county'] = county
                if state and not lead.get('service_state'):
                    updates['service_state'] = state
        
        return updates
    
    def _create_local_lead(self, ghl_contact: Dict):
        """Create new lead in local DB from GHL contact"""
        try:
            custom_fields = {cf['id']: cf.get('value', '') 
                           for cf in ghl_contact.get('customFields', [])}
            
            account = simple_db_instance.get_account_by_ghl_location_id(
                os.getenv('GHL_LOCATION_ID') or AppConfig.GHL_LOCATION_ID
            )
            if not account:
                return
            
            import uuid
            lead_data = {
                'id': str(uuid.uuid4()),
                'account_id': account['id'],
                'ghl_contact_id': ghl_contact.get('id'),
                'customer_name': f"{ghl_contact.get('firstName', '')} {ghl_contact.get('lastName', '')}".strip(),
                'customer_email': ghl_contact.get('email', ''),
                'customer_phone': ghl_contact.get('phone', ''),
                'primary_service_category': custom_fields.get('HRqfv0HnUydNRLKWhk27', ''),
                'specific_service_requested': custom_fields.get('FT85QGi0tBq1AfVGNJ9v', ''),
                'customer_zip_code': custom_fields.get('RmAja1dnU0u42ECXhCo9', ''),
                'status': 'unassigned',
                'source': 'ghl_sync'
            }
            
            # Get county/state from ZIP
            if lead_data['customer_zip_code']:
                from api.services.location_service import location_service
                location_data = location_service.zip_to_location(lead_data['customer_zip_code'])
                if not location_data.get('error'):
                    lead_data['service_county'] = location_data.get('county', '')
                    lead_data['service_state'] = location_data.get('state', '')
            
            # Insert into database
            conn = simple_db_instance._get_raw_conn()
            cursor = conn.cursor()
            
            columns = list(lead_data.keys())
            placeholders = ['?' for _ in columns]
            values = [lead_data[col] for col in columns]
            
            query = f"""
                INSERT INTO leads ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
            """
            
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            
            self.stats['leads_created'] += 1
            logger.info(f"✅ Created NEW lead from GHL: {lead_data['customer_name']}")
            
        except Exception as e:
            logger.error(f"❌ Error creating lead from GHL: {e}")
    
    def _update_lead_record(self, lead_id: str, updates: Dict) -> bool:
        """Update lead in database"""
        try:
            if not updates:
                return True
            
            conn = simple_db_instance._get_raw_conn()
            cursor = conn.cursor()
            
            set_clauses = []
            values = []
            
            for field, value in updates.items():
                set_clauses.append(f"{field} = ?")
                values.append(value)
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(lead_id)
            
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


# Main function for testing
if __name__ == "__main__":
    print("🚀 BI-DIRECTIONAL DATABASE SYNC")
    print("=" * 60)
    print("This will:")
    print("1. Fetch ALL vendor contacts from GoHighLevel")
    print("2. Update existing local records")
    print("3. Create NEW local records for new GHL vendors")
    print("4. Deactivate local vendors deleted from GHL")
    print("")
    
    response = input("Continue? (y/n): ")
    
    if response.lower() == 'y':
        sync_service = BidirectionalSync()
        results = sync_service.sync_all()
        
        if results['success']:
            print("\n✅ Sync completed successfully!")
        else:
            print(f"\n❌ Sync failed: {results.get('error', 'Unknown error')}")
        
        print("\nDetailed Statistics:")
        print(json.dumps(results['stats'], indent=2))