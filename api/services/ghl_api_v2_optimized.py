# api/services/ghl_api_v2_optimized.py
"""
Optimized GoHighLevel API Client
Uses v2 API endpoints with PIT token for improved performance
Only falls back to v1 for vendor user creation
"""

import requests
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class OptimizedGoHighLevelAPI:
    """
    Optimized GHL API client that uses v2 endpoints by default
    Significant latency improvements by using PIT token and v2 endpoints
    """
    
    def __init__(self, private_token: str = None, location_id: str = None, 
                 agency_api_key: str = None, location_api_key: str = None):
        """
        Initialize with PIT token as primary authentication
        Only use location API key as fallback or for specific v1 operations
        """
        self.private_token = private_token  # V2 PIT Token (PRIMARY)
        self.location_id = location_id
        self.agency_api_key = agency_api_key
        self.location_api_key = location_api_key  # V1 API Key (only for vendor user creation)
        
        # V2 API base URLs
        self.v2_base_url = "https://services.leadconnectorhq.com"
        self.v1_base_url = "https://rest.gohighlevel.com"
        
        # V2 headers with PIT token
        self.v2_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.private_token}",
            "Content-Type": "application/json",
            "Version": "2021-07-28"
        }
        
        # V1 headers for vendor user creation only
        if agency_api_key:
            self.v1_agency_headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {agency_api_key}",
                "Content-Type": "application/json",
                "Version": "2021-07-28"
            }
        else:
            self.v1_agency_headers = None
        
        if not self.private_token:
            raise ValueError("PIT token is required for v2 API operations")
        
        logger.info("🚀 Optimized GHL API v2 initialized")
        logger.info(f"   📍 Using v2 endpoints with PIT token for all operations except vendor user creation")
    
    # ============================================
    # CONTACT OPERATIONS (V2 API)
    # ============================================
    
    def search_contacts(self, query: str = None, email: str = None, phone: str = None, limit: int = 20) -> List[Dict]:
        """Deprecated: GET /contacts/ is deprecated. Use search_contacts_paginated (POST /contacts/search) or search_contacts_by_email for email lookup."""
        try:
            url = f"{self.v2_base_url}/contacts/"
            params = {
                "locationId": self.location_id,
                "limit": min(limit, 100)
            }
            if email:
                params["email"] = email
            elif phone:
                params["phone"] = phone
            elif query:
                params["query"] = query
            logger.debug(f"🔍 Searching contacts with v2 API: {params}")
            response = requests.get(url, headers=self.v2_headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                contacts = data.get('contacts', [])
                logger.info(f"✅ Found {len(contacts)} contacts using v2 API")
                return contacts
            else:
                logger.error(f"❌ v2 contact search failed: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"❌ Error searching contacts with v2 API: {str(e)}")
            return []

    def search_contacts_by_email(self, email: str, location_id: Optional[str] = None) -> List[Dict]:
        """
        Search contacts by email using POST /contacts/search (advanced search).
        Ref: https://marketplace.gohighlevel.com/docs/ghl/contacts/search-contacts-advanced
        Schema: https://doc.clickup.com/8631005/d/h/87cpx-158396/6e629989abe7fad
        """
        try:
            url = f"{self.v2_base_url}/contacts/search"
            loc = location_id or self.location_id
            # POST body: locationId + query (email value alone per API docs)
            payload = {
                "locationId": loc,
                "query": email.strip(),
            }
            response = requests.post(url, headers=self.v2_headers, json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                contacts = data.get("contacts", [])
                # Filter to exact email match (search can return partial matches)
                email_lower = email.lower().strip()
                exact = [c for c in contacts if (c.get("email") or "").lower().strip() == email_lower]
                result = exact if exact else contacts
                if result:
                    logger.info(f"✅ Found {len(result)} contact(s) for email {email[:3]}... via POST /contacts/search")
                return result
            else:
                logger.warning(f"   POST /contacts/search returned {response.status_code} for {email[:3]}...")
                return []
        except Exception as e:
            logger.warning(f"   search_contacts_by_email failed for {email[:3]}...: {e}")
            return []

    def search_contacts_paginated(
        self,
        location_id: Optional[str] = None,
        limit: int = 500,
        search_after: Optional[List[Any]] = None,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List/search contacts using POST /contacts/search (non-deprecated).
        Use this instead of GET /contacts/ which is deprecated.
        Ref: https://marketplace.gohighlevel.com/docs/ghl/contacts/search-contacts-advanced
        Schema: https://doc.clickup.com/8631005/d/h/87cpx-158396/6e629989abe7fad

        :param location_id: Location to search (defaults to instance location_id).
        :param limit: Max contacts per request (default 500; use up to 500).
        :param search_after: Cursor from previous response (last contact's "searchAfter" field).
        :param query: Optional search query (omit or empty to list all).
        :return: {"contacts": [...], "total": int, "search_after": [...] or None}
                 "search_after" is the cursor for the next page (from last contact).
        """
        try:
            url = f"{self.v2_base_url}/contacts/search"
            loc = location_id or self.location_id
            payload = {
                "locationId": loc,
                "limit": min(max(1, limit), 500),
            }
            if query is not None and str(query).strip():
                payload["query"] = str(query).strip()
            if search_after is not None and len(search_after) > 0:
                payload["searchAfter"] = search_after
            response = requests.post(url, headers=self.v2_headers, json=payload, timeout=30)
            if response.status_code != 200:
                logger.error(f"❌ POST /contacts/search failed: {response.status_code} - {response.text[:200]}")
                return {"contacts": [], "total": 0, "search_after": None}
            data = response.json()
            contacts = data.get("contacts") or []
            total = data.get("total", 0)
            next_cursor = None
            if contacts and isinstance(contacts[-1], dict) and "searchAfter" in contacts[-1]:
                next_cursor = contacts[-1].get("searchAfter")
            logger.info(f"✅ POST /contacts/search returned {len(contacts)} contacts (total={total})")
            return {"contacts": contacts, "total": total, "search_after": next_cursor}
        except Exception as e:
            logger.error(f"❌ search_contacts_paginated failed: {e}")
            return {"contacts": [], "total": 0, "search_after": None}
    
    def get_contact_by_id(self, contact_id: str, location_id: Optional[str] = None) -> Optional[Dict]:
        """Get contact by ID using v2 API. Pass location_id to scope to a location (recommended)."""
        try:
            url = f"{self.v2_base_url}/contacts/{contact_id}"
            params = {}
            if location_id or self.location_id:
                params["locationId"] = location_id or self.location_id
            response = requests.get(url, headers=self.v2_headers, params=params or None, timeout=15)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Retrieved contact {contact_id} using v2 API")
                return data.get('contact', data)
            else:
                logger.error(f"❌ Failed to get contact {contact_id}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Error getting contact {contact_id}: {str(e)}")
            return None
    
    def create_contact(self, contact_data: Dict) -> Optional[Dict]:
        """Create contact using v2 API for improved performance"""
        try:
            # V2 endpoint
            url = f"{self.v2_base_url}/contacts/"
            
            # Ensure locationId is present
            payload = {
                "locationId": self.location_id,
                **contact_data
            }
            
            logger.info(f"📞 Creating contact with v2 API: {contact_data.get('email', 'unknown')}")
            
            response = requests.post(url, headers=self.v2_headers, json=payload, timeout=15)
            
            if response.status_code in [200, 201]:
                data = response.json()
                contact_id = data.get("contact", {}).get("id") or data.get("id")
                logger.info(f"✅ Contact created successfully with v2 API: {contact_id}")
                return data
            else:
                logger.error(f"❌ v2 contact creation failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                
                # Return error details for debugging
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "message": response.text,
                    "api_version": "v2"
                }
                
        except requests.exceptions.Timeout:
            logger.error("⏱️ v2 contact creation timeout")
            return {"error": True, "message": "Request timeout", "api_version": "v2"}
        except Exception as e:
            logger.error(f"❌ Error creating contact with v2 API: {str(e)}")
            return {"error": True, "message": str(e), "api_version": "v2"}
    
    def update_contact(self, contact_id: str, update_data: Dict) -> bool:
        """Update contact using v2 API"""
        try:
            # V2 endpoint
            url = f"{self.v2_base_url}/contacts/{contact_id}"
            
            # Remove fields that shouldn't be updated
            fields_to_remove = ['id', 'locationId', 'dateAdded', 'dateUpdated']
            for field in fields_to_remove:
                update_data.pop(field, None)
            
            logger.info(f"📝 Updating contact {contact_id} with v2 API")
            
            response = requests.put(url, headers=self.v2_headers, json=update_data, timeout=15)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Contact {contact_id} updated successfully with v2 API")
                return True
            else:
                logger.error(f"❌ v2 contact update failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating contact {contact_id}: {str(e)}")
            return False
    
    # ============================================
    # OPPORTUNITY OPERATIONS (V2 API)
    # ============================================
    
    def create_opportunity(self, opportunity_data: Dict) -> Optional[Dict]:
        """Create opportunity using v2 API"""
        try:
            # V2 endpoint
            url = f"{self.v2_base_url}/opportunities/"
            
            # Don't include locationId in payload - it's already set correctly in the data
            payload = opportunity_data.copy()
            
            logger.info(f"🎯 Creating opportunity with v2 API")
            
            response = requests.post(url, headers=self.v2_headers, json=payload, timeout=15)
            
            if response.status_code in [200, 201]:
                data = response.json()
                opp_id = data.get("opportunity", {}).get("id") or data.get("id")
                logger.info(f"✅ Opportunity created successfully with v2 API: {opp_id}")
                return data
            else:
                logger.error(f"❌ v2 opportunity creation failed: {response.status_code}")
                logger.error(f"   Request payload: {json.dumps(payload, indent=2)}")
                logger.error(f"   Response: {response.text[:500]}")  # Log error details
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating opportunity: {str(e)}")
            return None
    
    def get_opportunities_by_contact(self, contact_id: str) -> List[Dict]:
        """Get opportunities for a contact using v2 API"""
        try:
            # V2 API endpoint for searching opportunities
            url = f"{self.v2_base_url}/opportunities/search"
            
            # Log the location_id to debug
            logger.info(f"🔍 Getting opportunities for contact {contact_id}")
            logger.info(f"   Location ID from self: {self.location_id}")
            
            # FIXED: Ensure location_id is not None
            if not self.location_id:
                logger.error("❌ Location ID is not set!")
                return []
            
            # Use underscore format for this endpoint
            params = {
                "location_id": str(self.location_id),  # This endpoint uses underscore
                "contact_id": str(contact_id),         # This endpoint uses underscore
                "limit": 20
            }
            
            logger.info(f"   Request URL: {url}")
            logger.info(f"   Request params: {json.dumps(params, indent=2)}")
            
            response = requests.get(url, headers=self.v2_headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                opportunities = data.get('opportunities', [])
                logger.info(f"✅ Found {len(opportunities)} opportunities for contact {contact_id}")
                return opportunities
            else:
                logger.error(f"❌ Failed to get opportunities: {response.status_code}")
                logger.error(f"   Response: {response.text[:500]}")  # Log error details
                return []
                
        except Exception as e:
            logger.error(f"❌ Error getting opportunities: {str(e)}")
            return []
    
    def update_opportunity(self, opportunity_id: str, update_data: Dict) -> bool:
        """Update opportunity using v2 API"""
        try:
            # V2 endpoint
            url = f"{self.v2_base_url}/opportunities/{opportunity_id}"
            
            logger.info(f"📝 Updating opportunity {opportunity_id} with v2 API")
            logger.info(f"   Update data: {json.dumps(update_data, indent=2)}")
            
            response = requests.put(url, headers=self.v2_headers, json=update_data, timeout=15)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Opportunity {opportunity_id} updated successfully")
                return True
            else:
                logger.error(f"❌ v2 opportunity update failed: {response.status_code}")
                logger.error(f"   Response: {response.text[:500]}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating opportunity: {str(e)}")
            return False
    
    def get_opportunity_by_id(self, opportunity_id: str) -> Optional[Dict]:
        """Get opportunity by ID using v2 API"""
        try:
            # V2 endpoint
            url = f"{self.v2_base_url}/opportunities/{opportunity_id}"
            
            response = requests.get(url, headers=self.v2_headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Retrieved opportunity {opportunity_id}")
                return data.get('opportunity', data)
            else:
                logger.error(f"❌ Failed to get opportunity: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting opportunity: {str(e)}")
            return None
    
    def search_opportunities(self, query: str = None, contact_id: str = None, 
                           pipeline_id: str = None, stage_id: str = None,
                           status: str = None, limit: int = 20) -> List[Dict]:
        """Search opportunities using v2 API with improved filtering"""
        try:
            # V2 API endpoint for searching
            url = f"{self.v2_base_url}/opportunities/search"
            
            params = {
                "locationId": self.location_id,
                "limit": min(limit, 100)
            }
            
            if query:
                params["q"] = query
            if contact_id:
                params["contact_id"] = contact_id
            if pipeline_id:
                params["pipelineId"] = pipeline_id
            if stage_id:
                params["stageId"] = stage_id
            if status:
                params["status"] = status
            
            response = requests.get(url, headers=self.v2_headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('opportunities', [])
            else:
                logger.error(f"❌ v2 opportunity search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error searching opportunities: {str(e)}")
            return []
    
    def get_pipelines(self) -> List[Dict]:
        """Get pipelines using v2 API"""
        try:
            # V2 endpoint
            url = f"{self.v2_base_url}/opportunities/pipelines"
            
            params = {"locationId": self.location_id}
            
            response = requests.get(url, headers=self.v2_headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('pipelines', [])
            else:
                logger.error(f"❌ Failed to get pipelines: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error getting pipelines: {str(e)}")
            return []
    
    # ============================================
    # USER OPERATIONS (V1 API - VENDOR CREATION ONLY)
    # ============================================
    
    def create_vendor_user(self, user_data: Dict) -> Optional[Dict]:
        """
        Create vendor user using v1 API
        This is the ONLY operation that requires v1 API
        """
        if not self.v1_agency_headers:
            logger.error("❌ Agency API key required for vendor user creation")
            return None
        
        try:
            # V1 endpoint for user creation
            url = f"{self.v1_base_url}/v1/users/"
            
            # Prepare v1 user data
            payload = {
                "locationIds": [self.location_id],
                **user_data
            }
            
            logger.info(f"👤 Creating vendor user with v1 API: {user_data.get('email')}")
            logger.debug(f"Using v1 endpoint: {url}")
            
            response = requests.post(url, headers=self.v1_agency_headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201]:
                data = response.json()
                user_id = data.get("user", {}).get("id") or data.get("id")
                logger.info(f"✅ Vendor user created successfully with v1 API: {user_id}")
                return data
            else:
                logger.error(f"❌ v1 vendor user creation failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating vendor user with v1 API: {str(e)}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Check if vendor user exists using v1 API
        Used before creating new vendor users
        """
        if not self.v1_agency_headers:
            logger.error("❌ Agency API key required for user lookup")
            return None
        
        try:
            # V1 endpoint for user lookup
            url = f"{self.v1_base_url}/v1/users"
            
            params = {
                "locationId": self.location_id,
                "email": email
            }
            
            response = requests.get(url, headers=self.v1_agency_headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                users = data.get("users", [])
                
                for user in users:
                    if user.get("email", "").lower() == email.lower():
                        logger.info(f"✅ Found existing vendor user: {email}")
                        return user
                
                logger.info(f"📭 No vendor user found for email: {email}")
                return None
            else:
                logger.error(f"❌ v1 user lookup failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error looking up vendor user: {str(e)}")
            return None
    
    # ============================================
    # OTHER V2 OPERATIONS
    # ============================================
    
    def send_sms(self, contact_id: str, message: str) -> bool:
        """Send SMS using v2 API"""
        try:
            # V2 endpoint for conversations
            url = f"{self.v2_base_url}/conversations/messages"
            
            payload = {
                "type": "SMS",
                "contactId": contact_id,
                "message": message
            }
            
            response = requests.post(url, headers=self.v2_headers, json=payload, timeout=10)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ SMS sent successfully to {contact_id}")
                return True
            else:
                logger.error(f"❌ Failed to send SMS: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending SMS: {str(e)}")
            return False
    
    def add_note(self, contact_id: str, note: str) -> bool:
        """Add note to contact using v2 API"""
        try:
            # V2 endpoint for notes
            url = f"{self.v2_base_url}/contacts/{contact_id}/notes"
            
            payload = {
                "body": note
            }
            
            response = requests.post(url, headers=self.v2_headers, json=payload, timeout=10)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Note added successfully to contact {contact_id}")
                return True
            else:
                logger.error(f"❌ Failed to add note: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error adding note: {str(e)}")
            return False
    
    def add_task(self, contact_id: str, title: str, body: str = None, 
                 due_date: datetime = None, assigned_to: str = None) -> bool:
        """Add task using v2 API"""
        try:
            # V2 endpoint for tasks
            url = f"{self.v2_base_url}/contacts/{contact_id}/tasks"
            
            payload = {
                "title": title,
                "completed": False
            }
            
            if body:
                payload["body"] = body
            if due_date:
                payload["dueDate"] = due_date.isoformat()
            if assigned_to:
                payload["assignedTo"] = assigned_to
            
            response = requests.post(url, headers=self.v2_headers, json=payload, timeout=10)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Task added successfully to contact {contact_id}")
                return True
            else:
                logger.error(f"❌ Failed to add task: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error adding task: {str(e)}")
            return False
    
    def get_custom_fields(self) -> List[Dict]:
        """Get custom fields using v2 API"""
        try:
            # V2 endpoint for custom fields
            url = f"{self.v2_base_url}/locations/{self.location_id}/customFields"
            
            response = requests.get(url, headers=self.v2_headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('customFields', [])
            else:
                logger.error(f"❌ Failed to get custom fields: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error getting custom fields: {str(e)}")
            return []
    
    def get_calendars(self) -> List[Dict]:
        """Get calendars using v2 API"""
        try:
            # V2 endpoint for calendars
            url = f"{self.v2_base_url}/calendars/"
            
            params = {"locationId": self.location_id}
            
            response = requests.get(url, headers=self.v2_headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('calendars', [])
            else:
                logger.error(f"❌ Failed to get calendars: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error getting calendars: {str(e)}")
            return []
    
    # ============================================
    # MIGRATION HELPERS
    # ============================================
    
    def test_v2_connection(self) -> bool:
        """Test v2 API connection and authentication"""
        try:
            logger.info("🔍 Testing v2 API connection...")
            
            # Try to get location custom fields as a test
            url = f"{self.v2_base_url}/locations/{self.location_id}/customFields"
            
            response = requests.get(url, headers=self.v2_headers, timeout=5)
            
            if response.status_code == 200:
                logger.info("✅ v2 API connection successful!")
                return True
            else:
                logger.error(f"❌ v2 API connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ v2 API connection error: {str(e)}")
            return False
    
    def get_api_stats(self) -> Dict:
        """Get API usage statistics for monitoring"""
        return {
            "api_version": "v2",
            "using_pit_token": bool(self.private_token),
            "v1_endpoints": ["POST /v1/users/ (vendor creation only)"],
            "v2_endpoints": [
                "GET/POST/PUT /contacts/",
                "GET/POST/PUT /opportunities/",
                "GET /opportunities/search",
                "GET /locations/{locationId}/customFields",
                "POST /conversations/messages",
                "GET /calendars/"
            ],
            "optimization": "Using v2 API with PIT token for all operations except vendor user creation"
        }