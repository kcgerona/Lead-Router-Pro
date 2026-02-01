# Vendor Submission Guide - DocksidePros Lead Router

## Overview

This guide provides the complete JSON format for vendor submissions and explains how the Lead Router processes vendor data beyond just sending it to GoHighLevel.

## Sample Vendor Submission (JSON Format)

```json
{
  "firstName": "Michael",
  "lastName": "Rodriguez",
  "email": "mike@marineprosolutions.com",
  "phone": "+1-305-555-0123",
  "vendor_company_name": "Marine Pro Solutions LLC",
  "companyName": "Marine Pro Solutions LLC",
  "address1": "1234 Marina Boulevard",
  "city": "Miami",
  "state": "FL",
  "postal_code": "33139",
  "website": "https://marineprosolutions.com",
  "services_provided": "Boat Maintenance, Marine Systems, Engine Service",
  "service_zip_codes": "33139,33140,33141,33154,33155,33156",
  "years_in_business": "8",
  "preferred_contact_method": "Phone",
  "vessel_types_serviced": "Sailboats, Motor Yachts, Sport Fishing Boats",
  "certifications_licenses": "ABYC Certified, Florida Marine Contractor License #MC12345",
  "insurance_coverage": "General Liability: $2M, Professional Liability: $1M",
  "availability_schedule": "Monday-Friday 8AM-6PM, Saturday 9AM-3PM",
  "emergency_services": "Yes",
  "service_radius_miles": "25",
  "crew_size": "4",
  "special_equipment": "Mobile crane, underwater welding equipment",
  "pricing_structure": "Hourly rates, Project-based quotes available",
  "payment_terms": "Net 30, Credit cards accepted",
  "references": "Harbor Marina (305-555-0100), Sunset Yacht Club (305-555-0200)",
  "special_requests__notes": "Specializing in luxury yacht maintenance and emergency repairs. Available 24/7 for emergency calls.",
  "source": "Vendor Application Form (DSP)",
  "tags": ["New Vendor Application", "Boat Maintenance", "Marine Systems"]
}
```

## What the Lead Router Does with Vendor Data

### 1. 🔄 Data Processing & Validation

**Field Mapping & Normalization:**
- Maps form field names to GHL custom field IDs using `field_mapper` service
- Normalizes phone numbers, email addresses, and ZIP codes
- Validates required fields (email, firstName, lastName, vendor_company_name)
- Converts service areas into searchable format

**Data Enrichment:**
- Adds source tracking ("Vendor Application Form (DSP)")
- Applies appropriate tags for categorization
- Timestamps all submissions for audit trails

### 2. 📊 GoHighLevel Integration

**Contact Creation:**
```json
{
  "locationId": "ilmrtA1Vk6rvcy4BswKg",
  "firstName": "Michael",
  "lastName": "Rodriguez",
  "email": "mike@marineprosolutions.com",
  "phone": "+1-305-555-0123",
  "companyName": "Marine Pro Solutions LLC",
  "address1": "1234 Marina Boulevard",
  "city": "Miami",
  "state": "FL",
  "postal_code": "33139",
  "website": "https://marineprosolutions.com",
  "tags": ["New Vendor Application", "Boat Maintenance", "Marine Systems"],
  "source": "Vendor Application Form (DSP)",
  "customFields": [
    {
      "id": "vendor_company_name_field_id",
      "value": "Marine Pro Solutions LLC"
    },
    {
      "id": "services_provided_field_id", 
      "value": "Boat Maintenance, Marine Systems, Engine Service"
    },
    {
      "id": "service_zip_codes_field_id",
      "value": "33139,33140,33141,33154,33155,33156"
    },
    {
      "id": "years_in_business_field_id",
      "value": "8"
    },
    {
      "id": "certifications_licenses_field_id",
      "value": "ABYC Certified, Florida Marine Contractor License #MC12345"
    },
    {
      "id": "insurance_coverage_field_id",
      "value": "General Liability: $2M, Professional Liability: $1M"
    },
    {
      "id": "emergency_services_field_id",
      "value": "Yes"
    },
    {
      "id": "service_radius_miles_field_id",
      "value": "25"
    },
    {
      "id": "special_equipment_field_id",
      "value": "Mobile crane, underwater welding equipment"
    },
    {
      "id": "special_requests__notes_field_id",
      "value": "Specializing in luxury yacht maintenance and emergency repairs. Available 24/7 for emergency calls."
    }
  ]
}
```

### 3. 🗄️ Internal Database Storage

**Vendor Record Creation:**
```sql
INSERT INTO vendors (
  account_id,
  name,
  email,
  phone,
  company_name,
  services_offered,
  service_areas,
  ghl_contact_id,
  status,
  performance_score,
  created_at
) VALUES (
  'account_uuid',
  'Michael Rodriguez',
  'mike@marineprosolutions.com',
  '+1-305-555-0123',
  'Marine Pro Solutions LLC',
  '["Boat Maintenance", "Marine Systems", "Engine Service"]',
  '["33139", "33140", "33141", "33154", "33155", "33156"]',
  'ghl_contact_id_from_api',
  'pending_approval',
  0.0,
  '2025-01-15 10:30:00'
);
```

**Service Category Mapping:**
- Parses `services_provided` field
- Maps to standardized service categories:
  - "Boat Maintenance" → `boat_maintenance`
  - "Marine Systems" → `marine_systems` 
  - "Engine Service" → `engines_generators`

**Geographic Indexing:**
- Extracts ZIP codes from `service_zip_codes`
- Creates searchable geographic coverage areas
- Enables location-based vendor matching for leads

### 4. 🎯 Lead Routing Integration

**Vendor Pool Management:**
```python
# When a lead comes in for "Boat Maintenance" in ZIP 33139:
matching_vendors = lead_routing_service.find_matching_vendors(
    account_id=account_id,
    service_category="Boat Maintenance",
    zip_code="33139",
    priority="normal"
)
# Returns: [Marine Pro Solutions LLC, other matching vendors]
```

**Performance Tracking:**
- Tracks response times to leads
- Monitors customer satisfaction ratings
- Adjusts vendor priority based on performance
- Implements round-robin and performance-based routing

### 5. 🔐 User Account Creation (When Approved)

**GHL User Creation via V1 API:**
```json
{
  "firstName": "Michael",
  "lastName": "Rodriguez", 
  "email": "mike@marineprosolutions.com",
  "password": "TempPass123!",
  "type": "account",
  "role": "user",
  "locationIds": ["ilmrtA1Vk6rvcy4BswKg"],
  "permissions": {
    "contactsEnabled": true,
    "opportunitiesEnabled": true,
    "conversationsEnabled": true,
    "assignedDataOnly": true,
    "phoneCallEnabled": true,
    "appointmentEnabled": true,
    "dashboardStatsEnabled": true,
    "campaignsEnabled": false,
    "settingsEnabled": false
  }
}
```

**Vendor Portal Access:**
- Limited permissions (only assigned leads)
- Can view and respond to opportunities
- Access to customer communication tools
- Performance dashboard access

### 6. 📧 Automated Communications

**Welcome Email (Upon Approval):**
```html
<h2>Welcome to Dockside Pros, Michael!</h2>
<p>Your vendor account has been approved and your user credentials have been created.</p>
<p><strong>Company:</strong> Marine Pro Solutions LLC</p>
<p><strong>Email:</strong> mike@marineprosolutions.com</p>
<p>You can now log in to your vendor portal to:</p>
<ul>
  <li>View and manage your assigned leads</li>
  <li>Update your availability status</li>
  <li>Communicate with clients through the portal</li>
</ul>
```

**Lead Notifications (When Assigned):**
```
🚤 NEW LEAD ALERT - Boat Maintenance

Customer: John Smith
Service: Ceramic coating for 40ft yacht
Location: 33139
Timeline: Within 2 weeks

Please respond quickly to secure this lead!
Contact customer: (305) 555-0456

- Dockside Pros Lead Router
```

### 7. 📊 Analytics & Reporting

**Vendor Performance Metrics:**
- Lead response time tracking
- Conversion rate monitoring
- Customer satisfaction scores
- Service area coverage analysis
- Revenue attribution

**Business Intelligence:**
- Service demand by geographic area
- Vendor capacity utilization
- Market gap identification
- Performance benchmarking

### 8. 🔄 Workflow Automation

**Approval Workflow:**
1. Vendor submits application → GHL contact created
2. Admin reviews application → Manual approval process
3. Approval triggers → GHL workflow webhook
4. User account created → Welcome email sent
5. Vendor activated → Available for lead routing

**Lead Assignment Workflow:**
1. Customer lead received → Service category classified
2. Geographic matching → Find vendors in service area
3. Performance-based selection → Choose optimal vendor
4. Lead assignment → Notify vendor via SMS/email
5. Response tracking → Monitor vendor engagement

## API Endpoints for Vendor Management

### Submit Vendor Application
```http
POST /api/v1/webhooks/elementor/vendor_application_general
Content-Type: application/json

{
  "firstName": "Michael",
  "lastName": "Rodriguez",
  "email": "mike@marineprosolutions.com",
  // ... rest of vendor data
}
```

### Trigger User Creation (GHL Workflow)
```http
POST /api/v1/webhooks/ghl/vendor-user-creation
Content-Type: application/json

{
  "contact_id": "ghl_contact_id",
  "email": "mike@marineprosolutions.com",
  "firstName": "Michael",
  "lastName": "Rodriguez",
  "vendor_company_name": "Marine Pro Solutions LLC"
}
```

### Get Vendor Status
```http
GET /api/v1/simple-admin/vendors
Authorization: Bearer jwt_token
```

## Required Custom Fields in GHL

The system expects these custom fields to be configured in GoHighLevel:

1. **vendor_company_name** - Company/Business Name
2. **services_provided** - Services Offered
3. **service_zip_codes** - Service Area ZIP Codes
4. **years_in_business** - Years in Business
5. **certifications_licenses** - Certifications & Licenses
6. **insurance_coverage** - Insurance Coverage
7. **emergency_services** - Emergency Services Available
8. **service_radius_miles** - Service Radius (Miles)
9. **special_equipment** - Special Equipment
10. **special_requests__notes** - Additional Notes

## Summary

The Lead Router does much more than just send vendor data to GoHighLevel:

✅ **Data Processing** - Validates, normalizes, and enriches vendor information
✅ **Multi-System Integration** - Stores in both GHL and internal database
✅ **Geographic Indexing** - Creates searchable service area coverage
✅ **Lead Routing Engine** - Matches vendors to incoming leads
✅ **Performance Tracking** - Monitors vendor metrics and adjusts routing
✅ **User Management** - Creates GHL user accounts with appropriate permissions
✅ **Automated Communications** - Sends welcome emails and lead notifications
✅ **Workflow Automation** - Handles approval and assignment processes
✅ **Analytics & Reporting** - Provides business intelligence and performance metrics

This creates a complete vendor management ecosystem that goes far beyond simple data storage!
