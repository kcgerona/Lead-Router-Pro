#!/usr/bin/env python3
"""
Enhanced Database Sync V3 - Efficient unified GHL contact sync

EFFICIENCY PLAN (vs V2):
------------------------
1. UNIFIED IDENTIFIER COLLECTION
   - Single DB round-trip (or two) to get all vendor (ghl_contact_id, email) and
     lead (ghl_contact_id, email, ghl_opportunity_id) identifiers.
   - Build union of all GHL contact IDs so each contact is fetched at most once
     (a contact is never both vendor and lead in practice, but dedupe anyway).

2. SINGLE CONTACT FETCH PHASE
   - Fetch by ID for every *unique* contact ID (vendors + leads combined).
     Fewer API calls when the same ID is used for both vendor and lead (dedupe).
   - Optional: use a small thread pool (e.g. 3–5 workers) with rate limiting to
     reduce wall-clock time for fetch-by-ID.
   - Build one contact_map[contact_id] = contact.
   - Missing emails = (vendor_emails | lead_emails) minus emails already in
     contact_map. For each missing email, one search (GET with email param or
     POST /contacts/search). No full list scan for emails we already have.

3. SINGLE PAGINATION FALLBACK (optional)
   - One paginated list pass (cap e.g. 10k–15k) only if there are still missing
     emails. For each contact in the batch, match by email (and by opportunity ID
     for leads). Stop when missing_emails is empty or cap reached. This serves
     both vendors and leads in one pass (v2 did two separate list scans).

4. CLASSIFY FROM SINGLE CONTACT MAP
   - vendor_contacts = { id: c for id, c in contact_map if id in vendor_ids or
     (c.email in vendor_emails) }.
   - lead_contacts = { id: c for id, c in contact_map if id in lead_ids or
     (c.email in lead_emails) }. Opportunity-ID matches already in contact_map
     from the fallback pass.
   - No duplicate fetches; same contact never requested twice.

5. REUSE V2 SYNC LOGIC
   - _process_vendor_sync(vendor_contacts, local_vendors_tuple)
   - _process_lead_sync(lead_contacts, local_leads) with same missing-lead
     handling (ids_fetch_failed so we don't mark as deleted when fetch failed).

Result: Fewer API calls (deduplicated IDs, one list pass for both), less
redundant work, same behavior as v2 for update/create/flag-missing.
"""

import json
import logging
import sys
import os
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import AppConfig
from api.services.ghl_api_v2_optimized import OptimizedGoHighLevelAPI
from database.simple_connection import db as simple_db_instance

logger = logging.getLogger(__name__)

# Rate limit between GHL API calls (seconds)
GHL_RATE_LIMIT_DELAY = 0.12
# Max workers for concurrent fetch-by-ID (keep low to respect rate limits)
FETCH_BY_ID_WORKERS = 3
# Pagination for POST /contacts/search (non-deprecated); max 500 per request
SEARCH_PAGE_LIMIT = 500
LIST_SCAN_CAP = 15000  # max contacts to scan in fallback

# GHL signals: treat contact as vendor if source contains this (even when type=lead)
VENDOR_SOURCE_KEYWORD = "Vendor Application"
# Tags that indicate a contact is a vendor (case-insensitive)
VENDOR_TAGS = {"new vendor", "new vendor application", "manually approved"}
# Tags that indicate a contact is a lead
LEAD_TAGS = {"new lead"}
# Lead: if "new lead" tag -> status "new lead"
LEAD_TAG_NEW_LEAD_STATUS = "new lead"
# Vendor status from tags: (level, tag, status) — higher level wins
VENDOR_TAG_LEVELS = [
    (0, "new vendor application", "new application"),
    (1, "onboarding in process", "onboarding in process"),
    (2, "manual approval", "pending"),
    (3, "manually approved", "active"),
    (4, "deactivated", "deactivated"),
    (5, "reactivated", "active"),
]
DEFAULT_VENDOR_STATUS = "pending"
DEFAULT_LEAD_STATUS = "pending"
# Status when lead/vendor exists locally but is not found in GHL contacts
MISSING_IN_GHL_STATUS = "missing_in_ghl"
# Status when lead/vendor does not exist on GHL (set for both in that case)
INACTIVE_GHL_DELETED_STATUS = "inactive_ghl_deleted"


class EnhancedDatabaseSyncV3:
    """
    Efficient bi-directional sync: single unified contact fetch, then classify
    into vendors vs leads and run same vendor/lead sync logic as v2.
    """

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

    LEAD_GHL_FIELDS = {
        'customer_name': ['firstName', 'lastName'],
        'customer_email': 'email',
        'customer_phone': 'phone',
        'primary_service_category': 'HRqfv0HnUydNRLKWhk27',
        'specific_service_requested': 'FT85QGi0tBq1AfVGNJ9v',
    }

    def __init__(self):
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
            self._lead_contact_ids_fetch_failed: Set[str] = set()
            logger.info("✅ EnhancedDatabaseSyncV3 initialized (unified contact fetch)")
        except Exception as e:
            logger.error(f"❌ Failed to initialize sync v3: {e}")
            raise

    def sync_all(self) -> Dict[str, Any]:
        """Run full bi-directional sync using unified contact fetch."""
        logger.info("🔄 Starting V3 Database Sync (unified fetch)")
        logger.info("=" * 60)
        start_time = datetime.now()
        try:
            # Step 1: Collect all identifiers (vendors + leads) and local data
            logger.info("\n📊 STEP 1: Collecting vendor and lead identifiers")
            identifiers = self._collect_all_identifiers()
            if not identifiers:
                logger.warning("   No vendor or lead identifiers found")
                return self._finish_sync(start_time, success=True)

            # Step 2: Single unified contact fetch from GHL
            logger.info("\n📊 STEP 2: Unified GHL contact fetch (by ID + email search + optional list)")
            contact_map = self._unified_fetch_contacts(identifiers)
            self.stats['ghl_contacts_fetched'] = len(contact_map)

            # Step 3: Classify into vendor vs lead contacts
            logger.info("\n📊 STEP 3: Classifying contacts (vendors vs leads)")
            vendor_contacts = self._classify_vendor_contacts(contact_map, identifiers)
            lead_contacts = self._classify_lead_contacts(contact_map, identifiers)
            logger.info(f"   Vendor contacts: {len(vendor_contacts)}, Lead contacts: {len(lead_contacts)}")

            # Step 4: Process vendor sync
            logger.info("\n📊 STEP 4: Processing vendor sync")
            local_vendors = self._get_local_vendors()
            self._process_vendor_sync(vendor_contacts, local_vendors)

            # Step 5: Process lead sync
            logger.info("\n📊 STEP 5: Processing lead sync")
            local_leads = self._get_local_leads()
            self._process_lead_sync(lead_contacts, local_leads)

            return self._finish_sync(start_time, success=True)
        except Exception as e:
            logger.error(f"❌ Sync failed: {e}")
            return self._finish_sync(start_time, success=False, error=str(e))

    def _finish_sync(self, start_time: datetime, success: bool, error: Optional[str] = None) -> Dict[str, Any]:
        duration = (datetime.now() - start_time).total_seconds()
        logger.info("\n" + "=" * 60)
        logger.info("🎉 V3 SYNC COMPLETED" if success else "❌ V3 SYNC FAILED")
        logger.info(f"⏱️  Duration: {duration:.2f}s")
        logger.info(f"   Vendors: {self.stats['vendors_updated']} updated, {self.stats['vendors_created']} created, "
                   f"{self.stats.get('vendors_missing_in_ghl', 0)} missing in GHL")
        logger.info(f"   Leads: {self.stats['leads_updated']} updated, {self.stats['leads_created']} created, {self.stats['leads_deleted']} deactivated")
        if self.stats['errors']:
            for err in self.stats['errors'][:5]:
                logger.warning(f"   - {err}")
        message = (f"Sync completed in {duration:.2f}s. "
                   f"Vendors: {self.stats['vendors_updated']} updated, {self.stats['vendors_created']} created. "
                   f"Leads: {self.stats['leads_updated']} updated, {self.stats['leads_created']} created, {self.stats['leads_deleted']} deleted.")
        return {
            'success': success,
            'message': message,
            'stats': self.stats,
            'duration': duration,
            **({'error': error} if error else {})
        }

    # -------------------------------------------------------------------------
    # Identifier collection
    # -------------------------------------------------------------------------

    def _collect_all_identifiers(self) -> Optional[Dict[str, Any]]:
        """
        Load vendor and lead identifiers from DB in minimal queries.
        Returns dict with: vendor_contact_ids, vendor_emails, lead_contact_ids,
        lead_emails, lead_opportunity_ids, lead_id_by_contact_id, lead_id_by_email.
        """
        try:
            conn = simple_db_instance._get_raw_conn()
            cursor = conn.cursor()

            vendor_contact_ids: Set[str] = set()
            vendor_emails: Set[str] = set()
            cursor.execute("""
                SELECT ghl_contact_id, email FROM vendors
                WHERE ghl_contact_id IS NOT NULL OR email IS NOT NULL
            """)
            for row in cursor.fetchall():
                if row[0]:
                    vendor_contact_ids.add(row[0])
                if row[1]:
                    vendor_emails.add((row[1] or "").strip().lower())

            lead_contact_ids: Set[str] = set()
            lead_emails: Dict[str, Any] = {}   # email -> local lead id (for logging)
            lead_opportunity_ids: Dict[str, str] = {}  # opp_id -> local lead id
            lead_id_by_contact_id: Dict[str, str] = {}
            cursor.execute("""
                SELECT DISTINCT ghl_contact_id, customer_email, ghl_opportunity_id, id
                FROM leads
                WHERE (ghl_contact_id IS NOT NULL AND ghl_contact_id != '')
                   OR (customer_email IS NOT NULL AND customer_email != '')
            """)
            for row in cursor.fetchall():
                if row[0]:
                    lead_contact_ids.add(row[0])
                    lead_id_by_contact_id[row[0]] = row[3]
                if row[1]:
                    lead_emails[(row[1] or "").strip().lower()] = row[3]
                if row[2]:
                    lead_opportunity_ids[row[2]] = row[3]
            conn.close()

            all_contact_ids = vendor_contact_ids | lead_contact_ids
            logger.info(f"   Vendor IDs: {len(vendor_contact_ids)}, emails: {len(vendor_emails)}")
            logger.info(f"   Lead IDs: {len(lead_contact_ids)}, emails: {len(lead_emails)}")
            logger.info(f"   Unique contact IDs to fetch: {len(all_contact_ids)}")

            return {
                'vendor_contact_ids': vendor_contact_ids,
                'vendor_emails': vendor_emails,
                'lead_contact_ids': lead_contact_ids,
                'lead_emails': lead_emails,
                'lead_opportunity_ids': lead_opportunity_ids,
                'lead_id_by_contact_id': lead_id_by_contact_id,
                'all_contact_ids': all_contact_ids,
            }
        except Exception as e:
            logger.error(f"❌ Error collecting identifiers: {e}")
            self.stats['errors'].append(f"Collect identifiers: {str(e)}")
            return None

    # -------------------------------------------------------------------------
    # Unified contact fetch
    # -------------------------------------------------------------------------

    def _unified_fetch_contacts(self, identifiers: Dict[str, Any]) -> Dict[str, Dict]:
        """
        Fetch all needed contacts in one flow:
        1) Fetch by ID for each unique contact ID (concurrent with rate limit).
        2) For missing emails, search by email (one call per missing email).
        3) Optional: one paginated list pass to match remaining by email/opportunity (cap LIST_SCAN_CAP).
        """
        contact_map: Dict[str, Dict] = {}
        loc_id = getattr(self.ghl_api, 'location_id', None) or os.getenv('GHL_LOCATION_ID') or (
            AppConfig.GHL_LOCATION_ID if hasattr(AppConfig, 'GHL_LOCATION_ID') else None)
        all_ids = list(identifiers.get('all_contact_ids') or [])
        vendor_emails = identifiers.get('vendor_emails') or set()
        lead_emails = identifiers.get('lead_emails') or {}
        lead_opp_ids = identifiers.get('lead_opportunity_ids') or {}
        lead_contact_ids = identifiers.get('lead_contact_ids') or set()

        # 1) Fetch by ID (each unique ID once); track which lead IDs failed
        self._lead_contact_ids_fetch_failed = set()
        if all_ids:
            logger.info(f"   Fetching {len(all_ids)} contacts by ID (workers={FETCH_BY_ID_WORKERS})...")
            last_request_time = [0.0]  # mutable for closure
            import threading
            lock = threading.Lock()

            def fetch_one(cid: str) -> Tuple[str, Optional[Dict]]:
                with lock:
                    now = time.monotonic()
                    wait = GHL_RATE_LIMIT_DELAY - (now - last_request_time[0])
                    if wait > 0:
                        time.sleep(wait)
                    last_request_time[0] = time.monotonic()
                try:
                    c = self.ghl_api.get_contact_by_id(cid, location_id=loc_id)
                    return (cid, c)
                except Exception as e:
                    logger.debug(f"   Fetch failed for {cid}: {e}")
                    return (cid, None)

            with ThreadPoolExecutor(max_workers=FETCH_BY_ID_WORKERS) as executor:
                futures = {executor.submit(fetch_one, cid): cid for cid in all_ids}
                for fut in as_completed(futures):
                    cid, contact = fut.result()
                    if contact:
                        contact_map[cid] = contact
                    else:
                        if cid in lead_contact_ids:
                            self._lead_contact_ids_fetch_failed.add(cid)
                            logger.warning(f"   get_contact_by_id returned None for lead contact {cid}")
            logger.info(f"   Fetched {len(contact_map)} contacts by ID ({len(self._lead_contact_ids_fetch_failed)} lead IDs failed)")

        # 2) Missing emails: we need vendor_emails and lead_emails not yet in contact_map
        emails_in_map = { (c.get('email') or '').strip().lower() for c in contact_map.values() if c.get('email') }
        missing_emails = (vendor_emails | set(lead_emails.keys())) - emails_in_map
        if missing_emails:
            logger.info(f"   Searching by email for {len(missing_emails)} missing...")
            for email in list(missing_emails):
                try:
                    contacts = self.ghl_api.search_contacts_by_email(email, location_id=loc_id)
                    if contacts:
                        c = contacts[0]
                        cid = c.get('id')
                        if cid:
                            contact_map[cid] = c
                            missing_emails.discard(email)
                except Exception as e:
                    logger.debug(f"   Search by email failed for {email}: {e}")
                time.sleep(GHL_RATE_LIMIT_DELAY)
            logger.info(f"   After email search: {len(contact_map)} contacts, {len(missing_emails)} emails still missing")

        # 3) Optional: one pass using POST /contacts/search (non-deprecated) for remaining missing emails / opportunity match
        if missing_emails or lead_opp_ids:
            search_after = None
            total_scanned = 0
            logger.info(f"   Using POST /contacts/search (limit={SEARCH_PAGE_LIMIT}) for list fallback...")
            while total_scanned < LIST_SCAN_CAP:
                result = self.ghl_api.search_contacts_paginated(
                    location_id=loc_id,
                    limit=SEARCH_PAGE_LIMIT,
                    search_after=search_after,
                    query=None,
                )
                contacts = result.get("contacts") or []
                if not contacts:
                    break
                for contact in contacts:
                    cid = contact.get("id")
                    if cid in contact_map:
                        continue
                    email_lower = (contact.get("email") or "").strip().lower()
                    if email_lower and email_lower in missing_emails:
                        c_copy = {k: v for k, v in contact.items() if k != "searchAfter"}
                        contact_map[cid] = c_copy
                        missing_emails.discard(email_lower)
                    if cid not in contact_map and lead_opp_ids:
                        for f in contact.get("customFields", []):
                            if (f.get("value") or "") in lead_opp_ids:
                                c_copy = {k: v for k, v in contact.items() if k != "searchAfter"}
                                contact_map[cid] = c_copy
                                break
                total_scanned += len(contacts)
                search_after = result.get("search_after")
                if not search_after or (not missing_emails and not lead_opp_ids):
                    break
                time.sleep(0.2)
            logger.info(f"   After POST /contacts/search fallback: {len(contact_map)} contacts (scanned {total_scanned})")

        return contact_map

    def _get_contact_tags_list(self, ghl_contact: Dict) -> List[str]:
        """Return normalized list of tag strings (lowercase) from a GHL contact."""
        tags_raw = ghl_contact.get("tags") or []
        if isinstance(tags_raw, str):
            return [t.strip().lower() for t in tags_raw.split(",") if t.strip()]
        if isinstance(tags_raw, list):
            out = []
            for t in tags_raw:
                if isinstance(t, str):
                    out.append(t.strip().lower())
                elif isinstance(t, dict):
                    name = (t.get("name") or t.get("tag") or "").strip().lower()
                    if name:
                        out.append(name)
                else:
                    out.append(str(t).strip().lower())
            return out
        return []

    def _is_vendor_by_ghl_signals(self, ghl_contact: Dict) -> bool:
        """
        True if GHL contact should be treated as a vendor based on source or tags,
        even when type=lead. Source containing 'Vendor Application' or tags like
        'new vendor', 'new vendor application', 'manually approved'.
        """
        source = (ghl_contact.get("source") or "").strip()
        if VENDOR_SOURCE_KEYWORD.lower() in source.lower():
            return True
        tags = self._get_contact_tags_list(ghl_contact)
        return bool(tags and any(t in VENDOR_TAGS for t in tags))

    def _is_staff_contact(self, ghl_contact: Dict) -> bool:
        """True if GHL contact type is staff; staff should not be added as vendor or lead."""
        contact_type = (ghl_contact.get("type") or "").strip().lower()
        return contact_type == "staff"

    def _classify_vendor_contacts(self, contact_map: Dict[str, Dict], identifiers: Dict[str, Any]) -> Dict[str, Dict]:
        vendor_ids = identifiers.get("vendor_contact_ids") or set()
        vendor_emails = identifiers.get("vendor_emails") or set()
        return {
            cid: c
            for cid, c in contact_map.items()
            if not self._is_staff_contact(c)
            and (
                cid in vendor_ids
                or ((c.get("email") or "").strip().lower() in vendor_emails)
                or self._is_vendor_by_ghl_signals(c)
            )
        }

    def _classify_lead_contacts(self, contact_map: Dict[str, Dict], identifiers: Dict[str, Any]) -> Dict[str, Dict]:
        """Lead = DB match only; exclude contacts that are vendor by GHL signals (vendor takes precedence)."""
        lead_ids = identifiers.get("lead_contact_ids") or set()
        lead_emails = identifiers.get("lead_emails") or {}
        return {
            cid: c
            for cid, c in contact_map.items()
            if not self._is_staff_contact(c)
            and (cid in lead_ids or ((c.get("email") or "").strip().lower() in lead_emails))
            and not self._is_vendor_by_ghl_signals(c)
        }

    # -------------------------------------------------------------------------
    # Local data (same as v2)
    # -------------------------------------------------------------------------

    def _get_local_vendors(self) -> Tuple[Dict[str, Dict], Dict[str, Dict]]:
        local_by_ghl_id: Dict[str, Dict] = {}
        local_by_email: Dict[str, Dict] = {}
        try:
            for v in simple_db_instance.get_vendors():
                ghl_id = v.get('ghl_contact_id')
                email = (v.get('email') or '').strip().lower()
                if ghl_id:
                    local_by_ghl_id[ghl_id] = v
                if email:
                    local_by_email[email] = v
            return local_by_ghl_id, local_by_email
        except Exception as e:
            logger.error(f"❌ Error fetching local vendors: {e}")
            self.stats['errors'].append(f"Local vendors: {str(e)}")
            return {}, {}

    def _get_local_leads(self) -> Dict[str, Dict]:
        local_by_ghl_id: Dict[str, Dict] = {}
        local_by_email: Dict[str, Dict] = {}
        try:
            conn = simple_db_instance._get_raw_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, ghl_contact_id, customer_name, customer_email, customer_phone,
                       primary_service_category, specific_service_requested, customer_zip_code,
                       service_county, service_state, status, vendor_id, ghl_opportunity_id
                FROM leads
            """)
            for row in cursor.fetchall():
                lead = {
                    'id': row[0], 'ghl_contact_id': row[1], 'customer_name': row[2], 'customer_email': row[3],
                    'customer_phone': row[4], 'primary_service_category': row[5], 'specific_service_requested': row[6],
                    'customer_zip_code': row[7], 'service_county': row[8], 'service_state': row[9],
                    'status': row[10], 'vendor_id': row[11], 'ghl_opportunity_id': row[12] if len(row) > 12 else None
                }
                if lead['ghl_contact_id']:
                    local_by_ghl_id[lead['ghl_contact_id']] = lead
                if lead['customer_email']:
                    local_by_email[(lead['customer_email'] or '').strip().lower()] = lead
            conn.close()
            combined = {}
            combined.update(local_by_email)
            combined.update(local_by_ghl_id)
            return combined
        except Exception as e:
            logger.error(f"❌ Error fetching local leads: {e}")
            return {}

    # -------------------------------------------------------------------------
    # Vendor sync (same logic as v2)
    # -------------------------------------------------------------------------

    def _process_vendor_sync(self, ghl_vendors: Dict[str, Dict], local_vendors_tuple: Tuple[Dict, Dict]):
        local_by_ghl_id, local_by_email = local_vendors_tuple
        processed = set()
        for ghl_id, ghl_contact in ghl_vendors.items():
            contact_email = (ghl_contact.get('email') or '').strip().lower()
            matched = local_by_ghl_id.get(ghl_id) or (local_by_email.get(contact_email) if contact_email else None)
            if matched:
                processed.add(matched['id'])
                if not matched.get('ghl_contact_id'):
                    matched['ghl_contact_id'] = ghl_id
                    logger.info(f"   Matched vendor by email, adding GHL contact ID: {ghl_id}")
                self._update_local_vendor(matched, ghl_contact)
            else:
                logger.warning(f"   Creating new vendor - not found by ID or email: {ghl_contact.get('email')}")
                self._create_local_vendor(ghl_contact)
        all_local = list(local_by_ghl_id.values()) + list(local_by_email.values())
        missing = [v for v in all_local if v['id'] not in processed]
        for v in missing:
            self._handle_missing_ghl_vendor(v)

    def _update_local_vendor(self, local_vendor: Dict, ghl_contact: Dict):
        try:
            updates = self._extract_vendor_updates(local_vendor, ghl_contact)
            if not local_vendor.get('ghl_contact_id') and ghl_contact.get('id'):
                updates['ghl_contact_id'] = ghl_contact.get('id')
            if updates:
                if self._update_vendor_record(local_vendor['id'], updates):
                    self.stats['vendors_updated'] += 1
        except Exception as e:
            logger.error(f"❌ Error updating vendor {local_vendor.get('id')}: {e}")
            self.stats['errors'].append(str(e))

    def _extract_vendor_updates(self, vendor: Dict, ghl_contact: Dict) -> Dict[str, Any]:
        updates = {}
        custom_fields = {}
        for field in ghl_contact.get('customFields', []):
            fid = field.get('id', '')
            val = field.get('value', '') or field.get('fieldValue', '')
            if fid:
                custom_fields[fid] = val
        ghl_user = custom_fields.get('HXVNT4y8OynNokWAfO2D', '').strip()
        if ghl_user and not vendor.get('ghl_user_id'):
            updates['ghl_user_id'] = ghl_user
        tag_status = self._get_vendor_status_from_tags(ghl_contact)
        if vendor.get('status') != tag_status:
            updates['status'] = tag_status
        zip_val = custom_fields.get('yDcN0FmwI3xacyxAuTWs', '').strip()
        if zip_val:
            cov = self._parse_coverage_from_zip_codes(zip_val)
            if cov['type']:
                if vendor.get('coverage_type') != cov['type']:
                    updates['coverage_type'] = cov['type']
                if cov['states']:
                    updates['coverage_states'] = json.dumps(cov['states'])
                if cov['counties']:
                    updates['coverage_counties'] = json.dumps(cov['counties'])
        for db_field, ghl_field in self.VENDOR_GHL_FIELDS.items():
            if db_field == 'service_zip_codes':
                continue
            current = vendor.get(db_field)
            new_value = None
            if db_field == 'name' and ghl_field == ['firstName', 'lastName']:
                new_value = f"{ghl_contact.get('firstName', '')} {ghl_contact.get('lastName', '')}".strip()
            elif ghl_field in ['email', 'phone']:
                new_value = (ghl_contact.get(ghl_field) or '').strip()
            elif isinstance(ghl_field, list):
                for fid in ghl_field:
                    v = custom_fields.get(fid, '').strip()
                    if v:
                        new_value = v
                        break
            else:
                raw = custom_fields.get(ghl_field, '')
                new_value = raw.strip() if isinstance(raw, str) else (str(raw) if raw else '')
            if db_field in ['service_categories', 'services_offered'] and new_value:
                new_value = json.dumps([s.strip() for s in new_value.split(',') if s.strip()])
            elif db_field == 'lead_close_percentage':
                try:
                    new_value = float((new_value or '0').replace('%', '').strip()) if new_value else 0.0
                except Exception:
                    new_value = 0.0
            elif db_field == 'taking_new_work' and new_value:
                new_value = 'Yes' if (new_value.strip().lower() in ['yes', 'true', '1']) else 'No'
            if new_value is not None and self._values_differ(current, new_value, db_field):
                updates[db_field] = new_value
        return updates

    def _parse_coverage_from_zip_codes(self, value: str) -> Dict:
        n = value.upper().strip()
        if 'GLOBAL' in n:
            return {'type': 'global', 'states': [], 'counties': []}
        if 'NATIONAL' in n or n in ['USA', 'UNITED STATES']:
            return {'type': 'national', 'states': [], 'counties': []}
        if ';' in value:
            items = [s.strip() for s in value.split(';') if s.strip()]
            if items and ', ' in items[0]:
                states = list({s.split(', ')[-1].strip() for s in items if ', ' in s})
                return {'type': 'county', 'states': states, 'counties': items}
        if ',' in value:
            items = [s.strip() for s in value.split(',') if s.strip()]
            if all(len(i) == 2 and i.isupper() for i in items):
                return {'type': 'state', 'states': items, 'counties': []}
        return {'type': None, 'states': None, 'counties': None}

    def _get_vendor_status_from_tags(self, ghl_contact: Dict) -> str:
        """Vendor status from tags by level; higher level wins."""
        tags_list = self._get_contact_tags_list(ghl_contact)
        tags_set = set(tags_list)
        best_level = -1
        status = DEFAULT_VENDOR_STATUS
        for level, tag, st in VENDOR_TAG_LEVELS:
            if tag in tags_set and level > best_level:
                best_level = level
                status = st
        return status

    def _get_lead_status_from_tags(self, ghl_contact: Dict) -> Optional[str]:
        """Lead status from tags: 'new lead' -> 'new lead'. Returns None to leave unchanged."""
        tags_list = self._get_contact_tags_list(ghl_contact)
        if "new lead" in tags_list:
            return LEAD_TAG_NEW_LEAD_STATUS
        return None

    def _values_differ(self, current: Any, new: Any, field_name: str) -> bool:
        if current is None and new == '':
            return False
        if current == '' and new is None:
            return False
        if field_name in ['service_categories', 'services_offered', 'coverage_states', 'coverage_counties']:
            try:
                a = set(json.loads(current) if current else [])
                b = set(json.loads(new) if new else [])
                return a != b
            except Exception:
                return str(current) != str(new)
        return str(current or '').strip() != str(new or '').strip()

    def _create_local_vendor(self, ghl_contact: Dict):
        try:
            custom_fields = {cf['id']: cf.get('value', '') for cf in ghl_contact.get('customFields', [])}
            account = simple_db_instance.get_account_by_ghl_location_id(
                os.getenv('GHL_LOCATION_ID') or AppConfig.GHL_LOCATION_ID)
            if not account:
                logger.error("❌ No account found for location")
                return
            tag_status = self._get_vendor_status_from_tags(ghl_contact)
            vendor_id = simple_db_instance.create_vendor(
                account_id=account['id'],
                name=f"{ghl_contact.get('firstName', '')} {ghl_contact.get('lastName', '')}".strip(),
                email=ghl_contact.get('email', ''),
                company_name=custom_fields.get('JexVrg2VNhnwIX7YlyJV', ''),
                phone=ghl_contact.get('phone', ''),
                ghl_contact_id=ghl_contact.get('id'),
                status=tag_status,
                taking_new_work=True,
            )
            if vendor_id:
                self.stats['vendors_created'] += 1
                logger.info(f"✅ Created NEW vendor from GHL: {ghl_contact.get('email')}")
        except Exception as e:
            logger.error(f"❌ Error creating vendor: {e}")
            self.stats['errors'].append(str(e))

    def _handle_missing_ghl_vendor(self, local_vendor: Dict):
        """Set vendor status to inactive_ghl_deleted when not found in GHL contacts."""
        try:
            updates = {'status': INACTIVE_GHL_DELETED_STATUS}
            if self._update_vendor_record(local_vendor['id'], updates):
                self.stats['vendors_missing_in_ghl'] = self.stats.get('vendors_missing_in_ghl', 0) + 1
        except Exception as e:
            self.stats['errors'].append(str(e))

    def _update_vendor_record(self, vendor_id: str, updates: Dict) -> bool:
        try:
            if not updates:
                return True
            conn = simple_db_instance._get_raw_conn()
            cursor = conn.cursor()
            set_clauses = [f"{k} = ?" for k in updates]
            values = list(updates.values()) + [vendor_id]
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            cursor.execute(f"UPDATE vendors SET {', '.join(set_clauses)} WHERE id = ?", values)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"❌ Error updating vendor {vendor_id}: {e}")
            return False

    # -------------------------------------------------------------------------
    # Lead sync (same logic as v2)
    # -------------------------------------------------------------------------

    def _process_lead_sync(self, ghl_leads: Dict[str, Dict], local_leads: Dict[str, Dict]):
        processed = set()
        for ghl_id, ghl_contact in ghl_leads.items():
            local_lead = local_leads.get(ghl_id)
            if not local_lead and ghl_contact.get('email'):
                local_lead = local_leads.get((ghl_contact.get('email') or '').strip().lower())
            if local_lead:
                self._update_local_lead(local_lead, ghl_contact)
                processed.add(local_lead['id'])
            else:
                # GHL contact is a lead but not in local DB -> create local lead
                self._create_local_lead(ghl_contact)
        all_local_ids = set(lead['id'] for lead in local_leads.values())
        ids_fetch_failed = getattr(self, '_lead_contact_ids_fetch_failed', set())
        for local_lead_id in all_local_ids:
            if local_lead_id in processed:
                continue
            local_lead = next((lead for lead in local_leads.values() if lead['id'] == local_lead_id), None)
            if not local_lead:
                continue
            ghl_cid = local_lead.get('ghl_contact_id') or ''
            if ghl_cid and ghl_cid in ids_fetch_failed:
                logger.warning(f"   Skipping mark-deleted for lead (ghl_contact_id {ghl_cid}): fetch failed")
                continue
            self._handle_missing_lead(local_lead)

    def _update_local_lead(self, local_lead: Dict, ghl_contact: Dict):
        try:
            updates = self._extract_lead_updates(local_lead, ghl_contact)
            if updates and self._update_lead_record(local_lead['id'], updates):
                self.stats['leads_updated'] += 1
        except Exception as e:
            logger.error(f"❌ Error updating lead: {e}")

    def _extract_lead_updates(self, lead: Dict, ghl_contact: Dict) -> Dict[str, Any]:
        updates = {}
        custom_fields = {cf['id']: cf.get('value', '') for cf in ghl_contact.get('customFields', [])}
        for db_field, ghl_field in self.LEAD_GHL_FIELDS.items():
            current = lead.get(db_field)
            new_value = None
            if db_field == 'customer_name' and ghl_field == ['firstName', 'lastName']:
                new_value = f"{ghl_contact.get('firstName', '')} {ghl_contact.get('lastName', '')}".strip()
            elif ghl_field == 'email':
                new_value = (ghl_contact.get('email') or '').strip()
            elif ghl_field == 'phone':
                new_value = (ghl_contact.get('phone') or '').strip()
            else:
                raw = custom_fields.get(ghl_field, '')
                new_value = raw.strip() if isinstance(raw, str) else (str(raw) if raw else '')
            if new_value and current != new_value:
                updates[db_field] = new_value
        zip_code = None
        if ghl_contact.get('postalCode'):
            zip_code = str(ghl_contact.get('postalCode'))
        elif ghl_contact.get('address1'):
            import re
            m = re.search(r'\b(\d{5})\b', ghl_contact.get('address1', ''))
            if m:
                zip_code = m.group(1)
        if zip_code and lead.get('service_zip_code') != zip_code:
            updates['service_zip_code'] = zip_code
        zip_to_convert = updates.get('service_zip_code') or lead.get('service_zip_code')
        if zip_to_convert and len(str(zip_to_convert)) == 5:
            try:
                from api.services.location_service import location_service
                loc = location_service.zip_to_location(str(zip_to_convert))
                if not loc.get('error'):
                    if loc.get('county') and not lead.get('service_county'):
                        updates['service_county'] = loc.get('county', '')
                    if loc.get('state') and not lead.get('service_state'):
                        updates['service_state'] = loc.get('state', '')
            except Exception:
                pass
        # Lead status from tags (e.g. "new lead" -> unassigned; default pending)
        tag_status = self._get_lead_status_from_tags(ghl_contact)
        if tag_status is not None and lead.get('status') != tag_status:
            updates['status'] = tag_status
        return updates

    def _create_local_lead(self, ghl_contact: Dict):
        """Create new lead in local DB when contact exists in GHL but not locally."""
        try:
            custom_fields = {cf['id']: cf.get('value', '') for cf in ghl_contact.get('customFields', [])}
            account = simple_db_instance.get_account_by_ghl_location_id(
                os.getenv('GHL_LOCATION_ID') or AppConfig.GHL_LOCATION_ID
            )
            if not account:
                logger.error("❌ No account found for location - cannot create lead")
                return
            import uuid
            status = self._get_lead_status_from_tags(ghl_contact) or "unassigned"
            zip_code = (
                custom_fields.get('RmAja1dnU0u42ECXhCo9', '') or
                str(ghl_contact.get('postalCode') or '')
            ).strip()
            if not zip_code and ghl_contact.get('address1'):
                import re
                m = re.search(r'\b(\d{5})\b', ghl_contact.get('address1', ''))
                if m:
                    zip_code = m.group(1)
            lead_data = {
                'id': str(uuid.uuid4()),
                'account_id': account['id'],
                'ghl_contact_id': ghl_contact.get('id'),
                'customer_name': f"{ghl_contact.get('firstName', '')} {ghl_contact.get('lastName', '')}".strip(),
                'customer_email': ghl_contact.get('email', ''),
                'customer_phone': ghl_contact.get('phone', ''),
                'primary_service_category': custom_fields.get('HRqfv0HnUydNRLKWhk27', ''),
                'specific_service_requested': custom_fields.get('FT85QGi0tBq1AfVGNJ9v', ''),
                'customer_zip_code': zip_code,
                'service_zip_code': zip_code,
                'status': status,
                'source': 'ghl_sync',
            }
            if zip_code and len(str(zip_code)) == 5:
                try:
                    from api.services.location_service import location_service
                    loc = location_service.zip_to_location(str(zip_code))
                    if not loc.get('error'):
                        lead_data['service_county'] = loc.get('county', '')
                        lead_data['service_state'] = loc.get('state', '')
                except Exception:
                    pass
            conn = simple_db_instance._get_raw_conn()
            cursor = conn.cursor()
            columns = list(lead_data.keys())
            placeholders = ['?' for _ in columns]
            values = [lead_data[col] for col in columns]
            cursor.execute(
                f"INSERT INTO leads ({', '.join(columns)}) VALUES ({', '.join(placeholders)})",
                values,
            )
            conn.commit()
            conn.close()
            self.stats['leads_created'] += 1
            logger.info(f"✅ Created NEW lead from GHL: {lead_data['customer_name']}")
        except Exception as e:
            logger.error(f"❌ Error creating lead from GHL: {e}")
            self.stats['errors'].append(f"Create lead: {str(e)}")

    def _handle_missing_lead(self, local_lead: Dict):
        """Set lead status to inactive_ghl_deleted when not found in GHL contacts."""
        try:
            if self._update_lead_record(local_lead['id'], {'status': INACTIVE_GHL_DELETED_STATUS}):
                self.stats['leads_deleted'] += 1
        except Exception as e:
            self.stats['errors'].append(str(e))

    def _update_lead_record(self, lead_id: str, updates: Dict) -> bool:
        try:
            if not updates:
                return True
            conn = simple_db_instance._get_raw_conn()
            cursor = conn.cursor()
            set_clauses = [f"{k} = ?" for k in updates]
            values = list(updates.values()) + [lead_id]
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            cursor.execute(f"UPDATE leads SET {', '.join(set_clauses)} WHERE id = ?", values)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"❌ Error updating lead {lead_id}: {e}")
            return False


if __name__ == "__main__":
    print("🚀 Enhanced Database Sync V3 (unified contact fetch)")
    print("=" * 60)
    response = input("Continue? (y/n): ")
    if response.lower() == 'y':
        sync = EnhancedDatabaseSyncV3()
        results = sync.sync_all()
        print("\n✅ Sync completed!" if results['success'] else f"\n❌ Sync failed: {results.get('error')}")
        print(json.dumps(results.get('stats', {}), indent=2))
