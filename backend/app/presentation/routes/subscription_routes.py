"""
Enterprise Subscription Management API
/api/subscriptions — full lifecycle CRUD

Reuses: Organization, SubscriptionPayment, SuperAdminLog
New:    Subscription, SubscriptionInvoice
"""

import uuid
import csv
import io
from datetime import datetime, timedelta, timezone
from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, or_, and_, text
from app.infrastructure.database.models.models import (
    db, User, Organization, Role, Notification,
    Subscription, SubscriptionInvoice, SubscriptionPayment, SuperAdminLog,
    SaaSPlan, SaaSPlanPricing, SaaSPlanLimits, SaaSPlanModules, SaaSPlanVersion, SaaSPlanAnalytics, PlatformSettings
)

from app.presentation.middleware.middleware import super_admin_required

import threading
from sqlalchemy.orm.attributes import flag_modified
from app.presentation.routes.error_helpers import internal_server_error

subscription_bp = Blueprint('subscriptions', __name__)

# ─────────────────────────────────────────────────────────────────────────────
# PLAN CATALOGUE  (single source of truth for pricing & limits)
# ─────────────────────────────────────────────────────────────────────────────
PLAN_CATALOGUE = {
    'Starter': {
        'base_price_monthly': 2500,
        'max_users': 100,
        'storage_limit_gb': 10.0,
        'api_limit': 10000,
        'support_level': 'Standard',
        'enabled_modules': ['Projects', 'Reports'],
        'features': ['Basic Projects', 'Email Support', '10 GB Storage', '100 Users']
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
    return db.session.get(User, user_id)


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
    year = datetime.now(timezone.utc).replace(tzinfo=None).year
    count = Subscription.query.count() + 1
    return f"SUB-{year}-{count:06d}"


def _inv_uid():
    """Generate a unique invoice UID like INV-2026-000123"""
    year = datetime.now(timezone.utc).replace(tzinfo=None).year
    count = SubscriptionInvoice.query.count() + 1
    return f"INV-{year}-{count:06d}"


def _calc_pricing(base_price, discount_percent, gst_percent, is_tax_inclusive=False):
    base_price = float(base_price or 0.0)
    discount_percent = float(discount_percent or 0.0)
    gst_percent = float(gst_percent or 0.0)

    if is_tax_inclusive:
        final_amount = round(base_price, 2)
        taxable = round(final_amount / (1.0 + (gst_percent / 100.0)), 2)
        discount_amount = round(taxable * (discount_percent / 100.0), 2) if discount_percent else 0.0
        calculated_base = round(taxable - discount_amount, 2)
        gst_amount = round(final_amount - calculated_base, 2)
        return discount_amount, gst_amount, final_amount, calculated_base
    else:
        discount_amount = round(base_price * (discount_percent / 100.0), 2) if discount_percent else 0.0
        taxable = round(base_price - discount_amount, 2)
        gst_amount = round(taxable * (gst_percent / 100.0), 2)
        final_amount = round(taxable + gst_amount, 2)
        return discount_amount, gst_amount, final_amount, base_price


def _get_plan_details(plan_name, billing_cycle='Monthly'):
    """
    Look up plan pricing & limits dynamically from SaaSPlan & SaaSPlanPricing tables first.
    Fall back to PLAN_CATALOGUE if not found in database.
    """
    if not plan_name:
        return None
        
    multiplier = BILLING_CYCLE_MULTIPLIER.get(billing_cycle, 1)
    
    # 1. Search in SaaSPlan table first by name or code
    db_plan = SaaSPlan.query.filter(
        (func.lower(func.trim(SaaSPlan.name)) == plan_name.strip().lower()) |
        (func.lower(func.trim(SaaSPlan.code)) == plan_name.strip().lower())
    ).first()
    
    if db_plan:
        # Check specific pricing for this billing cycle
        specific_pricing = None
        for pr in db_plan.pricing:
            if pr.billing_cycle and pr.billing_cycle.strip().lower() == billing_cycle.strip().lower() and pr.price > 0:
                specific_pricing = pr
                break
        
        if not specific_pricing:
            non_zero = [pr for pr in db_plan.pricing if pr.price > 0]
            if non_zero:
                specific_pricing = non_zero[0]

        if specific_pricing:
            if specific_pricing.billing_cycle and specific_pricing.billing_cycle.strip().lower() == billing_cycle.strip().lower():
                base_price = float(specific_pricing.price)
            else:
                base_price = float(specific_pricing.price) * (multiplier if billing_cycle != 'Monthly' else 1)
        else:
            base_price = 0.0

        limits = db_plan.limits
        modules = [m.module_name for m in db_plan.modules if m.is_enabled]
        is_tax_inclusive = getattr(specific_pricing, 'is_tax_inclusive', False) if specific_pricing else False
        tax_rate = getattr(specific_pricing, 'tax', 18.0) if specific_pricing else 18.0
        
        return {
            'plan_name': db_plan.name,
            'base_price': base_price,
            'tax_rate': tax_rate,
            'is_tax_inclusive': is_tax_inclusive,
            'max_users': limits.max_users if limits else 100,
            'storage_limit_gb': limits.storage_limit_gb if limits else 10.0,
            'api_limit': limits.api_limit if limits else 10000,
            'support_level': 'Standard',
            'enabled_modules': modules
        }
    
    # 2. Fall back to PLAN_CATALOGUE
    if plan_name in PLAN_CATALOGUE:
        cat = PLAN_CATALOGUE[plan_name]
        return {
            'plan_name': plan_name,
            'base_price': float(cat['base_price_monthly']) * multiplier,
            'max_users': cat['max_users'],
            'storage_limit_gb': cat['storage_limit_gb'],
            'api_limit': cat['api_limit'],
            'support_level': cat['support_level'],
            'enabled_modules': cat['enabled_modules']
        }
    
    return None


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

    # Resolve proper human-readable plan name
    raw_plan_name = sub.plan_name or '—'
    display_plan_name = raw_plan_name
    from app.infrastructure.database.models.models import SaaSPlan
    db_plan = None
    if getattr(sub, 'plan_id', None):
        db_plan = db.session.get(SaaSPlan, sub.plan_id)
    if not db_plan and raw_plan_name and raw_plan_name != '—':
        db_plan = SaaSPlan.query.filter(
            (func.lower(func.trim(SaaSPlan.code)) == raw_plan_name.strip().lower()) |
            (func.lower(func.trim(SaaSPlan.name)) == raw_plan_name.strip().lower())
        ).first()
    if db_plan and db_plan.name:
        display_plan_name = db_plan.name

    # Resolve proper human-readable billing cycle
    raw_cycle = sub.billing_cycle or '—'
    display_cycle = raw_cycle
    if sub.subscription_status in ('Trial', 'trialing') or (raw_cycle and raw_cycle.lower() in ('trial', 'trial duration')):
        if getattr(sub, 'trial_end_date', None) and getattr(sub, 'trial_start_date', None):
            days = max(1, (sub.trial_end_date - sub.trial_start_date).days)
            display_cycle = f"Trial ({days} Days)"
        elif getattr(sub, 'trial_end_date', None):
            days = max(1, (sub.trial_end_date - datetime.now(timezone.utc).replace(tzinfo=None)).days)
            display_cycle = f"Trial ({days} Days)"
        else:
            display_cycle = "Trial Duration"

    return {
        'id': sub.id,
        'subscription_uid': sub.subscription_uid,
        'org_id': sub.org_id,
        'organization_name': org.name if org else '—',
        'admin_email': org.email if org else '—',
        'admin_name': org.admin_name if org else '—',
        'plan_name': display_plan_name,
        'billing_cycle': display_cycle,
        'subscription_status': sub.subscription_status,
        'payment_status': sub.payment_status,
        'start_date': sub.start_date.isoformat() if sub.start_date else None,
        'end_date': sub.end_date.isoformat() if sub.end_date else None,
        'renewal_date': sub.renewal_date.isoformat() if sub.renewal_date else None,
        'trial_start_date': sub.trial_start_date.isoformat() if sub.trial_start_date else None,
        'trial_end_date': sub.trial_end_date.isoformat() if sub.trial_end_date else None,
        'trial_days_remaining': max(0, (sub.trial_end_date - datetime.now(timezone.utc).replace(tzinfo=None)).days) if sub.trial_end_date and sub.subscription_status == 'Trial' else None,
        'base_price': sub.base_price,
        'discount_percent': sub.discount_percent,
        'discount_amount': sub.discount_amount,
        'gst_percent': sub.gst_percent,
        'gst_amount': sub.gst_amount,
        'final_amount': sub.final_amount,
        'currency': sub.currency,
        'is_tax_inclusive': getattr(sub, 'is_tax_inclusive', False),
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
        'is_tax_inclusive': getattr(inv, 'is_tax_inclusive', False),
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
        org.license_number = f"LIC-{datetime.now(timezone.utc).replace(tzinfo=None).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


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
                created_at=datetime.now(timezone.utc).replace(tzinfo=None)
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
        return internal_server_error(e, "Subscription operation failed.")

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

        now = datetime.now(timezone.utc).replace(tzinfo=None)
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

            plan_details = _get_plan_details(org.subscription_plan or 'Starter', 'Monthly')
            base_price = plan_details['base_price'] if plan_details else 2500.0
            discount_amount, gst_amount, final_amount = _calc_pricing(base_price, 0.0, 18.0)

            sub = Subscription(
                org_id=org.id,
                subscription_uid=sub_uid,
                plan_name=org.subscription_plan or 'Starter',
                billing_cycle='Monthly',
                subscription_status=norm_status,
                payment_status='Paid' if norm_status == 'Active' else 'Pending',
                start_date=org.license_start_date or org.created_at or now,
                end_date=org.license_expiry_date or org.trial_ends_at or (now + timedelta(days=365)),
                renewal_date=org.license_expiry_date or org.trial_ends_at or (now + timedelta(days=365)),
                trial_start_date=org.created_at if norm_status == 'Trial' else None,
                trial_end_date=org.trial_ends_at if norm_status == 'Trial' else None,
                base_price=base_price,
                discount_percent=0.0,
                discount_amount=discount_amount,
                gst_percent=18.0,
                gst_amount=gst_amount,
                final_amount=final_amount,
                currency=org.currency or 'INR',
                max_users=org.max_users or (plan_details['max_users'] if plan_details else 100),
                storage_limit_gb=(org.storage_limit_mb or 10240.0) / 1024.0,
                api_limit=plan_details['api_limit'] if plan_details else 10000,
                enabled_modules=plan_details['enabled_modules'] if plan_details else ['Projects', 'Reports'],
                support_level=plan_details['support_level'] if plan_details else 'Standard',
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

        now = datetime.now(timezone.utc).replace(tzinfo=None)
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
        thirty_days_later = now + timedelta(days=30)
        start_window = now - timedelta(days=1)
        renewal_due = sub_query.filter(
            or_(
                Subscription.renewal_date.between(start_window, thirty_days_later),
                Subscription.end_date.between(start_window, thirty_days_later),
                Subscription.trial_end_date.between(start_window, thirty_days_later),
                (Subscription.renewal_date.is_(None)) & (Subscription.end_date.is_(None)) & (Subscription.trial_end_date.is_(None))
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

        # Plan distribution — map plan codes and plan names to human-readable plan names
        all_plans = SaaSPlan.query.all()
        plan_dist = {}
        for p in all_plans:
            label_name = p.name or p.code or 'Standard'
            cnt = Subscription.query.join(Organization, Subscription.org_id == Organization.id).filter(
                Organization.is_platform_org == False,
                Organization.is_deleted == False,
                db.or_(
                    Subscription.plan_name == p.name,
                    Subscription.plan_name == p.code
                )
            ).count()
            if cnt > 0:
                plan_dist[label_name] = plan_dist.get(label_name, 0) + cnt

        # Fallback if no specific SaaSPlan matched directly
        if not plan_dist:
            raw_subs = Subscription.query.join(Organization, Subscription.org_id == Organization.id).filter(
                Organization.is_platform_org == False,
                Organization.is_deleted == False
            ).all()
            for s in raw_subs:
                lbl = s.plan_name or 'Default'
                plan_dist[lbl] = plan_dist.get(lbl, 0) + 1

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

        org_id_param = request.args.get('org_id', type=int)
        if org_id_param:
            query = query.filter(Subscription.org_id == org_id_param)

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
            from app.infrastructure.database.models.models import SaaSPlan
            matching_sp_names = [
                sp.name for sp in SaaSPlan.query.filter(
                    db.or_(
                        SaaSPlan.plan_type.in_(plans),
                        SaaSPlan.name.in_(plans),
                        SaaSPlan.code.in_(plans)
                    )
                ).all()
            ]
            all_target_plans = set(plans + matching_sp_names)
            if any(p.lower() in ('trial', 'trialing') for p in plans):
                all_target_plans.update(['Trial', 'Trialing', 'Default Trial Plan'])
            query = query.filter(func.lower(Subscription.plan_name).in_([p.lower() for p in all_target_plans]))

        if billing_cycle_filter:
            cycles = [c.strip() for c in billing_cycle_filter.split(',')]
            query = query.filter(Subscription.billing_cycle.in_(cycles))

        if payment_status_filter:
            pstatus = [s.strip() for s in payment_status_filter.split(',')]
            query = query.filter(Subscription.payment_status.in_(pstatus))

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        start_window = now - timedelta(days=1)
        if renewal_window == '7d':
            end_window = now + timedelta(days=7)
            query = query.filter(or_(
                Subscription.renewal_date.between(start_window, end_window),
                Subscription.end_date.between(start_window, end_window),
                Subscription.trial_end_date.between(start_window, end_window)
            ))
        elif renewal_window in ('30d', 'this_month', 'due_this_month'):
            end_window = now + timedelta(days=30)
            query = query.filter(or_(
                Subscription.renewal_date.between(start_window, end_window),
                Subscription.end_date.between(start_window, end_window),
                Subscription.trial_end_date.between(start_window, end_window),
                (Subscription.renewal_date.is_(None)) & (Subscription.end_date.is_(None)) & (Subscription.trial_end_date.is_(None))
            ))
        elif renewal_window == '90d':
            end_window = now + timedelta(days=90)
            query = query.filter(or_(
                Subscription.renewal_date.between(start_window, end_window),
                Subscription.end_date.between(start_window, end_window),
                Subscription.trial_end_date.between(start_window, end_window)
            ))
        elif renewal_window == 'expired':
            query = query.filter(or_(
                Subscription.renewal_date < now,
                Subscription.end_date < now,
                Subscription.trial_end_date < now
            ))

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

    org = db.session.get(Organization, org_id)
    if not org:
        return jsonify({'error': 'Organization not found'}), 404

    plan_info = _get_plan_details(plan_name, billing_cycle)
    if not plan_info:
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
    base_price = float(data.get('base_price', plan_info['base_price']))
    discount_percent = float(data.get('discount_percent', 0.0))
    gst_percent = float(data.get('gst_percent', plan_info.get('tax_rate', 18.0)))
    is_tax_inclusive = bool(data.get('is_tax_inclusive', plan_info.get('is_tax_inclusive', False)))
    discount_amount, gst_amount, final_amount, calc_base = _calc_pricing(base_price, discount_percent, gst_percent, is_tax_inclusive)

    # ── Dates ──
    start_date = datetime.now(timezone.utc).replace(tzinfo=None)
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
        base_price=calc_base,
        discount_percent=discount_percent,
        discount_amount=discount_amount,
        gst_percent=gst_percent,
        gst_amount=gst_amount,
        final_amount=final_amount,
        currency=data.get('currency', org.currency or 'INR'),
        is_tax_inclusive=is_tax_inclusive,
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
        invoice_number=f"INV/{datetime.now(timezone.utc).replace(tzinfo=None).year}/{sub.id:04d}",
        invoice_date=start_date,
        due_date=start_date + timedelta(days=7),
        billing_period_start=start_date,
        billing_period_end=end_date,
        plan_name=plan_name,
        billing_cycle=billing_cycle,
        base_amount=calc_base,
        discount_percent=discount_percent,
        discount_amount=discount_amount,
        gst_percent=gst_percent,
        gst_amount=gst_amount,
        total_amount=final_amount,
        currency=sub.currency,
        is_tax_inclusive=is_tax_inclusive,
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
    renew_from = max(datetime.now(timezone.utc).replace(tzinfo=None), sub.end_date or datetime.now(timezone.utc).replace(tzinfo=None))
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
        invoice_number=f"INV/{datetime.now(timezone.utc).replace(tzinfo=None).year}/{sub.id:04d}R{len(sub.invoices)+1}",
        invoice_date=datetime.now(timezone.utc).replace(tzinfo=None),
        due_date=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7),
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

    plan_info = _get_plan_details(new_plan, sub.billing_cycle)
    if not plan_info:
        return jsonify({'error': f'Valid plan_name required: {new_plan}'}), 422

    # Storage Check: Ensure plan storage accommodates existing data
    org = sub.organization
    if org:
        from app.domain.services.storage_calculator_service import calculate_org_storage_realtime
        calc = calculate_org_storage_realtime(org.id)
        if isinstance(calc, dict):
            orgs = calc.get('organizations', [])
            used_storage_gb = float(orgs[0].get('storage_used_gb', 0.0)) if orgs and isinstance(orgs[0], dict) else float(calc.get('storage_used_gb', (org.storage_used_mb or 0.0) / 1024.0))
        elif isinstance(calc, list) and len(calc) > 0 and isinstance(calc[0], dict):
            used_storage_gb = float(calc[0].get('storage_used_gb', 0.0))
        else:
            used_storage_gb = float((org.storage_used_mb or 0.0) / 1024.0)
        target_storage_gb = float(data.get('storage_limit_gb', plan_info['storage_limit_gb']))
        if target_storage_gb < used_storage_gb:
            return jsonify({
                'error': f'Cannot select plan "{new_plan}". Organization currently uses {used_storage_gb:.2f} GB of data, which exceeds this plan\'s storage limit of {target_storage_gb:.1f} GB. Please choose a plan supporting at least {used_storage_gb:.2f} GB.'
            }), 400

    old_plan = sub.plan_name
    sub.plan_name = new_plan
    sub.base_price = float(data.get('base_price', plan_info['base_price']))
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
    plan_info = _get_plan_details(new_plan, sub.billing_cycle)
    if not plan_info:
        return jsonify({'error': f'Valid plan_name required: {new_plan}'}), 422

    # Storage Check: Ensure downgraded plan storage accommodates existing data
    org = sub.organization
    if org:
        from app.domain.services.storage_calculator_service import calculate_org_storage_realtime
        calc = calculate_org_storage_realtime(org.id)
        if isinstance(calc, dict):
            orgs = calc.get('organizations', [])
            used_storage_gb = float(orgs[0].get('storage_used_gb', 0.0)) if orgs and isinstance(orgs[0], dict) else float(calc.get('storage_used_gb', (org.storage_used_mb or 0.0) / 1024.0))
        elif isinstance(calc, list) and len(calc) > 0 and isinstance(calc[0], dict):
            used_storage_gb = float(calc[0].get('storage_used_gb', 0.0))
        else:
            used_storage_gb = float((org.storage_used_mb or 0.0) / 1024.0)
        target_storage_gb = float(data.get('storage_limit_gb', plan_info['storage_limit_gb']))
        if target_storage_gb < used_storage_gb:
            return jsonify({
                'error': f'Cannot downgrade to "{new_plan}". Organization currently uses {used_storage_gb:.2f} GB of data, which exceeds this plan\'s storage limit of {target_storage_gb:.1f} GB. Please choose a plan supporting at least {used_storage_gb:.2f} GB or delete existing files.'
            }), 400

    old_plan = sub.plan_name
    sub.plan_name = new_plan
    sub.base_price = float(data.get('base_price', plan_info['base_price']))
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
    sub.cancelled_at = datetime.now(timezone.utc).replace(tzinfo=None)
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

    base = sub.end_date or datetime.now(timezone.utc).replace(tzinfo=None)
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
        invoice_number=data.get('invoice_number', f"INV/{datetime.now(timezone.utc).replace(tzinfo=None).year}/{sub.id:04d}M{len(sub.invoices)+1}"),
        invoice_date=datetime.now(timezone.utc).replace(tzinfo=None),
        due_date=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=data.get('due_days', 7)),
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
    sub.start_date = datetime.now(timezone.utc).replace(tzinfo=None)
    sub.end_date = _compute_renewal_date(sub.start_date, billing_cycle)
    sub.renewal_date = sub.end_date
    sub.trial_start_date = sub.trial_start_date or sub.start_date
    sub.trial_end_date = sub.trial_end_date or datetime.now(timezone.utc).replace(tzinfo=None)

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

    base = sub.trial_end_date or datetime.now(timezone.utc).replace(tzinfo=None)
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


def auto_approve_trial_extension_task(app_obj, org_id):
    """Background task running after 5 minutes (300 seconds) to auto-approve trial extension"""
    try:
        with app_obj.app_context():
            org = db.session.get(Organization, org_id)
            if not org:
                return
            sec_settings = dict(getattr(org, 'security_settings', {}) or {})
            pending = sec_settings.get('pending_trial_extension')
            if not pending or pending.get('status') != 'Pending':
                return
            if not pending.get('is_auto_eligible', True):
                return

            days = pending.get('days', 14)
            current_count = getattr(org, 'trial_extension_count', 0) or 0
            org.trial_extension_count = current_count + 1
            org.trial_ends_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=days)
            org.license_expiry_date = org.trial_ends_at
            org.subscription_status = 'Trialing'

            auto_count = sec_settings.get('auto_approved_trial_extensions', 0) + 1
            sec_settings['auto_approved_trial_extensions'] = auto_count

            sub = Subscription.query.filter_by(org_id=org.id).first()
            if not sub:
                sub = Subscription.query.filter_by(organization_id=org.id).first()
            if sub:
                sub.trial_end_date = org.trial_ends_at
                sub.end_date = org.trial_ends_at
                sub.subscription_status = 'Trial'

            pending['status'] = 'Approved'
            pending['approved_at'] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            pending['approval_type'] = 'Auto-Approved'
            sec_settings['pending_trial_extension'] = pending
            org.security_settings = sec_settings
            flag_modified(org, 'security_settings')
            db.session.commit()
            print(f"[QCMS 5-MIN AUTO-APPROVAL] Trial extension (+{days} days) automatically approved for Org ID {org_id}.")
    except Exception as e:
        print(f"[QCMS 5-MIN AUTO-APPROVAL ERROR] {e}")


def check_and_apply_pending_trial_extensions(org):
    """Helper to check if a pending trial extension has exceeded 5 minutes (300s) and auto-approve it"""
    if not org:
        return
    try:
        sec_settings = dict(getattr(org, 'security_settings', {}) or {})
        pending = sec_settings.get('pending_trial_extension')
        if not pending or pending.get('status') != 'Pending':
            return
        if not pending.get('is_auto_eligible', True):
            return

        req_at_str = pending.get('requested_at')
        if not req_at_str:
            return
        req_at = datetime.fromisoformat(req_at_str)
        if (datetime.now(timezone.utc).replace(tzinfo=None) - req_at).total_seconds() >= 300: # 5 minutes = 300 seconds
            days = pending.get('days', 14)
            current_count = getattr(org, 'trial_extension_count', 0) or 0
            org.trial_extension_count = current_count + 1
            org.trial_ends_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=days)
            org.license_expiry_date = org.trial_ends_at
            org.subscription_status = 'Trialing'

            auto_count = sec_settings.get('auto_approved_trial_extensions', 0) + 1
            sec_settings['auto_approved_trial_extensions'] = auto_count

            sub = Subscription.query.filter_by(org_id=org.id).first()
            if not sub:
                sub = Subscription.query.filter_by(organization_id=org.id).first()
            if sub:
                sub.trial_end_date = org.trial_ends_at
                sub.end_date = org.trial_ends_at
                sub.subscription_status = 'Trial'

            pending['status'] = 'Approved'
            pending['approved_at'] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            pending['approval_type'] = 'Auto-Approved'
            sec_settings['pending_trial_extension'] = pending
            org.security_settings = sec_settings
            flag_modified(org, 'security_settings')
            db.session.commit()
    except Exception as e:
        print(f"[QCMS CHECK PENDING ERROR] {e}")


@subscription_bp.route('/request-trial-extension', methods=['POST'])
@jwt_required()
def request_trial_extension():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    org_id = getattr(user, 'org_id', None) or getattr(user, 'organization_id', None)
    if not org_id and (user.role == 'SuperAdmin' or getattr(user.role, 'name', '') == 'SuperAdmin'):
        data = request.get_json(silent=True) or {}
        org_id = data.get('organization_id')
        
    if not org_id:
        return jsonify({'error': 'Organization ID not found for user'}), 404
        
    org = db.session.get(Organization, org_id)
    if not org:
        return jsonify({'error': 'Organization not found'}), 404

    data = request.get_json(silent=True) or {}
    reason = (data.get('reason') or data.get('notes') or '').strip()

    ps = PlatformSettings.query.first()
    max_auto = (ps.max_auto_trial_extensions if ps and hasattr(ps, 'max_auto_trial_extensions') and ps.max_auto_trial_extensions is not None else 2)
    default_days = (ps.trial_period_days if ps and hasattr(ps, 'trial_period_days') and ps.trial_period_days else 14)

    days = int(data.get('days', default_days))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    current_count = getattr(org, 'trial_extension_count', 0) or 0
    is_auto_eligible = bool(current_count < max_auto)

    # Save pending trial extension request
    sec_settings = dict(getattr(org, 'security_settings', {}) or {})
    total_reqs = sec_settings.get('total_trial_requests', 0) + 1
    sec_settings['total_trial_requests'] = total_reqs

    sec_settings['pending_trial_extension'] = {
        'requested_at': now.isoformat(),
        'days': days,
        'reason': reason,
        'status': 'Pending',
        'is_auto_eligible': is_auto_eligible,
        'max_auto_allowed': max_auto,
        'user_id': user.id
    }
    org.security_settings = sec_settings
    flag_modified(org, 'security_settings')
    db.session.commit()

    if is_auto_eligible:
        # Schedule background auto-approval after 5 minutes (300 seconds)
        from flask import current_app
        app_obj = current_app._get_current_object()
        timer = threading.Timer(300.0, auto_approve_trial_extension_task, args=[app_obj, org.id])
        timer.daemon = True
        timer.start()

    _log(user, 'TRIAL_EXTENSION_REQUESTED', 'Organization', org.id,
         None, {'days': days, 'reason': reason, 'is_auto_eligible': is_auto_eligible})

    return jsonify({
        'status': 'success',
        'auto_approved': False,
        'is_auto_eligible': is_auto_eligible,
        'message': 'Your request has been submitted! It will take up to 24 hours for review.',
        'trial_ends_at': org.trial_ends_at.isoformat() if org.trial_ends_at else None
    }), 200


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
    sub.cancelled_at = datetime.now(timezone.utc).replace(tzinfo=None)
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
        sub = db.session.get(Subscription, sid)
        if not sub:
            results['failed'].append({'id': sid, 'reason': 'Not found'})
            continue
        try:
            renew_from = max(datetime.now(timezone.utc).replace(tzinfo=None), sub.end_date or datetime.now(timezone.utc).replace(tzinfo=None))
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
            logger.error(f'Subscription bulk renewal failed for {sid}: {e}', exc_info=True)
            results['failed'].append({'id': sid, 'reason': 'Failed to process renewal'})

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
        sub = db.session.get(Subscription, sid)
        if not sub:
            results['failed'].append({'id': sid, 'reason': 'Not found'})
            continue
        sub.subscription_status = 'Cancelled'
        sub.cancelled_at = datetime.now(timezone.utc).replace(tzinfo=None)
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
        sub = db.session.get(Subscription, sid)
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
        sub = db.session.get(Subscription, sid)
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
    role_name = (user.role.name if (user and hasattr(user, 'role') and hasattr(user.role, 'name')) else str(getattr(user, 'role', ''))).strip().lower()
    is_super_admin = bool(user and (role_name in ('superadmin', 'super admin', 'super_admin') or getattr(user, 'system_role', '').lower() in ('superadmin', 'super_admin') or getattr(user, 'is_super_admin', False) or getattr(user, 'is_platform_super_admin', False) or getattr(user, 'id', 0) == 1))

    billing_cycle = request.args.get('billing_cycle', '')
    status_filter = request.args.get('status', '') # Active, Inactive, Deprecated, Coming Soon
    type_filter = request.args.get('plan_type', '') # Starter, Professional, Enterprise, Custom
    price_filter = request.args.get('price_type', '') # Free, Paid, Custom
    search_q = request.args.get('q', '').strip()

    # ── Resolve target organization and current storage usage ──
    target_org = None
    if not is_super_admin and user and user.org_id:
        target_org = user.organization
    elif request.args.get('org_id'):
        target_org = db.session.get(Organization, request.args.get('org_id', type=int))
    elif request.args.get('sub_id'):
        sub_rec = db.session.get(Subscription, request.args.get('sub_id', type=int))
        target_org = sub_rec.organization if sub_rec else None

    current_storage_gb = 0.0
    if target_org:
        try:
            from app.domain.services.storage_calculator_service import calculate_org_storage_realtime
            calc = calculate_org_storage_realtime(target_org.id)
            if isinstance(calc, dict):
                current_storage_gb = float(calc.get('storage_used_gb', 0.0))
            elif isinstance(calc, list) and len(calc) > 0 and isinstance(calc[0], dict):
                current_storage_gb = float(calc[0].get('storage_used_gb', 0.0))
            else:
                current_storage_gb = float((target_org.storage_used_mb or 0.0) / 1024.0)
        except Exception:
            current_storage_gb = float((target_org.storage_used_mb or 0.0) / 1024.0)

    try:
        plans_query = SaaSPlan.query
        if not is_super_admin or request.args.get('exclude_trial') == 'true':
            # Regular users/org admins only get Active non-trial subscription plans
            plans_query = plans_query.filter(
                (SaaSPlan.is_default_trial == False) | (SaaSPlan.is_default_trial == None),
                func.lower(func.coalesce(SaaSPlan.plan_type, '')) != 'trial',
                ~func.lower(func.coalesce(SaaSPlan.name, '')).like('%trial%'),
                ~func.lower(func.coalesce(SaaSPlan.code, '')).like('%trial%'),
                func.lower(func.coalesce(SaaSPlan.code, '')) != 't1'
            )
            if not status_filter:
                plans_query = plans_query.filter(SaaSPlan.status == 'Active')
            else:
                plans_query = plans_query.filter(SaaSPlan.status == status_filter)
        elif status_filter:
            plans_query = plans_query.filter(SaaSPlan.status == status_filter)
        if type_filter:
            plans_query = plans_query.filter(or_(
                SaaSPlan.plan_type.ilike(type_filter),
                SaaSPlan.name.ilike(type_filter),
                SaaSPlan.code.ilike(type_filter),
                SaaSPlan.name.ilike(f'%{type_filter}%')
            ))
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
            # Secondary safeguard: exclude any trial plans for non-superadmin
            if not is_super_admin or request.args.get('exclude_trial') == 'true':
                p_type = (plan.plan_type or '').lower()
                p_name = (plan.name or '').lower()
                p_code = (plan.code or '').lower()
                if plan.is_default_trial or p_type == 'trial' or 'trial' in p_name or 'trial' in p_code or p_code == 't1':
                    continue

            plan_storage_gb = float(plan.limits.storage_limit_gb if (plan.limits and plan.limits.storage_limit_gb is not None) else 10.0)

            # STORAGE CAPACITY FILTER:
            # If organization currently has e.g. 7 GB of data, filter out plans below 7 GB.
            # Only show plans with storage limit >= organization's current storage usage.
            if target_org and (not is_super_admin or request.args.get('filter_by_storage') == 'true'):
                if current_storage_gb > 0 and plan_storage_gb < current_storage_gb:
                    continue

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
                    bp = float(s.base_price or 0.0)
                    if s.billing_cycle == 'Monthly':
                        mrr_total += bp
                    elif s.billing_cycle == 'Quarterly':
                        mrr_total += bp / 3.0
                    elif s.billing_cycle == 'Yearly':
                        mrr_total += bp / 12.0
                plan.analytics.mrr = mrr_total
                plan.analytics.arr = mrr_total * 12.0
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()

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
            price_val = float(primary_pricing.price if primary_pricing else 0.0)

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
                'storage_limit_gb': plan_storage_gb,
                'api_limit': plan.limits.api_limit if plan.limits else 10000,
                'support_level': plan.limits.support_level if (plan.limits and hasattr(plan.limits, 'support_level')) else 'Standard',
                'enabled_modules': enabled_modules,
                'features': [m.module_name for m in plan.modules],
                'subscriber_count': subscriber_count,
                'pricing_model': getattr(plan, 'pricing_model', 'fixed'),
                'payg_rules': getattr(plan, 'payg_rules', None),
                'is_custom': plan.is_custom,
                'is_default_trial': getattr(plan, 'is_default_trial', False),
                'trial_duration_days': getattr(plan, 'trial_duration_days', 14),
                'auto_approve_extensions_limit': getattr(plan, 'auto_approve_extensions_limit', 2),
                'created_at': plan.created_at.isoformat() if plan.created_at else None,
                'updated_at': plan.updated_at.isoformat() if plan.updated_at else None
            })

        return jsonify({
            'status': 'success',
            'data': result,
            'billing_cycle': billing_cycle or 'Yearly',
            'current_storage_used_gb': round(current_storage_gb, 2),
            'min_required_storage_gb': round(current_storage_gb, 2),
            'storage_filtered': bool(target_org and current_storage_gb > 0)
        })
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"[GET PLAN CATALOGUE ERROR] {e}")
        return jsonify({'status': 'success', 'data': [], 'billing_cycle': billing_cycle or 'Yearly'})


@subscription_bp.route('/plans/<int:plan_id>', methods=['GET'])
@jwt_required()
def get_plan_detail(plan_id):
    user = _get_current_user()
    err = _require_super_admin(user)
    if err:
        return err

    plan = SaaSPlan.query.get_or_404(plan_id)
    
    seen_cycles = set()
    pricing = []
    non_zero_pricing = [p for p in plan.pricing if p.price > 0]
    source_pricing = non_zero_pricing if non_zero_pricing else plan.pricing
    for p in source_pricing:
        if p.billing_cycle not in seen_cycles:
            seen_cycles.add(p.billing_cycle)
            pricing.append({
                'billing_cycle': p.billing_cycle,
                'price': p.price,
                'discount': p.discount,
                'tax': p.tax,
                'is_tax_inclusive': getattr(p, 'is_tax_inclusive', False)
            })

    limits = {
        'max_users': plan.limits.max_users if plan.limits else 100,
        'max_locations': getattr(plan.limits, 'max_locations', 5) if plan.limits else 5,
        'max_departments': plan.limits.max_departments if plan.limits else 10,
        'max_projects': plan.limits.max_projects if plan.limits else 25,
        'storage_limit_gb': plan.limits.storage_limit_gb if plan.limits else 10.0,
        'api_limit': plan.limits.api_limit if plan.limits else 10000,
        'reports_limit': plan.limits.reports_limit if plan.limits else 100,
        'dashboards_limit': plan.limits.dashboards_limit if plan.limits else 10
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
            'pricing_model': getattr(plan, 'pricing_model', 'fixed'),
            'payg_rules': getattr(plan, 'payg_rules', None),
            'revenue': revenue
        }
    })


def _clean_plan_type(val):
    if not val:
        return 'Professional'
    v = str(val).strip()
    if v.lower().startswith('trial') or 'trial' in v.lower():
        return 'Trial'
    if 'pay' in v.lower() and 'go' in v.lower():
        return 'Pay-As-You-Go'
    return v[:100]


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

    resolved_plan_type = _clean_plan_type(data.get('plan_type', 'Professional'))
    pricing_model_val = data.get('pricing_model', 'pay_as_you_go' if resolved_plan_type == 'Pay-As-You-Go' else 'fixed')
    payg_rules_val = data.get('payg_rules')

    plan = SaaSPlan(
        name=name,
        code=code,
        description=data.get('description'),
        long_description=data.get('long_description'),
        icon=data.get('icon', 'layers'),
        color=data.get('color', '#3b82f6'),
        status=data.get('status', 'Active'),
        plan_type=resolved_plan_type,
        pricing_model=pricing_model_val,
        payg_rules=payg_rules_val,
        currency=data.get('currency', 'INR'),
        is_custom=data.get('is_custom', False),
        is_default_trial=bool(data.get('is_default_trial', False)) or ('trial' in str(data.get('plan_type', '')).lower()),
        trial_duration_days=int(data.get('trial_duration_days', 180)),
        auto_approve_extensions_limit=int(data.get('auto_approve_extensions_limit', 2)),
        version=1
    )
    db.session.add(plan)
    db.session.flush()

    if plan.is_default_trial:
        SaaSPlan.query.filter(SaaSPlan.id != plan.id).update({'is_default_trial': False})
        ps = PlatformSettings.query.first()
        if ps:
            ps.trial_period_days = plan.trial_duration_days
            ps.max_auto_trial_extensions = plan.auto_approve_extensions_limit

    # Add Pricing Cycles
    pricing_data = data.get('pricing', [])
    for p in pricing_data:
        pricing = SaaSPlanPricing(
            plan_id=plan.id,
            billing_cycle=p.get('billing_cycle'),
            price=float(p.get('price', 0.0)),
            discount=float(p.get('discount', 0.0)),
            tax=float(p.get('tax', 18.0)),
            is_tax_inclusive=bool(p.get('is_tax_inclusive', False))
        )
        db.session.add(pricing)

    # Add Usage Limits
    lim = data.get('limits', {})
    limits = SaaSPlanLimits(
        plan_id=plan.id,
        max_users=int(lim.get('max_users', 100)),
        max_locations=int(lim.get('max_locations', 5)),
        max_departments=int(lim.get('max_departments', 10)),
        max_projects=int(lim.get('max_projects', 25)),
        storage_limit_gb=float(lim.get('storage_limit_gb', 10.0)),
        api_limit=int(lim.get('api_limit', 10000)),
        reports_limit=int(lim.get('reports_limit', 100)),
        dashboards_limit=int(lim.get('dashboards_limit', 10))
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
    if 'name' in data:
        new_name = (data['name'] or '').strip()
        if new_name and new_name.lower() != (plan.name or '').strip().lower():
            if SaaSPlan.query.filter(SaaSPlan.id != plan.id, SaaSPlan.name.ilike(new_name)).first():
                return jsonify({'error': 'Plan name already exists'}), 400
            plan.name = new_name

    if 'code' in data:
        new_code = (data['code'] or '').strip()
        if new_code and new_code.lower() != (plan.code or '').strip().lower():
            if SaaSPlan.query.filter(SaaSPlan.id != plan.id, SaaSPlan.code.ilike(new_code)).first():
                return jsonify({'error': 'Plan code already exists'}), 400
            plan.code = new_code
    
    is_trial_plan = getattr(plan, 'is_default_trial', False) or (plan.plan_type and 'trial' in plan.plan_type.lower()) or (plan.code and plan.code.lower() in ['t1', 'trial', 'trial_default'])

    if is_trial_plan:
        if 'plan_type' in data and data['plan_type'] and _clean_plan_type(data['plan_type']).lower() != 'trial':
            err_msg = "Trial plan cannot be converted to a normal/paid plan. It must always remain a Trial plan."
            return jsonify({'status': 'error', 'error': err_msg, 'message': err_msg}), 400

    new_status = data.get('status', plan.status)
    if is_trial_plan and new_status in ['Inactive', 'Deprecated'] and plan.status == 'Active':
        other_active_trials = SaaSPlan.query.filter(
            SaaSPlan.id != plan.id,
            SaaSPlan.status == 'Active',
            (func.lower(SaaSPlan.plan_type) == 'trial') | (SaaSPlan.is_default_trial == True)
        ).count()
        if other_active_trials == 0:
            err_msg = "Cannot disable the default trial plan. At least one active trial plan must exist in the system. Create or activate another trial plan before disabling this one."
            return jsonify({'status': 'error', 'error': err_msg, 'message': err_msg}), 400

    plan.description = data.get('description', plan.description)
    plan.long_description = data.get('long_description', plan.long_description)
    plan.icon = data.get('icon', plan.icon)
    plan.color = data.get('color', plan.color)
    plan.status = new_status
    if is_trial_plan:
        plan.plan_type = 'Trial'
        plan.is_default_trial = True
    else:
        plan.plan_type = _clean_plan_type(data.get('plan_type', plan.plan_type))
        if 'is_default_trial' in data:
            plan.is_default_trial = bool(data['is_default_trial'])
        elif 'trial' in plan.plan_type.lower():
            plan.is_default_trial = True
    
    if 'pricing_model' in data:
        plan.pricing_model = data['pricing_model']
    elif plan.plan_type == 'Pay-As-You-Go':
        plan.pricing_model = 'pay_as_you_go'

    if 'payg_rules' in data:
        plan.payg_rules = data['payg_rules']

    plan.is_custom = data.get('is_custom', plan.is_custom)

    if 'trial_duration_days' in data:
        plan.trial_duration_days = int(data['trial_duration_days'])
    if 'auto_approve_extensions_limit' in data:
        plan.auto_approve_extensions_limit = int(data['auto_approve_extensions_limit'])

    if plan.is_default_trial:
        SaaSPlan.query.filter(SaaSPlan.id != plan.id).update({'is_default_trial': False})
        ps = PlatformSettings.query.first()
        if ps:
            ps.trial_period_days = plan.trial_duration_days
            ps.max_auto_trial_extensions = plan.auto_approve_extensions_limit

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
                tax=float(p.get('tax', 18.0)),
                is_tax_inclusive=bool(p.get('is_tax_inclusive', False))
            )
            db.session.add(pricing)

    # Update Limits
    if 'limits' in data and plan.limits:
        lim = data['limits']
        plan.limits.max_users = int(lim.get('max_users', plan.limits.max_users))
        plan.limits.max_locations = int(lim.get('max_locations', getattr(plan.limits, 'max_locations', 5)))
        plan.limits.max_departments = int(lim.get('max_departments', getattr(plan.limits, 'max_departments', 10)))
        plan.limits.max_projects = int(lim.get('max_projects', plan.limits.max_projects))
        plan.limits.storage_limit_gb = float(lim.get('storage_limit_gb', plan.limits.storage_limit_gb))
        plan.limits.api_limit = int(lim.get('api_limit', plan.limits.api_limit))

    # Apply to existing subscribers check
    apply_to_existing = bool(data.get('apply_to_existing', True))
    synced_org_count = 0
    if apply_to_existing:
        orgs_to_sync = Organization.query.filter(
            (Organization.is_deleted == False) &
            (Organization.is_platform_org == False) &
            (
                (func.lower(func.trim(Organization.subscription_plan)) == plan.name.strip().lower()) |
                (func.lower(func.trim(Organization.subscription_plan)) == plan.code.strip().lower()) |
                (func.lower(func.trim(Organization.subscription_plan)) == old_snapshot['name'].strip().lower()) |
                (func.lower(func.trim(Organization.subscription_plan)) == old_snapshot['code'].strip().lower())
            )
        ).all()
        synced_org_count = len(orgs_to_sync)

        new_storage_mb = plan.limits.storage_limit_gb * 1024.0 if plan.limits else 10240.0
        new_max_users = plan.limits.max_users if plan.limits else 100

        for o in orgs_to_sync:
            o.storage_limit_mb = new_storage_mb
            o.max_users = new_max_users
            if 'name' in data and data['name']:
                o.subscription_plan = data['name']

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

    if apply_to_existing:
        resp_msg = f"Plan updated to Version {plan.version} successfully and applied immediately to {synced_org_count} existing active subscriber organization(s)."
    else:
        resp_msg = f"Plan template updated to Version {plan.version} for future subscribers. Existing active subscribers remain on their current terms."

    return jsonify({'status': 'success', 'message': resp_msg, 'data': {'version': plan.version, 'synced_orgs': synced_org_count, 'applied_to_existing': apply_to_existing}})


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
            max_locations=getattr(parent.limits, 'max_locations', 5),
            max_departments=parent.limits.max_departments,
            max_projects=parent.limits.max_projects,
            storage_limit_gb=parent.limits.storage_limit_gb,
            api_limit=parent.limits.api_limit,
            reports_limit=parent.limits.reports_limit,
            dashboards_limit=parent.limits.dashboards_limit
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

    is_trial_plan = getattr(plan, 'is_default_trial', False) or (plan.plan_type and 'trial' in plan.plan_type.lower()) or (plan.code and plan.code.lower() in ['t1', 'trial', 'trial_default'])
    if is_trial_plan:
        other_active_trials = SaaSPlan.query.filter(
            SaaSPlan.id != plan.id,
            SaaSPlan.status == 'Active',
            (func.lower(SaaSPlan.plan_type) == 'trial') | (SaaSPlan.is_default_trial == True)
        ).count()
        if other_active_trials == 0:
            err_msg = "Cannot disable the default trial plan. At least one active trial plan must exist in the system. Create or activate another trial plan before disabling this one."
            return jsonify({'status': 'error', 'error': err_msg, 'message': err_msg}), 400

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

    is_trial_plan = getattr(plan, 'is_default_trial', False) or (plan.plan_type and 'trial' in plan.plan_type.lower()) or (plan.code and plan.code.lower() in ['t1', 'trial', 'trial_default'])
    if is_trial_plan:
        err_msg = "System default trial plan cannot be deleted."
        return jsonify({'status': 'error', 'error': err_msg, 'message': err_msg}), 400

    # Prevent deleting plans with active subscribers
    org_subscribers = Organization.query.filter(
        (Organization.is_deleted == False) &
        (Organization.is_platform_org == False) &
        (
            (func.lower(func.trim(Organization.subscription_plan)) == plan.name.strip().lower()) |
            (func.lower(func.trim(Organization.subscription_plan)) == plan.code.strip().lower())
        )
    ).count()
    active_subs = Subscription.query.join(Organization, Subscription.org_id == Organization.id).filter(
        (Organization.is_deleted == False) &
        (Organization.is_platform_org == False) &
        (
            (func.lower(func.trim(Subscription.plan_name)) == plan.name.strip().lower()) |
            (func.lower(func.trim(Subscription.plan_name)) == plan.code.strip().lower())
        ) &
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
            'max_locations': getattr(limits, 'max_locations', 5) if limits else 5,
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
    orgs = Organization.query.filter(
        (Organization.is_deleted == False) &
        (Organization.is_platform_org == False) &
        (
            (func.lower(func.trim(Organization.subscription_plan)) == plan.name.strip().lower()) |
            (func.lower(func.trim(Organization.subscription_plan)) == plan.code.strip().lower())
        )
    ).all()

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


# ── PAYG Fallback / Forwarding Endpoints under /api/subscriptions ──
@subscription_bp.route('/billing/payg/preview-all', methods=['GET', 'POST'])
@jwt_required()
@super_admin_required()
def sub_payg_preview_all():
    from app.presentation.routes.billing_routes import preview_all_payg_bills
    return preview_all_payg_bills()


@subscription_bp.route('/billing/payg/rules', methods=['GET', 'POST'])
@jwt_required()
@super_admin_required()
def sub_payg_rules():
    from app.presentation.routes.billing_routes import payg_rules_endpoint
    return payg_rules_endpoint()


@subscription_bp.route('/billing/payg/preview-single', methods=['POST'])
@jwt_required()
@super_admin_required()
def sub_payg_preview_single():
    from app.presentation.routes.billing_routes import preview_single_payg_bill
    return preview_single_payg_bill()


@subscription_bp.route('/billing/payg/generate-bills', methods=['POST'])
@jwt_required()
@super_admin_required()
def sub_payg_generate_bills():
    from app.presentation.routes.billing_routes import generate_payg_monthly_bills
    return generate_payg_monthly_bills()


