from datetime import datetime
from datetime import timezone, timezone
import json
import os
from sqlalchemy.dialects.postgresql import ARRAY
from app import db, bcrypt
from .base import SafeVector, Vector, is_local, _utc_now

class Project(db.Model):
    __tablename__ = 'projects'
    __table_args__ = (
        db.Index('idx_project_org_status_created', 'org_id', 'status', 'created_at'),
        db.Index('idx_project_org_status', 'org_id', 'status'),
        db.Index('idx_project_org_created', 'org_id', 'created_at'),
        db.Index('idx_project_plant', 'plant'),
        db.Index('idx_project_dept', 'department_id'),
    )
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_uid = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    category = db.Column(db.String(20))
    team_leader_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    facilitator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    deadline = db.Column(db.Date, nullable=True)
    current_stage = db.Column(db.Integer, default=1)
    status = db.Column(db.String(50), default='In Progress')
    start_date = db.Column(db.Date, default=_utc_now)
    end_date = db.Column(db.Date)
    
    work_area = db.Column(db.String(255))
    plant = db.Column(db.String(255))
    project_source = db.Column(db.String(100))
    reference_number = db.Column(db.String(100))
    sponsor = db.Column(db.String(255))
    rejection_reason = db.Column(db.Text, nullable=True)
    
    stages_config = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=_utc_now)
    
    members = db.relationship('User', secondary='project_members', backref='projects')
    workflow = db.relationship('ProjectWorkflow', backref='project', lazy=True, cascade="all, delete-orphan")
    stage_tracker = db.relationship('ProjectStageTracker', backref='project', lazy=True, cascade="all, delete-orphan")

    department = db.relationship('Department', backref='projects_in_dept', lazy=True)
    creator = db.relationship('User', foreign_keys=[creator_id], backref='created_projects')
    team_leader = db.relationship('User', foreign_keys=[team_leader_id], backref='led_projects')
    facilitator = db.relationship('User', foreign_keys=[facilitator_id], backref='facilitated_projects')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id], backref='reviewed_projects')

class ProjectMember(db.Model):
    __tablename__ = 'project_members'
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)

class ProjectStageTracker(db.Model):
    __tablename__ = 'project_stage_tracker'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='In Progress')
    started_at = db.Column(db.DateTime, default=_utc_now)
    completed_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)

    __table_args__ = (
        db.UniqueConstraint('project_id', 'stage_number', name='uq_project_stage'),
    )

class ProjectWorkflow(db.Model):
    __tablename__ = 'project_workflow'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer, nullable=False)
    data = db.Column(db.JSON, default={})
    template_snapshot = db.Column(db.JSON, nullable=True)
    completed_at = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)
    version_id = db.Column(db.Integer, nullable=False, default=1)

    __mapper_args__ = {
        'version_id_col': version_id
    }

class ProjectMeeting(db.Model):
    __tablename__ = 'project_meetings'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    meeting_type = db.Column(db.String(50), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=_utc_now)

    project = db.relationship('Project', backref=db.backref('meetings', lazy=True, cascade="all, delete-orphan"))

class Stage1ProblemDefinitionProjectInitiation(db.Model):
    __tablename__ = 'stage_1_problem_definition_project_initiation'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, unique=True)
    
    project_team = db.Column(db.JSON)
    problem_5w2h = db.Column(db.JSON)
    current_performance = db.Column(db.JSON)
    justification = db.Column(db.JSON)
    emergency_response = db.Column(db.JSON)
    theme_target_schedule = db.Column(db.JSON)
    
    facilitator_approved = db.Column(db.Boolean, default=False)
    facilitator_approver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    facilitator_approved_at = db.Column(db.DateTime)
    facilitator_comments = db.Column(db.Text)

    is_approved = db.Column(db.Boolean, default=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    approval_comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=_utc_now)
    project_ref = db.relationship('Project', backref=db.backref('stage1_details', uselist=False))

class Stage2ObservationDataCollection(db.Model):
    __tablename__ = 'stage_2_observation_data_collection'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, unique=True)

    containment_actions = db.Column(db.JSON)
    data_collection_plan = db.Column(db.JSON)
    gemba_observations = db.Column(db.JSON)
    interim_verification = db.Column(db.JSON)

    @property
    def standard_verification(self):
        return self.interim_verification

    @standard_verification.setter
    def standard_verification(self, value):
        self.interim_verification = value

    reviewer_approval = db.Column(db.Boolean, default=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewer_approved_at = db.Column(db.DateTime)
    reviewer_comments = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=_utc_now)
    project_ref = db.relationship('Project', backref=db.backref('stage2_details', uselist=False))

class Stage3CauseIdentification(db.Model):
    __tablename__ = 'stage_3_cause_identification'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, unique=True)

    brainstorming_ideas = db.Column(db.JSON)
    cause_and_effect = db.Column(db.JSON)
    stratification_data = db.Column(db.JSON)
    shortlisted_causes = db.Column(db.JSON)

    facilitator_approved = db.Column(db.Boolean, default=False)
    facilitator_approver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    facilitator_approved_at = db.Column(db.DateTime)
    facilitator_comments = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=_utc_now)
    project_ref = db.relationship('Project', backref=db.backref('stage3_details', uselist=False))

class Stage4RootCauseAnalysisVerification(db.Model):
    __tablename__ = 'stage_4_root_cause_analysis_verification'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, unique=True)

    five_why_analysis = db.Column(db.JSON)
    root_cause_verification = db.Column(db.JSON)
    escape_point_analysis = db.Column(db.JSON)
    statistical_validation = db.Column(db.JSON)

    reviewer_approval = db.Column(db.Boolean, default=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewer_approved_at = db.Column(db.DateTime)
    reviewer_comments = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=_utc_now)
    project_ref = db.relationship('Project', backref=db.backref('stage4_details', uselist=False))

class Stage5CountermeasurePlanningSolutionDevelopment(db.Model):
    __tablename__ = 'stage_5_countermeasure_planning_solution_development'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, unique=True)

    proposed_countermeasures = db.Column(db.JSON)
    solution_evaluation_matrix = db.Column(db.JSON)
    risk_assessment_fmea = db.Column(db.JSON)
    action_plan_5w1h = db.Column(db.JSON)

    facilitator_approval = db.Column(db.Boolean, default=False)
    facilitator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    facilitator_approved_at = db.Column(db.DateTime)
    facilitator_comments = db.Column(db.Text)

    reviewer_approval = db.Column(db.Boolean, default=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewer_approved_at = db.Column(db.DateTime)
    reviewer_comments = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=_utc_now)
    project_ref = db.relationship('Project', backref=db.backref('stage5_details', uselist=False))

class Stage6ImplementationChangeManagement(db.Model):
    __tablename__ = 'stage_6_implementation_change_management'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, unique=True)

    pilot_execution = db.Column(db.JSON)
    full_scale_implementation = db.Column(db.JSON)
    training_and_sop = db.Column(db.JSON)
    change_management_log = db.Column(db.JSON)

    reviewer_approval = db.Column(db.Boolean, default=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewer_approved_at = db.Column(db.DateTime)
    reviewer_comments = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=_utc_now)
    project_ref = db.relationship('Project', backref=db.backref('stage6_details', uselist=False))

class Stage7PerformanceVerificationBenefitsRealization(db.Model):
    __tablename__ = 'stage_7_performance_verification_benefits_realization'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, unique=True)

    before_after_comparison = db.Column(db.JSON)
    tangible_benefits = db.Column(db.JSON)
    intangible_benefits = db.Column(db.JSON)
    sustainability_checks = db.Column(db.JSON)

    reviewer_approval = db.Column(db.Boolean, default=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewer_approved_at = db.Column(db.DateTime)
    reviewer_comments = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=_utc_now)
    project_ref = db.relationship('Project', backref=db.backref('stage7_details', uselist=False))

class Stage8StandardizationKnowledgeSharingProjectClosure(db.Model):
    __tablename__ = 'stage_8_standardization_knowledge_sharing_project_closure'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, unique=True)

    sop_standardization = db.Column(db.JSON)
    horizontal_deployment = db.Column(db.JSON)
    lessons_learned = db.Column(db.JSON)
    team_recognition = db.Column(db.JSON)
    
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

    created_at = db.Column(db.DateTime, default=_utc_now)
    project_ref = db.relationship('Project', backref=db.backref('stage8_closure', uselist=False))

class ProjectReview(db.Model):
    __tablename__ = 'project_reviews'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_number = db.Column(db.Integer)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(20), default='Pending')
    decision = db.Column(db.String(20))
    comments = db.Column(db.Text)
    decided_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=_utc_now)
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
    updated_at = db.Column(db.DateTime, default=_utc_now)

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
    created_at = db.Column(db.DateTime, default=_utc_now, index=True)

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
    last_updated = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)

    employee = db.relationship('User', backref=db.backref('leaderboard_entry', uselist=False, cascade='all, delete-orphan'))
    organization = db.relationship('Organization', backref='leaderboard_entries')

class FacilitatorNote(db.Model):
    __tablename__ = 'facilitator_notes'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_number = db.Column(db.Integer, nullable=False)
    note_text = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=_utc_now)

    project_ref = db.relationship('Project', backref=db.backref('facilitator_notes', lazy=True))
    author = db.relationship('User', backref='facilitator_notes')

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
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)

    project = db.relationship('Project', backref=db.backref('assistance_requests', lazy=True, cascade="all, delete-orphan"))
    requester = db.relationship('User', foreign_keys=[user_id], backref=db.backref('sent_assistance_requests', lazy=True))
    facilitator = db.relationship('User', foreign_keys=[facilitator_id], backref=db.backref('received_assistance_requests', lazy=True))

class ImportedIdea(db.Model):
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
    imported_at = db.Column(db.DateTime, default=_utc_now)
    linked_project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)

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

# Domain & Backward-Compatibility Aliases
Stage1 = Stage1ProblemDefinitionProjectInitiation
Stage2 = Stage2ObservationDataCollection
Stage3 = Stage3CauseIdentification
Stage4 = Stage4RootCauseAnalysisVerification
Stage5 = Stage5CountermeasurePlanningSolutionDevelopment
Stage6 = Stage6ImplementationChangeManagement
Stage7Performance = Stage7PerformanceVerificationBenefitsRealization
Stage7Development = Stage7PerformanceVerificationBenefitsRealization
Stage7 = Stage7PerformanceVerificationBenefitsRealization
Stage8Standardization = Stage8StandardizationKnowledgeSharingProjectClosure
Stage8Implementation = Stage8StandardizationKnowledgeSharingProjectClosure
Stage8 = Stage8StandardizationKnowledgeSharingProjectClosure

Stage1ProblemDefinition = Stage1ProblemDefinitionProjectInitiation
Stage2Observation = Stage2ObservationDataCollection
Stage3Cause = Stage3CauseIdentification
Stage4RootCause = Stage4RootCauseAnalysisVerification
Stage5Countermeasure = Stage5CountermeasurePlanningSolutionDevelopment
Stage6Implementation = Stage6ImplementationChangeManagement

Stage1Identification = Stage1ProblemDefinitionProjectInitiation
Stage2Selection = Stage2ObservationDataCollection
Stage3Analysis = Stage3CauseIdentification
Stage4Causes = Stage4RootCauseAnalysisVerification
Stage5RootCause = Stage5CountermeasurePlanningSolutionDevelopment
Stage6DataAnalysis = Stage6ImplementationChangeManagement
Stage1Problem = Stage1ProblemDefinitionProjectInitiation
Stage3RCA = Stage4RootCauseAnalysisVerification
Stage4Solution = Stage7PerformanceVerificationBenefitsRealization
Stage5Approval = Stage7PerformanceVerificationBenefitsRealization
Stage7Impact = Stage8StandardizationKnowledgeSharingProjectClosure
