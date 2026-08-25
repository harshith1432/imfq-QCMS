from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt, set_access_cookies, unset_jwt_cookies
from app.infrastructure.database.models.models import User, Role, Department, Organization, EmailVerification, PhoneVerification, SupportTicket, Notification, db
import random
import secrets
from app import bcrypt
from app.infrastructure.mailer.email_service import EmailUtils
from app.domain.services.subscription_service import SubscriptionManager
from datetime import timedelta, datetime, timezone
import os
import re
from werkzeug.utils import secure_filename
from app.utils.avatar_utils import get_profile_picture_url
from app.presentation.routes.error_helpers import internal_server_error

def _to_naive_utc(dt):
    if dt is None:
        return None
    if getattr(dt, 'tzinfo', None) is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'jfif', 'avif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


auth_bp = Blueprint('auth', __name__)

def get_platform_settings_safe():
    try:
        from app.infrastructure.database.models.models import PlatformSettings
        return PlatformSettings.query.order_by(PlatformSettings.id.asc()).first()
    except Exception as e:
        print(f"[QCMS Warning] PlatformSettings query error: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return None

def get_support_email_safe():
    try:
        from app.domain.services.document_branding_service import DocumentBrandingService
        branding_ctx = DocumentBrandingService.get_branding_context()
        if branding_ctx and branding_ctx.get('support_email'):
            return branding_ctx['support_email']
    except Exception:
        pass
        
    try:
        from app.infrastructure.database.models.models import CompanyContactsConfig
        cont = CompanyContactsConfig.query.filter_by(org_id=None).first()
        if cont and cont.support_email:
            return cont.support_email
    except Exception:
        pass

    try:
        from app.infrastructure.database.models.models import PlatformSettings
        ps = PlatformSettings.query.first()
        if ps and ps.support_email:
            return ps.support_email
    except Exception:
        pass

    return "support@ifqm.org.in"

@auth_bp.route('/registration-status', methods=['GET'])
def get_registration_status():
    settings = get_platform_settings_safe()
    is_open = bool(settings.registration_open) if (settings and settings.registration_open is not None) else True
    
    trial_plan_obj = SubscriptionManager.get_default_trial_plan()
    has_trial_plan = trial_plan_obj is not None
    support_email = get_support_email_safe()

    require_email_otp = getattr(settings, 'require_email_otp', True) if settings else True
    require_phone_otp = getattr(settings, 'require_phone_otp', False) if settings else False

    if not is_open:
        msg = "Self-service organization sign-up is currently disabled by the Super Admin."
    elif not has_trial_plan:
        msg = f"Something went wrong. Please contact the support team at {support_email}."
    else:
        msg = "Self-service organization sign-up is active"

    from app.domain.services.document_branding_service import DocumentBrandingService
    branding_ctx = DocumentBrandingService.get_branding_context(org_id=None)

    return jsonify({
        "status": "success",
        "registration_open": is_open and has_trial_plan,
        "is_open": is_open,
        "has_trial_plan": has_trial_plan,
        "trial_plan_name": trial_plan_obj.name if trial_plan_obj else None,
        "support_email": support_email,
        "require_email_otp": require_email_otp,
        "require_phone_otp": require_phone_otp,
        "branding": branding_ctx,
        "branding_context": branding_ctx,
        "message": msg
    }), 200

@auth_bp.route('/check-availability', methods=['POST'])
def check_availability():
    """Real-time validation for registration Step 1 (email, company_name) and Step 2 (username)."""
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    company_name = (data.get('company_name') or '').strip()
    username = (data.get('username') or '').strip().lower()

    from sqlalchemy import func

    if company_name:
        existing_org = Organization.query.filter(
            func.lower(Organization.name) == company_name.lower(),
            Organization.is_deleted == False
        ).first()
        if existing_org:
            return jsonify({
                "valid": False,
                "field": "company_name",
                "msg": "An organization with this company name already exists",
                "message": "An organization with this company name already exists"
            }), 200

    if email:
        existing_org_email = Organization.query.filter(
            func.lower(Organization.email) == email,
            Organization.is_deleted == False
        ).first()
        if existing_org_email:
            return jsonify({
                "valid": False,
                "field": "email",
                "msg": "An organization with this email address already exists",
                "message": "An organization with this email address already exists"
            }), 200

        existing_user_email = User.query.filter(
            func.lower(User.email) == email
        ).first()
        if existing_user_email:
            return jsonify({
                "valid": False,
                "field": "email",
                "msg": "A user with this email address already exists",
                "message": "A user with this email address already exists"
            }), 200

    if username:
        existing_username = User.query.filter(
            func.lower(User.username) == username
        ).first()
        if existing_username:
            return jsonify({
                "valid": False,
                "field": "username",
                "msg": "Username is already taken",
                "message": "Username is already taken"
            }), 200

    return jsonify({"valid": True, "msg": "Available", "message": "Available"}), 200

@auth_bp.route('/register-org', methods=['POST'])
def register_org():
    settings = get_platform_settings_safe()
    if settings:
        if not settings.registration_open:
            return jsonify({"msg": "Self-service organization sign-up is currently disabled by the Super Admin.", "message": "Self-service organization sign-up is currently disabled by the Super Admin."}), 403
        auth_settings = settings.authentication_settings or {}
        if auth_settings.get('native_email_enabled') is False:
            return jsonify({"msg": "Direct registration is disabled. Please use Single Sign-On (SSO)."}), 403

    from app.shared.validation import (
        ValidationError,
        sanitize_payload,
        validate_email,
        validate_string_length,
        validate_password
    )
    
    data = sanitize_payload(request.get_json() or {})
    
    try:
        email = validate_email(data.get('email'), "Email address")
        username = validate_string_length(data.get('username'), "Username", min_len=3, max_len=50)
        password = validate_password(data.get('password'), "Password")
        company_name = validate_string_length(data.get('company_name'), "Company Name", min_len=2, max_len=100)
    except ValidationError as ve:
        return jsonify({"msg": ve.message}), 400

    company_name_clean = company_name.strip()
    from sqlalchemy import func
    existing_org_name = Organization.query.filter(
        func.lower(Organization.name) == company_name_clean.lower(),
        Organization.is_deleted == False
    ).first()
    if existing_org_name:
        return jsonify({"msg": "An organization with this company name already exists", "message": "An organization with this company name already exists"}), 400

    email_clean = email.strip().lower()
    existing_org_email = Organization.query.filter(
        func.lower(Organization.email) == email_clean,
        Organization.is_deleted == False
    ).first()
    if existing_org_email:
        return jsonify({"msg": "An organization with this email address already exists", "message": "An organization with this email address already exists"}), 400
        
    if User.query.filter(func.lower(User.email) == email_clean).first():
        return jsonify({"msg": "A user with this email already exists"}), 400
        
    if User.query.filter(func.lower(User.username) == username.strip().lower()).first():
        return jsonify({"msg": "Username already taken"}), 400

    require_email_otp = getattr(settings, 'require_email_otp', True) if settings else True
    if require_email_otp:
        verification = EmailVerification.query.filter_by(email=email).first()
        if not verification or not verification.is_verified:
            return jsonify({"msg": "Email not verified. Please verify your email first."}), 400

    require_phone_otp = getattr(settings, 'require_phone_otp', False) if settings else False
    if require_phone_otp:
        phone_num = (data.get('phone') or '').strip()
        if not phone_num:
            return jsonify({"msg": "Phone number is required for OTP verification."}), 400
        phone_verif = PhoneVerification.query.filter_by(phone=phone_num).first()
        if not phone_verif or not phone_verif.is_verified:
            return jsonify({"msg": "Phone number not verified. Please verify your phone number via OTP first."}), 400
    
    # 1. Fetch Active Trial Plan & Support Email
    trial_plan_obj = SubscriptionManager.get_default_trial_plan()
    support_email = get_support_email_safe()

    # If NO active trial plan exists, reject organization registration with Support Email
    if not trial_plan_obj:
        err_msg = f"Something went wrong. Please contact the support team at {support_email}."
        return jsonify({
            "msg": err_msg,
            "message": err_msg,
            "support_email": support_email,
            "error_code": "NO_TRIAL_PLAN"
        }), 400

    # Auto-assign the active Trial Plan to the registering organization
    plan_name = trial_plan_obj.name
    plan_config = SubscriptionManager.get_plan_config(plan_name)
    if trial_plan_obj.limits:
        if trial_plan_obj.limits.max_users:
            plan_config['max_users'] = trial_plan_obj.limits.max_users
        if trial_plan_obj.limits.storage_limit_gb:
            plan_config['storage_limit_mb'] = trial_plan_obj.limits.storage_limit_gb * 1024.0

    trial_days = data.get('trial_days')
    if not trial_days and trial_plan_obj:
        trial_days = getattr(trial_plan_obj, 'trial_duration_days', None)
        if not trial_days and trial_plan_obj.pricing:
            import re
            for pr in trial_plan_obj.pricing:
                match = re.search(r'(\d+)', pr.billing_cycle or '')
                if match:
                    trial_days = int(match.group(1))
                    break
    if not trial_days:
        trial_days = 180
    
    trial_ends = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=int(trial_days))
    
    new_org = Organization(
        name=data.get('company_name'),
        industry=data.get('industry'),
        org_scale=data.get('org_scale', 'Small'),
        admin_name=data.get('admin_name'),
        email=email,
        phone=data.get('phone'),
        subscription_plan=plan_name,
        subscription_status='Trialing',
        trial_ends_at=trial_ends,
        max_users=plan_config.get('max_users', 50),
        storage_limit_mb=plan_config.get('storage_limit_mb', 5120.0),
        is_white_label=plan_config.get('white_label', False),
        multi_plant=plan_config.get('multi_plant', False),
        api_access=plan_config.get('api_access', False)
    )
    db.session.add(new_org)
    db.session.flush() # Get ID

    # Create associated Subscription record linked to trial_plan_obj
    try:
        import uuid
        sub_uid = f"SUB-{datetime.now(timezone.utc).replace(tzinfo=None).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        from app.infrastructure.database.models.models import Subscription
        new_sub = Subscription(
            org_id=new_org.id,
            subscription_uid=sub_uid,
            plan_name=plan_name,
            billing_cycle='Trial',
            subscription_status='Trial',
            payment_status='Paid',
            start_date=datetime.now(timezone.utc).replace(tzinfo=None),
            end_date=trial_ends,
            trial_start_date=datetime.now(timezone.utc).replace(tzinfo=None),
            trial_end_date=trial_ends,
            base_price=0.0,
            final_amount=0.0
        )
        db.session.add(new_sub)
    except Exception as se:
        print(f"[QCMS Warning] Failed to create Subscription entity for new org: {se}")

    # 2. Create Admin User
    admin_role = Role.query.filter_by(name='Admin').first()
    hashed_pw = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')
    
    admin_user = User(
        org_id=new_org.id,
        username=username,
        email=email,
        hashed_password=hashed_pw,
        role_id=admin_role.id if admin_role else None,
        status='Active',
        is_verified=True # Pre-verified
    )
    db.session.add(admin_user)
    
    # Clean up verification records if used
    if require_email_otp:
        verif = EmailVerification.query.filter_by(email=email).first()
        if verif:
            db.session.delete(verif)

    if require_phone_otp:
        phone_num = (data.get('phone') or '').strip()
        pverif = PhoneVerification.query.filter_by(phone=phone_num).first()
        if pverif:
            db.session.delete(pverif)
    
    db.session.commit()
    
    # Automatically dispatch Welcome & Onboarding Guide Email to new Org Admin
    try:
        from app.domain.services.email_notification_engine import EmailNotificationEngine
        EmailNotificationEngine.trigger_new_org_welcome_notification(new_org.id, admin_user.id)
    except Exception as email_err:
        print(f"[QCMS Auth] Welcome email trigger non-blocking error: {email_err}")

    return jsonify({
        "msg": f"Organization '{new_org.name}' and Admin account created successfully under the '{plan_name}' Trial plan.",
        "plan_name": plan_name,
        "trial_ends_at": trial_ends.isoformat()
    }), 201

@auth_bp.route('/request-registration-otp', methods=['POST'])
def request_registration_otp():
    settings = get_platform_settings_safe()
    require_email_otp = getattr(settings, 'require_email_otp', True) if settings else True
    if not require_email_otp:
        return jsonify({"msg": "Email OTP verification is disabled.", "require_email_otp": False}), 200

    if settings and not settings.registration_open:
        return jsonify({"msg": "Self-service organization sign-up is currently disabled by the Super Admin.", "message": "Self-service organization sign-up is currently disabled by the Super Admin."}), 403

    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    
    if not email:
        return jsonify({"msg": "Email is required"}), 400
        
    # Check if email is already taken
    if Organization.query.filter_by(email=email, is_deleted=False).first():
        return jsonify({"msg": "An organization with this email is already registered."}), 400

    from app.infrastructure.cache.redis_adapter import cache
    # Resend cooldown enforcement (60s)
    cooldown_key = f"otp_cooldown:email:{email}"
    if cache.get(cooldown_key):
        return jsonify({
            "status": "error",
            "msg": "Please wait 60 seconds before requesting a new verification code.",
            "code": "OTP_COOLDOWN_ACTIVE"
        }), 429

    # Generate 6-digit cryptographically secure OTP
    otp = f"{secrets.randbelow(1_000_000):06d}"
    
    # Update or create verification record
    verification = EmailVerification.query.filter_by(email=email).first()
    if verification:
        verification.otp = otp
        verification.is_verified = False
        verification.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
    else:
        verification = EmailVerification(
            email=email,
            otp=otp,
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
        )
        db.session.add(verification)
    
    # Set 60-second cooldown in cache
    cache.setex(cooldown_key, 60, "1")
    # Reset failed attempts counter
    cache.delete(f"otp_fails:email:{email}")

    # Send email via standardized utility (never return in HTTP response)
    EmailUtils.send_registration_otp(email, otp)
    
    db.session.commit()
    return jsonify({"msg": "Verification code sent to your email.", "require_email_otp": True}), 200

@auth_bp.route('/verify-registration-otp', methods=['POST'])
def verify_registration_otp():
    settings = get_platform_settings_safe()
    require_email_otp = getattr(settings, 'require_email_otp', True) if settings else True
    if not require_email_otp:
        return jsonify({"msg": "Email OTP verification is disabled. Proceeding.", "is_verified": True, "require_email_otp": False}), 200

    if settings and not settings.registration_open:
        return jsonify({"msg": "Self-service organization sign-up is currently disabled by the Super Admin.", "message": "Self-service organization sign-up is currently disabled by the Super Admin."}), 403

    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    otp = str(data.get('otp') or '').strip()
    
    if not email or not otp:
        return jsonify({"msg": "Email and OTP are required"}), 400

    from app.infrastructure.cache.redis_adapter import cache
    fails_key = f"otp_fails:email:{email}"
    current_fails = cache.incr(fails_key, amount=1, ttl_seconds=600)
    if current_fails > 5:
        return jsonify({
            "status": "error",
            "msg": "Too many invalid attempts. This verification code has been locked. Please request a new code.",
            "code": "OTP_ATTEMPTS_EXCEEDED"
        }), 429

    verification = EmailVerification.query.filter_by(email=email, otp=otp).first()
    
    if not verification:
        return jsonify({"msg": "Invalid verification code."}), 400
        
    if _to_naive_utc(verification.expires_at) < datetime.now(timezone.utc).replace(tzinfo=None):
        return jsonify({"msg": "Verification code has expired. Please request a new one."}), 400
        
    # Mark verified and immediately invalidate OTP to prevent reuse
    verification.is_verified = True
    verification.otp = None
    cache.delete(fails_key)
    cache.delete(f"otp_cooldown:email:{email}")
    db.session.commit()
    
    return jsonify({"msg": "Email verified successfully. You can now proceed.", "is_verified": True}), 200


def dispatch_phone_otp_sms(phone, otp):
    """
    Dispatch SMS OTP to mobile phone via active Jio DLT / Kaleyra SMS integration gateway.
    """
    try:
        from app.infrastructure.database.models.models import IntegrationConfig
        cfg = IntegrationConfig.query.filter_by(provider_id='jio_dlt').first()
        if not cfg or cfg.status != 'Connected':
            print(f"[QCMS Phone OTP] Jio DLT integration status is '{cfg.status if cfg else 'not found'}'. Simulating OTP {otp} for {phone}")
            return False, "SMS gateway not connected"

        settings = cfg.settings or {}
        api_key = (settings.get('api_key') or '').strip()
        entity_id = (settings.get('entity_id') or '').strip()
        sender_id = (settings.get('sender_id') or '').strip()
        template_id = (settings.get('template_id') or '').strip()
        account_sid = (settings.get('account_sid') or '').strip()
        api_url = (settings.get('api_url') or '').strip() or 'https://api.kaleyra.io/'

        if not api_key:
            print(f"[QCMS Phone OTP] Jio DLT API key is missing. Simulating OTP {otp} for {phone}")
            return False, "SMS API key missing"

        # Format phone number for SMS delivery (default country code +91 for 10-digit India numbers)
        clean_phone = phone.replace(' ', '').replace('-', '').replace('+', '')
        if len(clean_phone) == 10:
            formatted_phone = '91' + clean_phone
        else:
            formatted_phone = clean_phone

        # Load SMS body from DB (SmsTemplateConfig) — falls back to default if not configured
        sms_body_template = f"Dear Customer, use OTP {otp} to complete your activation on IFQM Skills. Do not share this OTP with anyone."
        try:
            from app.infrastructure.database.models.models import SmsTemplateConfig
            otp_tmpl = SmsTemplateConfig.query.filter_by(template_key='phone_otp_verification', is_active=True).first()
            if otp_tmpl and otp_tmpl.body:
                sms_body_template = otp_tmpl.body.replace('{{otp}}', otp).replace('{otp}', otp)
                # If template_id is configured in SmsTemplateConfig and not overridden in integration settings, use it
                if otp_tmpl.template_id and not template_id:
                    template_id = otp_tmpl.template_id
                if otp_tmpl.entity_id and not entity_id:
                    entity_id = otp_tmpl.entity_id
                if otp_tmpl.sender_id and not sender_id:
                    sender_id = otp_tmpl.sender_id
        except Exception as _e:
            print(f"[QCMS Phone OTP] Could not load SMS template from DB: {_e}")

        sms_body = sms_body_template

        import urllib.request
        import urllib.parse
        import urllib.error
        import json

        url = api_url.rstrip('/')
        if account_sid and 'kaleyra.io' in url and '/v1/' not in url:
            url = f"https://api.kaleyra.io/v1/{account_sid}/messages"
        elif not url.endswith('/messages') and not url.endswith('/send') and not url.endswith('.php'):
            if 'kaleyra.io' in url and '/v1/' not in url:
                print(f"[QCMS Phone OTP] Tip: Kaleyra requires your Account SID in the endpoint URL, e.g.: https://api.kaleyra.io/v1/<YOUR_ACCOUNT_SID>/messages")
                url = f"{url}/v1/messages"

        # Payload dictionary
        param_dict = {
            "to": "+" + formatted_phone,
            "type": "OTP",
            "sender": sender_id,
            "body": sms_body,
            "template_id": template_id,
            "entity_id": entity_id,
            "dlt_template_id": template_id,
            "pe_id": entity_id
        }

        # Try JSON POST first
        headers = {
            'User-Agent': 'QCMS-Enterprise-OS/1.0',
            'Content-Type': 'application/json',
            'api-key': api_key,
            'Authorization': f'Bearer {api_key}'
        }
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(param_dict).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                res_body = response.read().decode('utf-8')
                print(f"[QCMS Phone OTP] Jio DLT / Kaleyra API response HTTP {response.status}: {res_body}")
                cfg.usage_count = (cfg.usage_count or 0) + 1
                db.session.commit()
                return True, "SMS sent"
        except urllib.error.HTTPError as he:
            err_body = he.read().decode('utf-8') if he.fp else str(he)
            print(f"[QCMS Phone OTP] JSON request failed (HTTP {he.code}): {err_body}")

            # Try form-urlencoded format fallback
            form_headers = {
                'User-Agent': 'QCMS-Enterprise-OS/1.0',
                'Content-Type': 'application/x-www-form-urlencoded',
                'api-key': api_key
            }
            form_data = urllib.parse.urlencode(param_dict).encode('utf-8')
            req2 = urllib.request.Request(url, data=form_data, headers=form_headers, method='POST')
            try:
                with urllib.request.urlopen(req2, timeout=12) as response2:
                    res_body2 = response2.read().decode('utf-8')
                    print(f"[QCMS Phone OTP] Jio DLT Form API response HTTP {response2.status}: {res_body2}")
                    cfg.usage_count = (cfg.usage_count or 0) + 1
                    db.session.commit()
                    return True, "SMS sent"
            except urllib.error.HTTPError as he2:
                err_body2 = he2.read().decode('utf-8') if he2.fp else str(he2)
                print(f"[QCMS Phone OTP] Form request failed (HTTP {he2.code}): {err_body2}")
                return False, f"SMS Gateway Error (HTTP {he2.code}): {err_body2}"

    except Exception as e:
        print(f"[QCMS Phone OTP] Error calling Jio DLT SMS gateway: {e}")
        try:
            from app.infrastructure.database.models.models import IntegrationConfig
            cfg = IntegrationConfig.query.filter_by(provider_id='jio_dlt').first()
            if cfg:
                cfg.error_count = (cfg.error_count or 0) + 1
                db.session.commit()
        except Exception:
            pass
        return False, str(e)


@auth_bp.route('/request-phone-otp', methods=['POST'])
def request_phone_otp():
    settings = get_platform_settings_safe()
    if settings and not settings.registration_open:
        return jsonify({"msg": "Self-service organization sign-up is currently disabled by the Super Admin."}), 403

    data = request.get_json() or {}
    phone = (data.get('phone') or '').strip()
    if not phone:
        return jsonify({"msg": "Phone number is required"}), 400

    from app.infrastructure.cache.redis_adapter import cache
    cooldown_key = f"otp_cooldown:phone:{phone}"
    if cache.get(cooldown_key):
        return jsonify({
            "status": "error",
            "msg": "Please wait 60 seconds before requesting a new SMS verification code.",
            "code": "OTP_COOLDOWN_ACTIVE"
        }), 429

    otp = f"{secrets.randbelow(1_000_000):06d}"
    verif = PhoneVerification.query.filter_by(phone=phone).first()
    if verif:
        verif.otp = otp
        verif.is_verified = False
        verif.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
    else:
        verif = PhoneVerification(
            phone=phone,
            otp=otp,
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
        )
        db.session.add(verif)

    cache.setex(cooldown_key, 60, "1")
    cache.delete(f"otp_fails:phone:{phone}")
    db.session.commit()

    # Dispatch live SMS via Jio DLT / Kaleyra SMS Gateway (never return OTP in response)
    sms_sent, sms_status_msg = dispatch_phone_otp_sms(phone, otp)
    return jsonify({"msg": f"Verification code sent to {phone}."}), 200


@auth_bp.route('/verify-phone-otp', methods=['POST'])
def verify_phone_otp():
    data = request.get_json() or {}
    phone = (data.get('phone') or '').strip()
    otp = str(data.get('otp') or '').strip()

    if not phone or not otp:
        return jsonify({"msg": "Phone number and OTP code are required"}), 400

    from app.infrastructure.cache.redis_adapter import cache
    fails_key = f"otp_fails:phone:{phone}"
    current_fails = cache.incr(fails_key, amount=1, ttl_seconds=600)
    if current_fails > 5:
        return jsonify({
            "status": "error",
            "msg": "Too many invalid attempts. This phone verification code has been locked.",
            "code": "OTP_ATTEMPTS_EXCEEDED"
        }), 429

    verif = PhoneVerification.query.filter_by(phone=phone, otp=otp).first()
    if not verif:
        return jsonify({"msg": "Invalid phone verification code."}), 400

    if _to_naive_utc(verif.expires_at) < datetime.now(timezone.utc).replace(tzinfo=None):
        return jsonify({"msg": "Phone verification code has expired. Please request a new code."}), 400

    verif.is_verified = True
    verif.otp = None
    cache.delete(fails_key)
    cache.delete(f"otp_cooldown:phone:{phone}")
    db.session.commit()
    return jsonify({"msg": "Phone number verified successfully!"}), 200


@auth_bp.route('/register', methods=['POST'])
@jwt_required()
# DEPRECATED: Use /api/admin/users instead for audit logging and standardized creation.
def register():
    # Check PlatformSettings to see if native registration is disabled
    from app.infrastructure.database.models.models import PlatformSettings
    settings = PlatformSettings.query.first()
    auth_settings = (settings.authentication_settings or {}) if settings else {}
    if auth_settings.get('native_email_enabled') is False:
        return jsonify({"msg": "Direct registration is disabled. Please use Single Sign-On (SSO)."}), 403
    # Only Admin can create users in their own org
    identity = get_jwt_identity()
    try:
        current_user_id = int(identity)
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid user identity"}), 401
    admin = db.session.get(User, current_user_id)
    if admin.role.name != 'Admin':
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.get_json()
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"msg": "Username already exists"}), 400
        
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"msg": "A user with this email already exists"}), 400
        
    role = Role.query.filter_by(name=data.get('role', 'Team Member')).first()
    if not role:
        return jsonify({"msg": "Invalid role"}), 400
        
    # Temporary password logic
    temp_password = data.get('password', 'QCMS@123') # Default temp pass if not provided
    hashed_pw = bcrypt.generate_password_hash(temp_password).decode('utf-8')
    
    dept_id = None
    if data.get('department'):
        dept = Department.query.filter_by(name=data['department'], org_id=admin.org_id).first()
        if not dept:
            # Create department if it doesn't exist for this org
            dept = Department(name=data['department'], org_id=admin.org_id)
            db.session.add(dept)
            db.session.flush()
        dept_id = dept.id
    
    new_user = User(
        org_id=admin.org_id,
        username=data['username'],
        email=data['email'],
        hashed_password=hashed_pw,
        role_id=role.id,
        department_id=dept_id,
        is_temp_password=True,
        is_verified=True,  # Users created by Admin are pre-verified
        status='Active'
    )
    
    db.session.add(new_user)
    
    # Send email with temporary password
    EmailUtils.send_temp_password_email(new_user, temp_password)
    
    db.session.commit()
    
    return jsonify({
        "msg": "User created successfully. Credentials sent to their email.",
        "temp_password": temp_password if not data.get('password') else "provided by admin"
    }), 201

@auth_bp.route('/login-config', methods=['GET'])
def get_login_config():
    """
    Public endpoint — no JWT required.
    Given ?identifier=xxx, finds the user's org and returns
    the allowed login options + human-readable field labels, SSO config,
    and the dynamic document/platform branding identity.
    """
    from app.infrastructure.database.models.models import PlatformSettings, Organization
    from app.domain.services.document_branding_service import DocumentBrandingService

    settings = PlatformSettings.query.first()
    auth_settings = (settings.authentication_settings or {}) if settings else {}
    
    sso_config = {
        "google_enabled": auth_settings.get('oauth_google_enabled', False),
        "google_client_id": auth_settings.get('oauth_google_client_id', ''),
        "microsoft_enabled": auth_settings.get('oauth_microsoft_enabled', False) or auth_settings.get('azure_ad_enabled', False),
        "microsoft_client_id": auth_settings.get('oauth_microsoft_client_id', ''),
        "saml_enabled": auth_settings.get('saml_enabled', False),
        "saml_url": auth_settings.get('saml_metadata_url', ''),
        "native_enabled": auth_settings.get('native_email_enabled', True)
    }

    # Global platform branding
    branding = DocumentBrandingService.get_branding_context(org_id=None)

    identifier = request.args.get('identifier', request.args.get('email', '')).strip().lower()
    if not identifier:
        # Fallback to general system settings: return union of all login options active in the system
        all_orgs = Organization.query.filter(Organization.login_options.isnot(None)).all()
        options = ["email"]
        for o in all_orgs:
            for opt in (o.login_options or []):
                if opt not in options:
                    options.append(opt)
        
        system_labels = {"email": "Email ID", "username": "Username"}
        field_labels = {}
        for key in options:
            if key in system_labels:
                field_labels[key] = system_labels[key]
            else:
                field_labels[key] = key.replace('_', ' ').title()
                
        return jsonify({
            "login_options": options,
            "field_labels": field_labels,
            "sso_config": sso_config,
            "branding": branding
        }), 200

    from sqlalchemy import or_
    # Try finding user by email or username first
    user = User.query.filter(
        or_(
            User.email.ilike(identifier),
            User.username.ilike(identifier)
        )
    ).first()

    # If not found, search custom columns that are login options
    if not user:
        all_orgs_with_custom_login = Organization.query.filter(
            Organization.login_options.isnot(None)
        ).all()
        checked_keys = set()
        for org in all_orgs_with_custom_login:
            opts = org.login_options or []
            for key in opts:
                if key in ('email', 'username') or key in checked_keys:
                    continue
                checked_keys.add(key)
                try:
                    from sqlalchemy import text
                    result = db.session.execute(
                        text(f"SELECT id FROM users WHERE LOWER({key}::text) = LOWER(:val) LIMIT 1"),
                        {"val": identifier}
                    ).fetchone()
                    if result:
                        user = db.session.get(User, result[0])
                        break
                except Exception:
                    continue
            if user:
                break

    if user and user.org_id:
        try:
            branding = DocumentBrandingService.get_branding_context(org_id=user.org_id)
        except Exception:
            pass

    if not user or not user.organization:
        return jsonify({
            "login_options": ["email"], 
            "field_labels": {"email": "Email ID"},
            "sso_config": sso_config,
            "branding": branding
        }), 200

    org = user.organization
    options = org.login_options or ["email"]
    if "email" not in options:
        options = ["email"] + options

    # Build human-readable labels
    from app.infrastructure.database.models.models import UserCustomField
    custom_fields = UserCustomField.query.filter_by(org_id=org.id).all()
    cf_map = {cf.field_key: cf.display_name for cf in custom_fields}

    system_labels = {"email": "Email ID", "username": "Username"}
    field_labels = {}
    for key in options:
        if key in system_labels:
            field_labels[key] = system_labels[key]
        elif key in cf_map:
            field_labels[key] = cf_map[key]
        else:
            field_labels[key] = key.replace('_', ' ').title()

    return jsonify({
        "login_options": options,
        "field_labels": field_labels,
        "sso_config": sso_config,
        "branding": branding
    }), 200


def resolve_user_plant_and_dept(user):
    try:
        from app.infrastructure.database.models.models import Plant, Department
        
        cf = user.custom_fields or {}
        cf_loc = cf.get('location') or cf.get('plant_location') or cf.get('plant')
        cf_dept = cf.get('department') or cf.get('department_name')

        dept_obj = getattr(user, 'dept', None)
        if not dept_obj and user.department_id:
            dept_obj = db.session.get(Department, user.department_id)

        plant_obj = getattr(user, 'plant', None)
        if not plant_obj and user.plant_id:
            plant_obj = db.session.get(Plant, user.plant_id)

        if not plant_obj and dept_obj and dept_obj.plant_id:
            plant_obj = db.session.get(Plant, dept_obj.plant_id)

        if not plant_obj and cf_loc and user.org_id:
            plant_obj = Plant.query.filter(
                Plant.org_id == user.org_id,
                db.or_(Plant.name.ilike(cf_loc), Plant.location.ilike(cf_loc))
            ).first()

        if not dept_obj and cf_dept and user.org_id:
            dept_obj = Department.query.filter(
                Department.org_id == user.org_id,
                Department.name.ilike(cf_dept)
            ).first()

        p_name = None
        p_id = user.plant_id
        if plant_obj:
            p_name = plant_obj.name or plant_obj.location
            p_id = plant_obj.id
        elif cf_loc:
            p_name = cf_loc

        d_name = None
        d_id = user.department_id
        if dept_obj:
            d_name = dept_obj.name
            d_id = dept_obj.id
        elif cf_dept:
            d_name = cf_dept

        if not p_name and user.org_id and not user.plant_id and not cf_loc:
            def_plant = Plant.query.filter_by(org_id=user.org_id).first()
            if def_plant:
                p_name = def_plant.name
                p_id = def_plant.id

        if not d_name and user.org_id and not user.department_id and not cf_dept and p_id:
            def_dept = Department.query.filter_by(plant_id=p_id).first()
            if not def_dept:
                def_dept = Department.query.filter_by(org_id=user.org_id).first()
            if def_dept:
                d_name = def_dept.name
                d_id = def_dept.id

        return p_id, p_name, d_id, d_name
    except Exception as e:
        print(f"[PLANT/DEPT RESOLVE WARNING] {e}")
        return user.plant_id, None, user.department_id, None


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    identifier = (data.get('username') or data.get('email') or data.get('identifier') or '').strip()
    password = data.get('password', '')
    
    if not identifier:
        return jsonify({"msg": "Login identifier required"}), 400

    # Brute-force / lockout check (enforces security_settings.max_login_attempts)
    try:
        from app.presentation.middleware.security import is_login_locked, get_lockout_info
        client_ip = (request.headers.get('X-Forwarded-For', '') or '').split(',')[0].strip() or request.remote_addr or ''
        id_info  = get_lockout_info(identifier)
        is_loopback = client_ip in ('127.0.0.1', 'localhost', '::1', '')
        ip_info  = get_lockout_info(client_ip) if (client_ip and not is_loopback) else {'is_locked': False, 'remaining_seconds': 0, 'locked_until_epoch': None}
        if id_info['is_locked'] or ip_info['is_locked']:
            info = id_info if id_info['is_locked'] else ip_info
            return jsonify({
                "msg": "Account is temporarily locked due to too many failed login attempts.",
                "error_code": "ACCOUNT_LOCKED",
                "locked_until_epoch": info['locked_until_epoch'],
                "remaining_seconds": info['remaining_seconds']
            }), 429
    except Exception:
        pass  # Never block login on middleware errors

    # Build a flexible query: check username, phone, and email (system fields)
    from sqlalchemy import or_
    user = User.query.filter(
        or_(
            User.username.ilike(identifier),
            User.phone.ilike(identifier),
            User.email.ilike(identifier)
        )
    ).first()

    # Check PlatformSettings to see if native login is disabled
    from app.infrastructure.database.models.models import PlatformSettings
    settings = PlatformSettings.query.first()
    auth_settings = (settings.authentication_settings or {}) if settings else {}
    if auth_settings.get('native_email_enabled') is False:
        # Check if the user is a SuperAdmin (must load user to check role)
        if user and user.role.name != 'SuperAdmin':
            return jsonify({"msg": "Native password login is disabled. Please use Single Sign-On (SSO)."}), 403
        elif not user:
            # If user not found, we still return 403 block if native login is disabled globally
            return jsonify({"msg": "Native password login is disabled. Please use Single Sign-On (SSO)."}), 403

    # If not found via system fields, check custom field columns that are enabled as login options
    if not user:
        from app.infrastructure.database.models.models import UserCustomField
        # We can't know the org without finding the user, so search across all custom field columns
        # by looking at ALL organizations' login_options (safe since identifier must be unique)
        from app.infrastructure.database.models.models import Organization
        from sqlalchemy import text
        # Get all unique custom field keys that are marked as login options anywhere
        all_orgs_with_custom_login = Organization.query.filter(
            Organization.login_options.isnot(None)
        ).all()
        checked_keys = set()
        for org in all_orgs_with_custom_login:
            options = org.login_options or []
            for key in options:
                if key in ('email', 'username') or key in checked_keys:
                    continue
                checked_keys.add(key)
                # Check if this column exists in users table and search it
                try:
                    result = db.session.execute(
                        text(f"SELECT id FROM users WHERE LOWER({key}::text) = LOWER(:val) LIMIT 1"),
                        {"val": identifier}
                    ).fetchone()
                    if result:
                        user = db.session.get(User, result[0])
                        break
                except Exception:
                    continue
            if user:
                break

    if not user:
        # Record failed attempt (wrong identifier)
        try:
            from app.presentation.middleware.security import record_failed_login
            from app.presentation.routes.audit_routes import log_audit_event
            client_ip = (request.headers.get('X-Forwarded-For', '') or '').split(',')[0].strip() or request.remote_addr or ''
            record_failed_login(identifier)
            if client_ip and client_ip not in ('127.0.0.1', 'localhost', '::1'):
                record_failed_login(client_ip)
            log_audit_event(
                org_id=None,
                user_id=None,
                action="USER_LOGIN_FAILED",
                target_table="users",
                details={"identifier": identifier, "reason": "Username or email not found"},
                response_code=401
            )
        except Exception:
            pass
        return jsonify({"msg": "Username or email not found"}), 401

    if not bcrypt.check_password_hash(user.hashed_password, password):
        # Record failed attempt (wrong password)
        try:
            from app.presentation.middleware.security import record_failed_login
            from app.presentation.routes.audit_routes import log_audit_event
            client_ip = (request.headers.get('X-Forwarded-For', '') or '').split(',')[0].strip() or request.remote_addr or ''
            is_locked, attempts = record_failed_login(identifier)
            if client_ip and client_ip not in ('127.0.0.1', 'localhost', '::1'):
                record_failed_login(client_ip)
            
            if is_locked:
                log_audit_event(
                    org_id=user.org_id,
                    user_id=user.id,
                    action="USER_LOGIN_LOCKED",
                    target_table="users",
                    target_id=user.id,
                    details={"username": user.username, "reason": "Account locked due to excessive failed attempts"},
                    response_code=429
                )
                return jsonify({
                    "msg": "Account locked due to too many failed attempts. Try again later.",
                    "error_code": "ACCOUNT_LOCKED"
                }), 429

            log_audit_event(
                org_id=user.org_id,
                user_id=user.id,
                action="USER_LOGIN_FAILED",
                target_table="users",
                target_id=user.id,
                details={"username": user.username, "reason": "Incorrect password"},
                response_code=401
            )
        except Exception:
            pass
        return jsonify({"msg": "Incorrect password"}), 401

    # Check email verification (skip for temp passwords)
    if not user.is_verified and not user.is_temp_password:
        return jsonify({"msg": "Please verify your email address before logging in"}), 403

    # If the user's organization has been deleted (moved to Recycle Bin or permanently removed),
    # return a generic invalid credentials message — do not reveal the org is deleted.
    role_name_chk = (user.role.name if user.role else '').strip().lower()
    is_super_admin_user = role_name_chk in ('superadmin', 'super admin', 'super_admin') or getattr(user, 'is_super_admin', False) or getattr(user, 'is_platform_super_admin', False) or user.id == 1

    if not is_super_admin_user and user.organization and getattr(user.organization, 'is_deleted', False):
        return jsonify({"msg": "Invalid username or password"}), 401

    # If organization is suspended, restrict login to Admin, CEO, or SuperAdmin only
    if not is_super_admin_user and user.organization and user.organization.subscription_status == 'Suspended':
        if (user.role.name if user.role else '') not in ('Admin', 'CEO', 'SuperAdmin'):
            return jsonify({"msg": "Your organization's account is suspended. Access denied. Please contact your administrator."}), 403
        
    # Clear lockout on successful authentication
    try:
        from app.presentation.middleware.security import clear_login_lockout
        client_ip = (request.headers.get('X-Forwarded-For', '') or '').split(',')[0].strip() or request.remote_addr or ''
        clear_login_lockout(identifier)
        if client_ip:
            clear_login_lockout(client_ip)
    except Exception:
        pass

    # Generate session ID first so it can be bound to JWT claims
    session_id = f"SESS-{int(datetime.now(timezone.utc).replace(tzinfo=None).timestamp())}-{user.id}"

    # Scoped access token
    # Include sa_sub_role in claims so the frontend can enforce sub-role
    # restrictions immediately without an extra API call.
    role_name = user.role.name if user.role else 'SuperAdmin'
    sa_sub_role = None
    if user.role and user.role.name == 'SuperAdmin':
        cf = user.custom_fields if isinstance(user.custom_fields, dict) else {}
        sa_sub_role = cf.get('super_admin_role', 'Owner')

    remember_me = bool(data.get('remember_me') or data.get('rememberMe'))
    token_expiry = timedelta(days=30) if remember_me else timedelta(days=1)

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "session_id": session_id,
            "org_id": user.org_id,
            "role": role_name,
            "dept_id": user.department_id,
            "sa_sub_role": sa_sub_role,   # None for non-SuperAdmin users
        },
        expires_delta=token_expiry
    )
    
    # Update last login time
    user.last_login = datetime.now(timezone.utc).replace(tzinfo=None)

    # Warm session cache immediately
    try:
        from app.infrastructure.cache.redis_client import cache as session_cache
        session_cache.set(f"sess_status:{session_id}", "Active", ex=3600)
        session_cache.set(f"user_active:{user.id}", "active", ex=3600)
    except Exception:
        pass
    
    # Track session in db safely
    try:
        from app.infrastructure.database.models.models import SaaSUserSession
        from app.presentation.routes.audit_routes import parse_user_agent, get_geo_location, get_real_client_ip, log_audit_event
        
        # Mark old sessions as LoggedOut for security
        try:
            SaaSUserSession.query.filter_by(user_id=user.id, status='Active').update({"status": "LoggedOut", "logout_time": datetime.now(timezone.utc).replace(tzinfo=None)})
            db.session.commit()
        except Exception:
            db.session.rollback()

        ua_str = request.headers.get('User-Agent')
        ip_addr = get_real_client_ip(request)
        os_name, browser_name, device_name = parse_user_agent(ua_str)
        loc = None
        try:
            loc = get_geo_location(ip_addr, user=user, req=request)
        except Exception:
            pass

        new_sess = SaaSUserSession(
            session_id=session_id,
            user_id=user.id,
            org_id=user.org_id,
            device=device_name,
            browser=browser_name,
            os=os_name,
            ip_address=ip_addr,
            location=loc,
            status='Active',
            login_time=datetime.now(timezone.utc).replace(tzinfo=None),
            last_activity=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.session.add(new_sess)
        db.session.commit()

        # Log enriched login audit event
        try:
            log_audit_event(
                org_id=user.org_id,
                user_id=user.id,
                action="USER_LOGIN",
                target_table="users",
                target_id=user.id,
                details={"username": user.username, "ip": ip_addr}
            )
        except Exception:
            pass
    except Exception as sess_err:
        db.session.rollback()
        print(f"[LOGIN SESSION WARNING] {sess_err}")
    p_id, p_name, d_id, d_name = resolve_user_plant_and_dept(user)
    from app.presentation.routes.admin_routes import DEFAULT_ROLE_PERMISSIONS
    org_obj = user.organization if role_name != 'SuperAdmin' else None
    sec = getattr(org_obj, 'security_settings', {}) or {} if org_obj else {}
    role_perms = sec.get('role_permissions') if isinstance(sec, dict) else None
    merged_perms = {}
    for r_k, def_k in DEFAULT_ROLE_PERMISSIONS.items():
        merged_perms[r_k] = dict(def_k)
        if role_perms and isinstance(role_perms, dict) and r_k in role_perms and isinstance(role_perms[r_k], dict):
            merged_perms[r_k].update(role_perms[r_k])

    resp = jsonify({
        "access_token": access_token,
        "session_id": session_id,
        "org_id": user.org_id,
        "org_name": user.organization.name if user.organization else None,
        "role": user.role.name if user.role else 'SuperAdmin',
        "role_name": user.role.name if user.role else 'SuperAdmin',
        "role_permissions": merged_perms,
        "subscription_plan": user.organization.subscription_plan if user.organization else 'Starter',
        "subscription_status": user.organization.subscription_status if user.organization else 'Active',
        "username": user.username,
        "full_name": user.full_name or user.username,
        "profile_picture": get_profile_picture_url(user),
        "banner_image": user.banner_image,
        "email": user.email,
        "is_temp_password": user.is_temp_password,
        "language": user.language,
        "id": user.id,
        "department_id": d_id,
        "department": d_name,
        "department_name": d_name,
        "plant_id": p_id,
        "plant_name": p_name,
        "location": p_name,
        "org_primary_color": user.organization.primary_color if user.organization else None,
        "org_logo_url": user.organization.logo_url if user.organization else None,
        "org_favicon_url": user.organization.favicon_url if user.organization else None,
        "org_timezone": user.organization.timezone if user.organization else "Asia/Kolkata",
        "trial_ends_at": user.organization.trial_ends_at.isoformat() if user.organization and user.organization.trial_ends_at else None
    })
    set_access_cookies(resp, access_token)
    return resp, 200

@auth_bp.route('/me', methods=['GET'])
@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"status": "error", "message": "User account not found.", "session_terminated": True}), 401

    role_name = user.role.name if user.role else 'Admin'
    is_super_admin = role_name == 'SuperAdmin'

    if not is_super_admin and (not user.is_active and user.status not in ('Active', 'active')):
        return jsonify({
            "status": "error",
            "message": "Your account has been deactivated by an administrator.",
            "session_terminated": True
        }), 401

    try:
        from app.domain.services.document_branding_service import DocumentBrandingService
        branding_ctx = DocumentBrandingService.get_branding_context(user.org_id if role_name != 'SuperAdmin' else None)
    except Exception as e:
        branding_ctx = {}

    p_id, p_name, d_id, d_name = resolve_user_plant_and_dept(user)

    from app.presentation.routes.admin_routes import DEFAULT_ROLE_PERMISSIONS
    org_obj = user.organization if not is_super_admin else None
    sec = getattr(org_obj, 'security_settings', {}) or {} if org_obj else {}
    role_perms = sec.get('role_permissions') if isinstance(sec, dict) else None
    merged_perms = {}
    for r_k, def_k in DEFAULT_ROLE_PERMISSIONS.items():
        merged_perms[r_k] = dict(def_k)
        if role_perms and isinstance(role_perms, dict) and r_k in role_perms and isinstance(role_perms[r_k], dict):
            merged_perms[r_k].update(role_perms[r_k])

    return jsonify({
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name or user.username,
        "email": user.email,
        "role": user.role.name if user.role else 'SuperAdmin',
        "role_name": user.role.name if user.role else 'SuperAdmin',
        "role_permissions": merged_perms,
        "department": d_name,
        "department_name": d_name,
        "department_id": d_id,
        "plant_id": p_id,
        "plant_name": p_name,
        "location": p_name,
        "org_id": None if is_super_admin else user.org_id,
        "org_name": None if is_super_admin else (user.organization.name if user.organization else None),
        "status": 'Active' if is_super_admin else user.status,
        "is_active": True if is_super_admin else user.is_active,
        "deactivated_at": None if is_super_admin else (user.deactivated_at.isoformat() if getattr(user, 'deactivated_at', None) else None),
        "profile_picture": get_profile_picture_url(user),
        "banner_image": user.banner_image,
        "language": user.language,
        "org_primary_color": user.organization.primary_color if user.organization else None,
        "org_logo_url": (user.organization.logo_url if user.organization and user.organization.logo_url else None),
        "platform_logo_url": branding_ctx.get("logo_url"),
        "platform_software_name": branding_ctx.get("software_name"),
        "platform_short_name": branding_ctx.get("software_short_name"),
        "platform_title": branding_ctx.get("platform_title"),
        "platform_subtitle": branding_ctx.get("platform_subtitle"),
        "org_favicon_url": user.organization.favicon_url if user.organization else None,
        "org_timezone": user.organization.timezone if user.organization else "Asia/Kolkata",
        "subscription_status": 'Active' if is_super_admin else (user.organization.subscription_status if user.organization else 'Active'),
        "subscription_plan": 'Enterprise' if is_super_admin else (user.organization.subscription_plan if user.organization else 'Starter'),
        "trial_ends_at": None if is_super_admin else (user.organization.trial_ends_at.isoformat() if user.organization and user.organization.trial_ends_at else None)
    }), 200

@auth_bp.route('/user-reactivation-request', methods=['POST'])
@jwt_required()
def user_reactivation_request():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    data = request.get_json() or {}
    message_text = data.get('message', '').strip()
    if not message_text:
        return jsonify({"msg": "Request message is required"}), 400
        
    ticket_num = f"REACT-USER-{user.id}-{int(datetime.now(timezone.utc).replace(tzinfo=None).timestamp())}"
    ticket = SupportTicket(
        org_id=user.org_id,
        user_id=user.id,
        subject=f"Account Reactivation Request: {user.full_name or user.username}",
        message=f"Deactivated User: {user.full_name or user.username} ({user.email})\nRole: {user.role.name}\nDepartment: {user.dept.name if user.dept else 'N/A'}\n\nRequest Message:\n{message_text}",
        category="User Access",
        status="Open",
        priority="High",
        ticket_number=ticket_num
    )
    db.session.add(ticket)
    
    admin_users = User.query.join(Role).filter(
        User.org_id == user.org_id,
        Role.name == 'Admin',
        User.is_active == True
    ).all()
    
    for admin in admin_users:
        notif = Notification(
            org_id=user.org_id,
            user_id=admin.id,
            title="Account Reactivation Request",
            message=f"{user.full_name or user.username} has requested account reactivation: '{message_text[:100]}...'",
            link="/admin/users.html"
        )
        db.session.add(notif)
        
    try:
        from app.presentation.routes.audit_routes import log_audit_event
        log_audit_event(
            org_id=user.org_id,
            user_id=user.id,
            action="USER_REACTIVATION_REQUEST_SUBMITTED",
            target_table="users",
            target_id=user.id,
            details={"username": user.username, "request_message": message_text}
        )
    except Exception as e:
        print("Failed to log audit event:", e)
        
    db.session.commit()
    
    return jsonify({
        "status": "success",
        "message": "Your reactivation request has been sent to your administrator successfully."
    }), 201

@auth_bp.route('/request-reactivation', methods=['POST'])
@jwt_required()
def request_reactivation():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    org = user.organization
    if not org or org.subscription_status != 'Suspended':
        return jsonify({"msg": "Organization is not suspended"}), 400
        
    data = request.get_json()
    message_text = data.get('message', '').strip()
    if not message_text:
        return jsonify({"msg": "Request message is required"}), 400
        
    # Create support ticket in DB
    ticket = SupportTicket(
        org_id=org.id,
        user_id=user.id,
        subject="Account Reactivation Request",
        message=f"Request by {user.role.name} ({user.username}):\n\n{message_text}",
        status="Open",
        priority="High"
    )
    db.session.add(ticket)

    # Notify all SuperAdmins
    try:
        sa_role = Role.query.filter_by(name='SuperAdmin').first()
        if sa_role:
            sa_users = User.query.filter_by(role_id=sa_role.id).all()
            for sa in sa_users:
                notif = Notification(
                    org_id=sa.org_id or org.id,
                    user_id=sa.id,
                    title=f"Organization Reactivation Request: {org.name}",
                    message=f"Organization '{org.name}' (Org ID: {org.id}) requested account reactivation. Message: '{message_text}'",
                    link="/admin/super-admin.html?view=support",
                    is_read=False
                )
                db.session.add(notif)
    except Exception as e:
        print("[QCMS] Warning: Failed to send SuperAdmin notification:", e)

    db.session.commit()
    
    return jsonify({"status": "success", "message": "Reactivation request submitted successfully."}), 201

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    if request.is_json:
        data = request.get_json()
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'language' in data:
            user.language = data['language']
    else:
        if 'full_name' in request.form:
            user.full_name = request.form['full_name']
        if 'language' in request.form:
            user.language = request.form['language']
            
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename != '' and allowed_file(file.filename):
                upload_dir = current_app.config.get('UPLOAD_FOLDER', os.path.abspath(os.path.join(current_app.root_path, '..', 'uploads')))
                os.makedirs(upload_dir, exist_ok=True)
                filename = secure_filename(f"avatar_{user.id}_{file.filename}")
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                user.profile_picture = f"/uploads/{filename}"
                
        if 'banner_image' in request.files:
            file = request.files['banner_image']
            if file and file.filename != '' and allowed_file(file.filename):
                upload_dir = current_app.config.get('UPLOAD_FOLDER', os.path.abspath(os.path.join(current_app.root_path, '..', 'uploads')))
                os.makedirs(upload_dir, exist_ok=True)
                filename = secure_filename(f"banner_{user.id}_{file.filename}")
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                user.banner_image = f"/uploads/{filename}"
        
    from app.utils.i18n_utils import _
    db.session.commit()
    return jsonify({
        "msg": _("auth.update_success", user_id=user.id), 
        "full_name": user.full_name,
        "profile_picture": get_profile_picture_url(user),
        "banner_image": user.banner_image
    }), 200

@auth_bp.route('/public-profile/<int:user_id>', methods=['GET'])
@jwt_required()
def get_public_profile(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    return jsonify({
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name or user.username,
        "role_name": user.role.name,
        "department": user.dept.name if user.dept else None,
        "profile_picture": get_profile_picture_url(user),
        "banner_image": user.banner_image
    }), 200

@auth_bp.route('/request-password-otp', methods=['POST'])
@jwt_required()
def request_password_otp():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    data = request.get_json() or {}
    
    current_password = data.get('current_password')
    if not current_password:
        return jsonify({"msg": "Current password required"}), 400
        
    if not bcrypt.check_password_hash(user.hashed_password, current_password):
        return jsonify({"msg": "Invalid current password"}), 401
        
    settings = get_platform_settings_safe()
    require_email_otp = getattr(settings, 'require_email_otp', True) if settings else True
    if not require_email_otp:
        return jsonify({"msg": "Email OTP verification is disabled.", "require_email_otp": False}), 200

    # Generate 6-digit cryptographically secure OTP
    otp = f"{secrets.randbelow(1_000_000):06d}"
    
    user.otp_token = otp
    user.otp_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
    db.session.commit()
    
    # Send OTP email
    EmailUtils.send_otp_email(user, otp)
    
    return jsonify({"msg": "OTP sent to your email", "require_email_otp": True}), 200

@auth_bp.route('/change-password', methods=['PUT'])
@jwt_required()
def change_password():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    data = request.get_json() or {}
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    otp = data.get('otp')
    
    if not current_password or not new_password:
        return jsonify({"msg": "Current password and new password required"}), 400
        
    if not user.check_password(current_password):
        return jsonify({"msg": "Invalid current password"}), 401

    settings = get_platform_settings_safe()
    require_email_otp = getattr(settings, 'require_email_otp', True) if settings else True

    if require_email_otp:
        if not otp:
            return jsonify({"msg": "OTP is required"}), 400
        if user.otp_token != otp:
            return jsonify({"msg": "Invalid OTP code"}), 400
        if user.otp_expiry and _to_naive_utc(user.otp_expiry) < datetime.now(timezone.utc).replace(tzinfo=None):
            return jsonify({"msg": "OTP has expired"}), 400
        
    user.password = new_password
    user.is_temp_password = False
    user.is_verified = True
    
    # Clear OTP
    user.otp_token = None
    user.otp_expiry = None
    db.session.add(user)
    
    # Invalidate all active user sessions across DB and Redis cache for security
    from app.infrastructure.cache.redis_adapter import cache
    cache.set(f"user_active:{user.id}", "inactive", ex=30)
    try:
        from app.infrastructure.database.models.auth import SaaSUserSession
        active_sessions = SaaSUserSession.query.filter_by(user_id=user.id, status='Active').all()
        for s in active_sessions:
            s.status = 'Terminated'
            s.logout_time = datetime.now(timezone.utc).replace(tzinfo=None)
            cache.set(f"sess_status:{s.session_id}", "Terminated", ex=3600)
    except Exception as e:
        print(f"[AUTH] Error terminating user sessions: {e}")

    # Send notification email
    EmailUtils.send_password_change_notification(user)
    
    db.session.commit()
    
    return jsonify({"msg": "Password updated successfully"}), 200

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if user:
        from app.presentation.routes.audit_routes import log_audit_event
        from app.infrastructure.database.models.models import SaaSUserSession
        from app.infrastructure.cache.redis_adapter import cache
        from flask_jwt_extended import get_jwt
        from datetime import datetime
        
        jwt_payload = get_jwt()
        current_session_id = jwt_payload.get('session_id') if isinstance(jwt_payload, dict) else None

        # Terminate active sessions in db and cache
        active_sess = SaaSUserSession.query.filter_by(user_id=user.id, status='Active').all()
        for s in active_sess:
            s.status = 'LoggedOut'
            s.logout_time = datetime.now(timezone.utc).replace(tzinfo=None)
            s.session_duration = int((s.logout_time - s.login_time).total_seconds())
            cache.set(f"sess_status:{s.session_id}", "Terminated", ex=3600)

        if current_session_id:
            cache.set(f"sess_status:{current_session_id}", "Terminated", ex=3600)
        
        log_audit_event(
            org_id=user.org_id,
            user_id=user.id,
            action="USER_LOGOUT",
            target_table="users",
            target_id=user.id,
            details={"username": user.username, "ip": request.remote_addr}
        )
        db.session.commit()
    resp = jsonify({"msg": "Successfully logged out"})
    unset_jwt_cookies(resp)
    return resp, 200

@auth_bp.route('/heartbeat', methods=['POST', 'GET'])
@jwt_required()
def auth_heartbeat():
    """
    Heartbeat ping from active frontend client to record ongoing user movement and refresh last_activity.
    If session has had no user movement for >= 2 hours, it is terminated and returns 401.
    """
    try:
        from app.presentation.routes.audit_routes import cleanup_inactive_sessions
        from app.infrastructure.database.models.models import SaaSUserSession
        from flask_jwt_extended import get_jwt
        
        user_id = int(get_jwt_identity())
        claims = get_jwt()
        session_id = claims.get('session_id') if isinstance(claims, dict) else None
        
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cutoff = now - timedelta(hours=2)
        
        sess = None
        if session_id:
            sess = SaaSUserSession.query.filter_by(session_id=session_id).first()
        if not sess:
            sess = SaaSUserSession.query.filter_by(user_id=user_id, status='Active').order_by(SaaSUserSession.login_time.desc()).first()
            
        if sess:
            ref_time = sess.last_activity or sess.login_time
            if sess.status == 'Active' and ref_time and ref_time < cutoff:
                # 2-hour continuous inactivity exceeded
                sess.status = 'Expired'
                sess.logout_time = ref_time + timedelta(hours=2)
                if sess.login_time:
                    sess.session_duration = max(0, int((sess.logout_time - sess.login_time).total_seconds()))
                db.session.commit()
                return jsonify({"status": "expired", "message": "Session terminated due to 2 hours of inactivity."}), 401
                
            # User is actively working: keep/set status to Active and refresh last_activity
            sess.status = 'Active'
            sess.last_activity = now
            db.session.commit()
            return jsonify({
                "status": "active",
                "session_id": sess.session_id,
                "last_activity": now.isoformat() + "Z"
            }), 200
            
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return internal_server_error(e, "An internal server error occurred.")

def validate_password_complexity(password):
    import re
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number (0-9)."
    if not re.search(r'[^A-Za-z0-9]', password):
        return False, "Password must contain at least one special character (!@#$...)."
    return True, None

@auth_bp.route('/reset-password', methods=['POST'])
@jwt_required(optional=True)
def reset_password():
    data = request.get_json() or {}
    password = data.get('password') or data.get('new_password')
    token = data.get('token') or data.get('reset_token') or data.get('reset_password_token')

    user = None
    jwt_uid = get_jwt_identity()

    # Strategy 1: Active JWT session identity
    if jwt_uid:
        try:
            user = db.session.get(User, int(jwt_uid))
        except (ValueError, TypeError):
            pass

    # Strategy 2: auth_token / access_token provided in request body
    raw_jwt = data.get('auth_token') or data.get('access_token') or data.get('jwt')
    if not user and raw_jwt:
        try:
            from flask_jwt_extended import decode_token
            decoded = decode_token(raw_jwt)
            jwt_sub = decoded.get('sub')
            if jwt_sub:
                user = db.session.get(User, int(jwt_sub))
        except Exception:
            pass

    # Strategy 3: user_id provided in body
    uid_val = data.get('user_id') or data.get('id')
    if not user and uid_val:
        try:
            user = db.session.get(User, int(uid_val))
        except (ValueError, TypeError):
            pass

    # Strategy 4: username or email lookup
    uname_val = (data.get('username') or '').strip()
    if not user and uname_val:
        user = User.query.filter((User.username.ilike(uname_val)) | (User.email.ilike(uname_val))).first()

    email_val = (data.get('email') or '').strip()
    if not user and email_val:
        user = User.query.filter((User.email.ilike(email_val)) | (User.username.ilike(email_val))).first()

    # Strategy 5: One-time password reset token (from email link)
    if not user and token:
        user = User.query.filter_by(reset_token=token).first()
        if not user:
            return jsonify({"msg": "Invalid or expired reset token."}), 400

        if not user.token_expiry or _to_naive_utc(user.token_expiry) < datetime.now(timezone.utc).replace(tzinfo=None):
            return jsonify({"msg": "Password reset link has expired. Please request a new link."}), 400

    if not user:
        return jsonify({"msg": "Cryptographically valid reset token or authenticated user session is required."}), 400

    if not password:
        return jsonify({"msg": "New password is required."}), 400

    is_valid, error_msg = validate_password_complexity(password)
    if not is_valid:
        return jsonify({"msg": error_msg}), 400

    # Update password and mark as permanent
    user.hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user.is_temp_password = False
    user.is_verified = True
    user.reset_token = None
    user.token_expiry = None
    db.session.add(user)

    # Invalidate all active user sessions across DB and Redis cache for security
    from app.infrastructure.cache.redis_adapter import cache
    cache.set(f"user_active:{user.id}", "inactive", ex=30)
    try:
        from app.infrastructure.database.models.auth import SaaSUserSession
        active_sessions = SaaSUserSession.query.filter_by(user_id=user.id, status='Active').all()
        for s in active_sessions:
            s.status = 'Terminated'
            s.logout_time = datetime.now(timezone.utc).replace(tzinfo=None)
            cache.set(f"sess_status:{s.session_id}", "Terminated", ex=3600)
    except Exception as e:
        print(f"[AUTH] Could not terminate user sessions: {e}")

    # Send security alert email
    try:
        EmailUtils.send_password_change_notification(user)
    except Exception as e:
        print(f"[AUTH] Could not send password change notification: {e}")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal database error while saving password"}), 500

    return jsonify({"msg": "Password updated successfully. Please log in with your new password."}), 200

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json() or {}
    email = data.get('email')
    user = User.query.filter_by(email=email).first()
    
    if user:
        EmailUtils.send_reset_password_email(user)
        db.session.commit()
        return jsonify({"msg": "Password reset link sent to your email"}), 200
    
    return jsonify({"msg": "If that email exists in our system, a reset link has been sent."}), 200

@auth_bp.route('/verify-email/<token>', methods=['GET'])
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    
    if not user:
        return jsonify({"msg": "Invalid or expired verification token"}), 400
        
    if user.token_expiry and _to_naive_utc(user.token_expiry) < datetime.now(timezone.utc).replace(tzinfo=None):
        return jsonify({"msg": "Verification token has expired"}), 400
        
    user.is_verified = True
    user.verification_token = None
    user.token_expiry = None
    db.session.commit()
    
    return """
    <html>
        <body style="font-family: Arial; text-align: center; padding-top: 50px;">
            <h1 style="color: #2563eb;">Verification Successful!</h1>
            <p>Your email has been verified. You can now log in to the application.</p>
            <a href="http://localhost:3000/login" style="color: #2563eb;">Go to Login</a>
        </body>
    </html>
    """, 200

@auth_bp.route('/reset-password-confirm', methods=['POST'])
def reset_password_confirm():
    return reset_password()

@auth_bp.route('/avatar/<username>', methods=['GET'])
def get_avatar_svg(username):
    initials = "".join([part[0] for part in username.split() if part])[:2].upper()
    if not initials:
        initials = "U"
    
    colors = [
        "#f87171", "#fb923c", "#fbbf24", "#34d399", 
        "#2dd4bf", "#38bdf8", "#60a5fa", "#818cf8", 
        "#a78bfa", "#f472b6", "#fb7185"
    ]
    color_index = sum(ord(c) for c in username) % len(colors)
    bg_color = colors[color_index]
    
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
        <rect width="100%" height="100%" fill="{bg_color}" />
        <text x="50%" y="55%" font-family="Arial, Helvetica, sans-serif" font-size="40" font-weight="bold" fill="#ffffff" dominant-baseline="middle" text-anchor="middle">{initials}</text>
    </svg>"""
    from flask import Response
    return Response(svg, mimetype='image/svg+xml')

@auth_bp.route('/support/tickets', methods=['GET', 'POST'])
@jwt_required()
def handle_support_tickets():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    if request.method == 'GET':
        tickets = SupportTicket.query.filter_by(user_id=user_id).order_by(SupportTicket.created_at.desc()).all()
        output = []
        for t in tickets:
            public_comments = []
            for c in (t.comments or []):
                if not c.is_internal:
                    user_display = (c.user.username or c.user.email) if c.user else "Support Team"
                    is_support = bool(c.user and c.user.role and c.user.role.name in ['SuperAdmin', 'Support Engineer', 'Support Manager', 'Admin'])
                    public_comments.append({
                        "id": c.id,
                        "user": user_display,
                        "is_support": is_support,
                        "content": c.content,
                        "created_at": c.created_at.isoformat() if c.created_at else "",
                        "attachments": [{"file_name": a.file_name, "file_path": a.file_path, "file_size": a.file_size} for a in (c.attachments or [])]
                    })

            # Check if there is an explicit or effective resolution
            res_val = t.resolution
            if (not res_val or res_val.strip() == 'No resolution notes provided.') and public_comments:
                for c in reversed(public_comments):
                    if c["is_support"] or c["user"] != (user.username or user.email):
                        res_val = c["content"]
                        break

            output.append({
                "id": t.id,
                "ticket_number": t.ticket_number or f"TKT-{t.id:06d}",
                "subject": t.subject,
                "message": t.message,
                "priority": t.priority,
                "status": t.status,
                "category": t.category,
                "created_at": t.created_at.isoformat(),
                "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
                "resolution": res_val,
                "comments": public_comments
            })
        return jsonify({"status": "success", "data": output})

    elif request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({"msg": "Request body must be JSON"}), 400
            
        subject = data.get('subject', '').strip()
        message = data.get('message', '').strip()
        priority = data.get('priority', 'Medium').strip()
        category = data.get('category', 'Technical').strip()
        
        if not subject or not message:
            return jsonify({"msg": "Subject and message are required"}), 400
            
        ticket = SupportTicket(
            org_id=user.org_id,
            user_id=user.id,
            subject=subject,
            message=message,
            priority=priority,
            category=category,
            status="Open"
        )
        db.session.add(ticket)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Ticket created successfully",
            "ticket_id": ticket.id
        }), 201


@auth_bp.route('/sso/<provider>', methods=['POST'])
def sso_login(provider):
    data = request.get_json() or {}
    email = data.get('email')
    token = data.get('token')
    
    if not email:
        return jsonify({"msg": "Email is required for SSO"}), 400
        
    from app.infrastructure.database.models.models import PlatformSettings
    settings = PlatformSettings.query.first()
    auth_settings = (settings.authentication_settings or {}) if settings else {}
    
    # Verify provider configuration
    if provider == 'google':
        if not auth_settings.get('oauth_google_enabled'):
            return jsonify({"msg": "Google OAuth is disabled"}), 403
        client_id = auth_settings.get('oauth_google_client_id')
        if not client_id:
            return jsonify({"msg": "Google OAuth is not configured properly"}), 400
    elif provider == 'microsoft':
        if not auth_settings.get('oauth_microsoft_enabled') and not auth_settings.get('azure_ad_enabled'):
            return jsonify({"msg": "Azure AD / Microsoft login is disabled"}), 403
        client_id = auth_settings.get('oauth_microsoft_client_id')
        if not client_id:
            return jsonify({"msg": "Microsoft login is not configured properly"}), 400
    elif provider == 'saml':
        if not auth_settings.get('saml_enabled'):
            return jsonify({"msg": "SAML SSO is disabled"}), 403
        metadata_url = auth_settings.get('saml_metadata_url')
        if not metadata_url:
            return jsonify({"msg": "SAML SSO is not configured properly"}), 400
    else:
        return jsonify({"msg": "Invalid SSO provider"}), 400
        
    # Authenticate the user by email
    user = User.query.filter(User.email.ilike(email)).first()
    if not user:
        if settings.registration_open:
            # Find or create a default organization for SSO users
            from app.infrastructure.database.models.models import Organization, Role
            org = Organization.query.first()
            if not org:
                from app.domain.services.subscription_service import SubscriptionManager
                sso_trial_plan = SubscriptionManager.get_default_trial_plan()
                sso_plan_name = sso_trial_plan.name if sso_trial_plan else 'Trial'
                org = Organization(name="Default Organization", email=email, subscription_plan=sso_plan_name)
                db.session.add(org)
                db.session.flush()
                
            role = Role.query.filter_by(name='Team Member').first()
            
            # Generate a random username from email
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
                
            user = User(
                org_id=org.id,
                username=username,
                email=email,
                hashed_password=bcrypt.generate_password_hash("SSO_TEMP_PASSWORD").decode('utf-8'),
                role_id=role.id,
                is_verified=True,
                status='Active'
            )
            db.session.add(user)
            db.session.flush()
        else:
            return jsonify({"msg": "SSO user not registered on this platform. Please contact your admin."}), 404
            
    # Generate token
    from datetime import datetime, timedelta
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "org_id": user.org_id,
            "role": user.role.name,
            "dept_id": user.department_id
        },
        expires_delta=timedelta(hours=int(auth_settings.get('jwt_expiry_hours', 24)))
    )
    
    # Update last login
    user.last_login = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.commit()
    
    resp = jsonify({
        "access_token": access_token,
        "org_id": user.org_id,
        "org_name": user.organization.name if user.organization else None,
        "role": user.role.name,
        "username": user.username,
        "id": user.id,
        "org_primary_color": user.organization.primary_color if user.organization else None,
        "org_logo_url": user.organization.logo_url if user.organization else None
    })
    set_access_cookies(resp, access_token)
    return resp, 200


@auth_bp.route('/maintenance-status', methods=['GET'])
def maintenance_status():
    from app.infrastructure.database.models.models import PlatformSettings
    from sqlalchemy import text
    row = db.session.execute(
        text("SELECT maintenance_mode, maintenance_settings FROM platform_settings ORDER BY id ASC LIMIT 1")
    ).fetchone()
    if not row:
        return jsonify({"maintenance_mode": False}), 200

    maint_mode = bool(row[0]) if row[0] is not None else False
    import json as _json
    try:
        maint_settings = _json.loads(row[1]) if isinstance(row[1], str) else (row[1] or {})
    except Exception:
        maint_settings = {}
    return jsonify({
        "maintenance_mode": maint_mode,
        "message": maint_settings.get("maintenance_message") or "The system is currently undergoing scheduled maintenance. Please try again later.",
        "eta": maint_settings.get("estimated_completion") or ""
    }), 200

