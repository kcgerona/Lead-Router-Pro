"""
GHL Field Mapper Utility
========================
Provides field mapping utilities for GHL custom fields integration.
Replaces the old field_mapper module with proper support for GHL's nested customFields structure.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class GHLFieldMapper:
    """Maps form fields to GHL custom field IDs"""
    
    def __init__(self):
        self.field_reference = self._load_field_reference()
        self.field_lookup = self._build_lookup_tables()
        
    def _load_field_reference(self) -> Dict:
        """Load the field reference from JSON file"""
        try:
            field_ref_path = Path("/root/Lead-Router-Pro/field_reference.json")
            if field_ref_path.exists():
                with open(field_ref_path, 'r') as f:
                    data = json.load(f)
                    logger.info(f"✅ Loaded field reference with {len(data.get('client_fields', {}))} client fields and {len(data.get('vendor_fields', {}))} vendor fields")
                    return data
            else:
                logger.warning("⚠️ field_reference.json not found")
                return {"client_fields": {}, "vendor_fields": {}}
        except Exception as e:
            logger.error(f"❌ Error loading field reference: {e}")
            return {"client_fields": {}, "vendor_fields": {}}
    
    def _build_lookup_tables(self) -> Dict:
        """Build reverse lookup tables for quick access"""
        lookup = {
            "by_key": {},  # fieldKey -> field details
            "by_id": {},   # id -> field details
            "by_name": {}  # name -> field details
        }
        
        # Process both client and vendor fields
        for field_type in ["client_fields", "vendor_fields"]:
            for field_name, field_details in self.field_reference.get(field_type, {}).items():
                # Create a copy of field_details and ensure it has a 'name' field
                field_data = field_details.copy()
                field_data['name'] = field_name
                
                # Add to lookups
                field_key = field_data.get("fieldKey", "").replace("contact.", "")
                field_id = field_data.get("id")
                
                if field_key:
                    lookup["by_key"][field_key] = field_data
                if field_id:
                    lookup["by_id"][field_id] = field_data
                lookup["by_name"][field_name.lower()] = field_data
                
                # Also add underscore version for common variations
                underscore_key = field_key.replace(" ", "_").lower()
                if underscore_key:
                    lookup["by_key"][underscore_key] = field_data
                
        return lookup
    
    def get_all_ghl_field_keys(self) -> List[str]:
        """Get all valid GHL field keys"""
        # Start with standard GHL fields
        keys = [
            "firstName", "lastName", "email", "phone", "address1", 
            "city", "state", "postalCode", "country", "companyName",
            "tags", "source", "dateOfBirth", "website", "name",
            "secondaryEmail", "gender", "timezone", "dnd"
        ]
        
        # Add custom fields from field reference
        for field_type in ["client_fields", "vendor_fields"]:
            for field_details in self.field_reference.get(field_type, {}).values():
                field_key = field_details.get("fieldKey", "").replace("contact.", "")
                if field_key and field_key not in keys:
                    keys.append(field_key)
        return keys
    
    def get_mapping(self, field_name: str, industry: str = "marine") -> Optional[str]:
        """Get the GHL field key for a given form field name"""
        # Try direct lookup first
        field_lower = field_name.lower()
        
        # Check if it's already a GHL field key
        if field_name in self.field_lookup["by_key"]:
            return field_name
            
        # Check by name
        if field_lower in self.field_lookup["by_name"]:
            field_details = self.field_lookup["by_name"][field_lower]
            return field_details.get("fieldKey", "").replace("contact.", "")
            
        # Check common variations
        variations = [
            field_name.replace("_", " ").lower(),
            field_name.replace("-", " ").lower(),
            field_name.replace("_", "").lower()
        ]
        
        for variant in variations:
            if variant in self.field_lookup["by_name"]:
                field_details = self.field_lookup["by_name"][variant]
                return field_details.get("fieldKey", "").replace("contact.", "")
        
        # If not found, return the original field name (might be a standard field)
        return field_name
    
    def is_valid_ghl_field(self, field_key: str) -> bool:
        """Check if a field key is a valid GHL field"""
        # Standard fields that are always valid (these go directly in the payload)
        standard_fields = [
            "firstName", "lastName", "email", "phone", "address1", 
            "city", "state", "postalCode", "country", "companyName",
            "tags", "source", "dateOfBirth", "website", "name",
            # Additional standard fields
            "secondaryEmail", "gender", "timezone", "dnd", 
            "inboundDndSettings", "customFields"
        ]
        
        if field_key in standard_fields:
            return True
            
        # Check custom fields
        return field_key in self.field_lookup["by_key"] or field_key in self.field_lookup["by_id"]
    
    def get_ghl_field_details(self, field_name: str) -> Optional[Dict]:
        """Get full GHL field details including ID and data type"""
        # Try multiple lookup methods
        field_lower = field_name.lower()
        
        # Direct lookup by key
        if field_name in self.field_lookup["by_key"]:
            field_data = self.field_lookup["by_key"][field_name]
            # Ensure we have a 'name' field in the returned data
            if 'name' not in field_data:
                field_data['name'] = field_name
            return field_data
            
        # Lookup by name
        if field_lower in self.field_lookup["by_name"]:
            field_data = self.field_lookup["by_name"][field_lower]
            # Ensure we have a 'name' field in the returned data
            if 'name' not in field_data:
                # Find the original name from the field reference
                for field_type in ["client_fields", "vendor_fields"]:
                    for original_name, details in self.field_reference.get(field_type, {}).items():
                        if details.get("id") == field_data.get("id"):
                            field_data['name'] = original_name
                            break
            return field_data
            
        # Try with underscores
        underscore_key = field_name.replace(" ", "_").lower()
        if underscore_key in self.field_lookup["by_key"]:
            field_data = self.field_lookup["by_key"][underscore_key]
            if 'name' not in field_data:
                field_data['name'] = field_name
            return field_data
            
        # Try replacing underscores with spaces
        space_key = field_name.replace("_", " ").lower()
        if space_key in self.field_lookup["by_name"]:
            field_data = self.field_lookup["by_name"][space_key]
            if 'name' not in field_data:
                for field_type in ["client_fields", "vendor_fields"]:
                    for original_name, details in self.field_reference.get(field_type, {}).items():
                        if details.get("id") == field_data.get("id"):
                            field_data['name'] = original_name
                            break
            return field_data
            
        # Special handling for known field mappings
        known_mappings = {
            "primary_service_category": "Primary Service Category",
            "service_category": "Service Category",
            "services_provided": "Services Provided",
            "service_zip_codes": "Service ZIP Codes",
            "taking_new_work": "Taking New Work",
            "reviews__google_profile_url": "Reviews / Google Profile URL",
            "vendor_preferred_contact_method": "Vendor Preferred Contact Method",
            "vendor_address": "Vendor Address",
            "service_counties": "Service Counties"
        }
        
        if field_name in known_mappings:
            mapped_name = known_mappings[field_name]
            if mapped_name.lower() in self.field_lookup["by_name"]:
                field_data = self.field_lookup["by_name"][mapped_name.lower()]
                if 'name' not in field_data:
                    field_data['name'] = mapped_name
                return field_data
        
        return None
    
    def get_stats(self) -> Dict:
        """Get statistics about loaded fields"""
        return {
            "ghl_fields_loaded": len(self.field_lookup["by_key"]),
            "custom_fields_available": len(self.field_lookup["by_id"]),
            "client_fields": len(self.field_reference.get("client_fields", {})),
            "vendor_fields": len(self.field_reference.get("vendor_fields", {}))
        }


# Create singleton instance
field_mapper = GHLFieldMapper()