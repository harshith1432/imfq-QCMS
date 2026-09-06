# QCMS Enterprise OS — Quality & Continuous Improvement Management System

[![Production Frontend](https://img.shields.io/badge/Frontend-Live%20on%20Vercel-black.svg?logo=vercel)](https://imfq-qcms.vercel.app)
[![Production Backend](https://img.shields.io/badge/Backend-Live%20on%20Render-46E3B7.svg?logo=render)](https://imfq-qcms.onrender.com)
[![GitHub Repository](https://img.shields.io/badge/GitHub-IFQM--QCMS%2Fimfq--QCMS-181717.svg?logo=github)](https://github.com/IFQM-QCMS/imfq-QCMS)
[![System Architecture](https://img.shields.io/badge/Architecture-Clean%20Architecture%20%7C%20DDD-blue.svg)](#-system-architecture--data-flow)
[![Python Version](https://img.shields.io/badge/Python-3.11%2B-brightgreen.svg)](https://www.python.org/)
[![Backend Framework](https://img.shields.io/badge/Backend-Flask%203.1%20%7C%20SQLAlchemy%202.0-red.svg)](https://flask.palletsprojects.com/)
[![Database Engine](https://img.shields.io/badge/Database-PostgreSQL%2017.6%20%7C%20Supabase-3ECF8E.svg?logo=supabase)](https://supabase.com/)
[![Cache & Locks](https://img.shields.io/badge/Cache-Redis%207.2-DC382D.svg?logo=redis)](https://redis.io/)
[![UI Architecture](https://img.shields.io/badge/Frontend-Vanilla%20ES6%2B%20%7C%20Glassmorphic%20SPA-purple.svg)](#-frontend-architecture--client-driven-logic)
[![Security & Auth](https://img.shields.io/badge/Security-JWT%20%7C%20RBAC%20%7C%20ActionLock%20%7C%20Multi--Tenant-green.svg)](#-security-compliance--telemetry)
[![Module Engine](https://img.shields.io/badge/Feature%20Engine-144%20Modular%20Flags-orange.svg)](#-dynamic-feature-engine-144-modular-flags)
[![i18n Engine](https://img.shields.io/badge/i18n-6%20Languages%20(DOM%20Observer)-yellow.svg)](#-dynamic-multilingual-i18n-translation-engine)

An enterprise-grade, high-performance SaaS operating system engineered for structured 8-stage problem solving (**Quality Circle / 8D / DMAIC / Six Sigma**), multi-tenant organization governance, real-time collaborator presence & heartbeat telemetry, automated compliance audit reporting, 7 QC Tools statistical analytics, AI-powered root cause analysis & RAG knowledge archiving.

> 🌐 **Production Web Application**: [https://imfq-qcms.vercel.app](https://imfq-qcms.vercel.app)  
> 🔗 **Production API Endpoint**: [https://imfq-qcms.onrender.com](https://imfq-qcms.onrender.com)  
> 📦 **GitHub Repository**: [https://github.com/IFQM-QCMS/imfq-QCMS](https://github.com/IFQM-QCMS/imfq-QCMS)  

---

## 📑 Table of Contents

1. [Executive Overview & Value Proposition](#-executive-overview--value-proposition)
2. [System Architecture & Data Flow](#-system-architecture--data-flow)
3. [Frontend Architecture & Client-Driven Logic](#-frontend-architecture--client-driven-logic)
   - [Client-Driven Philosophy](#client-driven-philosophy)
   - [Directory & File Organization](#frontend-directory--file-organization)
   - [Core Client Singletons (`api.js`, `ActionLock`, `OctaQube`)](#core-client-singletons)
   - [Auth Guard & Role Normalization Engine](#auth-guard--role-normalization-engine)
   - [Strict Role-Based Routing & Dashboard Whitelist Matrix](#strict-role-based-routing--dashboard-whitelist-matrix)
   - [Dynamic Feature Engine (144 Modular Flags)](#dynamic-feature-engine-144-modular-flags)
   - [Dynamic Multilingual i18n Translation Engine](#dynamic-multilingual-i18n-translation-engine)
   - [Dual-Theme Engine & Dynamic Organization Branding](#dual-theme-engine--dynamic-organization-branding)
   - [Mobile-First Adaptive UX & Touch Gestures](#mobile-first-adaptive-ux--touch-gestures)
4. [The 8-Stage DMAIC Quality Circle Workflow](#-the-8-stage-dmaic-quality-circle-workflow)
   - [Stage-by-Stage Workflow Specifications](#stage-by-stage-workflow-specifications)
   - [Approval Gates & Decision Logic](#approval-gates--decision-logic)
   - [Knowledge Repository Auto-Archiving](#knowledge-repository-auto-archiving)
5. [Project Audit Trail & Member Lifecycle Tracking](#-project-audit-trail--member-lifecycle-tracking)
6. [Backend Architecture & Services Layer](#-backend-architecture--services-layer)
   - [Clean Architecture & Domain-Driven Design (DDD)](#clean-architecture--domain-driven-design)
   - [REST API Blueprint Catalog](#rest-api-blueprint-catalog)
   - [Storage Architecture & Provider Abstraction](#storage-architecture--provider-abstraction)
   - [Automated Document Generation (ReportLab QC Storybooks)](#automated-document-generation)
7. [Installation & Deployment Instructions](#-installation--deployment-instructions)
   - [Prerequisites](#prerequisites)
   - [Environment Configuration (`.env`)](#environment-configuration-env)
   - [Option A: Docker Deployment (Recommended)](#option-a-docker-deployment-recommended)
   - [Option B: Manual Local Setup](#option-b-manual-local-setup)
   - [Option C: Production Nginx Deployment](#option-c-production-nginx-deployment)
   - [Frontend Asset Minification & Bundling (`build.js`)](#frontend-asset-minification--bundling-buildjs)
8. [Testing & Quality Assurance](#-testing--quality-assurance)
9. [Operational FAQs & Troubleshooting](#-operational-faqs--troubleshooting)
10. [License & Governance](#-license--governance)

---

## 🌟 Executive Overview & Value Proposition

**QCMS Enterprise OS** is engineered for manufacturing plants, industrial enterprises, automotive OEMs, and quality institutions (such as IFQM) to systematically detect, analyze, resolve, and institutionalize solutions for operational deviations, scrap rates, equipment downtime, and quality defects.

### Core Value Propositions:
1. **Rigid 8-Stage DMAIC Discipline**: Enforces step-by-step problem resolution with independent reviewer and facilitator approval gates preventing premature or unverified stage progression.
2. **Client-Driven Business Logic**: The frontend client orchestrates data structures, formula evaluations (Pareto 80/20, Ishikawa 6M categorizations, ROI deltas), module visibility, and role navigation before dispatching validated payloads to the backend.
3. **Real-Time Collaboration & Concurrency**: Live collaborator presence rosters, heartbeat tracking, and stage-level collision alerts.
4. **Forensic Audit & Lifecycle Traceability**: Full timeline transparency into member transitions, mid-project additions, departures, and stakeholder handovers.
5. **Instant Executive Reporting**: One-click generation of comprehensive, publication-ready multi-page PDF QC Storybooks and ISO 9001 compliance certificates.
6. **Multi-Tenant SaaS Governance**: Complete database and file storage segregation per tenant organization (`org_id`), with custom company branding, plant/department partitioning, and plan quotas.

---

## 🏗️ System Architecture & Data Flow

The platform is architected around clean decoupling between a responsive, glassmorphic Single Page Application (SPA) frontend and a Python/Flask Clean Architecture REST backend:

```mermaid
graph TD
    %% Client Tier
    subgraph Client_Tier["🖥️ FRONTEND CLIENT TIER (Responsive Glassmorphism SPA)"]
        UI_AUTH["Auth & SSO Portal<br/>(Login, MFA, Password Reset, GPS Telemetry)"]
        UI_GUARD["AuthGuard Engine & Role Normalizer<br/>(normalizeRole, Session Heartbeat, Maintenance Mode)"]
        UI_DASH["Role-Tailored Workstations<br/>(SuperAdmin, Admin, CEO, Facilitator, Reviewer, Leader, Member)"]
        UI_WF["8-Stage DMAIC Workspace Engine<br/>(dynamic_renderer.js, stage1-8.js, Fishbone, Pareto)"]
        UI_FEAT["Feature Engine Matrix<br/>(144 Modular Flags via module-map.js)"]
        UI_PRES["Live Presence & Heartbeat Telemetry<br/>(Active Collaborator Roster, Lock Avoidance)"]
        UI_I18N["Dynamic i18n Translation Engine<br/>(6 Languages, DOM MutationObserver)"]
    end

    %% Gateway & Security Layer
    subgraph Gateway_Tier["🛡️ GATEWAY, SECURITY & INTERCEPTOR LAYER"]
        REV_PROXY["Nginx / Cloudflare Edge Proxy<br/>(SSL/TLS Termination, Gzip/Brotli, Static Asset Caching)"]
        ACTION_LOCK["ActionLock Deduplication Map<br/>(In-Flight Lock, Idempotency-Key Header)"]
        CORS_SEC["CORS & Request Sanitizer"]
        JWT_GUARD["JWT Token & Session Validator"]
        RBAC_GUARD["RBAC & Permission Evaluator<br/>(@admin_required, @role_required)"]
        QUOTA_GUARD["Subscription & Quota Guard<br/>(Users, Projects, Storage Verifiers)"]
    end

    %% Application Core Layer
    subgraph App_Tier["⚙️ APPLICATION CORE (Flask Clean Architecture / DDD)"]
        AUTH_SRV["Authentication & User Service<br/>(JWT, Bcrypt, Session Heartbeat Engine)"]
        WF_SRV["8-Stage Quality Workflow Machine<br/>(Sequential State Transitions, Gatekeeper Locks)"]
        PRES_SRV["Collaborator Presence Engine<br/>(Real-Time Heartbeats, TTL Presence Roster)"]
        AUDIT_SRV["Audit Trail & Member Lifecycle Engine<br/>(Tenure Tracking, Stakeholder Replaced, Governance)"]
        ANALYTICS_SRV["Operational Analytics & KPI Calculator<br/>(Before/After Metrics, Velocity, Savings)"]
        GOV_SRV["Multi-Tenant Organization Governance<br/>(Plan Tier Matrix, Document Branding)"]
        DOC_SRV["Automated Document & PDF Engine<br/>(ReportLab QC Story Reports, ISO Certificates)"]
        RAG_SRV["Vector RAG Knowledge Search<br/>(pgvector AI Assistant, Solution Recommendations)"]
    end

    %% Data & Persistence Tier
    subgraph Data_Tier["💾 DATA & PERSISTENCE LAYER"]
        DB[("PostgreSQL Database<br/>(Neon Serverless / Local PostgreSQL)<br/>35+ Relational Domain Entities")]
        STORAGE_FACADE["StorageService Abstraction Layer"]
        SUPABASE["Supabase Private Storage (Dev/Test)"]
        AZURE["Azure Blob Storage (Prod)"]
        LOCAL_STORE["Local Filesystem (Fallback)"]
        REDIS[("Redis 7 In-Memory Cache & Celery Broker")]
    end

    %% Connections
    Client_Tier -->|HTTPS / REST APIs / JSON| REV_PROXY
    REV_PROXY --> CORS_SEC
    CORS_SEC --> JWT_GUARD
    JWT_GUARD --> RBAC_GUARD
    RBAC_GUARD --> QUOTA_GUARD
    QUOTA_GUARD --> App_Tier

    App_Tier -->|SQLAlchemy 2.0 ORM| DB
    App_Tier -->|Celery Worker / Queue| REDIS
    App_Tier -->|File Storage Facade| STORAGE_FACADE
    STORAGE_FACADE --> SUPABASE
    STORAGE_FACADE --> AZURE
    STORAGE_FACADE --> LOCAL_STORE
```

---

## 💻 Frontend Architecture & Client-Driven Logic

### Client-Driven Philosophy

In QCMS Enterprise OS, the **frontend is not a passive display layer**; it acts as the primary orchestrator of business rules, validation schemas, role normalization, UI feature toggles, and workflow calculations:

1. **Schema Definition & Validation**: The backend accepts flexible stage JSON blobs (`project_stages`), while the frontend (`stage1.js` through `stage8.js` and `dynamic_renderer.js`) defines the strict form controls, required asterisks, numerical constraints, 5W2H framing, and Pareto distributions.
2. **Formula & Metric Computations**: Financial ROI, scrap cost reductions, cumulative Pareto percentages, and stage durations are calculated in real time in the browser before being persisted.
3. **Role Normalization**: Multiple raw role variations from database tokens or legacy setups are unified into canonical roles directly in client memory.
4. **Resilience & Offline Handling**: Client action locks, request deduplication, and caching prevent duplicate records even under high latency or network hiccups.

---

### Frontend Directory & File Organization

```text
frontend/
├── admin/                           # Administrative & Governance Interfaces
│   ├── audit-logs.html              # Organization security & action audit logs
│   ├── audit-queue.html             # Project audit & compliance review queue
│   ├── departments.html             # Department master directory management
│   ├── developer-portal.html        # API keys, webhooks, and REST documentation
│   ├── plants.html                  # Plant location master management
│   ├── settings.html                # Organization preferences, branding & colors
│   ├── sop-masters.html             # Standard Operating Procedure master catalog
│   ├── stage-template.html          # Custom stage field & form template builder
│   ├── subscriptions.html           # Plan tiers, license quotas & payment proofs
│   ├── super-admin-stage-template.html # Global template master for SuperAdmins
│   ├── super-admin.html             # SuperAdmin platform operator portal
│   ├── user-management.html         # User provisioning, invitation & role mapping
│   └── users.html                   # User roster, search & filtering
│
├── analytics/                       # Analytics & Reporting
│   └── analytics.html               # KPI dashboards, ROI calculators, velocity charts
│
├── assets/                          # Core Assets, Styles & Client Engines
│   ├── css/                         # Stylesheet Hierarchy
│   │   ├── design-system.css        # Base design tokens, typography, CSS variables
│   │   ├── glass.css                # Glassmorphism aesthetic, cards, backdrops
│   │   ├── glass_overrides.css      # Responsive media queries & accessibility rules
│   │   ├── styles.css               # Utility layout rules
│   │   └── mobile-layout.css        # Mobile-specific stacked cards & responsive tables
│   ├── dist/                        # Minified & cache-busted production bundles
│   │   ├── core.[hash].min.css      # Consolidated & minified stylesheet bundle
│   │   ├── core-bundle.[hash].min.js# Core client runtime (api, components, auth)
│   │   └── stages-bundle.[hash].min.js # Consolidated 8-Stage DMAIC workflow scripts
│   ├── i18n/                        # Multilingual translation dictionaries
│   │   ├── en.json                  # English master dictionary
│   │   ├── hi.json                  # Hindi dictionary
│   │   ├── kn.json                  # Kannada dictionary
│   │   ├── ml.json                  # Malayalam dictionary
│   │   ├── mr.json                  # Marathi dictionary
│   │   ├── ta.json                  # Tamil dictionary
│   │   └── te.json                  # Telugu dictionary
│   └── js/                          # Client JavaScript Runtime Modules
│       ├── action-lock.js           # Button lock & double-submit prevention
│       ├── api.js                   # API client, deduplication, GPS & auth headers
│       ├── auth-guard.js            # Pre-render route protection & role normalizer
│       ├── auth.js                  # Login, registration, MFA & password recovery
│       ├── components.js            # Global OctaQube object, navbars, sidebars, modals
│       ├── enterprise-analytics.js  # Chart.js analytics engine & metrics
│       ├── feature-engine.js        # Dynamic 144-feature toggle & gating engine
│       ├── i18n.js                  # Dynamic DOM MutationObserver translation engine
│       ├── live-presence.js         # Real-time collaborator presence & heartbeats
│       ├── module-map.js            # Central dictionary linking modules to routes/selectors
│       ├── platform-settings.js     # Theme, branding & dynamic custom colors
│       └── stages/                  # 8-Stage DMAIC Workflow Logic
│           ├── dynamic_renderer.js  # Dynamic stage form generator
│           ├── stage1.js            # 5W2H Problem definition & circle roster
│           ├── stage2.js            # KPI baseline, stratification & SOP deviations
│           ├── stage3.js            # 6M Ishikawa fishbone, 5-Why tree, Pareto 80/20
│           ├── stage4.js            # Root cause verification & risk assessment
│           ├── stage5.js            # Countermeasure development & trial plan
│           ├── stage6.js            # Execution tracking & milestone matrix
│           ├── stage7.js            # Financial savings ROI & verification
│           └── stage8.js            # Standardization, SOP update & auto-archive
│
├── auth/                            # Authentication Views
│   ├── forgot-password.html         # Password reset request
│   ├── login.html                   # Multi-tenant login portal
│   ├── profile.html                 # User profile & avatar management
│   ├── register-org.html            # Tenant organization onboarding
│   ├── register.html                # User self-registration
│   └── reset-password.html          # Cryptographic token password update
│
├── dashboard/                       # Role-Tailored Dashboard Views
│   ├── dashboard.html               # Dynamic gateway router (redirects by role)
│   ├── dashboard-admin.html         # Organization Administrator dashboard
│   ├── dashboard-ceo.html           # Executive & C-Suite operational overview
│   ├── dashboard-facilitator.html   # Methodological coach & RCA validation dashboard
│   ├── dashboard-reviewer.html      # Quality gatekeeper approval queue
│   ├── dashboard-team-leader.html   # Project leader workspace & assignments
│   └── dashboard-team-member.html   # Contributor workstation & task roster
│
├── projects/                        # Quality Circle Execution
│   ├── additional-sources.html      # External benchmarks & literature references
│   ├── project-details.html         # Project overview, milestones & audit history
│   ├── projects-repository.html     # Active & archived project repository
│   ├── repository.html              # Knowledge base & RAG search
│   ├── sop-deviation-analysis.html  # SOP deviation logs & failure modes
│   ├── standards.html               # Quality standards & compliance criteria
│   └── workspace.html               # 8-Stage DMAIC Problem-Solving Workspace
│
├── resources/                       # Documentation & Guidance
│   └── user-manual.html             # In-app user manual & operational guides
│
├── rewards/                         # Gamification & Recognition
│   └── leaderboard.html             # Team points, top circles & badges
│
├── build.js                         # Production asset bundler & cache-buster
├── index.html                       # Public marketing landing page
└── page.html                        # Generic CMS content page
```

---

### Core Client Singletons

#### 1. `api.js` (Unified API Client)
- **Token Management**: Automatically extracts JWT from `sessionStorage` or `localStorage` and injects `Authorization: Bearer <token>`.
- **Browser GPS Telemetry**: Captures client coordinates (with fallback reverse-geocoding) and attaches `X-Browser-Location` header to requests.
- **Request Deduplication**: `api.inFlightRequests` Map blocks duplicate concurrent write calls (`POST`, `PUT`, `PATCH`, `DELETE`) with identical payload bodies.
- **Idempotency Engine**: Generates unique `Idempotency-Key` and `X-Idempotency-Key` headers for write operations.
- **Feature Engine Pre-Flight Guard**: Intercepts requests destined for routes belonging to disabled feature modules before any network call occurs.
- **Cold-Start Resilience**: Configured with an `AbortController` timeout (120 seconds) to handle serverless database or backend cold-starts.
- **Session Termination Handling**: Catches 401 Unauthorized responses with `session_terminated` or `expired` reasons and redirects cleanly to `/auth/login.html`.

#### 2. `ActionLock` (UI Collision & Double-Submit Guard)
- Locks form submit buttons immediately upon click.
- Appends an animated loading spinner (`<i class="spinner-border spinner-border-sm me-1"></i>`).
- Automatically releases the lock when the HTTP promise resolves or rejects.

#### 3. `OctaQube` (`components.js`)
- Standardized UI rendering engine providing:
  - `OctaQube.renderNavbar()`: Dynamic top navigation with breadcrumbs, theme toggler, notification center, and user avatar.
  - `OctaQube.renderSidebar()`: Dynamic sidebar with role-filtered links, feature engine module hiding, and active link highlighting.
  - `OctaQube.toast(message, type)`: Non-blocking animated feedback notifications (`success`, `error`, `warning`, `info`).
  - `OctaQube.statusBadge(status)`: Unified glassmorphic badges for project and approval states (`Draft`, `Under Review`, `Approved`, `Revision Requested`, `Closed`).
  - `OctaQube.formatCurrency(val)`: Standardized Indian Rupee (₹) and international currency formatting.
  - `OctaQube.formatDate(val)`: Localized human-readable date and time formatting.

---

### Auth Guard & Role Normalization Engine

`auth-guard.js` executes synchronously inside `<head>` on all protected pages **before the DOM renders**, eliminating page flash:

#### Role Normalization Algorithm (`normalizeRole`)
Both backend and frontend support diverse role representations. `auth-guard.js` normalizes them into **7 canonical roles**:

```javascript
function normalizeRole(role) {
    if (!role) return null;
    let roleStr = typeof role === 'object' ? (role.name || role.role_name || role.role || '') : role;
    if (!roleStr || typeof roleStr !== 'string') return null;
    const r = roleStr.trim().toLowerCase();
    if (r.includes('super')) return 'SuperAdmin';
    if (r === 'admin' || r.includes('organization admin') || r.includes('org admin') || r === 'owner') return 'Admin';
    if (r.includes('leader')) return 'Team Leader';
    if (r.includes('member')) return 'Team Member';
    if (r.includes('facilitator')) return 'Facilitator';
    if (r.includes('reviewer')) return 'Reviewer';
    if (r.includes('ceo') || r.includes('exec')) return 'CEO';
    return roleStr;
}
```

#### Active Session Termination Heartbeat
To ensure administrative session revocation is enforced immediately (e.g., when a Super Admin or Org Admin disables an account or forces logout):
- The client dispatches a background session verification call to `/api/auth/me` every **30 seconds**.
- An immediate verification fires on window focus / tab visibility change if more than 15 seconds have elapsed.
- If a `401 Unauthorized` with `session_terminated` is returned, all local storage is wiped and the browser redirects to `/auth/login.html?reason=session_terminated`.

---

### Strict Role-Based Routing & Dashboard Whitelist Matrix

| Canonical Role | Default Landing Dashboard | Allowed Dashboards | Tenant Config Pages Access | SuperAdmin Portal Access |
| :--- | :--- | :--- | :---: | :---: |
| **SuperAdmin** | `/admin/super-admin.html` | `/admin/super-admin.html`, `/admin/super-admin-stage-template.html` | ❌ *(Isolated)* | ✅ *(Full)* |
| **Admin** *(Org Admin)* | `/dashboard/dashboard-admin.html` | All tenant dashboards | ✅ *(Full)* | ❌ *(Blocked)* |
| **CEO** *(Executive)* | `/dashboard/dashboard-ceo.html` | `/dashboard/dashboard-ceo.html`, `/dashboard/dashboard-admin.html` | ❌ *(Read-Only)* | ❌ *(Blocked)* |
| **Reviewer** | `/dashboard/dashboard-reviewer.html` | `/dashboard/dashboard-reviewer.html` | ❌ | ❌ *(Blocked)* |
| **Facilitator** | `/dashboard/dashboard-facilitator.html` | `/dashboard/dashboard-facilitator.html` | ❌ | ❌ *(Blocked)* |
| **Team Leader** | `/dashboard/dashboard-team-member.html` | `/dashboard/dashboard-team-member.html`, `/dashboard/dashboard-team-leader.html` | ❌ | ❌ *(Blocked)* |
| **Team Member** | `/dashboard/dashboard-team-member.html` | `/dashboard/dashboard-team-member.html` | ❌ | ❌ *(Blocked)* |

> [!IMPORTANT]
> **SuperAdmin Isolation**: SuperAdmins are global platform operators and have no tenant organization context (`org_id: null`). They are strictly barred from opening tenant-scoped operational dashboards (`dashboard-*.html`) and tenant master tables (`plants.html`, `departments.html`, `sop-masters.html`, `subscriptions.html`). SuperAdmins manage tenants, system templates, global announcements, and licenses exclusively via `super-admin.html`.

---

### Dynamic Feature Engine (144 Modular Flags)

The platform features an enterprise dynamic module gating architecture managed centrally by `module-map.js` and `feature-engine.js`:

#### Module Categories & Examples:
1. **IAM**: `users.view`, `users.create`, `users.edit`, `users.delete`, `departments.view`, `roles.manage`.
2. **CORE**: `projects.view`, `projects.create`, `projects.edit`, `projects.delete`, `files.view`, `files.upload`.
3. **WORKFLOW**: `workflow.stages`, `workflow.automation`.
4. **QUALITY**: `qc_tools.7qc`, `qc_tools.pareto`, `qc_tools.fishbone`, `qc_tools.spc`, `qc_tools.histogram`, `qc_tools.scatter`, `qc_tools.5why`.
5. **GOVERNANCE**: `sop.view`, `sop.create`, `sop.training`, `sop.certificate`, `compliance.audit_logs`.
6. **ANALYTICS**: `analytics.view`, `analytics.executive`.
7. **REPORTS**: `reports.view`, `reports.export_pdf`, `reports.export_excel`.
8. **SUPPORT & AI**: `support.tickets`, `notifications.announcements`, `ai.assistant`, `ai.rag`.

#### Multi-Tier Enforcement:
- **Route Level**: If a user navigates to a disabled module route, `auth-guard.js` displays a maintenance banner, disables submission buttons, and displays a warning notification.
- **UI Element Level**: `FeatureEngine.applyAll()` inspects DOM elements marked with `[data-feature='...']` or selectors defined in `module-map.js`, hiding or removing them if disabled.
- **Network Level**: `api.js` blocks outbound HTTP calls directed to endpoints belonging to disabled modules before the network request leaves the browser.

---

### Dynamic Multilingual i18n Translation Engine

The internationalization engine (`assets/js/i18n.js`) provides live, dynamic translation across all dashboard pages:

- **Supported Languages**: English (`en`), Hindi (`hi`), Kannada (`kn`), Telugu (`te`), Tamil (`ta`), Malayalam (`ml`), Marathi (`mr`).
- **Execution Mechanism**:
  1. Loads target dictionary from `/assets/i18n/<lang>.json`.
  2. Builds a flat dictionary map from English master strings to target language strings.
  3. Walks the DOM tree, replacing matching text nodes, input placeholders, titles, and `aria-label` attributes.
  4. Caches original English values in `node._originalText` to allow seamless multi-hop language switching (e.g. Hindi $ightarrow$ Kannada $ightarrow$ Tamil) without text degradation.
  5. Attaches a `MutationObserver` to watch for newly injected dynamic elements (e.g. AJAX tables, modal dialogs, KPI cards) and translates them instantly.
  6. Skips public auth pages (`login.html`, `register.html`) to preserve layout stability.

---

### Dual-Theme Engine & Dynamic Organization Branding

The `ThemeManager` in `components.js` provides comprehensive theme switching and tenant identity personalization:

- **Dark & Light Mode**: Controlled via `window.themeManager.applyTheme('light' | 'dark')`, setting `data-theme` on the root `<html>` element. Automatically defaults to system preferences (`prefers-color-scheme`) if no user preference exists.
- **Tenant Brand Customization**:
  - Custom platform title & organization acronym (e.g. `IFQM QCMS`, `ACME Quality Circle`).
  - Official company logo injection in top navbar and login screens.
  - Primary, secondary, and accent colors injected directly into CSS custom properties (`--ds-primary`, `--ds-accent`, `--ds-surface`).
  - Dynamic invoice headers and PDF certificate watermarks.

---

### Mobile-First Adaptive UX & Touch Gestures

Industrial floor operators and quality facilitators often access QCMS on mobile devices and rugged factory tablets:

1. **Responsive Data Tables**: On screens $\le 768	ext{px}$, tables in `.table-responsive` retain strict cell alignment, preventing awkward multi-line title wrapping while preserving horizontal touch scrolling.
2. **Touch Drag & Momentum Scrolling**: Integrated `enableDragScroll()` allows touch swiping and desktop mouse dragging across tab groups (`#facTabs`, `.ds-tab-group`) and wide data tables (`.table-responsive`).
3. **Mobile Visual Indicators**: Compact `<span class="badge"><i data-lucide="arrow-left-right"></i> Scroll</span>` hints in card headers provide clear affordance to mobile users.
4. **Overscroll Protection**: `overscroll-behavior-x: contain !important;` and `touch-action: pan-x pan-y !important;` prevent Android Chrome or iOS Safari history-swipe gestures from interrupting horizontal table navigation.

---

## 🔄 The 8-Stage DMAIC Quality Circle Workflow

QCMS enforces a sequential problem-solving lifecycle. Every project proceeds through eight rigid milestones governed by designated gatekeepers:

```mermaid
graph TD
    classDef tl fill:#d4edda,stroke:#28a745,color:#155724;
    classDef rev fill:#cce5ff,stroke:#004085,color:#004085;
    classDef fac fill:#fff3cd,stroke:#856404,color:#856404;
    classDef sys fill:#f8d7da,stroke:#721c24,color:#721c24;

    S1["Stage 1: Problem Definition & Initiation<br/>(5W2H, Team Roster, Containment, Baseline)"] -->|Facilitator & Management Sign-Off| S2["Stage 2: Observation & Data Collection<br/>(Stratification 4M/1E, SOP Deviations, Evidence)"]
    S2 -->|Reviewer Sign-Off| S3["Stage 3: Cause Identification<br/>(Ishikawa 6M, 5-Why Analysis, Pareto 80/20)"]
    S3 -->|Facilitator RCA Validation| S4["Stage 4: Root Cause Analysis & Verification<br/>(Hypothesis Validation, Risk Assessment)"]
    S4 -->|Reviewer Sign-Off| S5["Stage 5: Countermeasure Planning<br/>(Action Matrix 3W1H, Trial Run Setup)"]
    S5 -->|Reviewer Sign-Off| S6["Stage 6: Implementation & Execution<br/>(Milestone Tracking, Change Management)"]
    S6 -->|Reviewer Sign-Off| S7["Stage 7: Performance Verification & ROI<br/>(Before/After Delta, Financial Savings)"]
    S7 -->|Reviewer Sign-Off| S8["Stage 8: Standardization & Project Closure<br/>(SOP Institutionalization, Lessons Learned)"]

    S8 -->|Final Reviewer Sign-Off| S8_Decision{Final Approval?}
    S8_Decision -->|Approved| CLOSED["Project Status: Closed"]
    S8_Decision -->|Revision Requested| S8

    CLOSED --> AUTO_ARCHIVE["Auto-Archive Engine"]
    AUTO_ARCHIVE --> KB[("Knowledge Repository")]
    KB --> RAG_EMBED["Vector RAG Embedding Generation"]

    class S1,S3 fac;
    class S2,S4,S5,S6,S7,S8_Decision rev;
    class CLOSED,AUTO_ARCHIVE,KB,RAG_EMBED sys;
```

---

### Stage-by-Stage Workflow Specifications

#### Stage 1: Problem Definition & Team Formation
- **Objective**: Establish the project charter, build the cross-functional circle, quantify initial baseline metrics, and define the problem using **5W2H** methodology.
- **Core Sections**:
  - *Team Roster*: Team Leader, Facilitator, Reviewer, and participating members.
  - *5W2H Framing*: What, Where, When, Who, Why, How Discovered, How Big.
  - *Baseline KPI*: Baseline scrap rate, PPM, defect rate, downtime hours, financial loss.
  - *Emergency Containment*: Containment actions taken immediately to protect customer/line.
  - *Gantt Milestones*: Target completion dates for each of the 8 stages.
- **Mandatory Approvers**: **Facilitator** and **Management**.

#### Stage 2: Observation & Data Collection
- **Objective**: Collect empirical data from the gemba (shop floor) and stratify defects across categories.
- **Core Sections**:
  - *Stratification*: Data categorizations by 4M/1E (Man, Machine, Material, Method, Environment).
  - *SOP Deviation Analysis*: Identifying where existing standards were bypassed or absent.
  - *Evidence Uploads*: Timestamped photos, inspection sheets, and measurement logs.
- **Mandatory Approver**: **Reviewer**.

#### Stage 3: Cause Identification & Analysis
- **Objective**: Brainstorm and categorize potential causes using standard quality tools.
- **Core Sections**:
  - *Ishikawa (Fishbone) Diagram*: Interactive 6M cause mapping (Man, Machine, Material, Method, Measurement, Milieu/Environment).
  - *5-Why Analysis*: Multi-level root cause drill-down tree.
  - *Pareto 80/20 Chart*: Defect frequency ranking with cumulative percentage curve to pinpoint vital few causes.
- **Mandatory Approver**: **Facilitator** (validates RCA logic).

#### Stage 4: Root Cause Verification & Hypothesis Testing
- **Objective**: Experimentally test and verify whether identified root causes reproduce the problem.
- **Core Sections**:
  - *Hypothesis Matrix*: Proposed causes tested against gemba observations.
  - *Verification Tests*: Controlled trial testing to confirm true root causes.
  - *Risk Assessment*: Evaluating potential side-effects of eliminating identified causes.
- **Mandatory Approver**: **Reviewer**.

#### Stage 5: Countermeasure Planning & Solution Development
- **Objective**: Formulate targeted, permanent countermeasures preventing recurrence.
- **Core Sections**:
  - *Countermeasure Matrix (3W1H)*: What will be done, Who is responsible, When is the deadline, How will it be implemented.
  - *Cost-Benefit Evaluation*: Capital expenditure vs. expected monthly defect savings.
  - *Trial Implementation Plan*: Pilot testing protocols before full rollout.
- **Mandatory Approver**: **Reviewer**.

#### Stage 6: Implementation & Change Management
- **Objective**: Execute approved countermeasures on the production line.
- **Core Sections**:
  - *Action Execution Logs*: Step-by-step progress tracking against milestones.
  - *Trial Run Verification*: Production metrics during the pilot phase.
  - *Task Completion Matrix*: Member-specific task sign-offs.
- **Mandatory Approver**: **Reviewer**.

#### Stage 7: Performance Verification & Benefits Realization
- **Objective**: Measure post-countermeasure performance against baseline measurements from Stage 1 & 2.
- **Core Sections**:
  - *Before vs. After Comparison*: Side-by-side KPI metric verification (Yield, Defect %, OEE, Scrap).
  - *Tangible Savings Calculator*: Direct material, labor, and rework cost reductions.
  - *Intangible Benefits*: Safety improvements, morale boosts, customer satisfaction metrics.
  - *Sustainability Verification*: Audit confirming stability across multiple consecutive shifts.
- **Mandatory Approver**: **Reviewer**.

#### Stage 8: Standardization & Project Closure
- **Objective**: Institutionalize the solution across the organization to ensure defects never recur.
- **Core Sections**:
  - *SOP Integration*: Creation or modification of Standard Operating Procedures.
  - *Training Roster*: Retraining operators on revised procedures.
  - *Horizontal Deployment (Yokoten)*: Sharing findings with other plants or parallel production lines.
  - *Lessons Learned & Final Sign-Off*: Project conclusion commentary.
- **Mandatory Approver**: **Reviewer** (Final approval closes project).

---

### Approval Gates & Decision Logic

Every stage progression requires formal review:
- **Approval Actions**: Gatekeepers can **Approve** (advancing to the next stage) or **Request Revisions** (sending the stage back with specific feedback notes).
- **Validation Locks**: When a stage is submitted for review, input fields are locked in read-only mode for the author team until the reviewer acts.
- **Notification Dispatch**: Submissions and review decisions trigger immediate notifications and audit log events.

---

### Knowledge Repository Auto-Archiving

When **Stage 8** receives final approval:
1. The project status shifts to `Closed`.
2. The **Auto-Archive Engine** captures the entire 8-stage dataset, attachments, and final metrics.
3. The project is indexed in the **Knowledge Repository** (`/projects/repository.html`).
4. Vector embeddings are generated for the problem statement, root cause, and countermeasures via the backend **pgvector** service, allowing future teams to search and retrieve historical solutions using natural language queries.

---

## 🔍 Project Audit Trail & Member Lifecycle Tracking

QCMS maintains a comprehensive, forensic audit log of all project events and team transitions:

```text
[Project Timeline & Member Lifecycle]
├─ Inception Roster (Aug 01)
│  ├─ Team Leader: Rajan Verma
│  ├─ Facilitator: in_project_facilitator (Active: Aug 01 -> Aug 24)
│  └─ Members: Amit K., Deepa S., Suresh M.
├─ Mid-Project Member Added (Aug 15)
│  └─ Member: Priya Patel (Joined at Stage 2 · Added by Rajan Verma)
├─ Member Departure & Handover (Aug 24)
│  ├─ Departed Member: Suresh M. (Active: Aug 01 -> Aug 24 · Tenure: 23 days)
│  └─ Stakeholder Replaced: Facilitator replaced by Anita Das (Active: Aug 24 -> Present)
└─ Final Approval & Closure (Sep 05)
   └─ Reviewer: Dr. K. Ramanathan (Approved Stage 8)
```

- **Member Lifecycle Tracking**: Automatically tracks join dates, departure dates, total active tenure in days, and the identity of the actor who performed the transition.
- **Stakeholder Handovers**: Detects changes in Team Leaders, Facilitators, or Reviewers mid-project and visualizes both historical and current tenures.
- **Human-Readable Diff Engine**: Translates raw database JSON delta logs into clear Before/After chips and metric comparisons.

---

## ⚙️ Backend Architecture & Services Layer

### Clean Architecture & Domain-Driven Design (DDD)

The backend is organized following strict Clean Architecture and DDD principles:

```text
backend/app/
├── config/                  # Environment & secret configuration
│   ├── database.py          # SQLAlchemy engine & pooling config
│   └── settings.py          # Global app configuration & environment variables
├── domain/                  # Pure enterprise business models & rules
│   ├── models/              # Entity definitions (User, Project, Stage, SOP)
│   └── services/            # Pure business services (StorageCalculator, QualityAssistant)
├── application/             # Application use cases & orchestrators
│   ├── dtos/                # Data Transfer Objects
│   └── services/            # ProjectWorkflowService, AuditService
├── infrastructure/          # Database implementations & external adapters
│   ├── database/            # SQLAlchemy models (35+ relational entities)
│   ├── repositories/        # Database access repository implementations
│   ├── storage/             # Supabase, Azure Blob & Local storage providers
│   └── vector_db/           # Vector embeddings & RAG search service
├── presentation/            # REST API transport layer
│   ├── middleware/          # JWT verification, RBAC guards, CORS & ActionLock
│   └── routes/              # Modular Flask API blueprints
└── utils/                   # ReportLab PDF fillers, CSV exporters, avatars & helpers
```

---

### REST API Blueprint Catalog

| Blueprint | Route Prefix | Primary Responsibilities |
| :--- | :--- | :--- |
| `auth_routes` | `/api/auth` | Login, registration, profile (`/me`), session verification, password reset, GPS telemetry |
| `project_routes`| `/api/projects` | Project CRUD, team assignment, stage data persistence, filtering by plant/department |
| `workflow_routes`| `/api/workflow` | Stage transition gates, approvals, reviewer sign-offs, presence heartbeats |
| `facilitator_routes`| `/api/facilitator` | Assistance request replies, RCA validation locks, facilitator coaching notes |
| `analytics_routes`| `/api/analytics` | Plant/department metrics, Before/After savings, velocity benchmarks, project rosters |
| `admin_routes` | `/api/admin` | User management, plants, departments, bulk CSV import/export, organization audit logs |
| `super_admin_routes`| `/api/super-admin` | Multi-tenant provisioning, plan tier limits, custom branding, global announcements |
| `feature_engine_routes`| `/api/feature-engine` | Module flag toggles, organization feature permission evaluation |
| `sop_routes` | `/api/sops` | Standard Operating Procedure management, master templates, training quizzes |
| `rag_routes` | `/api/rag` | Vector search over historical projects, AI problem-solving recommendations |
| `notification_routes`| `/api/notifications` | Platform announcements, user notification inbox, acknowledgment tracking |
| `support_routes` | `/api/support` | Ticket submission, status tracking, helpdesk resolution workflows |

---

### Storage Architecture & Provider Abstraction

QCMS features a **provider-independent storage facade** (`StorageService`) enabling zero-downtime switching between cloud providers:

```text
               QCMS Application Code
                         │
                         ▼
        StorageService (Provider Abstraction)
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
SupabaseStorageProvider AzureBlobProvider LocalStorageProvider
 (Dev: private bucket) (Prod: Azure Blob)  (Local Fallback)
```

- **Supabase Storage** (Development & Testing): Connects via service role key, generating 15-minute signed URLs via `/storage/v1/object/sign/ifqmqc/<path>`.
- **Azure Blob Storage** (Production): Connects to private container `qcms-uploads`, generating 15-minute SAS signed URLs.
- **Local Filesystem** (Air-Gapped / Fallback): Stores files in the configured `UPLOAD_FOLDER`.

---

### Automated Document Generation

- **ReportLab QC Storybooks**: Generates publication-grade, multi-page PDF documents detailing all 8 DMAIC stages, 6M fishbone diagrams, Pareto charts, evidence photos, team rosters, and review signatures.
- **ISO 9001 Compliance Certificates**: Automated certificate rendering upon successful stage 8 project closure.
- **High-Speed CSV / Excel Exporters**: Streaming exports of project directories, audit trails, and user rosters via pandas/OpenPyXL.

---

## 🚀 Installation & Deployment Instructions

### Prerequisites

- **Python 3.10+** (with `pip` and `venv`)
- **PostgreSQL 14+** (Local PostgreSQL or Neon Serverless PostgreSQL)
- **Node.js 18+** & **npm** (for frontend asset bundling)
- **Redis 7+** (for Celery background tasks and caching)
- **Docker & Docker Compose** (optional, recommended for production)

---

### Environment Configuration (`.env`)

Create a `.env` file in `backend/`:

```env
# Flask Environment
FLASK_APP=run.py
FLASK_ENV=production
SECRET_KEY=generate_a_cryptographically_secure_random_string_here
JWT_SECRET_KEY=generate_another_cryptographically_secure_jwt_string_here
JWT_ACCESS_TOKEN_EXPIRES=86400

# Database Connection (PostgreSQL / Neon)
DATABASE_URL=postgresql://postgres:your_password@127.0.0.1:5432/ifqmmm

# Storage Provider Configuration ('supabase' | 'azure' | 'local')
STORAGE_BACKEND=local
UPLOAD_FOLDER=uploads

# Supabase Storage (Required if STORAGE_BACKEND=supabase)
# SUPABASE_URL=https://your-project-ref.supabase.co
# SUPABASE_SERVICE_ROLE_KEY=your_service_role_secret
# SUPABASE_STORAGE_BUCKET=ifqmqc

# Azure Blob Storage (Required if STORAGE_BACKEND=azure)
# AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;
# AZURE_STORAGE_CONTAINER_NAME=qcms-uploads
# AZURE_STORAGE_BLOB_URL=https://youraccount.blob.core.windows.net/qcms-uploads

# Redis & Celery Worker
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0

# Mail Service (Optional)
# MAIL_SERVER=smtp.resend.com
# MAIL_PORT=587
# MAIL_USE_TLS=True
# MAIL_USERNAME=resend
# MAIL_PASSWORD=your_resend_api_key
# MAIL_DEFAULT_SENDER=notifications@qcms.internal
```

---

### Option A: Docker Deployment (Recommended)

The easiest and most reliable way to run QCMS in production is using Docker Compose:

```bash
# 1. Clone the repository
git clone https://github.com/harshith1432/imfq-QCMS.git
cd imfq-QCMS

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your production database credentials

# 3. Build and launch containers
docker-compose up --build -d

# 4. Check service health
docker-compose ps
```

- **Frontend Application**: `http://localhost:80`
- **Backend REST API**: `http://localhost:5000`
- **Redis Service**: `localhost:6379`

---

### Option B: Manual Local Setup

#### 1. Backend Setup
```bash
cd backend

# Create and activate Python virtual environment
python -m venv venv

# Windows:
venv\Scriptsctivate
# Linux/macOS:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
flask db upgrade

# Start Flask development server
python run.py
```
*Backend runs at: `http://127.0.0.1:5000`*

#### 2. Celery Worker Setup (Terminal 2)
```bash
cd backend
# Windows:
venv\Scriptsctivate
# Linux/macOS:
# source venv/bin/activate

celery -A celery_worker.celery worker --loglevel=info --concurrency=2
```

#### 3. Frontend Setup (Terminal 3)
```bash
cd frontend

# Install devDependencies (clean-css, terser, eslint)
npm install

# Compile minified asset bundles with cache-busting content hashes
node build.js --update-html
```

You can serve the frontend with any static web server (such as Python's built-in HTTP server or Nginx):
```bash
# In frontend/ directory:
python -m http.server 8080
```
*Frontend accessible at: `http://127.0.0.1:8080`*

---

### Option C: Production Nginx Deployment

Example Nginx server block (`/etc/nginx/sites-available/qcms`):

```nginx
server {
    listen 80;
    server_name qcms.yourdomain.com;

    # Gzip Compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # Frontend Static Files
    root /var/www/qcms/frontend;
    index index.html;

    # Static Assets Caching
    location /assets/dist/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA Routing Fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Reverse Proxy to Flask Backend
    location /api/ {
        proxy_pass http://127.0.0.1:5000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket & Long-Polling Support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 120s;
    }
}
```

---

### Option D: Cloud Production Deployment (Vercel & Render)

QCMS Enterprise is optimized for zero-downtime automated deployment across modern cloud platforms:

#### 1. Frontend on Vercel
- **Production URL**: [https://imfq-qcms.vercel.app](https://imfq-qcms.vercel.app)
- **Configuration (`vercel.json`)**:
  - Automatically rewrites `/api/(.*)` requests to the Render backend (`https://imfq-qcms.onrender.com/api/$1`).
  - Seamlessly proxies `/uploads/(.*)` directly to Supabase storage CDN / Render storage endpoints.
  - Deployed directly via Vercel CLI or GitHub CI:
    ```bash
    npx vercel --prod --yes
    ```

#### 2. Backend on Render
- **Production URL**: [https://imfq-qcms.onrender.com](https://imfq-qcms.onrender.com)
- **Container Configuration**: Runs high-efficiency Python 3.11 with Gunicorn multi-threading (`gthread`), preloaded application context, and memory leak prevention (`max_requests = 1000`).
- **Database & Storage**: Connected to Supabase PostgreSQL 17.6 database pooler and Supabase Object Storage bucket (`ifqmqc`).
- **Cache & Concurrency**: Connected to managed Redis 7.2 for sub-50ms distributed locking and KPI caching.

---

### Frontend Asset Minification & Bundling (`build.js`)

The frontend includes a custom build engine that minifies CSS and JavaScript and generates content-hashed bundles for cache-busting:

```bash
cd frontend

# Minify, bundle, and update all HTML entrypoints with hashed links
npm run build:html
# or directly:
node build.js --update-html

# Restore HTML entrypoints to unbundled development mode
npm run restore:html
# or directly:
node build.js --restore-html
```

#### What `build.js` Does:
1. **Core CSS Bundle**: Merges `design-system.css`, `glass.css`, `glass_overrides.css`, `styles.css`, and `mobile-layout.css` into `core.[hash].min.css` using `clean-css`.
2. **Core JavaScript Bundle**: Minifies `api.js`, `components.js`, `auth-guard.js`, `auth.js`, `feature-engine.js`, and `module-map.js` into `core-bundle.[hash].min.js` via `terser`.
3. **Workflow Stages Bundle**: Bundles `dynamic_renderer.js` and `stage1.js` through `stage8.js` into `stages-bundle.[hash].min.js`.
4. **HTML Rewriter**: Updates `<link rel="stylesheet">` and `<script>` tags across all HTML files with new hashes and critical asset preloads (`<link rel="preload">`).

---

## 🧪 Testing & Quality Assurance

### Frontend Test Suite
The frontend includes a Node.js test suite validating role-based access control, routing rules, and syntax integrity:

```bash
cd frontend

# Run all 102 frontend tests
npm test
```

Test coverage includes:
- Role normalization mapping across all variations.
- Strict dashboard access isolation rules.
- Syntax and compilation verification for all 45+ JavaScript files.
- Form manager and dynamic rendering tests.

### Backend Test Suite
```bash
cd backend

# Run Python pytest test suite
pytest tests/ -v

# Run Bandit security SAST scan
bandit -r app/
```

---

## ❓ Operational FAQs & Troubleshooting

### Q1: Why are some features visible in code but hidden in the UI?
**A**: Check the **Feature Engine** (`module-map.js`). If an organization’s active subscription tier disables a feature module (e.g. `qc_tools.spc` or `ai.assistant`), the client hides the UI elements and blocks the associated routes. SuperAdmins can enable modules per tenant from `/admin/subscriptions.html`.

### Q2: How does the system handle mid-project member transitions?
**A**: When a member is removed or replaced in Stage 1, the backend does not delete the audit record. Instead, the **Member Lifecycle Engine** marks the departure timestamp, records the actor who made the change, and calculates their active tenure in days.

### Q3: Why does a 401 error redirect immediately to login?
**A**: QCMS enforces zero-trust active session invalidation. When an administrative session termination occurs or a JWT expires, `api.js` and `auth-guard.js` detect the session state and wipe local storage tokens to prevent stale session tampering.

### Q4: How do I enable dark mode by default for an organization?
**A**: Navigate to **Organization Settings** (`/admin/settings.html`). Select the default theme palette and click **Save Settings**. The preference is persisted in the database and applied to all users belonging to that organization.

### Q5: Can SuperAdmins edit project stage data?
**A**: SuperAdmins are system platform operators and do not belong to specific tenant organizations. They govern tenants, review global metrics, configure system-wide templates, and manage licenses. Project editing is reserved for tenant **Team Leaders**, **Team Members**, **Facilitators**, and **Reviewers**.

---

## 📜 License & Governance

QCMS Enterprise OS is engineered and maintained for industrial quality governance, manufacturing operational excellence, and ISO 9001 compliance standards.

© 2026 **QCMS Enterprise OS (IFQM)**. All rights reserved.
