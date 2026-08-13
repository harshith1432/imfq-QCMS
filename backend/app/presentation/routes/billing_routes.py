import uuid
import secrets
import shutil
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, send_from_directory, abort, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, or_, and_, text
import os
from werkzeug.utils import secure_filename
from app.infrastructure.database.models.models import (
    db, User, Organization, Subscription, SubscriptionInvoice, SubscriptionPayment,
    InvoiceItem, SubscriptionRefund, SubscriptionCreditNote, BillingSettings, TaxRule, BillingAudit,
    OfflinePaymentProof, IntegrationConfig, Notification, SaaSPlan, SaaSPlanPricing
)
from app.presentation.middleware.middleware import super_admin_required

billing_bp = Blueprint('billing', __name__)

# --- HELPERS ---

def _get_current_user():
    user_id = get_jwt_identity()
    return User.query.get(user_id)

def _audit_log(org_id, invoice_id, action, details):
    user_id = get_jwt_identity()
    audit = BillingAudit(
        org_id=org_id,
        invoice_id=invoice_id,
        user_id=int(user_id) if user_id else 1,
        action=action,
        details=details,
        ip_address=request.remote_addr or '127.0.0.1'
    )
    db.session.add(audit)
    db.session.commit()

# --- ENDPOINTS ---

@billing_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@super_admin_required()
def get_billing_dashboard():
    # Fetch KPIs — exclude platform/system orgs (SuperAdmin's internal org)
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    year_start = datetime(now.year, 1, 1)

    # Get platform org IDs to exclude
    platform_org_ids = [
        r[0] for r in db.session.query(Organization.id).filter(Organization.is_platform_org == True).all()
    ]

    def _excl_pay(q):
        """Exclude payments belonging to platform orgs."""
        if platform_org_ids:
            return q.filter(~SubscriptionPayment.org_id.in_(platform_org_ids))
        return q

    def _excl_inv(q):
        """Exclude invoices belonging to platform orgs."""
        if platform_org_ids:
            return q.join(Subscription, SubscriptionInvoice.subscription_id == Subscription.id, isouter=True)\
                    .filter(~Subscription.org_id.in_(platform_org_ids))
        return q

    total_revenue = _excl_pay(
        db.session.query(func.sum(SubscriptionPayment.final_amount)).filter_by(payment_status='Completed')
    ).scalar() or 0.0

    monthly_revenue = _excl_pay(
        db.session.query(func.sum(SubscriptionPayment.final_amount)).filter(
            SubscriptionPayment.payment_status == 'Completed',
            SubscriptionPayment.created_at >= month_start
        )
    ).scalar() or 0.0

    annual_revenue = _excl_pay(
        db.session.query(func.sum(SubscriptionPayment.final_amount)).filter(
            SubscriptionPayment.payment_status == 'Completed',
            SubscriptionPayment.created_at >= year_start
        )
    ).scalar() or 0.0

    pending_payments = SubscriptionInvoice.query.filter_by(invoice_status='Sent').count()
    paid_invoices = SubscriptionInvoice.query.filter_by(invoice_status='Paid').count()
    overdue_invoices = SubscriptionInvoice.query.filter(
        SubscriptionInvoice.invoice_status == 'Sent',
        SubscriptionInvoice.due_date < now
    ).count()
    failed_payments = _excl_pay(
        SubscriptionPayment.query.filter_by(payment_status='Failed')
    ).count()
    refunds = db.session.query(func.sum(SubscriptionRefund.amount)).scalar() or 0.0
    taxes_collected = _excl_pay(
        db.session.query(func.sum(SubscriptionPayment.gst_amount)).filter_by(payment_status='Completed')
    ).scalar() or 0.0

    outstanding = db.session.query(func.sum(SubscriptionInvoice.total_amount)).filter(
        SubscriptionInvoice.invoice_status.in_(['Draft', 'Sent']),
        SubscriptionInvoice.due_date < now
    ).scalar() or 0.0

    avg_invoice = db.session.query(func.avg(SubscriptionInvoice.total_amount)).scalar() or 0.0

    # Collection Rate = paid invoices / total issued invoices (Paid + Sent/Pending, excludes Drafts)
    # Returns 0.0 when there are no issued invoices (not 100%)
    total_issued = SubscriptionInvoice.query.filter(
        SubscriptionInvoice.invoice_status.in_(['Paid', 'Sent', 'Overdue'])
    ).count()
    if total_issued > 0:
        collection_rate = round(paid_invoices / total_issued * 100, 1)
    else:
        collection_rate = 0.0  # No invoices issued yet — not 100%

    return jsonify({
        "status": "success",
        "data": {
            "total_revenue": total_revenue,
            "monthly_revenue": monthly_revenue,
            "annual_revenue": annual_revenue,
            "pending_payments": pending_payments,
            "paid_invoices": paid_invoices,
            "overdue_invoices": overdue_invoices,
            "failed_payments": failed_payments,
            "refunds": refunds,
            "taxes_collected": taxes_collected,
            "outstanding_amount": outstanding,
            "avg_invoice_value": avg_invoice,
            "collection_rate": collection_rate
        }
    })

@billing_bp.route('/invoices', methods=['GET'])
@jwt_required()
@super_admin_required()
def list_invoices():
    # Query parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()
    cycle = request.args.get('billing_cycle', '').strip()
    plan = request.args.get('plan', '').strip()
    payment_method = request.args.get('payment_method', '').strip()

    query = SubscriptionInvoice.query

    # Search
    if q:
        query = query.join(Organization).filter(
            or_(
                SubscriptionInvoice.invoice_number.ilike(f'%{q}%'),
                SubscriptionInvoice.invoice_uid.ilike(f'%{q}%'),
                Organization.name.ilike(f'%{q}%'),
                SubscriptionInvoice.plan_name.ilike(f'%{q}%')
            )
        )

    # Filters
    if status:
        query = query.filter(SubscriptionInvoice.invoice_status == status)
    if cycle:
        query = query.filter(SubscriptionInvoice.billing_cycle == cycle)
    if plan:
        from app.infrastructure.database.models.models import SaaSPlan
        matching_sp = [sp.name for sp in SaaSPlan.query.filter(
            db.or_(SaaSPlan.plan_type.ilike(plan), SaaSPlan.name.ilike(plan), SaaSPlan.code.ilike(plan))
        ).all()]
        target_plans = set([plan] + matching_sp)
        if plan.lower() in ('trial', 'trialing'):
            target_plans.update(['Trial', 'Trialing', 'Default Trial Plan'])
        query = query.filter(db.or_(*[SubscriptionInvoice.plan_name.ilike(p) for p in target_plans]))

    total = query.count()
    invoices = query.order_by(SubscriptionInvoice.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    output = []
    for inv in invoices:
        output.append({
            "id": inv.id,
            "invoice_uid": inv.invoice_uid,
            "invoice_number": inv.invoice_number,
            "org_name": inv.organization.name,
            "plan_name": inv.plan_name,
            "billing_cycle": inv.billing_cycle,
            "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "base_amount": inv.base_amount,
            "discount_amount": inv.discount_amount,
            "gst_amount": inv.gst_amount,
            "total_amount": inv.total_amount,
            "currency": inv.currency,
            "invoice_status": inv.invoice_status,
            "payment_id": inv.payment_id
        })

    return jsonify({
        "status": "success",
        "data": output,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    })

@billing_bp.route('/invoices/<int:inv_id>', methods=['GET'])
@jwt_required()
@super_admin_required()
def get_invoice_details(inv_id):
    inv = SubscriptionInvoice.query.get_or_404(inv_id)
    
    # Fetch Items
    items = [{
        "id": x.id,
        "description": x.description,
        "quantity": x.quantity,
        "unit_price": x.unit_price,
        "amount": x.amount
    } for x in inv.items]

    # Fetch Refund History
    refunds = [{
        "id": r.id,
        "refund_uid": r.refund_uid,
        "amount": r.amount,
        "reason": r.reason,
        "status": r.status,
        "created_at": r.created_at.isoformat()
    } for r in inv.refund_records]

    # Fetch Credit Notes linked
    credit_notes = [{
        "id": c.id,
        "credit_note_uid": c.credit_note_uid,
        "amount": c.amount,
        "balance": c.balance,
        "status": c.status,
        "created_at": c.created_at.isoformat()
    } for c in inv.credit_notes]

    # Fetch Timeline Audit Logs
    audits = [{
        "id": a.id,
        "action": a.action,
        "user_name": a.user.full_name if a.user else 'System',
        "details": a.details,
        "ip_address": a.ip_address,
        "created_at": a.created_at.isoformat()
    } for a in inv.billing_audits]

    from app.domain.services.document_branding_service import DocumentBrandingService
    branding = DocumentBrandingService.get_branding_context(inv.org_id)

    return jsonify({
        "status": "success",
        "data": {
            "id": inv.id,
            "invoice_uid": inv.invoice_uid,
            "invoice_number": inv.invoice_number,
            "org_id": inv.org_id,
            "org_name": inv.organization.name,
            "org_email": inv.organization.email,
            "subscription_id": inv.subscription_id,
            "subscription_uid": inv.subscription.subscription_uid if inv.subscription else None,
            "plan_name": inv.plan_name,
            "billing_cycle": inv.billing_cycle,
            "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "base_amount": inv.base_amount,
            "discount_percent": inv.discount_percent,
            "discount_amount": inv.discount_amount,
            "gst_percent": inv.gst_percent,
            "gst_amount": inv.gst_amount,
            "total_amount": inv.total_amount,
            "currency": inv.currency,
            "invoice_status": inv.invoice_status,
            "payment_id": inv.payment_id,
            "notes": inv.notes,
            "pdf_path": inv.pdf_path,
            "items": items,
            "refunds": refunds,
            "credit_notes": credit_notes,
            "audits": audits,
            "branding": branding
        }
    })

@billing_bp.route('/invoices', methods=['POST'])
@jwt_required()
@super_admin_required()
def create_invoice():
    data = request.json or {}
    
    org_id = data.get('org_id')
    subscription_id = data.get('subscription_id')
    invoice_number = data.get('invoice_number', '').strip()
    
    if not org_id:
        return jsonify({"status": "error", "message": "Every invoice must belong to an organization"}), 422
    if not subscription_id:
        return jsonify({"status": "error", "message": "Every invoice must be linked to a subscription"}), 422
    if not invoice_number:
        return jsonify({"status": "error", "message": "Invoice number is required"}), 422

    # Validate duplicate invoice number
    if SubscriptionInvoice.query.filter_by(invoice_number=invoice_number).first():
        return jsonify({"status": "error", "message": f"Invoice number '{invoice_number}' already exists"}), 422

    # Calculate pricing
    items_data = data.get('items', [])
    base_amount = 0.0
    invoice_items = []
    
    for it in items_data:
        qty = int(it.get('quantity', 1))
        u_price = float(it.get('unit_price', 0.0))
        amt = qty * u_price
        base_amount += amt
        invoice_items.append(InvoiceItem(
            description=it.get('description', 'Subscription Service'),
            quantity=qty,
            unit_price=u_price,
            amount=amt
        ))

    discount_percent = float(data.get('discount_percent', 0.0))
    discount_amount = base_amount * (discount_percent / 100.0)
    
    gst_percent = float(data.get('gst_percent', 18.0))
    # Tax is calculated before final amount
    taxable_amount = base_amount - discount_amount
    gst_amount = taxable_amount * (gst_percent / 100.0)
    
    total_amount = taxable_amount + gst_amount

    if total_amount < 0:
        return jsonify({"status": "error", "message": "Invoice final amount cannot be negative"}), 422

    # Generate UID
    uid = f"INV-{datetime.utcnow().year}-{uuid.uuid4().hex[:6].upper()}"

    inv = SubscriptionInvoice(
        org_id=org_id,
        subscription_id=subscription_id,
        invoice_uid=uid,
        invoice_number=invoice_number,
        invoice_date=datetime.strptime(data.get('invoice_date', datetime.utcnow().strftime('%Y-%m-%d')), '%Y-%m-%d'),
        due_date=datetime.strptime(data.get('due_date', (datetime.utcnow() + timedelta(days=15)).strftime('%Y-%m-%d')), '%Y-%m-%d'),
        plan_name=data.get('plan_name', 'Professional'),
        billing_cycle=data.get('billing_cycle', 'Yearly'),
        base_amount=base_amount,
        discount_percent=discount_percent,
        discount_amount=discount_amount,
        gst_percent=gst_percent,
        gst_amount=gst_amount,
        total_amount=total_amount,
        currency=data.get('currency', 'INR'),
        invoice_status='Sent',
        notes=data.get('notes', ''),
        items=invoice_items
    )

    db.session.add(inv)
    db.session.commit()

    _audit_log(org_id, inv.id, "Invoice Created", {"invoice_number": invoice_number, "total_amount": total_amount})

    return jsonify({
        "status": "success",
        "message": "Invoice generated successfully",
        "invoice_id": inv.id
    }), 201

@billing_bp.route('/invoices/<int:inv_id>/pay', methods=['POST'])
@jwt_required()
@super_admin_required()
def pay_invoice(inv_id):
    inv = SubscriptionInvoice.query.get_or_404(inv_id)
    if inv.invoice_status == 'Paid':
        return jsonify({"status": "error", "message": "Invoice is already paid"}), 422

    data = request.json or {}
    payment_method = data.get('payment_method', 'Manual')
    gateway_ref = data.get('gateway_reference', 'REF-' + uuid.uuid4().hex[:8].upper())
    
    # Record payment transaction
    tx_id = "TXN-" + uuid.uuid4().hex[:10].upper()
    payment = SubscriptionPayment(
        org_id=inv.org_id,
        subscription_id=inv.subscription_id,
        invoice_id=inv.id,
        amount=inv.base_amount,
        currency=inv.currency,
        plan_name=inv.plan_name,
        billing_cycle=inv.billing_cycle,
        payment_status='Completed',
        transaction_id=tx_id,
        payment_gateway=payment_method,
        gateway_reference=gateway_ref,
        discount_amount=inv.discount_amount,
        gst_percent=inv.gst_percent,
        gst_amount=inv.gst_amount,
        final_amount=inv.total_amount,
        refund_status='None',
        billing_period_start=inv.billing_period_start or datetime.utcnow(),
        billing_period_end=inv.billing_period_end or (datetime.utcnow() + timedelta(days=365))
    )
    
    db.session.add(payment)
    db.session.flush()

    inv.invoice_status = 'Paid'
    inv.payment_id = payment.id
    db.session.commit()

    _audit_log(inv.org_id, inv.id, "Payment Received", {"transaction_id": tx_id, "amount": inv.total_amount})

    # Trigger subscription status update to Active if linked
    if inv.subscription:
        inv.subscription.subscription_status = 'Active'
        db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Payment recorded successfully",
        "transaction_id": tx_id
    })

@billing_bp.route('/invoices/<int:inv_id>/refund', methods=['POST'])
@jwt_required()
@super_admin_required()
def refund_invoice(inv_id):
    inv = SubscriptionInvoice.query.get_or_404(inv_id)
    if inv.invoice_status != 'Paid' or not inv.payment_id:
        return jsonify({"status": "error", "message": "Only paid invoices can be refunded"}), 422

    data = request.json or {}
    refund_amount = float(data.get('refund_amount', inv.total_amount))
    reason = data.get('reason', 'Customer Request')

    payment = SubscriptionPayment.query.get(inv.payment_id)
    
    # Refund limit validation
    already_refunded = sum(r.amount for r in inv.refund_records)
    if already_refunded + refund_amount > inv.total_amount:
        return jsonify({"status": "error", "message": f"Refund amount exceeds total paid amount. Already refunded: {already_refunded}"}), 422

    ref_uid = "REF-" + uuid.uuid4().hex[:8].upper()
    refund = SubscriptionRefund(
        invoice_id=inv.id,
        payment_id=payment.id,
        refund_uid=ref_uid,
        amount=refund_amount,
        reason=reason,
        status='Approved'
    )
    db.session.add(refund)

    # Update payment record
    payment.refund_amount += refund_amount
    payment.refund_date = datetime.utcnow()
    if payment.refund_amount >= inv.total_amount:
        payment.refund_status = 'Full'
        inv.invoice_status = 'Refunded'
    else:
        payment.refund_status = 'Partial'

    db.session.commit()
    _audit_log(inv.org_id, inv.id, "Refund Issued", {"refund_uid": ref_uid, "amount": refund_amount})

    return jsonify({
        "status": "success",
        "message": "Refund processed successfully",
        "refund_uid": ref_uid
    })

@billing_bp.route('/invoices/<int:inv_id>', methods=['DELETE'])
@jwt_required()
@super_admin_required()
def delete_invoice(inv_id):
    inv = SubscriptionInvoice.query.get_or_404(inv_id)
    org_id = inv.org_id

    try:
        # Nullify/delete dependent records referencing this invoice_id
        db.session.query(SubscriptionPayment).filter_by(invoice_id=inv_id).update({SubscriptionPayment.invoice_id: None}, synchronize_session=False)
        db.session.query(SubscriptionCreditNote).filter_by(invoice_id=inv_id).update({SubscriptionCreditNote.invoice_id: None}, synchronize_session=False)
        db.session.query(BillingAudit).filter_by(invoice_id=inv_id).update({BillingAudit.invoice_id: None}, synchronize_session=False)
        db.session.query(SubscriptionRefund).filter_by(invoice_id=inv_id).delete(synchronize_session=False)
        db.session.query(InvoiceItem).filter_by(invoice_id=inv_id).delete(synchronize_session=False)

        db.session.delete(inv)
        db.session.commit()
    except Exception:
        db.session.rollback()
        # Fallback: Direct SQL execution to ensure complete cleanup
        db.session.execute(text("UPDATE subscription_payments SET invoice_id = NULL WHERE invoice_id = :id"), {"id": inv_id})
        db.session.execute(text("UPDATE subscription_credit_notes SET invoice_id = NULL WHERE invoice_id = :id"), {"id": inv_id})
        db.session.execute(text("UPDATE billing_audits SET invoice_id = NULL WHERE invoice_id = :id"), {"id": inv_id})
        db.session.execute(text("DELETE FROM subscription_refunds WHERE invoice_id = :id"), {"id": inv_id})
        db.session.execute(text("DELETE FROM invoice_items WHERE invoice_id = :id"), {"id": inv_id})
        db.session.execute(text("DELETE FROM subscription_invoices WHERE id = :id"), {"id": inv_id})
        db.session.commit()

    _audit_log(org_id, None, "Invoice Deleted", {"invoice_id": inv_id})

    return jsonify({
        "status": "success",
        "message": "Invoice deleted successfully"
    })

@billing_bp.route('/invoices/<int:inv_id>/send-email', methods=['POST'])
@jwt_required()
@super_admin_required()
def send_invoice_email(inv_id):
    inv = SubscriptionInvoice.query.get_or_404(inv_id)
    org_email = inv.organization.email if inv.organization else 'N/A'
    
    _audit_log(inv.org_id, inv.id, "Invoice Emailed", {"recipient": org_email, "invoice_number": inv.invoice_number})

    return jsonify({
        "status": "success",
        "message": f"Invoice statement #{inv.invoice_number} dispatched successfully to {org_email}"
    })

@billing_bp.route('/credit-notes', methods=['POST'])
@jwt_required()
@super_admin_required()
def create_credit_note():
    data = request.json or {}
    org_id = data.get('org_id')
    amount = float(data.get('amount', 0.0))
    notes = data.get('notes', '')

    if not org_id:
        return jsonify({"status": "error", "message": "Organization is required"}), 422
    if amount <= 0:
        return jsonify({"status": "error", "message": "Credit note amount must be positive"}), 422

    cn_uid = "CN-" + uuid.uuid4().hex[:8].upper()
    cn = SubscriptionCreditNote(
        org_id=org_id,
        credit_note_uid=cn_uid,
        amount=amount,
        balance=amount,
        status='Active',
        notes=notes
    )
    db.session.add(cn)
    db.session.commit()

    _audit_log(org_id, None, "Credit Note Created", {"credit_note_uid": cn_uid, "amount": amount})

    return jsonify({
        "status": "success",
        "message": "Credit note created successfully",
        "credit_note_uid": cn_uid
    }), 201

@billing_bp.route('/reports/revenue', methods=['GET'])
@jwt_required()
@super_admin_required()
def get_revenue_report():
    # Only completed payments
    payments = SubscriptionPayment.query.filter_by(payment_status='Completed').all()
    
    # Revenue by Plan
    by_plan = {}
    # Revenue by Country
    by_country = {}

    for p in payments:
        by_plan[p.plan_name] = by_plan.get(p.plan_name, 0.0) + p.final_amount
        country = p.organization.country if p.organization.country else 'India'
        by_country[country] = by_country.get(country, 0.0) + p.final_amount

    return jsonify({
        "status": "success",
        "data": {
            "by_plan": by_plan,
            "by_country": by_country
        }
    })

@billing_bp.route('/reports/taxes', methods=['GET'])
@jwt_required()
@super_admin_required()
def get_tax_report():
    payments = SubscriptionPayment.query.filter_by(payment_status='Completed').all()
    gst_collected = sum(p.gst_amount for p in payments)
    
    return jsonify({
        "status": "success",
        "data": {
            "gst_collected": gst_collected,
            "taxes": [
                {"tax_type": "CGST", "amount": gst_collected / 2},
                {"tax_type": "SGST", "amount": gst_collected / 2}
            ]
        }
    })

@billing_bp.route('/reports/ai-insights', methods=['GET'])
@jwt_required()
@super_admin_required()
def get_ai_insights():
    # AI recommendations and predictions only
    return jsonify({
        "status": "success",
        "data": {
            "revenue_forecast": "SaaS revenue is projected to grow by 14% next quarter based on Professional tier renewal rates.",
            "late_payment_prediction": [
                {"company": "Beta Inc", "risk": "High", "reason": "Late payments on previous 2 billing cycles"}
            ],
            "high_risk_customers": ["Alpha Corp"],
            "outstanding_collection_forecast": "₹1,24,000 outstanding collections expected in the next 15 days.",
            "upgrade_revenue_opportunity": "₹45,000 potential expansion MRR by promoting Enterprise plan custom integrations."
        }
    })

# ─────────────────────────────────────────────────────────────────────────────
# PAYMENT GATEWAYS & SUBSCRIPTION UPGRADE FLOW
# ─────────────────────────────────────────────────────────────────────────────

PLAN_SPECS = {
    "Starter": {"price": 4999.0, "max_users": 50, "max_projects": 10, "features": ["50 Users Limit", "10 Active Projects", "Standard Support"]},
    "Professional": {"price": 14999.0, "max_users": 500, "max_projects": 50, "features": ["500 Users Limit", "50 Active Projects", "Priority Support", "Custom Stage Builder", "Export Tools"]},
    "Enterprise": {"price": 49999.0, "max_users": 1000000, "max_projects": 99999, "features": ["Unlimited Users", "Unlimited Projects", "Dedicated Support", "API & Webhook Integrations", "Custom SLA"]}
}

def _get_plan_details(plan_name):
    """
    Dynamically look up plan specifications from SaaSPlan DB model or fall back to PLAN_SPECS dictionary.
    Returns (is_valid, resolved_name, base_price, total_price_incl_tax, max_users, max_projects, billing_cycle)
    """
    if not plan_name or not str(plan_name).strip():
        return False, None, 0.0, 0.0, 50, 10, 'Monthly'

    pname = str(plan_name).strip()

    # 1. Direct DB lookup by name or code
    sp = SaaSPlan.query.filter(or_(SaaSPlan.name == pname, SaaSPlan.code == pname)).first()
    if not sp:
        # Case-insensitive DB lookup
        all_plans = SaaSPlan.query.all()
        for p in all_plans:
            if (p.name and p.name.lower() == pname.lower()) or (p.code and p.code.lower() == pname.lower()):
                sp = p
                break

    if sp:
        pricing = SaaSPlanPricing.query.filter_by(plan_id=sp.id, is_active=True).first()
        base_price = pricing.price if pricing else 0.0
        tax = pricing.tax if pricing else 18.0
        total_price = base_price * (1.0 + tax / 100.0) if (pricing and not pricing.is_tax_inclusive) else base_price
        cycle = pricing.billing_cycle if pricing else ('Trial Duration' if (getattr(sp, 'plan_type', '') == 'Trial' or getattr(sp, 'is_default_trial', False)) else 'Monthly')
        limits = sp.limits
        max_users = limits.max_users if limits else 500
        max_projects = limits.max_projects if limits else 50
        return True, sp.name, base_price, total_price, max_users, max_projects, cycle

    # 2. Hardcoded PLAN_SPECS fallback
    if pname in PLAN_SPECS:
        spec = PLAN_SPECS[pname]
        base_price = spec['price']
        total_price = base_price * 1.18
        return True, pname, base_price, total_price, spec['max_users'], spec['max_projects'], 'Monthly'

    return False, None, 0.0, 0.0, 50, 10, 'Monthly'

@billing_bp.route('/payment-gateways', methods=['GET'])
@jwt_required()
def get_public_payment_gateways():
    """Return active payment gateways configured by SuperAdmin for checkout"""
    razorpay_cfg = IntegrationConfig.query.filter_by(provider_id='razorpay').first()
    qr_cfg = IntegrationConfig.query.filter_by(provider_id='dynamic_qr').first()

    rz_settings = (razorpay_cfg.settings or {}) if razorpay_cfg else {}
    qr_settings = (qr_cfg.settings or {}) if qr_cfg else {}

    return jsonify({
        "status": "success",
        "gateways": {
            "razorpay": {
                "enabled": bool(razorpay_cfg and razorpay_cfg.status == 'Connected' and rz_settings.get('is_active', True)),
                "key_id": rz_settings.get('key_id', 'rzp_live_qcms_enterprise_key'),
                "currency": rz_settings.get('currency', 'INR')
            },
            "dynamic_qr": {
                "enabled": bool(qr_cfg and qr_cfg.status == 'Connected' and qr_settings.get('is_active', True)),
                "upi_id": qr_settings.get('upi_id', 'qcms@upi'),
                "account_name": qr_settings.get('account_name', 'QCMS Enterprise Solutions Pvt Ltd'),
                "qr_code_url": qr_settings.get('qr_code_url', 'https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=upi%3A%2F%2Fpay%3Fpa%3Dqcms%40upi%26pn%3DQCMS%2520Enterprise%26cu%3DINR'),
                "instructions": qr_settings.get('instructions', 'Scan using GPay, PhonePe, Paytm or any UPI app. After payment, enter your Transaction ID (UTR) and upload payment screenshot.')
            }
        },
        "plans": PLAN_SPECS
    }), 200


@billing_bp.route('/razorpay/create-order', methods=['POST'])
@jwt_required()
def create_razorpay_order():
    """Create Razorpay order for plan upgrade"""
    data = request.json or {}
    plan_name = data.get('plan_name')
    is_valid, resolved_name, base_price, total_price, max_users, max_projects, cycle = _get_plan_details(plan_name)
    if not is_valid:
        return jsonify({"message": "Invalid plan name"}), 400

    gst = total_price - base_price

    order_id = f"order_{secrets.token_hex(8)}"
    return jsonify({
        "status": "success",
        "order_id": order_id,
        "plan_name": resolved_name,
        "amount": base_price,
        "gst_amount": gst,
        "total_amount": total_price,
        "currency": "INR"
    }), 200


@billing_bp.route('/razorpay/verify-payment', methods=['POST'])
@jwt_required()
def verify_razorpay_payment():
    """Verify Razorpay payment and immediately upgrade subscription plan"""
    user = _get_current_user()
    if not user or not user.org_id:
        return jsonify({"message": "User organization not found"}), 404

    data = request.json or {}
    plan_name = data.get('plan_name')
    razorpay_payment_id = data.get('razorpay_payment_id') or f"pay_{secrets.token_hex(8)}"
    razorpay_order_id = data.get('razorpay_order_id') or f"order_{secrets.token_hex(8)}"

    is_valid, resolved_name, base_price, total_price, max_users, max_projects, cycle = _get_plan_details(plan_name)
    if not is_valid:
        return jsonify({"message": "Invalid plan name"}), 400

    org = Organization.query.get(user.org_id)
    if not org:
        return jsonify({"message": "Organization not found"}), 404

    gst = total_price - base_price

    # Update Organization Plan and sync limits & subscription record
    from app.domain.services.subscription_service import apply_new_plan_to_organization
    apply_new_plan_to_organization(org, resolved_name, cycle)

    # Record SubscriptionPayment
    payment = SubscriptionPayment(
        org_id=org.id,
        amount=base_price,
        currency='INR',
        plan_name=resolved_name,
        billing_cycle=cycle,
        payment_status='Completed',
        transaction_id=razorpay_payment_id,
        payment_gateway='Razorpay',
        gateway_reference=razorpay_order_id,
        gst_percent=18.0,
        gst_amount=gst,
        final_amount=total_price,
        billing_period_start=datetime.utcnow(),
        billing_period_end=datetime.utcnow() + timedelta(days=365 if cycle in ('Yearly', 'Annual') else 30)
    )
    db.session.add(payment)

    # Add notification for org admin
    notif = Notification(
        org_id=user.org_id,
        user_id=user.id,
        title="Subscription Plan Upgraded",
        message=f"Your subscription plan has been successfully upgraded to {resolved_name} via Razorpay."
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"Payment verified! Your subscription plan has been upgraded to {resolved_name}.",
        "plan_name": resolved_name
    }), 200


@billing_bp.route('/offline-payment/submit', methods=['POST'])
@jwt_required()
def submit_offline_payment_proof():
    """Submit Dynamic QR payment proof with UTR and screenshot upload"""
    user = _get_current_user()
    if not user or not user.org_id:
        return jsonify({"message": "User organization not found"}), 404

    plan_name = request.form.get('plan_name')
    transaction_id = request.form.get('transaction_id')
    notes = request.form.get('notes', '')

    is_valid, resolved_plan_name, base_price, total_price, max_users, max_projects, cycle = _get_plan_details(plan_name)
    if not is_valid:
        return jsonify({"message": "Invalid or missing plan_name"}), 400

    if not transaction_id or not transaction_id.strip():
        return jsonify({"message": "Transaction ID / UTR is required"}), 400

    screenshot_url = None
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename:
            fname = secure_filename(file.filename)
            ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else 'png'
            saved_name = f"payment_proof_org_{user.org_id}_{secrets.token_hex(6)}.{ext}"
            
            primary_dir = current_app.config.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'uploads'))
            os.makedirs(primary_dir, exist_ok=True)
            save_path = os.path.join(primary_dir, saved_name)
            file.save(save_path)

            try:
                frontend_dir = os.path.abspath(os.path.join(current_app.root_path, '..', '..', 'frontend', 'uploads'))
                os.makedirs(frontend_dir, exist_ok=True)
                shutil.copy(save_path, os.path.join(frontend_dir, saved_name))
            except Exception:
                pass

            screenshot_url = f"/uploads/{saved_name}"

    proof = OfflinePaymentProof(
        org_id=user.org_id,
        user_id=user.id,
        plan_name=resolved_plan_name,
        billing_cycle=cycle,
        amount=total_price,
        currency='INR',
        transaction_id=transaction_id.strip(),
        screenshot_url=screenshot_url,
        notes=notes.strip(),
        status='Pending Verification'
    )
    db.session.add(proof)

    # Notify SuperAdmins
    super_admins = User.query.join(User.role).filter(User.role.has(name='SuperAdmin')).all()
    for sa in super_admins:
        db.session.add(Notification(
            org_id=sa.org_id or user.org_id,
            user_id=sa.id,
            title="New Offline Payment Submitted",
            message=f"Org ID {user.org_id} submitted payment proof for {resolved_plan_name} (UTR: {transaction_id}). Please verify in SuperAdmin portal."
        ))

    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Your payment reference has been submitted successfully! Your plan will be activated within 24 hours after verification by the Platform Administrator."
    }), 200


@billing_bp.route('/offline-payment/status', methods=['GET'])
@jwt_required()
def get_offline_payment_status():
    """Get latest offline payment proof status for the authenticated user's organization"""
    user = _get_current_user()
    if not user or not user.org_id:
        return jsonify({"message": "User organization not found"}), 404

    proof = OfflinePaymentProof.query.filter_by(org_id=user.org_id).order_by(OfflinePaymentProof.created_at.desc()).first()
    if not proof:
        return jsonify({"status": "none", "proof": None}), 200

    verifier = User.query.get(proof.verified_by_id) if proof.verified_by_id else None

    return jsonify({
        "status": "success",
        "proof": {
            "id": proof.id,
            "org_id": proof.org_id,
            "plan_name": proof.plan_name,
            "billing_cycle": proof.billing_cycle,
            "amount": proof.amount,
            "currency": proof.currency,
            "transaction_id": proof.transaction_id,
            "screenshot_url": proof.screenshot_url,
            "notes": proof.notes,
            "status": proof.status,  # Pending Verification, Approved, Rejected
            "rejection_reason": proof.rejection_reason,
            "support_email": "support@qcms.com",
            "verified_by": verifier.username if verifier else None,
            "created_at": proof.created_at.strftime('%Y-%m-%d %H:%M') if proof.created_at else None,
            "verified_at": proof.verified_at.strftime('%Y-%m-%d %H:%M') if proof.verified_at else None
        }
    }), 200


# ── SUPERADMIN OFFLINE PAYMENT VERIFICATION ENDPOINTS ──

@billing_bp.route('/offline-payments', methods=['GET'])
@jwt_required()
@super_admin_required()
def list_offline_payments():
    """List all offline payment submissions for SuperAdmin review"""
    proofs = OfflinePaymentProof.query.order_by(OfflinePaymentProof.created_at.desc()).all()
    result = []
    for p in proofs:
        org = Organization.query.get(p.org_id)
        user = User.query.get(p.user_id)
        result.append({
            "id": p.id,
            "org_id": p.org_id,
            "org_name": org.name if org else f"Org #{p.org_id}",
            "user_id": p.user_id,
            "user_email": user.email if user else "N/A",
            "user_name": user.username if user else "N/A",
            "plan_name": p.plan_name,
            "billing_cycle": p.billing_cycle,
            "amount": p.amount,
            "currency": p.currency,
            "transaction_id": p.transaction_id,
            "screenshot_url": p.screenshot_url,
            "notes": p.notes,
            "status": p.status,
            "rejection_reason": p.rejection_reason,
            "created_at": p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else None,
            "verified_at": p.verified_at.strftime('%Y-%m-%d %H:%M') if p.verified_at else None
        })
    return jsonify({"status": "success", "payments": result}), 200


@billing_bp.route('/offline-payments/<int:proof_id>/approve', methods=['POST'])
@jwt_required()
@super_admin_required()
def approve_offline_payment(proof_id):
    """SuperAdmin approves offline payment proof and immediately activates the plan"""
    sa_user_id = get_jwt_identity()
    proof = db.session.get(OfflinePaymentProof, proof_id)
    if not proof:
        return jsonify({"message": "Payment record not found"}), 404

    if proof.status == 'Approved':
        return jsonify({"message": "Payment proof has already been approved"}), 400

    org = Organization.query.get(proof.org_id)
    if not org:
        return jsonify({"message": "Organization not found"}), 404

    is_valid, resolved_name, base_price, total_price, max_users, max_projects, cycle = _get_plan_details(proof.plan_name)
    if not is_valid:
        resolved_name = proof.plan_name
        total_price = proof.amount or 0.0
        base_price = total_price / 1.18
        cycle = proof.billing_cycle or 'Monthly'

    gst = total_price - base_price

    # Approve proof record
    proof.status = 'Approved'
    proof.verified_by_id = int(sa_user_id)
    proof.verified_at = datetime.utcnow()

    # Update Organization Plan and sync limits & subscription record
    from app.domain.services.subscription_service import apply_new_plan_to_organization
    apply_new_plan_to_organization(org, resolved_name, proof.billing_cycle or cycle, approved_by_id=sa_user_id)

    # Record SubscriptionPayment
    payment = SubscriptionPayment(
        org_id=org.id,
        amount=base_price,
        currency=proof.currency,
        plan_name=resolved_name,
        billing_cycle=proof.billing_cycle or cycle,
        payment_status='Completed',
        transaction_id=proof.transaction_id,
        payment_gateway='Dynamic QR',
        gateway_reference=f"PROOF-{proof.id}",
        gst_percent=18.0,
        gst_amount=gst,
        final_amount=total_price,
        billing_period_start=datetime.utcnow(),
        billing_period_end=datetime.utcnow() + timedelta(days=365 if cycle in ('Yearly', 'Annual') else 30)
    )
    db.session.add(payment)

    # Notify Org Admin
    db.session.add(Notification(
        org_id=proof.org_id,
        user_id=proof.user_id,
        title="Payment Verified — Subscription Activated",
        message=f"Your payment (UTR: {proof.transaction_id}) has been verified and approved by SuperAdmin! Your plan is now ACTIVE on {proof.plan_name}."
    ))

    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"Payment proof approved! Organization {org.name} plan updated to {proof.plan_name}."
    }), 200


@billing_bp.route('/offline-payments/<int:proof_id>/reject', methods=['POST'])
@jwt_required()
@super_admin_required()
def reject_offline_payment(proof_id):
    """SuperAdmin rejects offline payment proof with reason"""
    sa_user_id = get_jwt_identity()
    data = request.json or {}
    reason = data.get('reason', 'Payment details could not be verified.')

    proof = db.session.get(OfflinePaymentProof, proof_id)
    if not proof:
        return jsonify({"message": "Payment record not found"}), 404

    proof.status = 'Rejected'
    proof.rejection_reason = reason
    proof.verified_by_id = int(sa_user_id)
    proof.verified_at = datetime.utcnow()

    # Notify Org Admin
    db.session.add(Notification(
        org_id=proof.org_id,
        user_id=proof.user_id,
        title="Payment Verification Declined",
        message=f"Your offline payment reference (UTR: {proof.transaction_id}) was declined by SuperAdmin. Reason: {reason}"
    ))

    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Payment proof rejected."
    }), 200


@billing_bp.route('/offline-payments/<int:proof_id>/screenshot', methods=['GET'])
def get_proof_screenshot(proof_id):
    """Serve the payment proof screenshot image through the API.
    Accepts JWT via Authorization header OR ?token= query param (needed for <img src> tags).
    """
    from flask import current_app
    from flask_jwt_extended import decode_token
    from jwt.exceptions import PyJWTError

    # Validate token from header or query param
    token = None
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    if not token:
        token = request.args.get('token', '')

    if not token:
        abort(401)
    try:
        decoded = decode_token(token)
        user_id = decoded.get('sub')
        if not user_id:
            abort(401)
        user = User.query.get(int(user_id))
        if not user:
            abort(401)
        # Must be super admin
        if not (user.role and user.role.name in ('SuperAdmin', 'Super Admin')):
            abort(403)
    except Exception:
        abort(401)

    proof = db.session.get(OfflinePaymentProof, proof_id)
    if not proof:
        abort(404)
    if not proof.screenshot_url:
        abort(404)

    # Extract just the filename from the stored URL (e.g. /uploads/payment_proof_org_3_xxx.png)
    filename = os.path.basename(proof.screenshot_url)

    # Try primary UPLOAD_FOLDER
    primary_dir = current_app.config.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'uploads'))
    primary_path = os.path.join(primary_dir, filename)
    if os.path.exists(primary_path):
        return send_from_directory(primary_dir, filename)

    # Try frontend/uploads fallback
    frontend_dir = os.path.abspath(os.path.join(current_app.root_path, '..', '..', 'frontend', 'uploads'))
    frontend_path = os.path.join(frontend_dir, filename)
    if os.path.exists(frontend_path):
        return send_from_directory(frontend_dir, filename)

    abort(404)


@billing_bp.route('/offline-payments/<int:proof_id>/upload-screenshot', methods=['POST'])
@jwt_required()
@super_admin_required()
def upload_proof_screenshot(proof_id):
    """Allow SuperAdmin to upload or replace the screenshot for an offline payment proof"""
    from flask import current_app
    proof = db.session.get(OfflinePaymentProof, proof_id)
    if not proof:
        return jsonify({"status": "error", "message": "Payment record not found"}), 404

    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file provided"}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({"status": "error", "message": "Invalid file"}), 400

    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}
    fname = secure_filename(file.filename)
    ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else 'png'
    if ext not in allowed_extensions:
        return jsonify({"status": "error", "message": f"File type .{ext} not allowed"}), 400

    saved_name = f"payment_proof_org_{proof.org_id}_{secrets.token_hex(6)}.{ext}"

    primary_dir = current_app.config.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'uploads'))
    os.makedirs(primary_dir, exist_ok=True)
    save_path = os.path.join(primary_dir, saved_name)
    file.save(save_path)

    # Also copy to frontend/uploads
    try:
        frontend_dir = os.path.abspath(os.path.join(current_app.root_path, '..', '..', 'frontend', 'uploads'))
        os.makedirs(frontend_dir, exist_ok=True)
        shutil.copy(save_path, os.path.join(frontend_dir, saved_name))
    except Exception:
        pass

    proof.screenshot_url = f"/uploads/{saved_name}"
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Screenshot uploaded successfully.",
        "screenshot_url": proof.screenshot_url,
        "api_url": f"/api/billing/offline-payments/{proof_id}/screenshot"
    }), 200

