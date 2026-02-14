# api/services/field_reference_service.py
# Standalone field reference service for better separation of concerns

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


def _field_reference_path() -> str:
    """Path to field_reference.json under app data (data/) to avoid permission errors."""
    try:
        from config import AppConfig
        return getattr(AppConfig, "FIELD_REFERENCE_PATH", "data/field_reference.json")
    except ImportError:
        return "data/field_reference.json"


class FieldReferenceService:
    """
    Dedicated service for managing GoHighLevel field reference data
    Provides efficient field lookup, similarity matching, and context slicing
    """
    
    def __init__(self, reference_file: Optional[str] = None):
        self.reference_file = Path(reference_file or _field_reference_path())
        self.field_reference = {}
        self._field_name_index = {}
        self._load_field_reference()
        self._build_indices()
    
    def _load_field_reference(self):
        """Load field reference data from JSON file"""
        try:
            if self.reference_file.exists():
                with open(self.reference_file, 'r') as f:
                    data = json.load(f)
                    self.field_reference = data.get('all_ghl_fields', {})
                logger.info(f"✅ Loaded {len(self.field_reference)} GHL field definitions")
            else:
                logger.warning(f"⚠️ {self.reference_file} not found - using minimal fallback")
                self.field_reference = self._get_minimal_fallback()
        except Exception as e:
            logger.error(f"❌ Error loading field reference: {e}")
            self.field_reference = self._get_minimal_fallback()
    
    def _get_minimal_fallback(self) -> Dict[str, Any]:
        """Provide minimal field definitions when reference file is unavailable"""
        return {
            "firstName": {
                "id": "firstName_id",
                "fieldKey": "contact.firstName", 
                "dataType": "TEXT", 
                "name": "First Name"
            },
            "lastName": {
                "id": "lastName_id",
                "fieldKey": "contact.lastName", 
                "dataType": "TEXT", 
                "name": "Last Name"
            },
            "email": {
                "id": "email_id",
                "fieldKey": "contact.email", 
                "dataType": "EMAIL", 
                "name": "Email"
            },
            "phone": {
                "id": "phone_id",
                "fieldKey": "contact.phone", 
                "dataType": "PHONE", 
                "name": "Phone"
            }
        }
    
    def _build_indices(self):
        """Build search indices for efficient field lookup"""
        self._field_name_index = {}
        
        for field_key, field_def in self.field_reference.items():
            # Index by field name (display name)
            field_name = field_def.get('name', '').lower()
            if field_name:
                self._field_name_index[field_name] = field_key
            
            # Index by fieldKey variations
            field_key_parts = field_def.get('fieldKey', '').split('.')
            if len(field_key_parts) > 1:
                short_key = field_key_parts[-1].lower()
                if short_key not in self._field_name_index:
                    self._field_name_index[short_key] = field_key
    
    @lru_cache(maxsize=256)
    def get_field_definition(self, field_key: str) -> Optional[Dict[str, Any]]:
        """Get field definition by key (cached)"""
        return self.field_reference.get(field_key)
    
    def slice_relevant_fields(self, 
                             payload_keys: List[str], 
                             error_text: str = "", 
                             max_fields: int = 20) -> Dict[str, Any]:
        """
        Extract only relevant field definitions for AI analysis
        
        Args:
            payload_keys: Keys present in the payload
            error_text: Error message text for fuzzy matching
            max_fields: Maximum number of fields to return
        
        Returns:
            Dict of relevant field definitions
        """
        relevant_fields = {}
        relevance_scores = {}
        
        # Always include core fields
        core_fields = ["firstName", "lastName", "email", "phone"]
        for field in core_fields:
            if field in self.field_reference:
                relevant_fields[field] = self.field_reference[field]
                relevance_scores[field] = 100  # Highest priority
        
        # Direct payload key matches
        for key in payload_keys:
            if key in self.field_reference and key not in relevant_fields:
                relevant_fields[key] = self.field_reference[key]
                relevance_scores[key] = 90
        
        # Error text fuzzy matching
        if error_text:
            error_lower = error_text.lower()
            for field_key, field_def in self.field_reference.items():
                if field_key in relevant_fields:
                    continue
                
                field_name = field_def.get('name', '').lower()
                field_key_lower = field_key.lower()
                
                score = 0
                # Direct mentions in error text
                if field_key_lower in error_lower:
                    score = 80
                elif field_name in error_lower:
                    score = 70
                # Partial word matches
                elif any(word in error_lower for word in field_name.split() if len(word) > 3):
                    score = 50
                
                if score > 0 and len(relevant_fields) < max_fields:
                    relevant_fields[field_key] = field_def
                    relevance_scores[field_key] = score
        
        # Sort by relevance and limit results
        if len(relevant_fields) > max_fields:
            sorted_fields = sorted(relevance_scores.items(), key=lambda x: x[1], reverse=True)
            top_fields = dict(sorted_fields[:max_fields])
            relevant_fields = {k: relevant_fields[k] for k in top_fields.keys()}
        
        logger.debug(f"🔍 Selected {len(relevant_fields)} relevant fields from {len(self.field_reference)} total")
        return relevant_fields
    
    def find_similar_fields(self, 
                           field_name: str, 
                           max_results: int = 5,
                           min_score: float = 0.3) -> List[Tuple[str, Dict[str, Any], float]]:
        """
        Find fields similar to the given field name
        
        Args:
            field_name: Name to search for
            max_results: Maximum number of results
            min_score: Minimum similarity score
        
        Returns:
            List of (field_key, field_def, similarity_score) tuples
        """
        field_name_lower = field_name.lower()
        matches = []
        
        for field_key, field_def in self.field_reference.items():
            field_display_name = field_def.get('name', '').lower()
            field_key_lower = field_key.lower()
            
            # Calculate similarity score
            score = self._calculate_similarity_score(field_name_lower, field_key_lower, field_display_name)
            
            if score >= min_score:
                matches.append((field_key, field_def, score))
        
        # Sort by score and return top results
        matches.sort(key=lambda x: x[2], reverse=True)
        return matches[:max_results]
    
    def _calculate_similarity_score(self, 
                                   query: str, 
                                   field_key: str, 
                                   field_name: str) -> float:
        """Calculate similarity score between query and field"""
        
        # Exact matches
        if query == field_key:
            return 1.0
        if query == field_name:
            return 0.95
        
        # Substring matches
        if query in field_key or field_key in query:
            return 0.8
        if query in field_name or field_name in query:
            return 0.75
        
        # Word-based matching
        query_words = set(query.replace('_', ' ').split())
        field_words = set(field_name.replace('_', ' ').split())
        key_words = set(field_key.replace('_', ' ').split())
        
        # Jaccard similarity for word overlap
        all_field_words = field_words.union(key_words)
        if all_field_words:
            overlap = query_words.intersection(all_field_words)
            union = query_words.union(all_field_words)
            jaccard_score = len(overlap) / len(union) if union else 0
            
            if jaccard_score > 0:
                return 0.3 + (jaccard_score * 0.4)  # 0.3 to 0.7 range
        
        return 0.0
    
    def get_field_suggestions(self, 
                             unknown_field: str, 
                             context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get comprehensive suggestions for mapping an unknown field
        
        Args:
            unknown_field: The unknown field name
            context: Additional context (form type, industry, etc.)
        
        Returns:
            Dictionary with suggestions and analysis
        """
        similar_fields = self.find_similar_fields(unknown_field)
        
        # Analyze field name patterns
        field_analysis = self._analyze_field_name(unknown_field)
        
        # Consider context if provided
        context_hints = []
        if context:
            form_type = context.get('form_type', '')
            if 'vendor' in form_type.lower():
                context_hints = ["company_name", "services_provided", "coverage_area"]
            elif 'client' in form_type.lower():
                context_hints = ["vessel_make", "vessel_model", "zip_code_of_service"]
        
        return {
            "unknown_field": unknown_field,
            "field_analysis": field_analysis,
            "similar_fields": [
                {
                    "field_key": key,
                    "field_name": field_def.get('name', ''),
                    "data_type": field_def.get('dataType', ''),
                    "similarity_score": score,
                    "confidence": "high" if score > 0.8 else "medium" if score > 0.5 else "low"
                }
                for key, field_def, score in similar_fields
            ],
            "context_hints": context_hints,
            "recommendations": self._generate_recommendations(unknown_field, similar_fields, context)
        }
    
    def _analyze_field_name(self, field_name: str) -> Dict[str, Any]:
        """Analyze field name patterns and characteristics"""
        name_lower = field_name.lower()
        
        patterns = {
            "email": ["email", "mail"],
            "phone": ["phone", "tel", "mobile"],
            "name": ["name", "first", "last"],
            "address": ["address", "street", "city", "zip", "postal"],
            "vessel": ["boat", "yacht", "vessel", "ship"],
            "service": ["service", "request", "need"],
            "date": ["date", "time", "when"],
            "location": ["location", "area", "zip", "region"]
        }
        
        detected_patterns = []
        for pattern_type, keywords in patterns.items():
            if any(keyword in name_lower for keyword in keywords):
                detected_patterns.append(pattern_type)
        
        return {
            "original_name": field_name,
            "normalized_name": name_lower.replace('_', ' ').replace('-', ' '),
            "word_count": len(field_name.split('_')),
            "detected_patterns": detected_patterns,
            "likely_type": detected_patterns[0] if detected_patterns else "unknown"
        }
    
    def _generate_recommendations(self, 
                                 field_name: str, 
                                 similar_fields: List[Tuple[str, Dict[str, Any], float]], 
                                 context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate mapping recommendations based on analysis"""
        
        if not similar_fields:
            return {
                "action": "create_new_field",
                "reason": "No similar fields found",
                "suggested_name": field_name.replace('_', ' ').title(),
                "suggested_type": "TEXT"
            }
        
        best_match = similar_fields[0]
        best_score = best_match[2]
        
        if best_score > 0.8:
            return {
                "action": "map_to_existing",
                "field_key": best_match[0],
                "confidence": "high",
                "reason": f"Strong similarity match (score: {best_score:.2f})"
            }
        elif best_score > 0.5:
            return {
                "action": "map_to_existing",
                "field_key": best_match[0],
                "confidence": "medium",
                "reason": f"Moderate similarity match (score: {best_score:.2f})"
            }
        else:
            return {
                "action": "manual_review",
                "reason": "Low similarity scores - manual review recommended",
                "alternatives": [match[0] for match in similar_fields[:3]]
            }
    
    def get_field_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded field reference"""
        
        data_types = {}
        categories = {}
        
        for field_def in self.field_reference.values():
            # Count data types
            data_type = field_def.get('dataType', 'UNKNOWN')
            data_types[data_type] = data_types.get(data_type, 0) + 1
            
            # Count categories (if available)
            category = field_def.get('category', 'uncategorized')
            categories[category] = categories.get(category, 0) + 1
        
        return {
            "total_fields": len(self.field_reference),
            "data_types": data_types,
            "categories": categories,
            "index_size": len(self._field_name_index),
            "reference_file": str(self.reference_file),
            "file_exists": self.reference_file.exists()
        }
    
    def validate_field_reference(self) -> Dict[str, Any]:
        """Validate field reference data integrity"""
        
        issues = []
        warnings = []
        
        required_fields = {"id", "fieldKey", "dataType", "name"}
        
        for field_key, field_def in self.field_reference.items():
            # Check required fields
            missing_fields = required_fields - set(field_def.keys())
            if missing_fields:
                issues.append(f"Field '{field_key}' missing: {missing_fields}")
            
            # Check field key format
            field_key_value = field_def.get('fieldKey', '')
            if field_key_value and not field_key_value.startswith('contact.'):
                warnings.append(f"Field '{field_key}' has unusual fieldKey: {field_key_value}")
            
            # Check data type validity
            valid_types = {"TEXT", "EMAIL", "PHONE", "NUMBER", "DATE", "BOOLEAN", "TEXTAREA"}
            data_type = field_def.get('dataType', '')
            if data_type and data_type not in valid_types:
                warnings.append(f"Field '{field_key}' has unknown dataType: {data_type}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "total_fields_checked": len(self.field_reference)
        }


# Global singleton instance
field_reference_service = FieldReferenceService()