from datetime import datetime
from app import db, bcrypt
import os
from sqlalchemy.dialects.postgresql import ARRAY

# Check if running locally
database_url = os.environ.get('DATABASE_URL', '')
is_local = '127.0.0.1' in database_url or 'localhost' in database_url or not database_url

try:
    from pgvector.sqlalchemy import Vector
except Exception:
    class LocalVector(db.TypeDecorator):
        impl = ARRAY(db.Float)
        cache_ok = True
        
        class comparator_factory(ARRAY.Comparator):
            def cosine_distance(self, other):
                from sqlalchemy import literal
                return literal(0.0)
                
    Vector = lambda dim: LocalVector

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    users = db.relationship('User', backref='role', lazy=True)

class Organization(db.Model):
    __tablename__ = 'organizations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    industry = db.Column(db.String(100))
    admin_name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    logo_url = db.Column(db.String(500))
    favicon_url = db.Column(db.String(500))
    primary_color = db.Column(db.String(10), default='#2563eb')
    timezone = db.Column(db.String(50), default='UTC')
    date_format = db.Column(db.String(20), default='DD/MM/YYYY')
    currency = db.Column(db.String(10), default='INR')

    language = db.Column(db.String(10), default='en')
    
    # Address Info
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    country = db.Column(db.String(100))
    zip_code = db.Column(db.String(20))
    
    # Operational Policies
    auto_archive = db.Column(db.Boolean, default=True)
    notifications_enabled = db.Column(db.Boolean, default=True)
    maintenance_mode = db.Column(db.Boolean, default=False)
    session_timeout = db.Column(db.Integer, default=60)
    data_retention_days = db.Column(db.Integer, default=365)
    
    # Compliance
    compliance_standards = db.Column(db.JSON, default=[]) # e.g. ["ISO 9001", "AS9100"]
    
    # SaaS Subscription
    subscription_plan = db.Column(db.String(50), default='Professional', index=True) # Starter, Professional, Enterprise
    subscription_status = db.Column(db.String(20), default='Trialing', index=True) # Trialing, Active, Expired, Canceled
    trial_ends_at = db.Column(db.DateTime, index=True)
    max_users = db.Column(db.Integer, default=500)
    is_white_label = db.Column(db.Boolean, default=False)
    multi_plant = db.Column(db.Boolean, default=False)
    api_access = db.Column(db.Boolean, default=False)
    api_key = db.Column(db.String(255), unique=True, nullable=True)
    
    # Compliance & Licensing
    gst_number = db.Column(db.String(50), nullable=True)
    pan_number = db.Column(db.String(50), nullable=True)
    udyam_number = db.Column(db.String(50), nullable=True)
    org_scale = db.Column(db.String(50), default='Small') # Micro, Small, Medium, Large
    website = db.Column(db.String(255), nullable=True)
    org_code = db.Column(db.String(100), unique=True, nullable=True)
    license_number = db.Column(db.String(100), unique=True, nullable=True)
    storage_limit_mb = db.Column(db.Float, default=10240.0) # Default 10 GB
    enabled_modules = db.Column(db.JSON, default=list) # List of enabled modules, e.g. ["7-qc-tools", "spc-control-charts"]
    state = db.Column(db.String(100), nullable=True)
    is_deleted = db.Column(db.Boolean, default=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)
    # Marks this as an internal platform/system org (e.g. SuperAdmin's org).
    # Platform orgs are NEVER shown in tenant listings, subscriptions, or analytics.
    is_platform_org = db.Column(db.Boolean, default=False, nullable=False, server_default='false', index=True)

    license_start_date = db.Column(db.DateTime, default=datetime.utcnow)
    license_expiry_date = db.Column(db.DateTime, nullable=True, index=True)
    trial_extension_count = db.Column(db.Integer, default=0, nullable=False, server_default='0')
    storage_used_mb = db.Column(db.Float, default=0.0)
    
    # 8-Stage Workflow Template (org-level customization)
    stages_config = db.Column(db.JSON, nullable=True)
    applied_template_version = db.Column(db.Integer, default=1, nullable=False)
    has_pending_template_update = db.Column(db.Boolean, default=False, nullable=False)
    
    # Login Options: list of field keys allowed as login identifier
    # e.g. ["email", "phone", "employee_id"]
    # "email" is always present as the system default
    login_options = db.Column(db.JSON, default=lambda: ["email"])
    security_settings = db.Column(db.JSON, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    users = db.relationship('User', backref='organization', lazy=True)
    departments = db.relationship('Department', backref='organization', lazy=True)
    plants = db.relationship('Plant', backref='organization', lazy=True)
    projects = db.relationship('Project', backref='organization', lazy=True)

    DEFAULT_STAGES_CONFIG = [
        {
            "stage_id": 1, "original_id": 1,
            "title": "S0/S1 Plan & Establish Team", "icon": "target",
            "sections": [
                {"id": "s1_project_team", "type": "table", "label": "Project Team", "order": 1},
                {"id": "s1_problem_background", "type": "textarea", "label": "Problem Background (5W2H)", "order": 2},
                {"id": "s1_current_performance", "type": "table", "label": "Current Performance", "order": 3},
                {"id": "s1_justification", "type": "textarea", "label": "Justification", "order": 4},
                {"id": "s1_emergency_response", "type": "textarea", "label": "Emergency Response", "order": 5},
                {"id": "s1_theme_target_schedule", "type": "table", "label": "Theme, Target & Schedule", "order": 6},
            ]
        },
        {
            "stage_id": 2, "original_id": 2,
            "title": "S2 Define Problem", "icon": "database",
            "sections": [
                {"id": "s2_problem_definition", "type": "textarea", "label": "Problem Definition", "order": 1},
                {"id": "s2_std_verification", "type": "table", "label": "Standard Verification", "order": 2},
                {"id": "s2_observations", "type": "table", "label": "Data Collection & Observations (Gemba)", "order": 3},
                {"id": "s2_stratification", "type": "stratification", "label": "Stratification", "order": 4},
                {"id": "s2_pareto", "type": "pareto", "label": "Pareto Analysis", "order": 5},
                {"id": "s2_five_g", "type": "table", "label": "5G Verification", "order": 6},
                {"id": "s2_check_sheet", "type": "check_sheet", "label": "Check Sheet", "order": 7},
            ]
        },
        {
            "stage_id": 3, "original_id": 3,
            "title": "S3 Interim Containment", "icon": "git-branch",
            "sections": [
                {"id": "s3_brainstorm", "type": "multi_text", "label": "Brainstormed Causes", "order": 1},
                {"id": "s3_fishbone_pre", "type": "fishbone", "label": "Fishbone Diagram (Pre-Verification)", "order": 2},
                {"id": "s3_verification", "type": "verification_table", "label": "Cause Verification Table", "order": 3},
                {"id": "s3_fishbone_post", "type": "fishbone", "label": "Fishbone Diagram (Post-Verification)", "order": 4},
                {"id": "s3_hypothesis", "type": "table", "label": "Hypothesis Testing", "order": 5},
                {"id": "s3_pareto_verification", "type": "pareto", "label": "Run-Chart / Pareto Verification", "order": 6},
                {"id": "s3_root_cause_ident", "type": "textarea", "label": "Root Cause Identification", "order": 7},
                {"id": "s3_verif_checklist", "type": "check_sheet", "label": "Verification Checklist", "order": 8},
            ]
        },
        {
            "stage_id": 4, "original_id": 4,
            "title": "S4 Determine Root Causes", "icon": "search",
            "sections": [
                {"id": "s4_verified_causes", "type": "table", "label": "Root Causes", "order": 1},
                {"id": "s4_why_why_analysis", "type": "table", "label": "Why-Why Analysis (5-Why)", "order": 2},
                {"id": "s4_hypothesis_testing", "type": "table", "label": "Hypothesis Testing", "order": 3},
                {"id": "s4_good_bad_comparison", "type": "table", "label": "Good vs Bad Comparison", "order": 4},
                {"id": "s4_statistical_validation", "type": "table", "label": "Statistical Validation", "order": 5},
                {"id": "s4_data_reconfirmation", "type": "table", "label": "Data Reconfirmation", "order": 6},
                {"id": "s4_root_cause_register", "type": "table", "label": "Root Cause Register", "order": 7},
                {"id": "s4_root_cause_ranking", "type": "table", "label": "Root Cause Ranking", "order": 8},
            ]
        },
        {
            "stage_id": 5, "original_id": 5,
            "title": "S5 Choose Permanent Corrections", "icon": "lightbulb",
            "sections": [
                {"id": "s5_root_cause_mapping", "type": "table", "label": "Root Cause Mapping", "order": 1},
                {"id": "s5_solution_brainstorming", "type": "table", "label": "Solution Brainstorming", "order": 2},
                {"id": "s5_solution_evaluation", "type": "table", "label": "Solution Evaluation Matrix", "order": 3},
                {"id": "s5_cost_benefit_analysis", "type": "table", "label": "Cost Benefit Analysis", "order": 4},
                {"id": "s5_side_effect_analysis", "type": "table", "label": "Side Effect Analysis", "order": 5},
                {"id": "s5_pilot_solution_verification", "type": "table", "label": "Pilot Solution Verification", "order": 6},
                {"id": "s5_action_plan_3w1h", "type": "table", "label": "Action Plan (3W1H)", "order": 7},
                {"id": "s5_resource_planning", "type": "table", "label": "Resource Planning", "order": 8},
            ]
        },
        {
            "stage_id": 6, "original_id": 6,
            "title": "S6 Implement Corrective Actions", "icon": "settings-2",
            "sections": [
                {"id": "s6_countermeasures", "type": "table", "label": "Countermeasures", "order": 1},
                {"id": "s6_tasks", "type": "table", "label": "Countermeasure Task Assignments", "order": 2},
                {"id": "s6_resource_deployment", "type": "table", "label": "Resource Deployment", "order": 3},
                {"id": "s6_change_management", "type": "table", "label": "Change Management", "order": 4},
                {"id": "s6_risk_resistance", "type": "table", "label": "Risk & Resistance Management", "order": 5},
                {"id": "s6_side_effect_analysis", "type": "table", "label": "Side Effect Analysis", "order": 6},
                {"id": "s6_implementation_evidence", "type": "table", "label": "Implementation Evidence", "order": 7},
                {"id": "s6_communication", "type": "table", "label": "Communication Log", "order": 8},
                {"id": "s6_training", "type": "table", "label": "Training & Awareness", "order": 9},
                {"id": "s6_readiness_verification", "type": "table", "label": "Readiness Verification", "order": 10},
            ]
        },
        {
            "stage_id": 7, "original_id": 7,
            "title": "S7 Take Preventive Measures", "icon": "trending-up",
            "sections": [
                {"id": "s7_kpi_verification", "type": "table", "label": "KPI Verification", "order": 1},
                {"id": "s7_before_vs_after", "type": "table", "label": "Before vs After Analysis", "order": 2},
                {"id": "s7_statistical_validation", "type": "table", "label": "Statistical Validation", "order": 3},
                {"id": "s7_benefit_realization", "type": "table", "label": "Benefit Realization & Savings", "order": 4},
                {"id": "s7_roi_validation", "type": "table", "label": "ROI Validation", "order": 5},
                {"id": "s7_sustainability_check", "type": "table", "label": "Sustainability Check", "order": 6},
                {"id": "s7_side_effect_verification", "type": "table", "label": "Side Effect Verification", "order": 7},
                {"id": "s7_lessons_implementation", "type": "table", "label": "Lessons Implementation", "order": 8},
            ]
        },
        {
            "stage_id": 8, "original_id": 8,
            "title": "S8 Congratulate Team & Closure", "icon": "award",
            "sections": [
                {"id": "s8_standardization", "type": "table", "label": "Standardization & SOP", "order": 1},
                {"id": "s8_training_adoption", "type": "table", "label": "Training & Adoption", "order": 2},
                {"id": "s8_horizontal_deployment", "type": "table", "label": "Horizontal Deployment", "order": 3},
                {"id": "s8_lessons_learned", "type": "table", "label": "Lessons Learned", "order": 4},
                {"id": "s8_benefits_summary", "type": "table", "label": "Benefits Summary", "order": 5},
                {"id": "s8_remaining_opportunities", "type": "table", "label": "Remaining Opportunities", "order": 6},
                {"id": "s8_knowledge_repository", "type": "table", "label": "Knowledge Repository", "order": 7},
                {"id": "s8_team_recognition", "type": "table", "label": "Team Recognition", "order": 8},
                {"id": "s8_project_closure", "type": "table", "label": "Project Closure", "order": 9},
            ]
        },
    ]

    def get_stages_config(self):
        """Return org-customised stage config, or Super Admin global default, or built-in defaults."""
        import copy
        ps = PlatformSettings.query.first()
        base_defaults = (ps and ps.global_stages_config) or self.DEFAULT_STAGES_CONFIG
        
        raw = self.stages_config
        if raw and len(raw) > 0:
            # Back-fill sections from defaults for stages that don't have them yet
            default_map = {d["original_id"]: d for d in base_defaults}
            result = []
            for stage in raw:
                s = copy.deepcopy(stage)
                oid = s.get("original_id", s.get("stage_id", 1))
                default_stage = default_map.get(oid, {})
                if not s.get("sections") or len(s.get("sections", [])) < len(default_stage.get("sections", [])):
                    s["sections"] = copy.deepcopy(
                        default_stage.get("sections", [])
                    )
                result.append(s)
            return result
        return copy.deepcopy(base_defaults)

class Plant(db.Model):
    __tablename__ = 'plants'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    departments = db.relationship('Department', backref='plant', lazy=True)
    users = db.relationship('User', backref='plant', lazy=True)

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plants.id'), nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    users_in_dept = db.relationship('User', backref='dept', lazy=True)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True, index=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plants.id'), nullable=True, index=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(255))
    employee_id = db.Column(db.String(100), index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    hashed_password = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_temp_password = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255), unique=True, nullable=True)
    reset_token = db.Column(db.String(255), unique=True, nullable=True)
    otp_token = db.Column(db.String(10), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='Active', index=True) # Active, Inactive
    profile_picture = db.Column(db.String(255), nullable=True)
    banner_image = db.Column(db.String(255), nullable=True)
    language = db.Column(db.String(10), default='en')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_login = db.Column(db.DateTime, index=True)
    deactivated_at = db.Column(db.DateTime)
    custom_fields = db.Column(db.JSON, nullable=True)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.hashed_password, password)

    @property
    def org(self):
        return self.organization

class EmailVerification(db.Model):
    __tablename__ = 'email_verifications'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    otp = db.Column(db.String(6), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PhoneVerification(db.Model):
    __tablename__ = 'phone_verifications'
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(50), unique=True, nullable=False)
    otp = db.Column(db.String(6), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_uid = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    category = db.Column(db.String(20))  # Quality, Cost, Delivery, Safety, Morale, Environment, Productivity
    team_leader_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    facilitator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    deadline = db.Column(db.Date, nullable=True)
    current_stage = db.Column(db.Integer, default=1)
    status = db.Column(db.String(50), default='In Progress')
    start_date = db.Column(db.Date, default=datetime.utcnow)
    end_date = db.Column(db.Date)
    
    # New Initialization Fields
    work_area = db.Column(db.String(255))
    plant = db.Column(db.String(255))
    project_source = db.Column(db.String(100))
    reference_number = db.Column(db.String(100))
    sponsor = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    members = db.relationship('User', secondary='project_members', backref='projects')
    workflow = db.relationship('ProjectWorkflow', backref='project', lazy=True, cascade="all, delete-orphan")
    stage_tracker = db.relationship('ProjectStageTracker', backref='project', lazy=True, cascade="all, delete-orphan")

    # Explicit relationships for foreign keys
    department = db.relationship('Department', backref='projects_in_dept', lazy=True)
    creator = db.relationship('User', foreign_keys=[creator_id], backref='created_projects')
    team_leader = db.relationship('User', foreign_keys=[team_leader_id], backref='led_projects')
    facilitator = db.relationship('User', foreign_keys=[facilitator_id], backref='facilitated_projects')

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
    template_snapshot = db.Column(db.JSON, nullable=True)
    completed_at = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProjectMeeting(db.Model):
    __tablename__ = 'project_meetings'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer, nullable=False)  # 1 to 8
    title = db.Column(db.String(255), nullable=False)
    meeting_type = db.Column(db.String(50), nullable=False)  # 'online' or 'offline'
    scheduled_at = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    url = db.Column(db.String(500), nullable=True)  # only for 'online'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship('Project', backref=db.backref('meetings', lazy=True, cascade="all, delete-orphan"))

# ============================
# STAGE-SPECIFIC MODELS (8D WORKFLOW & 7 QC TOOLS)
# ============================

class Stage1ProblemDefinitionProjectInitiation(db.Model):
    __tablename__ = 'stage_1_problem_definition_project_initiation'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, unique=True)
    
    # --- New Stage 1 Sections (Stored as JSON) ---
    project_team = db.Column(db.JSON)
    problem_5w2h = db.Column(db.JSON)
    current_performance = db.Column(db.JSON)
    justification = db.Column(db.JSON)
    emergency_response = db.Column(db.JSON)
    theme_target_schedule = db.Column(db.JSON)
    
    # --- Approvals ---
    facilitator_approved = db.Column(db.Boolean, default=False)
    facilitator_approver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    facilitator_approved_at = db.Column(db.DateTime)
    facilitator_comments = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project_ref = db.relationship('Project', backref=db.backref('stage1_identification', uselist=False))

    # --- Legacy Properties for Backward Compatibility ---
    @property
    def problem_statement(self):
        return self.project_title or ""

    @problem_statement.setter
    def problem_statement(self, val):
        self.project_title = val

    @property
    def description(self):
        return self.policy_reference or ""

    @description.setter
    def description(self, val):
        self.policy_reference = val

    @property
    def initial_impact(self):
        return self.business_impact or ""

    @initial_impact.setter
    def initial_impact(self, val):
        self.business_impact = val

    @property
    def is_approved(self):
        return self.management_approved or False

    @is_approved.setter
    def is_approved(self, val):
        self.management_approved = val

    @property
    def tl_comments(self):
        return self.facilitator_comments or ""

    @tl_comments.setter
    def tl_comments(self, val):
        self.facilitator_comments = val

    @property
    def data(self):
        return {
            "problem_statement": self.project_title or "",
            "description": self.policy_reference or "",
            "initial_impact": self.business_impact or "",
            "team_name": self.team_name or "",
            "team_members": self.team_members or [],
            "competency_skills": self.competency_skills or [],
        }

class Stage2ObservationDataCollection(db.Model):
    __tablename__ = 'stage_2_observation_data_collection'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, unique=True)
    
    process_observation = db.Column(db.JSON)
    standard_verification = db.Column(db.JSON)
    data_collection = db.Column(db.JSON)
    stratification = db.Column(db.JSON)
    pareto = db.Column(db.JSON)
    five_g = db.Column(db.JSON)
    current_state = db.Column(db.JSON)

    reviewer_approved = db.Column(db.Boolean, default=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewer_approved_at = db.Column(db.DateTime)
    reviewer_comments = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_ref = db.relationship('Project', backref=db.backref('stage2_observation', uselist=False))

class Stage3CauseIdentification(db.Model):
    __tablename__ = 'stage_3_cause_identification'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, unique=True)
    
    brainstorming = db.Column(db.JSON)
    fishbone_l1 = db.Column(db.JSON)
    fishbone_l2 = db.Column(db.JSON)
    cause_register = db.Column(db.JSON)
    cause_prioritization = db.Column(db.JSON)
    cause_verification = db.Column(db.JSON)
    fishbone_l3 = db.Column(db.JSON)

    facilitator_approved = db.Column(db.Boolean, default=False)
    facilitator_approver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    facilitator_approved_at = db.Column(db.DateTime)
    facilitator_comments = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_ref = db.relationship('Project', backref=db.backref('stage3_causes', uselist=False))

class Stage4RootCauseAnalysisVerification(db.Model):
    __tablename__ = 'stage_4_root_cause_analysis_verification'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, unique=True)
    
    verified_causes = db.Column(db.JSON)
    hypothesis_testing = db.Column(db.JSON)
    good_vs_bad = db.Column(db.JSON)
    statistical_validation = db.Column(db.JSON)
    data_reconfirmation = db.Column(db.JSON)
    why_why_analysis = db.Column(db.JSON)
    root_cause_register = db.Column(db.JSON)
    root_cause_ranking = db.Column(db.JSON)

    reviewer_approved = db.Column(db.Boolean, default=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewer_approved_at = db.Column(db.DateTime)
    reviewer_comments = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_ref = db.relationship('Project', backref=db.backref('stage4_root_causes', uselist=False))

class Stage5CountermeasurePlanningSolutionDevelopment(db.Model):
    __tablename__ = 'stage_5_countermeasure_planning_solution_development'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, unique=True)
    
    root_cause_mapping = db.Column(db.JSON)
    solution_brainstorming = db.Column(db.JSON)
    solution_evaluation = db.Column(db.JSON)
    cost_benefit_analysis = db.Column(db.JSON)
    side_effect_analysis = db.Column(db.JSON)
    pilot_solution_verification = db.Column(db.JSON)
    action_plan_3w1h = db.Column(db.JSON)
    resource_planning = db.Column(db.JSON)

    # Added RCA Workspace Fields for Stage 5
    fishbone_data = db.Column(db.JSON)
    why_analysis = db.Column(db.JSON)
    pareto_data = db.Column(db.JSON)
    histogram_data = db.Column(db.JSON)
    control_chart_data = db.Column(db.JSON)
    scatter_data = db.Column(db.JSON)
    checksheet_data = db.Column(db.JSON)
    root_cause_summary = db.Column(db.Text)
    rca_validation_note = db.Column(db.Text)
    facilitator_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    reviewer_approved = db.Column(db.Boolean, default=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewer_approved_at = db.Column(db.DateTime)
    reviewer_comments = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_ref = db.relationship('Project', backref=db.backref('stage5_countermeasures', uselist=False))

class Stage6ImplementationChangeManagement(db.Model):
    __tablename__ = 'stage_6_implementation_change_management'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, unique=True)
    
    implementation_execution = db.Column(db.JSON)
    task_management = db.Column(db.JSON)
    resource_deployment = db.Column(db.JSON)
    change_management = db.Column(db.JSON)
    risk_resistance = db.Column(db.JSON)
    training_awareness = db.Column(db.JSON)
    communication_log = db.Column(db.JSON)
    implementation_evidence = db.Column(db.JSON)
    readiness_verification = db.Column(db.JSON)

    reviewer_approved = db.Column(db.Boolean, default=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewer_approved_at = db.Column(db.DateTime)
    reviewer_comments = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_ref = db.relationship('Project', backref=db.backref('stage6_implementation', uselist=False))

class Stage7PerformanceVerificationBenefitsRealization(db.Model):
    __tablename__ = 'stage_7_performance_verification_benefits_realization'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, unique=True)
    
    kpi_verification = db.Column(db.JSON)
    before_vs_after = db.Column(db.JSON)
    statistical_validation = db.Column(db.JSON)
    benefit_realization = db.Column(db.JSON)
    roi_validation = db.Column(db.JSON)
    sustainability_check = db.Column(db.JSON)
    side_effect_verification = db.Column(db.JSON)
    lessons_implementation = db.Column(db.JSON)

    # Added Fields for Stage 7
    action_plan = db.Column(db.JSON)
    budget_required = db.Column(db.Float, default=0.0)

    reviewer_approved = db.Column(db.Boolean, default=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewer_approved_at = db.Column(db.DateTime)
    reviewer_comments = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_ref = db.relationship('Project', backref=db.backref('stage7_verification', uselist=False))

class Stage8StandardizationKnowledgeSharingProjectClosure(db.Model):
    __tablename__ = 'stage_8_standardization_knowledge_sharing_project_closure'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, unique=True)
    
    standardization = db.Column(db.JSON)
    training_adoption = db.Column(db.JSON)
    horizontal_deployment = db.Column(db.JSON)
    lessons_learned = db.Column(db.JSON)
    benefits_summary = db.Column(db.JSON)
    remaining_opportunities = db.Column(db.JSON)
    knowledge_repository = db.Column(db.JSON)
    team_recognition = db.Column(db.JSON)
    project_closure = db.Column(db.JSON)

    # Added Fields for Stage 8 / Impact Statistics
    baseline_data = db.Column(db.JSON)
    final_data = db.Column(db.JSON)
    results_data = db.Column(db.JSON)
    sop_details = db.Column(db.JSON)
    training_records = db.Column(db.JSON)
    preventive_actions = db.Column(db.JSON)
    impact_vouchers = db.Column(db.JSON)
    
    kpi_improvement_pct = db.Column(db.Float, default=0.0)
    cost_savings = db.Column(db.Float, default=0.0)
    productivity_gain = db.Column(db.Float, default=0.0)
    actual_cost = db.Column(db.Float, default=0.0)
    
    status = db.Column(db.String(20), default='Pending')
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    facilitator_validation = db.Column(db.Boolean, default=False)
    admin_closure = db.Column(db.Boolean, default=False)

    final_approval = db.Column(db.Boolean, default=False)
    final_approval_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    final_approval_at = db.Column(db.DateTime)
    final_comments = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_ref = db.relationship('Project', backref=db.backref('stage8_closure', uselist=False))

# --- Normalized 7 QC Tools Tables ---

class QCCheckSheet(db.Model):
    __tablename__ = 'qc_check_sheets'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer, default=2)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    rows = db.relationship('QCCheckSheetRow', backref='check_sheet', cascade='all, delete-orphan')

class QCCheckSheetRow(db.Model):
    __tablename__ = 'qc_check_sheet_rows'
    id = db.Column(db.Integer, primary_key=True)
    check_sheet_id = db.Column(db.Integer, db.ForeignKey('qc_check_sheets.id'), nullable=False)
    category_name = db.Column(db.String(255), nullable=False)
    total_count = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)

class QCCheckSheetEntry(db.Model):
    __tablename__ = 'qc_check_sheet_entries'
    id = db.Column(db.Integer, primary_key=True)
    check_sheet_id = db.Column(db.Integer, db.ForeignKey('qc_check_sheets.id'), nullable=False)
    row_id = db.Column(db.Integer, db.ForeignKey('qc_check_sheet_rows.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    count = db.Column(db.Integer, default=1)
    inspector = db.Column(db.String(255))
    remarks = db.Column(db.Text)

class QCParetoChart(db.Model):
    __tablename__ = 'qc_pareto_charts'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer)  # Can be 2, 5, or 6
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    total_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    items = db.relationship('QCParetoItem', backref='pareto_chart', cascade='all, delete-orphan')

class QCParetoItem(db.Model):
    __tablename__ = 'qc_pareto_items'
    id = db.Column(db.Integer, primary_key=True)
    pareto_chart_id = db.Column(db.Integer, db.ForeignKey('qc_pareto_charts.id'), nullable=False)
    cause_name = db.Column(db.String(255), nullable=False)
    frequency = db.Column(db.Integer, nullable=False)
    cumulative_pct = db.Column(db.Float)
    priority_rank = db.Column(db.Integer)

class QCStratification(db.Model):
    __tablename__ = 'qc_stratifications'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer, default=2)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category_type = db.Column(db.String(100))  # Shift, Machine, Operator, Material
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    items = db.relationship('QCStratificationItem', backref='stratification', cascade='all, delete-orphan')

class QCStratificationItem(db.Model):
    __tablename__ = 'qc_stratification_items'
    id = db.Column(db.Integer, primary_key=True)
    stratification_id = db.Column(db.Integer, db.ForeignKey('qc_stratifications.id'), nullable=False)
    factor_name = db.Column(db.String(255), nullable=False)
    defect_count = db.Column(db.Integer, default=0)
    percentage = db.Column(db.Float)

class QCProcessMap(db.Model):
    __tablename__ = 'qc_process_maps'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer, default=2)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    steps = db.relationship('QCProcessStep', backref='process_map', cascade='all, delete-orphan')

class QCProcessStep(db.Model):
    __tablename__ = 'qc_process_steps'
    id = db.Column(db.Integer, primary_key=True)
    process_map_id = db.Column(db.Integer, db.ForeignKey('qc_process_maps.id'), nullable=False)
    step_order = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50))  # Input, Process, Decision, Output
    description = db.Column(db.Text)
    next_step_id = db.Column(db.Integer)

class QCFishboneDiagram(db.Model):
    __tablename__ = 'qc_fishbone_diagrams'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer, default=4)
    effect = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    branches = db.relationship('QCFishboneBranch', backref='fishbone', cascade='all, delete-orphan')

class QCFishboneBranch(db.Model):
    __tablename__ = 'qc_fishbone_branches'
    id = db.Column(db.Integer, primary_key=True)
    fishbone_id = db.Column(db.Integer, db.ForeignKey('qc_fishbone_diagrams.id'), nullable=False)
    category = db.Column(db.String(100), nullable=False)  # Man, Machine, Material, Method, Measurement, Environment
    parent_cause_id = db.Column(db.Integer, db.ForeignKey('qc_fishbone_branches.id'))
    text = db.Column(db.Text, nullable=False)

class QCScatterDiagram(db.Model):
    __tablename__ = 'qc_scatter_diagrams'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer)  # Can be 4 or 5
    x_axis_label = db.Column(db.String(100))
    y_axis_label = db.Column(db.String(100))
    correlation_coefficient = db.Column(db.Float)
    correlation_type = db.Column(db.String(50))  # Positive, Negative, None
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    points = db.relationship('QCScatterPoint', backref='scatter', cascade='all, delete-orphan')

class QCScatterPoint(db.Model):
    __tablename__ = 'qc_scatter_points'
    id = db.Column(db.Integer, primary_key=True)
    scatter_diagram_id = db.Column(db.Integer, db.ForeignKey('qc_scatter_diagrams.id'), nullable=False)
    x_value = db.Column(db.Float, nullable=False)
    y_value = db.Column(db.Float, nullable=False)
    remarks = db.Column(db.Text)

class QCControlChart(db.Model):
    __tablename__ = 'qc_control_charts'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer)  # Can be 4 or 6
    title = db.Column(db.String(255), nullable=False)
    chart_type = db.Column(db.String(50), default='Xbar-R')
    mean = db.Column(db.Float)
    ucl = db.Column(db.Float)
    lcl = db.Column(db.Float)
    std_dev = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    points = db.relationship('QCControlPoint', backref='control_chart', cascade='all, delete-orphan')

class QCControlPoint(db.Model):
    __tablename__ = 'qc_control_points'
    id = db.Column(db.Integer, primary_key=True)
    control_chart_id = db.Column(db.Integer, db.ForeignKey('qc_control_charts.id'), nullable=False)
    sample_index = db.Column(db.Integer, nullable=False)
    value = db.Column(db.Float, nullable=False)
    is_out_of_control = db.Column(db.Boolean, default=False)


class ProjectReview(db.Model):
    __tablename__ = 'project_reviews'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_number = db.Column(db.Integer)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(20), default='Pending')
    decision = db.Column(db.String(20)) # Approve / Reject
    comments = db.Column(db.Text)
    decided_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_ref = db.relationship('Project', backref=db.backref('reviews', lazy=True))

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
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    target_table = db.Column(db.String(100))
    target_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

class SaaSUserSession(db.Model):
    __tablename__ = 'saas_user_sessions'
    session_id = db.Column(db.String(100), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    logout_time = db.Column(db.DateTime)
    session_duration = db.Column(db.Integer)  # in seconds
    device = db.Column(db.String(50))
    browser = db.Column(db.String(50))
    os = db.Column(db.String(50))
    ip_address = db.Column(db.String(45))
    location = db.Column(db.String(100))
    status = db.Column(db.String(20), default='Active')  # Active, LoggedOut, Terminated

    user = db.relationship('User', backref=db.backref('sessions', cascade='all, delete-orphan'))
    organization = db.relationship('Organization', backref='sessions')

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    organization = db.relationship('Organization', backref='export_logs')
    user = db.relationship('User', backref='export_logs')


# Legacy stage models removed/replaced by 8D stage models above

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
    embedding = db.Column(Vector(384))  # Vector support enabled for production (Neon)
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
# MODULE 6: Employee Reward & Leaderboard Models
# ============================
class EmployeePoints(db.Model):
    __tablename__ = 'employee_points'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    activity_type = db.Column(db.String(100), nullable=False, index=True)
    activity_reference_id = db.Column(db.String(100), nullable=True)
    points = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        db.UniqueConstraint('employee_id', 'activity_type', 'activity_reference_id', name='uq_employee_activity_ref'),
    )

    employee = db.relationship('User', foreign_keys=[employee_id], backref=db.backref('points_entries', cascade='all, delete-orphan'))
    organization = db.relationship('Organization', backref='points_entries')
    project = db.relationship('Project', backref='points_entries')
    creator = db.relationship('User', foreign_keys=[created_by])


class EmployeeLeaderboard(db.Model):
    __tablename__ = 'employee_leaderboard'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)
    total_points = db.Column(db.Integer, default=0, index=True)
    projects_completed = db.Column(db.Integer, default=0)
    projects_created = db.Column(db.Integer, default=0)
    ideas_submitted = db.Column(db.Integer, default=0)
    ideas_approved = db.Column(db.Integer, default=0)
    knowledge_articles = db.Column(db.Integer, default=0)
    meetings_attended = db.Column(db.Integer, default=0)
    badges = db.Column(db.String(50), default='Beginner')
    rank = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('User', backref=db.backref('leaderboard_entry', uselist=False, cascade='all, delete-orphan'))
    organization = db.relationship('Organization', backref='leaderboard_entries')


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

# ============================
# Facilitator Assistance Request Model
# ============================
class FacilitatorAssistanceRequest(db.Model):
    __tablename__ = 'facilitator_assistance_requests'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer, nullable=False, default=1)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    facilitator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='Pending')
    response = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = db.relationship('Project', backref=db.backref('assistance_requests', lazy=True, cascade="all, delete-orphan"))
    requester = db.relationship('User', foreign_keys=[user_id], backref=db.backref('sent_assistance_requests', lazy=True))
    facilitator = db.relationship('User', foreign_keys=[facilitator_id], backref=db.backref('received_assistance_requests', lazy=True))


# ============================
# Backward-Compatible Aliases
# ============================
# These map old model names (used throughout routes) to the new 8-stage models.
# This avoids breaking dozens of route files that still import the old names.
# Aliases mapping new 8D models to existing frontend expectations
Stage1Identification = Stage1ProblemDefinitionProjectInitiation
Stage2Selection = Stage2ObservationDataCollection
Stage3Analysis = Stage3CauseIdentification
Stage4Causes = Stage4RootCauseAnalysisVerification
Stage5RootCause = Stage5CountermeasurePlanningSolutionDevelopment
Stage6DataAnalysis = Stage6ImplementationChangeManagement
Stage7Development = Stage7PerformanceVerificationBenefitsRealization
Stage8Implementation = Stage8StandardizationKnowledgeSharingProjectClosure

Stage1Problem = Stage1ProblemDefinitionProjectInitiation
Stage3RCA = Stage4RootCauseAnalysisVerification
Stage4Solution = Stage7PerformanceVerificationBenefitsRealization
Stage5Approval = Stage7PerformanceVerificationBenefitsRealization # Using a fallback since ProjectReview might not exist
Stage6Implementation = Stage8StandardizationKnowledgeSharingProjectClosure
Stage7Impact = Stage8StandardizationKnowledgeSharingProjectClosure
Stage8Standardization = Stage8StandardizationKnowledgeSharingProjectClosure

# ============================
# SUPER ADMIN & PLATFORM MODELS
# ============================

class PlatformSettings(db.Model):
    __tablename__ = 'platform_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.String(100), default="QCMS Enterprise")
    maintenance_mode = db.Column(db.Boolean, default=False)
    registration_open = db.Column(db.Boolean, default=True)
    require_email_otp = db.Column(db.Boolean, default=True)
    require_phone_otp = db.Column(db.Boolean, default=False)
    global_notification = db.Column(db.Text, nullable=True)
    support_email = db.Column(db.String(120), default="support@ifqm.org.in")
    system_version = db.Column(db.String(20), default="1.0.0")
    global_template_version = db.Column(db.Integer, default=1, nullable=False)
    global_template_updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    default_plan = db.Column(db.String(50), default="Starter")
    trial_period_days = db.Column(db.Integer, default=14)
    max_auto_trial_extensions = db.Column(db.Integer, default=2)
    payment_gateway_mode = db.Column(db.String(20), default="Test") # Test or Live
    plans_initial_seeded = db.Column(db.Boolean, default=False)
    
    # Extended Platform Settings Columns
    support_phone = db.Column(db.String(50), nullable=True)
    support_website = db.Column(db.String(255), nullable=True)
    company_address = db.Column(db.Text, nullable=True)
    timezone = db.Column(db.String(100), default="UTC")
    default_language = db.Column(db.String(10), default="en")
    date_format = db.Column(db.String(50), default="YYYY-MM-DD")
    time_format = db.Column(db.String(20), default="HH:mm:ss")
    currency = db.Column(db.String(10), default="USD")
    
    branding_settings = db.Column(db.JSON, nullable=True)
    localization_settings = db.Column(db.JSON, nullable=True)
    authentication_settings = db.Column(db.JSON, nullable=True)
    security_settings = db.Column(db.JSON, nullable=True)
    notification_settings = db.Column(db.JSON, nullable=True)
    email_settings = db.Column(db.JSON, nullable=True)
    sms_settings = db.Column(db.JSON, nullable=True)
    push_settings = db.Column(db.JSON, nullable=True)
    storage_settings = db.Column(db.JSON, nullable=True)
    backup_settings = db.Column(db.JSON, nullable=True)
    compliance_settings = db.Column(db.JSON, nullable=True)
    api_settings = db.Column(db.JSON, nullable=True)
    webhook_settings = db.Column(db.JSON, nullable=True)
    integrations_settings = db.Column(db.JSON, nullable=True)
    ai_settings = db.Column(db.JSON, nullable=True)
    feature_flags = db.Column(db.JSON, nullable=True)
    maintenance_settings = db.Column(db.JSON, nullable=True)
    system_settings = db.Column(db.JSON, nullable=True)
    landing_cms_settings = db.Column(db.JSON, nullable=True)
    organizations_settings = db.Column(db.JSON, nullable=True)
    billing_settings = db.Column(db.JSON, nullable=True)
    modules_settings = db.Column(db.JSON, nullable=True)
    developer_settings = db.Column(db.JSON, nullable=True)
    audit_logs_settings = db.Column(db.JSON, nullable=True)
    system_health_settings = db.Column(db.JSON, nullable=True)
    about_settings = db.Column(db.JSON, nullable=True)
    global_stages_config = db.Column(db.JSON, nullable=True)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SupportTicket(db.Model):
    __tablename__ = 'support_tickets'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='Medium') # Low, Medium, High, Urgent, Critical
    status = db.Column(db.String(20), default='Open') # Open, Assigned, In Progress, Waiting for Customer, Resolved, Closed, Cancelled
    category = db.Column(db.String(50)) # Technical, Billing, License, Subscription, User Access, Bug, Feature Request, Security, Performance, General Inquiry
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    resolution = db.Column(db.Text)
    
    # Advanced ticketing columns
    ticket_number = db.Column(db.String(100), unique=True, index=True)
    assigned_engineer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_team = db.Column(db.String(100), nullable=True)
    sla_status = db.Column(db.String(50), default='Within SLA') # Within SLA, Near Breach, Breached
    escalation_level = db.Column(db.Integer, default=0)
    tags = db.Column(db.JSON, default=list)
    
    # Relationships
    organization = db.relationship('Organization', backref='tickets')
    user = db.relationship('User', foreign_keys=[user_id], backref='tickets')
    assigned_engineer = db.relationship('User', foreign_keys=[assigned_engineer_id], backref='assigned_tickets')


class SupportComment(db.Model):
    __tablename__ = 'support_comments'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ticket = db.relationship('SupportTicket', backref=db.backref('comments', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref='ticket_comments')


class SupportAttachment(db.Model):
    __tablename__ = 'support_attachments'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id', ondelete='CASCADE'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('support_comments.id', ondelete='CASCADE'), nullable=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100))
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    virus_scan_passed = db.Column(db.Boolean, default=True)

    ticket = db.relationship('SupportTicket', backref=db.backref('attachments', lazy=True, cascade='all, delete-orphan'))
    comment = db.relationship('SupportComment', backref=db.backref('attachments', lazy=True))
    uploaded_by = db.relationship('User', backref='ticket_uploads')


class SupportSLA(db.Model):
    __tablename__ = 'support_slas'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id', ondelete='CASCADE'), nullable=False)
    first_response_due = db.Column(db.DateTime)
    first_response_responded_at = db.Column(db.DateTime)
    resolution_due = db.Column(db.DateTime)
    resolution_completed_at = db.Column(db.DateTime)
    sla_status = db.Column(db.String(50), default='Within SLA')
    is_paused = db.Column(db.Boolean, default=False)
    paused_at = db.Column(db.DateTime)
    accumulated_paused_seconds = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ticket = db.relationship('SupportTicket', backref=db.backref('sla', uselist=False, lazy=True, cascade='all, delete-orphan'))


class SupportEscalation(db.Model):
    __tablename__ = 'support_escalations'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id', ondelete='CASCADE'), nullable=False)
    escalation_level = db.Column(db.Integer, default=1)
    reason = db.Column(db.Text)
    escalated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    escalated_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    escalated_at = db.Column(db.DateTime, default=datetime.utcnow)

    ticket = db.relationship('SupportTicket', backref=db.backref('escalations', lazy=True, cascade='all, delete-orphan'))
    escalated_by = db.relationship('User', foreign_keys=[escalated_by_id])
    escalated_to = db.relationship('User', foreign_keys=[escalated_to_id])


class SupportRating(db.Model):
    __tablename__ = 'support_ratings'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id', ondelete='CASCADE'), unique=True, nullable=False)
    rating = db.Column(db.Integer, nullable=False) # 1 to 5
    feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ticket = db.relationship('SupportTicket', backref=db.backref('rating', uselist=False, lazy=True, cascade='all, delete-orphan'))


class SupportKnowledge(db.Model):
    __tablename__ = 'support_knowledge'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    views_count = db.Column(db.Integer, default=0)

    created_by = db.relationship('User', backref='kb_articles')


class SupportAudit(db.Model):
    __tablename__ = 'support_audits'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False) # Create Ticket, Update Ticket, Reassign Ticket, Comment Added, etc.
    old_values = db.Column(db.JSON)
    new_values = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ticket = db.relationship('SupportTicket', backref=db.backref('audits', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref='support_audit_actions')


class SalesEnquiry(db.Model):
    __tablename__ = 'sales_enquiries'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(50), default='Talk to Sales')
    status = db.Column(db.String(30), default='New')  # New, Contacted, In Progress, Converted, Closed
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SubscriptionPayment(db.Model):
    __tablename__ = 'subscription_payments'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    # FK to new Subscription model (nullable for legacy records)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('subscription_invoices.id', ondelete='SET NULL'), nullable=True)
    amount = db.Column(db.Float, nullable=False)  # base amount (preserved)
    currency = db.Column(db.String(10), default='INR')
    plan_name = db.Column(db.String(50))
    billing_cycle = db.Column(db.String(20))  # Monthly, Quarterly, Yearly, Lifetime
    payment_status = db.Column(db.String(20), default='Completed')  # Completed, Pending, Failed, Refunded
    transaction_id = db.Column(db.String(255), unique=True)
    payment_gateway = db.Column(db.String(50))  # Razorpay, Stripe, Manual, etc.
    gateway_reference = db.Column(db.String(255))
    discount_amount = db.Column(db.Float, default=0.0)
    gst_percent = db.Column(db.Float, default=18.0)
    gst_amount = db.Column(db.Float, default=0.0)
    final_amount = db.Column(db.Float)  # amount - discount + gst
    refund_status = db.Column(db.String(20))  # None, Partial, Full
    refund_amount = db.Column(db.Float, default=0.0)
    refund_date = db.Column(db.DateTime)
    billing_period_start = db.Column(db.DateTime)
    billing_period_end = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    organization = db.relationship('Organization', backref='payments')

class SuperAdminLog(db.Model):
    __tablename__ = 'super_admin_logs'
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    target_type = db.Column(db.String(50)) # Organization, User, SystemSetting
    target_id = db.Column(db.Integer)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship('User', backref='super_admin_logs')


# ============================
# MODULE: Enterprise Subscription Management
# ============================

class Subscription(db.Model):
    """Enterprise Subscription — full lifecycle entity, decoupled from Organization"""
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)

    # Unique subscription reference (e.g. SUB-2026-0001)
    subscription_uid = db.Column(db.String(50), unique=True, nullable=False)

    # Plan & Billing
    plan_name = db.Column(db.String(50), default='Professional')  # Starter, Professional, Enterprise, Custom
    billing_cycle = db.Column(db.String(20), default='Yearly')    # Monthly, Quarterly, Yearly, Lifetime

    # Status
    subscription_status = db.Column(db.String(20), default='Active')
    # Active, Trial, Expired, Cancelled, Suspended, Pending
    payment_status = db.Column(db.String(20), default='Paid')
    # Paid, Pending, Failed, Overdue, Cancelled

    # Dates
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    renewal_date = db.Column(db.DateTime)
    trial_start_date = db.Column(db.DateTime)
    trial_end_date = db.Column(db.DateTime)

    # Pricing
    base_price = db.Column(db.Float, default=0.0)
    discount_percent = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    gst_percent = db.Column(db.Float, default=18.0)
    gst_amount = db.Column(db.Float, default=0.0)
    final_amount = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(10), default='INR')
    is_tax_inclusive = db.Column(db.Boolean, default=False)

    # Limits & Configuration
    max_users = db.Column(db.Integer, default=500)
    storage_limit_gb = db.Column(db.Float, default=10.0)
    api_limit = db.Column(db.Integer, default=10000)  # API calls per month
    enabled_modules = db.Column(db.JSON, default=list)  # list of module names
    support_level = db.Column(db.String(50), default='Standard')  # Standard, Priority, Enterprise

    # Renewal settings
    auto_renewal = db.Column(db.Boolean, default=True)
    grace_period_days = db.Column(db.Integer, default=7)

    # Metadata
    billing_notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cancelled_at = db.Column(db.DateTime)
    cancellation_reason = db.Column(db.Text)

    # Relationships
    organization = db.relationship('Organization', backref=db.backref('subscriptions', lazy=True))
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_subscriptions')
    invoices = db.relationship('SubscriptionInvoice', backref='subscription', lazy=True,
                               foreign_keys='SubscriptionInvoice.subscription_id',
                               cascade='all, delete-orphan')
    subscription_payments = db.relationship('SubscriptionPayment', backref='subscription', lazy=True,
                                            foreign_keys='SubscriptionPayment.subscription_id')

class OfflinePaymentProof(db.Model):
    """Offline / Dynamic QR Payment Proof submitted by Organization Admins for manual SuperAdmin verification"""
    __tablename__ = 'offline_payment_proofs'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    plan_name = db.Column(db.String(50), nullable=False)          # Starter, Professional, Enterprise
    billing_cycle = db.Column(db.String(20), default='Monthly')   # Monthly, Yearly
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR')
    
    transaction_id = db.Column(db.String(255), nullable=False)   # UTR / Transaction Reference
    screenshot_url = db.Column(db.String(500), nullable=True)     # Path to uploaded receipt screenshot
    notes = db.Column(db.Text, nullable=True)
    
    status = db.Column(db.String(30), default='Pending Verification') # Pending Verification, Approved, Rejected
    rejection_reason = db.Column(db.Text, nullable=True)
    
    verified_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    organization = db.relationship('Organization', backref=db.backref('offline_payments', lazy=True))
    user = db.relationship('User', foreign_keys=[user_id])
    verified_by = db.relationship('User', foreign_keys=[verified_by_id])


class SubscriptionInvoice(db.Model):
    """Invoice generated for each billing event on a subscription"""
    __tablename__ = 'subscription_invoices'

    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)

    # Invoice Identity
    invoice_uid = db.Column(db.String(50), unique=True, nullable=False)  # INV-2026-0001
    invoice_number = db.Column(db.String(100), unique=True)              # human-readable
    invoice_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)

    # Billing Period
    billing_period_start = db.Column(db.DateTime)
    billing_period_end = db.Column(db.DateTime)

    # Plan details
    plan_name = db.Column(db.String(50))
    billing_cycle = db.Column(db.String(20))

    # Pricing
    base_amount = db.Column(db.Float, default=0.0)
    discount_percent = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    gst_percent = db.Column(db.Float, default=18.0)
    gst_amount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(10), default='INR')
    is_tax_inclusive = db.Column(db.Boolean, default=False)

    # Status
    invoice_status = db.Column(db.String(20), default='Draft')
    # Draft, Sent, Paid, Overdue, Cancelled, Refunded

    # Link to payment
    payment_id = db.Column(db.Integer, db.ForeignKey('subscription_payments.id', use_alter=True, name='fk_invoice_payment_id'), nullable=True)

    # Storage
    pdf_path = db.Column(db.String(500))
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = db.relationship('Organization', backref=db.backref('invoices', lazy=True))
    payment = db.relationship('SubscriptionPayment', backref='invoice_record', foreign_keys=[payment_id])


# ============================
# MODULE: SOP Management
# ============================

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('sop_approvals', lazy=True))

class SOPVersion(db.Model):
    __tablename__ = 'sop_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    sop_id = db.Column(db.Integer, db.ForeignKey('sop_master.id', ondelete='CASCADE'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    changes_made = db.Column(db.Text)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    changed_date = db.Column(db.DateTime, default=datetime.utcnow)
    approval_date = db.Column(db.DateTime)
    sop_data = db.Column(db.JSON) # Full JSON dump of the SOP and steps
    
    changed_by = db.relationship('User', backref=db.backref('sop_version_changes', lazy=True))

class SOPTraining(db.Model):
    __tablename__ = 'training_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    sop_id = db.Column(db.Integer, db.ForeignKey('sop_master.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_date = db.Column(db.DateTime, default=datetime.utcnow)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    sop = db.relationship('SOP', backref=db.backref('assessment_config', uselist=False, lazy=True, cascade="all, delete-orphan"))

class SOPAssessmentQuestion(db.Model):
    __tablename__ = 'assessment_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    sop_id = db.Column(db.Integer, db.ForeignKey('sop_master.id', ondelete='CASCADE'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False) # MCQ, TF, MS
    options = db.Column(db.JSON)
    correct_answers = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('assessment_results', lazy=True))
    training = db.relationship('SOPTraining', backref=db.backref('assessment_results', lazy=True, cascade="all, delete-orphan"))

class SOPCertificate(db.Model):
    __tablename__ = 'training_certificates'
    
    id = db.Column(db.Integer, primary_key=True)
    training_id = db.Column(db.Integer, db.ForeignKey('training_assignments.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    certificate_number = db.Column(db.String(100), unique=True, nullable=False)
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    pdf_path = db.Column(db.String(500))
    
    user = db.relationship('User', backref=db.backref('certificates', lazy=True))
    training = db.relationship('SOPTraining', backref=db.backref('certificate_record', uselist=False, lazy=True, cascade="all, delete-orphan"))

class SOPAuditReport(db.Model):
    __tablename__ = 'training_audit_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    generated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    report_type = db.Column(db.String(100), nullable=False) # Training Audit, Compliance
    pdf_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    generated_by = db.relationship('User', backref=db.backref('audit_reports', lazy=True))

class SOPArchive(db.Model):
    __tablename__ = 'training_archive'
    
    id = db.Column(db.Integer, primary_key=True)
    sop_id = db.Column(db.Integer, db.ForeignKey('sop_master.id', ondelete='CASCADE'), nullable=False)
    archived_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    archived_at = db.Column(db.DateTime, default=datetime.utcnow)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('sop_notifications', lazy=True))
    training = db.relationship('SOPTraining', backref=db.backref('notifications', lazy=True, cascade="all, delete-orphan"))

class UserCustomField(db.Model):
    __tablename__ = 'user_custom_fields'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    field_key = db.Column(db.String(100), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    is_required = db.Column(db.Boolean, default=False)
    is_system = db.Column(db.Boolean, default=False)
    data_type = db.Column(db.String(50), default='both')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================
# MODULE: SaaS Plans Management
# ============================

class SaaSPlan(db.Model):
    """SaaS Product Plan definition (acts as template for Subscriptions)"""
    __tablename__ = 'saas_plans'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    long_description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='layers')
    color = db.Column(db.String(20), default='#3b82f6')
    status = db.Column(db.String(20), default='Active')      # Active, Inactive, Deprecated, Coming Soon
    plan_type = db.Column(db.String(100), default='Professional') # Starter, Professional, Enterprise, Custom, Trial
    currency = db.Column(db.String(10), default='INR')
    is_custom = db.Column(db.Boolean, default=False)
    is_default_trial = db.Column(db.Boolean, default=False)
    trial_duration_days = db.Column(db.Integer, default=14)
    auto_approve_extensions_limit = db.Column(db.Integer, default=2)
    version = db.Column(db.Integer, default=1)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pricing = db.relationship('SaaSPlanPricing', backref='plan', lazy=True, cascade='all, delete-orphan')
    limits = db.relationship('SaaSPlanLimits', backref='plan', lazy=True, uselist=False, cascade='all, delete-orphan')
    modules = db.relationship('SaaSPlanModules', backref='plan', lazy=True, cascade='all, delete-orphan')
    versions = db.relationship('SaaSPlanVersion', backref='plan', lazy=True, cascade='all, delete-orphan')
    analytics = db.relationship('SaaSPlanAnalytics', backref='plan', lazy=True, uselist=False, cascade='all, delete-orphan')


class SaaSPlanPricing(db.Model):
    """Pricing configuration for different billing cycles of a Plan"""
    __tablename__ = 'saas_plan_pricing'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('saas_plans.id', ondelete='CASCADE'), nullable=False)
    billing_cycle = db.Column(db.String(20), nullable=False)  # Monthly, Quarterly, Yearly, Lifetime
    price = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0.0)              # Percentage discount
    tax = db.Column(db.Float, default=18.0)                  # Default tax rate
    is_tax_inclusive = db.Column(db.Boolean, default=False)   # True if price includes GST
    is_active = db.Column(db.Boolean, default=True)


class SaaSPlanLimits(db.Model):
    """Usage limits imposed by a Plan"""
    __tablename__ = 'saas_plan_limits'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('saas_plans.id', ondelete='CASCADE'), nullable=False)
    max_users = db.Column(db.Integer, default=100)
    max_departments = db.Column(db.Integer, default=10)
    max_projects = db.Column(db.Integer, default=25)
    storage_limit_gb = db.Column(db.Float, default=10.0)
    api_limit = db.Column(db.Integer, default=10000)
    reports_limit = db.Column(db.Integer, default=100)
    dashboards_limit = db.Column(db.Integer, default=10)
    backups_limit = db.Column(db.Integer, default=5)


class SaaSPlanModules(db.Model):
    """SaaS Modules enabled/disabled per Plan"""
    __tablename__ = 'saas_plan_modules'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('saas_plans.id', ondelete='CASCADE'), nullable=False)
    module_name = db.Column(db.String(50), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    is_premium = db.Column(db.Boolean, default=False)


class SaaSPlanVersion(db.Model):
    """Historical version snapshot for SaaS plans"""
    __tablename__ = 'saas_plan_versions'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('saas_plans.id', ondelete='CASCADE'), nullable=False)
    version = db.Column(db.Integer, nullable=False)
    plan_data = db.Column(db.JSON, nullable=False)  # Full JSON snapshot of limits, modules, pricing
    change_summary = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_by = db.relationship('User', foreign_keys=[created_by_id])


class SaaSPlanAnalytics(db.Model):
    """Aggregated subscriber analytics for a Plan"""
    __tablename__ = 'saas_plan_analytics'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('saas_plans.id', ondelete='CASCADE'), nullable=False)
    mrr = db.Column(db.Float, default=0.0)
    arr = db.Column(db.Float, default=0.0)
    subscriber_count = db.Column(db.Integer, default=0)
    renewal_rate = db.Column(db.Float, default=100.0)
    upgrade_rate = db.Column(db.Float, default=0.0)
    downgrade_rate = db.Column(db.Float, default=0.0)
    cancellation_rate = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Module(db.Model):
    """Registry entry for an enterprise feature module & feature flag"""
    __tablename__ = 'modules'

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100), default='Core')  # Core, Quality, Reports, Analytics, AI, Security, Governance, etc.
    icon = db.Column(db.String(50), default='package')
    color = db.Column(db.String(50), default='#3b82f6')
    display_order = db.Column(db.Integer, default=0)
    navigation_route = db.Column(db.String(255))
    api_prefix = db.Column(db.String(255))
    status = db.Column(db.String(50), default='Active')  # Active, Inactive, Beta, Deprecated, Hidden, Coming Soon, Disabled
    development_stage = db.Column(db.String(50), default='Released') # Under Development, Internal, Testing, Beta, Released, Deprecated, Disabled, Removed
    version = db.Column(db.String(50), default='1.0.0')
    minimum_plan = db.Column(db.String(50), default='Starter') # Starter, Professional, Enterprise, Ultimate
    
    # Flags/Configuration
    enable_by_default = db.Column(db.Boolean, default=False)
    visible_in_sidebar = db.Column(db.Boolean, default=True)
    visible_in_dashboard = db.Column(db.Boolean, default=True)
    page_visibility = db.Column(db.Boolean, default=True)
    widget_visibility = db.Column(db.Boolean, default=True)
    button_visibility = db.Column(db.Boolean, default=True)

    backend_enabled = db.Column(db.Boolean, default=True)
    frontend_enabled = db.Column(db.Boolean, default=True)
    api_enabled = db.Column(db.Boolean, default=True)
    export_enabled = db.Column(db.Boolean, default=True)
    import_enabled = db.Column(db.Boolean, default=True)
    notification_enabled = db.Column(db.Boolean, default=True)
    background_jobs_enabled = db.Column(db.Boolean, default=True)

    requires_license = db.Column(db.Boolean, default=False)
    requires_subscription = db.Column(db.Boolean, default=True)
    premium_feature = db.Column(db.Boolean, default=False)
    ai_enabled = db.Column(db.Boolean, default=False)
    beta_feature = db.Column(db.Boolean, default=False)
    system_module = db.Column(db.Boolean, default=False)
    
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # JSON config for feature flags (beta, experimental, internal_only, premium_only, trial_only, etc.)
    feature_flags = db.Column(db.JSON, default=dict)
    
    is_archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent = db.relationship('Module', remote_side=[id], backref=db.backref('children', lazy=True, cascade='all, delete-orphan'))
    dependencies = db.relationship('ModuleDependency', backref='module', lazy=True, cascade='all, delete-orphan', foreign_keys='ModuleDependency.module_id')
    assignments = db.relationship('ModuleAssignment', backref='module', lazy=True, cascade='all, delete-orphan')
    permissions = db.relationship('ModulePermission', backref='module', lazy=True, cascade='all, delete-orphan')
    analytics = db.relationship('ModuleUsageAnalytics', backref='module', lazy=True, cascade='all, delete-orphan')
    audit_logs = db.relationship('ModuleAuditLog', backref='module', lazy=True, cascade='all, delete-orphan')
    created_by = db.relationship('User', foreign_keys=[created_by_id])


class OrganizationFeatureOverride(db.Model):
    """Organization-level feature flag override (e.g. Add-on features purchased by specific tenant)"""
    __tablename__ = 'organization_features'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = db.relationship('Organization', backref=db.backref('feature_overrides', lazy=True, cascade='all, delete-orphan'))
    module = db.relationship('Module', backref=db.backref('org_overrides', lazy=True, cascade='all, delete-orphan'))


class FeatureCategory(db.Model):
    """Registry table for feature module categorization"""
    __tablename__ = 'feature_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='folder')
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FeatureVersion(db.Model):
    """Version snapshots for features"""
    __tablename__ = 'feature_versions'

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    version_number = db.Column(db.String(50), nullable=False)
    snapshot_json = db.Column(db.JSON, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    module = db.relationship('Module', backref=db.backref('versions_list', lazy=True, cascade='all, delete-orphan'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])


class ModuleDependency(db.Model):
    """Dependencies between modules"""
    __tablename__ = 'module_dependencies'

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    dependency_module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    dependency_type = db.Column(db.String(50), default='Required')  # Required, Blocked, Parent, Child

    # Relationship to get details of the dependency target
    dependency_module = db.relationship('Module', foreign_keys=[dependency_module_id])


class ModuleAssignment(db.Model):
    """Availability of modules to SaaS plans or specific organizations"""
    __tablename__ = 'module_assignments'

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    assigned_type = db.Column(db.String(50), nullable=False)  # Plan, Organization, Industry, Region, CustomerType
    assigned_target = db.Column(db.String(255), nullable=False)  # e.g., Starter, 15 (Org ID), Automotive, North, etc.
    assignment_metadata = db.Column(db.JSON, default=dict)  # Options like license key overrides


class ModulePermission(db.Model):
    """RBAC Permissions integration for modules"""
    __tablename__ = 'module_permissions'

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    role_name = db.Column(db.String(100), nullable=False)
    
    # Action access dict: {"view": true, "create": true, "update": true, "delete": true, "export": true, "approve": true, "admin": true}
    permissions = db.Column(db.JSON, default=dict)


class ModuleUsageAnalytics(db.Model):
    """Usage analytics metrics for module performance and growth trends"""
    __tablename__ = 'module_analytics'

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True)
    active_users = db.Column(db.Integer, default=0)
    daily_usage = db.Column(db.Integer, default=0)
    monthly_usage = db.Column(db.Integer, default=0)
    api_calls = db.Column(db.Integer, default=0)
    storage_consumption_mb = db.Column(db.Float, default=0.0)
    performance_ms = db.Column(db.Integer, default=0)
    error_rate = db.Column(db.Float, default=0.0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class ModuleAuditLog(db.Model):
    """Immutable audit logging for module adjustments"""
    __tablename__ = 'module_audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    admin_name = db.Column(db.String(150), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # CREATE, UPDATE, DISABLE, ENABLE, CHANGE_PERMISSION, ASSIGN_PLAN
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# ============================
# MODULE: Enterprise Analytics & Custom Reporting
# ============================

class AnalyticsCache(db.Model):
    __tablename__ = 'analytics_cache'
    id = db.Column(db.Integer, primary_key=True)
    cache_key = db.Column(db.String(150), unique=True, nullable=False, index=True)
    cache_data = db.Column(db.JSON, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AnalyticsReport(db.Model):
    __tablename__ = 'analytics_reports'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True) # Null means global template
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    config_json = db.Column(db.JSON, nullable=False) # contains fields, metrics, grouping, sorting, charts, filters
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    organization = db.relationship('Organization', backref=db.backref('analytics_reports', lazy=True, cascade='all, delete-orphan'))
    created_by = db.relationship('User', backref=db.backref('created_reports', lazy=True))

class AnalyticsSchedule(db.Model):
    __tablename__ = 'analytics_schedules'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    report_id = db.Column(db.Integer, db.ForeignKey('analytics_reports.id', ondelete='CASCADE'), nullable=False)
    frequency = db.Column(db.String(50), default='Daily') # Daily, Weekly, Monthly
    format = db.Column(db.String(20), default='CSV') # CSV, Excel, PDF
    recipient_emails = db.Column(db.JSON, default=list) # JSON list of emails
    next_run = db.Column(db.DateTime)
    last_run = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    organization = db.relationship('Organization', backref=db.backref('analytics_schedules', lazy=True, cascade='all, delete-orphan'))
    report = db.relationship('AnalyticsReport', backref=db.backref('schedules', lazy=True, cascade='all, delete-orphan'))

class AnalyticsExport(db.Model):
    __tablename__ = 'analytics_exports'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    report_type = db.Column(db.String(100), nullable=False) # Revenue, Users, Modules, Custom, etc.
    format = db.Column(db.String(20), nullable=False) # CSV, Excel, PDF
    file_path = db.Column(db.String(500))
    filters_applied = db.Column(db.JSON, default=dict)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    organization = db.relationship('Organization', backref=db.backref('analytics_exports', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('analytics_exports', lazy=True))

class AnalyticsAIInsights(db.Model):
    __tablename__ = 'analytics_ai_insights'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True) # Null means global
    insight_type = db.Column(db.String(100), nullable=False) # Revenue Forecast, Churn Prediction, Risk Score, etc.
    insight_json = db.Column(db.JSON, nullable=False)
    recommendation = db.Column(db.Text)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    organization = db.relationship('Organization', backref=db.backref('analytics_ai_insights', lazy=True, cascade='all, delete-orphan'))

class AnalyticsUsage(db.Model):
    __tablename__ = 'analytics_usage'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    module_name = db.Column(db.String(100), nullable=False)
    feature_name = db.Column(db.String(100))
    action_type = db.Column(db.String(100), nullable=False) # login, api_call, view, click
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    organization = db.relationship('Organization', backref=db.backref('analytics_usage', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('analytics_usage', lazy=True))


# ============================
# MODULE: Enterprise Billing & Revenue Management
# ============================

class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('subscription_invoices.id', ondelete='CASCADE'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0.0)
    amount = db.Column(db.Float, default=0.0)

    invoice = db.relationship('SubscriptionInvoice', backref=db.backref('items', lazy=True, cascade='all, delete-orphan'))

class SubscriptionRefund(db.Model):
    __tablename__ = 'subscription_refunds'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('subscription_invoices.id', ondelete='CASCADE'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('subscription_payments.id', ondelete='CASCADE'), nullable=False)
    refund_uid = db.Column(db.String(50), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(255))
    status = db.Column(db.String(20), default='Approved')  # Pending, Approved, Rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    invoice = db.relationship('SubscriptionInvoice', backref=db.backref('refund_records', lazy=True, cascade='all, delete-orphan'))
    payment = db.relationship('SubscriptionPayment', backref=db.backref('refund_records', lazy=True))

class SubscriptionCreditNote(db.Model):
    __tablename__ = 'subscription_credit_notes'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('subscription_invoices.id', ondelete='SET NULL'), nullable=True)
    credit_note_uid = db.Column(db.String(50), unique=True, nullable=False)
    amount = db.Column(db.Float, default=0.0)
    balance = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Active')  # Active, Applied, Void
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    organization = db.relationship('Organization', backref=db.backref('credit_notes', lazy=True))
    invoice = db.relationship('SubscriptionInvoice', backref=db.backref('credit_notes', lazy=True))

class BillingSettings(db.Model):
    __tablename__ = 'billing_settings'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), unique=True, nullable=False)
    auto_collection = db.Column(db.Boolean, default=True)
    reminder_schedule = db.Column(db.JSON, default=lambda: [3, 1, 0, -3])  # days before/after due date
    grace_period_days = db.Column(db.Integer, default=7)
    payment_retry_attempts = db.Column(db.Integer, default=3)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = db.relationship('Organization', backref=db.backref('billing_settings', uselist=False, lazy=True))

class TaxRule(db.Model):
    __tablename__ = 'tax_rules'
    id = db.Column(db.Integer, primary_key=True)
    country = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100))  # e.g., state code for IGST vs SGST/CGST
    tax_type = db.Column(db.String(50), default='GST')  # GST, VAT, custom
    rate = db.Column(db.Float, default=18.0)
    is_exempt = db.Column(db.Boolean, default=False)

class BillingAudit(db.Model):
    __tablename__ = 'billing_audits'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('subscription_invoices.id', ondelete='SET NULL'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # Created, Paid, Refunded, etc.
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    organization = db.relationship('Organization', backref=db.backref('billing_audits', lazy=True))
    invoice = db.relationship('SubscriptionInvoice', backref=db.backref('billing_audits', lazy=True))
    user = db.relationship('User', backref=db.backref('billing_audits', lazy=True))




# ============================
# MODULE: Enterprise Announcements
# ============================

class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    ann_number = db.Column(db.String(50), unique=True, nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    title = db.Column(db.String(500), nullable=False)
    summary = db.Column(db.Text)
    body = db.Column(db.Text)
    banner_url = db.Column(db.String(500))
    tags = db.Column(db.JSON, default=list)
    category = db.Column(db.String(50), default='General')
    priority = db.Column(db.String(20), default='Medium')
    status = db.Column(db.String(20), default='Draft')
    publish_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)
    timezone = db.Column(db.String(50), default='UTC')
    published_at = db.Column(db.DateTime)
    channels = db.Column(db.JSON, default=lambda: {'in_app': True, 'email': False, 'sms': False, 'push': False})
    audience_type = db.Column(db.String(20), default='all')
    total_delivered = db.Column(db.Integer, default=0)
    total_viewed = db.Column(db.Integer, default=0)
    total_read = db.Column(db.Integer, default=0)
    total_clicked = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    author = db.relationship('User', backref='authored_announcements', foreign_keys=[created_by])
    audience = db.relationship('AnnouncementAudience', backref='announcement', cascade='all, delete-orphan', lazy=True)
    deliveries = db.relationship('AnnouncementDelivery', backref='announcement', cascade='all, delete-orphan', lazy=True)
    reads = db.relationship('AnnouncementRead', backref='announcement', cascade='all, delete-orphan', lazy=True)
    attachments = db.relationship('AnnouncementAttachment', backref='announcement', cascade='all, delete-orphan', lazy=True)
    audit_logs = db.relationship('AnnouncementAudit', backref='announcement', cascade='all, delete-orphan', lazy=True)


class AnnouncementAudience(db.Model):
    __tablename__ = 'announcement_audience'
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements.id', ondelete='CASCADE'), nullable=False)
    target_type = db.Column(db.String(30), nullable=False)
    target_value = db.Column(db.String(255), nullable=False)


class AnnouncementDelivery(db.Model):
    __tablename__ = 'announcement_delivery'
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements.id', ondelete='CASCADE'), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    channel = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    sent_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    retry_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AnnouncementRead(db.Model):
    __tablename__ = 'announcement_reads'
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    viewed_at = db.Column(db.DateTime)
    read_at = db.Column(db.DateTime)
    clicked_at = db.Column(db.DateTime)
    dismissed_at = db.Column(db.DateTime)
    device = db.Column(db.String(30))
    browser = db.Column(db.String(50))
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AnnouncementAttachment(db.Model):
    __tablename__ = 'announcement_attachments'
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements.id', ondelete='CASCADE'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, default=0)
    file_type = db.Column(db.String(50))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AnnouncementAudit(db.Model):
    __tablename__ = 'announcement_audit'
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    actor = db.relationship('User', backref='announcement_audits')


# --- ENTERPRISE INTEGRATION HUB MODELS ---

class IntegrationConfig(db.Model):
    __tablename__ = 'integration_configs'
    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.String(100), unique=True, nullable=False)
    provider_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='Disconnected') # Connected, Disconnected, Disabled, Error
    version = db.Column(db.String(20), default='v1.0.0')
    settings = db.Column(db.JSON, default=dict) # JSON settings containing public keys, urls, hosts
    health_score = db.Column(db.Integer, default=100)
    last_sync = db.Column(db.DateTime, default=datetime.utcnow)
    usage_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IntegrationApiKey(db.Model):
    __tablename__ = 'integration_api_keys'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    key_prefix = db.Column(db.String(15), default='qc_live_')
    api_key_hash = db.Column(db.String(255), unique=True, nullable=False)
    secret_key_masked = db.Column(db.String(255))
    status = db.Column(db.String(20), default='Active') # Active, Disabled, Revoked
    expiration_date = db.Column(db.DateTime)
    rate_limit = db.Column(db.Integer, default=60)
    allowed_ips = db.Column(db.JSON, default=list)
    allowed_domains = db.Column(db.JSON, default=list)
    scopes = db.Column(db.JSON, default=list)
    owner = db.Column(db.String(100))
    usage_count = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class IntegrationWebhook(db.Model):
    __tablename__ = 'integration_webhooks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    secret = db.Column(db.String(255))
    status = db.Column(db.String(20), default='Active') # Active, Disabled
    headers = db.Column(db.JSON, default=dict)
    events = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class IntegrationWebhookDelivery(db.Model):
    __tablename__ = 'integration_webhook_deliveries'
    id = db.Column(db.Integer, primary_key=True)
    webhook_id = db.Column(db.Integer, db.ForeignKey('integration_webhooks.id', ondelete='CASCADE'), nullable=False)
    event = db.Column(db.String(100), nullable=False)
    payload = db.Column(db.JSON)
    response_code = db.Column(db.Integer)
    response_body = db.Column(db.Text)
    latency_ms = db.Column(db.Float, default=0.0)
    retry_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20)) # Success, Failed, Pending
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class IntegrationAuditLog(db.Model):
    __tablename__ = 'integration_audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    provider_id = db.Column(db.String(100))
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Compliance Standards — per-organisation certificate & audit data
# ---------------------------------------------------------------------------
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

    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at        = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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


# ---------------------------------------------------------------------------
# Integration API & Key Management Models
# ---------------------------------------------------------------------------
class OrgApiKey(db.Model):
    """Organization-level API Key for external integrations."""
    __tablename__ = 'org_api_keys'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, unique=True)
    api_key_hash = db.Column(db.String(255), unique=True, nullable=False)
    key_prefix = db.Column(db.String(30), default='qcms_live_')
    secret_key_masked = db.Column(db.String(255))
    status = db.Column(db.String(20), default='Active')  # Active, Disabled
    usage_count = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = db.relationship('Organization', backref=db.backref('org_api_key_rec', uselist=False))


class ImportedIdea(db.Model):
    """Approved ideas received from external tools (e.g. Ideation Tool)."""
    __tablename__ = 'imported_ideas'
    __table_args__ = (db.UniqueConstraint('organization_id', 'idea_code', name='uq_org_idea_code'),)

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    idea_code = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    problem_statement = db.Column(db.Text)
    proposed_solution = db.Column(db.Text)
    department = db.Column(db.String(255))
    category = db.Column(db.String(255))
    submitted_by = db.Column(db.String(255))
    co_suggesters = db.Column(db.JSON, default=list)
    tangible_benefit = db.Column(db.Float)
    intangible_benefit = db.Column(db.Text)
    investment_required = db.Column(db.Float)
    implementation_time = db.Column(db.String(100))
    impact_level = db.Column(db.String(50))
    status = db.Column(db.String(50), default='Approved')
    source = db.Column(db.String(100), default='Ideation Tool')
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)
    linked_project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'idea_code': self.idea_code,
            'title': self.title,
            'problem_statement': self.problem_statement,
            'proposed_solution': self.proposed_solution,
            'department': self.department,
            'category': self.category,
            'submitted_by': self.submitted_by,
            'co_suggesters': self.co_suggesters,
            'tangible_benefit': self.tangible_benefit,
            'intangible_benefit': self.intangible_benefit,
            'investment_required': self.investment_required,
            'implementation_time': self.implementation_time,
            'impact_level': self.impact_level,
            'status': self.status,
            'source': self.source,
            'imported_at': self.imported_at.isoformat() if self.imported_at else None,
            'linked_project_id': self.linked_project_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class IntegrationApiLog(db.Model):
    """Audit log for API requests received via Integration API."""
    __tablename__ = 'integration_api_logs'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    ip_address = db.Column(db.String(50))
    api_key_used = db.Column(db.String(100))
    request_time = db.Column(db.DateTime, default=datetime.utcnow)
    response_time_ms = db.Column(db.Float, default=0.0)
    endpoint = db.Column(db.String(255))
    status_code = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Document Identity, Branding & Template Management System & Usage Mapping Models
# ---------------------------------------------------------------------------

class PlatformIdentityConfig(db.Model):
    """Centralized Platform Identity parameters."""
    __tablename__ = 'platform_identity'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    software_name = db.Column(db.String(255), default="QCMS Enterprise OS")
    software_short_name = db.Column(db.String(100), default="QCMS")
    software_display_name = db.Column(db.String(255), default="QCMS Enterprise Platform")
    platform_title = db.Column(db.String(255), default="QCMS Quality Management System")
    platform_subtitle = db.Column(db.String(255), default="Enterprise Quality & Compliance Management System")
    tagline = db.Column(db.String(255), default="Accelerating Enterprise Excellence & Compliance")
    version = db.Column(db.String(50), default="v4.8.2-PROD")
    edition = db.Column(db.String(100), default="Enterprise Cloud Edition")
    website = db.Column(db.String(255), default="https://qcms.io")
    support_portal = db.Column(db.String(255), default="https://support.qcms.io")
    copyright_text = db.Column(db.String(255), default="© 2026 QCMS Enterprise Solutions. All rights reserved.")
    footer_copyright = db.Column(db.String(255), default="Confidential & Proprietary — Generated by QCMS Enterprise OS")
    default_language = db.Column(db.String(20), default="en")
    default_currency = db.Column(db.String(10), default="INR")
    default_timezone = db.Column(db.String(50), default="UTC")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompanyInformationConfig(db.Model):
    """Legal & Corporate Company Information parameters."""
    __tablename__ = 'company_information'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    legal_company_name = db.Column(db.String(255), default="QCMS Technologies Pvt Ltd")
    trading_name = db.Column(db.String(255), default="QCMS Solutions")
    company_description = db.Column(db.Text, default="Enterprise Quality, Compliance & SOP Management Software")
    gstin = db.Column(db.String(50), default="27AAACQ1234F1Z9")
    pan = db.Column(db.String(50), default="AAACQ1234F")
    cin = db.Column(db.String(50), default="U72200MH2026PTC123456")
    msme = db.Column(db.String(50), default="UDYAM-MH-01-0012345")
    registration_number = db.Column(db.String(100), default="REG-2026-98765")
    tax_number = db.Column(db.String(100), default="TAX-IN-889977")
    license_number = db.Column(db.String(100), default="LIC-QCMS-ENT-2026")
    trademark = db.Column(db.String(255), default="QCMS® Registered Trademark")
    official_seal_url = db.Column(db.String(500), default="/assets/img/official_seal.png")
    digital_signature_url = db.Column(db.String(500), default="/assets/img/digital_signature.png")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompanyContactsConfig(db.Model):
    """Company Contact Directory parameters."""
    __tablename__ = 'company_contacts'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    general_email = db.Column(db.String(255), default="info@qcms.com")
    general_sender_name = db.Column(db.String(255), default="QCMS General Info")
    support_email = db.Column(db.String(255), default="support@ifqm.org.in")
    support_sender_name = db.Column(db.String(255), default="QCMS Customer Support")
    billing_email = db.Column(db.String(255), default="billing@qcms.com")
    billing_sender_name = db.Column(db.String(255), default="QCMS Accounts & Billing")
    otp_email = db.Column(db.String(255), default="otp-auth@qcms.com")
    otp_sender_name = db.Column(db.String(255), default="QCMS OTP Verification")
    contact_email = db.Column(db.String(255), default="contact@qcms.com")
    contact_sender_name = db.Column(db.String(255), default="QCMS Business Inquiries")
    alerts_email = db.Column(db.String(255), default="alerts@qcms.com")
    alerts_sender_name = db.Column(db.String(255), default="QCMS System Alerts")
    feedback_email = db.Column(db.String(255), default="feedback@qcms.com")
    feedback_sender_name = db.Column(db.String(255), default="QCMS Product Feedback")
    onboarding_email = db.Column(db.String(255), default="onboarding@qcms.com")
    onboarding_sender_name = db.Column(db.String(255), default="QCMS User Onboarding")
    sales_email = db.Column(db.String(255), default="sales@qcms.com")
    legal_email = db.Column(db.String(255), default="legal@qcms.com")
    compliance_email = db.Column(db.String(255), default="compliance@qcms.com")
    privacy_email = db.Column(db.String(255), default="privacy@qcms.com")
    general_phone = db.Column(db.String(50), default="+1 (800) 555-0199")
    support_phone = db.Column(db.String(50), default="+1 (800) 555-0100")
    emergency_contact = db.Column(db.String(50), default="+91 98765 43210")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompanyAddressesConfig(db.Model):
    """Office Address parameters."""
    __tablename__ = 'company_addresses'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    registered_office = db.Column(db.Text, default="Suite 800, Innovation Tower, BKC, Mumbai, MH 400051, India")
    corporate_office = db.Column(db.Text, default="Tech Park Phase 2, Whitefield, Bengaluru, KA 560066, India")
    billing_office = db.Column(db.Text, default="Financial Center, Suite 400, Mumbai, MH 400051, India")
    country = db.Column(db.String(100), default="India")
    state = db.Column(db.String(100), default="Maharashtra")
    city = db.Column(db.String(100), default="Mumbai")
    pin = db.Column(db.String(20), default="400051")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BrandingAssetsConfig(db.Model):
    """Branding Asset URLs & Graphics."""
    __tablename__ = 'branding_assets'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    favicon_url = db.Column(db.String(500), default="/assets/img/favicon.ico")
    logo_url = db.Column(db.String(500), default="/assets/img/logo.png")
    dark_logo_url = db.Column(db.String(500), default="/assets/img/logo-dark.png")
    light_logo_url = db.Column(db.String(500), default="/assets/img/logo-light.png")
    print_logo_url = db.Column(db.String(500), default="/assets/img/logo-print.png")
    pdf_logo_url = db.Column(db.String(500), default="/assets/img/logo-pdf.png")
    email_logo_url = db.Column(db.String(500), default="/assets/img/logo-email.png")
    watermark_logo_url = db.Column(db.String(500), default="/assets/img/watermark.png")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DocumentTemplateConfig(db.Model):
    """Document Branding & Template Config per document type."""
    __tablename__ = 'document_templates'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    template_key = db.Column(db.String(100), nullable=False)
    template_name = db.Column(db.String(255), nullable=False)
    header_title = db.Column(db.String(255))
    subtitle = db.Column(db.String(255))
    header_text = db.Column(db.Text)
    footer_text = db.Column(db.Text)
    watermark_text = db.Column(db.String(255), default="CONFIDENTIAL")
    confidential_text = db.Column(db.String(255), default="STRICTLY CONFIDENTIAL — INTERNAL USE ONLY")
    terms_and_conditions = db.Column(db.Text)
    disclaimer_text = db.Column(db.Text)
    enable_qr_verification = db.Column(db.Boolean, default=True)
    enable_digital_signature = db.Column(db.Boolean, default=True)
    settings_json = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SettingUsageMap(db.Model):
    """Usage Mapping & Dependency Explorer registry."""
    __tablename__ = 'setting_usage_map'

    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), nullable=False, index=True)
    setting_name = db.Column(db.String(255), nullable=False)
    module = db.Column(db.String(100), nullable=False)
    feature = db.Column(db.String(100), nullable=False)
    component = db.Column(db.String(255), nullable=False)
    page = db.Column(db.String(255))
    route = db.Column(db.String(255))
    backend_service = db.Column(db.String(255))
    document_type = db.Column(db.String(100))
    template = db.Column(db.String(255))
    export_type = db.Column(db.String(50))
    file_path = db.Column(db.String(500))
    dependency_type = db.Column(db.String(50), default="Direct")
    usage_category = db.Column(db.String(50), default="Branding")
    last_verified = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'setting_key': self.setting_key,
            'setting_name': self.setting_name,
            'module': self.module,
            'feature': self.feature,
            'component': self.component,
            'page': self.page,
            'route': self.route,
            'backend_service': self.backend_service,
            'document_type': self.document_type,
            'template': self.template,
            'export_type': self.export_type,
            'file_path': self.file_path,
            'dependency_type': self.dependency_type,
            'usage_category': self.usage_category,
            'last_verified': self.last_verified.isoformat() if self.last_verified else None
        }


# ---------------------------------------------------------------------------
# Email Notification & Automation Rules Models
# ---------------------------------------------------------------------------

class EmailNotificationRule(db.Model):
    """Configuration for Automated & Broadcast Email Notifications."""
    __tablename__ = 'email_notification_rules'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), default='custom') # subscription_reminder, trial_reminder, maintenance, welcome, usage_guide, new_feature, support, custom
    description = db.Column(db.Text, nullable=True)
    
    # Email Content
    subject = db.Column(db.String(500), nullable=False)
    preheader = db.Column(db.String(255), nullable=True)
    heading = db.Column(db.String(255), nullable=True)
    body_html = db.Column(db.Text, nullable=False)
    banner_color = db.Column(db.String(50), default='#2563eb')
    cta_text = db.Column(db.String(100), nullable=True)
    cta_url = db.Column(db.String(500), nullable=True)
    
    # Sender Configuration
    sender_email = db.Column(db.String(255), default='notifications@qcms.com')
    sender_name = db.Column(db.String(255), default='QCMS Enterprise Notifications')
    reply_to = db.Column(db.String(255), nullable=True)
    
    # Triggers & Timing
    trigger_type = db.Column(db.String(50), default='manual') # event, scheduled, manual
    event_trigger = db.Column(db.String(100), nullable=True) # subscription_expiring_soon, trial_expiring_soon, subscription_expired, new_org_welcome, new_user_welcome
    trigger_days_before = db.Column(db.Integer, default=7) # e.g. 7, 3, 1, 0
    scheduled_at = db.Column(db.DateTime, nullable=True)
    
    # Audience & Targeting Filters
    target_audience_type = db.Column(db.String(50), default='all') # all, specific_orgs, role_based, subscription_based
    target_org_ids = db.Column(db.JSON, default=list) # [1, 2, 3] or []
    target_roles = db.Column(db.JSON, default=list) # ["Admin", "CEO", "All"]
    target_plans = db.Column(db.JSON, default=list) # ["Small MSME's", "Enterprise"]
    target_statuses = db.Column(db.JSON, default=list) # ["Active", "Trial", "Expiring", "Suspended"]
    
    # State & Audit
    is_active = db.Column(db.Boolean, default=True)
    is_system_preset = db.Column(db.Boolean, default=False)
    last_triggered_at = db.Column(db.DateTime, nullable=True)
    total_sent = db.Column(db.Integer, default=0)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description or '',
            'subject': self.subject,
            'preheader': self.preheader or '',
            'heading': self.heading or '',
            'body_html': self.body_html,
            'banner_color': self.banner_color or '#2563eb',
            'cta_text': self.cta_text or '',
            'cta_url': self.cta_url or '',
            'sender_email': self.sender_email,
            'sender_name': self.sender_name,
            'reply_to': self.reply_to or '',
            'trigger_type': self.trigger_type,
            'event_trigger': self.event_trigger or '',
            'trigger_days_before': self.trigger_days_before,
            'scheduled_at': self.scheduled_at.isoformat() + 'Z' if self.scheduled_at else None,
            'target_audience_type': self.target_audience_type,
            'target_org_ids': self.target_org_ids or [],
            'target_roles': self.target_roles or [],
            'target_plans': self.target_plans or [],
            'target_statuses': self.target_statuses or [],
            'is_active': self.is_active,
            'is_system_preset': self.is_system_preset,
            'last_triggered_at': self.last_triggered_at.isoformat() + 'Z' if self.last_triggered_at else None,
            'total_sent': self.total_sent or 0,
            'created_by': self.created_by.username if self.created_by else 'Super Admin',
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None
        }


class EmailNotificationLog(db.Model):
    """Delivery log for email notifications sent via rules or manual broadcasts."""
    __tablename__ = 'email_notification_logs'

    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('email_notification_rules.id', ondelete='SET NULL'), nullable=True)
    rule_name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), default='custom')
    subject = db.Column(db.String(500), nullable=False)
    sender_email = db.Column(db.String(255), nullable=False)
    sender_name = db.Column(db.String(255), nullable=True)
    recipient_count = db.Column(db.Integer, default=0)
    recipients_summary = db.Column(db.JSON, default=list)
    status = db.Column(db.String(50), default='Delivered') # Delivered, Failed, Partially Delivered, Processing
    error_message = db.Column(db.Text, nullable=True)
    sent_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

    rule = db.relationship('EmailNotificationRule', foreign_keys=[rule_id])
    sent_by = db.relationship('User', foreign_keys=[sent_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'category': self.category,
            'subject': self.subject,
            'sender_email': self.sender_email,
            'sender_name': self.sender_name or '',
            'recipient_count': self.recipient_count,
            'recipients_summary': self.recipients_summary or [],
            'status': self.status,
            'error_message': self.error_message or '',
            'sent_by': self.sent_by.username if self.sent_by else 'System Automation',
            'sent_at': self.sent_at.isoformat() + 'Z' if self.sent_at else None
        }


