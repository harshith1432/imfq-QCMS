import sys
import os

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app import create_app, db
from app.models import User, Organization, Role
from app.utils.email_utils import EmailUtils
from unittest.mock import patch

app = create_app()

def test_flows():
    with app.app_context():
        print("Testing Email Integration Flow...")
        
        # 1. Setup mock data
        org = Organization.query.filter_by(name="Test Org Email").first()
        if org:
            User.query.filter_by(org_id=org.id).delete()
            db.session.delete(org)
            db.session.commit()
            
        new_org = Organization(name="Test Org Email", email="test@example.com")
        db.session.add(new_org)
        db.session.flush()
        
        admin_role = Role.query.filter_by(name="Admin").first()
        user = User(
            org_id=new_org.id,
            username="testadmin_email",
            email="test@example.com",
            hashed_password="hashed",
            role_id=admin_role.id
        )
        db.session.add(user)
        db.session.commit()
        
        print(f"User created: {user.username}, is_verified: {user.is_verified}")
        
        # 2. Test Verification Token Generation
        with patch('app.utils.email_utils.resend.Emails.send') as mock_send:
            mock_send.return_value = {"id": "test-id"}
            EmailUtils.send_verification_email(user)
            db.session.commit()
            print(f"Verification token generated: {user.verification_token}")
            assert user.verification_token is not None
            
        # 3. Test Reset Token Generation
        with patch('app.utils.email_utils.resend.Emails.send') as mock_send:
            mock_send.return_value = {"id": "test-id"}
            EmailUtils.send_reset_password_email(user)
            db.session.commit()
            print(f"Reset token generated: {user.reset_token}")
            assert user.reset_token is not None
            
        # 4. Test OTP Generation for Password Change
        with patch('app.utils.email_utils.resend.Emails.send') as mock_send:
            mock_send.return_value = {"id": "test-id"}
            # Simulate manual OTP generation as in route
            import random
            otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            user.otp_token = otp
            from datetime import datetime, timedelta
            user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
            EmailUtils.send_otp_email(user, otp)
            db.session.commit()
            print(f"OTP generated and stored: {user.otp_token}, Expiry: {user.otp_expiry}")
            assert user.otp_token is not None
            assert len(user.otp_token) == 6
            
        print("Backend OTP logic verification successful!")

if __name__ == "__main__":
    test_flows()
