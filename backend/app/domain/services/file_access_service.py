# QCMS Enterprise 5-Factor File Access Authorization Service
import os
import re
import logging
from typing import Tuple, Optional, Dict, Any

from app import db
from app.infrastructure.database.models.models import (
    User, Organization, Project, ProjectMember, SOP, SOPVersion,
    SubscriptionInvoice, BillingInvoice, OfflinePaymentProof,
    SupportTicket, SupportAttachment, AuditExportLog
)
from app.domain.services.tenant_context import is_super_admin, has_permission

logger = logging.getLogger('QCMS.FileAuth')

PUBLIC_ASSET_PREFIXES = (
    'branding/',
    'template_previews/',
    'system/',
    'avatars/',
    'avatar_',
    'banner_',
)

PUBLIC_ASSET_EXTENSIONS = (
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp'
)


def is_public_asset_path(clean_path: str) -> bool:
    path_lower = clean_path.lower()
    for prefix in PUBLIC_ASSET_PREFIXES:
        if path_lower.startswith(prefix):
            return True
    if 'logo' in path_lower or 'favicon' in path_lower:
        return True
    if path_lower.startswith('public/') or path_lower.startswith('assets/'):
        return True
    return False


def sanitize_file_path(file_path: str) -> Optional[str]:
    if not file_path:
        return None
    normalized = os.path.normpath(file_path).replace('\\', '/')
    if '..' in normalized or normalized.startswith('/') or '\x00' in normalized:
        return None
    return normalized.lstrip('./')


def verify_file_access_authorization(
    user: Optional[User],
    file_path: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None
) -> Tuple[bool, str, int]:
    clean_path = sanitize_file_path(file_path)
    if not clean_path:
        return False, 'INVALID_FILE_PATH: Directory traversal or malformed path detected.', 400

    if is_public_asset_path(clean_path):
        return True, 'AUTHORIZED_PUBLIC_ASSET', 200

    # 1. User Identity & Active Status Verification
    if not user:
        return False, 'AUTHENTICATION_REQUIRED: User identity could not be verified.', 401

    if not getattr(user, 'is_active', True) or getattr(user, 'status', '') == 'Inactive':
        return False, 'USER_DEACTIVATED: User account is inactive or disabled.', 403

    if getattr(user, 'is_deleted', False):
        return False, 'USER_DELETED: User account has been removed.', 403

    if is_super_admin(user):
        return True, 'AUTHORIZED_SUPER_ADMIN', 200

    # 2. Organization Context & Tenant Isolation
    if not user.org_id:
        return False, 'MISSING_ORGANIZATION: User does not belong to any active organization.', 403

    org = db.session.get(Organization, user.org_id)
    if not org:
        return False, 'ORGANIZATION_NOT_FOUND: User organization does not exist.', 403

    if getattr(org, 'is_deleted', False):
        return False, 'ORGANIZATION_DELETED: Access denied for deleted tenant.', 403

    if getattr(org, 'subscription_status', '') == 'Suspended':
        return False, 'ORGANIZATION_SUSPENDED: Tenant subscription is currently suspended.', 403

    org_match = re.search(r'org_(\d+)', clean_path)
    if org_match:
        file_org_id = int(org_match.group(1))
        if file_org_id != user.org_id:
            logger.warning(f'[CrossTenantSecurityAlert] User #{user.id} (Org {user.org_id}) attempted to access file owned by Org {file_org_id}: {clean_path}')
            return False, 'CROSS_TENANT_FORBIDDEN: You do not have permission to access another organization files.', 403

    # 3, 4, 5. Resource Context, RBAC Permission & Ownership
    role_name = user.role.name if user.role else 'Team Member'
    path_lower = clean_path.lower()

    # Project Deliverables
    if 'project' in path_lower or 'stage' in path_lower or resource_type in ('project', 'stage', 'qc_tool'):
        proj_id = resource_id
        if not proj_id:
            proj_match = re.search(r'proj(?:ect)?_(\d+)', clean_path, re.IGNORECASE)
            if proj_match:
                proj_id = int(proj_match.group(1))

        if proj_id:
            project = Project.query.filter_by(id=proj_id, org_id=user.org_id).first()
            if not project:
                return False, 'PROJECT_NOT_FOUND: Project does not exist in your organization.', 404

            if role_name in ('Admin', 'CEO'):
                return True, 'AUTHORIZED_ORG_EXECUTIVE', 200

            is_assigned = (
                getattr(project, 'creator_id', None) == user.id or
                getattr(project, 'team_leader_id', None) == user.id or
                getattr(project, 'facilitator_id', None) == user.id or
                getattr(project, 'reviewer_id', None) == user.id
            )

            if not is_assigned:
                member_exists = ProjectMember.query.filter_by(project_id=project.id, user_id=user.id).first()
                if member_exists:
                    is_assigned = True

            if not is_assigned:
                if not has_permission(user, 'project.view') and not has_permission(user, 'projects.view'):
                    return False, 'PROJECT_MEMBERSHIP_REQUIRED: You are not assigned to this project.', 403

            return True, 'AUTHORIZED_PROJECT_RESOURCE', 200
        else:
            if not has_permission(user, 'project.view') and not has_permission(user, 'projects.view'):
                return False, 'INSUFFICIENT_PROJECT_PERMISSIONS', 403
            return True, 'AUTHORIZED_ORG_PROJECT_FILE', 200

    # SOP Documents
    if 'sop' in path_lower or resource_type == 'sop':
        sop_id = resource_id
        if not sop_id:
            sop_match = re.search(r'sop_(\d+)', clean_path, re.IGNORECASE)
            if sop_match:
                sop_id = int(sop_match.group(1))

        if sop_id:
            sop = SOP.query.filter_by(id=sop_id, org_id=user.org_id).first()
            if not sop:
                return False, 'SOP_NOT_FOUND: SOP not found in your organization.', 404

            if sop.department_id and user.department_id:
                if sop.department_id != user.department_id and role_name not in ('Admin', 'CEO', 'Reviewer', 'Facilitator'):
                    return False, 'DEPARTMENT_RESTRICTED_SOP: This SOP is restricted to another department.', 403

        return True, 'AUTHORIZED_SOP_RESOURCE', 200

    # Billing & Invoices
    if 'invoice' in path_lower or 'billing' in path_lower or 'payment' in path_lower or resource_type in ('invoice', 'billing', 'payment_proof'):
        if role_name not in ('Admin', 'SuperAdmin'):
            return False, 'BILLING_ACCESS_RESTRICTED: Only organization administrators can access financial documents.', 403

        proof_match = re.search(r'proof_(\d+)', clean_path, re.IGNORECASE)
        if proof_match:
            proof_id = int(proof_match.group(1))
            proof = OfflinePaymentProof.query.filter_by(id=proof_id, org_id=user.org_id).first()
            if not proof:
                return False, 'PAYMENT_PROOF_NOT_FOUND: Payment proof record not found.', 404

        return True, 'AUTHORIZED_BILLING_RESOURCE', 200

    # Support Tickets
    if 'support' in path_lower or 'ticket' in path_lower or resource_type == 'support':
        ticket_id = resource_id
        if not ticket_id:
            ticket_match = re.search(r'ticket_(\d+)', clean_path, re.IGNORECASE)
            if ticket_match:
                ticket_id = int(ticket_match.group(1))

        if ticket_id:
            ticket = SupportTicket.query.filter_by(id=ticket_id).first()
            if not ticket:
                return False, 'SUPPORT_TICKET_NOT_FOUND: Support ticket not found.', 404

            if ticket.org_id != user.org_id and not is_super_admin(user):
                return False, 'CROSS_TENANT_FORBIDDEN: Ticket belongs to another organization.', 403

            if role_name != 'Admin' and ticket.user_id != user.id:
                return False, 'TICKET_OWNERSHIP_REQUIRED: You can only access attachments on tickets you submitted.', 403

        return True, 'AUTHORIZED_SUPPORT_RESOURCE', 200

    # Compliance Audit Logs
    if 'audit' in path_lower or 'export' in path_lower or resource_type == 'audit':
        if role_name not in ('Admin', 'SuperAdmin', 'CEO'):
            return False, 'AUDIT_ACCESS_RESTRICTED: Audit exports require administrator privileges.', 403
        return True, 'AUTHORIZED_AUDIT_RESOURCE', 200

    # User Private Profile Files
    user_match = re.search(r'user_(\d+)', clean_path, re.IGNORECASE)
    if user_match:
        file_user_id = int(user_match.group(1))
        if file_user_id != user.id and role_name not in ('Admin', 'SuperAdmin'):
            return False, 'USER_FILE_OWNERSHIP_REQUIRED: You do not own this private file.', 403
        return True, 'AUTHORIZED_USER_PRIVATE_FILE', 200

    return True, 'AUTHORIZED_TENANT_FILE', 200
