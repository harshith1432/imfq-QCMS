from datetime import datetime
from datetime import timezone, timezone
import json
import os
from sqlalchemy.dialects.postgresql import ARRAY
from app import db, bcrypt
from .base import SafeVector, Vector, is_local, _utc_now

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    users = db.relationship('User', backref='role', lazy=True)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True, index=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plants.id'), nullable=True, index=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(255))
    employee_id = db.Column(db.String(100), index=True)
    phone = db.Column(db.String(50), nullable=True, index=True)
    email = db.Column(db.String(255), unique=True, nullable=True, index=True)
    hashed_password = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_temp_password = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255), unique=True, nullable=True)
    reset_token = db.Column(db.String(255), unique=True, nullable=True)
    otp_token = db.Column(db.String(10), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='Active', index=True) # Active, Inactive
    profile_picture = db.Column(db.String(255), nullable=True)
    banner_image = db.Column(db.String(255), nullable=True)
    language = db.Column(db.String(10), default='en')
    created_at = db.Column(db.DateTime, default=_utc_now, index=True)
    last_login = db.Column(db.DateTime, index=True)
    deactivated_at = db.Column(db.DateTime)
    custom_fields = db.Column(db.JSON, nullable=True)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    def set_password(self, password):
        self.password = password

    def check_password(self, password):
        return bcrypt.check_password_hash(self.hashed_password, password)

    @property
    def org(self):
        return self.organization

class EmailVerification(db.Model):
    __tablename__ = 'email_verifications'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    otp = db.Column(db.String(10), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=_utc_now)


class PhoneVerification(db.Model):
    __tablename__ = 'phone_verifications'
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(50), unique=True, nullable=False)
    otp = db.Column(db.String(10), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=_utc_now)



class SaaSUserSession(db.Model):
    __tablename__ = 'saas_user_sessions'
    __table_args__ = (
        db.Index('idx_session_token_status', 'session_id', 'status'),
        db.Index('idx_session_user_status', 'user_id', 'status'),
        db.Index('idx_session_org_status', 'org_id', 'status'),
    )
    session_id = db.Column(db.String(100), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    login_time = db.Column(db.DateTime, default=_utc_now)
    last_activity = db.Column(db.DateTime, default=_utc_now, onupdate=_utc_now, nullable=True)
    logout_time = db.Column(db.DateTime)
    session_duration = db.Column(db.Integer)  # in seconds
    device = db.Column(db.String(50))
    browser = db.Column(db.String(50))
    os = db.Column(db.String(50))
    ip_address = db.Column(db.String(45))
    location = db.Column(db.String(100))
    status = db.Column(db.String(20), default='Active')  # Active, LoggedOut, Terminated, Expired

    user = db.relationship('User', backref=db.backref('sessions', cascade='all, delete-orphan'))
    organization = db.relationship('Organization', backref='sessions')


class UserCustomField(db.Model):
    __tablename__ = 'user_custom_fields'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    field_key = db.Column(db.String(100), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    is_required = db.Column(db.Boolean, default=False)
    is_system = db.Column(db.Boolean, default=False)
    data_type = db.Column(db.String(50), default='both')
    created_at = db.Column(db.DateTime, default=_utc_now)


# ============================
# MODULE: SaaS Plans Management
# ============================

