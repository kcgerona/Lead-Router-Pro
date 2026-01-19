# api/routes/routing_admin.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
import requests
import json
import uuid
from database.simple_connection import db
from api.services.lead_routing_service import lead_routing_service
from api.services.ghl_api import GoHighLevelAPI
from api.routes.webhook_routes import create_lead_from_ghl_contact
from config import AppConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/routing", tags=["Lead Routing Administration"])

class RoutingConfigRequest(BaseModel):
    performance_percentage: int

class VendorMatchingRequest(BaseModel):
    zip_code: str
    service_category: str
    specific_service: Optional[str] = None  # NEW: Support for specific service testing

@router.get("/configuration")
async def get_routing_configuration():
    """Get current lead routing configuration"""
    try:
        # Get the default account for this GHL location
        account = db.get_account_by_ghl_location_id(AppConfig.GHL_LOCATION_ID)
        if not account:
            # Create default account if none exists
            account_id = db.create_account(
                company_name="Digital Marine LLC",
                industry="marine",
                ghl_location_id=AppConfig.GHL_LOCATION_ID,
                ghl_private_token=AppConfig.GHL_PRIVATE_TOKEN
            )
        else:
            account_id = account["id"]
        
        # Get routing statistics
        routing_stats = lead_routing_service.get_routing_stats(account_id)
        
        return {
            "status": "success",
            "data": routing_stats,
            "account_id": account_id,
            "message": "Routing configuration retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting routing configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve routing configuration")

@router.post("/configuration")
async def update_routing_configuration(request: RoutingConfigRequest):
    """Update lead routing configuration"""
    try:
        performance_percentage = request.performance_percentage
        
        # Validate percentage
        if not 0 <= performance_percentage <= 100:
            raise HTTPException(status_code=400, detail="Performance percentage must be between 0 and 100")
        
        # Get the default account for this GHL location
        account = db.get_account_by_ghl_location_id(AppConfig.GHL_LOCATION_ID)
        if not account:
            # Create default account if none exists
            account_id = db.create_account(
                company_name="Digital Marine LLC",
                industry="marine",
                ghl_location_id=AppConfig.GHL_LOCATION_ID,
                ghl_private_token=AppConfig.GHL_PRIVATE_TOKEN
            )
        else:
            account_id = account["id"]
        
        # Update routing configuration
        success = lead_routing_service.update_routing_configuration(account_id, performance_percentage)
        
        if success:
            # Get updated stats
            routing_stats = lead_routing_service.get_routing_stats(account_id)
            
            return {
                "status": "success",
                "data": routing_stats,
                "message": f"Routing configuration updated: {performance_percentage}% performance-based, {100 - performance_percentage}% round-robin"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update routing configuration")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating routing configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update routing configuration")

@router.get("/vendors")
async def get_routing_vendors():
    """Get vendors with routing information"""
    try:
        # Get the default account for this GHL location
        account = db.get_account_by_ghl_location_id(AppConfig.GHL_LOCATION_ID)
        if not account:
            return {
                "status": "success",
                "data": [],
                "message": "No account found - no vendors available"
            }
        
        account_id = account["id"]
        vendors = db.get_vendors(account_id)
        
        # Add routing-specific information
        for vendor in vendors:
            vendor['coverage_summary'] = _get_coverage_summary(vendor)
            vendor['routing_eligible'] = (
                vendor.get('status') == 'active' and 
                vendor.get('taking_new_work', False)
            )
        
        return {
            "status": "success",
            "data": vendors,
            "count": len(vendors),
            "message": "Vendors retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting routing vendors: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve vendors")

@router.post("/vendors/{vendor_id}/coverage")
async def update_vendor_coverage(vendor_id: str, coverage_data: Dict[str, Any]):
    """Update vendor coverage configuration"""
    try:
        # Validate coverage data
        coverage_type = coverage_data.get('service_coverage_type', 'zip')
        if coverage_type not in ['global', 'national', 'state', 'county', 'zip']:
            raise HTTPException(status_code=400, detail="Invalid coverage type")
        
        # Update vendor in database
        conn = db._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE vendors 
            SET service_coverage_type = ?, 
                service_states = ?, 
                service_counties = ?, 
                service_areas = ?,
                updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (
            coverage_type,
            str(coverage_data.get('service_states', [])),
            str(coverage_data.get('service_counties', [])),
            str(coverage_data.get('service_areas', [])),
            vendor_id
        ))
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Vendor not found")
        
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "message": f"Vendor coverage updated to {coverage_type}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating vendor coverage: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update vendor coverage")

@router.post("/test-matching")
async def test_vendor_matching(request: VendorMatchingRequest):
    """Test vendor matching for a specific location and service"""
    try:
        zip_code = request.zip_code
        service_category = request.service_category
        
        # Get the default account for this GHL location
        account = db.get_account_by_ghl_location_id(AppConfig.GHL_LOCATION_ID)
        if not account:
            return {
                "status": "success",
                "data": {
                    "matching_vendors": [],
                    "selected_vendor": None,
                    "message": "No account found - no vendors available"
                }
            }
        
        account_id = account["id"]
        
        # NEW: Extract specific service parameter for enhanced testing
        specific_service = request.specific_service
        
        # Validate service category and specific service against service hierarchy
        from api.services.service_categories import service_manager
        
        if not service_manager.is_valid_category(service_category):
            return {
                "status": "error",
                "message": f"Invalid service category: {service_category}",
                "available_categories": service_manager.get_all_categories()
            }
        
        # If specific service is provided, validate it
        if specific_service and not service_manager.is_service_in_category(specific_service, service_category):
            return {
                "status": "error", 
                "message": f"Service '{specific_service}' not found in category '{service_category}'",
                "available_services": service_manager.get_services_for_category(service_category)
            }
        
        # Find matching vendors using enhanced multi-level routing
        # Use test_mode=True to include pending/missing_in_ghl vendors for testing
        matching_vendors = lead_routing_service.find_matching_vendors(
            account_id=account_id,
            service_category=service_category,
            zip_code=zip_code,
            specific_service=specific_service,  # NEW: Pass specific service for exact matching
            test_mode=True  # Allow pending/missing vendors for testing (live assignments still require 'active')
        )
        
        # Select vendor using routing logic
        selected_vendor = None
        if matching_vendors:
            selected_vendor = lead_routing_service.select_vendor_from_pool(
                matching_vendors, account_id
            )
        
        # Enhanced response with routing details
        routing_method = "exact_service_match" if specific_service else "category_match"
        
        return {
            "status": "success",
            "data": {
                "zip_code": zip_code,
                "service_category": service_category,
                "specific_service": specific_service,
                "routing_method": routing_method,
                "matching_vendors": matching_vendors,
                "selected_vendor": selected_vendor,
                "match_count": len(matching_vendors)
            },
            "message": f"Found {len(matching_vendors)} matching vendors for {service_category}" + 
                      (f" -> {specific_service}" if specific_service else "") + f" in {zip_code}"
        }
        
    except Exception as e:
        logger.error(f"Error testing vendor matching: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to test vendor matching")

@router.post("/process-unassigned-leads")
async def process_unassigned_leads():
    """
    Enhanced feature: Pull unassigned leads from GoHighLevel and attempt to assign them to vendors
    This replaces the simple test matching with a more useful bulk assignment feature
    """
    try:
        # Get the default account for this GHL location
        account = db.get_account_by_ghl_location_id(AppConfig.GHL_LOCATION_ID)
        if not account:
            return {
                "status": "error",
                "message": "No account found - cannot process leads"
            }
        
        account_id = account["id"]
        
        # Step 1: Get unassigned leads from GoHighLevel
        unassigned_ghl_leads = await _get_unassigned_leads_from_ghl()
        
        if not unassigned_ghl_leads:
            return {
                "status": "success",
                "data": {
                    "processed_leads": 0,
                    "successful_assignments": 0,
                    "failed_assignments": 0,
                    "leads": []
                },
                "message": "No unassigned leads found in GoHighLevel"
            }
        
        # Step 2: Process each unassigned lead
        processed_leads = []
        successful_assignments = 0
        failed_assignments = 0
        
        for ghl_lead in unassigned_ghl_leads:
            lead_result = await _process_single_unassigned_lead(ghl_lead, account_id)
            processed_leads.append(lead_result)
            
            if lead_result["assignment_successful"]:
                successful_assignments += 1
            else:
                failed_assignments += 1
        
        return {
            "status": "success",
            "data": {
                "processed_leads": len(processed_leads),
                "successful_assignments": successful_assignments,
                "failed_assignments": failed_assignments,
                "leads": processed_leads
            },
            "message": f"Processed {len(processed_leads)} unassigned leads: {successful_assignments} assigned, {failed_assignments} failed"
        }
        
    except Exception as e:
        logger.error(f"Error processing unassigned leads: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process unassigned leads")

async def _get_unassigned_leads_from_ghl() -> List[Dict[str, Any]]:
    """
    Fetch unassigned leads from GoHighLevel API
    Returns leads that don't have a vendor assigned in the assignedTo field
    """
    try:
        # Initialize GHL API client
        ghl_api = GoHighLevelAPI(
            location_api_key=AppConfig.GHL_LOCATION_API,
            private_token=AppConfig.GHL_PRIVATE_TOKEN,
            location_id=AppConfig.GHL_LOCATION_ID,
            agency_api_key=AppConfig.GHL_AGENCY_API_KEY,
            company_id=AppConfig.GHL_COMPANY_ID
        )
        
        # Get contacts from GHL that are leads but don't have assigned vendors
        contacts = ghl_api.search_contacts(query="lead", limit=100)
        
        # Filter for unassigned leads (no assignedTo or assignedTo is empty)
        unassigned_leads = []
        for contact in contacts:
            # Check if this contact is a lead and doesn't have an assigned vendor
            assigned_to = contact.get('assignedTo')
            tags = contact.get('tags', [])
            
            # Consider it a lead if it has lead-related tags or is in a lead pipeline
            is_lead = any(tag.lower() in ['lead', 'new lead', 'unassigned'] for tag in tags)
            
            if is_lead and not assigned_to:
                # Extract relevant information for processing
                lead_info = {
                    'ghl_contact_id': contact.get('id'),
                    'name': f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip(),
                    'email': contact.get('email'),
                    'phone': contact.get('phone'),
                    'address': contact.get('address1'),
                    'city': contact.get('city'),
                    'state': contact.get('state'),
                    'postal_code': contact.get('postalCode'),
                    'tags': tags,
                    'custom_fields': contact.get('customFields', {}),
                    'source': contact.get('source', 'GoHighLevel'),
                    'created_at': contact.get('dateAdded')
                }
                unassigned_leads.append(lead_info)
        
        logger.info(f"Found {len(unassigned_leads)} unassigned leads in GoHighLevel")
        return unassigned_leads
        
    except Exception as e:
        logger.error(f"Error fetching unassigned leads from GHL: {e}")
        return []


def find_category_from_specific_service(specific_service: str) -> str:
    """
    Smart category lookup: derive primary category from specific service
    Uses DockSide Pros service dictionary to avoid defaulting to "Boater Resources"
    
    Example: "Outboard Engine Repair" → "Engines and Generators"
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not specific_service:
        return "Boater Resources"
    
    # DockSide Pros Service Dictionary
    SERVICE_CATEGORY_MAPPINGS = {
        "Engines and Generators": [
            "Engines and Generators Sales/Service", "Generator Sales or Service",
            "Engine Service or Sales", "Outboard Engine Service", "Inboard Engine Service", 
            "Outboard Engine Repair", "Inboard Engine Repair", "Generator Repair",
            "Motor Repair", "Engine Installation", "Generator Installation",
            "Diesel Engine Service", "Gas Engine Service", "Marine Engine Repair",
            "Outboard Engine Service", "Inboard Engine Service"
        ],
        
        "Boat Maintenance": [
            "Ceramic Coating", "Boat Detailing", "Bottom Cleaning",
            "Boat and Yacht Maintenance", "Boat Oil Change", "Bilge Cleaning",
            "Jet Ski Maintenance", "Barnacle Cleaning", "Yacht Fire Detection Systems",
            "Boat Wrapping and Marine Protection Film", "Boat Cleaning", "Boat Washing"
        ],
        
        "Marine Systems": [
            "Marine Systems Install and Sales", "Yacht Stabilizers and Seakeepers",
            "Instrument Panel and Dashboard", "Yacht AC Sales", "Yacht AC Service",
            "Boat Electrical Service", "Boat Sound Systems", "Yacht Plumbing",
            "Boat Lighting", "Yacht Refrigeration and Watermakers", "Marine Electronics"
        ],
        
        "Boat and Yacht Repair": [
            "Boat and Yacht Repair", "Fiberglass Repair", "Welding & Metal Fabrication",
            "Carpentry & Woodwork", "Riggers & Masts", "Jet Ski Repair",
            "Boat Canvas and Upholstery", "Boat Decking and Yacht Flooring"
        ]
    }
    
    # Keyword mappings for partial matches
    KEYWORD_MAPPINGS = {
        "engine": "Engines and Generators",
        "motor": "Engines and Generators", 
        "generator": "Engines and Generators",
        "outboard": "Engines and Generators",
        "inboard": "Engines and Generators",
        "diesel": "Engines and Generators",
        "detailing": "Boat Maintenance",
        "cleaning": "Boat Maintenance",
        "maintenance": "Boat Maintenance",
        "ceramic": "Boat Maintenance",
        "repair": "Boat and Yacht Repair",
        "fiberglass": "Boat and Yacht Repair",
        "electrical": "Marine Systems",
        "plumbing": "Marine Systems",
        "ac service": "Marine Systems"
    }
    
    specific_lower = specific_service.lower().strip()
    
    # Method 1: Exact match
    for category, services in SERVICE_CATEGORY_MAPPINGS.items():
        for service in services:
            if specific_lower == service.lower():
                logger.info(f"🎯 Exact service match: '{specific_service}' → {category}")
                return category
    
    # Method 2: Partial match
    for category, services in SERVICE_CATEGORY_MAPPINGS.items():
        for service in services:
            if specific_lower in service.lower() or service.lower() in specific_lower:
                logger.info(f"🎯 Partial service match: '{specific_service}' → {category} (matched: {service})")
                return category
    
    # Method 3: Keyword match
    for keyword, category in KEYWORD_MAPPINGS.items():
        if keyword in specific_lower:
            logger.info(f"🎯 Keyword match: '{specific_service}' → {category} (keyword: {keyword})")
            return category
    
    # Default fallback
    logger.warning(f"⚠️ No category match found for '{specific_service}' - defaulting to Boater Resources")
    return "Boater Resources"


async def _process_single_unassigned_lead(ghl_lead: Dict[str, Any], account_id: str) -> Dict[str, Any]:
    """
    Process a single unassigned lead: CREATE IN DATABASE FIRST, then route
    FIXED: Now creates leads in local database before attempting routing
    """
    lead_result = {
        "ghl_contact_id": ghl_lead.get('ghl_contact_id'),
        "customer_name": ghl_lead.get('name'),
        "assignment_successful": False,
        "assigned_vendor": None,
        "matching_vendors_count": 0,
        "error_message": None,
        "service_category": None,
        "zip_code": None,
        "database_lead_created": False,
        "opportunity_created": False,
        "processing_method": "bulk_assignment_pipeline"
    }
    
    try:
        contact_id = ghl_lead.get('ghl_contact_id')
        if not contact_id:
            lead_result["error_message"] = "No GHL contact ID provided"
            return lead_result
        
        logger.info(f"🔄 Processing bulk lead: {contact_id} - {ghl_lead.get('name')}")
        
        # Step 1: Check if database lead already exists (avoid duplicates)
        existing_lead = db.get_lead_by_ghl_contact_id(contact_id)
        
        lead_id = None
        opportunity_id = None
        
        if existing_lead:
            logger.info(f"📋 Database lead already exists: {existing_lead['id']}")
            lead_id = existing_lead['id']
            opportunity_id = existing_lead.get('ghl_opportunity_id')
            lead_result["database_lead_created"] = False  # Already existed
            
            # Extract existing lead data for routing (don't overwrite)
            service_category = existing_lead.get('primary_service_category') or existing_lead.get('service_category', '')
            zip_code = existing_lead.get('service_zip_code') or existing_lead.get('customer_zip_code', '')
            
            # If existing lead has incomplete data, try to update from GHL
            if not service_category or service_category == 'Boater Resources' or not zip_code:
                logger.info(f"🔄 Existing lead has incomplete data, checking GHL for updates...")
                
                # Get full contact data from GHL
                from api.services.ghl_api import GoHighLevelAPI
                from config import AppConfig
                
                ghl_api = GoHighLevelAPI(
                    location_id=AppConfig.GHL_LOCATION_ID,
                    private_token=AppConfig.GHL_PRIVATE_TOKEN
                )
                
                contact_response = ghl_api.get_contact(contact_id)
                if contact_response.get('success'):
                    full_contact = contact_response.get('contact', {})
                    custom_fields = full_contact.get('customFields', {})
                    
                    # Extract specific service from custom fields
                    specific_service = ""
                    if isinstance(custom_fields, dict):
                        specific_service = custom_fields.get('FT85QGi0tBq1AfVGNJ9v', '')
                    elif isinstance(custom_fields, list):
                        for field in custom_fields:
                            if isinstance(field, dict) and field.get('id') == 'FT85QGi0tBq1AfVGNJ9v':
                                specific_service = field.get('value', '')
                                break
                    
                    # Update service category if we found specific service
                    if specific_service and (not service_category or service_category == 'Boater Resources'):
                        service_category = find_category_from_specific_service(specific_service)
                        logger.info(f"🎯 Updated service category from GHL: {service_category}")
                        
                        # Update database with new category (but preserve source and created_at)
                        try:
                            db.update_lead_field(lead_id, 'primary_service_category', service_category)
                            db.update_lead_field(lead_id, 'specific_service_requested', specific_service)
                        except:
                            pass
                    
                    # Update ZIP if missing
                    if not zip_code:
                        zip_code = full_contact.get('postalCode', '')
                        if zip_code:
                            try:
                                db.update_lead_field(lead_id, 'customer_zip_code', zip_code)
                            except:
                                pass
            
        else:
            # Step 2: CREATE LEAD IN DATABASE (same pipeline as webhooks)
            logger.info(f"➕ Creating new database lead for contact {contact_id}")
            
            try:
                # Use the shared pipeline to create lead + opportunity
                from api.routes.webhook_routes import create_lead_from_ghl_contact
                
                # Convert GHL lead data to the format expected by create_lead_from_ghl_contact
                ghl_contact_data = {
                    'id': contact_id,
                    'firstName': ghl_lead.get('name', '').split(' ')[0] if ghl_lead.get('name') else '',
                    'lastName': ' '.join(ghl_lead.get('name', '').split(' ')[1:]) if ghl_lead.get('name') and len(ghl_lead.get('name', '').split(' ')) > 1 else '',
                    'email': ghl_lead.get('email', ''),
                    'phone': ghl_lead.get('phone', ''),
                    'address1': ghl_lead.get('address', ''),
                    'city': ghl_lead.get('city', ''),
                    'state': ghl_lead.get('state', ''),
                    'postalCode': ghl_lead.get('postal_code', ''),
                    'customFields': ghl_lead.get('custom_fields', {})
                }
                
                # Create lead using shared pipeline (same as webhooks)
                lead_id, opportunity_id = await create_lead_from_ghl_contact(
                    ghl_contact_data=ghl_contact_data,
                    account_id=account_id,
                    form_identifier="bulk_assignment"
                )
                
                logger.info(f"✅ Created database lead: {lead_id}")
                if opportunity_id:
                    logger.info(f"✅ Created opportunity: {opportunity_id}")
                
                lead_result["database_lead_created"] = True
                lead_result["opportunity_created"] = bool(opportunity_id)
                
                # Extract service category and ZIP for routing
                # Try to get specific service from custom fields
                custom_fields = ghl_contact_data.get('customFields', {})
                specific_service = ""
                
                # Handle custom fields as either dict or list
                if isinstance(custom_fields, dict):
                    # Look for specific service in custom fields (GHL field ID for specific_service_requested)
                    for field_id, field_value in custom_fields.items():
                        if field_id == 'FT85QGi0tBq1AfVGNJ9v':  # specific_service_requested field ID
                            specific_service = field_value
                            break
                elif isinstance(custom_fields, list):
                    # Handle list format (GHL sometimes returns as list of {id, value} objects)
                    for field in custom_fields:
                        if isinstance(field, dict) and field.get('id') == 'FT85QGi0tBq1AfVGNJ9v':
                            specific_service = field.get('value', '')
                            break
                
                # Smart category lookup from specific service
                if specific_service:
                    service_category = find_category_from_specific_service(specific_service)
                    logger.info(f"🧠 Smart lookup: '{specific_service}' → {service_category}")
                else:
                    # Try to extract from lead data before defaulting
                    service_category = ghl_lead.get('service_category', '')
                    if not service_category:
                        service_category = "Boater Resources"  # Final fallback
                        logger.warning(f"⚠️ No service category found for {contact_id}, using default")
                
                zip_code = ghl_lead.get('postal_code', '')
                
            except Exception as create_error:
                logger.error(f"❌ Failed to create database lead: {create_error}")
                lead_result["error_message"] = f"Lead creation failed: {create_error}"
                return lead_result
        
        # Step 3: Apply routing algorithm (same as webhooks)
        if lead_id and service_category:
            logger.info(f"🎯 Applying routing algorithm to lead {lead_id}")
            
            lead_result["service_category"] = service_category
            lead_result["zip_code"] = zip_code
            
            # Apply routing algorithm (same as webhook leads)
            if service_category and zip_code:
                logger.info(f"🔍 Finding vendors for {service_category} in {zip_code}")
                
                # Use the same routing service as webhooks
                from api.services.lead_routing_service import lead_routing_service
                
                matching_vendors = lead_routing_service.find_matching_vendors(
                    account_id=account_id,
                    service_category=service_category,
                    zip_code=zip_code,
                    priority="normal"
                )
                
                lead_result["matching_vendors_count"] = len(matching_vendors)
                
                if matching_vendors:
                    # Select vendor using same algorithm as webhooks (respects 70/30 setting)
                    selected_vendor = lead_routing_service.select_vendor_from_pool(
                        matching_vendors, account_id
                    )
                    
                    if selected_vendor:
                        # Assign to database (same as webhooks)
                        assignment_success = db.assign_lead_to_vendor(lead_id, selected_vendor['id'])
                        
                        if assignment_success:
                            logger.info(f"✅ Assigned lead {lead_id} to vendor {selected_vendor['name']}")
                            
                            # Update GHL opportunity (same as webhooks)
                            vendor_ghl_user_id = selected_vendor.get("ghl_user_id")
                            if vendor_ghl_user_id and opportunity_id:
                                logger.info(f"📋 Assigning opportunity {opportunity_id} to vendor {vendor_ghl_user_id}")
                                
                                try:
                                    from api.services.ghl_api import GoHighLevelAPI
                                    from config import AppConfig
                                    
                                    ghl_api_client = GoHighLevelAPI(
                                        private_token=AppConfig.GHL_PRIVATE_TOKEN,
                                        location_id=AppConfig.GHL_LOCATION_ID
                                    )
                                    
                                    assignment_result = ghl_api_client.update_opportunity(opportunity_id, {
                                        'assignedTo': vendor_ghl_user_id,
                                        'pipelineId': AppConfig.PIPELINE_ID,
                                        'pipelineStageId': AppConfig.NEW_LEAD_STAGE_ID
                                    })
                                    
                                    if assignment_result:
                                        logger.info(f"✅ Successfully assigned opportunity to {selected_vendor['name']}")
                                        lead_result["assignment_successful"] = True
                                        lead_result["assigned_vendor"] = selected_vendor
                                    else:
                                        logger.error(f"❌ Failed to update opportunity assignment")
                                        lead_result["error_message"] = "Failed to update GHL opportunity"
                                        
                                except Exception as opp_error:
                                    logger.error(f"❌ Error updating opportunity: {opp_error}")
                                    lead_result["error_message"] = f"Opportunity update error: {opp_error}"
                            else:
                                logger.warning(f"⚠️ Vendor {selected_vendor['name']} missing GHL user ID or no opportunity")
                                lead_result["assignment_successful"] = True  # Database assignment worked
                                lead_result["assigned_vendor"] = selected_vendor
                                lead_result["error_message"] = "Assigned but vendor missing GHL user ID"
                        else:
                            logger.error(f"❌ Failed to assign lead to vendor in database")
                            lead_result["error_message"] = "Database assignment failed"
                    else:
                        logger.warning(f"⚠️ No vendor selected from {len(matching_vendors)} matching vendors")
                        lead_result["error_message"] = "No vendor selected from pool"
                else:
                    logger.warning(f"⚠️ No matching vendors found for {service_category} in {zip_code}")
                    lead_result["error_message"] = "No matching vendors found"
            else:
                logger.warning(f"⚠️ Missing service category or ZIP code for routing")
                lead_result["error_message"] = f"Missing routing data: category={service_category}, zip={zip_code}"
        else:
            logger.error(f"❌ Missing lead_id or service_category for routing")
            lead_result["error_message"] = f"Missing lead_id ({lead_id}) or service_category ({service_category})"
        
        return lead_result
        
    except Exception as e:
        logger.error(f"❌ Error processing lead {contact_id}: {e}")
        lead_result["error_message"] = f"Processing error: {e}"
        return lead_result

