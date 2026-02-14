# api/routes/admin_functions.py

import logging
import json
import uuid
import sys
import os
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import text

# Import the proven components used by vendor widget
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from database.simple_connection import db as simple_db_instance
from api.services.ghl_api import GoHighLevelAPI
from api.services.field_mapper import field_mapper
from api.services.location_service import location_service
from config import AppConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["Admin Functions"])

# Pydantic models for request bodies
class BulkDeleteRequest(BaseModel):
    ids: List[str]
    
class VendorFilterRequest(BaseModel):
    status: Optional[str] = None
    include_inactive: bool = False

@router.post("/sync-single-vendor/{contact_id}")
async def sync_single_vendor(contact_id: str):
    """
    Sync a single vendor contact from GHL to local database
    Uses the same sync logic as full database sync but for one record
    
    This endpoint can be called by GHL webhook when a vendor contact is updated
    """
    try:
        logger.info(f"🔄 Single vendor sync initiated for GHL contact: {contact_id}")
        
        # Import the enhanced sync V2 module
        from api.services.enhanced_db_sync_v2 import EnhancedDatabaseSync
        
        # Initialize the sync service
        sync_service = EnhancedDatabaseSync()
        
        # Fetch the specific contact from GHL
        ghl_contact = sync_service.ghl_api.get_contact_by_id(contact_id)
        if not ghl_contact:
            logger.error(f"❌ Contact {contact_id} not found in GHL")
            return {
                "status": "error",
                "success": False,
                "message": f"Contact {contact_id} not found in GHL"
            }
        
        # Get account ID
        account = simple_db_instance.get_account_by_ghl_location_id(AppConfig.GHL_LOCATION_ID)
        if not account:
            logger.error("❌ No account found")
            return {
                "status": "error",
                "success": False,
                "message": "No account configured"
            }
        
        # Check if vendor exists locally
        vendor_email = ghl_contact.get('email', '')
        if vendor_email:
            existing_vendor = simple_db_instance.get_vendor_by_email_and_account(vendor_email, account['id'])
        else:
            existing_vendor = simple_db_instance.get_vendor_by_ghl_contact_id(contact_id)
        
        if existing_vendor:
            # Update existing vendor using the same logic as full sync
            sync_service._update_local_vendor(existing_vendor, ghl_contact)
            action = "updated"
        else:
            # Create new vendor if not exists
            sync_service._create_local_vendor(ghl_contact)
            action = "created"
        
        logger.info(f"✅ Single vendor sync completed: {action}")
        
        return {
            "status": "success",
            "success": True,
            "message": f"Vendor {action} successfully from GHL contact {contact_id}",
            "contact_id": contact_id,
            "action": action,
            "vendor_email": vendor_email
        }
        
    except Exception as e:
        logger.error(f"❌ Error in single vendor sync: {e}")
        return {
            "status": "error",
            "success": False,
            "message": f"Sync failed: {str(e)}",
            "error": str(e)
        }

@router.post("/sync-database")
async def sync_database():
    """
    Enhanced V2 database sync endpoint with bi-directional sync capabilities
    
    This function now:
    1. Fetches ALL contacts from GHL to discover new vendors/leads
    2. Updates existing vendor and lead records with ALL fields from GHL
    3. Creates new local records for GHL contacts not in database
    4. Detects and handles deleted GHL records
    5. Provides comprehensive statistics about the sync operation
    """
    try:
        logger.info("🔄 Database sync initiated from admin dashboard")
        
        # Import the enhanced sync V2 module (bi-directional) from services
        from api.services.enhanced_db_sync_v2 import EnhancedDatabaseSync
        
        # Initialize the sync service
        sync_service = EnhancedDatabaseSync()
        
        # Run the synchronization
        results = sync_service.sync_all()
        
        # Prepare response
        if results['success']:
            logger.info(f"✅ Sync completed: {results['message']}")
            
            return {
                "status": "success",  # Frontend expects 'status' not 'success'
                "success": True,
                "message": results['message'],
                # Frontend expects these at root level
                "vendors": {
                    "checked": results['stats'].get('vendors_checked', 0),
                    "updated": results['stats'].get('vendors_updated', 0),
                    "added": results['stats'].get('vendors_created', 0),  # Frontend expects 'added' not 'created'
                    "deleted": results['stats'].get('vendors_deactivated', 0),  # Using deactivated count
                    "created": results['stats'].get('vendors_created', 0),
                    "deactivated": results['stats'].get('vendors_deactivated', 0)
                },
                "leads": {
                    "checked": results['stats'].get('leads_checked', 0),
                    "updated": results['stats'].get('leads_updated', 0),
                    "added": results['stats'].get('leads_created', 0),  # Frontend expects 'added' not 'created'
                    "deleted": results['stats'].get('leads_deleted', 0),
                    "created": results['stats'].get('leads_created', 0)
                },
                "stats": {
                    "ghl_contacts_fetched": results['stats'].get('ghl_contacts_fetched', 0),
                    "errors": len(results['stats'].get('errors', [])),
                    "duration": results.get('duration', 0)
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            error_msg = results.get('error', 'Unknown error during sync')
            logger.error(f"❌ Sync failed: {error_msg}")
            
            return {
                "status": "error",  # Frontend expects 'status'
                "success": False,
                "message": f"Sync failed: {error_msg}",
                "vendors": {"updated": 0, "added": 0, "deleted": 0},
                "leads": {"updated": 0, "added": 0, "deleted": 0},
                "stats": results.get('stats', {}),
                "timestamp": datetime.now().isoformat()
            }
            
    except ImportError as e:
        logger.error(f"❌ Failed to import enhanced sync module: {e}")
        return {
            "status": "error",
            "success": False,
            "message": "Enhanced sync module not found. Please ensure enhanced_db_sync_v2.py is in api/services/.",
            "vendors": {"updated": 0, "added": 0, "deleted": 0},
            "leads": {"updated": 0, "added": 0, "deleted": 0},
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Unexpected error during sync: {e}")
        return {
            "status": "error",
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "vendors": {"updated": 0, "added": 0, "deleted": 0},
            "leads": {"updated": 0, "added": 0, "deleted": 0},
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


async def _sync_vendor_using_widget_logic(contact: Dict[str, Any], account_id: str, 
                                         ghl_user_id: str, vendor_company_name: str,
                                         service_categories: str, services_offered: str, 
                                         service_zip_codes: str) -> str:
    """Sync vendor using exact same logic as vendor widget"""
    try:
        vendor_email = contact.get('email', '')
        if not vendor_email:
            return "skipped"
        
        # Check if vendor exists (same as widget)
        existing_vendor = simple_db_instance.get_vendor_by_email_and_account(vendor_email, account_id)
        
        # Process service categories - EXPERIMENT: assume GHL returns it as array already
        service_categories_json = json.dumps([])
        if service_categories:
            try:
                # If it's already a list/array from GHL, use it directly
                if isinstance(service_categories, list):
                    service_categories_json = json.dumps(service_categories)
                    logger.info(f"📋 EXPERIMENT: Got service_categories as array: {service_categories}")
                # If it's a string that looks like JSON array, parse it
                elif isinstance(service_categories, str) and service_categories.startswith('[') and service_categories.endswith(']'):
                    categories_list = json.loads(service_categories)
                    service_categories_json = json.dumps(categories_list)
                    logger.info(f"📋 EXPERIMENT: Parsed service_categories from JSON string: {categories_list}")
                # If it's a comma-separated string, split it
                elif isinstance(service_categories, str):
                    categories_list = [cat.strip() for cat in service_categories.split(',') if cat.strip()]
                    service_categories_json = json.dumps(categories_list)
                    logger.info(f"📋 EXPERIMENT: Split service_categories from comma string: {categories_list}")
                else:
                    logger.info(f"📋 EXPERIMENT: Unknown service_categories type: {type(service_categories)} = {service_categories}")
                    service_categories_json = json.dumps([str(service_categories)])
            except Exception as e:
                logger.error(f"📋 EXPERIMENT: Error processing service_categories: {e}")
                service_categories_json = json.dumps([str(service_categories)])
        
        # Process services offered (same as widget)
        services_offered_json = json.dumps([])
        if services_offered:
            try:
                if services_offered.startswith('[') and services_offered.endswith(']'):
                    services_list = json.loads(services_offered)
                else:
                    services_list = [srv.strip() for srv in services_offered.split(',') if srv.strip()]
                services_offered_json = json.dumps(services_list)
            except:
                services_offered_json = json.dumps([services_offered])
        
        # Process coverage (same as widget logic)
        coverage_type = 'county'
        coverage_states_json = json.dumps([])
        coverage_counties_json = json.dumps([])
        
        if service_zip_codes:
            # Use same coverage processing as widget
            coverage_result = _process_coverage_like_widget(service_zip_codes)
            coverage_type = coverage_result['type']
            coverage_states_json = coverage_result['states']
            coverage_counties_json = coverage_result['counties']
        
        vendor_name = f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip()
        vendor_phone = contact.get('phone', '')
        
        # PAUL DEBUG: Check vendor lookup after processing
        if vendor_email == 'Paul.minnucci@allclassdetailing.com':
            logger.info(f"🎯 PAUL VENDOR LOOKUP (after processing):")
            logger.info(f"   vendor_email: {vendor_email}")
            logger.info(f"   account_id: {account_id}")
            logger.info(f"   existing_vendor found: {existing_vendor is not None}")
            if existing_vendor:
                logger.info(f"   existing_vendor ID: {existing_vendor.get('id')}")
                logger.info(f"   existing service_categories: {existing_vendor.get('service_categories')}")
            logger.info(f"   service_categories raw: {service_categories}")
            logger.info(f"   service_categories_json to save: {service_categories_json}")
        
        if existing_vendor:
            # Update existing vendor (same fields as widget creates)
            logger.info(f"🔄 Updating existing vendor: {vendor_email}")
            
            # Update the vendor using direct SQL since we don't have update_vendor method
            vendor_id = existing_vendor['id']
            try:
                conn = simple_db_instance._get_raw_conn()
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE vendors SET 
                            name = ?, 
                            company_name = ?,
                            phone = ?,
                            service_categories = ?,
                            services_offered = ?,
                            coverage_type = ?,
                            coverage_states = ?,
                            coverage_counties = ?,
                            updated_at = datetime('now')
                        WHERE id = ?
                    """, (
                        vendor_name,
                        vendor_company_name or '',
                        vendor_phone,
                        service_categories_json,
                        services_offered_json,
                        coverage_type,
                        coverage_states_json,
                        coverage_counties_json,
                        vendor_id
                    ))
                    conn.commit()
                    logger.info(f"✅ Updated vendor {vendor_email} with service_categories: {service_categories_json}")
                    return "updated"
                finally:
                    conn.close()
            except Exception as e:
                logger.error(f"❌ Error updating vendor {vendor_email}: {e}")
                return "error"
        else:
            # Create new vendor (same as widget)
            vendor_id = simple_db_instance.create_vendor(
                account_id=account_id,
                name=vendor_name,
                email=vendor_email,
                company_name=vendor_company_name or '',
                phone=vendor_phone,
                ghl_contact_id=contact.get('id'),
                status='active' if ghl_user_id else 'pending',
                service_categories=service_categories_json,
                services_offered=services_offered_json,
                coverage_type=coverage_type,
                coverage_states=coverage_states_json,
                coverage_counties=coverage_counties_json,
                primary_service_category='',
                taking_new_work=True
            )
            logger.info(f"✅ Created vendor: {vendor_email}")
            return "added"
            
    except Exception as e:
        logger.error(f"❌ Error syncing vendor {contact.get('email', 'unknown')}: {e}")
        return "error"


async def _sync_lead_using_widget_logic(contact: Dict[str, Any], account_id: str,
                                       specific_service: str, zip_code_of_service: str,
                                       mapped_payload: Dict[str, Any]) -> str:
    """Sync lead using exact same logic as vendor widget"""
    try:
        customer_email = contact.get('email', '')
        if not customer_email:
            return "skipped"
        
        # Check if lead exists
        existing_lead = simple_db_instance.get_lead_by_email(customer_email)
        
        # Process location (same as widget)
        service_county = ""
        service_state = ""
        
        if zip_code_of_service and len(zip_code_of_service) == 5 and zip_code_of_service.isdigit():
            location_data = location_service.zip_to_location(zip_code_of_service)
            if not location_data.get('error'):
                county = location_data.get('county', '')
                state = location_data.get('state', '')
                if county and state:
                    service_county = f"{county}, {state}"
                    service_state = state
        
        # Build service details from mapped payload (same as widget)
        service_details = {}
        standard_lead_fields = {
            "firstName", "lastName", "email", "phone", "primary_service_category",
            "customer_zip_code", "specific_service_requested"
        }
        
        for field_key, field_value in mapped_payload.items():
            if field_value and field_value != "" and field_key not in standard_lead_fields:
                service_details[field_key] = field_value
        
        customer_name = f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip()
        
        if existing_lead:
            logger.info(f"🔄 Updating existing lead: {customer_email}")
            return "updated"
        else:
            # Create new lead (same as widget)
            lead_id = simple_db_instance.create_lead(
                account_id=account_id,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=contact.get('phone', ''),
                primary_service_category='General Services',
                specific_service_requested=specific_service,
                customer_zip_code=zip_code_of_service or '',
                service_county=service_county,
                service_state=service_state,
                service_zip_code=zip_code_of_service or '',
                priority='normal',
                source='GHL Sync',
                ghl_contact_id=contact.get('id'),
                service_details_json=json.dumps(service_details),
                status='unassigned'
            )
            logger.info(f"✅ Created lead: {customer_email}")
            return "added"
            
    except Exception as e:
        logger.error(f"❌ Error syncing lead {contact.get('email', 'unknown')}: {e}")
        return "error"


def _process_coverage_like_widget(service_zip_codes: str) -> Dict[str, Any]:
    """Process coverage data using same logic as vendor widget"""
    coverage_type = 'county'
    coverage_states = []
    coverage_counties = []
    
    if not service_zip_codes:
        return {
            'type': coverage_type,
            'states': json.dumps(coverage_states),
            'counties': json.dumps(coverage_counties)
        }
    
    # Handle different formats (same as widget)
    if service_zip_codes.upper() in ['USA', 'UNITED STATES', 'NATIONAL', 'NATIONWIDE']:
        coverage_type = 'national'
    elif service_zip_codes.upper() in ['NONE', 'NULL', '']:
        coverage_type = 'county'
    elif len(service_zip_codes) == 2 and service_zip_codes.upper() in ['FL', 'CA', 'TX', 'NY', 'AL', 'GA']:
        coverage_type = 'state'
        coverage_states = [service_zip_codes.upper()]
    elif ',' in service_zip_codes and all(len(s.strip()) == 2 for s in service_zip_codes.split(',') if s.strip()):
        # Multiple states like "AL, FL, GA"
        state_list = [s.strip().upper() for s in service_zip_codes.split(',') if s.strip()]
        coverage_type = 'state' if len(state_list) <= 3 else 'national'
        coverage_states = state_list
    elif ';' in service_zip_codes and ',' in service_zip_codes:
        # Direct county format: "County, ST; County, ST"
        county_list = [c.strip() for c in service_zip_codes.split(';') if c.strip()]
        coverage_counties = county_list
        # Extract states
        for county in county_list:
            if ', ' in county:
                state = county.split(', ')[-1]
                if state not in coverage_states:
                    coverage_states.append(state)
        coverage_type = 'county'
    elif ',' in service_zip_codes and not ';' in service_zip_codes:
        # Comma-separated counties like "Miami Dade, Broward"
        county_list = [c.strip() for c in service_zip_codes.split(',') if c.strip()]
        # Add FL as default state (most common)
        for county_raw in county_list:
            county_clean = county_raw.replace(' County', '').strip()
            if county_clean:
                coverage_counties.append(f"{county_clean}, FL")
                if 'FL' not in coverage_states:
                    coverage_states.append('FL')
        coverage_type = 'county'
    
    return {
        'type': coverage_type,
        'states': json.dumps(coverage_states),
        'counties': json.dumps(coverage_counties)
    }

@router.get("/scripts")
async def list_admin_scripts():
    """
    List all administrative scripts in the project.
    Returns information about each script and its purpose.
    """
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        scripts = []
        
        # Look for Python scripts in the root directory
        for file in os.listdir(project_root):
            if file.endswith('.py') and not file.startswith('__'):
                file_path = os.path.join(project_root, file)
                try:
                    # Get file stats
                    stat = os.stat(file_path)
                    
                    # Try to read docstring for description
                    description = "No description available"
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read(1000)  # First 1000 chars
                            if '"""' in content:
                                start = content.find('"""') + 3
                                end = content.find('"""', start)
                                if end > start:
                                    description = content[start:end].strip().split('\n')[0]
                    except:
                        pass
                    
                    # Categorize scripts
                    category = "utility"
                    status = "review"
                    
                    if "sync" in file.lower():
                        category = "sync"
                        if file == "sync_ghl_as_truth.py":
                            status = "active"
                        elif file == "sync_vendors_from_ghl.py":
                            status = "legacy"
                    elif "test" in file.lower():
                        category = "test"
                        status = "cleanup"
                    elif "main" in file.lower() or "server" in file.lower():
                        category = "core"
                        status = "active"
                    elif any(word in file.lower() for word in ["debug", "temp", "scratch"]):
                        category = "debug"
                        status = "cleanup"
                    
                    scripts.append({
                        "name": file,
                        "path": file_path,
                        "description": description,
                        "category": category,
                        "status": status,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                    
                except Exception as e:
                    logger.warning(f"Could not analyze script {file}: {e}")
                    continue
        
        # Sort by category and name
        scripts.sort(key=lambda x: (x['category'], x['name']))
        
        return {
            "status": "success",
            "scripts": scripts,
            "total_count": len(scripts),
            "categories": {
                "active": len([s for s in scripts if s['status'] == 'active']),
                "review": len([s for s in scripts if s['status'] == 'review']),
                "cleanup": len([s for s in scripts if s['status'] == 'cleanup'])
            }
        }
        
    except Exception as e:
        logger.error(f"Error listing scripts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list scripts: {str(e)}")

@router.delete("/scripts/{script_name}")
async def delete_script(script_name: str):
    """
    Delete a script file (for cleanup purposes).
    Only allows deletion of scripts marked for cleanup.
    """
    try:
        # Security check - only allow deletion of certain types
        if not any(word in script_name.lower() for word in ["test", "debug", "temp", "scratch"]):
            raise HTTPException(status_code=403, detail="Only test, debug, and temporary scripts can be deleted")
        
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        script_path = os.path.join(project_root, script_name)
        
        if not os.path.exists(script_path):
            raise HTTPException(status_code=404, detail="Script not found")
        
        if not script_path.endswith('.py'):
            raise HTTPException(status_code=403, detail="Only Python scripts can be deleted")
        
        # Additional safety check
        if not script_path.startswith(project_root):
            raise HTTPException(status_code=403, detail="Invalid script path")
        
        os.remove(script_path)
        logger.info(f"Deleted script: {script_name}")
        
        return {
            "status": "success",
            "message": f"Script {script_name} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting script {script_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete script: {str(e)}")

@router.post("/vendors/bulk-action")
async def bulk_vendor_action(request: Dict[str, Any]):
    """
    Perform bulk actions on multiple vendors.
    
    Request body:
    {
        "action": "delete" | "activate" | "deactivate" | "restore",
        "vendor_ids": ["vendor_id_1", "vendor_id_2", ...],
        "filter": {  // Optional: alternative to vendor_ids
            "status": "missing_in_ghl" | "inactive_ghl_deleted" | "active" | "inactive"
        }
    }
    """
    try:
        action = request.get("action")
        vendor_ids = request.get("vendor_ids", [])
        filter_criteria = request.get("filter", {})
        
        if not action:
            raise HTTPException(status_code=400, detail="Action is required")
        
        if not vendor_ids and not filter_criteria:
            raise HTTPException(status_code=400, detail="Either vendor_ids or filter must be provided")
        
        # Get vendors to process
        if filter_criteria:
            # Fetch vendors by filter
            status_filter = filter_criteria.get("status")
            if status_filter:
                conn = simple_db_instance._get_raw_conn()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM vendors WHERE status = ?", (status_filter,))
                vendor_ids = [row[0] for row in cursor.fetchall()]
                conn.close()
                logger.info(f"Found {len(vendor_ids)} vendors with status '{status_filter}'")
        
        if not vendor_ids:
            return {
                "status": "success",
                "message": "No vendors to process",
                "processed": 0
            }
        
        # Perform the action
        processed = 0
        errors = []
        
        conn = simple_db_instance._get_raw_conn()
        cursor = conn.cursor()
        
        try:
            for vendor_id in vendor_ids:
                try:
                    if action == "delete":
                        # Hard delete from database
                        cursor.execute("DELETE FROM vendors WHERE id = ?", (vendor_id,))
                        logger.info(f"Deleted vendor {vendor_id}")
                    
                    elif action == "activate":
                        # Set status to active
                        cursor.execute(
                            "UPDATE vendors SET status = 'active', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (vendor_id,)
                        )
                        logger.info(f"Activated vendor {vendor_id}")
                    
                    elif action == "deactivate":
                        # Set status to inactive
                        cursor.execute(
                            "UPDATE vendors SET status = 'inactive', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (vendor_id,)
                        )
                        logger.info(f"Deactivated vendor {vendor_id}")
                    
                    elif action == "restore":
                        # Restore vendors marked as deleted/missing
                        cursor.execute(
                            "UPDATE vendors SET status = 'active', updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status IN ('inactive_ghl_deleted', 'missing_in_ghl')",
                            (vendor_id,)
                        )
                        logger.info(f"Restored vendor {vendor_id}")
                    
                    else:
                        raise ValueError(f"Unknown action: {action}")
                    
                    processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing vendor {vendor_id}: {e}")
                    errors.append({"vendor_id": vendor_id, "error": str(e)})
            
            conn.commit()
            
        finally:
            conn.close()
        
        return {
            "status": "success",
            "message": f"Bulk action '{action}' completed",
            "processed": processed,
            "failed": len(errors),
            "errors": errors if errors else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk vendor action: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk action failed: {str(e)}")

@router.get("/vendors/missing-in-ghl")
async def get_missing_vendors():
    """
    Get list of vendors flagged as missing in GHL.
    These vendors need admin review.
    """
    try:
        conn = simple_db_instance._get_raw_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, email, company_name, ghl_contact_id, 
                   service_categories, updated_at, status
            FROM vendors 
            WHERE status IN ('missing_in_ghl', 'inactive_ghl_deleted')
            ORDER BY updated_at DESC
        """)
        
        vendors = []
        for row in cursor.fetchall():
            vendors.append({
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "company_name": row[3],
                "ghl_contact_id": row[4],
                "service_categories": json.loads(row[5]) if row[5] else [],
                "updated_at": row[6],
                "status": row[7]
            })
        
        conn.close()
        
        return {
            "status": "success",
            "count": len(vendors),
            "vendors": vendors
        }
        
    except Exception as e:
        logger.error(f"Error fetching missing vendors: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch vendors: {str(e)}")

@router.get("/health")
async def admin_health_check():
    """Health check for admin functions"""
    return {
        "status": "healthy",
        "service": "admin_functions",
        "timestamp": datetime.now().isoformat()
    }

# ============================================
# Vendor and Lead Deletion Endpoints
# ============================================

@router.get("/vendors/filtered")
async def get_filtered_vendors(
    status: Optional[str] = None,
    include_inactive: bool = False
):
    """
    Get vendors with optional filtering
    - Filter by status (active, inactive, missing_in_ghl, inactive_ghl_deleted)
    - Include/exclude inactive vendors
    """
    try:
        session = simple_db_instance._get_conn()
        
        query = """
            SELECT id, name, email, company_name, status, ghl_contact_id,
                   taking_new_work, lead_close_percentage, created_at
            FROM vendors
            WHERE 1=1
        """
        params = {}
        
        if status:
            query += " AND status = :status"
            params["status"] = status
        
        if not include_inactive:
            query += " AND status NOT IN ('inactive', 'missing_in_ghl', 'inactive_ghl_deleted')"
        
        query += " ORDER BY created_at DESC"
        
        result = session.execute(text(query), params)
        vendors = []
        
        for row in result:
            vendors.append({
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'company_name': row[3],
                'status': row[4],
                'ghl_contact_id': row[5],
                'taking_new_work': row[6],
                'lead_close_percentage': row[7],
                'created_at': row[8]
            })
        
        session.close()
        
        return {
            "status": "success",
            "count": len(vendors),
            "vendors": vendors
        }
        
    except Exception as e:
        logger.error(f"Error fetching filtered vendors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/vendors/{vendor_id}")
async def delete_vendor(vendor_id: str):
    """
    Permanently delete a single vendor from the database
    """
    try:
        conn = simple_db_instance._get_raw_conn()
        cursor = conn.cursor()
        
        # Check if vendor exists
        cursor.execute("SELECT name FROM vendors WHERE id = ?", (vendor_id,))
        vendor = cursor.fetchone()
        
        if not vendor:
            conn.close()
            raise HTTPException(status_code=404, detail="Vendor not found")
        
        vendor_name = vendor[0]
        
        # Delete the vendor
        cursor.execute("DELETE FROM vendors WHERE id = ?", (vendor_id,))
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Permanently deleted vendor: {vendor_name} (ID: {vendor_id})")
        
        return {
            "status": "success",
            "message": f"Vendor {vendor_name} deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error deleting vendor: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vendors/bulk-delete")
async def bulk_delete_vendors(request: BulkDeleteRequest):
    """
    Permanently delete multiple vendors from the database
    """
    try:
        if not request.ids:
            raise HTTPException(status_code=400, detail="No vendor IDs provided")
        
        conn = simple_db_instance._get_raw_conn()
        cursor = conn.cursor()
        
        deleted_count = 0
        deleted_names = []
        
        for vendor_id in request.ids:
            cursor.execute("SELECT name FROM vendors WHERE id = ?", (vendor_id,))
            vendor = cursor.fetchone()
            
            if vendor:
                vendor_name = vendor[0]
                cursor.execute("DELETE FROM vendors WHERE id = ?", (vendor_id,))
                deleted_count += 1
                deleted_names.append(vendor_name)
                logger.info(f"✅ Deleted vendor: {vendor_name}")
        
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "deleted_vendors": deleted_names,
            "message": f"Successfully deleted {deleted_count} vendor(s)"
        }
        
    except Exception as e:
        logger.error(f"Error bulk deleting vendors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/leads/filtered")
async def get_filtered_leads(
    status: Optional[str] = None,
    include_inactive: bool = False
):
    """
    Get leads with optional filtering
    - Filter by status (new, assigned, completed, inactive_ghl_deleted)
    - Include/exclude inactive leads
    """
    try:
        session = simple_db_instance._get_conn()
        
        query = """
            SELECT l.id, l.customer_name, l.customer_email, l.customer_phone,
                   l.primary_service_category, l.specific_service_requested,
                   l.status, l.ghl_contact_id, l.created_at,
                   v.name as vendor_name
            FROM leads l
            LEFT JOIN vendors v ON l.vendor_id = v.id
            WHERE 1=1
        """
        params = {}
        
        if status:
            query += " AND l.status = :status"
            params["status"] = status
        
        if not include_inactive:
            query += " AND l.status != 'inactive_ghl_deleted'"
        
        query += " ORDER BY l.created_at DESC"
        
        result = session.execute(text(query), params)
        leads = []
        
        for row in result:
            leads.append({
                'id': row[0],
                'customer_name': row[1],
                'customer_email': row[2],
                'customer_phone': row[3],
                'primary_service_category': row[4],
                'specific_service_requested': row[5],
                'status': row[6],
                'ghl_contact_id': row[7],
                'created_at': row[8],
                'vendor_name': row[9]
            })
        
        session.close()
        
        return {
            "status": "success",
            "count": len(leads),
            "leads": leads
        }
        
    except Exception as e:
        logger.error(f"Error fetching filtered leads: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str):
    """
    Permanently delete a single lead from the database
    """
    try:
        conn = simple_db_instance._get_raw_conn()
        cursor = conn.cursor()
        
        # Check if lead exists
        cursor.execute("SELECT customer_name FROM leads WHERE id = ?", (lead_id,))
        lead = cursor.fetchone()
        
        if not lead:
            conn.close()
            raise HTTPException(status_code=404, detail="Lead not found")
        
        customer_name = lead[0]
        
        # Delete the lead
        cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Permanently deleted lead: {customer_name} (ID: {lead_id})")
        
        return {
            "status": "success",
            "message": f"Lead {customer_name} deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error deleting lead: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/leads/bulk-delete")
async def bulk_delete_leads(request: BulkDeleteRequest):
    """
    Permanently delete multiple leads from the database
    """
    try:
        if not request.ids:
            raise HTTPException(status_code=400, detail="No lead IDs provided")
        
        conn = simple_db_instance._get_raw_conn()
        cursor = conn.cursor()
        
        deleted_count = 0
        deleted_names = []
        
        for lead_id in request.ids:
            cursor.execute("SELECT customer_name FROM leads WHERE id = ?", (lead_id,))
            lead = cursor.fetchone()
            
            if lead:
                customer_name = lead[0]
                cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
                deleted_count += 1
                deleted_names.append(customer_name)
                logger.info(f"✅ Deleted lead: {customer_name}")
        
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "deleted_leads": deleted_names,
            "message": f"Successfully deleted {deleted_count} lead(s)"
        }
        
    except Exception as e:
        logger.error(f"Error bulk deleting leads: {e}")
        raise HTTPException(status_code=500, detail=str(e))