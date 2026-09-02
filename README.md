# QCMS Enterprise OS — Quality & Compliance Management System (IFQM)

[![System Architecture](https://img.shields.io/badge/Architecture-Clean%20Architecture%20%7C%20DDD-blue.svg)](#-system-architecture)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Backend-Flask%20%7C%20SQLAlchemy-red.svg)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%20%7C%20Neon-blue.svg)](https://www.postgresql.org/)
[![UI Design](https://img.shields.io/badge/UI-Glassmorphism%20%7C%20Vanilla%20ES6%2B-purple.svg)](#-frontend-architecture)
[![Security](https://img.shields.io/badge/Security-JWT%20%7C%20RBAC%20%7C%20Multi--Tenant-green.svg)](#-security-compliance--multi-tenancy)

An enterprise-grade, high-performance SaaS platform engineered for structured 8-stage problem solving (**Quality Circle / 8D / DMAIC / Six Sigma**), multi-tenant organization governance, real-time collaborator presence & heartbeat telemetry, automated compliance audit reporting, and advanced operational analytics.

---

## 📑 Table of Contents

- [Executive Overview](#-executive-overview)
- [System Architecture](#-system-architecture)
- [Comprehensive Subsystem Breakdown](#-comprehensive-subsystem-breakdown)
  - [1. Real-Time Presence & Collaborator Telemetry](#1-real-time-presence--collaborator-telemetry)
  - [2. The 8-Stage DMAIC Quality Circle Workflow](#2-the-8-stage-dmaic-quality-circle-workflow)
  - [3. Project Audit Trail & Member Lifecycle Tracking](#3-project-audit-trail--member-lifecycle-tracking)
  - [4. Multi-Tenant SaaS Governance & Dynamic Branding](#4-multi-tenant-saas-governance--dynamic-branding)
  - [5. Automated PDF & Export Generation Pipeline](#5-automated-pdf--export-generation-pipeline)
  - [6. Dynamic Multilingual i18n Translation Engine](#6-dynamic-multilingual-i18n-translation-engine)
  - [7. Dynamic Feature Engine (144 Modules)](#7-dynamic-feature-engine-144-modules)
- [Role-Based Access Control (RBAC) Matrix](#-role-based-access-control-rbac-matrix)
- [Repository & File Structure](#-repository--file-structure)
- [Technology Stack](#-technology-stack)
- [Installation & Quick Start](#-installation--quick-start)
  - [Prerequisites](#prerequisites)
  - [Environment Configuration](#environment-configuration)
  - [Option A: Docker Deployment (Recommended)](#option-a-docker-deployment-recommended)
  - [Option B: Manual Local Setup](#option-b-manual-local-setup)
- [API Endpoints Overview](#-api-endpoints-overview)
- [Security, Compliance & Reliability](#-security-compliance--reliability)
- [License & Copyright](#-license--copyright)

---

## 🌟 Executive Overview

**QCMS Enterprise OS** is purpose-built for industrial manufacturing units, enterprise organizations, and quality management institutions (including IFQM) to systematically detect, analyze, resolve, and institutionalize solutions for operational deviations, defect rates, cycle time bottlenecks, and compliance failures.

### Core Value Propositions:
1. **Rigid 8-Stage DMAIC Discipline**: Enforces step-by-step problem resolution with independent reviewer sign-off gates.
2. **Real-Time Collaboration**: Live collaborator presence indicators, heartbeat tracking, and stage-level collision prevention.
3. **Forensic Audit & Lifecycle Traceability**: Full transparency into who contributed, who approved, when members transitioned mid-project, and stakeholder handovers.
4. **Instant Executive Reporting**: One-click generation of comprehensive, publication-ready multi-page PDF QC Storybooks and ISO 9001 compliance certificates.
5. **Zero-Friction Multi-Tenancy**: Complete data segregation per tenant organization with customizable branding, plan quotas, and multi-tier subscription billing.

---

## 🏗️ System Architecture

The platform follows clean architecture principles with decoupled backend REST services, layered domain entities, and a responsive glassmorphic frontend client:

```mermaid
graph TD
    %% Client Tier
    subgraph Client_Tier["🖥️ FRONTEND CLIENT TIER (Responsive Glassmorphism UI)"]
        UI_AUTH["Auth & SSO Portal<br/>(Login, MFA, Password Reset, GPS Telemetry)"]
        UI_DASH["Role-Based Dashboards<br/>(Admin, CEO, Reviewer, Team Lead, Member)"]
        UI_WF["8-Stage DMAIC Problem-Solving Workspace<br/>(Fishbone, 5-Why, Pareto, Gantt, SOPs)"]
        UI_PRES["Real-Time Presence & Heartbeat Telemetry<br/>(Active Collaborator Roster, Lock Avoidance)"]
        UI_AN["Performance Analytics & Audit Trail<br/>(Member Lifecycle, KPI Comparisons, Financial ROI)"]
        UI_SA["Super Admin & Governance Portal<br/>(Tenant Management, Custom Branding, Plan Limits)"]
        UI_I18N["Dynamic i18n Translation Engine<br/>(6 Languages, DOM MutationObserver)"]
    end

    %% Gateway & Security Tier
    subgraph Gateway_Tier["🛡️ API GATEWAY & SECURITY INTERCEPTOR LAYER"]
        REV_PROXY["Nginx / Cloudflare Edge Proxy<br/>(SSL/TLS Termination, Rate Limiting)"]
        CORS_SEC["CORS & Request Sanitizer"]
        JWT_GUARD["JWT Token & Session Validator"]
        RBAC_GUARD["RBAC & Permission Evaluator<br/>(@admin_required, @role_required)"]
        QUOTA_GUARD["Subscription & Quota Guard<br/>(Users, Projects, Storage Limit Verifiers)"]
        ACTION_LOCK["Client ActionLock & Deduplication Map"]
    end

    %% Core Application Layer
    subgraph App_Tier["⚙️ APPLICATION CORE (Flask Clean Architecture)"]
        AUTH_SRV["Authentication & Profile Service<br/>(JWT, Bcrypt, Session Heartbeat Engine)"]
        WF_SRV["8-Stage Quality Workflow Engine<br/>(Sequential State Machine, Stage Lockers)"]
        PRES_SRV["Collaborator Presence & Heartbeat Engine<br/>(Real-Time Heartbeats, TTL Presence Roster)"]
        AUDIT_SRV["Audit Trail & Member Lifecycle Engine<br/>(Tenure Tracking, Stakeholder Replaced, Governance)"]
        ANALYTICS_SRV["Operational Analytics & KPI Calculator<br/>(Before/After Metrics, Velocity, Savings)"]
        GOV_SRV["Multi-Tenant Organization Governance<br/>(Plan Tier Matrix, Document Branding)"]
        DOC_SRV["Automated Document & PDF Engine<br/>(ReportLab QC Story Reports, ISO Certificates, CSV)"]
        FEAT_SRV["Feature Engine Matrix<br/>(144 Dynamic Module Access Toggles)"]
    end

    %% Data & Persistence Layer
    subgraph Data_Tier["💾 DATA & PERSISTENCE LAYER"]
        DB[("PostgreSQL Database<br/>(Neon Serverless / Local PostgreSQL)<br/>35+ Relational Domain Entities")]
        STORAGE["Secure File Storage System<br/>(Uploads, SOP Attachments, Generated PDFs)"]
        CACHE["In-Memory Deduplication & TTL Cache"]
    end

    %% Inter-Layer Flow
    Client_Tier -->|HTTPS / REST APIs / JSON| REV_PROXY
    REV_PROXY --> CORS_SEC
    CORS_SEC --> JWT_GUARD
    JWT_GUARD --> RBAC_GUARD
    RBAC_GUARD --> QUOTA_GUARD
    QUOTA_GUARD --> App_Tier

    App_Tier -->|SQLAlchemy ORM| DB
    App_Tier -->|File I/O Streams| STORAGE
    App_Tier -->|Memory Caching| CACHE
```

---

## 🏛️ Comprehensive Subsystem Breakdown

### 1. Real-Time Presence & Collaborator Telemetry
The presence subsystem monitors active collaborator engagement across every project and stage:
- **Client Heartbeat Dispatcher**: Active clients dispatch continuous background heartbeats (`/api/auth/heartbeat` and `/api/workflow/<project_id>/stage/<stage_id>/presence-heartbeat`) with browser GPS coordinates and timestamps.
- **Stage Concurrency & Lock Management**: Tracks who is currently viewing or actively modifying specific workflow stages, preventing accidental data overwrites and showing live collaborator badges.
- **Session Lifecycle & Invalidation**: Automatically revokes expired tokens and clears active sessions on idle timeouts or administrative terminations.

### 2. The 8-Stage DMAIC Quality Circle Workflow
A rigid, sequential problem-solving lifecycle with automated stage-transition approval locks:
- **Stage 1: Problem Definition & Team Formation**: Problem statement, 5W2H framing, initial baseline targets, circle team roster (Team Leader, Facilitator, Reviewer, Members).
- **Stage 2: Current State & Baseline Data Collection**: KPI baseline measurements, stratification, SOP deviation analysis, and physical evidence uploads.
- **Stage 3: Root Cause Analysis (RCA)**: Interactive visual **Ishikawa (Fishbone) diagram**, **5-Why analysis trees**, and **Pareto charts (80/20 rule)** with dynamic category weightage.
- **Stage 4: Solution Planning & Countermeasures**: Action planning, cost-benefit analysis, risk assessment, and financial ROI estimation.
- **Stage 5: Independent Review & Approval Gate**: Strict gatekeeper validation by designated Reviewer/Facilitator before implementation.
- **Stage 6: Implementation, Execution & Trial Testing**: Milestone tracking, task assignment matrices, and trial run evaluation.
- **Stage 7: Impact & Savings Verification**: Post-countermeasure vs. baseline KPI calculations, tangible and intangible financial savings computation.
- **Stage 8: Standardization, SOP Integration & Project Closure**: Standard Operating Procedure updates, institutional lessons learned, and final closure sign-offs.

### 3. Project Audit Trail & Member Lifecycle Tracking
Provides complete audit telemetry and member transition tracking:
- **Member Lifecycle Timeline**:
  - **Inception Roster**: Records all initial team members, leaders, facilitators, and reviewers.
  - **Mid-Project Joiners**: Captures when new members join during active stages with timestamps.
  - **Departures & Transitions**: Detects when members leave the project mid-way, calculating their exact joined date, departure date, total active tenure, and the actor who removed them.
  - **Stakeholder Handover**: Detects Facilitator replacements, Reviewer transitions, and Team Leader handovers (e.g. `in_project_facilitator` (Active: Aug 01 -> Aug 24) -> `Anita Das` (Active: Aug 24 -> Present)).
- **Human-Readable Formatter**: Parses JSON delta records into structured Before/After metric comparisons and chips without raw JSON formatting.
- **Governance Gate Logs**: Records every reviewer approval, rejection, and revision request along with timestamps and reviewer remarks.

### 4. Multi-Tenant SaaS Governance & Dynamic Branding
- **Tenant Isolation**: Every database query and storage bucket is strictly scoped by `org_id`.
- **Dynamic Plan Tiers**: Starter, Professional, Enterprise, and Custom tiers with automated license limit validation (Active Users, Active Projects, Storage Limits).
- **Document Identity & Custom Branding Engine**: Tenant organizations can configure custom platform titles, acronyms, company logos, and official invoice headers.
- **Broadcast & Announcement Engine**: Super Admins can dispatch global and targeted announcements with acknowledgment tracking.

### 5. Automated PDF & Export Generation Pipeline
- **QC Story Closure Reports**: Automated generation of comprehensive, publication-ready multi-page PDF summaries containing all 8 stages, charts, evidence photos, team rosters, and review signatures via ReportLab.
- **Bulk CSV / Excel Exporters**: High-speed export of organizational directories, project rosters, and audit logs with custom filter parameters.


### 6. Dynamic Multilingual i18n Engine
- **6 Supported Languages**: English, Hindi, Kannada, Telugu, Tamil, Malayalam.
- **Live DOM Mutation Observers**: Dynamically intercepts client rendering to translate tables, charts, navigation menus, and modal dialogs in real time.

### 7. Dynamic Feature Engine (144 Modules)
- **Granular Module Flags**: 144 modular feature flags managed centrally via `module-map.js` and `feature-engine.js`.
- **Subscription-Tier Enforcement**: Automatically shows or hides UI modules based on tenant plan permissions.

---

## 👥 Role-Based Access Control (RBAC) Matrix

| Feature / Capability | Super Admin | Org Admin | CEO / Executive | Quality Facilitator | Project Reviewer | Team Leader | Team Member |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Manage Tenant Orgs & Subscriptions** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Document Identity & Branding** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **User Directory & Bulk Import/Export** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Executive Performance Dashboard** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Create & Initialize Projects** | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Edit 8-Stage Workflow Data** | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Post Facilitator Guidance Notes** | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Gatekeeper Approvals / Revisions** | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **View Audit Trail & Member Lifecycle** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Download PDF QC Story Reports** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 📁 Repository & File Structure

```text
.
├── backend/                     # Decoupled Python/Flask REST API Service
│   ├── app/
│   │   ├── config/              # Environment configurations & secret management
│   │   ├── domain/              # Pure business entities, policies & subscription engine
│   │   │   ├── models/          # Entity definitions
│   │   │   └── services/        # Quota verification & domain rules
│   │   ├── application/         # Use-case handlers & business orchestrators
│   │   ├── infrastructure/      # Database models, ORM mappings & external mailers
│   │   │   └── database/        # SQLAlchemy schema (35+ domain models)
│   │   ├── presentation/        # REST route blueprints, JWT middleware & validators
│   │   │   ├── routes/          # Modular API endpoints (auth, project, analytics, admin, sop)
│   │   │   └── middleware/      # JWT authentication, role authorization & guards
│   │   └── utils/               # PDF fillers, report generators, i18n & avatar helpers
│   ├── run.py                   # Server WSGI entry point
│   ├── requirements.txt         # Dependency manifest
│   └── Dockerfile               # Backend container configuration
│
├── frontend/                    # Modern responsive web application client
│   ├── admin/                   # Super Admin portal, audit logs, settings & user management
│   ├── analytics/               # Enterprise KPI dashboards & financial reporting
│   ├── assets/                  # Design system CSS, i18n dictionaries & JS modules
│   │   ├── css/                 # Glassmorphic UI theme styles & utility tokens
│   │   ├── js/                  # Feature engines, stage renderers, analytics & API client
│   │   └── translations/        # Multilingual JSON dictionaries
│   ├── auth/                    # Login, registration, profile & password recovery
│   ├── dashboard/               # Role-tailored dashboards (Admin, CEO, Reviewer, Team Lead)
│   ├── projects/                # 8-Stage problem-solving workspace & standards repository
│   ├── index.html               # Public landing page & initial gatekeeper
│   ├── build.js                 # Frontend asset bundling, minification & cache-busting engine
│   ├── nginx.conf               # Nginx reverse proxy configuration
│   └── Dockerfile               # Frontend container configuration
│
└── docker-compose.yml           # Multi-container orchestration specification
```

---

## 🛠️ Technology Stack

| Tier | Component | Technology / Library |
| :--- | :--- | :--- |
| **Frontend UI** | Architecture | HTML5, Vanilla JavaScript (ES6+), Vanilla CSS3 (Glassmorphic Design System) |
| | Component Grid | Bootstrap 5 Grid, Flexbox Layouts |
| | Visuals & Charts | Lucide Icons, Chart.js |
| | Translation | Custom MutationObserver i18n Engine (6 Indian Languages) |
| **Backend API** | Framework | Python 3.10+, Flask RESTful Blueprint Architecture |
| | ORM & DB Driver | SQLAlchemy 2.0+, Psycopg2-binary |
| | Auth & Security | Flask-JWT-Extended, Flask-Bcrypt, CORS, ActionLock |
| | Document Engine | ReportLab, PyPDF2, OpenPyXL, Pandas |
| **Database** | Database Engine | PostgreSQL 15+ (Neon Serverless / Local PostgreSQL) |
| **DevOps & Cloud** | Containers | Docker, Docker Compose |
| | Reverse Proxy | Nginx, Cloudflare Edge |

---

## 🚀 Installation & Quick Start

### Prerequisites
- **Python 3.10+**
- **PostgreSQL 14+** (or Neon Serverless PostgreSQL connection string)
- **Node.js 18+** (for frontend build & bundling)
- **Docker & Docker Compose** (optional, for containerized deployment)

---

### Environment Configuration

Create a `.env` file in the `backend/` directory:

```env
# Flask Application Environment
FLASK_APP=run.py
FLASK_ENV=production
SECRET_KEY=your_super_secret_flask_key_here
JWT_SECRET_KEY=your_super_secret_jwt_key_here

# Database Connection (PostgreSQL / Neon)
DATABASE_URL=postgresql://postgres:password@127.0.0.1:5432/ifqmmm

# File Uploads Directory
UPLOAD_FOLDER=uploads

# Razorpay Payment Gateway (Optional for Billing)
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret

# Email Service (Optional for Mailers)
MAIL_SERVER=smtp.resend.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=resend
MAIL_PASSWORD=your_resend_api_key
MAIL_DEFAULT_SENDER=notifications@qcms.internal
```

---

### Option A: Docker Deployment (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/harshith1432/imfq-QCMS.git
cd imfq-QCMS

# 2. Build and launch services
docker-compose up --build -d

# 3. Verify running containers
docker-compose ps
```

- **Web Application**: `http://localhost:80`
- **Backend REST API**: `http://localhost:5000`

---

### Option B: Manual Local Setup

#### 1. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # On Linux/macOS: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
python run.py
```

#### 2. Frontend Build (Asset Bundling & Cache-Busting)
```bash
cd ../frontend

# Build minified asset bundles with cache-busting content hashes
node build.js
```

---

## 🔄 Automated CI/CD & Deployment Pipeline

Every push or pull-request to `main` triggers the automated GitHub Actions pipeline with database migrations, security scans, health checks, and smoke tests:

```text
Git push/merge to main
        ↓
Install dependencies (pip install -r requirements.txt, pytest, flake8, bandit)
        ↓
Run tests (pytest tests -v, flake8 syntax checks)
        ↓
Security scan (Bandit SAST vulnerability inspection)
        ↓
Build Docker image (Container build verification)
        ↓
Deploy (Hostinger VPS / Target Server via SSH)
        ↓
Run database migration (docker compose exec backend flask db upgrade)
        ↓
Health check (Liveness /health/live & Readiness /health/ready retry loop)
        ↓
Smoke test (Automated scripts/smoke_test.py validating critical endpoints)
        ↓
Deployment successful 🎉
```

---

## 🗄️ Storage Architecture & Provider Abstraction

QCMS features a **provider-independent storage abstraction layer** enabling seamless switching between **Supabase Storage** (development & testing) and **Azure Blob Storage** (production) without altering application code or compromising tenant security:

```text
QCMS Frontend Client
       │
       ▼
QCMS Flask Backend API
       │
[JWT Authentication & Session Verification]
       │
[5-Factor File Access Authorization Engine]
(Tenant Isolation / Role RBAC / Resource Ownership)
       │
       ▼
StorageService (Provider-Independent Facade)
       │
 ┌─────┴─────────────────────┬───────────────────────────┐
 ▼                           ▼                           ▼
SupabaseStorageProvider    AzureBlobStorageProvider    LocalStorageProvider
(Dev: private bucket 'ifqmqc') (Prod: Azure Blob Container) (Local Disk / Fallback)
```

### Switching Storage Providers

Switching the active storage backend requires only changing the `STORAGE_BACKEND` environment variable:

#### 1. Development & Testing (Supabase Storage)
```env
STORAGE_BACKEND=supabase
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-server-only-service-role-secret
SUPABASE_STORAGE_BUCKET=ifqmqc
```
- Operates on the private bucket `ifqmqc`.
- Credentials remain strictly on the backend.
- Generates 15-minute time-limited signed download URLs via `/storage/v1/object/sign/ifqmqc/<path>`.

#### 2. Production (Azure Blob Storage)
```env
STORAGE_BACKEND=azure
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;
AZURE_STORAGE_CONTAINER_NAME=qcms-uploads
AZURE_STORAGE_BLOB_URL=https://youraccount.blob.core.windows.net/qcms-uploads
```
- Connects to private container `qcms-uploads`.
- Generates 15-minute time-limited SAS signed URLs.

#### 3. Local Filesystem / Testing Fallback
```env
STORAGE_BACKEND=local
UPLOAD_FOLDER=uploads
```

---

## 🔌 API Endpoints Overview

| Blueprint | Route Prefix | Key Functionalities |
| :--- | :--- | :--- |
| **Authentication** | `/api/auth` | Login, register, profile (`/me`), session heartbeat, password reset, GPS telemetry |
| **Projects & Workflow** | `/api/projects` | Project CRUD, 8-stage data save/load, stage review approval, presence heartbeat |
| **Performance Analytics** | `/api/analytics` | Project roster, KPI metrics, Before/After savings, member lifecycle audit logs |
| **Organization Admin** | `/api/admin` | User management, plants, departments, bulk CSV export/import, org audit logs |
| **Super Admin** | `/api/super-admin` | Tenant provisioning, plan tier limits, document branding, global announcements |
| **SOP Repository** | `/api/sop` | Standard operating procedure builder, master templates, version control |
| **Reports & Export** | `/api/reports` | Multi-page PDF storybooks, Excel exports, ISO certificates |
| **Support Desk** | `/api/support` | Ticket submission, status updates, priority resolution tracking |

---

## 🔒 Security, Compliance & Reliability

1. **Strict Multi-Tenant Data Isolation**: Every SQL query and storage asset is guarded by `org_id` scoping to prevent cross-tenant data leaks.
2. **JWT Scoping & Expiration**: Access tokens are signed with cryptographic secrets and expire automatically, with active presence heartbeats verifying live sessions.
3. **Password Security**: Passwords are encrypted using salted multi-round Bcrypt hashing.
4. **Client-Side Deduplication & Idempotency**: ActionLock engine prevents duplicate form submissions and write requests via unique `Idempotency-Key` headers.
5. **Role-Based Authorization Decorators**: Protected routes enforce strict RBAC checks (`@admin_required`, `@super_admin_required`, `@role_required`).

---

## 📄 License & Copyright

Designed and engineered for enterprise quality governance, industrial compliance, and continuous operational excellence.


