import os
from flask import Flask, jsonify, send_from_directory, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from dotenv import load_dotenv
from flask_migrate import Migrate
from .boot_utils import bootstrap_database

from app.config import Config

db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()
migrate = Migrate()

def create_app():
    # Bootstrap database (create if missing)
    bootstrap_database()

    # Resolve frontend folder path (../frontend relative to backend/)
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend'))

    app = Flask(__name__, static_folder=None)
    
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
        from .presentation.routes.points_routes import points_bp
        from .presentation.routes.plant_routes import plant_bp
        
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
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
        app.register_blueprint(integrations_bp, url_prefix='/api/super-admin')
        app.register_blueprint(integration_v1_bp, url_prefix='/api/v1/integrations')
        app.register_blueprint(sop_bp, url_prefix='/api/sops')
        app.register_blueprint(document_branding_bp)
        app.register_blueprint(feature_engine_bp)

        # ── QCMS Security Middleware ───────────────────────────────────────────
        # Registers WAF, IP whitelist/blacklist, rate limiting, brute-force
        # protection, and security headers — all driven by security_settings in DB
        from .presentation.middleware.security import register_security_middleware
        register_security_middleware(app)

        try:
            is_serverless = bool(os.getenv('VERCEL') or os.getenv('VERCEL_ENV') or os.getenv('VERCEL_REGION') or os.getenv('AWS_LAMBDA_FUNCTION_NAME'))
            if not is_serverless:
                try:
                    db.create_all()
                except Exception:
                    pass
                from sqlalchemy import text
            alter_statements = [
                "CREATE TABLE IF NOT EXISTS plants (id SERIAL PRIMARY KEY, org_id INTEGER NOT NULL REFERENCES organizations(id), name VARCHAR(100) NOT NULL, code VARCHAR(50), location VARCHAR(255), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
                "ALTER TABLE departments ADD COLUMN IF NOT EXISTS plant_id INTEGER REFERENCES plants(id);",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS plant_id INTEGER REFERENCES plants(id);",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS custom_fields JSONB;",
                "ALTER TABLE user_custom_fields ADD COLUMN IF NOT EXISTS data_type VARCHAR(50) DEFAULT 'both';",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS pan_number VARCHAR(50);",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS website VARCHAR(255);",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS org_code VARCHAR(100);",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS license_number VARCHAR(100);",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS storage_limit_mb FLOAT DEFAULT 10240.0;",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS enabled_modules JSONB;",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS state VARCHAR(100);",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS is_platform_org BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS gst_number VARCHAR(50);",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS license_start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS license_expiry_date TIMESTAMP;",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS storage_used_mb FLOAT DEFAULT 0.0;",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS stages_config JSONB;",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS login_options JSONB;",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS security_settings JSONB;",
                # ── Enterprise Subscription Management additions ──────────────────────
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMP;",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS cancellation_reason TEXT;",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS trial_start_date TIMESTAMP;",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS trial_end_date TIMESTAMP;",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS base_price FLOAT DEFAULT 0.0;",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS discount_percent FLOAT DEFAULT 0.0;",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS discount_amount FLOAT DEFAULT 0.0;",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS gst_percent FLOAT DEFAULT 18.0;",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS gst_amount FLOAT DEFAULT 0.0;",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS final_amount FLOAT DEFAULT 0.0;",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'INR';",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS max_users INTEGER DEFAULT 500;",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS storage_limit_gb FLOAT DEFAULT 10.0;",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS api_limit INTEGER DEFAULT 10000;",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS enabled_modules JSONB;",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS support_level VARCHAR(50) DEFAULT 'Standard';",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS auto_renewal BOOLEAN DEFAULT TRUE;",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS grace_period_days INTEGER DEFAULT 7;",
                "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS billing_notes TEXT;",
                "ALTER TABLE subscription_payments ADD COLUMN IF NOT EXISTS subscription_id INTEGER REFERENCES subscriptions(id);",
                "ALTER TABLE subscription_payments ADD COLUMN IF NOT EXISTS invoice_id INTEGER REFERENCES subscription_invoices(id);",
                "ALTER TABLE subscription_payments ADD COLUMN IF NOT EXISTS billing_cycle VARCHAR(20);",
                "ALTER TABLE subscription_payments ADD COLUMN IF NOT EXISTS payment_gateway VARCHAR(50);",
                "ALTER TABLE subscription_payments ADD COLUMN IF NOT EXISTS gateway_reference VARCHAR(255);",
                "ALTER TABLE subscription_payments ADD COLUMN IF NOT EXISTS discount_amount FLOAT DEFAULT 0.0;",
                "ALTER TABLE subscription_payments ADD COLUMN IF NOT EXISTS gst_percent FLOAT DEFAULT 18.0;",
                "ALTER TABLE subscription_payments ADD COLUMN IF NOT EXISTS gst_amount FLOAT DEFAULT 0.0;",
                "ALTER TABLE subscription_payments ADD COLUMN IF NOT EXISTS final_amount FLOAT;",
                "ALTER TABLE subscription_payments ADD COLUMN IF NOT EXISTS refund_status VARCHAR(20);",
                "ALTER TABLE subscription_payments ADD COLUMN IF NOT EXISTS refund_amount FLOAT DEFAULT 0.0;",
                "ALTER TABLE subscription_payments ADD COLUMN IF NOT EXISTS refund_date TIMESTAMP;",
                # ── Support Tickets additions ──────────────────────
                "ALTER TABLE support_tickets ADD COLUMN IF NOT EXISTS ticket_number VARCHAR(100) UNIQUE;",
                "ALTER TABLE support_tickets ADD COLUMN IF NOT EXISTS assigned_engineer_id INTEGER REFERENCES users(id);",
                "ALTER TABLE support_tickets ADD COLUMN IF NOT EXISTS assigned_team VARCHAR(100);",
                "ALTER TABLE support_tickets ADD COLUMN IF NOT EXISTS sla_status VARCHAR(50) DEFAULT 'Within SLA';",
                "ALTER TABLE support_tickets ADD COLUMN IF NOT EXISTS escalation_level INTEGER DEFAULT 0;",
                "ALTER TABLE support_tickets ADD COLUMN IF NOT EXISTS tags JSONB;",
                # ── Audit Logs enterprise extensions ──────────────────────
                "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS session_id VARCHAR(100);",
                "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS request_id VARCHAR(100);",
                "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS response_code INTEGER;",
                "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS execution_time FLOAT;",
                "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS risk_level VARCHAR(20) DEFAULT 'Low';",
                "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS browser VARCHAR(50);",
                "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS os VARCHAR(50);",
                "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS device VARCHAR(50);",
                "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS location VARCHAR(100);",
                "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS before_data JSONB;",
                "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS after_data JSONB;",
                "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS hash_signature VARCHAR(128);",
                "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS is_tampered BOOLEAN DEFAULT FALSE;",
                # ── Platform Settings additions ──────────────────────
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS support_phone VARCHAR(50);",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS support_website VARCHAR(255);",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS company_address TEXT;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS timezone VARCHAR(100);",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS default_language VARCHAR(10);",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS date_format VARCHAR(50);",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS time_format VARCHAR(20);",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS currency VARCHAR(10);",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS branding_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS localization_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS authentication_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS security_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS notification_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS email_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS sms_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS push_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS storage_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS backup_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS compliance_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS api_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS webhook_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS integrations_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS ai_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS feature_flags JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS maintenance_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS system_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS organizations_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS billing_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS modules_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS developer_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS audit_logs_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS system_health_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS about_settings JSONB;",
                "ALTER TABLE platform_settings ADD COLUMN IF NOT EXISTS global_stages_config JSONB;",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS security_settings JSONB;"
            ]
            for statement in alter_statements:
                try:
                    db.session.execute(text(statement))
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    # Try fallback statement without IF NOT EXISTS if database is SQLite
                    if "IF NOT EXISTS" in statement:
                        fallback = statement.replace("IF NOT EXISTS ", "")
                        if "JSONB" in fallback:
                            fallback = fallback.replace("JSONB", "JSON")
                        try:
                            db.session.execute(text(fallback))
                            db.session.commit()
                        except Exception:
                            db.session.rollback()
            
            from .infrastructure.database.models.models import (
                Role, PlatformSettings, User, Organization, UserCustomField,
                SaaSPlan, SaaSPlanPricing, SaaSPlanLimits, SaaSPlanModules, SaaSPlanAnalytics,
                EmployeePoints, EmployeeLeaderboard
            )
            orgs = Organization.query.all()
            for org in orgs:
                system_fields = [
                    ('username', 'User', True, True, 'both'),
                    ('role', 'User Role', True, True, 'both'),
                    ('department', 'Department', True, True, 'both'),
                    ('email', 'Email Address', True, True, 'email')
                ]
                for key, name, req, sys, dtype in system_fields:
                    if not UserCustomField.query.filter_by(org_id=org.id, field_key=key).first():
                        db.session.add(UserCustomField(org_id=org.id, field_key=key, display_name=name, is_required=req, is_system=sys, data_type=dtype))
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
            
            # Seed Default Feature Modules & Child Features Hierarchy
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
                        {"name": "Training Certificates", "code": "training.certificates"},
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

                # Seed children
                for idx, child in enumerate(item.get('children', [])):
                    c_mod = Module.query.filter_by(code=child['code']).first()
                    if not c_mod:
                        c_mod = Module(
                            parent_id=parent_mod.id,
                            name=child['name'],
                            code=child['code'],
                            category=item['category'],
                            icon=item['icon'],
                            color=item.get('color', '#3b82f6'),
                            display_order=idx + 1,
                            navigation_route=child.get('navigation_route', item.get('navigation_route')),
                            status='Active',
                            development_stage='Released',
                            version='1.0.0',
                            enable_by_default=True,
                            visible_in_sidebar=True,
                            visible_in_dashboard=True,
                            requires_subscription=True,
                            system_module=parent_mod.system_module,
                            description=f"Sub-feature: {child['name']}"
                        )
                        db.session.add(c_mod)

            db.session.commit()
            print("[QCMS] Seeded Enterprise Feature Hierarchy (Parents & Children) successfully.")
            
            # Seed Default Super Admin
            sa_username = os.getenv('SUPER_ADMIN_USERNAME')
            sa_password = os.getenv('SUPER_ADMIN_PASSWORD')
            if sa_username and sa_password:
                sa_role = Role.query.filter_by(name='SuperAdmin').first()
                if sa_role:
                    # Check if a SuperAdmin already exists
                    sa_exists = User.query.filter_by(role_id=sa_role.id).first()
                    if not sa_exists:
                        # Check if the email is already used by another role
                        existing_user = User.query.filter_by(email=sa_username).first()
                        from .infrastructure.database.models.models import Organization
                        sa_org = Organization.query.filter_by(name='QCMS Admin Org').first()
                        if not sa_org:
                            sa_org = Organization(
                                name='QCMS Admin Org',
                                email='admin@qcms.com',
                                subscription_plan='Enterprise',
                                subscription_status='Active'
                            )
                            db.session.add(sa_org)
                            db.session.commit()
                        else:
                            # Ensure existing org stays Active
                            sa_org.subscription_status = 'Active'
                            sa_org.subscription_plan = 'Enterprise'

                        if existing_user:
                            # Promote existing user to SuperAdmin
                            existing_user.role_id = sa_role.id
                            existing_user.org_id = sa_org.id
                            existing_user.is_verified = True
                            existing_user.status = 'Active'
                        else:
                            hashed_pw = bcrypt.generate_password_hash(sa_password).decode('utf-8')
                            new_sa = User(
                                username=sa_username,
                                email=sa_username,
                                hashed_password=hashed_pw,
                                role_id=sa_role.id,
                                org_id=sa_org.id,
                                is_verified=True,
                                status='Active'
                            )
                            db.session.add(new_sa)

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

            print("[QCMS] Database tables verified, roles, super admin, tax rules, and billing settings seeded successfully.")
        except Exception as e:
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
        except Exception as e:
            pass
        return True

    # ─── Frontend Serving ───
    # Serve index.html at root (or redirect to login if landing page disabled)
    @app.route('/')
    def serve_index():
        if not is_landing_page_enabled():
            return redirect('/auth/login.html')
        return send_from_directory(frontend_dir, 'index.html')

    # Serve any frontend HTML page (e.g., /login.html, /dashboard-admin.html)
    @app.route('/<path:filename>')
    def serve_frontend(filename):
        if (filename == 'index.html' or filename == 'index' or filename == '') and not is_landing_page_enabled():
            return redirect('/auth/login.html')

        # 1. Direct match at root or exact path (e.g. assets, favicon)
        filepath = os.path.join(frontend_dir, filename)
        if os.path.isfile(filepath):
            return send_from_directory(frontend_dir, filename)
            
        # 2. Check within feature folders
        if filename.endswith('.html') or '.' not in filename:
            html_name = filename if filename.endswith('.html') else f"{filename}.html"
            subdirs = ['auth', 'dashboard', 'projects', 'admin', 'analytics']
            for s in subdirs:
                sub_path = os.path.join(frontend_dir, s, html_name)
                if os.path.isfile(sub_path):
                    return send_from_directory(os.path.join(frontend_dir, s), html_name)
                    
        # Fallback to index.html for SPA-like behavior
        if not is_landing_page_enabled():
            return redirect('/auth/login.html')
        return send_from_directory(frontend_dir, 'index.html')

    # Serve uploaded files
    @app.route('/uploads/<path:filename>')
    def serve_uploads(filename):
        primary_dir = app.config.get('UPLOAD_FOLDER')
        if primary_dir and os.path.exists(os.path.join(primary_dir, filename)):
            return send_from_directory(primary_dir, filename)
        
        frontend_dir = os.path.abspath(os.path.join(app.root_path, '..', '..', 'frontend', 'uploads'))
        if os.path.exists(os.path.join(frontend_dir, filename)):
            return send_from_directory(frontend_dir, filename)

        if primary_dir:
            return send_from_directory(primary_dir, filename)
        return jsonify({"message": "File not found"}), 404

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
        if request.path.startswith('/api/auth/login') or request.path.startswith('/api/super-admin') or request.path.startswith('/api/auth/register-org'):
            return
            
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        try:
            verify_jwt_in_request(optional=True)
            identity = get_jwt_identity()
            if identity:
                from app.infrastructure.database.models.models import User
                user = db.session.get(User, int(identity))
                if user and user.organization and user.organization.subscription_status == 'Suspended':
                    if user.role.name != 'SuperAdmin':
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

    # ─── Global Error Handlers ───
    from sqlalchemy.exc import OperationalError
    from werkzeug.exceptions import HTTPException
    
    @app.errorhandler(OperationalError)
    def handle_db_error(e):
        print(f"[QCMS] Critical Database Connection Error: {e}")
        return jsonify({
            "status": "error",
            "message": "The system could not connect to the database. Please ensure your PostgreSQL service is running.",
            "code": "DB_CONNECTION_ERROR"
        }), 503

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        return jsonify({
            "status": "error",
            "message": e.description,
            "code": e.code
        }), e.code

    @app.errorhandler(Exception)
    def handle_exception(e):
        print(f"[QCMS] Unhandled exception: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}",
            "code": "SERVER_ERROR"
        }), 500

    @app.after_request
    def add_header(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    @app.teardown_request
    def teardown_request(exception=None):
        if exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        try:
            db.session.remove()
        except Exception:
            pass

    @app.errorhandler(Exception)
    def handle_global_exception(e):
        import traceback
        tb = traceback.format_exc()
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": tb
        }), 500

    return app
