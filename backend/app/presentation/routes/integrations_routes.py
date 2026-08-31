from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.infrastructure.database.models.models import (
    db, User, IntegrationConfig, IntegrationApiKey, 
    IntegrationWebhook, IntegrationWebhookDelivery, IntegrationAuditLog
)
from datetime import datetime, timedelta, timezone
import secrets
import hashlib

integrations_bp = Blueprint('integrations', __name__)

# Helper to hash API keys securely
def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

# Helper to seed default integration cards if none exist
def seed_default_integrations():
    """Ensure all default integration providers exist in the database with unconfigured/empty credentials."""
    from sqlalchemy.orm.attributes import flag_modified
    import json

    # Remove deprecated / unneeded / removed providers
    to_remove = [
        "stripe", "twilio_sms", "anthropic", "openai", "aws_s3", "azure_blob", 
        "firebase", "slack", "ms_teams", "zapier", "jira", "google_ai", 
        "postgresql", "api_keys", "sentry", "health_checks"
    ]
    db.session.query(IntegrationConfig).filter(IntegrationConfig.provider_id.in_(to_remove)).delete(synchronize_session=False)

    defaults = [
        # Payments
        ("razorpay", "Razorpay Gateway", "Payments", "Disconnected", "v2.0", {
            "key_id": "",
            "key_secret": "",
            "webhook_secret": "",
            "currency": "INR",
            "is_active": False
        }),
        ("dynamic_qr", "Dynamic QR Gateway", "Payments", "Disconnected", "v1.0", {
            "upi_id": "",
            "account_name": "",
            "qr_code_url": "",
            "instructions": "",
            "is_active": False
        }),

        # Communication
        ("resend", "Resend Mail", "Communication", "Disconnected", "v1.3.0", {
            "sender_email": "",
            "sender_name": "",
            "api_key": "",
            "is_active": False
        }),
        ("jio_dlt", "Jio DLT SMS OTP", "Communication", "Disconnected", "v1.0.0", {
            "entity_id": "",
            "sender_id": "",
            "template_id": "",
            "api_key": "",
            "api_url": "https://api.jiodlt.com/sms/v1/send",
            "is_active": False
        }),
        ("zeptomail", "ZeptoMail (Zoho)", "Communication", "Disconnected", "v1.0.0", {
            "api_key": "",
            "sender_email": "",
            "sender_name": "",
            "api_url": "https://api.zeptomail.in/v1.1/email",
            "is_active": False
        })
    ]
    
    # Values that were previously seeded as fake defaults
    fake_markers = ["qcms_enterprise_key", "secret_qcms", "qcms@upi", "notifications@qcms.io", "re_abc123xyz", "1101234567890123456", "QCMOTP", "jio_live_auth", "Zoho-enczapikey_live_secret_key_887766", "otp@qcms.io"]

    for prov_id, name, cat, default_status, ver, empty_settings in defaults:
        existing = IntegrationConfig.query.filter_by(provider_id=prov_id).first()
        if not existing:
            cfg = IntegrationConfig(
                provider_id=prov_id,
                provider_name=name,
                category=cat,
                status=default_status,
                version=ver,
                settings=empty_settings,
                health_score=0,
                usage_count=0,
                error_count=0
            )
            db.session.add(cfg)
        else:
            # Clean up old fake credentials if row still contains legacy fake markers
            settings_str = json.dumps(existing.settings or {})
            if any(fm in settings_str for fm in fake_markers):
                existing.settings = empty_settings
                existing.status = "Disconnected"
                existing.health_score = 0
                flag_modified(existing, "settings")
    
    db.session.commit()

@integrations_bp.route('/integrations/email-providers', methods=['GET'])
@jwt_required()
def get_email_providers():
    """Return Communication-category integrations for use in announcement email channel selection."""
    seed_default_integrations()
    email_configs = IntegrationConfig.query.filter_by(category='Communication', status='Connected').all()
    result = []
    for c in email_configs:
        if c.provider_id in ['jio_dlt', 'twilio_sms', 'dlt_sms']:
            continue
        settings = c.settings or {}
        result.append({
            "provider_id": c.provider_id,
            "provider_name": c.provider_name,
            "status": c.status,
            "sender_email": settings.get('sender_email') or settings.get('api_url', ''),
            "sender_name": settings.get('sender_name', ''),
        })
    return jsonify({"status": "success", "data": result}), 200

@integrations_bp.route('/integrations/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    # Make sure default integrations are seeded
    seed_default_integrations()
    
    total_int = IntegrationConfig.query.count()
    active_int = IntegrationConfig.query.filter_by(status='Connected').count()
    failed_int = IntegrationConfig.query.filter_by(status='Error').count()
    
    connected_connector_keys = active_int
    active_dev_keys = IntegrationApiKey.query.filter_by(status='Active').count()
    active_keys = connected_connector_keys + active_dev_keys
    expired_keys = IntegrationApiKey.query.filter_by(status='Disabled').count()
    
    # Real-time counts computed from database logs for today
    today_start = datetime.now(timezone.utc).replace(tzinfo=None).replace(hour=0, minute=0, second=0, microsecond=0)
    
    from app.infrastructure.database.models.models import IntegrationApiLog
    api_requests_today = IntegrationApiLog.query.filter(IntegrationApiLog.request_time >= today_start).count()
    webhook_deliveries_today = IntegrationWebhookDelivery.query.filter(IntegrationWebhookDelivery.created_at >= today_start).count()
    
    total_webhooks = IntegrationWebhook.query.count()
    failed_webhooks = IntegrationWebhookDelivery.query.filter_by(status='Failed').count()
    
    return jsonify({
        "total_integrations": total_int,
        "active_integrations": active_int,
        "failed_integrations": failed_int,
        "api_requests_today": api_requests_today,
        "webhook_deliveries_today": webhook_deliveries_today,
        "email_sent_today": 0,
        "whatsapp_sent_today": 0,
        "sms_sent_today": 0,
        "active_api_keys": active_keys,
        "expired_api_keys": expired_keys,
        "failed_webhooks": failed_webhooks
    }), 200

@integrations_bp.route('/integrations', methods=['GET'])
@jwt_required()
def list_integrations():
    seed_default_integrations()
    configs = IntegrationConfig.query.all()
    
    result = []
    for c in configs:
        result.append({
            "id": c.id,
            "provider_id": c.provider_id,
            "provider_name": c.provider_name,
            "category": c.category,
            "status": c.status,
            "version": c.version,
            "health_score": c.health_score,
            "last_sync": c.last_sync.isoformat() + "Z" if c.last_sync else None,
            "usage_count": c.usage_count,
            "error_count": c.error_count,
            "settings": c.settings
        })
    return jsonify(result), 200

@integrations_bp.route('/integrations/<provider_id>/config', methods=['POST'])
@jwt_required()
def save_config(provider_id):
    cfg = IntegrationConfig.query.filter_by(provider_id=provider_id).first()
    if not cfg:
        return jsonify({"error": f"Integration provider '{provider_id}' not found"}), 404
        
    data = request.get_json() or {}
    
    # Save settings directly to database JSON column
    if 'settings' in data:
        new_settings = dict(data['settings'])
        cfg.settings = new_settings
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(cfg, "settings")

    if 'status' in data:
        cfg.status = data['status']
        if cfg.status == 'Connected':
            cfg.health_score = 100
        elif cfg.status in ['Disabled', 'Disconnected']:
            cfg.health_score = 0
        
    cfg.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    action_label = "Credential Update" if 'settings' in data else "Status Toggle"
    audit = IntegrationAuditLog(
        action=action_label, 
        provider_id=provider_id, 
        details={"status": cfg.status, "updated_fields": list(data.get('settings', {}).keys()) if 'settings' in data else ["status"]}
    )
    db.session.add(audit)
    db.session.commit()
    
    return jsonify({"message": f"Configuration saved for '{provider_id}'", "status": cfg.status, "health_score": cfg.health_score, "settings": cfg.settings}), 200


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: test_connection (Lines 220-412)
# Reason: Unused third-party integration test runner.
# ==============================================================================
# @integrations_bp.route('/integrations/<provider_id>/test', methods=['POST'])
# @jwt_required()
# def test_connection(provider_id):
#     cfg = IntegrationConfig.query.filter_by(provider_id=provider_id).first()
#     if not cfg:
#         return jsonify({"error": f"Integration provider '{provider_id}' not found"}), 404

#     # Simulate a connection check depending on provider settings
#     settings = cfg.settings or {}
#     success = True
#     message = "Connection verified successfully!"
#     latency = secrets.randbelow(150) + 50 # 50-200ms

#     if provider_id == 'resend':
#         key = settings.get('api_key', '')
#         email = settings.get('sender_email', '')
#         if not key or not key.startswith('re_'):
#             success = False
#             message = "Invalid Resend API Token. Must start with 're_'"
#         elif '@' not in email or '.' not in email:
#             success = False
#             message = "Invalid Sender Email format."

#     elif provider_id == 'jio_dlt':
#         entity_id = settings.get('entity_id', '')
#         sender_id = settings.get('sender_id', '')
#         template_id = settings.get('template_id', '')
#         api_key = settings.get('api_key', '')
#         if not entity_id or len(entity_id) < 5:
#             success = False
#             message = "Invalid Jio DLT Principal Entity ID. Entity ID is required."
#         elif not sender_id or len(sender_id) > 10:
#             success = False
#             message = "Invalid Sender / Header ID. Must be 3-6 characters (e.g. QCMOTP)."
#         elif not template_id or len(template_id) < 5:
#             success = False
#             message = "Invalid DLT Content Template ID."
#         elif not api_key or len(api_key) < 5:
#             success = False
#             message = "Jio DLT API Auth Key is required."

#     elif provider_id == 'zeptomail':
#         api_key = settings.get('api_key', '')
#         sender_email = settings.get('sender_email', '')
#         if not api_key or len(api_key) < 8:
#             success = False
#             message = "Invalid ZeptoMail Send Mail Token. Token is required (e.g., Zoho-enczapikey...)."
#         elif not sender_email or '@' not in sender_email or '.' not in sender_email:
#             success = False
#             message = "Invalid Verified Sender Email Address."

#     elif provider_id == 'twilio_sms':
#         sid = settings.get('account_sid', '')
#         token = settings.get('auth_token', '')
#         if not sid or not sid.startswith('AC') or len(sid) != 34:
#             success = False
#             message = "Invalid Twilio Account SID. Must start with 'AC' and be 34 characters."
#         elif not token or len(token) < 16:
#             success = False
#             message = "Invalid Twilio Auth Token length."

#     elif provider_id == 'meta_whatsapp':
#         pid = settings.get('phone_number_id', '')
#         token = settings.get('access_token', '')
#         if not pid or not pid.isdigit():
#             success = False
#             message = "Invalid Phone Number ID. Must be numeric."
#         elif not token or len(token) < 16:
#             success = False
#             message = "Invalid Meta access token."

#     elif provider_id == 'google_oauth':
#         cid = settings.get('client_id', '')
#         sec = settings.get('client_secret', '')
#         if not cid or 'googleusercontent.com' not in cid:
#             success = False
#             message = "Invalid Google Client ID. Must contain 'googleusercontent.com'"
#         elif not sec or len(sec) < 8:
#             success = False
#             message = "Google Client Secret is too short."

#     elif provider_id == 'firebase_auth':
#         pid = settings.get('project_id', '')
#         key = settings.get('api_key', '')
#         if not pid or len(pid) < 3:
#             success = False
#             message = "Invalid Firebase Project ID."
#         elif not key or not key.startswith('AIzaSy'):
#             success = False
#             message = "Invalid Firebase API Key. Must start with 'AIzaSy'"

#     elif provider_id == 'openai':
#         key = settings.get('api_key', '')
#         if not key or not key.startswith('sk-'):
#             success = False
#             message = "Invalid OpenAI API Key format. Must start with 'sk-'"

#     elif provider_id == 'google_gemini':
#         key = settings.get('api_key', '')
#         if not key or not key.startswith('AIzaSy'):
#             success = False
#             message = "Invalid Google Gemini API Key. Must start with 'AIzaSy'"

#     elif provider_id == 'aws_s3':
#         bucket = settings.get('bucket_name', '')
#         reg = settings.get('region', '')
#         ak = settings.get('access_key_id', '')
#         sk = settings.get('secret_access_key', '')
#         if not bucket:
#             success = False
#             message = "S3 bucket name cannot be empty."
#         elif len(reg) < 3:
#             success = False
#             message = "Invalid AWS region code."
#         elif not ak or not ak.startswith('AKIA'):
#             success = False
#             message = "Invalid Access Key ID. Must start with 'AKIA'"
#         elif not sk or len(sk) < 20:
#             success = False
#             message = "AWS Secret Access Key is invalid."

#     elif provider_id == 'postgresql':
#         host = settings.get('host', '')
#         port = settings.get('port')
#         db_name = settings.get('database', '')
#         if not host or len(host) < 3:
#             success = False
#             message = "Database hostname is required."
#         elif not port or not str(port).isdigit() or not (1 <= int(port) <= 65535):
#             success = False
#             message = "Invalid host port configuration (1 - 65535)."
#         elif not db_name or len(db_name) < 2:
#             success = False
#             message = "Logical database name is required."

#     elif provider_id == 'stripe':
#         pk = settings.get('public_key', '')
#         sk = settings.get('secret_key', '')
#         if not pk or not pk.startswith('pk_'):
#             success = False
#             message = "Invalid Stripe Public Key. Must start with 'pk_'"
#         elif not sk or not sk.startswith('sk_'):
#             success = False
#             message = "Invalid Stripe Secret Key. Must start with 'sk_'"

#     elif provider_id == 'google_analytics':
#         mid = settings.get('measurement_id', '')
#         if not mid or not mid.startswith('G-'):
#             success = False
#             message = "Invalid GA4 Measurement ID. Must start with 'G-'"

#     elif provider_id == 'sentry':
#         dsn = settings.get('dsn_url', '')
#         if not dsn or not dsn.startswith('https://') or '@' not in dsn or 'sentry.io' not in dsn:
#             success = False
#             message = "Invalid Sentry DSN URL format."

#     elif provider_id == 'google_maps':
#         key = settings.get('api_key', '')
#         if not key or not key.startswith('AIzaSy'):
#             success = False
#             message = "Invalid Google Maps API Key. Must start with 'AIzaSy'"

#     elif provider_id == 'health_checks':
#         interval = settings.get('heartbeat_interval')
#         if not interval or not str(interval).isdigit() or not (5 <= int(interval) <= 3600):
#             success = False
#             message = "Heartbeat interval must be an integer between 5 and 3600 seconds."

#     if success:
#         cfg.status = 'Connected'
#         cfg.health_score = min(100, cfg.health_score + 5)
#     else:
#         cfg.status = 'Error'
#         cfg.health_score = max(0, cfg.health_score - 20)
#         cfg.error_count += 1

#     # Audit log
#     audit = IntegrationAuditLog(
#         action="Test Connection", 
#         provider_id=provider_id, 
#         details={"success": success, "message": message, "latency_ms": latency}
#     )
#     db.session.add(audit)
#     db.session.commit()

#     return jsonify({
#         "success": success,
#         "message": message,
#         "latency_ms": latency,
#         "status": cfg.status,
#         "health_score": cfg.health_score
#     }), 200
# [END DEAD CODE: test_connection]


@integrations_bp.route('/integrations/<provider_id>/rotate', methods=['POST'])
@jwt_required()
def rotate_secrets(provider_id):
    cfg = IntegrationConfig.query.filter_by(provider_id=provider_id).first()
    if not cfg:
        return jsonify({"error": "Provider not found"}), 404
        
    # Generate new webhook secret or similar settings field
    settings = cfg.settings or {}
    new_secret = "whsec_" + secrets.token_hex(16)
    settings['webhook_secret'] = new_secret
    cfg.settings = settings
    
    audit = IntegrationAuditLog(action="Secret Rotation", provider_id=provider_id, details={"field": "webhook_secret"})
    db.session.add(audit)
    db.session.commit()
    
    return jsonify({"message": "Webhook secret successfully rotated", "webhook_secret": new_secret}), 200

# ── API Key Management Endpoints ──────────────────────────────────────────

@integrations_bp.route('/integrations/apikeys', methods=['GET'])
@jwt_required()
def get_api_keys():
    keys = IntegrationApiKey.query.order_by(IntegrationApiKey.created_at.desc()).all()
    return jsonify([{
        "id": k.id,
        "name": k.name,
        "key_prefix": k.key_prefix,
        "secret_key_masked": k.secret_key_masked,
        "status": k.status,
        "expiration_date": k.expiration_date.isoformat() + "Z" if k.expiration_date else None,
        "rate_limit": k.rate_limit,
        "allowed_ips": k.allowed_ips,
        "allowed_domains": k.allowed_domains,
        "scopes": k.scopes,
        "owner": k.owner,
        "usage_count": k.usage_count,
        "last_used": k.last_used.isoformat() + "Z" if k.last_used else None,
        "created_at": k.created_at.isoformat() + "Z"
    } for k in keys]), 200

@integrations_bp.route('/integrations/apikeys', methods=['POST'])
@jwt_required()
def generate_api_key():
    data = request.get_json() or {}
    name = data.get('name', 'New API Key')
    rate_limit = int(data.get('rate_limit', 60))
    allowed_ips = data.get('allowed_ips', [])
    allowed_domains = data.get('allowed_domains', [])
    scopes = data.get('scopes', ['read', 'write'])
    owner = data.get('owner', 'Super Admin')
    
    # Generate live credentials
    raw_key = "qc_live_" + secrets.token_urlsafe(32)
    key_hash = hash_key(raw_key)
    masked = raw_key[:12] + "..." + raw_key[-4:]
    
    expiration = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=365) # 1 year expiry
    
    new_key = IntegrationApiKey(
        name=name,
        key_prefix="qc_live_",
        api_key_hash=key_hash,
        secret_key_masked=masked,
        status='Active',
        expiration_date=expiration,
        rate_limit=rate_limit,
        allowed_ips=allowed_ips,
        allowed_domains=allowed_domains,
        scopes=scopes,
        owner=owner
    )
    
    db.session.add(new_key)
    
    # Audit log
    audit = IntegrationAuditLog(action="API Key Generation", provider_id="api_keys", details={"name": name, "owner": owner})
    db.session.add(audit)
    db.session.commit()
    
    # Return the raw key ONLY once
    return jsonify({
        "id": new_key.id,
        "name": new_key.name,
        "api_key": raw_key,
        "secret_key_masked": masked,
        "expiration_date": expiration.isoformat() + "Z",
        "status": new_key.status
    }), 201

@integrations_bp.route('/integrations/apikeys/<int:key_id>/status', methods=['POST'])
@jwt_required()
def change_api_key_status(key_id):
    key = db.session.get(IntegrationApiKey, key_id)
    if not key:
        return jsonify({"error": "API Key not found"}), 404
        
    data = request.get_json() or {}
    status = data.get('status', 'Active')
    
    key.status = status
    if status == 'Disabled' or status == 'Revoked':
        action = "API Key Revocation"
    else:
        action = "API Key Activation"
        
    audit = IntegrationAuditLog(action=action, provider_id="api_keys", details={"key_id": key_id, "name": key.name})
    db.session.add(audit)
    db.session.commit()
    
    return jsonify({"message": f"API Key status updated to '{status}'", "status": key.status}), 200

# ── Webhook Management Endpoints ──────────────────────────────────────────

@integrations_bp.route('/integrations/webhooks', methods=['GET'])
@jwt_required()
def get_webhooks():
    webhooks = IntegrationWebhook.query.all()
    return jsonify([{
        "id": w.id,
        "name": w.name,
        "url": w.url,
        "status": w.status,
        "events": w.events,
        "created_at": w.created_at.isoformat() + "Z"
    } for w in webhooks]), 200

@integrations_bp.route('/integrations/webhooks', methods=['POST'])
@jwt_required()
def create_webhook():
    data = request.get_json() or {}
    name = data.get('name', 'Webhook Endpoint')
    url = data.get('url')
    events = data.get('events', ['*'])
    
    if not url:
        return jsonify({"error": "Webhook endpoint URL is required"}), 400
        
    secret = "whsec_" + secrets.token_hex(16)
    
    new_wh = IntegrationWebhook(
        name=name,
        url=url,
        secret=secret,
        status='Active',
        headers={"Content-Type": "application/json"},
        events=events
    )
    
    db.session.add(new_wh)
    
    audit = IntegrationAuditLog(action="Webhook Update", provider_id="webhooks_mgr", details={"name": name, "url": url})
    db.session.add(audit)
    db.session.commit()
    
    return jsonify({
        "id": new_wh.id,
        "name": new_wh.name,
        "url": new_wh.url,
        "secret": secret,
        "status": new_wh.status,
        "events": new_wh.events
    }), 201

@integrations_bp.route('/integrations/webhooks/<int:webhook_id>', methods=['DELETE'])
@jwt_required()
def delete_webhook(webhook_id):
    wh = db.session.get(IntegrationWebhook, webhook_id)
    if not wh:
        return jsonify({"error": "Webhook not found"}), 404
        
    db.session.delete(wh)
    audit = IntegrationAuditLog(action="Webhook Delete", provider_id="webhooks_mgr", details={"webhook_id": webhook_id, "name": wh.name})
    db.session.add(audit)
    db.session.commit()
    
    return jsonify({"message": "Webhook deleted successfully"}), 200

# ── Logging, Deliveries, Playground ───────────────────────────────────────

@integrations_bp.route('/integrations/logs', methods=['GET'])
@jwt_required()
def get_logs():
    # Return mock request logs, webhook deliveries, and audit trails
    audits = IntegrationAuditLog.query.order_by(IntegrationAuditLog.created_at.desc()).limit(50).all()
    
    webhook_deliveries = [
        {
            "id": 1,
            "event": "invoice.created",
            "url": "https://api.tenant.org/webhooks",
            "response_code": 200,
            "status": "Success",
            "latency_ms": 112.5,
            "created_at": (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=15)).isoformat() + "Z"
        },
        {
            "id": 2,
            "event": "subscription.updated",
            "url": "https://hooks.billing-sys.net/receive",
            "response_code": 500,
            "status": "Failed",
            "latency_ms": 320.0,
            "created_at": (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)).isoformat() + "Z"
        }
    ]
    
    request_logs = [
        {
            "id": 101,
            "method": "POST",
            "path": "/api/v1/subscriptions",
            "client_ip": "192.168.1.50",
            "status_code": 201,
            "latency_ms": 45.2,
            "created_at": (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)).isoformat() + "Z"
        },
        {
            "id": 102,
            "method": "GET",
            "path": "/api/v1/licenses/validate",
            "client_ip": "203.0.113.195",
            "status_code": 401,
            "latency_ms": 12.1,
            "created_at": (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=12)).isoformat() + "Z"
        }
    ]
    
    return jsonify({
        "audit_logs": [{
            "id": a.id,
            "action": a.action,
            "provider_id": a.provider_id,
            "details": a.details,
            "created_at": a.created_at.isoformat() + "Z"
        } for a in audits],
        "webhook_deliveries": webhook_deliveries,
        "request_logs": request_logs
    }), 200

# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: retry_webhook (Lines 655-665)
# Reason: Unused manual webhook retry endpoint.
# ==============================================================================
# @integrations_bp.route('/integrations/webhooks/deliveries/<int:delivery_id>/retry', methods=['POST'])
# @jwt_required()
# def retry_webhook(delivery_id):
#     # Simulate a successful webhook redelivery
#     return jsonify({
#         "success": True,
#         "message": f"Webhook delivery #{delivery_id} re-enqueued. Dispatching payload...",
#         "response_code": 200,
#         "status": "Success",
#         "latency_ms": 95.4
#     }), 200
# [END DEAD CODE: retry_webhook]


@integrations_bp.route('/integrations/playground', methods=['POST'])
@jwt_required()
def run_playground():
    data = request.get_json() or {}
    method = data.get('method', 'GET')
    endpoint = data.get('endpoint', '/api/v1/licenses')
    api_key = data.get('api_key', '')
    payload = data.get('payload', {})
    
    if not api_key:
        return jsonify({
            "status_code": 401,
            "latency_ms": 5.4,
            "response": {"error": "Unauthorized. Developer API token is missing."}
        }), 200
        
    # Simulate key check
    hashed = hash_key(api_key)
    key_record = IntegrationApiKey.query.filter_by(api_key_hash=hashed).first()
    
    # Accept mock key
    if not key_record and api_key != "qc_live_demotok12345":
        return jsonify({
            "status_code": 403,
            "latency_ms": 8.1,
            "response": {"error": "Forbidden. Invalid API key signature."}
        }), 200
        
    # Mock routing response
    latency = secrets.randbelow(80) + 10
    response_data = {}
    status_code = 200
    
    if "licenses" in endpoint:
        response_data = {
            "object": "list",
            "data": [
                {"id": 9210, "license_key": "LIC-9821-ACTIVE", "tier": "Enterprise", "expires_at": "2027-01-01T00:00:00Z"},
                {"id": 9211, "license_key": "LIC-5421-TRIAL", "tier": "Starter", "expires_at": "2026-08-15T00:00:00Z"}
            ],
            "total_count": 2
        }
    elif "subscriptions" in endpoint:
        if method == "POST":
            status_code = 201
            response_data = {
                "id": 851,
                "status": "Active",
                "organization_id": payload.get("organization_id", 3),
                "plan": payload.get("plan", "Professional"),
                "billing_cycle": "Monthly",
                "created_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
            }
        else:
            response_data = {
                "object": "list",
                "data": [
                    {"id": 40, "organization": "Globex Corp", "plan": "Enterprise", "status": "Active"},
                    {"id": 41, "organization": "Initech LLC", "plan": "Starter", "status": "Trial"}
                ]
            }
    else:
        response_data = {
            "message": "Ping received. Sandbox environment is active."
        }
        
    return jsonify({
        "status_code": status_code,
        "latency_ms": latency,
        "response": response_data
    }), 200
