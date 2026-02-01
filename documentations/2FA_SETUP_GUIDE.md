# 🔐 2FA Email Setup Guide for Dockside Pro

This guide provides multiple options for setting up 2FA email delivery for testing the dashboard at dockside.life.

## 📦 Step 0: Install Dependencies (Required First)

**Before setting up 2FA, install all required dependencies:**

```bash
cd Lead-Router-Pro
python install_2fa_dependencies.py
```

This will:
- ✅ Check Python version compatibility
- ✅ Install all required email packages
- ✅ Verify imports work correctly
- ✅ Create sample .env file
- ✅ Test 2FA service functionality

---

## 🚀 Quick Start - Demo Mode (Recommended for Testing)

**For immediate testing without email setup:**

```bash
cd Lead-Router-Pro
python install_2fa_dependencies.py  # Install dependencies first
python demo_2fa_setup.py
```

This will:
- ✅ Configure 2FA in demo mode
- ✅ Display 2FA codes in the console
- ✅ Enable 2FA for existing users
- ✅ Create test scripts

**Login credentials remain the same:**
- Email: `joe@ezwai.com` or `admin@dockside.life`
- Password: `DocksideAdmin2025!`

When you login, the 2FA code will appear in your terminal/console.

---

## 📧 Production Setup - Real Email (Gmail)

**For production use with real email delivery:**

```bash
cd Lead-Router-Pro
python setup_free_2fa_email.py
```

This will guide you through:
1. Setting up a Gmail account for 2FA
2. Configuring Gmail App Password
3. Testing email delivery
4. Updating the authentication system

### Gmail App Password Setup:
1. Enable 2FA on your Google account
2. Go to Google Account Settings
3. Security > 2-Step Verification > App passwords
4. Generate password for "Mail"
5. Use the 16-character password in the setup

---

## 🧪 Testing Your Setup

### Option 1: Demo Mode Test
```bash
python test_demo_2fa.py
```

### Option 2: Real Email Test
```bash
python test_free_2fa_email.py
```

### Option 3: Full Authentication Test
```bash
python test_auth_system.py
```

---

## 🔑 Login Credentials for dockside.life

### Primary Admin Account
- **Email:** `joe@ezwai.com`
- **Password:** `DocksideAdmin2025!`
- **Role:** Admin (full access)

### Alternative Admin Account
- **Email:** `admin@dockside.life`
- **Password:** `DocksideAdmin2025!`
- **Role:** Admin (full access)

### Sample User Account
- **Email:** `user@dockside.life`
- **Password:** `DocksideUser2025!`
- **Role:** User (limited access)

---

## 🌐 Access URLs

- **Login Page:** https://dockside.life/login
- **Admin Dashboard:** https://dockside.life/admin
- **API Documentation:** https://dockside.life/docs
- **Health Check:** https://dockside.life/health

---

## 🔄 2FA Login Flow

1. **Step 1:** Enter email and password
2. **Step 2:** System sends 6-digit code
   - **Demo Mode:** Code appears in console
   - **Email Mode:** Code sent to email
3. **Step 3:** Enter the 6-digit code
4. **Step 4:** Access granted with JWT tokens

---

## 📁 Files Created

### Core 2FA Module
- `api/services/free_email_2fa.py` - Free email 2FA service
- `setup_free_2fa_email.py` - Gmail setup script
- `demo_2fa_setup.py` - Demo mode setup script

### Test Scripts
- `test_free_2fa_email.py` - Test email delivery
- `test_demo_2fa.py` - Test demo mode
- `enable_2fa_users.py` - Enable 2FA for users

### Configuration
- `.env` - Environment variables
- `2FA_SETUP_GUIDE.md` - This guide

---

## 🛠️ Manual Configuration

### Environment Variables (.env)

**For Demo Mode:**
```env
EMAIL_TEST_MODE=true
TWO_FACTOR_ENABLED=true
TWO_FACTOR_CODE_LENGTH=6
TWO_FACTOR_CODE_EXPIRE_MINUTES=10
DEMO_2FA_MODE=true
```

**For Gmail:**
```env
FREE_2FA_EMAIL=your.email@gmail.com
FREE_2FA_PASSWORD=your-16-char-app-password
EMAIL_TEST_MODE=false
TWO_FACTOR_ENABLED=true
TWO_FACTOR_CODE_LENGTH=6
TWO_FACTOR_CODE_EXPIRE_MINUTES=10
```

---

## 🔧 Troubleshooting

### Demo Mode Issues
- **Code not showing:** Check console output when logging in
- **Login fails:** Ensure demo_2fa_setup.py ran successfully
- **2FA not required:** Run `python enable_2fa_users.py`

### Email Mode Issues
- **Email not sending:** Check Gmail App Password
- **Authentication failed:** Verify 2FA is enabled on Google account
- **Wrong credentials:** Use App Password, not regular password

### General Issues
- **Server not starting:** Check `python main_working_final.py`
- **Database errors:** Run `python setup_auth.py`
- **Import errors:** Install requirements: `pip install -r requirements.txt`

---

## 🚀 Quick Commands Summary

```bash
# Setup demo mode (recommended for testing)
python demo_2fa_setup.py

# Setup real email (for production)
python setup_free_2fa_email.py

# Enable 2FA for users
python enable_2fa_users.py

# Start the server
python main_working_final.py

# Test the system
python test_demo_2fa.py
```

---

## 🔒 Security Notes

- **Change default passwords** immediately after first login
- **Demo mode** is for testing only - use real email for production
- **2FA codes expire** in 10 minutes
- **Account lockout** after 5 failed attempts (30 minutes)
- **Session timeout** after 60 minutes of inactivity

---

## 📞 Support

If you encounter issues:

1. Check the console output for error messages
2. Verify all dependencies are installed
3. Ensure the database is properly initialized
4. Check that the server is running on the correct port
5. Review the authentication logs for detailed error information

The system is designed to be robust and provide clear error messages to help with troubleshooting.

---

## 🎯 Next Steps

1. **Choose your setup method** (demo or email)
2. **Run the appropriate setup script**
3. **Start the server**
4. **Test login with 2FA**
5. **Access the dashboard at dockside.life**

Your secure 2FA-enabled authentication system is ready! 🚤
