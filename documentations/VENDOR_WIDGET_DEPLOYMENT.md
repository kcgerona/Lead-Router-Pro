# Vendor Widget Deployment Guide for dockside.life

## Current Configuration Status ✅

The vendor widget (`vendor_widget_wordpress_embed_example.html`) is **already configured** for production use on https://dockside.life

### Production Endpoints Configured:
1. **Form Submission**: `https://dockside.life/api/v1/webhooks/elementor/vendor_application`
2. **County Data API**: `https://dockside.life/api/v1/locations/states/{state_code}/counties`

### Key Features Ready for Production:
- ✅ Complete Level 3 services (300+ specific services)
- ✅ Orange badges showing Level 3 service counts
- ✅ Modal popup for Level 3 service selection
- ✅ Multi-step form with validation
- ✅ Coverage area selection (Global, National, State, County)
- ✅ Auto-save draft functionality
- ✅ CORS configured to accept requests from any origin

## Deployment Steps

### 1. Deploy the Widget File
Upload the file to your web server:
```bash
# Copy the vendor widget to your web root
cp vendor_widget_wordpress_embed_example.html /var/www/html/vendor-widget.html
```

Or serve it through the FastAPI application at:
- https://dockside.life/vendor-widget

### 2. Embed in WordPress/Elementor

#### Option A: Direct iFrame Embed
```html
<iframe 
    src="https://dockside.life/vendor-widget" 
    width="100%" 
    height="800" 
    frameborder="0"
    style="border: none; max-width: 600px; margin: 0 auto; display: block;">
</iframe>
```

#### Option B: HTML Embed with Responsive Container
```html
<div style="width: 100%; max-width: 600px; margin: 0 auto;">
    <iframe 
        src="https://dockside.life/vendor-widget" 
        width="100%" 
        height="800" 
        frameborder="0"
        style="border: none;">
    </iframe>
</div>
```

#### Option C: WordPress Shortcode (if using custom plugin)
```php
// Add to your theme's functions.php or custom plugin
function vendor_widget_shortcode() {
    return '<iframe src="https://dockside.life/vendor-widget" width="100%" height="800" frameborder="0" style="border: none; max-width: 600px; margin: 0 auto; display: block;"></iframe>';
}
add_shortcode('vendor_widget', 'vendor_widget_shortcode');

// Then use in WordPress: [vendor_widget]
```

### 3. Verify GoHighLevel Integration

The vendor application webhook sends data to GHL with the following mapping:

#### Core Fields Mapped to GHL:
- `firstName` → First Name
- `lastName` → Last Name
- `email` → Email
- `phone` → Phone
- `vendor_company_name` → Company Name (custom field)
- `primary_service_category` → Primary Category (custom field)
- `primary_services` → Primary Services (custom field)
- `additional_categories` → Additional Categories (custom field)
- `additional_services` → Additional Services (custom field)
- `service_coverage_area` → Coverage Area (custom field)
- `years_in_business` → Years in Business (custom field)

#### Level 3 Services Data:
- `primary_level3_services` → JSON object with selected Level 3 services
- `additional_level3_services` → JSON object with additional Level 3 services
- `all_level3_services` → Combined Level 3 services

#### Tags Added Automatically:
- "New Vendor Application"
- "Vendor"
- Service category tags

### 4. Test the Integration

1. **Test Form Submission**:
   ```bash
   # Monitor the webhook logs
   tail -f /var/log/leadrouter.log
   
   # Or check the API response
   curl -X GET https://dockside.life/api/v1/webhooks/health
   ```

2. **Verify in GoHighLevel**:
   - Check Contacts for new vendor applications
   - Verify custom fields are populated
   - Check tags are applied correctly
   - Confirm opportunity is created (if pipeline configured)

### 5. Monitor Performance

Check system health:
```bash
curl https://dockside.life/api/v1/webhooks/health
```

Expected response:
```json
{
    "status": "healthy",
    "service": "DocksidePros Clean Webhook System",
    "version": "2.0.0",
    "supported_form_types": ["client_lead", "vendor_application", "emergency_service", "general_inquiry"]
}
```

## Form Configuration

### Form Identifier
The webhook expects the form identifier: `vendor_application`

This is automatically handled by the widget when submitting to:
`https://dockside.life/api/v1/webhooks/elementor/vendor_application`

### Required Fields
The form validates these required fields:
- Company Name
- Contact Name (First & Last)
- Email
- Phone
- Primary Service Category
- At least one Primary Service
- Coverage Type
- SMS Consent

### Optional Fields with Level 3 Enhancement
- Additional Service Categories (up to 2)
- Level 3 Specific Services (modal selection)
- Years in Business
- Certifications
- Insurance Information
- Website
- Google Profile URL
- Additional Notes

## Troubleshooting

### Issue: Form Not Submitting
1. Check browser console for errors
2. Verify API endpoint is accessible:
   ```bash
   curl -X POST https://dockside.life/api/v1/webhooks/elementor/vendor_application \
     -H "Content-Type: application/json" \
     -d '{"test": "ping"}'
   ```

### Issue: Counties Not Loading
1. Test the counties API:
   ```bash
   curl https://dockside.life/api/v1/locations/states/FL/counties
   ```

### Issue: CORS Errors
The server is configured to allow all origins (`*`). If you still get CORS errors:
1. Check if any security middleware is blocking requests
2. Verify the API server is running
3. Check nginx/Apache configuration if using reverse proxy

### Issue: Data Not Appearing in GHL
1. Verify GHL API credentials in `.env`:
   ```
   GHL_LOCATION_ID=xxx
   GHL_PRIVATE_TOKEN=xxx
   GHL_AGENCY_API_KEY=xxx
   ```
2. Check field mappings in `field_reference.json`
3. Monitor webhook logs for errors

## Security Considerations

1. **IP Whitelisting**: Consider adding IP restrictions for production
2. **Rate Limiting**: Implement rate limiting for form submissions
3. **Input Validation**: The form includes client-side validation, server validates too
4. **SSL/TLS**: Ensure all endpoints use HTTPS
5. **API Keys**: Keep GHL API keys secure and rotate regularly

## Support

For issues or questions:
1. Check webhook logs: `/var/log/leadrouter.log`
2. Access admin dashboard: https://dockside.life/admin
3. View API documentation: https://dockside.life/docs

## Next Steps

1. **Monitor Initial Submissions**: Watch the first few vendor applications
2. **Optimize Field Mappings**: Adjust GHL custom fields as needed
3. **Set Up Automation**: Create GHL workflows for vendor onboarding
4. **Analytics**: Track conversion rates and form completions
5. **A/B Testing**: Test different form layouts or questions

---

**Status**: ✅ READY FOR PRODUCTION

The vendor widget is fully configured and ready to accept vendor applications on https://dockside.life