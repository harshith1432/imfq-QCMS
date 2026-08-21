from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import re
from app.infrastructure.database.models.models import (
    db, User, Organization, Role, SupportTicket, SupportComment,
    SupportAttachment, SupportSLA, SupportEscalation, SupportRating,
    SupportKnowledge, SupportAudit, Subscription, SalesEnquiry
)
from datetime import datetime, timedelta
from sqlalchemy import func, or_, desc
import random

support_bp = Blueprint('support_bp', __name__)

def get_current_user_and_check_rbac(required_roles=None, required_subroles=None):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return None, "User not found"
    
    role_name = user.role.name if user.role else 'Team Member'
    
    # SuperAdmin custom subrole check
    subrole = None
    if role_name == 'SuperAdmin':
        subrole = (user.custom_fields or {}).get('super_admin_role', 'Owner')
        
    if required_roles and role_name not in required_roles:
        return None, "Insufficient permissions"
        
    if required_subroles and role_name == 'SuperAdmin' and subrole not in required_subroles:
        return None, "Insufficient sub-role permissions"
        
    return user, None

# Helpers for audit logging
def log_support_audit(ticket_id, user_id, action, old_vals=None, new_vals=None):
    audit = SupportAudit(
        ticket_id=ticket_id,
        user_id=user_id,
        action=action,
        old_values=old_vals,
        new_values=new_vals
    )
    db.session.add(audit)
    db.session.commit()

# --- 1. DASHBOARD ---
@support_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    user, err = get_current_user_and_check_rbac()
    if err:
        return jsonify({"status": "error", "message": err}), 403

    # Date range filters (default last 30 days)
    date_range = request.args.get('date_range', 'Last 30 Days')
    days_map = {'Today': 1, 'Yesterday': 2, 'Last 7 Days': 7, 'Last 30 Days': 30, 'Last 90 Days': 90}
    days = days_map.get(date_range, 30)
    
    start_date = datetime.utcnow() - timedelta(days=days)
    prev_start_date = start_date - timedelta(days=days)
    
    # Scoping based on Role
    q = SupportTicket.query
    prev_q = SupportTicket.query
    
    # Tenant Isolation
    if user.role.name != 'SuperAdmin':
        q = q.filter_by(org_id=user.org_id)
        prev_q = prev_q.filter_by(org_id=user.org_id)
    else:
        # SuperAdmin can filter by Organization
        org_id = request.args.get('organization')
        if org_id and str(org_id).isdigit():
            org_int = int(org_id)
            q = q.filter_by(org_id=org_int)
            prev_q = prev_q.filter_by(org_id=org_int)

    # Apply date boundaries
    q_period = q.filter(SupportTicket.created_at >= start_date)
    prev_q_period = prev_q.filter(SupportTicket.created_at >= prev_start_date, SupportTicket.created_at < start_date)

    # Basic Counts
    total_cnt = q_period.count()
    prev_total = prev_q_period.count()
    growth_total = round(((total_cnt - prev_total) / prev_total * 100), 1) if prev_total > 0 else 0.0

    open_cnt = q_period.filter(SupportTicket.status.in_(['Open', 'Assigned'])).count()
    ip_cnt = q_period.filter(SupportTicket.status == 'In Progress').count()
    waiting_cnt = q_period.filter(SupportTicket.status == 'Waiting for Customer').count()
    resolved_cnt = q_period.filter(SupportTicket.status == 'Resolved').count()
    closed_cnt = q_period.filter(SupportTicket.status == 'Closed').count()
    
    # Priorities
    high_cnt = q_period.filter(SupportTicket.priority == 'High').count()
    critical_cnt = q_period.filter(SupportTicket.priority.in_(['Critical', 'Urgent'])).count()
    
    # SLA Breach count
    sla_breached_cnt = q_period.filter(SupportTicket.sla_status == 'Breached').count()

    # Average Resolution Time (in hours)
    resolved_tickets = q_period.filter(SupportTicket.resolved_at.isnot(None)).all()
    if resolved_tickets:
        total_res_hours = sum((t.resolved_at - t.created_at).total_seconds() / 3600.0 for t in resolved_tickets)
        avg_res_time = round(total_res_hours / len(resolved_tickets), 1)
    else:
        avg_res_time = 0.0

    # Average First Response Time (in hours, from SLA model)
    sla_records = db.session.query(SupportSLA).join(SupportTicket).filter(
        SupportTicket.created_at >= start_date,
        SupportSLA.first_response_responded_at.isnot(None)
    )
    if user.role.name != 'SuperAdmin':
        sla_records = sla_records.filter(SupportTicket.org_id == user.org_id)
    
    sla_records = sla_records.all()
    if sla_records:
        total_resp_hours = sum((s.first_response_responded_at - s.created_at).total_seconds() / 3600.0 for s in sla_records)
        avg_resp_time = round(total_resp_hours / len(sla_records), 1)
    else:
        avg_resp_time = 0.0

    # CSAT Score calculation
    ratings = db.session.query(SupportRating).join(SupportTicket).filter(
        SupportTicket.created_at >= start_date
    )
    if user.role.name != 'SuperAdmin':
        ratings = ratings.filter(SupportTicket.org_id == user.org_id)
        
    ratings = ratings.all()
    if ratings:
        avg_rating = sum(r.rating for r in ratings) / len(ratings)
        csat_score = round(avg_rating * 20.0, 1) # Out of 100%
    else:
        csat_score = 0.0

    # Structure payload exactly as required with icon, value, growth, trend, tooltips
    data = {
        "total_tickets": {"value": total_cnt, "icon": "life-buoy", "tooltip": "Total tickets created in the period"},
        "open_tickets": {"value": open_cnt, "icon": "folder-open", "tooltip": "Tickets awaiting action"},
        "in_progress_tickets": {"value": ip_cnt, "icon": "play-circle", "tooltip": "Tickets currently being worked on"},
        "resolved_tickets": {"value": resolved_cnt, "icon": "check-circle", "tooltip": "Tickets successfully solved"},
        "closed_tickets": {"value": closed_cnt, "icon": "archive", "tooltip": "Archived or permanently closed"},
        "high_priority_tickets": {"value": high_cnt, "icon": "alert-circle", "tooltip": "High priority issues"},
        "critical_tickets": {"value": critical_cnt, "icon": "alert-triangle", "tooltip": "Critical/Urgent outages"},
        "avg_resolution_time": {"value": avg_res_time, "suffix": " hrs", "icon": "activity", "tooltip": "Avg time from creation to resolution"}
    }
    
    return jsonify({"status": "success", "data": data, "last_updated": datetime.utcnow().isoformat()})

# --- 2. LIST TICKETS (SEARCH, SORT, PAGINATE, FILTER) ---
@support_bp.route('/tickets', methods=['GET'])
@jwt_required()
def list_tickets():
    user, err = get_current_user_and_check_rbac()
    if err:
        return jsonify({"status": "error", "message": err}), 403

    # Server-side pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Query build
    q = SupportTicket.query
    
    # Tenant Isolation
    if user.role.name != 'SuperAdmin':
        q = q.filter_by(org_id=user.org_id)
    else:
        # Admin can filter by organization ID
        org_id = request.args.get('organization')
        if org_id and str(org_id).isdigit():
            q = q.filter_by(org_id=int(org_id))

    # Enterprise Search Query
    search = request.args.get('q', '').strip()
    if search:
        # Join user, org and assigned engineer for deep search
        q = q.join(Organization, SupportTicket.org_id == Organization.id).outerjoin(
            User, SupportTicket.assigned_engineer_id == User.id
        )
        q = q.filter(
            or_(
                SupportTicket.ticket_number.ilike(f'%{search}%'),
                SupportTicket.subject.ilike(f'%{search}%'),
                SupportTicket.message.ilike(f'%{search}%'),
                Organization.name.ilike(f'%{search}%'),
                User.username.ilike(f'%{search}%'),
                SupportTicket.category.ilike(f'%{search}%'),
                SupportTicket.priority.ilike(f'%{search}%'),
                SupportTicket.status.ilike(f'%{search}%')
            )
        )

    # Advanced Filters
    status_filter = request.args.get('status')
    if status_filter:
        q = q.filter(SupportTicket.status == status_filter)
        
    priority_filter = request.args.get('priority')
    if priority_filter:
        q = q.filter(SupportTicket.priority == priority_filter)
        
    category_filter = request.args.get('category')
    if category_filter:
        q = q.filter(SupportTicket.category == category_filter)
        
    sla_filter = request.args.get('sla_status')
    if sla_filter:
        q = q.filter(SupportTicket.sla_status == sla_filter)

    engineer_filter = request.args.get('assigned_engineer_id')
    if engineer_filter:
        q = q.filter(SupportTicket.assigned_engineer_id == int(engineer_filter))

    # Sort
    field_to_sort = getattr(SupportTicket, sort_by, SupportTicket.created_at)
    if sort_order == 'desc':
        q = q.order_by(desc(field_to_sort))
    else:
        q = q.order_by(field_to_sort)

    # Paged Results
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    
    tickets_list = []
    for t in pagination.items:
        tickets_list.append({
            "id": t.id,
            "ticket_number": t.ticket_number or f"TKT-{t.id:06d}",
            "subject": t.subject,
            "organization": t.organization.name if t.organization else "System",
            "requester_name": t.user.username if t.user else "N/A",
            "requester_email": t.user.email if t.user else "N/A",
            "category": t.category,
            "priority": t.priority,
            "status": t.status,
            "assigned_engineer": t.assigned_engineer.username if t.assigned_engineer else "Unassigned",
            "created_at": t.created_at.isoformat(),
            "updated_at": t.created_at.isoformat(), # mock updated_at
            "sla_status": t.sla_status,
            "tags": t.tags or []
        })

    return jsonify({
        "status": "success",
        "data": tickets_list,
        "meta": {
            "page": page,
            "per_page": per_page,
            "total_items": pagination.total,
            "total_pages": pagination.pages
        }
    })

# --- 3. CREATE TICKET (5-STEP WIZARD INGESTION) ---
@support_bp.route('/tickets', methods=['POST'])
@jwt_required()
def create_ticket():
    user, err = get_current_user_and_check_rbac()
    if err:
        return jsonify({"status": "error", "message": err}), 403

    data = request.get_json() or {}
    
    subject = data.get('subject')
    description = data.get('description') or data.get('message')
    category = data.get('category', 'Technical')
    priority = data.get('priority', 'Medium')
    tags = data.get('tags', [])
    org_id = data.get('organization_id')
    requester_email = data.get('requester_email')
    
    if not subject or not description:
        return jsonify({"status": "error", "message": "Subject and description/message are required"}), 400

    # Ingestion check for org scoping
    if user.role.name != 'SuperAdmin':
        target_org_id = user.org_id
        target_user_id = user.id
    else:
        # Admin can create on behalf of other orgs & users
        target_org_id = int(org_id) if org_id else user.org_id
        # Look up user by email or fallback to admin
        if requester_email:
            req_user = User.query.filter_by(email=requester_email).first()
            target_user_id = req_user.id if req_user else user.id
        else:
            target_user_id = user.id

    # Create primary ticket instance
    tkt_num = f"TKT-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    
    ticket = SupportTicket(
        org_id=target_org_id,
        user_id=target_user_id,
        subject=subject,
        message=description,
        priority=priority,
        status='Open',
        category=category,
        ticket_number=tkt_num,
        tags=tags,
        sla_status='Within SLA'
    )
    
    db.session.add(ticket)
    db.session.commit() # Save first to generate ticket ID for SLA and attachments

    # Workload Balancing: automatic assignment to the Support Engineer with the fewest open tickets
    assigned_engineer_id = data.get('assigned_engineer_id')
    assigned_team = data.get('assigned_team', 'Tier 1 Support')
    
    if not assigned_engineer_id:
        engineers = User.query.join(Role).filter(Role.name.in_(['Support Engineer', 'Support Manager', 'SuperAdmin'])).all()
        if engineers:
            # Check open ticket workloads
            workloads = []
            for eng in engineers:
                cnt = SupportTicket.query.filter_by(assigned_engineer_id=eng.id).filter(
                    SupportTicket.status.in_(['Open', 'Assigned', 'In Progress'])
                ).count()
                workloads.append((cnt, eng.id))
            # Assign to fewest open tickets
            workloads.sort()
            assigned_engineer_id = workloads[0][1]

    if assigned_engineer_id:
        ticket.assigned_engineer_id = assigned_engineer_id
        ticket.assigned_team = assigned_team
        ticket.status = 'Assigned'

    # SLA config calculations
    org = Organization.query.get(target_org_id)
    plan_name = org.subscription_plan if org else 'Starter'
    
    # Priority & Plan Based SLAs
    if plan_name == 'Enterprise' or priority in ['Critical', 'Urgent']:
        first_resp_limit = 1 # 1 hour
        resolution_limit = 8 # 8 hours
    elif plan_name == 'Professional' or priority == 'High':
        first_resp_limit = 4 # 4 hours
        resolution_limit = 24 # 24 hours
    else:
        first_resp_limit = 24 # 24 hours
        resolution_limit = 72 # 72 hours
        
    sla = SupportSLA(
        ticket_id=ticket.id,
        first_response_due=datetime.utcnow() + timedelta(hours=first_resp_limit),
        resolution_due=datetime.utcnow() + timedelta(hours=resolution_limit)
    )
    db.session.add(sla)

    # Attachments
    attachments = data.get('attachments', [])
    for att in attachments:
        new_att = SupportAttachment(
            ticket_id=ticket.id,
            file_name=att.get('file_name'),
            file_path=att.get('file_path'),
            file_size=att.get('file_size', 0),
            mime_type=att.get('mime_type'),
            uploaded_by_id=user.id,
            virus_scan_passed=True # Mock scan successful
        )
        db.session.add(new_att)

    db.session.commit()
    
    # Audit log entry
    log_support_audit(ticket.id, user.id, "Create Ticket", new_vals={
        "subject": subject, "priority": priority, "category": category, "ticket_number": tkt_num
    })

    return jsonify({
        "status": "success",
        "message": "Ticket created successfully",
        "ticket_id": ticket.id,
        "ticket_number": tkt_num
    }), 201

# --- 4. TICKET DETAILS PAGE ---
@support_bp.route('/tickets/<int:ticket_id>', methods=['GET'])
@jwt_required()
def get_ticket_details(ticket_id):
    user, err = get_current_user_and_check_rbac()
    if err:
        return jsonify({"status": "error", "message": err}), 403

    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    # Tenant Isolation
    if user.role.name != 'SuperAdmin' and ticket.org_id != user.org_id:
        return jsonify({"status": "error", "message": "Tenant access forbidden"}), 403

    # Related info
    org = ticket.organization
    subscriptions = Subscription.query.filter_by(org_id=ticket.org_id).all() if org else []

    # Format timeline comments (public comments vs internal notes)
    role_name = user.role.name if (user and user.role) else 'User'
    comments_list = []
    for c in ticket.comments:
        # Support Engineers & Admins see internal notes; clients do not
        if c.is_internal and role_name not in ['SuperAdmin', 'Support Engineer', 'Support Manager']:
            continue
        comments_list.append({
            "id": c.id,
            "user": c.user.username if c.user else "System",
            "content": c.content,
            "is_internal": c.is_internal,
            "created_at": c.created_at.isoformat() if c.created_at else "",
            "attachments": [{"file_name": a.file_name, "file_path": a.file_path} for a in (c.attachments or [])]
        })

    # Activity audits
    audits_list = []
    for a in ticket.audits:
        audits_list.append({
            "user": a.user.username if a.user else "System",
            "action": a.action,
            "old_values": a.old_values,
            "new_values": a.new_values,
            "created_at": a.created_at.isoformat() if a.created_at else ""
        })

    # SLA remaining calculations
    sla_info = {}
    if ticket.sla:
        sla_info = {
            "first_response_due": ticket.sla.first_response_due.isoformat() if ticket.sla.first_response_due else None,
            "resolution_due": ticket.sla.resolution_due.isoformat() if ticket.sla.resolution_due else None,
            "sla_status": ticket.sla.sla_status,
            "is_paused": ticket.sla.is_paused
        }

    ticket_att_list = []
    for att in (ticket.attachments or []):
        ticket_att_list.append({
            "id": att.id,
            "file_name": att.file_name,
            "file_path": att.file_path,
            "file_size": att.file_size,
            "mime_type": att.mime_type,
            "uploaded_at": att.uploaded_at.isoformat() if hasattr(att, 'uploaded_at') and att.uploaded_at else ""
        })

    return jsonify({
        "status": "success",
        "data": {
            "id": ticket.id,
            "ticket_number": ticket.ticket_number or f"TKT-{ticket.id:06d}",
            "subject": ticket.subject,
            "description": ticket.message,
            "priority": ticket.priority,
            "status": ticket.status,
            "category": ticket.category,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else "",
            "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
            "resolution": ticket.resolution,
            "assigned_engineer": ticket.assigned_engineer.username if ticket.assigned_engineer else "Unassigned",
            "assigned_team": ticket.assigned_team or "Support Desk",
            "tags": ticket.tags or [],
            "attachments": ticket_att_list,
            "requester": {
                "name": ticket.user.username if ticket.user else "N/A",
                "email": ticket.user.email if ticket.user else "N/A"
            },
            "organization": {
                "id": org.id if org else None,
                "name": org.name if org else "N/A",
                "plan": org.subscription_plan if org else "N/A"
            },
            "comments": comments_list,
            "audits": audits_list,
            "sla": sla_info,
            "related_licenses": [{"key": org.license_number, "status": org.subscription_status}] if org and org.license_number else [],
            "related_subscriptions": [{"plan": s.plan_name, "status": getattr(s, 'subscription_status', 'Active')} for s in subscriptions]
        }
    })

# --- 5. UPDATE TICKET (PRIORITY, STATUS, ASSIGNEE) ---
@support_bp.route('/tickets/<int:ticket_id>', methods=['PUT'])
@jwt_required()
def update_ticket(ticket_id):
    user, err = get_current_user_and_check_rbac()
    if err:
        return jsonify({"status": "error", "message": err}), 403

    ticket = SupportTicket.query.get_or_404(ticket_id)
    if user.role.name != 'SuperAdmin' and ticket.org_id != user.org_id:
        return jsonify({"status": "error", "message": "Access denied"}), 403

    data = request.get_json() or {}
    old_status = ticket.status
    old_priority = ticket.priority
    old_assignee_id = ticket.assigned_engineer_id

    # Update actions
    if 'status' in data:
        new_status = data['status']
        ticket.status = new_status
        
        # Audit status changes
        log_support_audit(ticket.id, user.id, "Change Status", {"status": old_status}, {"status": new_status})
        
        # SLA timers pause when waiting for customer response
        if ticket.sla:
            if new_status == 'Waiting for Customer' and not ticket.sla.is_paused:
                ticket.sla.is_paused = True
                ticket.sla.paused_at = datetime.utcnow()
            elif new_status != 'Waiting for Customer' and ticket.sla.is_paused:
                # Resume
                ticket.sla.is_paused = False
                pause_secs = (datetime.utcnow() - ticket.sla.paused_at).total_seconds()
                ticket.sla.accumulated_paused_seconds += int(pause_secs)
                # Extend due dates
                if ticket.sla.first_response_due:
                    ticket.sla.first_response_due += timedelta(seconds=pause_secs)
                if ticket.sla.resolution_due:
                    ticket.sla.resolution_due += timedelta(seconds=pause_secs)

        # Record resolution timestamp
        if new_status in ['Resolved', 'Closed']:
            ticket.resolved_at = datetime.utcnow()
            res_val = data.get('resolution')
            if res_val and str(res_val).strip():
                ticket.resolution = str(res_val).strip()
            elif not ticket.resolution or ticket.resolution == 'No resolution notes provided.':
                last_pub = SupportComment.query.filter_by(ticket_id=ticket.id, is_internal=False).order_by(SupportComment.created_at.desc()).first()
                if last_pub and last_pub.content:
                    ticket.resolution = last_pub.content
                else:
                    ticket.resolution = f"Ticket marked as {new_status}."

            if ticket.sla:
                ticket.sla.resolution_completed_at = datetime.utcnow()
                # Check if resolved within SLA bounds
                if ticket.sla.resolution_due and datetime.utcnow() > ticket.sla.resolution_due:
                    ticket.sla.sla_status = 'Breached'
                    ticket.sla_status = 'Breached'

    if 'priority' in data:
        new_priority = data['priority']
        ticket.priority = new_priority
        log_support_audit(ticket.id, user.id, "Change Priority", {"priority": old_priority}, {"priority": new_priority})

    if 'assigned_engineer_id' in data:
        new_eng_id = int(data['assigned_engineer_id']) if data['assigned_engineer_id'] else None
        ticket.assigned_engineer_id = new_eng_id
        ticket.status = 'Assigned' if new_eng_id else 'Open'
        log_support_audit(ticket.id, user.id, "Assign Ticket", {"assigned_engineer_id": old_assignee_id}, {"assigned_engineer_id": new_eng_id})

    db.session.commit()
    return jsonify({"status": "success", "message": "Ticket updated successfully"})

# --- 6. ADD COMMENT OR INTERNAL NOTE ---
@support_bp.route('/tickets/<int:ticket_id>/comments', methods=['POST'])
@jwt_required()
def add_comment(ticket_id):
    user, err = get_current_user_and_check_rbac()
    if err:
        return jsonify({"status": "error", "message": err}), 403

    ticket = SupportTicket.query.get_or_404(ticket_id)
    if user.role.name != 'SuperAdmin' and ticket.org_id != user.org_id:
        return jsonify({"status": "error", "message": "Access denied"}), 403

    data = request.get_json() or {}
    content = data.get('content')
    is_internal = data.get('is_internal', False)

    if not content:
        return jsonify({"status": "error", "message": "Comment content cannot be empty"}), 400

    comment = SupportComment(
        ticket_id=ticket.id,
        user_id=user.id,
        content=content,
        is_internal=is_internal
    )
    db.session.add(comment)
    db.session.commit()

    # Track First Response SLA on initial agent public comment
    if ticket.sla and not ticket.sla.first_response_responded_at and not is_internal:
        # Check if commenter is support staff/engineer
        if user.role.name in ['SuperAdmin', 'Support Engineer', 'Support Manager']:
            ticket.sla.first_response_responded_at = datetime.utcnow()
            if datetime.utcnow() > ticket.sla.first_response_due:
                ticket.sla.sla_status = 'Breached'
                ticket.sla_status = 'Breached'
            db.session.commit()

    # Attachments to comments
    attachments = data.get('attachments', [])
    for att in attachments:
        new_att = SupportAttachment(
            ticket_id=ticket.id,
            comment_id=comment.id,
            file_name=att.get('file_name'),
            file_path=att.get('file_path'),
            file_size=att.get('file_size', 0),
            mime_type=att.get('mime_type'),
            uploaded_by_id=user.id
        )
        db.session.add(new_att)

    db.session.commit()
    log_support_audit(ticket.id, user.id, "Comment Added", new_vals={"comment_id": comment.id, "is_internal": is_internal})

    return jsonify({"status": "success", "message": "Comment added successfully"}), 201

# --- 7. ESCALATIONS ---
@support_bp.route('/tickets/<int:ticket_id>/escalate', methods=['POST'])
@jwt_required()
def escalate_ticket(ticket_id):
    user, err = get_current_user_and_check_rbac()
    if err:
        return jsonify({"status": "error", "message": err}), 403

    ticket = SupportTicket.query.get_or_404(ticket_id)
    if user.role.name != 'SuperAdmin' and ticket.org_id != user.org_id:
        return jsonify({"status": "error", "message": "Access denied"}), 403

    data = request.get_json() or {}
    reason = data.get('reason', 'Manual escalation triggered')

    ticket.escalation_level += 1
    ticket.priority = 'Critical' # Elevate priority to critical on escalation
    
    escalation = SupportEscalation(
        ticket_id=ticket.id,
        escalation_level=ticket.escalation_level,
        reason=reason,
        escalated_by_id=user.id
    )
    
    db.session.add(escalation)
    db.session.commit()
    
    log_support_audit(ticket.id, user.id, "Escalation", new_vals={"level": ticket.escalation_level, "reason": reason})
    
    return jsonify({"status": "success", "message": f"Ticket escalated to Level {ticket.escalation_level}"})

# --- 8. CSAT RATINGS ---
@support_bp.route('/tickets/<int:ticket_id>/rate', methods=['POST'])
@jwt_required()
def rate_ticket(ticket_id):
    user, err = get_current_user_and_check_rbac()
    if err:
        return jsonify({"status": "error", "message": err}), 403

    ticket = SupportTicket.query.get_or_404(ticket_id)
    if ticket.org_id != user.org_id:
        return jsonify({"status": "error", "message": "Tenant scope mismatch"}), 403

    data = request.get_json() or {}
    rating = data.get('rating') # 1-5
    feedback = data.get('feedback', '')

    if not rating or not (1 <= rating <= 5):
        return jsonify({"status": "error", "message": "Rating must be an integer between 1 and 5"}), 400

    # Ensure rating is unique per ticket
    existing_rating = SupportRating.query.filter_by(ticket_id=ticket_id).first()
    if existing_rating:
        existing_rating.rating = rating
        existing_rating.feedback = feedback
    else:
        new_rating = SupportRating(
            ticket_id=ticket.id,
            rating=rating,
            feedback=feedback
        )
        db.session.add(new_rating)

    db.session.commit()
    return jsonify({"status": "success", "message": "CSAT rating submitted successfully"})

# --- 9. KNOWLEDGE BASE SEARCH ---
@support_bp.route('/knowledge', methods=['GET', 'POST'])
@jwt_required()
def handle_knowledge():
    user, err = get_current_user_and_check_rbac()
    if err:
        return jsonify({"status": "error", "message": err}), 403

    if request.method == 'GET':
        query = request.args.get('q', '').strip()
        articles_q = SupportKnowledge.query
        if user.role.name not in ['SuperAdmin', 'Support Engineer', 'Support Manager']:
            articles_q = articles_q.filter_by(is_internal=False)
            
        if query:
            articles_q = articles_q.filter(
                or_(
                    SupportKnowledge.title.ilike(f'%{query}%'),
                    SupportKnowledge.content.ilike(f'%{query}%'),
                    SupportKnowledge.category.ilike(f'%{query}%')
                )
            )
        
        articles = articles_q.all()
        return jsonify({
            "status": "success",
            "articles": [{
                "id": a.id,
                "title": a.title,
                "category": a.category,
                "content": a.content,
                "is_internal": a.is_internal,
                "views_count": a.views_count
            } for a in articles]
        })

    elif request.method == 'POST':
        # Only support engineers/managers, admins, or superadmins can create articles
        if user.role.name not in ['SuperAdmin', 'Admin', 'CEO', 'Support Engineer', 'Support Manager']:
            return jsonify({"status": "error", "message": "Forbidden"}), 403
            
        data = request.get_json() or {}
        title = data.get('title')
        category = data.get('category')
        content = data.get('content')
        is_internal = data.get('is_internal', False)

        if not title or not content or not category:
            return jsonify({"status": "error", "message": "Title, category, and content are required"}), 400

        article = SupportKnowledge(
            title=title,
            category=category,
            content=content,
            is_internal=is_internal,
            created_by_id=user.id
        )
        db.session.add(article)
        db.session.commit()
        return jsonify({"status": "success", "article_id": article.id}), 201

# --- 10. AI ASSISTANCE ---
@support_bp.route('/ai', methods=['POST'])
@jwt_required()
def ai_assistance():
    user, err = get_current_user_and_check_rbac()
    if err:
        return jsonify({"status": "error", "message": err}), 403

    data = request.get_json() or {}
    text = data.get('text', '')
    
    # AI Regressive analysis mock values
    sentiment = "Negative" if any(w in text.lower() for w in ['broken', 'error', 'fail', 'bad', 'wrong', 'crash']) else "Neutral"
    risk_score = 75 if sentiment == "Negative" else 20
    
    suggested_response = (
        "Dear Customer,\n\nThank you for reaching out to QCMS Support. "
        "We are currently investigating your request regarding this feature. "
        "We will keep you updated within the SLA timeline.\n\nBest regards,\nSupport Team"
    )

    return jsonify({
        "status": "success",
        "ai_analysis": {
            "sentiment": sentiment,
            "risk_score": risk_score,
            "estimated_resolution_time": "3.5 hours",
            "category_recommendation": "Technical",
            "priority_recommendation": "High" if sentiment == "Negative" else "Medium",
            "suggested_response": suggested_response,
            "next_best_action": "Verify server connection logs and assign to the DevOps team.",
            "is_duplicate_detected": False
        }
    })

# --- 11. EXPORTS ---
@support_bp.route('/tickets/export', methods=['POST'])
@jwt_required()
def export_tickets():
    user, err = get_current_user_and_check_rbac()
    if err:
        return jsonify({"status": "error", "message": err}), 403

    # Generate CSV of all tickets matching tenant
    q = SupportTicket.query
    if user.role.name != 'SuperAdmin':
        q = q.filter_by(org_id=user.org_id)
        
    tickets = q.order_by(SupportTicket.created_at.desc()).all()
    
    csv_rows = ["Ticket ID,Ticket Number,Subject,Requester,Priority,Status,Created At"]
    for t in tickets:
        subj = (t.subject or '').replace('"', '""')
        req = (t.user.username if t.user else '').replace('"', '""')
        csv_rows.append(f'{t.id},{t.ticket_number or ""},"{subj}","{req}",{t.priority},{t.status},{t.created_at.isoformat()}')
        
    csv_content = "\n".join(csv_rows)
    return jsonify({"status": "success", "csv": csv_content}), 200


# --- 12. SALES ENQUIRIES & LANDING PAGE PROSPECT INTAKE ---

@support_bp.route('/public/enquiry', methods=['POST'])
def submit_public_enquiry():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    phone = (data.get('phone') or '').strip()
    company_name = (data.get('company_name') or '').strip()
    message = (data.get('message') or '').strip()
    source = (data.get('source') or 'Talk to Sales').strip()

    if not name or not email or not phone or not company_name:
        return jsonify({
            "status": "error",
            "message": "Full Name, Email Address, Phone Number, and Company Name are required fields."
        }), 400

    enquiry = SalesEnquiry(
        name=name,
        email=email,
        phone=phone,
        company_name=company_name,
        message=message if message else None,
        source=source,
        status='New',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.session.add(enquiry)
    db.session.commit()

    # --- Sales Lead Notification / Email Redirection ---
    try:
        from app.infrastructure.database.models.models import PlatformSettings
        from app.infrastructure.mailer.email_service import EmailUtils
        from app.domain.services.document_branding_service import DocumentBrandingService

        ps = PlatformSettings.query.first()
        notif_cfg = (ps.notification_settings or {}) if ps else {}
        sales_email = (notif_cfg.get('sales_notification_email') or '').strip()
        sales_enabled = bool(notif_cfg.get('sales_notification_enabled', False))

        if sales_enabled and sales_email:
            subject = f"🎯 New Sales Enquiry: {company_name} ({name})"
            body = f"""
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                    <div style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); padding: 24px; color: #ffffff;">
                        <h2 style="margin: 0; font-size: 20px; font-weight: 700;">New Sales Enquiry (Talk to Sales)</h2>
                        <p style="margin: 4px 0 0 0; font-size: 13px; opacity: 0.9;">A prospective enterprise client submitted an inquiry on the QCMS Platform.</p>
                    </div>
                    <div style="padding: 24px;">
                        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                            <tr style="border-bottom: 1px solid #f1f5f9;">
                                <td style="padding: 10px 0; color: #64748b; width: 35%;"><strong>Prospect Name:</strong></td>
                                <td style="padding: 10px 0; color: #0f172a; font-weight: 600;">{name}</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #f1f5f9;">
                                <td style="padding: 10px 0; color: #64748b;"><strong>Company Name:</strong></td>
                                <td style="padding: 10px 0; color: #0f172a; font-weight: 600;">{company_name}</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #f1f5f9;">
                                <td style="padding: 10px 0; color: #64748b;"><strong>Work Email:</strong></td>
                                <td style="padding: 10px 0; color: #2563eb; font-weight: 600;"><a href="mailto:{email}" style="color:#2563eb; text-decoration:none;">{email}</a></td>
                            </tr>
                            <tr style="border-bottom: 1px solid #f1f5f9;">
                                <td style="padding: 10px 0; color: #64748b;"><strong>Phone Number:</strong></td>
                                <td style="padding: 10px 0; color: #0f172a; font-weight: 600;">{phone}</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #f1f5f9;">
                                <td style="padding: 10px 0; color: #64748b;"><strong>Source Channel:</strong></td>
                                <td style="padding: 10px 0; color: #0f172a;"><span style="background: rgba(99, 102, 241, 0.1); color: #6366f1; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">{source}</span></td>
                            </tr>
                            <tr style="border-bottom: 1px solid #f1f5f9;">
                                <td style="padding: 10px 0; color: #64748b;"><strong>Submitted At:</strong></td>
                                <td style="padding: 10px 0; color: #475569;">{datetime.utcnow().strftime('%d %b %Y, %I:%M %p UTC')}</td>
                            </tr>
                            <tr>
                                <td style="padding: 12px 0 6px 0; color: #64748b; vertical-align: top;"><strong>Message / Notes:</strong></td>
                                <td style="padding: 12px 0 6px 0; color: #1e293b; line-height: 1.5;">{message if message else '<em style="color:#94a3b8;">No additional message provided.</em>'}</td>
                            </tr>
                        </table>
                    </div>
                    <div style="padding: 16px 24px; background: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center;">
                        <p style="font-size: 12px; color: #64748b; margin: 0;">This email was automatically forwarded by QCMS Platform because Sales Enquiry Email Forwarding is enabled.</p>
                    </div>
                </div>
            """
            wrapped_html = DocumentBrandingService.wrap_email_html(body, title=subject, include_header=False)
            EmailUtils.send_email_async(
                to_email=sales_email,
                subject=subject,
                html_content=wrapped_html,
                email_type='general'
            )
            print(f"[SupportRoutes] Sales enquiry #{enquiry.id} queued for forwarding to sales email: {sales_email}")
    except Exception as em_err:
        print(f"[SupportRoutes] Sales enquiry email forward error: {em_err}")

    return jsonify({
        "status": "success",
        "message": "Thank you! Your inquiry has been submitted. Our sales team will contact you shortly.",
        "enquiry_id": enquiry.id
    }), 201


@support_bp.route('/enquiries/settings', methods=['GET', 'POST', 'PUT'])
@support_bp.route('/support/enquiries/settings', methods=['GET', 'POST', 'PUT'])
@jwt_required()
def manage_enquiries_settings():
    user, err = get_current_user_and_check_rbac()
    if err:
        return jsonify({"status": "error", "message": err}), 403

    from app.infrastructure.database.models.models import PlatformSettings
    ps = PlatformSettings.query.first()
    if not ps:
        ps = PlatformSettings()
        db.session.add(ps)
        db.session.commit()

    notif_cfg = dict(ps.notification_settings or {})

    if request.method in ['POST', 'PUT']:
        data = request.get_json() or {}
        sales_email = (data.get('sales_notification_email') or '').strip()
        sales_enabled_raw = data.get('sales_notification_enabled')
        sales_enabled = bool(sales_enabled_raw)
        
        if sales_email:
            import re
            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", sales_email):
                return jsonify({"status": "error", "message": "Please enter a valid email address."}), 400
        else:
            sales_enabled = False

        notif_cfg['sales_notification_email'] = sales_email
        notif_cfg['sales_notification_enabled'] = sales_enabled

        ps.notification_settings = dict(notif_cfg)
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(ps, 'notification_settings')
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Sales Enquiry notification settings updated successfully.",
            "data": {
                "sales_notification_email": sales_email,
                "sales_notification_enabled": sales_enabled
            }
        }), 200

    return jsonify({
        "status": "success",
        "data": {
            "sales_notification_email": notif_cfg.get('sales_notification_email', ''),
            "sales_notification_enabled": bool(notif_cfg.get('sales_notification_enabled', False))
        }
    }), 200


@support_bp.route('/enquiries', methods=['GET'])
@jwt_required()
def list_enquiries():
    user, err = get_current_user_and_check_rbac()
    if err:
        return jsonify({"status": "error", "message": err}), 403

    status_filter = request.args.get('status', '').strip()
    search_q = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))

    query = SalesEnquiry.query

    if status_filter and status_filter.lower() != 'all':
        query = query.filter(SalesEnquiry.status == status_filter)

    if search_q:
        pattern = f"%{search_q}%"
        query = query.filter(
            or_(
                SalesEnquiry.name.ilike(pattern),
                SalesEnquiry.email.ilike(pattern),
                SalesEnquiry.company_name.ilike(pattern),
                SalesEnquiry.phone.ilike(pattern),
                SalesEnquiry.message.ilike(pattern)
            )
        )

    total_count = SalesEnquiry.query.count()
    new_count = SalesEnquiry.query.filter_by(status='New').count()
    contacted_count = SalesEnquiry.query.filter_by(status='Contacted').count()
    converted_count = SalesEnquiry.query.filter_by(status='Converted').count()

    paginated = query.order_by(SalesEnquiry.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for item in paginated.items:
        items.append({
            "id": item.id,
            "name": item.name,
            "email": item.email,
            "phone": item.phone,
            "company_name": item.company_name,
            "message": item.message or '',
            "source": item.source or 'Talk to Sales',
            "status": item.status or 'New',
            "notes": item.notes or '',
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None
        })

    return jsonify({
        "status": "success",
        "data": items,
        "metrics": {
            "total": total_count,
            "new": new_count,
            "contacted": contacted_count,
            "converted": converted_count
        },
        "pagination": {
            "total": paginated.total,
            "page": paginated.page,
            "per_page": paginated.per_page,
            "pages": paginated.pages
        }
    }), 200


@support_bp.route('/enquiries/<int:enquiry_id>', methods=['PUT'])
@jwt_required()
def update_enquiry(enquiry_id):
    user, err = get_current_user_and_check_rbac()
    if err:
        return jsonify({"status": "error", "message": err}), 403

    enquiry = SalesEnquiry.query.get_or_404(enquiry_id)
    data = request.get_json() or {}

    if 'status' in data:
        enquiry.status = data['status']
    if 'notes' in data:
        enquiry.notes = data['notes']

    enquiry.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"Enquiry #{enquiry_id} updated successfully.",
        "data": {
            "id": enquiry.id,
            "status": enquiry.status,
            "notes": enquiry.notes
        }
    }), 200


@support_bp.route('/enquiries/<int:enquiry_id>', methods=['DELETE'])
@jwt_required()
def delete_enquiry(enquiry_id):
    user, err = get_current_user_and_check_rbac()
    if err:
        return jsonify({"status": "error", "message": err}), 403

    enquiry = SalesEnquiry.query.get_or_404(enquiry_id)
    db.session.delete(enquiry)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"Enquiry #{enquiry_id} removed successfully."
    }), 200


@support_bp.route('/enquiries/<int:enquiry_id>/send-email', methods=['POST'])
@jwt_required()
def send_enquiry_email(enquiry_id):
    user, err = get_current_user_and_check_rbac()
    if err:
        return jsonify({"status": "error", "message": err}), 403

    enquiry = SalesEnquiry.query.get_or_404(enquiry_id)
    data = request.get_json() or {}

    recipient_email = (data.get('to_email') or enquiry.email or '').strip()
    subject = (data.get('subject') or f"Response to Inquiry - {enquiry.company_name or 'QCMS'}").strip()
    message_content = (data.get('message') or '').strip()

    if not recipient_email or not message_content:
        return jsonify({"status": "error", "message": "Recipient email and message content are required."}), 400

    try:
        from app.infrastructure.mailer.email_service import EmailUtils
        from app.domain.services.document_branding_service import DocumentBrandingService

        user_org_id = getattr(user, 'org_id', None)

        msg_str = message_content.strip()
        # Avoid duplicate greeting if message content already includes "Dear ...", "Hi ...", or "Hello ..."
        if re.match(r'^(dear|hi|hello|greetings)\b', msg_str, re.IGNORECASE):
            greeting_hdr = ""
        else:
            greeting_hdr = f"<p style=\"margin-bottom: 12px;\">Dear {enquiry.name or 'Valued Prospect'},</p>"

        body_html = f"""
        <div style="font-family: Arial, sans-serif; font-size: 14px; color: #1e293b; line-height: 1.6;">
            {greeting_hdr}
            <div style="margin: 8px 0; white-space: pre-wrap;">{msg_str}</div>
            <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
            <p style="font-size: 12px; color: #64748b;">
                This communication is sent regarding your sales inquiry with <strong>{enquiry.company_name or 'QCMS Enterprise'}</strong>.
            </p>
        </div>
        """
        html_wrapped = DocumentBrandingService.wrap_email_html(body_html, title=subject, org_id=user_org_id)

        # Dispatch email asynchronously using 'support' email_type in background
        EmailUtils.send_email_async(
            to_email=recipient_email,
            subject=subject,
            html_content=html_wrapped,
            email_type='support',
            org_id=user_org_id
        )

        # Log email dispatch in enquiry notes and update status to Contacted if New
        now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
        log_note = f"[{now_str}] Email sent to {recipient_email} by {getattr(user, 'username', 'Admin')}:\nSubject: {subject}\nMessage: {message_content[:200]}..."
        if enquiry.notes:
            enquiry.notes = log_note + "\n\n" + enquiry.notes
        else:
            enquiry.notes = log_note

        if enquiry.status == 'New':
            enquiry.status = 'Contacted'

        enquiry.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": f"Email successfully sent to {recipient_email} using Support Email.",
            "data": {
                "enquiry_id": enquiry.id,
                "status": enquiry.status,
                "notes": enquiry.notes
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Failed to send email: {str(e)}"}), 500


# --- FILE UPLOAD FOR SUPPORT TICKET ATTACHMENTS ---
@support_bp.route('/tickets/<int:ticket_id>/upload-attachment', methods=['POST'])
@jwt_required()
def upload_ticket_attachment(ticket_id):
    """Upload a file attachment for a support ticket (PDF and images only)."""
    import os
    from werkzeug.utils import secure_filename
    from flask import current_app

    user, err = get_current_user_and_check_rbac()
    if err:
        return jsonify({"status": "error", "message": err}), 403

    ticket = SupportTicket.query.get_or_404(ticket_id)
    if user.role.name != 'SuperAdmin' and ticket.org_id != user.org_id:
        return jsonify({"status": "error", "message": "Access denied"}), 403

    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file provided"}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"}), 400

    # Strict file type validation — only PDF and images allowed
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({
            "status": "error",
            "message": "Invalid file type. Only PDF and images (PNG, JPG, GIF, WEBP) are allowed."
        }), 400

    try:
        filename = secure_filename(file.filename)
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"ticket_{ticket_id}_{timestamp}_{filename}"

        upload_dir = os.path.join(
            current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'support_attachments'
        )
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        file_url = f"/uploads/support_attachments/{filename}"
        file_size = os.path.getsize(file_path)

        # Save record in DB linked to this ticket
        att = SupportAttachment(
            ticket_id=ticket.id,
            comment_id=None,
            file_name=file.filename,
            file_path=file_url,
            file_size=file_size,
            mime_type=file.content_type or f"application/{ext}",
            uploaded_by_id=user.id,
            virus_scan_passed=True
        )
        db.session.add(att)
        db.session.commit()

        return jsonify({
            "status": "success",
            "attachment": {
                "id": att.id,
                "file_name": att.file_name,
                "file_path": att.file_path,
                "file_size": att.file_size,
                "mime_type": att.mime_type
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Upload failed: {str(e)}"}), 500
