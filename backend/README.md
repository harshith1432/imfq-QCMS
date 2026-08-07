# QCMS Backend Developer Guide

The QCMS backend is a robust Flask REST API designed for high availability and structured data management. It uses SQLAlchemy as the ORM and follows a modular route structure for maintainability.

## 📁 Architectural Overview (Clean Architecture / Domain-Driven Design)

The backend follows Clean Architecture and Domain-Driven Design principles, separating concerns across decoupled, testable layers:

```text
backend/
├── app/
│   ├── __init__.py                  # App factory & extension initialization
│   ├── boot_utils.py                # Database server connection helper
│   ├── config/                      # Centralized environment configuration
│   │   ├── __init__.py
│   │   └── settings.py              # Loads variables from .env & masks logs
│   ├── domain/                      # Enterprise Business Rules (independent of DB/Framework)
│   │   ├── exceptions/              # Core business exception classes
│   │   ├── models/                  # Pure domain entity contracts
│   │   └── services/                # Domain services
│   │       └── subscription_service.py # Plan limit verification
│   ├── application/                 # Application Business Rules (Use Cases & interfaces)
│   │   ├── interfaces/              # Gateway & repository interfaces
│   │   └── use_cases/               # Command/Query orchestrator implementations
│   ├── infrastructure/              # Database & External Services Implementation
│   │   ├── database/                # Persistence mappings
│   │   │   ├── models/
│   │   │   │   └── models.py        # SQLAlchemy schema (30+ tables)
│   │   │   └── repositories/        # Repository implementations
│   │   ├── mailer/                  # External notifications
│   │   │   └── email_service.py     # Resend & SMTP mail implementation
│   │   └── vector_db/               # pgvector RAG implementation
│   │       ├── vector_ingest.py     # Knowledge injection scripts
│   │       └── vector_service.py    # Embedding similarity matching service
│   ├── presentation/                # REST Web Layer
│   │   ├── controllers/             # Request parsing & DTO handlers
│   │   ├── middleware/              # Security interceptors
│   │   │   └── middleware.py        # JWT & role authorization validators
│   │   └── routes/                  # Blueprint routers
│   │       ├── admin_routes.py      # Users & departments endpoints
│   │       ├── auth_routes.py       # Authentication & profile endpoints
│   │       ├── project_routes.py    # Core workspace & project endpoints
│   │       └── ... (role & feature specific blueprints)
│   └── utils/                       # Generic technical helpers (report generation, i18n)
├── run.py                           # Application WSGI entry point
└── requirements.txt                 # Dependencies list
```

## 🔐 Security & RBAC

All protected routes are guarded by the `@role_required` and `@jwt_required()` decorators defined under `app/presentation/middleware/middleware.py`.
- **JWT**: Scoped `access_token` includes `org_id`, `role`, and `dept_id` in the claim payload.
- **RBAC**: Middleware validates the user's role against permissions before granting access.

## 🔄 The 8-Stage Workflow Logic

The core logic for project progression resides in `app/presentation/routes/workflow_routes.py` (with plans to relocate logic to domain/services).
- **`ProjectStageTracker`**: A dedicated table that tracks the start and end of all 8 stages for every project.
- **Transitions**: Moving from Stage `N` to `N+1` requires specific conditions:
  - **Stage 3→4**: Requires a Facilitator's validation note.
  - **Stage 4→5**: Requires a Reviewer's manual approval.
  - **Stage 7→8**: Requires impact verification by an Admin or Facilitator.

## 🛠️ Adding a New Asset/API

1. **Model**: Update `app/infrastructure/database/models/models.py` with your new class.
2. **Migrations**: For production, use Flask-Migrate (`flask db migrate`).
3. **Route**: Create a new file in `app/presentation/routes/`.
4. **Register**: Import and register the blueprint in `app/__init__.py`.
   ```python
   from .presentation.routes.new_feature import new_bp
   app.register_blueprint(new_bp, url_prefix='/api/feature')
   ```

## 📊 KPI Engine
The `analytics_routes.py` dynamically calculates organizational metrics by aggregating data from the `kpi_metrics` and `stage_7_impact` tables.

---

