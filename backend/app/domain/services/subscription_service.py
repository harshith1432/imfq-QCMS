from app.infrastructure.database.models.models import Organization, Project, User
from app import db
from datetime import datetime

PLAN_LIMITS = {
    'Trial': {
        'max_users': 50,
        'max_active_projects': 25,
        'features': ['basic_workflow', 'standard_reports', 'full_workflow', 'advanced_analytics'],
        'workflow_stages': [1, 2, 3, 4, 5, 6, 7, 8],
        'ai_assistant': True,
        'white_label': False,
        'multi_plant': False,
        'api_access': True
    },
    'Starter': {
        'max_users': 50,
        'max_active_projects': 1,
        'features': ['basic_workflow', 'standard_reports'],
        'workflow_stages': [1, 2, 3, 4], # Starter only gets first 4 stages? Or maybe just limited active projects.
        'ai_assistant': False,
        'white_label': False,
        'multi_plant': False,
        'api_access': False
    },
    'Professional': {
        'max_users': 500,
        'max_active_projects': 5,
        'features': ['full_workflow', 'advanced_analytics', 'repository', 'ai_assistant', 'audit_logs'],
        'workflow_stages': [1, 2, 3, 4, 5, 6, 7, 8],
        'ai_assistant': True,
        'white_label': False,
        'multi_plant': False,
        'api_access': False
    },
    'Enterprise': {
        'max_users': 1000000, # Unlimited
        'max_active_projects': 1000000, # Unlimited
        'features': ['full_workflow', 'advanced_analytics', 'repository', 'ai_assistant', 'audit_logs', 'white_label', 'multi_plant', 'api_access'],
        'workflow_stages': [1, 2, 3, 4, 5, 6, 7, 8],
        'ai_assistant': True,
        'white_label': True,
        'multi_plant': True,
        'api_access': True
    }
}

class SubscriptionManager:
    @staticmethod
    def get_default_trial_plan():
        """
        Query the active SaaSPlan configured with plan_type='Trial'.
        Returns SaaSPlan instance or None.
        """
        from app.infrastructure.database.models.models import SaaSPlan
        from sqlalchemy import func
        trial_plan = SaaSPlan.query.filter(
            func.lower(SaaSPlan.status) == 'active',
            (SaaSPlan.is_default_trial == True) | 
            (func.lower(SaaSPlan.plan_type).like('%trial%')) | 
            (func.lower(SaaSPlan.name).like('%trial%'))
        ).order_by(SaaSPlan.is_default_trial.desc(), SaaSPlan.id.asc()).first()
        
        if not trial_plan:
            trial_plan = SaaSPlan.query.filter(func.lower(SaaSPlan.status) == 'active').order_by(SaaSPlan.id.asc()).first()
            if not trial_plan:
                trial_plan = SaaSPlan.query.order_by(SaaSPlan.id.asc()).first()
            if trial_plan and hasattr(trial_plan, 'is_default_trial') and not trial_plan.is_default_trial:
                try:
                    from app import db
                    trial_plan.is_default_trial = True
                    db.session.commit()
                except Exception:
                    pass
        return trial_plan

    @staticmethod
    def get_organization_plan_limits(org_id):
        """
        Determines the active subscription plan and limits for an organization.
        Queries:
          1. Organization record
          2. Active Subscription record
          3. SaaSPlan & SaaSPlanLimits definition from DB
          4. Static PLAN_LIMITS fallback dictionary
        Returns:
          dict: {
             'plan_name': str,
             'max_users': int,
             'max_projects': int,
             'storage_limit_gb': float
          }
        """
        from app.infrastructure.database.models.models import Organization, Subscription, SaaSPlan, SaaSPlanLimits
        from sqlalchemy import func

        org = Organization.query.get(org_id)
        if not org:
            return {
                'plan_name': 'Unknown',
                'max_users': 50,
                'max_projects': 1,
                'storage_limit_gb': 10.0
            }

        plan_name = org.subscription_plan or 'Starter'
        plan_obj = None

        # 1. Check active subscription record
        sub = Subscription.query.filter_by(org_id=org_id).order_by(Subscription.id.desc()).first()
        if sub:
            if hasattr(sub, 'plan_id') and sub.plan_id:
                plan_obj = SaaSPlan.query.get(sub.plan_id)
            if not plan_obj and getattr(sub, 'plan_name', None):
                plan_name = sub.plan_name

        # 2. Query SaaSPlan by name / code / plan_type
        if not plan_obj and plan_name:
            plan_obj = SaaSPlan.query.filter(
                (func.lower(SaaSPlan.name) == plan_name.lower()) |
                (func.lower(SaaSPlan.plan_type) == plan_name.lower()) |
                (func.lower(SaaSPlan.code) == plan_name.lower())
            ).first()

        max_projects = None
        max_users = None
        storage_gb = 10.0

        if plan_obj and plan_obj.limits:
            limits = plan_obj.limits
            max_projects = limits.max_projects
            max_users = limits.max_users
            storage_gb = getattr(limits, 'storage_limit_gb', 10.0)
            plan_name = plan_obj.name

        # 3. Fallback to PLAN_LIMITS dictionary if DB limit is not set
        fallback = PLAN_LIMITS.get(plan_name, PLAN_LIMITS.get(plan_obj.plan_type if plan_obj else 'Starter', PLAN_LIMITS.get('Trial', PLAN_LIMITS['Starter'])))

        final_max_projects = max_projects if max_projects is not None else fallback.get('max_active_projects', 25)
        final_max_users = max_users if max_users is not None else fallback.get('max_users', 50)

        return {
            'plan_name': plan_name,
            'max_projects': final_max_projects,
            'max_users': final_max_users,
            'storage_limit_gb': storage_gb
        }

    @staticmethod
    def get_plan_config(plan_name, org_id=None):
        if org_id:
            limits = SubscriptionManager.get_organization_plan_limits(org_id)
            base = PLAN_LIMITS.get(limits['plan_name'], PLAN_LIMITS.get('Trial', PLAN_LIMITS['Starter'])).copy()
            base['max_active_projects'] = limits['max_projects']
            base['max_users'] = limits['max_users']
            return base

        if plan_name:
            from app.infrastructure.database.models.models import SaaSPlan
            from sqlalchemy import func
            db_plan = SaaSPlan.query.filter(
                (func.lower(SaaSPlan.name) == plan_name.lower()) |
                (func.lower(SaaSPlan.plan_type) == plan_name.lower()) |
                (func.lower(SaaSPlan.code) == plan_name.lower())
            ).first()
            if db_plan and db_plan.limits:
                base = PLAN_LIMITS.get(db_plan.plan_type, PLAN_LIMITS.get('Trial', PLAN_LIMITS['Starter'])).copy()
                base['max_users'] = db_plan.limits.max_users
                base['max_active_projects'] = db_plan.limits.max_projects
                base['storage_limit_gb'] = db_plan.limits.storage_limit_gb
                return base

        base = PLAN_LIMITS.get(plan_name, PLAN_LIMITS.get('Trial', PLAN_LIMITS['Starter'])).copy()
        return base

    @staticmethod
    def check_user_limit(org_id):
        limits = SubscriptionManager.get_organization_plan_limits(org_id)
        plan_name = limits['plan_name']
        max_users = limits['max_users']

        current_users = User.query.filter_by(org_id=org_id).count()

        if current_users >= max_users:
            return False, f"User limit reached for {plan_name} plan ({max_users}). Please upgrade."

        return True, "Success"

    @staticmethod
    def check_project_limit(org_id):
        limits = SubscriptionManager.get_organization_plan_limits(org_id)
        plan_name = limits['plan_name']
        max_projects = limits['max_projects']

        # Count active/in-progress projects for this organization
        active_projects = Project.query.filter_by(org_id=org_id).filter(Project.status != 'Completed').count()

        if active_projects >= max_projects:
            return False, f"Active project limit reached for {plan_name} plan ({max_projects}). Please upgrade for more concurrent projects."

        return True, "Success"

    @staticmethod
    def has_feature(org_id, feature_name):
        org = Organization.query.get(org_id)
        if not org:
            return False
        
        config = SubscriptionManager.get_plan_config(org.subscription_plan)
        
        # Check if subscription is active or trialing
        if org.subscription_status not in ['Active', 'Trialing']:
            return False
            
        # Check trial expiry
        if org.subscription_status == 'Trialing' and org.trial_ends_at and org.trial_ends_at < datetime.utcnow():
            # Update status to Expired if we detected it here
            org.subscription_status = 'Expired'
            db.session.commit()
            return False

        return config.get(feature_name, False) or feature_name in config.get('features', [])

    @staticmethod
    def can_access_stage(org_id, stage_number):
        org = db.session.get(Organization, org_id)
        if not org:
            return False
        
        config = SubscriptionManager.get_plan_config(org.subscription_plan)
        return stage_number in config.get('workflow_stages', [])

    @staticmethod
    def get_usage_stats(org_id):
        org = db.session.get(Organization, org_id)
        if not org:
            return None
            
        config = SubscriptionManager.get_plan_config(org.subscription_plan)
        current_users = User.query.filter_by(org_id=org_id).count()
        active_projects = Project.query.filter_by(org_id=org_id).filter(Project.status != 'Completed').count()
        
        return {
            "plan_name": org.subscription_plan,
            "status": org.subscription_status,
            "usage": {
                "users": {
                    "current": current_users,
                    "limit": config['max_users']
                },
                "projects": {
                    "current": active_projects,
                    "limit": config['max_active_projects']
                }
            }
        }

    @staticmethod
    def is_expiring_soon(org):
        return is_org_expiring_soon(org)

    @staticmethod
    def get_effective_expiry_and_start(org):
        return get_org_effective_expiry_and_start(org)


import math

def get_org_effective_expiry_and_start(org):
    """
    Returns (expiry_date, start_date) for an organization based on its active or trial state.
    For Active/Paid orgs: uses license_expiry_date first, then active Subscription.end_date, then trial_ends_at.
    For Trial/Trialing orgs: uses trial_ends_at first, then active Subscription.trial_end_date, then license_expiry_date.
    """
    if not org:
        return None, None

    status = (getattr(org, 'subscription_status', '') or '').strip().lower()
    
    expiry_date = None
    start_date = None

    if status in ('active', 'paid'):
        expiry_date = getattr(org, 'license_expiry_date', None) or getattr(org, 'trial_ends_at', None)
        start_date = getattr(org, 'license_start_date', None) or getattr(org, 'created_at', None)
    else:
        expiry_date = getattr(org, 'trial_ends_at', None) or getattr(org, 'license_expiry_date', None)
        start_date = getattr(org, 'trial_start_date', None) or getattr(org, 'created_at', None)

    if not expiry_date:
        try:
            from app.infrastructure.database.models.models import Subscription
            sub = Subscription.query.filter_by(org_id=org.id).order_by(Subscription.id.desc()).first()
            if sub:
                expiry_date = sub.end_date or sub.trial_end_date
                start_date = start_date or sub.start_date or sub.trial_start_date
        except Exception:
            pass

    return expiry_date, start_date


def is_org_expiring_soon(org):
    """
    Determines if an organization's active subscription or trial is 'Expiring Soon'.
    Threshold rule:
    - 7 days or fewer remaining (for short plans/trials) OR
    - 20% or less remaining duration of total plan / trial period.
    Only applies to non-deleted organizations whose status is Active or Trialing.
    """
    if not org or getattr(org, 'is_deleted', False):
        return False
    
    status = (getattr(org, 'subscription_status', '') or '').strip().lower()
    if status in ('expired', 'suspended', 'canceled', 'revoked'):
        return False

    expiry_date, start_date = get_org_effective_expiry_and_start(org)
    if not expiry_date:
        return False

    now = datetime.utcnow()
    remaining_seconds = (expiry_date - now).total_seconds()
    remaining_days = remaining_seconds / 86400.0

    # If remaining_days is <= 0 but status is Active/Trialing (expiring today or due now)
    if remaining_days <= 0:
        return True

    # Calculate total plan/trial duration in days
    total_days = None
    if start_date and expiry_date > start_date:
        total_days = (expiry_date - start_date).days

    if not total_days or total_days <= 0:
        plan = (getattr(org, 'subscription_plan', '') or '').lower()
        if 'year' in plan or 'annual' in plan:
            total_days = 365
        elif 'quarter' in plan:
            total_days = 90
        elif status in ('trialing', 'trial'):
            total_days = 14
        else:
            total_days = 30

    # 20% threshold with a minimum guarantee of 7 days
    threshold_days = max(7, math.ceil(total_days * 0.20))

    return remaining_days <= threshold_days
