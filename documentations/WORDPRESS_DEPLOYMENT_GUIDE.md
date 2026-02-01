# Vendor Application Widget - WordPress Deployment Guide

## Overview
This document explains how to deploy the Vendor Application Widget on the main DocksidePros.com WordPress website. The widget is a multi-step form that allows marine service providers to apply to become featured vendors.

## Widget Features
- **Multi-step form** with 8 main slides plus thank you page
- **Real-time validation** with user-friendly error messages
- **Auto-formatting** for phone numbers, ZIP codes, and URLs
- **Dynamic county lookup** via API integration
- **Responsive design** optimized for desktop and mobile
- **Progress tracking** with visual progress bar
- **Cross-domain API calls** to dockside.life backend

## Technical Requirements

### WordPress Compatibility
- **WordPress Version**: 5.0+ recommended
- **Elementor Plugin**: Required for HTML widget embedding
- **PHP Version**: 7.4+ recommended
- **Modern browsers**: Chrome, Firefox, Safari, Edge

### API Dependencies
The widget makes API calls to:
- `https://dockside.life/api/v1/webhooks/elementor/vendor_application` (form submission)
- `https://dockside.life/api/v1/locations/states/{state}/counties` (county lookup)

**Note**: DocksidePros.com is already whitelisted for these API endpoints.

## Deployment Steps

### Step 1: Prepare the Widget Code
1. Copy the entire contents of `vendor_widget.html`
2. Remove the `<!DOCTYPE html>`, `<html>`, `<head>`, and `<body>` tags
3. Keep only the content from `<style>` to `</script>`

### Step 2: WordPress Integration Options

#### Option A: Elementor HTML Widget (Recommended)
1. **Edit the target page** in Elementor
2. **Add HTML Widget** where you want the form to appear
3. **Paste the prepared code** into the HTML widget
4. **Save and test** the functionality

#### Option B: Custom HTML Block (Gutenberg)
1. **Edit the page** in WordPress editor
2. **Add Custom HTML block**
3. **Paste the prepared code**
4. **Publish and test**

#### Option C: Popup Integration
1. **Use Elementor Popup Builder**
2. **Create new popup** with HTML widget
3. **Add trigger** to "Join Now" button
4. **Configure popup settings** (overlay, animation, etc.)

### Step 3: CSS Scoping Verification
The widget CSS is already scoped to `#vendor-survey-widget` to prevent theme conflicts. Verify that:
- Widget styling doesn't affect other page elements
- Theme styles don't interfere with widget appearance
- Mobile responsiveness is maintained

### Step 4: Button Integration
To trigger the widget as a popup:

```html
<button onclick="openVendorWidget()" class="join-now-button">
    Join Now
</button>

<script>
function openVendorWidget() {
    // Show Elementor popup or display widget div
    elementorProFrontend.modules.popup.showPopup('popup-id');
}
</script>
```

## Configuration Options

### Debug Mode
Enable debug logging by adding `?debug=true` to the page URL. This will:
- Log form interactions to browser console
- Show detailed API request/response data
- Help troubleshoot any issues

### API Endpoints
The widget is configured to use production endpoints:
- Form submission: `https://dockside.life/api/v1/webhooks/elementor/vendor_application`
- County lookup: `https://dockside.life/api/v1/locations/states/{state}/counties`

## Form Flow & Functionality

### Form Steps:
1. **Company Name** - Business name with alphanumeric validation
2. **Company Address** - Full address with validation and formatting
3. **Personal Info** - Contact details with email/phone formatting
4. **Primary Service** - Main service category selection
5. **Additional Services** - Up to 2 additional categories (optional)
6. **Additional Service Details** - Specific services (if additional categories selected)
7. **Coverage Area** - Service territory (global, national, state, county, or ZIP)
8. **Final Details** - Years in business, contact preferences, URLs, notes
9. **Thank You Page** - Success confirmation with next steps

### Key Features:
- **Auto-save draft** functionality using localStorage
- **Smart navigation** that skips irrelevant steps
- **Real-time validation** with immediate feedback
- **Progress tracking** with percentage completion
- **Mobile optimization** with touch-friendly controls

## WordPress-Specific Considerations

### Theme Compatibility
The widget is designed to work with any WordPress theme:
- All CSS is scoped to the widget container
- No global styles that could conflict
- Responsive design adapts to container width

### Plugin Conflicts
Potential conflicts and solutions:
- **jQuery conflicts**: Widget uses vanilla JavaScript with jQuery fallback
- **CSS conflicts**: All styles are scoped to prevent interference
- **Cache plugins**: Widget works with most caching solutions

### Performance
- **Lightweight**: ~2500 lines including all functionality
- **No external dependencies**: Self-contained HTML/CSS/JavaScript
- **Optimized images**: Rope separator loads from CDN

## Testing Checklist

### Pre-Deployment Testing:
- [ ] Form loads without JavaScript errors
- [ ] All validation rules work correctly
- [ ] API calls succeed (county lookup, form submission)
- [ ] Progress bar updates correctly
- [ ] Mobile responsiveness verified
- [ ] Thank you page displays properly

### Post-Deployment Testing:
- [ ] Test from different devices/browsers
- [ ] Verify form submissions reach the backend
- [ ] Check email notifications are sent
- [ ] Confirm data appears in admin dashboard
- [ ] Test popup trigger (if using popup method)

## Troubleshooting

### Common Issues:

#### 1. Counties Not Loading
- **Cause**: CORS or API connectivity issues
- **Solution**: Verify docksidepros.com is whitelisted in API
- **Fallback**: Manual county entry textarea appears automatically

#### 2. Form Submission Fails
- **Cause**: API endpoint unreachable or validation errors
- **Solution**: Check browser console for error details
- **Test**: Use debug mode to see full error messages

#### 3. CSS Conflicts
- **Cause**: Theme styles overriding widget styles
- **Solution**: Increase CSS specificity or add `!important` declarations
- **Prevention**: All widget CSS is already scoped

#### 4. Mobile Display Issues
- **Cause**: Theme responsive styles conflicting
- **Solution**: Test on actual devices, adjust widget container width
- **Note**: Widget is optimized for 600px max width

### Debug Tools:
- Browser Developer Console (F12)
- Network tab to monitor API calls
- Application tab to check localStorage (draft functionality)
- Console tab for JavaScript errors

## Support Information

### Widget Maintenance:
- Widget code is self-contained and doesn't require regular updates
- API endpoints are maintained separately
- Backend processing handles all data validation and storage

### Documentation:
- Complete form validation rules documented in main codebase
- API documentation available in project root
- Field mappings defined in database structure docs

### Contact:
For technical issues or modifications, contact the development team with:
- Page URL where widget is deployed
- Browser console errors (if any)
- Steps to reproduce the issue
- Screenshots of the problem

---

## Quick Reference

### Widget Container ID: `#vendor-survey-widget`
### API Base URL: `https://dockside.life/api/v1/`
### Required Permissions: CORS enabled for docksidepros.com
### Mobile Breakpoint: 768px
### Form Validation: Real-time + submit-time
### Data Storage: Auto-draft + final submission

This widget provides a professional, user-friendly interface for vendor applications while maintaining security and performance standards suitable for the main DocksidePros.com website.