"""
Centralized Financial Metrics Engine (Single Source of Truth)
Unified Financial Ledger & Analytics Engine for QCMS Enterprise OS.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import func, or_
from app.infrastructure.database.models.models import (
    db, Organization, Subscription, SubscriptionPayment, SubscriptionInvoice, SubscriptionRefund, SaaSPlan, SaaSPlanPricing
)

class FinancialMetricsEngine:
    @classmethod
    def get_consolidated_kpis(cls, org_id=None, date_range=None, start_date=None, end_date=None, date_range_name=None):
        """
        Calculates unified, non-redundant, cross-module financial KPIs.
        
        Single Source of Truth Rules:
        - total_revenue: Sum of completed SubscriptionPayment final_amount + issued/paid SubscriptionInvoice total_amount within selected period (minus refunds).
        - all_time_revenue: Cumulative all-time revenue across all paid subscriptions.
        - mrr: Contractual MRR from active subscriptions plus active monthly PAYG metered usage.
        - arr: mrr * 12.
        - trends: Dynamically bucketed revenue series matching the requested date range.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if not end_date:
            end_date = now
        if not start_date:
            start_date = now - timedelta(days=30)
            
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

        # 1. Total Revenue in Filter Period
        pay_period_q = _apply_org_filter(
            db.session.query(func.sum(SubscriptionPayment.final_amount)).filter(
                SubscriptionPayment.payment_status.in_(['Completed', 'Paid', 'SUCCESS']),
                SubscriptionPayment.created_at >= start_date,
                SubscriptionPayment.created_at <= end_date
            ),
            SubscriptionPayment
        )
        period_payment_rev = float(pay_period_q.scalar() or 0.0)

        paid_inv_period_q = db.session.query(func.sum(SubscriptionInvoice.total_amount)).filter(
            SubscriptionInvoice.invoice_status.in_(['Paid', 'Completed', 'PAID']),
            SubscriptionInvoice.payment_id == None,
            SubscriptionInvoice.created_at >= start_date,
            SubscriptionInvoice.created_at <= end_date
        )
        if org_id:
            paid_inv_period_q = paid_inv_period_q.filter(SubscriptionInvoice.org_id == org_id)
        if platform_org_ids:
            paid_inv_period_q = paid_inv_period_q.filter(~SubscriptionInvoice.org_id.in_(platform_org_ids))
        period_invoice_rev = float(paid_inv_period_q.scalar() or 0.0)

        refund_sum = 0.0
        try:
            ref_q = db.session.query(func.sum(SubscriptionRefund.amount)).filter(
                SubscriptionRefund.created_at >= start_date,
                SubscriptionRefund.created_at <= end_date
            )
            if org_id:
                ref_q = ref_q.filter(SubscriptionRefund.org_id == org_id)
            refund_sum = float(ref_q.scalar() or 0.0)
        except Exception:
            refund_sum = 0.0

        total_revenue = max(0.0, round(period_payment_rev + period_invoice_rev - refund_sum, 2))

        # 1b. All-Time Revenue (for fallback or cumulative stats)
        all_time_pay_q = _apply_org_filter(
            db.session.query(func.sum(SubscriptionPayment.final_amount)).filter(
                SubscriptionPayment.payment_status.in_(['Completed', 'Paid', 'SUCCESS'])
            ),
            SubscriptionPayment
        )
        all_time_inv_q = db.session.query(func.sum(SubscriptionInvoice.total_amount)).filter(
            SubscriptionInvoice.invoice_status.in_(['Paid', 'Completed', 'PAID']),
            SubscriptionInvoice.payment_id == None
        )
        if org_id:
            all_time_inv_q = all_time_inv_q.filter(SubscriptionInvoice.org_id == org_id)
        if platform_org_ids:
            all_time_inv_q = all_time_inv_q.filter(~SubscriptionInvoice.org_id.in_(platform_org_ids))
        all_time_revenue = max(0.0, round(float(all_time_pay_q.scalar() or 0.0) + float(all_time_inv_q.scalar() or 0.0), 2))

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

        # 3. Taxes Collected (GST/Tax sum in period)
        tax_q = _apply_org_filter(
            db.session.query(func.sum(SubscriptionPayment.gst_amount)).filter(
                SubscriptionPayment.payment_status.in_(['Completed', 'Paid', 'SUCCESS']),
                SubscriptionPayment.created_at >= start_date,
                SubscriptionPayment.created_at <= end_date
            ),
            SubscriptionPayment
        )
        taxes_collected = round(float(tax_q.scalar() or 0.0), 2)

        # 4. Invoices Metrics
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
                # Prioritize SaaSPlan configured pricing if s.final_amount is 0.0
                if amt == 0.0 and s.plan_name and s.plan_name.strip().lower() not in ('trial', 'trialing', 'default trial plan', ''):
                    sp = SaaSPlan.query.filter(
                        or_(
                            func.lower(func.trim(SaaSPlan.name)) == s.plan_name.strip().lower(),
                            func.lower(func.trim(SaaSPlan.code)) == s.plan_name.strip().lower()
                        )
                    ).first()
                    if sp:
                        pricing = SaaSPlanPricing.query.filter_by(plan_id=sp.id, is_active=True).first()
                        if pricing and pricing.price:
                            amt = float(pricing.price)
                            cycle_name = (pricing.billing_cycle or bcycle).lower()
                            months = 12 if ('year' in cycle_name or 'annual' in cycle_name) else (3 if 'quarter' in cycle_name else 1)

                # Fallback to payments or invoices only if plan has no configured pricing
                if amt == 0.0 and s.plan_name and s.plan_name.strip().lower() not in ('trial', 'trialing', 'default trial plan', ''):
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
                if bprice == 0.0:
                    bprice = amt
                mrr_val += amt / months
                if amt > bprice and bprice > 0:
                    upgrade_revenue += (amt - bprice)
                renewal_revenue += amt

        # Also account for customer organizations with active paid plans that may not have a Subscription row yet
        customer_orgs = Organization.query.filter(
            Organization.is_deleted == False,
            Organization.is_platform_org == False
        )
        if org_id:
            customer_orgs = customer_orgs.filter_by(id=org_id)
        existing_sub_org_ids = set(s.org_id for s in sub_q.all() if s.org_id)
        
        for org_item in customer_orgs.all():
            if org_item.id not in existing_sub_org_ids:
                p_name = (org_item.subscription_plan or '').strip()
                if p_name and p_name.lower() not in ('trial', 'trialing', 'default trial plan', ''):
                    sp = SaaSPlan.query.filter(
                        or_(
                            func.lower(func.trim(SaaSPlan.name)) == p_name.lower(),
                            func.lower(func.trim(SaaSPlan.code)) == p_name.lower()
                        )
                    ).first()
                    if sp:
                        pricing = SaaSPlanPricing.query.filter_by(plan_id=sp.id, is_active=True).first()
                        if pricing and pricing.price:
                            p_amt = float(pricing.price)
                            cycle_name = (pricing.billing_cycle or 'Monthly').lower()
                            months = 12 if ('year' in cycle_name or 'annual' in cycle_name) else (3 if 'quarter' in cycle_name else 1)
                            mrr_val += p_amt / months

        mrr = round(mrr_val, 2)
        arr = round(mrr * 12, 2)

        # 6. Dynamic Trends Construction based on Date Range
        bucket_data = {}
        delta_days = (end_date - start_date).total_seconds() / 86400.0

        # Fetch all completed payments and standalone invoices in this period
        period_pmts = _apply_org_filter(
            SubscriptionPayment.query.filter(
                SubscriptionPayment.payment_status.in_(['Completed', 'Paid', 'SUCCESS']),
                SubscriptionPayment.created_at >= start_date,
                SubscriptionPayment.created_at <= end_date
            ),
            SubscriptionPayment
        ).all()

        period_invs = SubscriptionInvoice.query.filter(
            SubscriptionInvoice.invoice_status.in_(['Paid', 'Completed', 'PAID']),
            SubscriptionInvoice.payment_id == None,
            SubscriptionInvoice.created_at >= start_date,
            SubscriptionInvoice.created_at <= end_date
        )
        if org_id:
            period_invs = period_invs.filter_by(org_id=org_id)
        if platform_org_ids:
            period_invs = period_invs.filter(~SubscriptionInvoice.org_id.in_(platform_org_ids))
        period_invs_list = period_invs.all()

        # Case A: Intraday (Today, Yesterday, or <= 1.5 days)
        if delta_days <= 1.5:
            cur = start_date.replace(minute=0, second=0, microsecond=0)
            while cur <= end_date:
                lbl = cur.strftime('%I %p')
                bucket_data[lbl] = 0.0
                cur += timedelta(hours=3)
            
            for p in period_pmts:
                if p.created_at:
                    hour_slot = (p.created_at.hour // 3) * 3
                    slot_lbl = p.created_at.replace(hour=hour_slot, minute=0, second=0).strftime('%I %p')
                    if slot_lbl in bucket_data:
                        bucket_data[slot_lbl] += float(p.final_amount or p.amount or 0.0)

        # Case B: Short / Medium range (2 to 45 days, e.g. Last 7 Days, Last 30 Days, This Month, Last Month)
        elif delta_days <= 45:
            cur = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            target_end = end_date.replace(hour=23, minute=59, second=59)
            while cur <= target_end:
                lbl = cur.strftime('%d %b')
                bucket_data[lbl] = 0.0
                cur += timedelta(days=1)
            
            for p in period_pmts:
                if p.created_at:
                    lbl = p.created_at.strftime('%d %b')
                    if lbl in bucket_data:
                        bucket_data[lbl] += float((p.final_amount if p.final_amount is not None else p.amount) or 0.0)
            for inv in period_invs_list:
                if inv.created_at:
                    lbl = inv.created_at.strftime('%d %b')
                    if lbl in bucket_data:
                        bucket_data[lbl] += float(inv.total_amount or 0.0)

        # Case C: Quarter / 90 Days (46 to 120 days)
        elif delta_days <= 120:
            cur = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            while cur <= end_date:
                lbl = cur.strftime('%d %b')
                bucket_data[lbl] = 0.0
                cur += timedelta(days=7)
            
            for p in period_pmts:
                if p.created_at:
                    amt = float((p.final_amount if p.final_amount is not None else p.amount) or 0.0)
                    closest_lbl = None
                    min_diff = 999999999
                    for b_str in bucket_data.keys():
                        try:
                            b_dt = datetime.strptime(f"{b_str} {p.created_at.year}", "%d %b %Y")
                            diff = abs((p.created_at - b_dt).total_seconds())
                            if diff < min_diff:
                                min_diff = diff
                                closest_lbl = b_str
                        except Exception:
                            pass
                    if closest_lbl:
                        bucket_data[closest_lbl] += amt

        # Case D: Long Range (> 120 days, e.g. Year to Date, Last 12 Months, All)
        else:
            cur = start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            while cur <= end_date:
                lbl = cur.strftime('%b %Y')
                bucket_data[lbl] = 0.0
                cur = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
            
            for p in period_pmts:
                if p.created_at:
                    lbl = p.created_at.strftime('%b %Y')
                    if lbl in bucket_data:
                        bucket_data[lbl] += float((p.final_amount if p.final_amount is not None else p.amount) or 0.0)
            for inv in period_invs_list:
                if inv.created_at:
                    lbl = inv.created_at.strftime('%b %Y')
                    if lbl in bucket_data:
                        bucket_data[lbl] += float(inv.total_amount or 0.0)

        trend_labels = list(bucket_data.keys())
        trend_values = [round(v, 2) for v in bucket_data.values()]

        # 7. 3-Month Revenue Forecasting Engine
        # Projects expected total monthly revenue for the next 3 consecutive calendar months
        # based on active MRR, recurring subscription run-rates, and historical monthly collections.
        forecast_labels = []
        forecast_values = []

        for i in range(1, 4):
            nxt_month = (now.replace(day=28) + timedelta(days=31 * i)).replace(day=1)
            forecast_labels.append(nxt_month.strftime('%b %Y'))

        # Aggregate monthly historical totals over past 6 calendar months
        hist_months = []
        for i in range(5, -1, -1):
            m_dt = (now.replace(day=28) - timedelta(days=31 * i)).replace(day=1)
            hist_months.append(m_dt.strftime('%b %Y'))

        hist_rev = {m: 0.0 for m in hist_months}
        all_completed_pmts = _apply_org_filter(
            db.session.query(SubscriptionPayment).filter(
                SubscriptionPayment.payment_status.in_(['Completed', 'Paid', 'SUCCESS'])
            ),
            SubscriptionPayment
        ).all()
        for p in all_completed_pmts:
            if p.created_at:
                m_str = p.created_at.strftime('%b %Y')
                if m_str in hist_rev:
                    hist_rev[m_str] += float((p.final_amount if p.final_amount is not None else p.amount) or 0.0)

        all_completed_invs = _apply_org_filter(
            db.session.query(SubscriptionInvoice).filter(
                SubscriptionInvoice.invoice_status.in_(['Paid', 'Completed', 'PAID']),
                SubscriptionInvoice.payment_id == None
            ),
            SubscriptionInvoice
        ).all()
        for inv in all_completed_invs:
            if inv.created_at:
                m_str = inv.created_at.strftime('%b %Y')
                if m_str in hist_rev:
                    hist_rev[m_str] += float(inv.total_amount or 0.0)

        # Baseline monthly revenue is the highest of:
        # 1. Contractual active MRR
        # 2. Maximum recent monthly collected revenue
        # 3. Average non-zero monthly collected revenue
        non_zero_months = [v for v in hist_rev.values() if v > 0]
        recent_monthly_max = max(non_zero_months) if non_zero_months else 0.0
        recent_monthly_avg = (sum(non_zero_months) / len(non_zero_months)) if non_zero_months else 0.0
        
        baseline_monthly = max(mrr, recent_monthly_max, recent_monthly_avg)

        # Calculate monthly growth trajectory
        if len(non_zero_months) >= 2:
            m_vals = list(hist_rev.values())
            xs = list(range(len(m_vals)))
            ys = m_vals
            mean_x = sum(xs) / len(xs)
            mean_y = sum(ys) / len(ys)
            num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(len(xs)))
            den = sum((xs[i] - mean_x) ** 2 for i in range(len(xs)))
            m_slope = num / den if den != 0 else 0.0
            
            for i in range(1, 4):
                proj = baseline_monthly + (m_slope * i)
                proj = max(baseline_monthly * (1.0 + (0.05 * i)), proj)
                forecast_values.append(round(proj, 2))
        else:
            growth_rates = [0.06, 0.12, 0.18]
            for i, rate in enumerate(growth_rates):
                proj = baseline_monthly * (1.0 + rate) if baseline_monthly > 0 else 0.0
                forecast_values.append(round(proj, 2))

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
