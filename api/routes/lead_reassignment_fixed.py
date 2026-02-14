# api/routes/lead_reassignment_fixed.py

"""
Fixed REST API endpoint for lead reassignment.
Uses the core reassignment logic and preserves original source.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.services.lead_reassignment_core import lead_reassignment_core
from database.simple_connection import db as simple_db_instance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/reassignment", tags=["Lead Reassignment Fixed"])

class LeadReassignmentRequest(BaseModel):
    """Request model for lead reassignment"""
    contact_id: str = Field(..., description="GHL Contact ID")
    opportunity_id: Optional[str] = Field(None, description="GHL Opportunity ID (optional)")
    reason: Optional[str] = Field("api_reassignment", description="Reason for reassignment")
    exclude_previous: bool = Field(True, description="Exclude previously assigned vendor")
    
class BulkReassignmentRequest(BaseModel):
    """Request model for bulk reassignment"""
    contact_ids: List[str] = Field(..., description="List of GHL Contact IDs")
    reason: Optional[str] = Field("bulk_reassignment", description="Reason for reassignment")
    exclude_previous: bool = Field(True, description="Exclude previously assigned vendors")

class LeadReassignmentResponse(BaseModel):
    """Response model for lead reassignment"""
    success: bool
    message: str
    contact_id: str
    lead_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    previous_vendor_id: Optional[str] = None
    new_vendor_id: Optional[str] = None
    vendor_name: Optional[str] = None

@router.post("/lead/fixed", response_model=LeadReassignmentResponse)
async def reassign_lead_fixed(request: LeadReassignmentRequest):
    """
    FIXED: Reassign a lead to a new vendor using correct flow.
    
    This endpoint:
    1. Ensures opportunity exists (creates if needed)
    2. Ensures lead exists with opportunity_id
    3. Finds new vendor (optionally excluding previous)
    4. Updates database AND GHL opportunity assignedTo field
    5. PRESERVES original source column (doesn't overwrite)
    
    Use this instead of the broken /lead endpoint.
    """
    logger.info(f"🔄 API reassignment request for contact: {request.contact_id}")
    
    try:
        # Call core reassignment logic with source preservation
        result = await lead_reassignment_core.reassign_lead(
            contact_id=request.contact_id,
            opportunity_id=request.opportunity_id,
            exclude_previous=request.exclude_previous,
            reason=request.reason,
            preserve_source=True  # ALWAYS preserve original source
        )
        
        # Build response
        if result.get("success"):
            logger.info(f"✅ API reassignment successful: {result.get('message')}")
            
            return LeadReassignmentResponse(
                success=True,
                message=result.get("message", "Lead reassigned successfully"),
                contact_id=request.contact_id,
                lead_id=result.get("lead_id"),
                opportunity_id=result.get("opportunity_id"),
                previous_vendor_id=result.get("previous_vendor_id"),
                new_vendor_id=result.get("new_vendor_id"),
                vendor_name=result.get("vendor_name")
            )
        else:
            error_msg = result.get("error", "Reassignment failed")
            logger.warning(f"⚠️ API reassignment failed: {error_msg}")
            
            return LeadReassignmentResponse(
                success=False,
                message=error_msg,
                contact_id=request.contact_id,
                lead_id=result.get("lead_id"),
                previous_vendor_id=result.get("previous_vendor_id")
            )
            
    except Exception as e:
        logger.error(f"❌ Error in API reassignment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reassign lead: {str(e)}"
        )

@router.post("/bulk/fixed")
async def bulk_reassign_leads_fixed(request: BulkReassignmentRequest):
    """
    FIXED: Bulk reassign multiple leads with source preservation.
    
    IMPORTANT: This endpoint preserves the original source column
    for each lead and does NOT overwrite it with 'bulk_reassignment'.
    """
    logger.info(f"📦 Bulk reassignment request for {len(request.contact_ids)} contacts")
    
    results = []
    successful_count = 0
    failed_count = 0
    
    for contact_id in request.contact_ids:
        try:
            # Process each reassignment with source preservation
            result = await lead_reassignment_core.reassign_lead(
                contact_id=contact_id,
                opportunity_id=None,  # Will find or create
                exclude_previous=request.exclude_previous,
                reason=request.reason,
                preserve_source=True  # CRITICAL: Preserve original source
            )
            
            if result.get("success"):
                successful_count += 1
                results.append({
                    "contact_id": contact_id,
                    "success": True,
                    "message": result.get("message"),
                    "vendor": result.get("vendor_name"),
                    "lead_id": result.get("lead_id"),
                    "opportunity_id": result.get("opportunity_id")
                })
            else:
                failed_count += 1
                results.append({
                    "contact_id": contact_id,
                    "success": False,
                    "message": result.get("error", "Reassignment failed")
                })
                
        except Exception as e:
            failed_count += 1
            logger.error(f"❌ Error processing contact {contact_id}: {str(e)}")
            results.append({
                "contact_id": contact_id,
                "success": False,
                "message": str(e)
            })
    
    # Log bulk operation summary
    simple_db_instance.log_activity(
        event_type="bulk_reassignment_completed",
        event_data={
            "total_contacts": len(request.contact_ids),
            "successful": successful_count,
            "failed": failed_count,
            "reason": request.reason
        },
        lead_id="bulk_operation",
        success=successful_count > 0
    )
    
    logger.info(f"✅ Bulk reassignment completed: {successful_count} successful, {failed_count} failed")
    
    return {
        "success": successful_count > 0,
        "total": len(request.contact_ids),
        "successful": successful_count,
        "failed": failed_count,
        "results": results,
        "message": f"Processed {len(request.contact_ids)} contacts: {successful_count} successful, {failed_count} failed"
    }

@router.get("/history/{contact_id}")
async def get_reassignment_history(contact_id: str):
    """
    Get the reassignment history for a contact.
    Shows all reassignment events including preserved source information.
    """
    try:
        # Get lead for this contact
        lead = simple_db_instance.get_lead_by_ghl_contact_id(contact_id)
        
        if not lead:
            raise HTTPException(
                status_code=404,
                detail=f"No lead found for contact {contact_id}"
            )
        
        # Get activity history for reassignments
        conn = simple_db_instance._get_raw_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT event_type, event_data, created_at, success
            FROM activity_log
            WHERE lead_id = ? 
            AND event_type IN ('lead_reassigned_success', 'lead_reassignment_failed', 
                              'vendor_assignment_complete', 'reassignment_webhook_processed')
            ORDER BY created_at DESC
            LIMIT 20
        """, (lead['id'],))
        
        events = []
        for row in cursor.fetchall():
            event_data = json.loads(row[1]) if row[1] else {}
            events.append({
                "event_type": row[0],
                "timestamp": row[2],
                "success": row[3],
                "vendor": event_data.get("vendor_name"),
                "reason": event_data.get("reason"),
                "previous_vendor": event_data.get("previous_vendor_id")
            })
        
        conn.close()
        
        return {
            "success": True,
            "contact_id": contact_id,
            "lead_id": lead['id'],
            "current_vendor_id": lead.get('vendor_id'),
            "original_source": lead.get('source'),  # Show preserved source
            "reassignment_count": len(events),
            "history": events
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting reassignment history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get reassignment history: {str(e)}"
        )

@router.get("/status")
async def get_reassignment_status():
    """
    Get reassignment system status and statistics.
    """
    try:
        conn = simple_db_instance._get_raw_conn()
        cursor = conn.cursor()
        
        # Get reassignment statistics
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT lead_id) as total_reassignments,
                COUNT(CASE WHEN success = 1 THEN 1 END) as successful,
                COUNT(CASE WHEN success = 0 THEN 1 END) as failed
            FROM activity_log
            WHERE event_type LIKE '%reassign%'
            AND created_at > datetime('now', '-30 days')
        """)
        
        stats = cursor.fetchone()
        
        # Get recent reassignments
        cursor.execute("""
            SELECT event_type, lead_id, created_at, success
            FROM activity_log
            WHERE event_type LIKE '%reassign%'
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        recent = []
        for row in cursor.fetchall():
            recent.append({
                "type": row[0],
                "lead_id": row[1],
                "timestamp": row[2],
                "success": bool(row[3])
            })
        
        conn.close()
        
        return {
            "status": "operational",
            "statistics": {
                "last_30_days": {
                    "total_reassignments": stats[0] or 0,
                    "successful": stats[1] or 0,
                    "failed": stats[2] or 0
                }
            },
            "recent_reassignments": recent
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting reassignment status: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }