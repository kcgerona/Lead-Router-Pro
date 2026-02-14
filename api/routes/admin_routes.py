# api/routes/admin_routes.py

import logging
import json
import csv
import io
import time
import tempfile
import os
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Database and config
from database.simple_connection import db as simple_db_instance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["Admin Dashboard"])

# Configuration - Import your config (no hardcoded fallback; use .env only)
try:
    from config import Config
    DSP_GHL_LOCATION_ID = Config.GHL_LOCATION_ID or ""
    DSP_LOCATION_PIT = Config.GHL_PRIVATE_TOKEN or ""
    DSP_AGENCY_API_KEY = getattr(Config, 'GHL_AGENCY_API_KEY', None)
except ImportError:
    DSP_GHL_LOCATION_ID = ""
    DSP_LOCATION_PIT = ""
    DSP_AGENCY_API_KEY = None

# Pydantic models for request validation
class GHLConnectionTest(BaseModel):
    locationId: str
    privateToken: str
    agencyApiKey: Optional[str] = None


class GenerateFieldReferenceRequest(BaseModel):
    """Optional credentials; if provided, used instead of server env vars."""
    locationId: Optional[str] = None
    privateToken: Optional[str] = None

# Simple GHL API functions (inline to avoid imports)
def test_ghl_connection(private_token: str, location_id: str) -> Dict:
    """Test GHL API connection"""
    try:
        url = f"https://services.leadconnectorhq.com/locations/{location_id}/customFields"
        headers = {
            "Authorization": f"Bearer {private_token}",
            "Content-Type": "application/json",
            "Version": "2021-07-28"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            custom_fields = data.get('customFields', [])
            field_count = len([f for f in custom_fields if f.get('documentType') == 'field'])
            
            return {
                "success": True,
                "message": "Connection successful",
                "fieldCount": field_count,
                "totalItems": len(custom_fields)
            }
        else:
            return {
                "success": False,
                "error": f"API returned {response.status_code}: {response.text}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def get_ghl_custom_fields(private_token: str, location_id: str) -> Dict:
    """Get all custom fields from GHL"""
    try:
        url = f"https://services.leadconnectorhq.com/locations/{location_id}/customFields"
        headers = {
            "Authorization": f"Bearer {private_token}",
            "Content-Type": "application/json",
            "Version": "2021-07-28"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "fields": data.get('customFields', [])}
        error_msg = f"API returned {response.status_code}"
        try:
            body = response.text[:200] if response.text else ""
            if body and "unauthorized" not in body.lower():
                error_msg += f": {body}"
        except Exception:
            pass
        return {
            "success": False,
            "error": error_msg,
            "status_code": response.status_code,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "status_code": None}

# Test GHL API Connection
@router.post("/test-ghl-connection")
async def test_ghl_connection_endpoint(config: GHLConnectionTest):
    """Test GoHighLevel API connection with provided credentials"""
    try:
        result = test_ghl_connection(config.privateToken, config.locationId)
        return result
            
    except Exception as e:
        logger.error(f"GHL connection test failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# Generate Field Reference
@router.post("/generate-field-reference")
async def generate_field_reference(body: Optional[GenerateFieldReferenceRequest] = None):
    """Generate field_reference.json from current GHL custom fields.
    Uses request body credentials if both privateToken and locationId are provided; otherwise server env vars.
    """
    try:
        if body and body.privateToken and body.locationId:
            token, location_id = body.privateToken.strip(), body.locationId.strip()
            logger.info("Generate field reference using credentials from request body")
        else:
            token, location_id = DSP_LOCATION_PIT, DSP_GHL_LOCATION_ID
            if not token or not location_id:
                raise HTTPException(
                    status_code=400,
                    detail="No credentials provided. Set GHL_PRIVATE_TOKEN and GHL_LOCATION_ID in request body or in server .env.",
                )
        fields_result = get_ghl_custom_fields(token, location_id)
        if not fields_result["success"]:
            status = fields_result.get("status_code")
            detail = f"Failed to retrieve custom fields: {fields_result['error']}"
            if status in (401, 403):
                detail += (
                    " GHL rejected the request. Use valid credentials in the form above (same as Test connection) "
                    "or set GHL_PRIVATE_TOKEN and GHL_LOCATION_ID in .env / docker-compose for this server. "
                )
                # DEBUG: show server env values (remove later)
                _tid = f"{token[:12]}...{token[-4:]}" if len(token) > 16 else ("(empty)" if not token else token[:8] + "...")
                detail += f" [DEBUG - remove later] GHL_LOCATION_ID={location_id!r} GHL_PRIVATE_TOKEN={_tid!r}"
                logger.warning("Generate field reference: GHL returned %s.", status)
            raise HTTPException(
                status_code=401 if status in (401, 403) else 500,
                detail=detail,
            )
        
        custom_fields = fields_result["fields"]
        
        # Process fields into reference format
        all_ghl_fields = {}
        client_fields = {}
        vendor_fields = {}
        
        for field in custom_fields:
            if field.get('documentType') == 'field':
                field_name = field.get('name')
                field_key = field.get('fieldKey')
                field_id = field.get('id')
                
                if field_name and field_key and field_id:
                    field_data = {
                        "fieldKey": field_key,
                        "id": field_id,
                        "dataType": field.get('dataType', 'TEXT'),
                        "model": field.get('model', 'contact')
                    }
                    
                    all_ghl_fields[field_name] = field_data
                    
                    # Categorize as client or vendor field
                    if any(keyword in field_name.lower() for keyword in ['vendor', 'company', 'business', 'service']):
                        vendor_fields[field_name] = field_data
                    else:
                        client_fields[field_name] = field_data
        
        # Create field reference structure
        field_reference = {
            "client_fields": client_fields,
            "vendor_fields": vendor_fields,
            "all_ghl_fields": all_ghl_fields,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save to file
        with open("field_reference.json", "w") as f:
            json.dump(field_reference, f, indent=2)
        
        logger.info(f"Generated field_reference.json with {len(all_ghl_fields)} fields")
        
        # Log to database
        simple_db_instance.log_activity(
            event_type="field_reference_generated",
            event_data={
                "location_id": location_id,
                "total_fields": len(all_ghl_fields),
                "client_fields": len(client_fields),
                "vendor_fields": len(vendor_fields)
            },
            success=True
        )
        
        return {
            "success": True,
            "message": "Field reference generated successfully",
            "fieldCount": len(all_ghl_fields),
            "clientFields": len(client_fields),
            "vendorFields": len(vendor_fields),
            "generatedAt": field_reference["generated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating field reference: {e}")
        simple_db_instance.log_activity(
            event_type="field_reference_generation_error",
            event_data={"error": str(e)},
            success=False,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to generate field reference: {str(e)}")

# Create Fields from CSV
@router.post("/create-fields-from-csv")
async def create_fields_from_csv(csvFile: UploadFile = File(...)):
    """Create custom fields in GHL from uploaded CSV file"""
    try:
        if not csvFile.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        # Read CSV content
        content = await csvFile.read()
        csv_text = content.decode('utf-8')
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        
        # Get existing fields to avoid duplicates
        fields_result = get_ghl_custom_fields(DSP_LOCATION_PIT, DSP_GHL_LOCATION_ID)
        
        existing_field_names = set()
        if fields_result["success"]:
            for field in fields_result["fields"]:
                if field.get('documentType') == 'field':
                    existing_field_names.add(field.get('name'))
        
        # Process CSV rows
        created_count = 0
        skipped_count = 0
        error_count = 0
        results = []
        
        headers = {
            "Authorization": f"Bearer {DSP_LOCATION_PIT}",
            "Content-Type": "application/json",
            "Version": "2021-07-28"
        }
        
        for row in csv_reader:
            field_name = row.get('Label / Field Name', '').strip()
            field_type = row.get('GHL Field Type to Select', '').strip()
            notes = row.get('Notes', '').strip()
            
            # Skip if no field name or if marked as do not create
            if not field_name or 'Built' in field_type or 'do NOT create' in notes:
                skipped_count += 1
                continue
            
            # Skip if field already exists
            if field_name in existing_field_names:
                skipped_count += 1
                results.append(f"Skipped {field_name} - already exists")
                continue
            
            # Map field type
            field_type_mapping = {
                "Single Line": "TEXT",
                "Multi Line": "LARGE_TEXT",
                "Number": "NUMERICAL", 
                "Date Picker": "DATE",
                "Dropdown (Single)": "TEXT",  # Simplified to text
                "Dropdown (Multiple)": "LARGE_TEXT",
                "Checkbox": "TEXT",
                "Radio": "TEXT"
            }
            
            ghl_field_type = field_type_mapping.get(field_type, "TEXT")
            
            # Create field payload
            field_payload = {
                "name": field_name,
                "dataType": ghl_field_type,
                "model": "contact"
            }
            
            # Add placeholder for text fields
            if ghl_field_type in ["TEXT", "LARGE_TEXT"]:
                field_payload["placeholder"] = f"Enter {field_name.lower()}"
            
            # Create the field
            try:
                url = f"https://services.leadconnectorhq.com/locations/{DSP_GHL_LOCATION_ID}/customFields"
                response = requests.post(url, headers=headers, json=field_payload)
                
                if response.status_code == 201:
                    created_count += 1
                    results.append(f"Created {field_name}")
                    existing_field_names.add(field_name)  # Add to avoid duplicates in same run
                else:
                    error_count += 1
                    results.append(f"Failed to create {field_name}: {response.text}")
                
                # Rate limiting
                time.sleep(1)
                
            except Exception as e:
                error_count += 1
                results.append(f"Error creating {field_name}: {str(e)}")
        
        # Log to database
        simple_db_instance.log_activity(
            event_type="bulk_field_creation",
            event_data={
                "csv_filename": csvFile.filename,
                "created": created_count,
                "skipped": skipped_count,
                "errors": error_count
            },
            success=True
        )
        
        return {
            "success": True,
            "message": f"Processed CSV file successfully",
            "created": created_count,
            "skipped": skipped_count,
            "errors": error_count,
            "details": results[:20]  # Limit details to first 20 for response size
        }
        
    except Exception as e:
        logger.error(f"Error processing CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {str(e)}")

# Get Recent Activity
@router.get("/recent-activity")
async def get_recent_activity(limit: int = 20):
    """Get recent system activity from database logs"""
    try:
        # For now, return mock data since we'd need to implement this in simple_connection.py
        activities = [
            {
                "event_type": "field_reference_generated",
                "success": True,
                "error_message": None,
                "timestamp": datetime.now().isoformat()
            },
            {
                "event_type": "elementor_webhook_created", 
                "success": True,
                "error_message": None,
                "timestamp": (datetime.now()).isoformat()
            }
        ]
        
        return {
            "success": True,
            "activities": activities,
            "count": len(activities)
        }
        
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recent activity: {str(e)}")

# Health Check for Admin API
@router.get("/health")
async def admin_health_check():
    """Health check for admin API endpoints"""
    try:
        # Test database connection
        stats = simple_db_instance.get_stats()
        
        # Test GHL API connection
        ghl_test = test_ghl_connection(DSP_LOCATION_PIT, DSP_GHL_LOCATION_ID)
        
        return {
            "status": "healthy",
            "admin_api": "operational",
            "database_connected": True,
            "ghl_api_connected": ghl_test.get("success", False),
            "database_stats": stats,
            "ghl_field_count": ghl_test.get("fieldCount", 0),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "admin_api": "degraded", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }