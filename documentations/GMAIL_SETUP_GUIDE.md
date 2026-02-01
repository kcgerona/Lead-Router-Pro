# 📧 Gmail Setup Guide for 2FA Email Service

This guide provides detailed step-by-step instructions for setting up Gmail to send 2FA emails for Dockside Pro.

## 🎯 Overview

We'll use Gmail's free SMTP service to send 2FA verification codes. This requires:
1. A Gmail account (free)
2. Enable 2-Step Verification on your Google account
3. Generate an App Password for email access
4. Configure the Dockside Pro system

---

## 📋 Prerequisites

- Gmail account (create one at gmail.com if needed)
- Access to Google Account settings
- Admin access to your Dockside Pro system

---

## 🔐 Step 1: Enable 2-Step Verification

### 1.1 Access Google Account Settings
1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Sign in with your Gmail account
3. Click on **"Security"** in the left sidebar

### 1.2 Enable 2-Step Verification
1. Look for **"2-Step Verification"** section
2. Click **"Get started"** or **"Turn on"**
3. Follow the setup wizard:
   - Verify your phone number
   - Choose verification method (SMS or voice call)
   - Enter the verification code sent to your phone
   - Click **"Turn on"**

### 1.3 Verify 2FA is Active
- You should see "2-Step Verification: On" in your Security settings
- You may see backup codes generated (save these safely)

---

## 🔑 Step 2: Generate App Password

### 2.1 Access App Passwords
1. Still in Google Account **Security** settings
2. Under **"2-Step Verification"** section, click **"App passwords"**
3. You may need to sign in again for security

### 2.2 Create New App Password
1. Click **"Select app"** dropdown
2. Choose **"Mail"** from the list
3. Click **"Select device"** dropdown
4. Choose **"Other (Custom name)"**
5. Enter a name like: **"Dockside Pro 2FA"**
6. Click **"Generate"**

### 2.3 Save the App Password
- Google will display a 16-character password like: `abcd efgh ijkl mnop`
- **IMPORTANT:** Copy this password immediately
- **IMPORTANT:** You won't be able to see it again
- Store it securely (you'll need it for configuration)

---

## ⚙️ Step 3: Configure Dockside Pro

### 3.1 Automatic Setup (Recommended)
```bash
cd Lead-Router-Pro
python setup_free_2fa_email.py
```

When prompted:
- **Gmail address:** Enter your full Gmail address (e.g., `yourname@gmail.com`)
- **App Password:** Enter the 16-character password from Step 2.3

### 3.2 Manual Setup (Alternative)
Create or edit `.env` file in your Lead-Router-Pro directory:

```env
# Free 2FA Email Configuration
FREE_2FA_EMAIL=yourname@gmail.com
FREE_2FA_PASSWORD=abcd efgh ijkl mnop
EMAIL_TEST_MODE=false
TWO_FACTOR_ENABLED=true
TWO_FACTOR_CODE_LENGTH=6
TWO_FACTOR_CODE_EXPIRE_MINUTES=10
```

Replace:
- `yourname@gmail.com` with your actual Gmail address
- `abcd efgh ijkl mnop` with your actual App Password

---

## 🧪 Step 4: Test the Setup

### 4.1 Test Email Connection
```bash
cd Lead-Router-Pro
python test_free_2fa_email.py
```

This will:
- Test the SMTP connection
- Send a test 2FA email to your Gmail address
- Verify the email delivery

### 4.2 Test Full 2FA Flow
```bash
cd Lead-Router-Pro
python test_demo_2fa.py
```

Or test through the web interface:
1. Start the server: `python main_working_final.py`
2. Go to: `http://localhost:8000/login`
3. Login with test credentials
4. Check your Gmail for the 2FA code

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### "Authentication failed" Error
**Problem:** SMTP authentication is failing
**Solutions:**
1. Double-check your Gmail address is correct
2. Verify you're using the App Password, not your regular password
3. Make sure 2-Step Verification is enabled
4. Try generating a new App Password

#### "Less secure app access" Error
**Problem:** Google is blocking the connection
**Solutions:**
1. This shouldn't happen with App Passwords
2. If it does, ensure you're using an App Password, not regular password
3. Check that 2-Step Verification is properly enabled

#### "Connection refused" or "Timeout" Error
**Problem:** Network or firewall issues
**Solutions:**
1. Check your internet connection
2. Verify firewall isn't blocking port 587
3. Try from a different network
4. Check if your ISP blocks SMTP

#### No Email Received
**Problem:** Email is sent but not received
**Solutions:**
1. Check your Gmail spam/junk folder
2. Check Gmail's "All Mail" folder
3. Verify the recipient email address is correct
4. Wait a few minutes (sometimes there's a delay)

#### "App Password not available" Error
**Problem:** Can't find App Passwords option
**Solutions:**
1. Ensure 2-Step Verification is enabled first
2. Sign out and sign back into Google Account
3. Try accessing from a different browser
4. Make sure you're using a personal Gmail account (not G Suite/Workspace)

---

## 🔒 Security Best Practices

### App Password Security
- **Never share** your App Password
- **Store securely** - treat it like a password
- **Use unique names** for each app/service
- **Revoke unused** App Passwords regularly

### Email Security
- **Monitor usage** - check for unexpected emails
- **Use dedicated account** - consider a separate Gmail for system emails
- **Regular review** - periodically check your Google Account activity

### System Security
- **Environment variables** - never commit passwords to code
- **Access control** - limit who can access the .env file
- **Regular updates** - keep dependencies updated

---

## 📊 Gmail Limits and Considerations

### Sending Limits
- **Daily limit:** 500 emails per day for free Gmail
- **Rate limit:** ~100 emails per hour
- **Recipient limit:** 500 recipients per day

### For High Volume
If you need to send more emails:
1. **Google Workspace:** Higher limits with paid accounts
2. **Multiple accounts:** Rotate between different Gmail accounts
3. **Dedicated service:** Consider services like SendGrid, Mailgun
4. **Business Gmail:** Upgrade to Gmail for Business

---

## 🚀 Advanced Configuration

### Custom SMTP Settings
If you need to customize SMTP settings, edit the `free_email_2fa.py` file:

```python
# Custom SMTP configuration
self.smtp_host = "smtp.gmail.com"  # Gmail SMTP server
self.smtp_port = 587               # TLS port
# Alternative: port 465 for SSL
```

### Email Templates
Customize email templates in `api/services/free_email_2fa.py`:
- HTML template in `_create_2fa_html()` method
- Text template in `_create_2fa_text()` method

### Multiple Email Accounts
To use multiple Gmail accounts for load balancing:
1. Set up multiple App Passwords
2. Modify the service to rotate between accounts
3. Store multiple credentials in environment variables

---

## 📞 Support and Help

### Google Support
- [Google Account Help](https://support.google.com/accounts)
- [2-Step Verification Help](https://support.google.com/accounts/answer/185839)
- [App Passwords Help](https://support.google.com/accounts/answer/185833)

### Testing Commands
```bash
# Test SMTP connection only
python -c "from api.services.free_email_2fa import free_2fa_service; print(free_2fa_service.test_connection())"

# Send test email
python test_free_2fa_email.py

# Full authentication test
python test_auth_system.py
```

### Debug Mode
Enable debug logging by adding to your `.env`:
```env
LOG_LEVEL=DEBUG
```

---

## ✅ Verification Checklist

Before going live, verify:

- [ ] Gmail account has 2-Step Verification enabled
- [ ] App Password generated and saved securely
- [ ] `.env` file configured with correct credentials
- [ ] SMTP connection test passes
- [ ] Test email received in Gmail inbox
- [ ] Full 2FA login flow works
- [ ] No error messages in application logs
- [ ] Email templates display correctly
- [ ] 2FA codes are readable and correct format

---

## 🎉 Success!

Once everything is working:
1. **Document your setup** - save your configuration details
2. **Test regularly** - verify emails are still working
3. **Monitor usage** - watch for any delivery issues
4. **Plan for scale** - consider limits as your user base grows

Your Gmail-powered 2FA email system is now ready for production use! 📧🔐

---

## 📝 Quick Reference

**Gmail SMTP Settings:**
- Server: `smtp.gmail.com`
- Port: `587` (TLS) or `465` (SSL)
- Security: TLS/SSL required
- Authentication: App Password required

**Environment Variables:**
```env
FREE_2FA_EMAIL=your.email@gmail.com
FREE_2FA_PASSWORD=your-16-char-app-password
EMAIL_TEST_MODE=false
TWO_FACTOR_ENABLED=true
```

**Test Commands:**
```bash
python setup_free_2fa_email.py    # Setup wizard
python test_free_2fa_email.py     # Test email delivery
python test_auth_system.py        # Test full system
