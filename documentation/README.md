# 📚 QCMS Enterprise OS — Documentation Hub & Technical Reference Library

Welcome to the centralized documentation library for **QCMS Enterprise OS**. This directory contains all technical blueprints, architectural specifications, AI/RAG algorithm explanations, database models, knowledge transfer documents, and presentations.

---

## 🗂️ Documentation Directory Structure

\\	ext
documentation/
├── README.md                                          <-- This master index & roadmap
│
├── architecture/                                      <-- Core system architecture & database schema
│   ├── QCMS_MASTER_ARCHITECTURE.md                   # Complete system architectural blueprint
│   ├── QCMS_PERFORMANCE_OPTIMIZATION_AND_LATENCY_REPORT.md  # Latency & performance optimization benchmarks
│   ├── qcms_database_architecture_report.html         # Interactive database visualizer & schema documentation
│   └── qcms_database_architecture_report.pdf          # Full printable database architecture report (5MB+)
│
├── ai_and_rag/                                        <-- AI Assistant, Neural RAG & Vector similarity
│   ├── quality_ai_feature_documentation.html          # Quality AI feature overview, DMAIC integration & prompts
│   ├── quality_ai_feature_documentation.pdf           # Printable Quality AI feature guide
│   ├── neural_rag_deep_dive.html                      # Deep-dive interactive guide into Neural RAG pipeline
│   ├── neural_rag_deep_dive.pdf                       # Printable Neural RAG technical whitepaper
│   ├── vector_cosine_similarity_explained.html        # Mathematical foundations & cosine vector matching visualizer
│   └── vector_cosine_similarity_explained.pdf         # Printable vector mathematics reference guide
│
├── knowledge_transfer_and_guides/                     <-- Workflows, Stage gates, and onboarding
│   ├── QCMS_Comprehensive_Knowledge_Transfer.pdf      # Complete end-to-end KT manual for new team members
│   ├── QCMS_KT_Documentation.html                     # Web-based KT reference guide
│   ├── QCMS_KT_Documentation.pdf                      # Printable KT guide
│   ├── README_STAGES.md                               # Complete 8-Stage DMAIC Quality Circle workflow specification
│   └── Reporter.md                                    # PDF & QC Storybook generation engine specification
│
├── presentations/                                     <-- Executive slide decks & presentations
│   ├── qcms_presentation.html                         # Interactive web-based presentation deck
│   └── qcms_enterprise_presentation.pdf               # High-resolution executive presentation deck
│
├── api/                                               <-- REST API endpoints & contract reference
│   └── API_DOCUMENTATION.md                           # REST API routes, request/response contracts & auth schemas
│
└── changelog/                                         <-- Version history & release notes
    └── QCMS_CHANGELOG.md                              # Historical changelog & platform evolution
\
---

## 🧭 Navigation & Reading Guide

### 1. 🏗️ Architecture & Database
* **[QCMS Master Architecture](./architecture/QCMS_MASTER_ARCHITECTURE.md)**: High-level Clean Architecture, Domain-Driven Design (DDD), Flask application factory, and multi-tenant security layers.
* **[Performance & Latency Optimization Report](./architecture/QCMS_PERFORMANCE_OPTIMIZATION_AND_LATENCY_REPORT.md)**: Audit and benchmark results showing sub-200ms latency, Redis caching, Gunicorn thread optimization, and database connection pooling.
* **[Database Architecture Report (HTML)](./architecture/qcms_database_architecture_report.html) / [(PDF)](./architecture/qcms_database_architecture_report.pdf)**: Complete entity-relationship diagram (ERD), tables, indexes, constraints, and audit log schemas.

### 2. 🧠 Artificial Intelligence & Neural RAG
* **[Quality AI Assistant Documentation (HTML)](./ai_and_rag/quality_ai_feature_documentation.html) / [(PDF)](./ai_and_rag/quality_ai_feature_documentation.pdf)**: Explains the built-in AI assistant, root cause generator, 5-Why analyzer, and DMAIC countermeasure suggestions.
* **[Neural RAG Deep Dive (HTML)](./ai_and_rag/neural_rag_deep_dive.html) / [(PDF)](./ai_and_rag/neural_rag_deep_dive.pdf)**: Explains the Retrieval-Augmented Generation pipeline across past closed quality projects and historical deviations.
* **[Vector Cosine Similarity Explained (HTML)](./ai_and_rag/vector_cosine_similarity_explained.html) / [(PDF)](./ai_and_rag/vector_cosine_similarity_explained.pdf)**: Mathematical guide on TF-IDF term frequency vectors, cosine angle distance formulas, and similarity thresholds.

### 3. 🔄 8-Stage DMAIC Quality Circle Workflow
* **[8-Stage Workflow Specifications](./knowledge_transfer_and_guides/README_STAGES.md)**: Step-by-step breakdown of Stages 1 through 8, input fields, gatekeeper approvals, Reviewer impact verification, CEO final sign-off, and auto-archiving.
* **[Knowledge Transfer Manual (PDF)](./knowledge_transfer_and_guides/QCMS_Comprehensive_Knowledge_Transfer.pdf)**: Comprehensive guide for developers, system administrators, and quality circle facilitators.
* **[QC Storybook Reporter Specification](./knowledge_transfer_and_guides/Reporter.md)**: ReportLab PDF engine specifications for automated generation of presentation-ready QC storybooks.

### 4. 🌐 REST API Reference
* **[API Documentation](./api/API_DOCUMENTATION.md)**: Complete catalog of REST endpoints spanning Authentication, Projects, 8 Stages, Analytics, SuperAdmin, Subscriptions, Audit Logs, and Storage.

---

## ⚡ Quick Links
- **Production Web Application**: [https://imfq-qcms.vercel.app](https://imfq-qcms.vercel.app)
- **Production REST API**: [https://imfq-qcms.onrender.com](https://imfq-qcms.onrender.com)
- **GitHub Repository**: [https://github.com/IFQM-QCMS/imfq-QCMS](https://github.com/IFQM-QCMS/imfq-QCMS)
