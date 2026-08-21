"""
Centralized Financial Metrics Engine (Single Source of Truth)
Unified Financial Ledger & Analytics Engine for QCMS Enterprise OS.
"""

from datetime import datetime, timedelta
from sqlalchemy import func, or_
from app.infrastructure.database.models.models import (
    db, Organization, Subscription, SubscriptionPayment, SubscriptionInvoice, SubscriptionRefund, SaaSPlan, SaaSPlanPricing
)

class FinancialMetricsEngine:
    @classmethod
    def get_consolidated_kpis(cls, org_id=None, date_range=None):
        """
        Calculates unified, non-redundant, cross-module financial KPIs.
        
        Single Source of Truth Rules:
        - total_revenue: Sum of completed SubscriptionPayment final_amount + issued/paid SubscriptionInvoice total_amount (minus approved refunds).
          Excludes platform/test organizations (is_platform_org == True).
        - mrr: Contractual MRR from active subscriptions plus active monthly PAYG metered usage.
        - arr: mrr * 12.
        - monthly_cash_collected: Completed payments/invoices in current calendar month.
        - outstanding_due: Sum of unpaid invoices with status in ['Sent', 'Overdue'].
        - unpaid_invoices_count: Count of overdue or pending sent invoices.
        - paid_invoices_count: Count of invoices with status 'Paid'.
        - taxes_collected: Sum of gst_amount on completed payments.
        - collection_rate: (paid_invoices / (paid_invoices + unpaid_invoices)) * 100.
        """
        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)

        # Exclude platform organizations
        platform_org_ids = [
            r[0] for r in db.session.query(Organization.id).filter(Organization.is_platform_org == True).all()
        ]

        def _apply_org_filter(q, model):
            if org_id:
                q = q.filter(getattr(model, 'org_id') == org_id)
            if platform_org_ids:
                q = q.filter(~getattr(model, 'org_id').in_(platform_org_ids))
            return q

        # 1. Total Revenue (Strictly Completed/Paid Payments + Unlinked Paid Invoices - Refunds)
        pay_q = _apply_org_filter(
            db.session.query(func.sum(SubscriptionPayment.final_amount)).filter(
                SubscriptionPayment.payment_status.in_(['Completed', 'Paid', 'SUCCESS'])
            ),
            SubscriptionPayment
        )
        total_payment_rev = float(pay_q.scalar() or 0.0)

        # Standalone Paid Invoices (marked Paid without a linked SubscriptionPayment record to prevent double-counting)
        paid_inv_q = db.session.query(func.sum(SubscriptionInvoice.total_amount)).filter(
            SubscriptionInvoice.invoice_status.in_(['Paid', 'Completed', 'PAID']),
            SubscriptionInvoice.payment_id == None
        )
        if org_id:
            paid_inv_q = paid_inv_q.filter(SubscriptionInvoice.org_id == org_id)
        if platform_org_ids:
            paid_inv_q = paid_inv_q.filter(~SubscriptionInvoice.org_id.in_(platform_org_ids))
        standalone_paid_invoices = float(paid_inv_q.scalar() or 0.0)

        refund_sum = 0.0
        try:
            ref_q = db.session.query(func.sum(SubscriptionRefund.amount))
            if org_id:
                ref_q = ref_q.filter(SubscriptionRefund.org_id == org_id)
            refund_sum = float(ref_q.scalar() or 0.0)
        except Exception:
            refund_sum = 0.0

        total_revenue = max(0.0, round(total_payment_rev + standalone_paid_invoices - refund_sum, 2))

        # 2. Monthly Cash Collected (Strictly Completed Paid Revenue in Current Calendar Month)
        month_pay_q = _apply_org_filter(
            db.session.query(func.sum(SubscriptionPayment.final_amount)).filter(
                SubscriptionPayment.payment_status.in_(['Completed', 'Paid', 'SUCCESS']),
                SubscriptionPayment.created_at >= month_start
            ),
            SubscriptionPayment
        )
        month_paid_inv_q = db.session.query(func.sum(SubscriptionInvoice.total_amount)).filter(
            SubscriptionInvoice.invoice_status.in_(['Paid', 'Completed', 'PAID']),
            SubscriptionInvoice.payment_id == None,
            SubscriptionInvoice.created_at >= month_start
        )
        if org_id:
            month_paid_inv_q = month_paid_inv_q.filter(SubscriptionInvoice.org_id == org_id)
        if platform_org_ids:
            month_paid_inv_q = month_paid_inv_q.filter(~SubscriptionInvoice.org_id.in_(platform_org_ids))

        monthly_cash_collected = round(float(month_pay_q.scalar() or 0.0) + float(month_paid_inv_q.scalar() or 0.0), 2)

        # 3. Taxes Collected (GST/Tax sum)
        tax_q = _apply_org_filter(
            db.session.query(func.sum(SubscriptionPayment.gst_amount)).filter(
                SubscriptionPayment.payment_status.in_(['Completed', 'Paid', 'SUCCESS'])
            ),
            SubscriptionPayment
        )
        taxes_collected = round(float(tax_q.scalar() or 0.0), 2)

        # 4. Invoices Metrics (Outstanding Due, Paid/Unpaid Counts, Collection Rate)
        inv_base = SubscriptionInvoice.query
        if org_id:
            inv_base = inv_base.filter_by(org_id=org_id)
        if platform_org_ids:
            inv_base = inv_base.filter(~SubscriptionInvoice.org_id.in_(platform_org_ids))

        paid_invoices_count = inv_base.filter(
            SubscriptionInvoice.invoice_status.in_(['Paid', 'PAID', 'Completed'])
        ).count()

        unpaid_invoices_q = inv_base.filter(
            SubscriptionInvoice.invoice_status.in_(['Sent', 'SENT', 'Overdue', 'OVERDUE', 'Issued'])
        )
        unpaid_invoices_count = unpaid_invoices_q.count()

        out_q = db.session.query(func.sum(SubscriptionInvoice.total_amount)).filter(
            SubscriptionInvoice.invoice_status.in_(['Sent', 'SENT', 'Overdue', 'OVERDUE', 'Issued'])
        )
        if org_id:
            out_q = out_q.filter(SubscriptionInvoice.org_id == org_id)
        if platform_org_ids:
            out_q = out_q.filter(~SubscriptionInvoice.org_id.in_(platform_org_ids))
        outstanding_due = round(float(out_q.scalar() or 0.0), 2)

        total_issued = paid_invoices_count + unpaid_invoices_count
        collection_rate = round((paid_invoices_count / float(total_issued)) * 100.0, 1) if total_issued > 0 else 100.0

        # 5. MRR & ARR Calculations
        sub_q = Subscription.query.filter(
            Subscription.subscription_status.in_(['Active', 'Trialing', 'Trial', 'ACTIVE'])
        )
        if org_id:
            sub_q = sub_q.filter_by(org_id=org_id)
        if platform_org_ids:
            sub_q = sub_q.filter(~Subscription.org_id.in_(platform_org_ids))

        mrr_val = 0.0
        upgrade_revenue = 0.0
        renewal_revenue = 0.0

        from app.domain.services.payg_billing_service import PaygBillingService

        for s in sub_q.all():
            bcycle = (s.billing_cycle or 'Monthly').lower()
            months = 12 if ('year' in bcycle or 'annual' in bcycle) else (3 if 'quarter' in bcycle else 1)

            is_payg = (s.pricing_model or '').lower() == 'pay_as_you_go' or (s.plan_name or '').lower() == 'pay-as-you-go'
            if is_payg:
                latest_inv = SubscriptionInvoice.query.filter_by(org_id=s.org_id).order_by(SubscriptionInvoice.created_at.desc()).first()
                if latest_inv and latest_inv.total_amount:
                    payg_amt = float(latest_inv.total_amount)
                else:
                    try:
                        brk = PaygBillingService.calculate_payg_bill_breakdown(s.org_id)
                        payg_amt = float(brk.get('total_amount', 0.0))
                    except Exception:
                        payg_amt = 0.0
                mrr_val += payg_amt
                renewal_revenue += payg_amt
            else:
                amt = float((s.final_amount if s.final_amount is not None else 0.0))
                if amt == 0.0:
                    latest_pmt = SubscriptionPayment.query.filter(
                        SubscriptionPayment.org_id == s.org_id,
                        SubscriptionPayment.payment_status.in_(['Completed', 'Paid', 'SUCCESS'])
                    ).order_by(SubscriptionPayment.created_at.desc()).first()
                    latest_inv = SubscriptionInvoice.query.filter_by(org_id=s.org_id).order_by(SubscriptionInvoice.created_at.desc()).first()
                    if latest_pmt and (latest_pmt.final_amount or latest_pmt.amount):
                        amt = float(latest_pmt.final_amount or latest_pmt.amount)
                    elif latest_inv and latest_inv.total_amount:
                        amt = float(latest_inv.total_amount)

                bprice = float((s.base_price if s.base_price is not None else 0.0))
                mrr_val += amt / months
                if amt > bprice and bprice > 0:
                    upgrade_revenue += (amt - bprice)
                renewal_revenue += amt

        mrr = round(mrr_val, 2)
        arr = round(mrr * 12, 2)

        # 6. Monthly Trends (Past 6 Months)
        bucket_data = {}
        month_cursor = (now.replace(day=1) - timedelta(days=150)).replace(day=1)
        end_cursor = now.replace(day=1)
        
        while month_cursor <= end_cursor:
            lbl = month_cursor.strftime('%b %Y')
            bucket_data[lbl] = 0.0
            month_cursor = (month_cursor.replace(day=28) + timedelta(days=4)).replace(day=1)

        pmts_trend = _apply_org_filter(
            SubscriptionPayment.query.filter(SubscriptionPayment.payment_status.in_(['Completed', 'Paid', 'SUCCESS'])),
            SubscriptionPayment
        ).all()
        for p in pmts_trend:
            if p.created_at:
                lbl = p.created_at.strftime('%b %Y')
                amt = float((p.final_amount if p.final_amount is not None else p.amount) or 0.0)
                if lbl in bucket_data:
                    bucket_data[lbl] += amt

        invs_trend = SubscriptionInvoice.query.filter(
            SubscriptionInvoice.invoice_status.in_(['Paid', 'Completed', 'PAID']),
            SubscriptionInvoice.payment_id == None
        )
        if org_id:
            invs_trend = invs_trend.filter_by(org_id=org_id)
        if platform_org_ids:
            invs_trend = invs_trend.filter(~SubscriptionInvoice.org_id.in_(platform_org_ids))
        
        for inv in invs_trend.all():
            if inv.created_at:
                lbl = inv.created_at.strftime('%b %Y')
                amt = float(inv.total_amount or 0.0)
                if lbl in bucket_data:
                    bucket_data[lbl] += amt

        trend_labels = list(bucket_data.keys())
        trend_values = [round(v, 2) for v in bucket_data.values()]

        # Forecast
        forecast_labels = []
        forecast_values = []
        if len(trend_values) >= 2:
            xs = list(range(len(trend_values)))
            ys = trend_values
            mean_x = sum(xs) / len(xs)
            mean_y = sum(ys) / len(ys)
            num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(len(xs)))
            den = sum((xs[i] - mean_x) ** 2 for i in range(len(xs)))
            slope = num / den if den != 0 else 0.0
            intercept = mean_y - slope * mean_x
            
            last_lbl = trend_labels[-1]
            try:
                last_date = datetime.strptime(last_lbl, '%b %Y')
            except ValueError:
                last_date = datetime.utcnow()

            for i in range(1, 4):
                nxt = (last_date.replace(day=28) + timedelta(days=30 * i)).replace(day=1)
                forecast_labels.append(nxt.strftime('%b %Y'))
                forecast_values.append(max(0.0, round(slope * (len(xs) - 1 + i) + intercept, 2)))
        else:
            forecast_labels = ['Sep 2026', 'Oct 2026', 'Nov 2026']
            forecast_values = [mrr] * 3

        return {
            "total_revenue": total_revenue,
            "mrr": mrr,
            "arr": arr,
            "monthly_cash_collected": monthly_cash_collected,
            "outstanding_due": outstanding_due,
            "unpaid_invoices_count": unpaid_invoices_count,
            "paid_invoices_count": paid_invoices_count,
            "taxes_collected": taxes_collected,
            "collection_rate": collection_rate,
            "upgrades": round(upgrade_revenue, 2),
            "renewals": round(renewal_revenue, 2),
            "trends": {"labels": trend_labels, "values": trend_values},
            "forecast": {"labels": forecast_labels, "values": forecast_values}
        }
