import os
from flask import Flask, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from dotenv import load_dotenv
from flask_migrate import Migrate

load_dotenv()

db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()
migrate = Migrate()

def create_app():
    # Resolve frontend folder path (../frontend relative to backend/)
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend'))

    app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
    
    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'qcms_secret')
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
    }
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable static file caching for frontend
    
    # File Upload Configuration
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), '..', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize Extensions
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    
    with app.app_context():
        # Import all models first so db.create_all() knows about them
        from . import models  # noqa: F401

        # Import and register Blueprints
        from .routes.auth_routes import auth_bp
        from .routes.project_routes import project_bp
        from .routes.workflow_routes import workflow_bp
        from .routes.analytics_routes import analytics_bp
        from .routes.admin_routes import admin_bp
        from .routes.facilitator_routes import facilitator_bp
        from .routes.reviewer_routes import reviewer_bp
        from .routes.team_leader_routes import team_leader_bp
        from .routes.team_member_routes import team_member_bp
        from .routes.qc_tools_routes import qc_tools_bp
        from .routes.dashboard_routes import dashboard_bp
        from .routes.repository_routes import repository_bp
        
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        app.register_blueprint(project_bp, url_prefix='/api/projects')
        app.register_blueprint(workflow_bp, url_prefix='/api/workflow')
        app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
        app.register_blueprint(admin_bp, url_prefix='/api/admin')
        app.register_blueprint(facilitator_bp, url_prefix='/api/facilitator')
        app.register_blueprint(reviewer_bp, url_prefix='/api/reviewer')
        app.register_blueprint(team_leader_bp, url_prefix='/api/team-leader')
        app.register_blueprint(team_member_bp, url_prefix='/api/team-member')
        app.register_blueprint(qc_tools_bp, url_prefix='/api/project')
        app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
        app.register_blueprint(repository_bp, url_prefix='/api/repository')
        
        # Auto-create all database tables if they don't exist
        # This is safe — db.create_all() only creates tables that are missing,
        # it will NOT drop or modify existing tables.
        try:
            db.create_all()
            # Auto-seed roles if empty
            from .models import Role
            roles = ['Admin', 'Reviewer', 'Facilitator', 'Team Leader', 'Team Member']
            for r_name in roles:
                if not Role.query.filter_by(name=r_name).first():
                    db.session.add(Role(name=r_name))
            db.session.commit()
            print("[QCMS] Database tables verified and roles seeded successfully.")
        except Exception as e:
            print(f"[QCMS] Warning: Could not auto-initialize database: {e}")

    # ─── Frontend Serving ───
    # Serve index.html at root
    @app.route('/')
    def serve_index():
        return send_from_directory(frontend_dir, 'index.html')

    # Serve any frontend HTML page (e.g., /login.html, /dashboard-admin.html)
    @app.route('/<path:filename>')
    def serve_frontend(filename):
        # Only serve if it's a real file, otherwise let API routes handle it
        filepath = os.path.join(frontend_dir, filename)
        if os.path.isfile(filepath):
            return send_from_directory(frontend_dir, filename)
        # Fallback to index.html for SPA-like behavior
        return send_from_directory(frontend_dir, 'index.html')

    # Serve uploaded files
    @app.route('/uploads/<path:filename>')
    def serve_uploads(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Health check API
    @app.route('/api/health')
    def health_check():
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            return jsonify({
                "status": "online",
                "message": "QCMS Backend API is Running",
                "database": "connected"
            }), 200
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e),
                "database": "disconnected"
            }), 500
            
    return app
