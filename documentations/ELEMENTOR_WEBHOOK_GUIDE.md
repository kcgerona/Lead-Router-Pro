# 🚤 Elementor Webhook Integration Guide for Dockside Pro

This guide shows WordPress developers how to configure Elementor forms to send webhooks to the Dockside Pro lead routing system.

## 🔧 Webhook Configuration Fixed

**✅ PROBLEM SOLVED:** The system now handles both JSON and form-encoded data automatically!

Your WordPress/Elementor forms can send data in either format:
- `application/json` (preferred)
- `application/x-www-form-urlencoded` (fallback)

The system will automatically detect and parse the correct format.

---

## 📡 Webhook URLs by Service Category

### Base URL Pattern:
```
https://dockside.life/api/v1/webhooks/elementor/{form_identifier}
```

### Complete Webhook URLs:

#### Boat Maintenance Services:
```
https://dockside.life/api/v1/webhooks/elementor/boat_maintenance
https://dockside.life/api/v1/webhooks/elementor/ceramic_coating
https://dockside.life/api/v1/webhooks/elementor/boat_detailing
https://dockside.life/api/v1/webhooks/elementor/bottom_cleaning
https://dockside.life/api/v1/webhooks/elementor/oil_change
https://dockside.life/api/v1/webhooks/elementor/bilge_cleaning
```

#### Marine Systems:
```
https://dockside.life/api/v1/webhooks/elementor/marine_systems
https://dockside.life/api/v1/webhooks/elementor/electrical_service
https://dockside.life/api/v1/webhooks/elementor/plumbing
https://dockside.life/api/v1/webhooks/elementor/ac_sales
https://dockside.life/api/v1/webhooks/elementor/ac_service
```

#### Emergency Services:
```
https://dockside.life/api/v1/webhooks/elementor/boat_towing
https://dockside.life/api/v1/webhooks/elementor/emergency_tow
https://dockside.life/api/v1/webhooks/elementor/towing_membership
```

#### Vendor Applications:
```
https://dockside.life/api/v1/webhooks/elementor/vendor_application
https://dockside.life/api/v1/webhooks/elementor/join_network
```

#### General Forms:
```
https://dockside.life/api/v1/webhooks/elementor/general_contact
https://dockside.life/api/v1/webhooks/elementor/email_subscribe
```

---

## 📋 Sample Webhook Payloads

### 1. Boat Detailing Service Request

**Webhook URL:** `https://dockside.life/api/v1/webhooks/elementor/boat_detailing`

**JSON Payload:**
```json
{
  "firstName": "John",
  "lastName": "Smith",
  "email": "john.smith@email.com",
  "phone": "555-123-4567",
  "specific_service_needed": "Ceramic coating and full detail",
  "zip_code_of_service": "33101",
  "vessel_make": "Sea Ray",
  "vessel_model": "Sundancer",
  "vessel_year": "2020",
  "vessel_length_ft": "35",
  "vessel_location__slip": "Marina Bay Slip 42",
  "desired_timeline": "Within 2 weeks",
  "budget_range": "$2000-$5000",
  "special_requests__notes": "Need work completed before boat show"
}
```

**Form-Encoded Alternative:**
```
firstName=John&lastName=Smith&email=john.smith@email.com&phone=555-123-4567&specific_service_needed=Ceramic coating and full detail&zip_code_of_service=33101&vessel_make=Sea Ray&vessel_model=Sundancer&vessel_year=2020&vessel_length_ft=35&vessel_location__slip=Marina Bay Slip 42&desired_timeline=Within 2 weeks&budget_range=$2000-$5000&special_requests__notes=Need work completed before boat show
```

### 2. Emergency Towing Request

**Webhook URL:** `https://dockside.life/api/v1/webhooks/elementor/emergency_tow`

**JSON Payload:**
```json
{
  "firstName": "Sarah",
  "lastName": "Johnson",
  "email": "sarah.j@email.com",
  "phone": "555-987-6543",
  "vessel_location__slip": "Anchor at coordinates 25.7617° N, 80.1918° W",
  "zip_code_of_service": "33139",
  "vessel_make": "Boston Whaler",
  "vessel_model": "Outrage",
  "vessel_length_ft": "28",
  "special_requests__notes": "Engine failure, need immediate assistance, 4 people on board"
}
```

### 3. Vendor Application

**Webhook URL:** `https://dockside.life/api/v1/webhooks/elementor/vendor_application`

**JSON Payload:**
```json
{
  "firstName": "Mike",
  "lastName": "Rodriguez",
  "email": "mike@marineservices.com",
  "phone": "555-456-7890",
  "vendor_company_name": "Rodriguez Marine Services",
  "services_provided": "Engine repair, electrical work, generator service",
  "service_zip_codes": "33101,33139,33154,33109",
  "years_in_business": "15",
  "special_requests__notes": "Certified Yamaha and Mercury technician"
}
```

### 4. General Contact Form

**Webhook URL:** `https://dockside.life/api/v1/webhooks/elementor/general_contact`

**JSON Payload:**
```json
{
  "firstName": "Lisa",
  "lastName": "Chen",
  "email": "lisa.chen@email.com",
  "phone": "555-321-9876",
  "special_requests__notes": "Interested in learning more about your services"
}
```

---

## 🔄 How the System Processes Webhooks

### Step 1: Payload Detection
The system automatically detects the format:
- **JSON:** `Content-Type: application/json`
- **Form-encoded:** `Content-Type: application/x-www-form-urlencoded`
- **Auto-detect:** If content-type is missing or incorrect

### Step 2: Field Mapping
Form fields are mapped to GHL (GoHighLevel) fields:

**Standard Fields (go directly to contact):**
- `firstName` → GHL firstName
- `lastName` → GHL lastName  
- `email` → GHL email
- `phone` → GHL phone
- `companyName` → GHL companyName

**Custom Fields (go to customFields array):**
- `specific_service_needed` → Custom field ID
- `zip_code_of_service` → Custom field ID
- `vessel_make` → Custom field ID
- `vessel_model` → Custom field ID
- `vessel_year` → Custom field ID
- `vessel_length_ft` → Custom field ID
- `vessel_location__slip` → Custom field ID
- `desired_timeline` → Custom field ID
- `budget_range` → Custom field ID
- `special_requests__notes` → Custom field ID

### Step 3: GHL Payload Creation
The system creates a properly formatted GHL payload:

```json
{
  "firstName": "John",
  "lastName": "Smith",
  "email": "john.smith@email.com",
  "phone": "555-123-4567",
  "tags": ["Boat Maintenance", "DSP Elementor", "New Lead"],
  "source": "Boat Detailing (DSP)",
  "customFields": [
    {
      "id": "ghl_field_id_1",
      "value": "Ceramic coating and full detail"
    },
    {
      "id": "ghl_field_id_2", 
      "value": "33101"
    },
    {
      "id": "ghl_field_id_3",
      "value": "Sea Ray"
    }
  ]
}
```

---

## 🎯 Form Identifier Logic

The form identifier in the URL determines:

### Service Category Detection:
- `boat_detailing` → "Boat Maintenance"
- `emergency_tow` → "Boat Towing" 
- `vendor_application` → "General"
- `marine_systems` → "Marine Systems"

### Form Type Classification:
- **Client Lead:** Most service forms (immediate routing)
- **Vendor Application:** Forms with "vendor", "network", "join", "application"
- **Emergency Service:** Forms with "emergency", "tow", "breakdown", "urgent"
- **General Inquiry:** Forms with "subscribe", "email", "contact", "inquiry"

### Priority Assignment:
- **High:** Emergency services
- **Normal:** Client leads, vendor applications
- **Low:** General inquiries

---

## 🛠️ Elementor Configuration

### Required Headers:
```
Content-Type: application/json
```
*OR*
```
Content-Type: application/x-www-form-urlencoded
```

### HTTP Method:
```
POST
```

### No Authentication Required:
- ❌ No Bearer tokens needed
- ❌ No API keys required
- ❌ No location ID headers needed

### Example Elementor Webhook Settings:
```
Webhook URL: https://dockside.life/api/v1/webhooks/elementor/boat_detailing
Method: POST
Content Type: application/json (preferred) or form-encoded (fallback)
```

---

## 📊 Field Reference Guide

### Required Fields (All Forms):
- `email` - Always required

### Required Fields (Client Leads):
- `firstName`
- `lastName` 
- `email`

### Required Fields (Vendor Applications):
- `firstName`
- `lastName`
- `email`
- `vendor_company_name`

### Common Optional Fields:
- `phone` - Phone number
- `specific_service_needed` - Service description
- `zip_code_of_service` - Service location
- `vessel_make` - Boat manufacturer
- `vessel_model` - Boat model
- `vessel_year` - Boat year
- `vessel_length_ft` - Boat length in feet
- `vessel_location__slip` - Current boat location
- `desired_timeline` - When service is needed
- `budget_range` - Budget expectations
- `special_requests__notes` - Additional notes

### Vendor-Specific Fields:
- `vendor_company_name` - Company name
- `services_provided` - Services offered
- `service_zip_codes` - Service areas (comma-separated)
- `years_in_business` - Experience level

---

## 🧪 Testing Your Webhooks

### Test with CURL:
```bash
curl -X POST "https://dockside.life/api/v1/webhooks/elementor/boat_detailing" \
  -H "Content-Type: application/json" \
  -d '{
    "firstName": "Test",
    "lastName": "User",
    "email": "test@example.com",
    "phone": "555-0123",
    "specific_service_needed": "Test service"
  }'
```

### Expected Response:
```json
{
  "status": "success",
  "message": "Webhook processed successfully. GHL contact {contact_id} created.",
  "contact_id": "ghl_contact_id",
  "action": "created",
  "form_type": "client_lead",
  "service_category": "Boat Maintenance",
  "processing_time_seconds": 1.234,
  "custom_fields_processed": 3
}
```

### Error Response Example:
```json
{
  "detail": "Form validation failed: Required field 'email' is missing or empty"
}
```

---

## 🔍 Debugging

### Check Webhook Logs:
The system logs all webhook attempts with detailed information:
- Content-Type received
- Payload parsing method used
- Field mapping results
- GHL API responses

### Common Issues:

#### 1. "Invalid JSON" Error:
- **Cause:** WordPress sending form-encoded data
- **Solution:** ✅ **FIXED** - System now handles both formats

#### 2. "Required field missing" Error:
- **Cause:** Missing email or other required fields
- **Solution:** Ensure all required fields are included

#### 3. "Field mapping warnings":
- **Cause:** Unknown field names
- **Solution:** Use the field names from this guide

---

## 🚀 Advanced Features

### Dynamic Form Processing:
- System automatically detects service category from form identifier
- No need to hardcode each form - supports unlimited forms
- Intelligent routing based on form type and priority

### AI Classification:
- Advanced AI analyzes form content for better categorization
- Improves lead routing accuracy
- Learns from successful matches

### Opportunity Creation:
- Automatically creates opportunities in GHL pipeline
- Transfers custom field data to opportunities
- Skips opportunity creation for vendor applications

### Vendor Matching:
- Finds matching vendors based on service category and location
- Assigns leads to best-scoring vendors
- Sends SMS notifications to selected vendors

---

## 📞 Support

### Webhook Health Check:
```
GET https://dockside.life/api/v1/webhooks/health
```

### Service Categories List:
```
GET https://dockside.life/api/v1/webhooks/service-categories
```

### Field Mappings Reference:
```
GET https://dockside.life/api/v1/webhooks/field-mappings
```

### Test Form Configuration:
```
POST https://dockside.life/api/v1/webhooks/test/{form_identifier}
```

---

## ✅ Quick Checklist

- [ ] Choose appropriate webhook URL for your service category
- [ ] Configure Elementor form with POST method
- [ ] Include required fields (email, firstName, lastName for client leads)
- [ ] Use field names from this guide
- [ ] Test webhook with sample data
- [ ] Verify successful response
- [ ] Check that contact appears in GHL

Your Elementor forms are now ready to send leads to the Dockside Pro system! 🚤
