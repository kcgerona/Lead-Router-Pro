"""
Unified Services API Routes
These routes use the unified service dictionary module to provide
consistent service data across all applications.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

# Import from unified module
from api.services.unified_service_dictionary import (
    get_vendor_app_data,
    get_vendor_matching_data,
    get_api_hierarchy,
    get_categories,
    validate_service_selection,
    search_for_service,
    UnifiedServiceDictionary
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/unified-services", tags=["Unified Services"])

# Create singleton instance
unified_dict = UnifiedServiceDictionary()


@router.get("/vendor-application")
async def get_vendor_application_data() -> Dict[str, Any]:
    """
    Get service data formatted for vendor application widget.
    This replaces the hardcoded SERVICE_CATEGORIES in the HTML.
    
    Returns:
        Dict with categories, subcategories, and level3Services
    """
    try:
        data = get_vendor_app_data()
        
        # Also include the SINGLE_SUBCATEGORY_WITH_LEVEL3 mapping
        # This is used by the widget for special handling
        single_subcat_mapping = {
            "Boat Charters and Rentals": "Boat Charters and Rentals",
            "Boat Towing": "Get Emergency Tow",
            "Fuel Delivery": "Fuel Delivery",
            "Dock and Slip Rental": "Dock and Slip Rental",
            "Yacht Management": "Yacht Management",
            "Maritime Education and Training": "Maritime Education and Training",
            "Wholesale or Dealer Product Pricing": "Wholesale or Dealer Product Pricing"
        }
        
        return {
            "success": True,
            "services": data,
            "singleSubcategoryMapping": single_subcat_mapping,
            "message": "Service data loaded from unified dictionary"
        }
    except Exception as e:
        logger.error(f"Error getting vendor application data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hierarchy")
async def get_service_hierarchy() -> Dict[str, Any]:
    """
    Get complete service hierarchy for all purposes.
    
    Returns:
        Nested hierarchy with categories, subcategories, and services
    """
    try:
        hierarchy = get_api_hierarchy()
        return {
            "success": True,
            "data": hierarchy,
            "total_categories": len(hierarchy)
        }
    except Exception as e:
        logger.error(f"Error getting service hierarchy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_all_categories() -> Dict[str, Any]:
    """
    Get list of all Level 1 categories.
    
    Returns:
        List of category names
    """
    try:
        categories = get_categories()
        return {
            "success": True,
            "categories": categories,
            "count": len(categories)
        }
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_services(query: str) -> Dict[str, Any]:
    """
    Search for services across all categories.
    
    Args:
        query: Search term
        
    Returns:
        List of matching services with their hierarchy
    """
    try:
        if not query or len(query) < 2:
            return {
                "success": False,
                "message": "Query must be at least 2 characters",
                "results": []
            }
        
        results = search_for_service(query)
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Error searching services: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_service(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a service selection.
    
    Args:
        data: Dict with category, subcategory, and optional specific_service
        
    Returns:
        Validation result with is_valid and message
    """
    try:
        category = data.get("category")
        subcategory = data.get("subcategory")
        specific_service = data.get("specific_service")
        
        if not category or not subcategory:
            return {
                "success": False,
                "is_valid": False,
                "message": "Category and subcategory are required"
            }
        
        is_valid, message = validate_service_selection(
            category, subcategory, specific_service
        )
        
        return {
            "success": True,
            "is_valid": is_valid,
            "message": message,
            "selection": {
                "category": category,
                "subcategory": subcategory,
                "specific_service": specific_service
            }
        }
    except Exception as e:
        logger.error(f"Error validating service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_service_statistics() -> Dict[str, Any]:
    """
    Get statistics about the service dictionary.
    
    Returns:
        Service counts and statistics
    """
    try:
        stats = unified_dict.get_service_count_stats()
        return {
            "success": True,
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vendor-matching")
async def get_vendor_matching_format() -> Dict[str, Any]:
    """
    Get service data in vendor-matching format.
    Provides backwards compatibility for vendor-matching endpoints.
    
    Returns:
        SERVICE_CATEGORIES and LEVEL_3_SERVICES dictionaries
    """
    try:
        service_categories, level3_services = get_vendor_matching_data()
        return {
            "success": True,
            "service_categories": service_categories,
            "level3_services": level3_services
        }
    except Exception as e:
        logger.error(f"Error getting vendor matching data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check for unified services API.
    
    Returns:
        API status and basic statistics
    """
    try:
        stats = unified_dict.get_service_count_stats()
        return {
            "success": True,
            "status": "healthy",
            "source": "unified_service_dictionary",
            "statistics": {
                "categories": stats["total_categories"],
                "subcategories": stats["total_subcategories"],
                "level3_services": stats["total_level3_services"]
            }
        }
    except Exception as e:
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }