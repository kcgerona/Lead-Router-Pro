"""
GHL Contact Classifier – global utilities for classifying contacts as vendor/lead and resolving status.

Use anywhere (webhooks, sync, scripts) without DB or GHL API dependencies.
Expects a GHL contact dict: { "tags", "source", "type", "email", "customFields", ... }.
"""

from typing import Dict, List, Any, Optional, Set

# ---------------------------------------------------------------------------
# Constants (aligned with enhanced_db_sync_v3)
# ---------------------------------------------------------------------------

# GHL: treat as vendor if source contains this (even when type=lead)
VENDOR_SOURCE_KEYWORD = "Vendor Application"

# Tags that indicate a contact is a vendor (case-insensitive)
VENDOR_TAGS = {"new vendor", "new vendor application", "manually approved"}

# Tags that indicate a contact is a lead
LEAD_TAGS = {"new lead"}

# Lead: if "new lead" tag -> status "new"
LEAD_TAG_NEW_LEAD_STATUS = "new"

# Vendor status from tags: (level, tag, status) — higher level wins
VENDOR_TAG_LEVELS = [
    (0, "new vendor application", "pending"),
    (1, "onboarding in process", "pending"),
    (2, "manual approval", "pending"),
    (3, "manually approved", "active"),
    (4, "deactivated", "deactivated"),
    (5, "reactivated", "active"),
]

DEFAULT_VENDOR_STATUS = "pending"
DEFAULT_LEAD_STATUS = "pending"

# Status when contact exists locally but is not found in GHL
MISSING_IN_GHL_STATUS = "missing_in_ghl"
# Status when contact does not exist on GHL (deleted there)
INACTIVE_GHL_DELETED_STATUS = "inactive_ghl_deleted"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_contact_tags_list(ghl_contact: Dict[str, Any]) -> List[str]:
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


# ---------------------------------------------------------------------------
# Classification: vendor vs lead (by GHL signals only, or with optional DB context)
# ---------------------------------------------------------------------------

def is_vendor_by_ghl_signals(ghl_contact: Dict[str, Any]) -> bool:
    """
    True if GHL contact should be treated as a vendor based on source or tags,
    even when type=lead. Source containing 'Vendor Application' or tags like
    'new vendor', 'new vendor application', 'manually approved'.
    """
    source = (ghl_contact.get("source") or "").strip()
    if VENDOR_SOURCE_KEYWORD.lower() in source.lower():
        return True
    tags = get_contact_tags_list(ghl_contact)
    return bool(tags and any(t in VENDOR_TAGS for t in tags))


def is_staff_contact(ghl_contact: Dict[str, Any]) -> bool:
    """True if GHL contact type is staff; staff should not be added as vendor or lead."""
    contact_type = (ghl_contact.get("type") or "").strip().lower()
    return contact_type == "staff"


def classify_contact(
    ghl_contact: Dict[str, Any],
    *,
    vendor_contact_ids: Optional[Set[str]] = None,
    vendor_emails: Optional[Set[str]] = None,
    lead_contact_ids: Optional[Set[str]] = None,
    lead_emails: Optional[Set[str]] = None,
) -> Optional[str]:
    """
    Classify a single GHL contact as "vendor", "lead", or "staff".
    Returns None if not staff and not clearly vendor/lead (e.g. unknown contact).

    Priority: staff > vendor (by signals or DB) > lead (by DB only; vendor takes precedence).
    If no identifier sets are passed, only GHL signals are used (vendor vs None for lead).
    """
    if is_staff_contact(ghl_contact):
        return "staff"

    cid = (ghl_contact.get("id") or "").strip()
    email = (ghl_contact.get("email") or "").strip().lower()

    is_vendor = is_vendor_by_ghl_signals(ghl_contact)
    if vendor_contact_ids and cid and cid in vendor_contact_ids:
        is_vendor = True
    if vendor_emails and email and email in vendor_emails:
        is_vendor = True

    if is_vendor:
        return "vendor"

    in_lead_db = False
    if lead_contact_ids and cid and cid in lead_contact_ids:
        in_lead_db = True
    if lead_emails and email and email in lead_emails:
        in_lead_db = True
    if in_lead_db:
        return "lead"

    return None


# ---------------------------------------------------------------------------
# Status resolution from tags (for lead and vendor)
# ---------------------------------------------------------------------------

def get_vendor_status_from_tags(ghl_contact: Dict[str, Any]) -> str:
    """Vendor status from tags by level; higher level wins. Default is DEFAULT_VENDOR_STATUS."""
    tags_list = get_contact_tags_list(ghl_contact)
    tags_set = set(tags_list)
    best_level = -1
    status = DEFAULT_VENDOR_STATUS
    for level, tag, st in VENDOR_TAG_LEVELS:
        if tag in tags_set and level > best_level:
            best_level = level
            status = st
    return status


def get_lead_status_from_tags(ghl_contact: Dict[str, Any]) -> Optional[str]:
    """Lead status from tags: 'new lead' -> 'new'. Returns None to leave status unchanged."""
    tags_list = get_contact_tags_list(ghl_contact)
    if "new lead" in tags_list:
        return LEAD_TAG_NEW_LEAD_STATUS
    return None


def get_lead_status_or_default(ghl_contact: Dict[str, Any], default: str = DEFAULT_LEAD_STATUS) -> str:
    """Lead status from tags, or default if no tag match."""
    return get_lead_status_from_tags(ghl_contact) or default
