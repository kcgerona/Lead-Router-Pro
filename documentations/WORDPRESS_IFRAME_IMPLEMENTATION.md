# WordPress Iframe Implementation Guide

## Overview
This guide shows how to properly embed the vendor widget iframe in WordPress with automatic height adjustment for mobile devices.

## Implementation Steps

### 1. HTML Iframe Code
Add this iframe to your WordPress page/post where you want the form to appear:

```html
<div class="vendor-widget-container">
    <iframe 
        id="vendor-widget-iframe"
        src="https://dockside.life/vendor-widget"
        width="100%" 
        style="border: none; min-height: 600px; max-width: 650px; margin: 0 auto; display: block;"
        title="Vendor Application Form"
        loading="lazy"
        allow="clipboard-write"
        sandbox="allow-scripts allow-forms allow-same-origin allow-popups">
        <p>Your browser does not support iframes. Please visit <a href="https://dockside.life/vendor-widget">our vendor application page</a> directly.</p>
    </iframe>
</div>
```

### 2. CSS (Optional - for better styling)
Add this CSS to your theme's style.css or via WordPress Customizer:

```css
.vendor-widget-container {
    max-width: 650px;
    margin: 20px auto;
    background: white;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

@media (max-width: 768px) {
    .vendor-widget-container {
        margin: 10px;
        border-radius: 0;
    }
    
    #vendor-widget-iframe {
        min-height: 500px !important;
    }
}
```

### 3. JavaScript for Auto-Height (Required)
Add this JavaScript to your WordPress page. You can do this in several ways:

#### Option A: Add to page template
If editing the page template directly, add this script tag:

```html
<script>
window.addEventListener('message', function(event) {
    // Security check - only accept messages from your domain
    if (event.origin !== 'https://dockside.life') {
        return;
    }
    
    // Handle iframe height adjustment
    if (event.data && event.data.type === 'vendorWidgetResize') {
        const iframe = document.getElementById('vendor-widget-iframe');
        if (iframe) {
            iframe.style.height = event.data.height + 'px';
        }
    }
});

// Mobile fallback height adjustment
function adjustMobileHeight() {
    const iframe = document.getElementById('vendor-widget-iframe');
    if (iframe && window.innerWidth <= 768) {
        const viewportHeight = window.innerHeight;
        iframe.style.height = Math.max(500, viewportHeight - 100) + 'px';
    }
}

// Run on load and resize
window.addEventListener('load', adjustMobileHeight);
window.addEventListener('resize', adjustMobileHeight);
</script>
```

#### Option B: Add via WordPress functions.php
Add to your theme's functions.php file:

```php
function add_vendor_widget_script() {
    // Only add on pages that have the iframe
    if (is_page('your-vendor-page-slug')) { // Replace with your page slug
        ?>
        <script>
        window.addEventListener('message', function(event) {
            if (event.origin !== 'https://dockside.life') return;
            if (event.data && event.data.type === 'vendorWidgetResize') {
                const iframe = document.getElementById('vendor-widget-iframe');
                if (iframe) iframe.style.height = event.data.height + 'px';
            }
        });
        </script>
        <?php
    }
}
add_action('wp_footer', 'add_vendor_widget_script');
```

#### Option C: Using WordPress wp_add_inline_script
```php
function enqueue_vendor_widget_script() {
    if (is_page('your-vendor-page-slug')) { // Replace with your page slug
        wp_enqueue_script('vendor-widget-resize', '', array(), '1.0', true);
        
        $script = "
        window.addEventListener('message', function(event) {
            if (event.origin !== 'https://dockside.life') return;
            if (event.data && event.data.type === 'vendorWidgetResize') {
                const iframe = document.getElementById('vendor-widget-iframe');
                if (iframe) iframe.style.height = event.data.height + 'px';
            }
        });";
        
        wp_add_inline_script('vendor-widget-resize', $script);
    }
}
add_action('wp_enqueue_scripts', 'enqueue_vendor_widget_script');
```

## Troubleshooting

### If the form doesn't show on mobile:
1. Check that the iframe has `width="100%"`
2. Verify the CSS includes mobile responsive styles
3. Test the JavaScript is loading (check browser console)
4. Ensure WordPress isn't stripping the iframe attributes

### If height doesn't adjust automatically:
1. Verify the JavaScript is running (check browser console for errors)
2. Make sure the iframe has the correct `id="vendor-widget-iframe"`
3. Check that the domain in the origin check matches exactly

### Security Notes:
- The `sandbox` attribute restricts iframe capabilities for security
- The origin check in JavaScript prevents malicious height changes
- The `loading="lazy"` improves page performance

## Testing
After implementation:
1. Test on desktop and mobile devices
2. Check browser console for any JavaScript errors
3. Verify the iframe height adjusts when navigating through form steps
4. Test form submission works properly

## Support
If you encounter issues, check that:
- The iframe source URL is accessible: https://dockside.life/vendor-widget
- JavaScript is not being blocked by plugins
- The page doesn't have conflicting CSS that affects iframe sizing