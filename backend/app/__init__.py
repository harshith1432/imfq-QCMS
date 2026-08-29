import os
import click
from flask import Flask, jsonify, send_from_directory, request, redirect
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from dotenv import load_dotenv
from flask_migrate import Migrate
from datetime import datetime, timezone
from .boot_utils import bootstrap_database

from app.config import Config

db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()
migrate = Migrate()

_DB_AUTO_MIGRATED = False

def create_app():
    # Bootstrap database (create if missing)
    bootstrap_database()

    # Resolve frontend folder path (../frontend relative to backend/)
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend'))

    app = Flask(__name__, static_folder=None)
    # x_for=1 means trust exactly 1 upstream proxy (e.g. Nginx or Cloudflare)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Load configuration from centralized settings
    app.config.from_object(Config)
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable static file caching for frontend
    
    # Ensure upload folder exists
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    except Exception:
        pass
    
    # Initialize Extensions
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    # Initialize Idempotency & Concurrency Middleware
    from app.presentation.middleware.idempotency_middleware import init_idempotency_middleware
    init_idempotency_middleware(app)

    # Initialize Structured Logging & Request Correlation ID Middleware (X-Request-ID)
    from app.presentation.middleware.logging_middleware import init_logging_middleware
    init_logging_middleware(app)

    # Configure JWT revocation / session termination verification with sub-millisecond in-memory / Redis caching
    from app.infrastructure.cache.redis_client import cache as session_cache

    @jwt.token_in_blocklist_loader
    def check_if_token_is_revoked(jwt_header, jwt_payload):
        try:
            session_id = jwt_payload.get("session_id")
            user_id = jwt_payload.get("sub")

            # 1. Fast Cache Check for Session ID (0.01ms vs 20ms DB query)
            if session_id:
                cached_status = session_cache.get(f"sess_status:{session_id}")
                if cached_status:
                    if cached_status in ('Terminated', 'Revoked'):
                        return True
                    elif cached_status == 'Active':
                        return False

            # 2. Fast Cache Check for User Active State
            if user_id:
                cached_u_status = session_cache.get(f"user_active:{user_id}")
                if cached_u_status == 'inactive':
                    return True

            from app.infrastructure.database.models.models import SaaSUserSession, User

            # 3. Check if user account itself has been deactivated or deleted (Cached for 120s)
            if user_id and session_cache.get(f"user_active:{user_id}") is None:
                try:
                    uid = int(user_id)
                    user = db.session.get(User, uid)
                    # User is inactive only if BOTH is_active=False AND status != 'Active'
                    # This prevents false session terminations when is_active has inconsistent state
                    is_truly_inactive = (
                        not user or
                        getattr(user, 'is_deleted', False) or
                        (not user.is_active and user.status not in ('Active', 'active'))
                    )
                    if is_truly_inactive:
                        session_cache.set(f"user_active:{user_id}", "inactive", ex=120)
                        return True
                    else:
                        session_cache.set(f"user_active:{user_id}", "active", ex=120)
                except Exception:
                    pass

            # 4. Fallback Session Lookup from DB (Cached for 300s)
            if session_id:
                sess = SaaSUserSession.query.filter_by(session_id=session_id).first()
                if sess:
                    session_cache.set(f"sess_status:{session_id}", sess.status, ex=300)
                    return sess.status in ('Terminated', 'Revoked')
                # If session_id claim exists but not yet in DB, cache as Active for 60s
                session_cache.set(f"sess_status:{session_id}", "Active", ex=60)
                return False

            elif user_id:
                try:
                    uid = int(user_id)
                    term_sess = SaaSUserSession.query.filter_by(user_id=uid, status='Terminated').order_by(SaaSUserSession.login_time.desc()).first()
                    if term_sess:
                        active_sess = SaaSUserSession.query.filter_by(user_id=uid, status='Active').order_by(SaaSUserSession.login_time.desc()).first()
                        if not active_sess or (active_sess.login_time and term_sess.login_time and active_sess.login_time < term_sess.login_time):
                            return True
                except (ValueError, TypeError):
                    pass
        except Exception as e:
            print(f"[QCMS JWT Revocation Check Exception] {e}")
        return False

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        from flask import jsonify
        return jsonify({
            "status": "error",
            "message": "Your session has been terminated by an administrator. Please sign in again.",
            "session_terminated": True
        }), 401
    
    # Print masked connection URL for logs
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    if db_uri and db_uri.startswith('postgresql'):
        try:
            from urllib.parse import urlparse
            result = urlparse(db_uri)
            masked_url = f"postgresql://{result.username}:****@{result.hostname}:{result.port or 5432}{result.path}"
            print(f"[QCMS] Connecting to database at: {masked_url}")
        except Exception:
            pass
            
    # Secure CORS configurations
    cors_origins = app.config.get('CORS_ORIGINS', '*')
    if cors_origins != '*':
        if isinstance(cors_origins, str):
            cors_origins = [origin.strip() for origin in cors_origins.split(',')]
    CORS(app, resources={r"/api/*": {"origins": cors_origins}})

    # Initialize Celery Distributed Worker Integration
    try:
        from .celery_app import make_celery
        make_celery(app)
    except Exception as cel_err:
        app.logger.warning(f"[QCMS] Celery initialization skipped: {cel_err}")
    
    with app.app_context():
        # Import all models first so db.create_all() knows about them
        from .infrastructure.database.models import models  # noqa: F401

        # Import and register Blueprints from presentation layer
        from .presentation.routes.auth_routes import auth_bp
        from .presentation.routes.project_routes import project_bp
        from .presentation.routes.workflow_routes import workflow_bp
        from .presentation.routes.analytics_routes import analytics_bp
        from .presentation.routes.admin_routes import admin_bp
        from .presentation.routes.facilitator_routes import facilitator_bp
        from .presentation.routes.reviewer_routes import reviewer_bp
        from .presentation.routes.team_leader_routes import team_leader_bp
        from .presentation.routes.team_member_routes import team_member_bp
        from .presentation.routes.qc_tools_routes import qc_tools_bp
        from .presentation.routes.dashboard_routes import dashboard_bp
        from .presentation.routes.repository_routes import repository_bp
        from .presentation.routes.rag_routes import rag_bp
        from .presentation.routes.super_admin_routes import super_admin_bp
        from .presentation.routes.super_admin_v1_routes import super_admin_v1_bp
        from .presentation.routes.ceo_routes import ceo_bp
        from .presentation.routes.notification_routes import notification_bp
        from .presentation.routes.reports_routes import reports_bp
        from .presentation.routes.subscription_routes import subscription_bp
        from .presentation.routes.license_routes import license_bp
        from .presentation.routes.modules_routes import modules_bp
        from .presentation.routes.support_routes import support_bp
        from .presentation.routes.billing_routes import billing_bp
        from .presentation.routes.audit_routes import audit_bp
        from .presentation.routes.announcement_routes import announcement_bp
        from .presentation.routes.integrations_routes import integrations_bp
        from .presentation.routes.integration_v1_routes import integration_v1_bp
        from .presentation.routes.sop_routes import sop_bp
        from .presentation.routes.document_branding_routes import document_branding_bp
        from .presentation.routes.feature_engine_routes import feature_engine_bp
        from .presentation.routes.email_notification_routes import email_notification_bp
        from .presentation.routes.points_routes import points_bp
        from .presentation.routes.plant_routes import plant_bp
        from .presentation.routes.storage_routes import storage_bp
        
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        app.register_blueprint(storage_bp, url_prefix='/api/storage')
        app.register_blueprint(project_bp, url_prefix='/api/projects')
        app.register_blueprint(workflow_bp, url_prefix='/api/workflow')
        app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
        app.register_blueprint(admin_bp, url_prefix='/api/admin')
        app.register_blueprint(plant_bp, url_prefix='/api/admin/plants')
        app.register_blueprint(facilitator_bp, url_prefix='/api/facilitator')
        app.register_blueprint(reviewer_bp, url_prefix='/api/reviewer')
        app.register_blueprint(team_leader_bp, url_prefix='/api/team-leader')
        app.register_blueprint(team_member_bp, url_prefix='/api/team-member')
        app.register_blueprint(qc_tools_bp, url_prefix='/api/project')
        app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
        app.register_blueprint(repository_bp, url_prefix='/api/repository')
        app.register_blueprint(rag_bp, url_prefix='/api/rag')
        app.register_blueprint(super_admin_bp, url_prefix='/api/super-admin')
        app.register_blueprint(super_admin_v1_bp, url_prefix='/api/v1')
        app.register_blueprint(ceo_bp, url_prefix='/api/ceo')
        app.register_blueprint(notification_bp, url_prefix='/api')
        app.register_blueprint(points_bp, url_prefix='/api')
        app.register_blueprint(reports_bp, url_prefix='/api/reports')
        app.register_blueprint(subscription_bp, url_prefix='/api/subscriptions')
        app.register_blueprint(license_bp, url_prefix='/api/licenses')
        app.register_blueprint(modules_bp, url_prefix='/api/modules')
        app.register_blueprint(modules_bp, url_prefix='/api/admin/modules', name='modules_admin_bp')
        app.register_blueprint(support_bp, url_prefix='/api/support')
        app.register_blueprint(billing_bp, url_prefix='/api/billing')
        app.register_blueprint(audit_bp)
        app.register_blueprint(announcement_bp)
        app.register_blueprint(email_notification_bp)
        app.register_blueprint(integrations_bp, url_prefix='/api/super-admin')
        app.register_blueprint(integration_v1_bp, url_prefix='/api/v1/integrations')
        app.register_blueprint(sop_bp, url_prefix='/api/sops')
        app.register_blueprint(sop_bp, url_prefix='/api/sop', name='sop_alias_bp')
        app.register_blueprint(document_branding_bp)
        app.register_blueprint(feature_engine_bp)

        # ── QCMS Security Middleware ───────────────────────────────────────────
        # Registers WAF, IP whitelist/blacklist, rate limiting, brute-force
        # protection, and security headers — all driven by security_settings in DB
        from .presentation.middleware.security import register_security_middleware
        register_security_middleware(app)

        global _DB_AUTO_MIGRATED
        if not _DB_AUTO_MIGRATED:
            try:
                # Schema management is handled via `flask init-db` CLI or Alembic migrations.
                # db.create_all() has been removed from startup to prevent race conditions
                # across multiple Gunicorn workers. Run `flask init-db` before first deploy.
                app.logger.debug('[QCMS] Startup: schema management skipped (use flask init-db).')

                # Startup performs only lightweight entity seeding and initial configuration checks.
                from .infrastructure.database.models.models import (
                    Role, PlatformSettings, User, Organization, UserCustomField,
                    SaaSPlan, SaaSPlanPricing, SaaSPlanLimits, SaaSPlanModules, SaaSPlanAnalytics,
                    EmployeePoints, EmployeeLeaderboard
                )
                orgs = Organization.query.all()
                for org in orgs:
                    # Clean up legacy system email field if present
                    legacy_email = UserCustomField.query.filter_by(org_id=org.id, field_key='email', is_system=True).first()
                    if legacy_email:
                        db.session.delete(legacy_email)

                    system_fields = [
                        ('username', 'User', True, True, 'both'),
                        ('phone', 'Phone Number', True, True, 'phone'),
                        ('role', 'User Role', True, True, 'both'),
                        ('department', 'Department', True, True, 'both'),
                        ('plant_location', 'Plant Location', True, True, 'both')
                    ]
                    for key, name, req, sys, dtype in system_fields:
                        existing_f = UserCustomField.query.filter_by(org_id=org.id, field_key=key).first()
                        if not existing_f:
                            db.session.add(UserCustomField(org_id=org.id, field_key=key, display_name=name, is_required=req, is_system=sys, data_type=dtype))
                        elif sys and not existing_f.is_system:
                            existing_f.is_system = True
                            existing_f.is_required = req
                db.session.commit()
                roles = ['SuperAdmin', 'Admin', 'Reviewer', 'Facilitator', 'Team Leader', 'Team Member', 'CEO']
                for r_name in roles:
                    if not Role.query.filter_by(name=r_name).first():
                        db.session.add(Role(name=r_name))
            
                # Seed Platform Settings
                ps = PlatformSettings.query.first()
                if not ps:
                    ps = PlatformSettings()
                    db.session.add(ps)
                    db.session.commit()

                # Seed Default SaaS Plans if not present
                if not SaaSPlan.query.first():
                    default_plans = [
                        SaaSPlan(name='Default Trial Plan', code='t1', plan_type='Trial', status='Active',
                                 is_default_trial=True, description='System default onboarding trial plan',
                                 trial_duration_days=14, auto_approve_extensions_limit=2),
                        SaaSPlan(name='Starter', code='starter', plan_type='Paid', status='Active',
                                 is_default_trial=False, description='Free starter plan for new organizations'),
                        SaaSPlan(name='Professional', code='professional', plan_type='Paid', status='Active',
                                 is_default_trial=False, description='Professional plan for growing organizations'),
                        SaaSPlan(name='Enterprise', code='enterprise', plan_type='Paid', status='Active',
                                 is_default_trial=False, description='Enterprise plan for large organizations'),
                    ]
                    for plan in default_plans:
                        db.session.add(plan)
                    db.session.commit()
                    print("[QCMS] Seeded default SaaS Plans (Trial/Starter/Professional/Enterprise) successfully.")
                else:
                    # Guarantee at least one system default trial plan exists
                    from sqlalchemy import func
                    trial_exists = SaaSPlan.query.filter(
                        (SaaSPlan.is_default_trial == True) | 
                        (func.lower(SaaSPlan.plan_type) == 'trial') |
                        (func.lower(SaaSPlan.code) == 't1')
                    ).first()
                    if not trial_exists:
                        def_trial = SaaSPlan(
                            name='Default Trial Plan',
                            code='t1',
                            plan_type='Trial',
                            status='Active',
                            is_default_trial=True,
                            description='System default onboarding trial plan',
                            trial_duration_days=14,
                            auto_approve_extensions_limit=2
                        )
                        db.session.add(def_trial)
                        db.session.commit()
                    # Guarantee default Pay-As-You-Go plan template exists
                    payg_exists = SaaSPlan.query.filter(
                        (SaaSPlan.plan_type == 'Pay-As-You-Go') | 
                        (SaaSPlan.pricing_model == 'pay_as_you_go') |
                        (func.lower(SaaSPlan.code) == 'payg')
                    ).first()
                    if not payg_exists:
                        from app.domain.services.payg_billing_service import DEFAULT_PAYG_RULES
                        def_payg = SaaSPlan(
                            name='Pay-As-You-Go (Metered)',
                            code='payg',
                            plan_type='Pay-As-You-Go',
                            pricing_model='pay_as_you_go',
                            payg_rules=DEFAULT_PAYG_RULES,
                            status='Active',
                            icon='gauge',
                            color='#8b5cf6',
                            is_custom=False,
                            is_default_trial=False,
                            description='Flexible metered billing based on active users, storage, projects, and API usage'
                        )
                        db.session.add(def_payg)
                        db.session.commit()
                        print("[QCMS] Created System Default Pay-As-You-Go Plan (payg).")




                from .infrastructure.database.models.models import Module, FeatureCategory
            
                # 1. Categories
                if not FeatureCategory.query.first():
                    cats = [
                        {"name": "Core", "code": "core", "icon": "folder", "order": 1},
                        {"name": "Quality", "code": "quality", "icon": "wrench", "order": 2},
                        {"name": "Reports", "code": "reports", "icon": "file-text", "order": 3},
                        {"name": "Analytics", "code": "analytics", "icon": "bar-chart-3", "order": 4},
                        {"name": "AI", "code": "ai", "icon": "bot", "order": 5},
                        {"name": "Integration", "code": "integration", "icon": "code-2", "order": 6},
                        {"name": "Support", "code": "support", "icon": "help-circle", "order": 7},
                        {"name": "Governance", "code": "governance", "icon": "shield-check", "order": 8},
                        {"name": "Communication", "code": "communication", "icon": "bell", "order": 9},
                        {"name": "IAM", "code": "iam", "icon": "users", "order": 10},
                        {"name": "Customization", "code": "customization", "icon": "palette", "order": 11},
                    ]
                    for c in cats:
                        db.session.add(FeatureCategory(name=c['name'], code=c['code'], icon=c['icon'], display_order=c['order']))
                    db.session.commit()

                # 2. Parent & Child Modules Hierarchy
                hierarchy_modules = [
                    # PARENT: Projects
                    {
                        "name": "Projects", "code": "projects", "category": "Core", "icon": "folder-git2", "color": "#3b82f6", "display_order": 1, "navigation_route": "/projects", "status": "Active", "version": "1.0.0", "system_module": True, "description": "Core project management workspace",
                        "children": [
                            {"name": "Projects Repository", "code": "projects.repository", "navigation_route": "/projects/repository"},
                            {"name": "Create Project", "code": "projects.create"},
                            {"name": "Edit Project", "code": "projects.edit"},
                            {"name": "Delete Project", "code": "projects.delete"},
                            {"name": "Archive Project", "code": "projects.archive"},
                            {"name": "Team Members", "code": "projects.team_members"},
                            {"name": "Meetings Log", "code": "projects.meetings"},
                            {"name": "Stage Gate Reviews", "code": "projects.reviews"},
                            {"name": "Project Attachments", "code": "projects.attachments"},
                            {"name": "Timeline & Gantt", "code": "projects.timeline"},
                            {"name": "Export Projects", "code": "projects.export"},
                            {"name": "Import Projects", "code": "projects.import"}
                        ]
                    },
                    # PARENT: QC Story Methodology
                    {
                        "name": "QC Story Methodology", "code": "qc_story", "category": "Quality", "icon": "award", "color": "#ec4899", "display_order": 2, "navigation_route": "/projects/workspace", "status": "Active", "version": "1.0.0", "system_module": True, "description": "8-Stage Quality Circle Improvement Methodology",
                        "children": [
                            {"name": "Stage 1: Problem Definition", "code": "qc_story.stage1"},
                            {"name": "Stage 2: Observation & Data Collection", "code": "qc_story.stage2"},
                            {"name": "Stage 3: Cause Analysis", "code": "qc_story.stage3"},
                            {"name": "Stage 4: Root Cause Verification", "code": "qc_story.stage4"},
                            {"name": "Stage 5: Countermeasure Planning", "code": "qc_story.stage5"},
                            {"name": "Stage 6: Implementation & Change", "code": "qc_story.stage6"},
                            {"name": "Stage 7: Performance Verification", "code": "qc_story.stage7"},
                            {"name": "Stage 8: Standardization & Closure", "code": "qc_story.stage8"}
                        ]
                    },
                    # PARENT: 7 QC Tools
                    {
                        "name": "7 QC Tools", "code": "qc_tools", "category": "Quality", "icon": "wrench", "color": "#f43f5e", "display_order": 3, "navigation_route": "/qc-tools", "status": "Active", "version": "1.1.0", "system_module": True, "description": "Interactive statistical 7 QC tools suite",
                        "children": [
                            {"name": "Check Sheet", "code": "qc_tools.checksheet"},
                            {"name": "Pareto Chart (80/20)", "code": "qc_tools.pareto"},
                            {"name": "Fishbone (Ishikawa 6M)", "code": "qc_tools.fishbone"},
                            {"name": "Scatter Diagram & Correlation", "code": "qc_tools.scatter"},
                            {"name": "Stratification Chart", "code": "qc_tools.stratification"},
                            {"name": "Process Map & Flowchart", "code": "qc_tools.process_map"},
                            {"name": "Control Chart (UCL/LCL)", "code": "qc_tools.control_chart"}
                        ]
                    },
                    # PARENT: SOP Management
                    {
                        "name": "SOP Management", "code": "sop", "category": "Quality", "icon": "book-open", "color": "#f59e0b", "display_order": 4, "navigation_route": "/compliance/sop", "status": "Active", "version": "1.0.1", "system_module": False, "description": "Standard Operating Procedure lifecycle management",
                        "children": [
                            {"name": "SOP Repository", "code": "sop.repository"},
                            {"name": "Create SOP", "code": "sop.create"},
                            {"name": "Edit SOP", "code": "sop.edit"},
                            {"name": "SOP Approvals", "code": "sop.approvals"},
                            {"name": "SOP Version Control", "code": "sop.version_control"},
                            {"name": "Archive SOP", "code": "sop.archive"},
                            {"name": "SOP PDF Export", "code": "sop.pdf"},
                            {"name": "SOP Comments", "code": "sop.comments"}
                        ]
                    },
                    # PARENT: Training & Assessment
                    {
                        "name": "Employee Training", "code": "training", "category": "Quality", "icon": "graduation-cap", "color": "#8b5cf6", "display_order": 5, "navigation_route": "/training", "status": "Active", "version": "1.0.0", "system_module": False, "description": "SOP reading, assessment and certificate engine",
                        "children": [
                            {"name": "Assign Training", "code": "training.assign"},
                            {"name": "Online Assessment", "code": "training.assessment"},
                            {"name": "Reading Progress Tracker", "code": "training.reading_progress"},
                            {"name": "Training Audit Reports", "code": "training.reports"}
                        ]
                    },
                    # PARENT: Reports Engine
                    {
                        "name": "Reports Engine", "code": "reports", "category": "Reports", "icon": "file-bar-chart", "color": "#10b981", "display_order": 6, "navigation_route": "/reports", "status": "Active", "version": "1.0.0", "system_module": True, "description": "PDF, Excel, CSV reports export engine",
                        "children": [
                            {"name": "PDF Export", "code": "reports.pdf"},
                            {"name": "Excel Export", "code": "reports.excel"},
                            {"name": "CSV Export", "code": "reports.csv"},
                            {"name": "Print Support", "code": "reports.print"},
                            {"name": "Custom Report Builder", "code": "reports.custom"},
                            {"name": "Scheduled Reports", "code": "reports.scheduled"}
                        ]
                    },
                    # PARENT: Analytics Platform
                    {
                        "name": "Analytics Platform", "code": "analytics", "category": "Analytics", "icon": "bar-chart-3", "color": "#6366f1", "display_order": 7, "navigation_route": "/analytics", "status": "Active", "version": "1.2.0", "system_module": False, "description": "Interactive KPI visualization and trends",
                        "children": [
                            {"name": "Analytics Dashboard", "code": "analytics.dashboard"},
                            {"name": "Project Analytics", "code": "analytics.project"},
                            {"name": "Department Analytics", "code": "analytics.department"},
                            {"name": "Executive Dashboard", "code": "analytics.executive"},
                            {"name": "KPI Tracker", "code": "analytics.kpi"},
                            {"name": "Performance Trends", "code": "analytics.trends"}
                        ]
                    },
                    # PARENT: Notifications & Communication
                    {
                        "name": "Notifications", "code": "notifications", "category": "Communication", "icon": "bell", "color": "#eab308", "display_order": 8, "navigation_route": "/announcements", "status": "Active", "version": "1.0.0", "system_module": False, "description": "Multi-channel notification broadcasts",
                        "children": [
                            {"name": "Announcements", "code": "notifications.announcements"},
                            {"name": "Email Notifications", "code": "notifications.email"},
                            {"name": "SMS Notifications", "code": "notifications.sms"},
                            {"name": "In-App Alerts", "code": "notifications.in_app"},
                            {"name": "Push Notifications", "code": "notifications.push"}
                        ]
                    },
                    # PARENT: Support Desk
                    {
                        "name": "Support Desk", "code": "support", "category": "Support", "icon": "help-circle", "color": "#06b6d4", "display_order": 9, "navigation_route": "/support", "status": "Active", "version": "1.0.0", "system_module": False, "description": "Ticketing system and SLA tracking",
                        "children": [
                            {"name": "Support Tickets", "code": "support.tickets"},
                            {"name": "SLA Management", "code": "support.sla"},
                            {"name": "Knowledge Base", "code": "support.knowledge_base"},
                            {"name": "Satisfaction Ratings", "code": "support.ratings"},
                            {"name": "Ticket Comments", "code": "support.comments"}
                        ]
                    },
                    # PARENT: Compliance Standards
                    {
                        "name": "Compliance Standards", "code": "compliance", "category": "Governance", "icon": "shield-check", "color": "#059669", "display_order": 10, "navigation_route": "/settings/compliance", "status": "Active", "version": "1.0.0", "system_module": False, "description": "ISO 9001, 14001, 45001 & IATF 16949 standards",
                        "children": [
                            {"name": "ISO 9001:2015", "code": "compliance.iso9001"},
                            {"name": "ISO 14001:2015", "code": "compliance.iso14001"},
                            {"name": "ISO 45001:2018", "code": "compliance.iso45001"},
                            {"name": "IATF 16949:2016", "code": "compliance.iatf"}
                        ]
                    },
                    # PARENT: AI Assistant
                    {
                        "name": "AI Assistant & RAG", "code": "ai", "category": "AI", "icon": "bot", "color": "#8b5cf6", "display_order": 11, "navigation_route": "/ai/assistant", "status": "Beta", "version": "0.9.0", "premium_feature": True, "ai_enabled": True, "beta_feature": True, "system_module": False, "description": "AI-powered RAG document search & root cause recommendations",
                        "children": [
                            {"name": "AI Assistant Chat", "code": "ai.chat"},
                            {"name": "AI Suggestions", "code": "ai.suggestions"},
                            {"name": "AI Reports Generator", "code": "ai.reports"},
                            {"name": "AI Root Cause Predictor", "code": "ai.root_cause"},
                            {"name": "AI Semantic Knowledge Search", "code": "ai.knowledge_search"}
                        ]
                    },
                    # PARENT: Integration Hub
                    {
                        "name": "Integration Hub", "code": "integrations", "category": "Integration", "icon": "code-2", "color": "#14b8a6", "display_order": 12, "navigation_route": "/settings/api", "status": "Active", "version": "2.0.0", "premium_feature": True, "system_module": False, "description": "REST API Key management, Webhooks & Developer Portal",
                        "children": [
                            {"name": "API Keys Management", "code": "integrations.api_keys"},
                            {"name": "Webhooks Subscriptions", "code": "integrations.webhooks"},
                            {"name": "Inbound Idea Import API", "code": "integrations.idea_import"},
                            {"name": "Developer Portal", "code": "integrations.developer_portal"},
                            {"name": "SDK Code Generator", "code": "integrations.sdk"}
                        ]
                    },
                    # PARENT: User Management
                    {
                        "name": "User Management", "code": "users", "category": "IAM", "icon": "users", "color": "#3b82f6", "display_order": 13, "navigation_route": "/admin/users", "status": "Active", "version": "1.0.0", "system_module": True, "description": "User CRUD, invitation & access control",
                        "children": [
                            {"name": "View Users", "code": "users.view"},
                            {"name": "Create User", "code": "users.create"},
                            {"name": "Edit User", "code": "users.edit"},
                            {"name": "Delete User", "code": "users.delete"},
                            {"name": "Invite User", "code": "users.invite"},
                            {"name": "Suspend User", "code": "users.suspend"},
                            {"name": "Import Users", "code": "users.import"},
                            {"name": "Export Users", "code": "users.export"}
                        ]
                    },
                    # PARENT: Departments
                    {
                        "name": "Departments", "code": "departments", "category": "IAM", "icon": "building", "color": "#64748b", "display_order": 14, "navigation_route": "/admin/departments", "status": "Active", "version": "1.0.0", "system_module": True, "description": "Department organizational structure",
                        "children": [
                            {"name": "View Departments", "code": "departments.view"},
                            {"name": "Create Department", "code": "departments.create"},
                            {"name": "Edit Department", "code": "departments.edit"},
                            {"name": "Delete Department", "code": "departments.delete"}
                        ]
                    },
                    # PARENT: Roles & Permissions
                    {
                        "name": "Roles & Permissions", "code": "roles", "category": "IAM", "icon": "shield", "color": "#475569", "display_order": 15, "navigation_route": "/admin/roles", "status": "Active", "version": "1.0.0", "system_module": True, "description": "Role definitions and action permissions",
                        "children": [
                            {"name": "View Roles", "code": "roles.view"},
                            {"name": "Create Role", "code": "roles.create"},
                            {"name": "Edit Role", "code": "roles.edit"},
                            {"name": "Delete Role", "code": "roles.delete"},
                            {"name": "Role Action Permissions", "code": "roles.permissions"}
                        ]
                    },
                    # PARENT: Organization Management
                    {
                        "name": "Organization Management", "code": "organization", "category": "Core", "icon": "globe", "color": "#2563eb", "display_order": 16, "navigation_route": "/admin/organization", "status": "Active", "version": "1.0.0", "system_module": True, "description": "Company profile, plants and business units",
                        "children": [
                            {"name": "Company Profile", "code": "organization.profile"},
                            {"name": "Manufacturing Plants", "code": "organization.plants"},
                            {"name": "Company Branches", "code": "organization.branches"},
                            {"name": "Business Units", "code": "organization.business_units"}
                        ]
                    },
                    # PARENT: Global Search
                    {
                        "name": "Global Search", "code": "search", "category": "Core", "icon": "search", "color": "#0284c7", "display_order": 17, "navigation_route": "/search", "status": "Active", "version": "1.0.0", "system_module": True, "description": "Universal search across projects and SOPs",
                        "children": [
                            {"name": "Global Search Bar", "code": "search.global"},
                            {"name": "Search Projects", "code": "search.projects"},
                            {"name": "Search SOPs", "code": "search.sops"}
                        ]
                    },
                    # PARENT: File Management
                    {
                        "name": "File Management", "code": "files", "category": "Core", "icon": "paperclip", "color": "#7c3aed", "display_order": 18, "navigation_route": "/files", "status": "Active", "version": "1.0.0", "system_module": True, "description": "Document uploads and version history",
                        "children": [
                            {"name": "Upload Files", "code": "files.upload"},
                            {"name": "Download Files", "code": "files.download"},
                            {"name": "Delete Files", "code": "files.delete"},
                            {"name": "File Version History", "code": "files.versions"}
                        ]
                    },
                    # PARENT: Workflow Engine
                    {
                        "name": "Workflow Engine", "code": "workflow", "category": "Core", "icon": "git-branch", "color": "#d97706", "display_order": 19, "navigation_route": "/workflow", "status": "Active", "version": "1.0.0", "system_module": True, "description": "Approval routing and escalation rules",
                        "children": [
                            {"name": "Approval Workflows", "code": "workflow.approvals"},
                            {"name": "Review Workflows", "code": "workflow.reviews"},
                            {"name": "Escalation Rules", "code": "workflow.escalation"},
                            {"name": "Auto Approval Rules", "code": "workflow.auto_approval"}
                        ]
                    },
                    # PARENT: Branding
                    {
                        "name": "White-Label Branding", "code": "branding", "category": "Customization", "icon": "palette", "color": "#06b6d4", "display_order": 20, "navigation_route": "/settings/branding", "status": "Active", "version": "1.0.0", "premium_feature": True, "system_module": False, "description": "Custom color branding, logo and domain routing",
                        "children": [
                            {"name": "Company Logo Upload", "code": "branding.logo"},
                            {"name": "Color Theme Customizer", "code": "branding.theme"},
                            {"name": "Branding Details", "code": "branding.company_details"}
                        ]
                    },
                    # PARENT: Localization
                    {
                        "name": "Localization & i18n", "code": "localization", "category": "Customization", "icon": "languages", "color": "#14b8a6", "display_order": 21, "navigation_route": "/settings/localization", "status": "Active", "version": "1.0.0", "system_module": True, "description": "Multi-language dictionary and timezone formatting",
                        "children": [
                            {"name": "Language Selection", "code": "localization.languages"},
                            {"name": "Date Formatting", "code": "localization.date_format"},
                            {"name": "Timezone Configuration", "code": "localization.timezone"}
                        ]
                    },
                    # PARENT: Audit Logs
                    {
                        "name": "Audit Logging", "code": "audit_logs", "category": "Governance", "icon": "file-text", "color": "#475569", "display_order": 22, "navigation_route": "/admin/audit-logs", "status": "Active", "version": "1.0.0", "system_module": True, "description": "Immutable security and activity audit trails",
                        "children": [
                            {"name": "User Activity Trail", "code": "audit_logs.user_activity"},
                            {"name": "Security Audit Logs", "code": "audit_logs.security"},
                            {"name": "Export Audit Logs", "code": "audit_logs.export"}
                        ]
                    }
                ]

                for item in hierarchy_modules:
                    parent_mod = Module.query.filter_by(code=item['code']).first()
                    if not parent_mod:
                        parent_mod = Module(
                            name=item['name'],
                            code=item['code'],
                            category=item['category'],
                            icon=item['icon'],
                            color=item.get('color', '#3b82f6'),
                            display_order=item.get('display_order', 0),
                            navigation_route=item.get('navigation_route'),
                            status=item.get('status', 'Active'),
                            development_stage='Released' if item.get('status') == 'Active' else 'Beta',
                            version=item.get('version', '1.0.0'),
                            enable_by_default=True,
                            visible_in_sidebar=True,
                            visible_in_dashboard=True,
                            requires_subscription=True,
                            premium_feature=item.get('premium_feature', False),
                            ai_enabled=item.get('ai_enabled', False),
                            beta_feature=item.get('beta_feature', False),
                            system_module=item.get('system_module', False),
                            description=item.get('description', '')
                        )
                        db.session.add(parent_mod)
                        db.session.flush()

                    if 'children' in item:
                        for child in item['children']:
                            child_mod = Module.query.filter_by(code=child['code']).first()
                            if not child_mod:
                                child_mod = Module(
                                    name=child['name'],
                                    code=child['code'],
                                    parent_id=parent_mod.id,
                                    category=parent_mod.category,
                                    icon=parent_mod.icon,
                                    status='Active',
                                    enable_by_default=True,
                                    system_module=parent_mod.system_module
                                )
                                db.session.add(child_mod)
                # Seed Default Super Admin (Only create if no SuperAdmin user exists)
                sa_role = Role.query.filter_by(name='SuperAdmin').first()
                if sa_role:
                    any_sa = User.query.filter_by(role_id=sa_role.id).first()
                    if not any_sa:
                        sa_username = (os.getenv('SUPER_ADMIN_USERNAME') or getattr(Config, 'SUPER_ADMIN_USERNAME', '') or '').strip().lower()
                        sa_password = os.getenv('SUPER_ADMIN_PASSWORD', '').strip()
                        if not sa_username or not sa_password:
                            app.logger.warning(
                                '[QCMS SECURITY] SUPER_ADMIN_USERNAME and/or SUPER_ADMIN_PASSWORD environment variables are not set in .env. '
                                'Skipping initial SuperAdmin creation to prevent insecure or hardcoded credentials. '
                                'Set SUPER_ADMIN_USERNAME and SUPER_ADMIN_PASSWORD in your .env file.'
                            )
                        else:
                            hashed_pw = bcrypt.generate_password_hash(sa_password).decode('utf-8')
                            new_sa = User(
                                username=sa_username,
                                email=sa_username,
                                hashed_password=hashed_pw,
                                role_id=sa_role.id,
                                org_id=None,
                                is_verified=True,
                                status='Active',
                                is_active=True
                            )
                            db.session.add(new_sa)
                            db.session.commit()
                            print(f"[QCMS] Initialized default SuperAdmin from environment configuration.")
                    else:
                        # Existing SuperAdmin: ensure system-level attributes remain valid without modifying passwords
                        sa_users = User.query.filter_by(role_id=sa_role.id).all()
                        for sa_user in sa_users:
                            if sa_user.org_id is not None:
                                sa_user.org_id = None
                            if not sa_user.is_active:
                                sa_user.is_active = True
                            if sa_user.status != 'Active':
                                sa_user.status = 'Active'
                        db.session.commit()
            
                # Seed Default Tax Rules & Billing Settings
                from .infrastructure.database.models.models import TaxRule, BillingSettings, Organization
                if not TaxRule.query.first():
                    default_taxes = [
                        TaxRule(country='India', state=None, tax_type='GST', rate=18.0, is_exempt=False),
                        TaxRule(country='India', state='CGST', tax_type='CGST', rate=9.0, is_exempt=False),
                        TaxRule(country='India', state='SGST', tax_type='SGST', rate=9.0, is_exempt=False),
                        TaxRule(country='India', state='IGST', tax_type='IGST', rate=18.0, is_exempt=False),
                        TaxRule(country='United Kingdom', state=None, tax_type='VAT', rate=20.0, is_exempt=False),
                        TaxRule(country='Germany', state=None, tax_type='VAT', rate=19.0, is_exempt=False),
                        TaxRule(country='Canada', state=None, tax_type='GST', rate=5.0, is_exempt=False),
                        TaxRule(country='United States', state=None, tax_type='Sales Tax', rate=0.0, is_exempt=True)
                    ]
                    db.session.bulk_save_objects(default_taxes)
                    db.session.commit()
                    print("[QCMS] Seeded default tax rules.")

                for org in Organization.query.all():
                    if not BillingSettings.query.filter_by(org_id=org.id).first():
                        db.session.add(BillingSettings(org_id=org.id, auto_collection=True, reminder_schedule=[3, 1, 0, -3], grace_period_days=7, payment_retry_attempts=3))
                db.session.commit()

            except Exception as e:
                try:
                    db.session.rollback()
                except Exception:
                    pass
                print(f"[QCMS] Warning: Could not auto-initialize database: {e}")

    # Helper to check if public landing page is enabled
    def is_landing_page_enabled():
        try:
            from app.infrastructure.database.models.models import PlatformSettings
            db.session.expire_all()
            s = PlatformSettings.query.order_by(PlatformSettings.id.asc()).first()
            if s and s.landing_cms_settings and isinstance(s.landing_cms_settings, dict):
                val = s.landing_cms_settings.get('enable_landing_page')
                if val is False or str(val).lower() in ('false', '0', 'off', 'disabled'):
                    return False
        except Exception:
            pass
        return True

    # Check if frontend files are present locally (otherwise redirect to Vercel)
    has_local_frontend = os.path.isdir(frontend_dir) and os.path.exists(os.path.join(frontend_dir, 'index.html'))
    vercel_url = 'https://imfq-qcms.vercel.app'

    # Serve index.html at root (or redirect to login if landing page disabled)
    @app.route('/')
    def serve_index():
        if not has_local_frontend:
            return redirect(vercel_url)
        if not is_landing_page_enabled():
            return redirect('/auth/login.html')
        return send_from_directory(frontend_dir, 'index.html')

    # Serve any frontend HTML page (e.g., /login.html, /dashboard-admin.html)
    @app.route('/<path:filename>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
    def serve_frontend(filename):
        if filename.startswith('api/'):
            return jsonify({"code": 404, "message": "API endpoint not found", "status": "error"}), 404

        if request.method != 'GET':
            return jsonify({"code": 405, "message": "Method not allowed", "status": "error"}), 405

        if not has_local_frontend:
            if filename.endswith('.html') or '.' not in filename:
                return redirect(f"{vercel_url}/{filename}")
            return jsonify({"code": 404, "message": "File not found", "status": "error"}), 404

        if (filename == 'index.html' or filename == 'index' or filename == '') and not is_landing_page_enabled():
            return redirect('/auth/login.html')

        # 1. Direct match at root or exact path (e.g. assets, favicon)
        filepath = os.path.join(frontend_dir, filename)
        if os.path.isfile(filepath):
            return send_from_directory(frontend_dir, filename)
            
        # 2. Check within feature folders
        if filename.endswith('.html') or '.' not in filename:
            html_name = filename if filename.endswith('.html') else f"{filename}.html"
            subdirs = ['auth', 'dashboard', 'projects', 'admin', 'analytics', 'resources', 'rewards', 'help']
            for s in subdirs:
                sub_path = os.path.join(frontend_dir, s, html_name)
                if os.path.isfile(sub_path):
                    return send_from_directory(os.path.join(frontend_dir, s), html_name)

        # Fallback to index.html for SPA-like behavior
        if not is_landing_page_enabled():
            return redirect('/auth/login.html')
        return send_from_directory(frontend_dir, 'index.html')

    # Serve uploaded files (Protected by JWT authentication & Tenant Isolation)
    @app.route('/uploads/<path:filename>')
    def serve_uploads(filename):
        import re
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

        clean_filename = os.path.normpath(filename).replace('\\', '/')
        if '..' in clean_filename or clean_filename.startswith('/'):
            return jsonify({"status": "error", "message": "Invalid file path."}), 400

        is_public_asset = (
            clean_filename.startswith('branding/') or
            clean_filename.startswith('template_previews/') or
            clean_filename.startswith('system/') or
            clean_filename.startswith('avatars/') or
            clean_filename.startswith('avatar_') or
            clean_filename.startswith('banner_') or
            'logo' in clean_filename.lower() or
            'favicon' in clean_filename.lower() or
            clean_filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp'))
        )

        if not is_public_asset:
            try:
                verify_jwt_in_request()
                user_id = get_jwt_identity()
                if isinstance(user_id, dict):
                    user_id = user_id.get('id') or user_id.get('user_id')
                user_id = int(user_id) if user_id else None
            except Exception:
                return jsonify({"status": "error", "message": "Authentication required to access this file.", "code": "UNAUTHORIZED"}), 401

            from app.infrastructure.database.models.models import User
            user = db.session.get(User, user_id) if user_id else None
            if not user:
                return jsonify({"status": "error", "message": "User not found."}), 403

            is_super_admin = (user.role and user.role.name in ('SuperAdmin', 'Admin') and (user.org_id is None or getattr(user, 'is_super_admin', False)))
            if not is_super_admin:
                org_match = re.search(r'org_(\d+)', clean_filename)
                if org_match:
                    owning_org_id = int(org_match.group(1))
                    if owning_org_id != user.org_id:
                        return jsonify({"status": "error", "message": "Access denied. You do not have permission to view this tenant file.", "code": "FORBIDDEN"}), 403

        primary_dir = app.config.get('UPLOAD_FOLDER')
        if primary_dir and os.path.exists(os.path.join(primary_dir, clean_filename)):
            return send_from_directory(primary_dir, clean_filename)
        
        frontend_dir_local = os.path.abspath(os.path.join(app.root_path, '..', '..', 'frontend', 'uploads'))
        if os.path.exists(os.path.join(frontend_dir_local, clean_filename)):
            return send_from_directory(frontend_dir_local, clean_filename)

        # Fallback to Unified Storage Service
        try:
            from app.infrastructure.storage import storage
            content_bytes, content_type = storage.get_file_bytes(clean_filename)
            if content_bytes is not None:
                from flask import Response
                return Response(content_bytes, mimetype=content_type)
        except Exception:
            pass

        return jsonify({"status": "error", "message": "File not found."}), 404

    @app.before_request
    def check_maintenance_mode():
        if not request.path.startswith('/api/'):
            return

        excluded_endpoints = [
            '/api/auth/maintenance-status',
            '/api/auth/login',
            '/api/auth/login-config',
            '/api/super-admin',
            '/api/v1/super-admin'
        ]
        
        is_excluded = False
        for endpoint in excluded_endpoints:
            if request.path.startswith(endpoint):
                is_excluded = True
                break
                
        if is_excluded:
            return

        from app.infrastructure.database.models.models import User
        from sqlalchemy import text as _sql_text
        # Use raw SQL to bypass SQLAlchemy identity map cache and always get fresh DB state
        _row = db.session.execute(
            _sql_text("SELECT id, maintenance_mode, maintenance_settings FROM platform_settings LIMIT 1")
        ).fetchone()
        maintenance_on = bool(_row[1]) if _row and _row[1] is not None else False
        if maintenance_on:
            import json as _json
            try:
                _maint_raw = _row[2]
                maint_settings = _json.loads(_maint_raw) if isinstance(_maint_raw, str) else (_maint_raw or {})
            except Exception:
                maint_settings = {}
            from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
            is_super_admin = False
            try:
                verify_jwt_in_request(optional=True)
                identity = get_jwt_identity()
                if identity:
                    user = db.session.get(User, int(identity))
                    if user and user.role.name == 'SuperAdmin':
                        is_super_admin = True
            except Exception:
                pass
                
            if not is_super_admin:
                is_download_or_export = "export" in request.path.lower() or "download" in request.path.lower()
                if request.method != 'GET' or is_download_or_export:
                    msg = maint_settings.get("maintenance_message") or "System is under maintenance. Database is read-only."
                    return jsonify({
                        "status": "error",
                        "message": msg,
                        "code": "MAINTENANCE_MODE"
                    }), 503

    @app.before_request
    def check_organization_suspension():
        # Intercept only API requests, excluding login/registration and super admin
        if not request.path.startswith('/api/'):
            return
        if request.path.startswith('/api/auth/login') or request.path.startswith('/api/super-admin') or request.path.startswith('/api/v1/super-admin') or request.path.startswith('/api/auth/register-org'):
            return
            
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        try:
            verify_jwt_in_request(optional=True)
            identity = get_jwt_identity()
            if identity:
                from app.infrastructure.database.models.models import User
                user = db.session.get(User, int(identity))
                if not user or not user.org_id or not user.organization:
                    return
                role_name = (user.role.name if user.role else '').strip().lower()
                if role_name in ('superadmin', 'super admin', 'super_admin') or getattr(user, 'is_super_admin', False) or getattr(user, 'is_platform_super_admin', False) or user.id == 1:
                    return

                if user.organization.subscription_status == 'Suspended':
                    allowed_paths = (
                        '/api/auth/me',
                        '/api/auth/profile',
                        '/api/auth/request-reactivation',
                        '/api/auth/user-reactivation-request',
                        '/api/auth/logout',
                        '/api/auth/login',
                        '/api/billing/offline-payment/status',
                        '/api/billing/offline-payment/submit'
                    )
                    if not any(request.path.startswith(p) for p in allowed_paths):
                        return jsonify({
                            "status": "suspended",
                            "msg": "Your organization's access to the QCMS platform has been suspended. Please contact the QCMS support team to reactivate your account.",
                            "error_code": "ORGANIZATION_SUSPENDED"
                        }), 403
        except Exception:
            pass

    @app.before_request
    def check_organization_deleted():
        """Block all API requests from users whose organization is soft-deleted (in Recycle Bin).
        This ensures existing valid JWT tokens stop working immediately after org deletion.
        """
        if not request.path.startswith('/api/'):
            return
        # Always allow login, logout, and super-admin routes
        always_allowed = ('/api/auth/login', '/api/auth/logout', '/api/super-admin', '/api/v1/super-admin', '/api/auth/register-org')
        if any(request.path.startswith(p) for p in always_allowed):
            return

        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        try:
            verify_jwt_in_request(optional=True)
            identity = get_jwt_identity()
            if identity:
                from app.infrastructure.database.models.models import User
                user = db.session.get(User, int(identity))
                if not user or not user.org_id or not user.organization:
                    return
                role_name = (user.role.name if user.role else '').strip().lower()
                if role_name in ('superadmin', 'super admin', 'super_admin') or getattr(user, 'is_super_admin', False) or getattr(user, 'is_platform_super_admin', False) or user.id == 1:
                    return

                if getattr(user.organization, 'is_deleted', False):
                    return jsonify({
                        "status": "error",
                        "msg": "Access denied. This organization has been deleted and your session is no longer valid.",
                        "error_code": "ORG_DELETED"
                    }), 403
        except Exception:
            pass

    # Register error handlers
    @app.errorhandler(404)
    def handle_404(e):
        return jsonify({"status": "error", "message": "Resource not found", "code": 404}), 404

    @app.errorhandler(405)
    def handle_405(e):
        return jsonify({"status": "error", "message": "Method not allowed", "code": 405}), 405

    @app.errorhandler(Exception)
    def handle_global_exception(e):
        import logging
        logging.getLogger('qcms.app').exception("[QCMS Global Exception] %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass
        response = {
            "status": "error",
            "message": "An internal server error occurred. Please contact support if the problem persists.",
            "code": "INTERNAL_SERVER_ERROR"
        }
        if app.config.get('DEBUG', False) and os.getenv('FLASK_ENV') == 'development':
            import traceback
            response["debug_error"] = str(e)
            response["traceback"] = traceback.format_exc()
        return jsonify(response), 500

    @app.after_request
    def add_header(response):
        # Baseline production security headers on all responses
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        response.headers.setdefault('Strict-Transport-Security', 'max-age=63072000; includeSubDomains; preload')
        response.headers.setdefault(
            'Content-Security-Policy',
            "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com; img-src 'self' data: blob: https:; connect-src 'self' ws: wss:; frame-ancestors 'self';"
        )

        path = request.path

        # 1. API routes & sensitive endpoints: strict no-store / no-cache
        if path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '-1'
            return response

        # 2. Hashed production assets and versioned static files: immutable 1-year cache
        is_immutable_asset = (
            path.startswith('/assets/dist/') or
            any(path.endswith(ext) for ext in ('.min.js', '.min.css', '.woff2', '.woff', '.ttf', '.eot')) or
            (path.startswith('/assets/') and any(path.endswith(ext) for ext in ('.svg', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.webp')))
        )
        if is_immutable_asset:
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            response.headers.pop('Pragma', None)
            response.headers.pop('Expires', None)
            return response

        # 3. HTML pages and root route: revalidate with ETags for instant 304 Not Modified
        is_html = (
            path == '/' or
            path.endswith('.html') or
            (response.mimetype and response.mimetype == 'text/html')
        )
        if is_html:
            response.headers['Cache-Control'] = 'no-cache, must-revalidate'
            response.headers.pop('Pragma', None)
            response.headers.pop('Expires', None)
            return response

        # 4. Other static resources (e.g. non-dist assets): cache with revalidation
        response.headers['Cache-Control'] = 'public, max-age=86400'
        response.headers.pop('Pragma', None)
        response.headers.pop('Expires', None)
        return response

    @app.teardown_request
    def teardown_request(exception=None):
        try:
            db.session.rollback()
        except Exception:
            pass
        try:
            db.session.remove()
        except Exception:
            pass

    # ── flask init-db CLI command ─────────────────────────────────────────────
    import click

    @app.cli.command('init-db')
    def init_db_command():
        """Create all database tables (run once per environment, idempotent)."""
        with app.app_context():
            try:
                db.create_all()
                click.echo('[QCMS] Database tables created successfully (flask init-db).')
            except Exception as exc:
                click.echo(f'[QCMS] init-db failed: {exc}', err=True)
                raise SystemExit(1)

    # ── Health probes ─────────────────────────────────────────────────────────
    import time as _time
    _app_start_time = _time.time()

    @app.route('/health/live', methods=['GET'])
    @app.route('/api/health/live', methods=['GET'])
    def health_live():
        """Liveness probe — returns 200 if the process is alive."""
        return jsonify({'status': 'ok', 'uptime_seconds': round(_time.time() - _app_start_time, 1)}), 200

    @app.route('/health/ready', methods=['GET'])
    @app.route('/api/health', methods=['GET'])
    @app.route('/health', methods=['GET'])
    def health_ready():
        """Readiness probe: returns 200 only when DB and Redis are both healthy within tight 2.0s timeouts."""
        from datetime import datetime, timezone
        from app.infrastructure.cache.redis_adapter import cache as _cache
        checks = {'status': 'ready', 'db': 'ok', 'redis': 'ok', 'timestamp': datetime.now(timezone.utc).isoformat()}
        http_status = 200
        
        # 1. Database check (fast timeout)
        try:
            db.session.execute(db.text('SELECT 1'))
        except Exception as exc:
            checks['db'] = 'error'
            checks['status'] = 'not_ready'
            http_status = 503
            app.logger.error('[QCMS Health] DB readiness check failed: %s', exc)
            
        # 2. Redis check (fast timeout ping)
        require_redis = os.environ.get('REQUIRE_REDIS_SECURITY', '').lower() in ('true', '1') or app.config.get('ENVIRONMENT') == 'production'
        if _cache.is_redis:
            try:
                if _cache.ping():
                    checks['redis'] = 'ok'
                else:
                    checks['redis'] = 'degraded'
                    if require_redis:
                        checks['status'] = 'not_ready'
                        http_status = 503
            except Exception as red_err:
                checks['redis'] = 'error'
                if require_redis:
                    checks['status'] = 'not_ready'
                    http_status = 503
        else:
            if require_redis:
                checks['redis'] = 'unreachable'
                checks['status'] = 'not_ready'
                http_status = 503
            else:
                checks['redis'] = 'ok'

        return jsonify(checks), http_status

    return app
