# QCMS MASTER ARCHITECTURE - Engineering Blueprint
**Version**: 1.2 (Enterprise SaaS)
**Status**: ACTIVE
**Last Updated**: 2026-05-05 (Schema Sync v1.2.1)
**Confidentiality**: Internal Engineering Use Only

---

## 1. System Vision & Value Proposition
QCMS (Quality & Continuous Improvement Management System) is an enterprise-grade SaaS platform designed to digitize, automate, and enforce structured problem-solving methodologies (primarily **8D** and **Six Sigma**). 

The platform serves as a "Quality Operating System" for large organizations, ensuring that every improvement project follows a rigid, validated workflow from problem identification to global standardization and SOP updates.

---

## 2. Enterprise SaaS Architecture

### 2.1 Multi-tenancy Model
- **Isolation Strategy**: Shared database, shared schema, row-level isolation.
- **Tenant Context**: All core entities (`Project`, `User`, `Department`, `AuditLog`) are scoped by `org_id`.
- **Branding**: Dynamic white-labeling supported via `Organization` model (colors, logos, favicons).

### 2.2 Role-Based Access Control (RBAC)
The system enforces a strict 6-tier hierarchical permission model:
1.  **Super Admin**: Platform-wide management (Organizations, Subscriptions, System Logs).
2.  **Admin**: Organization owner. Manages users, departments, and compliance policies.
3.  **Reviewer**: Quality gatekeeper. Mandatory approval authority for critical stage transitions (Stages 4, 5, 7, 8).
4.  **Facilitator**: Technical subject matter expert. Validates Root Cause Analysis (RCA) and data integrity.
5.  **Team Leader**: Project manager. Responsible for project execution and team coordination.
6.  **Team Member**: Core contributor. Responsible for data entry and task execution.

**Logic Enforcement**: Levels are mapped internally as `Team Member (0) < Team Leader (1) < Facilitator (2) < Reviewer (3) < Admin (4)`.

### 2.3 Subscription Ecosystem
Managed via `SubscriptionManager` and enforced through backend decorators:
- **Starter**: 5 Projects, 10 Users, Basic Analytics.
- **Professional**: 50 Projects, 100 Users, Advanced Analytics, White-labeling.
- **Enterprise**: Unlimited everything, RAG-AI Intelligent Search, Priority Support.

---

## 3. Technology Stack

| Layer | Technology | Implementation Detail |
|---|---|---|
| **Frontend** | Vanilla HTML5, JS (ES6) | High-performance custom UI engine. |
| **Styling** | CSS3 (Modern) | **Glassmorphism** design system with extensive variable usage. |
| **Backend** | Flask (Python 3.10+) | Modular Blueprint-based REST API. |
| **Database** | PostgreSQL (Neon) | Relational storage + JSONB for flexible workflow data. |
| **Vector DB** | FAISS | Local vector store for RAG (stored in `new updation/vector_store`). |
| **ORM** | SQLAlchemy | Type-safe data modeling. |
| **Auth** | JWT + Bcrypt | Secure, stateless authentication. |
| **Environment** | Docker | Containerized services. |

---

## 4. Backend Engineering (Flask Core)

### 4.1 Modular Routing (Blueprints)
API routes are strictly categorized by role and function in `backend/app/routes/`:
- `auth_routes.py`: Login, registration, password recovery, OTP management.
- `admin_routes.py`: Organization settings, user/dept management, audit logs.
- `workflow_routes.py`: Central engine for the 8-stage project lifecycle.
- `project_routes.py`: Basic CRUD for project containers.
- `rag_routes.py`: Proxies requests to the AI engine in `new updation/`.
- `super_admin_routes.py`: Multi-tenant orchestration and platform metrics.

### 4.2 Middleware Stack (`middleware.py`)
- `auth_guard`: Validates JWT and injects `current_user`.
- `role_required`: Enforces RBAC permissions based on hierarchy levels.
- `subscription_guard`: Feature-flagging based on tenant subscription tier.
- `audit_logger`: Intercepts and logs critical mutations.

---

## 5. Frontend Engineering (SPCI Pattern)

### 5.1 Single Page Component Injection (SPCI)
The frontend uses a custom pattern where UI components are dynamically generated and injected via JavaScript, primarily handled in `components.js`.

- **`QCMS` Object**: Central state holder. Contains `user` data and permission check utilities.
- **`ThemeManager`**: Handles light/dark mode transitions, system preference matching, and `data-theme` attribute synchronization.
- **`components.js`**: The UI Engine (46KB). Manages `renderSidebar`, `renderNavbar`, and shared components (`kpiCard`, `statusBadge`, `renderAvatar`).
- **`api.js`**: Service layer proxied through a standardized `api` object with auto-handling of `org_id` and headers.

### 5.2 Design System
- **`design-system.css`**: Defines design tokens (Glass effects, primary colors, spacing).
- **`glass.css`**: Aesthetic layer for premium "Glassmorphism" look and feel.

---

## 6. The 8-Stage Workflow Engine

The core of QCMS is the rigid 8-stage methodology. The system supports legacy model mapping for backward compatibility.

| Stage | Name | Model (Backend) | Legacy Alias |
|---|---|---|---|
| **1** | Identification | `Stage1Identification` | `Stage1Problem` |
| **2** | Selection | `Stage2Selection` | — |
| **3** | Analysis | `Stage3Analysis` | — |
| **4** | Causes | `Stage4Causes` | — |
| **5** | Root Cause | `Stage5RootCause` | `Stage3RCA` |
| **6** | Data Analysis | `Stage6DataAnalysis` | — |
| **7** | Development | `Stage7Development` | `Stage4Solution` |
| **8** | Implementation | `Stage8Implementation` | `Stage6Implementation`, `Stage7Impact`, `Stage8Standardization` |

### 6.1 State Transitions & Approvals
- **Quality Gates**: Stage 4, 5, 7, and 8 require Reviewer sign-off (`ProjectReview` model).
- **Facilitator Validation**: Required for Stage 5 (Root Cause) validation.

---

## 7. Intelligent Features (RAG-AI)

Located in the `/new updation/` directory, the AI sub-system uses Retrieval-Augmented Generation to assist users in finding historical quality solutions.

- **`rag_ingestion.py`**: Processes closed projects and indexes them into FAISS.
- **`rag_chat.py`**: Handles user queries by retrieving context from the vector store.
- **`vector_store/`**: Local directory containing the FAISS index and metadata.

---

## 8. Directory Topology

```text
/
├── backend/
│   ├── app/
│   │   ├── routes/          # API Endpoint Blueprints
│   │   ├── utils/           # Business logic (Subscription, Email)
│   │   ├── models.py        # SQLAlchemy Schema & Stage Aliases
│   │   ├── middleware.py    # Security & Logging
│   │   └── __init__.py      # App factory
├── frontend/
│   ├── assets/
│   │   ├── js/
│   │   │   ├── components.js # CORE UI ENGINE (46KB) - RBAC Sidebar/Navbar
│   │   │   ├── api.js        # Service Layer
│   │   │   └── auth-guard.js # Frontend permission enforcement
│   │   └── css/
│   │       ├── design-system.css # Design Tokens
│   │       └── glass.css     # UI Aesthetics
├── new updation/            # RAG-AI Engine & Specialized Views
│   ├── rag_chat.py          # AI logic
│   ├── rag_ingestion.py     # Data indexing
│   └── vector_store/        # FAISS Index
├── migrations/              # Database migration scripts
└── docker-compose.yml       # Full system orchestration
```

---

## 9. Deployment Protocol
1.  **Environment Variables**: Managed via `.env` in `backend/`.
2.  **Database**: Neon PostgreSQL for serverless scaling.
3.  **Audit Consistency**: All critical deletions and status changes MUST be logged via `AuditLog`.

---
**END OF BLUEPRINT**
