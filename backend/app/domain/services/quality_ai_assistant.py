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
    - Comprehensive 21-Case Super Admin Standard Operating Procedures (SOP) Library
    - Organization Admin Operational & Infrastructure Configuration Manual
    - 8-Stage QC Methodology & Quality Tools specialist (Fishbone 6M, Pareto 80/20, 5-Why, 3W1H)
    - Strict Role-Based Access Control (RBAC) & Dashboard Boundary enforcement
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
        role_lower = role_name.lower()
        clean_query = query.strip()
        lower_query = clean_query.lower()

        is_super_admin = (
            getattr(user, 'is_super_admin', False)
            or 'super' in role_lower
            or (getattr(user, 'org_id', None) == 1 and role_name in ['Super Admin', 'SuperAdmin'])
        )
        is_admin = is_super_admin or role_name in ['Admin', 'Administrator', 'Corporate Admin', 'Org Admin']
        is_ceo = any(w in role_lower for w in ['ceo', 'exec', 'director', 'managing'])

        # 1. RBAC Check: Restrict sensitive financial / admin data for lower-tier roles
        if not (is_admin or is_ceo):
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

        # 2. Super Admin 21 Use Cases Router (Evaluates Super Admin features & enforces role boundaries)
        sa_answer = cls._handle_super_admin_cases(lower_query, is_super_admin, role_name)
        if sa_answer:
            return sa_answer

        # 3. Dynamic Live Organization Data Query Router
        dynamic_answer = cls._handle_dynamic_org_queries(lower_query, clean_query, user, role_name, is_admin or is_ceo)
        if dynamic_answer:
            return dynamic_answer

        # 4. System How-To, Configuration & Navigation Manual Router (Checked for actionable instructions)
        how_to_answer = cls._handle_how_to_queries(lower_query, role_name, is_admin, is_super_admin)
        if how_to_answer:
            return how_to_answer

        # 5. 8-Stage QC Methodology & Quality Tools Knowledge Router
        qc_methodology_answer = cls._handle_qc_methodology_queries(lower_query)
        if qc_methodology_answer:
            return qc_methodology_answer

        # 6. Historical Knowledge Repository RAG Lookup (Archived Projects & Root Causes)
        rag_answer = cls._handle_knowledge_repository_lookup(clean_query, org_id)
        if rag_answer:
            return rag_answer

        # 7. Comprehensive Fallback Assistant Response
        return cls._generate_smart_fallback(clean_query, role_name, user, is_super_admin, is_admin)

    @classmethod
    def _handle_super_admin_cases(cls, lq: str, is_super_admin: bool, role_name: str):
        """
        Covers the 21 Super Administrator Standard Operating Procedures (SOPs).
        Enforces strict role boundary when non-super-admins ask about platform governance.
        """
        # Define the 21 Cases with intent matching
        cases_map = [
            # Case 1: Fetch/Modify Organization data
            {
                "keys": ['modify organisation', 'modify organization', 'fetch organisation', 'fetch organization', 'edit profile of org', 'reset password org', 'pause org', 'delete org', 'manage organization', 'organisation data', 'organization data', 'extend trail org'],
                "case_num": 1,
                "title": "To Fetch / Modify Organization Data",
                "steps": [
                    "Step 1: Go to **Organization** (`/admin/super-admin-orgs.html`) from the Super Admin sidebar.",
                    "Step 2: Click on **Action Button** (⋮) next to the target organization row.",
                    "Step 3: Click on **View Details / Edit Profile / Extend Trial / Reset Password / Pause / Delete Org** as required."
                ]
            },
            # Case 2: Download the Overall Organization
            {
                "keys": ['download overall organisation', 'download overall organization', 'export organization csv', 'export org csv', 'download all organizations', 'export organizations'],
                "case_num": 2,
                "title": "To Download Overall Organization Directory",
                "steps": [
                    "Step 1: Go to **Organization** (`/admin/super-admin-orgs.html`).",
                    "Step 2: Click on **Export CSV Button** in the top action toolbar."
                ]
            },
            # Case 3: Create New Plan
            {
                "keys": ['create new plan', 'create plan', 'add plan', 'new plan button', 'create subscription plan'],
                "case_num": 3,
                "title": "To Create New Subscription Plan",
                "steps": [
                    "Step 1: Go to **Plans** (`/admin/super-admin-plans.html`).",
                    "Step 2: Click on **New Plan Button**.",
                    "Step 3: Enter the plan Details (Plan Name, Pricing, User Quota, Plant Limit, Storage).",
                    "Step 4: Click **Next** and click the **Save** button."
                ]
            },
            # Case 4: Dispatch All Pay As You Go
            {
                "keys": ['pay as you go', 'dispatch bills', 'metered rules', 'generate & send invoices', 'generate and send invoices', 'dispatch all the pay as you go'],
                "case_num": 4,
                "title": "To Dispatch All Pay-As-You-Go Metered Bills",
                "steps": [
                    "Step 1: Go to **Plans** (`/admin/super-admin-plans.html`).",
                    "Step 2: Click on **Pay As You Go** tab.",
                    "Step 3: Click on **Set the Metered Rules** button to define per-unit rates.",
                    "Step 4: Click **Dispatch Bills Button**.",
                    "Step 5: Click on **Generate & Send Invoices** to dispatch metered invoices."
                ]
            },
            # Case 5: View/Edit the plan
            {
                "keys": ['view the plan', 'edit the plan', 'modify plan', 'view plan', 'edit plan'],
                "case_num": 5,
                "title": "To View / Edit Existing Subscription Plan",
                "steps": [
                    "Step 1: Go to **Plans** (`/admin/super-admin-plans.html`).",
                    "Step 2: Click on **Action Button** on the target plan tier.",
                    "Step 3: To view click on **View**.",
                    "Step 4: To edit click on **Edit**."
                ]
            },
            # Case 6: Extend Trial
            {
                "keys": ['extend trail', 'extend trial', 'extend organization trial', 'grant trial days'],
                "case_num": 6,
                "title": "To Extend Organization Trial",
                "steps": [
                    "Step 1: Go to **Support Tickets** (`/admin/super-admin-tickets.html`).",
                    "Step 2: Under Action, Click on **Extend Trial Button**."
                ]
            },
            # Case 7: Create Ticket
            {
                "keys": ['create ticket', 'new support ticket', 'open ticket', 'create support ticket'],
                "case_num": 7,
                "title": "To Create Support Ticket",
                "steps": [
                    "Step 1: Go to **Support Tickets** (`/admin/super-admin-tickets.html`).",
                    "Step 2: Click on **Create Ticket**.",
                    "Step 3: Enter the details (Target Org, Category, Priority, Subject).",
                    "Step 4: Review the content.",
                    "Step 5: Click on **Create Ticket**."
                ]
            },
            # Case 8: Define New SMS/Email Template
            {
                "keys": ['define new sms', 'define new email template', 'set sms/email notification', 'set sms email notification', 'save notification rule', 'sms template config', 'email notification rule'],
                "case_num": 8,
                "title": "To Define New SMS / Email Notification Template",
                "steps": [
                    "Step 1: Go to **Announcements** (`/admin/super-admin-announcements.html`).",
                    "Step 2: Click on **Set SMS / Email Notification**.",
                    "Step 3: Click on **Set SMS / Email Notification Button**.",
                    "Step 4: Define New Rule (Event Trigger, DLT Template ID, PE ID, Sender ID, Email/SMS Body).",
                    "Step 5: Click on **Save Notification Rule Button**."
                ]
            },
            # Case 9: Create New Announcement
            {
                "keys": ['create new announcement', 'compose broadcast', 'publish announcement', 'send announcement', 'broadcast announcement'],
                "case_num": 9,
                "title": "To Create New Announcement Broadcast",
                "steps": [
                    "Step 1: Go to **Announcements** (`/admin/super-admin-announcements.html`).",
                    "Step 2: Click on **Compose Broadcast**.",
                    "Step 3: Enter the details (Title, Message, Category).",
                    "Step 4: Select the Target Audience (All Organizations, Specific Tenants, Admins).",
                    "Step 5: Click on **Send**."
                ]
            },
            # Case 10: View Billing Details
            {
                "keys": ['view the billing details', 'view billing details', 'view invoice details', 'super admin billing', 'payment receipt details'],
                "case_num": 10,
                "title": "To View Organization Billing Details & Invoices",
                "steps": [
                    "Step 1: Go to **Billings** (`/admin/super-admin-billing.html`).",
                    "Step 2: Click on **Action Button** (⋮) on the invoice record.",
                    "Step 3: Click on **View Details**."
                ]
            },
            # Case 11: Delete / Purge Audit Logs
            {
                "keys": ['delete the audit logs', 'delete audit logs', 'purge audit logs', 'purge logs', 'clean audit trail'],
                "case_num": 11,
                "title": "To Delete / Purge Security Audit Logs",
                "steps": [
                    "Step 1: Go to **Audit Logs** (`/admin/super-admin-audit-logs.html`).",
                    "Step 2: Click on **Purge Audit Logs**.",
                    "Step 3: Select the option from the Dropdown (Older than 30/90 days, All Logs).",
                    "Step 4: Click on **Confirm & Purge Logs**."
                ]
            },
            # Case 12: Update Platform & Company Details
            {
                "keys": ['update the platform & company details', 'update platform details', 'doc identity & branding', 'doc identity', 'save platform identity', 'watermark settings'],
                "case_num": 12,
                "title": "To Update Platform & Company Identity Details",
                "steps": [
                    "Step 1: Go to **Doc Identity & Branding** (`/admin/super-admin-doc-identity.html`).",
                    "Step 2: Enter the details (Software Name, Support Email, Watermarks, Headers).",
                    "Step 3: Click on **Save Platform Identity Button**."
                ]
            },
            # Case 13: View Storage Used by Individual Organization
            {
                "keys": ['view storage used by individual organization', 'adjust storage limit', 'storage analytics', 'organization storage limit', 'tenant storage'],
                "case_num": 13,
                "title": "To View & Adjust Storage Used by Individual Organization",
                "steps": [
                    "Step 1: Click on **Storage Analytics** (`/admin/super-admin-storage-analytics.html`).",
                    "Step 2: Click on **Details Button** next to the target organization.",
                    "Step 3: Click on **Adjust Storage Limit**.",
                    "Step 4: Set new Limit (in GB).",
                    "Step 5: Click on **Save Button**."
                ]
            },
            # Case 14: Update Global 8 Stage Template
            {
                "keys": ['update global 8 stage template', 'global stage template', 'add new stage', 'add columns under the any stages', 'save templates button', 'reset to default button'],
                "case_num": 14,
                "title": "To Update Global 8-Stage Master Template",
                "steps": [
                    "Step 1: Go to **Global Stage Template** (`/admin/super-admin-stage-template.html`).",
                    "Step 2: Click on **Add New Stage Button** to add new Stage.",
                    "Step 3: To add New Columns in existing Stages, click on **Add Columns** under any stage.",
                    "Step 4: Click on **Save Templates Button**.",
                    "Step 5: To keep default template settings, click on **Reset to Default Button**."
                ]
            },
            # Case 15: Delete Organization Permanently
            {
                "keys": ['delete the organization permanently', 'delete org permanently', 'empty recycle bin', 'permanently delete organization'],
                "case_num": 15,
                "title": "To Delete Organization Permanently",
                "steps": [
                    "Step 1: Go to **Recycle Bin** (`/admin/super-admin-recycle-bin.html`).",
                    "Step 2: Click on the **Empty Recycle Bin Button**.",
                    "Step 3: Click **OK**."
                ]
            },
            # Case 16: Recover Organization from Recycle Bin
            {
                "keys": ['recover the organization from recycle bin', 'recover organization', 'recover org from recycle bin', 'restore organization'],
                "case_num": 16,
                "title": "To Recover Organization from Recycle Bin",
                "steps": [
                    "Step 1: Go to **Recycle Bin** (`/admin/super-admin-recycle-bin.html`).",
                    "Step 2: Click on **Recover Button** next to the soft-deleted organization.",
                    "Step 3: Click **OK**."
                ]
            },
            # Case 17: General Settings (Self-Service, Email OTP, Phone OTP, Maintenance)
            {
                "keys": ['self-service sign-up', 'self service sign up', 'email otp verification', 'phone otp verification', 'maintenance mode', 'general settings', 'all four options are available'],
                "case_num": 17,
                "title": "To Configure General Platform Settings (Self-Service, Email OTP, Phone OTP, Maintenance)",
                "steps": [
                    "Step 1: Go to **Settings** (`/admin/super-admin-settings.html`).",
                    "Step 2: Under **General**, all four options are available (*Self-Service Sign-up, Email OTP Verification, Phone OTP Verification, Maintenance Mode*).",
                    "Step 3: Turn On / Off the Button switches.",
                    "Step 4: Click on **Save**."
                ]
            },
            # Case 18: Upload Logo & Branding
            {
                "keys": ['upload the logo', 'upload logo', 'upload dark logo', 'upload favicon', 'upload background graphic', 'upload splash image', 'save branding button'],
                "case_num": 18,
                "title": "To Upload Platform Logos & Branding Assets",
                "steps": [
                    "Step 1: Go to **Settings** (`/admin/super-admin-settings.html`).",
                    "Step 2: Under **Branding**, upload Logo, Dark Logo, Favicon, Background Graphic, and Splash Image.",
                    "Step 3: Click on **Save Branding Button**."
                ]
            },
            # Case 19: Update Super Admin Password
            {
                "keys": ['update super admin password', 'change super admin password', 'super admin logins enter new password', 'update my credentials button'],
                "case_num": 19,
                "title": "To Update Super Admin Password",
                "steps": [
                    "Step 1: Go to **Settings** (`/admin/super-admin-settings.html`).",
                    "Step 2: Under **Super Admin Logins**, enter New Password.",
                    "Step 3: Click on **Update My Credentials Button**."
                ]
            },
            # Case 20: Add New Super Admin
            {
                "keys": ['add new super admin', 'add super admin', 'create super admin account', 'create super admin account button'],
                "case_num": 20,
                "title": "To Add New Super Admin Account",
                "steps": [
                    "Step 1: Go to **Settings** (`/admin/super-admin-settings.html`).",
                    "Step 2: Under **Super Admin Logins**, click on **Add Super Admin**.",
                    "Step 3: Enter the details (Name, Email, Username, Password).",
                    "Step 4: Click on **Create Super Admin Account Button**."
                ]
            },
            # Case 21: Modify Landing Page
            {
                "keys": ['modify landing page', 'landing cms', 'publish landing page', 'use default template button', 'edit landing page'],
                "case_num": 21,
                "title": "To Modify Platform Landing Page",
                "steps": [
                    "Step 1: Go to **Settings** (`/admin/super-admin-settings.html`).",
                    "Step 2: Under **Landing CMS**, enter the details (Hero Headline, Subtitle, Features, CTA labels).",
                    "Step 3: Click on **Publish Landing Page / Use Default Template Button**."
                ]
            }
        ]

        # Check for matching case
        for c in cases_map:
            if any(k in lq for k in c['keys']):
                # Role boundary enforcement
                if not is_super_admin:
                    return {
                        "answer": (
                            f"🔒 **Administrative Role Notice**\n\n"
                            f"The procedure **'{c['title']}'** is a **Super Administrator** feature and is managed inside the Super Admin Console (`/admin/super-admin.html`).\n\n"
                            f"As a **{role_name}**, your dashboard provides access to:\n"
                            f"- Quality Circle project workflows & stage progress (Stages 1 to 8)\n"
                            f"- Quality problem-solving tools (Fishbone 6M, Pareto 80/20, 5-Why Analysis)\n"
                            f"- Task assignments, idea submissions, and reward leaderboard rankings.\n\n"
                            f"If you need changes to platform subscriptions, global templates, or tenant settings, please contact your Super Administrator."
                        ),
                        "sources": []
                    }

                # If Super Admin, return the exact step-by-step SOP
                lines = [
                    f"### 🛡️ Super Admin SOP — Case {c['case_num']}: {c['title']}\n",
                    "Follow these standard operating steps:\n"
                ]
                for step in c['steps']:
                    lines.append(f"- {step}")
                lines.append("\n*Tip: All Super Admin procedures can also be viewed in the [Super Admin User Manual](/resources/user-manual.html).*")
                return {"answer": "\n".join(lines), "sources": []}

        return None

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
            from app.infrastructure.database.models.models import EmployeeLeaderboard
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
    def _handle_how_to_queries(cls, lq: str, role_name: str, is_admin: bool, is_super_admin: bool):
        # 1. How to manage / add Users / Employees, Bulk Import, Bulk Export & Custom Fields
        is_employee_query = any(w in lq for w in ['employee', 'user', 'member', 'stakeholder', 'person', 'staff', 'people'])
        is_add_action = any(w in lq for w in ['add', 'create', 'register', 'new', 'invite', 'provision', 'import', 'export', 'custom field', 'configure field', 'manage'])
        if (is_employee_query and is_add_action) or any(p in lq for p in ['how to add employee', 'how to add an employee', 'add employee', 'add user', 'add member', 'bulk import', 'bulk export', 'export user', 'configure field', 'custom field', 'manage users', 'user management']):
            if not is_admin:
                return {
                    "answer": (
                        f"🔒 **Admin Privilege Required**: Managing employee accounts, bulk imports, and custom fields requires **Organization Admin** privileges.\n\n"
                        f"As a **{role_name}**, you can view your team members inside your active projects on the **Project Details > Team** tab."
                    ),
                    "sources": []
                }
            return {
                "answer": (
                    "### 👥 How to Add & Manage Organization Employees (Org Admin)\n\n"
                    "Follow these steps to register members, bulk import/export, or customize user attributes:\n\n"
                    "1. **Navigate to User Management**:\n"
                    "   - Open the left sidebar and click **User Management** (`/admin/users.html`).\n\n"
                    "2. **Add an Individual Employee / Member**:\n"
                    "   - Click the purple **`+ Add Member`** button in the top right.\n"
                    "   - Fill in Full Name, Corporate Email, Username, Role (*Admin, Facilitator, Reviewer, Team Leader, Team Member*), Plant, and Department.\n"
                    "   - Click **Save Member**.\n\n"
                    "3. **Bulk Import from Excel / CSV (Batch Provisioning)**:\n"
                    "   - Click **`Bulk Import`** in the action bar, download the template, paste your roster, and upload.\n\n"
                    "4. **Bulk Export Directory**:\n"
                    "   - Click **`Bulk Export`** to download your full workforce directory.\n\n"
                    "5. **Configure Custom Employee Fields**:\n"
                    "   - Click **`Configure Fields`** to add custom columns like Employee ID, Grade, or Shift."
                ),
                "sources": []
            }

        # 2. How to configure / add a Plant Location
        is_plant_query = any(w in lq for w in ['plant', 'location', 'facility', 'site', 'factory', 'branch'])
        is_plant_action = any(w in lq for w in ['add', 'create', 'configure', 'setup', 'new', 'change', 'manage', 'how to'])
        if (is_plant_query and is_plant_action) or any(p in lq for p in ['plant location', 'configure plant', 'add plant', 'create plant']):
            if not is_admin:
                return {
                    "answer": f"🔒 **Admin Privilege Required**: Configuring plant locations requires **Organization Admin** privileges.",
                    "sources": []
                }
            return {
                "answer": (
                    "### 🏭 How to Configure & Manage Plant Locations\n\n"
                    "1. **Navigate to Plant Locations**:\n"
                    "   - Click **Plant Locations** (`/admin/plants.html`) under Administration.\n\n"
                    "2. **Add a New Plant**:\n"
                    "   - Click **`+ Add Plant Location`**.\n"
                    "   - Enter Plant Name, Plant Code, and Address.\n"
                    "   - Click **Save Plant Location**."
                ),
                "sources": []
            }

        # 3. How to configure / add Departments
        is_dept_query = any(w in lq for w in ['department', 'dept', 'unit', 'division'])
        is_dept_action = any(w in lq for w in ['add', 'create', 'configure', 'setup', 'new', 'change', 'manage', 'how to'])
        if (is_dept_query and is_dept_action) or any(p in lq for p in ['add department', 'create department', 'configure department']):
            if not is_admin:
                return {
                    "answer": f"🔒 **Admin Privilege Required**: Configuring departments requires **Organization Admin** privileges.",
                    "sources": []
                }
            return {
                "answer": (
                    "### 🏢 How to Configure & Manage Organization Departments\n\n"
                    "1. **Navigate to Departments** (`/admin/departments.html`).\n"
                    "2. **Select Parent Plant** from the dropdown filter.\n"
                    "3. Click **`+ Add Department`**, enter Department Name and Code, then click **Save**."
                ),
                "sources": []
            }

        # 4. How to create or start a new QC Project (Available to Team Leader, Member, Admin)
        is_proj_word = any(w in lq for w in ['project', 'qcms', 'quality circle', 'qc story'])
        is_proj_start = any(w in lq for w in ['start', 'create', 'launch', 'new', 'initiate', 'begin', 'execute'])
        if (is_proj_word and is_proj_start) or any(p in lq for p in ['create project', 'start project', 'new project', 'how to create a project', 'how to start a project', 'how to start and execute']):
            return {
                "answer": (
                    "### 🚀 How to Start & Execute an 8-Stage QCMS Project\n\n"
                    "1. **Open Project Repository**:\n"
                    "   - In the sidebar, click **Project Repository** (`/projects/projects-repository.html`).\n\n"
                    "2. **Launch Project Creator**:\n"
                    "   - Click the primary **`+ Create New Project`** button in the top right.\n\n"
                    "3. **Fill Project Initiation Charter**:\n"
                    "   - **Title & Problem Statement**: Define the quality problem clearly.\n"
                    "   - **Plant & Department**: Select operational unit.\n"
                    "   - **Assign Leadership**: Select Team Leader, Facilitator, and Reviewer.\n"
                    "   - **Select Team Members**: Pick team contributors.\n\n"
                    "4. Click **Create & Go to Stage 1** to initialize the project."
                ),
                "sources": []
            }

        # 5. How to submit Kaizen ideas or earn rewards
        if any(w in lq for w in ['idea', 'kaizen', 'submit idea', 'earn points', 'reward points', 'badge']):
            return {
                "answer": (
                    "### 💡 How to Submit Ideas & Earn Reward Points\n\n"
                    "1. **Submit Kaizen Ideas**:\n"
                    "   - Navigate to **Ideas Hub** in the sidebar.\n"
                    "   - Click **`+ Submit New Idea`**, describe your improvement proposal and projected impact.\n"
                    "   - Earn instant reward points upon submission and bonus points upon approval.\n\n"
                    "2. **Earn Points from Projects**:\n"
                    "   - Complete assigned Stage tasks, log 5-Why root cause findings, and standardize SOPs in Stage 8 to climb the organization leaderboard!"
                ),
                "sources": []
            }

        # 6. How to configure Stage Weightages
        if any(w in lq for w in ['weightage', 'weight slider', 'rca heavy', 'stage weight', 'stage percentage']):
            if not is_admin:
                return {
                    "answer": f"🔒 **Admin Privilege Required**: Configuring 8-stage progress weightages requires **Organization Admin** privileges.",
                    "sources": []
                }
            return {
                "answer": (
                    "### ⚖️ How to Configure 8-Stage Progress Weightages (Org Admin)\n\n"
                    "1. Go to **Administration > Stage Templates / Settings** (`/admin/settings.html`).\n"
                    "2. Move individual sliders or type numeric percentages for Stage 1 through Stage 8 (sum = 100%).\n"
                    "3. Apply presets (*Equal Weightage, RCA Heavy, or Execution Heavy*) and click **Save Weightages**."
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

        return None

    @classmethod
    def _handle_qc_methodology_queries(cls, lq: str):
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
        if any(p in lq for p in ['fishbone', 'ishikawa', 'cause and effect', '6m', 'cause identification']):
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

        # Manufacturing Defect Root Cause Intelligence (Welding, Casting, Machining, Molding, Assembly)
        if any(w in lq for w in ['weld', 'welding', 'porosity', 'spatter', 'undercut', 'slag', 'fusion']):
            return {
                "answer": (
                    "### ⚡ Welding Quality & Defect Root Cause Analysis\n\n"
                    "In Quality Circle projects addressing welding anomalies (e.g., porosity, lack of penetration, undercut, spatter), apply the **6M Ishikawa framework** across Stages 3 & 4:\n\n"
                    "1. **Common Welding Defects & Likely Root Causes**:\n"
                    "   - **Porosity / Blowholes**: Gas entrapment caused by moisture on electrodes, insufficient shielding gas flow rate, or oil/rust contamination on workpiece.\n"
                    "   - **Lack of Penetration / Fusion**: Low welding current, improper torch travel angle, excessive travel speed, or incorrect joint groove bevel.\n"
                    "   - **Undercut**: Excessive arc voltage/current, overly rapid travel speed, or improper weave technique.\n"
                    "   - **Excessive Spatter**: Current too high for wire diameter, arc length too long, or incorrect shielding gas mixture (e.g., pure CO₂ vs Ar/CO₂).\n"
                    "   - **Cracks (Hot/Cold)**: High thermal stress, hydrogen embrittlement, improper preheat/post-weld heat treatment, or sulfur/phosphorus impurities.\n\n"
                    "2. **Recommended 8-Stage QC Methodology Steps**:\n"
                    "   - **Stage 2 (Observation)**: Stratify defect data by welder ID, shift, joint geometry, and gas cylinder batch on a Pareto Chart.\n"
                    "   - **Stage 3 (Fishbone)**: Map potential 6M causes covering gas purity (Material), torch maintenance (Machine), and welder technique (Manpower).\n"
                    "   - **Stage 4 (Root Cause Verification)**: Conduct cross-sectional macro-etch testing and Good vs. Bad parameter comparison.\n"
                    "   - **Stage 5 & 6 (Countermeasures)**: Implement Poka-Yoke gas flow interlocks, standard parameter cards, and Welder Qualification (WQR).\n"
                    "   - **Stage 8 (SOP)**: Update the Welding Procedure Specification (WPS) and institutionalize pre-weld surface cleaning checklists."
                ),
                "sources": []
            }

        if any(w in lq for w in ['casting', 'shrinkage', 'blowhole', 'flash defect', 'misrun']):
            return {
                "answer": (
                    "### 🔩 Casting Quality & Defect Root Cause Analysis\n\n"
                    "For casting anomalies (shrinkage cavity, blowholes, misrun, sand inclusion):\n\n"
                    "1. **Primary Root Causes**:\n"
                    "   - **Shrinkage Porosity**: Inadequate riser volume, incorrect gating ratio, or improper pouring temperature.\n"
                    "   - **Blowholes**: High moisture content in molding sand, low sand permeability, or insufficient venting.\n"
                    "   - **Misrun / Cold Shut**: Low pouring temperature, sluggish metal fluidity, or thin section wall design.\n\n"
                    "2. **Recommended QC Tools**:\n"
                    "   - **Stage 3**: 6M Fishbone focusing on Mold Permeability (Method) and Melt Chemistry (Material).\n"
                    "   - **Stage 5**: Adjust gating design and implement strict mold temperature pyrometer controls."
                ),
                "sources": []
            }

        if any(w in lq for w in ['machining', 'tool wear', 'surface finish', 'burr', 'chatter', 'roughness', 'dimensional deviation']):
            return {
                "answer": (
                    "### ⚙️ Machining Quality & Dimensional Defect Analysis\n\n"
                    "For CNC turning, milling, and grinding quality challenges:\n\n"
                    "1. **Primary Root Causes**:\n"
                    "   - **Surface Roughness (High Ra)**: Tool edge built-up (BUE), incorrect feed per tooth, or worn insert radius.\n"
                    "   - **Chatter Marks**: Insufficient workpiece clamping rigidity, excessive tool overhang, or spindle bearing play.\n"
                    "   - **Dimensional Drift**: Thermal expansion of spindle/coolant, tool deflection, or fixture locator wear.\n\n"
                    "2. **Recommended QC Tools**:\n"
                    "   - **Stage 2**: Run SPC X-bar & R control charts to distinguish common cause vs. assignable cause variations.\n"
                    "   - **Stage 6**: Standardize tool life management counters and implement dial indicator fixture zero-checks."
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
    def _generate_smart_fallback(cls, query: str, role_name: str, user: User, is_super_admin: bool, is_admin: bool):
        if is_super_admin:
            return {
                "answer": (
                    f"Hello Super Administrator! Here are quick guides for your console:\n\n"
                    f"1. **Tenant Governance**: *'How to modify organization data?'* or *'How to download overall organization CSV?'*\n"
                    f"2. **Plans & Billing**: *'How to create a new plan?'* or *'How to dispatch pay-as-you-go bills?'*\n"
                    f"3. **Support & Notifications**: *'How to extend trial?'*, *'How to create support ticket?'*, or *'How to set SMS/Email notification rules?'*\n"
                    f"4. **System Security & CMS**: *'How to purge audit logs?'*, *'How to upload logo?'*, or *'How to modify landing page?'*\n\n"
                    f"Ask any question for instant step-by-step SOP guidance!"
                ),
                "sources": []
            }
        elif is_admin:
            return {
                "answer": (
                    f"Hello **{role_name}**! Here is what you can configure in your Organization Admin console:\n\n"
                    f"1. **Organization Hierarchy**: *'How to add plant locations or departments?'*\n"
                    f"2. **Workforce Management**: *'How to add employees, bulk import CSV, or configure custom fields?'*\n"
                    f"3. **QC Customization**: *'How to configure stage weightages or sign-off hierarchy?'*\n"
                    f"4. **Integrations & Branding**: *'How to set up email/SMS providers or document branding?'*\n\n"
                    f"Feel free to ask any question above!"
                ),
                "sources": []
            }
        else:
            return {
                "answer": (
                    f"Hello **{role_name}**! Here is what I can help you with in your workspace:\n\n"
                    f"1. **Quality Circle Projects**: *'How to create a project?'* or *'What is the 8-stage methodology?'*\n"
                    f"2. **Quality Tools**: *'How to build a Fishbone Diagram (6M)?'*, *'How to run Pareto Analysis?'*, or *'How to do 5-Why RCA?'*\n"
                    f"3. **Workforce & Leaderboards**: *'How many employees are in QC projects?'* or *'Show rewards leaderboard rankings.'*\n"
                    f"4. **Kaizen Ideas**: *'How to submit Kaizen ideas and earn points?'*\n\n"
                    f"Ask any question about your active project or quality tools!"
                ),
                "sources": []
            }
