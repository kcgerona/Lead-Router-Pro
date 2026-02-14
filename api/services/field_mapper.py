# api/services/field_mapper.py

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any, List, Set
from datetime import datetime

logger = logging.getLogger(__name__)

def _default_field_reference_path() -> str:
    """Path to field_reference.json under app data (data/) to avoid permission errors."""
    try:
        from config import AppConfig
        return getattr(AppConfig, "FIELD_REFERENCE_PATH", "data/field_reference.json")
    except ImportError:
        return "data/field_reference.json"


class FieldMapper:
    """
    Enhanced field mapping service that integrates with both field_mappings.json and field_reference.json
    
    This service provides:
    - Dynamic field name translation (form fields -> GHL fields)
    - GHL field ID and metadata lookup
    - Industry-specific mapping support
    - Integration with webhook_routes, admin_routes, field_mapping_routes, and dashboard
    """
    
    def __init__(self, mappings_file: str = "field_mappings.json", reference_file: Optional[str] = None):
        self._mappings_file = Path(mappings_file)
        self._reference_file = Path(reference_file or _default_field_reference_path())
        self._mappings = {}
        self._field_reference = {}
        self._ghl_field_mapping = {}  # Maps GHL field keys to their details (ID, name, etc.)
        self._reverse_mappings = {}  # Maps GHL field keys back to form field names
        
        # Load all data
        self.load_mappings()
        self.load_field_reference()
        self._build_ghl_field_mapping()
        self._generate_reverse_mappings()
        
        logger.info(f"✅ FieldMapper initialized with {len(self._mappings.get('default_mappings', {}))} default mappings and {len(self._ghl_field_mapping)} GHL fields")
    
    def load_mappings(self):
        """Load field mappings from JSON file"""
        try:
            if self._mappings_file.exists():
                with open(self._mappings_file, 'r') as f:
                    self._mappings = json.load(f)
                logger.info(f"✅ Loaded field mappings from {self._mappings_file}")
                
                # Validate structure
                if not isinstance(self._mappings.get('default_mappings'), dict):
                    self._mappings['default_mappings'] = {}
                if not isinstance(self._mappings.get('industry_specific'), dict):
                    self._mappings['industry_specific'] = {}
                    
            else:
                # Initialize with comprehensive default mappings based on your system
                self._mappings = {
                    "default_mappings": {
                        # Service and location mappings
                        "ServiceNeeded": "specific_service_requested",
                        "serviceNeeded": "specific_service_requested", 
                        "service_needed": "specific_service_requested",
                        "specificService": "specific_service_requested",  # Handle this field too
                        "zipCode": "zip_code_of_service",
                        "zip_code": "zip_code_of_service",
                        "serviceZipCode": "zip_code_of_service",
                        
                        # Vessel information mappings
                        "vesselMake": "vessel_make",
                        "vessel_make": "vessel_make",
                        "boatMake": "vessel_make",
                        "vesselModel": "vessel_model", 
                        "vessel_model": "vessel_model",
                        "boatModel": "vessel_model",
                        "vesselYear": "vessel_year",
                        "vessel_year": "vessel_year",
                        "boatYear": "vessel_year",
                        "vesselLength": "vessel_length_ft",
                        "vessel_length": "vessel_length_ft",
                        "boatLength": "vessel_length_ft",
                        "vesselLocation": "vessel_location__slip",
                        "vessel_location": "vessel_location__slip",
                        "boatLocation": "vessel_location__slip",
                        
                        # Request details mappings
                        "specialRequests": "special_requests__notes",
                        "special_requests": "special_requests__notes",
                        "notes": "special_requests__notes",
                        "preferredContact": "preferred_contact_method",
                        "preferred_contact": "preferred_contact_method", 
                        "contactMethod": "preferred_contact_method",
                        "desiredTimeline": "desired_timeline",
                        "desired_timeline": "desired_timeline",
                        "timeline": "desired_timeline",
                        "budgetRange": "budget_range",
                        "budget_range": "budget_range",
                        "budget": "budget_range",
                        
                        # Additional common mappings
                        "companyName": "vendor_company_name",
                        "company_name": "vendor_company_name",
                        "serviceCategory": "service_category",
                        "service_category": "service_category"
                    },
                    "industry_specific": {
                        "marine": {
                            # Marine-specific mappings
                            "boatType": "vessel_make",
                            "yachtMake": "vessel_make", 
                            "marineMake": "vessel_make",
                            "dockLocation": "vessel_location__slip",
                            "marinaName": "vessel_location__slip",
                            "emergencyTow": "need_emergency_tow",
                            "towService": "need_emergency_tow",
                            "marineService": "specific_service_requested"
                        },
                        "automotive": {
                            # Automotive mappings for future expansion
                            "vehicleMake": "vehicle_make",
                            "carMake": "vehicle_make",
                            "vehicleModel": "vehicle_model", 
                            "carModel": "vehicle_model",
                            "vehicleYear": "vehicle_year",
                            "carYear": "vehicle_year"
                        }
                    },
                    "reverse_mappings": {},  # Generated automatically
                    "metadata": {
                        "version": "2.0",
                        "created": datetime.now().strftime("%Y-%m-%d"),
                        "description": "Enhanced field mapping system for multi-industry lead routing with GHL integration",
                        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
                self.save_mappings()
                logger.info("🔧 Created enhanced default field mappings")
                
        except Exception as e:
            logger.error(f"❌ Error loading field mappings: {e}")
            self._mappings = {"default_mappings": {}, "industry_specific": {}, "reverse_mappings": {}}
    
    def load_field_reference(self):
        """Load GHL field reference data from field_reference.json"""
        try:
            if self._reference_file.exists():
                with open(self._reference_file, 'r') as f:
                    self._field_reference = json.load(f)
                logger.info(f"✅ Loaded field reference from {self._reference_file}")
                
                all_fields_count = len(self._field_reference.get('all_ghl_fields', {}))
                client_fields_count = len(self._field_reference.get('client_fields', {}))
                vendor_fields_count = len(self._field_reference.get('vendor_fields', {}))
                
                logger.info(f"📊 GHL Field Summary: {all_fields_count} total, {client_fields_count} client, {vendor_fields_count} vendor")
            else:
                logger.warning(f"⚠️ Field reference file {self._reference_file} not found - using minimal fallback")
                self._field_reference = {
                    "all_ghl_fields": {},
                    "client_fields": {},
                    "vendor_fields": {},
                    "generated_at": "missing"
                }
        except Exception as e:
            logger.error(f"❌ Error loading field reference: {e}")
            self._field_reference = {"all_ghl_fields": {}, "client_fields": {}, "vendor_fields": {}}
    
    def _build_ghl_field_mapping(self):
        """Build efficient mapping from GHL field keys to field details (ID, name, etc.)"""
        self._ghl_field_mapping = {}
        
        # FIXED: Combine client_fields and vendor_fields into all_ghl_fields
        all_ghl_fields = {}
        all_ghl_fields.update(self._field_reference.get("client_fields", {}))
        all_ghl_fields.update(self._field_reference.get("vendor_fields", {}))
        
        processed_count = 0
        
        for field_name, field_details in all_ghl_fields.items():
            field_key = field_details.get("fieldKey", "")
            field_id = field_details.get("id", "")
            
            if field_key and field_key.startswith("contact.") and field_id:
                # Extract the API key part after "contact."
                api_key = field_key.split("contact.")[-1]
                self._ghl_field_mapping[api_key] = {
                    "id": field_id,
                    "fieldKey": field_key,
                    "name": field_name,
                    "dataType": field_details.get("dataType", "TEXT"),
                    "model": field_details.get("model", "contact")
                }
                processed_count += 1
        
        logger.info(f"🔗 Built GHL field mapping: {processed_count} custom fields processed from {len(all_ghl_fields)} total fields")
    
    def _generate_reverse_mappings(self):
        """Generate reverse mappings (GHL field -> form field) for all industries"""
        self._reverse_mappings = {}
        
        # Default mappings
        default_mappings = self._mappings.get("default_mappings", {})
        for form_field, ghl_field in default_mappings.items():
            # Use the first form field that maps to each GHL field
            if ghl_field not in self._reverse_mappings:
                self._reverse_mappings[ghl_field] = form_field
        
        # Industry-specific mappings (these take precedence)
        industry_mappings = self._mappings.get("industry_specific", {})
        for industry, mappings in industry_mappings.items():
            for form_field, ghl_field in mappings.items():
                self._reverse_mappings[ghl_field] = form_field
        
        logger.debug(f"🔄 Generated {len(self._reverse_mappings)} reverse mappings")
    
    def get_mapping(self, field_name: str, industry: str = "marine") -> str:
        """
        Get the mapped GHL field name for a given form field name.
        
        Args:
            field_name: Original field name from form
            industry: Industry context for specific mappings
            
        Returns:
            Mapped GHL field name or original if no mapping exists
        """
        if not field_name:
            return field_name
        
        # Check industry-specific mappings first (highest priority)
        industry_mappings = self._mappings.get("industry_specific", {}).get(industry, {})
        if field_name in industry_mappings:
            mapped = industry_mappings[field_name]
            logger.debug(f"🏭 Industry mapping ({industry}): {field_name} → {mapped}")
            return mapped
        
        # Check default mappings
        default_mappings = self._mappings.get("default_mappings", {})
        if field_name in default_mappings:
            mapped = default_mappings[field_name]
            logger.debug(f"🔄 Default mapping: {field_name} → {mapped}")
            return mapped
        
        # Return original if no mapping found
        logger.debug(f"➡️ No mapping found for '{field_name}', using original")
        return field_name
    
    def get_reverse_mapping(self, ghl_field_name: str, industry: str = "marine") -> str:
        """
        Get the form field name that maps to a given GHL field.
        Useful for generating forms or documentation.
        """
        return self._reverse_mappings.get(ghl_field_name, ghl_field_name)
    
    def get_ghl_field_details(self, field_key: str) -> Optional[Dict[str, Any]]:
        """
        Get GHL field details (ID, name, dataType) for a given field key.
        
        This is used by webhook_routes.py to build the customFields array.
        """
        return self._ghl_field_mapping.get(field_key)
    
    def get_ghl_field_details_by_id(self, field_id: str) -> Optional[Dict[str, Any]]:
        """
        Get GHL field details by field ID.
        
        This is used by the county-based vendor creation system to extract data
        from GHL contact records when we know the field ID but need the key.
        """
        for field_key, field_details in self._ghl_field_mapping.items():
            if field_details.get("id") == field_id:
                return {
                    "key": field_key,
                    "id": field_id,
                    "fieldKey": field_details.get("fieldKey"),
                    "name": field_details.get("name"),
                    "dataType": field_details.get("dataType", "TEXT"),
                    "model": field_details.get("model", "contact")
                }
        return None
    
    def get_all_ghl_field_keys(self) -> Set[str]:
        """
        Get all valid GHL field keys (standard + custom).
        
        Used by webhook_routes.py for field validation.
        """
        # Standard GHL contact fields
        standard_fields = {
            "firstName", "lastName", "email", "phone", "companyName", 
            "address1", "city", "state", "postal_code", "name",
            "tags", "notes", "dnd", "country", "source", "website"
        }
        
        # Custom field keys from field_reference.json
        custom_field_keys = set(self._ghl_field_mapping.keys())
        
        return standard_fields.union(custom_field_keys)
    
    def is_valid_ghl_field(self, field_name: str) -> bool:
        """
        Check if a field name is a valid GHL field.
        
        Used by webhook_routes.py for field validation.
        """
        return field_name in self.get_all_ghl_field_keys()
    
    def map_payload(self, payload: Dict[str, Any], industry: str = "marine") -> Dict[str, Any]:
        """
        Map an entire payload using field mappings.
        
        Args:
            payload: Original payload with potentially unmapped field names
            industry: Industry context for mappings
            
        Returns:
            New payload with mapped field names
        """
        mapped_payload = {}
        mapping_log = []
        
        for field_name, value in payload.items():
            # Skip empty values (but allow 0 and False)
            if value == "" or value is None:
                logger.debug(f"Skipping empty value for field: {field_name}")
                continue
                
            mapped_name = self.get_mapping(field_name, industry)
            mapped_payload[mapped_name] = value
            
            if mapped_name != field_name:
                mapping_log.append(f"{field_name} → {mapped_name}")
        
        if mapping_log:
            logger.info(f"🔄 Applied field mappings: {', '.join(mapping_log)}")
        else:
            logger.debug(f"➡️ No field mappings applied (all fields already in correct format)")
        
        return mapped_payload
    
    def add_mapping(self, source_field: str, target_field: str, industry: Optional[str] = None):
        """Add a new field mapping (supports dashboard and API operations)"""
        if industry:
            if "industry_specific" not in self._mappings:
                self._mappings["industry_specific"] = {}
            if industry not in self._mappings["industry_specific"]:
                self._mappings["industry_specific"][industry] = {}
            
            self._mappings["industry_specific"][industry][source_field] = target_field
            logger.info(f"➕ Added industry mapping: {source_field} → {target_field} (industry: {industry})")
        else:
            if "default_mappings" not in self._mappings:
                self._mappings["default_mappings"] = {}
            
            self._mappings["default_mappings"][source_field] = target_field
            logger.info(f"➕ Added default mapping: {source_field} → {target_field}")
        
        # Update reverse mappings and save
        self._generate_reverse_mappings()
        self.save_mappings()
    
    def remove_mapping(self, source_field: str, industry: Optional[str] = None):
        """Remove a field mapping (supports dashboard and API operations)"""
        removed = False
        
        if industry:
            industry_mappings = self._mappings.get("industry_specific", {}).get(industry, {})
            if source_field in industry_mappings:
                del industry_mappings[source_field]
                removed = True
                logger.info(f"🗑️ Removed industry mapping: {source_field} (industry: {industry})")
        else:
            default_mappings = self._mappings.get("default_mappings", {})
            if source_field in default_mappings:
                del default_mappings[source_field]
                removed = True
                logger.info(f"🗑️ Removed default mapping: {source_field}")
        
        if removed:
            self._generate_reverse_mappings()
            self.save_mappings()
        else:
            logger.warning(f"⚠️ No mapping found to remove: {source_field} (industry: {industry or 'default'})")
    
    def get_all_mappings(self) -> Dict[str, Any]:
        """Get all current mappings (used by field_mapping_routes.py and dashboard)"""
        return self._mappings.copy()
    
    def update_mappings(self, new_mappings: Dict[str, Any]):
        """Update all mappings with new data (supports bulk operations from dashboard)"""
        self._mappings = new_mappings
        
        # Update metadata
        if "metadata" not in self._mappings:
            self._mappings["metadata"] = {}
        self._mappings["metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self._generate_reverse_mappings()
        self.save_mappings()
        logger.info("🔄 Updated all field mappings from external source")
    
    def get_mapping_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about current mappings (used by health checks and dashboard)"""
        default_count = len(self._mappings.get("default_mappings", {}))
        
        industry_mappings = self._mappings.get("industry_specific", {})
        industry_count = sum(len(mappings) for mappings in industry_mappings.values())
        industries = list(industry_mappings.keys())
        
        ghl_fields_loaded = len(self._ghl_field_mapping)
        total_ghl_fields = len(self._field_reference.get("all_ghl_fields", {}))
        
        return {
            "total_mappings": default_count + industry_count,
            "default_mappings": default_count,
            "industry_mappings": industry_count,
            "industries": industries,
            "ghl_fields_loaded": ghl_fields_loaded,
            "total_ghl_fields": total_ghl_fields,
            "field_reference_loaded": total_ghl_fields > 0,
            "reverse_mappings": len(self._reverse_mappings),
            "last_updated": self._mappings.get("metadata", {}).get("last_updated", "unknown")
        }
    
    def save_mappings(self):
        """Save current mappings to JSON file"""
        try:
            # Ensure metadata is updated
            if "metadata" not in self._mappings:
                self._mappings["metadata"] = {}
            self._mappings["metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(self._mappings_file, 'w') as f:
                json.dump(self._mappings, f, indent=2)
            logger.debug(f"💾 Saved field mappings to {self._mappings_file}")
        except Exception as e:
            logger.error(f"❌ Error saving field mappings: {e}")
    
    def validate_field_reference_integrity(self) -> Dict[str, Any]:
        """Validate field reference data integrity (used by admin health checks)"""
        issues = []
        warnings = []
        
        # Check if field reference is loaded
        if not self._field_reference.get("all_ghl_fields"):
            issues.append("No field reference data loaded")
            return {"valid": False, "issues": issues, "warnings": warnings}
        
        # Check for fields with missing IDs
        all_fields = self._field_reference.get("all_ghl_fields", {})
        missing_ids = []
        missing_field_keys = []
        
        for field_name, details in all_fields.items():
            if not details.get("id"):
                missing_ids.append(field_name)
            if not details.get("fieldKey"):
                missing_field_keys.append(field_name)
        
        if missing_ids:
            warnings.append(f"{len(missing_ids)} fields missing IDs: {missing_ids[:3]}...")
        if missing_field_keys:
            warnings.append(f"{len(missing_field_keys)} fields missing fieldKeys: {missing_field_keys[:3]}...")
        
        # Check mapping coverage
        mapped_fields = set(self._mappings.get("default_mappings", {}).values())
        available_fields = set(self._ghl_field_mapping.keys())
        unmapped_available = available_fields - mapped_fields
        
        if unmapped_available:
            warnings.append(f"{len(unmapped_available)} GHL fields available but not mapped")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "field_coverage": {
                "total_ghl_fields": len(all_fields),
                "usable_custom_fields": len(self._ghl_field_mapping),
                "mapped_fields": len(mapped_fields),
                "unmapped_available": len(unmapped_available)
            }
        }
    
    def get_field_suggestions(self, form_field_name: str, industry: str = "marine") -> List[str]:
        """Get suggested GHL field mappings for a form field (used by dashboard autocomplete)"""
        form_field_lower = form_field_name.lower()
        suggestions = []
        
        # Look for similar field names in available GHL fields
        for ghl_field_key, details in self._ghl_field_mapping.items():
            field_name_lower = details["name"].lower()
            
            # Exact matches
            if form_field_lower in field_name_lower or field_name_lower in form_field_lower:
                suggestions.append({
                    "ghl_field": ghl_field_key,
                    "name": details["name"],
                    "dataType": details["dataType"],
                    "confidence": "high"
                })
            # Partial matches
            elif any(word in field_name_lower for word in form_field_lower.split('_')):
                suggestions.append({
                    "ghl_field": ghl_field_key,
                    "name": details["name"], 
                    "dataType": details["dataType"],
                    "confidence": "medium"
                })
        
        # Sort by confidence and limit results
        suggestions.sort(key=lambda x: {"high": 3, "medium": 2, "low": 1}.get(x["confidence"], 0), reverse=True)
        return suggestions[:5]
    
    def export_mappings_for_backup(self) -> Dict[str, Any]:
        """Export complete mapping data for backup (used by admin operations)"""
        return {
            "field_mappings": self._mappings,
            "field_reference_stats": {
                "total_fields": len(self._field_reference.get("all_ghl_fields", {})),
                "generated_at": self._field_reference.get("generated_at", "unknown")
            },
            "export_info": {
                "exported_at": datetime.now().isoformat(),
                "total_mappings": self.get_mapping_stats()["total_mappings"],
                "version": self._mappings.get("metadata", {}).get("version", "1.0")
            }
        }


# Global singleton instance
field_mapper = FieldMapper()
