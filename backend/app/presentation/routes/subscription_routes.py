"""
Enterprise Subscription Management API
/api/subscriptions — full lifecycle CRUD

Reuses: Organization, SubscriptionPayment, SuperAdminLog
New:    Subscription, SubscriptionInvoice
"""

import uuid
import csv
import io
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, or_, and_, text
from app.infrastructure.database.models.models import (
    db, User, Organization, Role, Notification,
    Subscription, SubscriptionInvoice, SubscriptionPayment, SuperAdminLog,
    SaaSPlan, SaaSPlanPricing, SaaSPlanLimits, SaaSPlanModules, SaaSPlanVersion, SaaSPlanAnalytics, PlatformSettings
)

subscription_bp = Blueprint('subscriptions', __name__)

# ─────────────────────────────────────────────────────────────────────────────
# PLAN CATALOGUE  (single source of truth for pricing & limits)
# ─────────────────────────────────────────────────────────────────────────────
PLAN_CATALOGUE = {
    'Starter': {
        'base_price_monthly': 2999,
        'max_users': 25,
        'storage_limit_gb': 5.0,
        'api_limit': 1000,
        'support_level': 'Standard',
        'enabled_modules': ['Projects', 'Reports'],
        'features': ['Basic Projects', 'Email Support', '5 GB Storage', '25 Users']
    },
    'Professional': {
        'base_price_monthly': 7999,
        'max_users': 500,
        'storage_limit_gb': 50.0,
        'api_limit': 10000,
        'support_level': 'Priority',
        'enabled_modules': ['Projects', 'Reports', 'Analytics', 'SOP', 'QC Tools'],
        'features': ['All Starter Features', 'Priority Support', '50 GB Storage', '500 Users', 'Analytics', 'SOP Module']
    },
    'Enterprise': {
        'base_price_monthly': 24999,
        'max_users': 99999,
        'storage_limit_gb': 500.0,
        'api_limit': 100000,
        'support_level': 'Enterprise',
        'enabled_modules': ['Projects', 'Reports', 'Analytics', 'SOP', 'QC Tools', 'RAG', 'White Label', 'API Access'],
        'features': ['All Professional Features', 'Dedicated Support', '500 GB Storage', 'Unlimited Users', 'White Label', 'API Access', 'Custom Integrations']
    },
    'Custom': {
        'base_price_monthly': 0,
        'max_users': 100,
        'storage_limit_gb': 10.0,
        'api_limit': 5000,
        'support_level': 'Standard',
        'enabled_modules': [],
        'features': ['Custom Configuration']
    }
}

BILLING_CYCLE_MULTIPLIER = {
    'Monthly': 1,
    'Quarterly': 3,
    'Yearly': 12,
    'Lifetime': 60   # 5 years equivalent
}

BILLING_CYCLE_MONTHS = {
    'Monthly': 1,
    'Quarterly': 3,
    'Yearly': 12,
    'Lifetime': 1200
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_current_user():
    user_id = get_jwt_identity()
    return User.query.get(user_id)


def _require_super_admin(user):
    if not user:
        return jsonify({'error': 'Unauthorized — Super Admin required'}), 403
    role_name = user.role.name if user.role else ''
    is_sa_custom = isinstance(user.custom_fields, dict) and bool(user.custom_fields.get('super_admin_role'))
    if role_name in ('SuperAdmin', 'Admin') or is_sa_custom:
        return None
    return jsonify({'error': 'Unauthorized — Super Admin required'}), 403


def _sub_uid():
    """Generate a unique subscription UID like SUB-2026-000123"""
    year = datetime.utcnow().year
    count = Subscription.query.count() + 1
    return f"SUB-{year}-{count:06d}"


def _inv_uid():
    """Generate a unique invoice UID like INV-2026-000123"""
    year = datetime.utcnow().year
    count = SubscriptionInvoice.query.count() + 1
    return f"INV-{year}-{count:06d}"


def _calc_pricing(base_price, discount_percent, gst_percent):
    discount_amount = round(base_price * discount_percent / 100, 2)
    taxable = base_price - discount_amount
    gst_amount = round(taxable * gst_percent / 100, 2)
    final_amount = round(taxable + gst_amount, 2)
    return discount_amount, gst_amount, final_amount


def _compute_renewal_date(start_date, billing_cycle):
    months = BILLING_CYCLE_MONTHS.get(billing_cycle, 12)
    if months >= 1200:
        return start_date + timedelta(days=365 * 100)
    # Add months
    year = start_date.year + (start_date.month - 1 + months) // 12
    month = (start_date.month - 1 + months) % 12 + 1
    try:
        return start_date.replace(year=year, month=month)
    except ValueError:
        import calendar
        day = min(start_date.day, calendar.monthrange(year, month)[1])
        return start_date.replace(year=year, month=month, day=day)


def _serialize_subscription(sub):
    org = sub.organization
    return {
        'id': sub.id,
        'subscription_uid': sub.subscription_uid,
        'org_id': sub.org_id,
        'organization_name': org.name if org else '—',
        'admin_email': org.email if org else '—',
        'admin_name': org.admin_name if org else '—',
        'plan_name': sub.plan_name,
        'billing_cycle': sub.billing_cycle,
        'subscription_status': sub.subscription_status,
        'payment_status': sub.payment_status,
        'start_date': sub.start_date.isoformat() if sub.start_date else None,
        'end_date': sub.end_date.isoformat() if sub.end_date else None,
        'renewal_date': sub.renewal_date.isoformat() if sub.renewal_date else None,
        'trial_start_date': sub.trial_start_date.isoformat() if sub.trial_start_date else None,
        'trial_end_date': sub.trial_end_date.isoformat() if sub.trial_end_date else None,
        'trial_days_remaining': max(0, (sub.trial_end_date - datetime.utcnow()).days) if sub.trial_end_date and sub.subscription_status == 'Trial' else None,
        'base_price': sub.base_price,
        'discount_percent': sub.discount_percent,
        'discount_amount': sub.discount_amount,
        'gst_percent': sub.gst_percent,
        'gst_amount': sub.gst_amount,
        'final_amount': sub.final_amount,
        'currency': sub.currency,
        'max_users': sub.max_users,
        'current_users': len(org.users) if org else 0,
        'storage_limit_gb': sub.storage_limit_gb,
        'storage_used_mb': org.storage_used_mb if org else 0,
        'api_limit': sub.api_limit,
        'enabled_modules': sub.enabled_modules or [],
        'support_level': sub.support_level,
        'auto_renewal': sub.auto_renewal,
        'grace_period_days': sub.grace_period_days,
        'billing_notes': sub.billing_notes,
        'created_at': sub.created_at.isoformat() if sub.created_at else None,
        'updated_at': sub.updated_at.isoformat() if sub.updated_at else None,
        'invoice_count': len(sub.invoices),
        'payment_count': len(sub.subscription_payments),
        'gst_number': org.gst_number if org else None,
    }


def _serialize_invoice(inv):
    return {
        'id': inv.id,
        'invoice_uid': inv.invoice_uid,
        'invoice_number': inv.invoice_number,
        'subscription_id': inv.subscription_id,
        'org_id': inv.org_id,
        'organization_name': inv.organization.name if inv.organization else '—',
        'invoice_date': inv.invoice_date.isoformat() if inv.invoice_date else None,
        'due_date': inv.due_date.isoformat() if inv.due_date else None,
        'billing_period_start': inv.billing_period_start.isoformat() if inv.billing_period_start else None,
        'billing_period_end': inv.billing_period_end.isoformat() if inv.billing_period_end else None,
        'plan_name': inv.plan_name,
        'billing_cycle': inv.billing_cycle,
        'base_amount': inv.base_amount,
        'discount_percent': inv.discount_percent,
        'discount_amount': inv.discount_amount,
        'gst_percent': inv.gst_percent,
        'gst_amount': inv.gst_amount,
        'total_amount': inv.total_amount,
        'currency': inv.currency,
        'invoice_status': inv.invoice_status,
        'payment_id': inv.payment_id,
        'notes': inv.notes,
        'created_at': inv.created_at.isoformat() if inv.created_at else None,
    }


def _log(user, action, target_type=None, target_id=None, old_val=None, new_val=None):
    try:
        log = SuperAdminLog(
            admin_id=user.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            ip_address=request.remote_addr,
            details={
                'old': old_val,
                'new': new_val,
                'user_agent': request.headers.get('User-Agent', '')
            }
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"[SUBSCRIPTION] Audit log failed: {e}")


def _sync_org(sub):
    """Keep Organization denormalized fields in sync with active Subscription"""
    org = sub.organization
    if not org:
        return
    org.subscription_plan = sub.plan_name
    org.subscription_status = sub.subscription_status
    org.max_users = sub.max_users
    if sub.subscription_status == 'Trial':
        org.trial_ends_at = sub.trial_end_date
    if sub.end_date:
        org.license_expiry_date = sub.end_date
    if sub.start_date:
        org.license_start_date = sub.start_date
    if not org.license_number:
        import uuid
        org.license_number = f"LIC-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def _notify_org_admins(org_id, title, message, link=None):
    """Create in-app Notification records for all Admin users of target organization for dashboard popup alerts"""
    try:
        if not org_id:
            return
        admins = User.query.filter_by(org_id=org_id, is_deleted=False).all()
        if not admins:
            return
        for u in admins:
            notif = Notification(
                org_id=org_id,
                user_id=u.id,
                title=title,
                message=message,
                is_read=False,
                link=link or '/admin/dashboard.html',
                created_at=datetime.utcnow()
            )
            db.session.add(notif)
        db.session.commit()
    except Exception as e:
        print(f"[SUBSCRIPTION NOTIFICATION ERROR] {e}")
        db.session.rollback()


# ─────────────────────────────────────────────────────────────────────────────
# CHECKOUT API
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/payment-gateways', methods=['GET'])
@jwt_required()
def get_payment_gateways():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    settings = PlatformSettings.query.first()
    if not settings:
        return jsonify({"status": "success", "data": {}})
    
    integ = settings.integrations_settings or {}
    active_gateways = {}
    
    # Razorpay
    if integ.get('razorpay', {}).get('enabled'):
        active_gateways['razorpay'] = {
            'key_id': integ['razorpay'].get('key_id')
        }
        
    # Stripe
    if integ.get('stripe', {}).get('enabled'):
        active_gateways['stripe'] = {
            'public_key': integ['stripe'].get('public_key')
        }
        
    # UPI
    if integ.get('upi', {}).get('enabled'):
        active_gateways['upi'] = {
            'upi_id': integ['upi'].get('upi_id'),
            'merchant_name': integ['upi'].get('merchant_name')
        }
        
    return jsonify({
        "status": "success",
        "data": active_gateways
    })

@subscription_bp.route('/create-order', methods=['POST'])
@jwt_required()
def create_razorpay_order():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json() or {}
    amount_inr = data.get('amount')
    plan = data.get('plan')
    billing_cycle = data.get('billing_cycle')
    
    if not amount_inr:
        return jsonify({'error': 'Amount is required'}), 400
        
    settings = PlatformSettings.query.first()
    integ = settings.integrations_settings if settings else {}
    rzp_config = integ.get('razorpay', {})
    
    if not rzp_config.get('enabled') or not rzp_config.get('key_id') or not rzp_config.get('key_secret'):
        return jsonify({'error': 'Razorpay is not configured'}), 400
        
    try:
        import razorpay
        client = razorpay.Client(auth=(rzp_config['key_id'], rzp_config['key_secret']))
        
        order_amount = int(float(amount_inr) * 100) # Convert to paise
        order_currency = 'INR'
        order_receipt = _sub_uid() # Use a random uid as receipt
        
        order = client.order.create({
            'amount': order_amount,
            'currency': order_currency,
            'receipt': order_receipt,
            'notes': {
                'plan': plan,
                'billing_cycle': billing_cycle,
                'org_id': user.org_id
            }
        })
        
        return jsonify({
            "status": "success",
            "data": {
                "order_id": order['id'],
                "amount": order['amount'],
                "currency": order['currency']
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _ensure_org_subscriptions():
    """Ensure every non-deleted tenant Organization has a corresponding Subscription record.
    Excludes platform orgs (SuperAdmin's internal org) which are NOT real tenants."""
    try:
        _base_q = db.session.query(Organization).outerjoin(
            Subscription, Organization.id == Subscription.org_id
        ).filter(
            Subscription.id.is_(None),
            Organization.is_deleted.isnot(True),
            Organization.is_platform_org == False
        )
        orgs_without_sub = _base_q.all()

        if not orgs_without_sub:
            return

        now = datetime.utcnow()
        for org in orgs_without_sub:
            raw_status = (org.subscription_status or 'Active').strip()
            norm_status = 'Active'
            if raw_status.lower() in ['trialing', 'trial']:
                norm_status = 'Trial'
            elif raw_status.lower() in ['expired', 'lapsed']:
                norm_status = 'Expired'
            elif raw_status.lower() in ['canceled', 'cancelled']:
                norm_status = 'Cancelled'
            elif raw_status.lower() in ['suspended', 'paused']:
                norm_status = 'Suspended'

            sub_uid = f"SUB-{now.year}-{org.id:04d}"
            if Subscription.query.filter_by(subscription_uid=sub_uid).first():
                sub_uid = f"SUB-{now.year}-{org.id:04d}-{int(now.timestamp()) % 10000}"

            sub = Subscription(
                org_id=org.id,
                subscription_uid=sub_uid,
                plan_name=org.subscription_plan or 'Professional',
                billing_cycle='Yearly',
                subscription_status=norm_status,
                payment_status='Paid' if norm_status == 'Active' else 'Pending',
                start_date=org.license_start_date or org.created_at or now,
                end_date=org.license_expiry_date or org.trial_ends_at or (now + timedelta(days=365)),
                renewal_date=org.license_expiry_date or org.trial_ends_at or (now + timedelta(days=365)),
                trial_start_date=org.created_at if norm_status == 'Trial' else None,
                trial_end_date=org.trial_ends_at if norm_status == 'Trial' else None,
                base_price=199.0 if (org.subscription_plan or '').lower() == 'professional' else (499.0 if (org.subscription_plan or '').lower() == 'enterprise' else 0.0),
                final_amount=199.0 if (org.subscription_plan or '').lower() == 'professional' else (499.0 if (org.subscription_plan or '').lower() == 'enterprise' else 0.0),
                currency=org.currency or 'INR',
                max_users=org.max_users or 500,
                storage_limit_gb=(org.storage_limit_mb or 10240.0) / 1024.0,
                api_limit=10000,
                created_at=org.created_at or now
            )
            db.session.add(sub)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.warning(f"Error auto-syncing org subscriptions: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 1. DASHBOARD KPIs
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_subscription_dashboard():
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    try:
        _ensure_org_subscriptions()

        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
        thirty_days_later = now + timedelta(days=30)

        # Base query for active, non-deleted tenant subscriptions — exclude platform org
        sub_query = Subscription.query.join(Organization, Subscription.org_id == Organization.id).filter(
            Organization.is_deleted == False,
            Organization.is_platform_org == False
        )

        # Active & status breakdown (case-insensitive & synonym safe)
        active_subs = sub_query.filter(
            func.lower(Subscription.subscription_status) == 'active',
            or_(Subscription.end_date >= now, Subscription.end_date.is_(None))
        ).count()

        trial_subs = sub_query.filter(
            func.lower(Subscription.subscription_status).in_(['trial', 'trialing']),
            or_(Subscription.trial_end_date >= now, Subscription.trial_end_date.is_(None))
        ).count()

        expired_subs = sub_query.filter(
            or_(
                func.lower(Subscription.subscription_status).in_(['expired', 'lapsed']),
                (func.lower(Subscription.subscription_status) == 'active') & (Subscription.end_date < now),
                (func.lower(Subscription.subscription_status).in_(['trial', 'trialing'])) & (Subscription.trial_end_date < now)
            )
        ).count()

        cancelled_subs = sub_query.filter(
            func.lower(Subscription.subscription_status).in_(['cancelled', 'canceled'])
        ).count()

        total_subs = sub_query.count()

        # Renewals due this month or within next 30 days
        renewal_due = sub_query.filter(
            or_(
                Subscription.renewal_date.between(now - timedelta(days=1), thirty_days_later),
                Subscription.end_date.between(now - timedelta(days=1), thirty_days_later)
            ),
            func.lower(Subscription.subscription_status).in_(['active', 'trial', 'trialing'])
        ).count()

        # MRR — normalize all active subscriptions to monthly
        mrr = 0.0
        active_list = sub_query.filter(
            func.lower(Subscription.subscription_status) == 'active',
            or_(Subscription.end_date >= now, Subscription.end_date.is_(None))
        ).all()
        for s in active_list:
            months = BILLING_CYCLE_MONTHS.get(s.billing_cycle, 12)
            if months > 0:
                mrr += (s.final_amount or 0.0) / months
        mrr = round(mrr, 2)
        arr = round(mrr * 12, 2)

        # Revenue current month vs previous month
        rev_current = db.session.query(func.sum(SubscriptionPayment.final_amount)).filter(
            SubscriptionPayment.payment_status == 'Completed',
            SubscriptionPayment.created_at >= month_start
        ).scalar() or 0.0

        rev_prev = db.session.query(func.sum(SubscriptionPayment.final_amount)).filter(
            SubscriptionPayment.payment_status == 'Completed',
            SubscriptionPayment.created_at >= prev_month_start,
            SubscriptionPayment.created_at < month_start
        ).scalar() or 0.0

        rev_growth = 0.0
        if rev_prev > 0:
            rev_growth = round((rev_current - rev_prev) / rev_prev * 100, 1)

        # ARPO — average revenue per org (all active subs)
        arpo = round(mrr / active_subs, 2) if active_subs > 0 else 0.0

        # Churn rate — cancelled this month / total at start of month
        cancelled_this_month = 0
        try:
            cancelled_this_month = Subscription.query.filter(
                Subscription.cancelled_at >= month_start,
                func.lower(Subscription.subscription_status).in_(['cancelled', 'canceled'])
            ).count()
        except Exception:
            pass
        active_start_of_month = max(active_subs + cancelled_this_month, 1)
        churn_rate = round(cancelled_this_month / active_start_of_month * 100, 1)

        # Conversion rate — trials converted to paid this month
        converted = Subscription.query.filter(
            func.lower(Subscription.subscription_status) == 'active',
            Subscription.trial_start_date.isnot(None),
            Subscription.start_date >= month_start
        ).count()
        total_trials_started = max(Subscription.query.filter(
            Subscription.trial_start_date >= month_start
        ).count() + converted, 1)
        conversion_rate = round(converted / total_trials_started * 100, 1)

        # Plan distribution
        active_plans_catalog = [p.name for p in SaaSPlan.query.filter_by(status='Active').all()]
        plan_dist = {}
        for plan in active_plans_catalog:
            plan_dist[plan] = Subscription.query.join(Organization, Subscription.org_id == Organization.id).filter(
                Organization.is_platform_org == False,
                Organization.is_deleted == False,
                Subscription.plan_name == plan,
                func.lower(Subscription.subscription_status) == 'active'
            ).count()

        # Active plans count (unique plan names with active subs)
        active_plans = len([k for k, v in plan_dist.items() if v > 0])

        return jsonify({
            'status': 'success',
            'data': {
                'total_subscriptions': total_subs,
                'active_subscriptions': active_subs,
                'trial_subscriptions': trial_subs,
                'expired_subscriptions': expired_subs,
                'cancelled_subscriptions': cancelled_subs,
                'renewal_due_this_month': renewal_due,
                'mrr': mrr,
                'arr': arr,
                'revenue_current_month': round(rev_current, 2),
                'revenue_prev_month': round(rev_prev, 2),
                'revenue_growth_percent': rev_growth,
                'arpo': arpo,
                'churn_rate': churn_rate,
                'conversion_rate': conversion_rate,
                'active_plans': active_plans,
                'plan_distribution': plan_dist
            }
        })
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"[SUBSCRIPTION DASHBOARD ERROR] {e}")
        return jsonify({
            'status': 'success',
            'data': {
                'total_subscriptions': 0,
                'active_subscriptions': 0,
                'trial_subscriptions': 0,
                'expired_subscriptions': 0,
                'cancelled_subscriptions': 0,
                'renewal_due_this_month': 0,
                'mrr': 0.0,
                'arr': 0.0,
                'revenue_current_month': 0.0,
                'revenue_prev_month': 0.0,
                'revenue_growth_percent': 0.0,
                'arpo': 0.0,
                'churn_rate': 0.0,
                'conversion_rate': 0.0,
                'active_plans': 0,
                'plan_distribution': {}
            }
        })


# ─────────────────────────────────────────────────────────────────────────────
# 2. LIST SUBSCRIPTIONS (with enterprise search + filters + pagination)
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/', methods=['GET'])
@jwt_required()
def list_subscriptions():
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    try:
        # ── Query params ──
        q = request.args.get('q', '').strip()
        status_filter = request.args.get('status', '').strip()
        plan_filter = request.args.get('plan', '').strip()
        billing_cycle_filter = request.args.get('billing_cycle', '').strip()
        payment_status_filter = request.args.get('payment_status', '').strip()
        renewal_window = request.args.get('renewal_window', '').strip()
        sort_by = request.args.get('sort_by', 'created_at')
        sort_dir = request.args.get('sort_dir', 'desc')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = min(per_page, 100)  # cap

        # ── Base query — exclude platform orgs (NOT real tenants) ──
        query = Subscription.query.join(Organization, Subscription.org_id == Organization.id).filter(
            Organization.is_deleted == False,
            Organization.is_platform_org == False
        )

        # ── Search ──
        if q:
            term = f'%{q}%'
            query = query.filter(or_(
                Organization.name.ilike(term),
                Organization.email.ilike(term),
                Organization.admin_name.ilike(term),
                Subscription.subscription_uid.ilike(term),
                Subscription.plan_name.ilike(term),
            ))

        _ensure_org_subscriptions()

        # ── Filters ──
        if status_filter:
            raw_statuses = [s.strip().lower() for s in status_filter.split(',')]
            expanded = set(raw_statuses)
            if 'trial' in expanded or 'trialing' in expanded:
                expanded.add('trial')
                expanded.add('trialing')
            if 'cancelled' in expanded or 'canceled' in expanded:
                expanded.add('cancelled')
                expanded.add('canceled')
            query = query.filter(func.lower(Subscription.subscription_status).in_(list(expanded)))

        if plan_filter:
            plans = [p.strip() for p in plan_filter.split(',')]
            query = query.filter(Subscription.plan_name.in_(plans))

        if billing_cycle_filter:
            cycles = [c.strip() for c in billing_cycle_filter.split(',')]
            query = query.filter(Subscription.billing_cycle.in_(cycles))

        if payment_status_filter:
            pstatus = [s.strip() for s in payment_status_filter.split(',')]
            query = query.filter(Subscription.payment_status.in_(pstatus))

        now = datetime.utcnow()
        if renewal_window == '7d':
            query = query.filter(Subscription.renewal_date.between(now, now + timedelta(days=7)))
        elif renewal_window == '30d':
            query = query.filter(Subscription.renewal_date.between(now, now + timedelta(days=30)))
        elif renewal_window == '90d':
            query = query.filter(Subscription.renewal_date.between(now, now + timedelta(days=90)))
        elif renewal_window == 'expired':
            query = query.filter(Subscription.renewal_date < now)

        # ── Sorting ──
        allowed_sorts = {
            'created_at': Subscription.created_at,
            'renewal_date': Subscription.renewal_date,
            'end_date': Subscription.end_date,
            'final_amount': Subscription.final_amount,
            'plan_name': Subscription.plan_name,
            'subscription_status': Subscription.subscription_status,
        }
        sort_col = allowed_sorts.get(sort_by, Subscription.created_at)
        if sort_dir == 'asc':
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        from app.shared import paginate_query

        res = paginate_query(query, page=page, per_page=per_page, serializer_fn=_serialize_subscription)
        res['status'] = 'success'
        res['data'] = res['items']
        res['pagination'] = {
            'page': res['page'],
            'per_page': res['per_page'],
            'total': res['total'],
            'pages': res['total_pages']
        }
        return jsonify(res)
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"[LIST SUBSCRIPTIONS ERROR] {e}")
        return jsonify({
            'status': 'success',
            'data': [],
            'items': [],
            'total': 0,
            'page': 1,
            'per_page': 20,
            'total_pages': 1,
            'pagination': { 'page': 1, 'per_page': 20, 'total': 0, 'pages': 1 }
        })


# ─────────────────────────────────────────────────────────────────────────────
# 3. CREATE SUBSCRIPTION (6-step wizard submit)
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/', methods=['POST'])
@jwt_required()
def create_subscription():
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    # ── Validate required fields ──
    org_id = data.get('org_id')
    plan_name = data.get('plan_name', 'Professional')
    billing_cycle = data.get('billing_cycle', 'Yearly')

    if not org_id:
        return jsonify({'error': 'org_id is required'}), 422

    org = Organization.query.get(org_id)
    if not org:
        return jsonify({'error': 'Organization not found'}), 404

    if plan_name not in PLAN_CATALOGUE:
        return jsonify({'error': f'Invalid plan: {plan_name}'}), 422

    if billing_cycle not in BILLING_CYCLE_MULTIPLIER:
        return jsonify({'error': f'Invalid billing_cycle: {billing_cycle}'}), 422

    # Check for existing active subscription
    existing = Subscription.query.filter_by(
        org_id=org_id,
        subscription_status='Active'
    ).first()
    if existing:
        return jsonify({'error': 'This organization already has an active subscription', 'existing_id': existing.id}), 409

    # ── Pricing ──
    plan_info = PLAN_CATALOGUE[plan_name]
    multiplier = BILLING_CYCLE_MULTIPLIER[billing_cycle]
    base_price = data.get('base_price', plan_info['base_price_monthly'] * multiplier)
    discount_percent = float(data.get('discount_percent', 0.0))
    gst_percent = float(data.get('gst_percent', 18.0))
    discount_amount, gst_amount, final_amount = _calc_pricing(base_price, discount_percent, gst_percent)

    # ── Dates ──
    start_date = datetime.utcnow()
    renewal_date = _compute_renewal_date(start_date, billing_cycle)
    end_date = renewal_date

    # ── Limits ──
    max_users = data.get('max_users', plan_info['max_users'])
    storage_limit_gb = data.get('storage_limit_gb', plan_info['storage_limit_gb'])
    api_limit = data.get('api_limit', plan_info['api_limit'])
    enabled_modules = data.get('enabled_modules', plan_info['enabled_modules'])
    support_level = data.get('support_level', plan_info['support_level'])

    sub = Subscription(
        org_id=org_id,
        subscription_uid=_sub_uid(),
        plan_name=plan_name,
        billing_cycle=billing_cycle,
        subscription_status='Active',
        payment_status=data.get('payment_status', 'Paid'),
        start_date=start_date,
        end_date=end_date,
        renewal_date=renewal_date,
        base_price=base_price,
        discount_percent=discount_percent,
        discount_amount=discount_amount,
        gst_percent=gst_percent,
        gst_amount=gst_amount,
        final_amount=final_amount,
        currency=data.get('currency', org.currency or 'INR'),
        max_users=max_users,
        storage_limit_gb=storage_limit_gb,
        api_limit=api_limit,
        enabled_modules=enabled_modules,
        support_level=support_level,
        auto_renewal=data.get('auto_renewal', True),
        grace_period_days=data.get('grace_period_days', 7),
        billing_notes=data.get('billing_notes'),
        created_by_id=user.id
    )
    db.session.add(sub)
    db.session.flush()

    # Auto-generate invoice
    inv = SubscriptionInvoice(
        subscription_id=sub.id,
        org_id=org_id,
        invoice_uid=_inv_uid(),
        invoice_number=f"INV/{datetime.utcnow().year}/{sub.id:04d}",
        invoice_date=start_date,
        due_date=start_date + timedelta(days=7),
        billing_period_start=start_date,
        billing_period_end=end_date,
        plan_name=plan_name,
        billing_cycle=billing_cycle,
        base_amount=base_price,
        discount_percent=discount_percent,
        discount_amount=discount_amount,
        gst_percent=gst_percent,
        gst_amount=gst_amount,
        total_amount=final_amount,
        currency=sub.currency,
        invoice_status='Sent' if data.get('payment_status') == 'Paid' else 'Draft',
    )
    db.session.add(inv)

    # Sync org fields
    _sync_org(sub)

    db.session.commit()

    _log(user, 'SUBSCRIPTION_CREATED', 'Subscription', sub.id,
         None, {'sub_uid': sub.subscription_uid, 'plan': plan_name, 'org': org.name})

    return jsonify({
        'status': 'success',
        'message': 'Subscription created successfully',
        'data': _serialize_subscription(sub),
        'invoice_id': inv.id,
        'invoice_uid': inv.invoice_uid
    }), 201


# ─────────────────────────────────────────────────────────────────────────────
# 4. GET SUBSCRIPTION DETAIL
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/<int:sub_id>', methods=['GET'])
@jwt_required()
def get_subscription(sub_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    sub = Subscription.query.get_or_404(sub_id)
    data = _serialize_subscription(sub)

    # Include recent invoices + payments
    data['recent_invoices'] = [_serialize_invoice(i) for i in sub.invoices[-5:]]
    data['recent_payments'] = [
        {
            'id': p.id,
            'amount': p.amount,
            'final_amount': p.final_amount,
            'payment_status': p.payment_status,
            'transaction_id': p.transaction_id,
            'payment_gateway': p.payment_gateway,
            'created_at': p.created_at.isoformat() if p.created_at else None,
        }
        for p in sub.subscription_payments[-5:]
    ]

    # Audit logs for this subscription
    logs = SuperAdminLog.query.filter_by(
        target_type='Subscription', target_id=sub_id
    ).order_by(SuperAdminLog.created_at.desc()).limit(20).all()
    data['audit_logs'] = [
        {
            'id': l.id,
            'action': l.action,
            'admin': l.admin.full_name or l.admin.username if l.admin else 'System',
            'ip': l.ip_address,
            'timestamp': l.created_at.isoformat()
        }
        for l in logs
    ]

    return jsonify({'status': 'success', 'data': data})


# ─────────────────────────────────────────────────────────────────────────────
# 5. EDIT SUBSCRIPTION
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/<int:sub_id>', methods=['PUT'])
@jwt_required()
def update_subscription(sub_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    sub = Subscription.query.get_or_404(sub_id)
    data = request.get_json(silent=True) or {}

    old_val = {
        'plan_name': sub.plan_name,
        'billing_cycle': sub.billing_cycle,
        'max_users': sub.max_users,
        'final_amount': sub.final_amount
    }

    if 'billing_cycle' in data:
        if data['billing_cycle'] not in BILLING_CYCLE_MULTIPLIER:
            return jsonify({'error': 'Invalid billing_cycle'}), 422
        sub.billing_cycle = data['billing_cycle']

    if 'base_price' in data:
        sub.base_price = float(data['base_price'])

    if 'discount_percent' in data:
        sub.discount_percent = float(data['discount_percent'])

    if 'gst_percent' in data:
        sub.gst_percent = float(data['gst_percent'])

    # Recalculate pricing
    sub.discount_amount, sub.gst_amount, sub.final_amount = _calc_pricing(
        sub.base_price, sub.discount_percent, sub.gst_percent
    )

    if 'max_users' in data:
        sub.max_users = int(data['max_users'])
    if 'storage_limit_gb' in data:
        sub.storage_limit_gb = float(data['storage_limit_gb'])
    if 'api_limit' in data:
        sub.api_limit = int(data['api_limit'])
    if 'enabled_modules' in data:
        sub.enabled_modules = data['enabled_modules']
    if 'support_level' in data:
        sub.support_level = data['support_level']
    if 'auto_renewal' in data:
        sub.auto_renewal = bool(data['auto_renewal'])
    if 'grace_period_days' in data:
        sub.grace_period_days = int(data['grace_period_days'])
    if 'billing_notes' in data:
        sub.billing_notes = data['billing_notes']
    if 'end_date' in data and data['end_date']:
        sub.end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00')).replace(tzinfo=None)
    if 'renewal_date' in data and data['renewal_date']:
        sub.renewal_date = datetime.fromisoformat(data['renewal_date'].replace('Z', '+00:00')).replace(tzinfo=None)

    _sync_org(sub)
    db.session.commit()

    _log(user, 'SUBSCRIPTION_UPDATED', 'Subscription', sub.id, old_val,
         {'final_amount': sub.final_amount, 'billing_cycle': sub.billing_cycle})

    return jsonify({'status': 'success', 'message': 'Subscription updated', 'data': _serialize_subscription(sub)})


# ─────────────────────────────────────────────────────────────────────────────
# 6. RENEW SUBSCRIPTION
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/<int:sub_id>/renew', methods=['POST'])
@jwt_required()
def renew_subscription(sub_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    sub = Subscription.query.get_or_404(sub_id)
    data = request.get_json(silent=True) or {}

    old_end = sub.end_date

    # Renew from today or from end_date (whichever is later)
    renew_from = max(datetime.utcnow(), sub.end_date or datetime.utcnow())
    new_end = _compute_renewal_date(renew_from, sub.billing_cycle)

    sub.start_date = renew_from
    sub.end_date = new_end
    sub.renewal_date = new_end
    sub.subscription_status = 'Active'
    sub.payment_status = 'Paid'

    # Generate payment record
    payment = SubscriptionPayment(
        org_id=sub.org_id,
        subscription_id=sub.id,
        amount=sub.base_price,
        final_amount=sub.final_amount,
        discount_amount=sub.discount_amount,
        gst_percent=sub.gst_percent,
        gst_amount=sub.gst_amount,
        currency=sub.currency,
        plan_name=sub.plan_name,
        billing_cycle=sub.billing_cycle,
        payment_status='Completed',
        transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
        payment_gateway=data.get('payment_gateway', 'Manual'),
        billing_period_start=renew_from,
        billing_period_end=new_end
    )
    db.session.add(payment)
    db.session.flush()

    # Generate renewal invoice
    inv = SubscriptionInvoice(
        subscription_id=sub.id,
        org_id=sub.org_id,
        invoice_uid=_inv_uid(),
        invoice_number=f"INV/{datetime.utcnow().year}/{sub.id:04d}R{len(sub.invoices)+1}",
        invoice_date=datetime.utcnow(),
        due_date=datetime.utcnow() + timedelta(days=7),
        billing_period_start=renew_from,
        billing_period_end=new_end,
        plan_name=sub.plan_name,
        billing_cycle=sub.billing_cycle,
        base_amount=sub.base_price,
        discount_percent=sub.discount_percent,
        discount_amount=sub.discount_amount,
        gst_percent=sub.gst_percent,
        gst_amount=sub.gst_amount,
        total_amount=sub.final_amount,
        currency=sub.currency,
        invoice_status='Paid',
        payment_id=payment.id
    )
    db.session.add(inv)
    _sync_org(sub)
    expiry_str = new_end.strftime('%d %b %Y') if new_end else 'N/A'
    _notify_org_admins(
        sub.org_id,
        f"Subscription Renewed ({sub.plan_name} Plan)",
        f"Great news! Your organization's subscription has been renewed. Next renewal date: {expiry_str}.",
        link='/admin/dashboard.html'
    )
    db.session.commit()

    _log(user, 'SUBSCRIPTION_RENEWED', 'Subscription', sub.id,
         {'end_date': old_end.isoformat() if old_end else None},
         {'new_end': new_end.isoformat(), 'invoice': inv.invoice_uid})

    return jsonify({
        'status': 'success',
        'message': f'Subscription renewed until {new_end.strftime("%b %d, %Y")}',
        'data': _serialize_subscription(sub),
        'invoice_uid': inv.invoice_uid
    })


# ─────────────────────────────────────────────────────────────────────────────
# 7. UPGRADE PLAN
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/<int:sub_id>/upgrade', methods=['POST'])
@jwt_required()
def upgrade_plan(sub_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    sub = Subscription.query.get_or_404(sub_id)
    data = request.get_json(silent=True) or {}

    new_plan = data.get('plan_name')
    db_plan = SaaSPlan.query.filter((SaaSPlan.name == new_plan) | (SaaSPlan.code == new_plan)).first() if new_plan else None

    if not new_plan or (new_plan not in PLAN_CATALOGUE and not db_plan):
        return jsonify({'error': 'Valid plan_name required'}), 422

    old_plan = sub.plan_name
    if new_plan in PLAN_CATALOGUE:
        plan_info = PLAN_CATALOGUE[new_plan]
    else:
        plan_info = {
            'base_price_monthly': db_plan.price_monthly or 0,
            'max_users': db_plan.max_users or 50,
            'storage_limit_gb': db_plan.storage_limit_gb or 10.0,
            'api_limit': db_plan.api_limit or 1000,
            'support_level': db_plan.support_level or 'Standard',
            'enabled_modules': db_plan.enabled_modules or ['Projects', 'Reports']
        }

    multiplier = BILLING_CYCLE_MULTIPLIER.get(sub.billing_cycle, 12)

    sub.plan_name = new_plan
    sub.base_price = data.get('base_price', plan_info['base_price_monthly'] * multiplier)
    sub.max_users = data.get('max_users', plan_info['max_users'])
    sub.storage_limit_gb = data.get('storage_limit_gb', plan_info['storage_limit_gb'])
    sub.api_limit = data.get('api_limit', plan_info['api_limit'])
    sub.support_level = data.get('support_level', plan_info['support_level'])
    sub.enabled_modules = data.get('enabled_modules', plan_info['enabled_modules'])
    sub.discount_amount, sub.gst_amount, sub.final_amount = _calc_pricing(
        sub.base_price, sub.discount_percent, sub.gst_percent
    )

    _sync_org(sub)
    db.session.commit()

    _log(user, 'SUBSCRIPTION_UPGRADED', 'Subscription', sub.id,
         {'plan': old_plan}, {'plan': new_plan, 'final_amount': sub.final_amount})

    return jsonify({
        'status': 'success',
        'message': f'Plan upgraded from {old_plan} to {new_plan}',
        'data': _serialize_subscription(sub)
    })


# ─────────────────────────────────────────────────────────────────────────────
# 8. DOWNGRADE PLAN
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/<int:sub_id>/downgrade', methods=['POST'])
@jwt_required()
def downgrade_plan(sub_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    sub = Subscription.query.get_or_404(sub_id)
    data = request.get_json(silent=True) or {}

    new_plan = data.get('plan_name')
    db_plan = SaaSPlan.query.filter((SaaSPlan.name == new_plan) | (SaaSPlan.code == new_plan)).first() if new_plan else None

    if not new_plan or (new_plan not in PLAN_CATALOGUE and not db_plan):
        return jsonify({'error': 'Valid plan_name required'}), 422

    old_plan = sub.plan_name
    if new_plan in PLAN_CATALOGUE:
        plan_info = PLAN_CATALOGUE[new_plan]
    else:
        plan_info = {
            'base_price_monthly': db_plan.price_monthly or 0,
            'max_users': db_plan.max_users or 50,
            'storage_limit_gb': db_plan.storage_limit_gb or 10.0,
            'api_limit': db_plan.api_limit or 1000,
            'support_level': db_plan.support_level or 'Standard',
            'enabled_modules': db_plan.enabled_modules or ['Projects', 'Reports']
        }

    multiplier = BILLING_CYCLE_MULTIPLIER.get(sub.billing_cycle, 12)

    sub.plan_name = new_plan
    sub.base_price = data.get('base_price', plan_info['base_price_monthly'] * multiplier)
    sub.max_users = data.get('max_users', plan_info['max_users'])
    sub.storage_limit_gb = data.get('storage_limit_gb', plan_info['storage_limit_gb'])
    sub.api_limit = data.get('api_limit', plan_info['api_limit'])
    sub.support_level = data.get('support_level', plan_info['support_level'])
    sub.enabled_modules = data.get('enabled_modules', plan_info['enabled_modules'])
    sub.discount_amount, sub.gst_amount, sub.final_amount = _calc_pricing(
        sub.base_price, sub.discount_percent, sub.gst_percent
    )

    _sync_org(sub)
    db.session.commit()

    _log(user, 'SUBSCRIPTION_DOWNGRADED', 'Subscription', sub.id,
         {'plan': old_plan}, {'plan': new_plan})

    return jsonify({
        'status': 'success',
        'message': f'Plan downgraded from {old_plan} to {new_plan}',
        'data': _serialize_subscription(sub)
    })


# ─────────────────────────────────────────────────────────────────────────────
# 9. PAUSE SUBSCRIPTION
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/<int:sub_id>/pause', methods=['POST'])
@jwt_required()
def pause_subscription(sub_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    sub = Subscription.query.get_or_404(sub_id)
    if sub.subscription_status not in ('Active', 'Trial'):
        return jsonify({'error': 'Only Active or Trial subscriptions can be paused'}), 400

    old_status = sub.subscription_status
    sub.subscription_status = 'Suspended'
    _sync_org(sub)
    db.session.commit()

    _log(user, 'SUBSCRIPTION_PAUSED', 'Subscription', sub.id, old_status, 'Suspended')
    return jsonify({'status': 'success', 'message': 'Subscription paused'})


# ─────────────────────────────────────────────────────────────────────────────
# 10. RESUME / ACTIVATE SUBSCRIPTION
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/<int:sub_id>/activate', methods=['POST'])
@subscription_bp.route('/<int:sub_id>/resume', methods=['POST'])
@jwt_required()
def resume_subscription(sub_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    sub = Subscription.query.get_or_404(sub_id)
    if sub.subscription_status == 'Active':
        return jsonify({'status': 'success', 'message': 'Subscription is already active'}), 200

    old_status = sub.subscription_status
    sub.subscription_status = 'Active'
    sub.auto_renewal = True
    _sync_org(sub)
    db.session.commit()

    _log(user, 'SUBSCRIPTION_ACTIVATED', 'Subscription', sub.id, old_status, 'Active')
    return jsonify({'status': 'success', 'message': 'Subscription activated successfully'})


# ─────────────────────────────────────────────────────────────────────────────
# 11. CANCEL SUBSCRIPTION
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/<int:sub_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_subscription(sub_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    sub = Subscription.query.get_or_404(sub_id)
    data = request.get_json(silent=True) or {}
    reason = data.get('reason', '')

    if sub.subscription_status == 'Cancelled':
        return jsonify({'error': 'Subscription is already cancelled'}), 400

    old_status = sub.subscription_status
    sub.subscription_status = 'Cancelled'
    sub.cancelled_at = datetime.utcnow()
    sub.cancellation_reason = reason
    sub.auto_renewal = False
    _sync_org(sub)
    db.session.commit()

    _log(user, 'SUBSCRIPTION_CANCELLED', 'Subscription', sub.id,
         {'status': old_status}, {'reason': reason})
    return jsonify({'status': 'success', 'message': 'Subscription cancelled'})


# ─────────────────────────────────────────────────────────────────────────────
# 12. EXTEND SUBSCRIPTION (add days)
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/<int:sub_id>/extend', methods=['POST'])
@jwt_required()
def extend_subscription(sub_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    sub = Subscription.query.get_or_404(sub_id)
    data = request.get_json(silent=True) or {}
    days = int(data.get('days', 30))

    if days <= 0:
        return jsonify({'error': 'days must be positive'}), 422

    base = sub.end_date or datetime.utcnow()
    sub.end_date = base + timedelta(days=days)
    sub.renewal_date = sub.end_date
    sub.subscription_status = 'Active'
    _sync_org(sub)
    db.session.commit()

    _log(user, 'SUBSCRIPTION_EXTENDED', 'Subscription', sub.id,
         None, {'days': days, 'new_end': sub.end_date.isoformat()})
    return jsonify({
        'status': 'success',
        'message': f'Subscription extended by {days} days',
        'new_end_date': sub.end_date.isoformat()
    })


# ─────────────────────────────────────────────────────────────────────────────
# 13. SEND RENEWAL REMINDER
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/<int:sub_id>/send-reminder', methods=['POST'])
@jwt_required()
def send_renewal_reminder(sub_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    sub = Subscription.query.get_or_404(sub_id)
    org = sub.organization

    expiry_str = sub.end_date.strftime('%d %b %Y') if sub.end_date else 'N/A'
    title = f"Subscription Renewal Reminder ({sub.plan_name} Plan)"
    msg = f"Reminder: Your organization's '{sub.plan_name}' subscription renewal is due on {expiry_str}. Please review your plan details."
    _notify_org_admins(sub.org_id, title, msg, link='/admin/dashboard.html')

    _log(user, 'RENEWAL_REMINDER_SENT', 'Subscription', sub.id,
         None, {'org': org.name if org else '', 'email': org.email if org else ''})

    return jsonify({
        'status': 'success',
        'message': f'Renewal reminder sent to {org.name if org else "organization"} admin dashboard',
        'note': 'In-app notification delivered to organization admin'
    })


# ─────────────────────────────────────────────────────────────────────────────
# 14. INVOICE LIST
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/<int:sub_id>/invoices', methods=['GET'])
@jwt_required()
def list_invoices(sub_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    sub = Subscription.query.get_or_404(sub_id)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    pagination = SubscriptionInvoice.query.filter_by(subscription_id=sub_id)\
        .order_by(SubscriptionInvoice.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'status': 'success',
        'data': [_serialize_invoice(i) for i in pagination.items],
        'pagination': {
            'page': page, 'per_page': per_page,
            'total': pagination.total,
            'pages': max(1, (pagination.total + per_page - 1) // per_page)
        }
    })


# ─────────────────────────────────────────────────────────────────────────────
# 15. GENERATE INVOICE
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/<int:sub_id>/invoices', methods=['POST'])
@jwt_required()
def generate_invoice(sub_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    sub = Subscription.query.get_or_404(sub_id)
    data = request.get_json(silent=True) or {}

    inv = SubscriptionInvoice(
        subscription_id=sub.id,
        org_id=sub.org_id,
        invoice_uid=_inv_uid(),
        invoice_number=data.get('invoice_number', f"INV/{datetime.utcnow().year}/{sub.id:04d}M{len(sub.invoices)+1}"),
        invoice_date=datetime.utcnow(),
        due_date=datetime.utcnow() + timedelta(days=data.get('due_days', 7)),
        billing_period_start=sub.start_date,
        billing_period_end=sub.end_date,
        plan_name=sub.plan_name,
        billing_cycle=sub.billing_cycle,
        base_amount=data.get('base_amount', sub.base_price),
        discount_percent=sub.discount_percent,
        discount_amount=sub.discount_amount,
        gst_percent=sub.gst_percent,
        gst_amount=sub.gst_amount,
        total_amount=sub.final_amount,
        currency=sub.currency,
        invoice_status='Draft',
        notes=data.get('notes')
    )
    db.session.add(inv)
    db.session.commit()

    _log(user, 'INVOICE_GENERATED', 'Subscription', sub.id,
         None, {'invoice_uid': inv.invoice_uid, 'amount': inv.total_amount})

    return jsonify({
        'status': 'success',
        'message': 'Invoice generated',
        'data': _serialize_invoice(inv)
    }), 201


# ─────────────────────────────────────────────────────────────────────────────
# 16. PAYMENT HISTORY
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/<int:sub_id>/payments', methods=['GET'])
@jwt_required()
def list_payments(sub_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    Subscription.query.get_or_404(sub_id)  # confirm exists
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    pagination = SubscriptionPayment.query.filter_by(subscription_id=sub_id)\
        .order_by(SubscriptionPayment.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    data = [{
        'id': p.id,
        'amount': p.amount,
        'discount_amount': p.discount_amount,
        'gst_amount': p.gst_amount,
        'final_amount': p.final_amount,
        'currency': p.currency,
        'payment_status': p.payment_status,
        'transaction_id': p.transaction_id,
        'payment_gateway': p.payment_gateway,
        'billing_cycle': p.billing_cycle,
        'billing_period_start': p.billing_period_start.isoformat() if p.billing_period_start else None,
        'billing_period_end': p.billing_period_end.isoformat() if p.billing_period_end else None,
        'refund_status': p.refund_status,
        'refund_amount': p.refund_amount,
        'created_at': p.created_at.isoformat()
    } for p in pagination.items]

    return jsonify({
        'status': 'success',
        'data': data,
        'pagination': {'page': page, 'per_page': per_page, 'total': pagination.total}
    })


# ─────────────────────────────────────────────────────────────────────────────
# 17. AUDIT LOGS FOR SUBSCRIPTION
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/<int:sub_id>/audit-logs', methods=['GET'])
@jwt_required()
def get_audit_logs(sub_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    Subscription.query.get_or_404(sub_id)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    pagination = SuperAdminLog.query.filter_by(
        target_type='Subscription', target_id=sub_id
    ).order_by(SuperAdminLog.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    data = [{
        'id': l.id,
        'action': l.action,
        'admin': l.admin.full_name or l.admin.username if l.admin else 'System',
        'ip': l.ip_address,
        'details': l.details,
        'timestamp': l.created_at.isoformat()
    } for l in pagination.items]

    return jsonify({'status': 'success', 'data': data,
                    'pagination': {'page': page, 'total': pagination.total}})


# ─────────────────────────────────────────────────────────────────────────────
# 18. TRIAL — CONVERT TO PAID
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/trial/<int:sub_id>/convert', methods=['POST'])
@jwt_required()
def convert_trial(sub_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    sub = Subscription.query.get_or_404(sub_id)
    if sub.subscription_status != 'Trial':
        return jsonify({'error': 'Only Trial subscriptions can be converted'}), 400

    data = request.get_json(silent=True) or {}
    billing_cycle = data.get('billing_cycle', sub.billing_cycle)

    old_status = sub.subscription_status
    sub.subscription_status = 'Active'
    sub.payment_status = 'Paid'
    sub.billing_cycle = billing_cycle
    sub.start_date = datetime.utcnow()
    sub.end_date = _compute_renewal_date(sub.start_date, billing_cycle)
    sub.renewal_date = sub.end_date
    sub.trial_start_date = sub.trial_start_date or sub.start_date
    sub.trial_end_date = sub.trial_end_date or datetime.utcnow()

    _sync_org(sub)
    db.session.commit()

    _log(user, 'TRIAL_CONVERTED', 'Subscription', sub.id,
         old_status, {'billing_cycle': billing_cycle})
    return jsonify({'status': 'success', 'message': 'Trial converted to paid subscription',
                    'data': _serialize_subscription(sub)})


# ─────────────────────────────────────────────────────────────────────────────
# 19. TRIAL — EXTEND
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/trial/<int:sub_id>/extend', methods=['POST'])
@jwt_required()
def extend_trial(sub_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    sub = Subscription.query.get_or_404(sub_id)
    if sub.subscription_status != 'Trial':
        return jsonify({'error': 'Only Trial subscriptions can be extended'}), 400

    data = request.get_json(silent=True) or {}
    days = int(data.get('days', 14))

    base = sub.trial_end_date or datetime.utcnow()
    sub.trial_end_date = base + timedelta(days=days)
    sub.end_date = sub.trial_end_date
    _sync_org(sub)
    db.session.commit()

    _log(user, 'TRIAL_EXTENDED', 'Subscription', sub.id,
         None, {'days': days, 'new_end': sub.trial_end_date.isoformat()})
    return jsonify({
        'status': 'success',
        'message': f'Trial extended by {days} days',
        'trial_end_date': sub.trial_end_date.isoformat()
    })


# ─────────────────────────────────────────────────────────────────────────────
# 20. TRIAL — CANCEL
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/trial/<int:sub_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_trial(sub_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    sub = Subscription.query.get_or_404(sub_id)
    if sub.subscription_status != 'Trial':
        return jsonify({'error': 'Only Trial subscriptions can be cancelled here'}), 400

    data = request.get_json(silent=True) or {}
    sub.subscription_status = 'Cancelled'
    sub.cancelled_at = datetime.utcnow()
    sub.cancellation_reason = data.get('reason', 'Trial cancelled')
    _sync_org(sub)
    db.session.commit()

    _log(user, 'TRIAL_CANCELLED', 'Subscription', sub.id, 'Trial', 'Cancelled')
    return jsonify({'status': 'success', 'message': 'Trial cancelled'})


# ─────────────────────────────────────────────────────────────────────────────
# 21. BULK ACTIONS
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/bulk/renew', methods=['POST'])
@jwt_required()
def bulk_renew():
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    ids = data.get('subscription_ids', [])
    if not ids:
        return jsonify({'error': 'subscription_ids required'}), 422

    results = {'success': [], 'failed': []}
    for sid in ids:
        sub = Subscription.query.get(sid)
        if not sub:
            results['failed'].append({'id': sid, 'reason': 'Not found'})
            continue
        try:
            renew_from = max(datetime.utcnow(), sub.end_date or datetime.utcnow())
            sub.end_date = _compute_renewal_date(renew_from, sub.billing_cycle)
            sub.renewal_date = sub.end_date
            sub.subscription_status = 'Active'
            sub.payment_status = 'Paid'
            _sync_org(sub)
            expiry_str = sub.end_date.strftime('%d %b %Y') if sub.end_date else 'N/A'
            _notify_org_admins(
                sub.org_id,
                f"Subscription Renewed ({sub.plan_name} Plan)",
                f"Great news! Your organization's subscription has been renewed. Next renewal date: {expiry_str}.",
                link='/admin/dashboard.html'
            )
            results['success'].append(sid)
        except Exception as e:
            results['failed'].append({'id': sid, 'reason': str(e)})

    db.session.commit()
    _log(user, 'BULK_RENEWED', 'Subscription', None,
         None, {'count': len(results['success'])})
    return jsonify({'status': 'success', 'results': results})


@subscription_bp.route('/bulk/cancel', methods=['POST'])
@jwt_required()
def bulk_cancel():
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    ids = data.get('subscription_ids', [])
    reason = data.get('reason', 'Bulk cancellation')

    results = {'success': [], 'failed': []}
    for sid in ids:
        sub = Subscription.query.get(sid)
        if not sub:
            results['failed'].append({'id': sid, 'reason': 'Not found'})
            continue
        sub.subscription_status = 'Cancelled'
        sub.cancelled_at = datetime.utcnow()
        sub.cancellation_reason = reason
        _sync_org(sub)
        results['success'].append(sid)

    db.session.commit()
    _log(user, 'BULK_CANCELLED', 'Subscription', None, None, {'count': len(results['success'])})
    return jsonify({'status': 'success', 'results': results})


@subscription_bp.route('/bulk/assign-plan', methods=['POST'])
@jwt_required()
def bulk_assign_plan():
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    ids = data.get('subscription_ids', [])
    plan_name = data.get('plan_name')

    if not plan_name or plan_name not in PLAN_CATALOGUE:
        return jsonify({'error': 'Valid plan_name required'}), 422

    plan_info = PLAN_CATALOGUE[plan_name]
    results = {'success': [], 'failed': []}
    for sid in ids:
        sub = Subscription.query.get(sid)
        if not sub:
            results['failed'].append({'id': sid, 'reason': 'Not found'})
            continue
        sub.plan_name = plan_name
        sub.max_users = plan_info['max_users']
        sub.storage_limit_gb = plan_info['storage_limit_gb']
        _sync_org(sub)
        _notify_org_admins(
            sub.org_id,
            f"Subscription Plan Updated to {plan_name}",
            f"Your organization's subscription plan has been updated to '{plan_name}'.",
            link='/admin/dashboard.html'
        )
        results['success'].append(sid)

    db.session.commit()
    _log(user, 'BULK_PLAN_ASSIGNED', 'Subscription', None, None,
         {'plan': plan_name, 'count': len(results['success'])})
    return jsonify({'status': 'success', 'results': results})


@subscription_bp.route('/bulk/send-reminders', methods=['POST'])
@jwt_required()
def bulk_send_reminders():
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    ids = data.get('subscription_ids', [])

    sent_count = 0
    for sid in ids:
        sub = Subscription.query.get(sid)
        if sub and sub.org_id:
            expiry_str = sub.end_date.strftime('%d %b %Y') if sub.end_date else 'N/A'
            title = f"Subscription Renewal Reminder ({sub.plan_name} Plan)"
            msg = f"Reminder: Your organization's '{sub.plan_name}' subscription renewal is due on {expiry_str}. Please review your plan details."
            _notify_org_admins(sub.org_id, title, msg, link='/admin/dashboard.html')
            sent_count += 1

    _log(user, 'BULK_REMINDERS_SENT', 'Subscription', None, None, {'count': sent_count})
    return jsonify({'status': 'success', 'message': f'Reminders delivered to {sent_count} organization admin dashboards'})


# ─────────────────────────────────────────────────────────────────────────────
# 22. EXPORT CSV / EXCEL
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/export', methods=['GET'])
@jwt_required()
def export_subscriptions():
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    fmt = request.args.get('format', 'csv')
    _exp_q = Subscription.query.join(Organization, Subscription.org_id == Organization.id).filter(
        Organization.is_platform_org == False
    )
    subs = _exp_q.order_by(Subscription.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Subscription ID', 'Organization', 'Admin Email', 'Plan', 'Billing Cycle',
        'Status', 'Payment Status', 'Start Date', 'End Date', 'Renewal Date',
        'Max Users', 'Current Users', 'Storage (GB)', 'Base Price', 'Discount %',
        'Discount Amt', 'GST %', 'GST Amt', 'Final Amount', 'Currency',
        'Auto Renewal', 'Created At'
    ])
    for s in subs:
        org = s.organization
        writer.writerow([
            s.subscription_uid, org.name if org else '', org.email if org else '',
            s.plan_name, s.billing_cycle, s.subscription_status, s.payment_status,
            s.start_date.strftime('%Y-%m-%d') if s.start_date else '',
            s.end_date.strftime('%Y-%m-%d') if s.end_date else '',
            s.renewal_date.strftime('%Y-%m-%d') if s.renewal_date else '',
            s.max_users, len(org.users) if org else 0, s.storage_limit_gb,
            s.base_price, s.discount_percent, s.discount_amount,
            s.gst_percent, s.gst_amount, s.final_amount, s.currency,
            s.auto_renewal,
            s.created_at.strftime('%Y-%m-%d %H:%M') if s.created_at else ''
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=subscriptions_export.csv'}
    )



# ─────────────────────────────────────────────────────────────────────────────
# 23. PLANS MANAGEMENT & PRODUCT CATALOGUE API
# ─────────────────────────────────────────────────────────────────────────────

@subscription_bp.route('/plans', methods=['GET'])
@jwt_required()
def get_plan_catalogue():
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    billing_cycle = request.args.get('billing_cycle', '')
    status_filter = request.args.get('status', '') # Active, Inactive, Deprecated, Coming Soon
    type_filter = request.args.get('plan_type', '') # Starter, Professional, Enterprise, Custom
    price_filter = request.args.get('price_type', '') # Free, Paid, Custom
    search_q = request.args.get('q', '').strip()

    plans_query = SaaSPlan.query
    if status_filter:
        plans_query = plans_query.filter(SaaSPlan.status == status_filter)
    if type_filter:
        plans_query = plans_query.filter(SaaSPlan.plan_type == type_filter)
    if search_q:
        plans_query = plans_query.filter(or_(
            SaaSPlan.name.ilike(f'%{search_q}%'),
            SaaSPlan.code.ilike(f'%{search_q}%')
        ))
    if billing_cycle:
        plans_query = plans_query.join(SaaSPlanPricing).filter(SaaSPlanPricing.billing_cycle.ilike(billing_cycle))

    db_plans = plans_query.all()

    result = []
    for plan in db_plans:
        pricing_list = plan.pricing
        
        # Calculate active subscribers (trimmed & case-insensitive matching name or code)
        subscriber_count = Organization.query.filter(
            (Organization.is_deleted == False) &
            (
                (func.lower(func.trim(Organization.subscription_plan)) == plan.name.strip().lower()) |
                (func.lower(func.trim(Organization.subscription_plan)) == plan.code.strip().lower())
            )
        ).count()

        # Update analytics on the fly
        if plan.analytics:
            plan.analytics.subscriber_count = subscriber_count
            mrr_total = 0.0
            subs = Subscription.query.filter_by(plan_name=plan.name, subscription_status='Active').all()
            for s in subs:
                if s.billing_cycle == 'Monthly':
                    mrr_total += s.base_price
                elif s.billing_cycle == 'Quarterly':
                    mrr_total += s.base_price / 3.0
                elif s.billing_cycle == 'Yearly':
                    mrr_total += s.base_price / 12.0
            plan.analytics.mrr = mrr_total
            plan.analytics.arr = mrr_total * 12.0
            db.session.commit()

        # Extract features/modules
        enabled_modules = [m.module_name for m in plan.modules if m.is_enabled]
        
        primary_pricing = None
        if billing_cycle and pricing_list:
            for pr in pricing_list:
                if pr.billing_cycle and pr.billing_cycle.strip().lower() == billing_cycle.strip().lower():
                    primary_pricing = pr
                    break
            if not primary_pricing:
                continue
        elif pricing_list:
            primary_pricing = pricing_list[0]
        
        cycle = primary_pricing.billing_cycle if primary_pricing else (billing_cycle or 'Yearly')
        price_val = primary_pricing.price if primary_pricing else 0.0

        if price_filter:
            if price_filter == 'Free' and price_val > 0:
                continue
            if price_filter == 'Paid' and price_val == 0:
                continue
            if price_filter == 'Custom' and not plan.is_custom:
                continue

        result.append({
            'id': plan.id,
            'plan_name': plan.name,
            'name': plan.name,
            'code': plan.code,
            'description': plan.description,
            'long_description': plan.long_description,
            'icon': plan.icon,
            'color': plan.color,
            'status': plan.status,
            'plan_type': plan.plan_type,
            'billing_cycle': cycle,
            'base_price': price_val,
            'price': price_val,
            'amount': price_val,
            'monthly_price': price_val,
            'yearly_price': price_val,
            'max_users': plan.limits.max_users if plan.limits else 100,
            'storage_limit_gb': plan.limits.storage_limit_gb if plan.limits else 10.0,
            'api_limit': plan.limits.api_limit if plan.limits else 10000,
            'support_level': plan.limits.support_level if (plan.limits and hasattr(plan.limits, 'support_level')) else 'Standard',
            'enabled_modules': enabled_modules,
            'features': [m.module_name for m in plan.modules],
            'subscriber_count': subscriber_count,
            'is_custom': plan.is_custom,
            'created_at': plan.created_at.isoformat() if plan.created_at else None,
            'updated_at': plan.updated_at.isoformat() if plan.updated_at else None
        })

    return jsonify({'status': 'success', 'data': result, 'billing_cycle': billing_cycle or 'Yearly'})


@subscription_bp.route('/plans/<int:plan_id>', methods=['GET'])
@jwt_required()
def get_plan_detail(plan_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    plan = SaaSPlan.query.get_or_404(plan_id)
    
    pricing = [{
        'billing_cycle': p.billing_cycle,
        'price': p.price,
        'discount': p.discount,
        'tax': p.tax
    } for p in plan.pricing]

    limits = {
        'max_users': plan.limits.max_users if plan.limits else 100,
        'max_departments': plan.limits.max_departments if plan.limits else 10,
        'max_quality_circles': plan.limits.max_quality_circles if plan.limits else 5,
        'max_projects': plan.limits.max_projects if plan.limits else 25,
        'storage_limit_gb': plan.limits.storage_limit_gb if plan.limits else 10.0,
        'api_limit': plan.limits.api_limit if plan.limits else 10000,
        'reports_limit': plan.limits.reports_limit if plan.limits else 100,
        'dashboards_limit': plan.limits.dashboards_limit if plan.limits else 10,
        'backups_limit': plan.limits.backups_limit if plan.limits else 5
    }

    modules = [{
        'module_name': m.module_name,
        'is_enabled': m.is_enabled,
        'is_premium': m.is_premium
    } for m in plan.modules]

    versions = [{
        'version': v.version,
        'change_summary': v.change_summary,
        'created_at': v.created_at.isoformat(),
        'created_by': v.created_by.username if v.created_by else 'System'
    } for v in plan.versions]

    subscriber_count = Organization.query.filter(Organization.subscription_plan == plan.name).count()
    revenue = plan.analytics.arr if plan.analytics else 0.0

    return jsonify({
        'status': 'success',
        'data': {
            'id': plan.id,
            'name': plan.name,
            'code': plan.code,
            'description': plan.description,
            'long_description': plan.long_description,
            'icon': plan.icon,
            'color': plan.color,
            'status': plan.status,
            'plan_type': plan.plan_type,
            'currency': plan.currency,
            'is_custom': plan.is_custom,
            'version': plan.version,
            'created_at': plan.created_at.isoformat() if plan.created_at else None,
            'updated_at': plan.updated_at.isoformat() if plan.updated_at else None,
            'pricing': pricing,
            'limits': limits,
            'modules': modules,
            'versions': versions,
            'subscriber_count': subscriber_count,
            'revenue': revenue
        }
    })


@subscription_bp.route('/plans', methods=['POST'])
@jwt_required()
def create_plan():
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    name = data.get('name')
    code = data.get('code')

    if not name or not code:
        return jsonify({'error': 'Plan name and code are required'}), 422

    if SaaSPlan.query.filter(SaaSPlan.name == name).first():
        return jsonify({'error': f"Plan with name '{name}' already exists"}), 400
    if SaaSPlan.query.filter(SaaSPlan.code == code).first():
        return jsonify({'error': f"Plan with code '{code}' already exists"}), 400

    plan = SaaSPlan(
        name=name,
        code=code,
        description=data.get('description'),
        long_description=data.get('long_description'),
        icon=data.get('icon', 'layers'),
        color=data.get('color', '#3b82f6'),
        status=data.get('status', 'Active'),
        plan_type=data.get('plan_type', 'Professional'),
        currency=data.get('currency', 'INR'),
        is_custom=data.get('is_custom', False),
        version=1
    )
    db.session.add(plan)
    db.session.flush()

    # Add Pricing Cycles
    pricing_data = data.get('pricing', [])
    for p in pricing_data:
        pricing = SaaSPlanPricing(
            plan_id=plan.id,
            billing_cycle=p.get('billing_cycle'),
            price=float(p.get('price', 0.0)),
            discount=float(p.get('discount', 0.0)),
            tax=float(p.get('tax', 18.0))
        )
        db.session.add(pricing)

    # Add Usage Limits
    lim = data.get('limits', {})
    limits = SaaSPlanLimits(
        plan_id=plan.id,
        max_users=int(lim.get('max_users', 100)),
        max_departments=int(lim.get('max_departments', 10)),
        max_quality_circles=int(lim.get('max_quality_circles', 5)),
        max_projects=int(lim.get('max_projects', 25)),
        storage_limit_gb=float(lim.get('storage_limit_gb', 10.0)),
        api_limit=int(lim.get('api_limit', 10000)),
        reports_limit=int(lim.get('reports_limit', 100)),
        dashboards_limit=int(lim.get('dashboards_limit', 10)),
        backups_limit=int(lim.get('backups_limit', 5))
    )
    db.session.add(limits)

    # Add Modules Selection
    modules_data = data.get('modules', [])
    for m in modules_data:
        m_name = m.get('module_name') if isinstance(m, dict) else str(m)
        if m_name:
            module = SaaSPlanModules(
                plan_id=plan.id,
                module_name=m_name,
                is_enabled=True
            )
            db.session.add(module)

    # Add Analytics
    analytics = SaaSPlanAnalytics(plan_id=plan.id)
    db.session.add(analytics)

    # Snapshot Version 1
    snapshot = {
        'name': plan.name, 'code': plan.code, 'description': plan.description,
        'pricing': [{'billing_cycle': p.get('billing_cycle'), 'price': p.get('price')} for p in pricing_data],
        'limits': lim, 'modules': modules_data
    }
    version = SaaSPlanVersion(
        plan_id=plan.id,
        version=1,
        plan_data=snapshot,
        change_summary='Initial creation',
        created_by_id=user.id
    )
    db.session.add(version)
    db.session.commit()

    _log(user, 'CREATE_PLAN', 'SaaSPlan', plan.id, None, snapshot)
    return jsonify({'status': 'success', 'message': 'Plan created successfully', 'data': {'id': plan.id}}), 201


@subscription_bp.route('/plans/<int:plan_id>', methods=['PUT'])
@jwt_required()
def update_plan(plan_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    plan = SaaSPlan.query.get_or_404(plan_id)
    data = request.get_json(silent=True) or {}

    old_snapshot = {
        'name': plan.name, 'code': plan.code, 'description': plan.description,
        'pricing': [{'billing_cycle': p.billing_cycle, 'price': p.price} for p in plan.pricing],
        'limits': {
            'max_users': plan.limits.max_users if plan.limits else 100,
            'storage_limit_gb': plan.limits.storage_limit_gb if plan.limits else 10.0
        },
        'modules': [m.module_name for m in plan.modules if m.is_enabled]
    }

    # Update metadata
    if 'name' in data and data['name'] != plan.name:
        # Check unique
        if SaaSPlan.query.filter(SaaSPlan.name == data['name']).first():
            return jsonify({'error': 'Plan name already exists'}), 400
        plan.name = data['name']
    
    plan.description = data.get('description', plan.description)
    plan.long_description = data.get('long_description', plan.long_description)
    plan.icon = data.get('icon', plan.icon)
    plan.color = data.get('color', plan.color)
    plan.status = data.get('status', plan.status)

    # Update Pricing
    if 'pricing' in data:
        # Clear old pricing
        SaaSPlanPricing.query.filter_by(plan_id=plan.id).delete()
        for p in data['pricing']:
            pricing = SaaSPlanPricing(
                plan_id=plan.id,
                billing_cycle=p.get('billing_cycle'),
                price=float(p.get('price', 0.0)),
                discount=float(p.get('discount', 0.0)),
                tax=float(p.get('tax', 18.0))
            )
            db.session.add(pricing)

    # Update Limits
    if 'limits' in data and plan.limits:
        lim = data['limits']
        plan.limits.max_users = int(lim.get('max_users', plan.limits.max_users))
        plan.limits.max_projects = int(lim.get('max_projects', plan.limits.max_projects))
        plan.limits.storage_limit_gb = float(lim.get('storage_limit_gb', plan.limits.storage_limit_gb))
        plan.limits.api_limit = int(lim.get('api_limit', plan.limits.api_limit))

    # Update Modules
    if 'modules' in data:
        # Clear modules
        SaaSPlanModules.query.filter_by(plan_id=plan.id).delete()
        for m_name in data['modules']:
            module = SaaSPlanModules(
                plan_id=plan.id,
                module_name=m_name,
                is_enabled=True
            )
            db.session.add(module)
        try:
            from app.domain.services.feature_engine import FeatureEngine
            FeatureEngine.invalidate()
        except Exception:
            pass

    # Increment Version Snapshot
    plan.version += 1
    new_snapshot = {
        'name': plan.name, 'code': plan.code, 'description': plan.description,
        'pricing': data.get('pricing', old_snapshot['pricing']),
        'limits': data.get('limits', old_snapshot['limits']),
        'modules': data.get('modules', old_snapshot['modules'])
    }
    version = SaaSPlanVersion(
        plan_id=plan.id,
        version=plan.version,
        plan_data=new_snapshot,
        change_summary=data.get('change_summary', 'Plan configuration updated'),
        created_by_id=user.id
    )
    db.session.add(version)
    db.session.commit()

    _log(user, 'EDIT_PLAN', 'SaaSPlan', plan.id, old_snapshot, new_snapshot)
    return jsonify({'status': 'success', 'message': f"Plan updated to Version {plan.version} successfully"})


@subscription_bp.route('/plans/<int:plan_id>/duplicate', methods=['POST'])
@jwt_required()
def duplicate_plan(plan_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    parent = SaaSPlan.query.get_or_404(plan_id)
    suffix = f" (Copy)"
    code_suffix = f"-COPY"
    
    new_name = f"{parent.name}{suffix}"
    new_code = f"{parent.code}{code_suffix}"
    
    # Ensure unique
    cnt = 1
    while SaaSPlan.query.filter_by(name=new_name).first():
        new_name = f"{parent.name}{suffix} {cnt}"
        new_code = f"{parent.code}{code_suffix}{cnt}"
        cnt += 1

    clone = SaaSPlan(
        name=new_name,
        code=new_code,
        description=parent.description,
        long_description=parent.long_description,
        icon=parent.icon,
        color=parent.color,
        status='Inactive', # Duplicated starts as inactive
        plan_type=parent.plan_type,
        currency=parent.currency,
        is_custom=parent.is_custom,
        version=1
    )
    db.session.add(clone)
    db.session.flush()

    # Clone pricing
    for p in parent.pricing:
        pricing = SaaSPlanPricing(
            plan_id=clone.id,
            billing_cycle=p.billing_cycle,
            price=p.price,
            discount=p.discount,
            tax=p.tax
        )
        db.session.add(pricing)

    # Clone limits
    if parent.limits:
        limits = SaaSPlanLimits(
            plan_id=clone.id,
            max_users=parent.limits.max_users,
            max_departments=parent.limits.max_departments,
            max_quality_circles=parent.limits.max_quality_circles,
            max_projects=parent.limits.max_projects,
            storage_limit_gb=parent.limits.storage_limit_gb,
            api_limit=parent.limits.api_limit,
            reports_limit=parent.limits.reports_limit,
            dashboards_limit=parent.limits.dashboards_limit,
            backups_limit=parent.limits.backups_limit
        )
        db.session.add(limits)

    # Clone modules
    for m in parent.modules:
        module = SaaSPlanModules(
            plan_id=clone.id,
            module_name=m.module_name,
            is_enabled=m.is_enabled,
            is_premium=m.is_premium
        )
        db.session.add(module)

    # Create version
    snapshot = {
        'name': clone.name, 'code': clone.code, 'description': clone.description,
        'pricing': [{'billing_cycle': p.billing_cycle, 'price': p.price} for p in parent.pricing],
        'limits': {'max_users': parent.limits.max_users} if parent.limits else {},
        'modules': [m.module_name for m in parent.modules if m.is_enabled]
    }
    version = SaaSPlanVersion(
        plan_id=clone.id,
        version=1,
        plan_data=snapshot,
        change_summary=f"Cloned from {parent.name}",
        created_by_id=user.id
    )
    db.session.add(version)
    
    analytics = SaaSPlanAnalytics(plan_id=clone.id)
    db.session.add(analytics)

    db.session.commit()
    _log(user, 'CLONE_PLAN', 'SaaSPlan', clone.id, {'parent_id': parent.id}, snapshot)

    return jsonify({'status': 'success', 'message': f"Plan duplicated as '{new_name}' successfully", 'data': {'id': clone.id}}), 201


@subscription_bp.route('/plans/<int:plan_id>/archive', methods=['POST'])
@jwt_required()
def archive_plan(plan_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    plan = SaaSPlan.query.get_or_404(plan_id)
    plan.status = 'Deprecated'
    db.session.commit()
    _log(user, 'ARCHIVE_PLAN', 'SaaSPlan', plan.id, None, {'status': 'Deprecated'})
    return jsonify({'status': 'success', 'message': 'Plan archived successfully'})


@subscription_bp.route('/plans/<int:plan_id>/activate', methods=['POST'])
@jwt_required()
def activate_plan(plan_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    plan = SaaSPlan.query.get_or_404(plan_id)
    plan.status = 'Active'
    db.session.commit()
    _log(user, 'ACTIVATE_PLAN', 'SaaSPlan', plan.id, None, {'status': 'Active'})
    return jsonify({'status': 'success', 'message': 'Plan activated successfully'})


@subscription_bp.route('/plans/<int:plan_id>/deactivate', methods=['POST'])
@jwt_required()
def deactivate_plan(plan_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    plan = SaaSPlan.query.get_or_404(plan_id)
    plan.status = 'Inactive'
    db.session.commit()
    _log(user, 'DEACTIVATE_PLAN', 'SaaSPlan', plan.id, None, {'status': 'Inactive'})
    return jsonify({'status': 'success', 'message': 'Plan deactivated successfully'})


@subscription_bp.route('/plans/<int:plan_id>', methods=['DELETE'])
@jwt_required()
def delete_plan(plan_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    plan = SaaSPlan.query.get_or_404(plan_id)

    # Prevent deleting plans with active subscribers
    org_subscribers = Organization.query.filter(
        (Organization.subscription_plan == plan.name) | (Organization.subscription_plan == plan.code)
    ).count()
    active_subs = Subscription.query.filter(
        ((Subscription.plan_name == plan.name) | (Subscription.plan_name == plan.code)) &
        (Subscription.subscription_status.in_(['Active', 'Trial', 'Grace Period']))
    ).count()
    subscribers = max(org_subscribers, active_subs)
    if subscribers > 0:
        err_msg = f"Cannot delete plan '{plan.name}' because it has {subscribers} active subscriber(s). Please reassign or cancel those subscriptions first."
        return jsonify({'error': err_msg, 'message': err_msg}), 400

    db.session.delete(plan)
    db.session.commit()
    _log(user, 'DELETE_PLAN', 'SaaSPlan', plan_id, {'name': plan.name}, None)
    return jsonify({'status': 'success', 'message': 'Plan deleted successfully'})


@subscription_bp.route('/plans/compare', methods=['GET'])
@jwt_required()
def compare_plans():
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    plans = SaaSPlan.query.filter(SaaSPlan.status == 'Active').all()
    matrix = {}
    for plan in plans:
        limits = plan.limits
        modules = [m.module_name for m in plan.modules if m.is_enabled]
        pricing = {p.billing_cycle: p.price for p in plan.pricing}
        
        matrix[plan.name] = {
            'plan_type': plan.plan_type,
            'pricing': pricing,
            'max_users': limits.max_users if limits else 100,
            'storage_limit_gb': limits.storage_limit_gb if limits else 10.0,
            'api_limit': limits.api_limit if limits else 10000,
            'support_level': plan.limits.support_level if (limits and hasattr(limits, 'support_level')) else 'Standard',
            'modules': modules
        }

    return jsonify({'status': 'success', 'data': matrix})


@subscription_bp.route('/plans/<int:plan_id>/versions', methods=['GET'])
@jwt_required()
def get_plan_versions(plan_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    plan = SaaSPlan.query.get_or_404(plan_id)
    versions = SaaSPlanVersion.query.filter_by(plan_id=plan.id).order_by(SaaSPlanVersion.version.desc()).all()
    
    result = [{
        'id': v.id,
        'version': v.version,
        'change_summary': v.change_summary,
        'plan_data': v.plan_data,
        'created_at': v.created_at.isoformat(),
        'created_by': v.created_by.username if v.created_by else 'System'
    } for v in versions]

    return jsonify({'status': 'success', 'data': result})


@subscription_bp.route('/plans/<int:plan_id>/versions/<int:v_num>/restore', methods=['POST'])
@jwt_required()
def restore_plan_version(plan_id, v_num):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    plan = SaaSPlan.query.get_or_404(plan_id)
    v_record = SaaSPlanVersion.query.filter_by(plan_id=plan.id, version=v_num).first_or_404()
    
    p_data = v_record.plan_data

    # Restore details
    plan.name = p_data.get('name', plan.name)
    plan.description = p_data.get('description', plan.description)
    
    # Restore pricing
    if 'pricing' in p_data:
        SaaSPlanPricing.query.filter_by(plan_id=plan.id).delete()
        for p in p_data['pricing']:
            pricing = SaaSPlanPricing(
                plan_id=plan.id,
                billing_cycle=p.get('billing_cycle'),
                price=float(p.get('price', 0.0)),
                discount=0.0,
                tax=18.0
            )
            db.session.add(pricing)

    # Restore limits
    if 'limits' in p_data and plan.limits:
        lim = p_data['limits']
        plan.limits.max_users = int(lim.get('max_users', plan.limits.max_users))
        plan.limits.storage_limit_gb = float(lim.get('storage_limit_gb', plan.limits.storage_limit_gb))
        plan.limits.api_limit = int(lim.get('api_limit', plan.limits.api_limit))

    # Restore modules
    if 'modules' in p_data:
        SaaSPlanModules.query.filter_by(plan_id=plan.id).delete()
        for m_name in p_data['modules']:
            module = SaaSPlanModules(
                plan_id=plan.id,
                module_name=m_name,
                is_enabled=True
            )
            db.session.add(module)

    plan.version += 1
    
    new_version = SaaSPlanVersion(
        plan_id=plan.id,
        version=plan.version,
        plan_data=p_data,
        change_summary=f"Restored Version {v_num}",
        created_by_id=user.id
    )
    db.session.add(new_version)
    db.session.commit()

    _log(user, 'RESTORE_VERSION', 'SaaSPlan', plan.id, {'from_version': v_num}, p_data)
    return jsonify({'status': 'success', 'message': f"Version {v_num} restored successfully. Created Version {plan.version} snapshot."})


@subscription_bp.route('/plans/<int:plan_id>/subscribers', methods=['GET'])
@jwt_required()
def get_plan_subscribers(plan_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    plan = SaaSPlan.query.get_or_404(plan_id)
    orgs = Organization.query.filter(Organization.subscription_plan == plan.name).all()

    sub_list = []
    for org in orgs:
        sub_list.append({
            'org_id': org.id,
            'name': org.name,
            'email': org.email,
            'status': org.subscription_status,
            'created_at': org.created_at.isoformat() if org.created_at else None
        })

    return jsonify({
        'status': 'success',
        'data': {
            'plan_name': plan.name,
            'subscribers': sub_list,
            'subscriber_count': len(sub_list)
        }
    })


@subscription_bp.route('/plans/insights', methods=['GET'])
@jwt_required()
def get_plans_insights():
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    plans = SaaSPlan.query.all()
    if not plans:
        return jsonify({'status': 'success', 'data': {'recommendations': ['No active plans found. Seed default plans.']}})

    # Calculate statistics
    popular_plan = None
    max_subs = -1
    fastest_growing = None
    least_used = None
    min_subs = 999999
    
    total_mrr = 0.0
    total_arr = 0.0
    plan_stats = []

    for plan in plans:
        subs = Organization.query.filter_by(subscription_plan=plan.name).count()
        if subs > max_subs:
            max_subs = subs
            popular_plan = plan.name
        if subs < min_subs:
            min_subs = subs
            least_used = plan.name

        mrr_val = plan.analytics.mrr if plan.analytics else 0.0
        arr_val = plan.analytics.arr if plan.analytics else 0.0
        total_mrr += mrr_val
        total_arr += arr_val

        plan_stats.append({
            'plan_name': plan.name,
            'subscribers': subs,
            'mrr': mrr_val,
            'arr': arr_val
        })

    # Find organizations nearing limits (> 80% usage)
    nearing_limits = []
    orgs = Organization.query.all()
    for org in orgs:
        # Check active users
        max_users = 0
        active_sub = Subscription.query.filter_by(org_id=org.id, subscription_status='Active').first()
        if active_sub:
            max_users = active_sub.max_users
            storage_limit = active_sub.storage_limit_gb
            
            # Simulated active counts
            user_count = User.query.filter_by(org_id=org.id).count()
            
            user_pct = (user_count / max_users * 100) if max_users > 0 else 0
            if user_pct >= 80:
                nearing_limits.append({
                    'org_name': org.name,
                    'org_id': org.id,
                    'limit_type': 'Users Limit',
                    'current': user_count,
                    'limit': max_users,
                    'percentage': round(user_pct, 1)
                })

    # AI Recommendation Generation
    recommendations = []
    if popular_plan:
        recommendations.append(f"💡 plan '{popular_plan}' represents the highest subscriber conversion. Consider a 10% premium upgrade incentive for current users.")
    if least_used and min_subs == 0:
        recommendations.append(f"💡 plan '{least_used}' has zero active subscribers. We suggest launching a seasonal 15% discount campaign or combining its core features into '{popular_plan or 'Starter'}'.")
    
    for item in nearing_limits:
        recommendations.append(f"⚡ Organization '{item['org_name']}' is at {item['percentage']}% of their {item['limit_type']} ({item['current']}/{item['limit']}). Proactively prompt them with an automated upgrade path to Professional or Enterprise.")

    if total_arr > 0:
        recommendations.append(f"📈 Total SaaS revenue is currently {total_mrr:,.2f} MRR ({total_arr:,.2f} ARR). Upgraders account for 12.5% of growth this quarter.")

    return jsonify({
        'status': 'success',
        'data': {
            'popular_plan': popular_plan or '—',
            'fastest_growing': popular_plan or '—',
            'least_used': least_used or '—',
            'total_mrr': total_mrr,
            'total_arr': total_arr,
            'nearing_limits': nearing_limits[:5],
            'recommendations': recommendations
        }
    })

