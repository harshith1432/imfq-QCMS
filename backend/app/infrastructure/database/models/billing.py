from datetime import datetime
import json
import os
from sqlalchemy.dialects.postgresql import ARRAY
from app import db, bcrypt
from .base import SafeVector, Vector, is_local, _utc_now

class PlatformSettings(db.Model):
    __tablename__ = 'platform_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.String(100), default="QCMS Enterprise")
    maintenance_mode = db.Column(db.Boolean, default=False)
    registration_open = db.Column(db.Boolean, default=True)
    require_email_otp = db.Column(db.Boolean, default=True)
    require_phone_otp = db.Column(db.Boolean, default=False)
    global_notification = db.Column(db.Text, nullable=True)
    support_email = db.Column(db.String(120), default="support@ifqm.org.in")
    system_version = db.Column(db.String(20), default="1.0.0")
    global_template_version = db.Column(db.Integer, default=1, nullable=False)
    global_template_updated_at = db.Column(db.DateTime, default=_utc_now)
    global_template_release_notes = db.Column(db.Text, nullable=True)
    global_template_preview_image = db.Column(db.Text, nullable=True)
    
    default_plan = db.Column(db.String(50), default="Starter")
    trial_period_days = db.Column(db.Integer, default=180)
    max_auto_trial_extensions = db.Column(db.Integer, default=2)
    payment_gateway_mode = db.Column(db.String(20), default="Test") # Test or Live
    plans_initial_seeded = db.Column(db.Boolean, default=False)
    
    # Extended Platform Settings Columns
    support_phone = db.Column(db.String(50), nullable=True)
    support_website = db.Column(db.String(255), nullable=True)
    company_address = db.Column(db.Text, nullable=True)
    timezone = db.Column(db.String(100), default="UTC")
    default_language = db.Column(db.String(10), default="en")
    date_format = db.Column(db.String(50), default="YYYY-MM-DD")
    time_format = db.Column(db.String(20), default="HH:mm:ss")
    currency = db.Column(db.String(10), default="USD")
    
    branding_settings = db.Column(db.JSON, nullable=True)
    localization_settings = db.Column(db.JSON, nullable=True)
    authentication_settings = db.Column(db.JSON, nullable=True)
    security_settings = db.Column(db.JSON, nullable=True)
    notification_settings = db.Column(db.JSON, nullable=True)
    email_settings = db.Column(db.JSON, nullable=True)
    sms_settings = db.Column(db.JSON, nullable=True)
    push_settings = db.Column(db.JSON, nullable=True)
    storage_settings = db.Column(db.JSON, nullable=True)
    compliance_settings = db.Column(db.JSON, nullable=True)
    api_settings = db.Column(db.JSON, nullable=True)
    webhook_settings = db.Column(db.JSON, nullable=True)
    integrations_settings = db.Column(db.JSON, nullable=True)
    ai_settings = db.Column(db.JSON, nullable=True)
    feature_flags = db.Column(db.JSON, nullable=True)
    maintenance_settings = db.Column(db.JSON, nullable=True)
    system_settings = db.Column(db.JSON, nullable=True)
    landing_cms_settings = db.Column(db.JSON, nullable=True)
    organizations_settings = db.Column(db.JSON, nullable=True)
    billing_settings = db.Column(db.JSON, nullable=True)
    modules_settings = db.Column(db.JSON, nullable=True)
    developer_settings = db.Column(db.JSON, nullable=True)
    audit_logs_settings = db.Column(db.JSON, nullable=True)
    system_health_settings = db.Column(db.JSON, nullable=True)
    about_settings = db.Column(db.JSON, nullable=True)
    global_stages_config = db.Column(db.JSON, nullable=True)
    stage_weightage_config = db.Column(db.JSON, nullable=True)  # List of 8 floats summing to 100.0
    
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)

class SupportTicket(db.Model):
    __tablename__ = 'support_tickets'
    __table_args__ = (
        db.Index('idx_ticket_org_status', 'org_id', 'status'),
        db.Index('idx_ticket_assigned_status', 'assigned_engineer_id', 'status'),
    )
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='Medium') # Low, Medium, High, Urgent, Critical
    status = db.Column(db.String(20), default='Open') # Open, Assigned, In Progress, Waiting for Customer, Resolved, Closed, Cancelled
    category = db.Column(db.String(50)) # Technical, Billing, License, Subscription, User Access, Bug, Feature Request, Security, Performance, General Inquiry
    created_at = db.Column(db.DateTime, default=_utc_now)
    resolved_at = db.Column(db.DateTime)
    resolution = db.Column(db.Text)
    
    # Advanced ticketing columns
    ticket_number = db.Column(db.String(100), unique=True, index=True)
    assigned_engineer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_team = db.Column(db.String(100), nullable=True)
    sla_status = db.Column(db.String(50), default='Within SLA') # Within SLA, Near Breach, Breached
    escalation_level = db.Column(db.Integer, default=0)
    tags = db.Column(db.JSON, default=list)
    
    # Relationships
    organization = db.relationship('Organization', backref='tickets')
    user = db.relationship('User', foreign_keys=[user_id], backref='tickets')
    assigned_engineer = db.relationship('User', foreign_keys=[assigned_engineer_id], backref='assigned_tickets')


class SupportComment(db.Model):
    __tablename__ = 'support_comments'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)

    ticket = db.relationship('SupportTicket', backref=db.backref('comments', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref='ticket_comments')


class SupportAttachment(db.Model):
    __tablename__ = 'support_attachments'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id', ondelete='CASCADE'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('support_comments.id', ondelete='CASCADE'), nullable=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100))
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=_utc_now)
    virus_scan_passed = db.Column(db.Boolean, default=True)

    ticket = db.relationship('SupportTicket', backref=db.backref('attachments', lazy=True, cascade='all, delete-orphan'))
    comment = db.relationship('SupportComment', backref=db.backref('attachments', lazy=True))
    uploaded_by = db.relationship('User', backref='ticket_uploads')


class SupportSLA(db.Model):
    __tablename__ = 'support_slas'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id', ondelete='CASCADE'), nullable=False)
    first_response_due = db.Column(db.DateTime)
    first_response_responded_at = db.Column(db.DateTime)
    resolution_due = db.Column(db.DateTime)
    resolution_completed_at = db.Column(db.DateTime)
    sla_status = db.Column(db.String(50), default='Within SLA')
    is_paused = db.Column(db.Boolean, default=False)
    paused_at = db.Column(db.DateTime)
    accumulated_paused_seconds = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=_utc_now)

    ticket = db.relationship('SupportTicket', backref=db.backref('sla', uselist=False, lazy=True, cascade='all, delete-orphan'))


class SupportEscalation(db.Model):
    __tablename__ = 'support_escalations'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id', ondelete='CASCADE'), nullable=False)
    escalation_level = db.Column(db.Integer, default=1)
    reason = db.Column(db.Text)
    escalated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    escalated_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    escalated_at = db.Column(db.DateTime, default=_utc_now)

    ticket = db.relationship('SupportTicket', backref=db.backref('escalations', lazy=True, cascade='all, delete-orphan'))
    escalated_by = db.relationship('User', foreign_keys=[escalated_by_id])
    escalated_to = db.relationship('User', foreign_keys=[escalated_to_id])


class SupportRating(db.Model):
    __tablename__ = 'support_ratings'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id', ondelete='CASCADE'), unique=True, nullable=False)
    rating = db.Column(db.Integer, nullable=False) # 1 to 5
    feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=_utc_now)

    ticket = db.relationship('SupportTicket', backref=db.backref('rating', uselist=False, lazy=True, cascade='all, delete-orphan'))


class SupportKnowledge(db.Model):
    __tablename__ = 'support_knowledge'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=_utc_now)
    views_count = db.Column(db.Integer, default=0)

    created_by = db.relationship('User', backref='kb_articles')


class SupportAudit(db.Model):
    __tablename__ = 'support_audits'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False) # Create Ticket, Update Ticket, Reassign Ticket, Comment Added, etc.
    old_values = db.Column(db.JSON)
    new_values = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=_utc_now)

    ticket = db.relationship('SupportTicket', backref=db.backref('audits', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref='support_audit_actions')


class SalesEnquiry(db.Model):
    __tablename__ = 'sales_enquiries'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(50), default='Talk to Sales')
    status = db.Column(db.String(30), default='New')  # New, Contacted, In Progress, Converted, Closed
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)


class SubscriptionPayment(db.Model):
    __tablename__ = 'subscription_payments'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    # FK to new Subscription model (nullable for legacy records)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('subscription_invoices.id', ondelete='SET NULL'), nullable=True)
    amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)  # base amount
    currency = db.Column(db.String(10), default='INR')
    plan_name = db.Column(db.String(50))
    billing_cycle = db.Column(db.String(20))  # Monthly, Quarterly, Yearly, Lifetime
    payment_status = db.Column(db.String(20), default='Completed')  # Completed, Pending, Failed, Refunded
    transaction_id = db.Column(db.String(255), unique=True)
    payment_gateway = db.Column(db.String(50))  # Razorpay, Stripe, Manual, etc.
    gateway_reference = db.Column(db.String(255))
    discount_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    gst_percent = db.Column(db.Numeric(5, 2), default=18.00, nullable=False)
    gst_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    final_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)  # amount - discount + gst
    refund_status = db.Column(db.String(20))  # None, Partial, Full
    refund_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    refund_date = db.Column(db.DateTime)
    billing_period_start = db.Column(db.DateTime)
    billing_period_end = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=_utc_now)

    organization = db.relationship('Organization', backref='payments')


class Subscription(db.Model):
    """Enterprise Subscription — full lifecycle entity, decoupled from Organization"""
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)

    # Unique subscription reference (e.g. SUB-2026-0001)
    subscription_uid = db.Column(db.String(50), unique=True, nullable=False)

    # Plan & Billing
    plan_name = db.Column(db.String(50), default='Professional')  # Starter, Professional, Enterprise, Custom, Pay-As-You-Go
    pricing_model = db.Column(db.String(30), default='fixed')     # fixed, pay_as_you_go
    payg_rules = db.Column(db.JSON, nullable=True)                # Snapshot of metered rates
    billing_cycle = db.Column(db.String(20), default='Yearly')    # Monthly, Quarterly, Yearly, Lifetime
    last_metered_billing_at = db.Column(db.DateTime, nullable=True) # Last time monthly PAYG bill was processed

    # Status
    subscription_status = db.Column(db.String(20), default='Active')
    # Active, Trial, Expired, Cancelled, Suspended, Pending
    payment_status = db.Column(db.String(20), default='Paid')
    # Paid, Pending, Failed, Overdue, Cancelled

    # Dates
    start_date = db.Column(db.DateTime, default=_utc_now)
    end_date = db.Column(db.DateTime)
    renewal_date = db.Column(db.DateTime)
    trial_start_date = db.Column(db.DateTime)
    trial_end_date = db.Column(db.DateTime)

    # Pricing
    base_price = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    discount_percent = db.Column(db.Numeric(5, 2), default=0.00, nullable=False)
    discount_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    gst_percent = db.Column(db.Numeric(5, 2), default=18.00, nullable=False)
    gst_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    final_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    currency = db.Column(db.String(10), default='INR')
    is_tax_inclusive = db.Column(db.Boolean, default=False)

    # Limits & Configuration
    max_users = db.Column(db.Integer, default=500)
    max_locations = db.Column(db.Integer, default=5)
    storage_limit_gb = db.Column(db.Float, default=10.0)
    api_limit = db.Column(db.Integer, default=10000)  # API calls per month
    enabled_modules = db.Column(db.JSON, default=list)  # list of module names
    support_level = db.Column(db.String(50), default='Standard')  # Standard, Priority, Enterprise

    # Renewal settings
    auto_renewal = db.Column(db.Boolean, default=True)
    grace_period_days = db.Column(db.Integer, default=7)

    # Metadata
    billing_notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)
    cancelled_at = db.Column(db.DateTime)
    cancellation_reason = db.Column(db.Text)

    # Relationships
    organization = db.relationship('Organization', backref=db.backref('subscriptions', lazy=True))
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_subscriptions')
    invoices = db.relationship('SubscriptionInvoice', backref='subscription', lazy=True,
                               foreign_keys='SubscriptionInvoice.subscription_id',
                               cascade='all, delete-orphan')
    subscription_payments = db.relationship('SubscriptionPayment', backref='subscription', lazy=True,
                                            foreign_keys='SubscriptionPayment.subscription_id')

class OfflinePaymentProof(db.Model):
    """Offline / Dynamic QR Payment Proof submitted by Organization Admins for manual SuperAdmin verification"""
    __tablename__ = 'offline_payment_proofs'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    plan_name = db.Column(db.String(50), nullable=False)          # Starter, Professional, Enterprise
    billing_cycle = db.Column(db.String(20), default='Monthly')   # Monthly, Yearly
    amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    currency = db.Column(db.String(10), default='INR')
    
    transaction_id = db.Column(db.String(255), nullable=False)   # UTR / Transaction Reference
    screenshot_url = db.Column(db.String(500), nullable=True)     # Path to uploaded receipt screenshot
    notes = db.Column(db.Text, nullable=True)
    
    status = db.Column(db.String(30), default='Pending Verification') # Pending Verification, Approved, Rejected
    rejection_reason = db.Column(db.Text, nullable=True)
    
    verified_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=_utc_now)

    organization = db.relationship('Organization', backref=db.backref('offline_payments', lazy=True))
    user = db.relationship('User', foreign_keys=[user_id])
    verified_by = db.relationship('User', foreign_keys=[verified_by_id])


class SubscriptionInvoice(db.Model):
    """Invoice generated for each billing event on a subscription"""
    __tablename__ = 'subscription_invoices'

    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)

    # Invoice Identity
    invoice_uid = db.Column(db.String(50), unique=True, nullable=False)  # INV-2026-0001
    invoice_number = db.Column(db.String(100), unique=True)              # human-readable
    invoice_date = db.Column(db.DateTime, default=_utc_now)
    due_date = db.Column(db.DateTime)

    # Billing Period
    billing_period_start = db.Column(db.DateTime)
    billing_period_end = db.Column(db.DateTime)

    # Plan details
    plan_name = db.Column(db.String(50))
    billing_cycle = db.Column(db.String(20))

    # Pricing
    base_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    discount_percent = db.Column(db.Numeric(5, 2), default=0.00, nullable=False)
    discount_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    gst_percent = db.Column(db.Numeric(5, 2), default=18.00, nullable=False)
    gst_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    currency = db.Column(db.String(10), default='INR')
    is_tax_inclusive = db.Column(db.Boolean, default=False)

    # Status
    invoice_status = db.Column(db.String(20), default='Draft')
    # Draft, Sent, Paid, Overdue, Cancelled, Refunded

    # Type & Metered breakdown
    invoice_type = db.Column(db.String(30), default='subscription') # subscription, pay_as_you_go
    usage_breakdown = db.Column(db.JSON, nullable=True) # itemized metrics, rates, units, subtotal

    # Link to payment
    payment_id = db.Column(db.Integer, db.ForeignKey('subscription_payments.id', use_alter=True, name='fk_invoice_payment_id'), nullable=True)

    # Storage
    pdf_path = db.Column(db.String(500))
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)

    # Relationships
    organization = db.relationship('Organization', backref=db.backref('invoices', lazy=True))
    payment = db.relationship('SubscriptionPayment', backref='invoice_record', foreign_keys=[payment_id])


# ============================
# MODULE: SOP Management
# ============================


class SaaSPlan(db.Model):
    """SaaS Product Plan definition (acts as template for Subscriptions)"""
    __tablename__ = 'saas_plans'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    long_description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='layers')
    color = db.Column(db.String(20), default='#3b82f6')
    status = db.Column(db.String(20), default='Active')      # Active, Inactive, Deprecated, Coming Soon
    plan_type = db.Column(db.String(100), default='Professional') # Starter, Professional, Enterprise, Custom, Trial, Pay-As-You-Go
    pricing_model = db.Column(db.String(30), default='fixed') # fixed, pay_as_you_go
    payg_rules = db.Column(db.JSON, nullable=True)           # Metered pricing rules (base_fee, user_rate, storage_rate, etc.)
    currency = db.Column(db.String(10), default='INR')
    is_custom = db.Column(db.Boolean, default=False)
    is_default_trial = db.Column(db.Boolean, default=False)
    trial_duration_days = db.Column(db.Integer, default=180)
    auto_approve_extensions_limit = db.Column(db.Integer, default=2)
    version = db.Column(db.Integer, default=1)
    
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)

    # Relationships
    pricing = db.relationship('SaaSPlanPricing', backref='plan', lazy=True, cascade='all, delete-orphan')
    limits = db.relationship('SaaSPlanLimits', backref='plan', lazy=True, uselist=False, cascade='all, delete-orphan')
    modules = db.relationship('SaaSPlanModules', backref='plan', lazy=True, cascade='all, delete-orphan')
    versions = db.relationship('SaaSPlanVersion', backref='plan', lazy=True, cascade='all, delete-orphan')
    analytics = db.relationship('SaaSPlanAnalytics', backref='plan', lazy=True, uselist=False, cascade='all, delete-orphan')


class SaaSPlanPricing(db.Model):
    """Pricing configuration for different billing cycles of a Plan"""
    __tablename__ = 'saas_plan_pricing'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('saas_plans.id', ondelete='CASCADE'), nullable=False)
    billing_cycle = db.Column(db.String(20), nullable=False)  # Monthly, Quarterly, Yearly, Lifetime
    price = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    discount = db.Column(db.Numeric(5, 2), default=0.00, nullable=False)              # Percentage discount
    tax = db.Column(db.Numeric(5, 2), default=18.00, nullable=False)                  # Default tax rate
    is_tax_inclusive = db.Column(db.Boolean, default=False)   # True if price includes GST
    is_active = db.Column(db.Boolean, default=True)


class SaaSPlanLimits(db.Model):
    """Usage limits imposed by a Plan"""
    __tablename__ = 'saas_plan_limits'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('saas_plans.id', ondelete='CASCADE'), nullable=False)
    max_users = db.Column(db.Integer, default=100)
    max_locations = db.Column(db.Integer, default=5)
    max_departments = db.Column(db.Integer, default=10)
    max_projects = db.Column(db.Integer, default=25)
    storage_limit_gb = db.Column(db.Float, default=10.0)
    api_limit = db.Column(db.Integer, default=10000)
    reports_limit = db.Column(db.Integer, default=100)
    dashboards_limit = db.Column(db.Integer, default=10)


class SaaSPlanModules(db.Model):
    """SaaS Modules enabled/disabled per Plan"""
    __tablename__ = 'saas_plan_modules'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('saas_plans.id', ondelete='CASCADE'), nullable=False)
    module_name = db.Column(db.String(50), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    is_premium = db.Column(db.Boolean, default=False)


class SaaSPlanVersion(db.Model):
    """Historical version snapshot for SaaS plans"""
    __tablename__ = 'saas_plan_versions'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('saas_plans.id', ondelete='CASCADE'), nullable=False)
    version = db.Column(db.Integer, nullable=False)
    plan_data = db.Column(db.JSON, nullable=False)  # Full JSON snapshot of limits, modules, pricing
    change_summary = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=_utc_now)

    created_by = db.relationship('User', foreign_keys=[created_by_id])


class SaaSPlanAnalytics(db.Model):
    """Aggregated subscriber analytics for a Plan"""
    __tablename__ = 'saas_plan_analytics'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('saas_plans.id', ondelete='CASCADE'), nullable=False)
    mrr = db.Column(db.Float, default=0.0)
    arr = db.Column(db.Float, default=0.0)
    subscriber_count = db.Column(db.Integer, default=0)
    renewal_rate = db.Column(db.Float, default=100.0)
    upgrade_rate = db.Column(db.Float, default=0.0)
    downgrade_rate = db.Column(db.Float, default=0.0)
    cancellation_rate = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)


class Module(db.Model):
    """Registry entry for an enterprise feature module & feature flag"""
    __tablename__ = 'modules'

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100), default='Core')  # Core, Quality, Reports, Analytics, AI, Security, Governance, etc.
    icon = db.Column(db.String(50), default='package')
    color = db.Column(db.String(50), default='#3b82f6')
    display_order = db.Column(db.Integer, default=0)
    navigation_route = db.Column(db.String(255))
    api_prefix = db.Column(db.String(255))
    status = db.Column(db.String(50), default='Active')  # Active, Inactive, Beta, Deprecated, Hidden, Coming Soon, Disabled
    development_stage = db.Column(db.String(50), default='Released') # Under Development, Internal, Testing, Beta, Released, Deprecated, Disabled, Removed
    version = db.Column(db.String(50), default='1.0.0')
    minimum_plan = db.Column(db.String(50), default='Starter') # Starter, Professional, Enterprise, Ultimate
    
    # Flags/Configuration
    enable_by_default = db.Column(db.Boolean, default=False)
    visible_in_sidebar = db.Column(db.Boolean, default=True)
    visible_in_dashboard = db.Column(db.Boolean, default=True)
    page_visibility = db.Column(db.Boolean, default=True)
    widget_visibility = db.Column(db.Boolean, default=True)
    button_visibility = db.Column(db.Boolean, default=True)

    backend_enabled = db.Column(db.Boolean, default=True)
    frontend_enabled = db.Column(db.Boolean, default=True)
    api_enabled = db.Column(db.Boolean, default=True)
    export_enabled = db.Column(db.Boolean, default=True)
    import_enabled = db.Column(db.Boolean, default=True)
    notification_enabled = db.Column(db.Boolean, default=True)
    background_jobs_enabled = db.Column(db.Boolean, default=True)

    requires_license = db.Column(db.Boolean, default=False)
    requires_subscription = db.Column(db.Boolean, default=True)
    premium_feature = db.Column(db.Boolean, default=False)
    ai_enabled = db.Column(db.Boolean, default=False)
    beta_feature = db.Column(db.Boolean, default=False)
    system_module = db.Column(db.Boolean, default=False)
    
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # JSON config for feature flags (beta, experimental, internal_only, premium_only, trial_only, etc.)
    feature_flags = db.Column(db.JSON, default=dict)
    
    is_archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)

    # Relationships
    parent = db.relationship('Module', remote_side=[id], backref=db.backref('children', lazy=True, cascade='all, delete-orphan'))
    dependencies = db.relationship('ModuleDependency', backref='module', lazy=True, cascade='all, delete-orphan', foreign_keys='ModuleDependency.module_id')
    assignments = db.relationship('ModuleAssignment', backref='module', lazy=True, cascade='all, delete-orphan')
    permissions = db.relationship('ModulePermission', backref='module', lazy=True, cascade='all, delete-orphan')
    analytics = db.relationship('ModuleUsageAnalytics', backref='module', lazy=True, cascade='all, delete-orphan')
    audit_logs = db.relationship('ModuleAuditLog', backref='module', lazy=True, cascade='all, delete-orphan')
    created_by = db.relationship('User', foreign_keys=[created_by_id])



class FeatureCategory(db.Model):
    """Registry table for feature module categorization"""
    __tablename__ = 'feature_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='folder')
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=_utc_now)


class FeatureVersion(db.Model):
    """Version snapshots for features"""
    __tablename__ = 'feature_versions'

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    version_number = db.Column(db.String(50), nullable=False)
    snapshot_json = db.Column(db.JSON, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=_utc_now)

    module = db.relationship('Module', backref=db.backref('versions_list', lazy=True, cascade='all, delete-orphan'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])


class ModuleDependency(db.Model):
    """Dependencies between modules"""
    __tablename__ = 'module_dependencies'

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    dependency_module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    dependency_type = db.Column(db.String(50), default='Required')  # Required, Blocked, Parent, Child

    # Relationship to get details of the dependency target
    dependency_module = db.relationship('Module', foreign_keys=[dependency_module_id])


class ModuleAssignment(db.Model):
    """Availability of modules to SaaS plans or specific organizations"""
    __tablename__ = 'module_assignments'

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    assigned_type = db.Column(db.String(50), nullable=False)  # Plan, Organization, Industry, Region, CustomerType
    assigned_target = db.Column(db.String(255), nullable=False)  # e.g., Starter, 15 (Org ID), Automotive, North, etc.
    assignment_metadata = db.Column(db.JSON, default=dict)  # Options like license key overrides


class ModulePermission(db.Model):
    """RBAC Permissions integration for modules"""
    __tablename__ = 'module_permissions'

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    role_name = db.Column(db.String(100), nullable=False)
    
    # Action access dict: {"view": true, "create": true, "update": true, "delete": true, "export": true, "approve": true, "admin": true}
    permissions = db.Column(db.JSON, default=dict)


class ModuleUsageAnalytics(db.Model):
    """Usage analytics metrics for module performance and growth trends"""
    __tablename__ = 'module_analytics'

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True)
    active_users = db.Column(db.Integer, default=0)
    daily_usage = db.Column(db.Integer, default=0)
    monthly_usage = db.Column(db.Integer, default=0)
    api_calls = db.Column(db.Integer, default=0)
    storage_consumption_mb = db.Column(db.Float, default=0.0)
    performance_ms = db.Column(db.Integer, default=0)
    error_rate = db.Column(db.Float, default=0.0)
    timestamp = db.Column(db.DateTime, default=_utc_now)


class ModuleAuditLog(db.Model):
    """Immutable audit logging for module adjustments"""
    __tablename__ = 'module_audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    admin_name = db.Column(db.String(150), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # CREATE, UPDATE, DISABLE, ENABLE, CHANGE_PERMISSION, ASSIGN_PLAN
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=_utc_now)


# ============================
# MODULE: Enterprise Analytics & Custom Reporting
# ============================

class AnalyticsCache(db.Model):
    __tablename__ = 'analytics_cache'
    id = db.Column(db.Integer, primary_key=True)
    cache_key = db.Column(db.String(150), unique=True, nullable=False, index=True)
    cache_data = db.Column(db.JSON, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=_utc_now)

class AnalyticsReport(db.Model):
    __tablename__ = 'analytics_reports'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True) # Null means global template
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    config_json = db.Column(db.JSON, nullable=False) # contains fields, metrics, grouping, sorting, charts, filters
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=_utc_now)

    organization = db.relationship('Organization', backref=db.backref('analytics_reports', lazy=True, cascade='all, delete-orphan'))
    created_by = db.relationship('User', backref=db.backref('created_reports', lazy=True))

class AnalyticsSchedule(db.Model):
    __tablename__ = 'analytics_schedules'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    report_id = db.Column(db.Integer, db.ForeignKey('analytics_reports.id', ondelete='CASCADE'), nullable=False)
    frequency = db.Column(db.String(50), default='Daily') # Daily, Weekly, Monthly
    format = db.Column(db.String(20), default='CSV') # CSV, Excel, PDF
    recipient_emails = db.Column(db.JSON, default=list) # JSON list of emails
    next_run = db.Column(db.DateTime)
    last_run = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=_utc_now)

    organization = db.relationship('Organization', backref=db.backref('analytics_schedules', lazy=True, cascade='all, delete-orphan'))
    report = db.relationship('AnalyticsReport', backref=db.backref('schedules', lazy=True, cascade='all, delete-orphan'))

class AnalyticsExport(db.Model):
    __tablename__ = 'analytics_exports'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    report_type = db.Column(db.String(100), nullable=False) # Revenue, Users, Modules, Custom, etc.
    format = db.Column(db.String(20), nullable=False) # CSV, Excel, PDF
    file_path = db.Column(db.String(500))
    filters_applied = db.Column(db.JSON, default=dict)
    generated_at = db.Column(db.DateTime, default=_utc_now)

    organization = db.relationship('Organization', backref=db.backref('analytics_exports', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('analytics_exports', lazy=True))

class AnalyticsAIInsights(db.Model):
    __tablename__ = 'analytics_ai_insights'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True) # Null means global
    insight_type = db.Column(db.String(100), nullable=False) # Revenue Forecast, Churn Prediction, Risk Score, etc.
    insight_json = db.Column(db.JSON, nullable=False)
    recommendation = db.Column(db.Text)
    generated_at = db.Column(db.DateTime, default=_utc_now)

    organization = db.relationship('Organization', backref=db.backref('analytics_ai_insights', lazy=True, cascade='all, delete-orphan'))

class AnalyticsUsage(db.Model):
    __tablename__ = 'analytics_usage'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    module_name = db.Column(db.String(100), nullable=False)
    feature_name = db.Column(db.String(100))
    action_type = db.Column(db.String(100), nullable=False) # login, api_call, view, click
    created_at = db.Column(db.DateTime, default=_utc_now)

    organization = db.relationship('Organization', backref=db.backref('analytics_usage', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('analytics_usage', lazy=True))


# ============================
# MODULE: Enterprise Billing & Revenue Management
# ============================

class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('subscription_invoices.id', ondelete='CASCADE'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0.0)
    amount = db.Column(db.Float, default=0.0)

    invoice = db.relationship('SubscriptionInvoice', backref=db.backref('items', lazy=True, cascade='all, delete-orphan'))

class SubscriptionRefund(db.Model):
    __tablename__ = 'subscription_refunds'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('subscription_invoices.id', ondelete='CASCADE'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('subscription_payments.id', ondelete='CASCADE'), nullable=False)
    refund_uid = db.Column(db.String(50), unique=True, nullable=False)
    amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    reason = db.Column(db.String(255))
    status = db.Column(db.String(20), default='Approved')  # Pending, Approved, Rejected
    created_at = db.Column(db.DateTime, default=_utc_now)

    invoice = db.relationship('SubscriptionInvoice', backref=db.backref('refund_records', lazy=True, cascade='all, delete-orphan'))
    payment = db.relationship('SubscriptionPayment', backref=db.backref('refund_records', lazy=True))

class SubscriptionCreditNote(db.Model):
    __tablename__ = 'subscription_credit_notes'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('subscription_invoices.id', ondelete='SET NULL'), nullable=True)
    credit_note_uid = db.Column(db.String(50), unique=True, nullable=False)
    amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    balance = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    status = db.Column(db.String(20), default='Active')  # Active, Applied, Void
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=_utc_now)

    organization = db.relationship('Organization', backref=db.backref('credit_notes', lazy=True))
    invoice = db.relationship('SubscriptionInvoice', backref=db.backref('credit_notes', lazy=True))

class BillingSettings(db.Model):
    __tablename__ = 'billing_settings'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), unique=True, nullable=False)
    auto_collection = db.Column(db.Boolean, default=True)
    reminder_schedule = db.Column(db.JSON, default=lambda: [3, 1, 0, -3])  # days before/after due date
    grace_period_days = db.Column(db.Integer, default=7)
    payment_retry_attempts = db.Column(db.Integer, default=3)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)

    organization = db.relationship('Organization', backref=db.backref('billing_settings', uselist=False, lazy=True))

class TaxRule(db.Model):
    __tablename__ = 'tax_rules'
    id = db.Column(db.Integer, primary_key=True)
    country = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100))  # e.g., state code for IGST vs SGST/CGST
    tax_type = db.Column(db.String(50), default='GST')  # GST, VAT, custom
    rate = db.Column(db.Float, default=18.0)
    is_exempt = db.Column(db.Boolean, default=False)

class BillingAudit(db.Model):
    __tablename__ = 'billing_audits'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('subscription_invoices.id', ondelete='SET NULL'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # Created, Paid, Refunded, etc.
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=_utc_now)

    organization = db.relationship('Organization', backref=db.backref('billing_audits', lazy=True))
    invoice = db.relationship('SubscriptionInvoice', backref=db.backref('billing_audits', lazy=True))
    user = db.relationship('User', backref=db.backref('billing_audits', lazy=True))




# ============================
# MODULE: Enterprise Announcements
# ============================

class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    ann_number = db.Column(db.String(50), unique=True, nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    title = db.Column(db.String(500), nullable=False)
    summary = db.Column(db.Text)
    body = db.Column(db.Text)
    banner_url = db.Column(db.String(500))
    tags = db.Column(db.JSON, default=list)
    category = db.Column(db.String(50), default='General')
    priority = db.Column(db.String(20), default='Medium')
    status = db.Column(db.String(20), default='Draft')
    publish_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)
    timezone = db.Column(db.String(50), default='UTC')
    published_at = db.Column(db.DateTime)
    channels = db.Column(db.JSON, default=lambda: {'in_app': True, 'email': False, 'sms': False, 'push': False})
    audience_type = db.Column(db.String(20), default='all')
    total_delivered = db.Column(db.Integer, default=0)
    total_viewed = db.Column(db.Integer, default=0)
    total_read = db.Column(db.Integer, default=0)
    total_clicked = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)
    author = db.relationship('User', backref='authored_announcements', foreign_keys=[created_by])
    audience = db.relationship('AnnouncementAudience', backref='announcement', cascade='all, delete-orphan', lazy=True)
    deliveries = db.relationship('AnnouncementDelivery', backref='announcement', cascade='all, delete-orphan', lazy=True)
    reads = db.relationship('AnnouncementRead', backref='announcement', cascade='all, delete-orphan', lazy=True)
    attachments = db.relationship('AnnouncementAttachment', backref='announcement', cascade='all, delete-orphan', lazy=True)
    audit_logs = db.relationship('AnnouncementAudit', backref='announcement', cascade='all, delete-orphan', lazy=True)


class AnnouncementAudience(db.Model):
    __tablename__ = 'announcement_audience'
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements.id', ondelete='CASCADE'), nullable=False)
    target_type = db.Column(db.String(30), nullable=False)
    target_value = db.Column(db.String(255), nullable=False)


class AnnouncementDelivery(db.Model):
    __tablename__ = 'announcement_delivery'
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements.id', ondelete='CASCADE'), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    channel = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    sent_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    retry_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=_utc_now)


class AnnouncementRead(db.Model):
    __tablename__ = 'announcement_reads'
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    viewed_at = db.Column(db.DateTime)
    read_at = db.Column(db.DateTime)
    clicked_at = db.Column(db.DateTime)
    dismissed_at = db.Column(db.DateTime)
    device = db.Column(db.String(30))
    browser = db.Column(db.String(50))
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=_utc_now)


class AnnouncementAttachment(db.Model):
    __tablename__ = 'announcement_attachments'
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements.id', ondelete='CASCADE'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, default=0)
    file_type = db.Column(db.String(50))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=_utc_now)


class AnnouncementAudit(db.Model):
    __tablename__ = 'announcement_audit'
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=_utc_now)
    actor = db.relationship('User', backref='announcement_audits')


# --- ENTERPRISE INTEGRATION HUB MODELS ---

class IntegrationConfig(db.Model):
    __tablename__ = 'integration_configs'
    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.String(100), unique=True, nullable=False)
    provider_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='Disconnected') # Connected, Disconnected, Disabled, Error
    version = db.Column(db.String(20), default='v1.0.0')
    settings = db.Column(db.JSON, default=dict) # JSON settings containing public keys, urls, hosts
    health_score = db.Column(db.Integer, default=100)
    last_sync = db.Column(db.DateTime, default=_utc_now)
    usage_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)


class IntegrationApiKey(db.Model):
    __tablename__ = 'integration_api_keys'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    key_prefix = db.Column(db.String(15), default='qc_live_')
    api_key_hash = db.Column(db.String(255), unique=True, nullable=False)
    secret_key_masked = db.Column(db.String(255))
    status = db.Column(db.String(20), default='Active') # Active, Disabled, Revoked
    expiration_date = db.Column(db.DateTime)
    rate_limit = db.Column(db.Integer, default=60)
    allowed_ips = db.Column(db.JSON, default=list)
    allowed_domains = db.Column(db.JSON, default=list)
    scopes = db.Column(db.JSON, default=list)
    owner = db.Column(db.String(100))
    usage_count = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=_utc_now)


class IntegrationWebhook(db.Model):
    __tablename__ = 'integration_webhooks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    secret = db.Column(db.String(255))
    status = db.Column(db.String(20), default='Active') # Active, Disabled
    headers = db.Column(db.JSON, default=dict)
    events = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=_utc_now)


class IntegrationWebhookDelivery(db.Model):
    __tablename__ = 'integration_webhook_deliveries'
    id = db.Column(db.Integer, primary_key=True)
    webhook_id = db.Column(db.Integer, db.ForeignKey('integration_webhooks.id', ondelete='CASCADE'), nullable=False)
    event = db.Column(db.String(100), nullable=False)
    payload = db.Column(db.JSON)
    response_code = db.Column(db.Integer)
    response_body = db.Column(db.Text)
    latency_ms = db.Column(db.Float, default=0.0)
    retry_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20)) # Success, Failed, Pending
    created_at = db.Column(db.DateTime, default=_utc_now)


class IntegrationAuditLog(db.Model):
    __tablename__ = 'integration_audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    provider_id = db.Column(db.String(100))
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=_utc_now)


# ---------------------------------------------------------------------------
# Compliance Standards — per-organisation certificate & audit data
# ---------------------------------------------------------------------------

class IntegrationApiLog(db.Model):
    """Audit log for API requests received via Integration API."""
    __tablename__ = 'integration_api_logs'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    ip_address = db.Column(db.String(50))
    api_key_used = db.Column(db.String(100))
    request_time = db.Column(db.DateTime, default=_utc_now)
    response_time_ms = db.Column(db.Float, default=0.0)
    endpoint = db.Column(db.String(255))
    status_code = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=_utc_now)


# ---------------------------------------------------------------------------
# Document Identity, Branding & Template Management System & Usage Mapping Models
# ---------------------------------------------------------------------------

class PlatformIdentityConfig(db.Model):
    """Centralized Platform Identity parameters."""
    __tablename__ = 'platform_identity'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    software_name = db.Column(db.String(255), default="QCMS Enterprise OS")
    software_short_name = db.Column(db.String(100), default="QCMS")
    software_display_name = db.Column(db.String(255), default="QCMS Enterprise Platform")
    platform_title = db.Column(db.String(255), default="QCMS Quality Management System")
    platform_subtitle = db.Column(db.String(255), default="Enterprise Quality & Compliance Management System")
    tagline = db.Column(db.String(255), default="Accelerating Enterprise Excellence & Compliance")
    version = db.Column(db.String(50), default="v4.8.2-PROD")
    edition = db.Column(db.String(100), default="Enterprise Cloud Edition")
    website = db.Column(db.String(255), default="https://qcms.io")
    support_portal = db.Column(db.String(255), default="https://support.qcms.io")
    copyright_text = db.Column(db.String(255), default="© 2026 QCMS Enterprise Solutions. All rights reserved.")
    footer_copyright = db.Column(db.String(255), default="Confidential & Proprietary — Generated by QCMS Enterprise OS")
    default_language = db.Column(db.String(20), default="en")
    default_currency = db.Column(db.String(10), default="INR")
    default_timezone = db.Column(db.String(50), default="UTC")
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)


class CompanyInformationConfig(db.Model):
    """Legal & Corporate Company Information parameters."""
    __tablename__ = 'company_information'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    legal_company_name = db.Column(db.String(255), default="QCMS Technologies Pvt Ltd")
    trading_name = db.Column(db.String(255), default="QCMS Solutions")
    company_description = db.Column(db.Text, default="Enterprise Quality, Compliance & SOP Management Software")
    gstin = db.Column(db.String(50), default="27AAACQ1234F1Z9")
    pan = db.Column(db.String(50), default="AAACQ1234F")
    cin = db.Column(db.String(50), default="U72200MH2026PTC123456")
    msme = db.Column(db.String(50), default="UDYAM-MH-01-0012345")
    registration_number = db.Column(db.String(100), default="REG-2026-98765")
    tax_number = db.Column(db.String(100), default="TAX-IN-889977")
    license_number = db.Column(db.String(100), default="LIC-QCMS-ENT-2026")
    trademark = db.Column(db.String(255), default="QCMS® Registered Trademark")
    official_seal_url = db.Column(db.String(500), default="/assets/img/official_seal.png")
    digital_signature_url = db.Column(db.String(500), default="/assets/img/digital_signature.png")
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)


class CompanyContactsConfig(db.Model):
    """Company Contact Directory parameters."""
    __tablename__ = 'company_contacts'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    general_email = db.Column(db.String(255), default="info@qcms.com")
    general_sender_name = db.Column(db.String(255), default="QCMS General Info")
    support_email = db.Column(db.String(255), default="support@ifqm.org.in")
    support_sender_name = db.Column(db.String(255), default="QCMS Customer Support")
    billing_email = db.Column(db.String(255), default="billing@qcms.com")
    billing_sender_name = db.Column(db.String(255), default="QCMS Accounts & Billing")
    otp_email = db.Column(db.String(255), default="otp-auth@qcms.com")
    otp_sender_name = db.Column(db.String(255), default="QCMS OTP Verification")
    contact_email = db.Column(db.String(255), default="contact@qcms.com")
    contact_sender_name = db.Column(db.String(255), default="QCMS Business Inquiries")
    alerts_email = db.Column(db.String(255), default="alerts@qcms.com")
    alerts_sender_name = db.Column(db.String(255), default="QCMS System Alerts")
    feedback_email = db.Column(db.String(255), default="feedback@qcms.com")
    feedback_sender_name = db.Column(db.String(255), default="QCMS Product Feedback")
    onboarding_email = db.Column(db.String(255), default="onboarding@qcms.com")
    onboarding_sender_name = db.Column(db.String(255), default="QCMS User Onboarding")
    sales_email = db.Column(db.String(255), default="sales@qcms.com")
    legal_email = db.Column(db.String(255), default="legal@qcms.com")
    compliance_email = db.Column(db.String(255), default="compliance@qcms.com")
    privacy_email = db.Column(db.String(255), default="privacy@qcms.com")
    general_phone = db.Column(db.String(50), default="+1 (800) 555-0199")
    support_phone = db.Column(db.String(50), default="+1 (800) 555-0100")
    emergency_contact = db.Column(db.String(50), default="+91 98765 43210")
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)


class CompanyAddressesConfig(db.Model):
    """Office Address parameters."""
    __tablename__ = 'company_addresses'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    registered_office = db.Column(db.Text, default="Suite 800, Innovation Tower, BKC, Mumbai, MH 400051, India")
    corporate_office = db.Column(db.Text, default="Tech Park Phase 2, Whitefield, Bengaluru, KA 560066, India")
    billing_office = db.Column(db.Text, default="Financial Center, Suite 400, Mumbai, MH 400051, India")
    country = db.Column(db.String(100), default="India")
    state = db.Column(db.String(100), default="Maharashtra")
    city = db.Column(db.String(100), default="Mumbai")
    pin = db.Column(db.String(20), default="400051")
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)


class BrandingAssetsConfig(db.Model):
    """Branding Asset URLs & Graphics."""
    __tablename__ = 'branding_assets'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    favicon_url = db.Column(db.String(500), default="/assets/img/favicon.ico")
    logo_url = db.Column(db.String(500), default="/assets/img/logo.png")
    dark_logo_url = db.Column(db.String(500), default="/assets/img/logo-dark.png")
    light_logo_url = db.Column(db.String(500), default="/assets/img/logo-light.png")
    print_logo_url = db.Column(db.String(500), default="/assets/img/logo-print.png")
    pdf_logo_url = db.Column(db.String(500), default="/assets/img/logo-pdf.png")
    email_logo_url = db.Column(db.String(500), default="/assets/img/logo-email.png")
    watermark_logo_url = db.Column(db.String(500), default="/assets/img/watermark.png")
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)


class DocumentTemplateConfig(db.Model):
    """Document Branding & Template Config per document type."""
    __tablename__ = 'document_templates'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    template_key = db.Column(db.String(100), nullable=False)
    template_name = db.Column(db.String(255), nullable=False)
    header_title = db.Column(db.String(255))
    subtitle = db.Column(db.String(255))
    header_text = db.Column(db.Text)
    footer_text = db.Column(db.Text)
    watermark_text = db.Column(db.String(255), default="CONFIDENTIAL")
    confidential_text = db.Column(db.String(255), default="STRICTLY CONFIDENTIAL — INTERNAL USE ONLY")
    terms_and_conditions = db.Column(db.Text)
    disclaimer_text = db.Column(db.Text)
    enable_qr_verification = db.Column(db.Boolean, default=True)
    enable_digital_signature = db.Column(db.Boolean, default=True)
    settings_json = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)


class SettingUsageMap(db.Model):
    """Usage Mapping & Dependency Explorer registry."""
    __tablename__ = 'setting_usage_map'

    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), nullable=False, index=True)
    setting_name = db.Column(db.String(255), nullable=False)
    module = db.Column(db.String(100), nullable=False)
    feature = db.Column(db.String(100), nullable=False)
    component = db.Column(db.String(255), nullable=False)
    page = db.Column(db.String(255))
    route = db.Column(db.String(255))
    backend_service = db.Column(db.String(255))
    document_type = db.Column(db.String(100))
    template = db.Column(db.String(255))
    export_type = db.Column(db.String(50))
    file_path = db.Column(db.String(500))
    dependency_type = db.Column(db.String(50), default="Direct")
    usage_category = db.Column(db.String(50), default="Branding")
    last_verified = db.Column(db.DateTime, default=_utc_now)
    created_at = db.Column(db.DateTime, default=_utc_now)

    def to_dict(self):
        return {
            'id': self.id,
            'setting_key': self.setting_key,
            'setting_name': self.setting_name,
            'module': self.module,
            'feature': self.feature,
            'component': self.component,
            'page': self.page,
            'route': self.route,
            'backend_service': self.backend_service,
            'document_type': self.document_type,
            'template': self.template,
            'export_type': self.export_type,
            'file_path': self.file_path,
            'dependency_type': self.dependency_type,
            'usage_category': self.usage_category,
            'last_verified': self.last_verified.isoformat() if self.last_verified else None
        }


# ---------------------------------------------------------------------------
# Email Notification & Automation Rules Models
# ---------------------------------------------------------------------------

class EmailNotificationRule(db.Model):
    """Configuration for Automated & Broadcast Email Notifications."""
    __tablename__ = 'email_notification_rules'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), default='custom') # subscription_reminder, trial_reminder, maintenance, welcome, usage_guide, new_feature, support, custom
    description = db.Column(db.Text, nullable=True)
    
    # Email Content
    subject = db.Column(db.String(500), nullable=False)
    preheader = db.Column(db.String(255), nullable=True)
    heading = db.Column(db.String(255), nullable=True)
    body_html = db.Column(db.Text, nullable=False)
    banner_color = db.Column(db.String(50), default='#2563eb')
    cta_text = db.Column(db.String(100), nullable=True)
    cta_url = db.Column(db.String(500), nullable=True)
    
    # Sender Configuration
    sender_email = db.Column(db.String(255), default='notifications@qcms.com')
    sender_name = db.Column(db.String(255), default='QCMS Enterprise Notifications')
    reply_to = db.Column(db.String(255), nullable=True)
    
    # Triggers & Timing
    trigger_type = db.Column(db.String(50), default='manual') # event, scheduled, manual
    event_trigger = db.Column(db.String(100), nullable=True) # subscription_expiring_soon, trial_expiring_soon, subscription_expired, new_org_welcome, new_user_welcome
    trigger_days_before = db.Column(db.Integer, default=7) # e.g. 7, 3, 1, 0
    scheduled_at = db.Column(db.DateTime, nullable=True)
    
    # Audience & Targeting Filters
    target_audience_type = db.Column(db.String(50), default='all') # all, specific_orgs, role_based, subscription_based
    target_org_ids = db.Column(db.JSON, default=list) # [1, 2, 3] or []
    target_roles = db.Column(db.JSON, default=list) # ["Admin", "CEO", "All"]
    target_plans = db.Column(db.JSON, default=list) # ["Small MSME's", "Enterprise"]
    target_statuses = db.Column(db.JSON, default=list) # ["Active", "Trial", "Expiring", "Suspended"]

    # SMS Notification Configuration (Gio DLT / Kaleyra Gateway)
    sms_enabled = db.Column(db.Boolean, default=False)           # Send SMS alongside email
    sms_template_id = db.Column(db.String(100), nullable=True)   # Gio DLT registered Template ID
    sms_entity_id = db.Column(db.String(100), nullable=True)     # DLT Entity / PE ID
    sms_sender_id = db.Column(db.String(20), nullable=True)      # 6-char DLT approved Sender ID (e.g. IFQMSK)
    sms_body = db.Column(db.Text, nullable=True)                 # SMS body with {{variable}} placeholders
    sms_total_sent = db.Column(db.Integer, default=0)

    # State & Audit
    is_active = db.Column(db.Boolean, default=True)
    is_system_preset = db.Column(db.Boolean, default=False)
    last_triggered_at = db.Column(db.DateTime, nullable=True)
    total_sent = db.Column(db.Integer, default=0)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)

    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description or '',
            'subject': self.subject,
            'preheader': self.preheader or '',
            'heading': self.heading or '',
            'body_html': self.body_html,
            'banner_color': self.banner_color or '#2563eb',
            'cta_text': self.cta_text or '',
            'cta_url': self.cta_url or '',
            'sender_email': self.sender_email,
            'sender_name': self.sender_name,
            'reply_to': self.reply_to or '',
            'trigger_type': self.trigger_type,
            'event_trigger': self.event_trigger or '',
            'trigger_days_before': self.trigger_days_before,
            'scheduled_at': self.scheduled_at.isoformat() + 'Z' if self.scheduled_at else None,
            'target_audience_type': self.target_audience_type,
            'target_org_ids': self.target_org_ids or [],
            'target_roles': self.target_roles or [],
            'target_plans': self.target_plans or [],
            'target_statuses': self.target_statuses or [],
            'is_active': self.is_active,
            'is_system_preset': self.is_system_preset,
            'last_triggered_at': self.last_triggered_at.isoformat() + 'Z' if self.last_triggered_at else None,
            'total_sent': self.total_sent or 0,
            # SMS fields
            'sms_enabled': self.sms_enabled or False,
            'sms_template_id': self.sms_template_id or '',
            'sms_entity_id': self.sms_entity_id or '',
            'sms_sender_id': self.sms_sender_id or '',
            'sms_body': self.sms_body or '',
            'sms_total_sent': self.sms_total_sent or 0,
            'created_by': self.created_by.username if self.created_by else 'Super Admin',
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None
        }


class SmsTemplateConfig(db.Model):
    """Standalone SMS Template Configurations for system-level SMS (OTP, alerts, quality events, audience targeting)."""
    __tablename__ = 'sms_template_configs'

    id = db.Column(db.Integer, primary_key=True)
    template_key = db.Column(db.String(100), unique=True, nullable=False)  # e.g. phone_otp_verification
    display_name = db.Column(db.String(255), nullable=False)               # Human-readable label
    category = db.Column(db.String(100), default='custom')                 # auth, quality, subscription, billing, etc.
    description = db.Column(db.Text, nullable=True)
    template_id = db.Column(db.String(100), nullable=True)                 # Gio DLT Template ID
    entity_id = db.Column(db.String(100), nullable=True)                   # DLT Entity / PE ID
    sender_id = db.Column(db.String(20), nullable=True)                    # 6-char DLT Sender ID (e.g. IFQMSK)
    body = db.Column(db.Text, nullable=True)                               # SMS body with {{variable}} placeholders

    # Triggers & Timing
    trigger_type = db.Column(db.String(50), default='event')               # event, scheduled, manual
    event_trigger = db.Column(db.String(100), nullable=True)
    trigger_days_before = db.Column(db.Integer, default=0)
    scheduled_at = db.Column(db.DateTime, nullable=True)

    # Audience & Targeting Filters
    target_audience_type = db.Column(db.String(50), default='all')         # all, specific_orgs, role_based, subscription_based
    target_org_ids = db.Column(db.JSON, default=list)                      # [1, 2, 3] or []
    target_roles = db.Column(db.JSON, default=list)                        # ["Admin", "CEO", "All"]
    target_plans = db.Column(db.JSON, default=list)                        # ["Small MSME's", "Enterprise"]
    target_statuses = db.Column(db.JSON, default=list)                     # ["Active", "Trial", "Expiring", "Suspended"]

    is_active = db.Column(db.Boolean, default=True)
    is_system_preset = db.Column(db.Boolean, default=True)
    total_sent = db.Column(db.Integer, default=0)
    last_triggered_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=_utc_now)
    updated_at = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now)

    def to_dict(self):
        return {
            'id': self.id,
            'template_key': self.template_key,
            'display_name': self.display_name,
            'category': self.category or 'custom',
            'description': self.description or '',
            'template_id': self.template_id or '',
            'entity_id': self.entity_id or '',
            'sender_id': self.sender_id or '',
            'body': self.body or '',
            'trigger_type': self.trigger_type or 'event',
            'event_trigger': self.event_trigger or '',
            'trigger_days_before': self.trigger_days_before or 0,
            'scheduled_at': self.scheduled_at.isoformat() + 'Z' if self.scheduled_at else None,
            'target_audience_type': self.target_audience_type or 'all',
            'target_org_ids': self.target_org_ids or [],
            'target_roles': self.target_roles or [],
            'target_plans': self.target_plans or [],
            'target_statuses': self.target_statuses or [],
            'is_active': self.is_active,
            'is_system_preset': self.is_system_preset,
            'total_sent': self.total_sent or 0,
            'last_triggered_at': self.last_triggered_at.isoformat() + 'Z' if self.last_triggered_at else None,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None
        }


class EmailNotificationLog(db.Model):
    """Delivery log for email notifications sent via rules or manual broadcasts."""
    __tablename__ = 'email_notification_logs'

    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('email_notification_rules.id', ondelete='SET NULL'), nullable=True)
    rule_name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), default='custom')
    subject = db.Column(db.String(500), nullable=False)
    sender_email = db.Column(db.String(255), nullable=False)
    sender_name = db.Column(db.String(255), nullable=True)
    recipient_count = db.Column(db.Integer, default=0)
    recipients_summary = db.Column(db.JSON, default=list)
    status = db.Column(db.String(50), default='Delivered') # Delivered, Failed, Partially Delivered, Processing
    error_message = db.Column(db.Text, nullable=True)
    sent_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    sent_at = db.Column(db.DateTime, default=_utc_now)

    rule = db.relationship('EmailNotificationRule', foreign_keys=[rule_id])
    sent_by = db.relationship('User', foreign_keys=[sent_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'category': self.category,
            'subject': self.subject,
            'sender_email': self.sender_email,
            'sender_name': self.sender_name or '',
            'recipient_count': self.recipient_count,
            'recipients_summary': self.recipients_summary or [],
            'status': self.status,
            'error_message': self.error_message or '',
            'sent_by': self.sent_by.username if self.sent_by else 'System Automation',
            'sent_at': self.sent_at.isoformat() + 'Z' if self.sent_at else None
        }


class SmsNotificationLog(db.Model):
    """Delivery log for SMS notifications sent via templates, OTPs, or manual broadcasts."""
    __tablename__ = 'sms_notification_logs'

    id = db.Column(db.Integer, primary_key=True)
    template_key = db.Column(db.String(100), nullable=True)
    template_name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), default='custom')
    sender_id = db.Column(db.String(20), nullable=True)
    dlt_template_id = db.Column(db.String(100), nullable=True)
    dlt_entity_id = db.Column(db.String(100), nullable=True)
    message_body = db.Column(db.Text, nullable=False)
    phone_number = db.Column(db.String(50), nullable=False)
    recipient_name = db.Column(db.String(255), nullable=True)
    org_name = db.Column(db.String(255), nullable=True)
    gateway = db.Column(db.String(100), default='Fast2SMS / Resend')
    status = db.Column(db.String(50), default='Delivered')  # Delivered, Sent, Failed
    error_message = db.Column(db.Text, nullable=True)
    sent_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    sent_at = db.Column(db.DateTime, default=_utc_now)

    sent_by = db.relationship('User', foreign_keys=[sent_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'template_key': self.template_key or '',
            'template_name': self.template_name or '',
            'category': self.category or 'custom',
            'sender_id': self.sender_id or 'IFQMSK',
            'dlt_template_id': self.dlt_template_id or '',
            'dlt_entity_id': self.dlt_entity_id or '',
            'message_body': self.message_body or '',
            'phone_number': self.phone_number or '',
            'recipient_name': self.recipient_name or 'Team Member',
            'org_name': self.org_name or 'Enterprise Org',
            'gateway': self.gateway or 'Fast2SMS / Resend',
            'status': self.status or 'Delivered',
            'error_message': self.error_message or '',
            'sent_by': self.sent_by.username if self.sent_by else 'System Automation',
            'sent_at': self.sent_at.isoformat() + 'Z' if self.sent_at else None
        }

# Domain & Backward-Compatibility Aliases
SubscriptionPlan = SaaSPlan
BillingInvoice = SubscriptionInvoice
