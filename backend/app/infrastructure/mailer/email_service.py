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
    def construct_sender_email(base_sender, email_type='general', org_id=None):
        """
        Dynamically fetch the sender email address directly from the Contact Directory field.
        No email address or domain is hardcoded — it reads whatever value the user types into the UI fields.
        """
        try:
            from app.domain.services.document_branding_service import DocumentBrandingService
            ctx = DocumentBrandingService.get_branding_context(org_id)
        except Exception:
            ctx = {}

        type_key_map = {
            'otp': 'otp_email',
            'security': 'otp_email',
            'auth': 'otp_email',
            'contact': 'contact_email',
            'alerts': 'alerts_email',
            'feedback': 'feedback_email',
            'onboarding': 'onboarding_email',
            'welcome': 'onboarding_email',
            'support': 'support_email',
            'billing': 'billing_email',
            'general': 'general_email',
            'announcement': 'general_email'
        }
        
        contact_field = type_key_map.get(email_type, 'general_email')
        val_from_field = (ctx.get(contact_field) or '').strip()

        # Extract local prefix from Contact Directory field (e.g. 'onboarding' from 'onboarding@' or 'onboarding@qcms.com')
        if val_from_field and '@' in val_from_field:
            prefix = val_from_field.split('@')[0].strip()
        elif val_from_field:
            prefix = val_from_field.strip()
        else:
            prefix = 'onboarding' if email_type in ['onboarding', 'welcome'] else 'noreplay'

        # Extract verified domain from Integration Hub base_sender (e.g. 'ifqm.org.in' from 'noreplay@ifqm.org.in')
        clean_base = (base_sender or '').strip()
        if "<" in clean_base and ">" in clean_base:
            clean_base = clean_base.split("<")[1].split(">")[0].strip()

        if '@' in clean_base:
            domain = clean_base.split("@")[-1].strip()
        else:
            domain = clean_base

        if not prefix:
            prefix = 'onboarding' if email_type in ['onboarding', 'welcome'] else 'noreplay'

        if domain:
            return f"{prefix}@{domain}"
        return val_from_field or clean_base

    @staticmethod
    def construct_sender_name(base_sender_name, email_type='general', org_id=None):
        """
        Dynamically fetch the Sender Display Label directly from the Contact Directory field for this email_type.
        If the user typed a Sender Display Label in Contact Directory (e.g. 'IFQM OTP Verification' for otp_email),
        use that display label as the email header sender name!
        """
        try:
            from app.domain.services.document_branding_service import DocumentBrandingService
            ctx = DocumentBrandingService.get_branding_context(org_id)
        except Exception:
            ctx = {}

        type_sender_name_map = {
            'otp': 'otp_sender_name',
            'security': 'otp_sender_name',
            'auth': 'otp_sender_name',
            'contact': 'contact_sender_name',
            'alerts': 'alerts_sender_name',
            'feedback': 'feedback_sender_name',
            'onboarding': 'onboarding_sender_name',
            'welcome': 'onboarding_sender_name',
            'support': 'support_sender_name',
            'billing': 'billing_sender_name',
            'general': 'general_sender_name',
            'announcement': 'general_sender_name'
        }

        sender_field = type_sender_name_map.get(email_type, 'general_sender_name')
        val_from_field = (ctx.get(sender_field) or '').strip()

        if val_from_field:
            return val_from_field

        # Fallback to Integration Hub sender_name or software display name
        if base_sender_name and base_sender_name.strip():
            return base_sender_name.strip()

        return ctx.get('software_display_name') or ctx.get('software_name') or 'QCMS Notifications'

    @staticmethod
    def send_email(to_email, subject, html_content, provider_override=None, email_type='general', org_id=None, sender_email=None, sender_name=None, reply_to=None, attachments=None):
        """Sends an email using the active connected integration provider (ZeptoMail or Resend) from the database."""
        import requests
        import base64
        from app.infrastructure.database.models.models import IntegrationConfig

        provider_type, settings = None, {}
        try:
            query = IntegrationConfig.query.filter(
                IntegrationConfig.category == 'Communication',
                IntegrationConfig.status == 'Connected',
                IntegrationConfig.provider_id.in_(['zeptomail', 'resend'])
            )
            if provider_override:
                override_cfg = query.filter(IntegrationConfig.provider_id == provider_override).first()
                if not override_cfg:
                    override_cfg = IntegrationConfig.query.filter_by(provider_id=provider_override).first()
                if override_cfg and override_cfg.settings:
                    provider_type = override_cfg.provider_id
                    settings = override_cfg.settings

            if not provider_type:
                configs = query.all()
                for cfg in configs:
                    s = cfg.settings or {}
                    if cfg.provider_id == 'zeptomail' and (s.get('api_key') or s.get('sender_email')):
                        provider_type, settings = 'zeptomail', s
                        break
                    elif cfg.provider_id == 'resend' and (s.get('api_key') or s.get('sender_email')):
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
            elif provider_override:
                provider_type = provider_override
                settings = {
                    'sender_email': os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev"),
                    'sender_name': 'QCMS Enterprise Broadcast'
                }

        if not provider_type:
            print("[QCMS] Error: No active connected email integration provider (ZeptoMail/Resend) found.")
            return None

        # Determine dynamic sender email & sender display name directly from Contact Directory field & Integration Hub
        cfg_sender = settings.get('sender_email') or ''
        cfg_sender_name = settings.get('sender_name') or ''

        # Extract verified domain from Integration Hub (Verified Sender Email Address)
        clean_base = (cfg_sender or '').strip()
        if "<" in clean_base and ">" in clean_base:
            clean_base = clean_base.split("<")[1].split(">")[0].strip()
        if '@' in clean_base:
            verified_domain = clean_base.split("@")[-1].strip()
        else:
            verified_domain = clean_base

        if sender_email and ('@' in str(sender_email)):
            local_prefix = str(sender_email).split('@')[0].strip()
            if verified_domain:
                clean_from = f"{local_prefix}@{verified_domain}"
            else:
                clean_from = str(sender_email).strip()
        elif sender_email and str(sender_email).strip():
            local_prefix = str(sender_email).strip()
            if verified_domain:
                clean_from = f"{local_prefix}@{verified_domain}"
            else:
                clean_from = local_prefix
        else:
            clean_from = EmailUtils.construct_sender_email(cfg_sender, email_type=email_type, org_id=org_id)

        if not sender_name:
            sender_name = EmailUtils.construct_sender_name(cfg_sender_name, email_type=email_type, org_id=org_id)

        if "<" in str(clean_from) and ">" in str(clean_from):
            clean_from = str(clean_from).split("<")[1].split(">")[0]

        is_dev = os.getenv("FLASK_ENV") == "development"

        # Log email dispatch in development/console
        if is_dev:
            try:
                print("\n" + "="*50)
                print(f"DEVELOPMENT MODE: EMAIL SENT VIA {provider_type.upper()}")
                print(f"FROM: {sender_name} <{clean_from}>")
                print(f"TO: {to_email}")
                print(f"SUBJECT: {subject}".encode('ascii', errors='replace').decode('ascii'))
                if reply_to:
                    print(f"REPLY-TO: {reply_to}")
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

                print("EMAIL CONTENT (Truncated preview):")
                print(html_content[:300].encode('ascii', errors='replace').decode('ascii'))
                print("="*50 + "\n")
            except Exception:
                pass

        # Real Email Dispatch
        try:
            if provider_type == 'zeptomail':
                raw_url = (settings.get('api_url') or 'https://api.zeptomail.in/v1.1/email').rstrip('/')
                if raw_url.endswith('/send'):
                    raw_url = raw_url[:-5]
                api_url = raw_url

                api_key = (settings.get('api_key') or '').strip()
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
                if reply_to:
                    payload["reply_to"] = [{"address": reply_to, "name": sender_name}]

                if attachments:
                    payload["attachments"] = []
                    for att in attachments:
                        att_content = att.get("content", b"")
                        if isinstance(att_content, bytes):
                            att_base64 = base64.b64encode(att_content).decode("utf-8")
                        else:
                            att_base64 = str(att_content)
                        payload["attachments"].append({
                            "content": att_base64,
                            "mime_type": att.get("mime_type", att.get("type", "application/pdf")),
                            "name": att.get("filename", att.get("name", "Official_Invoice.pdf"))
                        })

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
                    if is_dev:
                        return {"id": "dev_mode_dummy_id", "status": "simulated"}
                    return None

            elif provider_type == 'resend':
                resend.api_key = settings.get('api_key')
                params = {
                    "from": f"{sender_name} <{clean_from}>",
                    "to": [to_email],
                    "subject": subject,
                    "html": html_content,
                }
                if reply_to:
                    params["reply_to"] = reply_to

                if attachments:
                    params["attachments"] = []
                    for att in attachments:
                        att_content = att.get("content", b"")
                        if isinstance(att_content, bytes):
                            att_base64 = base64.b64encode(att_content).decode("utf-8")
                        else:
                            att_base64 = str(att_content)
                        params["attachments"].append({
                            "content": att_base64,
                            "filename": att.get("filename", att.get("name", "Official_Invoice.pdf"))
                        })

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
        return EmailUtils.send_email(user.email, subject, html, email_type='otp', org_id=user.org_id)

    @staticmethod
    def send_temp_password_email(user, temp_password):
        """Sends an email with a temporary password to a newly created user using the Email Notification Rule from DB if available."""
        from sqlalchemy import or_
        from app.infrastructure.database.models.models import EmailNotificationRule
        from app.domain.services.email_notification_engine import EmailNotificationEngine

        branding_ctx = DocumentBrandingService.get_branding_context(user.org_id)
        org_name = user.organization.name if user.organization else branding_ctx.get('organization_name', 'QCMS Enterprise')
        user_name = user.full_name or user.username or user.email
        role_name = user.role.name if user.role else 'User'

        user_ctx = {
            'user_name': user_name,
            'username': user.username or user.email,
            'user_email': user.email,
            'email': user.email,
            'temp_password': temp_password,
            'password': temp_password,
            'org_name': org_name,
            'role_name': role_name,
            'assigned_role': role_name,
            'app_url': EmailUtils._get_app_url(),
            'software_name': branding_ctx.get('software_name', 'QCMS Enterprise OS'),
            'software_short_name': branding_ctx.get('software_short_name', 'QCMS'),
            'support_email': branding_ctx.get('support_email', 'support@ifqm.org.in')
        }

        try:
            # STRICT GATE: Look up the welcome rule for new_user_welcome / user_welcome regardless of active state.
            # If rule exists and toggle is OFF (is_active == False), IMMEDIATELY CANCEL & RETURN FALSE — do NOT send any email!
            rule = EmailNotificationRule.query.filter(
                or_(
                    EmailNotificationRule.event_trigger == 'new_user_welcome',
                    EmailNotificationRule.category == 'user_welcome'
                )
            ).first()

            if rule:
                if not rule.is_active:
                    print(f"[EmailUtils] User welcome notification rule '{rule.name}' is PAUSED/DISABLED in Set Email Notifications dashboard. Cancelling email generation and dispatch completely.")
                    return False

                rule_dict = rule.to_dict()
                subject = EmailNotificationEngine.replace_variables(rule.subject, user_ctx)
                html = EmailNotificationEngine.generate_html_email(rule_dict, user_ctx)
                branding_sender = EmailNotificationEngine.get_sender_from_branding(rule.category)
                sender_email = rule.sender_email if (rule.sender_email and not rule.sender_email.endswith('@qcms.com')) else branding_sender['email']
                sender_name = rule.sender_name if (rule.sender_name and not rule.sender_name.startswith('QCMS ')) else branding_sender['name']
                reply_to = rule.reply_to if (rule.reply_to and not rule.reply_to.endswith('@qcms.com')) else branding_sender['reply_to']
                return EmailUtils.send_email(user.email, subject, html, sender_email=sender_email, sender_name=sender_name, reply_to=reply_to, email_type='onboarding', org_id=user.org_id)
        except Exception as e:
            print(f"[EmailUtils] Error loading custom welcome email rule: {e}")

        # Fallback to default template if no rule is found
        subject = f"Your {branding_ctx.get('software_short_name', 'QCMS')} Account Credentials"
        body = f"""
            <h2 style="color: #2563eb; margin-top:0;">Welcome to the Team!</h2>
            <p>Hello {user_name},</p>
            <p>An account has been created for you at {branding_ctx.get('software_name', 'QCMS Enterprise OS')} for <strong>{org_name}</strong>.</p>
            <div style="background-color: #f8fafc; border:1px solid #e2e8f0; padding: 16px; border-radius: 6px; margin: 20px 0;">
                <p style="margin: 0;"><strong>Username:</strong> {user.email or user.username}</p>
                <p style="margin: 10px 0 0 0;"><strong>Temporary Password:</strong> <code style="background-color: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-family:monospace;">{temp_password}</code></p>
            </div>
            <p>Please log in and change your password immediately upon your first sign-in.</p>
            <div style="margin: 25px 0;">
                <a href="{EmailUtils._get_app_url()}/login.html" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display:inline-block;">Log In Now</a>
            </div>
        """
        html = DocumentBrandingService.wrap_email_html(body, title="Account Credentials", org_id=user.org_id)
        return EmailUtils.send_email(user.email, subject, html, email_type='onboarding', org_id=user.org_id)

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
        return EmailUtils.send_email(user.email, subject, html, email_type='security', org_id=user.org_id)

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
        return EmailUtils.send_email(user.email, subject, html, email_type='otp', org_id=user.org_id)

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
        return EmailUtils.send_email(email, subject, html, email_type='otp')

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
            <p style="color: #64748b; font-size: 13px; text-align: center;">This code will expire in <strong>10 minutes</strong>. If you did not request this code, please contact <a href="mailto:{ctx.get('otp_email', 'otp-auth@qcms.com')}">{ctx.get('otp_email', 'otp-auth@qcms.com')}</a> immediately.</p>
        """
        html = DocumentBrandingService.wrap_email_html(body, title="Security OTP", org_id=org_id)
        return EmailUtils.send_email(user.email, subject, html, email_type='otp', org_id=org_id)
