from app.infrastructure.database.models.models import Organization, Project, User
from app import db
from datetime import datetime, timedelta

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
                'plan_name': 'Trial',
                'max_users': 50,
                'max_projects': 25,
                'storage_limit_gb': 10.0
            }

        raw_plan_name = (org.subscription_plan or '').strip()
        plan_obj = None
        is_trial_status = org.subscription_status in ['Trialing', 'Trial'] or raw_plan_name.lower() in ['trial', 't1']

        # 1. Check active subscription record
        sub = Subscription.query.filter_by(org_id=org_id).order_by(Subscription.id.desc()).first()
        if sub and hasattr(sub, 'plan_id') and sub.plan_id:
            plan_obj = SaaSPlan.query.get(sub.plan_id)

        # 2. Prioritize default trial plan if organization is on trial
        if not plan_obj and is_trial_status:
            plan_obj = SaaSPlan.query.filter(
                (SaaSPlan.is_default_trial == True) |
                (func.lower(func.trim(SaaSPlan.plan_type)) == 'trial') |
                (func.lower(func.trim(SaaSPlan.name)) == 'trial')
            ).first()

        # 3. Query SaaSPlan by stripped name / code / plan_type
        if not plan_obj and raw_plan_name:
            plan_obj = SaaSPlan.query.filter(
                (func.lower(func.trim(SaaSPlan.name)) == raw_plan_name.lower()) |
                (func.lower(func.trim(SaaSPlan.plan_type)) == raw_plan_name.lower()) |
                (func.lower(func.trim(SaaSPlan.code)) == raw_plan_name.lower())
            ).first()

        max_projects = None
        max_users = None
        storage_gb = 10.0
        plan_name = raw_plan_name or 'Trial'

        if plan_obj and plan_obj.limits:
            limits = plan_obj.limits
            max_projects = limits.max_projects
            max_users = limits.max_users
            storage_gb = getattr(limits, 'storage_limit_gb', 10.0)
            plan_name = plan_obj.name.strip()

        # 4. Fallback to PLAN_LIMITS dictionary
        fallback_key = 'Trial' if is_trial_status else 'Starter'
        fallback = PLAN_LIMITS.get(plan_name, PLAN_LIMITS.get(plan_obj.plan_type if plan_obj else fallback_key, PLAN_LIMITS.get(fallback_key, PLAN_LIMITS['Trial'])))

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
            org = db.session.get(Organization, org_id) if isinstance(org_id, int) else org_id
            is_trial = org and org.subscription_status in ['Trialing', 'Trial']
            fallback_key = 'Trial' if is_trial else 'Starter'
            base = PLAN_LIMITS.get(limits['plan_name'], PLAN_LIMITS.get(fallback_key, PLAN_LIMITS['Trial'])).copy()
            base['max_active_projects'] = limits['max_projects']
            base['max_users'] = limits['max_users']
            return base

        clean_name = (plan_name or '').strip()
        if clean_name:
            from app.infrastructure.database.models.models import SaaSPlan
            from sqlalchemy import func
            db_plan = SaaSPlan.query.filter(
                (func.lower(func.trim(SaaSPlan.name)) == clean_name.lower()) |
                (func.lower(func.trim(SaaSPlan.plan_type)) == clean_name.lower()) |
                (func.lower(func.trim(SaaSPlan.code)) == clean_name.lower())
            ).first()
            if db_plan and db_plan.limits:
                base = PLAN_LIMITS.get(db_plan.plan_type, PLAN_LIMITS.get('Trial', PLAN_LIMITS['Starter'])).copy()
                base['max_users'] = db_plan.limits.max_users
                base['max_active_projects'] = db_plan.limits.max_projects
                base['storage_limit_gb'] = db_plan.limits.storage_limit_gb
                return base

        base = PLAN_LIMITS.get(clean_name, PLAN_LIMITS.get('Trial', PLAN_LIMITS['Starter'])).copy()
        return base
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
        
        status_str = (org.subscription_status or 'Active')
        plan_str = (org.subscription_plan or 'Starter')
        is_trial = status_str.lower() in ['trialing', 'trial'] or 'trial' in plan_str.lower()

        return {
            "plan_name": plan_str,
            "status": status_str,
            "is_trial": is_trial,
            "trial_ends_at": org.trial_ends_at.isoformat() if org.trial_ends_at else None,
            "trial_extension_count": getattr(org, 'trial_extension_count', 0) or 0,
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
    Returns (expiry_date, start_date) for an organization based on its assigned plan cycle.
    Supports Monthly (30d), Quarterly (90d), Yearly (365d), Trial (trial_days), or Custom duration.
    Calculates dynamic countdown days remaining.
    """
    if not org:
        return None, None

    now = datetime.utcnow()
    status = (getattr(org, 'subscription_status', '') or '').strip().lower()

    from app.infrastructure.database.models.models import Subscription, SaaSPlan
    sub = Subscription.query.filter_by(org_id=org.id).order_by(Subscription.id.desc()).first()

    start_date = getattr(org, 'license_start_date', None) or (sub.start_date if sub else None) or getattr(org, 'created_at', None) or now
    expiry_date = getattr(org, 'license_expiry_date', None) or (sub.end_date if sub else None) or getattr(org, 'trial_ends_at', None) or (sub.trial_end_date if sub else None)

    plan_name = getattr(org, 'subscription_plan', None) or (sub.plan_name if sub else None)
    if plan_name:
        sp = SaaSPlan.query.filter(
            db.or_(SaaSPlan.name == plan_name, SaaSPlan.code == plan_name)
        ).first()
        if sp:
            from app.infrastructure.database.models.models import SaaSPlanPricing
            pricing = SaaSPlanPricing.query.filter_by(plan_id=sp.id, is_active=True).first()
            cycle = (pricing.billing_cycle if pricing else (getattr(sp, 'billing_cycle', None) or (sub.billing_cycle if sub else None) or 'Monthly')).strip().title()
            
            if cycle in ('Yearly', 'Annual'):
                duration_days = 365
            elif cycle in ('Quarterly', 'Quarter'):
                duration_days = 90
            elif cycle in ('Monthly', 'Month'):
                duration_days = 30
            elif getattr(sp, 'duration_days', None) and sp.duration_days > 0:
                duration_days = sp.duration_days
            elif cycle in ('Trial', 'Trialing', 'Trial Duration'):
                duration_days = getattr(sp, 'trial_days', None) or getattr(sp, 'trial_duration_days', 30) or 30
            else:
                duration_days = 30  # Monthly default

            calc_expiry = start_date + timedelta(days=duration_days)

            # If no expiry date set or if existing expiry date exceeds plan cycle bounds (e.g. 365 for Quarterly)
            if not expiry_date or abs((expiry_date - calc_expiry).days) > 3 or (cycle in ('Quarterly', 'Quarter') and (expiry_date - start_date).days > 100):
                expiry_date = calc_expiry

    if not expiry_date:
        expiry_date = start_date + timedelta(days=30)

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


def apply_new_plan_to_organization(org, plan_name, billing_cycle=None, approved_by_id=None):
    """
    Updates an Organization and its active Subscription record when a new plan is assigned or payment is approved.
    Synchronizes:
      - org.subscription_plan
      - org.subscription_status ('Active' or 'Trialing')
      - org.max_users (from new plan limits)
      - org.storage_limit_mb (from new plan limits)
      - org.license_start_date & org.license_expiry_date & org.trial_ends_at (calculated from plan cycle duration)
      - Active Subscription record (created or updated)
    """
    if not org or not plan_name:
        return org

    import secrets
    import math
    now = datetime.utcnow()
    pname = str(plan_name).strip()

    from app.infrastructure.database.models.models import db, SaaSPlan, SaaSPlanPricing, Subscription, User
    from sqlalchemy import func, or_

    sp = SaaSPlan.query.filter(
        or_(func.lower(SaaSPlan.name) == pname.lower(), func.lower(SaaSPlan.code) == pname.lower())
    ).first()

    # Determine limits
    max_users = 50
    max_projects = 10
    storage_mb = 10240.0
    cycle = billing_cycle

    if sp:
        pname = sp.name
        if sp.limits:
            max_users = sp.limits.max_users if sp.limits.max_users is not None else 500
            max_projects = sp.limits.max_projects if sp.limits.max_projects is not None else 50
            if getattr(sp.limits, 'storage_limit_gb', None):
                storage_mb = float(sp.limits.storage_limit_gb) * 1024.0

        pricing = SaaSPlanPricing.query.filter_by(plan_id=sp.id, is_active=True).first()
        if pricing and not cycle:
            cycle = pricing.billing_cycle

    if not cycle:
        cycle = 'Quarterly' if 'quarter' in pname.lower() else ('Yearly' if 'year' in pname.lower() else 'Monthly')

    cycle_title = cycle.strip().title()

    # Calculate duration
    if cycle_title in ('Yearly', 'Annual'):
        duration_days = 365
    elif cycle_title in ('Quarterly', 'Quarter'):
        duration_days = 90
    elif cycle_title in ('Trial', 'Trialing', 'Trial Duration'):
        duration_days = getattr(sp, 'trial_duration_days', None) or getattr(sp, 'trial_days', None) or 30
    else:
        duration_days = 30

    start_dt = now
    expiry_dt = start_dt + timedelta(days=duration_days)

    # 1. Update Organization attributes
    org.subscription_plan = pname
    org.subscription_status = 'Active' if cycle_title not in ('Trial', 'Trialing') else 'Trialing'
    org.max_users = max_users
    org.storage_limit_mb = storage_mb
    org.license_start_date = start_dt
    org.license_expiry_date = expiry_dt
    org.trial_ends_at = expiry_dt

    # Ensure org users are active
    User.query.filter_by(org_id=org.id).update({'is_active': True, 'deactivated_at': None})

    # 2. Update or Create Subscription record
    sub = Subscription.query.filter_by(org_id=org.id).order_by(Subscription.id.desc()).first()
    if not sub:
        sub = Subscription(
            org_id=org.id,
            subscription_uid=f"SUB-{now.year}-{org.id}-{secrets.token_hex(4).upper()}",
            plan_name=pname,
            billing_cycle=cycle_title,
            subscription_status=org.subscription_status,
            start_date=start_dt,
            end_date=expiry_dt,
            max_users=max_users,
            storage_limit_gb=storage_mb / 1024.0
        )
        db.session.add(sub)
    else:
        sub.plan_name = pname
        sub.billing_cycle = cycle_title
        sub.subscription_status = org.subscription_status
        sub.start_date = start_dt
        sub.end_date = expiry_dt
        sub.max_users = max_users
        sub.storage_limit_gb = storage_mb / 1024.0

    db.session.commit()
    return org
