import logging
logger = logging.getLogger('qcms.email_service')
import resend
import os
import secrets
import re
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from flask import current_app
from app import db
from app.domain.services.document_branding_service import DocumentBrandingService

# Global dedicated thread pool for non-blocking asynchronous email processing
email_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="qcms_email_worker")


# Email Utility to handle all system notifications
class EmailUtils:
    @staticmethod
    def _get_app_url():
        """Returns the base app URL formatted correctly."""
        url = os.getenv("APP_URL", "http://localhost:5000")
        return url.rstrip("/")

    @staticmethod
    def is_email_integration_connected(provider_override=None):
        """
        Checks whether an active, connected email integration provider (ZeptoMail or Resend)
        is enabled in the Integration Hub database.
        Returns (is_connected, provider_type, settings).
        """
        try:
            from app.infrastructure.database.models.models import IntegrationConfig
            query = IntegrationConfig.query.filter(
                IntegrationConfig.category == 'Communication',
                IntegrationConfig.provider_id.in_(['zeptomail', 'resend'])
            )
            configs = query.all()
            if not configs:
                # If no IntegrationConfig records exist at all in DB, check env vars as bootstrap fallback
                resend_key = os.getenv("RESEND_API_KEY")
                if resend_key:
                    return True, 'resend', {
                        'api_key': resend_key,
                        'sender_email': os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev"),
                        'sender_name': "QCMS Notifications"
                    }
                return False, None, {}

            # Strict check: only providers with status == 'Connected' and (settings.is_active is not False) are active
            connected_configs = [
                c for c in configs 
                if c.status == 'Connected' and (c.settings or {}).get('is_active', True) is not False
            ]

            if provider_override:
                match = next((c for c in connected_configs if c.provider_id == provider_override), None)
                if match:
                    return True, match.provider_id, match.settings or {}
                return False, None, {}

            for cfg in connected_configs:
                s = cfg.settings or {}
                if cfg.provider_id == 'zeptomail' and (s.get('api_key') or s.get('sender_email')):
                    return True, 'zeptomail', s
                elif cfg.provider_id == 'resend' and (s.get('api_key') or s.get('sender_email')):
                    return True, 'resend', s

            # If configs exist in DB but all are Disconnected/Disabled, email integrations are OFF!
            return False, None, {}
        except Exception as e:
            if current_app:
                current_app.logger.warning(f"Could not check email integration status: {e}")
            return False, None, {}

    @staticmethod
    def send_email_async(to_email, subject, html_content, provider_override=None, email_type='general', org_id=None, sender_email=None, sender_name=None, reply_to=None, attachments=None, app=None):
        """Dispatches an email asynchronously via Celery distributed task queue (with in-process fallback)."""
        if not to_email or not str(to_email).strip() or str(to_email).strip().lower() in ('none', 'null', ''):
            logger.info("[QCMS Email] Skipping email dispatch: recipient address is None or empty.")
            return False

        # Check if email integration is connected before scheduling async work
        is_conn, _, _ = EmailUtils.is_email_integration_connected(provider_override=provider_override)
        if not is_conn:
            logger.info(f"[QCMS Email] Skipping email dispatch to {to_email}: All email integrations (Resend/ZeptoMail) are Disconnected in Integration Hub.")
            return False

        # 1. Try Celery distributed worker dispatch ONLY if Redis is connected
        from app.infrastructure.cache.redis_adapter import cache
        if not attachments and not provider_override and cache.is_redis:
            try:
                from app.infrastructure.tasks.email_tasks import send_async_email
                send_async_email.delay(
                    recipient=to_email,
                    subject=subject,
                    html_body=html_content,
                    sender_name=sender_name,
                    org_id=org_id
                )
                return True
            except Exception as celery_err:
                logger.warning(f"[Celery Dispatch Failed, using thread pool]: {celery_err}")

        # 2. In-process fallback or attachment handling
        if not app:
            try:
                app = current_app._get_current_object()
            except Exception:
                app = None

        def _async_worker(target_app):
            try:
                if target_app:
                    with target_app.app_context():
                        try:
                            EmailUtils.send_email(
                                to_email=to_email,
                                subject=subject,
                                html_content=html_content,
                                provider_override=provider_override,
                                email_type=email_type,
                                org_id=org_id,
                                sender_email=sender_email,
                                sender_name=sender_name,
                                reply_to=reply_to,
                                attachments=attachments
                            )
                        except Exception as err:
                            target_app.logger.error(f"[AsyncEmail] Error sending background email to {to_email}: {err}")
                else:
                    try:
                        EmailUtils.send_email(
                            to_email=to_email,
                            subject=subject,
                            html_content=html_content,
                            provider_override=provider_override,
                            email_type=email_type,
                            org_id=org_id,
                            sender_email=sender_email,
                            sender_name=sender_name,
                            reply_to=reply_to,
                            attachments=attachments
                        )
                    except Exception as err:
                        logger.info(f"[AsyncEmail] Error sending background email to {to_email}: {err}")
            finally:
                try:
                    from app import db
                    db.session.remove()
                except Exception:
                    pass

        email_executor.submit(_async_worker, app)
        return True

    @staticmethod
    def send_bulk_welcome_emails_async(user_credentials_list, app=None):
        """
        Asynchronously sends welcome/credentials emails for a batch of newly imported users in the background.
        user_credentials_list format: [{'user_id': 123, 'temp_password': 'xyz'}, ...]
        """
        if not app:
            try:
                app = current_app._get_current_object()
            except Exception:
                app = None

        def _process_single_credential(target_app, item):
            try:
                if target_app:
                    with target_app.app_context():
                        from app.infrastructure.database.models.models import User, db
                        try:
                            user_id = item.get('user_id')
                            temp_pass = item.get('temp_password')
                            user = db.session.get(User, user_id) if user_id else item.get('user')
                            if user:
                                EmailUtils.send_temp_password_email(user, temp_pass)
                        except Exception as err:
                            target_app.logger.error(f"[BulkEmail] Error in async welcome notification for user {item.get('user_id')}: {err}")
                else:
                    try:
                        user = item.get('user')
                        temp_pass = item.get('temp_password')
                        if user:
                            EmailUtils.send_temp_password_email(user, temp_pass)
                    except Exception as err:
                        logger.info(f"[BulkEmail] Error in async welcome notification: {err}")
            finally:
                try:
                    from app import db
                    db.session.remove()
                except Exception:
                    pass

        for item in user_credentials_list:
            email_executor.submit(_process_single_credential, app, item)
        return True

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
        if not to_email or not str(to_email).strip() or str(to_email).strip().lower() in ('none', 'null', ''):
            logger.info("[QCMS Email] Skipping send_email: recipient address is None or empty.")
            return None

        import requests
        import base64

        is_connected, provider_type, settings = EmailUtils.is_email_integration_connected(provider_override=provider_override)

        if not is_connected or not provider_type:
            logger.info(f"[QCMS Email] Skipping email dispatch to {to_email}: Email integrations (Resend/ZeptoMail) are Disconnected in Integration Hub.")
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
                logger.info("\n" + "="*50)
                logger.info(f"DEVELOPMENT MODE: EMAIL SENT VIA {provider_type.upper()}")
                logger.info(f"FROM: {sender_name} <{clean_from}>")
                logger.info(f"TO: {to_email}")
                logger.info(f"SUBJECT: {subject}".encode('ascii', errors='replace').decode('ascii'))
                if reply_to:
                    logger.info(f"REPLY-TO: {reply_to}")
                logger.info("-" * 50)

                otp_match = re.search(r'>\s*(\d{6})\s*<', html_content)
                if otp_match:
                    logger.info(f"OTP CODE: {otp_match.group(1)}")

                links = re.findall(r'href="([^"]+)"', html_content)
                if links:
                    logger.info("EXTRACTED LINKS:")
                    for link in links:
                        logger.info(f"  - {link}")
                    logger.info("-" * 50)

                logger.info("EMAIL CONTENT (Truncated preview):")
                logger.info(html_content[:300].encode('ascii', errors='replace').decode('ascii'))
                logger.info("="*50 + "\n")
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
                    else: logger.info(error_msg)
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
            else: logger.info(error_msg)
            if is_dev: return {"id": "dev_mode_dummy_id"}
            return None

    @staticmethod
    def generate_token():
        """Generates a secure random token."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def send_verification_email(user, is_async=True):
        """Sends an email verification link to the user."""
        token = EmailUtils.generate_token()
        user.verification_token = token
        user.token_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=24)
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
        if is_async:
            return EmailUtils.send_email_async(user.email, subject, html, email_type='otp', org_id=user.org_id)
        return EmailUtils.send_email(user.email, subject, html, email_type='otp', org_id=user.org_id)

    @staticmethod
    def get_user_login_identifier(user):
        """
        Determines the primary login identifier to present to the user:
        1. If the organization allows email login ('email' in org.login_options) AND user.email is present -> return user.email
        2. Otherwise (or if user has no email) -> return user.phone (or user.mobile / user.phone_number)
        3. If phone is not present -> fallback to user.email or user.username
        """
        if not user:
            return ""

        org = getattr(user, 'organization', None)
        org_login_opts = (org.login_options or ["phone", "email"]) if org else ["phone", "email"]
        if not isinstance(org_login_opts, list):
            org_login_opts = ["phone", "email"]

        user_email = (getattr(user, 'email', None) or '').strip()
        user_phone = (getattr(user, 'phone', None) or getattr(user, 'mobile', None) or getattr(user, 'phone_number', None) or '').strip()

        # If email login is enabled for this organization and user has an email:
        if "email" in org_login_opts and user_email:
            return user_email

        # Otherwise, default to phone number:
        if user_phone:
            return user_phone

        # If phone is not available, fall back to email:
        if user_email:
            return user_email

        return getattr(user, 'username', '')

    @staticmethod
    def send_temp_password_email(user, temp_password, is_async=False):
        """Sends an email with a temporary password to a newly created user using the Email Notification Rule from DB if available."""
        from sqlalchemy import or_
        from app.infrastructure.database.models.models import EmailNotificationRule
        from app.domain.services.email_notification_engine import EmailNotificationEngine

        branding_ctx = DocumentBrandingService.get_branding_context(user.org_id)
        org_name = user.organization.name if user.organization else branding_ctx.get('organization_name', 'QCMS Enterprise')
        user_name = user.full_name or user.username or user.email
        role_name = user.role.name if user.role else 'User'
        user_phone = getattr(user, 'phone', None) or getattr(user, 'mobile', None) or getattr(user, 'phone_number', None) or ''
        login_identifier = EmailUtils.get_user_login_identifier(user)

        user_ctx = {
            'user_name': user_name,
            'username': login_identifier,
            'login_identifier': login_identifier,
            'user_email': user.email,
            'email': user.email,
            'phone': user_phone,
            'phone_number': user_phone,
            'temp_password': temp_password,
            'password': temp_password,
            'Password': temp_password,
            'default_password': temp_password,
            'temporary_password': temp_password,
            'org_name': org_name,
            'role_name': role_name,
            'assigned_role': role_name,
            'app_url': EmailUtils._get_app_url(),
            'software_name': branding_ctx.get('software_name', 'QCMS Enterprise OS'),
            'software_short_name': branding_ctx.get('software_short_name', 'QCMS'),
            'support_email': branding_ctx.get('support_email', 'support@ifqm.org.in')
        }

        # 1. Dispatch Welcome SMS from Set SMS Notifications (SmsTemplateConfig)
        from app.infrastructure.database.models.models import SmsTemplateConfig, SmsNotificationLog
        user_phone = getattr(user, 'phone', None) or getattr(user, 'mobile', None) or getattr(user, 'phone_number', None)
        if user_phone:
            try:
                sms_tmpl = SmsTemplateConfig.query.filter_by(template_key='user_welcome_credentials', is_active=True).first()
                if not sms_tmpl:
                    sms_tmpl = SmsTemplateConfig.query.filter_by(template_key='user_welcome_credentials').first()

                if sms_tmpl and (sms_tmpl.is_active is not False) and sms_tmpl.body:
                    sms_body = EmailNotificationEngine.replace_variables(sms_tmpl.body, user_ctx)
                    sms_ok, sms_msg = EmailNotificationEngine.dispatch_dlt_sms(
                        phone=user_phone,
                        sms_body=sms_body,
                        template_id=sms_tmpl.template_id,
                        entity_id=sms_tmpl.entity_id,
                        sender_id=sms_tmpl.sender_id,
                        msg_type="TXN"
                    )
                    sms_log = SmsNotificationLog(
                        template_key=sms_tmpl.template_key,
                        template_name=sms_tmpl.display_name,
                        category=sms_tmpl.category or 'auth',
                        sender_id=sms_tmpl.sender_id or 'IFQMQC',
                        dlt_template_id=sms_tmpl.template_id,
                        dlt_entity_id=sms_tmpl.entity_id,
                        message_body=sms_body,
                        phone_number=user_phone,
                        recipient_name=user_name,
                        org_name=org_name,
                        gateway='Jio DLT / Kaleyra' if sms_ok else 'Jio DLT / Simulated',
                        status='Delivered' if sms_ok else 'Logged',
                        error_message=None if sms_ok else sms_msg,
                        sent_by_id=user.id,
                        sent_at=datetime.now(timezone.utc).replace(tzinfo=None)
                    )
                    db.session.add(sms_log)
                    if sms_ok:
                        sms_tmpl.total_sent = (sms_tmpl.total_sent or 0) + 1
                        sms_tmpl.last_triggered_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    db.session.commit()
            except Exception as se:
                db.session.rollback()
                logger.info(f"[EmailUtils] Error dispatching user welcome SMS: {se}")

        if not user.email:
            return True

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
                    logger.info(f"[EmailUtils] User welcome notification rule '{rule.name}' is PAUSED/DISABLED in Set Email Notifications dashboard. Cancelling email generation and dispatch completely.")
                    return False

                # Dispatch SMS alongside email if enabled on the rule and not already sent
                if rule.sms_enabled and rule.sms_body and user_phone and not sms_tmpl:
                    try:
                        p_sms_body = EmailNotificationEngine.replace_variables(rule.sms_body, user_ctx)
                        EmailNotificationEngine.dispatch_dlt_sms(
                            user_phone,
                            p_sms_body,
                            template_id=rule.sms_template_id,
                            entity_id=rule.sms_entity_id,
                            sender_id=rule.sms_sender_id
                        )
                    except Exception as se:
                        logger.info(f"[EmailUtils] Error dispatching user welcome SMS: {se}")

                rule_dict = rule.to_dict()
                subject = EmailNotificationEngine.replace_variables(rule.subject, user_ctx)
                html = EmailNotificationEngine.generate_html_email(rule_dict, user_ctx)
                branding_sender = EmailNotificationEngine.get_sender_from_branding(rule.category)
                sender_email = rule.sender_email if (rule.sender_email and not rule.sender_email.endswith('@qcms.com')) else branding_sender['email']
                sender_name = rule.sender_name if (rule.sender_name and not rule.sender_name.startswith('QCMS ')) else branding_sender['name']
                reply_to = rule.reply_to if (rule.reply_to and not rule.reply_to.endswith('@qcms.com')) else branding_sender['reply_to']
                if is_async:
                    return EmailUtils.send_email_async(user.email, subject, html, sender_email=sender_email, sender_name=sender_name, reply_to=reply_to, email_type='onboarding', org_id=user.org_id)
                return EmailUtils.send_email(user.email, subject, html, sender_email=sender_email, sender_name=sender_name, reply_to=reply_to, email_type='onboarding', org_id=user.org_id)
        except Exception as e:
            logger.info(f"[EmailUtils] Error loading custom welcome email rule: {e}")

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
        if is_async:
            return EmailUtils.send_email_async(user.email, subject, html, email_type='onboarding', org_id=user.org_id)
        return EmailUtils.send_email(user.email, subject, html, email_type='onboarding', org_id=user.org_id)

    @staticmethod
    def send_password_change_notification(user, is_async=True):
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
        if is_async:
            return EmailUtils.send_email_async(user.email, subject, html, email_type='security', org_id=user.org_id)
        return EmailUtils.send_email(user.email, subject, html, email_type='security', org_id=user.org_id)

    @staticmethod
    def send_reset_password_email(user, is_async=True):
        """Sends a password reset link."""
        token = EmailUtils.generate_token()
        user.reset_token = token
        user.token_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
        
        app_url = EmailUtils._get_app_url()
        reset_url = f"{app_url}/auth/reset-password.html?token={token}"
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
        if is_async:
            return EmailUtils.send_email_async(user.email, subject, html, email_type='otp', org_id=user.org_id)
        return EmailUtils.send_email(user.email, subject, html, email_type='otp', org_id=user.org_id)

    @staticmethod
    def send_password_reset_otp_email(user, otp, is_async=True):
        """Sends a Password Reset OTP verification email using active template configuration."""
        try:
            from app.domain.services.email_notification_engine import EmailNotificationEngine
            return EmailNotificationEngine.trigger_password_reset_otp_notification(user, otp)
        except Exception as e:
            logger.error(f"[EmailUtils] Error in send_password_reset_otp_email: {e}")
            org_id = getattr(user, 'org_id', None)
            ctx = DocumentBrandingService.get_branding_context(org_id)
            subject = f"Your Password Reset OTP Code - {ctx['software_name']}"
            body = f"""
                <h2 style="color: #2563eb; margin-top:0; text-align:center;">Password Reset Verification</h2>
                <p>Hello {user.username or user.email},</p>
                <p>We received a request to reset your password. Use the verification code below to proceed:</p>
                <div style="background: #f8fafc; border: 2px dashed #cbd5e1; padding: 20px; text-align: center; margin: 25px 0; border-radius: 12px;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 10px; color: #1e40af; font-family: monospace;">{otp}</span>
                </div>
                <p style="color: #64748b; font-size: 13px; text-align: center;">This code will expire in <strong>10 minutes</strong>.</p>
            """
            html = DocumentBrandingService.wrap_email_html(body, title="Password Reset OTP", org_id=org_id)
            if is_async:
                return EmailUtils.send_email_async(user.email, subject, html, email_type='otp', org_id=org_id)
            return EmailUtils.send_email(user.email, subject, html, email_type='otp', org_id=org_id)


    @staticmethod
    def send_registration_otp(email, otp, is_async=True):
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
        if is_async:
            return EmailUtils.send_email_async(email, subject, html, email_type='otp')
        return EmailUtils.send_email(email, subject, html, email_type='otp')

    @staticmethod
    def send_otp_email(user, otp, is_async=True):
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
        if is_async:
            return EmailUtils.send_email_async(user.email, subject, html, email_type='otp', org_id=org_id)
        return EmailUtils.send_email(user.email, subject, html, email_type='otp', org_id=org_id)
