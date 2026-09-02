from datetime import datetime
from datetime import timezone, timezone
import json
import os
from sqlalchemy.dialects.postgresql import ARRAY
from app import db, bcrypt
from .base import SafeVector, Vector, is_local, _utc_now

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    __table_args__ = (
        db.Index('idx_audit_org_created', 'org_id', 'created_at'),
        db.Index('idx_audit_user_action', 'user_id', 'action'),
        db.Index('idx_audit_project_created', 'project_id', 'created_at'),
    )
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    target_table = db.Column(db.String(100))
    target_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=_utc_now)

    # Enterprise extensions
    session_id = db.Column(db.String(100))
    request_id = db.Column(db.String(100))
    response_code = db.Column(db.Integer)
    execution_time = db.Column(db.Float)  # ms
    risk_level = db.Column(db.String(20), default='Low')  # Low, Medium, High, Critical
    browser = db.Column(db.String(50))
    os = db.Column(db.String(50))
    device = db.Column(db.String(50))
    location = db.Column(db.String(100))
    before_data = db.Column(db.JSON)
    after_data = db.Column(db.JSON)
    hash_signature = db.Column(db.String(128))
    is_tampered = db.Column(db.Boolean, default=False)

    # Relationships
    user = db.relationship('User', backref='logs')


@db.event.listens_for(AuditLog, 'before_insert')
def auto_populate_audit_log_telemetry(mapper, connection, target):
    try:
        from flask import request, has_request_context, g
        if has_request_context():
            if not target.ip_address:
                header_keys = ['CF-Connecting-IP', 'X-Forwarded-For', 'X-Real-IP', 'True-Client-IP', 'X-Client-IP']
                for key in header_keys:
                    val = request.headers.get(key)
                    if val and val.strip():
                        ip = val.split(',')[0].strip()
                        if ip and ip not in ('127.0.0.1', '::1', 'localhost'):
                            target.ip_address = ip
                            break
                if not target.ip_address:
                    target.ip_address = request.remote_addr or '127.0.0.1'

            if not target.user_agent:
                target.user_agent = request.headers.get('User-Agent')

            if target.user_agent and (not target.os or not target.browser or not target.device):
                ua = target.user_agent.lower()
                if "mobile" in ua or "android" in ua or "iphone" in ua:
                    target.device = target.device or "Mobile"
                elif "tablet" in ua or "ipad" in ua:
                    target.device = target.device or "Tablet"
                else:
                    target.device = target.device or "Desktop"
                    
                if "windows" in ua: target.os = target.os or "Windows"
                elif "macintosh" in ua or "mac os" in ua: target.os = target.os or "macOS"
                elif "linux" in ua: target.os = target.os or "Linux"
                elif "iphone" in ua or "ipad" in ua: target.os = target.os or "iOS"
                elif "android" in ua: target.os = target.os or "Android"
                else: target.os = target.os or "Windows"

                if "edg/" in ua or "edge" in ua: target.browser = target.browser or "Edge"
                elif "opr/" in ua or "opera" in ua: target.browser = target.browser or "Opera"
                elif "brave" in ua: target.browser = target.browser or "Brave"
                elif "chrome" in ua: target.browser = target.browser or "Chrome"
                elif "firefox" in ua: target.browser = target.browser or "Firefox"
                elif "safari" in ua and "chrome" not in ua: target.browser = target.browser or "Safari"
                else: target.browser = target.browser or "Chrome"

            if not target.request_id:
                target.request_id = getattr(g, 'request_id', None) or request.headers.get('X-Request-ID')

            if not target.session_id:
                try:
                    from flask_jwt_extended import get_jwt
                    claims = get_jwt()
                    if claims: target.session_id = claims.get('session_id')
                except Exception:
                    pass

            if target.execution_time is None or target.execution_time == 0.0:
                import time
                if hasattr(g, 'start_time'):
                    target.execution_time = round((time.time() - g.start_time) * 1000, 2)
    except Exception:
        pass


class AuditRiskAlert(db.Model):
    __tablename__ = 'audit_risk_alerts'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    log_id = db.Column(db.Integer, db.ForeignKey('audit_logs.id', ondelete='CASCADE'), nullable=False)
    risk_score = db.Column(db.Float, default=0.0)
    risk_level = db.Column(db.String(20), default='Low')  # Low, Medium, High, Critical
    triggered_rules = db.Column(db.JSON, default=list)
    suggested_actions = db.Column(db.JSON, default=list)
    status = db.Column(db.String(20), default='Unresolved')  # Unresolved, Resolved, Ignored
    created_at = db.Column(db.DateTime, default=_utc_now)

    organization = db.relationship('Organization', backref='risk_alerts')
    user = db.relationship('User', backref='risk_alerts')
    audit_log = db.relationship('AuditLog', backref='risk_alerts')

class AuditExportLog(db.Model):
    __tablename__ = 'audit_export_logs'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    export_type = db.Column(db.String(20))  # CSV, Excel, PDF
    record_count = db.Column(db.Integer, default=0)
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=_utc_now)

    organization = db.relationship('Organization', backref='export_logs')
    user = db.relationship('User', backref='export_logs')


# Legacy stage models removed/replaced by 8D stage models above

# ============================
# MODULE 6: Knowledge Repository
# ============================
class KnowledgeRepository(db.Model):
    __tablename__ = 'knowledge_repository'
    __table_args__ = (
        db.Index('idx_kr_org_status', 'org_id', 'status'),
        db.Index('idx_kr_project', 'project_id'),
    )
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), unique=True, nullable=False)
    title = db.Column(db.String(255))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    category = db.Column(db.String(20))
    problem_summary = db.Column(db.Text)
    root_cause = db.Column(db.Text)
    solution_summary = db.Column(db.Text)
    kpi_improvement_pct = db.Column(db.Float)
    cost_savings = db.Column(db.Float)
    sop_path = db.Column(db.String(500))
    closure_report_path = db.Column(db.String(500))
    tags = db.Column(db.JSON)
    keywords = db.Column(db.Text)
    embedding = db.Column(Vector(384))  # Vector support enabled for production (Neon)
    archived_at = db.Column(db.DateTime, default=_utc_now)
    status = db.Column(db.String(20), default='Archived')
    
    project_ref = db.relationship('Project', backref=db.backref('knowledge_entry', uselist=False))

# ============================
# MODULE 5: KPI Dashboard Cache
# ============================
class KPIDashboardCache(db.Model):
    __tablename__ = 'kpi_dashboard_cache'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    cache_key = db.Column(db.String(100), unique=True, nullable=False)
    data = db.Column(db.JSON)
    updated_at = db.Column(db.DateTime, default=_utc_now)


# ============================
# MODULE 6: Employee Reward & Leaderboard Models
# ============================

class SuperAdminLog(db.Model):
    __tablename__ = 'super_admin_logs'
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    target_type = db.Column(db.String(50)) # Organization, User, SystemSetting
    target_id = db.Column(db.Integer)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=_utc_now)

    admin = db.relationship('User', backref='super_admin_logs')


# ============================
# MODULE: Enterprise Subscription Management
# ============================


class SOPCategory(db.Model):
    __tablename__ = 'sop_categories'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=_utc_now)

class SOPType(db.Model):
    __tablename__ = 'sop_types'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=_utc_now)

class SOP(db.Model):
    __tablename__ = 'sop_master'
    
    id = db.Column(db.Integer, primary_key=True)
    sop_uid = db.Column(db.String(50), unique=True, nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    process_name = db.Column(db.String(255))
    sop_type = db.Column(db.String(100))
    description = db.Column(db.Text)
    purpose = db.Column(db.Text)
    scope = db.Column(db.Text)
    applicability = db.Column(db.Text)
    responsibilities = db.Column(db.Text)
    
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    effective_date = db.Column(db.Date)
    review_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)
    
    version = db.Column(db.Integer, default=1)
    status = db.Column(db.String(50), default='Draft') # Draft, Under Review, Approved, Active, Archived, Obsolete
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)
    attachments = db.Column(db.JSON, default=[])
    sop_document_path = db.Column(db.String(500))
    preventive_actions = db.Column(db.Text)
    lessons_learned = db.Column(db.Text)
    training_records = db.Column(db.Text)
    
    # Module 6 configuration columns
    due_days = db.Column(db.Integer, default=30)
    pass_percentage = db.Column(db.Integer, default=80)
    time_limit = db.Column(db.Integer, default=30) # in minutes
    max_attempts = db.Column(db.Integer, default=3)
    is_archived = db.Column(db.Boolean, default=False)

    # Relationships
    department = db.relationship('Department', backref=db.backref('sops', lazy=True))
    author = db.relationship('User', foreign_keys=[author_id], backref=db.backref('authored_sops', lazy=True))
    owner = db.relationship('User', foreign_keys=[owner_id], backref=db.backref('owned_sops', lazy=True))
    reviewer = db.relationship('User', foreign_keys=[reviewer_id], backref=db.backref('reviewed_sops', lazy=True))
    approver = db.relationship('User', foreign_keys=[approver_id], backref=db.backref('approved_sops', lazy=True))
    project = db.relationship('Project', backref=db.backref('linked_sops', lazy=True))
    
    steps = db.relationship('SOPStep', backref='sop', lazy=True, cascade="all, delete-orphan")
    approvals = db.relationship('SOPApproval', backref='sop', lazy=True, cascade="all, delete-orphan")
    versions = db.relationship('SOPVersion', backref='sop', lazy=True, cascade="all, delete-orphan")
    trainings = db.relationship('SOPTraining', backref='sop', lazy=True, cascade="all, delete-orphan")

class SOPStep(db.Model):
    __tablename__ = 'sop_steps'
    
    id = db.Column(db.Integer, primary_key=True)
    sop_id = db.Column(db.Integer, db.ForeignKey('sop_master.id', ondelete='CASCADE'), nullable=False)
    step_number = db.Column(db.Integer, nullable=False)
    step_title = db.Column(db.String(255), nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(500))
    video_path = db.Column(db.String(500))
    safety_notes = db.Column(db.Text)
    quality_checkpoints = db.Column(db.Text)

class SOPApproval(db.Model):
    __tablename__ = 'sop_approvals'
    
    id = db.Column(db.Integer, primary_key=True)
    sop_id = db.Column(db.Integer, db.ForeignKey('sop_master.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(50), nullable=False) # Submit, Approve, Reject, Send Back
    comments = db.Column(db.Text)
    signature = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=_utc_now)
    
    user = db.relationship('User', backref=db.backref('sop_approvals', lazy=True))

class SOPVersion(db.Model):
    __tablename__ = 'sop_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    sop_id = db.Column(db.Integer, db.ForeignKey('sop_master.id', ondelete='CASCADE'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    changes_made = db.Column(db.Text)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    changed_date = db.Column(db.DateTime, default=_utc_now)
    approval_date = db.Column(db.DateTime)
    sop_data = db.Column(db.JSON) # Full JSON dump of the SOP and steps
    
    changed_by = db.relationship('User', backref=db.backref('sop_version_changes', lazy=True))

class SOPTraining(db.Model):
    __tablename__ = 'training_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    sop_id = db.Column(db.Integer, db.ForeignKey('sop_master.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_date = db.Column(db.DateTime, default=_utc_now)
    read_status = db.Column(db.Boolean, default=False)
    acknowledgement_status = db.Column(db.Boolean, default=False)
    training_completion_status = db.Column(db.Boolean, default=False)
    assessment_score = db.Column(db.Integer)
    completed_at = db.Column(db.DateTime)
    
    # Module 6 tracking columns
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    due_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='Not Started') # Not Started, In Progress, Acknowledged, Assessment Pending, Completed, Failed, Overdue
    first_opened_at = db.Column(db.DateTime)
    last_viewed_at = db.Column(db.DateTime)
    total_reading_time = db.Column(db.Integer, default=0) # in seconds
    reading_percentage = db.Column(db.Float, default=0.0)
    attempts_left = db.Column(db.Integer, default=3)
    
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('sop_trainings', lazy=True))
    assigned_by = db.relationship('User', foreign_keys=[assigned_by_id], backref=db.backref('assigned_sop_trainings', lazy=True))

class SOPComment(db.Model):
    __tablename__ = 'sop_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    sop_id = db.Column(db.Integer, db.ForeignKey('sop_master.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    comment_type = db.Column(db.String(50), default='General') # General, Feedback, Verification, Review, AdminCorrection
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=_utc_now)
    
    user = db.relationship('User', backref=db.backref('sop_comments', lazy=True))
    sop = db.relationship('SOP', backref=db.backref('comments_list', lazy=True, cascade="all, delete-orphan"))



class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    is_starred = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=_utc_now)
    link = db.Column(db.String(500))
    
    user = db.relationship('User', backref=db.backref('user_notifications', lazy=True, cascade="all, delete-orphan"))


class SOPAcknowledgement(db.Model):
    __tablename__ = 'training_acknowledgements'
    
    id = db.Column(db.Integer, primary_key=True)
    training_id = db.Column(db.Integer, db.ForeignKey('training_assignments.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    statement = db.Column(db.String(500), nullable=False)
    ip_address = db.Column(db.String(100))
    digital_signature = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=_utc_now)
    
    user = db.relationship('User', backref=db.backref('sop_acknowledgements', lazy=True))
    training = db.relationship('SOPTraining', backref=db.backref('acknowledgement_record', uselist=False, lazy=True, cascade="all, delete-orphan"))

class SOPAssessment(db.Model):
    __tablename__ = 'training_assessments'
    
    id = db.Column(db.Integer, primary_key=True)
    sop_id = db.Column(db.Integer, db.ForeignKey('sop_master.id', ondelete='CASCADE'), nullable=False)
    pass_percentage = db.Column(db.Integer, default=80)
    time_limit = db.Column(db.Integer, default=30) # in minutes
    attempts_allowed = db.Column(db.Integer, default=3)
    random_order = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=_utc_now)
    
    sop = db.relationship('SOP', backref=db.backref('assessment_config', uselist=False, lazy=True, cascade="all, delete-orphan"))

class SOPAssessmentQuestion(db.Model):
    __tablename__ = 'assessment_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    sop_id = db.Column(db.Integer, db.ForeignKey('sop_master.id', ondelete='CASCADE'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False) # MCQ, TF, MS
    options = db.Column(db.JSON)
    correct_answers = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=_utc_now)
    
    sop = db.relationship('SOP', backref=db.backref('assessment_questions', lazy=True, cascade="all, delete-orphan"))

class SOPAssessmentResult(db.Model):
    __tablename__ = 'assessment_results'
    
    id = db.Column(db.Integer, primary_key=True)
    training_id = db.Column(db.Integer, db.ForeignKey('training_assignments.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    attempt_number = db.Column(db.Integer, nullable=False)
    result = db.Column(db.String(50), nullable=False) # Pass, Fail
    answers_submitted = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=_utc_now)
    
    user = db.relationship('User', backref=db.backref('assessment_results', lazy=True))
    training = db.relationship('SOPTraining', backref=db.backref('assessment_results', lazy=True, cascade="all, delete-orphan"))


class SOPAuditReport(db.Model):
    __tablename__ = 'training_audit_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    generated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    report_type = db.Column(db.String(100), nullable=False) # Training Audit, Compliance
    pdf_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=_utc_now)
    
    generated_by = db.relationship('User', backref=db.backref('audit_reports', lazy=True))

class SOPArchive(db.Model):
    __tablename__ = 'training_archive'
    
    id = db.Column(db.Integer, primary_key=True)
    sop_id = db.Column(db.Integer, db.ForeignKey('sop_master.id', ondelete='CASCADE'), nullable=False)
    archived_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    archived_at = db.Column(db.DateTime, default=_utc_now)
    reason = db.Column(db.Text)
    
    sop = db.relationship('SOP', backref=db.backref('archive_record', uselist=False, lazy=True, cascade="all, delete-orphan"))
    archived_by = db.relationship('User', backref=db.backref('archives_created', lazy=True))

class SOPNotification(db.Model):
    __tablename__ = 'training_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    training_id = db.Column(db.Integer, db.ForeignKey('training_assignments.id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notification_type = db.Column(db.String(100), nullable=False) # New Assignment, Due Reminder, Overdue Reminder, Failed, Completed
    message = db.Column(db.Text, nullable=False)
    is_sent = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=_utc_now)
    
    user = db.relationship('User', backref=db.backref('sop_notifications', lazy=True))
    training = db.relationship('SOPTraining', backref=db.backref('notifications', lazy=True, cascade="all, delete-orphan"))


class ComplianceStandard(db.Model):
    """One row per compliance framework per organisation.
    Created on demand via GET /api/admin/compliance/standards (auto-seed).
    """
    __tablename__ = 'compliance_standard_records'

    id                = db.Column(db.Integer, primary_key=True)
    org_id            = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    standard_name     = db.Column(db.String(100), nullable=False)   # "ISO 9001:2015"
    standard_code     = db.Column(db.String(50),  nullable=False)   # "iso9001"
    description       = db.Column(db.String(255))                   # "Quality Management System"
    icon              = db.Column(db.String(50), default='award')   # Lucide icon name

    # Enable/disable toggle
    is_enabled        = db.Column(db.Boolean, default=False)

    # Certificate fields (filled in by the admin)
    certificate_number = db.Column(db.String(100))
    issue_date         = db.Column(db.Date)
    expiry_date        = db.Column(db.Date)
    last_audit_date    = db.Column(db.Date)
    next_audit_date    = db.Column(db.Date)
    audit_score        = db.Column(db.Integer)          # 0-100
    owner              = db.Column(db.String(100))      # department / person
    registrar_body     = db.Column(db.String(100))      # e.g. "BSI Group"
    lead_auditor       = db.Column(db.String(100))
    framework_scope    = db.Column(db.Text)
    risk_level         = db.Column(db.String(20))       # low / medium / high
    cert_file_url      = db.Column(db.String(500))

    # Status derived & stored: certified / pending / expired / not_configured
    status            = db.Column(db.String(30), default='not_configured')

    created_at        = db.Column(db.DateTime, default=_utc_now)
    updated_at        = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)

    __table_args__ = (
        db.UniqueConstraint('org_id', 'standard_code', name='uq_org_standard_code'),
    )

    def compute_status(self):
        """Derive status from certificate data and dates."""
        from datetime import date
        today = date.today()
        if not self.certificate_number:
            return 'not_configured'
        if self.expiry_date and self.expiry_date < today:
            return 'expired'
        if self.issue_date and self.certificate_number:
            return 'certified'
        return 'pending'

    def to_dict(self):
        return {
            'id':                 self.id,
            'org_id':             self.org_id,
            'standard_name':      self.standard_name,
            'standard_code':      self.standard_code,
            'description':        self.description,
            'icon':               self.icon,
            'is_enabled':         self.is_enabled,
            'certificate_number': self.certificate_number,
            'issue_date':         self.issue_date.isoformat()       if self.issue_date       else None,
            'expiry_date':        self.expiry_date.isoformat()      if self.expiry_date      else None,
            'last_audit_date':    self.last_audit_date.isoformat()  if self.last_audit_date  else None,
            'next_audit_date':    self.next_audit_date.isoformat()  if self.next_audit_date  else None,
            'audit_score':        self.audit_score,
            'owner':              self.owner,
            'registrar_body':     self.registrar_body,
            'lead_auditor':       self.lead_auditor,
            'framework_scope':    self.framework_scope,
            'risk_level':         self.risk_level,
            'cert_file_url':      self.cert_file_url,
            'status':             self.status,
            'created_at':         self.created_at.isoformat() if self.created_at else None,
            'updated_at':         self.updated_at.isoformat() if self.updated_at else None,
        }

# Domain & Backward-Compatibility Aliases
SOPMaster = SOP
