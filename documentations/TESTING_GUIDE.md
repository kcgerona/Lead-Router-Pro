# Lead Router Pro - Integration Testing Guide

**Date:** 6/10/2025  
**Purpose:** Test the integrated admin dashboard and API functionality

## Pre-Testing Setup

### 1. Verify Dependencies
```bash
cd Lead-Router-Pro
pip install -r requirements.txt
```

### 2. Check Configuration
Ensure your `.env` file has:
```
GHL_LOCATION_ID=ilmrtA1Vk6rvcy4BswKg
GHL_PRIVATE_TOKEN=pit-c361d89c-d943-4812-9839-8e3223c2f31a
GHL_AGENCY_API_KEY=your_agency_key_if_available
```

### 3. Start the Application
```bash
python main_working_final.py
```

Expected output:
```
🚀 DocksidePros Lead Router Pro starting up...
✅ Enhanced webhook system loaded
✅ Admin dashboard available at /admin
✅ API documentation available at /docs
🎯 Ready to process form submissions!
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Testing Sequence

### Phase 1: Basic Application Health

#### Test 1.1: Root Endpoint
```bash
curl http://localhost:8000/
```
**Expected:** HTML page with navigation links

#### Test 1.2: Health Check
```bash
curl http://localhost:8000/health
```
**Expected:** JSON with status "healthy" and feature list

#### Test 1.3: API Documentation
Visit: `http://localhost:8000/docs`
**Expected:** Interactive Swagger API documentation

### Phase 2: Admin Dashboard Access

#### Test 2.1: Dashboard Loading
Visit: `http://localhost:8000/admin`
**Expected:** 
- Professional dashboard with header
- 4 statistics cards (Forms, Vendors, Leads, Fields)
- 5 navigation tabs
- Loading indicators showing "Checking..." or actual data

#### Test 2.2: System Status Check
In the dashboard, observe the header status indicator
**Expected:** 
- Shows "✅ System Healthy", "⚠️ System Degraded", or "❌ System Error"
- System Status section shows individual component health

### Phase 3: Admin API Endpoints

#### Test 3.1: Admin Health Check
```bash
curl http://localhost:8000/api/v1/admin/health
```
**Expected:** JSON with admin API status and database stats

#### Test 3.2: Test GHL Connection (via dashboard)
1. Go to admin dashboard
2. Click "System Configuration" tab
3. Enter your Location ID and Private Token
4. Click "Test Connection"
**Expected:** Success message with field count

#### Test 3.3: Test GHL Connection (via API)
```bash
curl -X POST http://localhost:8000/api/v1/admin/test-ghl-connection \
  -H "Content-Type: application/json" \
  -d '{
    "locationId": "ilmrtA1Vk6rvcy4BswKg",
    "privateToken": "pit-c361d89c-d943-4812-9839-8e3223c2f31a"
  }'
```
**Expected:** JSON with success=true and fieldCount

### Phase 4: Field Management Testing

#### Test 4.1: Generate Field Reference (Dashboard)
1. Click "Field Management" tab
2. Click "Generate field_reference.json" button
**Expected:** Success message with field counts

#### Test 4.2: Generate Field Reference (API)
```bash
curl -X POST http://localhost:8000/api/v1/admin/generate-field-reference
```
**Expected:** JSON with success=true and field statistics

#### Test 4.3: View Current Fields
1. In "Field Management" tab, check "Current Custom Fields" section
2. Click "Refresh Fields" if needed
**Expected:** List of fields with names, keys, and data types

#### Test 4.4: Load Field Mappings (API)
```bash
curl http://localhost:8000/api/v1/webhooks/field-mappings
```
**Expected:** JSON with custom_field_mappings object

### Phase 5: Form Testing

#### Test 5.1: Test Form Submission (Dashboard)
1. Click "Form Testing" tab
2. Select a form type (e.g., "Ceramic Coating Request")
3. Fill in test data
4. Click "Test Form Submission"
**Expected:** Success message with contact ID and processing details

#### Test 5.2: Test Form Submission (API)
```bash
curl -X POST http://localhost:8000/api/v1/webhooks/elementor/boat_maintenance_ceramic_coating \
  -H "Content-Type: application/json" \
  -d '{
    "firstName": "Test",
    "lastName": "User",
    "email": "test@example.com",
    "phone": "555-123-4567",
    "specific_service_needed": "Test ceramic coating request"
  }'
```
**Expected:** JSON with status="success" and contact details

### Phase 6: System Monitoring

#### Test 6.1: System Health Check
```bash
curl http://localhost:8000/api/v1/webhooks/health
```
**Expected:** JSON with system status and component health

#### Test 6.2: Service Categories
```bash
curl http://localhost:8000/api/v1/webhooks/service-categories
```
**Expected:** JSON with service categories and subcategories

#### Test 6.3: Monitor in Dashboard
1. Click "System Monitoring" tab
2. Check "Recent Activity" and "Active Service Categories"
**Expected:** Activity logs and category listings

### Phase 7: Vendor Management

#### Test 7.1: Get System Stats
```bash
curl http://localhost:8000/api/v1/simple-admin/stats
```
**Expected:** JSON with vendor and lead counts

#### Test 7.2: View Vendors (Dashboard)
1. Click "Vendor Management" tab
**Expected:** Table showing vendors or "No vendors found"

#### Test 7.3: Get Vendors (API)
```bash
curl http://localhost:8000/api/v1/simple-admin/vendors
```
**Expected:** JSON array of vendor data

### Phase 8: CSV Field Creation (if you have CSV file)

#### Test 8.1: Upload CSV via Dashboard
1. Go to "Field Management" tab
2. In "Create Missing Fields" section
3. Select your CSV file
4. Click "Create Fields from CSV"
**Expected:** Success message with created/skipped counts

## Error Testing

### Test Error Handling
Try these deliberately incorrect requests:

#### Invalid GHL Credentials
```bash
curl -X POST http://localhost:8000/api/v1/admin/test-ghl-connection \
  -H "Content-Type: application/json" \
  -d '{
    "locationId": "invalid",
    "privateToken": "invalid"
  }'
```
**Expected:** Error response with meaningful message

#### Invalid Form Submission
```bash
curl -X POST http://localhost:8000/api/v1/webhooks/elementor/nonexistent_form \
  -H "Content-Type: application/json" \
  -d '{}'
```
**Expected:** Error response or graceful fallback

## Integration Verification

### Dashboard-API Integration
1. Perform actions in dashboard
2. Verify API endpoints return expected data
3. Check that dashboard displays API responses correctly

### Database Integration
1. Submit test forms
2. Check if data appears in stats
3. Verify vendor/lead counts update

### Field Reference Integration
1. Generate field reference
2. Check file is created: `ls -la field_reference.json`
3. Verify dashboard loads current fields correctly

## Success Criteria

✅ **All API endpoints respond without 500 errors**  
✅ **Dashboard loads and displays data correctly**  
✅ **GHL API connection works**  
✅ **Form submissions process successfully**  
✅ **Field management functions work**  
✅ **System monitoring shows accurate status**  
✅ **Error handling provides meaningful feedback**

## Common Issues & Solutions

### Issue: Dashboard shows "Connection failed"
**Solution:** Check that the server is running and baseURL is correct

### Issue: GHL API test fails
**Solution:** Verify credentials in .env file and Location ID

### Issue: Field reference generation fails
**Solution:** Check GHL API credentials and network connectivity

### Issue: Form submission fails
**Solution:** Verify webhook routes are loaded and field mappings exist

## Performance Testing

### Load Testing (Optional)
```bash
# Test multiple form submissions
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/webhooks/elementor/boat_maintenance_ceramic_coating \
    -H "Content-Type: application/json" \
    -d "{\"firstName\":\"Test$i\",\"lastName\":\"User\",\"email\":\"test$i@example.com\",\"phone\":\"555-123-456$i\"}"
done
```

## Next Steps After Testing

1. **If all tests pass:** System is ready for production deployment
2. **If some tests fail:** Review error messages and check configurations
3. **For production:** Update CORS settings and security configurations
4. **Documentation:** Update API documentation with any discovered endpoints

## Cleanup Redundant Files (After Successful Testing)

Once testing confirms everything works:
```bash
# Remove redundant test files (backup first!)
mkdir backup_redundant_files
mv test_*.py backup_redundant_files/
mv check_client_fields.py backup_redundant_files/
mv debug_field_keys.py backup_redundant_files/
mv ghl_field_*.py backup_redundant_files/
mv lead_simulation_script.py backup_redundant_files/
mv vendor_signup_simulator.py backup_redundant_files/
mv "Port 8000 Monitor.py" backup_redundant_files/
```

## Test Log Template

Use this to track your testing:

```
[ ] Phase 1: Basic Application Health
[ ] Phase 2: Admin Dashboard Access  
[ ] Phase 3: Admin API Endpoints
[ ] Phase 4: Field Management Testing
[ ] Phase 5: Form Testing
[ ] Phase 6: System Monitoring
[ ] Phase 7: Vendor Management
[ ] Phase 8: CSV Field Creation
[ ] Error Testing
[ ] Integration Verification

Notes:
_________________________________
_________________________________
_________________________________
