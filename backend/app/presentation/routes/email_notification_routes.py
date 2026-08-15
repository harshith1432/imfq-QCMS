from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.infrastructure.database.models.models import (
    User, Organization, SaaSPlan, EmailNotificationRule, EmailNotificationLog
)
from app.domain.services.email_notification_engine import EmailNotificationEngine, DEFAULT_NOTIFICATION_PRESETS
from app.domain.services.document_branding_service import DocumentBrandingService

email_notification_bp = Blueprint('email_notifications', __name__, url_prefix='/api/email-notifications')


def _get_current_user():
    uid = get_jwt_identity()
    return db.session.get(User, uid) if uid else None


def _require_super_admin(user):
    if not user:
        return jsonify({"message": "Unauthorized"}), 401
    role_name = user.role.name if (user.role and hasattr(user.role, 'name')) else str(getattr(user, 'role', ''))
    if role_name not in ['SuperAdmin', 'Owner', 'Platform Admin']:
        return jsonify({"message": "Forbidden. Super Admin access required."}), 403
    return None


@email_notification_bp.route('/rules', methods=['GET'])
@jwt_required()
def list_notification_rules():
    user = _get_current_user()
    err = _require_super_admin(user)
    if err: return err

    # Ensure system presets are seeded
    EmailNotificationEngine.seed_default_presets()

    category = request.args.get('category', '').strip()
    status_filter = request.args.get('status', '').strip() # 'active', 'paused'
    search_q = request.args.get('q', '').strip()

    query = EmailNotificationRule.query

    if category:
        query = query.filter_by(category=category)
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'paused':
        query = query.filter_by(is_active=False)
    if search_q:
        query = query.filter(EmailNotificationRule.name.ilike(f'%{search_q}%') | EmailNotificationRule.subject.ilike(f'%{search_q}%'))

    rules = query.order_by(EmailNotificationRule.is_system_preset.desc(), EmailNotificationRule.created_at.desc()).all()
    
    # Calculate summary metrics
    total_rules = EmailNotificationRule.query.count()
    active_rules = EmailNotificationRule.query.filter_by(is_active=True).count()
    total_delivered = db.session.query(db.func.sum(EmailNotificationRule.total_sent)).scalar() or 0
    total_logs = EmailNotificationLog.query.count()

    return jsonify({
        "status": "success",
        "data": [r.to_dict() for r in rules],
        "metrics": {
            "total_rules": total_rules,
            "active_rules": active_rules,
            "paused_rules": total_rules - active_rules,
            "total_delivered": int(total_delivered),
            "total_logs": total_logs
        }
    }), 200


@email_notification_bp.route('/rules', methods=['POST'])
@jwt_required()
def create_notification_rule():
    user = _get_current_user()
    err = _require_super_admin(user)
    if err: return err

    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    subject = (data.get('subject') or '').strip()
    body_html = (data.get('body_html') or '').strip()

    if not name or not subject or not body_html:
        return jsonify({"status": "error", "message": "Name, Subject, and Body HTML are required fields."}), 400

    scheduled_at = None
    if data.get('scheduled_at'):
        try:
            scheduled_at = datetime.fromisoformat(data['scheduled_at'].replace('Z', ''))
        except Exception:
            pass

    cat = data.get('category', 'custom')
    branding_sender = EmailNotificationEngine.get_sender_from_branding(cat)

    rule = EmailNotificationRule(
        name=name,
        category=cat,
        description=data.get('description', ''),
        subject=subject,
        preheader=data.get('preheader', ''),
        heading=data.get('heading', ''),
        body_html=body_html,
        banner_color=data.get('banner_color', '#2563eb'),
        cta_text=data.get('cta_text', ''),
        cta_url=data.get('cta_url', ''),
        sender_email=data.get('sender_email') or branding_sender.get('email', 'info@ifqm.org.in'),
        sender_name=data.get('sender_name') or branding_sender.get('name', 'QCMS Notifications'),
        reply_to=data.get('reply_to') or branding_sender.get('reply_to', 'support@ifqm.org.in'),
        trigger_type=data.get('trigger_type', 'manual'),
        event_trigger=data.get('event_trigger', ''),
        trigger_days_before=int(data.get('trigger_days_before') or 7),
        scheduled_at=scheduled_at,
        target_audience_type=data.get('target_audience_type', 'all'),
        target_org_ids=data.get('target_org_ids', []),
        target_roles=data.get('target_roles', []),
        target_plans=data.get('target_plans', []),
        target_statuses=data.get('target_statuses', []),
        is_active=bool(data.get('is_active', True)),
        is_system_preset=False,
        created_by_id=user.id
    )

    db.session.add(rule)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Email notification rule created successfully.",
        "data": rule.to_dict()
    }), 201


@email_notification_bp.route('/rules/<int:rule_id>', methods=['GET'])
@jwt_required()
def get_notification_rule(rule_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err: return err

    rule = db.session.get(EmailNotificationRule, rule_id)
    if not rule:
        return jsonify({"status": "error", "message": "Rule not found"}), 404

    return jsonify({"status": "success", "data": rule.to_dict()}), 200


@email_notification_bp.route('/rules/<int:rule_id>', methods=['PUT'])
@jwt_required()
def update_notification_rule(rule_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err: return err

    rule = db.session.get(EmailNotificationRule, rule_id)
    if not rule:
        return jsonify({"status": "error", "message": "Rule not found"}), 404

    data = request.get_json() or {}

    if 'name' in data: rule.name = (data['name'] or '').strip()
    if 'category' in data: rule.category = data['category']
    if 'description' in data: rule.description = data['description']
    if 'subject' in data: rule.subject = (data['subject'] or '').strip()
    if 'preheader' in data: rule.preheader = data['preheader']
    if 'heading' in data: rule.heading = data['heading']
    if 'body_html' in data: rule.body_html = data['body_html']
    if 'banner_color' in data: rule.banner_color = data['banner_color']
    if 'cta_text' in data: rule.cta_text = data['cta_text']
    if 'cta_url' in data: rule.cta_url = data['cta_url']
    if 'sender_email' in data: rule.sender_email = data['sender_email']
    if 'sender_name' in data: rule.sender_name = data['sender_name']
    if 'reply_to' in data: rule.reply_to = data['reply_to']
    if 'trigger_type' in data: rule.trigger_type = data['trigger_type']
    if 'event_trigger' in data: rule.event_trigger = data['event_trigger']
    if 'trigger_days_before' in data: rule.trigger_days_before = int(data['trigger_days_before'] or 7)
    if 'target_audience_type' in data: rule.target_audience_type = data['target_audience_type']
    if 'target_org_ids' in data: rule.target_org_ids = data['target_org_ids']
    if 'target_roles' in data: rule.target_roles = data['target_roles']
    if 'target_plans' in data: rule.target_plans = data['target_plans']
    if 'target_statuses' in data: rule.target_statuses = data['target_statuses']
    if 'is_active' in data: rule.is_active = bool(data['is_active'])

    if 'scheduled_at' in data:
        if data['scheduled_at']:
            try:
                rule.scheduled_at = datetime.fromisoformat(data['scheduled_at'].replace('Z', ''))
            except Exception:
                pass
        else:
            rule.scheduled_at = None

    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Email notification rule updated successfully.",
        "data": rule.to_dict()
    }), 200


@email_notification_bp.route('/rules/<int:rule_id>', methods=['DELETE'])
@jwt_required()
def delete_notification_rule(rule_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err: return err

    rule = db.session.get(EmailNotificationRule, rule_id)
    if not rule:
        return jsonify({"status": "error", "message": "Rule not found"}), 404

    db.session.delete(rule)
    db.session.commit()

    return jsonify({"status": "success", "message": "Rule deleted successfully."}), 200


@email_notification_bp.route('/rules/<int:rule_id>/toggle', methods=['POST'])
@jwt_required()
def toggle_notification_rule(rule_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err: return err

    rule = db.session.get(EmailNotificationRule, rule_id)
    if not rule:
        return jsonify({"status": "error", "message": "Rule not found"}), 404

    rule.is_active = not rule.is_active
    db.session.commit()

    status_str = "Active" if rule.is_active else "Paused"
    return jsonify({
        "status": "success",
        "message": f"Rule '{rule.name}' is now {status_str}.",
        "is_active": rule.is_active
    }), 200


@email_notification_bp.route('/rules/<int:rule_id>/send-test', methods=['POST'])
@jwt_required()
def send_test_email_notification(rule_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err: return err

    data = request.get_json() or {}
    test_email = (data.get('email') or (user.email if user else '')).strip()

    if not test_email:
        return jsonify({"status": "error", "message": "Target test email address is required."}), 400

    res = EmailNotificationEngine.send_rule_notification(rule_id, test_email=test_email, current_user_id=user.id)
    return jsonify(res), (200 if res.get('status') == 'success' else 400)


@email_notification_bp.route('/rules/<int:rule_id>/recipients', methods=['GET'])
@jwt_required()
def get_rule_recipients(rule_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err: return err

    rule = db.session.get(EmailNotificationRule, rule_id)
    if not rule:
        return jsonify({"status": "error", "message": "Notification rule not found"}), 404

    recipients = EmailNotificationEngine.resolve_recipients(rule)
    branding_sender = EmailNotificationEngine.get_sender_from_branding(rule.category)
    sender_addr = rule.sender_email if (rule.sender_email and not rule.sender_email.endswith('@qcms.com')) else branding_sender['email']
    sender_name = rule.sender_name if (rule.sender_name and not rule.sender_name.startswith('QCMS ')) else branding_sender['name']

    return jsonify({
        "status": "success",
        "rule_id": rule.id,
        "rule_name": rule.name,
        "subject": rule.subject,
        "sender_email": sender_addr,
        "sender_name": sender_name,
        "target_roles": rule.target_roles or ['All'],
        "target_statuses": rule.target_statuses or ['All'],
        "target_audience_type": rule.target_audience_type or 'all',
        "admin_email": user.email,
        "total_recipients": len(recipients),
        "recipients": [
            {
                "user_id": r.get('user_id'),
                "email": r.get('email'),
                "name": r.get('name'),
                "role": r.get('context', {}).get('role_name', 'User'),
                "org_name": r.get('org_name'),
                "org_id": r.get('org_id')
            }
            for r in recipients
        ]
    }), 200


@email_notification_bp.route('/rules/<int:rule_id>/trigger-now', methods=['POST'])
@jwt_required()
def trigger_notification_broadcast(rule_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err: return err

    data = request.get_json() or {}
    include_admin = bool(data.get('include_current_admin', False))

    res = EmailNotificationEngine.send_rule_notification(
        rule_id,
        current_user_id=user.id,
        include_current_admin=include_admin,
        admin_email=user.email
    )
    return jsonify(res), (200 if res.get('status') in ['success', 'warning', 'info'] else 400)


@email_notification_bp.route('/preview', methods=['POST'])
@jwt_required()
def preview_email_html():
    user = _get_current_user()
    err = _require_super_admin(user)
    if err: return err

    data = request.get_json() or {}
    context = data.get('context', {})
    
    html = EmailNotificationEngine.generate_html_email(data, context)
    return jsonify({"status": "success", "html": html}), 200


@email_notification_bp.route('/logs', methods=['GET'])
@jwt_required()
def get_notification_logs():
    user = _get_current_user()
    err = _require_super_admin(user)
    if err: return err

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    search_q = request.args.get('q', '').strip()

    query = EmailNotificationLog.query

    if search_q:
        query = query.filter(
            EmailNotificationLog.rule_name.ilike(f'%{search_q}%') |
            EmailNotificationLog.subject.ilike(f'%{search_q}%') |
            EmailNotificationLog.sender_email.ilike(f'%{search_q}%')
        )

    pagination = query.order_by(EmailNotificationLog.sent_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "status": "success",
        "data": [l.to_dict() for l in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages
    }), 200


@email_notification_bp.route('/meta', methods=['GET'])
@jwt_required()
def get_notification_meta():
    """Metadata helper for populating dropdowns and filters in the notification builder."""
    user = _get_current_user()
    err = _require_super_admin(user)
    if err: return err

    orgs = Organization.query.filter_by(is_deleted=False).order_by(Organization.name.asc()).all()
    plans = SaaSPlan.query.filter_by(status='Active').all()
    branding = DocumentBrandingService.get_branding_context()

    contact_directory_channels = [
        {"key": "general", "label": "General Info", "email": branding.get('general_email', 'info@ifqm.org.in'), "name": branding.get('general_sender_name', 'info')},
        {"key": "billing", "label": "Billing & Accounts", "email": branding.get('billing_email', 'billing@ifqm.org.in'), "name": branding.get('billing_sender_name', 'Invoice and billing')},
        {"key": "support", "label": "Customer Support", "email": branding.get('support_email', 'support@ifqm.org.in'), "name": branding.get('support_sender_name', 'Support desk desk')},
        {"key": "onboarding", "label": "Onboarding & Welcome", "email": branding.get('onboarding_email', 'on-boarding@ifqm.org.in'), "name": branding.get('onboarding_sender_name', 'Welcome to IFQM')},
        {"key": "alerts", "label": "System Alerts & Maintenance", "email": branding.get('alerts_email', 'alert@ifqm.org.in'), "name": branding.get('alerts_sender_name', 'Emergency alert')},
        {"key": "security", "label": "Security & OTP", "email": branding.get('otp_email', 'noreplay12@ifqm.org.in'), "name": branding.get('otp_sender_name', 'Notification OTP verification')},
        {"key": "contact", "label": "Contact / Inquiry", "email": branding.get('contact_email', 'contact@ifqm.org.in'), "name": branding.get('contact_sender_name', 'Customer support')},
        {"key": "feedback", "label": "Product Feedback", "email": branding.get('feedback_email', 'feedback@ifqm.org.in'), "name": branding.get('feedback_sender_name', 'Feedback')}
    ]

    sender_suggestions = [
        {"email": c["email"], "name": c["name"], "category": c["label"], "key": c["key"]}
        for c in contact_directory_channels if c.get("email")
    ]

    return jsonify({
        "status": "success",
        "branding": {
            "software_name": branding.get('software_name', 'QCMS Enterprise OS'),
            "software_short_name": branding.get('software_short_name', 'QCMS'),
            "support_email": branding.get('support_email', 'support@ifqm.org.in'),
            "general_email": branding.get('general_email', 'info@ifqm.org.in'),
            "contact_directory": contact_directory_channels
        },
        "organizations": [{"id": o.id, "name": o.name, "code": o.org_code, "status": o.subscription_status} for o in orgs],
        "plans": [{"id": p.id, "name": p.name, "code": p.code} for p in plans if not p.is_default_trial],
        "roles": ["All", "Admin", "CEO", "Reviewer", "Facilitator", "Team Member"],
        "subscription_statuses": ["Active", "Trial", "Expiring", "Suspended"],
        "categories": [
            {"key": "subscription_reminder", "label": "Subscription Expiry Reminder", "icon": "clock", "color": "#2563eb", "channel": "billing"},
            {"key": "trial_reminder", "label": "Trial Ending Alert", "icon": "hourglass", "color": "#d97706", "channel": "onboarding"},
            {"key": "maintenance", "label": "Software Maintenance Notice", "icon": "wrench", "color": "#4f46e5", "channel": "alerts"},
            {"key": "welcome", "label": "Welcome & Onboarding Email", "icon": "sparkles", "color": "#16a34a", "channel": "onboarding"},
            {"key": "usage_guide", "label": "Software Usage & How-to Guide", "icon": "book-open", "color": "#0284c7", "channel": "general"},
            {"key": "new_feature", "label": "New Features & Release Notes", "icon": "zap", "color": "#8b5cf6", "channel": "general"},
            {"key": "support", "label": "Customer Support Check-in", "icon": "life-buoy", "color": "#0d9488", "channel": "support"},
            {"key": "custom", "label": "Custom Email Broadcast", "icon": "mail", "color": "#64748b", "channel": "general"}
        ],
        "contact_directory_channels": contact_directory_channels,
        "sender_suggestions": sender_suggestions,
        "available_variables": [
            {"tag": "{{org_name}}", "label": "Organization Name", "example": "Acme Manufacturing Ltd."},
            {"tag": "{{user_name}}", "label": "Recipient User Name", "example": "John Doe"},
            {"tag": "{{user_email}}", "label": "Recipient Email Address", "example": "john@acme.com"},
            {"tag": "{{role_name}}", "label": "User Role", "example": "Company Admin"},
            {"tag": "{{plan_name}}", "label": "Subscription Plan", "example": "Small MSME's Plan"},
            {"tag": "{{trial_days}}", "label": "Trial Days Duration", "example": "14"},
            {"tag": "{{trial_end_date}}", "label": "Trial Expiration Date", "example": "28 Aug 2026"},
            {"tag": "{{max_users}}", "label": "Max Team Capacity", "example": "50"},
            {"tag": "{{storage_limit_mb}}", "label": "Cloud Storage Limit (MB)", "example": "5120"},
            {"tag": "{{industry}}", "label": "Industry Sector", "example": "Automotive Quality"},
            {"tag": "{{expiry_date}}", "label": "Expiry Date", "example": "21 Aug 2026"},
            {"tag": "{{days_left}}", "label": "Days Left Until Expiry", "example": "7"},
            {"tag": "{{support_email}}", "label": "Support Desk Email", "example": "support@ifqm.org.in"},
            {"tag": "{{app_url}}", "label": "Application URL", "example": "http://127.0.0.1:5000"},
            {"tag": "{{cta_url}}", "label": "Action Button Link", "example": "/admin/settings.html?tab=billing"},
            {"tag": "{{cta_text}}", "label": "Action Button Text", "example": "Renew Subscription"}
        ]
    }), 200
