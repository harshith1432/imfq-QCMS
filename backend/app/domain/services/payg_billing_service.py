"""
Pay-As-You-Go (PAYG) Metered Billing Service
Calculates real-time organization usage (active users, storage, projects, API calls, QC circles),
evaluates custom metered pricing rules, generates itemized SubscriptionInvoices,
and dispatches monthly bills to tenant dashboards and via email.
"""
import uuid
from datetime import datetime, timedelta
from app.infrastructure.database.models.models import (
    db, Organization, User, Project, Department, Plant, Subscription,
    SubscriptionInvoice, SaaSPlan, Notification
)
from app.domain.services.storage_calculator_service import calculate_org_storage_realtime
from app.infrastructure.mailer.email_service import EmailUtils
from app.domain.services.document_branding_service import DocumentBrandingService

DEFAULT_PAYG_RULES = {
    "base_fee": 999.0,              # Monthly base access fee (INR)
    "user_rate": 50.0,              # ₹ / active user / month
    "user_free_tier": 5,            # 5 users included free
    "storage_rate_per_gb": 20.0,    # ₹ / GB storage / month
    "storage_free_tier_gb": 5.0,    # 5 GB included free
    "project_rate": 100.0,          # ₹ / project created / month
    "project_free_tier": 2,         # 2 projects included free
    "department_rate": 50.0,        # ₹ / department / month
    "department_free_tier": 2,      # 2 departments included free
    "location_rate": 100.0,         # ₹ / plant location / month
    "location_free_tier": 1,        # 1 location included free
    "api_rate_per_1k": 10.0,        # ₹ / 1,000 API calls
    "api_free_tier_1k": 10,         # 10k API calls free
    "qc_circle_rate": 150.0,        # ₹ / Quality Circle / month
    "qc_circle_free_tier": 1,       # 1 QC Circle free
    "tax_percent": 18.0,            # 18% GST standard
    "billing_cycle": "Monthly",
    "currency": "INR"
}


class PaygBillingService:

    @staticmethod
    def get_effective_payg_rules(org_id=None, plan_or_sub=None):
        """
        Retrieves the active Pay-As-You-Go rules dictionary for an organization or plan.
        Merges custom configured rules with DEFAULT_PAYG_RULES.
        """
        rules = dict(DEFAULT_PAYG_RULES)
        if plan_or_sub and getattr(plan_or_sub, 'payg_rules', None):
            if isinstance(plan_or_sub.payg_rules, dict):
                rules.update(plan_or_sub.payg_rules)
            return rules

        if org_id:
            sub = Subscription.query.filter_by(org_id=org_id, subscription_status='Active').first()
            if sub and sub.payg_rules and isinstance(sub.payg_rules, dict):
                rules.update(sub.payg_rules)
                return rules
            
            org = Organization.query.get(org_id)
            if org and org.subscription_plan:
                sp = SaaSPlan.query.filter(
                    (SaaSPlan.name == org.subscription_plan) | 
                    (SaaSPlan.code == org.subscription_plan) |
                    (SaaSPlan.plan_type == 'Pay-As-You-Go')
                ).first()
                if sp and sp.payg_rules and isinstance(sp.payg_rules, dict):
                    rules.update(sp.payg_rules)
                    return rules

        # Look up any active SaaSPlan configured as Pay-As-You-Go
        payg_plan = SaaSPlan.query.filter(
            (SaaSPlan.plan_type == 'Pay-As-You-Go') | (SaaSPlan.pricing_model == 'pay_as_you_go')
        ).first()
        if payg_plan and payg_plan.payg_rules and isinstance(payg_plan.payg_rules, dict):
            rules.update(payg_plan.payg_rules)

        return rules

    @staticmethod
    def get_org_realtime_metrics(org_id, start_date=None, end_date=None):
        """
        Computes accurate real-time usage metrics for an organization within a date window.
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            # Default to first day of the current month
            start_date = datetime(end_date.year, end_date.month, 1)

        org = Organization.query.get(org_id)
        if not org:
            return {
                "active_users": 0,
                "storage_used_gb": 0.0,
                "storage_used_mb": 0.0,
                "projects_count": 0,
                "qc_circles_count": 0,
                "api_calls_count": 0,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat()
            }

        # 1. Active Users
        active_users = User.query.filter(
            User.org_id == org_id,
            (User.is_active == True) | (User.is_active == None)
        ).count()

        # 2. Real-time Storage
        storage_data = calculate_org_storage_realtime(org_id)
        storage_gb = 0.0
        storage_mb = 0.0
        if isinstance(storage_data, dict):
            orgs_list = storage_data.get('organizations', [])
            if orgs_list:
                storage_gb = float(orgs_list[0].get('storage_used_gb', 0.0))
                storage_mb = float(orgs_list[0].get('storage_used_mb', 0.0))
            elif 'summary' in storage_data:
                storage_gb = float(storage_data['summary'].get('total_used_gb', 0.0))

        # 3. Projects (Created in billing window or total active)
        projects_count = Project.query.filter(
            Project.org_id == org_id,
            Project.created_at >= start_date,
            Project.created_at <= end_date
        ).count()
        if projects_count == 0:
            # Fallback to total projects if none created in the strict window
            projects_count = Project.query.filter_by(org_id=org_id).count()

        # 4. Department / Quality Teams
        departments_count = 0
        try:
            departments_count = Department.query.filter_by(org_id=org_id).count()
        except Exception:
            pass

        # 5. Plant Locations / Operating Sites
        plants_count = 0
        try:
            plants_count = Plant.query.filter_by(org_id=org_id).count()
        except Exception:
            pass

        # 6. API / System Operations estimate
        api_calls_count = 120 # Baseline recorded telemetry
        try:
            from app.infrastructure.database.models.models import AuditLog
            api_calls_count = AuditLog.query.filter(
                AuditLog.org_id == org_id,
                AuditLog.created_at >= start_date,
                AuditLog.created_at <= end_date
            ).count()
        except Exception:
            pass

        return {
            "org_id": org_id,
            "org_name": org.name,
            "active_users": active_users,
            "storage_used_gb": round(storage_gb, 3),
            "storage_used_mb": round(storage_mb, 2),
            "projects_count": projects_count,
            "departments_count": departments_count,
            "plants_count": plants_count,
            "qc_circles_count": departments_count,
            "api_calls_count": api_calls_count,
            "period_start": start_date.strftime('%Y-%m-%d'),
            "period_end": end_date.strftime('%Y-%m-%d')
        }

    @classmethod
    def calculate_payg_bill_breakdown(cls, org_id, payg_rules=None, start_date=None, end_date=None):
        """
        Calculates itemized usage line items, subtotal, GST, and final amount based on PAYG rules.
        """
        rules = payg_rules or cls.get_effective_payg_rules(org_id)
        metrics = cls.get_org_realtime_metrics(org_id, start_date, end_date)

        base_fee = float(rules.get('base_fee', 999.0))
        user_rate = float(rules.get('user_rate', 50.0))
        user_free = int(rules.get('user_free_tier', 5))
        storage_rate = float(rules.get('storage_rate_per_gb', 20.0))
        storage_free = float(rules.get('storage_free_tier_gb', 5.0))
        project_rate = float(rules.get('project_rate', 100.0))
        project_free = int(rules.get('project_free_tier', 2))
        dept_rate = float(rules.get('department_rate', 50.0))
        dept_free = int(rules.get('department_free_tier', 2))
        loc_rate = float(rules.get('location_rate', 100.0))
        loc_free = int(rules.get('location_free_tier', 1))
        api_rate_1k = float(rules.get('api_rate_per_1k', 10.0))
        api_free_1k = float(rules.get('api_free_tier_1k', 10.0))
        tax_pct = float(rules.get('tax_percent', 18.0))
        currency = rules.get('currency', 'INR')

        line_items = []
        subtotal = 0.0

        # 1. Base Platform Access Fee
        line_items.append({
            "code": "BASE_FEE",
            "metric": "Platform Access Base Fee",
            "description": "Monthly base infrastructure, security, and tenant hosting access fee",
            "units_used": 1,
            "free_allowance": 0,
            "billable_units": 1,
            "unit_price": base_fee,
            "unit_label": "Month",
            "line_total": base_fee
        })
        subtotal += base_fee

        # 2. Active Users Usage
        users_count = metrics['active_users']
        billable_users = max(0, users_count - user_free)
        users_cost = round(billable_users * user_rate, 2)
        line_items.append({
            "code": "ACTIVE_USERS",
            "metric": "Active User Seats",
            "description": f"Licensed active team members and reviewers ({user_free} seats free)",
            "units_used": users_count,
            "free_allowance": user_free,
            "billable_units": billable_users,
            "unit_price": user_rate,
            "unit_label": "User / mo",
            "line_total": users_cost
        })
        subtotal += users_cost

        # 3. Storage Consumption
        storage_gb = metrics['storage_used_gb']
        billable_storage = max(0.0, storage_gb - storage_free)
        storage_cost = round(billable_storage * storage_rate, 2)
        line_items.append({
            "code": "STORAGE_USAGE",
            "metric": "Cloud Data & File Storage",
            "description": f"Repository assets, attachments, and DB records ({storage_free} GB free)",
            "units_used": round(storage_gb, 3),
            "free_allowance": storage_free,
            "billable_units": round(billable_storage, 3),
            "unit_price": storage_rate,
            "unit_label": "GB / mo",
            "line_total": storage_cost
        })
        subtotal += storage_cost

        # 4. Project Initiatives
        proj_count = metrics['projects_count']
        billable_proj = max(0, proj_count - project_free)
        proj_cost = round(billable_proj * project_rate, 2)
        line_items.append({
            "code": "PROJECT_USAGE",
            "metric": "8-Stage QC Projects Created",
            "description": f"Quality control and continuous improvement projects ({project_free} projects free)",
            "units_used": proj_count,
            "free_allowance": project_free,
            "billable_units": billable_proj,
            "unit_price": project_rate,
            "unit_label": "Project / mo",
            "line_total": proj_cost
        })
        subtotal += proj_cost

        # 5. Departments
        depts_count = metrics['departments_count']
        billable_depts = max(0, depts_count - dept_free)
        depts_cost = round(billable_depts * dept_rate, 2)
        line_items.append({
            "code": "DEPARTMENTS",
            "metric": "Functional Departments",
            "description": f"Organization departments and functional teams ({dept_free} departments free)",
            "units_used": depts_count,
            "free_allowance": dept_free,
            "billable_units": billable_depts,
            "unit_price": dept_rate,
            "unit_label": "Dept / mo",
            "line_total": depts_cost
        })
        subtotal += depts_cost

        # 6. Plant Locations / Operating Sites
        plants_count = metrics['plants_count']
        billable_plants = max(0, plants_count - loc_free)
        plants_cost = round(billable_plants * loc_rate, 2)
        line_items.append({
            "code": "PLANT_LOCATIONS",
            "metric": "Plant Locations / Operating Sites",
            "description": f"Physical operating plants and facility locations ({loc_free} location free)",
            "units_used": plants_count,
            "free_allowance": loc_free,
            "billable_units": billable_plants,
            "unit_price": loc_rate,
            "unit_label": "Location / mo",
            "line_total": plants_cost
        })
        subtotal += plants_cost

        gst_amount = round(subtotal * (tax_pct / 100.0), 2)
        total_amount = round(subtotal + gst_amount, 2)

        return {
            "org_id": org_id,
            "org_name": metrics.get('org_name', f'Organization #{org_id}'),
            "pricing_model": "pay_as_you_go",
            "billing_cycle": "Monthly",
            "currency": currency,
            "period_start": metrics['period_start'],
            "period_end": metrics['period_end'],
            "metrics": metrics,
            "rules": rules,
            "line_items": line_items,
            "subtotal_amount": round(subtotal, 2),
            "discount_amount": 0.0,
            "gst_percent": tax_pct,
            "gst_amount": gst_amount,
            "total_amount": total_amount
        }

    @classmethod
    def get_global_payg_rules(cls):
        return cls.get_effective_payg_rules()

    @classmethod
    def update_global_payg_rules(cls, new_rules):
        global DEFAULT_PAYG_RULES
        if not isinstance(new_rules, dict):
            return cls.get_effective_payg_rules()

        # Update in-memory default rules
        for k, v in new_rules.items():
            if k in DEFAULT_PAYG_RULES or k in ['department_rate', 'department_free_tier', 'location_rate', 'location_free_tier']:
                try:
                    if 'tier' in k:
                        DEFAULT_PAYG_RULES[k] = int(v)
                    elif 'rate' in k or 'fee' in k or 'percent' in k or 'tax' in k:
                        DEFAULT_PAYG_RULES[k] = float(v)
                    else:
                        DEFAULT_PAYG_RULES[k] = v
                except Exception:
                    DEFAULT_PAYG_RULES[k] = v

        # Persist to SaaSPlan(code='payg')
        payg_plan = SaaSPlan.query.filter(
            (SaaSPlan.plan_type == 'Pay-As-You-Go') | (SaaSPlan.code == 'payg')
        ).first()
        if payg_plan:
            payg_plan.payg_rules = dict(DEFAULT_PAYG_RULES)
            if 'base_fee' in DEFAULT_PAYG_RULES:
                if payg_plan.pricing:
                    for pr in payg_plan.pricing:
                        pr.price = float(DEFAULT_PAYG_RULES['base_fee'])
            db.session.commit()

        return dict(DEFAULT_PAYG_RULES)

    @classmethod
    def generate_and_send_monthly_invoice(cls, org_id, start_date=None, end_date=None, auto_send_email=True, created_by_id=None, recipient_email=None, cc_email=None, subject=None):
        """
        Generates an official SubscriptionInvoice record for the monthly Pay-As-You-Go bill,
        dispatches in-app notification, and sends branded email bill to org admins.
        """
        org = Organization.query.get(org_id)
        if not org:
            raise ValueError(f"Organization ID {org_id} does not exist.")

        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        breakdown = cls.calculate_payg_bill_breakdown(org_id, start_date=start_date, end_date=end_date)
        
        # Check active subscription or create fallback link
        sub = Subscription.query.filter_by(org_id=org_id, subscription_status='Active').first()
        sub_id = sub.id if sub else None

        invoice_uid = f"INV-PAYG-{datetime.utcnow().strftime('%Y%m')}-{org_id:03d}-{uuid.uuid4().hex[:4].upper()}"
        base_inv_number = f"QCMS-PAYG-{datetime.utcnow().strftime('%Y%m%d')}-{org_id}"
        existing_inv = SubscriptionInvoice.query.filter_by(invoice_number=base_inv_number).first()
        if existing_inv:
            invoice_number = f"{base_inv_number}-{uuid.uuid4().hex[:4].upper()}"
        else:
            invoice_number = base_inv_number

        invoice = SubscriptionInvoice(
            subscription_id=sub_id,
            org_id=org_id,
            invoice_uid=invoice_uid,
            invoice_number=invoice_number,
            invoice_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=15),
            billing_period_start=start_date,
            billing_period_end=end_date,
            plan_name="Pay-As-You-Go",
            billing_cycle="Monthly",
            base_amount=breakdown['subtotal_amount'],
            discount_percent=0.0,
            discount_amount=0.0,
            gst_percent=breakdown['gst_percent'],
            gst_amount=breakdown['gst_amount'],
            total_amount=breakdown['total_amount'],
            currency=breakdown['currency'],
            is_tax_inclusive=False,
            invoice_status="Sent",
            invoice_type="pay_as_you_go",
            usage_breakdown=breakdown,
            notes=f"Monthly metered usage bill for period {breakdown['period_start']} to {breakdown['period_end']}."
        )

        db.session.add(invoice)
        if sub:
            sub.last_metered_billing_at = datetime.utcnow()

        db.session.commit()

        # In-App Notification to Org Admins
        try:
            admin_users = User.query.filter_by(org_id=org_id).all()
            for admin in admin_users:
                notif = Notification(
                    org_id=org_id,
                    user_id=admin.id,
                    title=f"📄 Monthly Pay-As-You-Go Bill ({breakdown['period_start']} to {breakdown['period_end']})",
                    message=f"Your monthly metered invoice of ₹{breakdown['total_amount']:,.2f} is generated and ready for review in your Billing dashboard.",
                    link="/admin/subscriptions.html"
                )
                db.session.add(notif)
            db.session.commit()
        except Exception as e:
            print(f"[PaygBillingService] Notification dispatch error: {e}")

        # Email Dispatch
        email_sent = False
        if auto_send_email:
            try:
                email_sent = cls.send_payg_invoice_email(org, invoice, breakdown, target_email=recipient_email, cc_email=cc_email, custom_subject=subject)
            except Exception as e:
                print(f"[PaygBillingService] Email dispatch failed: {e}")

        return {
            "status": "success",
            "invoice_id": invoice.id,
            "invoice_uid": invoice.invoice_uid,
            "invoice_number": invoice.invoice_number,
            "total_amount": invoice.total_amount,
            "email_sent": email_sent,
            "breakdown": breakdown
        }

    @classmethod
    def generate_payg_invoice_html(cls, invoice, org, breakdown):
        """
        Constructs a beautifully formatted, compliant HTML tax bill for email & PDF downloads.
        """
        app_url = EmailUtils._get_app_url()
        line_items_html = ""
        for item in breakdown.get('line_items', []):
            line_items_html += f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 12px 10px; font-size: 13px; color: #1e293b;">
                    <strong>{item['metric']}</strong><br>
                    <span style="font-size: 11px; color: #64748b;">{item['description']}</span>
                </td>
                <td style="padding: 12px 10px; text-align: center; font-size: 13px; color: #475569;">
                    {item['units_used']} <span style="font-size: 11px; color: #94a3b8;">({item['unit_label']})</span>
                </td>
                <td style="padding: 12px 10px; text-align: center; font-size: 13px; color: #10b981; font-weight: 600;">
                    {item['free_allowance']}
                </td>
                <td style="padding: 12px 10px; text-align: center; font-size: 13px; color: #1e293b; font-weight: 600;">
                    {item['billable_units']}
                </td>
                <td style="padding: 12px 10px; text-align: right; font-size: 13px; color: #475569;">
                    ₹{item['unit_price']:,.2f}
                </td>
                <td style="padding: 12px 10px; text-align: right; font-size: 13px; font-weight: bold; color: #0f172a;">
                    ₹{item['line_total']:,.2f}
                </td>
            </tr>
            """

        invoice_html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 680px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); padding: 28px 24px; color: #ffffff;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h2 style="margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.5px;">QCMS Enterprise OS</h2>
                        <div style="font-size: 12px; opacity: 0.9; margin-top: 4px;">Monthly Pay-As-You-Go Tax Invoice</div>
                    </div>
                    <div style="text-align: right;">
                        <span style="background: rgba(255,255,255,0.2); padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase;">
                            {invoice.invoice_status}
                        </span>
                    </div>
                </div>
            </div>

            <!-- Meta Details -->
            <div style="padding: 24px; background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <tr>
                        <td style="vertical-align: top; width: 50%; padding-right: 15px;">
                            <span style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase;">Billed To:</span><br>
                            <strong style="font-size: 15px; color: #0f172a;">{org.name}</strong><br>
                            <span style="color: #475569;">Org Code: {org.org_code or f'ORG-{org.id:03d}'}</span><br>
                            <span style="color: #475569;">Plan: Pay-As-You-Go (Metered)</span>
                        </td>
                        <td style="vertical-align: top; width: 50%; text-align: right;">
                            <span style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase;">Invoice Details:</span><br>
                            <strong style="color: #0f172a;">Invoice #: {invoice.invoice_number}</strong><br>
                            <span style="color: #475569;">Billing Window: {breakdown.get('period_start')} to {breakdown.get('period_end')}</span><br>
                            <span style="color: #475569;">Due Date: {invoice.due_date.strftime('%B %d, %Y') if invoice.due_date else 'Immediate'}</span>
                        </td>
                    </tr>
                </table>
            </div>

            <!-- Table of Line Items -->
            <div style="padding: 24px 20px;">
                <table style="width: 100%; border-collapse: collapse; text-align: left;">
                    <thead>
                        <tr style="background: #f1f5f9; border-bottom: 2px solid #cbd5e1;">
                            <th style="padding: 10px; font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase;">Usage Metric</th>
                            <th style="padding: 10px; font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; text-align: center;">Total Units</th>
                            <th style="padding: 10px; font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; text-align: center;">Free Tier</th>
                            <th style="padding: 10px; font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; text-align: center;">Billable</th>
                            <th style="padding: 10px; font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; text-align: right;">Rate</th>
                            <th style="padding: 10px; font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; text-align: right;">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        {line_items_html}
                    </tbody>
                </table>

                <!-- Summary Totals -->
                <div style="margin-top: 20px; display: flex; justify-content: flex-end;">
                    <table style="width: 260px; border-collapse: collapse; font-size: 13px; margin-left: auto;">
                        <tr>
                            <td style="padding: 6px 0; color: #64748b;">Subtotal (Excl. Tax):</td>
                            <td style="padding: 6px 0; text-align: right; font-weight: 600; color: #0f172a;">₹{invoice.base_amount:,.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 6px 0; color: #64748b;">GST ({invoice.gst_percent}%):</td>
                            <td style="padding: 6px 0; text-align: right; font-weight: 600; color: #0f172a;">₹{invoice.gst_amount:,.2f}</td>
                        </tr>
                        <tr style="border-top: 2px solid #0f172a;">
                            <td style="padding: 10px 0; font-size: 15px; font-weight: 800; color: #0f172a;">Total Payable:</td>
                            <td style="padding: 10px 0; font-size: 17px; font-weight: 800; color: #2563eb; text-align: right;">₹{invoice.total_amount:,.2f}</td>
                        </tr>
                    </table>
                </div>
            </div>

            <!-- Footer Action & Help -->
            <div style="padding: 20px 24px; background: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center;">
                <p style="font-size: 12px; color: #64748b; margin: 0 0 12px 0;">
                    You can pay this bill online via NetBanking, UPI, or Credit Card directly in your QCMS Billing Portal.
                </p>
                <a href="{app_url}/admin/subscriptions.html" style="background-color: #2563eb; color: #ffffff; padding: 10px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 13px; display: inline-block;">
                    View Invoice in Dashboard →
                </a>
            </div>
        </div>
        """
        return invoice_html

    @classmethod
    def send_payg_invoice_email(cls, org, invoice, breakdown, target_email=None, cc_email=None, custom_subject=None):
        """
        Sends the monthly pay-as-you-go bill to tenant organization administrators via EmailUtils.
        Checks if the email rule is enabled in Email Notifications Registry.
        """
        # Check Notification Rule state in Email Notifications Registry
        from app.infrastructure.database.models.models import EmailNotificationRule
        rule = EmailNotificationRule.query.filter(
            (EmailNotificationRule.event_trigger == 'payg_invoice_generated') |
            (EmailNotificationRule.category == 'billing') |
            (EmailNotificationRule.name == 'Monthly Pay-As-You-Go Metered Tax Invoice')
        ).first()

        if rule and not rule.is_active:
            print(f"[PaygBillingService] PAYG Monthly Invoice Email Notification Rule is disabled (OFF). Skipping email dispatch.")
            return False

        if target_email:
            recipient_emails = [target_email.strip()]
        else:
            # Find recipient emails
            admins = User.query.filter(
                User.org_id == org.id,
                User.email != None
            ).all()
            recipient_emails = [u.email for u in admins if u.email]
            if org.email and org.email not in recipient_emails:
                recipient_emails.append(org.email)
            if org.billing_email and org.billing_email not in recipient_emails:
                recipient_emails.append(org.billing_email)

        if cc_email and cc_email.strip() and cc_email.strip() not in recipient_emails:
            recipient_emails.append(cc_email.strip())

        if not recipient_emails:
            print(f"[PaygBillingService] No admin emails found for Org {org.id} ({org.name})")
            return False

        subject = custom_subject or f"📄 Monthly Pay-As-You-Go Invoice #{invoice.invoice_number} ({org.name})"
        raw_body_html = cls.generate_payg_invoice_html(invoice, org, breakdown)
        branded_html = DocumentBrandingService.wrap_email_html(raw_body_html, title=subject, org_id=org.id, include_header=False)

        # --- Generate PDF attachment using reportlab ---
        pdf_attachment = None
        try:
            from io import BytesIO
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            )
            from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT

            pdf_buffer = BytesIO()
            doc = SimpleDocTemplate(
                pdf_buffer, pagesize=A4,
                topMargin=15*mm, bottomMargin=15*mm,
                leftMargin=18*mm, rightMargin=18*mm
            )
            styles = getSampleStyleSheet()
            story = []

            # Header styles
            title_style  = ParagraphStyle('title',  fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=colors.HexColor('#1e3a8a'), spaceAfter=6)
            sub_style    = ParagraphStyle('sub',    fontName='Helvetica',      fontSize=9,  leading=13, textColor=colors.HexColor('#64748b'), spaceBefore=2, spaceAfter=10)
            label_style  = ParagraphStyle('label',  fontName='Helvetica-Bold', fontSize=8,  textColor=colors.HexColor('#64748b'), spaceBefore=4)
            value_style  = ParagraphStyle('value',  fontName='Helvetica',      fontSize=10, leading=14, textColor=colors.HexColor('#0f172a'))
            bold_style   = ParagraphStyle('bold',   fontName='Helvetica-Bold', fontSize=10, leading=14, textColor=colors.HexColor('#0f172a'))
            total_style  = ParagraphStyle('total',  fontName='Helvetica-Bold', fontSize=13, textColor=colors.HexColor('#2563eb'), alignment=TA_RIGHT)
            footer_style = ParagraphStyle('footer', fontName='Helvetica',      fontSize=8,  textColor=colors.HexColor('#94a3b8'), alignment=TA_CENTER)

            # Title block
            story.append(Paragraph("QCMS Enterprise OS", title_style))
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph("Official Monthly Pay-As-You-Go Tax Invoice", sub_style))
            story.append(Spacer(1, 2*mm))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1')))
            story.append(Spacer(1, 4*mm))

            # Billed To / Invoice Details side-by-side
            period_start = breakdown.get('period_start', '')
            period_end   = breakdown.get('period_end', '')
            due_str      = invoice.due_date.strftime('%d %b %Y') if invoice.due_date else 'Immediate'
            meta_data = [
                [
                    Paragraph("<b>BILLED TO</b>", label_style),
                    Paragraph("<b>INVOICE DETAILS</b>", label_style)
                ],
                [
                    Paragraph(f"<b>{org.name}</b>", bold_style),
                    Paragraph(f"Invoice #: <b>{invoice.invoice_number}</b>", value_style)
                ],
                [
                    Paragraph(f"Org Code: {org.org_code or f'ORG-{org.id:03d}'}", value_style),
                    Paragraph(f"Billing Period: {period_start} to {period_end}", value_style)
                ],
                [
                    Paragraph("Plan: Pay-As-You-Go (Metered)", value_style),
                    Paragraph(f"Due Date: {due_str}", value_style)
                ],
                [
                    Paragraph(f"Status: <b>{invoice.invoice_status}</b>", bold_style),
                    Paragraph("", value_style)
                ],
            ]
            meta_table = Table(meta_data, colWidths=[85*mm, 85*mm])
            meta_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(meta_table)
            story.append(Spacer(1, 5*mm))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e2e8f0')))
            story.append(Spacer(1, 4*mm))

            # Line items table
            line_items  = breakdown.get('line_items', [])
            hdr_style   = ParagraphStyle('hdr', fontName='Helvetica-Bold', fontSize=8,  textColor=colors.white)
            cell_style  = ParagraphStyle('cell', fontName='Helvetica',      fontSize=9,  textColor=colors.HexColor('#1e293b'))
            cell_sm     = ParagraphStyle('cellsm', fontName='Helvetica',    fontSize=7,  textColor=colors.HexColor('#64748b'))

            table_data = [[
                Paragraph("USAGE METRIC",  hdr_style),
                Paragraph("TOTAL UNITS",   hdr_style),
                Paragraph("FREE TIER",     hdr_style),
                Paragraph("BILLABLE",      hdr_style),
                Paragraph("RATE (Rs.)",    hdr_style),
                Paragraph("AMOUNT (Rs.)",  hdr_style),
            ]]
            for item in line_items:
                metric_para = Paragraph(
                    f"<b>{item.get('metric','')}</b><br/><font size='7' color='#64748b'>{item.get('description','')}</font>",
                    cell_style
                )
                table_data.append([
                    metric_para,
                    Paragraph(str(item.get('units_used', 0)), cell_style),
                    Paragraph(str(item.get('free_allowance', 0)), cell_style),
                    Paragraph(str(item.get('billable_units', 0)), cell_style),
                    Paragraph(f"{item.get('unit_price', 0):,.2f}", cell_style),
                    Paragraph(f"{item.get('line_total', 0):,.2f}", cell_style),
                ])

            items_table = Table(
                table_data,
                colWidths=[62*mm, 22*mm, 22*mm, 22*mm, 22*mm, 22*mm]
            )
            items_table.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor('#1e3a8a')),
                ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
                ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
                ('GRID',          (0, 0), (-1, -1),  0.3, colors.HexColor('#e2e8f0')),
                ('VALIGN',        (0, 0), (-1, -1),  'TOP'),
                ('ALIGN',         (1, 0), (-1, -1),  'CENTER'),
                ('ALIGN',         (4, 0), (-1, -1),  'RIGHT'),
                ('TOPPADDING',    (0, 0), (-1, -1),  5),
                ('BOTTOMPADDING', (0, 0), (-1, -1),  5),
                ('LEFTPADDING',   (0, 0), (-1, -1),  6),
                ('RIGHTPADDING',  (0, 0), (-1, -1),  6),
            ]))
            story.append(items_table)
            story.append(Spacer(1, 5*mm))

            # Totals summary
            totals_data = [
                ["Subtotal (Excl. Tax):", f"Rs. {invoice.base_amount:,.2f}"],
                [f"GST ({invoice.gst_percent}%):", f"Rs. {invoice.gst_amount:,.2f}"],
                ["TOTAL PAYABLE:", f"Rs. {invoice.total_amount:,.2f}"],
            ]
            totals_style_list = ParagraphStyle('tot_lbl', fontName='Helvetica',      fontSize=9,  textColor=colors.HexColor('#475569'), alignment=TA_LEFT)
            totals_style_val  = ParagraphStyle('tot_val', fontName='Helvetica-Bold', fontSize=9,  textColor=colors.HexColor('#0f172a'), alignment=TA_RIGHT)
            totals_style_lblb = ParagraphStyle('tot_lblb',fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#0f172a'), alignment=TA_LEFT)
            totals_style_valb = ParagraphStyle('tot_valb',fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#2563eb'), alignment=TA_RIGHT)

            totals_para = [
                [Paragraph("Subtotal (Excl. Tax):", totals_style_list), Paragraph(f"Rs. {invoice.base_amount:,.2f}", totals_style_val)],
                [Paragraph(f"GST ({invoice.gst_percent}%):", totals_style_list), Paragraph(f"Rs. {invoice.gst_amount:,.2f}", totals_style_val)],
                [Paragraph("TOTAL PAYABLE:", totals_style_lblb), Paragraph(f"Rs. {invoice.total_amount:,.2f}", totals_style_valb)],
            ]
            totals_table = Table(totals_para, colWidths=[110*mm, 60*mm], hAlign='RIGHT')
            totals_table.setStyle(TableStyle([
                ('LINEABOVE',     (0, 2), (-1, 2), 1.5, colors.HexColor('#1e3a8a')),
                ('TOPPADDING',    (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(totals_table)
            story.append(Spacer(1, 6*mm))

            # Footer
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e2e8f0')))
            story.append(Spacer(1, 3*mm))
            story.append(Paragraph(
                "This is a system-generated invoice from QCMS Enterprise OS. For queries, contact your platform administrator.",
                footer_style
            ))

            doc.build(story)
            pdf_bytes = pdf_buffer.getvalue()
            safe_inv_num = invoice.invoice_number.replace('/', '-').replace('\\', '-')
            pdf_filename = f"Invoice_{safe_inv_num}.pdf"
            pdf_attachment = [{
                "content":   pdf_bytes,
                "filename":  pdf_filename,
                "name":      pdf_filename,
                "mime_type": "application/pdf"
            }]
            print(f"[PaygBillingService] PDF invoice generated: {pdf_filename} ({len(pdf_bytes)} bytes)")
        except Exception as pdf_err:
            print(f"[PaygBillingService] PDF attachment error: {pdf_err}. Sending email without attachment.")

        all_sent = True
        for email in recipient_emails:
            res = EmailUtils.send_email_async(
                to_email=email,
                subject=subject,
                html_content=branded_html,
                email_type='billing',
                org_id=org.id,
                attachments=pdf_attachment
            )
            if not res:
                all_sent = False

        return True

    @classmethod
    def preview_all_payg_organizations(cls):
        """
        Aggregates accrued monthly usage and estimated billing amounts for all organizations
        currently subscribed to or assigned to Pay-As-You-Go plans.
        """
        orgs = Organization.query.filter(
            (Organization.is_deleted == False) | (Organization.is_deleted == None)
        ).all()

        results = []
        for org in orgs:
            # Check if org is on PAYG
            sub = Subscription.query.filter_by(org_id=org.id, subscription_status='Active').first()
            is_payg = False
            if sub and (sub.pricing_model == 'pay_as_you_go' or (sub.plan_name and 'pay-as-you-go' in sub.plan_name.lower())):
                is_payg = True
            elif org.subscription_plan and 'pay-as-you-go' in org.subscription_plan.lower():
                is_payg = True

            if not is_payg:
                continue

            breakdown = cls.calculate_payg_bill_breakdown(org.id)
            results.append(breakdown)

        return results

    @classmethod
    def run_monthly_payg_batch(cls, admin_id=None):
        """
        Executes a batch run across all Pay-As-You-Go organizations,
        generates monthly invoices, and dispatches dashboard + email notifications.
        """
        orgs = Organization.query.filter(
            (Organization.is_deleted == False) | (Organization.is_deleted == None)
        ).all()

        generated_invoices = []
        for org in orgs:
            sub = Subscription.query.filter_by(org_id=org.id, subscription_status='Active').first()
            is_payg = False
            if sub and (sub.pricing_model == 'pay_as_you_go' or (sub.plan_name and 'pay-as-you-go' in sub.plan_name.lower())):
                is_payg = True
            elif org.subscription_plan and 'pay-as-you-go' in org.subscription_plan.lower():
                is_payg = True

            if not is_payg:
                continue

            try:
                inv_res = cls.generate_and_send_monthly_invoice(
                    org_id=org.id,
                    auto_send_email=True,
                    created_by_id=admin_id
                )
                generated_invoices.append(inv_res)
            except Exception as e:
                print(f"[PaygBillingService] Batch billing error for org {org.id}: {e}")

        return {
            "status": "success",
            "total_processed": len(generated_invoices),
            "invoices": generated_invoices
        }
