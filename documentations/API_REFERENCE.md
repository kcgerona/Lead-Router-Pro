# Lead Router Pro - API Reference

## Base URL
```
Development: http://localhost:8000
Production: https://api.yourdomain.com
```

## Authentication

Most API endpoints require JWT authentication. Obtain a token via the login endpoint and include it in the Authorization header:

```
Authorization: Bearer YOUR_JWT_TOKEN
```

---

## Endpoints Overview

### Public Endpoints (No Auth Required)
- `POST /api/v1/webhooks/elementor/{form_identifier}` - Process form submissions
- `GET /health` - System health check
- `GET /api/v1/webhooks/health` - Webhook system health

### Authentication Endpoints
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/verify-2fa` - Verify 2FA code
- `POST /api/v1/auth/refresh` - Refresh JWT token
- `POST /api/v1/auth/logout` - Logout user

### Admin Endpoints (Auth Required)
- `GET /api/v1/admin/health` - Detailed system health
- `GET /api/v1/admin/stats` - System statistics
- `POST /api/v1/admin/field-reference/generate` - Generate GHL field reference
- `POST /api/v1/admin/fields/create-from-csv` - Create custom fields from CSV
- `GET /api/v1/admin/vendors` - List all vendors
- `POST /api/v1/admin/vendors/{vendor_id}/approve` - Approve vendor

### Vendor Management Endpoints
- `GET /api/v1/routing/vendors` - List active vendors
- `GET /api/v1/routing/vendors/{vendor_id}` - Get vendor details
- `POST /api/v1/routing/vendors/{vendor_id}/coverage` - Update vendor coverage
- `POST /api/v1/routing/match` - Find matching vendors for lead
- `GET /api/v1/routing/services` - Get available services
- `GET /api/v1/routing/services/level3/{category}/{subcategory}` - Get Level 3 services

### Security Endpoints
- `GET /api/v1/security/whitelist` - Get IP whitelist
- `POST /api/v1/security/whitelist/add` - Add IP to whitelist
- `DELETE /api/v1/security/whitelist/remove` - Remove IP from whitelist

---

## Detailed Endpoint Documentation

### 1. Process Form Submission

**Endpoint:** `POST /api/v1/webhooks/elementor/{form_identifier}`

**Description:** Processes form submissions from WordPress/Elementor forms, creates/updates GHL contacts, and routes leads to vendors.

**Headers:**
```
Content-Type: application/json
X-Webhook-API-Key: your_webhook_api_key
```

**Request Body:**
```json
{
  "firstName": "John",
  "lastName": "Doe",
  "email": "john.doe@example.com",
  "phone": "(555) 123-4567",
  "service_requested": "Boat Detailing",
  "zip_code": "33139",
  "special_requests": "Need service ASAP",
  "vendor_company_name": "Marine Services Inc",  // For vendor applications
  "primary_service_category": "Boat Maintenance",  // For vendor applications
  "primary_services": ["Boat Detailing", "Bottom Cleaning"],  // Level 2
  "primary_level3_services": {  // Level 3 services
    "Boat Detailing": ["Ceramic Coating", "Wax and Polish"]
  }
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Form processed successfully",
  "contact_id": "ghl_contact_123",
  "lead_id": "lead_456",
  "vendor_assigned": "vendor_789",
  "processing_time": 1.234
}
```

---

### 2. User Login

**Endpoint:** `POST /api/v1/auth/login`

**Request Body:**
```json
{
  "email": "admin@example.com",
  "password": "secure_password"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "2FA code sent to email",
  "temp_token": "temporary_token_for_2fa",
  "expires_in": 300
}
```

---

### 3. Verify 2FA

**Endpoint:** `POST /api/v1/auth/verify-2fa`

**Request Body:**
```json
{
  "temp_token": "temporary_token_from_login",
  "code": "123456"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "user_123",
    "email": "admin@example.com",
    "role": "admin",
    "name": "Admin User"
  }
}
```

---

### 4. Find Matching Vendors

**Endpoint:** `POST /api/v1/routing/match`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "service_category": "Boat Maintenance",
  "specific_service": "Boat Detailing",
  "zip_code": "33139",
  "priority": "normal"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "matches": [
    {
      "vendor_id": "vendor_123",
      "name": "Premium Marine Services",
      "company_name": "Premium Marine Services LLC",
      "services_offered": ["Boat Detailing", "Ceramic Coating"],
      "coverage_type": "county",
      "coverage_areas": ["Miami-Dade County, FL"],
      "match_score": 0.95,
      "distance": 5.2
    }
  ],
  "total_matches": 1
}
```

---

### 5. System Health Check

**Endpoint:** `GET /api/v1/admin/health`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-01T10:00:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "response_time": 0.023,
      "connections": 5
    },
    "ghl_api": {
      "status": "healthy",
      "response_time": 0.234,
      "last_sync": "2024-12-01T09:55:00Z"
    },
    "email_service": {
      "status": "healthy",
      "provider": "gmail",
      "last_sent": "2024-12-01T09:45:00Z"
    },
    "webhook_processor": {
      "status": "healthy",
      "queue_size": 0,
      "processing_rate": 50
    }
  },
  "metrics": {
    "leads_processed_today": 145,
    "active_vendors": 23,
    "average_processing_time": 1.234,
    "error_rate": 0.02
  }
}
```

---

### 6. Generate Field Reference

**Endpoint:** `POST /api/v1/admin/field-reference/generate`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
```

**Request Body:**
```json
{
  "force_refresh": true
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Field reference generated successfully",
  "fields_created": 12,
  "fields_updated": 3,
  "total_fields": 45,
  "reference_file": "field_reference.json"
}
```

---

### 7. Get Level 3 Services

**Endpoint:** `GET /api/v1/routing/services/level3/{category}/{subcategory}`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
```

**Example:** `GET /api/v1/routing/services/level3/Charters%20and%20Tours/Fishing%20Charters`

**Response (200 OK):**
```json
{
  "category": "Charters and Tours",
  "subcategory": "Fishing Charters",
  "level3_services": [
    "Inshore Fishing Charter",
    "Offshore (Deep Sea) Fishing Charter",
    "Reef & Wreck Fishing Charter",
    "Drift Boat Charter",
    "Freshwater Fishing Charter",
    "Private Party Boat Charter"
  ]
}
```

---

### 8. Approve Vendor

**Endpoint:** `POST /api/v1/admin/vendors/{vendor_id}/approve`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
```

**Request Body:**
```json
{
  "create_ghl_user": true,
  "send_welcome_email": true
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Vendor approved successfully",
  "vendor_id": "vendor_123",
  "ghl_user_id": "ghl_user_456",
  "email_sent": true
}
```

---

## Webhook Security

### Required Header

All webhook endpoints require the `X-Webhook-API-Key` header:

```
X-Webhook-API-Key: your_webhook_api_key
```

### IP Whitelisting

Webhooks can be restricted to specific IP addresses. Configure in the admin dashboard or via API.

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid request",
  "message": "Missing required field: email",
  "field": "email"
}
```

### 401 Unauthorized
```json
{
  "error": "Unauthorized",
  "message": "Invalid or expired token"
}
```

### 403 Forbidden
```json
{
  "error": "Forbidden",
  "message": "Insufficient permissions for this operation"
}
```

### 404 Not Found
```json
{
  "error": "Not found",
  "message": "Vendor not found",
  "resource": "vendor",
  "id": "vendor_123"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "message": "An unexpected error occurred",
  "request_id": "req_abc123"
}
```

---

## Rate Limiting

API endpoints are rate limited to prevent abuse:

- **Webhook endpoints**: 100 requests per minute
- **Auth endpoints**: 10 requests per minute
- **Admin endpoints**: 60 requests per minute
- **Public endpoints**: 30 requests per minute

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1701432000
```

---

## Pagination

List endpoints support pagination:

**Query Parameters:**
- `page` - Page number (default: 1)
- `limit` - Items per page (default: 20, max: 100)
- `sort` - Sort field (e.g., "created_at")
- `order` - Sort order ("asc" or "desc")

**Example:**
```
GET /api/v1/admin/vendors?page=2&limit=10&sort=created_at&order=desc
```

**Paginated Response:**
```json
{
  "data": [...],
  "pagination": {
    "page": 2,
    "limit": 10,
    "total": 45,
    "pages": 5,
    "has_next": true,
    "has_prev": true
  }
}
```

---

## WebSocket Events (Coming Soon)

Real-time updates via WebSocket:

```javascript
const ws = new WebSocket('wss://api.yourdomain.com/ws');

ws.on('lead.created', (data) => {
  console.log('New lead:', data);
});

ws.on('vendor.assigned', (data) => {
  console.log('Vendor assigned:', data);
});
```

---

## SDK Examples

### JavaScript/Node.js
```javascript
const LeadRouterClient = require('leadrouter-sdk');

const client = new LeadRouterClient({
  baseUrl: 'https://api.yourdomain.com',
  apiKey: 'your_api_key'
});

// Process form
const result = await client.webhooks.processForm('contact-form', {
  firstName: 'John',
  lastName: 'Doe',
  email: 'john@example.com',
  service_requested: 'Boat Detailing',
  zip_code: '33139'
});
```

### Python
```python
from leadrouter import LeadRouterClient

client = LeadRouterClient(
    base_url='https://api.yourdomain.com',
    api_key='your_api_key'
)

# Find matching vendors
matches = client.routing.find_vendors(
    service_category='Boat Maintenance',
    specific_service='Boat Detailing',
    zip_code='33139'
)
```

---

## Testing

Use the Swagger UI for interactive testing:
```
http://localhost:8000/docs
```

Or use curl:
```bash
curl -X POST http://localhost:8000/api/v1/webhooks/elementor/test \
  -H "Content-Type: application/json" \
  -H "X-Webhook-API-Key: test_key" \
  -d '{"firstName": "Test", "email": "test@example.com"}'
```

---

## Support

- **API Status**: https://status.leadrouterpro.com
- **Documentation**: https://docs.leadrouterpro.com
- **Support Email**: api-support@leadrouterpro.com

---

**Version**: 2.0.0 | **Last Updated**: December 2024