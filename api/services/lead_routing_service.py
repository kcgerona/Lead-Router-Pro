# api/services/lead_routing_service.py

import logging
import random
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from api.services.location_service import location_service
from api.services.service_categories import service_manager
from database.simple_connection import db as simple_db_instance

logger = logging.getLogger(__name__)

class LeadRoutingService:
    """
    Enhanced lead routing service that supports:
    - Geographic coverage types (global, national, state, county, zip)
    - Dual routing methods (round-robin vs performance-based)
    - Configurable routing distribution percentages
    - DIRECT STRING MATCHING for service matching (no keyword matching)
    """
    
    def __init__(self):
        self.location_service = location_service
    
    def find_matching_vendors(self, account_id: str, service_category: str,
                            zip_code: str, priority: str = "normal",
                            specific_service: str = None, test_mode: bool = False) -> List[Dict[str, Any]]:
        """
        Find all vendors that can serve the specified location and service category.
        Enhanced with multi-level service matching for precise vendor routing.

        Args:
            account_id: Account ID to search within
            service_category: Primary service category (e.g., "Marine Systems")
            zip_code: ZIP code where service is needed
            priority: Priority level of the request
            specific_service: Specific service needed (e.g., "AC Service") - NEW
            test_mode: If True, allows pending/missing vendors for testing (default: False for live assignments)

        Returns:
            List of matching vendors with coverage verification
        """
        try:
            # Convert ZIP code to location information
            location_data = self.location_service.zip_to_location(zip_code)
            
            if location_data.get('error'):
                logger.warning(f"⚠️ Could not resolve ZIP code {zip_code}: {location_data['error']}")
                # Continue with limited matching for legacy ZIP code vendors
                target_state = None
                target_county = None
            else:
                target_state = location_data.get('state')
                target_county = location_data.get('county')
                logger.info(f"📍 Lead location: {zip_code} → {target_state}, {target_county} County")
            
            # Get all active vendors for this account
            all_vendors = self._get_vendors_from_database(account_id)
            eligible_vendors = []
            
            for vendor in all_vendors:
                vendor_name = vendor.get('company_name', vendor.get('name', 'Unknown'))

                # Check vendor status and availability
                # Test mode: Allow active, pending, and missing_in_ghl vendors for testing
                # Live mode: Only allow active vendors for real lead assignments
                if test_mode:
                    # Test mode: Exclude only inactive/suspended vendors
                    if vendor.get("status") in ["inactive", "suspended"]:
                        logger.debug(f"❌ Skipping vendor {vendor_name} - status={vendor.get('status')} (test mode: only excludes inactive/suspended)")
                        continue
                else:
                    # Live mode: Strict filter - only active vendors
                    if vendor.get("status") != "active":
                        logger.debug(f"❌ Skipping vendor {vendor_name} - status={vendor.get('status')} (live mode: requires 'active')")
                        continue

                # Check if taking new work (applies to both modes)
                if not vendor.get("taking_new_work", False):
                    logger.debug(f"❌ Skipping vendor {vendor_name} - not taking new work")
                    continue
                
                # DIRECT SERVICE MATCHING - match specific service if provided, otherwise category
                service_to_match = specific_service if specific_service else service_category
                logger.debug(f"🔍 Checking vendor {vendor_name} for service: '{service_to_match}'")
                
                if not self._vendor_matches_service(vendor, service_to_match):
                    logger.debug(f"❌ Skipping vendor {vendor_name} - no service match for '{service_to_match}'")
                    continue
                
                # Check if vendor can serve this location
                if self._vendor_covers_location(vendor, zip_code, target_state, target_county):
                    # Add coverage info for debugging
                    vendor_copy = vendor.copy()
                    vendor_copy['coverage_match_reason'] = self._get_coverage_match_reason(
                        vendor, zip_code, target_state, target_county
                    )
                    eligible_vendors.append(vendor_copy)
                    logger.info(f"✅ MATCH: Vendor {vendor_name} matches - {vendor_copy['coverage_match_reason']}")
                else:
                    logger.debug(f"❌ Skipping vendor {vendor_name} - location not covered")
            
            service_desc = f"specific service '{specific_service}'" if specific_service else f"category '{service_category}'"
            logger.info(f"🎯 Found {len(eligible_vendors)} eligible vendors for {service_desc} in {zip_code}")
            return eligible_vendors
            
        except Exception as e:
            logger.error(f"❌ Error finding matching vendors: {e}")
            return []
    
    def _get_vendors_from_database(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Get vendors from database using ACTUAL field names (no incorrect mapping).
        FIXED: Uses the field names that actually exist in the database.
        """
        try:
            import sqlite3
            
            conn = sqlite3.connect('smart_lead_router.db')
            cursor = conn.cursor()
            
            # Query vendors using ACTUAL database field names
            cursor.execute("""
                SELECT id, account_id, ghl_contact_id, ghl_user_id, name, email, phone,
                       company_name, service_categories, services_offered, coverage_type,
                       coverage_states, coverage_counties, last_lead_assigned,
                       lead_close_percentage, status, taking_new_work
                FROM vendors
                WHERE account_id = ?
            """, (account_id,))
            
            vendors = []
            for row in cursor.fetchall():
                vendor = {
                    'id': row[0],
                    'account_id': row[1],
                    'ghl_contact_id': row[2],
                    'ghl_user_id': row[3],
                    'name': row[4],
                    'email': row[5],
                    'phone': row[6],
                    'company_name': row[7],
                    'service_categories': json.loads(row[8]) if row[8] else [],
                    'services_offered': json.loads(row[9]) if row[9] else [],  # ACTUAL field name
                    'coverage_type': row[10] or 'county',  # ACTUAL field name
                    'coverage_states': json.loads(row[11]) if row[11] else [],  # ACTUAL field name
                    'coverage_counties': json.loads(row[12]) if row[12] else [],  # ACTUAL field name
                    'last_lead_assigned': row[13],
                    'lead_close_percentage': row[14] or 0.0,
                    'status': row[15] or 'active',
                    'taking_new_work': bool(row[16]) if row[16] is not None else True
                }
                vendors.append(vendor)
            
            conn.close()
            logger.debug(f"📊 Retrieved {len(vendors)} vendors using actual field names for account {account_id}")
            return vendors
            
        except Exception as e:
            logger.error(f"❌ Error getting vendors from database: {e}")
            return []
    
    def _vendor_matches_service(self, vendor: Dict[str, Any], service_requested: str) -> bool:
        """
        Check if vendor provides the requested service.
        CRITICAL FIX: Properly handles Level 3 specific services vs Level 2 categories.
        
        Args:
            vendor: Vendor dictionary with services_offered field
            service_requested: Service requested - can be Level 2 category or Level 3 specific service
            
        Returns:
            bool: True if vendor offers the service, False otherwise
        """
        try:
            # Import service categories for Level 2/3 matching
            from api.services.service_categories import SERVICE_CATEGORIES, LEVEL_3_SERVICES
            
            services_offered = vendor.get('services_offered', [])
            
            # Handle string format (convert to list)
            if isinstance(services_offered, str):
                try:
                    services_offered = json.loads(services_offered)
                except (json.JSONDecodeError, TypeError):
                    # If JSON parsing fails, treat as comma-separated string
                    services_offered = [s.strip() for s in services_offered.split(',') if s.strip()]
            
            # Ensure it's a list
            if not isinstance(services_offered, list):
                logger.warning(f"Vendor {vendor.get('name')} has malformed services_offered: {services_offered}")
                return False
            
            # Direct string matching - case insensitive
            service_lower = str(service_requested).strip().lower()
            
            # CRITICAL: Determine if vendor has Level 3 services
            vendor_has_level3 = False
            vendor_level3_services = set()
            
            # Check all vendor's services against known Level 3 services
            for category_dict in LEVEL_3_SERVICES.values():
                for subcategory, level3_list in category_dict.items():
                    for offered_service in services_offered:
                        if offered_service in level3_list:
                            vendor_has_level3 = True
                            vendor_level3_services.add(offered_service)
            
            if vendor_has_level3:
                logger.debug(f"🔍 Vendor has Level 3 services: {vendor_level3_services}")
                
                # For vendors with Level 3 services, ONLY match on exact Level 3 service
                for offered_service in services_offered:
                    offered_lower = str(offered_service).strip().lower()
                    if offered_lower == service_lower:
                        logger.info(f"✅ Level 3 EXACT match: '{service_requested}' == '{offered_service}'")
                        return True
                
                # Special case: If service_requested is a Level 1 category (like "Boat Maintenance")
                # and vendor has specific Level 3 services for subcategories under it, do NOT match
                # This prevents vendors who specified Level 3 services from getting generic category leads
                if service_requested in SERVICE_CATEGORIES:
                    logger.debug(f"❌ Lead requests Level 1 category '{service_requested}' but vendor has specific Level 3 services")
                    return False
                
                # Check if requested service is a subcategory that has Level 3 services
                for category, subcategories in LEVEL_3_SERVICES.items():
                    if service_requested in subcategories:
                        logger.debug(f"❌ Lead requests subcategory '{service_requested}' but vendor specified Level 3 services")
                        return False
                
                logger.debug(f"❌ No Level 3 match: '{service_requested}' not in vendor's Level 3 services: {vendor_level3_services}")
                return False
            
            # For vendors with only Level 2 services (backward compatibility)
            logger.debug(f"🔍 Vendor uses Level 2 services: {services_offered}")
            
            # First try exact match
            for offered_service in services_offered:
                offered_lower = str(offered_service).strip().lower()
                
                # Exact match
                if offered_lower == service_lower:
                    logger.info(f"✅ Level 2 EXACT match: '{service_requested}' == '{offered_service}'")
                    return True
                
                # Handle common variations (e.g., "Boat Bottom Cleaning" matches "Bottom Cleaning")
                if service_lower == "bottom cleaning" and "bottom cleaning" in offered_lower:
                    logger.debug(f"✅ Service variant match: '{service_requested}' matched with '{offered_service}'")
                    return True
            
            # Check if service_requested is a child of any vendor's offered categories
            for offered_service in services_offered:
                # Check if offered_service is a category
                if offered_service in SERVICE_CATEGORIES:
                    # Get all services under this category
                    category_services = SERVICE_CATEGORIES.get(offered_service, [])
                    category_services_lower = [s.lower() for s in category_services]
                    
                    # Check if requested service is in this category
                    if service_lower in category_services_lower:
                        logger.info(f"✅ Level 2 parent match: Vendor offers category '{offered_service}' which includes '{service_requested}'")
                        return True
            
            # Check if this is a Level 2 category requested and vendor offers services under it
            if service_requested in SERVICE_CATEGORIES:
                # This is a Level 2 category - check if vendor offers ANY Level 3 service under this category
                category_services = SERVICE_CATEGORIES.get(service_requested, [])
                category_services_lower = [s.lower() for s in category_services]
                
                for offered_service in services_offered:
                    offered_lower = str(offered_service).strip().lower()
                    if offered_lower in category_services_lower:
                        logger.info(f"✅ Level 2 category match: Vendor offers '{offered_service}' under '{service_requested}'")
                        return True
                
                logger.debug(f"❌ No Level 3 services found for category '{service_requested}' in vendor's services: {services_offered}")
            else:
                # Not a category and no exact match found
                logger.debug(f"❌ No match for '{service_requested}' in services offered: {services_offered}")
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error in service matching for vendor {vendor.get('name')}: {e}")
            return False
    
    def _vendor_covers_location(self, vendor: Dict[str, Any], zip_code: str, 
                              target_state: Optional[str], target_county: Optional[str]) -> bool:
        """
        Check if vendor covers the specified location, with improved data validation.
        FIXED: Uses actual database field names (coverage_type, coverage_states, coverage_counties)
        """
        coverage_type = vendor.get('coverage_type', 'zip')  # FIXED: Use actual field name
        vendor_name = vendor.get('company_name', vendor.get('name', 'Unknown'))
        
        logger.debug(f"🔍 Checking coverage for vendor {vendor_name}: type={coverage_type}, target_state={target_state}, target_county={target_county}")
        
        if coverage_type == 'global':
            logger.debug(f"✅ Vendor {vendor_name} has GLOBAL coverage - matches all locations")
            return True
        
        if coverage_type == 'national':
            matches = target_state is not None
            logger.debug(f"{'✅' if matches else '❌'} Vendor {vendor_name} has NATIONAL coverage - matches={matches} (target_state={target_state})")
            return matches
        
        if coverage_type == 'state':
            if not target_state:
                logger.debug(f"❌ Vendor {vendor_name} has STATE coverage but no target_state provided")
                return False
            coverage_states = vendor.get('coverage_states', [])  # FIXED: Use actual field name
            if not isinstance(coverage_states, list):
                logger.warning(f"Vendor {vendor_name} has malformed coverage_states: {coverage_states}")
                return False
            
            # Map of state codes to full names for matching flexibility
            state_mapping = {
                'FL': 'Florida', 'CA': 'California', 'NY': 'New York', 'TX': 'Texas',
                'GA': 'Georgia', 'NC': 'North Carolina', 'SC': 'South Carolina',
                'AL': 'Alabama', 'LA': 'Louisiana', 'MS': 'Mississippi', 'TN': 'Tennessee',
                'KY': 'Kentucky', 'VA': 'Virginia', 'MD': 'Maryland', 'NJ': 'New Jersey',
                'PA': 'Pennsylvania', 'OH': 'Ohio', 'MI': 'Michigan', 'IN': 'Indiana',
                'IL': 'Illinois', 'WI': 'Wisconsin', 'MO': 'Missouri', 'AR': 'Arkansas'
            }
            
            # Check if target state matches any coverage state (handle both codes and full names)
            matches = False
            for coverage_state in coverage_states:
                coverage_state_clean = coverage_state.strip()
                # Direct match (code to code or name to name)
                if target_state == coverage_state_clean:
                    matches = True
                    break
                # Check if target is code and coverage is full name
                if target_state in state_mapping and state_mapping[target_state] == coverage_state_clean:
                    matches = True
                    break
                # Check if target matches when looked up as full name
                if target_state == state_mapping.get(coverage_state_clean):
                    matches = True
                    break
            
            logger.debug(f"{'✅' if matches else '❌'} Vendor {vendor_name} STATE coverage check: {target_state} in {coverage_states} = {matches}")
            return matches
        
        if coverage_type == 'county':
            if not target_county or not target_state:
                logger.debug(f"❌ Vendor {vendor_name} has COUNTY coverage but missing target location (county={target_county}, state={target_state})")
                return False
            coverage_counties = vendor.get('coverage_counties', [])  # FIXED: Use actual field name
            if not isinstance(coverage_counties, list):
                logger.warning(f"Vendor {vendor_name} has malformed coverage_counties: {coverage_counties}")
                return False
            
            # Map of state codes to full names for matching flexibility
            state_mapping = {
                'FL': 'Florida', 'CA': 'California', 'NY': 'New York', 'TX': 'Texas',
                'GA': 'Georgia', 'NC': 'North Carolina', 'SC': 'South Carolina',
                'AL': 'Alabama', 'LA': 'Louisiana', 'MS': 'Mississippi', 'TN': 'Tennessee',
                'KY': 'Kentucky', 'VA': 'Virginia', 'MD': 'Maryland', 'NJ': 'New Jersey',
                'PA': 'Pennsylvania', 'OH': 'Ohio', 'MI': 'Michigan', 'IN': 'Indiana',
                'IL': 'Illinois', 'WI': 'Wisconsin', 'MO': 'Missouri', 'AR': 'Arkansas'
            }
            
            # Build possible county string formats to match
            county_formats = [
                f"{target_county}, {target_state}",  # "Broward, FL"
                f"{target_county} County, {target_state}",  # "Broward County, FL"
                f"{target_county}, {state_mapping.get(target_state, target_state)}",  # "Broward, Florida"
                f"{target_county} County, {state_mapping.get(target_state, target_state)}"  # "Broward County, Florida"
            ]
            
            for coverage_area in coverage_counties:
                coverage_clean = coverage_area.strip()
                
                # Check all possible formats
                for county_format in county_formats:
                    if coverage_clean.lower() == county_format.lower():
                        logger.debug(f"✅ Vendor {vendor_name} COUNTY match: '{coverage_clean}' matches '{county_format}'")
                        return True
                
                # Also try component matching for flexibility
                if ',' in coverage_area:
                    county_part, state_part = coverage_area.split(',', 1)
                    county_part_clean = county_part.strip().replace(' County', '').replace(' county', '')
                    state_part_clean = state_part.strip()
                    
                    # Check if county matches (with or without "County" suffix)
                    if target_county.lower() == county_part_clean.lower():
                        # Check state match (code or full name)
                        if (target_state == state_part_clean or
                            state_mapping.get(target_state) == state_part_clean or
                            target_state == state_mapping.get(state_part_clean)):
                            logger.debug(f"✅ Vendor {vendor_name} COUNTY component match: {target_county}, {target_state}")
                            return True
            
            logger.debug(f"❌ Vendor {vendor_name} COUNTY coverage: no match for {target_county}, {target_state} in {coverage_counties}")
            return False
        
        if coverage_type == 'zip':
            service_areas = vendor.get('service_areas', [])  # NOTE: This field doesn't exist in vendors table
            if not isinstance(service_areas, list):
                logger.warning(f"Vendor {vendor.get('name')} has malformed service_areas: {service_areas}")
                return False
            normalized_zip = self.location_service.normalize_zip_code(zip_code)
            normalized_service_areas = [
                self.location_service.normalize_zip_code(z) for z in service_areas
            ]
            return normalized_zip in normalized_service_areas
        
        return False
    
    def _get_coverage_match_reason(self, vendor: Dict[str, Any], zip_code: str,
                                 target_state: Optional[str], target_county: Optional[str]) -> str:
        """
        Get human-readable reason for why vendor matches the location
        FIXED: Uses actual database field name (coverage_type)
        """
        coverage_type = vendor.get('coverage_type', 'zip')  # FIXED: Use actual field name
        
        if coverage_type == 'global':
            return "Global coverage"
        elif coverage_type == 'national':
            return "National coverage"
        elif coverage_type == 'state':
            return f"State coverage: {target_state}"
        elif coverage_type == 'county':
            return f"County coverage: {target_county}, {target_state}"
        elif coverage_type == 'zip':
            return f"ZIP code coverage: {zip_code}"
        else:
            return f"Coverage type: {coverage_type}"
    
    def select_vendor_from_pool(self, eligible_vendors: List[Dict[str, Any]], 
                              account_id: str) -> Optional[Dict[str, Any]]:
        """
        Select a vendor from the eligible pool using the configured routing method
        
        Args:
            eligible_vendors: List of vendors that can serve the request
            account_id: Account ID for routing configuration
            
        Returns:
            Selected vendor or None if no vendors available
        """
        if not eligible_vendors:
            return None
        
        # Get routing configuration for this account
        routing_config = self._get_routing_configuration(account_id)
        performance_percentage = routing_config.get('performance_percentage', 0)
        
        # Decide which routing method to use based on percentage
        use_performance = random.randint(1, 100) <= performance_percentage
        
        if use_performance:
            logger.info(f"🎯 Using performance-based routing ({performance_percentage}% configured)")
            selected_vendor = self._select_by_performance(eligible_vendors)
        else:
            logger.info(f"🔄 Using round-robin routing ({100 - performance_percentage}% configured)")
            selected_vendor = self._select_by_round_robin(eligible_vendors)
        
        # Update vendor's last_lead_assigned timestamp
        if selected_vendor:
            self._update_vendor_last_assigned(selected_vendor['id'])
        
        return selected_vendor
    
    def _get_routing_configuration(self, account_id: str) -> Dict[str, Any]:
        """
        Get routing configuration for the account
        
        Args:
            account_id: Account ID
            
        Returns:
            Routing configuration dictionary
        """
        try:
            # Get performance percentage from account settings
            performance_percentage = simple_db_instance.get_account_setting(
                account_id, 'lead_routing_performance_percentage'
            )
            
            if performance_percentage is None:
                # Default to 0% performance-based (100% round-robin)
                performance_percentage = 0
                # Save default setting
                simple_db_instance.upsert_account_setting(
                    account_id, 'lead_routing_performance_percentage', 0
                )
            else:
                performance_percentage = int(performance_percentage)
            
            return {
                'performance_percentage': performance_percentage,
                'round_robin_percentage': 100 - performance_percentage
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting routing configuration for account {account_id}: {e}")
            return {'performance_percentage': 0, 'round_robin_percentage': 100}
    
    def _select_by_performance(self, vendors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select vendor with highest lead_close_percentage
        
        Args:
            vendors: List of eligible vendors
            
        Returns:
            Vendor with best performance
        """
        # Sort by close percentage (desc), then by last_lead_assigned (asc) for ties
        sorted_vendors = sorted(
            vendors,
            key=lambda v: (
                -v.get('lead_close_percentage', 0),  # Higher percentage first
                v.get('last_lead_assigned') or '1900-01-01'  # Older assignment first for ties
            )
        )
        
        selected = sorted_vendors[0]
        logger.info(f"🏆 Performance-based selection: {selected.get('name')} "
                   f"(close rate: {selected.get('lead_close_percentage', 0)}%)")
        return selected
    
    def _select_by_round_robin(self, vendors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select vendor with oldest last_lead_assigned date
        
        Args:
            vendors: List of eligible vendors
            
        Returns:
            Vendor with oldest assignment
        """
        # Sort by last_lead_assigned (asc) - oldest first
        sorted_vendors = sorted(
            vendors,
            key=lambda v: v.get('last_lead_assigned') or '1900-01-01'
        )
        
        selected = sorted_vendors[0]
        last_assigned = selected.get('last_lead_assigned', 'Never')
        logger.info(f"🔄 Round-robin selection: {selected.get('name')} "
                   f"(last assigned: {last_assigned})")
        return selected
    
    def _update_vendor_last_assigned(self, vendor_id: str) -> None:
        """
        Update vendor's last_lead_assigned timestamp
        
        Args:
            vendor_id: Vendor ID to update
        """
        try:
            conn = simple_db_instance._get_raw_conn()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE vendors 
                SET last_lead_assigned = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (vendor_id,))
            conn.commit()
            conn.close()
            logger.debug(f"✅ Updated last_lead_assigned for vendor {vendor_id}")
        except Exception as e:
            logger.error(f"❌ Error updating last_lead_assigned for vendor {vendor_id}: {e}")
    
    def update_routing_configuration(self, account_id: str, performance_percentage: int) -> bool:
        """
        Update the routing configuration for an account
        
        Args:
            account_id: Account ID
            performance_percentage: Percentage of leads to route by performance (0-100)
            
        Returns:
            True if update was successful
        """
        try:
            # Validate percentage
            if not 0 <= performance_percentage <= 100:
                raise ValueError("Performance percentage must be between 0 and 100")
            
            # Save to account settings
            simple_db_instance.upsert_account_setting(
                account_id, 'lead_routing_performance_percentage', performance_percentage
            )
            
            logger.info(f"✅ Updated routing configuration for account {account_id}: "
                       f"{performance_percentage}% performance, {100 - performance_percentage}% round-robin")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating routing configuration for account {account_id}: {e}")
            return False
    
    def get_routing_stats(self, account_id: str) -> Dict[str, Any]:
        """
        Get routing statistics for an account
        
        Args:
            account_id: Account ID
            
        Returns:
            Dictionary with routing statistics
        """
        try:
            config = self._get_routing_configuration(account_id)
            vendors = simple_db_instance.get_vendors(account_id=account_id)
            
            # Count vendors by coverage type
            coverage_stats = {}
            for vendor in vendors:
                coverage_type = vendor.get('coverage_type', 'zip')  # FIXED: Use actual field name
                coverage_stats[coverage_type] = coverage_stats.get(coverage_type, 0) + 1
            
            # Get recent lead assignments (would need to track this in activity log)
            # For now, return basic stats
            
            return {
                'routing_configuration': config,
                'total_vendors': len(vendors),
                'active_vendors': len([v for v in vendors if v.get('status') == 'active']),
                'vendors_taking_work': len([v for v in vendors if v.get('taking_new_work', False)]),
                'coverage_distribution': coverage_stats,
                'location_service_status': 'active' if self.location_service.geo_us else 'inactive'
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting routing stats for account {account_id}: {e}")
            return {}


# COMPREHENSIVE SERVICE LIST FOR VALIDATION
COMPLETE_SERVICES_LIST = [
    "Barnacle Cleaning", "Boat and Yacht Maintenance", "Boat and Yacht Parts", 
    "Boat Bilge Cleaning", "Boat Bottom Cleaning", "Boat Brokers", "Boat Builders", 
    "Boat Canvas and Upholstery", "Boat Charters and Rentals", "Boat Clubs", 
    "Boat Dealers", "Boat Decking and Yacht Flooring", "Boat Detailing", 
    "Boat Electrical Service", "Boat Financing", "Boat Hauling and Transport", 
    "Boat Insurance", "Boat Lift Installers", "Boat Lighting", "Boat Oil Change", 
    "Boat Salvage", "Boat Sound Systems", "Boat Surveyors", 
    "Boat Wrapping and Marine Protection Film", "Carpentry & Woodwork", 
    "Ceramic Coating", "Davit and Hydraulic Platform", "Diesel Engine Sales", 
    "Diesel Engine Service", "Dive Equipment and Services", 
    "Dock and Seawall Builders or Repair", "Dock and Slip Rental", 
    "eFoil, Kiteboarding & Wing Surfing", "Fiberglass Repair", "Fishing Charters", 
    "Floating Dock Sales", "Fuel Delivery", "Generator Sales", 
    "Generator Service and Repair", "Get Emergency Tow", "Get Towing Membership", 
    "Inboard Engine Sales", "Inboard Engine Service", "Jet Ski Maintenance", 
    "Jet Ski Repair", "Maritime Academy", "Maritime Certification", 
    "New Waterfront Developments", "Outboard Engine Sales", "Outboard Engine Service", 
    "Provisioning", "Rent My Dock", "Riggers & Masts", "Sailboat Charters", 
    "Sailing Schools", "Sell Your Waterfront Home", "Waterfront Homes For Sale", 
    "Welding & Metal Fabrication", "Wholesale or Dealer Product Pricing", 
    "Yacht AC Sales", "Yacht AC Service", "Yacht Account Management and Bookkeeping", 
    "Yacht and Catamaran Charters", "Yacht Armor", "Yacht Brokers", 
    "Yacht Builders", "Yacht Crew Placement", "Yacht Dealers", "Yacht Delivery", 
    "Yacht Fire Detection Systems", "Yacht Insurance", "Yacht Management", 
    "Yacht Photography", "Yacht Plumbing", "Yacht Refrigeration & Watermakers", 
    "Yacht Stabilizers & Seakeepers", "Yacht Training", "Yacht Videography", 
    "Yacht Wi-Fi"
]

def validate_service_name(service_name: str) -> bool:
    """
    Validate that a service name is in the approved comprehensive list
    
    Args:
        service_name: Service name to validate
        
    Returns:
        bool: True if service is in approved list, False otherwise
    """
    return service_name.strip() in COMPLETE_SERVICES_LIST


# Global instance for use throughout the application
lead_routing_service = LeadRoutingService()
