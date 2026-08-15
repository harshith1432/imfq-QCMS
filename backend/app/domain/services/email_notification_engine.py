import os
import re
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import func, or_
from app import db
from app.infrastructure.database.models.models import (
    User, Organization, Role, Subscription, SaaSPlan, EmailNotificationRule, EmailNotificationLog
)
from app.infrastructure.mailer.email_service import EmailUtils
from app.domain.services.document_branding_service import DocumentBrandingService


DEFAULT_NOTIFICATION_PRESETS = [
    {
        "name": "Subscription Expiry Reminder (7 Days)",
        "category": "subscription_reminder",
        "description": "Automatically notifies organization administrators 7 days before their subscription renewal date.",
        "subject": "Action Required: Your {{plan_name}} subscription expires in 7 days",
        "preheader": "Renew now to ensure uninterrupted team access to QCMS Enterprise OS.",
        "heading": "Your Subscription is Expiring Soon",
        "banner_color": "#2563eb",
        "body_html": """<p>Dear <strong>{{user_name}}</strong>,</p>
<p>This is a courtesy reminder that your organization's <strong>{{plan_name}}</strong> subscription for <strong>{{org_name}}</strong> will expire in <strong>{{days_left}} days</strong> on <strong>{{expiry_date}}</strong>.</p>
<p>To avoid any disruption to your team's quality workflows, 8-stage projects, and audit logs, please renew or upgrade your subscription plan today.</p>
<div style="background: rgba(37,99,235,0.06); border-left: 4px solid #2563eb; padding: 12px 16px; margin: 20px 0; border-radius: 4px;">
    <strong>Account Summary:</strong><br>
    • Organization: <strong>{{org_name}}</strong><br>
    • Current Plan: <strong>{{plan_name}}</strong><br>
    • Expiry Date: <strong>{{expiry_date}}</strong> ({{days_left}} days remaining)
</div>
<p>If you have already processed your renewal, please disregard this notice. For custom enterprise billing or PO invoicing, contact our support team.</p>""",
        "cta_text": "Renew / Upgrade Plan Now",
        "cta_url": "{{app_url}}/admin/settings.html?tab=billing",
        "trigger_type": "event",
        "event_trigger": "subscription_expiring_soon",
        "trigger_days_before": 7,
        "target_audience_type": "subscription_based",
        "target_roles": ["Admin", "CEO"],
        "target_statuses": ["Active"],
        "is_active": True,
        "is_system_preset": True
    },
    {
        "name": "Subscription Expiry Urgent Notice (1 Day)",
        "category": "subscription_reminder",
        "description": "Urgent reminder sent 24 hours before subscription expiration to prevent workflow interruption.",
        "subject": "URGENT: Your {{plan_name}} subscription expires tomorrow",
        "preheader": "Immediate action required: Subscription for {{org_name}} expires in 24 hours.",
        "heading": "Urgent: Final Subscription Expiry Notice",
        "banner_color": "#dc2626",
        "body_html": """<p>Dear <strong>{{user_name}}</strong>,</p>
<p>Your subscription for <strong>{{org_name}}</strong> is scheduled to expire <strong>tomorrow, {{expiry_date}}</strong>.</p>
<p>Upon expiration, new project creations and stage review approvals may be temporarily paused until your subscription renewal is completed.</p>
<p>Please complete your payment checkout immediately using our instant payment options (UPI, Razorpay, Bank Transfer).</p>""",
        "cta_text": "Complete Immediate Renewal",
        "cta_url": "{{app_url}}/admin/settings.html?tab=billing",
        "trigger_type": "event",
        "event_trigger": "subscription_expiring_soon",
        "trigger_days_before": 1,
        "target_audience_type": "subscription_based",
        "target_roles": ["Admin", "CEO"],
        "target_statuses": ["Active"],
        "is_active": True,
        "is_system_preset": True
    },
    {
        "name": "Trial Plan Ending Reminder (3 Days)",
        "category": "trial_reminder",
        "description": "Notifies trial organizations 3 days before their free onboarding trial lapses.",
        "subject": "Your free trial for {{org_name}} ends in 3 days – Upgrade today!",
        "preheader": "Keep your quality data, audits, and projects active with an enterprise plan.",
        "heading": "Your Free Trial is Ending Soon",
        "banner_color": "#d97706",
        "body_html": """<p>Hello <strong>{{user_name}}</strong>,</p>
<p>We hope your team is enjoying exploring <strong>QCMS Enterprise OS</strong>! Your free onboarding trial for <strong>{{org_name}}</strong> will conclude in <strong>{{days_left}} days</strong> on <strong>{{expiry_date}}</strong>.</p>
<p>Upgrade to a commercial plan today to unlock unlimited projects, increased storage capacity, custom stage templates, and full team collaboration.</p>
<p>Need more time to evaluate? You can also request a trial extension directly from your settings panel.</p>""",
        "cta_text": "Explore Plans & Upgrade",
        "cta_url": "{{app_url}}/admin/settings.html?tab=billing",
        "trigger_type": "event",
        "event_trigger": "trial_expiring_soon",
        "trigger_days_before": 3,
        "target_audience_type": "subscription_based",
        "target_roles": ["Admin", "CEO"],
        "target_statuses": ["Trial"],
        "is_active": True,
        "is_system_preset": True
    },
    {
        "name": "Scheduled Software Maintenance & Downtime Notice",
        "category": "maintenance",
        "description": "Informs users of upcoming platform maintenance windows and system upgrades.",
        "subject": "Scheduled Platform Maintenance Notice: QCMS Enterprise OS",
        "preheader": "Notice of scheduled maintenance to enhance performance, security, and reliability.",
        "heading": "Scheduled System Maintenance",
        "banner_color": "#4f46e5",
        "body_html": """<p>Dear <strong>{{user_name}}</strong>,</p>
<p>To ensure optimal platform reliability, database performance, and security enhancements, we have scheduled a planned maintenance window.</p>
<div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 16px; margin: 18px 0;">
    <strong>Maintenance Schedule Details:</strong><br>
    • <strong>Date & Time:</strong> Sunday at 02:00 AM – 04:00 AM IST (Expected 2 hours)<br>
    • <strong>Affected Services:</strong> Web application access & API sync<br>
    • <strong>Impact:</strong> Brief intermittent connectivity during database indexing
</div>
<p>All data and project records remain completely secure. We recommend saving any active draft edits before the maintenance window begins.</p>""",
        "cta_text": "Check System Status",
        "cta_url": "{{app_url}}/dashboard/dashboard-admin.html",
        "trigger_type": "manual",
        "target_audience_type": "all",
        "target_roles": ["All"],
        "is_active": True,
        "is_system_preset": True
    },
    {
        "name": "Welcome & Onboarding to QCMS Enterprise OS",
        "category": "welcome",
        "description": "Comprehensive onboarding guide sent automatically to administrators upon organization registration, covering trial access, role assignments, corporate profile completion, and subscription plans.",
        "subject": "Welcome to QCMS Enterprise OS – Essential Onboarding & Setup Guide for {{org_name}}",
        "preheader": "Welcome aboard {{org_name}}! Here is your complete administrator quickstart guide, trial details, and role manual.",
        "heading": "Welcome to QCMS Enterprise Quality Management OS",
        "banner_color": "#16a34a",
        "body_html": """<p>Dear <strong>{{user_name}}</strong>,</p>

<p>Congratulations and welcome to <strong>QCMS Enterprise OS</strong>! Your organization workspace for <strong>{{org_name}}</strong> has been successfully provisioned and is active.</p>

<div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 18px 20px; margin: 20px 0;">
    <div style="font-size: 15px; font-weight: bold; color: #166534; margin-bottom: 8px;">
        🎯 Your Active Workspace &amp; Trial Plan Summary
    </div>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px; color: #1e293b;">
        <tr>
            <td style="padding: 4px 0; width: 45%; color: #64748b;">• <strong>Organization Name:</strong></td>
            <td style="padding: 4px 0; font-weight: 600;">{{org_name}}</td>
        </tr>
        <tr>
            <td style="padding: 4px 0; color: #64748b;">• <strong>Assigned Plan:</strong></td>
            <td style="padding: 4px 0; font-weight: 600; color: #16a34a;">{{plan_name}} (Free Trial)</td>
        </tr>
        <tr>
            <td style="padding: 4px 0; color: #64748b;">• <strong>Trial Period &amp; Validity:</strong></td>
            <td style="padding: 4px 0; font-weight: 600;">{{trial_days}} Days (Valid until {{trial_end_date}})</td>
        </tr>
        <tr>
            <td style="padding: 4px 0; color: #64748b;">• <strong>Team Capacity:</strong></td>
            <td style="padding: 4px 0; font-weight: 600;">Up to {{max_users}} User Accounts</td>
        </tr>
        <tr>
            <td style="padding: 4px 0; color: #64748b;">• <strong>Encrypted Cloud Storage:</strong></td>
            <td style="padding: 4px 0; font-weight: 600;">{{storage_limit_mb}} MB</td>
        </tr>
    </table>
    <div style="margin-top: 10px; padding-top: 10px; border-top: 1px dashed #86efac; font-size: 12px; color: #15803d; line-height: 1.5;">
        <strong>How Your Trial Works:</strong> You have 100% unrestricted access to all 8-stage problem-solving tools, SOP management, executive dashboards, and multi-department controls. No billing or credit card is required during your trial. When you upgrade, all your created users, projects, and SOP data will remain fully preserved without any interruption.
    </div>
</div>

<div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px 20px; margin: 20px 0;">
    <div style="font-size: 15px; font-weight: bold; color: #0f172a; margin-bottom: 10px;">
        👥 System User Roles &amp; Assignment Guidance
    </div>
    <p style="font-size: 13px; color: #475569; margin-bottom: 12px; line-height: 1.5;">
        QCMS uses strict Role-Based Access Control (RBAC). When provisioning accounts for your team, assign them to the appropriate role:
    </p>
    <div style="font-size: 13px; line-height: 1.6; color: #334155;">
        <div style="margin-bottom: 8px; padding-left: 10px; border-left: 3px solid #2563eb;">
            <strong>1. Administrator (Admin):</strong> Full workspace control. Manages company profile, user invites, role permission matrix, plant/department setup, and subscription billing.
        </div>
        <div style="margin-bottom: 8px; padding-left: 10px; border-left: 3px solid #d97706;">
            <strong>2. Executive / CEO (CEO):</strong> High-level strategic oversight, corporate ROI and financial savings analytics, and official Stage 8 project review &amp; closure sign-off.
        </div>
        <div style="margin-bottom: 8px; padding-left: 10px; border-left: 3px solid #8b5cf6;">
            <strong>3. Reviewer:</strong> Independent technical auditor for stage transitions (Stages 1–8), reviewing root-cause verification, SOP validation, and either signing off or escalating to CEO.
        </div>
        <div style="margin-bottom: 8px; padding-left: 10px; border-left: 3px solid #06b6d4;">
            <strong>4. Facilitator:</strong> Quality circle coach and mentor. Assists circle teams with 7 QC tools, Fishbone/5-Why methodologies, and validates interim milestones.
        </div>
        <div style="margin-bottom: 8px; padding-left: 10px; border-left: 3px solid #16a34a;">
            <strong>5. Team Leader:</strong> Circle leader responsible for team coordination, meeting schedules, action item assignments, and stage milestone submissions.
        </div>
        <div style="margin-bottom: 4px; padding-left: 10px; border-left: 3px solid #64748b;">
            <strong>6. Team Member:</strong> Active circle participants executing root cause analysis, logging data check sheets, and implementing countermeasures.
        </div>
    </div>
</div>

<div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px 20px; margin: 20px 0;">
    <div style="font-size: 15px; font-weight: bold; color: #0f172a; margin-bottom: 12px;">
        🚀 Administrator Quickstart &amp; Setup Checklist
    </div>
    <ol style="margin: 0; padding-left: 20px; font-size: 13px; color: #334155; line-height: 1.7;">
        <li>
            <strong>Complete Your Corporate Profile:</strong> Go to <em>Admin Settings &gt; Company Information</em> to fill in your GSTIN, PAN, Udyam number, industry sector, plant location, and upload your official company logo &amp; favicon for branded reports.
        </li>
        <li>
            <strong>Set Up Plants &amp; Departments:</strong> Configure your manufacturing facilities, assembly lines, and organizational departments under <em>Admin &gt; Plants &amp; Departments</em>.
        </li>
        <li>
            <strong>Invite &amp; Provision Team Members:</strong> Navigate to <em>User Management &gt; Add User</em> (or use CSV Bulk Upload) to invite your colleagues with their designated role.
        </li>
        <li>
            <strong>Launch Your First 8-Stage Project:</strong> Click <em>New Project</em> to start driving structured continuous improvement initiatives using our built-in 8-Stage methodology.
        </li>
    </ol>
</div>

<div style="background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px; padding: 16px 20px; margin: 20px 0;">
    <div style="font-size: 14px; font-weight: bold; color: #0f172a; margin-bottom: 8px;">
        💳 Subscription Plans &amp; Scalability
    </div>
    <p style="font-size: 12.5px; color: #475569; margin-bottom: 8px; line-height: 1.5;">
        You can upgrade your subscription at any point during or after the trial directly inside your portal with instant UPI / Credit Card / NetBanking / Offline Bank Transfer options:
    </p>
    <ul style="margin: 0; padding-left: 18px; font-size: 12.5px; color: #334155; line-height: 1.6;">
        <li><strong>Starter / MSME Plan:</strong> Ideal for single-plant setups with up to 25 users.</li>
        <li><strong>Growth / Professional Plan:</strong> Multi-department collaboration with up to 100 users and advanced QC analytics.</li>
        <li><strong>Enterprise Plan:</strong> Unlimited scale with multi-plant partitioning, custom branding, API access, and dedicated technical support.</li>
    </ul>
</div>

<p style="font-size: 13px; color: #475569; line-height: 1.5;">
    Our technical customer success team is available 24/7. If you have any questions or require custom setup assistance, please reply to this email or contact us at <strong>{{support_email}}</strong>.
</p>""",
        "cta_text": "Access Administrator Dashboard",
        "cta_url": "{{app_url}}/auth/login.html",
        "trigger_type": "event",
        "event_trigger": "new_org_welcome",
        "target_audience_type": "all",
        "target_roles": ["Admin", "CEO"],
        "is_active": True,
        "is_system_preset": True
    },
    {
        "name": "How to Use QCMS: 8-Stage Quality Workflow Guide",
        "category": "usage_guide",
        "description": "Educational guide on streamlining project quality reviews and stage transitions.",
        "subject": "Mastering the 8-Stage Problem Solving Workflow in QCMS",
        "preheader": "Tips & best practices to accelerate quality improvement projects with your team.",
        "heading": "Software Guide: 8-Stage Quality Methodology",
        "banner_color": "#0284c7",
        "body_html": """<p>Hello <strong>{{user_name}}</strong>,</p>
<p>Did you know that teams utilizing structured stage gate reviews achieve a <strong>40% faster problem resolution time</strong>?</p>
<p>In this guide, discover how to leverage QCMS's built-in 8-Stage workflow:</p>
<ul style="padding-left: 20px; line-height: 1.6;">
    <li><strong>Stages 1–3:</strong> Problem definition, containment actions, and root cause analysis (Ishikawa & 5-Why).</li>
    <li><strong>Stages 4–6:</strong> Corrective action implementation, validation, and horizontal deployment.</li>
    <li><strong>Stages 7–8:</strong> Standard operating procedure updates and team recognition.</li>
</ul>
<p>Access templates and real-world case studies in your Knowledge Base repository.</p>""",
        "cta_text": "Open Knowledge Base & Guides",
        "cta_url": "{{app_url}}/projects/repository.html",
        "trigger_type": "manual",
        "target_audience_type": "all",
        "target_roles": ["All"],
        "is_active": True,
        "is_system_preset": True
    },
    {
        "name": "New Features & Release Notes Announcement",
        "category": "new_feature",
        "description": "Broadcasts new feature releases, UI improvements, and capability updates.",
        "subject": "What's New in QCMS: New Features & Performance Enhancements",
        "preheader": "Check out the latest updates, customizable permissions, and reporting tools.",
        "heading": "New Platform Features & Updates",
        "banner_color": "#8b5cf6",
        "body_html": """<p>Dear <strong>{{user_name}}</strong>,</p>
<p>We are excited to share the latest updates and enhancements now live in your QCMS Enterprise OS workspace!</p>
<div style="background: rgba(139,92,246,0.06); border-left: 4px solid #8b5cf6; padding: 14px 18px; margin: 18px 0; border-radius: 4px;">
    <strong>Highlights of this Release:</strong><br>
    • <strong>Granular Role Access Control:</strong> Fine-tune module permissions per role with one-click matrix switches.<br>
    • <strong>Centralized Document Identity & Branding:</strong> Universal header/footer styling across PDF reports and certificates.<br>
    • <strong>Enhanced Real-Time Audit Logs:</strong> Instant traceability of security and system actions.
</div>
<p>Log in to explore the new capabilities with your team today.</p>""",
        "cta_text": "Explore New Features",
        "cta_url": "{{app_url}}",
        "trigger_type": "manual",
        "target_audience_type": "all",
        "target_roles": ["All"],
        "is_active": True,
        "is_system_preset": True
    },
    {
        "name": "Customer Support & Success Check-in",
        "category": "support",
        "description": "Proactive support check-in offering assistance, training, and direct support links.",
        "subject": "How is your experience with QCMS? We're here to help!",
        "preheader": "Connect with our dedicated support engineers for assistance or custom workflow setup.",
        "heading": "Dedicated Support & Customer Success",
        "banner_color": "#0d9488",
        "body_html": """<p>Hello <strong>{{user_name}}</strong>,</p>
<p>Our goal is to help <strong>{{org_name}}</strong> achieve excellence in quality management and organizational compliance.</p>
<p>If you have any questions regarding system setup, user onboarding, data migration, or advanced reporting, our dedicated technical team is available to assist you.</p>
<p>You can raise a support ticket directly inside your portal or schedule a 1-on-1 walkthrough with our solutions specialist.</p>""",
        "cta_text": "Open Support Helpdesk",
        "cta_url": "{{app_url}}/admin/super-admin.html?view=support",
        "trigger_type": "manual",
        "target_audience_type": "all",
        "target_roles": ["Admin", "CEO"],
        "is_active": True,
        "is_system_preset": True
    },
    {
        "name": "Subscription Payment Approved & Tax Invoice Receipt",
        "category": "payment_confirmation",
        "description": "Sent automatically when an organization's subscription payment is approved or activated, including their official Tax Invoice PDF attachment.",
        "subject": "Payment Confirmed: Official Tax Invoice & Subscription Receipt for {{org_name}}",
        "preheader": "Your subscription payment has been verified and approved. Invoice PDF attached.",
        "heading": "Subscription Payment & Tax Invoice Receipt",
        "banner_color": "#16a34a",
        "body_html": """<p>Dear <strong>{{user_name}}</strong>,</p>
<p>Thank you for your payment! We are pleased to confirm that your subscription payment for <strong>{{org_name}}</strong> has been successfully verified and approved.</p>
<div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 16px; margin: 18px 0;">
    <strong>Payment & Subscription Details:</strong><br>
    • Organization: <strong>{{org_name}}</strong><br>
    • Activated Plan: <strong>{{plan_name}}</strong> ({{billing_cycle}})<br>
    • Amount Paid: <strong>INR {{amount}}</strong><br>
    • Transaction Reference: <strong>{{transaction_id}}</strong><br>
    • Subscription Expiry: <strong>{{expiry_date}}</strong>
</div>
<p>Your official computer-generated <strong>Tax Invoice PDF</strong> has been generated and attached directly to this email for your accounting and finance records.</p>
<p>Your workspace and all associated team features are fully active. Log in to your portal to start exploring.</p>""",
        "cta_text": "Access Your Enterprise Portal",
        "cta_url": "{{app_url}}/admin/settings.html?tab=billing",
        "trigger_type": "event",
        "event_trigger": "payment_approved",
        "trigger_days_before": 0,
        "target_audience_type": "subscription_based",
        "target_roles": ["Admin", "CEO"],
        "is_active": True,
        "is_system_preset": True
    },
    {
        "name": "Offline Payment Verification Declined Notice",
        "category": "payment_rejection",
        "description": "Notifies organization administrators when an offline payment or QR code proof is declined, specifying the rejection reason.",
        "subject": "Payment Verification Update for {{org_name}} – Decision Notice",
        "preheader": "Important update regarding your offline payment submission for {{plan_name}}.",
        "heading": "Payment Proof Verification Declined",
        "banner_color": "#dc2626",
        "body_html": """<p>Dear <strong>{{user_name}}</strong>,</p>
<p>We are writing regarding your recent offline payment proof submission (Transaction Ref: <strong>{{transaction_id}}</strong>) for <strong>{{org_name}}</strong>.</p>
<p>Our finance verification team reviewed the submitted transaction proof, but could not approve it due to the following reason:</p>
<div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; padding: 16px; margin: 18px 0; color: #991b1b;">
    <strong>Reason for Rejection:</strong><br>
    <em>{{rejection_reason}}</em>
</div>
<p>Please review your payment details, upload a clear transaction screenshot with a valid bank UTR reference number, or choose another payment method to complete your subscription setup.</p>""",
        "cta_text": "Resubmit Payment Proof / Retry",
        "cta_url": "{{app_url}}/admin/settings.html?tab=billing",
        "trigger_type": "event",
        "event_trigger": "payment_rejected",
        "trigger_days_before": 0,
        "target_audience_type": "subscription_based",
        "target_roles": ["Admin", "CEO"],
        "is_active": True,
        "is_system_preset": True
    },
    {
        "name": "Project Assignment & Kickoff Notification",
        "category": "project_assignment",
        "description": "Notifies assigned team members, reviewers, facilitators, and team leaders immediately upon project creation, welcoming them to the initiative with problem statement and role details.",
        "subject": "Welcome to Project: {{project_title}} ({{project_code}}) – Assigned as {{assigned_role}}",
        "preheader": "Welcome to project {{project_title}} in {{org_name}}! You have been assigned as {{assigned_role}}.",
        "heading": "Welcome to Quality Circle Project: {{project_title}}",
        "banner_color": "#2563eb",
        "body_html": """<p>Dear <strong>{{user_name}}</strong>,</p>

<p>Welcome to the newly initiated continuous improvement project <strong>{{project_title}}</strong> in <strong>{{org_name}}</strong>! You have been designated as <strong>{{assigned_role}}</strong> for this quality initiative.</p>

<div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 18px 20px; margin: 20px 0;">
    <div style="font-size: 15px; font-weight: bold; color: #166534; margin-bottom: 8px;">
        📋 Project Summary &amp; Role Details
    </div>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px; color: #1e293b;">
        <tr>
            <td style="padding: 4px 0; width: 40%; color: #64748b;">• <strong>Project Code:</strong></td>
            <td style="padding: 4px 0; font-weight: 600;">{{project_code}}</td>
        </tr>
        <tr>
            <td style="padding: 4px 0; color: #64748b;">• <strong>Project Title:</strong></td>
            <td style="padding: 4px 0; font-weight: 600;">{{project_title}}</td>
        </tr>
        <tr>
            <td style="padding: 4px 0; color: #64748b;">• <strong>Category / Domain:</strong></td>
            <td style="padding: 4px 0; font-weight: 600;">{{project_category}}</td>
        </tr>
        <tr>
            <td style="padding: 4px 0; color: #64748b;">• <strong>Project Owner:</strong></td>
            <td style="padding: 4px 0; font-weight: 600;">{{created_by_name}}</td>
        </tr>
        <tr>
            <td style="padding: 4px 0; color: #64748b;">• <strong>Your Assigned Role:</strong></td>
            <td style="padding: 4px 0; font-weight: 700; color: #2563eb;">{{assigned_role}}</td>
        </tr>
        <tr>
            <td style="padding: 4px 0; color: #64748b;">• <strong>Problem Statement:</strong></td>
            <td style="padding: 4px 0;">{{problem_statement}}</td>
        </tr>
    </table>
</div>

<div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 20px; margin: 20px 0;">
    <div style="font-size: 14px; font-weight: bold; color: #0f172a; margin-bottom: 8px;">
        🎯 Next Steps &amp; 8-Stage Quality Workflow
    </div>
    <p style="font-size: 13px; color: #475569; margin-bottom: 8px; line-height: 1.5;">
        Your team is beginning <strong>Stage 1 (Problem Definition &amp; Team Initiation)</strong>. Please log in to your project workspace to review assigned tasks, schedule circle meetings, and record initial observations.
    </p>
</div>

<p style="font-size: 13px; color: #475569; line-height: 1.5;">
    Collaborate with your Team Leader and Facilitator to progress through the DMAIC / 8-Stage methodology.
</p>""",
        "cta_text": "Open Project Workspace",
        "cta_url": "{{app_url}}/auth/login.html?redirect=/projects/project-details.html?id={{project_id}}",
        "trigger_type": "event",
        "event_trigger": "project_assigned",
        "trigger_days_before": 0,
        "target_audience_type": "all",
        "target_roles": ["All"],
        "is_active": True,
        "is_system_preset": True
    },
    {
        "name": "Project Completion, Approval & Improvement Report",
        "category": "project_completion",
        "description": "Sent automatically upon final Stage 8 reviewer closure, congratulating the team and summarizing achievements with a direct link to the approved report.",
        "subject": "Project Successfully Approved & Completed: {{project_title}} ({{project_code}})",
        "preheader": "Project {{project_title}} has achieved final Stage 8 approval and closure.",
        "heading": "Congratulations! Project Officially Completed & Approved",
        "banner_color": "#16a34a",
        "body_html": """<p>Dear <strong>{{user_name}}</strong>,</p>
<p>Congratulations to you and the entire project team! The quality improvement project <strong>{{project_title}}</strong> ({{project_code}}) has successfully received <strong>Final Reviewer Approval &amp; Official Closure</strong> across all 8 stages.</p>
<div style="background: rgba(22,163,74,0.06); border: 1px solid rgba(22,163,74,0.25); border-radius: 6px; padding: 16px; margin: 18px 0;">
    <strong>Executive Summary &amp; Key Improvements:</strong><br>
    • <strong>Project:</strong> {{project_title}} ({{project_code}})<br>
    • <strong>Organization:</strong> {{org_name}}<br>
    • <strong>Problem Addressed:</strong> {{problem_statement}}<br>
    • <strong>Root Causes Resolved:</strong> Ishikawa &amp; 5-Why analysis verified.<br>
    • <strong>Standardization:</strong> SOPs deployed and horizontal rollout established.<br>
    • <strong>Final Status:</strong> Approved &amp; Archived in QCMS Knowledge Repository
</div>
<p>Your team's dedication to continuous quality improvement and rigorous compliance has delivered measurable impact. The complete approved project dossier is available in your Knowledge Repository.</p>""",
        "cta_text": "View Final Approved Project Report",
        "cta_url": "{{app_url}}/auth/login.html?redirect=/projects/repository.html?project_id={{project_id}}",
        "trigger_type": "event",
        "event_trigger": "project_completed",
        "trigger_days_before": 0,
        "target_audience_type": "all",
        "target_roles": ["All"],
        "is_active": True,
        "is_system_preset": True
    }
]


class EmailNotificationEngine:
    @staticmethod
    def get_sender_from_branding(category='general'):
        """Fetch exact Sender Identity & Address Configuration from Document Identity & Branding (Contact Directory)."""
        try:
            branding = DocumentBrandingService.get_branding_context()
        except Exception:
            branding = {}

        cat_lower = (category or 'general').lower()

        if cat_lower in ['subscription_reminder', 'subscription_urgent', 'trial_reminder', 'payment_confirmation', 'payment_rejection', 'billing']:
            email = branding.get('billing_email') or 'billing@ifqm.org.in'
            name = branding.get('billing_sender_name') or 'Invoice and billing'
        elif cat_lower in ['maintenance', 'alerts', 'downtime']:
            email = branding.get('alerts_email') or 'alert@ifqm.org.in'
            name = branding.get('alerts_sender_name') or 'Emergency alert'
        elif cat_lower in ['welcome', 'onboarding']:
            email = branding.get('onboarding_email') or 'on-boarding@ifqm.org.in'
            name = branding.get('onboarding_sender_name') or 'Welcome to IFQM'
        elif cat_lower in ['support']:
            email = branding.get('support_email') or 'support@ifqm.org.in'
            name = branding.get('support_sender_name') or 'Support desk desk'
        elif cat_lower in ['security', 'otp']:
            email = branding.get('otp_email') or 'noreplay12@ifqm.org.in'
            name = branding.get('otp_sender_name') or 'Notification OTP verification'
        else:
            email = branding.get('general_email') or 'info@ifqm.org.in'
            name = branding.get('general_sender_name') or branding.get('software_display_name') or 'info'

        reply_to = branding.get('support_email') or branding.get('general_email') or 'support@ifqm.org.in'
        return {"email": email, "name": name, "reply_to": reply_to}

    @staticmethod
    def seed_default_presets():
        """Ensure all default preset email notification rules exist and are synchronized with Document Identity & Branding."""
        try:
            for p in DEFAULT_NOTIFICATION_PRESETS:
                branding_sender = EmailNotificationEngine.get_sender_from_branding(p.get('category'))
                sender_email = branding_sender['email']
                sender_name = branding_sender['name']
                reply_to = branding_sender['reply_to']

                existing = EmailNotificationRule.query.filter_by(name=p['name']).first()
                if not existing:
                    rule = EmailNotificationRule(
                        name=p['name'],
                        category=p.get('category', 'custom'),
                        description=p.get('description', ''),
                        subject=p['subject'],
                        preheader=p.get('preheader', ''),
                        heading=p.get('heading', ''),
                        body_html=p['body_html'],
                        banner_color=p.get('banner_color', '#2563eb'),
                        cta_text=p.get('cta_text', ''),
                        cta_url=p.get('cta_url', ''),
                        sender_email=sender_email,
                        sender_name=sender_name,
                        reply_to=reply_to,
                        trigger_type=p.get('trigger_type', 'manual'),
                        event_trigger=p.get('event_trigger', ''),
                        trigger_days_before=p.get('trigger_days_before', 7),
                        target_audience_type=p.get('target_audience_type', 'all'),
                        target_roles=p.get('target_roles', []),
                        target_statuses=p.get('target_statuses', []),
                        is_active=p.get('is_active', True),
                        is_system_preset=True
                    )
                    db.session.add(rule)
                elif existing.is_system_preset:
                    # Keep system presets synced with Contact Directory & latest content templates
                    existing.sender_email = sender_email
                    existing.sender_name = sender_name
                    existing.reply_to = reply_to
                    existing.subject = p['subject']
                    existing.preheader = p.get('preheader', '')
                    existing.heading = p.get('heading', '')
                    existing.body_html = p['body_html']
                    existing.banner_color = p.get('banner_color', '#2563eb')
                    existing.cta_text = p.get('cta_text', '')
                    existing.cta_url = p.get('cta_url', '')
                    existing.description = p.get('description', '')
                    existing.event_trigger = p.get('event_trigger', '')
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[EmailNotificationEngine] Error seeding default presets: {e}")

    @staticmethod
    def replace_variables(text, context):
        """Replace all {{variable_name}} tags with real contextual values."""
        if not text:
            return ""
        
        output = str(text)
        for key, val in context.items():
            pattern = re.compile(r'\{\{\s*' + re.escape(key) + r'\s*\}\}', re.IGNORECASE)
            output = pattern.sub(str(val if val is not None else ''), output)
        
        # Clean any unresolved variables gracefully
        output = re.sub(r'\{\{\s*[a-zA-Z0-9_-]+\s*\}\}', '', output)
        return output

    @staticmethod
    def generate_html_email(rule_dict, context=None):
        """
        Build an enterprise, responsive HTML email template.
        """
        if context is None:
            context = {}

        # Default sample context if none provided
        app_url = EmailUtils._get_app_url()
        branding = DocumentBrandingService.get_branding_context()
        software_name = branding.get('software_name') or 'QCMS Enterprise OS'
        support_email = branding.get('support_email') or 'support@ifqm.org.in'

        merged_context = {
            'org_name': context.get('org_name', 'Acme Quality Manufacturing Ltd.'),
            'user_name': context.get('user_name', 'John Doe'),
            'user_email': context.get('user_email', 'admin@acme.com'),
            'role_name': context.get('role_name', 'Company Admin'),
            'assigned_role': context.get('assigned_role', 'Team Member'),
            'project_title': context.get('project_title', 'Assembly Line Productivity Improvement'),
            'project_code': context.get('project_code', 'PRJ-8821'),
            'project_category': context.get('project_category', 'Quality'),
            'problem_statement': context.get('problem_statement', 'Reduce monthly assembly defects from 3.5% to < 1.0% through structured 8-stage problem solving.'),
            'created_by_name': context.get('created_by_name', 'Quality Operations Lead'),
            'project_id': str(context.get('project_id', '1')),
            'plan_name': context.get('plan_name', 'Small MSME\'s Plan'),
            'expiry_date': context.get('expiry_date', (datetime.utcnow() + timedelta(days=7)).strftime('%d %b %Y')),
            'days_left': str(context.get('days_left', '7')),
            'trial_days': str(context.get('trial_days', '14')),
            'trial_end_date': context.get('trial_end_date', (datetime.utcnow() + timedelta(days=14)).strftime('%d %b %Y')),
            'max_users': str(context.get('max_users', '50')),
            'storage_limit_mb': str(context.get('storage_limit_mb', '5120')),
            'industry': context.get('industry', 'Manufacturing & Quality Operations'),
            'org_scale': context.get('org_scale', 'Small MSME'),
            'subscription_status': context.get('subscription_status', 'Trialing'),
            'app_url': app_url,
            'software_name': software_name,
            'support_email': support_email
        }
        for k, v in context.items():
            merged_context[k] = v

        subject = EmailNotificationEngine.replace_variables(rule_dict.get('subject', 'Notification'), merged_context)
        preheader = EmailNotificationEngine.replace_variables(rule_dict.get('preheader', ''), merged_context)
        heading = EmailNotificationEngine.replace_variables(rule_dict.get('heading', subject), merged_context)
        body_html = EmailNotificationEngine.replace_variables(rule_dict.get('body_html', ''), merged_context)
        cta_text = EmailNotificationEngine.replace_variables(rule_dict.get('cta_text', ''), merged_context)
        cta_url = EmailNotificationEngine.replace_variables(rule_dict.get('cta_url', ''), merged_context)
        banner_color = rule_dict.get('banner_color', '#2563eb')
        category_label = (rule_dict.get('category') or 'NOTIFICATION').replace('_', ' ').upper()

        cta_button_html = ""
        if cta_text and cta_url:
            cta_button_html = f"""
            <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="margin: 28px 0;">
                <tr>
                    <td align="center">
                        <a href="{cta_url}" target="_blank" style="display: inline-block; background-color: {banner_color}; color: #ffffff; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 14px; font-weight: 700; line-height: 48px; text-align: center; text-decoration: none; padding: 0 28px; border-radius: 6px; -webkit-text-size-adjust: none; box-shadow: 0 3px 10px rgba(0,0,0,0.12);">
                            {cta_text} &rarr;
                        </a>
                    </td>
                </tr>
            </table>
            """

        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
    <style>
        body {{ margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; }}
        table {{ border-collapse: separate; }}
        a {{ color: {banner_color}; text-decoration: underline; }}
        p {{ margin: 0 0 16px; color: #334155; font-size: 15px; line-height: 1.65; }}
        @media only screen and (max-width: 620px) {{
            .main-container {{ width: 100% !important; padding: 12px !important; }}
            .content-box {{ padding: 20px 16px !important; }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; background-color: #f1f5f9;">
    <!-- Preheader Hidden Text -->
    <div style="display: none; max-height: 0px; overflow: hidden;">
        {preheader}
        &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
    </div>

    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f1f5f9; padding: 30px 10px;">
        <tr>
            <td align="center">
                <!-- Main Container -->
                <table role="presentation" class="main-container" border="0" cellpadding="0" cellspacing="0" width="600" style="max-width: 600px; width: 100%; margin: 0 auto;">
                    
                    <!-- Header with Logo & Tag -->
                    <tr>
                        <td style="padding: 0 0 20px; text-align: center;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td align="center">
                                        <div style="font-size: 20px; font-weight: 800; color: #0f172a; letter-spacing: -0.5px;">
                                            {software_name}
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Card Box -->
                    <tr>
                        <td>
                            <table role="presentation" class="content-box" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #ffffff; border-radius: 10px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.04);">
                                
                                <!-- Top Accent Banner Stripe -->
                                <tr>
                                    <td style="height: 6px; background-color: {banner_color}; font-size: 0; line-height: 0;">&nbsp;</td>
                                </tr>

                                <tr>
                                    <td style="padding: 32px 32px 28px;">
                                        <!-- Category Tag -->
                                        <div style="display: inline-block; background-color: rgba(37,99,235,0.08); color: {banner_color}; font-size: 11px; font-weight: 700; letter-spacing: 0.8px; padding: 4px 10px; border-radius: 4px; margin-bottom: 14px; text-transform: uppercase;">
                                            {category_label}
                                        </div>

                                        <!-- Main Heading -->
                                        <h1 style="margin: 0 0 20px; color: #0f172a; font-size: 22px; font-weight: 700; line-height: 1.35; letter-spacing: -0.3px;">
                                            {heading}
                                        </h1>

                                        <!-- Email Content Body -->
                                        <div style="color: #334155; font-size: 15px; line-height: 1.65;">
                                            {body_html}
                                        </div>

                                        <!-- Action Button -->
                                        {cta_button_html}

                                        <!-- Signoff / Support Note -->
                                        <div style="border-top: 1px solid #f1f5f9; padding-top: 20px; margin-top: 28px; color: #64748b; font-size: 13px; line-height: 1.5;">
                                            Need assistance? Contact our team at <a href="mailto:{support_email}" style="color: {banner_color}; font-weight: 600; text-decoration: none;">{support_email}</a>.
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 16px; text-align: center; color: #94a3b8; font-size: 12px; line-height: 1.6;">
                            <p style="margin: 0 0 6px; color: #94a3b8; font-size: 12px;">
                                Sent by <strong>{rule_dict.get('sender_name', 'QCMS Enterprise Notifications')}</strong>
                            </p>
                            <p style="margin: 0; color: #cbd5e1; font-size: 11px;">
                                &copy; {datetime.utcnow().year} {software_name}. All rights reserved.<br>
                                Automated Quality & Compliance Management System.
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
        return full_html

    @staticmethod
    def resolve_recipients(rule):
        """
        Query all users that match the rule's audience criteria.
        Returns a list of dicts: [{'user': user, 'org': org, 'context': context_dict}]
        """
        target_type = rule.target_audience_type or 'all'
        target_org_ids = rule.target_org_ids or []
        target_roles = rule.target_roles or []
        target_statuses = rule.target_statuses or []
        target_plans = rule.target_plans or []

        users_query = User.query.filter(User.is_active == True, User.status != 'Inactive')

        # Organization Filter
        if target_type == 'specific_orgs' and target_org_ids:
            users_query = users_query.filter(User.org_id.in_(target_org_ids))
        
        # Role Filter
        if target_roles and "All" not in target_roles:
            target_roles_lower = [str(r).strip().lower() for r in target_roles]
            role_conditions = []
            for r in target_roles_lower:
                if r in ['admin', 'company admin']:
                    role_conditions.append(User.role.has(func.lower(Role.name).in_(['admin', 'company admin', 'superadmin'])))
                elif r in ['ceo', 'executive']:
                    role_conditions.append(User.role.has(func.lower(Role.name).in_(['ceo', 'executive'])))
                elif r == 'reviewer':
                    role_conditions.append(User.role.has(func.lower(Role.name) == 'reviewer'))
                elif r == 'facilitator':
                    role_conditions.append(User.role.has(func.lower(Role.name) == 'facilitator'))
                elif r in ['team member', 'member']:
                    role_conditions.append(User.role.has(func.lower(Role.name).in_(['team member', 'team leader', 'member'])))
                else:
                    role_conditions.append(User.role.has(func.lower(Role.name) == r))
            if role_conditions:
                users_query = users_query.filter(or_(*role_conditions))

        users = users_query.all()
        recipients = []
        app_url = EmailUtils._get_app_url()

        def norm_status(s):
            val = (s or '').strip().lower()
            if 'trial' in val: return 'trial'
            if 'active' in val: return 'active'
            if 'expir' in val: return 'expiring'
            if 'suspend' in val or 'cancel' in val or 'deactiv' in val: return 'suspended'
            return val

        norm_target_statuses = [norm_status(s) for s in target_statuses] if target_statuses else []

        for u in users:
            org = u.organization
            if not org or org.is_deleted:
                continue

            # Subscription Status Filter (robust against 'Trial' vs 'Trialing', etc.)
            org_status = getattr(org, 'subscription_status', 'Active') or 'Active'
            if norm_target_statuses and norm_status(org_status) not in norm_target_statuses:
                continue

            # Subscription Plan Filter
            org_plan = getattr(org, 'subscription_plan', '') or ''
            if target_plans and org_plan not in target_plans:
                continue

            # Calculate expiry date & days left
            expiry_date_str = "Ongoing"
            days_left = 30
            if getattr(org, 'subscription_end_date', None):
                exp = org.subscription_end_date
                expiry_date_str = exp.strftime('%d %b %Y')
                delta = (exp.date() - datetime.utcnow().date()).days
                days_left = max(0, delta)
            elif getattr(org, 'trial_ends_at', None):
                exp = org.trial_ends_at
                expiry_date_str = exp.strftime('%d %b %Y')
                delta = (exp.date() - datetime.utcnow().date()).days
                days_left = max(0, delta)

            ctx = {
                'org_name': org.name,
                'user_name': u.username or u.email.split('@')[0],
                'user_email': u.email,
                'role_name': u.role.name if u.role else 'User',
                'plan_name': org_plan or 'Standard Enterprise',
                'expiry_date': expiry_date_str,
                'days_left': str(days_left),
                'app_url': app_url
            }

            recipients.append({
                'user_id': u.id,
                'email': u.email,
                'name': u.username or u.email.split('@')[0],
                'org_id': org.id,
                'org_name': org.name,
                'context': ctx
            })

        return recipients

    @staticmethod
    def send_rule_notification(rule_id, test_email=None, current_user_id=None, include_current_admin=False, admin_email=None):
        """
        Execute sending an email notification rule.
        If test_email is provided, sends a single test email with sample data.
        Otherwise, resolves target recipients and sends to all matched users.
        """
        rule = db.session.get(EmailNotificationRule, rule_id)
        if not rule:
            return {"status": "error", "message": "Notification rule not found"}

        rule_dict = rule.to_dict()

        if test_email:
            # Send test email
            sample_ctx = {
                'org_name': 'Sample Enterprise Corp',
                'user_name': 'Test Administrator',
                'user_email': test_email,
                'role_name': 'Company Admin',
                'plan_name': 'Enterprise Cloud Edition',
                'expiry_date': (datetime.utcnow() + timedelta(days=rule.trigger_days_before or 7)).strftime('%d %b %Y'),
                'days_left': str(rule.trigger_days_before or 7),
                'app_url': EmailUtils._get_app_url()
            }
            html_content = EmailNotificationEngine.generate_html_email(rule_dict, sample_ctx)
            subject = EmailNotificationEngine.replace_variables(rule.subject, sample_ctx)
            
            branding_sender = EmailNotificationEngine.get_sender_from_branding(rule.category)
            sender_addr = rule.sender_email if (rule.sender_email and not rule.sender_email.endswith('@qcms.com')) else branding_sender['email']
            sender_name = rule.sender_name if (rule.sender_name and not rule.sender_name.startswith('QCMS ')) else branding_sender['name']
            reply_to_addr = rule.reply_to if (rule.reply_to and not rule.reply_to.endswith('@qcms.com')) else branding_sender['reply_to']

            sent_res = EmailUtils.send_email(
                to_email=test_email,
                subject=subject,
                html_content=html_content,
                sender_email=sender_addr,
                sender_name=sender_name,
                reply_to=reply_to_addr
            )

            if sent_res:
                return {"status": "success", "message": f"Test email successfully dispatched to {test_email}"}
            else:
                return {"status": "error", "message": f"Failed to send test email to {test_email}. Please verify SMTP/Email integration settings in Integration Hub."}

        # Real Broadcast / Execution
        recipients = EmailNotificationEngine.resolve_recipients(rule)

        if include_current_admin and admin_email:
            existing_emails = {r['email'].lower() for r in recipients}
            if admin_email.lower() not in existing_emails:
                admin_user = User.query.filter_by(email=admin_email).first()
                admin_name = admin_user.username if admin_user else admin_email.split('@')[0]
                recipients.append({
                    'user_id': admin_user.id if admin_user else None,
                    'email': admin_email,
                    'name': f"{admin_name} (SuperAdmin Copy)",
                    'org_id': None,
                    'org_name': 'QCMS Platform Administration',
                    'context': {
                        'org_name': 'QCMS Platform Administration',
                        'user_name': admin_name,
                        'user_email': admin_email,
                        'role_name': 'SuperAdmin',
                        'plan_name': 'SuperAdmin Console',
                        'expiry_date': 'Ongoing',
                        'days_left': '30',
                        'app_url': EmailUtils._get_app_url()
                    }
                })

        if not recipients:
            return {"status": "warning", "message": "No matching active users found for the selected audience criteria."}

        success_count = 0
        failed_count = 0
        delivery_summary = []

        branding_sender = EmailNotificationEngine.get_sender_from_branding(rule.category)
        sender_addr = rule.sender_email if (rule.sender_email and not rule.sender_email.endswith('@qcms.com')) else branding_sender['email']
        sender_name = rule.sender_name if (rule.sender_name and not rule.sender_name.startswith('QCMS ')) else branding_sender['name']
        reply_to_addr = rule.reply_to if (rule.reply_to and not rule.reply_to.endswith('@qcms.com')) else branding_sender['reply_to']

        for r in recipients:
            html_content = EmailNotificationEngine.generate_html_email(rule_dict, r['context'])
            personalized_subject = EmailNotificationEngine.replace_variables(rule.subject, r['context'])

            sent_res = EmailUtils.send_email(
                to_email=r['email'],
                subject=personalized_subject,
                html_content=html_content,
                sender_email=sender_addr,
                sender_name=sender_name,
                reply_to=reply_to_addr
            )

            if sent_res:
                success_count += 1
                delivery_summary.append({
                    "email": r['email'],
                    "name": r['name'],
                    "role": r.get('context', {}).get('role_name', 'User'),
                    "org": r.get('org_name', 'System'),
                    "status": "Delivered"
                })
            else:
                failed_count += 1
                delivery_summary.append({
                    "email": r['email'],
                    "name": r['name'],
                    "role": r.get('context', {}).get('role_name', 'User'),
                    "org": r.get('org_name', 'System'),
                    "status": "Failed"
                })

        # Update Rule statistics
        rule.total_sent = (rule.total_sent or 0) + success_count
        rule.last_triggered_at = datetime.utcnow()

        # Create Log Entry
        overall_status = "Delivered" if failed_count == 0 else ("Partially Delivered" if success_count > 0 else "Failed")
        log_entry = EmailNotificationLog(
            rule_id=rule.id,
            rule_name=rule.name,
            category=rule.category,
            subject=rule.subject,
            sender_email=sender_addr,
            sender_name=sender_name,
            recipient_count=success_count + failed_count,
            recipients_summary=delivery_summary[:200],
            status=overall_status,
            error_message=f"{failed_count} deliveries failed" if failed_count > 0 else None,
            sent_by_id=current_user_id,
            sent_at=datetime.utcnow()
        )
        db.session.add(log_entry)
        db.session.commit()

        return {
            "status": "success" if success_count > 0 else "error",
            "message": f"Email notification sent to {success_count} recipient(s). {failed_count} failed.",
            "total_recipients": len(recipients),
            "delivered": success_count,
            "failed": failed_count
        }

    @staticmethod
    def run_automated_expiry_checks():
        """
        Background automated task to evaluate subscription & trial expiry rules.
        """
        active_rules = EmailNotificationRule.query.filter_by(is_active=True, trigger_type='event').all()
        results = []
        for r in active_rules:
            if r.event_trigger in ['subscription_expiring_soon', 'trial_expiring_soon', 'subscription_expired']:
                res = EmailNotificationEngine.send_rule_notification(r.id)
                results.append({"rule": r.name, "result": res})
        return results

    @staticmethod
    def dispatch_payment_success_invoice_email(org_id, user_id=None, plan_name='Enterprise', billing_cycle='Monthly', amount=0.0, transaction_id='TXN-001', payment_date=None):
        """Generates Tax Invoice PDF and emails payment approval receipt to Organization Admin."""
        try:
            org = db.session.get(Organization, org_id) if isinstance(org_id, int) else org_id
            if not org: return False

            user = None
            if user_id:
                user = db.session.get(User, user_id)
            if not user:
                admin_role = Role.query.filter(Role.name.ilike('%Admin%')).first()
                user = User.query.filter_by(org_id=org.id).filter(User.role_id == admin_role.id if admin_role else True).first()
            if not user:
                user = User.query.filter_by(org_id=org.id).first()
            if not user or not user.email:
                return False

            branding = DocumentBrandingService.get_branding_context(org.id)
            tx = str(transaction_id or 'TXN-001')
            amt = float(amount or 0.0)
            pdate = payment_date or datetime.utcnow()
            exp_date_str = (datetime.utcnow() + timedelta(days=365 if str(billing_cycle) in ('Yearly', 'Annual') else 30)).strftime('%d %b %Y')

            # Generate Invoice PDF bytes
            from app.utils.invoice_pdf_generator import generate_invoice_pdf_bytes
            pdf_bytes = generate_invoice_pdf_bytes(
                org_name=org.name,
                admin_name=user.username or 'Organization Admin',
                admin_email=user.email,
                plan_name=plan_name,
                billing_cycle=billing_cycle,
                amount=amt,
                transaction_id=tx,
                payment_date=pdate,
                branding_context=branding
            )

            # STRICT GATE: look up the rule for payment_approved regardless of active state.
            # If rule doesn't exist or toggle is OFF, immediately return False — no email sent.
            rule = EmailNotificationRule.query.filter_by(event_trigger='payment_approved').first()
            if not rule or not rule.is_active:
                return False  # Toggle is OFF — do NOT send any email
            sample_ctx = {
                'org_name': org.name,
                'user_name': user.username or 'Organization Admin',
                'user_email': user.email,
                'plan_name': plan_name,
                'billing_cycle': billing_cycle,
                'amount': f"{amt:,.2f}",
                'transaction_id': tx,
                'expiry_date': exp_date_str,
                'app_url': EmailUtils._get_app_url()
            }

            rule_dict = rule.to_dict()
            html_content = EmailNotificationEngine.generate_html_email(rule_dict, sample_ctx)
            subject = EmailNotificationEngine.replace_variables(rule.subject, sample_ctx)
            sender_addr = rule.sender_email
            sender_name = rule.sender_name
            reply_to = rule.reply_to

            filename = f"Official_Invoice_{tx[-8:] if len(tx)>8 else tx}.pdf"
            attachments = [{
                "filename": filename,
                "name": filename,
                "content": pdf_bytes,
                "mime_type": "application/pdf"
            }]

            sent = EmailUtils.send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content,
                email_type='billing',
                org_id=org.id,
                sender_email=sender_addr,
                sender_name=sender_name,
                reply_to=reply_to,
                attachments=attachments
            )
            return bool(sent)
        except Exception as e:
            if current_app: current_app.logger.error(f"Error dispatching payment invoice email: {e}")
            return False

    @staticmethod
    def dispatch_payment_rejection_email(org_id, user_id=None, plan_name='Enterprise', transaction_id='TXN-001', rejection_reason='Payment details could not be verified.'):
        """Emails payment proof rejection notice with specified reason to Organization Admin."""
        try:
            org = db.session.get(Organization, org_id) if isinstance(org_id, int) else org_id
            if not org: return False

            user = None
            if user_id:
                user = db.session.get(User, user_id)
            if not user:
                admin_role = Role.query.filter(Role.name.ilike('%Admin%')).first()
                user = User.query.filter_by(org_id=org.id).filter(User.role_id == admin_role.id if admin_role else True).first()
            if not user:
                user = User.query.filter_by(org_id=org.id).first()
            if not user or not user.email:
                return False

            tx = str(transaction_id or 'TXN-001')
            reason_str = str(rejection_reason or 'Payment details could not be verified.')

            # STRICT GATE: look up the rule regardless of active state.
            # If rule doesn't exist or toggle is OFF, immediately return False — no email sent.
            rule = EmailNotificationRule.query.filter_by(event_trigger='payment_rejected').first()
            if not rule or not rule.is_active:
                return False  # Toggle is OFF — do NOT send any email
            sample_ctx = {
                'org_name': org.name,
                'user_name': user.username or 'Organization Admin',
                'user_email': user.email,
                'plan_name': plan_name,
                'transaction_id': tx,
                'rejection_reason': reason_str,
                'app_url': EmailUtils._get_app_url()
            }

            rule_dict = rule.to_dict()
            html_content = EmailNotificationEngine.generate_html_email(rule_dict, sample_ctx)
            subject = EmailNotificationEngine.replace_variables(rule.subject, sample_ctx)
            sender_addr = rule.sender_email
            sender_name = rule.sender_name
            reply_to = rule.reply_to

            sent = EmailUtils.send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content,
                email_type='billing',
                org_id=org.id,
                sender_email=sender_addr,
                sender_name=sender_name,
                reply_to=reply_to
            )
            return bool(sent)
        except Exception as e:
            if current_app: current_app.logger.error(f"Error dispatching payment rejection email: {e}")
            return False

    @staticmethod
    def trigger_project_assigned_notification(project_id):
        """
        Dispatches Project Assignment & Kickoff Notification to all assigned team members,
        reviewers, facilitators, and team leaders for a newly initialized project.
        """
        try:
            from app.infrastructure.database.models.models import Project, ProjectMember
            project = db.session.get(Project, project_id) if isinstance(project_id, int) else project_id
            if not project:
                return False

            org = db.session.get(Organization, project.org_id) if project.org_id else None
            creator = db.session.get(User, project.creator_id) if project.creator_id else None
            creator_name = creator.full_name or creator.username if creator else 'Project Owner'

            # Gather all participant user IDs and their specific assigned role
            participants_map = {}  # user_id -> role_name

            if project.team_leader_id:
                participants_map[project.team_leader_id] = "Team Leader"
            if project.facilitator_id:
                participants_map[project.facilitator_id] = "Facilitator"
            if project.reviewer_id:
                participants_map[project.reviewer_id] = "Reviewer"

            members = ProjectMember.query.filter_by(project_id=project.id).all()
            for m in members:
                if m.user_id not in participants_map:
                    u_rec = db.session.get(User, m.user_id)
                    participants_map[m.user_id] = u_rec.role.name if (u_rec and u_rec.role) else "Team Member"

            if not participants_map:
                return False

            # STRICT GATE: look up the rule regardless of active state first.
            # If the rule doesn't exist OR the toggle is OFF, immediately exit — no email sent.
            rule = EmailNotificationRule.query.filter_by(
                category='project_assignment'
            ).first()

            if not rule or not rule.is_active:
                return False  # Toggle is OFF — do NOT send any email

            rule_dict = rule.to_dict()

            branding_sender = EmailNotificationEngine.get_sender_from_branding('project_assignment')
            sender_addr = rule.sender_email or branding_sender['email']
            sender_name = rule.sender_name or 'QCMS Project Workflow'
            reply_to_addr = rule.reply_to or branding_sender['reply_to']

            success_count = 0
            delivery_summary = []

            for uid, assigned_role in participants_map.items():
                target_user = db.session.get(User, uid)
                if not target_user or not target_user.email:
                    continue

                user_name = target_user.full_name or target_user.username or target_user.email.split('@')[0]
                
                context = {
                    'user_name': user_name,
                    'user_email': target_user.email,
                    'assigned_role': assigned_role,
                    'project_id': str(project.id),
                    'project_title': project.title or 'Quality Improvement Project',
                    'project_code': project.project_uid or f'PRJ-{project.id}',
                    'project_category': project.category or 'Quality',
                    'problem_statement': project.description or '8-Stage Quality Problem Solving Project',
                    'created_by_name': creator_name,
                    'org_name': org.name if org else 'QCMS Organization',
                    'app_url': EmailUtils._get_app_url()
                }

                html_content = EmailNotificationEngine.generate_html_email(rule_dict, context)
                personalized_subject = EmailNotificationEngine.replace_variables(rule.subject, context)

                sent = EmailUtils.send_email(
                    to_email=target_user.email,
                    subject=personalized_subject,
                    html_content=html_content,
                    email_type='general',
                    org_id=project.org_id,
                    sender_email=sender_addr,
                    sender_name=sender_name,
                    reply_to=reply_to_addr
                )

                if sent:
                    success_count += 1
                    delivery_summary.append({
                        "email": target_user.email,
                        "name": user_name,
                        "role": assigned_role,
                        "org": org.name if org else "Platform",
                        "status": "Delivered"
                    })

            # Create Audit Log Entry
            if success_count > 0 and rule:
                rule.total_sent = (rule.total_sent or 0) + success_count
                rule.last_triggered_at = datetime.utcnow()
                log_entry = EmailNotificationLog(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    category=rule.category,
                    subject=f"Assigned to Project: {project.title} ({project.project_uid})",
                    sender_email=sender_addr,
                    sender_name=sender_name,
                    recipient_count=success_count,
                    recipients_summary=delivery_summary,
                    status="Delivered",
                    sent_by_id=project.creator_id,
                    sent_at=datetime.utcnow()
                )
                db.session.add(log_entry)
                db.session.commit()

            return success_count > 0
        except Exception as e:
            if current_app: current_app.logger.error(f"Error dispatching project assigned email: {e}")
            return False

    @staticmethod
    def trigger_project_completed_notification(project_id):
        """
        Dispatches Project Completion & Congratulatory Report Email to all project members,
        facilitator, reviewer, and organization administrators upon Stage 8 closure.
        """
        try:
            from app.infrastructure.database.models.models import Project, ProjectMember
            project = db.session.get(Project, project_id) if isinstance(project_id, int) else project_id
            if not project:
                return False

            org = db.session.get(Organization, project.org_id) if project.org_id else None

            # Collect all recipient user IDs
            recipient_ids = set()
            if project.creator_id: recipient_ids.add(project.creator_id)
            if project.team_leader_id: recipient_ids.add(project.team_leader_id)
            if project.facilitator_id: recipient_ids.add(project.facilitator_id)
            if project.reviewer_id: recipient_ids.add(project.reviewer_id)

            members = ProjectMember.query.filter_by(project_id=project.id).all()
            for m in members:
                recipient_ids.add(m.user_id)

            # Also include Org Admins
            admin_role = Role.query.filter(Role.name.ilike('%Admin%')).first()
            if admin_role and project.org_id:
                admins = User.query.filter_by(org_id=project.org_id, role_id=admin_role.id).all()
                for a in admins:
                    recipient_ids.add(a.id)

            if not recipient_ids:
                return False

            # STRICT GATE: look up the rule regardless of active state first.
            # If the rule doesn't exist OR the toggle is OFF, immediately exit — no email sent.
            rule = EmailNotificationRule.query.filter_by(
                category='project_completion'
            ).first()

            if not rule or not rule.is_active:
                return False  # Toggle is OFF — do NOT send any email

            rule_dict = rule.to_dict()

            branding_sender = EmailNotificationEngine.get_sender_from_branding('project_completion')
            sender_addr = rule.sender_email or branding_sender['email']
            sender_name = rule.sender_name or 'QCMS Quality Assurance'
            reply_to_addr = rule.reply_to or branding_sender['reply_to']

            success_count = 0
            delivery_summary = []

            for uid in recipient_ids:
                target_user = db.session.get(User, uid)
                if not target_user or not target_user.email:
                    continue

                user_name = target_user.full_name or target_user.username or target_user.email.split('@')[0]
                user_role = target_user.role.name if target_user.role else "User"

                context = {
                    'user_name': user_name,
                    'user_email': target_user.email,
                    'project_id': str(project.id),
                    'project_title': project.title or 'Quality Improvement Project',
                    'project_code': project.project_uid or f'PRJ-{project.id}',
                    'project_category': project.category or 'Quality',
                    'problem_statement': project.description or '8-Stage Quality Problem Solving Project',
                    'org_name': org.name if org else 'QCMS Organization',
                    'app_url': EmailUtils._get_app_url()
                }

                html_content = EmailNotificationEngine.generate_html_email(rule_dict, context)
                personalized_subject = EmailNotificationEngine.replace_variables(rule.subject, context)

                sent = EmailUtils.send_email(
                    to_email=target_user.email,
                    subject=personalized_subject,
                    html_content=html_content,
                    email_type='general',
                    org_id=project.org_id,
                    sender_email=sender_addr,
                    sender_name=sender_name,
                    reply_to=reply_to_addr
                )

                if sent:
                    success_count += 1
                    delivery_summary.append({
                        "email": target_user.email,
                        "name": user_name,
                        "role": user_role,
                        "org": org.name if org else "Platform",
                        "status": "Delivered"
                    })

            # Create Audit Log Entry
            if success_count > 0 and rule:
                rule.total_sent = (rule.total_sent or 0) + success_count
                rule.last_triggered_at = datetime.utcnow()
                log_entry = EmailNotificationLog(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    category=rule.category,
                    subject=f"Project Approved & Completed: {project.title} ({project.project_uid})",
                    sender_email=sender_addr,
                    sender_name=sender_name,
                    recipient_count=success_count,
                    recipients_summary=delivery_summary,
                    status="Delivered",
                    sent_by_id=project.creator_id,
                    sent_at=datetime.utcnow()
                )
                db.session.add(log_entry)
                db.session.commit()

            return success_count > 0
        except Exception as e:
            if current_app: current_app.logger.error(f"Error dispatching project completed email: {e}")
            return False

    @staticmethod
    def trigger_new_org_welcome_notification(org_id, admin_user_id=None):
        """
        Dispatches the Comprehensive Welcome & Onboarding Guide Email to the Organization Administrator
        immediately upon registration or workspace provisioning.
        """
        try:
            from app.infrastructure.database.models.models import Organization, User, Role, SaaSPlan
            org = db.session.get(Organization, org_id) if isinstance(org_id, int) else org_id
            if not org:
                return False

            admin_user = None
            if admin_user_id:
                admin_user = db.session.get(User, admin_user_id)
            if not admin_user:
                admin_role = Role.query.filter_by(name='Admin').first()
                if admin_role:
                    admin_user = User.query.filter_by(org_id=org.id, role_id=admin_role.id).first()
            if not admin_user and org.email:
                admin_user = User.query.filter_by(org_id=org.id, email=org.email).first()

            if not admin_user or not admin_user.email:
                return False

            # STRICT GATE: look up the rule regardless of active state first.
            # If the rule doesn't exist OR the toggle is OFF, immediately exit — no email sent.
            rule = EmailNotificationRule.query.filter(
                or_(
                    EmailNotificationRule.category == 'welcome',
                    EmailNotificationRule.event_trigger == 'new_org_welcome'
                )
            ).first()

            if not rule or not rule.is_active:
                return False  # Toggle is OFF — do NOT send any email

            rule_dict = rule.to_dict()

            branding_sender = EmailNotificationEngine.get_sender_from_branding('welcome')
            sender_addr = (rule.sender_email if rule and rule.sender_email else None) or branding_sender['email']
            sender_name = (rule.sender_name if rule and rule.sender_name else None) or 'QCMS Onboarding Team'
            reply_to_addr = (rule.reply_to if rule and rule.reply_to else None) or branding_sender['reply_to']

            trial_end_str = org.trial_ends_at.strftime('%d %b %Y') if org.trial_ends_at else '14 Days from Registration'
            trial_days = '14'
            if org.trial_ends_at:
                delta = (org.trial_ends_at - datetime.utcnow()).days
                trial_days = str(max(1, delta))

            user_name = admin_user.full_name or admin_user.username or admin_user.email.split('@')[0]
            plan_name = org.subscription_plan or 'Standard Enterprise'

            context = {
                'user_name': user_name,
                'user_email': admin_user.email,
                'org_name': org.name or 'Your Organization',
                'plan_name': plan_name,
                'subscription_status': org.subscription_status or 'Trialing',
                'trial_days': trial_days,
                'trial_end_date': trial_end_str,
                'max_users': str(org.max_users or 50),
                'storage_limit_mb': f"{org.storage_limit_mb or 5120:.0f}",
                'industry': org.industry or 'Manufacturing & Quality Operations',
                'org_scale': org.org_scale or 'Small',
                'app_url': EmailUtils._get_app_url(),
                'support_email': branding_sender.get('reply_to', 'support@ifqm.org.in')
            }

            html_content = EmailNotificationEngine.generate_html_email(rule_dict, context)
            final_subject = EmailNotificationEngine.replace_variables(rule_dict.get('subject', 'Welcome to QCMS Enterprise OS'), context)

            sent = EmailUtils.send_email(
                to_email=admin_user.email,
                subject=final_subject,
                html_content=html_content,
                email_type='general',
                org_id=org.id,
                sender_email=sender_addr,
                sender_name=sender_name,
                reply_to=reply_to_addr
            )

            # Log dispatch in EmailNotificationLog
            try:
                log_entry = EmailNotificationLog(
                    rule_id=rule.id if rule else None,
                    rule_name=rule.name if rule else "Welcome & Onboarding to QCMS Enterprise OS",
                    category="welcome",
                    subject=final_subject,
                    sender_email=sender_addr,
                    sender_name=sender_name,
                    recipient_count=1 if sent else 0,
                    recipients_summary=[{
                        "email": admin_user.email,
                        "name": user_name,
                        "role": "Admin",
                        "org": org.name,
                        "status": "Delivered" if sent else "Failed"
                    }],
                    status="Delivered" if sent else "Failed",
                    error_message=None if sent else "SMTP transmission failed",
                    sent_by_id=admin_user.id,
                    sent_at=datetime.utcnow()
                )
                if rule and sent:
                    rule.total_sent = (rule.total_sent or 0) + 1
                    rule.last_triggered_at = datetime.utcnow()
                db.session.add(log_entry)
                db.session.commit()
            except Exception as log_err:
                db.session.rollback()
                print(f"[EmailNotificationEngine] Welcome email log error: {log_err}")

            return bool(sent)
        except Exception as e:
            if current_app: current_app.logger.error(f"Error dispatching welcome onboarding email: {e}")
            return False


