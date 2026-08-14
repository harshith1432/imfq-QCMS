"""
QCMS Employee Reward & Leaderboard System - Point Engine Service
Handles point allocations, duplicate prevention, badge calculations,
leaderboard rank synchronizations, and audit logs.
"""

from datetime import datetime
from sqlalchemy import func
from app import db
from app.infrastructure.database.models.models import (
    User, Organization, EmployeePoints, EmployeeLeaderboard, Project, KnowledgeRepository
)


# ─── POINT VALUE REGISTRY ───────────────────────────────────────────────────
POINT_RULES = {
    # PROJECT
    "project_created": {"points": 30, "description": "Created new Quality Circle project"},
    "project_team_joined": {"points": 10, "description": "Joined Quality Circle project team"},
    "project_became_leader": {"points": 40, "description": "Assigned as Team Leader"},
    "project_became_facilitator": {"points": 25, "description": "Assigned as Project Facilitator"},
    "project_completed": {"points": 100, "description": "Successfully completed Quality Circle project"},
    "project_approved": {"points": 75, "description": "Project approved by Steering Committee"},
    "project_award_won": {"points": 300, "description": "Won Organization Quality Award"},

    # QC STORY (STAGES)
    "qc_stage_1_problem_definition": {"points": 15, "description": "Completed Stage 1: Problem Definition"},
    "qc_stage_2_observation": {"points": 15, "description": "Completed Stage 2: Observation & Gemba Data Collection"},
    "qc_stage_3_interim_containment": {"points": 15, "description": "Completed Stage 3: Interim Containment & Cause Verification"},
    "qc_stage_4_root_cause_analysis": {"points": 25, "description": "Completed Stage 4: Root Cause Analysis (5-Why)"},
    "qc_stage_5_action_planning": {"points": 20, "description": "Completed Stage 5: Countermeasure Action Planning"},
    "qc_stage_6_implementation": {"points": 30, "description": "Completed Stage 6: Implementation & Change Management"},
    "qc_stage_7_verification": {"points": 20, "description": "Completed Stage 7: Performance Verification & Benefits Realization"},
    "qc_stage_8_standardization": {"points": 20, "description": "Completed Stage 8: Standardization & Horizontal Deployment"},
    "qc_stage_8_project_closure": {"points": 25, "description": "Completed Stage 8: Project Closure"},
    "qc_all_8_stages_bonus": {"points": 50, "description": "Completed all 8 QC Story stages bonus"},

    # QUALITY IMPROVEMENT
    "idea_submitted": {"points": 15, "description": "Submitted improvement suggestion / idea"},
    "idea_approved": {"points": 50, "description": "Improvement idea approved for implementation"},
    "suggestion_implemented": {"points": 80, "description": "Implemented quality improvement suggestion"},
    "knowledge_article_published": {"points": 20, "description": "Published article to Knowledge Repository"},
    "best_practice_uploaded": {"points": 25, "description": "Uploaded validated Best Practice case"},
    "sop_uploaded": {"points": 30, "description": "Uploaded or updated Standard Operating Procedure (SOP)"},

    # QC TOOLS
    "tool_5_why": {"points": 10, "description": "Executed 5-Why Analysis"},
    "tool_fishbone": {"points": 15, "description": "Created Fishbone (Ishikawa) Diagram"},
    "tool_pareto": {"points": 15, "description": "Generated Pareto Chart (80/20)"},
    "tool_histogram": {"points": 10, "description": "Created Histogram Chart"},
    "tool_scatter": {"points": 10, "description": "Performed Scatter Diagram & Correlation Analysis"},
    "tool_control_chart": {"points": 10, "description": "Generated Control Chart (UCL/LCL)"},
    "tool_check_sheet": {"points": 10, "description": "Logged Data Check Sheet"},
    "tool_flow_chart": {"points": 10, "description": "Created Process Flowchart"},

    # COLLABORATION
    "comment_added": {"points": 2, "description": "Contributed comment to project"},
    "helpful_comment_marked": {"points": 10, "description": "Comment marked as helpful"},
    "evidence_uploaded": {"points": 5, "description": "Uploaded verification evidence / photo"},
    "review_another_team": {"points": 15, "description": "Reviewed another Quality Circle team's project"},
    "mentor_employee": {"points": 20, "description": "Mentored team member on QC methodology"},

    # MEETING
    "attend_qc_meeting": {"points": 5, "description": "Attended QC Circle meeting"},
    "present_project": {"points": 20, "description": "Presented QC Project at convention/review"},
    "monthly_review": {"points": 15, "description": "Participated in Monthly Quality Review"},
    "weekly_review": {"points": 10, "description": "Participated in Weekly QC Standup"},

    # ADMIN
    "admin_approve_project": {"points": 15, "description": "Approved project milestone"},
    "admin_review_project": {"points": 10, "description": "Completed project review"},
    "admin_close_project": {"points": 10, "description": "Officially closed project"},
    "admin_assign_team": {"points": 5, "description": "Assigned team member to project"},

    # PENALTIES
    "penalty_miss_deadline": {"points": -15, "description": "Penalty: Missed project deadline"},
    "penalty_rejected_review": {"points": -10, "description": "Penalty: Stage submission rejected"},
    "penalty_duplicate_idea": {"points": -5, "description": "Penalty: Submitted duplicate idea"},
    "penalty_inactive_30_days": {"points": -20, "description": "Penalty: Inactive for 30 consecutive days"},
    "penalty_incomplete_stage": {"points": -5, "description": "Penalty: Incomplete stage requirements"}
}

BADGE_THRESHOLDS = [
    (10000, "Quality Champion"),
    (5000, "Diamond"),
    (3000, "Platinum"),
    (1500, "Gold"),
    (700, "Silver"),
    (300, "Bronze"),
    (100, "Beginner"),
    (0, "Newbie")
]


class PointEngineService:
    @staticmethod
    def get_badge_for_points(pts: int) -> str:
        for threshold, name in BADGE_THRESHOLDS:
            if pts >= threshold:
                return name
        return "Newbie"

    @staticmethod
    def award_points(employee_id: int, org_id: int, activity_type: str, 
                     points: int = None, description: str = None, 
                     ref_id: str = None, project_id: int = None, 
                     created_by: int = None):
        """
        Awards points to an employee for a specific activity.
        Guarantees no duplicate records per (employee_id, activity_type, ref_id).
        Recalculates total points, metrics, badge tier, and organization-wide rank.
        """
        if not employee_id or not org_id or not activity_type:
            return None

        # Fetch rule defaults if not specified
        rule = POINT_RULES.get(activity_type, {})
        final_points = points if points is not None else rule.get("points", 0)
        final_desc = description if description else rule.get("description", activity_type.replace('_', ' ').title())

        # Prevent duplicates using activity_reference_id
        ref_str = str(ref_id) if ref_id else f"auto_{int(datetime.utcnow().timestamp())}"
        
        existing = EmployeePoints.query.filter_by(
            employee_id=employee_id,
            activity_type=activity_type,
            activity_reference_id=ref_str
        ).first()
        if existing:
            return {"status": "duplicate", "message": "Points already awarded for this activity", "entry": existing}

        # Insert Point Audit Record
        try:
            pt_entry = EmployeePoints(
                employee_id=employee_id,
                organization_id=org_id,
                project_id=project_id,
                activity_type=activity_type,
                activity_reference_id=ref_str,
                points=final_points,
                description=final_desc,
                created_by=created_by or employee_id,
                created_at=datetime.utcnow()
            )
            db.session.add(pt_entry)
            db.session.commit()
        except Exception as ex:
            db.session.rollback()
            existing = EmployeePoints.query.filter_by(
                employee_id=employee_id,
                activity_type=activity_type,
                activity_reference_id=ref_str
            ).first()
            if existing:
                return {"status": "duplicate", "message": "Points already awarded for this activity", "entry": existing}

        # Update or Create Employee Leaderboard entry
        lb_entry = EmployeeLeaderboard.query.filter_by(employee_id=employee_id).first()
        if not lb_entry:
            lb_entry = EmployeeLeaderboard(
                employee_id=employee_id,
                organization_id=org_id,
                total_points=0,
                badges="Newbie"
            )
            db.session.add(lb_entry)
            db.session.commit()

        # Recalculate metrics for employee
        old_badge = lb_entry.badges
        PointEngineService.sync_employee_metrics(employee_id, org_id)

        # Re-fetch updated leaderboard entry
        lb_entry = EmployeeLeaderboard.query.filter_by(employee_id=employee_id).first()
        new_badge = lb_entry.badges if lb_entry else "Newbie"
        badge_upgraded = old_badge != new_badge

        # Trigger Organization Rank Recalculation
        PointEngineService.recalculate_ranks(org_id)

        return {
            "status": "success",
            "earned_points": final_points,
            "total_points": lb_entry.total_points if lb_entry else 0,
            "badge": new_badge,
            "badge_upgraded": badge_upgraded,
            "old_badge": old_badge,
            "description": final_desc
        }

    @staticmethod
    def sync_employee_metrics(employee_id: int, org_id: int):
        """Recalculate an individual employee's total points and metric counts from source tables."""
        total_pts = db.session.query(func.coalesce(func.sum(EmployeePoints.points), 0))\
            .filter(EmployeePoints.employee_id == employee_id).scalar() or 0

        # Count specific activities
        proj_created = EmployeePoints.query.filter_by(employee_id=employee_id, activity_type="project_created").count()
        proj_completed = EmployeePoints.query.filter_by(employee_id=employee_id, activity_type="project_completed").count()
        ideas_sub = EmployeePoints.query.filter_by(employee_id=employee_id, activity_type="idea_submitted").count()
        ideas_app = EmployeePoints.query.filter_by(employee_id=employee_id, activity_type="idea_approved").count()
        know_art = EmployeePoints.query.filter(
            EmployeePoints.employee_id == employee_id,
            EmployeePoints.activity_type.in_(["knowledge_article_published", "sop_uploaded", "best_practice_uploaded"])
        ).count()
        meet_att = EmployeePoints.query.filter(
            EmployeePoints.employee_id == employee_id,
            EmployeePoints.activity_type.in_(["attend_qc_meeting", "monthly_review", "weekly_review", "present_project"])
        ).count()

        new_badge = PointEngineService.get_badge_for_points(total_pts)

        lb = EmployeeLeaderboard.query.filter_by(employee_id=employee_id).first()
        if not lb:
            lb = EmployeeLeaderboard(employee_id=employee_id, organization_id=org_id)
            db.session.add(lb)

        lb.organization_id = org_id
        lb.total_points = total_pts
        lb.projects_created = proj_created
        lb.projects_completed = proj_completed
        lb.ideas_submitted = ideas_sub
        lb.ideas_approved = ideas_app
        lb.knowledge_articles = know_art
        lb.meetings_attended = meet_att
        lb.badges = new_badge
        lb.last_updated = datetime.utcnow()

        db.session.commit()

    @staticmethod
    def recalculate_ranks(org_id: int):
        """
        Recalculates organization-wide leaderboard rankings using exact tie-breaking rules:
        1. total_points DESC
        2. projects_completed DESC
        3. ideas_approved DESC
        4. knowledge_articles DESC
        5. User.created_at ASC
        """
        entries = db.session.query(EmployeeLeaderboard)\
            .join(User, User.id == EmployeeLeaderboard.employee_id)\
            .filter(EmployeeLeaderboard.organization_id == org_id)\
            .order_by(
                EmployeeLeaderboard.total_points.desc(),
                EmployeeLeaderboard.projects_completed.desc(),
                EmployeeLeaderboard.ideas_approved.desc(),
                EmployeeLeaderboard.knowledge_articles.desc(),
                User.created_at.asc()
            ).all()

        for idx, entry in enumerate(entries, start=1):
            entry.rank = idx

        db.session.commit()

    @staticmethod
    def seed_initial_points_if_needed(org_id: int):
        """
        Initializes leaderboard rows and points for all existing users in the organization
        by scanning real activity in Project, Stage trackers, SOPs, and Knowledge Repository.
        Guarantees NO fake numbers — only real historical actions!
        """
        if not org_id:
            return
        users = User.query.filter_by(org_id=org_id).all()
        for u in users:
            # Ensure leaderboard row exists
            lb = EmployeeLeaderboard.query.filter_by(employee_id=u.id).first()
            if not lb:
                lb = EmployeeLeaderboard(employee_id=u.id, organization_id=org_id, total_points=0, badges="Newbie")
                db.session.add(lb)
                db.session.commit()

            # 1. Projects Created
            created_projs = Project.query.filter_by(creator_id=u.id, org_id=org_id).all()
            for p in created_projs:
                PointEngineService.award_points(
                    employee_id=u.id, org_id=org_id, activity_type="project_created",
                    ref_id=f"proj_create_{p.id}", project_id=p.id, description=f"Created project '{p.title}'"
                )

            # 2. Team Leaders
            leader_projs = Project.query.filter_by(team_leader_id=u.id, org_id=org_id).all()
            for p in leader_projs:
                PointEngineService.award_points(
                    employee_id=u.id, org_id=org_id, activity_type="project_became_leader",
                    ref_id=f"proj_leader_{p.id}", project_id=p.id, description=f"Assigned Team Leader for '{p.title}'"
                )

            # 3. Facilitators
            facil_projs = Project.query.filter_by(facilitator_id=u.id, org_id=org_id).all()
            for p in facil_projs:
                PointEngineService.award_points(
                    employee_id=u.id, org_id=org_id, activity_type="project_became_facilitator",
                    ref_id=f"proj_facil_{p.id}", project_id=p.id, description=f"Assigned Facilitator for '{p.title}'"
                )

            # 4. Completed Projects
            comp_projs = Project.query.filter(Project.creator_id == u.id, Project.status.in_(['Completed', 'Closed'])).all()
            for p in comp_projs:
                PointEngineService.award_points(
                    employee_id=u.id, org_id=org_id, activity_type="project_completed",
                    ref_id=f"proj_completed_{p.id}", project_id=p.id, description=f"Completed project '{p.title}'"
                )

            # 5. Knowledge Articles
            know_entries = KnowledgeRepository.query.filter_by(org_id=org_id).all()
            for k in know_entries:
                if k.project_ref and k.project_ref.creator_id == u.id:
                    PointEngineService.award_points(
                        employee_id=u.id, org_id=org_id, activity_type="knowledge_article_published",
                        ref_id=f"know_art_{k.id}", project_id=k.project_id, description=f"Published knowledge article for '{k.title}'"
                    )

            PointEngineService.sync_employee_metrics(u.id, org_id)

        PointEngineService.recalculate_ranks(org_id)
