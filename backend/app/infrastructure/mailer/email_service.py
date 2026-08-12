import resend
import os
import secrets
import re
from datetime import datetime, timedelta
from flask import current_app
from app.domain.services.document_branding_service import DocumentBrandingService


# Email Utility to handle all system notifications
class EmailUtils:
    @staticmethod
    def _get_app_url():
        """Returns the base app URL formatted correctly."""
        url = os.getenv("APP_URL", "http://localhost:5000")
        return url.rstrip("/")

    @staticmethod
    def send_email(to_email, subject, html_content):
        """Sends an email using the active connected integration provider (ZeptoMail or Resend) from the database."""
        import requests
        from app.infrastructure.database.models.models import IntegrationConfig

        provider_type, settings = None, {}
        try:
            configs = IntegrationConfig.query.filter(
                IntegrationConfig.category == 'Communication',
                IntegrationConfig.status == 'Connected',
                IntegrationConfig.provider_id.in_(['zeptomail', 'resend'])
            ).all()

            for cfg in configs:
                s = cfg.settings or {}
                if cfg.provider_id == 'zeptomail' and s.get('api_key') and s.get('sender_email'):
                    provider_type, settings = 'zeptomail', s
                    break
                elif cfg.provider_id == 'resend' and s.get('api_key'):
                    provider_type, settings = 'resend', s
                    break
        except Exception as e:
            if current_app:
                current_app.logger.warning(f"Could not query integration config: {e}")

        # Fallback to env vars if no DB integration is active
        if not provider_type:
            resend_key = os.getenv("RESEND_API_KEY")
            if resend_key:
                provider_type = 'resend'
                settings = {
                    'api_key': resend_key,
                    'sender_email': os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev"),
                    'sender_name': "QCMS Notifications"
                }

        if not provider_type:
            print("[QCMS] Error: No active connected email integration provider (ZeptoMail/Resend) found.")
            return None

        # Determine sender email and name
        sender_email = settings.get('sender_email') or 'noreply@ifqm.org.in'
        sender_name = settings.get('sender_name') or 'QCMS Notifications'
        clean_from = sender_email
        if "<" in sender_email and ">" in sender_email:
            clean_from = sender_email.split("<")[1].split(">")[0]

        is_dev = os.getenv("FLASK_ENV") == "development"

        # Log email dispatch in development/console
        if is_dev:
            print("\n" + "="*50)
            print(f"DEVELOPMENT MODE: EMAIL SENT VIA {provider_type.upper()}")
            print(f"FROM: {sender_name} <{clean_from}>")
            print(f"TO: {to_email}")
            print(f"SUBJECT: {subject}")
            print("-" * 50)

            otp_match = re.search(r'>\s*(\d{6})\s*<', html_content)
            if otp_match:
                print(f"OTP CODE: {otp_match.group(1)}")

            links = re.findall(r'href="([^"]+)"', html_content)
            if links:
                print("EXTRACTED LINKS:")
                for link in links:
                    print(f"  - {link}")
                print("-" * 50)

            print("EMAIL CONTENT:")
            print(html_content)
            print("="*50 + "\n")

            if os.getenv("FORCE_REAL_EMAIL_IN_DEV", "false").lower() != "true":
                if current_app:
                    current_app.logger.info(f"Development mode: Skipped sending actual email via {provider_type} from {clean_from} to {to_email}")
                return {"id": "dev_mode_dummy_id"}

        # Real Email Dispatch
        try:
            if provider_type == 'zeptomail':
                api_url = settings.get('api_url') or 'https://api.zeptomail.in/v1.1/email/send'
                api_key = settings.get('api_key', '')
                auth_header = api_key if api_key.startswith("Zoho-enczapikey") else f"Zoho-enczapikey {api_key}"

                payload = {
                    "from": {
                        "address": clean_from,
                        "name": sender_name
                    },
                    "to": [
                        {
                            "email_address": {
                                "address": to_email
                            }
                        }
                    ],
                    "subject": subject,
                    "htmlbody": html_content
                }

                resp = requests.post(
                    api_url,
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    json=payload,
                    timeout=10
                )
                if resp.status_code in [200, 201]:
                    return resp.json()
                else:
                    error_msg = f"ZeptoMail API Error ({resp.status_code}): {resp.text}"
                    if current_app: current_app.logger.error(error_msg)
                    else: print(error_msg)
                    return None

            elif provider_type == 'resend':
                resend.api_key = settings.get('api_key')
                params = {
                    "from": f"{sender_name} <{clean_from}>",
                    "to": [to_email],
                    "subject": subject,
                    "html": html_content,
                }
                email = resend.Emails.send(params)
                return email
        except Exception as e:
            error_msg = f"Email Provider ({provider_type}) Error: {str(e)}"
            if current_app: current_app.logger.error(error_msg)
            else: print(error_msg)
            if is_dev: return {"id": "dev_mode_dummy_id"}
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
        app_url = EmailUtils._get_app_url()
        verify_url = f"{app_url}/api/auth/verify-email/{token}"
        ctx = DocumentBrandingService.get_branding_context(user.org_id)

        subject = f"Verify Your {ctx['software_short_name']} Account"
        body = f"""
            <h2 style="color: #2563eb; margin-top:0;">Welcome to {ctx['software_name']}!</h2>
            <p>Hello {user.username},</p>
            <p>Thank you for registering your organization with {ctx['software_name']}. Please verify your email address to activate your account:</p>
            <div style="margin: 25px 0;">
                <a href="{verify_url}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display:inline-block;">Verify Email Address</a>
            </div>
            <p style="font-size:13px; color:#64748b;">If the button doesn't work, copy and paste this link into your browser:<br><a href="{verify_url}">{verify_url}</a></p>
            <p style="font-size:13px; color:#64748b;">This link will expire in 24 hours.</p>
        """
        html = DocumentBrandingService.wrap_email_html(body, title="Account Verification", org_id=user.org_id)
        return EmailUtils.send_email(user.email, subject, html)

    @staticmethod
    def send_temp_password_email(user, temp_password):
        """Sends an email with a temporary password to a newly created user."""
        ctx = DocumentBrandingService.get_branding_context(user.org_id)
        subject = f"Your {ctx['software_short_name']} Account Credentials"
        body = f"""
            <h2 style="color: #2563eb; margin-top:0;">Welcome to the Team!</h2>
            <p>Hello {user.username or user.email},</p>
            <p>An account has been created for you at {ctx['software_name']} for <strong>{user.organization.name if user.organization else ctx['organization_name']}</strong>.</p>
            <div style="background-color: #f8fafc; border:1px solid #e2e8f0; padding: 16px; border-radius: 6px; margin: 20px 0;">
                <p style="margin: 0;"><strong>Username:</strong> {user.username}</p>
                <p style="margin: 10px 0 0 0;"><strong>Temporary Password:</strong> <code style="background-color: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-family:monospace;">{temp_password}</code></p>
            </div>
            <p>Please log in and change your password immediately upon your first sign-in.</p>
            <div style="margin: 25px 0;">
                <a href="{EmailUtils._get_app_url()}/login.html" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display:inline-block;">Log In Now</a>
            </div>
        """
        html = DocumentBrandingService.wrap_email_html(body, title="Account Credentials", org_id=user.org_id)
        return EmailUtils.send_email(user.email, subject, html)

    @staticmethod
    def send_password_change_notification(user):
        """Sends a notification that the password was changed."""
        ctx = DocumentBrandingService.get_branding_context(user.org_id)
        subject = f"Your {ctx['software_short_name']} Password Was Changed"
        body = f"""
            <h2 style="color: #2563eb; margin-top:0;">Security Notification</h2>
            <p>Hello {user.username},</p>
            <p>This is a formal notification that the password for your {ctx['software_name']} account was successfully changed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.</p>
            <p><strong>If you did not perform this action, please contact your organization administrator or <a href="mailto:{ctx['support_email']}">{ctx['support_email']}</a> immediately to secure your account.</strong></p>
        """
        html = DocumentBrandingService.wrap_email_html(body, title="Security Alert", org_id=user.org_id)
        return EmailUtils.send_email(user.email, subject, html)

    @staticmethod
    def send_reset_password_email(user):
        """Sends a password reset link."""
        token = EmailUtils.generate_token()
        user.reset_token = token
        user.token_expiry = datetime.utcnow() + timedelta(hours=1)
        
        app_url = EmailUtils._get_app_url()
        reset_url = f"{app_url}/reset-password.html?token={token}"
        ctx = DocumentBrandingService.get_branding_context(user.org_id)
        
        subject = f"Reset Your {ctx['software_short_name']} Password"
        body = f"""
            <h2 style="color: #2563eb; margin-top:0;">Password Reset Request</h2>
            <p>Hello {user.username},</p>
            <p>We received a request to reset the password for your {ctx['software_name']} account. Click the button below to set a new password:</p>
            <div style="margin: 25px 0;">
                <a href="{reset_url}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display:inline-block;">Reset Password</a>
            </div>
            <p style="font-size:13px; color:#64748b;">This link will expire in 1 hour.</p>
        """
        html = DocumentBrandingService.wrap_email_html(body, title="Password Reset", org_id=user.org_id)
        return EmailUtils.send_email(user.email, subject, html)

    @staticmethod
    def send_registration_otp(email, otp):
        """Sends a 6-digit OTP specifically for new organization registration."""
        ctx = DocumentBrandingService.get_branding_context(None)
        subject = f"Your {ctx['software_short_name']} Registration Verification Code"
        body = f"""
            <h2 style="color: #1e293b; margin-top:0; text-align:center;">Verify Your Work Email</h2>
            <p style="color: #334155; line-height: 1.6;">Thank you for choosing {ctx['software_name']}. To verify your email address and continue with the organization setup, please use the verification code below:</p>
            <div style="background: #f8fafc; border: 2px dashed #cbd5e1; padding: 20px; text-align: center; margin: 25px 0; border-radius: 12px;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 10px; color: #1e40af; font-family: monospace;">{otp}</span>
            </div>
            <p style="color: #64748b; font-size: 13px; text-align: center;">This code will expire in <strong>10 minutes</strong> for security reasons.</p>
        """
        html = DocumentBrandingService.wrap_email_html(body, title="Email Verification", org_id=None)
        return EmailUtils.send_email(email, subject, html)

    @staticmethod
    def send_otp_email(user, otp):
        """Sends a 2FA / Login OTP email to a user."""
        org_id = getattr(user, 'org_id', None)
        ctx = DocumentBrandingService.get_branding_context(org_id)
        subject = f"Your {ctx['software_short_name']} One-Time Verification Code"
        body = f"""
            <h2 style="color: #1e293b; margin-top:0; text-align:center;">Security Verification Code</h2>
            <p style="color: #334155; line-height: 1.6;">Hello {user.username or user.email},</p>
            <p style="color: #334155; line-height: 1.6;">Please use the verification code below to complete your sign-in to {ctx['software_name']}:</p>
            <div style="background: #f8fafc; border: 2px dashed #cbd5e1; padding: 20px; text-align: center; margin: 25px 0; border-radius: 12px;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 10px; color: #1e40af; font-family: monospace;">{otp}</span>
            </div>
            <p style="color: #64748b; font-size: 13px; text-align: center;">This code will expire in <strong>10 minutes</strong>.</p>
        """
        html = DocumentBrandingService.wrap_email_html(body, title="Security OTP", org_id=org_id)
        return EmailUtils.send_email(user.email, subject, html)
