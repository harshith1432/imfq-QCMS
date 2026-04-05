import resend
import os
import secrets
import re
from datetime import datetime, timedelta
from flask import current_app

# Initialize resend with API key from environment
resend.api_key = os.getenv("RESEND_API_KEY")

class EmailUtils:
    @staticmethod
    def _get_app_url():
        """Returns the base app URL formatted correctly."""
        url = os.getenv("APP_URL", "http://localhost:5000")
        return url.rstrip("/")

    @staticmethod
    def send_email(to_email, subject, html_content):
        """Sends an email using Resend API."""
        # Determine the sender address
        from_email = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
        
        # If it's the default onboarding email, try to use the APP_URL domain if available
        if from_email == "onboarding@resend.dev":
            app_url = EmailUtils._get_app_url()
            if "localhost" not in app_url:
                from urllib.parse import urlparse
                try:
                    domain = urlparse(app_url).netloc
                    if domain:
                        # Extract just the domain part (strip port if present)
                        clean_domain = domain.split(":")[0]
                        from_email = f"no-reply@{clean_domain}"
                except:
                    pass

        # Ensure from_email is just the email address if the user provided "Name <email>" in .env
        clean_from = from_email
        if "<" in from_email and ">" in from_email:
            clean_from = from_email.split("<")[1].split(">")[0]

        is_dev = os.getenv("FLASK_ENV") == "development"
        
        # In development mode, always log the email to the console
        if is_dev:
            print("\n" + "="*50)
            print(f"DEVELOPMENT MODE: EMAIL SENT")
            print(f"FROM: {clean_from}")
            print(f"TO: {to_email}")
            print(f"SUBJECT: {subject}")
            print("-" * 50)
            # Try to extract 6-digit OTP if it's an OTP email
            otp_match = re.search(r'>\s*(\d{6})\s*<', html_content)
            if otp_match:
                print(f"OTP CODE: {otp_match.group(1)}")
            else:
                # Fallback: print first 200 chars of HTML
                print(f"CONTENT (truncated): {html_content[:200]}...")
            print("="*50 + "\n")

        try:
            params = {
                "from": f"IMFQ Notifications <{clean_from}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }
            
            # Log what we are trying to send (without sensitive info)
            if current_app:
                current_app.logger.info(f"Attempting to send email via Resend from {clean_from} to {to_email}")

            email = resend.Emails.send(params)
            return email
        except Exception as e:
            error_msg = f"Resend API Error: {str(e)}"
            if "403" in str(e) or "forbidden" in str(e).lower():
                error_msg += " (Likely unverified domain or restricted recipient on free tier. Visit resend.com/domains)"
            
            if current_app:
                current_app.logger.error(error_msg)
            else:
                print(error_msg)
            
            if is_dev:
                return {"id": "dev_mode_dummy_id"}
            return None

    @staticmethod
    def generate_token():
        """Generates a secure random token."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def send_verification_email(user):
        """Sends an email verification link to the user."""
        token = EmailUtils.generate_token()
        user.verification_token = token
        user.token_expiry = datetime.utcnow() + timedelta(hours=24)
        
        # Use APP_URL for external access
        app_url = EmailUtils._get_app_url()
        verify_url = f"{app_url}/api/auth/verify-email/{token}"
        
        subject = "Verify Your IMFQ Account"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2563eb;">Welcome to IMFQ!</h2>
            <p>Hello {user.username},</p>
            <p>Thank you for registering your organization with IMFQ. Please verify your email address to activate your account:</p>
            <div style="margin: 30px 0;">
                <a href="{verify_url}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">Verify Email Address</a>
            </div>
            <p>If the button doesn't work, copy and paste this link into your browser:</p>
            <p>{verify_url}</p>
            <p>This link will expire in 24 hours.</p>
            <p>If you didn't create an account, please ignore this email.</p>
            <hr style="border: 0; border-top: 1px solid #e5e7eb; margin: 30px 0;">
            <p style="color: #6b7280; font-size: 14px;">&copy; {datetime.now().year} IMFQ Enterprise. All rights reserved.</p>
        </div>
        """
        return EmailUtils.send_email(user.email, subject, html)

    @staticmethod
    def send_temp_password_email(user, temp_password):
        """Sends an email with a temporary password to a newly created user."""
        subject = "Your IMFQ Account Credentials"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2563eb;">Welcome to the Team!</h2>
            <p>Hello {user.username or user.email},</p>
            <p>An account has been created for you at IMFQ for <strong>{user.organization.name}</strong>.</p>
            <p>Your login credentials are:</p>
            <div style="background-color: #f3f4f6; padding: 20px; border-radius: 4px; margin: 20px 0;">
                <p style="margin: 0;"><strong>Username:</strong> {user.username}</p>
                <p style="margin: 10px 0 0 0;"><strong>Temporary Password:</strong> <code style="background-color: #e5e7eb; padding: 2px 4px; border-radius: 2px;">{temp_password}</code></p>
            </div>
            <p>Please log in and change your password immediately upon your first sign-in.</p>
            <div style="margin: 30px 0;">
                <a href=\"{EmailUtils._get_app_url()}/login.html\" style=\"background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;\">Log In Now</a>
            </div>
            <hr style="border: 0; border-top: 1px solid #e5e7eb; margin: 30px 0;">
            <p style="color: #6b7280; font-size: 14px;">&copy; {datetime.now().year} IMFQ Enterprise. All rights reserved.</p>
        </div>
        """
        return EmailUtils.send_email(user.email, subject, html)

    @staticmethod
    def send_password_change_notification(user):
        """Sends a notification that the password was changed."""
        subject = "Your IMFQ Password Was Changed"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2563eb;">Security Notification</h2>
            <p>Hello {user.username},</p>
            <p>This is a formal notification that the password for your IMFQ account was successfully changed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.</p>
            <p><strong>If you did not perform this action, please contact your organization administrator or IMFQ support immediately to secure your account.</strong></p>
            <p>If you did change your password, you can safely ignore this email.</p>
            <hr style="border: 0; border-top: 1px solid #e5e7eb; margin: 30px 0;">
            <p style="color: #6b7280; font-size: 14px;">&copy; {datetime.now().year} IMFQ Enterprise. All rights reserved.</p>
        </div>
        """
        return EmailUtils.send_email(user.email, subject, html)

    @staticmethod
    def send_reset_password_email(user):
        """Sends a password reset link."""
        token = EmailUtils.generate_token()
        user.reset_token = token
        user.token_expiry = datetime.utcnow() + timedelta(hours=1)
        
        # Use APP_URL for external access
        app_url = EmailUtils._get_app_url()
        reset_url = f"{app_url}/reset-password.html?token={token}"
        
        subject = "Reset Your IMFQ Password"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2563eb;">Password Reset Request</h2>
            <p>Hello {user.username},</p>
            <p>We received a request to reset the password for your IMFQ account. Click the button below to set a new password:</p>
            <div style="margin: 30px 0;">
                <a href="{reset_url}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">Reset Password</a>
            </div>
            <p>If the button doesn't work, copy and paste this link into your browser:</p>
            <p>{reset_url}</p>
            <p><strong>This link will expire in 1 hour.</strong></p>
            <p>If you didn't request a password reset, please ignore this email; no changes will be made to your account.</p>
            <hr style="border: 0; border-top: 1px solid #e5e7eb; margin: 30px 0;">
            <p style="color: #6b7280; font-size: 14px;">&copy; {datetime.now().year} IMFQ Enterprise. All rights reserved.</p>
        </div>
        """
        return EmailUtils.send_email(user.email, subject, html)
    @staticmethod
    def send_otp_email(user, otp):
        """Sends a 6-digit OTP for password change."""
        subject = "Your Password Change OTP - IMFQ"
        html_content = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
            <h2 style="color: #2563eb;">Password Change Request</h2>
            <p>You are requesting to change your password for your IMFQ account.</p>
            <p>Please use the following 6-digit One-Time Password (OTP) to proceed:</p>
            <div style="background: #f3f4f6; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 5px; border-radius: 5px; margin: 20px 0;">
                {otp}
            </div>
            <p>This code will expire in 10 minutes.</p>
            <p>If you did not request this change, please ignore this email or contact support.</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="font-size: 12px; color: #6b7280;">This is an automated message, please do not reply.</p>
        </div>
        """
        return EmailUtils.send_email(user.email, subject, html_content)
