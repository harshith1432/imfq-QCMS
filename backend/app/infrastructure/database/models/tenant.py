from datetime import datetime
import json
import os
from sqlalchemy.dialects.postgresql import ARRAY
from app import db, bcrypt
from .base import SafeVector, Vector, is_local, _utc_now

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
    project_inactivity_days = db.Column(db.Integer, default=30)
    
    # Compliance
    compliance_standards = db.Column(db.JSON, default=[]) # e.g. ["ISO 9001", "AS9100"]
    
    # SaaS Subscription
    subscription_plan = db.Column(db.String(50), default='Trial', index=True) # Trial, Starter, Professional, Enterprise
    subscription_status = db.Column(db.String(20), default='Trialing', index=True) # Trialing, Active, Expired, Canceled
    trial_ends_at = db.Column(db.DateTime, index=True)
    max_users = db.Column(db.Integer, default=500)
    max_locations = db.Column(db.Integer, default=5)
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

    license_start_date = db.Column(db.DateTime, default=_utc_now)
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
    signoff_hierarchy_config = db.Column(db.JSON, nullable=True)  # List of hierarchy roles for PDF report sign-off
    
    created_at = db.Column(db.DateTime, default=_utc_now, index=True)
    
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
            ]
        },
        {
            "stage_id": 6, "original_id": 6,
            "title": "S6 Implement Corrective Actions", "icon": "settings-2",
            "sections": [
                {"id": "s6_countermeasures", "type": "table", "label": "Countermeasures", "order": 1},
                {"id": "s6_tasks", "type": "table", "label": "Countermeasure Task Assignments", "order": 2},
                {"id": "s6_resource_planning_deployment", "type": "table", "label": "Resource Planning & Deployment", "order": 3},
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
        try:
            from .billing import PlatformSettings
            ps = PlatformSettings.query.first()
        except Exception:
            ps = None
        base_defaults = (ps and ps.global_stages_config) or self.DEFAULT_STAGES_CONFIG
        
        raw = self.stages_config
        if raw and len(raw) > 0:
            # Back-fill sections from defaults only for stages that have no sections defined at all
            default_map = {d["original_id"]: d for d in base_defaults}
            result = []
            for stage in raw:
                s = copy.deepcopy(stage)
                oid = s.get("original_id", s.get("stage_id", 1))
                default_stage = default_map.get(oid, {})
                if not s.get("sections"):
                    s["sections"] = copy.deepcopy(
                        default_stage.get("sections", [])
                    )
                result.append(s)

            # Enforce positional invariance: Project Initiation is always Stage 1 (Index 0),
            # Project Closure is always the Final Stage (Last Index), and all intermediate stages sit in the middle.
            if len(result) >= 2:
                closure_idx = None
                for idx, stg in enumerate(result):
                    if stg.get("original_id") == 8 or "closure" in stg.get("title", "").lower() or "congratulat" in stg.get("title", "").lower():
                        closure_idx = idx
                        break
                if closure_idx is not None and closure_idx != len(result) - 1:
                    closure_stg = result.pop(closure_idx)
                    result.append(closure_stg)

                init_idx = None
                for idx, stg in enumerate(result):
                    if stg.get("original_id") == 1 or "initiat" in stg.get("title", "").lower():
                        init_idx = idx
                        break
                if init_idx is not None and init_idx != 0:
                    init_stg = result.pop(init_idx)
                    result.insert(0, init_stg)

                for idx, stg in enumerate(result):
                    stg["stage_id"] = idx + 1

            return result
        return copy.deepcopy(base_defaults)

class Plant(db.Model):
    __tablename__ = 'plants'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=_utc_now, index=True)

    departments = db.relationship('Department', backref='plant', lazy=True)
    users = db.relationship('User', backref='plant', lazy=True)

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plants.id'), nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=_utc_now, index=True)
    
    users_in_dept = db.relationship('User', backref='dept', lazy=True)


class OrganizationFeatureOverride(db.Model):
    """Organization-level feature flag override (e.g. Add-on features purchased by specific tenant)"""
    __tablename__ = 'organization_features'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)

    organization = db.relationship('Organization', backref=db.backref('feature_overrides', lazy=True, cascade='all, delete-orphan'))
    module = db.relationship('Module', backref=db.backref('org_overrides', lazy=True, cascade='all, delete-orphan'))



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
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)

    organization = db.relationship('Organization', backref=db.backref('org_api_key_rec', uselist=False))


