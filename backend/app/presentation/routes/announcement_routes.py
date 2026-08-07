import random
import string
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.infrastructure.database.models.models import (
    User, Organization, Announcement, AnnouncementAudience,
    AnnouncementDelivery, AnnouncementRead, AnnouncementAttachment,
    AnnouncementAudit, Notification
)

announcement_bp = Blueprint('announcements', __name__, url_prefix='/api/announcements')

# ─── Permission helpers ────────────────────────────────────────────────────────

ALLOWED_ROLES = ('SuperAdmin', 'Owner', 'Platform Admin', 'Communications Manager', 'Support Manager')
READ_ROLES = ALLOWED_ROLES + ('Read Only',)

def get_current_user():
    uid = get_jwt_identity()
    return db.session.get(User, uid)

def require_admin(user):
    if not user or not user.role or user.role.name not in ALLOWED_ROLES:
        return jsonify({"message": "Insufficient permissions"}), 403
    return None

def ann_number():
    suffix = ''.join(random.choices(string.digits, k=4))
    return f"ANN-{datetime.utcnow().strftime('%Y%m%d')}-{suffix}"

def log_ann_event(announcement_id, user_id, action, details=None):
    audit = AnnouncementAudit(
        announcement_id=announcement_id,
        user_id=user_id,
        action=action,
        details=details or {},
        ip_address=request.remote_addr if request else '127.0.0.1'
    )
    db.session.add(audit)

def ann_to_dict(a, include_body=False):
    d = {
        "id": a.id,
        "ann_number": a.ann_number,
        "title": a.title,
        "summary": a.summary,
        "category": a.category,
        "priority": a.priority,
        "status": a.status,
        "tags": a.tags or [],
        "banner_url": a.banner_url,
        "audience_type": a.audience_type,
        "channels": a.channels or {},
        "publish_at": a.publish_at.isoformat() + "Z" if a.publish_at else None,
        "published_at": a.published_at.isoformat() + "Z" if a.published_at else None,
        "expires_at": a.expires_at.isoformat() + "Z" if a.expires_at else None,
        "timezone": a.timezone,
        "total_delivered": a.total_delivered,
        "total_viewed": a.total_viewed,
        "total_read": a.total_read,
        "total_clicked": a.total_clicked,
        "read_pct": round(a.total_read / a.total_delivered * 100, 1) if a.total_delivered > 0 else 0,
        "created_by": a.author.username if a.author else "System",
        "created_by_email": a.author.email if a.author else "",
        "created_at": a.created_at.isoformat() + "Z",
        "updated_at": a.updated_at.isoformat() + "Z" if a.updated_at else None,
        "attachment_count": len(a.attachments),
    }
    if include_body:
        d["body"] = a.body
        d["audience"] = [{"type": aud.target_type, "value": aud.target_value} for aud in a.audience]
        d["attachments"] = [{"id": at.id, "file_name": at.file_name, "file_url": at.file_url, "file_type": at.file_type, "file_size": at.file_size} for at in a.attachments]
    return d

def deliver_in_app(announcement, user_ids):
    """Create in-app notifications for each user."""
    for uid in user_ids:
        user = db.session.get(User, uid)
        if not user:
            continue
        notif = Notification(
            org_id=user.org_id,
            user_id=uid,
            title=f"📢 {announcement.title}",
            message=announcement.summary or announcement.body or "",
            link=f"/admin/super-admin.html?view=announcements&ann={announcement.id}"
        )
        db.session.add(notif)
        delivery = AnnouncementDelivery(
            announcement_id=announcement.id,
            org_id=user.org_id,
            user_id=uid,
            channel='in_app',
            status='Sent',
            sent_at=datetime.utcnow()
        )
        db.session.add(delivery)
    announcement.total_delivered = AnnouncementDelivery.query.filter_by(
        announcement_id=announcement.id, channel='in_app', status='Sent'
    ).count() + len(user_ids)

def resolve_audience(ann):
    """Return list of user_ids who should receive this announcement."""
    if ann.audience_type == 'all':
        users = User.query.filter(User.is_active == True).all() if hasattr(User, 'is_active') else User.query.all()
        return [u.id for u in users]

    criteria = ann.audience
    user_ids = set()
    for criterion in criteria:
        t = criterion.target_type
        v = (criterion.target_value or '').strip()
        if not v:
            continue
        if t == 'org':
            if v.isdigit():
                us = User.query.filter_by(org_id=int(v)).all()
                user_ids.update(u.id for u in us)
            else:
                orgs = Organization.query.filter(Organization.name.ilike(f"%{v}%")).all()
                for org in orgs:
                    us = User.query.filter_by(org_id=org.id).all()
                    user_ids.update(u.id for u in us)
        elif t == 'plan':
            orgs = Organization.query.filter(Organization.subscription_plan.ilike(f"%{v}%")).all()
            for org in orgs:
                us = User.query.filter_by(org_id=org.id).all()
                user_ids.update(u.id for u in us)
        elif t == 'role':
            from app.infrastructure.database.models.models import Role
            role_v = v.rstrip('s').strip()
            us = User.query.join(Role, User.role_id == Role.id).filter(
                db.or_(Role.name.ilike(f"%{v}%"), Role.name.ilike(f"%{role_v}%"))
            ).all()
            user_ids.update(u.id for u in us)
        elif t == 'country':
            orgs = Organization.query.filter(Organization.country.ilike(f"%{v}%")).all()
            for org in orgs:
                us = User.query.filter_by(org_id=org.id).all()
                user_ids.update(u.id for u in us)
        elif t == 'status':
            orgs = Organization.query.filter(Organization.status.ilike(f"%{v}%")).all()
            for org in orgs:
                us = User.query.filter_by(org_id=org.id).all()
                user_ids.update(u.id for u in us)
    return list(user_ids)


def user_matches_announcement(user, ann):
    if not ann or ann.status not in ('Published', 'Expired'):
        return False
    if ann.audience_type == 'all':
        return True
    
    org = db.session.get(Organization, user.org_id) if user.org_id else None
    role_name = user.role.name if user.role else ''
    
    for c in ann.audience:
        t = c.target_type
        v = (c.target_value or '').strip()
        if not v:
            continue
        if t == 'org':
            if v.isdigit() and str(user.org_id) == str(v):
                return True
            elif org and org.name and v.lower() in org.name.lower():
                return True
        elif t == 'role':
            role_target = v.rstrip('s').strip().lower()
            if role_target in role_name.lower() or role_name.lower() in role_target:
                return True
        elif t == 'plan' and org and org.subscription_plan and v.lower() in org.subscription_plan.lower():
            return True
        elif t == 'country' and org and org.country and v.lower() in org.country.lower():
            return True
        elif t == 'status' and org and org.status and v.lower() in org.status.lower():
            return True
    return False


# ─── Dashboard ────────────────────────────────────────────────────────────────

@announcement_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    user = get_current_user()
    if not user or not user.role or user.role.name not in READ_ROLES:
        return jsonify({"message": "Unauthorized"}), 403

    now = datetime.utcnow()
    thirty_ago = now - timedelta(days=30)

    total = Announcement.query.count()
    active = Announcement.query.filter_by(status='Published').count()
    scheduled = Announcement.query.filter_by(status='Scheduled').count()
    expired = Announcement.query.filter_by(status='Expired').count()
    drafts = Announcement.query.filter_by(status='Draft').count()
    archived = Announcement.query.filter_by(status='Archived').count()
    high_priority = Announcement.query.filter(Announcement.priority.in_(['High', 'Critical'])).count()

    total_delivered = db.session.query(db.func.sum(Announcement.total_delivered)).scalar() or 0
    total_viewed = db.session.query(db.func.sum(Announcement.total_viewed)).scalar() or 0
    total_read = db.session.query(db.func.sum(Announcement.total_read)).scalar() or 0
    total_clicked = db.session.query(db.func.sum(Announcement.total_clicked)).scalar() or 0

    if total_delivered > 0:
        read_pct = round(total_read / total_delivered * 100, 1)
        unread_pct = round((total_delivered - total_read) / total_delivered * 100, 1)
    else:
        read_pct = 0.0
        unread_pct = 0.0
    ctr = round(total_clicked / total_delivered * 100, 1) if total_delivered > 0 else 0
    failed_deliveries = AnnouncementDelivery.query.filter_by(status='Failed').count()

    # Period comparison (last 30 days vs prior 30 days)
    curr_total = Announcement.query.filter(Announcement.created_at >= thirty_ago).count()
    prev_total = Announcement.query.filter(
        Announcement.created_at >= thirty_ago - timedelta(days=30),
        Announcement.created_at < thirty_ago
    ).count()
    growth = round(((curr_total - prev_total) / prev_total * 100) if prev_total > 0 else 0, 1)

    # Recent activity (last 10 published)
    recent = Announcement.query.filter(
        Announcement.status.in_(['Published', 'Scheduled'])
    ).order_by(Announcement.created_at.desc()).limit(10).all()

    # Category breakdown
    cat_counts = db.session.query(
        Announcement.category, db.func.count(Announcement.id)
    ).group_by(Announcement.category).all()

    # Priority breakdown
    pri_counts = db.session.query(
        Announcement.priority, db.func.count(Announcement.id)
    ).group_by(Announcement.priority).all()

    return jsonify({
        "status": "success",
        "data": {
            "kpis": {
                "total_announcements": {"icon": "megaphone", "value": total, "growth": growth, "tooltip": "Total count of all broadcast notices created across all statuses (Published, Draft, Scheduled, Expired, Archived).", "last_updated": now.isoformat()},
                "active_announcements": {"icon": "radio", "value": active, "growth": 0, "tooltip": "Currently active and published announcements visible to target organization users in real time.", "last_updated": now.isoformat()},
                "scheduled": {"icon": "clock", "value": scheduled, "growth": 0, "tooltip": "Announcements queued for automatic broadcast delivery at a future date and time.", "last_updated": now.isoformat()},
                "expired": {"icon": "calendar-x", "value": expired, "growth": 0, "tooltip": "Past broadcasts that have reached their expiration date and are no longer active.", "last_updated": now.isoformat()},
                "drafts": {"icon": "file-text", "value": drafts, "growth": 0, "tooltip": "Saved draft messages currently being prepared before broadcasting.", "last_updated": now.isoformat()},
                "archived": {"icon": "archive", "value": archived, "growth": 0, "tooltip": "Inactive announcements moved to archive history for record keeping.", "last_updated": now.isoformat()},
                "high_priority": {"icon": "alert-triangle", "value": high_priority, "growth": 0, "tooltip": "Urgent broadcasts marked with High or Critical priority requiring immediate attention.", "last_updated": now.isoformat()},
                "total_views": {"icon": "eye", "value": total_viewed, "growth": 0, "tooltip": "Total cumulative views across all broadcast notices by organization users.", "last_updated": now.isoformat()},
                "failed_deliveries": {"icon": "alert-circle", "value": failed_deliveries, "growth": 0, "tooltip": "Total delivery failure attempts across recipient organizations.", "last_updated": now.isoformat()},
            },
            "recent": [ann_to_dict(a) for a in recent],
            "by_category": {row[0]: row[1] for row in cat_counts},
            "by_priority": {row[0]: row[1] for row in pri_counts},
        }
    }), 200


# ─── List / Search ────────────────────────────────────────────────────────────

@announcement_bp.route('/', methods=['GET'])
@jwt_required()
def list_announcements():
    user = get_current_user()
    if not user or not user.role or user.role.name not in READ_ROLES:
        return jsonify({"message": "Unauthorized"}), 403

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    category = request.args.get('category', '')
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')

    query = Announcement.query

    if q:
        pattern = f"%{q}%"
        query = query.filter(db.or_(
            Announcement.title.ilike(pattern),
            Announcement.summary.ilike(pattern),
            Announcement.ann_number.ilike(pattern),
            Announcement.category.ilike(pattern),
        ))
    if status:
        statuses = [s.strip() for s in status.split(',')]
        query = query.filter(Announcement.status.in_(statuses))
    if priority:
        priorities = [p.strip() for p in priority.split(',')]
        query = query.filter(Announcement.priority.in_(priorities))
    if category:
        query = query.filter(Announcement.category == category)

    sort_col = getattr(Announcement, sort_by, Announcement.created_at)
    query = query.order_by(sort_col.desc() if sort_order == 'desc' else sort_col.asc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "status": "success",
        "data": [ann_to_dict(a) for a in pagination.items],
        "meta": {
            "total": pagination.total,
            "pages": pagination.pages,
            "page": page,
            "per_page": per_page
        }
    }), 200


# ─── Detail ───────────────────────────────────────────────────────────────────

@announcement_bp.route('/<int:ann_id>', methods=['GET'])
@jwt_required()
def get_announcement(ann_id):
    user = get_current_user()
    if not user or not user.role or user.role.name not in READ_ROLES:
        return jsonify({"message": "Unauthorized"}), 403
    ann = db.session.get(Announcement, ann_id)
    if not ann:
        return jsonify({"message": "Not found"}), 404
    return jsonify({"status": "success", "data": ann_to_dict(ann, include_body=True)}), 200


# ─── Create ───────────────────────────────────────────────────────────────────

@announcement_bp.route('/', methods=['POST'])
@jwt_required()
def create_announcement():
    user = get_current_user()
    err = require_admin(user)
    if err:
        return err

    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    body = (data.get('body') or '').strip()
    if not title:
        return jsonify({"message": "Title is required"}), 422
    if not body:
        return jsonify({"message": "Message details are required"}), 422

    # Parse dates
    publish_at = None
    expires_at = None
    try:
        if data.get('publish_at'):
            publish_at = datetime.fromisoformat(data['publish_at'].replace('Z', ''))
        if data.get('expires_at'):
            expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', ''))
    except ValueError:
        return jsonify({"message": "Invalid date format"}), 422

    # Determine status
    status = 'Draft'
    if data.get('action') == 'publish':
        status = 'Published'
    elif data.get('action') == 'schedule' and publish_at:
        status = 'Scheduled'

    ann = Announcement(
        ann_number=ann_number(),
        created_by=user.id,
        title=title,
        summary=data.get('summary', ''),
        body=data.get('body', ''),
        category=data.get('category', 'General'),
        priority=data.get('priority', 'Medium'),
        status=status,
        tags=data.get('tags', []),
        audience_type=data.get('audience_type', 'all'),
        channels=data.get('channels', {"in_app": True, "email": False, "sms": False, "push": False}),
        publish_at=publish_at,
        expires_at=expires_at,
        timezone=data.get('timezone', 'UTC'),
        published_at=datetime.utcnow() if status == 'Published' else None
    )
    db.session.add(ann)
    db.session.flush()

    # Audience rules
    for rule in data.get('audience', []):
        db.session.add(AnnouncementAudience(
            announcement_id=ann.id,
            target_type=rule.get('type'),
            target_value=str(rule.get('value'))
        ))

    log_ann_event(ann.id, user.id, 'CREATED', {"title": title, "status": status})

    # If publishing immediately, deliver in-app
    if status == 'Published' and ann.channels.get('in_app'):
        user_ids = resolve_audience(ann)
        deliver_in_app(ann, user_ids)

    db.session.commit()
    return jsonify({"status": "success", "data": ann_to_dict(ann), "message": f"Announcement {ann.ann_number} created."}), 201


# ─── Update ───────────────────────────────────────────────────────────────────

@announcement_bp.route('/<int:ann_id>', methods=['PUT'])
@jwt_required()
def update_announcement(ann_id):
    user = get_current_user()
    err = require_admin(user)
    if err:
        return err

    ann = db.session.get(Announcement, ann_id)
    if not ann:
        return jsonify({"message": "Not found"}), 404

    data = request.get_json() or {}
    for field in ('title', 'summary', 'body', 'category', 'priority', 'tags', 'channels', 'audience_type', 'timezone', 'banner_url'):
        if field in data:
            setattr(ann, field, data[field])

    if 'publish_at' in data and data['publish_at']:
        ann.publish_at = datetime.fromisoformat(data['publish_at'].replace('Z', ''))
    if 'expires_at' in data and data['expires_at']:
        ann.expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', ''))

    # Refresh audience if provided
    if 'audience' in data:
        AnnouncementAudience.query.filter_by(announcement_id=ann.id).delete()
        for rule in data['audience']:
            db.session.add(AnnouncementAudience(
                announcement_id=ann.id,
                target_type=rule.get('type'),
                target_value=str(rule.get('value'))
            ))

    ann.updated_at = datetime.utcnow()
    log_ann_event(ann.id, user.id, 'UPDATED', {"changed_fields": list(data.keys())})
    db.session.commit()
    return jsonify({"status": "success", "data": ann_to_dict(ann), "message": "Announcement updated."}), 200


# ─── Publish ──────────────────────────────────────────────────────────────────

@announcement_bp.route('/<int:ann_id>/publish', methods=['POST'])
@jwt_required()
def publish_announcement(ann_id):
    user = get_current_user()
    err = require_admin(user)
    if err:
        return err

    ann = db.session.get(Announcement, ann_id)
    if not ann:
        return jsonify({"message": "Not found"}), 404
    if ann.status == 'Published':
        return jsonify({"message": "Already published"}), 400

    ann.status = 'Published'
    ann.published_at = datetime.utcnow()
    log_ann_event(ann.id, user.id, 'PUBLISHED')

    if ann.channels and ann.channels.get('in_app'):
        user_ids = resolve_audience(ann)
        deliver_in_app(ann, user_ids)

    db.session.commit()
    return jsonify({"status": "success", "message": f"{ann.ann_number} published to all targets.", "total_delivered": ann.total_delivered}), 200


# ─── Schedule ─────────────────────────────────────────────────────────────────

@announcement_bp.route('/<int:ann_id>/schedule', methods=['POST'])
@jwt_required()
def schedule_announcement(ann_id):
    user = get_current_user()
    err = require_admin(user)
    if err:
        return err

    ann = db.session.get(Announcement, ann_id)
    if not ann:
        return jsonify({"message": "Not found"}), 404

    data = request.get_json() or {}
    if not data.get('publish_at'):
        return jsonify({"message": "publish_at is required for scheduling"}), 422
    try:
        ann.publish_at = datetime.fromisoformat(data['publish_at'].replace('Z', ''))
    except ValueError:
        return jsonify({"message": "Invalid date format"}), 422

    ann.status = 'Scheduled'
    if data.get('expires_at'):
        ann.expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', ''))

    log_ann_event(ann.id, user.id, 'SCHEDULED', {"publish_at": ann.publish_at.isoformat()})
    db.session.commit()
    return jsonify({"status": "success", "message": f"{ann.ann_number} scheduled for {ann.publish_at.isoformat()}Z"}), 200


# ─── Unpublish ────────────────────────────────────────────────────────────────

@announcement_bp.route('/<int:ann_id>/unpublish', methods=['POST'])
@jwt_required()
def unpublish_announcement(ann_id):
    user = get_current_user()
    err = require_admin(user)
    if err:
        return err

    ann = db.session.get(Announcement, ann_id)
    if not ann:
        return jsonify({"message": "Not found"}), 404

    ann.status = 'Draft'
    ann.published_at = None
    log_ann_event(ann.id, user.id, 'UNPUBLISHED')
    db.session.commit()
    return jsonify({"status": "success", "message": f"{ann.ann_number} moved back to Draft."}), 200


# ─── Archive ──────────────────────────────────────────────────────────────────

@announcement_bp.route('/<int:ann_id>/archive', methods=['POST'])
@jwt_required()
def archive_announcement(ann_id):
    user = get_current_user()
    err = require_admin(user)
    if err:
        return err

    ann = db.session.get(Announcement, ann_id)
    if not ann:
        return jsonify({"message": "Not found"}), 404

    ann.status = 'Archived'
    log_ann_event(ann.id, user.id, 'ARCHIVED')
    db.session.commit()
    return jsonify({"status": "success", "message": f"{ann.ann_number} archived."}), 200


# ─── Duplicate ────────────────────────────────────────────────────────────────

@announcement_bp.route('/<int:ann_id>/duplicate', methods=['POST'])
@jwt_required()
def duplicate_announcement(ann_id):
    user = get_current_user()
    err = require_admin(user)
    if err:
        return err

    src = db.session.get(Announcement, ann_id)
    if not src:
        return jsonify({"message": "Not found"}), 404

    copy = Announcement(
        ann_number=ann_number(),
        created_by=user.id,
        title=f"[Copy] {src.title}",
        summary=src.summary,
        body=src.body,
        category=src.category,
        priority=src.priority,
        status='Draft',
        tags=src.tags,
        audience_type=src.audience_type,
        channels=src.channels,
        timezone=src.timezone,
    )
    db.session.add(copy)
    db.session.flush()

    for aud in src.audience:
        db.session.add(AnnouncementAudience(
            announcement_id=copy.id,
            target_type=aud.target_type,
            target_value=aud.target_value
        ))
    log_ann_event(copy.id, user.id, 'CREATED', {"duplicated_from": src.id})
    db.session.commit()
    return jsonify({"status": "success", "data": ann_to_dict(copy), "message": f"Duplicate created: {copy.ann_number}"}), 201


# ─── Delete ───────────────────────────────────────────────────────────────────

@announcement_bp.route('/<int:ann_id>', methods=['DELETE'])
@jwt_required()
def delete_announcement(ann_id):
    user = get_current_user()
    err = require_admin(user)
    if err:
        return err

    ann = db.session.get(Announcement, ann_id)
    if not ann:
        return jsonify({"message": "Not found"}), 404

    # Log before delete
    log_ann_event(ann.id, user.id, 'DELETED', {"title": ann.title})
    db.session.commit()

    # Archive instead of hard-delete to preserve history
    ann.status = 'Archived'
    ann.title = f"[DELETED] {ann.title}"
    db.session.commit()
    return jsonify({"status": "success", "message": "Announcement deleted (archived for audit trail)."}), 200


# ─── Delivery Status ──────────────────────────────────────────────────────────

@announcement_bp.route('/<int:ann_id>/delivery', methods=['GET'])
@jwt_required()
def get_delivery_status(ann_id):
    user = get_current_user()
    if not user or not user.role or user.role.name not in READ_ROLES:
        return jsonify({"message": "Unauthorized"}), 403

    ann = db.session.get(Announcement, ann_id)
    if not ann:
        return jsonify({"message": "Not found"}), 404

    deliveries = AnnouncementDelivery.query.filter_by(announcement_id=ann_id).all()
    by_channel = {}
    by_status = {}
    for d in deliveries:
        by_channel[d.channel] = by_channel.get(d.channel, 0) + 1
        by_status[d.status] = by_status.get(d.status, 0) + 1

    return jsonify({
        "status": "success",
        "data": {
            "total": len(deliveries),
            "by_channel": by_channel,
            "by_status": by_status,
            "recent": [{
                "id": d.id,
                "channel": d.channel,
                "status": d.status,
                "sent_at": d.sent_at.isoformat() + "Z" if d.sent_at else None,
                "error": d.error_message,
                "retry_count": d.retry_count
            } for d in deliveries[-50:]]
        }
    }), 200


# ─── Read Statistics ──────────────────────────────────────────────────────────

@announcement_bp.route('/<int:ann_id>/reads', methods=['GET'])
@jwt_required()
def get_read_stats(ann_id):
    user = get_current_user()
    if not user or not user.role or user.role.name not in READ_ROLES:
        return jsonify({"message": "Unauthorized"}), 403

    ann = db.session.get(Announcement, ann_id)
    if not ann:
        return jsonify({"message": "Not found"}), 404

    reads = AnnouncementRead.query.filter_by(announcement_id=ann_id).all()
    viewed = sum(1 for r in reads if r.viewed_at)
    read = sum(1 for r in reads if r.read_at)
    clicked = sum(1 for r in reads if r.clicked_at)
    dismissed = sum(1 for r in reads if r.dismissed_at)

    device_counts = {}
    for r in reads:
        dev = r.device or 'Unknown'
        device_counts[dev] = device_counts.get(dev, 0) + 1

    return jsonify({
        "status": "success",
        "data": {
            "total_delivered": ann.total_delivered,
            "total_viewed": viewed,
            "total_read": read,
            "total_clicked": clicked,
            "total_dismissed": dismissed,
            "unread": max(0, ann.total_delivered - read),
            "read_pct": round(read / ann.total_delivered * 100, 1) if ann.total_delivered > 0 else 0,
            "ctr": round(clicked / ann.total_delivered * 100, 1) if ann.total_delivered > 0 else 0,
            "by_device": device_counts,
        }
    }), 200


# ─── Mark Read ────────────────────────────────────────────────────────────────

@announcement_bp.route('/<int:ann_id>/mark-read', methods=['POST'])
@jwt_required()
def mark_read(ann_id):
    user = get_current_user()
    ann = db.session.get(Announcement, ann_id)
    if not ann:
        return jsonify({"message": "Not found"}), 404

    existing = AnnouncementRead.query.filter_by(announcement_id=ann_id, user_id=user.id).first()
    now = datetime.utcnow()
    if existing:
        if not existing.read_at:
            existing.read_at = now
            ann.total_read = max(0, ann.total_read + 1)
    else:
        r = AnnouncementRead(
            announcement_id=ann_id,
            user_id=user.id,
            org_id=user.org_id,
            viewed_at=now,
            read_at=now,
            device='Desktop',
            ip_address=request.remote_addr
        )
        db.session.add(r)
        ann.total_viewed = max(0, ann.total_viewed + 1)
        ann.total_read = max(0, ann.total_read + 1)

    db.session.commit()
    return jsonify({"status": "success", "message": "Marked as read"}), 200


# ─── Audit Logs ───────────────────────────────────────────────────────────────

@announcement_bp.route('/<int:ann_id>/audit', methods=['GET'])
@jwt_required()
def get_ann_audit(ann_id):
    user = get_current_user()
    if not user or not user.role or user.role.name not in READ_ROLES:
        return jsonify({"message": "Unauthorized"}), 403

    logs = AnnouncementAudit.query.filter_by(announcement_id=ann_id).order_by(AnnouncementAudit.created_at.desc()).all()
    return jsonify({
        "status": "success",
        "data": [{
            "id": l.id,
            "action": l.action,
            "actor": l.actor.username if l.actor else "System",
            "details": l.details,
            "ip_address": l.ip_address,
            "timestamp": l.created_at.isoformat() + "Z"
        } for l in logs]
    }), 200


# ─── Export ───────────────────────────────────────────────────────────────────

@announcement_bp.route('/export', methods=['POST'])
@jwt_required()
def export_announcements():
    user = get_current_user()
    err = require_admin(user)
    if err:
        return err

    data = request.get_json() or {}
    status_filter = data.get('status', '')
    priority_filter = data.get('priority', '')
    format_type = data.get('format', 'csv')

    query = Announcement.query
    if status_filter:
        query = query.filter(Announcement.status == status_filter)
    if priority_filter:
        query = query.filter(Announcement.priority == priority_filter)

    anns = query.order_by(Announcement.created_at.desc()).all()

    csv_lines = ["ID,Number,Title,Category,Priority,Status,Audience,Delivered,Read %,Published At,Expires At,Created By,Created At\n"]
    for a in anns:
        read_pct = round(a.total_read / a.total_delivered * 100, 1) if a.total_delivered > 0 else 0
        row = [
            str(a.id), a.ann_number, f'"{a.title}"', a.category, a.priority, a.status,
            a.audience_type, str(a.total_delivered), f"{read_pct}%",
            a.published_at.isoformat() if a.published_at else "",
            a.expires_at.isoformat() if a.expires_at else "",
            a.author.email if a.author else "",
            a.created_at.isoformat()
        ]
        csv_lines.append(",".join(row) + "\n")

    return jsonify({
        "status": "success",
        "format": format_type,
        "count": len(anns),
        "csv": "".join(csv_lines)
    }), 200


# ─── AI Insights ──────────────────────────────────────────────────────────────

@announcement_bp.route('/ai-insights', methods=['GET'])
@jwt_required()
def get_ai_insights():
    user = get_current_user()
    if not user or not user.role or user.role.name not in READ_ROLES:
        return jsonify({"message": "Unauthorized"}), 403

    total = Announcement.query.count()
    total_delivered = db.session.query(db.func.sum(Announcement.total_delivered)).scalar() or 0
    total_read = db.session.query(db.func.sum(Announcement.total_read)).scalar() or 0

    avg_read_rate = round(total_read / total_delivered * 100, 1) if total_delivered > 0 else 0

    # Best publish times heuristic
    best_times = ["Tuesday 10:00 AM IST", "Wednesday 2:00 PM IST", "Thursday 11:00 AM IST"]

    recommendations = []
    high_pri = Announcement.query.filter(Announcement.priority.in_(['High', 'Critical']), Announcement.status == 'Published').count()
    if high_pri > 0:
        recommendations.append(f"{high_pri} high/critical priority announcements are live. Ensure read confirmations are collected for compliance.")
    if avg_read_rate < 50:
        recommendations.append("Read rate is below 50%. Consider shorter titles, higher-contrast banners, and pushing via email.")
    else:
        recommendations.append("Read rate is healthy. Continue monitoring weekly to detect drops.")

    drafts = Announcement.query.filter_by(status='Draft').count()
    if drafts > 5:
        recommendations.append(f"You have {drafts} unfinished drafts. Review and either publish or archive stale content.")

    return jsonify({
        "status": "success",
        "data": {
            "predicted_read_rate": avg_read_rate,
            "best_publish_times": best_times,
            "engagement_score": min(100, int(avg_read_rate * 1.2)),
            "recommendations": recommendations,
            "performance_score": round(min(100, (avg_read_rate * 0.6) + (min(total, 20) * 2)), 1),
            "suggested_category": "Maintenance" if datetime.utcnow().weekday() == 5 else "General",
        }
    }), 200


# ─── Recipient User Endpoints ──────────────────────────────────────────────────

@announcement_bp.route('/user-active', methods=['GET'])
@jwt_required()
def get_user_active_announcements():
    user = get_current_user()
    if not user:
        return jsonify({"message": "User not found"}), 404

    now = datetime.utcnow()
    # Published announcements that are active
    query = Announcement.query.filter(
        Announcement.status == 'Published',
        db.or_(Announcement.publish_at == None, Announcement.publish_at <= now),
        db.or_(Announcement.expires_at == None, Announcement.expires_at > now)
    ).order_by(Announcement.created_at.desc())

    published_anns = query.all()
    user_anns = []

    for ann in published_anns:
        if user_matches_announcement(user, ann):
            read_rec = AnnouncementRead.query.filter_by(announcement_id=ann.id, user_id=user.id).first()
            is_read = bool(read_rec and read_rec.read_at)
            is_dismissed = bool(read_rec and read_rec.dismissed_at)

            d = ann_to_dict(ann, include_body=True)
            d["is_read"] = is_read
            d["is_dismissed"] = is_dismissed
            user_anns.append(d)

    return jsonify({
        "status": "success",
        "data": user_anns,
        "count": len(user_anns)
    }), 200


@announcement_bp.route('/<int:ann_id>/dismiss', methods=['POST'])
@jwt_required()
def dismiss_announcement(ann_id):
    user = get_current_user()
    if not user:
        return jsonify({"message": "User not found"}), 404

    ann = db.session.get(Announcement, ann_id)
    if not ann:
        return jsonify({"message": "Announcement not found"}), 404

    read_rec = AnnouncementRead.query.filter_by(announcement_id=ann_id, user_id=user.id).first()
    now = datetime.utcnow()
    if not read_rec:
        read_rec = AnnouncementRead(
            announcement_id=ann_id,
            user_id=user.id,
            org_id=user.org_id,
            viewed_at=now,
            dismissed_at=now,
            device='Desktop',
            ip_address=request.remote_addr
        )
        db.session.add(read_rec)
        ann.total_viewed = max(0, ann.total_viewed + 1)
    else:
        read_rec.dismissed_at = now

    db.session.commit()
    return jsonify({"status": "success", "message": "Announcement dismissed"}), 200


@announcement_bp.route('/my-announcements', methods=['GET'])
@jwt_required()
def get_my_announcements():
    user = get_current_user()
    if not user:
        return jsonify({"message": "User not found"}), 404

    now = datetime.utcnow()
    q_str = request.args.get('q', '').strip().lower()
    cat_filter = request.args.get('category', '').strip()
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'

    query = Announcement.query.filter(
        Announcement.status.in_(['Published', 'Expired']),
        db.or_(Announcement.publish_at == None, Announcement.publish_at <= now)
    ).order_by(Announcement.created_at.desc())

    if cat_filter:
        query = query.filter(Announcement.category == cat_filter)

    all_anns = query.all()
    user_anns = []

    for ann in all_anns:
        if user_matches_announcement(user, ann):
            if q_str and (q_str not in (ann.title or '').lower() and q_str not in (ann.summary or '').lower()):
                continue

            read_rec = AnnouncementRead.query.filter_by(announcement_id=ann.id, user_id=user.id).first()
            is_read = bool(read_rec and read_rec.read_at)
            is_dismissed = bool(read_rec and read_rec.dismissed_at)

            if unread_only and is_read:
                continue

            d = ann_to_dict(ann, include_body=True)
            d["is_read"] = is_read
            d["is_dismissed"] = is_dismissed
            user_anns.append(d)

    return jsonify({
        "status": "success",
        "data": user_anns,
        "total": len(user_anns)
    }), 200
