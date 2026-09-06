# QCMS CHANGELOG
All notable changes to the QCMS Enterprise SaaS platform will be documented in this file.

## [1.2.1] - 2026-05-05
### Fixed
- **Database Schema Sync**: Resolved `psycopg2.errors.UndefinedColumn` by executing the `add_saas_columns.py` migration script.
- Added missing SaaS-related columns to the `organizations` table: `api_key`, `subscription_plan`, `subscription_status`, `trial_ends_at`, `max_users`, `is_white_label`, `multi_plant`, and `api_access`.

---

## [1.2.0] - 2026-05-05
### Added
- **MASTER ARCHITECTURE FINALIZATION**: Updated `QCMS_MASTER_ARCHITECTURE.md` to version 1.2.
- Integrated deep technical details:
    - **RAG-AI Architecture**: Documented the FAISS integration and vector storage in the `new updation/` directory.
    - **Workflow Aliases**: Documented the mapping between legacy models and the new 8-stage methodology to ensure backward compatibility.
    - **RBAC Hierarchy Levels**: Defined the exact numeric levels (0-4) used for permission enforcement.
    - **Frontend Core Utilities**: Added documentation for `ThemeManager` and the `QCMS` utility belt.

---

## [1.1.0] - 2026-05-05
### Added
- **MASTER ARCHITECTURE FORMALIZATION**: Created `QCMS_MASTER_ARCHITECTURE.md` as the definitive engineering blueprint.
- Expanded system documentation to include RBAC, 8-Stage Workflow, and Directory Topology.

### Changed
- Restructured `settings.html` UI to match the main dashboard sidebar design system.

### Fixed
- Improved sidebar navigation consistency across all role-based dashboards.

---

## [1.0.0] - 2026-05-04
### Added
- Initial system structure and base UI implementation.
- Core 8D workflow models in PostgreSQL.
- Glassmorphism design system implementation.
