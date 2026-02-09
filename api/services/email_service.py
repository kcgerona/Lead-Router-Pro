"""
Email Service
Handles sending emails for 2FA codes, password resets, and notifications
"""

import os
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from jinja2 import Environment, FileSystemLoader
import logging
from config import AppConfig

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        # Use centralized configuration
        config = AppConfig()
        self.smtp_host = config.SMTP_HOST or "smtp.gmail.com"
        self.smtp_port = config.SMTP_PORT
        self.smtp_username = config.SMTP_USERNAME
        self.smtp_password = config.SMTP_PASSWORD
        self.from_email = config.SMTP_FROM_EMAIL or "noreply@dockside.life"
        self.from_name = config.SMTP_FROM_NAME or "Dockside Pro Security"
        
        # Setup Jinja2 for email templates
        self.template_env = Environment(
            loader=FileSystemLoader('templates/email')
        )

    async def send_email(self, to_email: str, subject: str, html_body: str, 
                        text_body: Optional[str] = None) -> bool:
        """Send an email"""
        try:
            if not self.smtp_username or not self.smtp_password:
                logger.warning("SMTP credentials not configured - email not sent")
                return False

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email

            # Add text part if provided
            if text_body:
                text_part = MIMEText(text_body, 'plain')
                msg.attach(text_part)

            # Add HTML part
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)

            # Send email with increased timeout for better reliability
            # Use SMTP_SSL for port 465, SMTP for other ports
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=60)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=60)
                server.starttls()
            
            with server:
                # For SendGrid, use API key as password with 'apikey' as username
                if self.smtp_host == 'smtp.sendgrid.net':
                    server.login('apikey', self.smtp_password)
                else:
                    server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to send email to {to_email}: {error_msg}")
            
            # Check for specific SendGrid authentication errors
            if "Authentication failed" in error_msg or "invalid, expired, or revoked" in error_msg:
                logger.error("SendGrid API key authentication failed - please check SMTP_PASSWORD in .env file")
            
            return False

    async def send_2fa_code(self, to_email: str, code: str, user_name: str = None) -> bool:
        """Send 2FA code email - wait for completion to ensure it works"""
        try:
            # Send email synchronously to ensure it works
            subject = "Your Dockside Pro Security Code"
            
            # HTML template
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Security Code</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
                    .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                    .header {{ text-align: center; margin-bottom: 30px; }}
                    .logo {{ color: #2563eb; font-size: 24px; font-weight: bold; }}
                    .code-container {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0; }}
                    .code {{ font-size: 32px; font-weight: bold; letter-spacing: 4px; margin: 10px 0; }}
                    .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #6c757d; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">🚤 Dockside Pro</div>
                        <h2>Security Verification Code</h2>
                    </div>
                    
                    <p>{"Hello " + user_name + "," if user_name else "Hello,"}</p>
                    
                    <p>You have requested to access your Dockside Pro account. Please use the following security code to complete your login:</p>
                    
                    <div class="code-container">
                        <div>Your Security Code:</div>
                        <div class="code">{code}</div>
                        <div style="font-size: 14px; margin-top: 10px;">This code expires in 10 minutes</div>
                    </div>
                    
                    <div class="warning">
                        <strong>Security Notice:</strong> If you did not request this code, please ignore this email and consider changing your password. Never share this code with anyone.
                    </div>
                    
                    <p>For security reasons, this code will expire in 10 minutes. If you need a new code, please request one from the login page.</p>
                    
                    <div class="footer">
                        <p>This is an automated message from Dockside Pro Security System</p>
                        <p>© 2025 Dockside Pro. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Text fallback
            text_body = f"""
            Dockside Pro Security Verification
            
            {"Hello " + user_name + "," if user_name else "Hello,"}
            
            Your security code is: {code}
            
            This code expires in 10 minutes.
            
            If you did not request this code, please ignore this email.
            
            © 2025 Dockside Pro. All rights reserved.
            """
            
            # Send email synchronously and wait for result
            return await self.send_email(to_email, subject, html_body, text_body)
            
        except Exception as e:
            logger.error(f"Failed to queue 2FA email to {to_email}: {str(e)}")
            return False

    async def _send_2fa_email_async(self, to_email: str, code: str, user_name: str = None):
        """Actually send the 2FA email asynchronously"""
        subject = "Your Dockside Pro Security Code"
        
        # HTML template
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Security Code</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ color: #2563eb; font-size: 24px; font-weight: bold; }}
                .code-container {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0; }}
                .code {{ font-size: 32px; font-weight: bold; letter-spacing: 4px; margin: 10px 0; }}
                .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #6c757d; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🚤 Dockside Pro</div>
                    <h2>Security Verification Code</h2>
                </div>
                
                <p>{"Hello " + user_name + "," if user_name else "Hello,"}</p>
                
                <p>You have requested to access your Dockside Pro account. Please use the following security code to complete your login:</p>
                
                <div class="code-container">
                    <div>Your Security Code:</div>
                    <div class="code">{code}</div>
                    <div style="font-size: 14px; margin-top: 10px;">This code expires in 10 minutes</div>
                </div>
                
                <div class="warning">
                    <strong>Security Notice:</strong> If you did not request this code, please ignore this email and consider changing your password. Never share this code with anyone.
                </div>
                
                <p>For security reasons, this code will expire in 10 minutes. If you need a new code, please request one from the login page.</p>
                
                <div class="footer">
                    <p>This is an automated message from Dockside Pro Security System</p>
                    <p>© 2025 Dockside Pro. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Text fallback
        text_body = f"""
        Dockside Pro Security Verification
        
        {"Hello " + user_name + "," if user_name else "Hello,"}
        
        Your security code is: {code}
        
        This code expires in 10 minutes.
        
        If you did not request this code, please ignore this email.
        
        © 2025 Dockside Pro. All rights reserved.
        """
        
        # Send email asynchronously (no return needed for background task)
        await self.send_email(to_email, subject, html_body, text_body)

    async def send_password_reset(self, to_email: str, reset_code: str, user_name: str = None) -> bool:
        """Send password reset email"""
        subject = "Password Reset Request - Dockside Pro"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Reset</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ color: #2563eb; font-size: 24px; font-weight: bold; }}
                .code-container {{ background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0; }}
                .code {{ font-size: 32px; font-weight: bold; letter-spacing: 4px; margin: 10px 0; }}
                .warning {{ background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #6c757d; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🚤 Dockside Pro</div>
                    <h2>Password Reset Request</h2>
                </div>
                
                <p>{"Hello " + user_name + "," if user_name else "Hello,"}</p>
                
                <p>You have requested to reset your password for your Dockside Pro account. Please use the following code to proceed with your password reset:</p>
                
                <div class="code-container">
                    <div>Password Reset Code:</div>
                    <div class="code">{reset_code}</div>
                    <div style="font-size: 14px; margin-top: 10px;">This code expires in 1 hour</div>
                </div>
                
                <div class="warning">
                    <strong>Security Warning:</strong> If you did not request a password reset, please ignore this email and consider reviewing your account security. Someone may have tried to access your account.
                </div>
                
                <p>For security reasons, this code will expire in 1 hour. If you need a new code, please request one from the password reset page.</p>
                
                <div class="footer">
                    <p>This is an automated message from Dockside Pro Security System</p>
                    <p>© 2025 Dockside Pro. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Dockside Pro Password Reset
        
        {"Hello " + user_name + "," if user_name else "Hello,"}
        
        Your password reset code is: {reset_code}
        
        This code expires in 1 hour.
        
        If you did not request this reset, please ignore this email.
        
        © 2025 Dockside Pro. All rights reserved.
        """
        
        return await self.send_email(to_email, subject, html_body, text_body)

    async def send_account_locked_notification(self, to_email: str, user_name: str = None, 
                                             unlock_time: str = None) -> bool:
        """Send account locked notification"""
        subject = "Account Security Alert - Dockside Pro"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Account Locked</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ color: #2563eb; font-size: 24px; font-weight: bold; }}
                .alert {{ background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #6c757d; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🚤 Dockside Pro</div>
                    <h2>Account Security Alert</h2>
                </div>
                
                <p>{"Hello " + user_name + "," if user_name else "Hello,"}</p>
                
                <div class="alert">
                    <h3>🔒 Account Temporarily Locked</h3>
                    <p>Your account has been temporarily locked due to multiple failed login attempts.</p>
                    {f"<p><strong>Account will be unlocked at:</strong> {unlock_time} UTC</p>" if unlock_time else ""}
                </div>
                
                <p>This is a security measure to protect your account. If you were not attempting to log in, please:</p>
                
                <ul>
                    <li>Review your account security</li>
                    <li>Consider changing your password once the account is unlocked</li>
                    <li>Contact support if you suspect unauthorized access</li>
                </ul>
                
                <p>You will be able to log in again after the lockout period expires.</p>
                
                <div class="footer">
                    <p>This is an automated security message from Dockside Pro</p>
                    <p>© 2025 Dockside Pro. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(to_email, subject, html_body)

    async def send_welcome_email(self, to_email: str, user_name: str, verification_code: str) -> bool:
        """Send welcome email with verification code"""
        subject = "Welcome to Dockside Pro - Verify Your Account"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to Dockside Pro</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ color: #2563eb; font-size: 24px; font-weight: bold; }}
                .welcome {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0; }}
                .code {{ font-size: 24px; font-weight: bold; letter-spacing: 2px; margin: 10px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #6c757d; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🚤 Dockside Pro</div>
                    <h2>Welcome to Dockside Pro!</h2>
                </div>
                
                <p>Hello {user_name},</p>
                
                <p>Welcome to Dockside Pro! We're excited to have you on board. To complete your account setup, please verify your email address with the code below:</p>
                
                <div class="welcome">
                    <h3>Email Verification Code:</h3>
                    <div class="code">{verification_code}</div>
                    <p>This code expires in 10 minutes</p>
                </div>
                
                <p>Once verified, you'll have access to:</p>
                <ul>
                    <li>Smart lead routing system</li>
                    <li>Multi-tenant dashboard</li>
                    <li>Advanced security features</li>
                    <li>Real-time analytics</li>
                </ul>
                
                <p>If you have any questions, our support team is here to help!</p>
                
                <div class="footer">
                    <p>Thank you for choosing Dockside Pro</p>
                    <p>© 2025 Dockside Pro. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(to_email, subject, html_body)


# Global instance
email_service = EmailService()
