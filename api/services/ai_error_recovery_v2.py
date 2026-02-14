# api/services/ai_error_recovery_v2.py
# Production-ready AI Error Recovery with all improvements from code review

import os
import json
import hashlib
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime
from pathlib import Path
import anthropic
from functools import lru_cache
from cachetools import TTLCache
import time

from config import AppConfig

logger = logging.getLogger(__name__)

class RetryState(Enum):
    """State machine for retry logic"""
    INITIAL = "initial"
    ANALYZING = "analyzing"
    CORRECTING = "correcting"
    RETRYING = "retrying"
    SUCCESS = "success"
    FAILED = "failed"
    MAX_RETRIES_REACHED = "max_retries_reached"

@dataclass
class AnalysisResult:
    """Structured analysis result"""
    error_type: str
    root_cause: str
    problematic_fields: List[str]
    suggested_corrections: Dict[str, str]
    corrected_payload: Optional[Dict[str, Any]]
    confidence: str
    reasoning: str
    retry_recommended: bool
    additional_checks: List[str]
    ai_powered: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "root_cause": self.root_cause,
            "problematic_fields": self.problematic_fields,
            "suggested_corrections": self.suggested_corrections,
            "corrected_payload": self.corrected_payload,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "retry_recommended": self.retry_recommended,
            "additional_checks": self.additional_checks,
            "ai_powered": self.ai_powered
        }

class FieldReferenceService:
    """Separated service for field reference management"""
    
    def __init__(self):
        self.field_reference = {}
        self._field_embeddings = {}  # For future embedding-based matching
        self._load_field_reference()
    
    def _load_field_reference(self):
        """Load field reference once at startup (app data path to avoid permission errors)."""
        ref_path = getattr(AppConfig, "FIELD_REFERENCE_PATH", "data/field_reference.json")
        reference_file = Path(ref_path)
        
        try:
            if reference_file.exists():
                with open(reference_file, 'r') as f:
                    data = json.load(f)
                    self.field_reference = data.get('all_ghl_fields', {})
                logger.info(f"✅ Loaded {len(self.field_reference)} field definitions")
            else:
                logger.warning("⚠️ field_reference.json not found - using minimal fallback")
                self.field_reference = self._get_minimal_fallback()
        except Exception as e:
            logger.error(f"❌ Error loading field reference: {e}")
            self.field_reference = self._get_minimal_fallback()
    
    def _get_minimal_fallback(self) -> Dict[str, Any]:
        """Minimal fallback when field_reference.json is unavailable"""
        return {
            "firstName": {"fieldKey": "contact.firstName", "dataType": "TEXT", "name": "First Name"},
            "lastName": {"fieldKey": "contact.lastName", "dataType": "TEXT", "name": "Last Name"},
            "email": {"fieldKey": "contact.email", "dataType": "EMAIL", "name": "Email"},
            "phone": {"fieldKey": "contact.phone", "dataType": "PHONE", "name": "Phone"}
        }
    
    def slice_relevant_fields(self, payload_keys: List[str], error_text: str = "") -> Dict[str, Any]:
        """Extract only relevant field definitions for analysis"""
        relevant_fields = {}
        
        # Direct key matches
        for key in payload_keys:
            if key in self.field_reference:
                relevant_fields[key] = self.field_reference[key]
        
        # Fuzzy matches based on error text
        if error_text:
            error_lower = error_text.lower()
            for field_key, field_def in self.field_reference.items():
                field_name = field_def.get('name', '').lower()
                if field_name in error_lower or field_key.lower() in error_lower:
                    relevant_fields[field_key] = field_def
        
        # Always include core fields
        core_fields = ["firstName", "lastName", "email", "phone"]
        for field in core_fields:
            if field in self.field_reference:
                relevant_fields[field] = self.field_reference[field]
        
        return relevant_fields
    
    def find_similar_fields(self, field_name: str, max_results: int = 5) -> List[Tuple[str, Dict[str, Any], float]]:
        """Find similar fields using simple string matching (placeholder for embeddings)"""
        field_name_lower = field_name.lower()
        matches = []
        
        for key, field_def in self.field_reference.items():
            name_lower = field_def.get('name', '').lower()
            key_lower = key.lower()
            
            # Simple similarity scoring
            score = 0.0
            if field_name_lower == key_lower:
                score = 1.0
            elif field_name_lower in key_lower or key_lower in field_name_lower:
                score = 0.8
            elif field_name_lower == name_lower:
                score = 0.9
            elif field_name_lower in name_lower or name_lower in field_name_lower:
                score = 0.6
            elif any(word in name_lower for word in field_name_lower.split('_')):
                score = 0.4
            
            if score > 0.3:
                matches.append((key, field_def, score))
        
        return sorted(matches, key=lambda x: x[2], reverse=True)[:max_results]

class ErrorSignatureCache:
    """LRU cache for repeated error patterns"""
    
    def __init__(self, max_size: int = 100, ttl: int = 3600):  # 1 hour TTL
        self.cache = TTLCache(maxsize=max_size, ttl=ttl)
        self.hit_count = 0
        self.miss_count = 0
    
    def _create_signature(self, error_response: Dict[str, Any], payload_keys: List[str]) -> str:
        """Create a signature for error+payload combination"""
        error_text = error_response.get("response_text", "")
        status_code = error_response.get("status_code", 0)
        sorted_keys = sorted(payload_keys)
        
        signature_data = f"{status_code}:{error_text[:200]}:{','.join(sorted_keys)}"
        return hashlib.md5(signature_data.encode()).hexdigest()
    
    def get(self, error_response: Dict[str, Any], payload_keys: List[str]) -> Optional[AnalysisResult]:
        """Get cached analysis if available"""
        signature = self._create_signature(error_response, payload_keys)
        
        if signature in self.cache:
            self.hit_count += 1
            cached_result = self.cache[signature]
            # Reduce confidence for cached results
            cached_result.confidence = "medium" if cached_result.confidence == "high" else "low"
            logger.info(f"🎯 Cache hit for error signature: {signature[:8]}")
            return cached_result
        
        self.miss_count += 1
        return None
    
    def put(self, error_response: Dict[str, Any], payload_keys: List[str], analysis: AnalysisResult):
        """Cache analysis result"""
        signature = self._create_signature(error_response, payload_keys)
        self.cache[signature] = analysis
        logger.debug(f"💾 Cached analysis for signature: {signature[:8]}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hits": self.hit_count,
            "misses": self.miss_count,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_size": len(self.cache),
            "max_size": self.cache.maxsize
        }

class AIErrorRecoveryServiceV2:
    """Production-ready AI Error Recovery Service with all improvements"""
    
    def __init__(self):
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        self.enabled = bool(self.anthropic_api_key and self.anthropic_api_key != "your_anthropic_api_key")
        
        # Initialize services
        self.field_service = FieldReferenceService()
        self.error_cache = ErrorSignatureCache()
        
        # Metrics
        self.metrics = {
            "total_analyses": 0,
            "cache_hits": 0,
            "ai_calls": 0,
            "token_usage": {"input": 0, "output": 0},
            "retry_attempts": 0,
            "successful_recoveries": 0
        }
        
        # Load prompt template
        self.prompt_template = self._load_prompt_template()
        
        if self.enabled:
            try:
                self.client = anthropic.Anthropic(api_key=self.anthropic_api_key)
                logger.info("✅ AI Error Recovery V2 initialized with Anthropic")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Anthropic client: {e}")
                self.enabled = False
        else:
            logger.warning("⚠️ AI Error Recovery V2 disabled - no valid ANTHROPIC_API_KEY")
    
    def _load_prompt_template(self) -> str:
        """Load external prompt template"""
        template_file = Path("prompts/error_analysis_template.txt")
        
        if template_file.exists():
            try:
                with open(template_file, 'r') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"⚠️ Could not load prompt template: {e}")
        
        # Fallback to inline template
        return """You are an expert at analyzing GoHighLevel API errors and suggesting corrections.

CONTEXT:
Operation: {operation_type}
Endpoint: {endpoint}
Error Status: {status_code}

ERROR RESPONSE:
{error_text}

PAYLOAD (compact):
{payload_json}

RELEVANT GHL FIELDS:
{relevant_fields}

Analyze and respond with the specified JSON structure for error correction."""
    
    async def analyze_ghl_api_error(self, 
                                   error_response: Dict[str, Any], 
                                   original_payload: Dict[str, Any],
                                   api_endpoint: str,
                                   operation_type: str = "unknown") -> AnalysisResult:
        """Enhanced error analysis with caching and efficiency improvements"""
        
        self.metrics["total_analyses"] += 1
        
        payload_keys = list(original_payload.keys()) if isinstance(original_payload, dict) else []
        
        # Check cache first
        cached_result = self.error_cache.get(error_response, payload_keys)
        if cached_result:
            self.metrics["cache_hits"] += 1
            return cached_result
        
        if not self.enabled:
            return self._fallback_error_analysis(error_response, original_payload)
        
        try:
            # Get only relevant field definitions
            error_text = error_response.get("response_text", "")
            relevant_fields = self.field_service.slice_relevant_fields(payload_keys, error_text)
            
            # Prepare minimal context
            context = self._prepare_minimal_context(
                error_response, original_payload, api_endpoint, operation_type, relevant_fields
            )
            
            # Use structured function calling
            analysis = await self._query_claude_structured(context)
            
            # Cache the result
            self.error_cache.put(error_response, payload_keys, analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ AI Error Analysis exception: {e}")
            return self._fallback_error_analysis(error_response, original_payload)
    
    def _prepare_minimal_context(self, 
                                error_response: Dict[str, Any], 
                                original_payload: Dict[str, Any],
                                api_endpoint: str,
                                operation_type: str,
                                relevant_fields: Dict[str, Any]) -> Dict[str, str]:
        """Prepare minimal, token-efficient context"""
        
        # Compact JSON serialization
        sanitized_payload = self._sanitize_payload_minimal(original_payload)
        payload_json = json.dumps(sanitized_payload, separators=(',', ':'))
        
        # Compact field definitions
        field_summaries = []
        for key, field_def in relevant_fields.items():
            field_summaries.append(f"{key}:{field_def.get('dataType', 'TEXT')}")
        
        return {
            "operation_type": operation_type,
            "endpoint": api_endpoint,
            "status_code": str(error_response.get("status_code", "")),
            "error_text": error_response.get("response_text", "")[:500],  # Truncate
            "payload_json": payload_json,
            "relevant_fields": ", ".join(field_summaries)
        }
    
    def _sanitize_payload_minimal(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ultra-minimal payload sanitization"""
        
        if not isinstance(payload, dict):
            return {"type": type(payload).__name__}
        
        sanitized = {}
        sensitive_keys = {"password", "token", "key", "secret", "auth"}
        
        for key, value in payload.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, (str, int, float, bool)):
                # Truncate long strings
                if isinstance(value, str) and len(value) > 100:
                    sanitized[key] = value[:100] + "..."
                else:
                    sanitized[key] = value
            elif isinstance(value, list):
                sanitized[key] = f"[Array({len(value)})]"
            elif isinstance(value, dict):
                sanitized[key] = f"[Object({len(value)})]"
            else:
                sanitized[key] = f"[{type(value).__name__}]"
        
        return sanitized
    
    async def _query_claude_structured(self, context: Dict[str, str]) -> AnalysisResult:
        """Use structured function calling for reliable parsing"""
        
        self.metrics["ai_calls"] += 1
        
        # Fill template with minimal placeholders
        prompt = self.prompt_template.format(**context)
        
        try:
            # Use Anthropic's tools/function calling for structured output
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,  # Reduced tokens
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                tools=[
                    {
                        "name": "error_analysis",
                        "description": "Analyze API error and suggest corrections",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "error_type": {
                                    "type": "string",
                                    "enum": ["validation_error", "format_error", "missing_field", "duplicate", "auth_error", "unknown"]
                                },
                                "root_cause": {"type": "string"},
                                "problematic_fields": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "suggested_corrections": {
                                    "type": "object",
                                    "additionalProperties": {"type": "string"}
                                },
                                "corrected_payload": {"type": "object"},
                                "confidence": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"]
                                },
                                "reasoning": {"type": "string"},
                                "retry_recommended": {"type": "boolean"},
                                "additional_checks": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "required": ["error_type", "root_cause", "confidence", "retry_recommended"]
                        }
                    }
                ],
                tool_choice={"type": "tool", "name": "error_analysis"}
            )
            
            # Track token usage
            if hasattr(response, 'usage'):
                self.metrics["token_usage"]["input"] += response.usage.input_tokens
                self.metrics["token_usage"]["output"] += response.usage.output_tokens
            
            # Extract structured result
            if response.content and response.content[0].type == "tool_use":
                tool_input = response.content[0].input
                
                return AnalysisResult(
                    error_type=tool_input.get("error_type", "unknown"),
                    root_cause=tool_input.get("root_cause", ""),
                    problematic_fields=tool_input.get("problematic_fields", []),
                    suggested_corrections=tool_input.get("suggested_corrections", {}),
                    corrected_payload=tool_input.get("corrected_payload"),
                    confidence=tool_input.get("confidence", "low"),
                    reasoning=tool_input.get("reasoning", ""),
                    retry_recommended=tool_input.get("retry_recommended", False),
                    additional_checks=tool_input.get("additional_checks", []),
                    ai_powered=True
                )
            
            # Fallback if structured output fails
            raise Exception("No structured output received")
            
        except Exception as e:
            logger.error(f"❌ Claude structured query error: {e}")
            # Return minimal fallback analysis
            return AnalysisResult(
                error_type="unknown",
                root_cause=f"AI analysis failed: {e}",
                problematic_fields=[],
                suggested_corrections={},
                corrected_payload=None,
                confidence="low",
                reasoning="AI analysis unavailable",
                retry_recommended=False,
                additional_checks=[],
                ai_powered=False
            )
    
    def _fallback_error_analysis(self, 
                                error_response: Dict[str, Any], 
                                original_payload: Dict[str, Any]) -> AnalysisResult:
        """Enhanced rule-based fallback"""
        
        status_code = error_response.get("status_code")
        response_text = error_response.get("response_text", "").lower()
        
        # More sophisticated rule-based analysis
        if status_code == 400:
            if "email" in response_text and "invalid" in response_text:
                return AnalysisResult(
                    error_type="validation_error",
                    root_cause="Email validation failed",
                    problematic_fields=["email"],
                    suggested_corrections={"email": "Fix email format"},
                    corrected_payload=None,
                    confidence="medium",
                    reasoning="Email validation error detected in response",
                    retry_recommended=True,
                    additional_checks=["Verify email format"],
                    ai_powered=False
                )
        
        # Generic fallback
        return AnalysisResult(
            error_type="unknown",
            root_cause=f"HTTP {status_code} error",
            problematic_fields=[],
            suggested_corrections={},
            corrected_payload=None,
            confidence="low",
            reasoning="Rule-based analysis - limited information",
            retry_recommended=False,
            additional_checks=[],
            ai_powered=False
        )
    
    async def smart_retry_with_state_machine(self,
                                           api_function,
                                           original_payload: Dict[str, Any],
                                           error_response: Dict[str, Any],
                                           api_endpoint: str,
                                           operation_type: str,
                                           max_retries: int = 2) -> Dict[str, Any]:
        """State machine-based retry logic"""
        
        # Initialize state machine
        state = RetryState.INITIAL
        retry_attempt = 0
        current_payload = original_payload.copy()
        analysis_history = []
        
        start_time = time.time()
        
        logger.info(f"🤖 Starting state machine retry for {operation_type}")
        
        while state not in [RetryState.SUCCESS, RetryState.FAILED, RetryState.MAX_RETRIES_REACHED]:
            
            if state == RetryState.INITIAL:
                # Analyze the initial error
                state = RetryState.ANALYZING
                
            elif state == RetryState.ANALYZING:
                analysis = await self.analyze_ghl_api_error(
                    error_response, current_payload, api_endpoint, operation_type
                )
                analysis_history.append(analysis)
                
                if not analysis.retry_recommended:
                    state = RetryState.FAILED
                else:
                    state = RetryState.CORRECTING
                    
            elif state == RetryState.CORRECTING:
                # Apply corrections
                latest_analysis = analysis_history[-1]
                current_payload = await self._apply_corrections_smart(
                    current_payload, latest_analysis
                )
                state = RetryState.RETRYING
                
            elif state == RetryState.RETRYING:
                retry_attempt += 1
                self.metrics["retry_attempts"] += 1
                
                if retry_attempt > max_retries:
                    state = RetryState.MAX_RETRIES_REACHED
                    break
                
                # Attempt the API call
                try:
                    result = await api_function(current_payload)
                    
                    if result and not isinstance(result, dict) or not result.get("error"):
                        state = RetryState.SUCCESS
                        self.metrics["successful_recoveries"] += 1
                        break
                    
                    # Still failing - analyze new error
                    if isinstance(result, dict) and result.get("error"):
                        error_response = result
                        state = RetryState.ANALYZING
                    else:
                        state = RetryState.FAILED
                        
                except Exception as e:
                    logger.error(f"❌ Exception during retry {retry_attempt}: {e}")
                    state = RetryState.FAILED
        
        # Compile final result
        elapsed_time = time.time() - start_time
        
        return {
            "success": state == RetryState.SUCCESS,
            "final_state": state.value,
            "retry_attempted": retry_attempt > 0,
            "retry_attempts": retry_attempt,
            "analysis_history": [a.to_dict() for a in analysis_history],
            "final_payload": current_payload,
            "elapsed_time_seconds": round(elapsed_time, 3),
            "final_error": error_response if state != RetryState.SUCCESS else None
        }
    
    async def _apply_corrections_smart(self, 
                                     payload: Dict[str, Any], 
                                     analysis: AnalysisResult) -> Dict[str, Any]:
        """Apply AI corrections with field reference awareness"""
        
        corrected = payload.copy()
        
        # Apply AI-suggested corrected payload if available
        if analysis.corrected_payload:
            corrected.update(analysis.corrected_payload)
        
        # Apply specific field corrections
        for field in analysis.problematic_fields:
            if field in corrected:
                correction = analysis.suggested_corrections.get(field, "")
                
                # Use field reference for smart corrections
                field_def = self.field_service.field_reference.get(field, {})
                data_type = field_def.get('dataType', 'TEXT')
                
                if field == "email" and data_type == "EMAIL":
                    corrected[field] = self._fix_email(corrected[field])
                elif field == "phone" and data_type == "PHONE":
                    corrected[field] = self._fix_phone(corrected[field])
                
                logger.info(f"🔧 Applied smart correction to {field} ({data_type})")
        
        return corrected
    
    def _fix_email(self, email: str) -> str:
        """Smart email correction"""
        if not isinstance(email, str):
            return str(email)
        
        email = email.strip().lower()
        
        # Common fixes
        if "@" not in email and "." in email:
            # Might be missing @
            parts = email.split(".")
            if len(parts) >= 2:
                email = f"{parts[0]}@{'.'.join(parts[1:])}"
        
        return email
    
    def _fix_phone(self, phone: str) -> str:
        """Smart phone correction"""
        if not isinstance(phone, str):
            return str(phone)
        
        # Extract digits only
        digits = ''.join(filter(str.isdigit, phone))
        
        # Apply E.164 format
        if len(digits) == 10:
            return f"+1{digits}"
        elif len(digits) == 11 and digits.startswith("1"):
            return f"+{digits}"
        
        return phone
    
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """Comprehensive service statistics"""
        cache_stats = self.error_cache.get_stats()
        
        return {
            "ai_enabled": self.enabled,
            "anthropic_configured": bool(self.anthropic_api_key),
            "service_status": "active" if self.enabled else "disabled",
            "field_reference_loaded": len(self.field_service.field_reference),
            "metrics": self.metrics,
            "cache_stats": cache_stats,
            "efficiency": {
                "cache_hit_rate": cache_stats["hit_rate_percent"],
                "avg_tokens_per_call": (
                    self.metrics["token_usage"]["input"] + self.metrics["token_usage"]["output"]
                ) / max(self.metrics["ai_calls"], 1),
                "successful_recovery_rate": (
                    self.metrics["successful_recoveries"] / max(self.metrics["retry_attempts"], 1) * 100
                ) if self.metrics["retry_attempts"] > 0 else 0
            },
            "last_check": datetime.now().isoformat()
        }


# Global enhanced instance
ai_error_recovery_v2 = AIErrorRecoveryServiceV2()