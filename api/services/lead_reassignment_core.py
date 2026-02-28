# api/services/lead_reassignment_core.py

"""
Core lead reassignment logic shared by both webhook and API endpoints.
Follows the corrected flow: ensure opportunity → ensure lead → reassign vendor
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from config import AppConfig
from database.simple_connection import db as simple_db_instance
from api.services.ghl_api_v2_optimized import OptimizedGoHighLevelAPI
from api.services.lead_routing_service import lead_routing_service
from api.services.location_service import location_service
from api.services.service_dictionary_mapper import ServiceDictionaryMapper

logger = logging.getLogger(__name__)

class LeadReassignmentCore:
    """
    Core service for lead reassignment that ensures proper flow:
    1. Opportunity exists or is created
    2. Lead exists with opportunity_id
    3. Vendor is reassigned
    4. GHL opportunity is updated
    """
    
    def __init__(self):
        self.ghl_api = OptimizedGoHighLevelAPI(
            private_token=AppConfig.GHL_PRIVATE_TOKEN,
            location_id=AppConfig.GHL_LOCATION_ID,
            agency_api_key=AppConfig.GHL_AGENCY_API_KEY
        )
        self.lead_routing = lead_routing_service
        self.location_service = location_service
        self.service_mapper = ServiceDictionaryMapper()
    
    async def reassign_lead(
        self,
        contact_id: str,
        opportunity_id: Optional[str] = None,
        exclude_previous: bool = True,
        reason: str = "reassignment",
        preserve_source: bool = True
    ) -> Dict[str, Any]:
        """
        Core reassignment logic following correct flow.
        
        Args:
            contact_id: GHL contact ID
            opportunity_id: Optional existing opportunity ID
            exclude_previous: Whether to exclude previously assigned vendor
            reason: Reason for reassignment
            preserve_source: Whether to preserve original source (IMPORTANT for bulk operations)
            
        Returns:
            Dict with reassignment results
        """
        logger.info(f"🔄 Starting core reassignment for contact {contact_id}")
        
        try:
            # Step 1: Get contact details from GHL
            contact_details = self.ghl_api.get_contact_by_id(contact_id)
            if not contact_details:
                return {
                    "success": False,
                    "error": "Contact not found in GHL",
                    "contact_id": contact_id
                }
            
            # Extract customer information
            customer_name = f"{contact_details.get('firstName', '')} {contact_details.get('lastName', '')}".strip()
            customer_email = contact_details.get('email', '')
            customer_phone = contact_details.get('phone', '')
            
            # FIRST: Try to get data from existing lead record (most reliable)
            existing_lead = simple_db_instance.get_lead_by_ghl_contact_id(contact_id)
            
            if existing_lead:
                # Use existing lead data - this is the most accurate
                logger.info(f"📋 Using existing lead data for reassignment")
                service_category = existing_lead.get('primary_service_category', '')
                specific_service = existing_lead.get('specific_service_requested', '')
                zip_code = existing_lead.get('service_zip_code', '') or existing_lead.get('customer_zip_code', '')
                service_county = existing_lead.get('service_county', '')
                service_state = existing_lead.get('service_state', '')
                
                # Use specific service if available, otherwise category
                if specific_service:
                    service_category = specific_service
                    logger.info(f"   Using specific service: {specific_service}")
                else:
                    logger.info(f"   Using service category: {service_category}")
            else:
                # FALLBACK: Try to extract from GHL contact custom fields
                logger.info(f"📋 No existing lead - attempting to extract from GHL contact")
                
                # Extract custom fields directly
                custom_fields_dict = {}
                for field in contact_details.get('customFields', []):
                    field_id = field.get('id')
                    field_value = field.get('value')
                    if field_id and field_value:
                        custom_fields_dict[field_id] = field_value
                
                # Use ServiceDictionaryMapper for mapping
                mapping_result = self.service_mapper.map_payload_to_service(contact_details)
                mapped_data = mapping_result.get('standardized_fields', {})
                
                # SIMPLIFIED: Direct extraction without hierarchy complexity
                # Priority 1: Get from known GHL field IDs
                LEAD_FIELD_IDS = {
                    'primary_service_category': 'HRqfv0HnUydNRLKWhk27',
                    'specific_service_needed': 'FT85QGi0tBq1AfVGNJ9v',
                    'zip_code_of_service': 'y3Xo7qsFEQumoFugTeCq'
                }
                
                # Get specific service directly - this is what matters for vendor matching
                specific_service = custom_fields_dict.get(LEAD_FIELD_IDS['specific_service_needed'], '') or \
                                  mapped_data.get('specific_service_needed', '')
                
                # Get primary category if available
                service_category = custom_fields_dict.get(LEAD_FIELD_IDS['primary_service_category'], '') or \
                                 mapped_data.get('primary_service_category', '')
                
                # If no category but have specific service, try to infer category
                if not service_category and specific_service:
                    from api.services.service_categories import SERVICE_CATEGORIES, LEVEL_3_SERVICES
                    for cat, services in SERVICE_CATEGORIES.items():
                        if specific_service in services:
                            service_category = cat
                            break
                    if not service_category:
                        for cat, subcats in LEVEL_3_SERVICES.items():
                            for subcat, l3_services in subcats.items():
                                if specific_service in l3_services:
                                    service_category = cat
                                    break
                            if service_category:
                                break
                
                # Try multiple sources for ZIP code
                zip_code = (
                    custom_fields_dict.get(LEAD_FIELD_IDS.get('zip_code_of_service', ''), '') or
                    mapped_data.get('zip_code_of_service', '') or 
                    mapped_data.get('customer_zip_code', '') or
                    custom_fields_dict.get('zip_code_of_service', '') or
                    custom_fields_dict.get('customer_zip_code', '') or
                    contact_details.get('postalCode', '') or
                    contact_details.get('address1', '')[-5:] if contact_details.get('address1') and len(contact_details.get('address1', '')) >= 5 else ''
                )
                
                # Clean up zip code - ensure it's 5 digits
                if zip_code:
                    zip_code = str(zip_code).strip()
                    # Extract 5-digit ZIP from longer strings
                    import re
                    zip_match = re.search(r'\b(\d{5})\b', zip_code)
                    if zip_match:
                        zip_code = zip_match.group(1)
                    
                service_county = ""
                service_state = ""
            
            if not service_category and not specific_service:
                return {
                    "success": False,
                    "error": f"Cannot determine service (no service data in lead or GHL contact)",
                    "contact_id": contact_id
                }
            
            if not zip_code or len(zip_code) != 5:
                return {
                    "success": False,
                    "error": "Cannot determine service location",
                    "contact_id": contact_id
                }
            
            # Convert ZIP to county only if we don't already have it from the lead
            if not service_county and not service_state:
                location_data = self.location_service.zip_to_location(zip_code)
                if not location_data.get('error'):
                    county = location_data.get('county', '')
                    state = location_data.get('state', '')
                    if county and state:
                        service_county = f"{county}, {state}"
                        service_state = state
            
            logger.info(f"📍 Reassignment for: {service_category} in {service_county or zip_code}")
            
            # Step 2: Ensure opportunity exists
            if not opportunity_id:
                logger.info(f"📈 No opportunity provided - checking for existing or creating new")
                
                # Check if contact has existing opportunities
                opportunities = self.ghl_api.get_opportunities_by_contact(contact_id)
                if opportunities and len(opportunities) > 0:
                    # Use most recent open opportunity
                    for opp in opportunities:
                        if opp.get('status') == 'open':
                            opportunity_id = opp.get('id')
                            logger.info(f"📋 Found existing open opportunity: {opportunity_id}")
                            break
                    
                    if not opportunity_id:
                        # No open opportunities, use most recent
                        opportunity_id = opportunities[0].get('id')
                        logger.info(f"📋 Using most recent opportunity: {opportunity_id}")
                
                # Create opportunity if none exists
                if not opportunity_id:
                    logger.info(f"➕ Creating new opportunity for reassignment")
                    
                    opportunity_data = {
                        'contactId': contact_id,
                        'pipelineId': AppConfig.PIPELINE_ID,
                        'pipelineStageId': AppConfig.NEW_LEAD_STAGE_ID,
                        'name': f"{customer_name} - {service_category} (Reassignment)",
                        'monetaryValue': 0,
                        'status': 'open',
                        'source': f"reassignment_{reason}",
                        'locationId': AppConfig.GHL_LOCATION_ID,
                    }
                    
                    opportunity_response = self.ghl_api.create_opportunity(opportunity_data)
                    
                    # Handle both v1 and v2 API response formats
                    if opportunity_response:
                        if opportunity_response.get('opportunity', {}).get('id'):
                            # v2 API format - opportunity is nested
                            opportunity_id = opportunity_response['opportunity']['id']
                            logger.info(f"✅ Created opportunity (v2 format): {opportunity_id}")
                        elif opportunity_response.get('id'):
                            # v1 API format - id at root level
                            opportunity_id = opportunity_response['id']
                            logger.info(f"✅ Created opportunity (v1 format): {opportunity_id}")
                        else:
                            logger.error(f"❌ Unexpected opportunity response format: {opportunity_response}")
                            return {
                                "success": False,
                                "error": f"Unexpected opportunity response format: {opportunity_response}",
                                "contact_id": contact_id
                            }
                    else:
                        return {
                            "success": False,
                            "error": "Failed to create opportunity - no response",
                            "contact_id": contact_id
                        }
            
            # Step 3: Get account information
            account = simple_db_instance.get_account_by_ghl_location_id(AppConfig.GHL_LOCATION_ID)
            if not account:
                # Create default account
                account_id = simple_db_instance.create_account(
                    company_name="Default Account",
                    industry="marine",
                    ghl_location_id=AppConfig.GHL_LOCATION_ID,
                    ghl_private_token=AppConfig.GHL_PRIVATE_TOKEN
                )
            else:
                account_id = account["id"]
            
            # Step 4: Ensure lead exists with opportunity_id
            # Note: We're re-fetching since we already got it earlier for service data
            existing_lead = simple_db_instance.get_lead_by_ghl_contact_id(contact_id)
            previous_vendor_id = None
            original_source = None
            
            if existing_lead:
                lead_id = existing_lead['id']
                previous_vendor_id = existing_lead.get('vendor_id')
                original_source = existing_lead.get('source')  # Preserve original source
                
                logger.info(f"📋 Found existing lead: {lead_id}")
                
                # Update lead with opportunity_id if missing or different
                if not existing_lead.get('ghl_opportunity_id') or existing_lead.get('ghl_opportunity_id') != opportunity_id:
                    simple_db_instance.update_lead_opportunity_id(lead_id, opportunity_id)
                    logger.info(f"✅ Updated lead with opportunity_id: {opportunity_id}")
                
                # Clear current vendor assignment for reassignment
                if previous_vendor_id:
                    logger.info(f"🔄 Clearing previous vendor assignment: {previous_vendor_id}")
                    simple_db_instance.unassign_lead_from_vendor(lead_id)
            else:
                # Create new lead WITH opportunity_id
                lead_id = str(uuid.uuid4())
                logger.info(f"➕ Creating new lead with opportunity_id")
                
                conn = simple_db_instance._get_raw_conn()
                cursor = conn.cursor()
                
                try:
                    cursor.execute('''
                        INSERT INTO leads (
                            id, account_id, ghl_contact_id, ghl_opportunity_id, customer_name,
                            customer_email, customer_phone, primary_service_category, specific_service_requested,
                            customer_zip_code, service_county, service_state, vendor_id, 
                            assigned_at, status, priority, source, service_details, 
                            created_at, updated_at, service_zip_code, service_city,
                            service_complexity, estimated_duration, requires_emergency_response,
                            classification_confidence, classification_reasoning
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        lead_id, account_id, contact_id, opportunity_id, customer_name,
                        customer_email, customer_phone, service_category, specific_service,
                        zip_code, service_county, service_state, None, None,
                        "pending_reassignment", "high", f"reassignment_{reason}",
                        json.dumps({"reassignment_reason": reason}),
                        zip_code, "", "simple", "medium", False, 1.0,
                        f"Lead created for reassignment: {reason}"
                    ))
                    conn.commit()
                    logger.info(f"✅ Created lead: {lead_id}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to create lead: {e}")
                    conn.rollback()
                    return {
                        "success": False,
                        "error": f"Database error: {str(e)}",
                        "contact_id": contact_id
                    }
                finally:
                    conn.close()
            
            # Step 5: Find matching vendors (exclude previous + vendors who rejected this lead)
            # Use specific service for matching if available, otherwise use category
            service_to_match = specific_service if specific_service else service_category
            logger.info(f"🔍 Searching for vendors matching: '{service_to_match}' in ZIP {zip_code}")
            
            rejected_ghl_user_ids = simple_db_instance.get_rejected_ghl_user_ids_for_contact(contact_id) if contact_id else set()
            if rejected_ghl_user_ids:
                logger.info(f"   Excluding {len(rejected_ghl_user_ids)} vendor(s) who previously rejected this lead")
            
            available_vendors = self.lead_routing.find_matching_vendors(
                account_id=account_id,
                service_category=service_to_match.split(" - ")[0] if " - " in service_to_match else service_to_match,
                zip_code=zip_code,
                priority='high',
                specific_service=service_to_match,
                exclude_ghl_user_ids=rejected_ghl_user_ids
            )
            
            if not available_vendors:
                logger.warning(f"⚠️ No matching vendors found")
                return {
                    "success": False,
                    "error": "No matching vendors found",
                    "contact_id": contact_id,
                    "lead_id": lead_id,
                    "previous_vendor_id": previous_vendor_id
                }
            
            # Exclude previous vendor if requested
            if exclude_previous and previous_vendor_id:
                available_vendors = [v for v in available_vendors if v['id'] != previous_vendor_id]
                logger.info(f"🚫 Excluded previous vendor {previous_vendor_id}")
                
                if not available_vendors:
                    return {
                        "success": False,
                        "error": "No alternative vendors available",
                        "contact_id": contact_id,
                        "lead_id": lead_id,
                        "previous_vendor_id": previous_vendor_id
                    }
            
            # Step 6: Select new vendor
            selected_vendor = self.lead_routing.select_vendor_from_pool(available_vendors, account_id)
            
            if not selected_vendor:
                return {
                    "success": False,
                    "error": "Vendor selection failed",
                    "contact_id": contact_id,
                    "lead_id": lead_id
                }
            
            vendor_id = selected_vendor['id']
            vendor_name = selected_vendor.get('company_name', selected_vendor.get('name', 'Unknown'))
            vendor_ghl_user = selected_vendor.get('ghl_user_id')
            
            logger.info(f"🎯 Selected vendor: {vendor_name} (ID: {vendor_id})")
            
            # Step 7: Update lead with new vendor (preserve original source)
            db_update = simple_db_instance.assign_lead_to_vendor(lead_id, vendor_id)
            
            if not db_update:
                return {
                    "success": False,
                    "error": "Failed to update lead in database",
                    "contact_id": contact_id,
                    "lead_id": lead_id
                }
            
            # IMPORTANT: If we need to preserve source, update it back
            if preserve_source and original_source:
                conn = simple_db_instance._get_raw_conn()
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "UPDATE leads SET source = ? WHERE id = ?",
                        (original_source, lead_id)
                    )
                    conn.commit()
                    logger.info(f"✅ Preserved original source: {original_source}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not preserve source: {e}")
                finally:
                    conn.close()
            
            # Step 8: Update GHL opportunity with vendor assignment
            if vendor_ghl_user and opportunity_id:
                try:
                    update_data = {
                        'assignedTo': vendor_ghl_user,
                        'pipelineId': AppConfig.PIPELINE_ID,
                        'pipelineStageId': AppConfig.NEW_LEAD_STAGE_ID
                    }
                    
                    ghl_success = self.ghl_api.update_opportunity(opportunity_id, update_data)
                    
                    if ghl_success:
                        logger.info(f"✅ Updated GHL opportunity with vendor assignment")
                    else:
                        logger.warning(f"⚠️ Failed to update GHL opportunity")
                        
                except Exception as e:
                    logger.error(f"❌ Error updating GHL opportunity: {e}")
            
            # Step 9: Log reassignment event
            simple_db_instance.log_activity(
                event_type="lead_reassigned_success",
                event_data={
                    "lead_id": lead_id,
                    "contact_id": contact_id,
                    "opportunity_id": opportunity_id,
                    "previous_vendor_id": previous_vendor_id,
                    "new_vendor_id": vendor_id,
                    "vendor_name": vendor_name,
                    "reason": reason,
                    "service": f"{specific_service or service_category}",
                    "location": f"{service_county or zip_code}"
                },
                lead_id=lead_id,
                success=True
            )
            
            return {
                "success": True,
                "contact_id": contact_id,
                "lead_id": lead_id,
                "opportunity_id": opportunity_id,
                "previous_vendor_id": previous_vendor_id,
                "new_vendor_id": vendor_id,
                "vendor_name": vendor_name,
                "vendor_ghl_user": vendor_ghl_user,
                "message": f"Successfully reassigned to {vendor_name}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error in core reassignment: {e}")
            return {
                "success": False,
                "error": str(e),
                "contact_id": contact_id
            }

# Singleton instance
lead_reassignment_core = LeadReassignmentCore()