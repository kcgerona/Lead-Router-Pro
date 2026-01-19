# api/routes/webhook_routes.py

import logging
import json
from typing import Dict, List, Any, Optional
import time
import uuid
import re
import asyncio
import threading
from urllib.parse import parse_qs

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

# --- Core Service Imports - Direct Processing Only ---
from config import AppConfig
from database.simple_connection import db as simple_db_instance
from api.services.ghl_api import GoHighLevelAPI
from api.services.ghl_api_v2_optimized import OptimizedGoHighLevelAPI
# REMOVED: from api.services.field_mapper import field_mapper  # OLD - can't handle GHL nested customFields
from api.services.ghl_field_mapper import field_mapper  # NEW: Replacement with proper GHL support
from api.services.lead_routing_service import lead_routing_service
from api.services.location_service import location_service
from api.services.service_mapper import (
    get_service_category as get_direct_service_category,
    get_specific_service as get_specific_service_from_form,
    find_matching_service,
    DOCKSIDE_PROS_CATEGORIES,
    DOCKSIDE_PROS_SERVICES,
    FORM_TO_SPECIFIC_SERVICE
)
# NEW: Proper mappers for GHL custom fields and service hierarchy
from api.services.service_dictionary_mapper import ServiceDictionaryMapper
from api.services.service_categories import (
    SERVICE_CATEGORIES, 
    LEVEL_3_SERVICES,
    service_manager
)

# Import the new service dictionary mapper for intelligent field consolidation
from api.services.webhook_integration_patch import process_webhook_with_service_mapping


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/webhooks", tags=["Clean Elementor Webhooks - Direct Processing"])

# Location services router for widget integration
location_router = APIRouter(prefix="/api/v1/locations", tags=["Location Services"])

@location_router.get("/states/{state_code}/counties")
async def get_counties_by_state(state_code: str):
    """Return all counties for a given state"""
    try:
        counties = location_service.get_state_counties(state_code.upper())
        return {
            "status": "success",
            "state": state_code.upper(),
            "counties": counties,
            "count": len(counties)
        }
    except Exception as e:
        logger.error(f"Error getting counties for state {state_code}: {e}")
        return {
            "status": "error",
            "message": "Failed to retrieve counties",
            "state": state_code.upper(),
            "counties": []
        }

# ============================================================================
# NEW EXTRACTION FUNCTIONS FOR PROPER GHL CUSTOM FIELDS HANDLING
# ============================================================================

def extract_ghl_custom_fields(contact_details: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract GHL custom fields from nested array structure to flat dictionary.
    
    Args:
        contact_details: GHL contact data with customFields array
        
    Returns:
        Flat dictionary with field_id -> value mappings
    """
    custom_fields_dict = {}
    custom_fields = contact_details.get('customFields', [])
    
    for field in custom_fields:
        field_id = field.get('id')
        field_value = field.get('value')
        if field_id and field_value:  # Only include non-empty values
            custom_fields_dict[field_id] = field_value
            
    logger.info(f"📋 Extracted {len(custom_fields_dict)} custom fields from GHL contact")
    return custom_fields_dict

def map_ghl_contact_to_lead(contact_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map GHL contact data to standardized lead format using ServiceDictionaryMapper.
    
    Args:
        contact_details: GHL contact data
        
    Returns:
        Mapped payload with standardized service information
    """
    from api.services.service_dictionary_mapper import ServiceDictionaryMapper
    
    # Extract custom fields into flat dictionary
    custom_fields_dict = extract_ghl_custom_fields(contact_details)
    
    # Combine standard fields with custom fields for mapping
    combined_payload = {
        **contact_details,  # Standard fields like firstName, lastName, email
        **custom_fields_dict  # Flattened custom fields with field IDs as keys
    }
    
    # Use ServiceDictionaryMapper to map the fields properly
    mapper = ServiceDictionaryMapper()
    mapping_result = mapper.map_payload_to_service(combined_payload)
    
    logger.info(f"🔄 ServiceDictionaryMapper result: {mapping_result.get('service_classification', {})}")
    
    return mapping_result

def determine_service_hierarchy(primary_category: str, specific_service: str) -> Dict[str, str]:
    """
    Determine the correct service hierarchy based on Level 1 category and specific service.
    For categories WITHOUT Level 3 services, the Level 2 service IS the specific_service_requested.
    
    Args:
        primary_category: Level 1 category (e.g., "Boat Maintenance")
        specific_service: Level 2 or 3 service (e.g., "Boat Oil Change")
        
    Returns:
        Dictionary with properly classified service levels
    """
    from api.services.service_categories import SERVICE_CATEGORIES, LEVEL_3_SERVICES
    
    result = {
        'primary_service_category': primary_category or '',
        'specific_service_requested': '',
        'service_level': 'unknown'
    }
    
    if not primary_category:
        logger.warning("⚠️ No primary category provided for service hierarchy determination")
        return result
        
    # Check if this category has Level 3 services
    if primary_category in LEVEL_3_SERVICES:
        # This category has Level 3, need to check if specific_service is Level 2 or 3
        level3_map = LEVEL_3_SERVICES.get(primary_category, {})
        
        # Check if it's a Level 3 service
        for level2_service, level3_list in level3_map.items():
            if specific_service in level3_list:
                result['specific_service_requested'] = specific_service
                result['service_level'] = 'level3'
                logger.info(f"✅ Identified Level 3 service: {specific_service} under {level2_service}")
                return result
                
        # Not Level 3, might be Level 2 subcategory
        if specific_service in level3_map:
            # It's a Level 2 subcategory, not specific enough
            result['service_level'] = 'level2_subcategory'
            logger.warning(f"⚠️ {specific_service} is a Level 2 subcategory, need Level 3 for specific service")
        else:
            logger.warning(f"⚠️ {specific_service} not found in Level 3 services for {primary_category}")
            
    else:
        # No Level 3 for this category, so Level 2 IS the specific service
        if specific_service in SERVICE_CATEGORIES.get(primary_category, []):
            result['specific_service_requested'] = specific_service
            result['service_level'] = 'level2'
            logger.info(f"✅ Category {primary_category} has no Level 3 - using Level 2 service: {specific_service}")
        else:
            logger.warning(f"⚠️ {specific_service} not found in Level 2 services for {primary_category}")
            
    return result

# Known GHL field IDs for lead routing (from field_reference.json)
LEAD_ROUTING_FIELD_IDS = {
    'primary_service_category': 'HRqfv0HnUydNRLKWhk27',  # Level 1 category for routing
    'specific_service_needed': 'FT85QGi0tBq1AfVGNJ9v',    # Level 2/3 specific service
    # DO NOT USE 'O84LyhN1QjZ8Zz5mteCM' - that's for vendor service capabilities!
}

async def create_lead_from_ghl_contact(
    ghl_contact_data: Dict[str, Any],
    account_id: str,
    form_identifier: str = "bulk_assignment"
) -> tuple[str, Optional[str]]:
    """
    SHARED PIPELINE: Convert GHL contact to database lead + opportunity
    Used by both webhook and bulk assignment workflows for consistency
    
    Returns: (lead_id, opportunity_id)
    """
    try:
        # Step 1: Extract customer data (reuse webhook logic)
        customer_data = {
            "name": f"{ghl_contact_data.get('firstName', '')} {ghl_contact_data.get('lastName', '')}".strip(),
            "email": ghl_contact_data.get("email", ""),
            "phone": ghl_contact_data.get("phone", "")
        }
        
        # Step 2: Apply field mapping using new ServiceDictionaryMapper
        mapping_result = map_ghl_contact_to_lead(ghl_contact_data)
        mapped_payload = mapping_result.get('standardized_fields', {})
        service_classification = mapping_result.get('service_classification', {})
        logger.info(f"🔄 ServiceDictionaryMapper field mapping. Original keys: {list(ghl_contact_data.keys())}, Mapped keys: {list(mapped_payload.keys())}")
        
        # Step 3: Service classification from mapping result
        service_category = service_classification.get('level1_category') or get_direct_service_category(form_identifier)
        
        # Step 4: ZIP → County conversion (critical for routing)
        zip_code = mapped_payload.get("zip_code_of_service", "")
        service_county = ""
        service_state = ""
        
        if zip_code and len(zip_code) == 5 and zip_code.isdigit():
            logger.info(f"🗺️ Converting ZIP {zip_code} to county using shared pipeline")
            location_data = location_service.zip_to_location(zip_code)
            
            if not location_data.get('error'):
                county = location_data.get('county', '')
                state = location_data.get('state', '')
                if county and state:
                    service_county = f"{county}, {state}"
                    service_state = state
                    logger.info(f"✅ Shared pipeline ZIP {zip_code} → {service_county}")
                else:
                    logger.warning(f"⚠️ Shared pipeline ZIP {zip_code} conversion incomplete: county={county}, state={state}")
            else:
                logger.warning(f"⚠️ Shared pipeline could not convert ZIP {zip_code}: {location_data['error']}")
        else:
            logger.warning(f"⚠️ Shared pipeline invalid ZIP code format: '{zip_code}'")

        # Step 5: Create database lead using correct schema
        lead_id_str = str(uuid.uuid4())
        
        # Build service_details from all mapped fields
        service_details = {}
        standard_lead_fields = {
            "firstName", "lastName", "email", "phone", "primary_service_category",
            "customer_zip_code", "specific_service_requested"
        }
        
        for field_key, field_value in mapped_payload.items():
            if field_value and field_value != "" and field_key not in standard_lead_fields:
                service_details[field_key] = field_value
                
        service_details.update({
            "form_source": form_identifier,
            "processing_method": "shared_pipeline",
            "created_via": "create_lead_from_ghl_contact"
        })
        
        # Database INSERT using correct schema
        conn = None
        try:
            conn = simple_db_instance._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO leads (
                    id, account_id, ghl_contact_id, ghl_opportunity_id, customer_name,
                    customer_email, customer_phone, primary_service_category, specific_service_requested,
                    service_zip_code, service_county, service_state, vendor_id, 
                    status, priority, source, service_details, 
                    created_at, updated_at, service_city, 
                    service_complexity, estimated_duration, requires_emergency_response, 
                    classification_confidence, classification_reasoning
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?)
            ''', (
                lead_id_str,                                                # id
                account_id,                                                 # account_id
                ghl_contact_data.get('id'),                                 # ghl_contact_id
                None,                                                       # ghl_opportunity_id (will be updated)
                customer_data.get("name", ""),                              # customer_name
                customer_data.get("email", "").lower().strip() if customer_data.get("email") else None,  # customer_email
                customer_data.get("phone", ""),                             # customer_phone
                service_category,                                           # primary_service_category (FIXED)
                mapped_payload.get("specific_service_requested", ""),                # specific_service_requested (FIXED)
                zip_code,                                                   # service_zip_code (FIXED)
                service_county,                                             # service_county
                service_state,                                              # service_state
                None,                                                       # vendor_id (unassigned)
                "unassigned",                                               # status
                "normal",                                                   # priority
                form_identifier,                                            # source
                json.dumps(service_details),                                # service_details
                "",                                                         # service_city
                "simple",                                                   # service_complexity
                "medium",                                                   # estimated_duration
                False,                                                      # requires_emergency_response
                1.0,                                                        # classification_confidence
                f"Created via shared pipeline from {form_identifier}"       # classification_reasoning
            ))
            
            conn.commit()
            logger.info(f"✅ Shared pipeline created lead: {lead_id_str}")
            
        except Exception as e:
            logger.error(f"❌ Shared pipeline lead creation error: {e}")
            raise
        finally:
            if conn:
                conn.close()
        
        # Step 6: Create opportunity if needed (check for existing first)
        opportunity_id = None
        if AppConfig.PIPELINE_ID and AppConfig.NEW_LEAD_STAGE_ID:
            # Use optimized v2 API for better performance
            ghl_api_client = OptimizedGoHighLevelAPI(
                private_token=AppConfig.GHL_PRIVATE_TOKEN,
                location_id=AppConfig.GHL_LOCATION_ID,
                agency_api_key=AppConfig.GHL_AGENCY_API_KEY
            )
            
            # First check if an opportunity already exists for this contact
            existing_opportunities = ghl_api_client.get_opportunities_by_contact(ghl_contact_data.get('id'))
            
            if existing_opportunities and len(existing_opportunities) > 0:
                # Use existing opportunity
                opportunity_id = existing_opportunities[0].get('id')
                logger.info(f"📋 Shared pipeline using existing opportunity: {opportunity_id}")
            else:
                # Create new opportunity
                logger.info(f"📈 Shared pipeline creating opportunity for {service_category} lead")
                
                customer_name = customer_data["name"]
                
                opportunity_data = {
                    'contactId': ghl_contact_data.get('id'),
                    'pipelineId': AppConfig.PIPELINE_ID,
                    'pipelineStageId': AppConfig.NEW_LEAD_STAGE_ID,
                    'name': f"{customer_name} - {service_category}",
                    'monetaryValue': 0,
                    'status': 'open',
                    'source': f"{form_identifier} (DSP Shared Pipeline)",
                    'locationId': AppConfig.GHL_LOCATION_ID,
                }
                
                opportunity_response = ghl_api_client.create_opportunity(opportunity_data)
                
                # Handle both v1 and v2 API response formats
                if opportunity_response:
                    if opportunity_response.get('opportunity', {}).get('id'):
                        # v2 API format - opportunity is nested
                        opportunity_id = opportunity_response['opportunity']['id']
                        logger.info(f"✅ Shared pipeline created opportunity (v2 format): {opportunity_id}")
                    elif opportunity_response.get('id'):
                        # v1 API format - id at root level
                        opportunity_id = opportunity_response['id']
                        logger.info(f"✅ Shared pipeline created opportunity (v1 format): {opportunity_id}")
                    else:
                        logger.error(f"❌ Shared pipeline unexpected opportunity response format: {opportunity_response}")
                else:
                    logger.error(f"❌ Shared pipeline failed to create opportunity: No response received")
            
            # Update lead with opportunity ID if we have one
            if opportunity_id:
                try:
                    simple_db_instance.update_lead_opportunity_id(lead_id_str, opportunity_id)
                    logger.info(f"✅ Shared pipeline linked opportunity {opportunity_id} to lead {lead_id_str}")
                except Exception as e:
                    logger.warning(f"⚠️ Shared pipeline could not link opportunity ID: {e}")
        else:
            logger.warning("⚠️ Shared pipeline: Pipeline not configured - skipping opportunity creation")
        
        return lead_id_str, opportunity_id
        
    except Exception as e:
        logger.error(f"❌ Shared pipeline error for contact {ghl_contact_data.get('id', 'unknown')}: {e}")
        raise


# Service mappings have been moved to api.services.service_mapper
# Duplicate definitions removed for better modularity

async def parse_webhook_payload(request: Request) -> Dict[str, Any]:
    """
    Robust payload parser that handles both JSON and form-encoded data
    Provides fallback support for WordPress/Elementor webhooks that may send either format
    """
    content_type = request.headers.get("content-type", "").lower()
    
    logger.info(f"🔍 PAYLOAD PARSER: Content-Type='{content_type}'")
    
    # Method 1: Try JSON parsing first (preferred format)
    if "application/json" in content_type:
        try:
            payload = await request.json()
            logger.info(f"✅ Successfully parsed JSON payload with {len(payload)} fields")
            return normalize_field_names(payload)
        except Exception as json_error:
            logger.warning(f"⚠️ JSON parsing failed despite JSON content-type: {json_error}")
            # Fall through to form parsing
    
    # Method 2: Try form-encoded parsing
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        try:
            form_data = await request.form()
            payload = dict(form_data)
            logger.info(f"✅ Successfully parsed form-encoded payload with {len(payload)} fields")
            
            # Log the conversion for debugging
            logger.info(f"🔄 Form-encoded fields: {list(payload.keys())}")
            
            return normalize_field_names(payload)
        except Exception as form_error:
            logger.warning(f"⚠️ Form parsing failed: {form_error}")
    
    # Method 3: Auto-detect fallback - try both methods
    logger.info("🔄 Auto-detecting payload format...")
    
    # Get raw body for inspection
    try:
        body = await request.body()
        body_str = body.decode('utf-8')
        logger.info(f"📄 Raw body preview (first 200 chars): {body_str[:200]}")
        
        # Try to detect format from content
        if body_str.strip().startswith('{') and body_str.strip().endswith('}'):
            # Looks like JSON
            try:
                payload = json.loads(body_str)
                logger.info(f"✅ Auto-detected and parsed JSON payload with {len(payload)} fields")
                return normalize_field_names(payload)
            except Exception as e:
                logger.warning(f"⚠️ Auto-detect JSON parsing failed: {e}")
        
        # Try form-encoded parsing
        if '=' in body_str and ('&' in body_str or len(body_str.split('=')) == 2):
            # Looks like form data
            try:
                # Parse URL-encoded data manually
                parsed_data = parse_qs(body_str, keep_blank_values=True)
                # Convert lists to single values (form data typically has single values)
                payload = {key: (values[0] if values else '') for key, values in parsed_data.items()}
                logger.info(f"✅ Auto-detected and parsed form-encoded payload with {len(payload)} fields")
                return normalize_field_names(payload)
            except Exception as e:
                logger.warning(f"⚠️ Auto-detect form parsing failed: {e}")
        
    except Exception as e:
        logger.error(f"❌ Failed to read request body for auto-detection: {e}")
    
    # Method 4: Last resort - return empty dict with error logging
    logger.error("❌ All payload parsing methods failed - returning empty payload")
    logger.error(f"❌ Content-Type: {content_type}")
    logger.error(f"❌ Headers: {dict(request.headers)}")
    
    # Return empty payload but don't raise exception - let validation handle it
    return {}

def normalize_field_names(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize WordPress/Elementor field names to expected format
    Handles BOTH flat and nested field formats automatically
    Maps common WordPress field variations to standard field names
    """
    
    # First, check if we have nested Elementor format and extract if needed
    if any(key.startswith('fields[') for key in payload.keys()):
        logger.info("📦 Detected nested Elementor format (fields[name][value]) - extracting...")
        extracted_payload = {}
        meta_fields = {}
        form_info = {}
        
        for key, value in payload.items():
            # Handle fields[field_name][property] format
            if key.startswith('fields[') and '][' in key:
                parts = key.replace('fields[', '').replace(']', '').split('[')
                if len(parts) >= 2:
                    field_name = parts[0]
                    property_name = parts[1] if len(parts) > 1 else 'value'
                    
                    if field_name not in extracted_payload:
                        extracted_payload[field_name] = {}
                    
                    if isinstance(extracted_payload[field_name], dict):
                        extracted_payload[field_name][property_name] = value
            
            # Handle meta fields
            elif key.startswith('meta['):
                parts = key.replace('meta[', '').replace(']', '').split('[')
                if len(parts) >= 2 and parts[1] == 'value':
                    meta_fields[f"meta_{parts[0]}"] = value
            
            # Handle form fields
            elif key.startswith('form['):
                parts = key.replace('form[', '').replace(']', '')
                form_info[f"form_{parts}"] = value
            
            # Keep flat fields as-is
            else:
                extracted_payload[key] = value
        
        # Flatten the extracted fields - get 'value' property for each field
        flattened_payload = {}
        for field_name, field_data in extracted_payload.items():
            if isinstance(field_data, dict):
                if 'value' in field_data:
                    flattened_payload[field_name] = field_data['value']
                elif 'raw_value' in field_data:
                    flattened_payload[field_name] = field_data['raw_value']
            else:
                flattened_payload[field_name] = field_data
        
        # Add meta and form fields
        flattened_payload.update(meta_fields)
        flattened_payload.update(form_info)
        
        logger.info(f"✅ Extracted {len(flattened_payload)} fields from nested format")
        payload = flattened_payload
    
    # Now proceed with field name mapping for WordPress/Elementor forms
    field_mappings = {
        # Name fields
        "First Name": "firstName",
        "first_name": "firstName", 
        "fname": "firstName",
        "Last Name": "lastName",
        "last_name": "lastName",
        "lname": "lastName",
        
        # Email fields
        "Your Contact Email?": "email",
        "Email": "email",
        "email_address": "email",
        "contact_email": "email",
        "Email Address": "email",
        
        # Phone fields
        "Your Contact Phone #?": "phone",
        "Phone": "phone",
        "phone_number": "phone",
        "contact_phone": "phone",
        "Phone Number": "phone",
        
        # Service-specific fields
        "What Zip Code Are You Requesting Service In?": "zip_code_of_service",
        "What Zip Code Are You Requesting a Charter In?": "zip_code_of_service",
        "What Zip Code Are You Requesting a Fishing Charter In?": "zip_code_of_service",
        "What Zip Code Are You Requesting a Generator Service In?": "zip_code_of_service",
        "What Zip Code Are You Requesting Service In?": "zip_code_of_service",
        "What Zip Code Are You Requesting a Charter In?": "zip_code_of_service",
        "What Zip Code Are You Requesting a Fishing Charter In?": "zip_code_of_service",
        "What Zip Code Are You Requesting a Generator Service In?": "zip_code_of_service",
        "What Zip code are you looking for management services In?": "zip_code_of_service",
        "What Zip code are you looking to buy or sell a property In?": "zip_code_of_service",
        "What Zip code are you looking to buy or sell In?": "zip_code_of_service",
        "What Zip code are you looking to rent a dock or slip In?": "zip_code_of_service",
        "What Zip code are you looking to rent your dock or slip In?": "zip_code_of_service",
        "What Zip code are you requesting a boat club In?": "zip_code_of_service",
        "What Zip code are you requesting a charter or rental In?": "zip_code_of_service",
        "What Zip code are you requesting a lesson or equipment In?": "zip_code_of_service",
        "What Zip code are you requesting a party boat charter In?": "zip_code_of_service",
        "What Zip code are you requesting a pontoon rental or charter In?": "zip_code_of_service",
        "What Zip code are you requesting a private yacht charter In?": "zip_code_of_service",
        "What Zip code are you requesting dive services or equipment In?": "zip_code_of_service",
        "What Zip code are you requesting education or training In?": "zip_code_of_service",
        "What Zip code are you requesting financing In?": "zip_code_of_service",
        "What Zip code are you requesting insurance In?": "zip_code_of_service",
        "What Zip code are you requesting jet ski rental or tours In?": "zip_code_of_service",
        "What Zip code are you requesting kayak rental or tours In?": "zip_code_of_service",
        "What Zip code are you requesting paddleboard rental or tours In?": "zip_code_of_service",
        "What Zip code are you requesting parts In?": "zip_code_of_service",
        "What Zip code are you requesting products In?": "zip_code_of_service",
        "What Zip code are you requesting surveying In?": "zip_code_of_service",
        "Zip Code": "zip_code_of_service",
        "Service Zip Code": "zip_code_of_service",
        "Location": "zip_code_of_service",
        
        # Service needed variations - comprehensive list
        "What Specific Service(s) Do You Request?": "specific_service_needed",
        "What Specific Service(s) Do You Request? ": "specific_service_needed",  # With trailing space
        "What Specific Service Do You Request?": "specific_service_needed",  # Without (s)
        "What Specific Service Do You Request": "specific_service_needed",  # Without ?
        "What Specific Services Do You Request?": "specific_service_needed",  # Services plural
        "What Specific Charter Do You Request?": "specific_service_needed",
        "What Specific service do you request?": "specific_service_needed",
        "What Service Do You Need?": "specific_service_needed",
        "Service Needed": "specific_service_needed",
        "Service Request": "specific_service_needed",
        "Services": "specific_service_needed",
        "Specific Service": "specific_service_needed",
        "Service Type": "specific_service_needed",
        
        "Your Vessel Manufacturer? ": "vessel_make",
        "Vessel Make": "vessel_make",
        "Boat Make": "vessel_make",
        "Manufacturer": "vessel_make",
        
        "Your Vessel Model": "vessel_model",
        "Vessel Model": "vessel_model",
        "Your Vessel Model or Length of Vessel in Feet?": "vessel_model",  # CRITICAL FIX
        "Your Vessel Length": "vessel_length_ft",
        "Vessel Length (ft)": "vessel_length_ft",
        "Length of Vessel in Feet": "vessel_length_ft",
        "Boat Model": "vessel_model",
        "Model": "vessel_model",
        
        "Year of Vessel?": "vessel_year",
        "Vessel Year": "vessel_year",
        "Boat Year": "vessel_year",
        "Year": "vessel_year",
        
        "Is The Vessel On a Dock, At a Marina, or On a Trailer?": "vessel_location__slip",
        "Vessel Location": "vessel_location__slip",
        "Boat Location": "vessel_location__slip",
        "Location Details": "vessel_location__slip",
        
        "When Do You Prefer Service?": "desired_timeline",
        "Timeline": "desired_timeline",
        "Service Timeline": "desired_timeline",
        "Preferred Date": "desired_timeline",
        
        "Any Special Requests or Other Information?": "special_requests__notes",
        "Special Requests": "special_requests__notes",
        "Additional Notes": "special_requests__notes",
        "Comments": "special_requests__notes",
        "Notes": "special_requests__notes",
        
        # Vendor fields
        "What is Your Company Name?": "vendor_company_name",
        "Company Name": "vendor_company_name",
        "Business Name": "vendor_company_name",
        "Services Provided": "services_provided",
        "What Main Service Does Your Company Offer?": "services_provided",
        "Service Areas": "service_zip_codes",
        "Years in Business": "years_in_business",
        
        # Vendor contact preference
        "How Should We Contact You (Vendor)?": "vendor_preferred_contact_method",
        "Vendor Contact Preference": "vendor_preferred_contact_method",
        "Vendor Preferred Contact Method": "vendor_preferred_contact_method",
        "vendor_preferred_contact_method": "vendor_preferred_contact_method",  # Pass through
        
        # Vendor category and service fields
        "service_categories_selected": "service_categories_selected",  # No change needed
        "service_categorires_selected": "service_categories_selected",  # Fix typo if it exists
        
        # Contact preference
        "How Should We Contact You Back?": "preferred_contact_method",  # FIXED: Removed trailing space
        "How Should We Contact You Back? ": "preferred_contact_method",  # Keep for backward compatibility
        "Contact Preference": "preferred_contact_method",
        "Preferred Contact": "preferred_contact_method",
        
        # Form metadata fields (CRITICAL ADDITIONS)
        "Consent": "consent",
        "Preferred Partner": "vendor_preferred_partner",  # Maps to GHL field {{ contact.vendor_preferred_partner }}
        "Date": "form_submission_date",
        "Time": "form_submission_time",
        "Page URL": "source_page_url",
        "form_id": "elementor_form_id",
        "form_name": "elementor_form_name",
        # A Fields
        "any other requests or information?": "any_other_requests_or_information",
        "any special requests or information?": "any_special_requests_or_information",
        "are you a us citizen?": "are_you_a_us_citizen",
        "are you currently involved in a dispute with the person or company you're asking about?": "are_you_currently_involved_in_a_dispute_with_the_person_or_company_you're_asking_about",
        "are you currently working with a broker or dealer?": "are_you_currently_working_with_a_broker_or_dealer",
        "are you currently working with a realtor or broker?": "are_you_currently_working_with_a_realtor_or_broker",
        "are you looking for a custom or semi custom build?": "are_you_looking_for_a_custom_or_semi_custom_build",
        "are you looking for a jet ski rental or tour?": "are_you_looking_for_a_jet_ski_rental_or_tour",
        "are you looking for a kayak rental or tour?": "are_you_looking_for_a_kayak_rental_or_tour",
        "are you looking for a paddleboard rental or tour?": "are_you_looking_for_a_paddleboard_rental_or_tour",
        "are you looking for a pontoon rental or charter?": "are_you_looking_for_a_pontoon_rental_or_charter",
        "are you looking for any specific accreditations or compliance?": "are_you_looking_for_any_specific_accreditations_or_compliance",
        "are you looking to buy or sell a vessel?": "are_you_looking_to_buy_or_sell_a_vessel",
        "are you looking to buy or sell?": "are_you_looking_to_buy_or_sell",
        "are you requesting crew or looking for a job?": "are_you_requesting_crew_or_looking_for_a_job",
        "are you the owner of the property?": "are_you_the_owner_of_the_property",
        "are you the vessel owner?": "are_you_the_vessel_owner",
        
        # B Fields
        "brand/model of vessel looking to buy or sell?": "brand/model_of_vessel_looking_to_buy_or_sell",
        
        # C Fields
        "can you briefly describe the reason for your inquiry?": "can_you_briefly_describe_the_reason_for_your_inquiry",
        "current address of vessel?": "current_address_of_vessel",
        
        # D Fields
        "desired country manufacturer?": "desired_country_manufacturer",
        "desired delivery timeframe?": "desired_delivery_timeframe",
        "desired policy start date?": "desired_policy_start_date",
        "desired rental rate?": "desired_rental_rate",
        "desired survey date?": "desired_survey_date",
        "desired timeline of course or training?": "desired_timeline_of_course_or_training",
        "desired vessel length in feet?": "desired_vessel_length_in_feet",
        "destination address of vessel?": "destination_address_of_vessel",
        "did you purchase vessel yet?": "did_you_purchase_vessel_yet",
        "do you currently have boat insurance?": "do_you_currently_have_boat_insurance",
        "do you have a budget in mind?": "do_you_have_a_budget_in_mind",
        "do you have a budget in mind for this charter?": "do_you_have_a_budget_in_mind_for_this_charter",
        "do you have a desired manufacturer?": "do_you_have_a_desired_manufacturer",
        "do you have a trade-in?": "do_you_have_a_trade-in",
        "do you have capacity to take on more work?": "do_you_have_capacity_to_take_on_more_work",
        "do you own a vessel?": "do_you_own_a_vessel",
        "do you own the vessel?": "do_you_own_the_vessel",
        "do you own the vessel or what is your relationship?": "do_you_own_the_vessel_or_what_is_your_relationship",
        "do you require an emergency tow or towing membership?": "do_you_require_an_emergency_tow_or_towing_membership",
        
        # E Fields
        "estimated length of vessel looking to buy or sell?": "estimated_length_of_vessel_looking_to_buy_or_sell",
        
        # F Fields
        "finance amount requested?": "finance_amount_requested",
        "for how many people?": "for_how_many_people",
        "fuel delivery address?": "fuel_delivery_address",
        
        # H Fields
        "have you been a member of a boat club before?": "have_you_been_a_member_of_a_boat_club_before",
        "how long do you request dockage??": "how_long_do_you_request_dockage",
        "how long is your space available to rent?": "how_long_is_your_space_available_to_rent",
        "how many fuel tanks?": "how_many_fuel_tanks",
        "how many gallons of fuel needed roughly?": "how_many_gallons_of_fuel_needed_roughly",
        "how many jet skis are you interested in renting?": "how_many_jet_skis_are_you_interested_in_renting",
        "how many kayaks are you interested in renting?": "how_many_kayaks_are_you_interested_in_renting",
        "how many paddleboards are you interested in renting?": "how_many_paddleboards_are_you_interested_in_renting",
        "how many people in your party?": "how_many_people_in_your_party",
        "how many people roughly on the party boat charter?": "how_many_people_roughly_on_the_party_boat_charter",
        "how many people roughly on the pontoon rental or charter?": "how_many_people_roughly_on_the_pontoon_rental_or_charter",
        "how many people roughly on the private yacht charter?": "how_many_people_roughly_on_the_private_yacht_charter",
        "how often do you plan to use a boat each month?": "how_often_do_you_plan_to_use_a_boat_each_month",
        "how soon are you looking to buy or sell?": "how_soon_are_you_looking_to_buy_or_sell",
        "how will boat be used?": "how_will_boat_be_used",
        
        # I Fields
        "if looking for crew, how many positions?": "if_looking_for_crew,_how_many_positions",
        "is the vessel on a dock, at a marina, or on a trailer?": "is_the_vessel_on_a_dock,_at_a_marina,_or_on_a_trailer",
        "is this a one-time request or ongoing service?": "is_this_a_one-time_request_or_ongoing_service",
        
        # L Fields
        "length of desired dockage in feet?": "length_of_desired_dockage_in_feet",
        "length of dock or seawall in feet?": "length_of_dock_or_seawall_in_feet",
        "longest desired rental?": "longest_desired_rental",
        
        # M Fields
        "manufactuer of vessel?": "manufactuer_of_vessel",
        
        # N Fields
        "number of engines?": "number_of_engines",
        "number of rooms or desired rooms?": "number_of_rooms_or_desired_rooms",
        "number of years boating experience?": "number_of_years_boating_experience",
        
        # S Fields
        "send a link to some of your reviews?": "send_a_link_to_some_of_your_reviews",
        "shortest desired rental?": "shortest_desired_rental",
        "square feet of home or desired square feet?": "square_feet_of_home_or_desired_square_feet",
        
        # T Fields
        "tell us more about your company?": "tell_us_more_about_your_company",
        "type of dockage available?": "type_of_dockage_available",
        "type of dockage requested?": "type_of_dockage_requested",
        "type of financing requested?": "type_of_financing_requested",
        
        # W Fields
        "what accomodations are included?": "what_accomodations_are_included",
        "what dates specifically is the dock or slip available?": "what_dates_specifically_is_the_dock_or_slip_available",
        "what education or training do you request? ": "what_education_or_training_do_you_request",
        "what is the duration of your request?": "what_is_the_duration_of_your_request",
        "what is the vessel manufacturer?": "what_is_the_vessel_manufacturer",
        "what is the vessel model or length of vessel in feet?": "what_is_the_vessel_model_or_length_of_vessel_in_feet",
        "what is your boating experience?": "what_is_your_boating_experience",
        "what is your ideal budget?": "what_is_your_ideal_budget",
        "what management services do you request?": "what_management_services_do_you_request",
        "what product category are you interested in?": "what_product_category_are_you_interested_in",
        "what product specifically are you interested in?": "what_product_specifically_are_you_interested_in",
        "what specific attorney service do you request?": "what_specific_attorney_service_do_you_request",
        "what specific charter do you request?": "what_specific_charter_do_you_request",
        "what specific dates do you require dockage?": "what_specific_dates_do_you_require_dockage",
        "what specific parts do you request?": "what_specific_parts_do_you_request",
        "what specific sailboat charter do you request?": "what_specific_sailboat_charter_do_you_request",
        "what specific service do you request?": "what_specific_service_do_you_request",
        "what to survey?": "what_to_survey",
        "what type of boat club are you interested in??": "what_type_of_boat_club_are_you_interested_in",
        "what type of crew?": "what_type_of_crew",
        "what type of fuel do you need?": "what_type_of_fuel_do_you_need",
        "what type of party boat are you interested in?": "what_type_of_party_boat_are_you_interested_in",
        "what type of private yacht charter are you interested in?": "what_type_of_private_yacht_charter_are_you_interested_in",
        "what type of salvage do you request?": "what_type_of_salvage_do_you_request",
        "what type of trip do you request provisioning for?": "what_type_of_trip_do_you_request_provisioning_for",
        "what type of vessel are you looking to buy or sell?": "what_type_of_vessel_are_you_looking_to_buy_or_sell",
        "what type of vessel are you looking to insure?": "what_type_of_vessel_are_you_looking_to_insure",
        "what type of vessel are you looking to survey?": "what_type_of_vessel_are_you_looking_to_survey",
        "what types of boats are you most comfortable or interested in?": "what_types_of_boats_are_you_most_comfortable_or_interested_in",
        "what zip code is your vessel in most frequently?": "what_zip_code_is_your_vessel_in_most_frequently",
        "what's your current company address?": "what's_your_current_company_address",
        "when do you prefer buying or selling?": "when_do_you_prefer_buying_or_selling",
        "when do you prefer your charter?": "when_do_you_prefer_your_charter",
        "when do you prefer your charter or rental?": "when_do_you_prefer_your_charter_or_rental",
        "when do you prefer your dive charter, lessons or equipment rental?": "when_do_you_prefer_your_dive_charter,_lessons_or_equipment_rental",
        "when do you prefer your fishing charter?": "when_do_you_prefer_your_fishing_charter",
        "when do you prefer your lessons or equipment rental?": "when_do_you_prefer_your_lessons_or_equipment_rental",
        "when do you prefer your rental or charter?": "when_do_you_prefer_your_rental_or_charter",
        "when do you prefer your rental or tour?": "when_do_you_prefer_your_rental_or_tour",
        "where is the vessel located?": "where_is_the_vessel_located",
        "where is the vessel now?": "where_is_the_vessel_now",
        "who are you?": "who_are_you",
        
        # Y Fields
        "your engine manufacturer or preferred engine manufacturer?": "your_engine_manufacturer_or_preferred_engine_manufacturer",
        "your generator manufacturer or preferred generator manufacturer?": "your_generator_manufacturer_or_preferred_generator_manufacturer",
        "your primary zip code?": "your_primary_zip_code"
    }
    
    normalized_payload = {}
    
    # Create a stripped version of field_mappings for fuzzy matching
    stripped_mappings = {}
    for key, value in field_mappings.items():
        stripped_key = key.strip().lower()
        stripped_mappings[stripped_key] = value
    
    # First pass: direct mapping with intelligent matching
    for original_key, value in payload.items():
        # Skip empty values and system fields
        if not value or value == "" or original_key.startswith("No Label"):
            continue
            
        # Try exact match first
        if original_key in field_mappings:
            normalized_payload[field_mappings[original_key]] = value
        else:
            # Try stripped/lowercase match for robustness
            stripped_key = original_key.strip().lower()
            if stripped_key in stripped_mappings:
                normalized_payload[stripped_mappings[stripped_key]] = value
                logger.debug(f"🔄 Fuzzy matched '{original_key}' → '{stripped_mappings[stripped_key]}' (stripped whitespace)")
            else:
                # Keep original key if no mapping found
                normalized_payload[original_key] = value
    
    # Log the normalization for debugging
    mapped_fields = []
    for original_key in payload.keys():
        if original_key in field_mappings:
            mapped_fields.append(f"{original_key} → {field_mappings[original_key]}")
    
    if mapped_fields:
        logger.info(f"🔄 Field name normalization applied:")
        for mapping in mapped_fields:
            logger.info(f"   {mapping}")
    
    logger.info(f"📋 Normalized payload keys: {list(normalized_payload.keys())}")
    
    # Detect critical unmapped fields and warn
    critical_patterns = [
        ("service", "specific_service_needed"),
        ("zip", "zip_code_of_service"),
        ("email", "email"),
        ("phone", "phone"),
        ("name", "firstName or lastName")
    ]
    
    unmapped_keys = [k for k in payload.keys() 
                     if k not in field_mappings 
                     and not k.startswith("No Label")
                     and k.strip().lower() not in stripped_mappings]
    
    if unmapped_keys:
        logger.warning(f"⚠️ Found {len(unmapped_keys)} unmapped fields: {unmapped_keys}")
        for key in unmapped_keys:
            key_lower = key.lower()
            for pattern, expected_field in critical_patterns:
                if pattern in key_lower:
                    logger.warning(f"❗ Critical field '{key}' might need mapping to '{expected_field}'")
                    # Auto-map obvious service fields
                    if pattern == "service" and "specific" in key_lower and "specific_service_needed" not in normalized_payload:
                        normalized_payload["specific_service_needed"] = payload[key]
                        logger.info(f"🔧 Auto-mapped '{key}' to 'specific_service_needed' based on pattern match")
    
    return normalized_payload

def get_form_configuration(form_identifier: str) -> Dict[str, Any]:
    """
    Direct form configuration - NO AI processing
    Returns configuration based on form identifier patterns
    """
    
    # Extract service category using direct mapping
    service_category = get_direct_service_category(form_identifier)
    
    # Determine form type based on identifier patterns
    form_type = "unknown"
    priority = "normal"
    requires_immediate_routing = False
    
    if any(keyword in form_identifier.lower() for keyword in ["vendor", "network", "join", "application"]):
        form_type = "vendor_application"
        requires_immediate_routing = False
        priority = "normal"
    elif any(keyword in form_identifier.lower() for keyword in ["emergency", "tow", "breakdown", "urgent"]):
        form_type = "emergency_service"
        requires_immediate_routing = True
        priority = "high"
    elif any(keyword in form_identifier.lower() for keyword in ["subscribe", "email", "contact", "inquiry"]):
        form_type = "general_inquiry"
        requires_immediate_routing = False
        priority = "low"
    else:
        form_type = "client_lead"
        requires_immediate_routing = True
        priority = "normal"
    
    # Generate appropriate tags
    tags = [service_category, "DSP Elementor"]
    if form_type == "emergency_service":
        tags.extend(["Emergency", "High Priority", "Urgent"])
    elif form_type == "vendor_application":
        tags.extend(["New Vendor Application"])
    else:
        tags.extend(["New Lead"])
    
    # Generate source description
    source_name = form_identifier.replace("_", " ").title()
    if not source_name.endswith("(DSP)"):
        source_name += " (DSP)"
    
    return {
        "form_type": form_type,
        "service_category": service_category,
        "tags": tags,
        "source": source_name,
        "priority": priority,
        "requires_immediate_routing": requires_immediate_routing,
        "expected_fields": get_expected_fields_for_form_type(form_type)
    }

def get_expected_fields_for_form_type(form_type: str) -> List[str]:
    """Return expected fields based on form type"""
    base_fields = ["firstName", "lastName", "email", "phone"]
    
    if form_type == "client_lead":
        return base_fields + ["zip_code_of_service", "specific_service_needed", "desired_timeline", "special_requests__notes"]
    elif form_type == "vendor_application":
        return base_fields + ["vendor_company_name", "services_provided", "service_zip_codes", "years_in_business"]
    elif form_type == "emergency_service":
        return base_fields + ["vessel_location__slip", "special_requests__notes", "zip_code_of_service"]
    else:
        return base_fields

def validate_form_submission(form_identifier: str, payload: Dict[str, Any], form_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Direct validation for form submissions - NO AI processing
    """
    validation_result = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "missing_expected_fields": [],
        "unexpected_fields": [],
        "field_count": len(payload)
    }
    
    # Check for required fields based on form type
    required_fields = ["email"]  # Email is always required
    form_type = form_config.get("form_type")
    
    if form_type in ["client_lead", "emergency_service"]:
        required_fields.extend(["firstName", "lastName"])
    elif form_type == "vendor_application":
        required_fields.extend(["firstName", "lastName", "vendor_company_name"])
    
    # Validate required fields
    for field in required_fields:
        if not payload.get(field) or str(payload.get(field)).strip() == "":
            validation_result["errors"].append(f"Required field '{field}' is missing or empty")
            validation_result["is_valid"] = False
    
    # Check for expected fields (warnings only)
    expected_fields = form_config.get("expected_fields", [])
    for field in expected_fields:
        if not payload.get(field):
            validation_result["missing_expected_fields"].append(field)
            validation_result["warnings"].append(f"Expected field '{field}' is missing - form may be incomplete")
    
    # Check for unexpected fields (informational) - using field_mapper
    valid_ghl_fields = field_mapper.get_all_ghl_field_keys()
    for field in payload.keys():
        # Check if field maps to a valid GHL field
        mapped_field = field_mapper.get_mapping(field, "marine")
        if mapped_field not in valid_ghl_fields:
            validation_result["unexpected_fields"].append(field)
            validation_result["warnings"].append(f"Field '{field}' maps to '{mapped_field}' which is not a recognized GHL field")
    
    # Validate email format
    email = payload.get("email", "")
    if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        validation_result["errors"].append("Invalid email format")
        validation_result["is_valid"] = False
    
    return validation_result

def process_payload_to_ghl_format(elementor_payload: Dict[str, Any], form_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process Elementor payload into GHL format - PRESERVE ALL FIELDS
    Direct field mapping only - NO AI processing
    """
    # Apply field mapping using ServiceDictionaryMapper
    mapper = ServiceDictionaryMapper()
    mapping_result = mapper.map_payload_to_service(elementor_payload)
    mapped_payload = mapping_result.get('standardized_fields', {})
    service_classification = mapping_result.get('service_classification', {})
    logger.info(f"🔄 Applied ServiceDictionaryMapper. Original keys: {list(elementor_payload.keys())}, Mapped keys: {list(mapped_payload.keys())}")
    
    final_ghl_payload = {}
    custom_fields_array = []
    
    # Standard GHL contact fields
    standard_fields = {
        "firstName", "lastName", "email", "phone", "companyName", 
        "address1", "city", "state", "postal_code", "name",
        "tags", "notes", "dnd", "country", "source", "website"
    }
    
    # Process each field from mapped payload - PRESERVE EVERYTHING
    for field_key, field_value in mapped_payload.items():
        # Skip empty values (but allow 0 and False)
        if field_value == "" or field_value is None:
            logger.debug(f"Skipping empty value for field '{field_key}'")
            continue
        
        # Check if it's a valid GHL field using field_mapper
        if field_mapper.is_valid_ghl_field(field_key):
            if field_key in standard_fields:
                # Standard GHL contact fields go directly in main payload
                final_ghl_payload[field_key] = field_value
                logger.debug(f"Added standard field: {field_key} = {field_value}")
            else:
                # Custom fields go into customFields array using field_mapper
                field_details = field_mapper.get_ghl_field_details(field_key)
                if field_details and field_details.get("id"):
                    custom_fields_array.append({
                        "id": field_details["id"],
                        "value": str(field_value)
                    })
                    logger.debug(f"Added custom field: {field_details['name']} ({field_key}) = {field_value} [ID: {field_details['id']}]")
                else:
                    logger.warning(f"Custom field '{field_key}' is valid but missing GHL field ID mapping")
        else:
            logger.warning(f"Field '{field_key}' from form is not a recognized GHL field. Ignoring.")
    
    # Add form-specific static data from configuration
    for ghl_key, static_value in form_config.items():
        # Skip non-field configuration items and service_category for vendor applications
        if ghl_key in ["form_type", "priority", "requires_immediate_routing", "expected_fields"]:
            continue
        
        # Don't override service_category for vendor applications - let form data take precedence
        if ghl_key == "service_category" and form_config.get("form_type") == "vendor_application":
            continue
            
        if ghl_key == "tags":
            # Handle tags merging carefully
            current_tags = final_ghl_payload.get("tags", [])
            if isinstance(current_tags, str):
                current_tags = [t.strip() for t in current_tags.split(',') if t.strip()]
            elif not isinstance(current_tags, list):
                current_tags = []
            
            new_tags = static_value if isinstance(static_value, list) else [static_value]
            # Merge and deduplicate tags
            final_ghl_payload["tags"] = list(set(current_tags + new_tags))
            
        elif ghl_key in standard_fields:
            # Only set standard fields if not already provided by form
            if not final_ghl_payload.get(ghl_key):
                final_ghl_payload[ghl_key] = static_value
        else:
            # Custom field from form config - add to customFields array if not already present
            field_details = field_mapper.get_ghl_field_details(ghl_key)
            if field_details and field_details.get("id"):
                # Check if this field is already in the custom fields array
                field_exists = any(cf["id"] == field_details["id"] for cf in custom_fields_array)
                if not field_exists:
                    custom_fields_array.append({
                        "id": field_details["id"],
                        "value": str(static_value)
                    })
                    logger.debug(f"Added static custom field: {field_details['name']} ({ghl_key}) = {static_value}")

    # SPECIAL HANDLING: For vendor applications, ensure all vendor-specific fields are properly mapped
    if form_config.get("form_type") == "vendor_application":
        # 1. Handle NEW multi-step service category structure
        # Primary service category (single selection)
        primary_service_category = elementor_payload.get('primary_service_category', '')
        if primary_service_category:
            primary_category_field = field_mapper.get_ghl_field_details("primary_service_category")
            if primary_category_field and primary_category_field.get("id"):
                field_exists = any(cf["id"] == primary_category_field["id"] for cf in custom_fields_array)
                if not field_exists:
                    custom_fields_array.append({
                        "id": primary_category_field["id"],
                        "value": primary_service_category
                    })
                    logger.info(f"✅ Added Primary Service Category field: {primary_service_category}")
        
        # Combined service categories (primary + additional, max 3 total)
        combined_categories = []
        if primary_service_category:
            combined_categories.append(primary_service_category)
        
        # Add additional categories (up to 2 more)
        additional_categories = elementor_payload.get('additional_categories', [])
        if isinstance(additional_categories, list):
            combined_categories.extend(additional_categories[:2])  # Max 2 additional
        elif isinstance(additional_categories, str) and additional_categories:
            # Handle comma-separated string
            additional_list = [cat.strip() for cat in additional_categories.split(',')]
            combined_categories.extend(additional_list[:2])
        
        # Store combined categories in the general service_category field for backward compatibility
        if combined_categories:
            service_category_field = field_mapper.get_ghl_field_details("service_category")
            if service_category_field and service_category_field.get("id"):
                field_exists = any(cf["id"] == service_category_field["id"] for cf in custom_fields_array)
                if not field_exists:
                    combined_categories_str = ', '.join(combined_categories)
                    custom_fields_array.append({
                        "id": service_category_field["id"],
                        "value": combined_categories_str
                    })
                    logger.info(f"✅ Added Combined Service Categories field: {combined_categories_str}")
            else:
                logger.warning(f"⚠️ Could not find Service Category field details in field_mapper")
        
        # 2. Handle services provided (from multi-step selection)
        # Combine primary services and additional services
        all_services = []
        
        # CRITICAL FIX: Handle Level 3 services when available, otherwise use Level 2
        # Level 3 services are the specific services within subcategories
        primary_level3_services = elementor_payload.get('primary_level3_services', {})
        additional_level3_services = elementor_payload.get('additional_level3_services', {})
        
        # DEBUG: Log exactly what we received for Level 3 services
        logger.info(f"🔍 DEBUG - Raw primary_level3_services type: {type(primary_level3_services)}")
        logger.info(f"🔍 DEBUG - Raw primary_level3_services content: {primary_level3_services}")
        logger.info(f"🔍 DEBUG - Raw additional_level3_services type: {type(additional_level3_services)}")
        logger.info(f"🔍 DEBUG - Raw additional_level3_services content: {additional_level3_services}")
        
        # Combine all Level 3 services if they exist
        all_level3_services = []
        
        # Process primary Level 3 services
        if primary_level3_services and isinstance(primary_level3_services, dict):
            for subcategory, level3_list in primary_level3_services.items():
                if isinstance(level3_list, list):
                    all_level3_services.extend(level3_list)
                    logger.info(f"📋 Primary Level 3 services for {subcategory}: {level3_list}")
        
        # Process additional Level 3 services
        if additional_level3_services and isinstance(additional_level3_services, dict):
            for subcategory, level3_list in additional_level3_services.items():
                if isinstance(level3_list, list):
                    all_level3_services.extend(level3_list)
                    logger.info(f"📋 Additional Level 3 services for {subcategory}: {level3_list}")
        
        # If we have Level 3 services, use them. Otherwise fall back to Level 2
        if all_level3_services:
            # Use Level 3 services as the specific services offered
            all_services = all_level3_services
            logger.info(f"✅ Using Level 3 services: {all_services}")
            
            # CRITICAL: Override the incoming services_provided field with Level 3 services
            # The form sends Level 2 in services_provided, but we want Level 3 when available
            elementor_payload['services_provided'] = ', '.join(all_level3_services)
            logger.info(f"📝 Overriding services_provided with Level 3 services")
        else:
            # Fall back to Level 2 services (subcategories) when no Level 3 exists
            all_services = []
            
            # Primary services from the primary category (Level 2)
            primary_services = elementor_payload.get('primary_services', [])
            if isinstance(primary_services, list):
                all_services.extend(primary_services)
            elif isinstance(primary_services, str) and primary_services:
                primary_list = [svc.strip() for svc in primary_services.split(',')]
                all_services.extend(primary_list)
            
            # Additional services from additional categories (Level 2)
            additional_services = elementor_payload.get('additional_services', [])
            if isinstance(additional_services, list):
                all_services.extend(additional_services)
            elif isinstance(additional_services, str) and additional_services:
                additional_list = [svc.strip() for svc in additional_services.split(',')]
                all_services.extend(additional_list)
            
            logger.info(f"ℹ️ No Level 3 services found, using Level 2 services: {all_services}")
        
        # Store combined services
        if all_services:
            services_provided_field = field_mapper.get_ghl_field_details("services_provided")
            if services_provided_field and services_provided_field.get("id"):
                # Remove any existing services_provided field to replace with correct data
                custom_fields_array = [cf for cf in custom_fields_array if cf.get("id") != services_provided_field["id"]]
                
                combined_services_str = ', '.join(all_services)
                custom_fields_array.append({
                    "id": services_provided_field["id"],
                    "value": combined_services_str
                })
                logger.info(f"✅ Added Combined Services Provided field with Level 3: {combined_services_str}")
        
        # Also check for legacy services_provided field for backward compatibility
        legacy_services = elementor_payload.get('services_provided', '')
        if legacy_services and not all_services:
            services_provided_field = field_mapper.get_ghl_field_details("services_provided")
            if services_provided_field and services_provided_field.get("id"):
                field_exists = any(cf["id"] == services_provided_field["id"] for cf in custom_fields_array)
                if not field_exists:
                    custom_fields_array.append({
                        "id": services_provided_field["id"],
                        "value": legacy_services
                    })
                    logger.info(f"✅ Added Legacy Services Provided field: {legacy_services}")
        
        # 3. Handle service ZIP codes (use existing service_zip_codes field)
        # Store coverage data in service_zip_codes field based on coverage type
        coverage_type = elementor_payload.get('coverage_type', 'county')
        service_coverage_area = elementor_payload.get('service_coverage_area', '')
        
        # Get the service_zip_codes field which exists in GHL
        service_zip_codes_field = field_mapper.get_ghl_field_details("service_zip_codes")
        if service_zip_codes_field and service_zip_codes_field.get("id"):
            field_exists = any(cf["id"] == service_zip_codes_field["id"] for cf in custom_fields_array)
            if not field_exists:
                # Format the coverage data appropriately
                coverage_value = ""
                
                if coverage_type == "global":
                    coverage_value = "GLOBAL COVERAGE"
                elif coverage_type == "national":
                    coverage_value = "NATIONAL COVERAGE (USA)"
                elif coverage_type == "state":
                    coverage_states = elementor_payload.get('coverage_states', [])
                    if coverage_states:
                        coverage_value = f"STATES: {', '.join(coverage_states)}"
                elif coverage_type == "county":
                    coverage_counties = elementor_payload.get('coverage_counties', [])
                    if coverage_counties:
                        coverage_value = f"COUNTIES: {'; '.join(coverage_counties)}"
                elif coverage_type == "zip":
                    zip_codes = elementor_payload.get('service_zip_codes', '')
                    if zip_codes:
                        coverage_value = f"ZIP CODES: {zip_codes}"
                
                # If we have coverage data, add it to the field
                if coverage_value:
                    custom_fields_array.append({
                        "id": service_zip_codes_field["id"],
                        "value": coverage_value
                    })
                    logger.info(f"✅ Added Service Coverage to service_zip_codes field: {coverage_value}")
        
        # 4. Add taking new work field
        taking_new_work = elementor_payload.get('taking_new_work', '')
        if taking_new_work:
            taking_work_field = field_mapper.get_ghl_field_details("taking_new_work")
            if taking_work_field and taking_work_field.get("id"):
                field_exists = any(cf["id"] == taking_work_field["id"] for cf in custom_fields_array)
                if not field_exists:
                    custom_fields_array.append({
                        "id": taking_work_field["id"],
                        "value": taking_new_work
                    })
                    logger.info(f"✅ Added Taking New Work field: {taking_new_work}")
        
        # 5. Add reviews URL field
        reviews_url = elementor_payload.get('reviews__google_profile_url', '')
        if reviews_url:
            reviews_field = field_mapper.get_ghl_field_details("reviews__google_profile_url")
            if reviews_field and reviews_field.get("id"):
                field_exists = any(cf["id"] == reviews_field["id"] for cf in custom_fields_array)
                if not field_exists:
                    custom_fields_array.append({
                        "id": reviews_field["id"],
                        "value": reviews_url
                    })
                    logger.info(f"✅ Added Reviews URL field: {reviews_url}")
        
        # 6. Add vendor preferred contact method
        contact_method = elementor_payload.get('vendor_preferred_contact_method', '')
        if contact_method:
            contact_method_field = field_mapper.get_ghl_field_details("vendor_preferred_contact_method")
            if contact_method_field and contact_method_field.get("id"):
                field_exists = any(cf["id"] == contact_method_field["id"] for cf in custom_fields_array)
                if not field_exists:
                    custom_fields_array.append({
                        "id": contact_method_field["id"],
                        "value": contact_method
                    })
                    logger.info(f"✅ Added Vendor Preferred Contact Method field: {contact_method}")
        
        # 7. Add vendor address information if available
        if elementor_payload.get('address1'):
            vendor_address_field = field_mapper.get_ghl_field_details("vendor_address")
            if vendor_address_field and vendor_address_field.get("id"):
                field_exists = any(cf["id"] == vendor_address_field["id"] for cf in custom_fields_array)
                if not field_exists:
                    custom_fields_array.append({
                        "id": vendor_address_field["id"],
                        "value": elementor_payload.get('address1', '')
                    })
                    logger.info(f"✅ Added Vendor Address field")

    # Add customFields array to payload if we have any custom fields
    if custom_fields_array:
        final_ghl_payload["customFields"] = custom_fields_array
        logger.info(f"✅ Added {len(custom_fields_array)} custom fields to GHL payload")
        
        # Log each custom field being sent
        for i, field in enumerate(custom_fields_array):
            logger.info(f"  Custom Field [{i}]: ID={field['id']}, Value='{field['value']}'")
    else:
        logger.warning("⚠️ No custom fields added to GHL payload - this may indicate a mapping issue")
    
    return final_ghl_payload

def convert_service_areas_to_counties(zip_codes_input) -> Dict[str, Any]:
    """
    Convert ZIP codes to counties for vendor applications
    Direct location service conversion - NO AI processing
    Handles both string and list input formats
    """
    if not zip_codes_input:
        return {"counties": [], "zip_codes": [], "conversion_success": False}
    
    # Handle both list and string input
    if isinstance(zip_codes_input, list):
        # If it's already a list, use it directly but clean up each entry
        zip_codes = [zip_code.strip() for zip_code in zip_codes_input if zip_code and zip_code.strip()]
    elif isinstance(zip_codes_input, str):
        # If it's a string, split by comma
        zip_codes = [zip_code.strip() for zip_code in zip_codes_input.split(',') if zip_code.strip()]
    else:
        # Unknown format
        return {"counties": [], "zip_codes": [], "conversion_success": False}
    
    if not zip_codes:
        return {"counties": [], "zip_codes": [], "conversion_success": False}
    
    # Convert ZIP codes to counties using location service
    counties = []
    successful_conversions = 0
    conversion_details = []
    
    for zip_code in zip_codes:
        zip_str = zip_code.strip()
        
        # Validate ZIP code format
        if len(zip_str) == 5 and zip_str.isdigit():
            location_data = location_service.zip_to_location(zip_str)
            
            if not location_data.get('error'):
                county = location_data.get('county')
                state = location_data.get('state')
                city = location_data.get('city')
                
                if county and state:
                    county_entry = f"{county}, {state}"
                    if county_entry not in counties:
                        counties.append(county_entry)
                    
                    conversion_details.append({
                        "zip_code": zip_str,
                        "county": county,
                        "state": state,
                        "city": city,
                        "success": True
                    })
                    successful_conversions += 1
                    logger.info(f"🗺️ Vendor Application: ZIP {zip_str} → {county_entry}")
                else:
                    conversion_details.append({
                        "zip_code": zip_str,
                        "error": "No county/state data",
                        "success": False
                    })
                    logger.warning(f"⚠️ Vendor Application: ZIP {zip_str} resolved but missing county/state")
            else:
                conversion_details.append({
                    "zip_code": zip_str,
                    "error": location_data['error'],
                    "success": False
                })
                logger.warning(f"⚠️ Vendor Application: Could not convert ZIP {zip_str}: {location_data['error']}")
        else:
            conversion_details.append({
                "zip_code": zip_str,
                "error": "Invalid ZIP code format",
                "success": False
            })
            logger.warning(f"⚠️ Vendor Application: Invalid ZIP code format: '{zip_str}'")
    
    conversion_rate = (successful_conversions / len(zip_codes)) * 100 if zip_codes else 0
    
    return {
        "counties": counties,
        "zip_codes": zip_codes,
        "conversion_success": successful_conversions > 0,
        "conversion_rate": conversion_rate,
        "conversion_details": conversion_details,
        "successful_conversions": successful_conversions,
        "total_zip_codes": len(zip_codes)
    }

# DEBUG GET endpoint to test routing
@router.get("/elementor/{form_identifier}")
@router.get("/elementor/{form_identifier}/")
async def debug_webhook_endpoint(form_identifier: str, request: Request):
    """
    DEBUG: This GET endpoint should help diagnose the redirect issue
    """
    logger.info(f"🔍 DEBUG GET REQUEST: form_identifier={form_identifier}, method={request.method}, url={request.url}")
    return {
        "status": "debug_response",
        "message": f"This is a GET request to the webhook endpoint for form '{form_identifier}'",
        "method_received": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "note": "If you're seeing this, there's likely a redirect converting your POST to GET. Check your webhook URL configuration.",
        "correct_method": "POST",
        "webhook_url": f"/api/v1/webhooks/elementor/{form_identifier}"
    }

@router.post("/elementor/{form_identifier}")
@router.post("/elementor/{form_identifier}/")
async def handle_clean_elementor_webhook(
    form_identifier: str, 
    request: Request,
    background_tasks: BackgroundTasks  # Keep parameter for compatibility but don't use it
):
    """
    Clean webhook handler for ALL Elementor form submissions.
    Returns 200 OK immediately and processes in background.
    Direct processing only - NO AI interference.
    Preserves ALL form data exactly as received from WordPress.
    """
    # Get the raw body - this is async but fast
    body = await request.body()
    content_type = request.headers.get("content-type", "")
    
    # Start a completely independent thread for processing
    # This ensures the response is returned immediately
    def run_async_task():
        """Run the async task in a new event loop in a separate thread"""
        try:
            # Set up logging for this thread
            logger.info(f"🚀 Starting background thread for webhook: {form_identifier}")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    process_elementor_webhook_with_body(
                        form_identifier,
                        body,
                        content_type
                    )
                )
                logger.info(f"✅ Background thread completed for webhook: {form_identifier}")
            except Exception as e:
                logger.error(f"❌ Background thread error for {form_identifier}: {e}", exc_info=True)
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"💥 Critical thread error for {form_identifier}: {e}", exc_info=True)
    
    # Start the thread - this returns immediately
    thread = threading.Thread(target=run_async_task, daemon=True, name=f"webhook-{form_identifier}")
    thread.start()
    logger.info(f"📤 Returning immediate 200 OK for {form_identifier}, processing in thread: {thread.name}")
    
    # Return 200 OK immediately using JSONResponse for fastest response
    return JSONResponse(
        content={
            "status": "accepted",
            "message": "Webhook received and queued for processing",
            "form_identifier": form_identifier
        },
        status_code=200
    )


async def process_elementor_webhook_with_body(
    form_identifier: str,
    body: bytes,
    content_type: str
):
    """
    Background task to process Elementor webhook from raw body.
    This runs after returning 200 OK to WordPress.
    """
    start_time = time.time()
    
    try:
        logger.info(f"🔄 Background processing started for '{form_identifier}' - Content-Type: {content_type}")
        
        # Now parse the body in the background
        if "application/json" in content_type:
            elementor_payload = json.loads(body.decode('utf-8'))
            logger.info(f"✅ Parsed JSON payload with {len(elementor_payload)} fields")
        elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            from urllib.parse import parse_qs
            body_str = body.decode('utf-8')
            elementor_payload = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(body_str).items()}
            logger.info(f"✅ Parsed form-encoded payload with {len(elementor_payload)} fields")
        else:
            # Try JSON by default
            elementor_payload = json.loads(body.decode('utf-8'))
            logger.info(f"✅ Parsed payload as JSON (default) with {len(elementor_payload)} fields")
        
        # Use enhanced service mapping instead of just normalization
        # This consolidates redundant fields and adds intelligent service classification
        try:
            logger.info(f"🔧 Applying intelligent service mapping for form '{form_identifier}'")
            processed_payload, service_metadata = process_webhook_with_service_mapping(elementor_payload)
            elementor_payload = processed_payload
            
            # Log the service classification results
            logger.info(f"📊 Service Classification Results:")
            logger.info(f"   - Level 1 Category: {service_metadata.get('primary_category', 'Not identified')}")
            logger.info(f"   - Level 2 Service: {service_metadata.get('service_type', 'Not identified')}")
            logger.info(f"   - Level 3 Specific: {service_metadata.get('specific_service', 'Not identified')}")
            logger.info(f"   - Routing Priority: {service_metadata.get('routing_priority', 'normal')}")
            
        except Exception as e:
            logger.warning(f"⚠️ Service mapping failed, falling back to basic normalization: {e}")
            # Fallback to basic normalization if service mapping fails
            elementor_payload = normalize_field_names(elementor_payload)
        
        logger.info(f"📥 Processing webhook in background for form '{form_identifier}': {json.dumps(elementor_payload, indent=2)}")
        
        # Now continue with the original processing
        await process_elementor_webhook_async(form_identifier, elementor_payload)
        
        processing_time = time.time() - start_time
        logger.info(f"✅ Background processing completed for '{form_identifier}' in {processing_time:.2f}s")
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ Failed to process webhook body for form '{form_identifier}' after {processing_time:.2f}s: {e}", exc_info=True)
        simple_db_instance.log_activity(
            event_type="webhook_processing_error",
            event_data={
                "form": form_identifier,
                "error": str(e),
                "processing_time": processing_time
            },
            success=False,
            error_message=str(e)
        )


async def process_elementor_webhook_async(
    form_identifier: str,
    elementor_payload: Dict[str, Any]
):
    """
    Background task to process Elementor webhook data.
    This runs after returning 200 OK to WordPress.
    """
    start_time = time.time()
    
    try:
        logger.info(f"🔄 Starting background processing for form '{form_identifier}'")
        
        # Debug logging for key vendor fields
        logger.info(f"📋 Key vendor fields in normalized payload:")
        logger.info(f"   - vendor_company_name: '{elementor_payload.get('vendor_company_name')}'")
        logger.info(f"   - service_categories_selected: '{elementor_payload.get('service_categories_selected')}'")
        logger.info(f"   - services_provided: '{elementor_payload.get('services_provided')}'")
        logger.info(f"   - service_zip_codes: '{elementor_payload.get('service_zip_codes')}'")
        
        # SPECIAL DEBUG for Level 3 services investigation
        if "vendor" in form_identifier.lower():
            logger.info(f"🔍 VENDOR APPLICATION - Level 3 Services Debug:")
            logger.info(f"   - primary_level3_services present: {'primary_level3_services' in elementor_payload}")
            logger.info(f"   - additional_level3_services present: {'additional_level3_services' in elementor_payload}")
            logger.info(f"   - all_level3_services present: {'all_level3_services' in elementor_payload}")
            if 'primary_level3_services' in elementor_payload:
                logger.info(f"   - primary_level3_services type: {type(elementor_payload.get('primary_level3_services'))}")
                logger.info(f"   - primary_level3_services content: {elementor_payload.get('primary_level3_services')}")
            if 'additional_level3_services' in elementor_payload:
                logger.info(f"   - additional_level3_services type: {type(elementor_payload.get('additional_level3_services'))}")
                logger.info(f"   - additional_level3_services content: {elementor_payload.get('additional_level3_services')}")

        # Get direct form configuration - NO AI
        form_config = get_form_configuration(form_identifier)
        logger.info(f"📋 Direct form config for '{form_identifier}': {form_config}")

        # Validate form submission - Direct validation only
        validation_result = validate_form_submission(form_identifier, elementor_payload, form_config)
        if not validation_result["is_valid"]:
            logger.error(f"❌ Form validation failed for '{form_identifier}': {validation_result['errors']}")
            simple_db_instance.log_activity(
                event_type="elementor_webhook_validation_error",
                event_data={
                    "form": form_identifier,
                    "validation_errors": validation_result["errors"],
                    "payload_keys": list(elementor_payload.keys())
                },
                success=False,
                error_message=f"Validation failed: {', '.join(validation_result['errors'])}"
            )
            raise HTTPException(status_code=400, detail=f"Form validation failed: {', '.join(validation_result['errors'])}")
        
        # Log any warnings
        if validation_result["warnings"]:
            logger.warning(f"⚠️ Form validation warnings for '{form_identifier}': {validation_result['warnings']}")

        # Initialize GHL API client
        # Use optimized v2 API for better performance
        ghl_api_client = OptimizedGoHighLevelAPI(
            private_token=AppConfig.GHL_PRIVATE_TOKEN, 
            location_id=AppConfig.GHL_LOCATION_ID,
            agency_api_key=AppConfig.GHL_AGENCY_API_KEY,
            location_api_key=AppConfig.GHL_LOCATION_API  # Keep for fallback
        )
        logger.info(f"🔑 GHL API client initialized")

        # Process payload into GHL format - PRESERVE ALL FIELDS
        final_ghl_payload = process_payload_to_ghl_format(elementor_payload, form_config)
        
        # Handle vendor application specific coverage data processing
        if form_config.get("form_type") == "vendor_application":
            coverage_type = elementor_payload.get('coverage_type', 'county')
            
            # For ZIP code coverage type, attempt to convert to counties
            if coverage_type == 'zip':
                service_zip_codes = elementor_payload.get('service_zip_codes', '')
                
                if service_zip_codes:
                    logger.info(f"🔄 Converting service ZIP codes to counties for vendor application")
                    
                    county_conversion = convert_service_areas_to_counties(service_zip_codes)
                    
                    if county_conversion['conversion_success']:
                        counties_str = ', '.join(county_conversion['counties'])
                        
                        # Add county information to GHL payload
                        service_counties_field = field_mapper.get_ghl_field_details("service_counties")
                        
                        if not final_ghl_payload.get("customFields"):
                            final_ghl_payload["customFields"] = []
                        
                        if service_counties_field and service_counties_field.get("id"):
                            # Check if field already exists
                            field_exists = any(cf["id"] == service_counties_field["id"] for cf in final_ghl_payload["customFields"])
                            if not field_exists:
                                final_ghl_payload["customFields"].append({
                                    "id": service_counties_field["id"],
                                    "value": counties_str
                                })
                                logger.info(f"✅ Added service_counties to GHL payload: {counties_str}")
                        
                        logger.info(f"✅ Vendor Application: Converted {county_conversion['successful_conversions']}/{county_conversion['total_zip_codes']} ZIP codes")
                        logger.info(f"📍 Vendor Application: Service counties: {', '.join(county_conversion['counties'])}")
                        
                        # Store the county conversion result in the elementor_payload for database storage
                        elementor_payload['_converted_counties'] = county_conversion['counties']
                    else:
                        logger.warning(f"⚠️ Vendor Application: Could not convert any ZIP codes to counties")
            
            # Log what coverage data we have for debugging
            logger.info(f"🌍 Vendor coverage processing complete:")
            logger.info(f"   Coverage Type: {coverage_type}")
            logger.info(f"   Coverage Area: {elementor_payload.get('service_coverage_area', 'Not specified')}")
            logger.info(f"   Coverage States: {elementor_payload.get('coverage_states', [])}")
            logger.info(f"   Coverage Counties: {elementor_payload.get('coverage_counties', [])}")
            logger.info(f"   Service ZIP Codes: {elementor_payload.get('service_zip_codes', 'Not specified')}")
        
        # Ensure email is present and normalized
        if not final_ghl_payload.get("email"):
            logger.error(f"❌ No email provided in payload for form {form_identifier}")
            raise HTTPException(status_code=400, detail="Email is required for processing this form.")

        final_ghl_payload["email"] = final_ghl_payload["email"].lower().strip()

        logger.info(f"🎯 Prepared Final GHL Payload for '{form_identifier}': {json.dumps(final_ghl_payload, indent=2)}")

        # --- GHL API OPERATIONS: Create or Update Contact ---
        existing_ghl_contact = None
        final_ghl_contact_id = None
        operation_successful = False
        action_taken = ""
        api_response_details = None

        # Search for existing contact by email AND phone
        search_email = final_ghl_payload["email"]
        search_phone = final_ghl_payload.get("phone", "")
        
        logger.info(f"🔍 Searching for existing contact with email: {search_email}")
        if search_phone:
            logger.info(f"🔍 Also checking for phone duplicates: {search_phone}")
        
        # Search by email first
        email_search_results = ghl_api_client.search_contacts(query=search_email, limit=10)
        phone_search_results = []
        
        # Search by phone if provided
        if search_phone:
            phone_search_results = ghl_api_client.search_contacts(query=search_phone, limit=10)
        
        # Combine and deduplicate results
        all_search_results = email_search_results or []
        if phone_search_results:
            existing_ids = {contact.get('id') for contact in all_search_results}
            for phone_contact in phone_search_results:
                if phone_contact.get('id') not in existing_ids:
                    all_search_results.append(phone_contact)
        
        if all_search_results:
            logger.info(f"📋 Search returned {len(all_search_results)} potential matches")
            
            for i, contact_result in enumerate(all_search_results):
                contact_id = contact_result.get('id')
                contact_email = contact_result.get('email', '').lower()
                contact_phone = contact_result.get('phone', '')
                
                logger.info(f"  [{i}] Contact: {contact_id} - Email: {contact_email}, Phone: {contact_phone}")
                
                # Check for exact email match
                if contact_email == search_email:
                    existing_ghl_contact = contact_result
                    logger.info(f"✅ Found exact EMAIL match: {existing_ghl_contact.get('id')}")
                    break
                    
                # Check for phone match with normalization
                elif search_phone and contact_phone:
                    # Normalize phone numbers for comparison (remove non-digits)
                    search_phone_normalized = ''.join(filter(str.isdigit, search_phone))
                    contact_phone_normalized = ''.join(filter(str.isdigit, contact_phone))
                    
                    if search_phone_normalized == contact_phone_normalized:
                        existing_ghl_contact = contact_result
                        logger.info(f"✅ Found PHONE match: {existing_ghl_contact.get('id')}")
                        break
        else:
            logger.info("📋 No search results returned for email or phone - contact appears to be new")

        # Create or update contact
        if existing_ghl_contact:
            # UPDATE EXISTING CONTACT
            final_ghl_contact_id = existing_ghl_contact["id"]
            action_taken = "updated"
            logger.info(f"🔄 Updating existing GHL contact {final_ghl_contact_id}")
            
            update_payload = final_ghl_payload.copy()
            update_payload.pop("locationId", None) 
            update_payload.pop("id", None)

            operation_successful = ghl_api_client.update_contact(final_ghl_contact_id, update_payload)
            if not operation_successful:
                api_response_details = "Update call returned false - check GHL API logs"
                logger.error(f"❌ Failed to update GHL contact {final_ghl_contact_id}")
        else:
            # CREATE NEW CONTACT
            action_taken = "created"
            logger.info(f"➕ Creating new GHL contact for email {final_ghl_payload.get('email')}")
            
            created_contact_response = ghl_api_client.create_contact(final_ghl_payload)
            
            if created_contact_response and isinstance(created_contact_response, dict):
                # Handle both v1 and v2 API response formats
                # v2 API returns {'contact': {'id': '...'}} while v1 returns {'id': '...'}
                contact_data = created_contact_response.get("contact", created_contact_response)
                contact_id = contact_data.get("id")
                
                if not created_contact_response.get("error") and contact_id:
                    final_ghl_contact_id = contact_id
                    operation_successful = True
                    logger.info(f"✅ Successfully created new GHL contact {final_ghl_contact_id}")
                else:
                    logger.error(f"❌ GHL contact creation failed: {created_contact_response}")
                    api_response_details = created_contact_response
            else:
                logger.error(f"❌ Unexpected response from GHL API: {created_contact_response}")
                api_response_details = {"error": True, "unexpected_response": created_contact_response}

        # Handle success/failure and log results
        processing_time = round(time.time() - start_time, 3)
        
        if operation_successful and final_ghl_contact_id:
            logger.info(f"✅ Successfully {action_taken} GHL contact {final_ghl_contact_id} for form '{form_identifier}' in {processing_time}s")
            
            # Log successful activity to database
            simple_db_instance.log_activity(
                event_type=f"clean_webhook_{action_taken}",
                event_data={
                    "form": form_identifier,
                    "form_type": form_config.get("form_type"),
                    "ghl_contact_id": final_ghl_contact_id,
                    "elementor_payload_keys": list(elementor_payload.keys()),
                    "service_category": form_config.get("service_category"),
                    "processing_time_seconds": processing_time,
                    "validation_warnings": validation_result.get("warnings", []),
                    "custom_fields_sent": len(final_ghl_payload.get("customFields", []))
                },
                lead_id=final_ghl_contact_id, 
                success=True
            )
            
            # Initialize account_id for all form types (not just vendor applications)
            account_record = simple_db_instance.get_account_by_ghl_location_id(AppConfig.GHL_LOCATION_ID)
            if not account_record:
                account_id = simple_db_instance.create_account(
                    ghl_location_id=AppConfig.GHL_LOCATION_ID,
                    company_name="DocksidePros",
                    industry="Marine Services"
                )
            else:
                account_id = account_record["id"]
            
            # Create vendor record in database
            if form_config.get("form_type") == "vendor_application" and final_ghl_contact_id:
                try:
                    # Extract vendor data from payload
                    vendor_company_name = elementor_payload.get('vendor_company_name', '')
                    vendor_first_name = elementor_payload.get('firstName', '')
                    vendor_last_name = elementor_payload.get('lastName', '')
                    vendor_email = elementor_payload.get('email', '')
                    vendor_phone = elementor_payload.get('phone', '')
                    
                    # Process service categories - NEW LOGIC for primary + additional structure
                    primary_service_category = elementor_payload.get('primary_service_category', '')
                    service_categories = elementor_payload.get('service_categories', '')
                    
                    # Build final categories list (primary + additional up to 3 total)
                    categories_list = []
                    if primary_service_category:
                        categories_list.append(primary_service_category)
                        logger.info(f"📋 Primary service category: {primary_service_category}")
                    
                    if service_categories:
                        # Parse additional categories from service_categories field
                        additional_categories = [s.strip() for s in service_categories.split(',') if s.strip() and s.strip() != primary_service_category]
                        categories_list.extend(additional_categories[:2])  # Max 2 additional
                        logger.info(f"📋 Service categories: {service_categories}")
                        logger.info(f"📋 Final categories list: {categories_list}")
                    
                    # Create JSON for database storage
                    if categories_list:
                        service_categories_json = json.dumps(categories_list)
                        logger.info(f"📋 Final service categories JSON: {service_categories_json}")
                    else:
                        # Fallback if no categories provided
                        service_categories_json = json.dumps(['General Services'])
                        logger.warning(f"📋 No categories provided, using fallback")
                    
                    # CRITICAL FIX: Extract specific services offered using Level 3 when available
                    # First, check for Level 3 services (most specific)
                    primary_level3_services_raw = elementor_payload.get('primary_level3_services', {})
                    additional_level3_services_raw = elementor_payload.get('additional_level3_services', {})
                    
                    # Parse Level 3 services - handle both JSON strings and dict/list formats
                    primary_level3_services = {}
                    additional_level3_services = {}
                    
                    # Parse primary Level 3 services
                    if primary_level3_services_raw:
                        if isinstance(primary_level3_services_raw, str):
                            try:
                                primary_level3_services = json.loads(primary_level3_services_raw)
                                logger.info(f"📋 Parsed primary Level 3 services from JSON string")
                            except json.JSONDecodeError:
                                logger.warning(f"⚠️ Failed to parse primary Level 3 services JSON: {primary_level3_services_raw}")
                                # Try to treat as comma-separated list
                                primary_level3_services = {"services": [s.strip() for s in primary_level3_services_raw.split(',') if s.strip()]}
                        elif isinstance(primary_level3_services_raw, dict):
                            primary_level3_services = primary_level3_services_raw
                        elif isinstance(primary_level3_services_raw, list):
                            # If it's a flat list, convert to dict format
                            primary_level3_services = {"services": primary_level3_services_raw}
                    
                    # Parse additional Level 3 services
                    if additional_level3_services_raw:
                        if isinstance(additional_level3_services_raw, str):
                            try:
                                additional_level3_services = json.loads(additional_level3_services_raw)
                                logger.info(f"📋 Parsed additional Level 3 services from JSON string")
                            except json.JSONDecodeError:
                                logger.warning(f"⚠️ Failed to parse additional Level 3 services JSON: {additional_level3_services_raw}")
                                # Try to treat as comma-separated list
                                additional_level3_services = {"services": [s.strip() for s in additional_level3_services_raw.split(',') if s.strip()]}
                        elif isinstance(additional_level3_services_raw, dict):
                            additional_level3_services = additional_level3_services_raw
                        elif isinstance(additional_level3_services_raw, list):
                            # If it's a flat list, convert to dict format
                            additional_level3_services = {"services": additional_level3_services_raw}
                    
                    services_list = []
                    
                    # Collect all Level 3 services
                    if primary_level3_services and isinstance(primary_level3_services, dict):
                        for subcategory, level3_list in primary_level3_services.items():
                            if isinstance(level3_list, list):
                                services_list.extend(level3_list)
                                logger.info(f"📋 Level 3 services for {subcategory}: {level3_list}")
                            elif isinstance(level3_list, str):
                                # Handle case where value is a string instead of list
                                services_list.extend([s.strip() for s in level3_list.split(',') if s.strip()])
                                logger.info(f"📋 Level 3 services for {subcategory} (from string): {level3_list}")
                    
                    if additional_level3_services and isinstance(additional_level3_services, dict):
                        for subcategory, level3_list in additional_level3_services.items():
                            if isinstance(level3_list, list):
                                services_list.extend(level3_list)
                                logger.info(f"📋 Additional Level 3 services for {subcategory}: {level3_list}")
                            elif isinstance(level3_list, str):
                                # Handle case where value is a string instead of list
                                services_list.extend([s.strip() for s in level3_list.split(',') if s.strip()])
                                logger.info(f"📋 Additional Level 3 services for {subcategory} (from string): {level3_list}")
                    
                    # If no Level 3 services, fall back to services_provided field (Level 2 or combined)
                    if not services_list:
                        services_provided = elementor_payload.get('services_provided', '')
                        if services_provided:
                            # These are the Level 2 services or combined services
                            services_list = [s.strip() for s in services_provided.split(',') if s.strip()]
                            logger.info(f"📋 Using Level 2 services from services_provided: {services_list}")
                        else:
                            # If still no services, try to use primary_services and additional_services (Level 2)
                            primary_services = elementor_payload.get('primary_services', [])
                            additional_services = elementor_payload.get('additional_services', [])
                            
                            if isinstance(primary_services, list):
                                services_list.extend(primary_services)
                            elif isinstance(primary_services, str) and primary_services:
                                services_list.extend([s.strip() for s in primary_services.split(',') if s.strip()])
                            
                            if isinstance(additional_services, list):
                                services_list.extend(additional_services)
                            elif isinstance(additional_services, str) and additional_services:
                                services_list.extend([s.strip() for s in additional_services.split(',') if s.strip()])
                            
                            if services_list:
                                logger.info(f"📋 Using Level 2 services from primary/additional: {services_list}")
                    
                    # Store the final services list
                    if services_list:
                        services_offered_json = json.dumps(services_list)
                        logger.info(f"✅ Final services offered for vendor: {services_list}")
                    else:
                        services_offered_json = json.dumps([])
                        logger.warning(f"⚠️ No specific services provided for vendor")
                    
                    # Extract coverage type and coverage areas
                    coverage_type = elementor_payload.get('coverage_type', 'county')
                    logger.info(f"📋 Coverage type: {coverage_type}")
                    
                    # Handle coverage states (for state-level coverage)
                    coverage_states = elementor_payload.get('coverage_states', [])
                    if isinstance(coverage_states, list):
                        coverage_states_json = json.dumps(coverage_states)
                        logger.info(f"📋 Coverage states: {coverage_states}")
                    elif isinstance(coverage_states, str) and coverage_states:
                        # If it's a comma-separated string
                        states_list = [s.strip() for s in coverage_states.split(',') if s.strip()]
                        coverage_states_json = json.dumps(states_list)
                        logger.info(f"📋 Coverage states parsed from string: {states_list}")
                    else:
                        coverage_states_json = json.dumps([])
                    
                    # Handle coverage data based on coverage type
                    service_coverage_area = elementor_payload.get('service_coverage_area', '')
                    coverage_counties_json = json.dumps([])
                    
                    # Process coverage data based on type
                    if coverage_type == 'state':
                        # Already handled above in coverage_states
                        pass
                    
                    elif coverage_type == 'county':
                        # Handle county coverage from the widget
                        coverage_counties = elementor_payload.get('coverage_counties', [])
                        if isinstance(coverage_counties, list) and coverage_counties:
                            coverage_counties_json = json.dumps(coverage_counties)
                            logger.info(f"📋 Coverage counties: {coverage_counties}")
                        elif isinstance(coverage_counties, str) and coverage_counties:
                            # Parse comma-separated counties
                            counties_list = [c.strip() for c in coverage_counties.split(',') if c.strip()]
                            coverage_counties_json = json.dumps(counties_list)
                            logger.info(f"📋 Parsed coverage counties: {counties_list}")
                    
                    elif coverage_type == 'zip':
                        # Handle ZIP code coverage
                        service_zip_codes = elementor_payload.get('service_zip_codes', '')
                        if service_zip_codes:
                            # Check if we have converted counties from earlier ZIP conversion
                            converted_counties = elementor_payload.get('_converted_counties', [])
                            if converted_counties:
                                coverage_counties_json = json.dumps(converted_counties)
                                logger.info(f"📋 Using converted counties from ZIP codes: {converted_counties}")
                            else:
                                # Store ZIP codes as coverage
                                if isinstance(service_zip_codes, str):
                                    zips_list = [z.strip() for z in service_zip_codes.split(',') if z.strip()]
                                    coverage_counties_json = json.dumps(zips_list)
                                    logger.info(f"📋 Storing ZIP codes as coverage: {zips_list}")
                    
                    elif coverage_type in ['global', 'national']:
                        # For global/national, we store empty counties but note in service_coverage_area
                        coverage_counties_json = json.dumps([])
                        logger.info(f"🌍 {coverage_type.title()} coverage - no specific counties")
                    
                    logger.info(f"🗺️ Final coverage data:")
                    logger.info(f"   Coverage Type: {coverage_type}")
                    logger.info(f"   Coverage States: {coverage_states_json}")
                    logger.info(f"   Coverage Counties: {coverage_counties_json}")
                    logger.info(f"   Service Categories: {service_categories_json}")
                    logger.info(f"   Services Offered: {services_offered_json}")
                    
                    # Note: account_id is already initialized above for all form types
                    
                    # Check if vendor already exists
                    existing_vendor = simple_db_instance.get_vendor_by_email_and_account(vendor_email, account_id)
                    
                    if existing_vendor:
                        logger.info(f"📋 Vendor already exists: {existing_vendor['id']}")
                        vendor_id = existing_vendor['id']
                        
                        # Update existing vendor with new information
                        try:
                            # Update service categories and coverage if provided
                            update_data = {}
                            if service_categories_json != json.dumps(['General Services']):
                                update_data['service_categories'] = service_categories_json
                            if coverage_counties_json != json.dumps([]):
                                update_data['coverage_counties'] = coverage_counties_json
                            
                            if update_data:
                                # You may need to add an update_vendor method to simple_db_instance
                                logger.info(f"🔄 Would update vendor {vendor_id} with: {update_data}")
                        except Exception as update_error:
                            logger.warning(f"⚠️ Failed to update existing vendor: {update_error}")
                    else:
                        # Create new vendor record
                        primary_category = elementor_payload.get('primary_service_category', '')
                        taking_work = elementor_payload.get('taking_new_work', 'Yes') == 'Yes'
                        
                        vendor_id = simple_db_instance.create_vendor(
                            account_id=account_id,
                            name=f"{vendor_first_name} {vendor_last_name}".strip(),
                            email=vendor_email,
                            company_name=vendor_company_name,
                            phone=vendor_phone,
                            ghl_contact_id=final_ghl_contact_id,
                            status='pending',  # Start as pending until approved
                            service_categories=service_categories_json,  # Categories like "Boat Maintenance"
                            services_offered=services_offered_json,      # Specific services like "Boat Detailing"
                            coverage_type=coverage_type,                 # state, county, zip, etc.
                            coverage_states=coverage_states_json,        # ["FL", "GA"] for state coverage
                            coverage_counties=coverage_counties_json,    # Counties or ZIP codes
                            primary_service_category=primary_category,   # Primary category from multi-step flow
                            taking_new_work=taking_work                  # Boolean for taking new work
                        )
                        logger.info(f"✅ Created vendor record: {vendor_id}")
                        logger.info(f"   Company: {vendor_company_name}")
                        logger.info(f"   Name: {vendor_first_name} {vendor_last_name}")
                        logger.info(f"   Email: {vendor_email}")
                        logger.info(f"   Services: {service_categories_json}")
                        logger.info(f"   Coverage: {coverage_counties_json}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to create vendor record: {str(e)}")
                    logger.error(f"   Error type: {type(e).__name__}")
                    logger.error(f"   Service categories selected: {elementor_payload.get('service_categories_selected', 'NOT_FOUND')}")
                    logger.error(f"   Vendor company name: {elementor_payload.get('vendor_company_name', 'NOT_FOUND')}")
                    logger.error(f"   Service zip codes: {elementor_payload.get('service_zip_codes', 'NOT_FOUND')}")
                    
                    # Log the full elementor payload for debugging
                    logger.error(f"   Full payload keys: {list(elementor_payload.keys())}")
                    
                    # Continue processing even if vendor record fails - don't break the webhook
                    pass
            
            # Trigger background tasks based on form type
            if form_config.get("requires_immediate_routing"):
                # FIXED: No more pre-selection - vendor assignment happens AFTER lead creation
                # Trigger lead routing workflow (vendor assignment will happen inside)
                await trigger_clean_lead_routing_workflow(
                    ghl_contact_id=final_ghl_contact_id,
                    form_identifier=form_identifier,
                    form_config=form_config,
                    form_data=elementor_payload
                )

            
            # NOTE: Opportunity creation now handled in background task for client leads
            logger.info("ℹ️ Opportunity creation will be handled by background task if needed")
            
            # Log successful processing in background
            logger.info(f"✅ Background processing completed successfully for form '{form_identifier}'")
            logger.info(f"   - GHL contact {final_ghl_contact_id} {action_taken}")
            logger.info(f"   - Processing time: {processing_time}s")
            logger.info(f"   - Custom fields processed: {len(final_ghl_payload.get('customFields', []))}")
        else:
            # Operation failed
            error_message = f"Failed to {action_taken} GHL contact for form '{form_identifier}'"
            logger.error(f"❌ {error_message}. API Response: {api_response_details}")
            
            simple_db_instance.log_activity(
                event_type="clean_webhook_ghl_failure",
                event_data={
                    "form": form_identifier,
                    "form_type": form_config.get("form_type"),
                    "error_details": api_response_details,
                    "action_attempted": action_taken,
                    "elementor_payload_keys": list(elementor_payload.keys()),
                    "processing_time_seconds": processing_time
                },
                success=False,
                error_message=f"GHL API interaction failed during contact {action_taken}"
            )
            
            logger.error(f"❌ Background processing failed: GHL API interaction failed")

    except Exception as e:
        processing_time = round(time.time() - start_time, 3)
        logger.exception(f"💥 Critical error in background processing for form '{form_identifier}' after {processing_time}s: {e}")
        simple_db_instance.log_activity(
            event_type="clean_webhook_exception",
            event_data={
                "form": form_identifier,
                "processing_time_seconds": processing_time,
                "error_class": e.__class__.__name__
            },
            success=False,
            error_message=str(e)
        )
        # Don't raise exceptions in background tasks - just log them

async def assign_vendor_to_lead(
    lead_id: str,
    account_id: str,
    opportunity_id: str,
    specific_service: str,
    service_county: str,
    service_state: str,
    service_zip: str,
    priority: str = "normal"
) -> Dict[str, Any]:
    """
    Assign vendor to lead AFTER lead creation with opportunity_id.
    Returns assignment result dictionary.
    """
    try:
        logger.info(f"🎯 Starting vendor assignment for lead {lead_id}")
        logger.info(f"   Service: {specific_service}")
        logger.info(f"   Location: {service_county}, {service_state} {service_zip}")
        
        # Find matching vendors
        matching_vendors = lead_routing_service.find_matching_vendors(
            account_id=account_id,
            service_category=specific_service.split(" - ")[0] if " - " in specific_service else specific_service,
            zip_code=service_zip,
            priority=priority,
            specific_service=specific_service
        )
        
        if not matching_vendors:
            logger.warning(f"⚠️ No vendors found for {specific_service} in {service_county}, {service_state}")
            return {"success": False, "reason": "no_vendors_found"}
        
        logger.info(f"✅ Found {len(matching_vendors)} matching vendors")
        
        # Select vendor using configured algorithm
        selected_vendor = lead_routing_service.select_vendor_from_pool(
            matching_vendors, account_id
        )
        
        if not selected_vendor:
            logger.error(f"❌ Vendor selection failed")
            return {"success": False, "reason": "selection_failed"}
        
        vendor_id = selected_vendor['id']
        vendor_ghl_user_id = selected_vendor.get('ghl_user_id')
        vendor_name = selected_vendor.get('company_name', selected_vendor.get('name', 'Unknown'))
        
        logger.info(f"🎯 Selected vendor: {vendor_name} (ID: {vendor_id}, GHL User: {vendor_ghl_user_id})")
        
        # Update lead with vendor assignment
        if not simple_db_instance.assign_lead_to_vendor(lead_id, vendor_id):
            return {"success": False, "reason": "database_update_failed"}
        
        # Update GHL opportunity
        if vendor_ghl_user_id and opportunity_id:
            try:
                ghl_api = OptimizedGoHighLevelAPI(
                    private_token=AppConfig.GHL_PRIVATE_TOKEN,
                    location_id=AppConfig.GHL_LOCATION_ID,
                    agency_api_key=AppConfig.GHL_AGENCY_API_KEY
                )
                
                update_data = {
                    'assignedTo': vendor_ghl_user_id,
                    'pipelineId': AppConfig.PIPELINE_ID,
                    'pipelineStageId': AppConfig.NEW_LEAD_STAGE_ID
                }
                
                if ghl_api.update_opportunity(opportunity_id, update_data):
                    logger.info(f"✅ Assigned GHL opportunity {opportunity_id} to {vendor_name}")
                    return {"success": True, "vendor_id": vendor_id, "vendor_name": vendor_name}
                else:
                    logger.error(f"❌ Failed to update GHL opportunity")
                    return {"success": False, "reason": "ghl_update_failed", "vendor_id": vendor_id}
            except Exception as e:
                logger.error(f"❌ Error updating GHL: {e}")
                return {"success": False, "reason": "ghl_error", "error": str(e)}
        else:
            logger.warning(f"⚠️ Missing GHL User ID or opportunity ID")
            return {"success": False, "reason": "missing_ids"}
            
    except Exception as e:
        logger.error(f"❌ Error in vendor assignment: {e}")
        return {"success": False, "reason": "process_error", "error": str(e)}

async def trigger_clean_lead_routing_workflow(
    ghl_contact_id: str, 
    form_identifier: str, 
    form_config: Dict[str, Any],
    form_data: Dict[str, Any],
    selected_vendor_id: Optional[str] = None,      # Pre-selected vendor ID (deprecated)
    selected_vendor_ghl_user: Optional[str] = None  # Pre-selected vendor GHL user ID (deprecated)
):
    """
    FIXED: Clean background task for lead routing with correct order of operations
    1. Create opportunity FIRST
    2. Create lead WITH opportunity_id
    3. Trigger vendor assignment
    """
    logger.info(f"🚀 CLEAN BACKGROUND TASK: Processing lead for contact {ghl_contact_id} from form '{form_identifier}'")
    
    try:
        # Get account information
        account = simple_db_instance.get_account_by_ghl_location_id(AppConfig.GHL_LOCATION_ID)
        if not account:
            logger.warning(f"⚠️ No account found for GHL Location ID: {AppConfig.GHL_LOCATION_ID}")
            account_id = simple_db_instance.create_account(
                company_name="Digital Marine LLC",
                industry="marine",
                ghl_location_id=AppConfig.GHL_LOCATION_ID,
                ghl_private_token=AppConfig.GHL_PRIVATE_TOKEN
            )
        else:
            account_id = account["id"]
 
        # Direct service classification (NO AI)
        service_category = form_config.get("service_category", "No Category")
        
        # Extract customer data directly from form (NO PHONE)
        customer_data = {
            "name": f"{form_data.get('firstName', '')} {form_data.get('lastName', '')}".strip(),
            "email": form_data.get("email", ""),
            "phone": form_data.get("phone", "")
        }
        
        # FIXED CODE - Use ServiceDictionaryMapper like contact creation
        mapper = ServiceDictionaryMapper()
        mapping_result = mapper.map_payload_to_service(form_data)
        mapped_payload = mapping_result.get('standardized_fields', {})
        logger.info(f"🔄 Lead creation using ServiceDictionaryMapper. Original keys: {list(form_data.keys())}, Mapped keys: {list(mapped_payload.keys())}")
        
        # Create service_details from ALL mapped fields (preserves all form data)
        service_details = {}
        
        # Standard fields that have dedicated database columns (don't duplicate in service_details)
        standard_lead_fields = {
            "firstName", "lastName", "email", "phone", "primary_service_category",
            "customer_zip_code", "specific_service_requested"
        }
        
        # Store ALL other fields in service_details (preserves all 16 form types)
        for field_key, field_value in mapped_payload.items():
            # Skip empty values and standard fields (those go in dedicated columns)
            if field_value == "" or field_value is None or field_key in standard_lead_fields:
                continue
                
            service_details[field_key] = field_value
            
        # Add form metadata (NO PHONE)
        service_details.update({
            "form_source": form_identifier,
            "submission_time": form_data.get("Time", ""),
            "submission_date": form_data.get("Date", ""),
            "processing_method": "direct_mapping"
        })
        
        logger.info(f"📦 Created service_details with {len(service_details)} fields from mapped payload")

        # FIXED: Convert ZIP to county for lead routing (CRITICAL FIX FOR VENDOR MATCHING)
        zip_code = mapped_payload.get("zip_code_of_service", "")
        service_county = ""
        service_state = ""
        
        if zip_code and len(zip_code) == 5 and zip_code.isdigit():
            logger.info(f"🗺️ Converting ZIP {zip_code} to county for lead routing")
            location_data = location_service.zip_to_location(zip_code)
            
            if not location_data.get('error'):
                county = location_data.get('county', '')
                state = location_data.get('state', '')
                if county and state:
                    service_county = f"{county}, {state}"  # Format: "Miami-Dade, FL"
                    service_state = state
                    logger.info(f"✅ ZIP {zip_code} → {service_county}")
                else:
                    logger.warning(f"⚠️ ZIP {zip_code} conversion incomplete: county={county}, state={state}")
            else:
                logger.warning(f"⚠️ Could not convert ZIP {zip_code}: {location_data['error']}")
        else:
            logger.warning(f"⚠️ Invalid ZIP code format: '{zip_code}' - service_county will remain NULL")

        # Get service values from mapped payload (mapped from GHL custom fields)
        specific_service_requested = mapped_payload.get("specific_service_needed", "")  # From GHL field FT85QGi0tBq1AfVGNJ9v
        
        # If no Level 3 specific service, extract Level 2 from form identifier
        if not specific_service_requested:
            # Try to get the Level 2 subcategory from form identifier
            level2_service = get_specific_service_from_form(form_identifier)
            if level2_service:
                specific_service_requested = level2_service
                logger.info(f"📝 Using Level 2 subcategory from form identifier: {specific_service_requested}")
            else:
                # Last resort: use the form identifier itself as a readable service name
                specific_service_requested = form_identifier.replace("_", " ").title()
                logger.info(f"📝 Using form identifier as Level 2: {specific_service_requested}")
        
        # STEP 1: Create opportunity FIRST (before lead creation)
        opportunity_id = None
        form_type = form_config.get("form_type", "unknown")
        if form_type == "client_lead" or form_type == "emergency_service":
            if AppConfig.PIPELINE_ID and AppConfig.NEW_LEAD_STAGE_ID:
                logger.info(f"📈 Creating opportunity FIRST for {service_category} lead")
                
                ghl_api_client = OptimizedGoHighLevelAPI(
                    private_token=AppConfig.GHL_PRIVATE_TOKEN,
                    location_id=AppConfig.GHL_LOCATION_ID,
                    agency_api_key=AppConfig.GHL_AGENCY_API_KEY
                )
                
                customer_name = customer_data["name"]
                location_info = mapped_payload.get("zip_code_of_service", "Unknown Location")
                
                opportunity_data = {
                    'contactId': ghl_contact_id,
                    'pipelineId': AppConfig.PIPELINE_ID,
                    'pipelineStageId': AppConfig.NEW_LEAD_STAGE_ID,
                    'name': f"{customer_name} - {service_category}",
                    'monetaryValue': 0,
                    'status': 'open',
                    'source': f"{form_identifier} (DSP)",
                    'locationId': AppConfig.GHL_LOCATION_ID,
                    # NOTE: assignedTo will be set AFTER vendor selection
                }
                
                opportunity_response = ghl_api_client.create_opportunity(opportunity_data)
                
                # Handle both v1 and v2 API response formats
                if opportunity_response:
                    if opportunity_response.get('opportunity', {}).get('id'):
                        # v2 API format - opportunity is nested
                        opportunity_id = opportunity_response['opportunity']['id']
                        logger.info(f"✅ Created opportunity FIRST (v2 format): {opportunity_id}")
                    elif opportunity_response.get('id'):
                        # v1 API format - id at root level
                        opportunity_id = opportunity_response['id']
                        logger.info(f"✅ Created opportunity FIRST (v1 format): {opportunity_id}")
                    else:
                        logger.error(f"❌ Unexpected opportunity response format: {opportunity_response}")
                else:
                    logger.error(f"❌ Failed to create opportunity: No response received")
            else:
                logger.warning("⚠️ Pipeline not configured - skipping opportunity creation")
        
        # STEP 2: Create lead WITH opportunity_id
        conn = None
        lead_id = None
        try:
            lead_id = str(uuid.uuid4())
            conn = simple_db_instance._get_conn()
            cursor = conn.cursor()
            
            # FIXED: INSERT using actual database schema field names (26 fields)
            cursor.execute('''
            INSERT INTO leads (
                id, account_id, ghl_contact_id, ghl_opportunity_id, customer_name,
                customer_email, customer_phone, primary_service_category, specific_service_requested,
                customer_zip_code, service_county, service_state, vendor_id, 
                assigned_at, status, priority, source, service_details, 
                service_zip_code, service_city, specific_services,
                service_complexity, estimated_duration, requires_emergency_response, 
                classification_confidence, classification_reasoning
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            lead_id,                                                      # id
            account_id,                                                   # account_id  
            ghl_contact_id,                                               # ghl_contact_id
            opportunity_id,                                               # ghl_opportunity_id (NOW WE HAVE IT!)
            customer_data.get("name", ""),                                # customer_name
            customer_data.get("email", "").lower().strip() if customer_data.get("email") else None,  # customer_email
            customer_data.get("phone", ""),                               # customer_phone
            service_category,                                             # primary_service_category (from form_config)
            specific_service_requested,                                   # specific_service_requested (from GHL field)
            zip_code,                                                     # customer_zip_code
            service_county,                                               # service_county
            service_state,                                                # service_state
            None,                                                         # vendor_id (NULL initially)
            None,                                                         # assigned_at (NULL initially)
            "pending_assignment" if opportunity_id else "unassigned",    # status
            "normal",                                                     # priority  
            f"{form_identifier} (DSP)",                                   # source
            json.dumps(service_details),                                  # service_details
            zip_code,                                                     # service_zip_code 
            "",                                                           # service_city
            "[]",                                                         # specific_services (JSON array)
            "simple",                                                     # service_complexity
            "medium",                                                     # estimated_duration
            False,                                                        # requires_emergency_response
            1.0,                                                          # classification_confidence
            "Direct form mapping"                                         # classification_reasoning
        ))
            
            conn.commit()
            logger.info(f"✅ Lead created with ID: {lead_id}")
            
        except Exception as e:
            logger.error(f"❌ Lead creation error: {e}")
            raise
        finally:
            if conn:
                conn.close()
        
        # STEP 3: Trigger vendor assignment (if we have opportunity and required data)
        if opportunity_id and specific_service_requested and (service_county or zip_code):
            logger.info(f"🎯 Triggering vendor assignment for lead {lead_id}")
            logger.info(f"   Opportunity: {opportunity_id}")
            logger.info(f"   Service: {specific_service_requested}")
            logger.info(f"   Location: {service_county or zip_code}")
            
            # Call the vendor assignment function
            assignment_result = await assign_vendor_to_lead(
                lead_id=lead_id,
                account_id=account_id,
                opportunity_id=opportunity_id,
                specific_service=specific_service_requested,
                service_county=service_county,
                service_state=service_state,
                service_zip=zip_code,
                priority=form_config.get("priority", "normal")
            )
            
            if assignment_result['success']:
                logger.info(f"✅ Vendor assignment successful: {assignment_result.get('vendor_name')}")
                
                # Log successful vendor assignment
                simple_db_instance.log_activity(
                    event_type="vendor_assignment_complete",
                    event_data={
                        "lead_id": lead_id,
                        "opportunity_id": opportunity_id,
                        "vendor_id": assignment_result.get('vendor_id'),
                        "vendor_name": assignment_result.get('vendor_name'),
                        "service": specific_service_requested,
                        "location": f"{service_county}, {service_state}"
                    },
                    lead_id=lead_id,
                    success=True
                )
            else:
                logger.warning(f"⚠️ Vendor assignment failed: {assignment_result.get('reason')}")
                
                # Log failed vendor assignment
                simple_db_instance.log_activity(
                    event_type="vendor_assignment_failed",
                    event_data={
                        "lead_id": lead_id,
                        "opportunity_id": opportunity_id,
                        "reason": assignment_result.get('reason'),
                        "error": assignment_result.get('error', '')
                    },
                    lead_id=lead_id,
                    success=False,
                    error_message=assignment_result.get('reason')
                )
        else:
            logger.warning(f"⚠️ Cannot assign vendor - missing required data:")
            logger.warning(f"   Opportunity ID: {opportunity_id}")
            logger.warning(f"   Service: {specific_service_requested}")
            logger.warning(f"   Location: {service_county or zip_code}")
            
            # Notify admin about vendor assignment failure
            if not opportunity_id:
                error_reason = "No opportunity ID available"
            elif not specific_service_requested:
                error_reason = "No specific service identified"
            elif not (service_county or zip_code):
                error_reason = "No location information"
            else:
                error_reason = "Unknown reason"
            
            # Log the failure for admin notification
            simple_db_instance.log_activity(
                event_type="vendor_assignment_skipped",
                event_data={
                    "lead_id": lead_id,
                    "reason": error_reason,
                    "opportunity_id": opportunity_id,
                    "service": specific_service_requested,
                    "location": service_county or zip_code
                },
                lead_id=lead_id,
                success=False,
                error_message=f"Vendor assignment prerequisites not met: {error_reason}"
            )
            
            # TODO: Send notification to GHL admin user
            # This would typically be done via GHL task/note creation or email
        
        # Note: Vendor assignment now happens in assign_vendor_to_lead function above
        # This ensures proper order: opportunity -> lead -> vendor assignment
        
        # Log successful routing
        simple_db_instance.log_activity(
            event_type="clean_lead_routing_completed",
            event_data={
                "ghl_location_id": AppConfig.GHL_LOCATION_ID,
                "ghl_contact_id": ghl_contact_id,
                "lead_id": lead_id,
                "form_identifier": form_identifier,
                "form_type": form_type,
                "priority": priority,
                "service_category": service_category,
                "processing_method": "direct_only_no_ai",
                "timestamp": time.time()
            },
            lead_id=ghl_contact_id,
            success=True
        )
        
        logger.info(f"✅ Clean lead routing completed for {ghl_contact_id} with priority: {priority}")
        
    except Exception as e:
        logger.error(f"❌ Error in clean lead routing workflow for {ghl_contact_id}: {e}")
        simple_db_instance.log_activity(
            event_type="clean_lead_routing_error",
            event_data={
                "ghl_contact_id": ghl_contact_id,
                "form_identifier": form_identifier,
                "error": str(e)
            },
            lead_id=ghl_contact_id,
            success=False,
            error_message=str(e)
        )

async def notify_admin_of_unmatched_lead(lead_data: Dict[str, Any], ghl_contact_id: str, service_category: str, location: str):
    """
    Notify admin when no vendors are found for a lead
    Direct notification - NO AI processing
    """
    try:
        # Use optimized v2 API for better performance
        ghl_api_client = OptimizedGoHighLevelAPI(
            private_token=AppConfig.GHL_PRIVATE_TOKEN, 
            location_id=AppConfig.GHL_LOCATION_ID,
            agency_api_key=AppConfig.GHL_AGENCY_API_KEY
        )
        
        # Use existing admin contact ID
        admin_contact_id = "b69NCeI1P32jooC7ySfw"  # Jeremy's contact ID
        
        customer_name = lead_data.get("customer_data", {}).get("name", "Customer")
        customer_email = lead_data.get("customer_data", {}).get("email", "No email")
        customer_phone = lead_data.get("customer_data", {}).get("phone", "No phone")
        
        admin_notification_message = f"""
🚨 UNMATCHED LEAD ALERT - {service_category}

No vendors found for this lead!

Customer: {customer_name}
Email: {customer_email}
Phone: {customer_phone}
Service: {service_category}
Location: {location}
Timeline: {lead_data.get('timeline', 'Not specified')}

Please manually assign this lead or add vendors for this service area.

Lead ID: {ghl_contact_id}

- Dockside Pros Lead Router (CLEAN/DIRECT)
        """.strip()
        
        # Send SMS notification to admin
        sms_sent = ghl_api_client.send_sms(admin_contact_id, admin_notification_message)
        
        if sms_sent:
            logger.info(f"📱 Admin notification sent for unmatched lead {ghl_contact_id}")
        else:
            logger.warning(f"⚠️ Failed to send admin notification for unmatched lead {ghl_contact_id}")
        
        # Log admin notification attempt
        simple_db_instance.log_activity(
            event_type="admin_unmatched_lead_notification",
            event_data={
                "admin_contact_id": admin_contact_id,
                "lead_contact_id": ghl_contact_id,
                "service_category": service_category,
                "location": location,
                "notification_type": "SMS",
                "success": sms_sent,
                "processing_method": "direct_only_no_ai"
            },
            lead_id=ghl_contact_id,
            success=sms_sent
        )
        
    except Exception as e:
        logger.error(f"Error notifying admin of unmatched lead {ghl_contact_id}: {e}")

# Legacy vendor user creation webhook (maintained for compatibility)
@router.post("/ghl/vendor-user-creation")
async def handle_vendor_user_creation_webhook(request: Request):
    """
    Legacy webhook endpoint for GHL workflow to trigger vendor user creation.
    Direct processing only - NO AI.
    """
    start_time = time.time()
    
    try:
        # Validate API key
        api_key = request.headers.get("X-Webhook-API-Key")
        expected_api_key = AppConfig.GHL_WEBHOOK_API_KEY
        
        if not api_key:
            logger.error(f"❌ GHL webhook request missing API key from IP: {request.client.host}")
            raise HTTPException(status_code=401, detail="Missing X-Webhook-API-Key header")
        
        if api_key != expected_api_key:
            logger.error(f"❌ GHL webhook API key mismatch from IP: {request.client.host}")
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        logger.info(f"✅ GHL webhook API key validated successfully")
        
        # Parse incoming GHL workflow webhook payload
        ghl_payload = await request.json()
        logger.info(f"📥 GHL Vendor User Creation Webhook received: {json.dumps(ghl_payload, indent=2)}")
        
        # Extract vendor information directly from webhook payload
        contact_id = ghl_payload.get("contact_id") or ghl_payload.get("contactId")
        vendor_email = ghl_payload.get("email", "")
        vendor_first_name = ghl_payload.get("first_name", "") or ghl_payload.get("firstName", "")
        vendor_last_name = ghl_payload.get("last_name", "") or ghl_payload.get("lastName", "")
        vendor_phone = ghl_payload.get("phone", "")
        vendor_company_name = ghl_payload.get("Vendor Company Name", "") or ghl_payload.get("vendor_company_name", "")
        
        logger.info(f"📋 Using vendor data directly from webhook payload:")
        logger.info(f"   👤 Contact ID: {contact_id}")
        logger.info(f"   📧 Email: {vendor_email}")
        logger.info(f"   👨 Name: {vendor_first_name} {vendor_last_name}")
        logger.info(f"   📱 Phone: {vendor_phone}")
        logger.info(f"   🏢 Company: {vendor_company_name}")
        
        # Use v1 API for vendor user creation (required for GHL user management)
        # This is the ONLY place where v1 API is still required
        ghl_api_client = GoHighLevelAPI(
            private_token=AppConfig.GHL_PRIVATE_TOKEN, 
            location_id=AppConfig.GHL_LOCATION_ID,
            agency_api_key=AppConfig.GHL_AGENCY_API_KEY,
            company_id=AppConfig.GHL_COMPANY_ID
        )
        
        if not vendor_email:
            logger.error(f"❌ No email found for contact {contact_id}")
            raise HTTPException(status_code=400, detail="Vendor email is required for user creation")
        
        # Check if user already exists
        # Note: get_user_by_email and create_user use v1 API which is required for vendor user creation
        existing_user = ghl_api_client.get_user_by_email(vendor_email)
        if existing_user:
            logger.info(f"✅ User already exists for {vendor_email}: {existing_user.get('id')}")
            
            # Get account and update vendor record
            account_record = simple_db_instance.get_account_by_ghl_location_id(AppConfig.GHL_LOCATION_ID)
            if account_record:
                vendor_record = simple_db_instance.get_vendor_by_email_and_account(vendor_email, account_record["id"])    
                if vendor_record:
                    simple_db_instance.update_vendor_status(
                        vendor_record["id"], 
                        "active", 
                        existing_user.get("id")
                    )
            
            return {
                "status": "success",
                "message": f"User already exists for vendor {vendor_email}",
                "user_id": existing_user.get("id"),
                "contact_id": contact_id,
                "action": "existing_user_found"
            }
        
        # Create new user data
        user_data = {
            "firstName": vendor_first_name,
            "lastName": vendor_last_name,
            "email": vendor_email,
            "phone": vendor_phone,
            "type": "account",
            "role": "user",
            "permissions": {
                "campaignsEnabled": False,
                "campaignsReadOnly": True,
                "contactsEnabled": True,
                "workflowsEnabled": False,
                "triggersEnabled": False,
                "funnelsEnabled": False,
                "websitesEnabled": False,
                "opportunitiesEnabled": True,
                "dashboardStatsEnabled": True,
                "bulkRequestsEnabled": False,
                "appointmentEnabled": True,
                "reviewsEnabled": False,
                "onlineListingsEnabled": False,
                "phoneCallEnabled": True,
                "conversationsEnabled": True,
                "assignedDataOnly": True,
                "adwordsReportingEnabled": False,
                "membershipEnabled": False,
                "facebookAdsReportingEnabled": False,
                "attributionsReportingEnabled": False,
                "settingsEnabled": False,
                "tagsEnabled": False,
                "leadValueEnabled": True,
                "marketingEnabled": False,
                "agentReportingEnabled": True,
                "botService": False,
                "socialPlanner": False,
                "bloggingEnabled": False,
                "invoiceEnabled": False,
                "affiliateManagerEnabled": False,
                "contentAiEnabled": False,
                "refundsEnabled": False,
                "recordPaymentEnabled": False,
                "cancelSubscriptionEnabled": False,
                "paymentsEnabled": False,
                "communitiesEnabled": False,
                "exportPaymentsEnabled": False
            }
        }
        
        # Create user in GHL
        logger.info(f"🔐 Creating GHL user for vendor: {vendor_email}")
        # Note: create_user uses v1 API endpoint which is required for GHL user creation
        created_user = ghl_api_client.create_user(user_data)
        
        if not created_user:
            logger.error(f"❌ No response from GHL user creation API for {vendor_email}")
            raise HTTPException(status_code=502, detail="No response from GHL user creation API")
        
        if isinstance(created_user, dict) and created_user.get("error"):
            error_details = {
                "api_version": created_user.get("api_version", "V1"),
                "status_code": created_user.get("status_code"),
                "response_text": created_user.get("response_text"),
                "exception": created_user.get("exception"),
                "url": created_user.get("url")
            }
            logger.error(f"❌ GHL V1 API user creation failed: {error_details}")
            error_msg = f"GHL V1 API error: {created_user.get('response_text', 'Unknown error')}"
            raise HTTPException(status_code=502, detail=error_msg)
        
        user_id = created_user.get("id")
        if not user_id:
            logger.error(f"❌ GHL user creation succeeded but no user ID returned: {created_user}")
            raise HTTPException(status_code=502, detail="User created but no ID returned from GHL")
        
        logger.info(f"✅ Successfully created GHL user: {user_id} for {vendor_email}")
        
        # Wait for GHL user propagation
        import asyncio
        logger.info(f"⏳ Waiting 10 seconds for GHL user propagation...")
        await asyncio.sleep(10)
        logger.info(f"✅ User propagation delay complete")
        
        # FIXED: Ensure vendor record exists when GHL User ID is assigned
        try:
            # Get account info
            account_record = simple_db_instance.get_account_by_ghl_location_id(AppConfig.GHL_LOCATION_ID)
            if not account_record:
                logger.error("❌ No account found for location")
                raise HTTPException(status_code=500, detail="Account configuration error")
            
            # Try to find existing vendor by email
            existing_vendor = simple_db_instance.get_vendor_by_email_and_account(vendor_email, account_record['id'])
            
            if existing_vendor:
                # Update existing vendor with GHL User ID AND set status to active
                simple_db_instance.update_vendor_status(existing_vendor['id'], 'active', user_id)
                logger.info(f"✅ Updated existing vendor {existing_vendor['id']} with GHL User ID: {user_id} and set status to active")
            else:
                # CRITICAL ERROR: Vendor approval webhook called but no vendor record exists
                # This should not happen - vendors must be created via form submission first
                logger.error(f"❌ CRITICAL: Vendor approval triggered for {vendor_email} but no vendor record exists!")
                logger.error(f"   This suggests the vendor was never created via form submission.")
                logger.error(f"   Contact ID: {contact_id}")
                logger.error(f"   Name: {vendor_first_name} {vendor_last_name}")
                logger.error(f"   Company: {vendor_company_name}")
                
                # Return error instead of creating bad data
                return {
                    "status": "error",
                    "message": f"No vendor record found for {vendor_email}. Vendor must be created via form submission before approval.",
                    "contact_id": contact_id,
                    "action": "approval_failed_no_vendor_record",
                    "error_code": "VENDOR_NOT_FOUND"
                }
        
        except Exception as e:
            logger.error(f"❌ Failed to link vendor with GHL User ID: {str(e)}")
            # Don't fail the webhook - the user was created successfully

        # Get account ID for remaining operations
        account_record = simple_db_instance.get_account_by_ghl_location_id(AppConfig.GHL_LOCATION_ID)
        if not account_record:
            account_id = simple_db_instance.create_account(
                ghl_location_id=AppConfig.GHL_LOCATION_ID,
                company_name="DocksidePros",
                industry="Marine Services"
            )
        else:
            account_id = account_record["id"]
        
        # Update the contact record with the GHL User ID
        if contact_id:
            logger.info(f"🔄 Updating contact {contact_id} with GHL User ID: {user_id}")
            
            ghl_user_id_field = field_mapper.get_ghl_field_details("ghl_user_id")
            if ghl_user_id_field and ghl_user_id_field.get("id"):
                update_payload = {
                    "customFields": [
                        {
                            "id": ghl_user_id_field["id"],
                            "value": user_id
                        }
                    ]
                }
                
                update_success = ghl_api_client.update_contact(contact_id, update_payload)
                if update_success:
                    logger.info(f"✅ Successfully updated contact {contact_id} with GHL User ID: {user_id}")
                else:
                    logger.warning(f"⚠️ Failed to update contact {contact_id} with GHL User ID")
            else:
                logger.warning(f"⚠️ Could not find GHL User ID field mapping for contact update")
        
        # Update vendor record in database
        vendor_record = simple_db_instance.get_vendor_by_email_and_account(vendor_email, account_id)
        if vendor_record:
            simple_db_instance.update_vendor_status(vendor_record["id"], "active", user_id)
            logger.info(f"✅ Updated vendor record with user ID: {user_id}")
        else:
            logger.warning(f"⚠️ No vendor record found for {vendor_email} - user created but not linked")
        
        # Log successful activity
        processing_time = round(time.time() - start_time, 3)
        simple_db_instance.log_activity(
            event_type="vendor_user_created_clean",
            event_data={
                "contact_id": contact_id,
                "user_id": user_id,
                "vendor_email": vendor_email,
                "vendor_company": vendor_company_name,
                "processing_time_seconds": processing_time,
                "processing_method": "direct_only_no_ai"
            },
            lead_id=contact_id,
            success=True
        )
        
        logger.info(f"📧 Vendor notifications handled by GHL automation workflows")
        
        return {
            "status": "success",
            "message": f"Successfully created user for vendor {vendor_email}",
            "user_id": user_id,
            "contact_id": contact_id,
            "vendor_email": vendor_email,
            "vendor_company": vendor_company_name,
            "processing_time_seconds": processing_time,
            "action": "user_created",
            "processing_method": "direct_only_no_ai"
        }
        
    except HTTPException:
        raise
    
    except Exception as e:
        processing_time = round(time.time() - start_time, 3)
        logger.exception(f"💥 Critical error processing vendor user creation webhook after {processing_time}s: {e}")
        simple_db_instance.log_activity(
            event_type="vendor_user_creation_error_clean",
            event_data={
                "processing_time_seconds": processing_time,
                "error_class": e.__class__.__name__,
                "processing_method": "direct_only_no_ai"
            },
            success=False,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Health check endpoint
@router.get("/health")
async def clean_webhook_health_check():
    """Clean health check for webhook system - NO AI dependencies"""
    try:
        # Test database connection
        db_stats = simple_db_instance.get_stats()
        db_healthy = True
    except Exception as e:
        db_stats = {"error": str(e)}
        db_healthy = False
    
    # Test field reference loading directly from field_reference.json
    try:
        import json
        from pathlib import Path
        field_ref_path = Path("/root/Lead-Router-Pro/field_reference.json")
        if field_ref_path.exists():
            with open(field_ref_path, 'r') as f:
                field_reference = json.load(f)
                # field_reference.json has direct field IDs as keys, not a customFields array
                field_count = len(field_reference)
        else:
            field_reference = {}
            field_count = 0
    except Exception as e:
        logger.error(f"Error loading field reference: {e}")
        field_reference = {}
        field_count = 0
    
    field_mapper_stats = {
        "ghl_fields_loaded": field_count,
        "custom_fields_available": field_count
    }
    field_reference_healthy = field_count > 0
    
    return {
        "status": "healthy" if (db_healthy and field_reference_healthy) else "degraded",
        "webhook_system": "clean_direct_processing_no_ai",
        "ghl_location_id": AppConfig.GHL_LOCATION_ID,
        "pipeline_configured": AppConfig.PIPELINE_ID is not None and AppConfig.NEW_LEAD_STAGE_ID is not None,
        "valid_field_count": field_mapper_stats.get("ghl_fields_loaded", 0),
        "custom_field_mappings": field_mapper_stats.get("ghl_fields_loaded", 0),
        "service_categories": len(DOCKSIDE_PROS_SERVICES),
        "database_status": "healthy" if db_healthy else "error",
        "database_stats": db_stats,
        "field_reference_status": "loaded" if field_reference_healthy else "missing",
        "field_mapper_stats": field_mapper_stats,
        "supported_form_types": ["client_lead", "vendor_application", "emergency_service", "general_inquiry"],
        "routing_method": "direct_vendor_matching_no_ai",
        "ai_processing": "completely_disabled",
        "opportunity_creation": "enabled" if AppConfig.PIPELINE_ID else "disabled",
        "message": "Clean webhook system ready for direct processing - NO AI interference"
    }

# Get service categories endpoint
@router.get("/service-categories")
async def get_clean_service_categories():
    """Return all supported service categories - Direct mapping only"""
    
    # Group categories by type
    categories_by_type = {}
    for form_key, category in DOCKSIDE_PROS_SERVICES.items():
        if category not in categories_by_type:
            categories_by_type[category] = []
        categories_by_type[category].append(form_key)
    
    return {
        "status": "success",
        "service_categories": categories_by_type,
        "total_categories": len(set(DOCKSIDE_PROS_SERVICES.values())),
        "total_form_identifiers": len(DOCKSIDE_PROS_SERVICES),
        "processing_method": "direct_mapping_no_ai",
        "ai_processing": "disabled",
        "message": f"All {len(set(DOCKSIDE_PROS_SERVICES.values()))} marine service categories supported with direct form handling - NO AI"
    }

# Get field mappings endpoint
@router.get("/field-mappings")
async def get_clean_field_mappings():
    """Return all available field mappings for form development - Direct only"""
    
    # Load field reference directly from field_reference.json
    try:
        import json
        from pathlib import Path
        field_ref_path = Path("/root/Lead-Router-Pro/field_reference.json")
        if field_ref_path.exists():
            with open(field_ref_path, 'r') as f:
                field_reference = json.load(f)
        else:
            field_reference = {}
    except Exception as e:
        logger.error(f"Error loading field reference for mappings: {e}")
        field_reference = {}
    
    # Build custom field mappings from field_reference.json
    # The file has field IDs as keys directly
    custom_field_mappings = {}
    for field_id, field_info in field_reference.items():
        if isinstance(field_info, dict):
            custom_field_mappings[field_id] = {
                'name': field_info.get('name', field_id),
                'id': field_id,
                'type': field_info.get('fieldType', 'TEXT')
            }
    
    return {
        "status": "success",
        "standard_fields": [
            "firstName", "lastName", "email", "phone", "companyName", 
            "address1", "city", "state", "postal_code", "name",
            "tags", "notes", "source", "website"
        ],
        "custom_field_mappings": custom_field_mappings,
        "total_custom_fields": len(custom_field_mappings),
        "field_reference_source": "ServiceDictionaryMapper with field_reference.json",
        "mapping_stats": {
            "ghl_fields_loaded": len(custom_field_mappings),
            "custom_fields_available": len(custom_field_mappings)
        },
        "processing_method": "direct_field_mapping_no_ai",
        "ai_processing": "disabled",
        "message": "Complete field mappings for GHL integration - Direct processing only"
    }

# Dynamic form testing endpoint
@router.post("/test/{form_identifier}")
async def test_clean_form_configuration(form_identifier: str):
    """Test endpoint to see how any form identifier would be configured - Direct only"""
    
    try:
        form_config = get_form_configuration(form_identifier)
        
        return {
            "status": "success",
            "form_identifier": form_identifier,
            "generated_configuration": form_config,
            "webhook_url": f"https://dockside.life/api/v1/webhooks/elementor/{form_identifier}",
            "processing_method": "direct_configuration_no_ai",
            "ai_processing": "disabled",
            "message": f"Direct configuration generated for form '{form_identifier}' - NO AI processing"
        }
    except Exception as e:
        return {
            "status": "error",
            "form_identifier": form_identifier,
            "error": str(e),
            "message": "Failed to generate configuration"
        }

@router.post("/ghl/reassign-lead")
async def handle_lead_reassignment_webhook(request: Request):
    """
    FIXED: Delegates to the corrected reassignment handler that follows proper flow.
    """
    from api.routes.webhook_reassignment_fixed import handle_lead_reassignment_webhook_fixed
    return await handle_lead_reassignment_webhook_fixed(request)

@router.post("/ghl/process-new-contact")
async def handle_ghl_new_contact_trigger(request: Request):
    """
    GHL webhook endpoint triggered when a contact is created with "New Lead" tag.
    Bypasses WordPress form handling and picks up lead processing at the point where
    a lead needs to be created in the Lead Router database, followed by opportunity
    creation and vendor assignment.
    
    Flow:
    1. Parse GHL webhook payload and extract contact ID
    2. Fetch complete contact details from GHL
    3. Extract required fields from contact data
    4. Check for duplicate leads (idempotent)
    5. Create lead record in database
    6. Create opportunity in GHL
    7. Perform vendor matching and assignment
    8. Return success response
    """
    start_time = time.time()
    
    try:
        # Step 1: Parse incoming webhook payload
        ghl_payload = await request.json()
        logger.info(f"📥 GHL New Contact Webhook received: {json.dumps(ghl_payload, indent=2)}")
        
        # Check if this is a custom workflow webhook with customData
        custom_data = ghl_payload.get("customData", {})
        
        # Extract contact ID from webhook - check multiple possible locations including customData
        contact_id = (
            ghl_payload.get("contactId") or 
            ghl_payload.get("contact_id") or 
            ghl_payload.get("id") or 
            ghl_payload.get("contact", {}).get("id") or
            ghl_payload.get("Contact ID") or
            ghl_payload.get("contact", {}).get("Contact ID") or
            custom_data.get("contact_id")
        )
        
        if not contact_id:
            logger.error(f"❌ No contact ID found in webhook payload. Keys received: {list(ghl_payload.keys())}, customData keys: {list(custom_data.keys())}")
            raise HTTPException(status_code=400, detail="Contact ID is required")
        
        logger.info(f"🎯 Processing new contact: {contact_id}")
        
        # Log webhook for debugging
        simple_db_instance.log_activity(
            event_type="ghl_new_contact_webhook",
            event_data={
                "contact_id": contact_id,
                "webhook_type": ghl_payload.get("type", "unknown"),
                "payload_keys": list(ghl_payload.keys())
            },
            lead_id=contact_id,
            success=True
        )
        
        # Step 2: Initialize GHL API and fetch complete contact details
        ghl_api = OptimizedGoHighLevelAPI(
            private_token=AppConfig.GHL_PRIVATE_TOKEN,
            location_id=AppConfig.GHL_LOCATION_ID,
            agency_api_key=AppConfig.GHL_AGENCY_API_KEY
        )
        
        logger.info(f"📋 Fetching complete contact details for {contact_id}")
        contact_details = ghl_api.get_contact_by_id(contact_id)
        
        if not contact_details:
            logger.error(f"❌ Could not fetch contact details for {contact_id}")
            raise HTTPException(status_code=404, detail="Contact not found in GHL")
        
        logger.info(f"✅ Retrieved contact: {contact_details.get('firstName')} {contact_details.get('lastName')}")
        
        # Step 3: Extract required fields from contact data
        customer_name = f"{contact_details.get('firstName', '')} {contact_details.get('lastName', '')}".strip()
        customer_email = contact_details.get('email', '')
        customer_phone = contact_details.get('phone', '')
        
        # NEW: Apply proper field mapping using ServiceDictionaryMapper
        # First extract custom fields into flat dictionary
        custom_fields_dict = extract_ghl_custom_fields(contact_details)
        
        # Map using ServiceDictionaryMapper
        mapping_result = map_ghl_contact_to_lead(contact_details)
        mapped_payload = mapping_result.get('standardized_fields', {})
        service_classification = mapping_result.get('service_classification', {})
        logger.info(f"🔄 ServiceDictionaryMapper complete. Service classification: {service_classification}")
        
        # Extract service information using proper field IDs
        primary_category = None
        specific_service = None
        
        # First try to get from the known GHL field IDs
        if LEAD_ROUTING_FIELD_IDS['primary_service_category'] in custom_fields_dict:
            primary_category = custom_fields_dict[LEAD_ROUTING_FIELD_IDS['primary_service_category']]
            logger.info(f"✅ Found primary category from GHL field: '{primary_category}'")
            
        if LEAD_ROUTING_FIELD_IDS['specific_service_needed'] in custom_fields_dict:
            specific_service = custom_fields_dict[LEAD_ROUTING_FIELD_IDS['specific_service_needed']]
            logger.info(f"✅ Found specific service from GHL field: '{specific_service}'")
        
        # Fallback to ServiceDictionaryMapper results if not found in GHL fields
        if not primary_category:
            primary_category = service_classification.get('level1_category')
            if primary_category:
                logger.info(f"📌 Using primary category from ServiceDictionaryMapper: '{primary_category}'")
        
        if not specific_service:
            # Check Level 3 first, then Level 2
            specific_service = service_classification.get('level3_specific') or service_classification.get('level2_service')
            if specific_service:
                logger.info(f"📌 Using specific service from ServiceDictionaryMapper: '{specific_service}'")
        
        # Check custom data for fallback
        if not primary_category and custom_data.get('routing_category'):
            primary_category = custom_data.get('routing_category')
            logger.info(f"📌 Using primary category from customData: '{primary_category}'")
            
        if not specific_service and custom_data.get('specific_service_requested'):
            specific_service = custom_data.get('specific_service_requested')
            logger.info(f"📌 Using specific service from customData: '{specific_service}'")
        
        # SIMPLIFIED: Just use the specific service directly for vendor matching
        # We don't need complex hierarchy logic - vendors are matched by specific service
        final_specific_service = specific_service  # Use whatever service was extracted
        
        # For the primary category, use what we have or try to infer from service
        if primary_category:
            service_category = primary_category
        elif specific_service:
            # Try to find which category this service belongs to
            from api.services.service_categories import SERVICE_CATEGORIES, LEVEL_3_SERVICES
            service_category = None
            
            # Check Level 2 services
            for cat, services in SERVICE_CATEGORIES.items():
                if specific_service in services:
                    service_category = cat
                    logger.info(f"📌 Inferred category '{cat}' from Level 2 service '{specific_service}'")
                    break
            
            # Check Level 3 services if not found
            if not service_category:
                for cat, subcats in LEVEL_3_SERVICES.items():
                    for subcat, level3_services in subcats.items():
                        if specific_service in level3_services:
                            service_category = cat
                            logger.info(f"📌 Inferred category '{cat}' from Level 3 service '{specific_service}'")
                            break
                    if service_category:
                        break
            
            if not service_category:
                service_category = "Uncategorized"
                logger.warning(f"⚠️ Could not infer category for service '{specific_service}'")
        else:
            service_category = "Uncategorized"
            logger.error(f"❌ No service information found for contact {contact_id}")
        
        logger.info(f"✅ Final: category='{service_category}', specific_service='{final_specific_service}'")
        
        # Extract ZIP code - check customData first, then mapped payload and contact details
        zip_code = custom_data.get("customer_zip_code") or \
                  custom_data.get("zip_code") or \
                  mapped_payload.get("zip_code_of_service") or \
                  mapped_payload.get("customer_zip_code") or \
                  contact_details.get("postalCode") or ""
        
        service_county = ""
        service_state = ""
        
        if zip_code and len(str(zip_code)) == 5 and str(zip_code).isdigit():
            logger.info(f"🗺️ Converting ZIP {zip_code} to county")
            location_data = location_service.zip_to_location(str(zip_code))
            
            if not location_data.get('error'):
                county = location_data.get('county', '')
                state = location_data.get('state', '')
                if county and state:
                    service_county = f"{county}, {state}"
                    service_state = state
                    logger.info(f"✅ ZIP {zip_code} → {service_county}")
                else:
                    logger.warning(f"⚠️ ZIP {zip_code} conversion incomplete")
            else:
                logger.warning(f"⚠️ Could not convert ZIP {zip_code}: {location_data['error']}")
        
        # Get account information
        account_record = simple_db_instance.get_account_by_ghl_location_id(AppConfig.GHL_LOCATION_ID)
        if not account_record:
            logger.error("❌ No account found for GHL location")
            raise HTTPException(status_code=500, detail="Account configuration error")
        
        account_id = account_record['id']
        
        # Step 4: Check for duplicate leads (idempotent behavior)
        existing_lead = simple_db_instance.get_lead_by_ghl_contact_id(contact_id)
        
        if existing_lead:
            logger.info(f"📋 Lead already exists for contact {contact_id}: {existing_lead['id']}")
            return {
                "status": "success",
                "message": "Lead already processed",
                "lead_id": existing_lead['id'],
                "ghl_contact_id": contact_id,
                "duplicate": True,
                "processing_time": round(time.time() - start_time, 3)
            }
        
        # Step 5: Create lead record in database
        lead_id = str(uuid.uuid4())
        
        # Build service details from all mapped fields
        service_details = {
            "source": "ghl_automation",
            "trigger": "new_lead_tag",
            "processed_via": "ghl_contact_trigger",
            "service_category": service_category,
            "zip_code": zip_code
        }
        
        # Add any additional custom fields to service_details
        for field_key, field_value in mapped_payload.items():
            if field_value and field_key not in ["firstName", "lastName", "email", "phone"]:
                service_details[field_key] = field_value
        
        logger.info(f"💾 Creating lead record in database")
        
        conn = None
        try:
            conn = simple_db_instance._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO leads (
                    id, account_id, ghl_contact_id, ghl_opportunity_id, customer_name,
                    customer_email, customer_phone, primary_service_category, specific_service_requested,
                    customer_zip_code, service_zip_code, service_county, service_state, vendor_id, 
                    status, priority, source, service_details, 
                    created_at, updated_at, service_city, 
                    service_complexity, estimated_duration, requires_emergency_response, 
                    classification_confidence, classification_reasoning
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?)
            ''', (
                lead_id,                                                    # id
                account_id,                                                 # account_id
                contact_id,                                                 # ghl_contact_id
                None,                                                       # ghl_opportunity_id (will be updated)
                customer_name,                                              # customer_name
                customer_email.lower().strip() if customer_email else None, # customer_email
                customer_phone,                                             # customer_phone
                service_category,                                           # primary_service_category
                final_specific_service or "",                               # specific_service_requested (properly extracted)
                zip_code,                                                   # customer_zip_code
                zip_code,                                                   # service_zip_code
                service_county,                                             # service_county
                service_state,                                              # service_state
                None,                                                       # vendor_id (unassigned)
                "new",                                                      # status
                "normal",                                                   # priority
                "ghl_automation",                                           # source
                json.dumps(service_details),                                # service_details
                "",                                                         # service_city
                "simple",                                                   # service_complexity
                "medium",                                                   # estimated_duration
                False,                                                      # requires_emergency_response
                1.0,                                                        # classification_confidence
                "Created via GHL new contact trigger"                       # classification_reasoning
            ))
            
            conn.commit()
            logger.info(f"✅ Created lead: {lead_id}")
            
        except Exception as e:
            logger.error(f"❌ Lead creation error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
        
        # Step 6: Create opportunity in GHL
        opportunity_id = None
        
        if AppConfig.PIPELINE_ID and AppConfig.NEW_LEAD_STAGE_ID:
            # Check for existing opportunity first
            existing_opportunities = ghl_api.get_opportunities_by_contact(contact_id)
            
            if existing_opportunities and len(existing_opportunities) > 0:
                opportunity_id = existing_opportunities[0].get('id')
                logger.info(f"📋 Using existing opportunity: {opportunity_id}")
            else:
                # Create new opportunity
                logger.info(f"📈 Creating opportunity for {service_category} lead")
                
                opportunity_data = {
                    "contactId": contact_id,
                    "name": f"{service_category} - {customer_name}",
                    "pipelineId": AppConfig.PIPELINE_ID,
                    "pipelineStageId": AppConfig.NEW_LEAD_STAGE_ID,
                    "status": "open",
                    "monetaryValue": 0,
                    "source": "GHL Automation (New Lead Tag)",
                    "locationId": AppConfig.GHL_LOCATION_ID
                }
                
                opportunity_response = ghl_api.create_opportunity(opportunity_data)
                
                # Check for opportunity in the response (v2 API returns it nested)
                if opportunity_response:
                    if opportunity_response.get('opportunity', {}).get('id'):
                        opportunity_id = opportunity_response['opportunity']['id']
                        logger.info(f"✅ Created opportunity: {opportunity_id}")
                    elif opportunity_response.get('id'):
                        opportunity_id = opportunity_response['id']
                        logger.info(f"✅ Created opportunity: {opportunity_id}")
                    else:
                        logger.error(f"❌ Failed to create opportunity: {opportunity_response}")
            
            # Update lead with opportunity ID
            if opportunity_id:
                try:
                    simple_db_instance.update_lead_opportunity_id(lead_id, opportunity_id)
                    logger.info(f"✅ Linked opportunity {opportunity_id} to lead {lead_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not link opportunity ID: {e}")
        else:
            logger.warning("⚠️ Pipeline not configured - skipping opportunity creation")
        
        # Step 7: Perform vendor matching and assignment
        vendor_assigned = False
        selected_vendor = None
        
        # Use the properly extracted specific service from our hierarchy determination
        logger.info(f"🔍 Finding matching vendors for {service_category} (specific: {final_specific_service}) in {zip_code}")
        
        available_vendors = lead_routing_service.find_matching_vendors(
            account_id=account_id,
            service_category=service_category,
            zip_code=zip_code,
            priority="normal",
            specific_service=final_specific_service or ""
        )
        
        if available_vendors:
            logger.info(f"✅ Found {len(available_vendors)} matching vendors")
            
            # Select vendor from pool
            selected_vendor = lead_routing_service.select_vendor_from_pool(available_vendors, account_id)
            
            if selected_vendor and selected_vendor.get('ghl_user_id'):
                logger.info(f"🎯 Selected vendor: {selected_vendor['name']}")
                
                # Assign lead to vendor in database
                assignment_success = simple_db_instance.assign_lead_to_vendor(lead_id, selected_vendor['id'])
                
                if assignment_success:
                    logger.info(f"✅ Assigned lead to vendor in database")
                    vendor_assigned = True
                    
                    # Update opportunity with vendor assignment
                    if opportunity_id:
                        try:
                            update_data = {
                                'assignedTo': selected_vendor['ghl_user_id'],
                                'pipelineId': AppConfig.PIPELINE_ID,
                                'pipelineStageId': AppConfig.NEW_LEAD_STAGE_ID
                            }
                            
                            ghl_assignment_success = ghl_api.update_opportunity(opportunity_id, update_data)
                            
                            if ghl_assignment_success:
                                logger.info(f"✅ Assigned opportunity to vendor in GHL")
                            else:
                                logger.warning(f"⚠️ Failed to assign opportunity in GHL")
                        except Exception as e:
                            logger.error(f"❌ Error assigning opportunity: {e}")
                else:
                    logger.error(f"❌ Failed to assign lead to vendor in database")
            else:
                logger.warning(f"⚠️ Selected vendor has no GHL User ID")
        else:
            logger.warning(f"⚠️ No matching vendors found for {service_category} in {zip_code}")
        
        # Log activity
        processing_time = round(time.time() - start_time, 3)
        simple_db_instance.log_activity(
            event_type="ghl_contact_processed",
            event_data={
                "contact_id": contact_id,
                "lead_id": lead_id,
                "opportunity_id": opportunity_id,
                "service_category": service_category,
                "zip_code": zip_code,
                "vendor_assigned": vendor_assigned,
                "vendor_id": selected_vendor['id'] if selected_vendor else None,
                "processing_time": processing_time
            },
            lead_id=lead_id,
            success=True
        )
        
        # Step 8: Return success response
        response_data = {
            "status": "success",
            "message": "Contact processed successfully",
            "lead_id": lead_id,
            "ghl_contact_id": contact_id,
            "opportunity_id": opportunity_id,
            "service_category": service_category,
            "location": f"{zip_code} ({service_county})" if service_county else zip_code,
            "vendor_assigned": vendor_assigned,
            "processing_time": processing_time
        }
        
        if selected_vendor:
            response_data["vendor"] = {
                "id": selected_vendor['id'],
                "name": selected_vendor['name'],
                "email": selected_vendor.get('email')
            }
        
        logger.info(f"✅ GHL contact processing complete in {processing_time}s")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing GHL contact: {e}", exc_info=True)
        
        # Log error
        simple_db_instance.log_activity(
            event_type="ghl_contact_processing_error",
            event_data={
                "error": str(e),
                "contact_id": contact_id if 'contact_id' in locals() else None
            },
            success=False,
            error_message=str(e)
        )
        
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
