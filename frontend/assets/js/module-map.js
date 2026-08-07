/**
 * QCMS Feature Engine — Module Mapping Dictionary
 * ===============================================
 * Links all 144 Feature Modules to their corresponding:
 *   - Page routes
 *   - Sidebar items
 *   - DOM element selectors (buttons, modals, tabs, widgets)
 *   - Backend API endpoints
 */

window.QCMS_MODULE_MAP = {
    // ── IAM & USER MANAGEMENT ───────────────────────────────────────────────
    "users.view": {
        category: "IAM",
        name: "View Users",
        route: "/admin/users",
        selectors: ["#nav-users", "[data-feature='users.view']"],
        api: "/api/admin/users"
    },
    "users.create": {
        category: "IAM",
        name: "Create User",
        selectors: ["#btn-create-user", ".btn-add-user", "[data-feature='users.create']"],
        api: "/api/admin/users"
    },
    "users.edit": {
        category: "IAM",
        name: "Edit User",
        selectors: [".btn-edit-user", "[data-feature='users.edit']"],
        api: "/api/admin/users/"
    },
    "users.delete": {
        category: "IAM",
        name: "Delete User",
        selectors: [".btn-delete-user", "[data-feature='users.delete']"],
        api: "/api/admin/users/"
    },
    "departments.view": {
        category: "IAM",
        name: "View Departments",
        route: "/admin/departments",
        selectors: ["#nav-departments", "[data-feature='departments.view']"],
        api: "/api/projects/departments"
    },
    "roles.manage": {
        category: "IAM",
        name: "Manage Roles & Permissions",
        route: "/admin/roles",
        selectors: ["#nav-roles", "[data-feature='roles.manage']"],
        api: "/api/admin/roles"
    },

    // ── CORE PROJECTS & QC WORKFLOW ─────────────────────────────────────────
    "projects.view": {
        category: "CORE",
        name: "View Projects",
        route: "/projects/list.html",
        selectors: ["#nav-projects", "[data-feature='projects.view']"],
        api: "/api/projects"
    },
    "projects.create": {
        category: "CORE",
        name: "Create Project",
        selectors: ["#btn-create-project", ".fab-create-project", "#modal-create-project", "[data-feature='projects.create']"],
        api: "/api/projects"
    },
    "projects.edit": {
        category: "CORE",
        name: "Edit Project Details",
        selectors: [".btn-edit-project", "[data-feature='projects.edit']"],
        api: "/api/projects/"
    },
    "projects.delete": {
        category: "CORE",
        name: "Delete Project",
        selectors: [".btn-delete-project", "[data-feature='projects.delete']"],
        api: "/api/projects/"
    },
    "workflow.stages": {
        category: "WORKFLOW",
        name: "8D/QC Story Workflow Stages",
        selectors: [".workflow-stage-stepper", "#stageTrackerContainer", "[data-feature='workflow.stages']"],
        api: "/api/workflow"
    },
    "workflow.automation": {
        category: "WORKFLOW",
        name: "Automated Stage Transition & Gateways",
        selectors: [".btn-advance-stage", "[data-feature='workflow.automation']"],
        api: "/api/workflow/advance"
    },

    // ── 7 QC TOOLS & SPC STATISTICAL ENGINE ─────────────────────────────────
    "qc_tools.7qc": {
        category: "QUALITY",
        name: "7 QC Tools Suite",
        route: "/qc-tools",
        selectors: ["#nav-qc-tools", "[data-feature='qc_tools.7qc']"],
        api: "/api/project/qc-tools"
    },
    "qc_tools.pareto": {
        category: "QUALITY",
        name: "Pareto Chart Analyzer",
        selectors: ["#tab-pareto", "[data-feature='qc_tools.pareto']"],
        api: "/api/project/qc-tools/pareto"
    },
    "qc_tools.fishbone": {
        category: "QUALITY",
        name: "Cause & Effect (Ishikawa) Diagram",
        selectors: ["#tab-fishbone", "[data-feature='qc_tools.fishbone']"],
        api: "/api/project/qc-tools/fishbone"
    },
    "qc_tools.spc": {
        category: "QUALITY",
        name: "SPC Control Charts (X-Bar, R, P, C)",
        selectors: ["#tab-spc", "[data-feature='qc_tools.spc']"],
        api: "/api/project/qc-tools/spc"
    },
    "qc_tools.histogram": {
        category: "QUALITY",
        name: "Histogram & Process Capability (Cp/Cpk)",
        selectors: ["#tab-histogram", "[data-feature='qc_tools.histogram']"],
        api: "/api/project/qc-tools/histogram"
    },
    "qc_tools.scatter": {
        category: "QUALITY",
        name: "Scatter Diagram & Correlation",
        selectors: ["#tab-scatter", "[data-feature='qc_tools.scatter']"],
        api: "/api/project/qc-tools/scatter"
    },
    "qc_tools.5why": {
        category: "QUALITY",
        name: "5-Why Root Cause Analysis",
        selectors: ["#tab-5why", "[data-feature='qc_tools.5why']"],
        api: "/api/project/qc-tools/5why"
    },

    // ── SOP & COMPLIANCE TRAINING ───────────────────────────────────────────
    "sop.view": {
        category: "GOVERNANCE",
        name: "View Standard Operating Procedures",
        route: "/sops",
        selectors: ["#nav-sops", "[data-feature='sop.view']"],
        api: "/api/sops"
    },
    "sop.create": {
        category: "GOVERNANCE",
        name: "Create & Publish SOP",
        selectors: ["#btn-create-sop", "[data-feature='sop.create']"],
        api: "/api/sops"
    },
    "sop.training": {
        category: "GOVERNANCE",
        name: "SOP Training & Quizzes",
        selectors: ["#tab-sop-training", "[data-feature='sop.training']"],
        api: "/api/sops/training"
    },
    "sop.certificate": {
        category: "GOVERNANCE",
        name: "SOP Compliance Certificate Generator",
        selectors: [".btn-generate-certificate", "[data-feature='sop.certificate']"],
        api: "/api/sops/certificate"
    },

    // ── ANALYTICS & EXECUTIVE REPORTING ─────────────────────────────────────
    "analytics.view": {
        category: "ANALYTICS",
        name: "Analytics Dashboard",
        route: "/analytics",
        selectors: ["#nav-analytics", "[data-feature='analytics.view']"],
        api: "/api/analytics"
    },
    "analytics.executive": {
        category: "ANALYTICS",
        name: "Executive Overview & Cost of Poor Quality (COPQ)",
        selectors: ["#widget-executive-copq", "[data-feature='analytics.executive']"],
        api: "/api/analytics/executive"
    },
    "reports.view": {
        category: "REPORTS",
        name: "Report Hub",
        route: "/reports",
        selectors: ["#nav-reports", "[data-feature='reports.view']"],
        api: "/api/reports"
    },
    "reports.export_pdf": {
        category: "REPORTS",
        name: "PDF Report Export Engine",
        selectors: [".btn-export-pdf", "#btn-download-pdf-report", "[data-feature='reports.export_pdf']"],
        api: "/api/reports/export/pdf"
    },
    "reports.export_excel": {
        category: "REPORTS",
        name: "Excel & CSV Data Export",
        selectors: [".btn-export-excel", ".btn-export-csv", "[data-feature='reports.export_excel']"],
        api: "/api/reports/export/excel"
    },

    // ── REPOSITORY & FILE MANAGEMENT ────────────────────────────────────────
    "files.view": {
        category: "CORE",
        name: "Document Repository Explorer",
        route: "/repository",
        selectors: ["#nav-repository", "[data-feature='files.view']"],
        api: "/api/repository"
    },
    "files.upload": {
        category: "CORE",
        name: "Upload Files & Evidence Attachments",
        selectors: ["#btn-upload-file", ".dropzone-upload", "[data-feature='files.upload']"],
        api: "/api/repository/upload"
    },

    // ── AI ASSISTANT & RAG SEARCH ───────────────────────────────────────────
    "ai.assistant": {
        category: "AI",
        name: "Antigravity AI Quality Assistant",
        selectors: ["#ai-chat-widget", ".btn-open-ai-chat", "[data-feature='ai.assistant']"],
        api: "/api/rag/query"
    },
    "ai.rag": {
        category: "AI",
        name: "Vector RAG Knowledge Search",
        selectors: ["#ai-knowledge-search", "[data-feature='ai.rag']"],
        api: "/api/rag/search"
    },

    // ── SUPPORT & INTEGRATIONS ──────────────────────────────────────────────
    "support.tickets": {
        category: "SUPPORT",
        name: "Support Desk & Ticket Portal",
        route: "/support",
        selectors: ["#nav-support", "[data-feature='support.tickets']"],
        api: "/api/support"
    },
    "notifications.announcements": {
        category: "COMMUNICATION",
        name: "Platform Announcement Banner & Alerts",
        selectors: ["#announcement-banner-container", "[data-feature='notifications.announcements']"],
        api: "/api/announcements"
    },
    "compliance.audit_logs": {
        category: "GOVERNANCE",
        name: "System Audit Logs & Security History",
        route: "/admin/audit-logs",
        selectors: ["#nav-audit-logs", "[data-feature='compliance.audit_logs']"],
        api: "/api/audit"
    }
};

/**
 * Helper to get module code by route or selector.
 */
window.QCMS_MODULE_MAP.findByRoute = function (pathname) {
    for (const [code, item] of Object.entries(window.QCMS_MODULE_MAP)) {
        if (item.route && pathname.startsWith(item.route)) return code;
    }
    return null;
};

/**
 * Helper to get module code by human readable module name.
 */
window.QCMS_MODULE_MAP.findByName = function (name) {
    if (!name) return null;
    const lower = name.trim().toLowerCase();
    for (const [code, item] of Object.entries(window.QCMS_MODULE_MAP)) {
        if (item.name && item.name.toLowerCase() === lower) return code;
    }
    return null;
};
