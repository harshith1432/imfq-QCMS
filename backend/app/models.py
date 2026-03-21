from datetime import datetime
from . import db

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    users = db.relationship('User', backref='role', lazy=True)

class Organization(db.Model):
    __tablename__ = 'organizations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    industry = db.Column(db.String(100))
    admin_name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    users = db.relationship('User', backref='organization', lazy=True)
    departments = db.relationship('Department', backref='organization', lazy=True)
    projects = db.relationship('Project', backref='organization', lazy=True)

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    users_in_dept = db.relationship('User', backref='dept', lazy=True)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    full_name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True, nullable=False)
    hashed_password = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    is_active = db.Column(db.Boolean, default=True)
    is_temp_password = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='Active') # Active, Inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    deactivated_at = db.Column(db.DateTime)

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_uid = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    category = db.Column(db.String(20))  # Safety, Quality, Productivity, Cost
    team_leader_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    deadline = db.Column(db.Date, nullable=True)
    current_stage = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='In Progress')
    start_date = db.Column(db.Date, default=datetime.utcnow)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    members = db.relationship('User', secondary='project_members', backref='projects')
    workflow = db.relationship('ProjectWorkflow', backref='project', lazy=True, cascade="all, delete-orphan")
    stage_tracker = db.relationship('ProjectStageTracker', backref='project', lazy=True, cascade="all, delete-orphan")

    # Explicit relationships for foreign keys
    department = db.relationship('Department', backref='projects_in_dept', lazy=True)
    creator = db.relationship('User', foreign_keys=[creator_id], backref='created_projects')
    team_leader = db.relationship('User', foreign_keys=[team_leader_id], backref='led_projects')

class ProjectMember(db.Model):
    __tablename__ = 'project_members'
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)

# ============================
# MODULE 3: Stage Tracker 
# ============================
class ProjectStageTracker(db.Model):
    """Master tracker: 8 rows per project, one per stage."""
    __tablename__ = 'project_stage_tracker'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_number = db.Column(db.Integer, nullable=False)  # 1-8
    status = db.Column(db.String(20), default='Not Started')  # Not Started, In Progress, Completed
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    __table_args__ = (
        db.UniqueConstraint('project_id', 'stage_number', name='uq_project_stage'),
    )

class ProjectWorkflow(db.Model):
    """Stores stage data (JSONB) for each stage of a project."""
    __tablename__ = 'project_workflow'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer, nullable=False)
    data = db.Column(db.JSON, default={})
    completed_at = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ============================
# STAGE-SPECIFIC MODELS (8-STAGE WORKFLOW)
# ============================

class Stage1Problem(db.Model):
    __tablename__ = 'stage_1_problem'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    problem_statement = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    evidence = db.Column(db.Text)
    location = db.Column(db.String(255))
    frequency_of_occurrence = db.Column(db.String(100))
    initial_impact = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_ref = db.relationship('Project', backref=db.backref('stage1_problem', uselist=False))

class Stage2Data(db.Model):
    __tablename__ = 'stage_2_data'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    raw_data = db.Column(db.JSON)
    baseline_kpi = db.Column(db.Float)
    data_method = db.Column(db.String(100))
    findings_summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_ref = db.relationship('Project', backref=db.backref('stage2_data', uselist=False))
class Stage4Solution(db.Model):
    __tablename__ = 'stage_4_solution'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    budget_required = db.Column(db.Float, default=0.0)
    estimated_roi = db.Column(db.Float, default=0.0)
    resource_plan = db.Column(db.Text)
    kpi_targets = db.Column(db.JSON)
    implementation_plan = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_ref = db.relationship('Project', backref=db.backref('stage4_solution', uselist=False))

class Stage5Approval(db.Model):
    __tablename__ = 'stage_5_approval'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer, default=5)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(20), default='Pending')
    decision = db.Column(db.String(20)) # Approve / Reject
    comments = db.Column(db.Text)
    decided_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_ref = db.relationship('Project', backref=db.backref('stage5_approval', uselist=False))

class KPIMetric(db.Model):
    __tablename__ = 'kpi_metrics'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    cost_saving = db.Column(db.Float, default=0.0)
    productivity_gain = db.Column(db.Float, default=0.0)
    quality_index = db.Column(db.Float, default=0.0)
    safety_score = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    target_table = db.Column(db.String(100))
    target_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='logs')

class Stage3RCA(db.Model):
    __tablename__ = 'stage_3_rca'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    fishbone_data = db.Column(db.JSON)
    why_analysis = db.Column(db.JSON)
    pareto_data = db.Column(db.JSON)
    histogram_data = db.Column(db.JSON)
    control_chart_data = db.Column(db.JSON)
    scatter_data = db.Column(db.JSON)
    checksheet_data = db.Column(db.JSON)
    flowchart_data = db.Column(db.JSON)
    fives_audit_data = db.Column(db.JSON)
    pokayoke_data = db.Column(db.JSON)
    root_cause_summary = db.Column(db.Text)
    rca_validation_note = db.Column(db.Text)  # Facilitator must fill this to unlock Stage 3→4
    facilitator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    project_ref = db.relationship('Project', backref=db.backref('stage3_rca', lazy=True))

class Stage6Implementation(db.Model):
    __tablename__ = 'stage_6_implementation'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    action_plan = db.Column(db.Text)
    actual_cost = db.Column(db.Float, default=0.0)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    execution_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_ref = db.relationship('Project', backref=db.backref('stage6_implementation', uselist=False))

class Stage7Impact(db.Model):
    __tablename__ = 'stage_7_impact'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    baseline_data = db.Column(db.JSON)
    final_data = db.Column(db.JSON)
    kpi_improvement_pct = db.Column(db.Float)
    cost_savings = db.Column(db.Float)
    productivity_gain = db.Column(db.Float)
    impact_vouchers = db.Column(db.Text)
    status = db.Column(db.String(20), default='Pending')  # Pending / Approved — Facilitator only
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_ref = db.relationship('Project', backref=db.backref('stage7_impact', lazy=True))

class Stage8Standardization(db.Model):
    __tablename__ = 'stage_8_standardization'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    sop_url = db.Column(db.String(500))
    training_records = db.Column(db.JSON)
    preventive_actions = db.Column(db.Text)
    lessons_learned = db.Column(db.Text)
    facilitator_validation = db.Column(db.Boolean, default=False)
    admin_closure = db.Column(db.Boolean, default=False)
    closure_report_path = db.Column(db.String(500))
    final_pdf_report = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_ref = db.relationship('Project', backref=db.backref('stage8_standardization', uselist=False))

# ============================
# MODULE 6: Knowledge Repository
# ============================
class KnowledgeRepository(db.Model):
    __tablename__ = 'knowledge_repository'
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
    archived_at = db.Column(db.DateTime, default=datetime.utcnow)
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
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================
# MODULE 7: Facilitator Notes
# ============================
class FacilitatorNote(db.Model):
    __tablename__ = 'facilitator_notes'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_number = db.Column(db.Integer, nullable=False)
    note_text = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project_ref = db.relationship('Project', backref=db.backref('facilitator_notes', lazy=True))
    author = db.relationship('User', backref='facilitator_notes')
