# Lead Router Pro - Complete Setup Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [GoHighLevel Configuration](#gohighlevel-configuration)
4. [Database Initialization](#database-initialization)
5. [Email & 2FA Setup](#email--2fa-setup)
6. [Application Deployment](#application-deployment)
7. [Admin Dashboard Setup](#admin-dashboard-setup)
8. [Vendor Configuration](#vendor-configuration)
9. [Testing & Validation](#testing--validation)
10. [Production Deployment](#production-deployment)

---

## Prerequisites

### System Requirements
- **Operating System**: Ubuntu 20.04+ / macOS / Windows WSL2
- **Python**: 3.8 or higher
- **Memory**: Minimum 2GB RAM
- **Storage**: 1GB free space
- **Network**: Stable internet connection

### Required Accounts
- **GoHighLevel**: Agency account with API access
- **Email Provider**: Gmail or SMTP server for 2FA
- **Domain** (Production): For webhook endpoints

### Software Dependencies
```bash
# Check Python version
python3 --version  # Should be 3.8+

# Install pip if not present
sudo apt-get update
sudo apt-get install python3-pip

# Install virtual environment
pip3 install virtualenv
```

---

## Environment Setup

### 1. Clone Repository
```bash
git clone https://github.com/your-org/Lead-Router-Pro.git
cd Lead-Router-Pro
```

### 2. Create Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create Environment File
```bash
cp .env.example .env
```

### 5. Configure Environment Variables
Edit `.env` file with your credentials:

```env
# ======================
# GoHighLevel Configuration
# ======================
GHL_LOCATION_ID=your_location_id_here
GHL_PRIVATE_TOKEN=your_private_token_here
GHL_AGENCY_API_KEY=your_agency_api_key_here
GHL_COMPANY_ID=your_company_id_here
GHL_WEBHOOK_API_KEY=generate_secure_key_here

# ======================
# Database Configuration
# ======================
DATABASE_URL=sqlite:///smart_lead_router.db
# For PostgreSQL (production):
# DATABASE_URL=postgresql://user:password@localhost/leadrouter

# ======================
# Security Configuration
# ======================
SECRET_KEY=generate_32_char_secret_key_here
JWT_SECRET_KEY=generate_jwt_secret_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# ======================
# Email Configuration (2FA)
# ======================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_specific_password
SMTP_FROM_EMAIL=noreply@yourdomain.com

# ======================
# Application Settings
# ======================
APP_ENV=development  # or production
APP_DEBUG=true  # false in production
APP_HOST=0.0.0.0
APP_PORT=8000
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# ======================
# GHL Pipeline (Optional)
# ======================
PIPELINE_ID=your_pipeline_id
PIPELINE_STAGE_ID=your_stage_id
OPPORTUNITY_MONETARY_VALUE=1000

# ======================
# IP Security (Optional)
# ======================
ALLOWED_IPS=127.0.0.1,your_server_ip
WEBHOOK_TIMEOUT=30
MAX_RETRIES=3
```

---

## GoHighLevel Configuration

### 1. Obtain API Credentials

#### Location ID
1. Log into GoHighLevel
2. Navigate to Settings → Business Info
3. Copy the Location ID

#### Private Token
1. Go to Settings → Integrations → API
2. Click "Generate Private Token"
3. Name it "Lead Router Pro"
4. Copy and save securely

#### Agency API Key
1. Access Agency Settings
2. Navigate to API Keys
3. Generate new key for "Lead Router Pro"
4. Set appropriate permissions

### 2. Create Custom Fields

Run the field generation script:
```bash
python -c "
from api.services.ghl_api import GoHighLevelAPI
from config import AppConfig

ghl = GoHighLevelAPI(
    private_token=AppConfig.GHL_PRIVATE_TOKEN,
    location_id=AppConfig.GHL_LOCATION_ID
)

# Create required custom fields
fields = [
    'service_category',
    'specific_service',
    'zip_code_of_service',
    'vendor_company_name',
    'services_offered',
    'coverage_type',
    'coverage_areas'
]

for field in fields:
    ghl.create_custom_field(field, 'CONTACT')
    print(f'Created field: {field}')
"
```

### 3. Configure Webhooks

In GoHighLevel:
1. Navigate to Settings → Webhooks
2. Create new webhook
3. Set URL: `https://yourdomain.com/api/v1/webhooks/elementor/{form_name}`
4. Add header: `X-Webhook-API-Key: your_webhook_api_key`
5. Select triggers: Contact Created, Contact Updated

---

## Database Initialization

### 1. Create Database Tables
```bash
python -c "
from database.simple_connection import db
db.create_tables()
print('Database tables created successfully')
"
```

### 2. Create Admin User
```bash
python test_scripts/create_admin_user.py
```

Follow prompts to set:
- Admin email
- Admin password
- Admin name

### 3. Verify Database
```bash
sqlite3 smart_lead_router.db ".tables"
# Should show: tenants, users, vendors, leads, etc.
```

---

## Email & 2FA Setup

### Gmail Configuration

1. **Enable 2-Step Verification**
   - Go to Google Account settings
   - Security → 2-Step Verification
   - Enable and configure

2. **Generate App Password**
   - Security → App passwords
   - Select "Mail"
   - Generate password
   - Copy to `.env` as `SMTP_PASSWORD`

3. **Test Email Configuration**
```bash
python test_scripts/test_email_direct.py
```

### Custom SMTP Configuration

For other email providers, update `.env`:
```env
SMTP_HOST=mail.yourdomain.com
SMTP_PORT=465  # or 587 for TLS
SMTP_USERNAME=noreply@yourdomain.com
SMTP_PASSWORD=your_password
SMTP_USE_TLS=true  # or false for SSL
```

---

## Application Deployment

### Development Mode

```bash
# Start the application
python main_working_final.py

# Application will be available at:
# - Admin Dashboard: http://localhost:8000/admin
# - API Docs: http://localhost:8000/docs
# - Health Check: http://localhost:8000/health
```

### Production Mode with Gunicorn

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn main_working_final:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile /var/log/leadrouter/access.log \
  --error-logfile /var/log/leadrouter/error.log
```

### Docker Deployment

```bash
# Build Docker image
docker build -t leadrouter:latest .

# Run container
docker run -d \
  --name leadrouter \
  -p 8000:8000 \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/smart_lead_router.db:/app/smart_lead_router.db \
  leadrouter:latest
```

### SystemD Service (Production)

Create `/etc/systemd/system/leadrouter.service`:

```ini
[Unit]
Description=Lead Router Pro Application
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/Lead-Router-Pro
Environment="PATH=/opt/Lead-Router-Pro/venv/bin"
ExecStart=/opt/Lead-Router-Pro/venv/bin/gunicorn main_working_final:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable leadrouter
sudo systemctl start leadrouter
sudo systemctl status leadrouter
```

---

## Admin Dashboard Setup

### 1. Access Dashboard
Navigate to: `http://localhost:8000/admin`

### 2. Login with 2FA
1. Enter admin credentials
2. Check email for 2FA code
3. Enter code to complete login

### 3. Initial Configuration

#### System Health Check
- Navigate to "System Health" tab
- Verify all components are green
- Check GHL connection status

#### Field Reference Generation
1. Go to "Field Management" tab
2. Click "Generate Field Reference"
3. System will sync with GHL
4. Verify fields are loaded

#### IP Whitelist Setup
1. Navigate to "Security" tab
2. Add trusted IP addresses
3. Enable IP filtering if needed

---

## Vendor Configuration

### 1. Service Categories Setup

Verify service categories are loaded:
```bash
python -c "
from api.services.service_categories import SERVICE_CATEGORIES, LEVEL_3_SERVICES
print(f'Level 1 Categories: {len(SERVICE_CATEGORIES)}')
print(f'Categories with Level 3: {len(LEVEL_3_SERVICES)}')
"
```

### 2. Vendor Application Widget

Deploy vendor application form:

```html
<!-- Add to your website -->
<iframe 
  src="https://yourdomain.com/vendor-widget" 
  width="100%" 
  height="800"
  frameborder="0">
</iframe>
```

### 3. Vendor Approval Workflow

1. Vendor submits application via widget
2. Admin reviews in dashboard
3. Approve vendor → Creates GHL user
4. Vendor receives credentials
5. Vendor is activated for lead routing

---

## Testing & Validation

### 1. Test Form Submission
```bash
curl -X POST http://localhost:8000/api/v1/webhooks/elementor/test \
  -H "Content-Type: application/json" \
  -H "X-Webhook-API-Key: your_webhook_key" \
  -d '{
    "firstName": "Test",
    "lastName": "User",
    "email": "test@example.com",
    "phone": "555-0100",
    "service_requested": "Boat Detailing",
    "zip_code": "33139"
  }'
```

### 2. Test Vendor Matching
```bash
python test_scripts/test_vendor_matching.py
```

### 3. Test GHL Integration
```bash
python test_scripts/test_ghl_connection.py
```

### 4. Load Testing
```bash
# Install locust
pip install locust

# Run load test
locust -f test_scripts/load_test.py --host=http://localhost:8000
```

---

## Production Deployment

### 1. Domain Configuration

#### Nginx Reverse Proxy
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### SSL with Let's Encrypt
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
```

### 2. Environment Hardening

```bash
# Set production environment
export APP_ENV=production
export APP_DEBUG=false

# Restrict file permissions
chmod 600 .env
chmod 700 /opt/Lead-Router-Pro

# Create non-root user
useradd -m -s /bin/bash leadrouter
chown -R leadrouter:leadrouter /opt/Lead-Router-Pro
```

### 3. Monitoring Setup

#### Health Check Monitoring
```bash
# Add to crontab
*/5 * * * * curl -f http://localhost:8000/health || systemctl restart leadrouter
```

#### Log Rotation
Create `/etc/logrotate.d/leadrouter`:
```
/var/log/leadrouter/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload leadrouter
    endscript
}
```

### 4. Backup Strategy

```bash
# Daily database backup
0 2 * * * sqlite3 /opt/Lead-Router-Pro/smart_lead_router.db ".backup /backup/leadrouter-$(date +\%Y\%m\%d).db"

# Weekly full backup
0 3 * * 0 tar -czf /backup/leadrouter-full-$(date +\%Y\%m\%d).tar.gz /opt/Lead-Router-Pro
```

---

## Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000
# Kill process
kill -9 <PID>
```

#### Database Locked
```bash
# Check for locks
fuser smart_lead_router.db
# Clear locks
rm smart_lead_router.db-journal
```

#### GHL Connection Failed
1. Verify API credentials in `.env`
2. Check IP whitelist in GHL
3. Test with `curl` to GHL API
4. Review logs for specific errors

#### Email/2FA Not Working
1. Verify SMTP settings
2. Check app password (not regular password)
3. Test with `test_scripts/test_email_direct.py`
4. Check spam folder

### Debug Mode

Enable detailed logging:
```python
# In main_working_final.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Support

For additional help:
- Check logs: `/var/log/leadrouter/`
- API Documentation: `/docs`
- GitHub Issues: Report bugs and feature requests
- Email: support@leadrouterpro.com

---

## Next Steps

1. **Configure Webhooks**: Set up form integrations
2. **Add Vendors**: Onboard service providers
3. **Test Workflows**: Validate end-to-end process
4. **Monitor Performance**: Set up analytics
5. **Scale as Needed**: Add workers, upgrade database

---

**Last Updated**: December 2024 | **Version**: 2.0.0