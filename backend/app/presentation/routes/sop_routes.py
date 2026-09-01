from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.infrastructure.database.models.models import (
    db, User, Department, Project, ProjectMember, AuditLog, SOP, SOPStep, SOPApproval, SOPVersion, SOPTraining, SOPComment,
    SOPAcknowledgement, SOPAssessment, SOPAssessmentQuestion, SOPAssessmentResult, SOPAuditReport, SOPArchive, SOPNotification,
    SOPCategory, SOPType
)
from app.presentation.middleware.middleware import role_required
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
import json
import os
import io
from app.presentation.routes.error_helpers import internal_server_error

sop_bp = Blueprint('sops', __name__)

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None

def parse_int(val):
    if val is None or val == "" or val == "None" or str(val).strip() == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None

def scope_sop_query(query, user):
    role_name = user.role.name if user.role else 'Team Member'
    
    if role_name != 'SuperAdmin':
        query = query.filter(SOP.org_id == user.org_id)
        
    if role_name in ('SuperAdmin', 'Admin', 'CEO'):
        return query
        
    from app.infrastructure.database.models.models import Project, ProjectMember
    active_project_ids_query = db.session.query(Project.id).filter(Project.status != 'Closed')
    
    training_sop_ids = db.session.query(SOPTraining.sop_id).filter(
        SOPTraining.user_id == user.id
    )
    
    member_projects_subquery = db.session.query(Project.id).filter(
        db.or_(
            Project.creator_id == user.id,
            Project.team_leader_id == user.id,
            Project.facilitator_id == user.id,
            Project.reviewer_id == user.id,
            Project.id.in_(db.session.query(ProjectMember.project_id).filter_by(user_id=user.id))
        )
    )
    
    published_visibility = db.and_(
        SOP.status == 'Active',
        db.or_(
            # Case 1: SOP is linked to a project -> user must be a member of that project
            db.and_(
                SOP.project_id != None,
                SOP.project_id.in_(member_projects_subquery)
            ),
            # Case 2: SOP is standalone but linked to a department -> user must be in that department
            db.and_(
                SOP.project_id == None,
                SOP.department_id != None,
                SOP.department_id == user.department_id
            ),
            # Case 3: SOP is completely global (no project, no department) -> visible to everyone
            db.and_(
                SOP.project_id == None,
                SOP.department_id == None
            )
        )
    )
    
    visibility_cond = db.or_(
        SOP.author_id == user.id,
        SOP.owner_id == user.id,
        SOP.reviewer_id == user.id,
        SOP.approver_id == user.id,
        SOP.id.in_(training_sop_ids),
        db.and_(
            SOP.project_id != None,
            SOP.project_id.in_(member_projects_subquery)
        ),
        db.and_(
            db.or_(
                SOP.project_id == None,
                SOP.project_id.notin_(active_project_ids_query)
            ),
            published_visibility
        )
    )
    
    return query.filter(visibility_cond)


# ============================
# SOP CRUD & MASTER MANAGEMENT
# ============================

@sop_bp.route('', methods=['POST'])
@jwt_required()
@role_required(['Reviewer', 'Admin', 'SuperAdmin'])
def create_sop():
    """Create a new SOP (Draft) with dynamic steps."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    data = request.get_json()
    title = data.get('title')
    category = data.get('category')
    
    if not title or not category:
        return jsonify({"msg": "Title and Category are required"}), 400
        
    # Generate unique SOP ID: SOP-YYYY-XXXX (last 4 of timestamp + random)
    import random
    import string
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    sop_uid = f"SOP-{datetime.now(timezone.utc).replace(tzinfo=None).year}-{random_suffix}"
    
    try:
        # Create SOP Master
        sop = SOP(
            sop_uid=sop_uid,
            org_id=user.org_id,
            title=title,
            category=category,
            department_id=parse_int(data.get('department_id')) or user.department_id,
            process_name=data.get('process_name'),
            sop_type=data.get('sop_type', 'Operational'),
            description=data.get('description'),
            purpose=data.get('purpose'),
            scope=data.get('scope'),
            applicability=data.get('applicability'),
            responsibilities=data.get('responsibilities'),
            owner_id=parse_int(data.get('owner_id')) or user_id,
            author_id=user_id,
            reviewer_id=parse_int(data.get('reviewer_id')),
            approver_id=parse_int(data.get('approver_id')),
            effective_date=parse_date(data.get('effective_date')),
            review_date=parse_date(data.get('review_date')),
            expiry_date=parse_date(data.get('expiry_date')),
            status='Active',
            version=1,
            project_id=parse_int(data.get('project_id')),
            attachments=data.get('attachments', []),
            sop_document_path=data.get('sop_document_path'),
            preventive_actions=data.get('preventive_actions'),
            lessons_learned=data.get('lessons_learned'),
            training_records=data.get('training_records')
        )
        
        db.session.add(sop)
        db.session.flush() # Populate sop.id
        
        # Add dynamic steps
        steps = data.get('steps', [])
        for i, step in enumerate(steps):
            sop_step = SOPStep(
                sop_id=sop.id,
                step_number=step.get('step_number') or (i + 1),
                step_title=step.get('step_title', f"Step {i+1}"),
                instructions=step.get('instructions', ''),
                image_path=step.get('image_path'),
                video_path=step.get('video_path'),
                safety_notes=step.get('safety_notes'),
                quality_checkpoints=step.get('quality_checkpoints')
            )
            db.session.add(sop_step)
            
        # Log approval history (Draft creation)
        approval = SOPApproval(
            sop_id=sop.id,
            user_id=user_id,
            role=user.role.name,
            action='Draft Created',
            comments='Initial draft creation',
            signature=f"Signed by {user.full_name or user.username} at {datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}"
        )
        db.session.add(approval)
        
        # Audit Log
        audit = AuditLog(
            org_id=user.org_id,
            user_id=user_id,
            project_id=sop.project_id,
            action='SOP_CREATED',
            target_table='sops',
            target_id=sop.id,
            details={"title": sop.title, "sop_uid": sop_uid, "role": user.role.name}
        )
        db.session.add(audit)
        
        db.session.commit()

        # If this SOP is linked to a project in 'Impact Approved' status,
        # advance project to 'SOP Created' so the Facilitator can proceed to closure
        if sop.project_id:
            from app.infrastructure.database.models.models import Project
            linked_project = db.session.get(Project, sop.project_id)
            if linked_project and linked_project.status == 'Impact Approved':
                linked_project.status = 'SOP Created'
                db.session.commit()

        return jsonify({"msg": "SOP created successfully", "id": sop.id, "sop_uid": sop_uid}), 201
        
    except Exception as e:
        db.session.rollback()
        return internal_server_error(e, "Failed to create SOP.")

@sop_bp.route('', methods=['GET'])
@jwt_required()
def search_sops():
    """Advanced search, sorting, and filtering of SOPs."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    
    # Query parameters
    q = request.args.get('q', '')
    status = request.args.get('status')
    category = request.args.get('category')
    dept_id = request.args.get('department_id')
    sop_type = request.args.get('sop_type')
    project_id = request.args.get('project_id')
    
    if user.role.name == 'SuperAdmin':
        query = SOP.query
    else:
        query = SOP.query.filter_by(org_id=user.org_id)
    query = scope_sop_query(query, user)
    
    if project_id:
        query = query.filter_by(project_id=int(project_id))
    
    if q:
        search_filter = f"%{q}%"
        query = query.filter(
            db.or_(
                SOP.title.ilike(search_filter),
                SOP.sop_uid.ilike(search_filter),
                SOP.process_name.ilike(search_filter),
                SOP.description.ilike(search_filter)
            )
        )
        
    if status:
        query = query.filter_by(status=status)
    if category:
        query = query.filter_by(category=category)
    if dept_id:
        query = query.filter_by(department_id=int(dept_id))
    if sop_type:
        query = query.filter_by(sop_type=sop_type)
        
    sops = query.order_by(SOP.created_at.desc()).all()
    
    results = []
    for s in sops:
        results.append({
            "id": s.id,
            "sop_uid": s.sop_uid,
            "title": s.title,
            "category": s.category,
            "department_name": s.department.name if s.department else "Organization",
            "process_name": s.process_name or (s.project.title if s.project else None) or "Operational",
            "project_name": s.project.title if s.project else (s.process_name or None),
            "sop_type": s.sop_type,
            "status": s.status,
            "version": s.version,
            "author_name": s.author.full_name or s.author.username if s.author else "System",
            "effective_date": s.effective_date.isoformat() if s.effective_date else None,
            "created_at": s.created_at.isoformat() + "Z"
        })
        
    return jsonify(results), 200

# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: get_sop_details (Lines 284-426)
# Reason: Unused single SOP detail fetch.
# ==============================================================================
# @sop_bp.route('/<int:sop_id>', methods=['GET'])
# @jwt_required()
# def get_sop_details(sop_id):
#     """Retrieve full details of a specific SOP."""
#     user_id = get_jwt_identity()
#     user = db.session.get(User, user_id)

#     if user.role.name == 'SuperAdmin':
#         query = SOP.query.filter_by(id=sop_id)
#     else:
#         query = SOP.query.filter_by(id=sop_id, org_id=user.org_id)
#     sop = scope_sop_query(query, user).first_or_404()

#     # Format steps
#     steps_list = [{
#         "id": step.id,
#         "step_number": step.step_number,
#         "step_title": step.step_title,
#         "instructions": step.instructions,
#         "image_path": step.image_path,
#         "video_path": step.video_path,
#         "safety_notes": step.safety_notes,
#         "quality_checkpoints": step.quality_checkpoints
#     } for step in sorted(sop.steps, key=lambda x: x.step_number)]

#     # Format approvals
#     approvals_list = [{
#         "id": app.id,
#         "user_name": app.user.full_name or app.user.username if app.user else "System",
#         "role": app.role,
#         "action": app.action,
#         "comments": app.comments,
#         "signature": app.signature,
#         "created_at": app.created_at.isoformat() + "Z"
#     } for app in sorted(sop.approvals, key=lambda x: x.created_at, reverse=True)]

#     # Format version list
#     versions_list = [{
#         "id": v.id,
#         "version_number": v.version_number,
#         "changes_made": v.changes_made,
#         "changed_by_name": v.changed_by.full_name or v.changed_by.username if v.changed_by else "System",
#         "changed_date": v.changed_date.isoformat() + "Z",
#         "approval_date": v.approval_date.isoformat() + "Z" if v.approval_date else None
#     } for v in sorted(sop.versions, key=lambda x: x.version_number, reverse=True)]

#     # Check if this user is assigned training for this SOP
#     training_record = SOPTraining.query.filter_by(sop_id=sop.id, user_id=user_id).first()
#     my_training = {
#         "assigned": training_record is not None,
#         "id": training_record.id if training_record else None,
#         "read_status": training_record.read_status if training_record else False,
#         "acknowledgement_status": training_record.acknowledgement_status if training_record else False,
#         "training_completion_status": training_record.training_completion_status if training_record else False,
#         "assessment_score": training_record.assessment_score if training_record else None,
#         "completed_at": training_record.completed_at.isoformat() + "Z" if training_record and training_record.completed_at else None,
#         "status": training_record.status if training_record else "Not Started"
#     } if training_record else None

#     # Format training records for managers/owners
#     trainings_list = []
#     if user.role.name in ('Admin', 'Facilitator', 'Team Leader', 'Team Member', 'SuperAdmin', 'Reviewer'):
#         for t in sorted(sop.trainings, key=lambda x: x.assigned_date, reverse=True):
#             user_projects = Project.query.filter(
#                 (Project.creator_id == t.user_id) |
#                 (Project.team_leader_id == t.user_id) |
#                 (Project.facilitator_id == t.user_id) |
#                 (Project.reviewer_id == t.user_id) |
#                 Project.members.any(id=t.user_id)
#             ).all()
#             project_ids = [p.id for p in user_projects]

#             trainings_list.append({
#                 "id": t.id,
#                 "user_id": t.user_id,
#                 "employee_name": t.user.full_name or t.user.username,
#                 "employee_id": t.user_id,
#                 "department": t.user.dept.name if t.user.dept else "N/A",
#                 "department_id": t.user.department_id,
#                 "role_id": t.user.role_id,
#                 "project_ids": project_ids,
#                 "assigned_date": t.assigned_date.isoformat() + "Z" if t.assigned_date else None,
#                 "completed_at": t.completed_at.isoformat() + "Z" if t.completed_at else None,
#                 "read_status": t.read_status,
#                 "acknowledgement_status": t.acknowledgement_status,
#                 "training_completion_status": t.training_completion_status,
#                 "assessment_score": t.assessment_score,
#                 "status": t.status
#             })

#     # Format comments list
#     comments_list = [{
#         "id": c.id,
#         "user_name": c.user.full_name or c.user.username,
#         "role": c.role,
#         "comment_type": c.comment_type,
#         "content": c.content,
#         "created_at": c.created_at.isoformat() + "Z"
#     } for c in sorted(sop.comments_list, key=lambda x: x.created_at, reverse=True)]

#     return jsonify({
#         "id": sop.id,
#         "sop_uid": sop.sop_uid,
#         "title": sop.title,
#         "category": sop.category,
#         "department_id": sop.department_id,
#         "department_name": sop.department.name if sop.department else "Organization",
#         "process_name": sop.process_name or (sop.project.title if sop.project else None) or "Operational",
#         "project_name": sop.project.title if sop.project else (sop.process_name or None),
#         "sop_type": sop.sop_type,
#         "description": sop.description,
#         "purpose": sop.purpose,
#         "scope": sop.scope,
#         "applicability": sop.applicability,
#         "responsibilities": sop.responsibilities,
#         "status": sop.status,
#         "version": sop.version,
#         "project_id": sop.project_id,
#         "project_title": sop.project.title if sop.project else (sop.process_name or None),
#         "project_uid": sop.project.project_uid if sop.project else None,
#         "effective_date": sop.effective_date.isoformat() if sop.effective_date else None,
#         "review_date": sop.review_date.isoformat() if sop.review_date else None,
#         "expiry_date": sop.expiry_date.isoformat() if sop.expiry_date else None,
#         "author_id": sop.author_id,
#         "author_name": sop.author.full_name or sop.author.username if sop.author else "System",
#         "owner_id": sop.owner_id,
#         "owner_name": sop.owner.full_name or sop.owner.username if sop.owner else "System",
#         "reviewer_id": sop.reviewer_id,
#         "reviewer_name": sop.reviewer.full_name or sop.reviewer.username if sop.reviewer else None,
#         "approver_id": sop.approver_id,
#         "approver_name": sop.approver.full_name or sop.approver.username if sop.approver else None,
#         "sop_document_path": sop.sop_document_path,
#         "preventive_actions": sop.preventive_actions,
#         "lessons_learned": sop.lessons_learned,
#         "training_records_notes": sop.training_records,
#         "steps": steps_list,
#         "approvals": approvals_list,
#         "versions": versions_list,
#         "my_training": my_training,
#         "trainings": trainings_list,
#         "comments": comments_list,
#         "attachments": sop.attachments or []
#     }), 200
# [END DEAD CODE: get_sop_details]


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: export_sop_pdf (Lines 428-464)
# Reason: Unused SOP standalone PDF export route.
# ==============================================================================
# @sop_bp.route('/<int:sop_id>/pdf', methods=['GET'])
# @jwt_required()
# def export_sop_pdf(sop_id):
#     """Generate and download a PDF representation of the SOP."""
#     from flask import send_file
#     import io
#     from app.utils.report_gen import generate_sop_pdf_report

#     user_id = get_jwt_identity()
#     user = db.session.get(User, user_id)
#     if not user:
#         return jsonify({"msg": "User not found"}), 404

#     query = SOP.query.filter_by(id=sop_id, org_id=user.org_id)
#     sop = scope_sop_query(query, user).first_or_404()

#     # Log Audit Log
#     db.session.add(AuditLog(
#         org_id=user.org_id,
#         user_id=user.id,
#         action="EXPORT_SOP_PDF",
#         target_table="sops",
#         target_id=sop_id,
#         details={"sop_uid": sop.sop_uid, "ip": request.remote_addr}
#     ))
#     db.session.commit()

#     pdf_data = generate_sop_pdf_report(sop)
#     if not pdf_data:
#         return jsonify({"msg": "Failed to generate SOP PDF"}), 400

#     return send_file(
#         io.BytesIO(pdf_data),
#         mimetype='application/pdf',
#         as_attachment=True,
#         download_name=f"{sop.sop_uid}_SOP.pdf"
#     )
# [END DEAD CODE: export_sop_pdf]


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: update_sop (Lines 466-633)
# Reason: Unused direct SOP editor route.
# ==============================================================================
# @sop_bp.route('/<int:sop_id>', methods=['PUT'])
# @jwt_required()
# @role_required(['Reviewer', 'Admin', 'SuperAdmin'])
# def update_sop(sop_id):
#     """Update an SOP. Handles automatic version archiving if the SOP is already published/Active."""
#     user_id = get_jwt_identity()
#     user = db.session.get(User, user_id)

#     sop = SOP.query.filter_by(id=sop_id, org_id=user.org_id).first_or_404()

#     # Author/Owner checks if role is Reviewer
#     if user.role.name == 'Reviewer':
#         is_authorized = (
#             sop.author_id == user.id or
#             sop.owner_id == user.id or
#             (sop.project and sop.project.reviewer_id == user.id)
#         )
#         if not is_authorized:
#             return jsonify({"msg": "Access denied. You are not authorized to edit this SOP."}), 403

#     data = request.get_json()

#     try:
#         # Check if SOP is Active. If so, a revision creates a new version archiving the current state.
#         is_revising_active = (sop.status == 'Active')

#         changes_description = data.get('changes_made', 'Minor updates')

#         if is_revising_active:
#             # 1. Gather all existing SOP steps before modifying
#             existing_steps = [{
#                 "step_number": s.step_number,
#                 "step_title": s.step_title,
#                 "instructions": s.instructions,
#                 "image_path": s.image_path,
#                 "video_path": s.video_path,
#                 "safety_notes": s.safety_notes,
#                 "quality_checkpoints": s.quality_checkpoints
#             } for s in sop.steps]

#             # 2. Archive current version to SOPVersion
#             snapshot = {
#                 "title": sop.title,
#                 "category": sop.category,
#                 "process_name": sop.process_name,
#                 "sop_type": sop.sop_type,
#                 "description": sop.description,
#                 "purpose": sop.purpose,
#                 "scope": sop.scope,
#                 "applicability": sop.applicability,
#                 "responsibilities": sop.responsibilities,
#                 "effective_date": sop.effective_date.isoformat() if sop.effective_date else None,
#                 "review_date": sop.review_date.isoformat() if sop.review_date else None,
#                 "expiry_date": sop.expiry_date.isoformat() if sop.expiry_date else None,
#                 "owner_id": sop.owner_id,
#                 "reviewer_id": sop.reviewer_id,
#                 "approver_id": sop.approver_id,
#                 "steps": existing_steps,
#                 "attachments": sop.attachments
#             }

#             archive_version = SOPVersion(
#                 sop_id=sop.id,
#                 version_number=sop.version,
#                 changes_made=changes_description,
#                 changed_by_id=user_id,
#                 approval_date=datetime.now(timezone.utc).replace(tzinfo=None),
#                 sop_data=snapshot
#             )
#             db.session.add(archive_version)

#             # 3. Increment Version, return back to Under Review state
#             sop.version += 1
#             sop.status = 'Active'

#         # Update Master SOP fields only if present in payload keys
#         if 'title' in data:
#             sop.title = data['title']
#         if 'category' in data:
#             sop.category = data['category']
#         if 'department_id' in data:
#             sop.department_id = parse_int(data['department_id']) or sop.department_id
#         if 'process_name' in data:
#             sop.process_name = data['process_name']
#         if 'sop_type' in data:
#             sop.sop_type = data['sop_type']
#         if 'description' in data:
#             sop.description = data['description']
#         if 'purpose' in data:
#             sop.purpose = data['purpose']
#         if 'scope' in data:
#             sop.scope = data['scope']
#         if 'applicability' in data:
#             sop.applicability = data['applicability']
#         if 'responsibilities' in data:
#             sop.responsibilities = data['responsibilities']
#         if 'owner_id' in data:
#             sop.owner_id = parse_int(data['owner_id']) or sop.owner_id
#         if 'reviewer_id' in data:
#             sop.reviewer_id = parse_int(data['reviewer_id'])
#         if 'approver_id' in data:
#             sop.approver_id = parse_int(data['approver_id'])
#         if 'effective_date' in data:
#             sop.effective_date = parse_date(data['effective_date']) or sop.effective_date
#         if 'review_date' in data:
#             sop.review_date = parse_date(data['review_date']) or sop.review_date
#         if 'expiry_date' in data:
#             sop.expiry_date = parse_date(data['expiry_date']) or sop.expiry_date
#         if 'attachments' in data:
#             sop.attachments = data['attachments']
#         if 'sop_document_path' in data:
#             sop.sop_document_path = data['sop_document_path']
#         if 'preventive_actions' in data:
#             sop.preventive_actions = data['preventive_actions']
#         if 'lessons_learned' in data:
#             sop.lessons_learned = data['lessons_learned']
#         if 'training_records' in data:
#             sop.training_records = data['training_records']
#         if 'project_id' in data:
#             sop.project_id = parse_int(data['project_id'])

#         # Replace steps if provided in request
#         if 'steps' in data:
#             # Delete old steps
#             SOPStep.query.filter_by(sop_id=sop.id).delete()

#             # Add updated steps
#             for i, step in enumerate(data['steps']):
#                 sop_step = SOPStep(
#                     sop_id=sop.id,
#                     step_number=step.get('step_number') or (i + 1),
#                     step_title=step.get('step_title', f"Step {i+1}"),
#                     instructions=step.get('instructions', ''),
#                     image_path=step.get('image_path'),
#                     video_path=step.get('video_path'),
#                     safety_notes=step.get('safety_notes'),
#                     quality_checkpoints=step.get('quality_checkpoints')
#                 )
#                 db.session.add(sop_step)

#         # Approval flow record
#         approval = SOPApproval(
#             sop_id=sop.id,
#             user_id=user_id,
#             role=user.role.name,
#             action='Revised' if is_revising_active else 'Updated',
#             comments=changes_description,
#             signature=f"Signed by {user.full_name or user.username} at {datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}"
#         )
#         db.session.add(approval)

#         # Audit Log
#         audit = AuditLog(
#             org_id=user.org_id,
#             user_id=user_id,
#             action='SOP_UPDATED',
#             target_table='sops',
#             target_id=sop.id,
#             details={"title": sop.title, "version": sop.version, "role": user.role.name}
#         )
#         db.session.add(audit)

#         db.session.commit()
#         return jsonify({"msg": "SOP updated successfully", "version": sop.version, "status": sop.status}), 200

#     except Exception as e:
#         db.session.rollback()
#         return internal_server_error(e, "Failed to update SOP.")
# [END DEAD CODE: update_sop]


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: rename_sop (Lines 635-681)
# Reason: SOP rename route.
# ==============================================================================
# @sop_bp.route('/<int:sop_id>/rename', methods=['PATCH'])
# @jwt_required()
# @role_required(['Reviewer', 'Admin', 'SuperAdmin'])
# def rename_sop(sop_id):
#     """Rename an SOP's title directly without creating a new revision version."""
#     user_id = get_jwt_identity()
#     user = db.session.get(User, user_id)
#     if not user:
#         return jsonify({"msg": "User not found"}), 404

#     sop = SOP.query.filter_by(id=sop_id, org_id=user.org_id).first_or_404()

#     # Author/Owner/Reviewer checks
#     if user.role.name == 'Reviewer':
#         is_authorized = (
#             sop.author_id == user.id or
#             sop.owner_id == user.id or
#             (sop.project and sop.project.reviewer_id == user.id)
#         )
#         if not is_authorized:
#             return jsonify({"msg": "Access denied. You are not authorized to rename this SOP."}), 403

#     data = request.get_json()
#     new_title = data.get('title')
#     if not new_title or not new_title.strip():
#         return jsonify({"msg": "Title is required"}), 400

#     old_title = sop.title
#     sop.title = new_title.strip()

#     # Audit Log
#     audit = AuditLog(
#         org_id=user.org_id,
#         user_id=user_id,
#         action='SOP_RENAMED',
#         target_table='sops',
#         target_id=sop.id,
#         details={"old_title": old_title, "new_title": sop.title, "role": user.role.name}
#     )
#     db.session.add(audit)

#     try:
#         db.session.commit()
#         return jsonify({"msg": "SOP renamed successfully", "id": sop.id, "title": sop.title}), 200
#     except Exception as e:
#         db.session.rollback()
#         return internal_server_error(e, "Failed to rename SOP.")
# [END DEAD CODE: rename_sop]


# ============================
# SOP APPROVAL WORKFLOW
# ============================

@sop_bp.route('/<int:sop_id>/approve', methods=['POST'])
@jwt_required()
@role_required(['Facilitator', 'Reviewer', 'Admin', 'CEO', 'SuperAdmin'])
def approve_sop(sop_id):
    """Execute approval workflow operations (Submit for Review, Approve, Reject, Send Back)."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    
    sop = SOP.query.filter_by(id=sop_id, org_id=user.org_id).first_or_404()
    data = request.get_json()
    action = data.get('action') # Submit, Approve, Reject, Send Back
    comments = data.get('comments', '')
    
    if not action:
        return jsonify({"msg": "Action is required"}), 400
        
    try:
        old_status = sop.status
        new_status = old_status
        
        if action == 'Submit':
            new_status = 'Under Review'
        elif action == 'Approve':
            # Flow: Draft -> Under Review -> Approved -> Active
            if old_status == 'Under Review':
                if user.id == sop.reviewer_id or user.role.name in ['Admin', 'Reviewer', 'SuperAdmin']:
                    new_status = 'Approved'
                else:
                    return jsonify({"msg": "Only the assigned reviewer can execute reviewer approval"}), 403
            elif old_status == 'Approved' or old_status == 'Under Review':
                if user.id == sop.approver_id or user.role.name in ['Admin', 'CEO', 'SuperAdmin']:
                    new_status = 'Active'
                else:
                    return jsonify({"msg": "Only the assigned approver/management can publish SOP as Active"}), 403
        elif action == 'Reject':
            new_status = 'Obsolete'
        elif action == 'Send Back':

            new_status = 'Draft'
            
        sop.status = new_status
        
        # Log approval history
        approval = SOPApproval(
            sop_id=sop.id,
            user_id=user_id,
            role=user.role.name,
            action=action,
            comments=comments,
            signature=f"Electronically signed by {user.full_name or user.username} ({user.role.name}) at {datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}"
        )
        db.session.add(approval)
        
        # Audit log
        audit = AuditLog(
            org_id=user.org_id,
            user_id=user_id,
            action=f'SOP_{action.upper()}',
            target_table='sops',
            target_id=sop.id,
            details={"from": old_status, "to": new_status, "comments": comments}
        )
        db.session.add(audit)
        
        db.session.commit()
        return jsonify({"msg": f"SOP {action} action completed successfully", "status": new_status}), 200
        
    except Exception as e:
        db.session.rollback()
        return internal_server_error(e, "Approval submission failed.")

# ============================
# SOP VERSIONING AND ROLLBACKS
# ============================

@sop_bp.route('/<int:sop_id>/versions/compare', methods=['POST'])
@jwt_required()
def compare_versions(sop_id):
    """Compare the current details with an archived version or compare two archived versions."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    
    data = request.get_json()
    v1_num = data.get('v1')
    v2_num = data.get('v2')
    
    if not v1_num:
        return jsonify({"msg": "v1 version number is required"}), 400
        
    sop = SOP.query.filter_by(id=sop_id, org_id=user.org_id).first_or_404()
    
    # Get v1 snapshot data
    v1 = SOPVersion.query.filter_by(sop_id=sop_id, version_number=v1_num).first()
    if not v1:
        return jsonify({"msg": f"Version {v1_num} not found"}), 404
        
    # Get v2 snapshot data
    v2_data = None
    if v2_num:
        v2 = SOPVersion.query.filter_by(sop_id=sop_id, version_number=v2_num).first()
        if not v2:
            return jsonify({"msg": f"Version {v2_num} not found"}), 404
        v2_data = v2.sop_data
    else:
        # Fallback: Compare with the current state on active database
        current_steps = [{
            "step_number": s.step_number,
            "step_title": s.step_title,
            "instructions": s.instructions,
            "image_path": s.image_path,
            "video_path": s.video_path,
            "safety_notes": s.safety_notes,
            "quality_checkpoints": s.quality_checkpoints
        } for s in sop.steps]
        
        v2_data = {
            "title": sop.title,
            "category": sop.category,
            "process_name": sop.process_name,
            "sop_type": sop.sop_type,
            "description": sop.description,
            "purpose": sop.purpose,
            "scope": sop.scope,
            "applicability": sop.applicability,
            "responsibilities": sop.responsibilities,
            "effective_date": sop.effective_date.isoformat() if sop.effective_date else None,
            "review_date": sop.review_date.isoformat() if sop.review_date else None,
            "expiry_date": sop.expiry_date.isoformat() if sop.expiry_date else None,
            "owner_id": sop.owner_id,
            "reviewer_id": sop.reviewer_id,
            "approver_id": sop.approver_id,
            "steps": current_steps,
            "attachments": sop.attachments
        }
        
    return jsonify({
        "v1": v1.sop_data,
        "v2": v2_data
    }), 200

@sop_bp.route('/<int:sop_id>/versions/<int:version_number>/restore', methods=['POST'])
@jwt_required()
@role_required(['Admin', 'SuperAdmin'])
def restore_version(sop_id, version_number):
    """Restore an SOP back to a previous archived snapshot version."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    
    sop = SOP.query.filter_by(id=sop_id, org_id=user.org_id).first_or_404()
    
    # Locate historical record
    archive = SOPVersion.query.filter_by(sop_id=sop_id, version_number=version_number).first_or_404()
    v_data = archive.sop_data
    
    try:
        # Restore fields
        sop.title = v_data.get('title', sop.title)
        sop.category = v_data.get('category', sop.category)
        sop.process_name = v_data.get('process_name', sop.process_name)
        sop.sop_type = v_data.get('sop_type', sop.sop_type)
        sop.description = v_data.get('description', sop.description)
        sop.purpose = v_data.get('purpose', sop.purpose)
        sop.scope = v_data.get('scope', sop.scope)
        sop.applicability = v_data.get('applicability', sop.applicability)
        sop.responsibilities = v_data.get('responsibilities', sop.responsibilities)
        sop.effective_date = parse_date(v_data.get('effective_date'))
        sop.review_date = parse_date(v_data.get('review_date'))
        sop.expiry_date = parse_date(v_data.get('expiry_date'))
        sop.attachments = v_data.get('attachments', [])
        
        # Delete old steps
        SOPStep.query.filter_by(sop_id=sop.id).delete()
        
        # Restore old steps
        for i, step in enumerate(v_data.get('steps', [])):
            sop_step = SOPStep(
                sop_id=sop.id,
                step_number=step.get('step_number') or (i + 1),
                step_title=step.get('step_title', f"Step {i+1}"),
                instructions=step.get('instructions', ''),
                image_path=step.get('image_path'),
                video_path=step.get('video_path'),
                safety_notes=step.get('safety_notes'),
                quality_checkpoints=step.get('quality_checkpoints')
            )
            db.session.add(sop_step)
            
        # Log approval history
        approval = SOPApproval(
            sop_id=sop.id,
            user_id=user_id,
            role=user.role.name,
            action='Restored',
            comments=f"Restored to version {version_number} snapshot data.",
            signature=f"Signed by {user.full_name or user.username} at {datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}"
        )
        db.session.add(approval)
        
        # Audit log
        audit = AuditLog(
            org_id=user.org_id,
            user_id=user_id,
            action='SOP_RESTORED',
            target_table='sops',
            target_id=sop.id,
            details={"version_restored": version_number, "role": user.role.name}
        )
        db.session.add(audit)
        
        db.session.commit()
        return jsonify({"msg": f"SOP successfully restored to version {version_number}", "version": sop.version}), 200
        
    except Exception as e:
        db.session.rollback()
        return internal_server_error(e, "Failed to restore version.")

# ============================
# SOP TRAINING & ACKNOWLEDGEMENT
# ============================

# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: assign_training (Lines 907-1033)
# Reason: Training assignment feature removed from frontend.
# ==============================================================================
# @sop_bp.route('/<int:sop_id>/assign-training', methods=['POST'])
# @jwt_required()
# @role_required(['Reviewer', 'Admin', 'SuperAdmin'])
# def assign_training(sop_id):
#     """Assign training read task to a user, department, role, or project team."""
#     user_id = get_jwt_identity()
#     user = db.session.get(User, user_id)

#     sop = SOP.query.filter_by(id=sop_id, org_id=user.org_id).first_or_404()
#     data = request.get_json()

#     target_user_id = parse_int(data.get('user_id'))
#     target_dept_id = parse_int(data.get('department_id'))
#     target_project_id = parse_int(data.get('project_id'))
#     target_role_id = parse_int(data.get('role_id'))

#     if not any([target_user_id, target_dept_id, target_project_id, target_role_id]):
#         return jsonify({"msg": "At least one target (user_id, department_id, project_id, role_id) must be provided"}), 400

#     # Department constraint for Team Leaders
#     if user.role.name in ('Team Leader', 'Team Member'):
#         if target_dept_id and target_dept_id != user.department_id:
#             return jsonify({"msg": "Access denied. Team Leaders can only assign training to their own department."}), 403
#         if target_user_id:
#             target_user = User.query.filter_by(id=target_user_id, org_id=user.org_id).first()
#             if target_user and target_user.department_id != user.department_id:
#                 return jsonify({"msg": "Access denied. Team Leaders can only assign training to members of their own department."}), 403

#     try:
#         users_to_assign = []
#         if target_user_id:
#             u = User.query.filter_by(id=target_user_id, org_id=user.org_id).first()
#             if u:
#                 users_to_assign.append(u)
#         elif target_dept_id:
#             users_to_assign = User.query.filter_by(department_id=target_dept_id, org_id=user.org_id).all()
#         elif target_role_id:
#             users_to_assign = User.query.filter_by(role_id=target_role_id, org_id=user.org_id).all()
#         elif target_project_id:
#             proj_members = ProjectMember.query.filter_by(project_id=target_project_id).all()
#             member_ids = {pm.user_id for pm in proj_members}
#             target_proj = db.session.get(Project, target_project_id)
#             if target_proj and target_proj.org_id == user.org_id:
#                 if target_proj.creator_id: member_ids.add(target_proj.creator_id)
#                 if target_proj.team_leader_id: member_ids.add(target_proj.team_leader_id)
#                 if target_proj.facilitator_id: member_ids.add(target_proj.facilitator_id)
#                 if target_proj.reviewer_id: member_ids.add(target_proj.reviewer_id)
#             users_to_assign = User.query.filter(User.id.in_(list(member_ids)), User.org_id == user.org_id).all()

#         count = 0
#         due_date = datetime.now(timezone.utc).replace(tzinfo=None).date() + timedelta(days=sop.due_days)
#         expiry_date = datetime.now(timezone.utc).replace(tzinfo=None).date() + timedelta(days=365) # default 1 year expiry

#         for u in users_to_assign:
#             # Check if already assigned
#             existing = SOPTraining.query.filter_by(sop_id=sop.id, user_id=u.id).first()
#             if not existing:
#                 t = SOPTraining(
#                     sop_id=sop.id,
#                     user_id=u.id,
#                     assigned_by_id=user_id,
#                     assigned_date=datetime.now(timezone.utc).replace(tzinfo=None),
#                     due_date=due_date,
#                     expiry_date=expiry_date,
#                     attempts_left=sop.max_attempts or 3,
#                     status='Not Started',
#                     read_status=False,
#                     acknowledgement_status=False,
#                     training_completion_status=False
#                 )
#                 db.session.add(t)
#                 db.session.flush() # populate t.id

#                 # In-app Notification
#                 from app.presentation.routes.notification_routes import create_notification
#                 create_notification(
#                     org_id=user.org_id,
#                     user_id=u.id,
#                     title="New SOP Assigned",
#                     message=f"You have been assigned training for SOP '{sop.title}'. Due Date: {due_date}",
#                     link=f"/projects/standards.html?tab=training"
#                 )

#                 # SOPNotification Log
#                 notif = SOPNotification(
#                     training_id=t.id,
#                     user_id=u.id,
#                     notification_type='New Assignment',
#                     message=f"You have been assigned to read and train on SOP: '{sop.title}'. Due Date: {due_date}"
#                 )
#                 db.session.add(notif)
#                 count += 1
#             else:
#                 # Reset training record to allow retry
#                 existing.assigned_by_id = user_id
#                 existing.assigned_date = datetime.now(timezone.utc).replace(tzinfo=None)
#                 existing.due_date = due_date
#                 existing.expiry_date = expiry_date
#                 existing.attempts_left = sop.max_attempts or 3
#                 existing.status = 'Not Started'
#                 existing.read_status = False
#                 existing.acknowledgement_status = False
#                 existing.training_completion_status = False
#                 existing.assessment_score = None
#                 existing.completed_at = None
#                 existing.total_reading_time = 0
#                 existing.reading_percentage = 0.0
#                 existing.first_opened_at = None
#                 existing.last_viewed_at = None

#                 # In-app Notification for Reset/Re-assign
#                 from app.presentation.routes.notification_routes import create_notification
#                 create_notification(
#                     org_id=user.org_id,
#                     user_id=u.id,
#                     title="SOP Training Reset / Re-assigned",
#                     message=f"Your training progress for SOP '{sop.title}' has been reset by the facilitator. Please retake the training.",
#                     link=f"/projects/standards.html?tab=training"
#                 )
#                 count += 1

#         db.session.commit()
#         return jsonify({"msg": f"SOP assigned successfully to {count} users"}), 200

#     except Exception as e:
#         db.session.rollback()
#         return internal_server_error(e, "Assignment failed.")
# [END DEAD CODE: assign_training]


@sop_bp.route('/training/dashboard', methods=['GET'])
@jwt_required()
def training_dashboard():
    """Retrieve lists of assigned, completed, and pending SOPs, or compliance metrics depending on role."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    role_name = user.role.name
    
    # User specific training list
    my_tasks = SOPTraining.query.filter_by(user_id=user_id).all()
    pending = []
    completed = []
    
    for t in my_tasks:
        sop = t.sop
        if not sop:
            continue
            
        task_data = {
            "id": t.id,
            "sop_id": sop.id,
            "sop_uid": sop.sop_uid,
            "title": sop.title,
            "category": sop.category,
            "department_name": sop.department.name if sop.department else "Organization",
            "assigned_date": t.assigned_date.isoformat() if t.assigned_date else None,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "expiry_date": t.expiry_date.isoformat() if t.expiry_date else None,
            "status": t.status,
            "attempts_left": t.attempts_left,
            "total_reading_time": t.total_reading_time,
            "reading_percentage": t.reading_percentage,
            "read_status": t.read_status,
            "acknowledgement_status": t.acknowledgement_status,
            "training_completion_status": t.training_completion_status,
            "assessment_score": t.assessment_score,
            "completed_at": t.completed_at.isoformat() + "Z" if t.completed_at else None,
            "is_archived": sop.is_archived
        }
        
        if t.training_completion_status:
            completed.append(task_data)
        else:
            pending.append(task_data)
            
    # Compile role-specific dashboards
    dashboard_data = {
        "stats": {
            "total_assigned": len(my_tasks),
            "completed": len(completed),
            "pending": len(pending),
            "compliance_rate": round((len(completed) / len(my_tasks) * 100)) if my_tasks else 100
        },
        "pending": pending,
        "completed": completed
    }
    
    if role_name in ('Team Leader', 'Team Member') and user.department_id:
        # Department stats
        dept_trainings = SOPTraining.query.join(SOP).filter(
            db.or_(
                SOP.department_id == user.department_id,
                SOP.project_id.in_(db.session.query(Project.id).filter_by(department_id=user.department_id))
            )
        ).all()
        dept_completed = sum(1 for t in dept_trainings if t.training_completion_status)
        dept_total = len(dept_trainings)
        dept_pending = sum(1 for t in dept_trainings if not t.training_completion_status and t.status != 'Overdue' and t.status != 'Failed')
        dept_failed = sum(1 for t in dept_trainings if t.status == 'Failed')
        dept_overdue = sum(1 for t in dept_trainings if t.status == 'Overdue')
        
        dashboard_data["team_stats"] = {
            "completion_percentage": round((dept_completed / dept_total * 100)) if dept_total > 0 else 100,
            "total_assigned": dept_total,
            "completed": dept_completed,
            "pending": dept_pending,
            "failed": dept_failed,
            "overdue": dept_overdue
        }
        
    elif role_name in ('Facilitator', 'Admin', 'SuperAdmin', 'CEO', 'Reviewer'):
        # Global stats
        all_trainings = SOPTraining.query.join(SOP).filter(SOP.org_id == user.org_id).all()
        total_g = len(all_trainings)
        completed_g = sum(1 for t in all_trainings if t.training_completion_status)
        pending_g = sum(1 for t in all_trainings if not t.training_completion_status and t.status != 'Overdue' and t.status != 'Failed')
        failed_g = sum(1 for t in all_trainings if t.status == 'Failed')
        overdue_g = sum(1 for t in all_trainings if t.status == 'Overdue')
        
        dashboard_data["global_stats"] = {
            "total_assigned": total_g,
            "completed": completed_g,
            "pending": pending_g,
            "failed": failed_g,
            "overdue": overdue_g,
            "compliance_rate": round((completed_g / total_g * 100)) if total_g > 0 else 100
        }
        
    return jsonify(dashboard_data), 200

# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: track_reading (Lines 1135-1172)
# Reason: Reading progress tracking feature removed from frontend.
# ==============================================================================
# @sop_bp.route('/training/<int:training_id>/track', methods=['POST'])
# @jwt_required()
# def track_reading(training_id):
#     """Accumulate reading duration and percentage scroll completion."""
#     user_id = get_jwt_identity()
#     t = SOPTraining.query.filter_by(id=training_id, user_id=user_id).first_or_404()

#     if t.sop.is_archived:
#         return jsonify({"msg": "Access denied. This SOP has been archived and is read-only."}), 403

#     data = request.get_json()
#     reading_time = parse_int(data.get('reading_time')) or 0 # in seconds
#     reading_percentage = float(data.get('reading_percentage') or 0.0)

#     try:
#         if not t.first_opened_at:
#             t.first_opened_at = datetime.now(timezone.utc).replace(tzinfo=None)
#         t.last_viewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
#         t.total_reading_time += reading_time
#         t.reading_percentage = max(t.reading_percentage, reading_percentage)

#         # Validation Rule: Must open document, scroll 100%, and minimum reading time of 5 seconds
#         if t.reading_percentage >= 100.0 and t.total_reading_time >= 5:
#             t.read_status = True
#             if t.status == 'Not Started':
#                 t.status = 'In Progress'

#         db.session.commit()
#         return jsonify({
#             "msg": "Reading metrics tracked successfully",
#             "total_reading_time": t.total_reading_time,
#             "reading_percentage": t.reading_percentage,
#             "read_status": t.read_status,
#             "status": t.status
#         }), 200
#     except Exception as e:
#         db.session.rollback()
#         return internal_server_error(e, "Failed to track reading metrics.")
# [END DEAD CODE: track_reading]


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: acknowledge_training (Lines 1174-1237)
# Reason: Training acknowledgment removed from frontend.
# ==============================================================================
# @sop_bp.route('/training/<int:training_id>/acknowledge', methods=['POST'])
# @jwt_required()
# def acknowledge_training(training_id):
#     """Submit digital signature acknowledgement."""
#     user_id = get_jwt_identity()
#     user = db.session.get(User, user_id)
#     t = SOPTraining.query.filter_by(id=training_id, user_id=user_id).first_or_404()

#     if t.sop.is_archived:
#         return jsonify({"msg": "Access denied. This SOP has been archived and is read-only."}), 403

#     if not t.read_status:
#         return jsonify({"msg": "SOP must be opened and read completely before acknowledgement."}), 400

#     data = request.get_json()
#     digital_signature = data.get('digital_signature')
#     employee_id = data.get('employee_id')

#     if not digital_signature or not digital_signature.strip():
#         return jsonify({"msg": "Digital signature is required."}), 400

#     try:
#         if employee_id and not user.employee_id:
#             user.employee_id = employee_id

#         statement = "I confirm that I have read, understood, and agree to follow this SOP."
#         ack = SOPAcknowledgement(
#             training_id=t.id,
#             user_id=user_id,
#             statement=statement,
#             ip_address=request.remote_addr,
#             digital_signature=digital_signature.strip(),
#             created_at=datetime.now(timezone.utc).replace(tzinfo=None)
#         )
#         db.session.add(ack)
#         t.acknowledgement_status = True

#         # Check if assessment exists
#         has_questions = SOPAssessmentQuestion.query.filter_by(sop_id=t.sop_id).first() is not None
#         if has_questions:
#             t.status = 'Assessment Pending'
#         else:
#             # Exempt from assessment, complete immediately
#             t.status = 'Completed'
#             t.training_completion_status = True
#             t.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)

#             # SOPNotification Completed
#             notif = SOPNotification(
#                 training_id=t.id,
#                 user_id=user_id,
#                 notification_type='Training Completed',
#                 message=f"Congratulations! You completed training for SOP: '{t.sop.title}'."
#             )
#             db.session.add(notif)

#         db.session.commit()
#         return jsonify({
#             "status": t.status,
#             "completed": t.training_completion_status
#         }), 200
#     except Exception as e:
#         db.session.rollback()
#         return internal_server_error(e, "Acknowledgement failed.")
# [END DEAD CODE: acknowledge_training]


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: get_sop_assessment (Lines 1239-1278)
# Reason: SOP quiz/assessment feature removed from frontend.
# ==============================================================================
# @sop_bp.route('/<int:sop_id>/assessment', methods=['GET'])
# @jwt_required()
# def get_sop_assessment(sop_id):
#     """Retrieve quiz questions for the SOP, shuffling options if random_order is enabled."""
#     user_id = get_jwt_identity()
#     user = db.session.get(User, user_id)
#     sop = SOP.query.filter_by(id=sop_id, org_id=user.org_id).first_or_404()

#     config = SOPAssessment.query.filter_by(sop_id=sop.id).first()
#     questions = SOPAssessmentQuestion.query.filter_by(sop_id=sop.id).all()

#     is_staff = user.role.name in ('Admin', 'SuperAdmin', 'CEO', 'Facilitator', 'Reviewer')

#     import random
#     q_list = []
#     for q in questions:
#         opts = list(q.options) if q.options else []
#         if config and config.random_order and not is_staff:
#             random.shuffle(opts)

#         q_data = {
#             "id": q.id,
#             "question_text": q.question_text,
#             "question_type": q.question_type,
#             "options": opts
#         }
#         if is_staff:
#             q_data["correct_answers"] = q.correct_answers

#         q_list.append(q_data)

#     if config and config.random_order and not is_staff:
#         random.shuffle(q_list)

#     return jsonify({
#         "pass_percentage": config.pass_percentage if config else 80,
#         "time_limit": config.time_limit if config else 30,
#         "attempts_allowed": config.attempts_allowed if config else 3,
#         "questions": q_list
#     }), 200
# [END DEAD CODE: get_sop_assessment]


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: add_sop_assessment_questions (Lines 1280-1329)
# Reason: Assessment question authoring removed from frontend.
# ==============================================================================
# @sop_bp.route('/<int:sop_id>/assessment/questions', methods=['POST'])
# @jwt_required()
# @role_required(['Reviewer', 'Admin', 'SuperAdmin'])
# def add_sop_assessment_questions(sop_id):
#     """Define quiz questions and configuration for an SOP."""
#     user_id = get_jwt_identity()
#     user = db.session.get(User, user_id)
#     sop = SOP.query.filter_by(id=sop_id, org_id=user.org_id).first_or_404()

#     if sop.is_archived:
#         return jsonify({"msg": "Access denied. This SOP has been archived and is read-only."}), 403

#     data = request.get_json()
#     pass_percentage = parse_int(data.get('pass_percentage')) or 80
#     time_limit = parse_int(data.get('time_limit')) or 30
#     attempts_allowed = parse_int(data.get('attempts_allowed')) or 3
#     random_order = bool(data.get('random_order', False))

#     questions_data = data.get('questions', [])
#     if not questions_data:
#         return jsonify({"msg": "Questions list cannot be empty."}), 400

#     try:
#         # Create/Update config
#         config = SOPAssessment.query.filter_by(sop_id=sop.id).first()
#         if not config:
#             config = SOPAssessment(sop_id=sop.id)
#             db.session.add(config)
#         config.pass_percentage = pass_percentage
#         config.time_limit = time_limit
#         config.attempts_allowed = attempts_allowed
#         config.random_order = random_order

#         # Replace questions
#         SOPAssessmentQuestion.query.filter_by(sop_id=sop.id).delete()
#         for q in questions_data:
#             new_q = SOPAssessmentQuestion(
#                 sop_id=sop.id,
#                 question_text=q.get('question_text'),
#                 question_type=q.get('question_type', 'MCQ'),
#                 options=q.get('options', []),
#                 correct_answers=q.get('correct_answers', [])
#             )
#             db.session.add(new_q)

#         db.session.commit()
#         return jsonify({"msg": "Assessment questions and configuration saved successfully"}), 200
#     except Exception as e:
#         db.session.rollback()
#         return internal_server_error(e, "Failed to save assessment.")
# [END DEAD CODE: add_sop_assessment_questions]


@sop_bp.route('/training/<int:training_id>/assessment/submit', methods=['POST'])
@jwt_required()
def submit_assessment(training_id):
    """Grade quiz answers, record attempt, and trigger completion logic."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    t = SOPTraining.query.filter_by(id=training_id, user_id=user_id).first_or_404()
    
    if t.sop.is_archived:
        return jsonify({"msg": "Access denied. This SOP has been archived and is read-only."}), 403
        
    if t.attempts_left <= 0:
        return jsonify({"msg": "No assessment attempts remaining."}), 400
        
    data = request.get_json()
    user_answers = data.get('answers', []) # list of dicts: {"question_id": X, "answers": [Y]}
    
    questions = {q.id: q for q in SOPAssessmentQuestion.query.filter_by(sop_id=t.sop_id).all()}
    if not questions:
        return jsonify({"msg": "No assessment configured for this SOP."}), 400
        
    correct_count = 0
    total_questions = len(questions)
    
    for ans in user_answers:
        q_id = parse_int(ans.get('question_id'))
        ans_list = ans.get('answers', [])
        
        if q_id in questions:
            q = questions[q_id]
            # Grade comparison
            correct_set = set(q.correct_answers or [])
            user_set = set(ans_list or [])
            if correct_set == user_set:
                correct_count += 1
                
    percentage = (correct_count / total_questions * 100.0) if total_questions > 0 else 100.0
    config = SOPAssessment.query.filter_by(sop_id=t.sop_id).first()
    pass_pct = config.pass_percentage if config else 80
    result_str = 'Pass' if percentage >= pass_pct else 'Fail'
    
    attempt_num = (config.attempts_allowed if config else 3) - t.attempts_left + 1
    t.attempts_left -= 1
    
    try:
        # Save Result Log
        res = SOPAssessmentResult(
            training_id=t.id,
            user_id=user_id,
            score=correct_count,
            percentage=percentage,
            attempt_number=attempt_num,
            result=result_str,
            answers_submitted=user_answers,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.session.add(res)
        
        t.assessment_score = int(percentage)
        
        if result_str == 'Pass':
            t.status = 'Completed'
            t.training_completion_status = True
            t.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            
            # In-app alert
            from app.presentation.routes.notification_routes import create_notification
            create_notification(
                org_id=user.org_id,
                user_id=user_id,
                title="Training Completed Successfully",
                message=f"You passed the assessment and completed training for SOP '{t.sop.title}'!",
                link=f"/projects/standards.html?tab=training"
            )
            
            # SOPNotification Completed
            notif = SOPNotification(
                training_id=t.id,
                user_id=user_id,
                notification_type='Training Completed',
                message=f"Congratulations! You passed the assessment and completed training for SOP: '{t.sop.title}'."
            )
            db.session.add(notif)
            
        else:
            if t.attempts_left <= 0:
                t.status = 'Failed'
            else:
                t.status = 'Assessment Pending'
                
            # SOPNotification Failed
            notif = SOPNotification(
                training_id=t.id,
                user_id=user_id,
                notification_type='Assessment Failed',
                message=f"You failed attempt {attempt_num} for SOP assessment: '{t.sop.title}'. Score: {percentage:.0f}%"
            )
            db.session.add(notif)
            
        db.session.commit()
        return jsonify({
            "result": result_str,
            "percentage": percentage,
            "attempts_left": t.attempts_left,
            "status": t.status,
            "completed": t.training_completion_status
        }), 200
    except Exception as e:
        db.session.rollback()
        return internal_server_error(e, "Failed to submit assessment.")

@sop_bp.route('/training/<int:training_id>/results', methods=['GET'])
@jwt_required()
def get_training_results(training_id):
    """Retrieve detailed assessment results for a specific training record."""
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    t = SOPTraining.query.filter_by(id=training_id).first_or_404()
    
    # Permission check: User must be the trainee themselves, or an Admin/Facilitator/Team Leader/Reviewer in the org
    is_authorized = (
        t.user_id == user_id or
        user.role.name in ('Admin', 'Facilitator', 'Team Leader', 'Team Member', 'SuperAdmin', 'CEO', 'Reviewer')
    )
    if not is_authorized or t.user.org_id != user.org_id:
        return jsonify({"msg": "Unauthorized to view these results."}), 403
        
    results = SOPAssessmentResult.query.filter_by(training_id=training_id).order_by(SOPAssessmentResult.attempt_number.desc()).all()
    
    # Retrieve configured questions for the SOP
    questions = {q.id: q for q in SOPAssessmentQuestion.query.filter_by(sop_id=t.sop_id).all()}
    
    response_data = []
    for r in results:
        attempt_details = []
        user_answers_list = r.answers_submitted or []
        
        # Loop through configured questions and match with user answers
        for q_id, q in questions.items():
            user_ans = []
            for ua in user_answers_list:
                try:
                    ua_qid = int(ua.get('question_id'))
                except (ValueError, TypeError):
                    ua_qid = None
                    
                if ua_qid == q_id:
                    user_ans = ua.get('answers', [])
                    break
            
            correct_set = set(q.correct_answers or [])
            user_set = set(user_ans or [])
            is_correct = (correct_set == user_set)
            
            attempt_details.append({
                "question_text": q.question_text,
                "question_type": q.question_type,
                "options": q.options or [],
                "user_answers": user_ans,
                "correct_answers": q.correct_answers or [],
                "is_correct": is_correct
            })
            
        response_data.append({
            "attempt_number": r.attempt_number,
            "score": r.score,
            "percentage": r.percentage,
            "result": r.result,
            "created_at": r.created_at.isoformat() + "Z",
            "details": attempt_details
        })
        
    return jsonify(response_data), 200

@sop_bp.route('/<int:sop_id>/archive', methods=['POST'])
@jwt_required()
@role_required(['Reviewer', 'Admin', 'SuperAdmin'])
def archive_sop(sop_id):
    """Archiving SOP and marking records as read-only."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    sop = SOP.query.filter_by(id=sop_id, org_id=user.org_id).first_or_404()
    
    data = request.get_json() or {}
    reason = data.get('reason', 'Administrative Archival')
    
    try:
        sop.is_archived = True
        sop.status = 'Archived'
        
        archive = SOPArchive(
            sop_id=sop.id,
            archived_by_id=user_id,
            archived_at=datetime.now(timezone.utc).replace(tzinfo=None),
            reason=reason
        )
        db.session.add(archive)
        
        # Log to Audit Log
        audit = AuditLog(
            org_id=user.org_id,
            user_id=user_id,
            project_id=sop.project_id,
            action='SOP_ARCHIVED',
            target_table='sop_master',
            target_id=sop.id,
            details={"sop_uid": sop.sop_uid, "reason": reason}
        )
        db.session.add(audit)
        
        db.session.commit()
        return jsonify({"msg": "SOP successfully archived. Records are now read-only."}), 200
    except Exception as e:
        db.session.rollback()
        return internal_server_error(e, "Failed to archive SOP.")

# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: restore_sop (Lines 1547-1579)
# Reason: SOP archive restoration.
# ==============================================================================
# @sop_bp.route('/<int:sop_id>/restore-archive', methods=['POST'])
# @jwt_required()
# @role_required(['Reviewer', 'Admin', 'SuperAdmin'])
# def restore_sop(sop_id):
#     """Restores an archived SOP."""
#     user_id = get_jwt_identity()
#     user = db.session.get(User, user_id)
#     sop = SOP.query.filter_by(id=sop_id, org_id=user.org_id).first_or_404()

#     try:
#         sop.is_archived = False
#         sop.status = 'Active'

#         # Delete archive log
#         SOPArchive.query.filter_by(sop_id=sop.id).delete()

#         # Log to Audit Log
#         audit = AuditLog(
#             org_id=user.org_id,
#             user_id=user_id,
#             project_id=sop.project_id,
#             action='SOP_RESTORED',
#             target_table='sop_master',
#             target_id=sop.id,
#             details={"sop_uid": sop.sop_uid}
#         )
#         db.session.add(audit)

#         db.session.commit()
#         return jsonify({"msg": "SOP successfully restored and activated."}), 200
#     except Exception as e:
#         db.session.rollback()
#         return internal_server_error(e, "Failed to restore SOP.")
# [END DEAD CODE: restore_sop]


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: delete_sop (Lines 1581-1617)
# Reason: Hard delete SOP route.
# ==============================================================================
# @sop_bp.route('/<int:sop_id>', methods=['DELETE'])
# @jwt_required()
# @role_required(['Reviewer', 'Admin', 'SuperAdmin'])
# def delete_sop(sop_id):
#     """Delete a specific SOP completely, with its child records cascading."""
#     user_id = get_jwt_identity()
#     user = db.session.get(User, user_id)
#     sop = SOP.query.filter_by(id=sop_id, org_id=user.org_id).first_or_404()

#     # Check if the reviewer is authorized (author or owner)
#     is_authorized = (
#         sop.author_id == user.id or
#         sop.owner_id == user.id or
#         (sop.project and sop.project.reviewer_id == user.id)
#     )
#     if not is_authorized:
#         return jsonify({"msg": "Access denied. You are not authorized to delete this SOP."}), 403

#     try:
#         # Audit Log
#         audit = AuditLog(
#             org_id=user.org_id,
#             user_id=user_id,
#             project_id=sop.project_id,
#             action='SOP_DELETED',
#             target_table='sop_master',
#             target_id=sop.id,
#             details={"title": sop.title, "sop_uid": sop.sop_uid}
#         )
#         db.session.add(audit)

#         db.session.delete(sop)
#         db.session.commit()
#         return jsonify({"msg": "SOP and all associated training records deleted successfully."}), 200
#     except Exception as e:
#         db.session.rollback()
#         return internal_server_error(e, "Failed to delete SOP.")
# [END DEAD CODE: delete_sop]


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: audit_sop (Lines 1619-1646)
# Reason: Standalone SOP audit trigger.
# ==============================================================================
# @sop_bp.route('/<int:sop_id>/audit', methods=['POST'])
# @jwt_required()
# @role_required(['Reviewer', 'Admin', 'SuperAdmin'])
# def audit_sop(sop_id):
#     """Assess training checklist metrics prior to final sign-off."""
#     user_id = get_jwt_identity()
#     user = db.session.get(User, user_id)
#     sop = SOP.query.filter_by(id=sop_id, org_id=user.org_id).first_or_404()

#     trainings = SOPTraining.query.filter_by(sop_id=sop.id).all()
#     total = len(trainings)
#     completed = sum(1 for t in trainings if t.training_completion_status)
#     pending = total - completed
#     failed = sum(1 for t in trainings if t.status == 'Failed')
#     overdue = sum(1 for t in trainings if t.status == 'Overdue')

#     audit_passed = (pending == 0 and failed == 0 and overdue == 0)

#     return jsonify({
#         "sop_uid": sop.sop_uid,
#         "title": sop.title,
#         "total_assigned": total,
#         "completed": completed,
#         "pending": pending,
#         "failed": failed,
#         "overdue": overdue,
#         "audit_passed": audit_passed
#     }), 200
# [END DEAD CODE: audit_sop]


@sop_bp.route('/<int:sop_id>/audit/report', methods=['GET'])
@jwt_required()
@role_required(['Reviewer', 'Admin', 'SuperAdmin'])
def download_audit_report(sop_id):
    """Download PDF final audit report."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    sop = SOP.query.filter_by(id=sop_id, org_id=user.org_id).first_or_404()
    trainings = SOPTraining.query.filter_by(sop_id=sop.id).all()
    
    try:
        from app.utils.report_gen import generate_sop_audit_report
        pdf_bytes = generate_sop_audit_report(sop, trainings, report_type='Training Audit')
        
        # Save audit record
        audit_rep = SOPAuditReport(
            org_id=user.org_id,
            project_id=sop.project_id,
            generated_by_id=user_id,
            report_type='Training Audit'
        )
        db.session.add(audit_rep)
        db.session.commit()
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"AuditReport_{sop.sop_uid}.pdf"
        )
    except Exception as e:
        return internal_server_error(e, "Failed to generate audit report.")

@sop_bp.route('/<int:sop_id>/compliance/report', methods=['GET'])
@jwt_required()
@role_required(['Facilitator', 'Reviewer', 'Admin', 'SuperAdmin'])
def download_compliance_report(sop_id):
    """Download PDF compliance report."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    sop = SOP.query.filter_by(id=sop_id, org_id=user.org_id).first_or_404()
    trainings = SOPTraining.query.filter_by(sop_id=sop.id).all()
    
    try:
        from app.utils.report_gen import generate_sop_audit_report
        pdf_bytes = generate_sop_audit_report(sop, trainings, report_type='Compliance')
        
        audit_rep = SOPAuditReport(
            org_id=user.org_id,
            project_id=sop.project_id,
            generated_by_id=user_id,
            report_type='Compliance'
        )
        db.session.add(audit_rep)
        db.session.commit()
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"ComplianceReport_{sop.sop_uid}.pdf"
        )
    except Exception as e:
        return internal_server_error(e, "Failed to generate compliance report.")

@sop_bp.route('/training/notifications', methods=['GET'])
@jwt_required()
def get_sop_notifications():
    """Retrieve logged training notifications for current user."""
    user_id = get_jwt_identity()
    notifs = SOPNotification.query.filter_by(user_id=user_id).order_by(SOPNotification.created_at.desc()).limit(15).all()
    
    results = [{
        "id": n.id,
        "notification_type": n.notification_type,
        "message": n.message,
        "created_at": n.created_at.isoformat() + "Z"
    } for n in notifs]
    return jsonify(results), 200

# ============================
# SOP ANALYTICS DASHBOARD
# ============================

@sop_bp.route('/analytics', methods=['GET'])
@jwt_required()
def get_sop_analytics():
    """Retrieve detailed analytics regarding total, active, expired, and department compliance rates."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    
    # 1. Status aggregates
    status_counts = db.session.query(SOP.status, func.count(SOP.id)).filter_by(org_id=user.org_id).group_by(SOP.status).all()
    status_dict = {"Draft": 0, "Under Review": 0, "Approved": 0, "Active": 0, "Archived": 0, "Obsolete": 0}
    for st, count in status_counts:
        status_dict[st] = count
        
    # 2. Category aggregates
    category_counts = db.session.query(SOP.category, func.count(SOP.id)).filter_by(org_id=user.org_id).group_by(SOP.category).all()
    category_dict = {}
    for cat, count in category_counts:
        category_dict[cat] = count
        
    # 3. Department-wise SOP distribution
    dept_counts = db.session.query(Department.name, func.count(SOP.id)).join(SOP, SOP.department_id == Department.id)\
        .filter(SOP.org_id == user.org_id).group_by(Department.name).all()
    dept_dict = {}
    for dept_name, count in dept_counts:
        dept_dict[dept_name] = count
        
    # 4. Compliance/Adoption statistics
    total_assigned = db.session.query(func.count(SOPTraining.id)).join(SOP, SOPTraining.sop_id == SOP.id).filter(SOP.org_id == user.org_id).scalar() or 0
    completed_assigned = db.session.query(func.count(SOPTraining.id)).join(SOP, SOPTraining.sop_id == SOP.id)\
        .filter(SOP.org_id == user.org_id, SOPTraining.training_completion_status == True).scalar() or 0
        
    compliance_rate = round((completed_assigned / total_assigned * 100)) if total_assigned > 0 else 100
    
    # 5. List of upcoming reviews (within 30 days)
    upcoming_reviews = []
    limit_date = datetime.now(timezone.utc).replace(tzinfo=None)
    review_alerts = SOP.query.filter(
        SOP.org_id == user.org_id,
        SOP.status == 'Active',
        SOP.review_date.isnot(None),
        SOP.review_date >= limit_date.date()
    ).order_by(SOP.review_date.asc()).limit(5).all()
    
    for r in review_alerts:
        upcoming_reviews.append({
            "id": r.id,
            "sop_uid": r.sop_uid,
            "title": r.title,
            "review_date": r.review_date.isoformat(),
            "owner": r.owner.full_name or r.owner.username if r.owner else "N/A"
        })

    return jsonify({
        "stats": {
            "total": sum(status_dict.values()),
            "active": status_dict.get("Active", 0),
            "under_review": status_dict.get("Under Review", 0) + status_dict.get("Approved", 0),
            "draft": status_dict.get("Draft", 0),
            "archived": status_dict.get("Archived", 0),
            "obsolete": status_dict.get("Obsolete", 0),
            "training_compliance_rate": compliance_rate,
            "total_training_assigned": total_assigned,
            "total_training_completed": completed_assigned
        },
        "by_status": status_dict,
        "by_category": category_dict,
        "by_department": dept_dict,
        "upcoming_reviews": upcoming_reviews
    }), 200

# ============================
# SOP COMMENTS & FEEDBACK
# ============================

@sop_bp.route('/<int:sop_id>/comments', methods=['POST'])
@jwt_required()
def add_sop_comment(sop_id):
    """Add a feedback, verification, compliance, or administrative comment to an SOP."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    query = SOP.query.filter_by(id=sop_id, org_id=user.org_id)
    sop = scope_sop_query(query, user).first_or_404()
    
    data = request.get_json()
    content = data.get('content')
    comment_type = data.get('comment_type', 'General')
    
    if not content or not content.strip():
        return jsonify({"msg": "Comment content is required"}), 400
        
    # Map roles to comment types if not specified
    role_name = user.role.name
    if not data.get('comment_type'):
        if role_name == 'Team Member':
            is_tl = False
            if sop.project_id:
                proj = db.session.get(Project, sop.project_id)
                if proj and proj.team_leader_id == user.id:
                    is_tl = True
            comment_type = 'Verification' if is_tl else 'Feedback'
        elif role_name == 'Team Leader':
            comment_type = 'Verification'
        elif role_name == 'Reviewer':
            comment_type = 'Review'
        elif role_name in ('Admin', 'SuperAdmin'):
            comment_type = 'AdminCorrection'
            
    try:
        comment = SOPComment(
            sop_id=sop.id,
            user_id=user.id,
            role=role_name,
            comment_type=comment_type,
            content=content.strip()
        )
        db.session.add(comment)
        
        # Log to Audit Log
        audit = AuditLog(
            org_id=user.org_id,
            user_id=user_id,
            project_id=sop.project_id,
            action='SOP_COMMENT_ADDED',
            target_table='sop_comments',
            target_id=sop.id,
            details={"sop_uid": sop.sop_uid, "role": role_name, "comment_type": comment_type}
        )
        db.session.add(audit)
        
        db.session.commit()
        return jsonify({
            "msg": "Comment added successfully",
            "comment": {
                "id": comment.id,
                "user_name": user.full_name or user.username,
                "role": role_name,
                "comment_type": comment_type,
                "content": comment.content,
                "created_at": comment.created_at.isoformat() + "Z"
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return internal_server_error(e, "Failed to add comment.")

@sop_bp.route('/<int:sop_id>/comments', methods=['GET'])
@jwt_required()
def get_sop_comments(sop_id):
    """Retrieve comments for a specific SOP."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    
    query = SOP.query.filter_by(id=sop_id, org_id=user.org_id)
    sop = scope_sop_query(query, user).first_or_404()
    
    comments = SOPComment.query.filter_by(sop_id=sop.id).order_by(SOPComment.created_at.desc()).all()
    
    results = [{
        "id": c.id,
        "user_name": c.user.full_name or c.user.username,
        "role": c.role,
        "comment_type": c.comment_type,
        "content": c.content,
        "created_at": c.created_at.isoformat() + "Z"
    } for c in comments]
    
    return jsonify(results), 200

@sop_bp.route('/upload', methods=['POST'])
@jwt_required()
@role_required(['Team Member', 'Team Leader', 'Reviewer', 'Facilitator', 'Admin', 'SuperAdmin'])
def upload_sop_file():
    """Upload PDF/DOCX/XLSX/Images for SOP or Reference Documents (Max 2MB)."""
    if 'file' not in request.files:
        return jsonify({"msg": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"msg": "No selected file"}), 400
        
    # Check extension
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ('pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'):
        return jsonify({"msg": "Supported formats: PDF, DOCX, XLSX, PNG, JPG, JPEG"}), 400
        
    # Check file size (Strict 2MB limit: 2 * 1024 * 1024 bytes)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
    if file_size > MAX_FILE_SIZE:
        size_mb = round(file_size / (1024 * 1024), 2)
        return jsonify({"msg": f"File size exceeds 2MB limit ({size_mb} MB). Please upload a document up to 2MB."}), 400

    from app.infrastructure.storage import storage
    from werkzeug.utils import secure_filename
    filename = secure_filename(file.filename)
    target_name = f"sop_{datetime.now(timezone.utc).replace(tzinfo=None).strftime('%Y%m%d_%H%M%S')}_{filename}"
    result = storage.save_file(file, filename=target_name, subfolder="sop")
    
    return jsonify({
        "url": result['url'],
        "storage_backend": result.get('backend', 'local')
    }), 200


# ==========================================
# DYNAMIC SOP CATEGORY & TYPE MANAGEMENT
# ==========================================

DEFAULT_SOP_CATEGORIES = [
    {"name": "Quality", "description": "Quality assurance and defect prevention standards"},
    {"name": "Cost", "description": "Cost reduction and waste elimination procedures"},
    {"name": "Delivery", "description": "Logistics, lead time, and delivery standards"},
    {"name": "Safety", "description": "Occupational health and safety guidelines"},
    {"name": "Morale", "description": "Team engagement, workplace culture, and recognition"},
    {"name": "Environment", "description": "Environmental management and sustainability"},
    {"name": "Productivity", "description": "OEE improvement and cycle time optimization"}
]

DEFAULT_SOP_TYPES = [
    {"name": "Operational", "description": "Standard work instructions for daily machine and assembly operations"},
    {"name": "Safety Standard", "description": "EHS protocols, PPE rules, and emergency procedures"},
    {"name": "Quality Control", "description": "Inspection criteria, sampling methods, and defect verification"},
    {"name": "Maintenance", "description": "Preventive maintenance checklists and calibration guides"},
    {"name": "Administrative", "description": "Management processes, documentation, and office protocols"}
]

@sop_bp.route('/masters', methods=['GET'])
@jwt_required()
def get_sop_masters():
    """Retrieve or auto-seed organization's custom Categories and SOP Types."""
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id)) if user_id else None
    org_id = user.org_id if (user and user.org_id) else None

    if not org_id:
        return jsonify({
            "categories": [{"id": i + 1, "name": c["name"], "description": c["description"], "created_at": None} for i, c in enumerate(DEFAULT_SOP_CATEGORIES)],
            "types": [{"id": i + 1, "name": t["name"], "description": t["description"], "created_at": None} for i, t in enumerate(DEFAULT_SOP_TYPES)]
        }), 200

    cats = SOPCategory.query.filter_by(org_id=org_id).order_by(SOPCategory.name.asc()).all()
    if not cats:
        for c in DEFAULT_SOP_CATEGORIES:
            db.session.add(SOPCategory(org_id=org_id, name=c["name"], description=c["description"]))
        db.session.commit()
        cats = SOPCategory.query.filter_by(org_id=org_id).order_by(SOPCategory.name.asc()).all()

    types = SOPType.query.filter_by(org_id=org_id).order_by(SOPType.name.asc()).all()
    if not types:
        for t in DEFAULT_SOP_TYPES:
            db.session.add(SOPType(org_id=org_id, name=t["name"], description=t["description"]))
        db.session.commit()
        types = SOPType.query.filter_by(org_id=org_id).order_by(SOPType.name.asc()).all()

    return jsonify({
        "categories": [{"id": c.id, "name": c.name, "description": c.description, "created_at": c.created_at.isoformat() if c.created_at else None} for c in cats],
        "types": [{"id": t.id, "name": t.name, "description": t.description, "created_at": t.created_at.isoformat() if t.created_at else None} for t in types]
    }), 200

@sop_bp.route('/categories', methods=['POST'])
@jwt_required()
def create_sop_category():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    org_id = user.org_id if user else 1

    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    desc = (data.get('description') or '').strip()

    if not name:
        return jsonify({"msg": "Category name is required"}), 400

    existing = SOPCategory.query.filter_by(org_id=org_id, name=name).first()
    if existing:
        return jsonify({"msg": "Category already exists"}), 400

    cat = SOPCategory(org_id=org_id, name=name, description=desc)
    db.session.add(cat)
    db.session.commit()

    return jsonify({"msg": "Category created successfully", "category": {"id": cat.id, "name": cat.name, "description": cat.description}}), 201

@sop_bp.route('/categories/<int:cat_id>', methods=['PUT'])
@jwt_required()
def update_sop_category(cat_id):
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    org_id = user.org_id if user else 1

    cat = SOPCategory.query.filter_by(id=cat_id, org_id=org_id).first_or_404()
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if name:
        cat.name = name
    if 'description' in data:
        cat.description = (data.get('description') or '').strip()
    db.session.commit()

    return jsonify({"msg": "Category updated successfully", "category": {"id": cat.id, "name": cat.name, "description": cat.description}}), 200

@sop_bp.route('/categories/<int:cat_id>', methods=['DELETE'])
@jwt_required()
def delete_sop_category(cat_id):
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    org_id = user.org_id if user else 1

    cat = SOPCategory.query.filter_by(id=cat_id, org_id=org_id).first_or_404()
    db.session.delete(cat)
    db.session.commit()

    return jsonify({"msg": "Category deleted successfully"}), 200

@sop_bp.route('/types', methods=['POST'])
@jwt_required()
def create_sop_type():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    org_id = user.org_id if user else 1

    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    desc = (data.get('description') or '').strip()

    if not name:
        return jsonify({"msg": "SOP Type name is required"}), 400

    existing = SOPType.query.filter_by(org_id=org_id, name=name).first()
    if existing:
        return jsonify({"msg": "SOP Type already exists"}), 400

    t = SOPType(org_id=org_id, name=name, description=desc)
    db.session.add(t)
    db.session.commit()

    return jsonify({"msg": "SOP Type created successfully", "type": {"id": t.id, "name": t.name, "description": t.description}}), 201

# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: update_sop_type (Lines 2075-2091)
# Reason: SOP type edit.
# ==============================================================================
# @sop_bp.route('/types/<int:type_id>', methods=['PUT'])
# @jwt_required()
# def update_sop_type(type_id):
#     user_id = get_jwt_identity()
#     user = db.session.get(User, user_id)
#     org_id = user.org_id if user else 1

#     t = SOPType.query.filter_by(id=type_id, org_id=org_id).first_or_404()
#     data = request.get_json() or {}
#     name = (data.get('name') or '').strip()
#     if name:
#         t.name = name
#     if 'description' in data:
#         t.description = (data.get('description') or '').strip()
#     db.session.commit()

#     return jsonify({"msg": "SOP Type updated successfully", "type": {"id": t.id, "name": t.name, "description": t.description}}), 200
# [END DEAD CODE: update_sop_type]


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: delete_sop_type (Lines 2093-2104)
# Reason: SOP type delete.
# ==============================================================================
# @sop_bp.route('/types/<int:type_id>', methods=['DELETE'])
# @jwt_required()
# def delete_sop_type(type_id):
#     user_id = get_jwt_identity()
#     user = db.session.get(User, user_id)
#     org_id = user.org_id if user else 1

#     t = SOPType.query.filter_by(id=type_id, org_id=org_id).first_or_404()
#     db.session.delete(t)
#     db.session.commit()

#     return jsonify({"msg": "SOP Type deleted successfully"}), 200
# [END DEAD CODE: delete_sop_type]

