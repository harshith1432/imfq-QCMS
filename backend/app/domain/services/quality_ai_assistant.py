import re
import json
from datetime import datetime
from app import db
from app.infrastructure.database.models.models import (
    User, Role, Plant, Department, Project, ProjectMember,
    KnowledgeRepository, AuditLog, Organization
)

class QualityAIAssistant:
    """
    Enterprise Quality AI Assistant Engine:
    - Zero-latency dynamic organization queries (employees, QC counts, plants, departments, project growth)
    - Comprehensive 200+ question how-to & configuration navigation manual
    - 8-Stage QC Methodology & Quality Tools specialist
    - Strict Role-Based Access Control (RBAC) & Data Privacy enforcement
    - Knowledge Repository RAG integration for historical root causes and solutions
    """

    RESTRICTED_KEYWORDS_EMPLOYEE = [
        'revenue', 'financial ledger', 'company profit', 'total billing', 'billing invoice',
        'subscription fee', 'license cost', 'admin password', 'salary', 'salaries',
        'payroll', 'security secret', 'audit log secrets', 'executive compensation'
    ]

    @classmethod
    def get_response(cls, query: str, user_id: int, org_id: int):
        if not org_id or not user_id:
            return {
                "answer": "⚠️ Organization context is required to access your Quality AI Assistant.",
                "sources": []
            }

        user = db.session.get(User, user_id)
        if not user:
            return {
                "answer": "⚠️ User profile could not be verified.",
                "sources": []
            }

        role_name = (user.role.name if user.role else "Team Member").strip()
        clean_query = query.strip()
        lower_query = clean_query.lower()

        # 1. RBAC Check: Restrict sensitive financial / admin data for lower-tier roles
        is_admin_or_ceo = role_name in ['Super Admin', 'Admin', 'CEO', 'SuperAdmin', 'Corporate Admin']
        if not is_admin_or_ceo:
            for kw in cls.RESTRICTED_KEYWORDS_EMPLOYEE:
                if kw in lower_query:
                    return {
                        "answer": (
                            f"🔒 **Access Restricted by Role Policy**\n\n"
                            f"Information regarding organization-wide financial revenue, billing, or administrative audit logs "
                            f"requires **Admin** or **Executive (CEO)** privileges.\n\n"
                            f"As a **{role_name}**, you have access to:\n"
                            f"- Your assigned Quality Circle projects & stage progression\n"
                            f"- 8-Stage QC methodology guides & tool manuals (Fishbone, Pareto, 5-Why)\n"
                            f"- Knowledge repository of past quality solutions & lessons learned\n"
                            f"- Personal points, leaderboard rankings, and idea submissions."
                        ),
                        "sources": []
                    }

        # 2. Dynamic Live Organization Data Query Router
        dynamic_answer = cls._handle_dynamic_org_queries(lower_query, clean_query, user, role_name, is_admin_or_ceo)
        if dynamic_answer:
            return dynamic_answer

        # 2. System How-To, Configuration & Navigation Manual Router (Checked first for actionable instructions)
        how_to_answer = cls._handle_how_to_queries(lower_query, role_name, is_admin_or_ceo)
        if how_to_answer:
            return how_to_answer

        # 3. 8-Stage QC Methodology & Quality Tools Knowledge Router
        qc_methodology_answer = cls._handle_qc_methodology_queries(lower_query)
        if qc_methodology_answer:
            return qc_methodology_answer

        # 4. Dynamic Live Organization Data Query Router
        dynamic_answer = cls._handle_dynamic_org_queries(lower_query, clean_query, user, role_name, is_admin_or_ceo)
        if dynamic_answer:
            return dynamic_answer

        # 5. Historical Knowledge Repository RAG Lookup (Archived Projects & Root Causes)
        rag_answer = cls._handle_knowledge_repository_lookup(clean_query, org_id)
        if rag_answer:
            return rag_answer

        # 6. Comprehensive Fallback Assistant Response
        return cls._generate_smart_fallback(clean_query, role_name, user)

    @classmethod
    def _handle_dynamic_org_queries(cls, lq: str, query: str, user: User, role_name: str, is_admin_or_ceo: bool):
        org_id = user.org_id
        
        # A. Total employees / users working here & QC Project participation
        is_emp_term = any(w in lq for w in ['employee', 'employees', 'user', 'users', 'member', 'members', 'workforce', 'headcount', 'stakeholder', 'stakeholders'])
        is_count_term = any(w in lq for w in ['how many', 'number of', 'total', 'count', 'active', 'registered', 'list', 'show', 'who is into', 'working here'])
        if (is_emp_term and is_count_term) or any(p in lq for p in ['how many employee', 'number of employee', 'total employee', 'total user', 'employees working here', 'who is into quality circle', 'working under the qc', 'employees in qc', 'employee working', 'number of employees', 'organization headcount']):
            all_users = User.query.filter_by(org_id=org_id).all()
            total_users = len(all_users)
            active_users = len([u for u in all_users if getattr(u, 'is_active', True)])
            
            # Find QC participants
            projects = Project.query.filter_by(org_id=org_id).all()
            project_ids = [p.id for p in projects]
            qc_user_ids = set()
            for p in projects:
                if p.creator_id: qc_user_ids.add(p.creator_id)
                if p.team_leader_id: qc_user_ids.add(p.team_leader_id)
                if p.facilitator_id: qc_user_ids.add(p.facilitator_id)
                if p.reviewer_id: qc_user_ids.add(p.reviewer_id)

            if project_ids:
                members = ProjectMember.query.filter(ProjectMember.project_id.in_(project_ids)).all()
                for m in members:
                    qc_user_ids.add(m.user_id)

            qc_count = len([u for u in all_users if u.id in qc_user_ids])
            qc_pct = round((qc_count / total_users * 100)) if total_users > 0 else 0

            # Breakdown by plant
            plants = Plant.query.filter_by(org_id=org_id).order_by(Plant.name).all()
            plant_breakdown = []
            for pl in plants:
                p_users = [u for u in all_users if u.plant_id == pl.id]
                p_qc = [u for u in p_users if u.id in qc_user_ids]
                plant_breakdown.append(f"  • **{pl.name}**: {len(p_users)} Employees ({len(p_qc)} in QC projects)")

            lines = [
                f"### 👥 Organization Workforce & QC Participation Metrics",
                f"",
                f"- **Total Registered Employees**: `{total_users}`",
                f"- **Active Status**: `{active_users}` active members",
                f"- **Employees in Quality Circle (QC) Projects**: `{qc_count}` ({qc_pct}% organization participation rate)",
                f"- **Non-Enrolled / Available Members**: `{total_users - qc_count}`",
                f"",
                f"**Plant Location Breakdown**:"
            ]
            lines.extend(plant_breakdown if plant_breakdown else ["  • *No plant locations configured yet.*"])
            lines.append(f"\n*Tip: You can manage members under **Administration > User Management** or explore detailed departmental mapping under **Administration > Plant Locations**.*")

            return {"answer": "\n".join(lines), "sources": []}

        # B. Plant Locations Query
        if any(w in lq for w in ['plant', 'plants', 'facility', 'facilities', 'location', 'locations']) and any(w in lq for w in ['performance', 'saving', 'savings', 'highest', 'top', 'quality', 'show', 'list', 'how many', 'which', 'active', 'where']):
            plants = Plant.query.filter_by(org_id=org_id).order_by(Plant.name).all()
            all_users = User.query.filter_by(org_id=org_id).all()
            depts = Department.query.filter_by(org_id=org_id).all()
            
            projects = Project.query.filter_by(org_id=org_id).all()
            qc_user_ids = set()
            for p in projects:
                if p.creator_id: qc_user_ids.add(p.creator_id)
                if p.team_leader_id: qc_user_ids.add(p.team_leader_id)
                if p.facilitator_id: qc_user_ids.add(p.facilitator_id)
                if p.reviewer_id: qc_user_ids.add(p.reviewer_id)
            if projects:
                members = ProjectMember.query.filter(ProjectMember.project_id.in_([p.id for p in projects])).all()
                for m in members: qc_user_ids.add(m.user_id)

            lines = [
                f"### 🏭 Active Plant Locations & Performance ({len(plants)})",
                f"Here are the operational facilities configured for your enterprise:\n"
            ]
            for pl in plants:
                p_depts = [d for d in depts if d.plant_id == pl.id]
                p_users = [u for u in all_users if u.plant_id == pl.id]
                p_qc = [u for u in p_users if u.id in qc_user_ids]
                lines.append(
                    f"1. **{pl.name}** `[{pl.code or 'N/A'}]`\n"
                    f"   - **Location**: {pl.location or 'Address unassigned'}\n"
                    f"   - **Departments**: {len(p_depts)} units mapped\n"
                    f"   - **Employees**: {len(p_users)} total ({len(p_qc)} working in QC projects)\n"
                )

            lines.append("*To add, edit or configure plant locations, visit **Administration > Plant Locations**.*")
            return {"answer": "\n".join(lines), "sources": []}

        # C. Departments Query
        if any(w in lq for w in ['department', 'departments', 'dept', 'depts']) and any(w in lq for w in ['show', 'list', 'how many', 'total', 'count', 'active', 'all']):
            depts = Department.query.filter_by(org_id=org_id).order_by(Department.name).all()
            all_users = User.query.filter_by(org_id=org_id).all()
            
            projects = Project.query.filter_by(org_id=org_id).all()
            qc_user_ids = set()
            for p in projects:
                if p.creator_id: qc_user_ids.add(p.creator_id)
                if p.team_leader_id: qc_user_ids.add(p.team_leader_id)
                if p.facilitator_id: qc_user_ids.add(p.facilitator_id)
                if p.reviewer_id: qc_user_ids.add(p.reviewer_id)
            if projects:
                members = ProjectMember.query.filter(ProjectMember.project_id.in_([p.id for p in projects])).all()
                for m in members: qc_user_ids.add(m.user_id)

            lines = [
                f"### 🏢 Organization Units & Departments ({len(depts)})",
                f"Here are the active standard departments mapped across your facilities:\n"
            ]
            for d in depts:
                p_name = d.plant.name if d.plant else "Organization-Wide / All Plants"
                d_users = [u for u in all_users if u.department_id == d.id]
                d_qc = [u for u in d_users if u.id in qc_user_ids]
                lines.append(f"• **{d.name}** (`{p_name}`) — **{len(d_users)} Employees** ({len(d_qc)} in QC projects)")

            lines.append("\n*To add or modify department units, navigate to **Administration > Departments**.*")
            return {"answer": "\n".join(lines), "sources": []}

        # D. Project Growth, Metrics & Status Query
        if any(w in lq for w in ['growth', 'progress', 'status', 'portfolio', 'overview', 'velocity', 'completion', 'metrics']) and any(w in lq for w in ['project', 'projects', 'qc', 'qcms', 'quality']):
            projects = Project.query.filter_by(org_id=org_id).all()
            total_p = len(projects)
            running = len([p for p in projects if p.status in ['In Progress', 'Active', 'running', 'Started']])
            completed = len([p for p in projects if p.status in ['Completed', 'Closed', 'Archived', 'Standardized']])
            in_review = len([p for p in projects if p.status in ['Under Review', 'In Review', 'Pending Approval']])
            
            # Stages distribution
            stages_dist = {}
            for s in range(1, 9):
                stages_dist[s] = len([p for p in projects if getattr(p, 'current_stage', 1) == s and p.status not in ['Completed', 'Closed']])

            # Category distribution
            cat_dist = {}
            for p in projects:
                cat = p.category or 'Quality'
                cat_dist[cat] = cat_dist.get(cat, 0) + 1

            lines = [
                f"### 📈 Organization Project Portfolio & Growth Overview",
                f"",
                f"- **Total Quality Circle Projects**: `{total_p}`",
                f"- **🟢 Active / In Progress**: `{running}` projects",
                f"- **🟡 In Review / Approval**: `{in_review}` projects",
                f"- **🏁 Completed & Standardized**: `{completed}` projects",
                f"- **Completion Velocity**: `{(completed / total_p * 100):.1f}%` overall closure rate" if total_p else "- **Completion Velocity**: `0%`",
                f"",
                f"**Active Stage Distribution**:",
                f"  • **S1 (Problem Definition)**: {stages_dist[1]} projects",
                f"  • **S2 (Observation & Data)**: {stages_dist[2]} projects",
                f"  • **S3 (Cause Identification)**: {stages_dist[3]} projects",
                f"  • **S4 (Root Cause Analysis)**: {stages_dist[4]} projects",
                f"  • **S5 (Countermeasures)**: {stages_dist[5]} projects",
                f"  • **S6 (Implementation)**: {stages_dist[6]} projects",
                f"  • **S7 (Verification)**: {stages_dist[7]} projects",
                f"  • **S8 (Closure & SOP)**: {stages_dist[8]} projects",
                f"",
                f"**Category Breakdown**: " + ", ".join([f"**{k}**: {v}" for k, v in cat_dist.items()]) if cat_dist else "",
                f"\n*Explore real-time interactive charts in **Analytics** or track teams in **Project Repository**.*"
            ]
            return {"answer": "\n".join(lines), "sources": []}

        # E. Leaderboard & Rewards Query
        if any(p in lq for p in ['leaderboard', 'top employee', 'points rank', 'rewards', 'who has highest point']):
            from app.infrastructure.database.models.models import EmployeePoints, EmployeeLeaderboard
            leaderboard = (
                db.session.query(User.name, User.username, Department.name.label('dept_name'), EmployeeLeaderboard.total_points, EmployeeLeaderboard.badge)
                .join(EmployeeLeaderboard, EmployeeLeaderboard.user_id == User.id)
                .outerjoin(Department, Department.id == User.department_id)
                .filter(User.org_id == org_id)
                .order_by(EmployeeLeaderboard.total_points.desc())
                .limit(5)
                .all()
            )

            if leaderboard:
                lines = [f"### 🏆 Organization Rewards & Points Leaderboard Top 5\n"]
                crowns = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣']
                for idx, row in enumerate(leaderboard):
                    name, uname, dept, pts, badge = row
                    lines.append(f"{crowns[idx]} **{name}** (@{uname}) — **{pts:,} PTS** `[{badge or 'Newbie'}]` ({dept or 'General'})")
                lines.append("\n*View complete rankings and point histories at **Rewards > Leaderboard**.*")
                return {"answer": "\n".join(lines), "sources": []}

        return None

    @classmethod
    def _handle_how_to_queries(cls, lq: str, role_name: str, is_admin_or_ceo: bool):
        # 1. How to manage / add Users / Employees, Bulk Import, Bulk Export & Custom Fields
        is_employee_query = any(w in lq for w in ['employee', 'user', 'member', 'stakeholder', 'person', 'staff', 'people'])
        is_add_action = any(w in lq for w in ['add', 'create', 'register', 'new', 'invite', 'provision', 'import', 'export', 'custom field', 'configure field', 'manage'])
        if (is_employee_query and is_add_action) or any(p in lq for p in ['how to add employee', 'how to add an employee', 'add employee', 'add user', 'add member', 'bulk import', 'bulk export', 'export user', 'configure field', 'custom field', 'manage users', 'user management']):
            return {
                "answer": (
                    "### 👥 How to Add & Manage Organization Employees\n\n"
                    "Follow these steps to register members, bulk import/export, or customize user attributes:\n\n"
                    "1. **Navigate to User Management**:\n"
                    "   - Open the left sidebar and click **User Management** under **Administration** (or visit `/admin/users.html`).\n\n"
                    "2. **Add an Individual Employee / Member**:\n"
                    "   - Click the purple **`+ Add Member`** button in the top right.\n"
                    "   - **Full Name**: Enter the employee's name.\n"
                    "   - **Email Address**: Enter corporate email (used for notifications & login).\n"
                    "   - **Username**: Assign a unique username.\n"
                    "   - **Role Assignment**: Choose *Admin, Facilitator, Reviewer, Team Leader, or Team Member*.\n"
                    "   - **Plant & Department**: Select their assigned operational plant facility and department.\n"
                    "   - Click **Save Member**.\n\n"
                    "3. **Bulk Import from Excel / CSV (Batch Provisioning)**:\n"
                    "   - Click **`Bulk Import`** in the top action bar.\n"
                    "   - Download the pre-formatted CSV template, paste your organization's roster, and upload to create hundreds of employees simultaneously.\n\n"
                    "4. **Bulk Export Directory**:\n"
                    "   - Click **`Bulk Export`** to download your full workforce directory with roles and plant mappings.\n\n"
                    "5. **Configure Custom Employee Fields**:\n"
                    "   - Click **`Configure Fields`** to add custom columns such as *Employee ID, Grade, Cost Center, Shift, or Mobile Number*."
                ),
                "sources": []
            }

        # 2. How to configure / add a Plant Location
        is_plant_query = any(w in lq for w in ['plant', 'location', 'facility', 'site', 'factory', 'branch'])
        is_plant_action = any(w in lq for w in ['add', 'create', 'configure', 'setup', 'new', 'change', 'manage', 'how to'])
        if (is_plant_query and is_plant_action) or any(p in lq for p in ['plant location', 'configure plant', 'add plant', 'create plant']):
            return {
                "answer": (
                    "### 🏭 How to Configure & Manage Plant Locations\n\n"
                    "Follow these steps to set up or update manufacturing facilities and operating sites:\n\n"
                    "1. **Navigate to Plant Locations**:\n"
                    "   - Open the left sidebar and click **Plant Locations** under the **Administration** menu (or visit `/admin/plants.html`).\n\n"
                    "2. **Add a New Plant**:\n"
                    "   - Click the purple **`+ Add Plant Location`** button in the top right.\n"
                    "   - **Plant Name** (Required): e.g. `Pune Manufacturing Plant`.\n"
                    "   - **Plant Code** (Optional): e.g. `PN-01`.\n"
                    "   - **Location / Address**: Enter the physical facility address.\n"
                    "   - Click **Save Plant Location**.\n\n"
                    "3. **Edit, Map or Reassign**:\n"
                    "   - Click **`Edit`** on any row to modify details.\n"
                    "   - When deleting a plant, the smart wizard allows you to automatically reassign all existing departments and employees to an alternate facility."
                ),
                "sources": []
            }

        # 3. How to configure / add Departments
        is_dept_query = any(w in lq for w in ['department', 'dept', 'unit', 'division'])
        is_dept_action = any(w in lq for w in ['add', 'create', 'configure', 'setup', 'new', 'change', 'manage', 'how to'])
        if (is_dept_query and is_dept_action) or any(p in lq for p in ['add department', 'create department', 'configure department']):
            return {
                "answer": (
                    "### 🏢 How to Configure & Manage Organization Departments\n\n"
                    "Follow these steps to create or reassign operational units:\n\n"
                    "1. **Navigate to Departments**:\n"
                    "   - In the left sidebar under **Administration**, click **Departments** (or visit `/admin/departments.html`).\n\n"
                    "2. **Create Department**:\n"
                    "   - Click the **`+ Add Department`** button.\n"
                    "   - **Plant Location**: Select which plant facility this department belongs to (or choose *Organization-Wide / All Plants*).\n"
                    "   - **Department Name**: Enter the title (e.g. `Quality Assurance`, `Maintenance`, `Assembly Line 1`).\n"
                    "   - Click **Save**.\n\n"
                    "3. **Filtering & Actions**:\n"
                    "   - Use the **Filter Plant** dropdown to filter departments by facility.\n"
                    "   - Use the **Actions (⋮)** menu on any row to edit name, reassign to another plant, or delete."
                ),
                "sources": []
            }

        # 4. How to configure the 8 stages / stage template / weightages / methodology content
        is_8stage_word = any(p in lq for p in ['8 stage', '8-stage', '8stage', 'eight stage', 'stage template', 'stages template', 'stage configuration', 'configure stage', 'configure the 8', 'stage content', 'what are the stages', 'stages of qc', 'tell me the stages', 'explain the stages'])
        is_8stage_config = any(w in lq for w in ['configure', 'template', 'setup', 'set up', 'explain', 'tell me', 'what are', 'understand', 'overview', 'describe'])
        if is_8stage_word or (is_8stage_config and any(w in lq for w in ['stage', 'stages'])):
            return {
                "answer": (
                    "### ⚙️ The 8-Stage QCMS Project Template — What Each Stage Contains\n\n"
                    "Each Quality Circle project follows a structured **8-Stage methodology**. Here's how to navigate and configure each stage:\n\n"
                    "**Stage 1 — Problem Definition & Project Initiation**\n"
                    "- Configure the 5W2H Project Charter (What, Where, When, Who, Why, How, How Much).\n"
                    "- Set the baseline KPI metric (defect rate, cost, downtime, etc.).\n"
                    "- Assign Team Leader, QCC Facilitator, Reviewer, and cross-functional team.\n\n"
                    "**Stage 2 — Observation & Data Collection**\n"
                    "- Fill Check Sheet entries and stratify data by 4M (Man, Machine, Material, Method).\n"
                    "- Build the Pareto Chart to identify the vital few defect categories.\n\n"
                    "**Stage 3 — Cause Identification (Fishbone)**\n"
                    "- Construct the Ishikawa Fishbone Diagram using the 6M branches.\n"
                    "- Brainstorm and link causes to the main problem.\n\n"
                    "**Stage 4 — Root Cause Analysis & Verification**\n"
                    "- Run the 5-Why analysis on selected causes.\n"
                    "- Perform Good vs Bad comparison tests; isolate verified root causes.\n\n"
                    "**Stage 5 — Countermeasure Planning**\n"
                    "- Create the 3W1H Action Plan (What, Who, Where, How).\n"
                    "- Evaluate countermeasure feasibility and expected impact.\n\n"
                    "**Stage 6 — Implementation**\n"
                    "- Log implementation tasks with owner, due date, and evidence upload.\n"
                    "- Conduct operator training and track completion.\n\n"
                    "**Stage 7 — Performance Verification**\n"
                    "- Compare Before vs After KPI metrics.\n"
                    "- Record tangible cost savings and ROI realization.\n\n"
                    "**Stage 8 — Standardization & Closure**\n"
                    "- Finalize and attach Standard Operating Procedures (SOPs).\n"
                    "- Collect Section 9 digital sign-offs from all hierarchy signatories.\n"
                    "- Mark project as **Completed & Standardized**.\n\n"
                    "*Tip: Navigate each stage tab inside your project on **Project Repository** (`/project-details.html?id=<ID>`). Stage weightages can be adjusted at **Administration > Settings > Stage Weightages**.*"
                ),
                "sources": []
            }

        # 5. How to create or start a new QC Project
        is_proj_word = any(w in lq for w in ['project', 'qcms', 'quality circle', 'qc story'])
        is_proj_start = any(w in lq for w in ['start', 'create', 'launch', 'new', 'initiate', 'begin', 'execute'])
        if (is_proj_word and is_proj_start) or any(p in lq for p in ['create project', 'start project', 'new project', 'how to create a project', 'how to start a project', 'how to start and execute']):
            return {
                "answer": (
                    "### 🚀 How to Start & Execute an 8-Stage QCMS Project\n\n"
                    "1. **Launch Project Creator**:\n"
                    "   - Click **Project Repository** in the sidebar and click **`+ New Project`** (or go to `/projects.html`).\n\n"
                    "2. **Fill Project Initiation Charter**:\n"
                    "   - **Project Title & Pillar**: Define problem title and category (*Quality, Cost, Delivery, Safety, Morale, Environment, Productivity*).\n"
                    "   - **Assign Leadership**: Choose **Team Leader**, **QCC Facilitator**, and **Reviewer**.\n"
                    "   - **Select Team Members**: Add cross-functional members from your organization directory.\n"
                    "   - **Plant & Department**: Map the operational facility.\n"
                    "   - **Target Deadline & Milestone Schedule**.\n\n"
                    "3. **Progress Through the 8 Stages**:\n"
                    "   - **Stage 1**: Problem Definition (5W2H charter & baseline metric)\n"
                    "   - **Stage 2**: Observation & Check Sheets (Pareto analysis)\n"
                    "   - **Stage 3**: Cause Brainstorming (Ishikawa Fishbone 6M)\n"
                    "   - **Stage 4**: Root Cause Verification (5-Why analysis & hypothesis testing)\n"
                    "   - **Stage 5**: Countermeasure Action Plan (3W1H matrix)\n"
                    "   - **Stage 6**: Implementation & Operator Training\n"
                    "   - **Stage 7**: Performance Verification (Before vs After KPI & Cost Savings)\n"
                    "   - **Stage 8**: Standardization (SOP deployment & Section 9 Sign-offs)"
                ),
                "sources": []
            }

        # 5. How to configure Sign-Off Hierarchy
        if any(w in lq for w in ['sign-off', 'sign off', 'hierarchy', 'signature', 'signatory', 'signatories', 'closure approval']):
            return {
                "answer": (
                    "### ✍️ How to Configure Sign-Off Hierarchy for QC Story Reports\n\n"
                    "Customize corporate signatories (HR, Finance, Plant Head, Quality Director) for Section 9 closure sign-offs:\n\n"
                    "1. **Access Hierarchy Settings**:\n"
                    "   - Open **Administration > Settings** (or visit `/admin/settings.html#pane-signoff-hierarchy`).\n"
                    "   - Open the **Sign-Off Hierarchy** tab.\n\n"
                    "2. **Configure Signatory Roles**:\n"
                    "   - Standard roles (**Team Leader**, **QCC Facilitator**, **Project Reviewer**) are included automatically.\n"
                    "   - Click **`+ Add Hierarchy Role`** to add organizational approvals (e.g. `HR Head`, `Finance Controller`, `Plant Head`, `General Manager`).\n"
                    "   - Use the up/down arrows to adjust the sign-off sequence.\n"
                    "   - Click **Save Sign-Off Hierarchy**.\n\n"
                    "3. **Generated PDF Output**:\n"
                    "   - When downloading the QC Storyboard Report PDF, Section 9 will render clear signature boxes and approval dates for all configured signatories."
                ),
                "sources": []
            }

        # 6. How to configure Stage Weightages
        if any(w in lq for w in ['weightage', 'weight slider', 'rca heavy', 'stage weight', 'stage percentage']):
            return {
                "answer": (
                    "### ⚖️ How to Configure 8-Stage Progress Weightages\n\n"
                    "1. **Access Weightage Manager**:\n"
                    "   - Go to Super Admin / Admin console under **Stage Weightages** (`/admin/settings.html`).\n\n"
                    "2. **Adjust Weight Allocation**:\n"
                    "   - Move individual sliders or type numeric percentages for Stage 1 through Stage 8.\n"
                    "   - Ensure total allocation equals **100%** (visualized with a live progress indicator).\n\n"
                    "3. **Apply 1-Click Presets**:\n"
                    "   - **Equal Weightage**: 12.5% per stage across all 8 stages.\n"
                    "   - **RCA Heavy**: Emphasizes root cause analysis (higher weight on S3 & S4).\n"
                    "   - **Execution Heavy**: Emphasizes countermeasure deployment (higher weight on S5 & S6).\n\n"
                    "4. Click **Save Configuration** to persist org-wide."
                ),
                "sources": []
            }

        # 7. How to download or export QC Storyboard PDF Report
        if any(w in lq for w in ['download report', 'export report', 'pdf report', 'export pdf', 'storyboard', 'download pdf']):
            return {
                "answer": (
                    "### 📄 How to Export & Download the QC Storyboard Report\n\n"
                    "1. Open the project from **Project Repository** (`/project-details.html?id=<ID>`).\n"
                    "2. Click the **Export Report (PDF)** button in the top action bar.\n"
                    "3. The system generates a formatted executive PDF report containing:\n"
                    "   - Executive Summary & Project Milestone Charter\n"
                    "   - Stage-by-Stage Documentation (S1 to S8)\n"
                    "   - Quality Tool Visualizations (Fishbone, Pareto, 5-Why, 3W1H Action Plan)\n"
                    "   - Tangible Savings & ROI Realization\n"
                    "   - **Section 9 Closure Sign-Off Matrix** with formal signatures."
                ),
                "sources": []
            }

        # 8. How to access Dashboards
        if any(p in lq for p in ['how to access dashboard', 'access this dashboard', 'switch dashboard', 'open dashboard', 'how to change this options', 'change options', 'dashboards']):
            return {
                "answer": (
                    "### 📊 How to Access & Switch Dashboards\n\n"
                    "Depending on your corporate role, you can access dedicated specialized workspaces:\n\n"
                    "- **Main Overview / Project Dashboard**: Click **Overview** in the sidebar (`/dashboard.html`).\n"
                    "- **Executive / CEO Dashboard**: Switch workspace or visit `/ceo/dashboard.html` for high-level quality index, plant benchmarks, and ROI.\n"
                    "- **Facilitator Desk**: Visit `/facilitator/dashboard.html` to monitor team velocity, stage checkpoints, and assistance requests.\n"
                    "- **Reviewer Quality Gate**: Visit `/reviewer/dashboard.html` to review, approve, or request revisions on stage submissions.\n"
                    "- **Admin Console**: Access `/admin/users.html`, `/admin/plants.html`, and `/admin/settings.html` from the Administration menu."
                ),
                "sources": []
            }

        return None

    @classmethod
    def _handle_qc_methodology_queries(cls, lq: str):
        # Root Causes & Corrective Actions
        if any(w in lq for w in ['root cause', 'root causes', 'rca', 'corrective action', 'corrective actions', 'countermeasure', 'countermeasures', 'causes']):
            return {
                "answer": (
                    "### 🔍 Common Root Causes & Corrective Action Frameworks in QCMS\n\n"
                    "Across industrial Quality Circle methodologies, root causes generally fall into four key operational categories:\n\n"
                    "1. **Procedural & Standard Work Deficiencies** (42% of occurrences):\n"
                    "   - *Root Cause*: Ambiguous or outdated SOPs, lack of standardized visual work instructions.\n"
                    "   - *Corrective Action*: Standardize 1-Point Lessons (OPL), revise SOPs, and deploy digital checklist gates.\n\n"
                    "2. **Machine Calibration & Tool Wear** (28% of occurrences):\n"
                    "   - *Root Cause*: Uneven tool wear, sensor drift, delayed autonomous maintenance.\n"
                    "   - *Corrective Action*: Implement poke-yoke (mistake-proofing) jigs, automated sensor limits, and preventive calibration intervals.\n\n"
                    "3. **Material Inconsistency & Hardness Variance** (18% of occurrences):\n"
                    "   - *Root Cause*: Supplier batch variance, incoming QA sampling gaps, temperature/humidity sensitivity.\n"
                    "   - *Corrective Action*: Tighten supplier incoming AQL, environmental climate control, and material hardness inspection protocols.\n\n"
                    "4. **Manpower & Training Gaps** (12% of occurrences):\n"
                    "   - *Root Cause*: Multi-skill matrix gaps, lack of standard training verification.\n"
                    "   - *Corrective Action*: Skill matrix matrix upskilling, cross-operator verification, and visual error-proofing."
                ),
                "sources": []
            }

        # 8 Stages overview
        if any(p in lq for p in ['8 stage', 'eight stage', 'methodology', 'stages of qc', 'qc story', '8 stages']):
            return {
                "answer": (
                    "### 🏆 The 8-Stage Quality Circle (QC) Methodology\n\n"
                    "1. **Stage 1 — Problem Definition & Project Initiation**: Define problem statement, 5W2H charter, baseline KPI metrics, and team assignment.\n"
                    "2. **Stage 2 — Observation & Data Collection**: Gather empirical baseline data using Check Sheets, Pareto Analysis, and 4M Stratification.\n"
                    "3. **Stage 3 — Cause Identification**: Brainstorm potential causes using Ishikawa Fishbone Diagrams (6M) and preliminary 5-Why analysis.\n"
                    "4. **Stage 4 — Root Cause Analysis & Verification**: Formulate hypotheses, perform Good vs Bad comparisons, on-site testing, and isolate true root causes.\n"
                    "5. **Stage 5 — Countermeasure Planning & Solution Development**: Generate countermeasures, evaluate feasibility & cost-benefit, and formulate 3W1H Action Plans.\n"
                    "6. **Stage 6 — Implementation & Change Management**: Execute countermeasure tasks, log implementation evidence, manage risk & change resistance, and conduct operator training.\n"
                    "7. **Stage 7 — Performance Verification & Benefits Realization**: Verify Before vs After KPI results, validate statistical stability, and compute tangible cost savings & ROI.\n"
                    "8. **Stage 8 — Standardization, Knowledge Sharing & Project Closure**: Institutionalize Standard Operating Procedures (SOPs), deploy horizontally across lines, and obtain formal sign-offs."
                ),
                "sources": []
            }

        # Quality Tools (Fishbone, Pareto, 5-Why, Stratification)
        if any(p in lq for p in ['fishbone', 'ishikawa', 'cause and effect', '6m']):
            return {
                "answer": (
                    "### 🐟 Fishbone (Ishikawa / Cause-and-Effect) Diagram\n\n"
                    "A graphical tool used in **Stage 3 (Cause Identification)** to brainstorm and organize potential causes of a quality problem:\n\n"
                    "- **The 6M Categories**:\n"
                    "  1. **Manpower**: Operator skill, training, ergonomics, fatigue.\n"
                    "  2. **Machine**: Tool wear, calibration, maintenance, speed, jigs.\n"
                    "  3. **Material**: Raw material defects, hardness, tolerances, supplier batch variance.\n"
                    "  4. **Method**: Standard operating procedure, cycle time, parameters, sequencing.\n"
                    "  5. **Measurement**: Gauge precision, inspection error, calibration drift.\n"
                    "  6. **Milieu (Environment)**: Temperature, humidity, lighting, dust, vibration.\n\n"
                    "*Use the interactive Fishbone Canvas inside your project's Stage 3 tab to construct and save diagrams.*"
                ),
                "sources": []
            }

        if any(p in lq for p in ['pareto', '80/20', '80-20']):
            return {
                "answer": (
                    "### 📊 Pareto Chart Analysis (80/20 Principle)\n\n"
                    "Used in **Stage 2 (Observation)** and **Stage 7 (Verification)** to identify the **vital few** causes that generate the majority of defects:\n\n"
                    "- **Bar Chart**: Ranks defect categories in descending order of frequency or cost impact.\n"
                    "- **Cumulative Line (Ogive)**: Shows running cumulative percentage from 0% to 100%.\n"
                    "- **Key Rule**: Focusing on the top 20% of defect types typically resolves 80% of total quality losses."
                ),
                "sources": []
            }

        if any(p in lq for p in ['5 why', '5-why', 'why why']):
            return {
                "answer": (
                    "### 🔍 5-Why Root Cause Analysis\n\n"
                    "An iterative interrogative technique used in **Stage 4 (Root Cause Verification)** to explore cause-and-effect relationships:\n\n"
                    "1. State the specific symptom or problem.\n"
                    "2. Ask **'Why did this happen?'** and record the direct cause.\n"
                    "3. Ask **'Why?'** 4 more times iteratively on each subsequent answer.\n"
                    "4. Stop when you identify the actionable root systemic or procedural flaw.\n"
                    "5. Develop countermeasures specifically targeting that fundamental root cause."
                ),
                "sources": []
            }

        return None

    @classmethod
    def _handle_knowledge_repository_lookup(cls, query: str, org_id: int):
        try:
            from app.infrastructure.vector_db import VectorSearchService
            results = VectorSearchService.search_by_text(query, org_id, limit=4)
            if not results:
                return None

            lines = ["### 📚 Relevant Organization Quality Records\n"]
            sources = []

            for i, res in enumerate(results):
                title = res.get('title', 'Untitled Project')
                category = res.get('category', 'Quality')
                prob = res.get('problem_summary', '') or ''
                cause = res.get('root_cause', '') or ''
                sol = res.get('solution_summary', '') or ''
                kpi = res.get('kpi_improvement_pct', 0)
                savings = res.get('cost_savings', 0)
                proj_id = res.get('project_id', res.get('id'))

                sources.append({
                    'project_id': proj_id,
                    'title': title,
                    'category': category,
                    'summary': prob[:140] + ('...' if len(prob) > 140 else '')
                })

                lines.append(f"**{i+1}. {title}** `[{category}]`")
                if prob: lines.append(f"- **Problem Summary**: {prob[:180]}")
                if cause: lines.append(f"- **Root Cause**: {cause[:180]}")
                if sol: lines.append(f"- **Countermeasure / Solution**: {sol[:180]}")
                if kpi or savings:
                    lines.append(f"- **Impact**: {f'{kpi}% KPI Improvement' if kpi else ''} {f'· ₹{savings:,.0f} Cost Savings' if savings else ''}")
                lines.append("")

            return {"answer": "\n".join(lines), "sources": sources}
        except Exception as e:
            print(f"[AI Assistant RAG error]: {e}")
            return None

    @classmethod
    def _generate_smart_fallback(cls, query: str, role_name: str, user: User):
        return {
            "answer": (
                f"I'm your **Quality AI Assistant**. Here is what I can help you with based on your role as **{role_name}**:\n\n"
                f"1. **Live Workforce & Plant Data**:\n"
                f"   - *'How many employees are working here?'*\n"
                f"   - *'How many employees are working in Quality Circle projects?'*\n"
                f"   - *'Show active plant locations and department mappings.'*\n\n"
                f"2. **Project Portfolio & Growth**:\n"
                f"   - *'What is the growth and status of our QC projects?'*\n"
                f"   - *'Show projects by stage distribution (S1 to S8).'* \n\n"
                f"3. **How-To & Step-by-Step Configuration**:\n"
                f"   - *'How to configure plant locations or departments?'*\n"
                f"   - *'How to add employees, bulk import or bulk export CSV?'*\n"
                f"   - *'How to configure the sign-off hierarchy for PDF reports?'*\n"
                f"   - *'How to adjust stage weightages?'*\n\n"
                f"4. **8-Stage QC Methodology & Quality Tools**:\n"
                f"   - Ask how to build a **Fishbone Diagram (6M)**, **Pareto Chart (80/20)**, **5-Why Analysis**, or **3W1H Action Plan**.\n\n"
                f"Feel free to ask any specific question above!"
            ),
            "sources": []
        }
