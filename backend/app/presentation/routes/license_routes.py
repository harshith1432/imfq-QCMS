import uuid
import json
import base64
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, or_, and_, text
from app.infrastructure.database.models.models import (
    db, User, Organization, Role, Subscription, SubscriptionInvoice, SubscriptionPayment, SuperAdminLog
)

license_bp = Blueprint('licenses', __name__)

# HMAC secret key for license key signing
HMAC_SECRET = "QCMS_SUPER_SECRET_LICENSING_KEY_2026"

# Single source of truth plan catalogue (aligned with subscription_routes.py)
PLAN_CATALOGUE = {
    'Starter': {
        'max_users': 25,
        'storage_limit_gb': 5.0,
        'api_limit': 1000,
        'support_level': 'Standard',
        'enabled_modules': ['Projects', 'Reports']
    },
    'Professional': {
        'max_users': 500,
        'storage_limit_gb': 50.0,
        'api_limit': 10000,
        'support_level': 'Priority',
        'enabled_modules': ['Projects', 'Reports', 'Analytics', 'SOP', 'QC Tools']
    },
    'Enterprise': {
        'max_users': 99999,
        'storage_limit_gb': 500.0,
        'api_limit': 100000,
        'support_level': 'Enterprise',
        'enabled_modules': ['Projects', 'Reports', 'Analytics', 'SOP', 'QC Tools', 'RAG', 'White Label', 'API Access']
    },
    'Custom': {
        'max_users': 100,
        'storage_limit_gb': 10.0,
        'api_limit': 5000,
        'support_level': 'Standard',
        'enabled_modules': []
    }
}

# --- HELPERS ---

def _get_current_user():
    user_id = get_jwt_identity()
    return db.session.get(User, user_id)

def _require_role(user, allowed_capabilities):
    if not user:
        return jsonify({'error': 'Unauthorized — Super Admin required'}), 403
        
    role_name = user.role.name if user.role else ''
    is_sa_custom = isinstance(user.custom_fields, dict) and bool(user.custom_fields.get('super_admin_role'))
    is_sa = role_name == 'SuperAdmin' or is_sa_custom or getattr(user, 'is_super_admin', False)
    if not is_sa:
        return jsonify({'error': 'Unauthorized — Super Admin required'}), 403
    
    sub_role = (user.custom_fields or {}).get('super_admin_role', 'Owner') if isinstance(user.custom_fields, dict) else 'Owner'
    if sub_role in ('Owner', 'SuperAdmin') or not user.custom_fields:
        return None # Full access
        
    # Check capabilities
    user_caps = {
        'Platform Operations': ['view', 'edit', 'export', 'impersonate'],
        'Billing': ['view', 'export'],
        'Support': ['view', 'export'],
        'Product': ['view', 'export'],
        'Read Only': ['view']
    }.get(sub_role, ['view'])

    for cap in allowed_capabilities:
        if cap in user_caps:
            return None
            
    return jsonify({'error': f'Forbidden — {sub_role} lacks required permissions'}), 403

def _log_action(user, action, org_id, old_val=None, new_val=None):
    try:
        log = SuperAdminLog(
            admin_id=user.id,
            action=action,
            target_type='Organization',
            target_id=org_id,
            ip_address=request.remote_addr or '127.0.0.1',
            details={
                'old_value': old_val,
                'new_value': new_val,
                'user_agent': request.headers.get('User-Agent', '')
            }
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"[LICENSING] Audit log error: {e}")

def _generate_key():
    """Generate a clean enterprise key formatted like QCMS-XXXX-XXXX-XXXX-XXXX"""
    raw = uuid.uuid4().hex.upper()
    return f"QCMS-{raw[:4]}-{raw[4:8]}-{raw[8:12]}-{raw[12:16]}"

def _sync_org(org, plan_name, status, max_users, storage_gb, start_date, expiry_date, modules):
    org.subscription_plan = plan_name
    org.subscription_status = status
    org.max_users = max_users
    org.storage_limit_mb = storage_gb * 1024.0
    org.license_start_date = start_date
    org.license_expiry_date = expiry_date
    org.enabled_modules = modules
    if status == 'Trial':
        org.trial_ends_at = expiry_date

# --- ENDPOINTS ---

@license_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_license_stats():
    user = _get_current_user()
    err = _require_role(user, ['view'])
    if err:
        return err

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    query = Organization.query.filter(Organization.is_deleted == False)

    total = query.count()
    active = query.filter_by(subscription_status='Active').count()
    trial = query.filter(Organization.subscription_status.in_(['Trialing', 'Trial'])).count()
    expired = query.filter(
        or_(
            Organization.subscription_status == 'Expired',
            Organization.license_expiry_date < now
        )
    ).count()
    suspended = query.filter_by(subscription_status='Suspended').count()
    revoked = query.filter_by(subscription_status='Revoked').count()
    from app.domain.services.subscription_service import is_org_expiring_soon
    expiring_soon = len([org for org in query.all() if is_org_expiring_soon(org)])
    lifetime = query.filter(
        or_(
            Organization.subscription_plan == 'Lifetime',
            Organization.subscription_plan == 'Custom'
        )
    ).count()

    return jsonify({
        'status': 'success',
        'data': {
            'total': total,
            'active': active,
            'trial': trial,
            'expired': expired,
            'suspended': suspended,
            'revoked': revoked,
            'expiring_soon': expiring_soon,
            'lifetime': lifetime
        }
    })

@license_bp.route('/', methods=['GET'])
@jwt_required()
def list_licenses():
    user = _get_current_user()
    err = _require_role(user, ['view'])
    if err:
        return err

    # Query params
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()
    plan = request.args.get('plan', '').strip()
    expiry_window = request.args.get('expiry_window', '').strip()
    country = request.args.get('country', '').strip()
    state = request.args.get('state', '').strip()
    industry = request.args.get('industry', '').strip()
    
    sort_by = request.args.get('sort_by', 'created_at').strip()
    sort_dir = request.args.get('sort_dir', 'desc').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 15, type=int)

    # Base query
    query = Organization.query.filter(Organization.is_deleted == False)

    # Apply search
    if q:
        search_val = f"%{q}%"
        query = query.filter(
            or_(
                Organization.license_number.ilike(search_val),
                Organization.name.ilike(search_val),
                Organization.org_code.ilike(search_val),
                Organization.email.ilike(search_val)
            )
        )

    # Apply filters
    if status:
        if status == 'Trial':
            query = query.filter(Organization.subscription_status.in_(['Trialing', 'Trial']))
        else:
            query = query.filter(Organization.subscription_status == status)
            
    if plan:
        from app.infrastructure.database.models.models import SaaSPlan
        matching_sp = [sp.name for sp in SaaSPlan.query.filter(
            db.or_(SaaSPlan.plan_type.ilike(plan), SaaSPlan.name.ilike(plan), SaaSPlan.code.ilike(plan))
        ).all()]
        target_plans = set([plan] + matching_sp)
        if plan.lower() in ('trial', 'trialing'):
            target_plans.update(['Trial', 'Trialing', 'Default Trial Plan'])
        query = query.filter(db.or_(*[Organization.subscription_plan.ilike(p) for p in target_plans]))
        
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if expiry_window == '7d':
        query = query.filter(Organization.license_expiry_date >= now, Organization.license_expiry_date <= now + timedelta(days=7))
    elif expiry_window == '30d':
        query = query.filter(Organization.license_expiry_date >= now, Organization.license_expiry_date <= now + timedelta(days=30))
    elif expiry_window == '90d':
        query = query.filter(Organization.license_expiry_date >= now, Organization.license_expiry_date <= now + timedelta(days=90))
    elif expiry_window == 'expired':
        query = query.filter(Organization.license_expiry_date < now)

    if country:
        query = query.filter(Organization.country.ilike(f"%{country}%"))
    if state:
        query = query.filter(Organization.state.ilike(f"%{state}%"))
    if industry:
        query = query.filter(Organization.industry.ilike(f"%{industry}%"))

    # Sorting
    allowed_cols = {
        'created_at': Organization.created_at,
        'license_expiry_date': Organization.license_expiry_date,
        'license_start_date': Organization.license_start_date,
        'max_users': Organization.max_users,
        'name': Organization.name,
        'license_number': Organization.license_number
    }
    col = allowed_cols.get(sort_by, Organization.created_at)
    if sort_dir == 'asc':
        query = query.order_by(col.asc())
    else:
        query = query.order_by(col.desc())

    # Pagination
    pag = query.paginate(page=page, per_page=per_page, error_out=False)

    data = []
    for o in pag.items:
        remaining = None
        if o.license_expiry_date:
            remaining = (o.license_expiry_date - now).days
            
        data.append({
            'id': o.id,
            'license_number': o.license_number or '—',
            'organization_name': o.name,
            'org_code': o.org_code or '—',
            'admin_email': o.email,
            'subscription_plan': o.subscription_plan,
            'subscription_status': o.subscription_status,
            'license_start_date': o.license_start_date.isoformat() if o.license_start_date else None,
            'license_expiry_date': o.license_expiry_date.isoformat() if o.license_expiry_date else None,
            'remaining_days': remaining,
            'max_users': o.max_users,
            'storage_limit_gb': round(o.storage_limit_mb / 1024.0, 1),
            'enabled_modules': o.enabled_modules or [],
            'created_at': o.created_at.isoformat() if o.created_at else None
        })

    return jsonify({
        'status': 'success',
        'data': data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pag.total,
            'pages': pag.pages
        }
    })

# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: get_license_details (Lines 290-353)
# Reason: Unused single organization license detail.
# ==============================================================================
# @license_bp.route('/<int:org_id>', methods=['GET'])
# @jwt_required()
# def get_license_details(org_id):
#     user = _get_current_user()
#     err = _require_role(user, ['view'])
#     if err:
#         return err

#     org = db.get_or_404(Organization, org_id)

#     active_users = len(org.users)
#     active_projects = len(org.projects)
#     active_depts = len(org.departments)

#     sub = Subscription.query.filter_by(org_id=org_id, subscription_status='Active').first()
#     sub_data = None
#     if sub:
#         sub_data = {
#             'subscription_uid': sub.subscription_uid,
#             'billing_cycle': sub.billing_cycle,
#             'support_level': sub.support_level,
#             'payment_status': sub.payment_status,
#             'final_amount': sub.final_amount,
#             'currency': sub.currency
#         }

#     logs = SuperAdminLog.query.filter_by(target_id=org_id, target_type='Organization').order_by(SuperAdminLog.created_at.desc()).limit(15).all()
#     history = []
#     for l in logs:
#         history.append({
#             'action': l.action,
#             'admin': l.admin.full_name if l.admin else 'System',
#             'timestamp': l.created_at.isoformat(),
#             'details': l.details
#         })

#     return jsonify({
#         'status': 'success',
#         'data': {
#             'id': org.id,
#             'license_number': org.license_number or '—',
#             'organization_name': org.name,
#             'org_code': org.org_code or '—',
#             'admin_name': org.admin_name or '—',
#             'admin_email': org.email,
#             'subscription_plan': org.subscription_plan,
#             'subscription_status': org.subscription_status,
#             'license_start_date': org.license_start_date.isoformat() if org.license_start_date else None,
#             'license_expiry_date': org.license_expiry_date.isoformat() if org.license_expiry_date else None,
#             'max_users': org.max_users,
#             'storage_limit_gb': round(org.storage_limit_mb / 1024.0, 1),
#             'storage_used_mb': round(org.storage_used_mb, 2),
#             'enabled_modules': org.enabled_modules or [],
#             'created_at': org.created_at.isoformat() if org.created_at else None,
#             'usage': {
#                 'active_users': active_users,
#                 'active_projects': active_projects,
#                 'active_departments': active_depts,
#                 'api_calls': 4120
#             },
#             'subscription': sub_data,
#             'history': history
#         }
#     })
# [END DEAD CODE: get_license_details]


@license_bp.route('/', methods=['POST'])
@jwt_required()
def create_license():
    user = _get_current_user()
    err = _require_role(user, ['edit'])
    if err:
        return err

    data = request.get_json() or {}
    org_id = data.get('org_id')
    plan_name = data.get('plan_name', 'Professional')
    license_type = data.get('license_type', 'Professional')
    
    if not org_id:
        return jsonify({'error': 'Organization ID is required'}), 422
        
    org = db.session.get(Organization, org_id)
    if not org:
        return jsonify({'error': 'Organization not found'}), 404

    if org.subscription_status == 'Active' and org.license_expiry_date and org.license_expiry_date > datetime.now(timezone.utc).replace(tzinfo=None):
        return jsonify({'error': 'Organization already has a valid active license'}), 409

    start_date = datetime.now(timezone.utc).replace(tzinfo=None)
    
    expiry_date = start_date + timedelta(days=365)
    if license_type == 'Lifetime':
        expiry_date = start_date + timedelta(days=365 * 100)
    elif license_type == 'Trial':
        expiry_date = start_date + timedelta(days=14)

    cat = PLAN_CATALOGUE.get(plan_name, PLAN_CATALOGUE['Professional'])
    max_users = int(data.get('max_users', cat['max_users']))
    storage_gb = float(data.get('storage_limit_gb', cat['storage_limit_gb']))
    enabled_modules = data.get('enabled_modules', cat['enabled_modules'])

    key = _generate_key()
    org.license_number = key
    
    _sync_org(
        org=org,
        plan_name=plan_name,
        status='Active' if license_type != 'Trial' else 'Trial',
        max_users=max_users,
        storage_gb=storage_gb,
        start_date=start_date,
        expiry_date=expiry_date,
        modules=enabled_modules
    )

    db.session.commit()
    _log_action(user, 'LICENSE_CREATED', org.id, None, {
        'license_number': key,
        'plan': plan_name,
        'type': license_type,
        'max_users': max_users,
        'storage_limit_gb': storage_gb,
        'enabled_modules': enabled_modules
    })

    return jsonify({
        'status': 'success',
        'message': 'License generated successfully',
        'license_key': key
    }), 201

# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: update_license (Lines 421-462)
# Reason: Unused direct license editor.
# ==============================================================================
# @license_bp.route('/<int:org_id>', methods=['PUT'])
# @jwt_required()
# def update_license(org_id):
#     user = _get_current_user()
#     err = _require_role(user, ['edit'])
#     if err:
#         return err

#     org = db.get_or_404(Organization, org_id)
#     data = request.get_json() or {}

#     old_val = {
#         'max_users': org.max_users,
#         'storage_limit_mb': org.storage_limit_mb,
#         'enabled_modules': org.enabled_modules,
#         'subscription_plan': org.subscription_plan
#     }

#     if 'plan_name' in data:
#         org.subscription_plan = data['plan_name']
#     if 'max_users' in data:
#         org.max_users = int(data['max_users'])
#     if 'storage_limit_gb' in data:
#         org.storage_limit_mb = float(data['storage_limit_gb']) * 1024.0
#     if 'enabled_modules' in data:
#         org.enabled_modules = data['enabled_modules']

#     db.session.commit()

#     new_val = {
#         'max_users': org.max_users,
#         'storage_limit_mb': org.storage_limit_mb,
#         'enabled_modules': org.enabled_modules,
#         'subscription_plan': org.subscription_plan
#     }

#     _log_action(user, 'LICENSE_UPDATED', org.id, old_val, new_val)

#     return jsonify({
#         'status': 'success',
#         'message': 'License parameters updated successfully'
#     })
# [END DEAD CODE: update_license]


@license_bp.route('/<int:org_id>/activate', methods=['POST'])
@jwt_required()
def activate_license(org_id):
    user = _get_current_user()
    err = _require_role(user, ['edit'])
    if err:
        return err

    org = db.get_or_404(Organization, org_id)
    old_status = org.subscription_status
    
    org.subscription_status = 'Active'
    db.session.commit()
    
    _log_action(user, 'LICENSE_ACTIVATED', org.id, old_status, 'Active')
    return jsonify({'status': 'success', 'message': 'License activated successfully'})

@license_bp.route('/<int:org_id>/suspend', methods=['POST'])
@jwt_required()
def suspend_license(org_id):
    user = _get_current_user()
    err = _require_role(user, ['edit'])
    if err:
        return err

    org = db.get_or_404(Organization, org_id)
    data = request.get_json() or {}
    reason = data.get('reason', 'Administrative suspension')
    
    old_status = org.subscription_status
    org.subscription_status = 'Suspended'
    db.session.commit()
    
    _log_action(user, 'LICENSE_SUSPENDED', org.id, old_status, {'status': 'Suspended', 'reason': reason})
    return jsonify({'status': 'success', 'message': 'License suspended successfully'})

@license_bp.route('/<int:org_id>/resume', methods=['POST'])
@jwt_required()
def resume_license(org_id):
    user = _get_current_user()
    err = _require_role(user, ['edit'])
    if err:
        return err

    org = db.get_or_404(Organization, org_id)
    old_status = org.subscription_status
    
    org.subscription_status = 'Active'
    db.session.commit()
    
    _log_action(user, 'LICENSE_RESUMED', org.id, old_status, 'Active')
    return jsonify({'status': 'success', 'message': 'License resumed successfully'})

# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: renew_license (Lines 517-547)
# Reason: Unused license renewal route.
# ==============================================================================
# @license_bp.route('/<int:org_id>/renew', methods=['POST'])
# @jwt_required()
# def renew_license(org_id):
#     user = _get_current_user()
#     err = _require_role(user, ['edit'])
#     if err:
#         return err

#     org = db.get_or_404(Organization, org_id)

#     now = datetime.now(timezone.utc).replace(tzinfo=None)
#     current_expiry = org.license_expiry_date or now
#     if current_expiry < now:
#         current_expiry = now

#     new_expiry = current_expiry + timedelta(days=365)
#     old_expiry = org.license_expiry_date

#     org.license_expiry_date = new_expiry
#     org.subscription_status = 'Active'
#     db.session.commit()

#     _log_action(user, 'LICENSE_RENEWED', org.id, 
#                 old_expiry.isoformat() if old_expiry else None, 
#                 new_expiry.isoformat())

#     return jsonify({
#         'status': 'success', 
#         'message': 'License renewed successfully',
#         'new_expiry': new_expiry.isoformat()
#     })
# [END DEAD CODE: renew_license]


@license_bp.route('/<int:org_id>/extend', methods=['POST'])
@jwt_required()
def extend_license(org_id):
    user = _get_current_user()
    err = _require_role(user, ['edit'])
    if err:
        return err

    org = db.get_or_404(Organization, org_id)
    data = request.get_json() or {}
    days = int(data.get('days', 30))
    
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    current_expiry = org.license_expiry_date or now
    new_expiry = current_expiry + timedelta(days=days)
    old_expiry = org.license_expiry_date
    
    org.license_expiry_date = new_expiry
    db.session.commit()
    
    _log_action(user, 'LICENSE_EXTENDED', org.id,
                old_expiry.isoformat() if old_expiry else None,
                new_expiry.isoformat())
                
    return jsonify({
        'status': 'success',
        'message': f'License extended by {days} days',
        'new_expiry': new_expiry.isoformat()
    })

@license_bp.route('/<int:org_id>/revoke', methods=['POST'])
@jwt_required()
def revoke_license(org_id):
    user = _get_current_user()
    err = _require_role(user, ['edit'])
    if err:
        return err

    org = db.get_or_404(Organization, org_id)
    old_status = org.subscription_status
    
    org.subscription_status = 'Revoked'
    db.session.commit()
    
    _log_action(user, 'LICENSE_REVOKED', org.id, old_status, 'Revoked')
    return jsonify({'status': 'success', 'message': 'License permanently revoked'})

@license_bp.route('/<int:org_id>/regenerate-key', methods=['POST'])
@jwt_required()
def regenerate_key(org_id):
    user = _get_current_user()
    err = _require_role(user, ['edit'])
    if err:
        return err

    org = db.get_or_404(Organization, org_id)
    old_key = org.license_number
    
    new_key = _generate_key()
    org.license_number = new_key
    db.session.commit()
    
    _log_action(user, 'LICENSE_KEY_REGENERATED', org.id, old_key, new_key)
    return jsonify({
        'status': 'success',
        'message': 'New license key issued successfully',
        'license_key': new_key
    })

@license_bp.route('/<int:org_id>/download', methods=['GET'])
@jwt_required()
def download_license_file(org_id):
    user = _get_current_user()
    err = _require_role(user, ['export'])
    if err:
        return err

    org = db.get_or_404(Organization, org_id)
    if not org.license_number:
        return jsonify({'error': 'Organization has no license key generated'}), 400

    payload = {
        "license_number": org.license_number,
        "organization_name": org.name,
        "organization_code": org.org_code or "QCMS-T",
        "subscription_plan": org.subscription_plan,
        "subscription_status": org.subscription_status,
        "max_users": org.max_users,
        "storage_limit_mb": org.storage_limit_mb,
        "enabled_modules": org.enabled_modules or [],
        "expiry_date": org.license_expiry_date.isoformat() if org.license_expiry_date else None,
        "issued_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    }
    
    payload_str = json.dumps(payload, sort_keys=True)
    signature = hmac.new(HMAC_SECRET.encode('utf-8'), payload_str.encode('utf-8'), hashlib.sha256).hexdigest()
    
    license_data = {
        "payload": payload,
        "signature": signature
    }
    
    raw_json = json.dumps(license_data, indent=2)
    b64_content = base64.b64encode(raw_json.encode('utf-8')).decode('utf-8')

    _log_action(user, 'LICENSE_DOWNLOADED', org.id, None, org.license_number)

    return jsonify({
        'status': 'success',
        'filename': f"license_{org.org_code or org.id}.lic",
        'content': b64_content
    })
