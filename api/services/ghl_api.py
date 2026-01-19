# api/services/ghl_api.py

import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class GoHighLevelAPI:
    """Enhanced GHL API client with V1/V2 fallback support"""
    
    def __init__(self, location_api_key: Optional[str] = None, private_token: Optional[str] = None, location_id: Optional[str] = None, agency_api_key: Optional[str] = None, api_key: Optional[str] = None, company_id: Optional[str] = None):
        # Store both API keys for fallback logic
        self.location_api_key = location_api_key or api_key  # V1 Location API Key (preferred)
        self.private_token = private_token  # V2 PIT Token (fallback)
        self.agency_api_key = agency_api_key
        self.location_id = location_id
        self.company_id = company_id  # For V2 user creation API
        self.base_url = "https://services.leadconnectorhq.com"
        
        # Determine which API version to try first
        if self.location_api_key:
            self.primary_auth_type = "location_api"
            self.primary_headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.location_api_key}",
                "Content-Type": "application/json",
                "Version": "2021-07-28"
            }
            logger.info("🔑 Using V1 Location API Key as primary authentication")
        else:
            self.primary_auth_type = "pit_token"
            self.primary_headers = {
                "Accept": "application/json",  # Ensure Accept header is present for V2 API
                "Authorization": f"Bearer {self.private_token}",
                "Content-Type": "application/json",
                "Version": "2021-07-28"
            }
            logger.info("🔑 Using V2 PIT Token as primary authentication")
        
        # Set up fallback headers if both keys are available
        if self.location_api_key and self.private_token:
            if self.primary_auth_type == "location_api":
                self.fallback_auth_type = "pit_token"
                self.fallback_headers = {
                    "Accept": "application/json",  # Ensure Accept header is present
                    "Authorization": f"Bearer {self.private_token}",
                    "Content-Type": "application/json",
                    "Version": "2021-07-28"
                }
            else:
                self.fallback_auth_type = "location_api"
                self.fallback_headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.location_api_key}",
                    "Content-Type": "application/json",
                    "Version": "2021-07-28"
                }
            logger.info(f"🔄 Fallback authentication available: {self.fallback_auth_type}")
        else:
            self.fallback_headers = None
            self.fallback_auth_type = None
        
        # Validate at least one auth method is available
        if not self.location_api_key and not self.private_token:
            raise ValueError("Either location_api_key or private_token must be provided")
        
        # Agency API headers for user management operations
        if agency_api_key:
            self.agency_headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {agency_api_key}",
                "Content-Type": "application/json",
                "Version": "2021-07-28"
            }
        else:
            self.agency_headers = None
    
    def _make_request_with_fallback(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make request with automatic fallback between API key types"""
        
        # Try primary authentication first
        try:
            logger.debug(f"🔑 Trying {self.primary_auth_type} for {method} {url}")
            kwargs['headers'] = self.primary_headers
            response = requests.request(method, url, **kwargs)
            
            # If successful (2xx status), return immediately
            if 200 <= response.status_code < 300:
                logger.debug(f"✅ {self.primary_auth_type} succeeded: {response.status_code}")
                return response
                
            # If authentication error and fallback available, try fallback
            if response.status_code in [401, 403] and self.fallback_headers:
                logger.warning(f"🔄 {self.primary_auth_type} failed ({response.status_code}), trying {self.fallback_auth_type}")
                
                kwargs['headers'] = self.fallback_headers
                fallback_response = requests.request(method, url, **kwargs)
                
                if 200 <= fallback_response.status_code < 300:
                    logger.info(f"✅ {self.fallback_auth_type} succeeded: {fallback_response.status_code}")
                    return fallback_response
                else:
                    logger.error(f"❌ Both auth methods failed. Primary: {response.status_code}, Fallback: {fallback_response.status_code}")
                    return fallback_response  # Return the fallback response for error handling
            else:
                # No fallback available or not an auth error
                logger.debug(f"❌ {self.primary_auth_type} failed: {response.status_code} (no fallback attempted)")
                return response
                
        except Exception as e:
            logger.error(f"❌ Request exception with {self.primary_auth_type}: {e}")
            
            # Try fallback if available
            if self.fallback_headers:
                try:
                    logger.warning(f"🔄 Trying {self.fallback_auth_type} after exception")
                    kwargs['headers'] = self.fallback_headers
                    return requests.request(method, url, **kwargs)
                except Exception as fallback_e:
                    logger.error(f"❌ Fallback also failed: {fallback_e}")
                    raise fallback_e
            else:
                raise e
    
    def search_contacts(self, query: str = "", limit: int = 100) -> List[Dict]:
        """Search contacts in GHL with fallback authentication"""
        try:
            # Ensure limit doesn't exceed 100
            limit = min(limit, 100)
            
            url = f"{self.base_url}/contacts/"
            params = {
                "locationId": self.location_id,
                "limit": limit
            }
            
            if query:
                params["query"] = query
            
            logger.debug(f"Searching contacts with params: {params}")
            
            response = self._make_request_with_fallback("GET", url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('contacts', [])
            else:
                logger.error(f"Failed to search contacts: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error searching contacts: {str(e)}")
            return []
    
    def get_contact_by_id(self, contact_id: str) -> Optional[Dict]:
        """Get contact details by ID with fallback authentication"""
        try:
            url = f"{self.base_url}/contacts/{contact_id}"
            response = self._make_request_with_fallback("GET", url)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('contact', {})
            else:
                logger.error(f"Failed to get contact: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting contact: {str(e)}")
            return None
    
    def create_contact(self, contact_data: Dict) -> Optional[Dict]:
        """Create a new contact in GHL with detailed error reporting and fallback authentication"""
        try:
            url = f"{self.base_url}/contacts/"
            
            # Prepare payload with locationId
            payload = {
                "locationId": self.location_id,
                **contact_data
            }
            
            # Ensure locationId is not overridden by contact_data
            payload["locationId"] = self.location_id
            
            # VERBOSE DEBUG LOGGING
            logger.info(f"🔍 GHL API CREATE CONTACT REQUEST:")
            logger.info(f"  📍 URL: {url}")
            logger.info(f"  🔑 Primary Auth: {self.primary_auth_type}")
            logger.info(f"  🏢 LocationId being used: {self.location_id}")
            logger.info(f"  📦 Payload Keys: {list(payload.keys())}")
            
            # Verify locationId is in payload
            if "locationId" in payload:
                logger.info(f"  ✅ LocationId is in payload: {payload['locationId']}")
            else:
                logger.error(f"  ❌ LocationId is MISSING from payload!")
            
            # Detailed custom fields debugging
            if 'customFields' in payload:
                custom_fields = payload['customFields']
                logger.info(f"  🏷️  CustomFields Type: {type(custom_fields)}")
                logger.info(f"  🏷️  CustomFields Length: {len(custom_fields) if isinstance(custom_fields, (list, dict)) else 'N/A'}")
                if isinstance(custom_fields, list):
                    logger.info(f"  ✅ CustomFields is ARRAY (correct format)")
                    for i, field in enumerate(custom_fields):
                        logger.info(f"    [{i}] ID: {field.get('id', 'missing')}, Value: {field.get('value', 'missing')}")
                else:
                    logger.error(f"  ❌ CustomFields is {type(custom_fields)} (should be array!)")
                    logger.error(f"  ❌ CustomFields content: {custom_fields}")
            else:
                logger.info(f"  📝 No customFields in payload")
                
            logger.info(f"  📋 Full Payload: {payload}")
            
            # Use fallback request system
            response = self._make_request_with_fallback("POST", url, json=payload)
            
            # VERBOSE RESPONSE LOGGING
            logger.info(f"🔍 GHL API CREATE CONTACT RESPONSE:")
            logger.info(f"  📈 Status Code: {response.status_code}")
            logger.info(f"  📄 Response Headers: {dict(response.headers)}")
            logger.info(f"  📝 Response Text: {response.text}")
            
            if response.status_code == 201:
                data = response.json()
                contact = data.get('contact', {})
                logger.info(f"  ✅ SUCCESS: Created contact ID: {contact.get('id')}")
                return contact
            else:
                # Return detailed error information instead of None
                error_details = {
                    "error": True,
                    "status_code": response.status_code,
                    "response_text": response.text,
                    "url": url,
                    "payload_keys": list(payload.keys()),
                    "locationId_in_payload": payload.get('locationId', 'MISSING!')
                }
                
                # Try to parse JSON error if possible
                try:
                    error_json = response.json()
                    error_details["error_json"] = error_json
                except:
                    pass
                
                logger.error(f"  ❌ FAILED to create contact: {response.status_code}")
                logger.error(f"  ❌ Error details: {error_details}")
                return error_details
                
        except Exception as e:
            error_details = {
                "error": True,
                "exception": str(e),
                "exception_type": e.__class__.__name__
            }
            logger.error(f"❌ Exception creating contact: {str(e)}")
            return error_details
    
    def update_contact(self, contact_id: str, update_data: Dict) -> bool:
        """Update contact in GHL with fallback authentication"""
        try:
            url = f"{self.base_url}/contacts/{contact_id}"
            
            # For updates, we don't include locationId in the body, just the data to update
            payload = update_data.copy()
            # Remove locationId if it exists in update_data
            payload.pop("locationId", None)
            payload.pop("id", None)
            
            logger.debug(f"Updating contact {contact_id} with payload: {payload}")
            
            response = self._make_request_with_fallback("PUT", url, json=payload)
            
            if response.status_code == 200:
                logger.debug(f"Successfully updated contact {contact_id}")
                return True
            else:
                logger.error(f"Failed to update contact: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error updating contact: {str(e)}")
            return False
    
    def create_opportunity(self, opportunity_data: Dict) -> Optional[Dict]:
        """Create opportunity in GHL with fallback authentication"""
        try:
            url = f"{self.base_url}/opportunities/"
            
            # Ensure locationId is in opportunity data
            payload = {
                "locationId": self.location_id,
                **opportunity_data
            }
            payload["locationId"] = self.location_id  # Ensure it's not overridden
            
            logger.debug(f"Creating GHL opportunity. URL: {url}, Payload: {payload}")

            # Use _make_request_with_fallback for robust API calls
            response = self._make_request_with_fallback("POST", url, json=payload)
            
            if response.status_code == 201:
                data = response.json()
                logger.info(f"Successfully created GHL opportunity: {data.get('opportunity', {}).get('id')}")
                return data.get('opportunity', {})
            else:
                error_text = response.text
                error_json_response = None
                try:
                    error_json_response = response.json()
                    logger.error(f"Failed to create GHL opportunity: {response.status_code} - {error_text} - JSON: {error_json_response}")
                except ValueError:
                    logger.error(f"Failed to create GHL opportunity: {response.status_code} - {error_text}")
                
                # Return a dictionary with error details, similar to create_contact
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "response_text": response.text,
                    "error_json": error_json_response,
                    "message": "Failed to create GHL opportunity"
                }
                
        except Exception as e:
            logger.exception(f"Exception creating GHL opportunity: {str(e)}")
            # Return a dictionary with error details on exception
            return {
                "error": True,
                "exception": str(e),
                "exception_type": e.__class__.__name__,
                "message": f"Exception occurred: {str(e)}"
            }
    
    def get_opportunities_by_contact(self, contact_id: str) -> List[Dict]:
        """Get opportunities for a specific contact"""
        try:
            url = f"{self.base_url}/opportunities"
            params = {
                "contactId": contact_id,
                "locationId": self.location_id
            }
            
            response = self._make_request_with_fallback("GET", url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                opportunities = data.get('opportunities', [])
                logger.info(f"Found {len(opportunities)} opportunities for contact {contact_id}")
                return opportunities
            else:
                logger.error(f"Failed to get opportunities for contact: {response.status_code}")
                return []
                
        except Exception as e:
            logger.exception(f"Exception getting opportunities for contact: {str(e)}")
            return []
    
    def update_opportunity(self, opportunity_id: str, update_data: Dict) -> bool:
        """Update opportunity in GHL with fallback authentication"""
        try:
            url = f"{self.base_url}/opportunities/{opportunity_id}"
            
            # For updates, we don't include locationId in the body, just the data to update
            payload = update_data.copy()
            # Remove locationId if it exists in update_data
            payload.pop("locationId", None)
            payload.pop("id", None)
            
            logger.info(f"🔄 Updating GHL opportunity {opportunity_id} with payload: {payload}")
            
            response = self._make_request_with_fallback("PUT", url, json=payload)
            
            if response.status_code == 200:
                logger.info(f"✅ Successfully updated opportunity {opportunity_id}")
                return True
            else:
                logger.error(f"❌ Failed to update opportunity: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Error updating opportunity: {str(e)}")
            return False
    
    def get_opportunity_by_id(self, opportunity_id: str) -> Optional[Dict]:
        """Get opportunity details by ID with fallback authentication"""
        try:
            url = f"{self.base_url}/opportunities/{opportunity_id}"
            response = self._make_request_with_fallback("GET", url)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('opportunity', {})
            else:
                logger.error(f"Failed to get opportunity: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting opportunity: {str(e)}")
            return None
    
    def get_pipelines(self) -> List[Dict]:
        """Get all pipelines for the location"""
        try:
            url = f"{self.base_url}/opportunities/pipelines"
            params = {"locationId": self.location_id}
            
            response = self._make_request_with_fallback("GET", url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('pipelines', [])
            else:
                logger.error(f"Failed to get pipelines: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error getting pipelines: {str(e)}")
            return []
    
    def get_custom_fields(self) -> List[Dict]:
        """Get custom fields for the location"""
        try:
            url = f"{self.base_url}/locations/{self.location_id}/customFields"
            
            response = self._make_request_with_fallback("GET", url)
            if response.status_code == 200:
                data = response.json()
                return data.get('customFields', [])
            else:
                logger.error(f"Failed to get custom fields: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error getting custom fields: {str(e)}")
            return []
    
    def send_sms(self, contact_id: str, message: str) -> bool:
        """Send SMS to contact"""
        try:
            url = f"{self.base_url}/conversations/messages"
            payload = {
                "type": "SMS",
                "contactId": contact_id,
                "message": message,
                "locationId": self.location_id
            }
            
            response = self._make_request_with_fallback("POST", url, json=payload)
            if response.status_code == 201:
                return True
            else:
                logger.error(f"Failed to send SMS: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return False
    
    def send_email(self, contact_id: str, subject: str, html_body: str) -> bool:
        """Send email to contact"""
        try:
            url = f"{self.base_url}/conversations/messages"
            payload = {
                "type": "Email",
                "contactId": contact_id,
                "subject": subject,
                "html": html_body,
                "locationId": self.location_id
            }
            
            response = self._make_request_with_fallback("POST", url, json=payload)
            if response.status_code == 201:
                return True
            else:
                logger.error(f"Failed to send email: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def create_user_v2(self, user_data: Dict) -> Optional[Dict]:
        """Create a new user in GHL using V2 OAuth API with CLEAN, minimal payload"""
        try:
            if not self.private_token:
                logger.error("❌ V2 API FAIL: Private token required for V2 user creation")
                return {
                    "error": True,
                    "message": "Private token required for V2 user creation",
                    "api_version": "V2"
                }
            
            if not self.company_id:
                logger.error("❌ V2 API FAIL: Company ID required for V2 user creation")
                return {
                    "error": True,
                    "message": "Company ID required for V2 user creation",
                    "api_version": "V2"
                }
            
            # V2 API endpoint for user creation
            url = f"{self.base_url}/users/"
            
            # V2 API headers with Private Token - EXACT MATCH TO OFFICIAL DOCS
            v2_headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.private_token}",
                "Content-Type": "application/json",
                "Version": "2021-07-28"
            }
            
            # Generate a secure password if not provided
            password = user_data.get("password", "TempPass123!")
            
                        # MINIMAL V2 scopes for vendors (restrictive)
            vendor_scopes = [
                "contacts.write",              # Assigned contacts only
                "conversations.write",         # Messages to assigned contacts only
                "opportunities.write"          # Manage assigned opportunities
            ]

            # Assigned-only enforcement - vendors see ONLY their assigned data
            vendor_assigned_scopes = [
                "contacts.write",              # ONLY assigned contacts
                "conversations.write",         # ONLY assigned conversations  
                "opportunities.write"          # ONLY assigned opportunities
            ]
            
            # 🔥 V2 PAYLOAD - OFFICIAL TEMPLATE WITH RESTRICTIVE VENDOR PERMISSIONS
            payload = {
                "companyId": self.company_id,
                "firstName": user_data.get("firstName", ""),
                "lastName": user_data.get("lastName", ""),
                "email": user_data.get("email", ""),
                "password": password,
                "phone": user_data.get("phone", ""),
                "type": "account",
                "role": "user",  # User role instead of admin for vendors
                "locationIds": [self.location_id],
                "sendInvite": False,  # DISABLED: Don't auto-send invite to avoid agency branding during onboarding
                "permissions": {
                    # VENDOR ESSENTIALS - ENABLED
                    "contactsEnabled": True,           # View/manage assigned contacts
                    "conversationsEnabled": True,      # Send messages to assigned contacts
                    "opportunitiesEnabled": True,      # Manage assigned opportunities
                    "appointmentsEnabled": True,       # Schedule appointments
                    "dashboardStatsEnabled": True,     # Basic dashboard access
                    "assignedDataOnly": True,          # CRITICAL: Only see assigned data
                    
                    # EVERYTHING ELSE - DISABLED FOR SECURITY
                    "campaignsEnabled": False,
                    "campaignsReadOnly": False,
                    "workflowsEnabled": False,
                    "workflowsReadOnly": False,
                    "triggersEnabled": False,
                    "funnelsEnabled": False,
                    "websitesEnabled": False,
                    "bulkRequestsEnabled": False,
                    "reviewsEnabled": False,
                    "onlineListingsEnabled": False,
                    "phoneCallEnabled": False,         # Disable calls for security
                    "adwordsReportingEnabled": False,
                    "membershipEnabled": False,
                    "facebookAdsReportingEnabled": False,
                    "attributionsReportingEnabled": False,
                    "settingsEnabled": False,          # CRITICAL: No account settings
                    "tagsEnabled": False,
                    "leadValueEnabled": False,
                    "marketingEnabled": False,         # CRITICAL: No marketing tools
                    "agentReportingEnabled": False,
                    "botService": False,
                    "socialPlanner": False,            # CRITICAL: No social media
                    "bloggingEnabled": False,
                    "invoiceEnabled": False,
                    "affiliateManagerEnabled": False,
                    "contentAiEnabled": False,
                    "refundsEnabled": False,
                    "recordPaymentEnabled": False,
                    "cancelSubscriptionEnabled": False,
                    "paymentsEnabled": False,
                    "communitiesEnabled": False,
                    "exportPaymentsEnabled": False
                },
                "scopes": vendor_scopes,
                "scopesAssignedToOnly": vendor_assigned_scopes
            }
            
            # 🔍 ULTRA-DETAILED V2 API REQUEST DEBUGGING
            logger.error("=" * 80)
            logger.error("🔥 V2 API REQUEST DEBUG - FULL DETAILS")
            logger.error("=" * 80)
            logger.error(f"📍 V2 URL: {url}")
            logger.error(f"🔑 V2 Headers: {v2_headers}")
            logger.error(f"📦 V2 Payload (CLEAN - NO V1 PERMISSIONS):")
            logger.error(f"   companyId: '{payload['companyId']}'")
            logger.error(f"   firstName: '{payload['firstName']}'")
            logger.error(f"   lastName: '{payload['lastName']}'")
            logger.error(f"   email: '{payload['email']}'")
            logger.error(f"   phone: '{payload['phone']}'")
            logger.error(f"   password: '{payload['password'][:3]}***'")
            logger.error(f"   type: '{payload['type']}'")
            logger.error(f"   role: '{payload['role']}'")
            logger.error(f"   locationIds: {payload['locationIds']}")
            logger.error(f"   scopes: {payload['scopes']}")
            logger.error(f"   scopesAssignedToOnly: {payload['scopesAssignedToOnly']}")
            logger.error(f"📋 FULL JSON PAYLOAD:")
            
            import json
            logger.error(json.dumps(payload, indent=2))
            logger.error("=" * 80)
            
            # Make V2 API request
            logger.info("🚀 SENDING V2 API REQUEST...")
            response = requests.post(url, headers=v2_headers, json=payload, timeout=30)
            
            # 🔍 ULTRA-DETAILED V2 API RESPONSE DEBUGGING
            logger.error("=" * 80)
            logger.error("📥 V2 API RESPONSE DEBUG - FULL DETAILS")
            logger.error("=" * 80)
            logger.error(f"📈 Status Code: {response.status_code}")
            logger.error(f"📄 Response Headers: {dict(response.headers)}")
            logger.error(f"📝 Response Body (RAW): {response.text}")
            logger.error(f"⏱️  Response Time: {response.elapsed.total_seconds():.2f}s")
            
            # Try to parse JSON response
            try:
                response_json = response.json()
                logger.error(f"📋 Response JSON (PARSED):")
                logger.error(json.dumps(response_json, indent=2))
            except Exception as json_err:
                logger.error(f"❌ Could not parse response as JSON: {json_err}")
            
            logger.error("=" * 80)
            
            # Handle V2 API response
            if response.status_code == 201:
                data = response.json()
                user_id = data.get('id')
                logger.info(f"✅ V2 API SUCCESS! Created user: {user_id}")
                logger.info(f"🔒 Applied restrictive scopes: {vendor_scopes}")
                return data
            elif response.status_code == 200:
                # Some APIs return 200 instead of 201
                data = response.json()
                user_id = data.get('id')
                logger.info(f"✅ V2 API SUCCESS! (200 response) Created user: {user_id}")
                return data
            else:
                logger.error(f"❌ V2 API FAILED: {response.status_code}")
                logger.error(f"❌ V2 Error Response: {response.text}")
                
                # Parse detailed error if possible
                try:
                    error_data = response.json()
                    logger.error(f"❌ V2 Parsed Error: {json.dumps(error_data, indent=2)}")
                    
                    # Log specific error details
                    if 'message' in error_data:
                        logger.error(f"❌ V2 Error Message: {error_data['message']}")
                    if 'errors' in error_data:
                        logger.error(f"❌ V2 Error Details: {error_data['errors']}")
                        
                except Exception as parse_err:
                    logger.error(f"❌ Could not parse V2 error response: {parse_err}")
                
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "response_text": response.text,
                    "api_version": "V2",
                    "url": url,
                    "clean_payload": True
                }
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ V2 API TIMEOUT after 30 seconds")
            return {
                "error": True,
                "message": "V2 API request timeout",
                "api_version": "V2"
            }
        except Exception as e:
            logger.error(f"❌ V2 API EXCEPTION: {str(e)}")
            import traceback
            logger.error(f"❌ V2 Exception Traceback: {traceback.format_exc()}")
            return {
                "error": True,
                "exception": str(e),
                "exception_type": e.__class__.__name__,
                "api_version": "V2"
            }

    def create_user_v1(self, user_data: Dict) -> Optional[Dict]:
        """Create a new user in GHL using V1 API endpoint with Agency API key (FALLBACK)"""
        try:
            if not self.agency_api_key:
                logger.error("Agency API key required for user creation")
                return None
            
            # CORRECTED: Use V1 API endpoint for user creation
            v1_base_url = "https://rest.gohighlevel.com"
            url = f"{v1_base_url}/v1/users/"
            
            # CORRECTED: V1 API headers with Agency API key
            v1_headers = {
                "Authorization": f"Bearer {self.agency_api_key}",
                "Content-Type": "application/json"
            }
            
            # CORRECTED: V1 API payload structure with locationIds array  
            # Generate a secure password if not provided
            password = user_data.get("password", "TempPass123!")
            
            payload = {
                "firstName": user_data.get("firstName", ""),
                "lastName": user_data.get("lastName", ""),
                "email": user_data.get("email", ""),
                "phone": user_data.get("phone", ""),  # FIXED: Add phone number to payload
                "password": password,
                "type": user_data.get("type", "account"),  # V1 API: account, agency
                "role": user_data.get("role", "user"),     # V1 API: admin, user
                "locationIds": [self.location_id],         # CORRECTED: Must be array with location ID
                "sendInvite": False,  # DISABLED: Don't auto-send invite to avoid agency branding during onboarding
                "permissions": user_data.get("permissions", {
                    "campaignsEnabled": False,
                    "campaignsReadOnly": True,
                    "contactsEnabled": True,
                    "workflowsEnabled": False,
                    "triggersEnabled": False,
                    "funnelsEnabled": False,
                    "websitesEnabled": False,
                    "opportunitiesEnabled": True,
                    "dashboardStatsEnabled": True,
                    "bulkRequestsEnabled": False,
                    "appointmentEnabled": True,
                    "reviewsEnabled": False,
                    "onlineListingsEnabled": False,
                    "phoneCallEnabled": True,
                    "conversationsEnabled": True,
                    "assignedDataOnly": True,  # Only see their assigned leads
                    "adwordsReportingEnabled": False,
                    "membershipEnabled": False,
                    "facebookAdsReportingEnabled": False,
                    "attributionsReportingEnabled": False,
                    "settingsEnabled": False,
                    "tagsEnabled": False,
                    "leadValueEnabled": True,
                    "marketingEnabled": False,
                    "agentReportingEnabled": True,
                    "botService": False,
                    "socialPlanner": False,
                    "bloggingEnabled": False,
                    "invoiceEnabled": False,
                    "affiliateManagerEnabled": False,
                    "contentAiEnabled": False,
                    "refundsEnabled": False,
                    "recordPaymentEnabled": False,
                    "cancelSubscriptionEnabled": False,
                    "paymentsEnabled": False,
                    "communitiesEnabled": False,
                    "exportPaymentsEnabled": False
                })
            }
            
            # VERBOSE LOGGING for V1 API request
            logger.info(f"🔐 Creating GHL user with V1 API. URL: {url}")
            logger.info(f"📋 V1 User payload DETAILED:")
            logger.info(f"  firstName: '{payload.get('firstName', 'MISSING')}'")
            logger.info(f"  lastName: '{payload.get('lastName', 'MISSING')}'")
            logger.info(f"  email: '{payload.get('email', 'MISSING')}'")
            logger.info(f"  phone: '{payload.get('phone', 'MISSING')}'")  # FIXED: Log phone number
            logger.info(f"  password: '{payload.get('password', 'MISSING')[:3]}***' (showing first 3 chars)")
            logger.info(f"  type: '{payload.get('type', 'MISSING')}'")
            logger.info(f"  role: '{payload.get('role', 'MISSING')}'")
            logger.info(f"  locationIds: {payload.get('locationIds', 'MISSING')}")
            logger.info(f"  permissions keys: {list(payload.get('permissions', {}).keys())}")
            logger.info(f"🔑 V1 Headers: Authorization: Bearer {self.agency_api_key[:10]}...{self.agency_api_key[-4:]}")
            logger.info(f"📋 Full V1 Payload: {payload}")
            
            # CORRECTED: Use V1 API endpoint and headers
            response = requests.post(url, headers=v1_headers, json=payload)
            
            logger.info(f"📈 V1 User Creation Response: Status={response.status_code}")
            logger.info(f"📄 V1 Response Headers: {dict(response.headers)}")
            logger.info(f"📄 V1 Response Text: {response.text}")
            
            # FIXED: Accept both 200 and 201 status codes
            if response.status_code in [200, 201]:
                data = response.json()
                user = data.get('user', data)  # Handle different response structures
                user_id = user.get('id') if isinstance(user, dict) else None
                logger.info(f"✅ Successfully created GHL user with V1 API: {user_id}")
                return user
            else:
                logger.error(f"❌ Failed to create user with V1 API: {response.status_code} - {response.text}")
                
                # Try to parse error response
                try:
                    error_data = response.json()
                    logger.error(f"📋 V1 API Error Details: {error_data}")
                except:
                    pass
                
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "response_text": response.text,
                    "api_version": "V1",
                    "url": url
                }
        except Exception as e:
            logger.error(f"❌ Exception creating user with V1 API: {str(e)}")
            return {
                "error": True,
                "exception": str(e),
                "exception_type": e.__class__.__name__,
                "api_version": "V1"
            }

    def create_user(self, user_data: Dict) -> Optional[Dict]:
        """
        Create a new user in GHL with V2 API (preferred) and V1 API fallback
        V2 provides granular scope control for better vendor permission management
        """
        logger.info(f"🚀 Starting user creation with V2 → V1 fallback strategy for {user_data.get('email', 'unknown')}")
        
        # Try V2 API first (preferred for scope control)
        if self.private_token and self.company_id:
            logger.info(f"🎯 Attempting V2 API user creation (preferred method)")
            v2_result = self.create_user_v2(user_data)
            
            # Check if V2 was successful
            if v2_result and not v2_result.get("error"):
                logger.info(f"✅ V2 API user creation successful - vendor will have limited scope permissions")
                return v2_result
            else:
                logger.warning(f"⚠️ V2 API user creation failed: {v2_result.get('response_text', 'Unknown error')}")
                logger.info(f"🔄 Falling back to V1 API...")
        else:
            missing_reqs = []
            if not self.private_token:
                missing_reqs.append("private_token")
            if not self.company_id:
                missing_reqs.append("company_id")
            logger.info(f"⚠️ V2 API requirements missing: {missing_reqs}. Skipping to V1 API fallback.")
        
        # Fallback to V1 API
        if self.agency_api_key:
            logger.info(f"🔄 Attempting V1 API user creation (fallback method)")
            v1_result = self.create_user_v1(user_data)
            
            # Check if V1 was successful
            if v1_result and not v1_result.get("error"):
                logger.info(f"✅ V1 API user creation successful - user will have broader permissions (manual adjustment may be needed)")
                return v1_result
            else:
                logger.error(f"❌ V1 API user creation also failed: {v1_result.get('response_text', 'Unknown error') if v1_result else 'No response'}")
        else:
            logger.error(f"❌ No agency API key available for V1 fallback")
        
        # Both methods failed
        logger.error(f"❌ Both V2 and V1 user creation methods failed")
        return {
            "error": True,
            "message": "Both V2 and V1 user creation methods failed",
            "v2_available": bool(self.private_token and self.company_id),
            "v1_available": bool(self.agency_api_key),
            "recommendation": "Check API keys and company_id configuration"
        }
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email address using V1 API (matches create_user endpoint)"""
        try:
            # CORRECTED: Use V1 API base URL and endpoint for user lookup
            v1_base_url = "https://rest.gohighlevel.com"
            url = f"{v1_base_url}/v1/users"
            
            # Use Agency API key for V1 user operations
            if not self.agency_api_key:
                logger.warning("No agency API key available for V1 user lookup")
                return None
                
            v1_headers = {
                "Authorization": f"Bearer {self.agency_api_key}",
                "Content-Type": "application/json"
            }
            
            # V1 API might require different query parameters
            params = {"email": email}
            
            logger.info(f"🔍 V1 User lookup: {url} with email={email}")
            response = requests.get(url, headers=v1_headers, params=params)
            
            logger.info(f"📈 V1 User lookup response: Status={response.status_code}")
            logger.debug(f"📄 V1 User lookup response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                users = data.get('users', [])
                for user in users:
                    if user.get('email', '').lower() == email.lower():
                        logger.info(f"✅ Found existing V1 user: {user.get('id')}")
                        return user
                logger.info(f"📋 No user found with email {email} in V1 API response")
                return None
            elif response.status_code == 404:
                logger.info(f"📋 V1 User lookup: No users found (404) - this is normal for new vendors")
                return None
            else:
                logger.error(f"❌ Failed to get users from V1 API: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ Error getting user by email from V1 API: {str(e)}")
            return None
    
    def get_opportunities(self, pipeline_id: str = None, stage_id: str = None, limit: int = 100) -> List[Dict]:
        """Get opportunities with optional pipeline and stage filtering"""
        try:
            url = f"{self.base_url}/opportunities/search"
            params = {
                "locationId": self.location_id,
                "limit": min(limit, 100)
            }
            
            if pipeline_id:
                params["pipelineId"] = pipeline_id
            if stage_id:
                params["pipelineStageId"] = stage_id
                
            response = self._make_request_with_fallback("GET", url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('opportunities', [])
            else:
                logger.error(f"Failed to get opportunities: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error getting opportunities: {str(e)}")
            return []


    def update_user(self, user_id: str, update_data: Dict) -> bool:
        """Update user in GHL"""
        try:
            url = f"{self.base_url}/locations/{self.location_id}/users/{user_id}"
            
            response = self._make_request_with_fallback("PUT", url, json=update_data)
            if response.status_code == 200:
                logger.info(f"Successfully updated user {user_id}")
                return True
            else:
                logger.error(f"Failed to update user: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            return False
    
    def delete_user(self, user_id: str) -> bool:
        """Delete user from GHL location"""
        try:
            url = f"{self.base_url}/locations/{self.location_id}/users/{user_id}"
            
            response = self._make_request_with_fallback("DELETE", url)
            if response.status_code == 200:
                logger.info(f"Successfully deleted user {user_id}")
                return True
            else:
                logger.error(f"Failed to delete user: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            return False
    
    def test_location_access(self) -> Dict:
        """Test if the token can access the location"""
        try:
            url = f"{self.base_url}/contacts/"
            params = {
                "locationId": self.location_id,
                "limit": 1
            }
            
            response = self._make_request_with_fallback("GET", url, params=params)
            
            return {
                "status_code": response.status_code,
                "can_access": response.status_code == 200,
                "response_text": response.text,
                "location_id": self.location_id,
                "headers_used": self.primary_headers
            }
        except Exception as e:
            return {
                "status_code": None,
                "can_access": False,
                "error": str(e),
                "location_id": self.location_id,
                "headers_used": self.primary_headers
            }
