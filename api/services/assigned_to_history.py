# api/services/assigned_to_history.py
"""
Reusable logic for recording assignedTo changes in assigned_to_histories.
Use when a contact/opportunity is assigned to a GHL user (e.g. in process-new-contact or reassignment flows).
"""

import logging
from typing import Dict, Any, Optional

from database.simple_connection import db as simple_db_instance

logger = logging.getLogger(__name__)


def record_assigned_to_change(
    ghl_contact_id: str,
    new_ghl_user_id: str,
    previous_ghl_user_id: Optional[str] = None,
    service_details: Optional[Dict[str, Any]] = None,
    status: str = "approved",
) -> Optional[str]:
    """
    Record an assignedTo change in assigned_to_histories when the assignee has actually changed.
    Call this after updating an opportunity's assignedTo in GHL (or whenever assignment is set).

    Args:
        ghl_contact_id: GHL contact ID (required).
        new_ghl_user_id: GHL user ID of the new assignee.
        previous_ghl_user_id: GHL user ID of the previous assignee (None if first assignment).
        service_details: Optional dict to store as JSON in service_details column.
        status: One of 'approved', 'rejected', 'past-approved', 'past-rejected'. Default 'approved'.

    Returns:
        The assigned_to_histories row id if recorded, None if skipped (no change) or on error.
    """
    if not ghl_contact_id or not new_ghl_user_id:
        logger.warning("record_assigned_to_change: ghl_contact_id and new_ghl_user_id are required")
        return None
    prev = (previous_ghl_user_id or "").strip() or None
    new = (new_ghl_user_id or "").strip()
    if prev == new:
        logger.debug(f"record_assigned_to_change: no change for contact {ghl_contact_id} (same user)")
        return None
    return simple_db_instance.record_assigned_to_history(
        ghl_contact_id=ghl_contact_id,
        ghl_user_id=new,
        status=status,
        service_details=service_details,
    )
