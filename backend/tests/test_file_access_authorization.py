import os
import pytest
from app import create_app, db
from app.infrastructure.database.models.models import (
    User, Organization, Role, Project, ProjectMember, SupportTicket, OfflinePaymentProof
)
from app.domain.services.file_access_service import verify_file_access_authorization, sanitize_file_path

def test_sanitize_file_path():
    assert sanitize_file_path('../../etc/passwd') is None
    assert sanitize_file_path('org_1/../../secret.txt') is None
    assert sanitize_file_path('/absolute/path.txt') is None
    assert sanitize_file_path('projects/org_55/proj_1/report.pdf') == 'projects/org_55/proj_1/report.pdf'
    assert sanitize_file_path('branding\\logo.png') == 'branding/logo.png'

def test_public_asset_authorization(app):
    with app.app_context():
        is_auth, reason, status = verify_file_access_authorization(
            user=None,
            file_path='branding/logo.png'
        )
        assert is_auth is True
        assert status == 200
        assert 'PUBLIC_ASSET' in reason

def test_unauthenticated_private_file_access(app):
    with app.app_context():
        is_auth, reason, status = verify_file_access_authorization(
            user=None,
            file_path='projects/org_55/proj_1/deliverable.pdf'
        )
        assert is_auth is False
        assert status == 401
        assert 'AUTHENTICATION_REQUIRED' in reason

def test_cross_tenant_file_access_blocked(app):
    with app.app_context():
        admin_user = User.query.filter_by(email='gelala@fxzig.com').first()
        assert admin_user is not None
        assert admin_user.org_id == 55

        # Attempt to access Org 99 file
        is_auth, reason, status = verify_file_access_authorization(
            user=admin_user,
            file_path='projects/org_99/proj_10/confidential.pdf'
        )
        assert is_auth is False
        assert status == 403
        assert 'CROSS_TENANT_FORBIDDEN' in reason

def test_billing_invoice_permission_restricted_to_admin(app):
    with app.app_context():
        admin_user = User.query.filter_by(email='gelala@fxzig.com').first()
        team_user = User.query.filter_by(email='nitin.murthy9@example.com').first()
        assert admin_user is not None
        assert team_user is not None

        # Admin accessing Org 55 invoice
        is_auth, reason, status = verify_file_access_authorization(
            user=admin_user,
            file_path='invoices/org_55/inv_202608.pdf'
        )
        assert is_auth is True
        assert status == 200

        # Team member attempting to access Org 55 invoice
        is_auth_tm, reason_tm, status_tm = verify_file_access_authorization(
            user=team_user,
            file_path='invoices/org_55/inv_202608.pdf'
        )
        assert is_auth_tm is False
        assert status_tm == 403
        assert 'BILLING_ACCESS_RESTRICTED' in reason_tm

def test_support_ticket_ownership_authorization(app):
    with app.app_context():
        admin_user = User.query.filter_by(email='gelala@fxzig.com').first()
        team_user = User.query.filter_by(email='nitin.murthy9@example.com').first()
        other_user = User.query.filter_by(email='kavya.raghavan174@example.com').first()

        ticket = SupportTicket.query.filter_by(org_id=55, user_id=team_user.id).first()
        if not ticket:
            ticket = SupportTicket(
                org_id=55,
                user_id=team_user.id,
                ticket_number='TICK-TEST-99',
                subject='Test Storage Issue',
                message='Testing storage access',
                priority='Low',
                status='Open'
            )
            db.session.add(ticket)
            db.session.commit()

        file_path = f'support/org_55/ticket_{ticket.id}/screenshot.png'

        # Ticket author can access
        is_auth, _, status = verify_file_access_authorization(user=team_user, file_path=file_path)
        assert is_auth is True
        assert status == 200

        # Admin can access
        is_auth_admin, _, status_admin = verify_file_access_authorization(user=admin_user, file_path=file_path)
        assert is_auth_admin is True
        assert status_admin == 200

        # Other regular team member cannot access
        is_auth_other, reason_other, status_other = verify_file_access_authorization(user=other_user, file_path=file_path)
        assert is_auth_other is False
        assert status_other == 403
        assert 'TICKET_OWNERSHIP_REQUIRED' in reason_other

@pytest.mark.skip(reason="[DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE] signed-url endpoint was removed from storage routes.")
def test_signed_url_endpoint(client, app):
    with app.app_context():
        import uuid
        from flask_jwt_extended import create_access_token
        admin_user = User.query.filter_by(email='gelala@fxzig.com').first()
        team_user = User.query.filter_by(email='nitin.murthy9@example.com').first()
        
        admin_token = create_access_token(identity=str(admin_user.id), additional_claims={'session_id': str(uuid.uuid4())})
        team_token = create_access_token(identity=str(team_user.id), additional_claims={'session_id': str(uuid.uuid4())})

        # Admin requests invoice signed url
        res = client.post('/api/storage/signed-url', json={'file_path': 'invoices/org_55/inv_01.pdf'}, headers={'Authorization': f'Bearer {admin_token}'})
        # If file not in storage, returns 404, but auth passed (not 403)
        assert res.status_code in (200, 404)

        # Team user requests billing invoice signed url -> 403 Forbidden
        res_tm = client.post('/api/storage/signed-url', json={'file_path': 'invoices/org_55/inv_01.pdf'}, headers={'Authorization': f'Bearer {team_token}'})
        assert res_tm.status_code == 403
        assert 'BILLING_ACCESS_RESTRICTED' in res_tm.get_json()['message']

        # Cross-tenant request -> 403 Forbidden
        res_xt = client.post('/api/storage/signed-url', json={'file_path': 'projects/org_999/proj_1/specs.pdf'}, headers={'Authorization': f'Bearer {admin_token}'})
        assert res_xt.status_code == 403
        assert 'CROSS_TENANT_FORBIDDEN' in res_xt.get_json()['message']
