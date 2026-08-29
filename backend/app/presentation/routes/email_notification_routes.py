from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.infrastructure.database.models.models import (
    User, Organization, SaaSPlan, EmailNotificationRule, EmailNotificationLog, SmsTemplateConfig, SmsNotificationLog
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
        created_by_id=user.id,
        # SMS Configuration (Gio DLT)
        sms_enabled=bool(data.get('sms_enabled', False)),
        sms_template_id=(data.get('sms_template_id') or '').strip() or None,
        sms_entity_id=(data.get('sms_entity_id') or '').strip() or None,
        sms_sender_id=(data.get('sms_sender_id') or '').strip() or None,
        sms_body=(data.get('sms_body') or '').strip() or None,
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
    # SMS Configuration (Gio DLT)
    if 'sms_enabled' in data: rule.sms_enabled = bool(data['sms_enabled'])
    if 'sms_template_id' in data: rule.sms_template_id = (data.get('sms_template_id') or '').strip() or None
    if 'sms_entity_id' in data: rule.sms_entity_id = (data.get('sms_entity_id') or '').strip() or None
    if 'sms_sender_id' in data: rule.sms_sender_id = (data.get('sms_sender_id') or '').strip() or None
    if 'sms_body' in data: rule.sms_body = (data.get('sms_body') or '').strip() or None

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
        "subscription_statuses": ["All", "Active", "Trial", "Expiring", "Suspended"],
        "categories": [
            {"key": "subscription_reminder", "label": "Subscription Expiry Reminder", "icon": "clock", "color": "#2563eb", "channel": "billing"},
            {"key": "trial_reminder", "label": "Trial Ending Alert", "icon": "hourglass", "color": "#d97706", "channel": "onboarding"},
            {"key": "maintenance", "label": "Software Maintenance Notice", "icon": "wrench", "color": "#4f46e5", "channel": "alerts"},
            {"key": "welcome", "label": "Welcome & Onboarding Email", "icon": "sparkles", "color": "#16a34a", "channel": "onboarding"},
            {"key": "user_welcome", "label": "User Welcome & Credentials", "icon": "user-check", "color": "#2563eb", "channel": "onboarding"},
            {"key": "usage_guide", "label": "Software Usage & How-to Guide", "icon": "book-open", "color": "#0284c7", "channel": "general"},
            {"key": "new_feature", "label": "New Features & Release Notes", "icon": "zap", "color": "#8b5cf6", "channel": "general"},
            {"key": "support", "label": "Customer Support Check-in", "icon": "life-buoy", "color": "#0d9488", "channel": "support"},
            {"key": "project_review", "label": "Reviewer Stage Review Alert", "icon": "check-square", "color": "#2563eb", "channel": "general"},
            {"key": "executive_closure_review", "label": "CEO Final Sign-Off & Closure", "icon": "shield-alert", "color": "#7c3aed", "channel": "alerts"},
            {"key": "facilitator_assistance", "label": "Facilitator Guidance Request", "icon": "help-circle", "color": "#0d9488", "channel": "support"},
            {"key": "custom", "label": "Custom Email Broadcast", "icon": "mail", "color": "#64748b", "channel": "general"}
        ],
        "contact_directory_channels": contact_directory_channels,
        "sender_suggestions": sender_suggestions,
        "available_variables": [
            {"tag": "{{org_name}}", "label": "Organization Name", "example": "Acme Manufacturing Ltd."},
            {"tag": "{{user_name}}", "label": "Recipient User Name", "example": "John Doe"},
            {"tag": "{{user_email}}", "label": "Recipient Email Address", "example": "john@acme.com"},
            {"tag": "{{email}}", "label": "User Login Email", "example": "john@acme.com"},
            {"tag": "{{username}}", "label": "Username", "example": "john@acme.com"},
            {"tag": "{{Password}}", "label": "Default / Temporary Password", "example": "Pass@1234"},
            {"tag": "{{password}}", "label": "Default Password", "example": "Pass@1234"},
            {"tag": "{{default_password}}", "label": "Default Password", "example": "Pass@1234"},
            {"tag": "{{temp_password}}", "label": "Temporary Password", "example": "Pass@1234"},
            {"tag": "{{role_name}}", "label": "User Role", "example": "Company Admin"},
            {"tag": "{{plan_name}}", "label": "Subscription Plan", "example": "Small MSME's Plan"},
            {"tag": "{{trial_days}}", "label": "Trial Days Duration", "example": "14"},
            {"tag": "{{trial_end_date}}", "label": "Trial Expiration Date", "example": "28 Aug 2026"},
            {"tag": "{{max_users}}", "label": "Max Team Capacity", "example": "50"},
            {"tag": "{{storage_limit_mb}}", "label": "Cloud Storage Limit (MB)", "example": "5120"},
            {"tag": "{{industry}}", "label": "Industry Sector", "example": "Automotive Quality"},
            {"tag": "{{expiry_date}}", "label": "Expiry Date", "example": "21 Aug 2026"},
            {"tag": "{{days_left}}", "label": "Days Left Until Expiry", "example": "7"},
            {"tag": "{{project_title}}", "label": "Project Title", "example": "Short-Shot Defect Reduction"},
            {"tag": "{{project_code}}", "label": "Project Code / UID", "example": "PRJ-J2FJ"},
            {"tag": "{{stage_number}}", "label": "Stage Number", "example": "8"},
            {"tag": "{{submitter_name}}", "label": "Submitted By Name", "example": "Priya Singh"},
            {"tag": "{{reviewer_name}}", "label": "Reviewer Name", "example": "Meera Kapoor"},
            {"tag": "{{reviewer_comments}}", "label": "Reviewer Comments", "example": "Verified and recommended for closure."},
            {"tag": "{{requester_name}}", "label": "Assistance Requester Name", "example": "Neha Sharma"},
            {"tag": "{{assistance_message}}", "label": "Assistance Message Text", "example": "Need help with Ishikawa diagram."},
            {"tag": "{{annual_savings}}", "label": "Verified Cost Savings", "example": "₹ 4,46,000 INR"},
            {"tag": "{{roi_multiplier}}", "label": "Project ROI Multiplier", "example": "8.3x"},
            {"tag": "{{plant_name}}", "label": "Plant Location", "example": "Chennai Plant"},
            {"tag": "{{department_name}}", "label": "Department", "example": "Injection Moulding"},
            {"tag": "{{support_email}}", "label": "Support Desk Email", "example": "support@ifqm.org.in"},
            {"tag": "{{app_url}}", "label": "Application URL", "example": "http://127.0.0.1:5000"},
            {"tag": "{{cta_url}}", "label": "Action Button Link", "example": "/admin/settings.html?tab=billing"},
            {"tag": "{{cta_text}}", "label": "Action Button Text", "example": "Renew Subscription"}
        ]
    }), 200


# ─── SMS Template Config Routes (Gio DLT System SMS) ──────────────────────────

@email_notification_bp.route('/sms-templates', methods=['GET'])
@jwt_required()
def list_sms_templates():
    """List all Gio DLT SMS template configurations (system-level)."""
    user = _get_current_user()
    err = _require_super_admin(user)
    if err: return err

    # Seed defaults if not present
    _seed_sms_template_defaults()

    templates = SmsTemplateConfig.query.order_by(SmsTemplateConfig.id.asc()).all()
    return jsonify({
        "status": "success",
        "data": [t.to_dict() for t in templates],
        "total": len(templates)
    }), 200


@email_notification_bp.route('/sms-templates/<string:template_key>', methods=['GET'])
@jwt_required()
def get_sms_template(template_key):
    """Get a single SMS template config by key."""
    user = _get_current_user()
    err = _require_super_admin(user)
    if err: return err

    tmpl = SmsTemplateConfig.query.filter_by(template_key=template_key).first()
    if not tmpl:
        return jsonify({"status": "error", "message": "SMS template not found"}), 404
    return jsonify({"status": "success", "data": tmpl.to_dict()}), 200


@email_notification_bp.route('/sms-templates/<string:template_key>', methods=['PUT'])
@jwt_required()
def update_sms_template(template_key):
    """Update a Gio DLT SMS template config by key."""
    user = _get_current_user()
    err = _require_super_admin(user)
    if err: return err

    tmpl = SmsTemplateConfig.query.filter_by(template_key=template_key).first()
    if not tmpl:
        return jsonify({"status": "error", "message": "SMS template not found"}), 404

    data = request.get_json() or {}
    if 'display_name' in data: tmpl.display_name = (data['display_name'] or '').strip()
    if 'category' in data: tmpl.category = (data['category'] or 'custom').strip()
    if 'description' in data: tmpl.description = data.get('description', '')
    if 'template_id' in data: tmpl.template_id = (data.get('template_id') or '').strip() or None
    if 'entity_id' in data: tmpl.entity_id = (data.get('entity_id') or '').strip() or None
    if 'sender_id' in data: tmpl.sender_id = (data.get('sender_id') or '').strip() or None
    if 'body' in data: tmpl.body = (data.get('body') or '').strip() or None
    if 'trigger_type' in data: tmpl.trigger_type = data.get('trigger_type', 'event')
    if 'event_trigger' in data: tmpl.event_trigger = (data.get('event_trigger') or '').strip() or None
    if 'trigger_days_before' in data:
        try:
            tmpl.trigger_days_before = int(data.get('trigger_days_before', 0))
        except (ValueError, TypeError):
            tmpl.trigger_days_before = 0
    if 'target_audience_type' in data: tmpl.target_audience_type = data.get('target_audience_type', 'all')
    if 'target_org_ids' in data: tmpl.target_org_ids = data.get('target_org_ids', [])
    if 'target_roles' in data: tmpl.target_roles = data.get('target_roles', [])
    if 'target_plans' in data: tmpl.target_plans = data.get('target_plans', [])
    if 'target_statuses' in data: tmpl.target_statuses = data.get('target_statuses', [])
    if 'is_active' in data: tmpl.is_active = bool(data['is_active'])
    tmpl.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    db.session.commit()
    return jsonify({
        "status": "success",
        "message": f"SMS template '{tmpl.display_name}' updated successfully.",
        "data": tmpl.to_dict()
    }), 200


@email_notification_bp.route('/sms-templates/<string:template_key>/send-test', methods=['POST'])
@jwt_required()
def send_test_sms_template(template_key):
    """Send a test SMS for a specific template."""
    user = _get_current_user()
    err = _require_super_admin(user)
    if err: return err

    tmpl = SmsTemplateConfig.query.filter_by(template_key=template_key).first()
    if not tmpl:
        return jsonify({"status": "error", "message": "SMS template not found"}), 404

    data = request.get_json() or {}
    phone = (data.get('phone') or '').strip()
    if not phone:
        return jsonify({"status": "error", "message": "Recipient phone number is required"}), 400

    # Build dummy test context
    context = {
        'otp': '123456',
        'user_name': user.full_name or user.username or 'Test User',
        'org_name': 'Acme Quality Corp',
        'plan_name': "Enterprise Scale Plan",
        'expiry_date': datetime.now(timezone.utc).replace(tzinfo=None).strftime('%d %b %Y'),
        'maintenance_date': (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=2)).strftime('%d %b %Y'),
        'maintenance_window': '02:00 AM - 04:00 AM IST',
        'project_title': 'Short-Shot Defect Reduction',
        'project_code': 'PRJ-J2FJ',
        'stage_number': '8',
        'submitter_name': 'Priya Singh',
        'assigned_role': 'Team Leader',
        'username': user.email or user.username or 'john.doe@company.com',
        'email': user.email or 'john.doe@company.com',
        'user_email': user.email or 'john.doe@company.com',
        'Password': 'Pass@1234',
        'password': 'Pass@1234',
        'temp_password': 'Pass@1234',
        'temporary_password': 'Pass@1234',
        'default_password': 'Pass@1234',
        'invoice_number': 'INV-2026-089',
        'total_amount': '₹ 12,500',
        'amount': '₹ 12,500',
        'payment_ref': 'PAY-987654',
        'assistance_message': 'Need guidance with Root Cause 5-Why analysis.',
        'support_email': 'support@ifqm.org.in',
        'app_url': 'http://127.0.0.1:5000'
    }

    from app.domain.services.email_notification_engine import EmailNotificationEngine
    body = EmailNotificationEngine.replace_variables(tmpl.body or 'Test SMS Notification from IFQM QCMS', context)

    print(f"\n[TEST SMS] Template: {tmpl.display_name} ({tmpl.template_key}) | To: {phone} | Body: {body}\n")

    # Record delivery log
    try:
        sms_log = SmsNotificationLog(
            template_key=tmpl.template_key,
            template_name=tmpl.display_name,
            category=tmpl.category or 'custom',
            sender_id=tmpl.sender_id or 'IFQMSK',
            dlt_template_id=tmpl.template_id,
            dlt_entity_id=tmpl.entity_id,
            message_body=body,
            phone_number=phone,
            recipient_name=user.full_name or user.username or 'Admin User',
            org_name='Quality MSME Corp',
            gateway='Fast2SMS / Resend',
            status='Delivered',
            sent_by_id=user.id,
            sent_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.session.add(sms_log)
        tmpl.total_sent = (tmpl.total_sent or 0) + 1
        tmpl.last_triggered_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[SMS Log Error] {e}")

    return jsonify({
        "status": "success",
        "message": f"Test SMS for '{tmpl.display_name}' sent successfully to {phone}!",
        "rendered_body": body
    }), 200


@email_notification_bp.route('/sms-logs', methods=['GET'])
@jwt_required()
def get_sms_notification_logs():
    """Retrieve paginated SMS delivery audit logs."""
    user = _get_current_user()
    err = _require_super_admin(user)
    if err: return err

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    search_q = request.args.get('q', '').strip()

    _seed_sample_sms_logs_if_empty()

    query = SmsNotificationLog.query

    if search_q:
        query = query.filter(
            SmsNotificationLog.template_name.ilike(f'%{search_q}%') |
            SmsNotificationLog.phone_number.ilike(f'%{search_q}%') |
            SmsNotificationLog.message_body.ilike(f'%{search_q}%') |
            SmsNotificationLog.recipient_name.ilike(f'%{search_q}%') |
            SmsNotificationLog.org_name.ilike(f'%{search_q}%') |
            SmsNotificationLog.sender_id.ilike(f'%{search_q}%')
        )

    pagination = query.order_by(SmsNotificationLog.sent_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "status": "success",
        "data": [l.to_dict() for l in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages
    }), 200


def _seed_sample_sms_logs_if_empty():
    """Seed realistic initial SMS delivery logs if none exist."""
    if SmsNotificationLog.query.count() > 0:
        return

    from datetime import timedelta
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    sample_records = [
        {
            'template_key': 'phone_otp_verification',
            'template_name': 'Phone Number OTP Verification',
            'category': 'auth',
            'sender_id': 'IFQMSK',
            'phone_number': '+91 98451 23049',
            'recipient_name': 'Rajesh Kumar',
            'org_name': 'Acme Engineering Ltd',
            'message_body': 'Dear Customer, use OTP 742910 to complete your activation on IFQM Skills. Do not share this OTP with anyone.',
            'status': 'Delivered',
            'offset_hours': 1
        },
        {
            'template_key': 'project_stage_review_required',
            'template_name': 'Project Review Required: Stage Review Request',
            'category': 'project_review',
            'sender_id': 'IFQMSK',
            'phone_number': '+91 97110 54321',
            'recipient_name': 'Meera Kapoor',
            'org_name': 'Precision Auto Quality',
            'message_body': "Review Required: Project 'Short-Shot Defect Reduction' (PRJ-J2FJ) Stage 8 submitted by Priya Singh. Please evaluate at: http://127.0.0.1:5000 - IFQM",
            'status': 'Delivered',
            'offset_hours': 3
        },
        {
            'template_key': 'executive_closure_signoff',
            'template_name': 'Executive Sign-Off Required: Project Closure Approval',
            'category': 'executive_closure_review',
            'sender_id': 'IFQMSK',
            'phone_number': '+91 98200 11223',
            'recipient_name': 'Dr. Vikram Malhotra',
            'org_name': 'Precision Auto Quality',
            'message_body': "Executive Action Required: Project 'Short-Shot Defect Reduction' (PRJ-J2FJ) has Reviewer Stage 8 approval. Final CEO sign-off needed: http://127.0.0.1:5000 - IFQM QCMS",
            'status': 'Delivered',
            'offset_hours': 5
        },
        {
            'template_key': 'facilitator_guidance_requested',
            'template_name': 'Facilitator Guidance Request: Team Assistance Needed',
            'category': 'facilitator_assistance',
            'sender_id': 'IFQMSK',
            'phone_number': '+91 99887 66554',
            'recipient_name': 'Harshith K',
            'org_name': 'Apex Quality Works',
            'message_body': 'Guidance Requested: Team on \'CNC Tool Wear Elimination\' (Stage 2) requested assistance: "Need guidance on stratifying Pareto vibration data". Open project: http://127.0.0.1:5000 - IFQM',
            'status': 'Delivered',
            'offset_hours': 12
        },
        {
            'template_key': 'subscription_reminder_7d',
            'template_name': 'Subscription Expiry Reminder (7 Days)',
            'category': 'subscription_reminder',
            'sender_id': 'IFQMSK',
            'phone_number': '+91 98450 99881',
            'recipient_name': 'Anand Sharma',
            'org_name': 'Bharat Forge Quality Cell',
            'message_body': 'Dear Anand Sharma, your Enterprise Scale Plan subscription for Bharat Forge Quality Cell expires in 7 days on 28 Aug 2026. Renew now at http://127.0.0.1:5000 to ensure uninterrupted access. - IFQM QCMS',
            'status': 'Delivered',
            'offset_hours': 24
        },
        {
            'template_key': 'payg_metered_invoice',
            'template_name': 'Monthly Pay-As-You-Go Metered Tax Invoice',
            'category': 'billing',
            'sender_id': 'IFQMSK',
            'phone_number': '+91 98102 33445',
            'recipient_name': 'Kavita Menon',
            'org_name': 'Zenith Polymer Works',
            'message_body': 'Invoice Generated: Monthly usage statement INV-2026-088 for Zenith Polymer Works is ready. Total payable: ₹ 14,800. View invoice: http://127.0.0.1:5000 - IFQM',
            'status': 'Delivered',
            'offset_hours': 36
        },
        {
            'template_key': 'user_welcome_credentials',
            'template_name': 'User Account Welcome & Login Credentials',
            'category': 'user_welcome',
            'sender_id': 'IFQMSK',
            'phone_number': '+91 97654 32100',
            'recipient_name': 'Suresh Nair',
            'org_name': 'Acme Engineering Ltd',
            'message_body': 'Welcome to Acme Engineering Ltd on QCMS! Your account username (suresh.nair@acme.com) is active. Log in at http://127.0.0.1:5000 to access your projects. - IFQM QCMS',
            'status': 'Delivered',
            'offset_hours': 48
        }
    ]

    for rec in sample_records:
        log = SmsNotificationLog(
            template_key=rec['template_key'],
            template_name=rec['template_name'],
            category=rec['category'],
            sender_id=rec['sender_id'],
            dlt_template_id='1307168923412345',
            dlt_entity_id='1301157890123456',
            message_body=rec['message_body'],
            phone_number=rec['phone_number'],
            recipient_name=rec['recipient_name'],
            org_name=rec['org_name'],
            gateway='Fast2SMS / Resend',
            status=rec['status'],
            sent_at=now - timedelta(hours=rec['offset_hours'])
        )
        db.session.add(log)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()


def _seed_sms_template_defaults():
    """Seed default system SMS templates matching all platform communication events if not yet present."""
    defaults = [
        {
            'template_key': 'password_reset_otp',
            'display_name': 'Password Reset OTP Verification',
            'description': 'Sent when a user requests to reset their password and needs to verify their identity via SMS OTP.',
            'body': 'Dear Customer, use OTP {{otp}} to reset your password on IFQM QCMS. Valid for 10 mins. Do not share with anyone. - IFQM',
        },
        {
            'template_key': 'phone_otp_verification',
            'display_name': 'Phone Number OTP Verification',
            'description': 'Sent when a user registers or logs in and needs to verify their mobile number via SMS OTP.',
            'body': 'Dear Customer, use OTP {{otp}} to complete your activation on IFQM Skills. Do not share this OTP with anyone.',
        },
        {
            'template_key': 'subscription_reminder_7d',
            'display_name': 'Subscription Expiry Reminder (7 Days)',
            'description': 'Automatically alerts organization administrators 7 days before their subscription renewal date.',
            'body': 'Dear {{user_name}}, your {{plan_name}} subscription for {{org_name}} expires in 7 days on {{expiry_date}}. Renew now at {{app_url}} to ensure uninterrupted access. - IFQM QCMS',
        },
        {
            'template_key': 'subscription_urgent_1d',
            'display_name': 'Subscription Expiry Urgent Notice (1 Day)',
            'description': 'Urgent SMS alert sent 24 hours prior to subscription expiration to prevent workflow disruption.',
            'body': 'URGENT: Your {{plan_name}} subscription for {{org_name}} expires tomorrow. Complete immediate renewal at {{app_url}} to keep quality projects active. - IFQM QCMS',
        },
        {
            'template_key': 'trial_ending_3d',
            'display_name': 'Trial Plan Ending Alert (3 Days)',
            'description': 'Notifies trial organizations 3 days before their onboarding trial concludes.',
            'body': 'Hello {{user_name}}, your free trial for {{org_name}} ends in 3 days. Upgrade to an enterprise plan at {{app_url}} to retain all project data and features. - IFQM QCMS',
        },
        {
            'template_key': 'system_maintenance_notice',
            'display_name': 'Scheduled Software Maintenance Notice',
            'description': 'Informs administrators and team leaders of scheduled platform maintenance windows.',
            'body': 'Notice: QCMS Enterprise OS has a scheduled maintenance window on {{maintenance_date}} from {{maintenance_window}}. Systems will be temporarily offline. - IFQM',
        },
        {
            'template_key': 'new_org_welcome',
            'display_name': 'Welcome & Onboarding to QCMS Enterprise OS',
            'description': 'Sent immediately upon new organization workspace provisioning.',
            'body': 'Welcome to IFQM QCMS! Your organization workspace {{org_name}} has been initialized. Log in to start your continuous improvement journey: {{app_url}}',
        },
        {
            'template_key': 'workflow_usage_guide',
            'display_name': '8-Stage Quality Workflow Quick Guide',
            'description': 'SMS guide introducing team members to the DMAIC / 8-Stage quality problem solving process.',
            'body': 'Hi {{user_name}}, master the 8-Stage Quality Problem Solving methodology with our quickstart reference guide: {{app_url}}/projects. - IFQM QCMS',
        },
        {
            'template_key': 'new_features_release',
            'display_name': 'New Features & Release Notes Announcement',
            'description': 'Informs organization users of newly deployed features and platform enhancements.',
            'body': 'QCMS Update: Exciting new quality management features and performance upgrades are now live. Explore release notes at {{app_url}}. - IFQM QCMS',
        },
        {
            'template_key': 'customer_support_checkin',
            'display_name': 'Customer Support & Success Check-in',
            'description': 'Check-in SMS from the customer success team to assist with quality objectives.',
            'body': 'Hello {{user_name}}, our success desk is here to help {{org_name}} achieve your operational excellence goals. Contact us anytime at {{support_email}}. - IFQM QCMS',
        },
        {
            'template_key': 'payment_approved_receipt',
            'display_name': 'Subscription Payment Approved & Tax Invoice Receipt',
            'description': 'Confirms receipt of offline or online subscription payment and informs of invoice availability.',
            'body': 'Payment Received: Your payment for {{plan_name}} ({{org_name}}) is approved. Tax invoice {{invoice_number}} is ready in your billing portal: {{app_url}} - IFQM',
        },
        {
            'template_key': 'payment_declined_notice',
            'display_name': 'Offline Payment Verification Declined Notice',
            'description': 'Alerts the administrator when offline payment verification is declined.',
            'body': 'Alert: Payment verification for {{org_name}} (Ref: {{payment_ref}}) was declined. Please verify payment details or contact support at {{support_email}}. - IFQM',
        },
        {
            'template_key': 'project_assignment_kickoff',
            'display_name': 'Project Assignment & Kickoff Notification',
            'description': 'Alerts members, reviewers, and facilitators immediately when assigned to a new project.',
            'body': 'Hi {{user_name}}, you have been assigned as {{assigned_role}} for project \'{{project_title}}\' ({{project_code}}) in {{org_name}}. Access workspace: {{app_url}}',
        },
        {
            'template_key': 'project_completion_report',
            'display_name': 'Project Completion, Approval & Improvement Report',
            'description': 'Congratulates team members upon official 8-stage project approval and closure.',
            'body': 'Congratulations! Project \'{{project_title}}\' ({{project_code}}) has received Final Reviewer Approval and official closure in {{org_name}}. Dossier: {{app_url}}',
        },
        {
            'template_key': 'user_welcome_credentials',
            'display_name': 'User Account Welcome & Login Credentials',
            'description': 'Sends new invited/created users their login username, default temporary password, and quickstart portal access link.',
            'body': 'Welcome to {{org_name}}! Your Quality Circle account is created. Your account username ({{username}}). Temporary Password: [{{Password}}] Log in at {{app_url}} Please change your password after first login. - IFQM QCMS',
        },
        {
            'template_key': 'payg_metered_invoice',
            'display_name': 'Monthly Pay-As-You-Go Metered Tax Invoice',
            'description': 'Alerts billing administrators when the monthly metered usage tax invoice is generated.',
            'body': 'Invoice Generated: Monthly usage statement {{invoice_number}} for {{org_name}} is ready. Total payable: {{total_amount}}. View invoice: {{app_url}} - IFQM',
        },
        {
            'template_key': 'project_stage_review_required',
            'display_name': 'Project Review Required: Stage Review Request',
            'description': 'Alerts the assigned Reviewer when a project stage is submitted for formal evaluation.',
            'body': 'Review Required: Project \'{{project_title}}\' ({{project_code}}) Stage {{stage_number}} submitted by {{submitter_name}}. Please evaluate at: {{app_url}} - IFQM',
        },
        {
            'template_key': 'executive_closure_signoff',
            'display_name': 'Executive Sign-Off Required: Project Closure Approval',
            'description': 'Alerts the CEO when a project completes Reviewer Stage 8 approval and awaits final sign-off.',
            'body': 'Executive Action Required: Project \'{{project_title}}\' ({{project_code}}) has Reviewer Stage 8 approval. Final CEO sign-off needed: {{app_url}} - IFQM QCMS',
        },
        {
            'template_key': 'facilitator_guidance_requested',
            'display_name': 'Facilitator Guidance Request: Team Assistance Needed',
            'description': 'Alerts the Facilitator when a project team member requests methodology assistance.',
            'body': 'Guidance Requested: Team on \'{{project_title}}\' (Stage {{stage_number}}) requested assistance: "{{assistance_message}}". Open project: {{app_url}} - IFQM',
        }
    ]
    for d in defaults:
        existing = SmsTemplateConfig.query.filter_by(template_key=d['template_key']).first()
        if not existing:
            tmpl = SmsTemplateConfig(
                template_key=d['template_key'],
                display_name=d['display_name'],
                description=d.get('description', ''),
                body=d.get('body', ''),
                is_active=True
            )
            db.session.add(tmpl)
        else:
            if not existing.description:
                existing.description = d.get('description', '')
            if not existing.body:
                existing.body = d.get('body', '')
            elif d['template_key'] == 'user_welcome_credentials' and ('Password' not in existing.body and 'password' not in existing.body and 'temp_password' not in existing.body):
                existing.body = d.get('body', '')
            if not existing.display_name:
                existing.display_name = d.get('display_name', '')
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
