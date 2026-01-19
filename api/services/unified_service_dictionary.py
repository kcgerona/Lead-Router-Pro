"""
Unified Service Dictionary Module
This is the SINGLE interface for accessing service categories and hierarchies.
All APIs and components should use this module instead of accessing data sources directly.

Author: Lead Router Pro Team
Created: 2025-10-06
Purpose: Establish single source of truth for service data
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from functools import lru_cache
import hashlib

# Import the SINGLE SOURCE OF TRUTH
from api.services.dockside_pros_service_dictionary import (
    DOCKSIDE_PROS_SERVICES,
    get_all_categories,
    get_subcategories_for_category,
    get_specific_services,
    validate_service_hierarchy
)

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL_SECONDS = 3600  # 1 hour cache
_cache_timestamp = None
_cache_data = {}


class UnifiedServiceDictionary:
    """
    Unified interface for all service dictionary operations.
    This class provides various formats needed by different consumers
    while maintaining a single source of truth.
    """
    
    def __init__(self):
        self.source_data = DOCKSIDE_PROS_SERVICES
        self._cache = {}
        self._last_cache_clear = datetime.now()
        
    def clear_cache_if_needed(self):
        """Clear cache if TTL expired"""
        if datetime.now() - self._last_cache_clear > timedelta(seconds=CACHE_TTL_SECONDS):
            self._cache.clear()
            self._last_cache_clear = datetime.now()
            logger.info("Cache cleared after TTL expiration")
    
    @lru_cache(maxsize=128)
    def get_cache_key(self, *args) -> str:
        """Generate cache key from arguments"""
        return hashlib.md5(str(args).encode()).hexdigest()
    
    # ============= CORE DATA ACCESS METHODS =============
    
    def get_raw_dictionary(self) -> Dict:
        """Get the raw service dictionary (direct access)"""
        return self.source_data
    
    def get_all_categories(self) -> List[str]:
        """Get list of all Level 1 category names"""
        return get_all_categories()
    
    def get_category_by_name(self, category_name: str) -> Optional[Dict]:
        """Get category data by name"""
        for cat_id, cat_data in self.source_data.items():
            if cat_data["name"] == category_name:
                return cat_data
        return None
    
    def get_subcategories(self, category_name: str) -> List[str]:
        """Get Level 2 subcategories for a category"""
        return get_subcategories_for_category(category_name)
    
    def get_level3_services(self, category_name: str, subcategory_name: str) -> List[str]:
        """Get Level 3 specific services"""
        return get_specific_services(category_name, subcategory_name)
    
    # ============= FORMAT ADAPTERS FOR DIFFERENT CONSUMERS =============
    
    def get_vendor_application_format(self) -> Dict:
        """
        Format for vendor application widget
        Returns hierarchical structure with subcategories and level3Services
        """
        cache_key = "vendor_app_format"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        result = {}
        for cat_id, cat_data in self.source_data.items():
            category_name = cat_data["name"]
            result[category_name] = {
                "subcategories": list(cat_data["subcategories"].keys()),
                "level3Services": {}
            }
            
            # Add Level 3 services for each subcategory
            for subcat_name, subcat_data in cat_data["subcategories"].items():
                if "specific_services" in subcat_data and subcat_data["specific_services"]:
                    result[category_name]["level3Services"][subcat_name] = subcat_data["specific_services"]
        
        self._cache[cache_key] = result
        return result
    
    def get_vendor_matching_format(self) -> Tuple[Dict, Dict]:
        """
        Format for vendor-matching API
        Returns tuple of (SERVICE_CATEGORIES dict, LEVEL_3_SERVICES dict)
        """
        cache_key = "vendor_matching_format"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        service_categories = {}
        level3_services = {}
        
        for cat_id, cat_data in self.source_data.items():
            category_name = cat_data["name"]
            
            # Extract Level 2 services (subcategory names)
            service_categories[category_name] = list(cat_data["subcategories"].keys())
            
            # Extract Level 3 services if they exist
            category_has_level3 = False
            level3_for_category = {}
            
            for subcat_name, subcat_data in cat_data["subcategories"].items():
                if "specific_services" in subcat_data and subcat_data["specific_services"]:
                    # Skip single-item Level 3 that just repeats the subcategory name
                    if not (len(subcat_data["specific_services"]) == 1 and 
                            subcat_data["specific_services"][0] == subcat_name):
                        level3_for_category[subcat_name] = subcat_data["specific_services"]
                        category_has_level3 = True
            
            if category_has_level3:
                level3_services[category_name] = level3_for_category
        
        result = (service_categories, level3_services)
        self._cache[cache_key] = result
        return result
    
    def get_api_hierarchy_format(self) -> Dict:
        """
        Format for /api/v1/services/hierarchy endpoint
        Returns nested structure suitable for frontend consumption
        """
        cache_key = "api_hierarchy_format"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        hierarchy = {}
        
        for cat_id, cat_data in self.source_data.items():
            category_name = cat_data["name"]
            hierarchy[category_name] = {
                "id": cat_id,
                "name": category_name,
                "subcategories": {}
            }
            
            for subcat_name, subcat_data in cat_data["subcategories"].items():
                hierarchy[category_name]["subcategories"][subcat_name] = {
                    "name": subcat_name,
                    "request_a_pro": subcat_data.get("request_a_pro", True),
                    "specific_services": subcat_data.get("specific_services", []),
                    "hardcoded_vendor": subcat_data.get("hardcoded_vendor")
                }
        
        self._cache[cache_key] = hierarchy
        return hierarchy
    
    def get_flat_service_list(self) -> Dict[str, List[str]]:
        """
        Get flat list of all services by category
        Useful for dropdowns and simple listings
        """
        cache_key = "flat_service_list"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        result = {}
        for cat_id, cat_data in self.source_data.items():
            category_name = cat_data["name"]
            services = []
            
            for subcat_name, subcat_data in cat_data["subcategories"].items():
                services.append(subcat_name)
                # Add Level 3 services if they exist and are different from subcategory
                if "specific_services" in subcat_data:
                    for service in subcat_data["specific_services"]:
                        if service != subcat_name and service not in services:
                            services.append(f"{subcat_name} - {service}")
            
            result[category_name] = services
        
        self._cache[cache_key] = result
        return result
    
    def validate_service(self, category: str, subcategory: str, 
                        specific_service: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate a service hierarchy
        Returns (is_valid, message)
        """
        return validate_service_hierarchy(category, subcategory, specific_service)
    
    def search_services(self, query: str) -> List[Dict]:
        """
        Search for services across all categories
        Returns list of matching services with their hierarchy
        """
        query_lower = query.lower()
        results = []
        
        for cat_id, cat_data in self.source_data.items():
            category_name = cat_data["name"]
            
            for subcat_name, subcat_data in cat_data["subcategories"].items():
                # Check subcategory name
                if query_lower in subcat_name.lower():
                    results.append({
                        "category": category_name,
                        "subcategory": subcat_name,
                        "level": 2,
                        "match_type": "subcategory"
                    })
                
                # Check Level 3 services
                if "specific_services" in subcat_data:
                    for service in subcat_data["specific_services"]:
                        if query_lower in service.lower():
                            results.append({
                                "category": category_name,
                                "subcategory": subcat_name,
                                "specific_service": service,
                                "level": 3,
                                "match_type": "specific_service"
                            })
        
        return results
    
    def get_service_count_stats(self) -> Dict:
        """Get statistics about service counts"""
        total_categories = len(self.source_data)
        total_subcategories = 0
        total_level3_services = 0
        categories_with_level3 = 0
        
        for cat_data in self.source_data.values():
            subcats = cat_data["subcategories"]
            total_subcategories += len(subcats)
            
            has_level3 = False
            for subcat_data in subcats.values():
                if "specific_services" in subcat_data and subcat_data["specific_services"]:
                    total_level3_services += len(subcat_data["specific_services"])
                    has_level3 = True
            
            if has_level3:
                categories_with_level3 += 1
        
        return {
            "total_categories": total_categories,
            "total_subcategories": total_subcategories,
            "total_level3_services": total_level3_services,
            "categories_with_level3": categories_with_level3,
            "average_subcategories_per_category": round(total_subcategories / total_categories, 2),
            "percentage_categories_with_level3": round(categories_with_level3 / total_categories * 100, 1)
        }


# ============= MODULE-LEVEL CONVENIENCE FUNCTIONS =============

# Create singleton instance
_unified_dict = UnifiedServiceDictionary()

def get_unified_dictionary() -> UnifiedServiceDictionary:
    """Get the singleton unified dictionary instance"""
    return _unified_dict

def get_categories() -> List[str]:
    """Quick access to category list"""
    return _unified_dict.get_all_categories()

def get_vendor_app_data() -> Dict:
    """Quick access to vendor application format"""
    return _unified_dict.get_vendor_application_format()

def get_vendor_matching_data() -> Tuple[Dict, Dict]:
    """Quick access to vendor matching format"""
    return _unified_dict.get_vendor_matching_format()

def get_api_hierarchy() -> Dict:
    """Quick access to API hierarchy format"""
    return _unified_dict.get_api_hierarchy_format()

def validate_service_selection(category: str, subcategory: str, 
                              specific: Optional[str] = None) -> Tuple[bool, str]:
    """Quick validation of service selection"""
    return _unified_dict.validate_service(category, subcategory, specific)

def search_for_service(query: str) -> List[Dict]:
    """Quick service search"""
    return _unified_dict.search_services(query)

# For backwards compatibility
def get_service_categories_for_vendor_matching():
    """Legacy function for vendor matching - returns SERVICE_CATEGORIES format"""
    categories, _ = _unified_dict.get_vendor_matching_format()
    return categories

def get_level3_services_for_vendor_matching():
    """Legacy function for vendor matching - returns LEVEL_3_SERVICES format"""
    _, level3 = _unified_dict.get_vendor_matching_format()
    return level3


if __name__ == "__main__":
    # Test the unified dictionary
    ud = UnifiedServiceDictionary()
    
    print("=" * 50)
    print("UNIFIED SERVICE DICTIONARY TEST")
    print("=" * 50)
    
    # Test basic access
    categories = ud.get_all_categories()
    print(f"\nTotal Categories: {len(categories)}")
    print(f"First 5 categories: {categories[:5]}")
    
    # Test vendor app format
    vendor_app_data = ud.get_vendor_application_format()
    print(f"\nVendor App Format - Boat Maintenance:")
    if "Boat Maintenance" in vendor_app_data:
        bm_data = vendor_app_data["Boat Maintenance"]
        print(f"  Subcategories: {len(bm_data['subcategories'])}")
        print(f"  Has Finsulate: {'Finsulate' in bm_data['subcategories']}")
    
    # Test statistics
    stats = ud.get_service_count_stats()
    print(f"\nService Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Test search
    search_results = ud.search_services("finsulate")
    print(f"\nSearch for 'finsulate': {len(search_results)} results")
    for result in search_results:
        print(f"  - {result}")