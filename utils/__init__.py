# utils/__init__.py
from .dependency_manager import dependency_manager, get_module, is_available, require_module
from .ghl_contact_classifier import (
    get_contact_tags_list,
    is_vendor_by_ghl_signals,
    is_staff_contact,
    classify_contact,
    get_vendor_status_from_tags,
    get_lead_status_from_tags,
    get_lead_status_or_default,
    VENDOR_SOURCE_KEYWORD,
    VENDOR_TAGS,
    LEAD_TAGS,
    VENDOR_TAG_LEVELS,
    DEFAULT_VENDOR_STATUS,
    DEFAULT_LEAD_STATUS,
    MISSING_IN_GHL_STATUS,
    INACTIVE_GHL_DELETED_STATUS,
)

__all__ = [
    'dependency_manager', 'get_module', 'is_available', 'require_module',
    'get_contact_tags_list', 'is_vendor_by_ghl_signals', 'is_staff_contact',
    'classify_contact', 'get_vendor_status_from_tags', 'get_lead_status_from_tags',
    'get_lead_status_or_default',
    'VENDOR_SOURCE_KEYWORD', 'VENDOR_TAGS', 'LEAD_TAGS', 'VENDOR_TAG_LEVELS',
    'DEFAULT_VENDOR_STATUS', 'DEFAULT_LEAD_STATUS', 'MISSING_IN_GHL_STATUS', 'INACTIVE_GHL_DELETED_STATUS',
]