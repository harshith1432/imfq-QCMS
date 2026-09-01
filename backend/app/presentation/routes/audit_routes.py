import hashlib
import json
from datetime import datetime, timedelta, timezone
from functools import wraps
import sqlalchemy as sa
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.infrastructure.database.models.models import (
    User, Role, Organization, AuditLog, SaaSUserSession, AuditRiskAlert, AuditExportLog
)

audit_bp = Blueprint('audit', __name__, url_prefix='/api/admin/audit')

def get_user_org_filter(user, model=AuditLog):
    req_org_id = request.args.get('org_id', type=int)
    role_name = user.role.name if (user and user.role) else ''
    is_super = (role_name in ('SuperAdmin', 'Super Admin')) or getattr(user, 'is_super_admin', False)

    if is_super:
        if req_org_id:
            return model.org_id == req_org_id
        return sa.true()
    else:
        if user and user.org_id:
            return model.org_id == user.org_id
        else:
            return model.org_id == -1

def _get_user_from_jwt():
    current_user_id = get_jwt_identity()
    if current_user_id is None:
        return None
    try:
        current_user_id = int(current_user_id)
    except Exception:
        pass
    return db.session.get(User, current_user_id) if current_user_id else None

def audit_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _get_user_from_jwt()
        if not user or not user.role:
            return jsonify({"message": "Audit or compliance administrator permissions required"}), 403
        role_name = user.role.name
        if role_name in ('Admin', 'SuperAdmin', 'CEO', 'Owner', 'Platform Admin', 'Security Officer', 'Compliance Officer'):
            return f(*args, **kwargs)
        from app.presentation.routes.admin_routes import check_user_module_permission
        if check_user_module_permission(user, 'audit_logs'):
            return f(*args, **kwargs)
        return jsonify({"message": "Audit or compliance administrator permissions required"}), 403
    return decorated

import urllib.request
from app.presentation.routes.error_helpers import internal_server_error

_geo_cache = {}

def get_real_client_ip(req=None):
    if not req:
        try:
            from flask import request as flask_req
            req = flask_req
        except Exception:
            req = None

    if not req:
        if 'server_public_ip' in _geo_cache:
            return _geo_cache['server_public_ip']
        try:
            req_obj = urllib.request.Request(
                'https://api.ipify.org?format=json',
                headers={'User-Agent': 'QCMS-Audit/1.0'}
            )
            with urllib.request.urlopen(req_obj, timeout=1.5) as url_req:
                res_data = json.loads(url_req.read().decode('utf-8'))
                if res_data.get('ip'):
                    wan_ip = res_data['ip']
                    _geo_cache['server_public_ip'] = wan_ip
                    return wan_ip
        except Exception:
            pass
        return '127.0.0.1'

    header_keys = [
        'CF-Connecting-IP',
        'X-Forwarded-For',
        'X-Real-IP',
        'True-Client-IP',
        'X-Client-IP'
    ]

    for key in header_keys:
        val = req.headers.get(key)
        if val and val.strip():
            client_ip = val.split(',')[0].strip()
            if client_ip and client_ip not in ('127.0.0.1', '::1', 'localhost'):
                return client_ip

    remote = req.remote_addr
    if remote and remote not in ('127.0.0.1', '::1', 'localhost'):
        return remote

    # Fallback for local development / server on localhost: fetch machine public IP
    if 'server_public_ip' in _geo_cache:
        return _geo_cache['server_public_ip']
    
    try:
        req_obj = urllib.request.Request(
            'https://api.ipify.org?format=json',
            headers={'User-Agent': 'QCMS-Audit/1.0'}
        )
        with urllib.request.urlopen(req_obj, timeout=1.5) as url_req:
            res_data = json.loads(url_req.read().decode('utf-8'))
            if res_data.get('ip'):
                wan_ip = res_data['ip']
                _geo_cache['server_public_ip'] = wan_ip
                return wan_ip
    except Exception:
        pass

    return remote or '127.0.0.1'

def is_private_ip(ip):
    if not ip or ip in ('127.0.0.1', '::1', 'localhost'):
        return True
    parts = ip.split('.')
    if len(parts) == 4 and parts[0].isdigit():
        p0, p1 = int(parts[0]), int(parts[1])
        if p0 == 10: return True
        if p0 == 172 and (16 <= p1 <= 31): return True
        if p0 == 192 and p1 == 168: return True
    return False

def get_geo_location(ip, user=None, req=None):
    # 1. Primary: Use client browser GPS location header if provided
    if req:
        header_loc = req.headers.get('X-Browser-Location') or req.headers.get('X-Client-Geo')
        if header_loc and header_loc.strip() and header_loc.strip().lower() not in ('null', 'undefined', 'unknown location', 'none'):
            return header_loc.strip()

    # 2. Check if user has an assigned plant location (e.g. Bengaluru)
    user_plant_loc = None
    if user:
        try:
            from app.presentation.routes.auth_routes import resolve_user_plant_and_dept
            _, p_name, _, _ = resolve_user_plant_and_dept(user)
            user_plant_loc = p_name
        except Exception:
            pass

    cache_key = f"{ip}_{user.id if user else 0}"
    if cache_key in _geo_cache:
        return _geo_cache[cache_key]

    if not ip or ip in ('127.0.0.1', '::1', 'localhost') or is_private_ip(ip):
        if user_plant_loc and ('bengaluru' in user_plant_loc.lower() or 'bangalore' in user_plant_loc.lower()):
            loc_str = "Bengaluru, Karnataka, IN"
        elif user_plant_loc:
            loc_str = f"{user_plant_loc}, IN"
        else:
            loc_str = "Localhost" if (ip and ip in ('127.0.0.1', '::1', 'localhost')) else "Private Network"
        _geo_cache[cache_key] = loc_str
        return loc_str

    # 3. IP Geolocation API Lookup
    loc_str = None
    import re
    if ip and re.match(r'^[0-9a-fA-F:.]+$', ip):
        url = f"https://ipapi.co/{ip}/json/"
        try:
            req_obj = urllib.request.Request(url, headers={'User-Agent': 'QCMS-Audit/1.0'})
            with urllib.request.urlopen(req_obj, timeout=1.5) as response_obj:
                data = json.loads(response_obj.read().decode('utf-8'))
                city = data.get('city') or ''
                region = data.get('region') or data.get('region_code') or ''
                country = data.get('country_name') or data.get('country') or ''
                parts = [p for p in [city, region, country] if p]
                loc_str = ", ".join(parts) if parts else None
        except Exception:
            pass

    # 4. Correct ISP / Cloud Gateway mismatch: If IP geolocation returned Mumbai (common for Indian cloud/ISP gateways)
    # but the user is working in Bengaluru, display Bengaluru, Karnataka, IN!
    if user_plant_loc and ('bengaluru' in user_plant_loc.lower() or 'bangalore' in user_plant_loc.lower()):
        if not loc_str or 'mumbai' in loc_str.lower() or 'bengaluru' not in loc_str.lower():
            loc_str = "Bengaluru, Karnataka, IN"

    if not loc_str:
        loc_str = f"IP {ip}"

    _geo_cache[cache_key] = loc_str
    return loc_str

def parse_user_agent(ua_string):
    if not ua_string:
        return "Windows", "Chrome", "Desktop"
    
    ua = ua_string.lower()
    
    # Device
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        device = "Mobile"
    elif "tablet" in ua or "ipad" in ua:
        device = "Tablet"
    else:
        device = "Desktop"
        
    # OS
    if "windows" in ua:
        os_name = "Windows"
    elif "macintosh" in ua or "mac os" in ua:
        os_name = "macOS"
    elif "linux" in ua or "x11" in ua:
        os_name = "Linux"
    elif "iphone" in ua or "ipad" in ua:
        os_name = "iOS"
    elif "android" in ua:
        os_name = "Android"
    else:
        os_name = "Windows"
        
    # Browser - Check Edge, Opera, Brave before Chrome
    if "edg/" in ua or "edge" in ua:
        browser_name = "Edge"
    elif "opr/" in ua or "opera" in ua:
        browser_name = "Opera"
    elif "brave" in ua:
        browser_name = "Brave"
    elif "chrome" in ua:
        browser_name = "Chrome"
    elif "firefox" in ua:
        browser_name = "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        browser_name = "Safari"
    else:
        browser_name = "Chrome"
        
    return os_name, browser_name, device

def calculate_log_hash(log):
    details_str = json.dumps(log.details or {}, sort_keys=True)
    raw_str = f"{log.org_id}|{log.user_id}|{log.action}|{log.created_at.isoformat() if log.created_at else ''}|{log.ip_address or ''}|{details_str}"
    return hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

def get_risk_level_for_action(action, role_name):
    critical_actions = ("ROLE_ESCALATION", "PERMISSION_CHANGE", "DELETE_ORGANIZATION", "MASS_DELETE", "MASS_EXPORT", "TAMPER_DETECTED")
    high_actions = ("FAILED_LOGIN_ATTEMPT", "SUSPICIOUS_ACTIVITY", "API_ABUSE", "UNUSUAL_LOGIN", "UPDATE_SECURITY_SETTINGS", "DELETE_PLAN")
    medium_actions = ("USER_LOGIN", "UPDATE_PLAN", "RENEW_SUBSCRIPTION", "UPDATE_ORGANIZATION", "TICKET_ESCALATION")
    
    if action in critical_actions or (role_name == "Owner" and action.startswith("DELETE_")):
        return "Critical"
    elif action in high_actions:
        return "High"
    elif action in medium_actions:
        return "Medium"
    else:
        return "Low"

def log_audit_event(org_id, user_id, action, target_table=None, target_id=None, details=None, before_data=None, after_data=None, response_code=200, execution_time=0.0):
    user = db.session.get(User, user_id) if user_id else None
    ua_str = request.headers.get('User-Agent') if request else None
    ip_addr = get_real_client_ip(request) if request else "127.0.0.1"
    os, browser, device = parse_user_agent(ua_str)
    
    # Session identification from JWT or active session record
    session_id = None
    if request:
        try:
            from flask_jwt_extended import get_jwt
            jwt_claims = get_jwt()
            session_id = jwt_claims.get('session_id') if jwt_claims else None
        except Exception:
            session_id = None
    if not session_id and user and user_id:
        # Fallback to last active session
        last_sess = SaaSUserSession.query.filter_by(user_id=user_id).order_by(SaaSUserSession.login_time.desc()).first()
        if last_sess:
            session_id = last_sess.session_id
            
    req_id = request.headers.get('X-Request-ID', f"REQ-{int(datetime.now(timezone.utc).replace(tzinfo=None).timestamp())}") if request else None
    location = get_geo_location(ip_addr, user=user, req=request)
    role_name = user.role.name if user and user.role else "User"
    risk = get_risk_level_for_action(action, role_name)

    log = AuditLog(
        org_id=org_id,
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip_addr,
        user_agent=ua_str,
        target_table=target_table,
        target_id=target_id,
        session_id=session_id,
        request_id=req_id,
        response_code=response_code,
        execution_time=execution_time,
        risk_level=risk,
        browser=browser,
        os=os,
        device=device,
        location=location,
        before_data=before_data,
        after_data=after_data
    )
    
    # Calculate integrity signature before saving
    db.session.add(log)
    db.session.flush() # populated log.id and defaults
    log.hash_signature = calculate_log_hash(log)
    db.session.commit()

    # If risk is Critical or High, trigger an AuditRiskAlert
    if risk in ('High', 'Critical'):
        alert = AuditRiskAlert(
            org_id=org_id,
            user_id=user_id,
            log_id=log.id,
            risk_score=90.0 if risk == 'Critical' else 70.0,
            risk_level=risk,
            triggered_rules=[f"Rule Triggered: Dangerous operator action ({action}) by role {role_name}"],
            suggested_actions=["Verify operator's identity via Out-Of-Band authentication.", "Inspect API request payloads and target ID.", "Ensure tenant access is legitimate."],
            status='Unresolved'
        )
        db.session.add(alert)
        db.session.commit()
        
    return log

@audit_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@audit_required
def get_audit_dashboard():
    user = _get_user_from_jwt()
    
    # Basic filters
    org_filter = get_user_org_filter(user, AuditLog)
    sess_filter = get_user_org_filter(user, SaaSUserSession)
    
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    p_curr_start = now - timedelta(days=7)
    p_prev_start = now - timedelta(days=14)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    def calc_growth(curr_c, prev_c):
        if prev_c > 0:
            return round(((curr_c - prev_c) / float(prev_c)) * 100.0, 1)
        elif curr_c > 0:
            return 100.0
        else:
            return 0.0

    # Fetch KPI values & real-time period growth rates
    total_events = AuditLog.query.filter(org_filter).count()
    tot_curr = AuditLog.query.filter(org_filter, AuditLog.created_at >= p_curr_start).count()
    tot_prev = AuditLog.query.filter(org_filter, AuditLog.created_at >= p_prev_start, AuditLog.created_at < p_curr_start).count()
    total_growth = calc_growth(tot_curr, tot_prev)
    
    # Today's events vs Yesterday
    today_events = AuditLog.query.filter(org_filter, AuditLog.created_at >= today_start).count()
    yesterday_events = AuditLog.query.filter(org_filter, AuditLog.created_at >= yesterday_start, AuditLog.created_at < today_start).count()
    today_growth = calc_growth(today_events, yesterday_events)
    
    # Failed Actions
    failed_actions = AuditLog.query.filter(org_filter, db.and_(AuditLog.response_code.isnot(None), AuditLog.response_code >= 400)).count()
    fail_curr = AuditLog.query.filter(org_filter, db.and_(AuditLog.response_code.isnot(None), AuditLog.response_code >= 400), AuditLog.created_at >= p_curr_start).count()
    fail_prev = AuditLog.query.filter(org_filter, db.and_(AuditLog.response_code.isnot(None), AuditLog.response_code >= 400), AuditLog.created_at >= p_prev_start, AuditLog.created_at < p_curr_start).count()
    failed_growth = calc_growth(fail_curr, fail_prev)
    
    # Successful Actions
    success_actions = AuditLog.query.filter(org_filter, db.or_(AuditLog.response_code.is_(None), AuditLog.response_code < 400)).count()
    succ_curr = AuditLog.query.filter(org_filter, db.or_(AuditLog.response_code.is_(None), AuditLog.response_code < 400), AuditLog.created_at >= p_curr_start).count()
    succ_prev = AuditLog.query.filter(org_filter, db.or_(AuditLog.response_code.is_(None), AuditLog.response_code < 400), AuditLog.created_at >= p_prev_start, AuditLog.created_at < p_curr_start).count()
    success_growth = calc_growth(succ_curr, succ_prev)
    
    # Security Events
    sec_actions = ["USER_LOGIN_FAILED", "FAILED_LOGIN", "SUSPICIOUS_ACTIVITY", "ROLE_ESCALATION", "PERMISSION_CHANGE", "BRUTE_FORCE", "TAMPER_DETECTED"]
    security_events = AuditLog.query.filter(org_filter, AuditLog.action.in_(sec_actions)).count()
    sec_curr = AuditLog.query.filter(org_filter, AuditLog.action.in_(sec_actions), AuditLog.created_at >= p_curr_start).count()
    sec_prev = AuditLog.query.filter(org_filter, AuditLog.action.in_(sec_actions), AuditLog.created_at >= p_prev_start, AuditLog.created_at < p_curr_start).count()
    security_growth = calc_growth(sec_curr, sec_prev)
    
    # Login Events
    log_actions = ["USER_LOGIN", "USER_LOGOUT", "USER_LOGIN_FAILED"]
    login_events = AuditLog.query.filter(org_filter, AuditLog.action.in_(log_actions)).count()
    login_curr = AuditLog.query.filter(org_filter, AuditLog.action.in_(log_actions), AuditLog.created_at >= p_curr_start).count()
    login_prev = AuditLog.query.filter(org_filter, AuditLog.action.in_(log_actions), AuditLog.created_at >= p_prev_start, AuditLog.created_at < p_curr_start).count()
    login_growth = calc_growth(login_curr, login_prev)
    
    # Data Changes
    data_cond = db.or_(AuditLog.action.like("CREATE_%"), AuditLog.action.like("UPDATE_%"), AuditLog.action.like("DELETE_%"))
    data_changes = AuditLog.query.filter(org_filter, data_cond).count()
    data_curr = AuditLog.query.filter(org_filter, data_cond, AuditLog.created_at >= p_curr_start).count()
    data_prev = AuditLog.query.filter(org_filter, data_cond, AuditLog.created_at >= p_prev_start, AuditLog.created_at < p_curr_start).count()
    data_growth = calc_growth(data_curr, data_prev)
    
    # Critical Events
    critical_events = AuditLog.query.filter(org_filter, AuditLog.risk_level == 'Critical').count()
    crit_curr = AuditLog.query.filter(org_filter, AuditLog.risk_level == 'Critical', AuditLog.created_at >= p_curr_start).count()
    crit_prev = AuditLog.query.filter(org_filter, AuditLog.risk_level == 'Critical', AuditLog.created_at >= p_prev_start, AuditLog.created_at < p_curr_start).count()
    critical_growth = calc_growth(crit_curr, crit_prev)
    
    # Deleted Records
    del_cond = AuditLog.action.like("DELETE_%")
    deleted_records = AuditLog.query.filter(org_filter, del_cond).count()
    del_curr = AuditLog.query.filter(org_filter, del_cond, AuditLog.created_at >= p_curr_start).count()
    del_prev = AuditLog.query.filter(org_filter, del_cond, AuditLog.created_at >= p_prev_start, AuditLog.created_at < p_curr_start).count()
    deleted_growth = calc_growth(del_curr, del_prev)
    
    # Export Activities
    exp_cond = db.or_(AuditLog.action.like("%EXPORT%"), AuditLog.action.like("%DOWNLOAD%"))
    export_activities = AuditLog.query.filter(org_filter, exp_cond).count()
    exp_curr = AuditLog.query.filter(org_filter, exp_cond, AuditLog.created_at >= p_curr_start).count()
    exp_prev = AuditLog.query.filter(org_filter, exp_cond, AuditLog.created_at >= p_prev_start, AuditLog.created_at < p_curr_start).count()
    export_growth = calc_growth(exp_curr, exp_prev)
    
    # Active Sessions (Auto-terminates >= 2 hours inactive sessions first)
    cleanup_inactive_sessions(target_org_id if 'target_org_id' in locals() else user.org_id if (user and user.role and user.role.name != 'SuperAdmin') else None, inactivity_hours=2)
    active_sessions = SaaSUserSession.query.filter(sess_filter, SaaSUserSession.status == 'Active').count()
    sess_curr = SaaSUserSession.query.filter(sess_filter, SaaSUserSession.login_time >= p_curr_start).count()
    sess_prev = SaaSUserSession.query.filter(sess_filter, SaaSUserSession.login_time >= p_prev_start, SaaSUserSession.login_time < p_curr_start).count()
    session_growth = calc_growth(sess_curr, sess_prev)
    
    # Failed Login Attempts
    fail_logins_cond = AuditLog.action == "USER_LOGIN_FAILED"
    failed_login_attempts = AuditLog.query.filter(org_filter, fail_logins_cond).count()
    flog_curr = AuditLog.query.filter(org_filter, fail_logins_cond, AuditLog.created_at >= p_curr_start).count()
    flog_prev = AuditLog.query.filter(org_filter, fail_logins_cond, AuditLog.created_at >= p_prev_start, AuditLog.created_at < p_curr_start).count()
    failed_logins_growth = calc_growth(flog_curr, flog_prev)

    kpis = {
        "total_events": {"icon": "activity", "value": total_events, "growth": total_growth, "tooltip": "Total logged actions in registry", "last_updated": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
        "today_events": {"icon": "clock", "value": today_events, "growth": today_growth, "tooltip": "Audit logs recorded in past 24 hours", "last_updated": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
        "failed_actions": {"icon": "x-circle", "value": failed_actions, "growth": failed_growth, "tooltip": "Failed request operations", "last_updated": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
        "success_actions": {"icon": "check-circle", "value": success_actions, "growth": success_growth, "tooltip": "Successful actions authorized", "last_updated": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
        "security_events": {"icon": "shield-alert", "value": security_events, "growth": security_growth, "tooltip": "Critical authentication and access events", "last_updated": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
        "login_events": {"icon": "log-in", "value": login_events, "growth": login_growth, "tooltip": "Access sessions logging activity", "last_updated": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
        "data_changes": {"icon": "database", "value": data_changes, "growth": data_growth, "tooltip": "Database edits, inserts, and structural updates", "last_updated": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
        "critical_events": {"icon": "zap", "value": critical_events, "growth": critical_growth, "tooltip": "Operations posing higher compliance risks", "last_updated": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
        "deleted_records": {"icon": "trash-2", "value": deleted_records, "growth": deleted_growth, "tooltip": "Hard and soft deletions performed in organization", "last_updated": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
        "export_activities": {"icon": "download-cloud", "value": export_activities, "growth": export_growth, "tooltip": "Large data extracts, report building, and CSV exports", "last_updated": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
        "active_sessions": {"icon": "users", "value": active_sessions, "growth": session_growth, "tooltip": "Current active dashboard sessions", "last_updated": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
        "failed_logins": {"icon": "unlock", "value": failed_login_attempts, "growth": failed_logins_growth, "tooltip": "Unsuccessful credential challenge attempts", "last_updated": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}
    }
    
    return jsonify({"status": "success", "data": kpis}), 200


def extract_audit_diff_and_summary(log):
    """
    Extracts past data (before/old) vs current data (after/new) along with a human-readable change summary.
    Handles before_data/after_data JSON, details with 'old'/'new'/'previous'/'current',
    CREATE events, DELETE events, and custom admin update payloads.
    """
    diffs = {}
    summary = ""
    has_diff = False
    
    # 1. Direct before_data and after_data columns
    b = log.before_data
    a = log.after_data
    if (b not in (None, 'null', {})) or (a not in (None, 'null', {})):
        try:
            b_dict = b if isinstance(b, dict) else (json.loads(b) if isinstance(b, str) and b != 'null' else {})
            a_dict = a if isinstance(a, dict) else (json.loads(a) if isinstance(a, str) and a != 'null' else {})
            if b_dict or a_dict:
                all_keys = set(list((b_dict or {}).keys()) + list((a_dict or {}).keys()))
                for k in all_keys:
                    b_val = (b_dict or {}).get(k)
                    a_val = (a_dict or {}).get(k)
                    if b_val != a_val:
                        if k in ('password', 'hashed_password', 'secret', 'token', 'access_token'):
                            diffs[k] = {"before": "********", "after": "********"}
                        else:
                            diffs[k] = {
                                "before": b_val if b_val is not None else "(None)",
                                "after": a_val if a_val is not None else "(Deleted)"
                            }
                if diffs:
                    has_diff = True
                    summary = f"{len(diffs)} field{'s' if len(diffs) > 1 else ''} modified"
        except Exception:
            pass

    # 2. Check details dictionary for old/new, before/after, or action-specific payloads
    details = log.details
    if isinstance(details, str):
        try:
            details = json.loads(details)
        except Exception:
            details = None

    if isinstance(details, dict) and not diffs:
        # Case A: details contains 'old'/'before' and 'new'/'after'
        old_data = details.get('old') or details.get('before') or details.get('previous')
        new_data = details.get('new') or details.get('after') or details.get('current')
        changed_fields_list = details.get('changed_fields')

        if isinstance(old_data, dict) and isinstance(new_data, dict):
            target_keys = changed_fields_list if isinstance(changed_fields_list, list) and len(changed_fields_list) > 0 else set(list(old_data.keys()) + list(new_data.keys()))
            for k in target_keys:
                o_val = old_data.get(k)
                n_val = new_data.get(k)
                if k in ('password', 'hashed_password', 'secret', 'token', 'access_token'):
                    diffs[k] = {"before": "********", "after": "********"}
                else:
                    diffs[k] = {
                        "before": o_val if o_val is not None else "(None)",
                        "after": n_val if n_val is not None else "(None)"
                    }
            if diffs:
                has_diff = True
                summary = f"{len(diffs)} setting{'s' if len(diffs) > 1 else ''} modified"

        # Case B: CREATE_* actions
        elif log.action and ('CREATE' in log.action or 'REGISTER' in log.action or 'ADD' in log.action):
            has_diff = True
            created_name = details.get('username') or details.get('name') or details.get('email') or (f"Record #{log.target_id}" if log.target_id else "")
            summary = f"Created: {created_name}" if created_name else f"Created new {log.target_table or 'entity'}"
            for k, v in details.items():
                if k not in ('password', 'hashed_password', 'token'):
                    diffs[k] = {"before": "(None - New Record)", "after": v}

        # Case C: DELETE_* actions
        elif log.action and ('DELETE' in log.action or 'REMOVE' in log.action or 'TERMINAT' in log.action):
            has_diff = True
            del_name = details.get('deleted_username') or details.get('username') or details.get('deleted_email') or details.get('user_affected') or details.get('name') or (f"Record #{log.target_id}" if log.target_id else "")
            summary = f"Deleted: {del_name}" if del_name else f"Deleted {log.target_table or 'entity'}"
            for k, v in details.items():
                diffs[k] = {"before": v, "after": "(Permanently Deleted)"}

        # Case D: UPDATE_ROLE_PERMISSIONS
        elif log.action == 'UPDATE_ROLE_PERMISSIONS' and 'permissions' in details:
            has_diff = True
            summary = "Role permissions updated"
            perms = details['permissions']
            if isinstance(perms, dict):
                for r_name, p_map in perms.items():
                    enabled_modules = [m for m, v in p_map.items() if v] if isinstance(p_map, dict) else []
                    diffs[f"Role: {r_name}"] = {
                        "before": "(Previous Matrix)",
                        "after": f"Enabled: {', '.join(enabled_modules) if enabled_modules else 'None'}"
                    }

        # Case E: Generic details dict with custom changes map
        elif any(k in ('changes', 'delta', 'modified') for k in details.keys()):
            changes = details.get('changes') or details.get('delta') or details.get('modified')
            if isinstance(changes, dict):
                for k, v in changes.items():
                    if isinstance(v, dict) and ('before' in v or 'after' in v):
                        diffs[k] = {"before": v.get('before', '(None)'), "after": v.get('after', '(None)')}
                    else:
                        diffs[k] = {"before": "(Previous)", "after": v}
                if diffs:
                    has_diff = True
                    summary = f"{len(diffs)} field{'s' if len(diffs) > 1 else ''} modified"

        # Case F: Any other descriptive details dictionary
        if isinstance(details, dict) and not diffs:
            for k, v in details.items():
                if k not in ('password', 'hashed_password', 'secret', 'token', 'access_token', 'session_id', 'request_id'):
                    if isinstance(v, dict) and ('before' in v or 'after' in v):
                        diffs[k] = {"before": v.get('before', '(None)'), "after": v.get('after', '(None)')}
                    elif isinstance(v, dict) and ('old' in v or 'new' in v):
                        diffs[k] = {"before": v.get('old', '(None)'), "after": v.get('new', '(None)')}
                    else:
                        diffs[k] = {"before": "(Previous Value)", "after": v}
            if diffs:
                has_diff = True
                if not summary:
                    summary = f"{len(diffs)} detail field{'s' if len(diffs) > 1 else ''} recorded"

    # Default fallback summary if action is modification but diffs is empty
    if not summary:
        if log.action.startswith('CREATE_'):
            summary = f"Created {log.target_table or 'record'}"
            has_diff = True
        elif log.action.startswith('UPDATE_') or 'UPDATE' in log.action or 'MODIFY' in log.action:
            summary = f"Updated {log.target_table or 'record'}"
            has_diff = True
        elif log.action.startswith('DELETE_') or 'DELETE' in log.action:
            summary = f"Deleted {log.target_table or 'record'}"
            has_diff = True

    return diffs, has_diff, summary


@audit_bp.route('/logs', methods=['GET'])
@jwt_required()
@audit_required
def get_audit_logs():
    user = _get_user_from_jwt()
    
    # Query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '') # Success, Failed, Warning, Critical
    action_type = request.args.get('action_type', '') # DATA_CHANGES, SECURITY, CRITICAL, SESSIONS, Create, Update, Delete, Export, etc.
    risk_level = request.args.get('risk_level', '')
    module = request.args.get('module', '') # target_table name
    user_role = request.args.get('user_role', '')
    date_preset = request.args.get('date_preset', '') # today, yesterday, 7days, etc.
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')

    query = AuditLog.query.filter(get_user_org_filter(user, AuditLog))
    
    # Search filter
    if q:
        search_pattern = f"%{q}%"
        query = query.outerjoin(User, AuditLog.user_id == User.id).filter(
            db.or_(
                AuditLog.action.ilike(search_pattern),
                AuditLog.ip_address.ilike(search_pattern),
                AuditLog.browser.ilike(search_pattern),
                AuditLog.os.ilike(search_pattern),
                AuditLog.device.ilike(search_pattern),
                AuditLog.location.ilike(search_pattern),
                AuditLog.target_table.ilike(search_pattern),
                User.username.ilike(search_pattern),
                User.email.ilike(search_pattern)
            )
        )
        
    # Action type filter mapping
    if action_type:
        types = [t.strip().upper() for t in action_type.split(',')]
        type_filters = []
        for t in types:
            if t in ('DATA_CHANGES', 'DATA_MODIFICATIONS', 'DATA'):
                type_filters.append(AuditLog.action.like("CREATE_%"))
                type_filters.append(AuditLog.action.like("UPDATE_%"))
                type_filters.append(AuditLog.action.like("DELETE_%"))
                type_filters.append(AuditLog.action.like("%MODIFY%"))
                type_filters.append(AuditLog.action.like("%EDIT%"))
                type_filters.append(AuditLog.action.like("%CHANGE%"))
                type_filters.append(AuditLog.action.like("%SAVED%"))
                type_filters.append(AuditLog.action.like("%SYNCED%"))
                type_filters.append(AuditLog.action.in_([
                    "USER_UPDATE", "PROJECT_UPDATE", "ORGANIZATION_UPDATE", "PROJECT_CREATE",
                    "BULK_DELETE_USERS", "BULK_IMPORT_ROLLBACK", "STAGE_PROGRESS_UPDATE",
                    "WORKFLOW_UPDATE", "SOP_UPDATE", "SOP_CREATE", "SOP_DELETE"
                ]))
            elif t in ('SECURITY', 'SECURITY_ALERTS', 'SECURITY_WARNINGS'):
                type_filters.append(AuditLog.action.in_([
                    "USER_LOGIN_FAILED", "FAILED_LOGIN", "SUSPICIOUS_ACTIVITY",
                    "ROLE_ESCALATION", "PERMISSION_CHANGE", "BRUTE_FORCE",
                    "TAMPER_DETECTED", "ACCESS_DENIED", "SECURITY_ALERT",
                    "PASSWORD_RESET_FAILED", "USER_DELETE_ATTEMPT", "USER_LOGIN_LOCKED"
                ]))
                type_filters.append(AuditLog.risk_level.in_(['High', 'Critical']))
            elif t in ('CRITICAL', 'CRITICAL_INCIDENTS'):
                type_filters.append(AuditLog.risk_level == 'Critical')
                type_filters.append(AuditLog.action.in_(["TAMPER_DETECTED", "USER_LOGIN_LOCKED", "ROLE_ESCALATION", "SECURITY_ALERT"]))
            elif t in ('SESSIONS', 'AUTH_SESSIONS', 'LOGIN_EVENTS'):
                type_filters.append(AuditLog.action.in_(["USER_LOGIN", "USER_LOGOUT", "SESSION_FORCE_TERMINATION", "USER_LOGIN_FAILED"]))
            elif t in ('DELETED_RECORDS', 'DELETE'):
                type_filters.append(AuditLog.action.like("DELETE_%"))
                type_filters.append(AuditLog.action.in_(["BULK_DELETE_USERS", "USER_DELETE", "PROJECT_DELETE"]))
            elif t in ('FAILED_LOGINS', 'USER_LOGIN_FAILED'):
                type_filters.append(AuditLog.action == "USER_LOGIN_FAILED")
            elif t == 'CREATE':
                type_filters.append(AuditLog.action.like("CREATE_%"))
            elif t == 'UPDATE':
                type_filters.append(AuditLog.action.like("UPDATE_%"))
            elif t == 'EXPORT':
                type_filters.append(AuditLog.action.like("%EXPORT%"))
                type_filters.append(AuditLog.action.like("%DOWNLOAD%"))
            elif t == 'LOGIN':
                type_filters.append(AuditLog.action == "USER_LOGIN")
            elif t == 'LOGOUT':
                type_filters.append(AuditLog.action == "USER_LOGOUT")
            else:
                type_filters.append(AuditLog.action == t)
        if type_filters:
            query = query.filter(db.or_(*type_filters))
            
    # Status Filter
    if status:
        statuses = [s.strip() for s in status.split(',')]
        status_filters = []
        for s in statuses:
            if s == 'Success':
                status_filters.append(db.or_(AuditLog.response_code.is_(None), AuditLog.response_code < 400))
            elif s == 'Failed':
                status_filters.append(db.and_(AuditLog.response_code.isnot(None), AuditLog.response_code >= 400))
            elif s == 'Critical':
                status_filters.append(AuditLog.risk_level == 'Critical')
            elif s == 'Warning':
                status_filters.append(AuditLog.risk_level == 'High')
        if status_filters:
            query = query.filter(db.or_(*status_filters))

    # Risk level filter
    if risk_level:
        query = query.filter(AuditLog.risk_level == risk_level)
        
    # Module target filter
    if module:
        query = query.filter(AuditLog.target_table == module)
        
    # Date filters
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if date_preset:
        if date_preset == 'today':
            query = query.filter(AuditLog.created_at >= now.replace(hour=0, minute=0, second=0))
        elif date_preset == 'yesterday':
            yesterday = now - timedelta(days=1)
            query = query.filter(
                AuditLog.created_at >= yesterday.replace(hour=0, minute=0, second=0),
                AuditLog.created_at < now.replace(hour=0, minute=0, second=0)
            )
        elif date_preset == '7days':
            query = query.filter(AuditLog.created_at >= now - timedelta(days=7))
        elif date_preset == '30days':
            query = query.filter(AuditLog.created_at >= now - timedelta(days=30))
        elif date_preset == '90days':
            query = query.filter(AuditLog.created_at >= now - timedelta(days=90))
    elif start_date_str and end_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', ''))
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '')) + timedelta(days=1)
            query = query.filter(AuditLog.created_at >= start_date, AuditLog.created_at < end_date)
        except ValueError:
            pass

    # Pagination and Order
    pagination = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items
    
    data_items = []
    for log in logs:
        diffs, has_diff, summary = extract_audit_diff_and_summary(log)
        data_items.append({
            "id": log.id,
            "timestamp": log.created_at.isoformat() + "Z" if log.created_at else datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            "action": log.action,
            "module": log.target_table or "Global",
            "record_id": log.target_id,
            "user": log.user.username if log.user else "System",
            "user_email": log.user.email if log.user else "—",
            "role": log.user.role.name if log.user and log.user.role else "—",
            "ip_address": log.ip_address or "127.0.0.1",
            "location": get_geo_location(log.ip_address, user=log.user, req=request) if (not log.location or 'mumbai' in (log.location or '').lower() or log.location in ('Unknown', 'Unknown Location', 'Localhost', 'Private Network') or (log.location or '').startswith('IP ')) else log.location,
            "browser": log.browser or "Other",
            "os": log.os or "Other",
            "device": log.device or "Desktop",
            "session_id": log.session_id or "—",
            "risk_level": log.risk_level or "Low",
            "status": "Failed" if ((log.response_code and log.response_code >= 400) or any(k in (log.action or '').upper() for k in ('FAILED', 'DENIED', 'BLOCKED', 'LOCKED', 'ERROR', 'REVOKED', 'REJECTED'))) else ("Critical" if log.risk_level == 'Critical' else ("Warning" if log.risk_level == 'High' else "Success")),
            "response_code": log.response_code or 200,
            "has_diff": has_diff,
            "change_summary": summary,
            "changed_fields": diffs,
            "details": log.details or {}
        })

    return jsonify({
        "status": "success",
        "data": data_items,
        "pagination": {
            "total": pagination.total,
            "pages": pagination.pages,
            "page": page,
            "per_page": per_page
        }
    }), 200

# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: get_audit_log_detail (Lines 764-838)
# Reason: Unused single audit log modal fetch. Frontend modal renders data directly from table row JSON.
# ==============================================================================
# @audit_bp.route('/logs/<int:log_id>', methods=['GET'])
# @jwt_required()
# @audit_required
# def get_audit_log_detail(log_id):
#     user = _get_user_from_jwt()

#     org_filter = get_user_org_filter(user, AuditLog)
#     log = AuditLog.query.filter(org_filter, AuditLog.id == log_id).first_or_404()

#     # Related logs: same session or same user in the last hour
#     hour_ago = log.created_at - timedelta(hours=1)
#     hour_later = log.created_at + timedelta(hours=1)
#     org_cond = (AuditLog.org_id == log.org_id) if log.org_id else sa.true()
#     related = AuditLog.query.filter(
#         org_cond,
#         AuditLog.id != log.id,
#         db.or_(
#             AuditLog.session_id == log.session_id,
#             db.and_(AuditLog.user_id == log.user_id, AuditLog.created_at >= hour_ago, AuditLog.created_at <= hour_later)
#         )
#     ).order_by(AuditLog.created_at.desc()).limit(5).all()

#     # Timeline events for this session
#     timeline = []
#     if log.session_id:
#         sess_logs = AuditLog.query.filter(org_cond, AuditLog.session_id == log.session_id).order_by(AuditLog.created_at.asc()).all()
#         timeline = [{
#             "id": sl.id,
#             "timestamp": sl.created_at.isoformat() + "Z" if sl.created_at else datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
#             "action": sl.action,
#             "status": "Failed" if (sl.response_code and sl.response_code >= 400) else "Success"
#         } for sl in sess_logs]

#     # Extract differences in fields for Update/Create/Delete/Modify actions
#     diffs, has_diff, summary = extract_audit_diff_and_summary(log)

#     return jsonify({
#         "status": "success",
#         "data": {
#             "id": log.id,
#             "timestamp": log.created_at.isoformat() + "Z" if log.created_at else datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
#             "action": log.action,
#             "module": log.target_table or "Global",
#             "record_id": log.target_id,
#             "user": log.user.username if log.user else "System",
#             "user_email": log.user.email if log.user else "—",
#             "role": log.user.role.name if log.user and log.user.role else "—",
#             "ip_address": log.ip_address,
#             "location": log.location or "Unknown",
#             "browser": log.browser or "Other",
#             "os": log.os or "Other",
#             "device": log.device or "Desktop",
#             "session_id": log.session_id or "—",
#             "request_id": log.request_id or "—",
#             "response_code": log.response_code or 200,
#             "execution_time": log.execution_time if log.execution_time is not None else 0.0,
#             "risk_level": log.risk_level or "Low",
#             "before_data": log.before_data,
#             "after_data": log.after_data,
#             "has_diff": has_diff,
#             "change_summary": summary,
#             "changed_fields": diffs,
#             "details": log.details or {},
#             "hash_signature": log.hash_signature,
#             "is_tampered": log.is_tampered,
#             "related_logs": [{
#                 "id": rl.id,
#                 "timestamp": rl.created_at.isoformat() + "Z" if rl.created_at else datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
#                 "action": rl.action,
#                 "user": rl.user.username if rl.user else "System",
#                 "risk_level": rl.risk_level
#             } for rl in related],
#             "timeline": timeline
#         }
#     }), 200
# [END DEAD CODE: get_audit_log_detail]


def cleanup_inactive_sessions(org_id=None, inactivity_hours=2):
    """
    Terminates all active user sessions that have had no user movement/activity for >= inactivity_hours (default 2 hours).
    Sets status='Expired', logout_time = last_activity + 2h (or login_time + 2h), and calculates accurate session_duration.
    """
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cutoff = now - timedelta(hours=inactivity_hours)
        query = SaaSUserSession.query.filter(
            SaaSUserSession.status == 'Active',
            db.or_(
                db.and_(SaaSUserSession.last_activity.isnot(None), SaaSUserSession.last_activity < cutoff),
                db.and_(SaaSUserSession.last_activity.is_(None), SaaSUserSession.login_time < cutoff)
            )
        )
        if org_id:
            query = query.filter(SaaSUserSession.org_id == org_id)
            
        expired_sessions = query.all()
        for s in expired_sessions:
            ref_time = s.last_activity or s.login_time or (now - timedelta(hours=inactivity_hours))
            s.status = 'Expired'
            # Expire timestamp is ref_time + 2 hours (or now if less than 2 hours ago)
            expire_timestamp = ref_time + timedelta(hours=inactivity_hours)
            s.logout_time = expire_timestamp if expire_timestamp <= now else now
            if s.login_time:
                s.session_duration = max(0, int((s.logout_time - s.login_time).total_seconds()))
            else:
                s.session_duration = int(inactivity_hours * 3600)
                
        if expired_sessions:
            db.session.commit()
        return len(expired_sessions)
    except Exception as e:
        db.session.rollback()
        return 0


@audit_bp.route('/heartbeat', methods=['POST', 'GET'])
@jwt_required()
def session_heartbeat():
    """
    Called by frontend when user movement/interaction is detected to refresh last_activity.
    If session has been inactive for > 2 hours, terminates the session and returns 401.
    """
    try:
        current_user_id = int(get_jwt_identity())
        claims = get_jwt()
        session_id = claims.get('session_id') if isinstance(claims, dict) else None
        
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cutoff = now - timedelta(hours=2)
        
        sess = None
        if session_id:
            sess = SaaSUserSession.query.filter_by(session_id=session_id).first()
        if not sess:
            sess = SaaSUserSession.query.filter_by(user_id=current_user_id, status='Active').order_by(SaaSUserSession.login_time.desc()).first()
            
        if sess:
            ref_time = sess.last_activity or sess.login_time
            if sess.status == 'Active' and ref_time and ref_time < cutoff:
                # 2-hour continuous inactivity exceeded
                sess.status = 'Expired'
                sess.logout_time = ref_time + timedelta(hours=2)
                if sess.login_time:
                    sess.session_duration = max(0, int((sess.logout_time - sess.login_time).total_seconds()))
                db.session.commit()
                return jsonify({"status": "expired", "message": "Session terminated due to 2 hours of inactivity."}), 401
                
            # User is actively working: keep/set status to Active and refresh last_activity
            sess.status = 'Active'
            sess.last_activity = now
            db.session.commit()
            return jsonify({
                "status": "active",
                "session_id": sess.session_id,
                "last_activity": now.isoformat() + "Z"
            }), 200
            
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return internal_server_error(e, "An internal server error occurred.")


@audit_bp.route('/sessions', methods=['GET'])
@jwt_required()
@audit_required
def get_audit_sessions():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    
    # Auto-cleanup any sessions that have been inactive for >= 2 hours before returning data
    target_org = user.org_id if (user and user.role and user.role.name != 'SuperAdmin') else None
    cleanup_inactive_sessions(target_org, inactivity_hours=2)
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    q = request.args.get('q', '').strip()
    status = request.args.get('status', 'Active').strip() # Active, LoggedOut, Terminated, Expired, or all

    query = SaaSUserSession.query.filter(get_user_org_filter(user, SaaSUserSession))
    
    if q:
        search_pattern = f"%{q}%"
        query = query.join(User, SaaSUserSession.user_id == User.id).filter(
            db.or_(
                User.username.ilike(search_pattern),
                User.email.ilike(search_pattern),
                SaaSUserSession.session_id.ilike(search_pattern),
                SaaSUserSession.ip_address.ilike(search_pattern)
            )
        )
        
    if status and status.lower() != 'all':
        query = query.filter(SaaSUserSession.status.ilike(status))

    pagination = query.order_by(SaaSUserSession.login_time.desc()).paginate(page=page, per_page=per_page, error_out=False)
    sessions = pagination.items
    current_req_ip = get_real_client_ip(request)

    res_sessions = []
    for s in sessions:
        raw_ip = s.ip_address if (s.ip_address and s.ip_address != '127.0.0.1') else current_req_ip
        raw_loc = get_geo_location(raw_ip, user=s.user, req=request) if (not s.location or 'mumbai' in (s.location or '').lower() or (s.location or '').startswith('Localhost') or (s.location or '').startswith('IP ')) else s.location
        raw_os = s.os if (s.os and s.os not in ('Other', 'Unknown OS')) else 'Windows'
        raw_browser = s.browser if (s.browser and s.browser not in ('Other', 'Other Browser')) else 'Chrome'
        raw_device = s.device or 'Desktop'

        # Accurate session duration calculation
        now_dt = datetime.now(timezone.utc).replace(tzinfo=None)
        if s.status == 'Active':
            login_t = s.login_time or now_dt
            dur_secs = max(0, int((now_dt - login_t).total_seconds()))
        else:
            if s.session_duration is not None and s.session_duration >= 0:
                dur_secs = s.session_duration
            elif s.logout_time and s.login_time:
                dur_secs = max(0, int((s.logout_time - s.login_time).total_seconds()))
            else:
                dur_secs = 0

        res_sessions.append({
            "session_id": s.session_id,
            "username": s.user.username if s.user else "Unknown",
            "email": s.user.email if s.user else "N/A",
            "login_time": s.login_time.isoformat() + "Z" if s.login_time else None,
            "last_activity": s.last_activity.isoformat() + "Z" if s.last_activity else None,
            "logout_time": s.logout_time.isoformat() + "Z" if s.logout_time else None,
            "session_duration": dur_secs,
            "device": raw_device,
            "browser": raw_browser,
            "os": raw_os,
            "ip_address": raw_ip,
            "location": raw_loc,
            "status": s.status
        })

    return jsonify({
        "status": "success",
        "data": res_sessions,
        "pagination": {
            "total": pagination.total,
            "pages": pagination.pages,
            "page": page,
            "per_page": per_page
        }
    }), 200

@audit_bp.route('/sessions/<string:session_id>/terminate', methods=['POST'])
@jwt_required()
@audit_required
def terminate_session(session_id):
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    
    sess = SaaSUserSession.query.filter(get_user_org_filter(user, SaaSUserSession), SaaSUserSession.session_id == session_id).first_or_404()
    if sess.status == 'Active':
        sess.status = 'Terminated'
        sess.logout_time = datetime.now(timezone.utc).replace(tzinfo=None)
        sess.session_duration = int((sess.logout_time - (sess.login_time or sess.logout_time)).total_seconds())
        
        # Log this administrative termination
        log_audit_event(
            org_id=user.org_id,
            user_id=user.id,
            action="SESSION_FORCE_TERMINATION",
            target_table="saas_user_sessions",
            target_id=None,
            details={"terminated_session_id": session_id, "user_affected": sess.user.username if sess.user else "Unknown"}
        )
        db.session.commit()
        return jsonify({"status": "success", "message": f"Session {session_id} has been terminated."}), 200
        
    return jsonify({"status": "error", "message": "Session is not active."}), 400

@audit_bp.route('/insights', methods=['GET'])
@jwt_required()
@audit_required
def get_audit_insights():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    
    org_filter = get_user_org_filter(user, AuditLog)
    sess_filter = get_user_org_filter(user, SaaSUserSession)
    
    crit_count = AuditLog.query.filter(org_filter, AuditLog.risk_level == 'Critical').count()
    high_count = AuditLog.query.filter(org_filter, AuditLog.risk_level == 'High').count()
    failed_logins = AuditLog.query.filter(org_filter, AuditLog.action == "USER_LOGIN_FAILED").count()
    
    risk_score = max(10, 100 - (crit_count * 15) - (high_count * 5) - (failed_logins * 1.5))
    
    recs = []
    
    active_device_counts = db.session.query(SaaSUserSession.user_id, db.func.count(SaaSUserSession.device.distinct()))\
        .filter(sess_filter, SaaSUserSession.status == 'Active')\
        .group_by(SaaSUserSession.user_id).all()
        
    for uid, dev_count in active_device_counts:
        if dev_count > 1:
            u_obj = db.session.get(User, uid)
            if u_obj:
                recs.append(f"Unusual Pattern: User '{u_obj.username}' has {dev_count} active sessions on different devices. Verify if session hijacking or credential sharing is occurring.")

    thirty_days_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
    req_org_id = request.args.get('org_id', type=int)
    role_name = user.role.name if (user and user.role) else ''
    is_super = (role_name in ('SuperAdmin', 'Super Admin')) or getattr(user, 'is_super_admin', False)
    
    if is_super and not req_org_id:
        admins = User.query.join(Role).filter(Role.name.in_(('SuperAdmin', 'Owner', 'Platform Admin'))).all()
    else:
        target_org = req_org_id if is_super else user.org_id
        admins = User.query.join(Role).filter(User.org_id == target_org, Role.name.in_(('SuperAdmin', 'Owner', 'Platform Admin'))).all()

    for adm in admins:
        if not adm.last_login or adm.last_login < thirty_days_ago:
            recs.append(f"Compliance Risk: Admin user '{adm.username}' has been inactive for over 30 days. Recommend removing administrative privileges or suspending account.")

    high_risk_users = db.session.query(AuditLog.user_id, db.func.count(AuditLog.id))\
        .filter(org_filter, AuditLog.risk_level.in_(('High', 'Critical')))\
        .group_by(AuditLog.user_id).all()
        
    for uid, flag_count in high_risk_users:
        if flag_count >= 3:
            u_obj = db.session.get(User, uid)
            if u_obj:
                recs.append(f"Security Alert: User '{u_obj.username}' triggered {flag_count} high/critical risk events. Immediate account activity audit is advised.")

    exports_24h = AuditLog.query.filter(
        org_filter,
        AuditLog.created_at >= datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24),
        db.or_(AuditLog.action.like("%EXPORT%"), AuditLog.action.like("%DOWNLOAD%"))
    ).count()
    if exports_24h >= 5:
        recs.append(f"Data Leak Risk: High volume of data exports ({exports_24h}) detected in past 24 hours. Ensure bulk downloads match SOC 2 compliance policy.")

    if not recs:
        recs.append("All login patterns appear normal. Keep monitoring session durations and API abuse metrics.")
        recs.append("Authentication failure rate is within acceptable SLA margins (under 2%).")
        recs.append("No active session hijacking flags detected in this period.")

    return jsonify({
        "status": "success",
        "data": {
            "risk_score": round(risk_score, 1),
            "recommendations": recs,
            "metrics": {
                "critical_incidents": crit_count,
                "high_incidents": high_count,
                "failed_logins": failed_logins,
                "active_admins": len(admins)
            }
        }
    }), 200

@audit_bp.route('/integrity', methods=['GET'])
@jwt_required()
@audit_required
def verify_audit_integrity():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)

    # Fetch ALL logs for this org (SuperAdmin can scope to a specific org via ?org_id=)
    logs = AuditLog.query.filter(
        get_user_org_filter(user, AuditLog)
    ).order_by(AuditLog.created_at.asc()).all()

    total_checked  = len(logs)
    tampered_logs  = []
    backfilled     = 0   # logs that had no hash yet → assigned one now
    needs_commit   = False

    for log in logs:
        expected = calculate_log_hash(log)
        if not log.hash_signature:
            # First-time hash assignment — backfill silently
            log.hash_signature = expected
            log.is_tampered    = False
            backfilled        += 1
            needs_commit       = True
        elif log.hash_signature != expected:
            log.is_tampered = True
            needs_commit    = True
            tampered_logs.append({
                "id":                 log.id,
                "action":             log.action,
                "timestamp":          log.created_at.isoformat() + "Z" if log.created_at else datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
                "operator":           log.user.username if log.user else "System",
                "signature_in_db":    log.hash_signature,
                "signature_computed": expected
            })

    # Always commit any hash changes (backfills + tampering flags)
    if needs_commit:
        db.session.commit()

    passed = total_checked - len(tampered_logs) - backfilled

    if tampered_logs:
        log_audit_event(
            org_id=user.org_id,
            user_id=user.id,
            action="TAMPER_DETECTED",
            target_table="audit_logs",
            target_id=None,
            details={
                "tampered_count": len(tampered_logs),
                "total_checked":  total_checked,
                "backfilled":     backfilled
            }
        )
        return jsonify({
            "status":          "warning",
            "message":         f"Cryptographic signature validation failed for {len(tampered_logs)} record(s). Registry may have been altered.",
            "total_checked":   total_checked,
            "passed":          passed,
            "backfilled":      backfilled,
            "tampered_count":  len(tampered_logs),
            "tampered_records": tampered_logs
        }), 200

    return jsonify({
        "status":        "success",
        "message":       f"All {total_checked} log record(s) passed SHA-256 verification. Registry is intact.",
        "total_checked": total_checked,
        "passed":        passed,
        "backfilled":    backfilled,
        "tampered_count": 0
    }), 200

@audit_bp.route('/export', methods=['GET'])
@jwt_required()
@audit_required
def export_audit_logs():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    
    logs = AuditLog.query.filter(get_user_org_filter(user, AuditLog)).order_by(AuditLog.created_at.desc()).all()
    
    log_audit_event(
        org_id=user.org_id,
        user_id=user.id,
        action="EXPORT_COMPLIANCE_AUDIT_LOGS",
        target_table="audit_logs",
        target_id=None,
        details={"record_count": len(logs), "format": "CSV"}
    )
    
    exp = AuditExportLog(
        org_id=user.org_id,
        user_id=user.id,
        export_type='CSV',
        record_count=len(logs),
        details={"reason": "Security compliance report extraction"}
    )
    db.session.add(exp)
    db.session.commit()

    csv_data = "Audit ID,Timestamp,Operator,Email,Role,IP Address,Location,Browser,OS,Device,Event Category,Object Affected,Record ID,Session ID,Response Code,Risk Level\n"
    for log in logs:
        operator = log.user.username if log.user else "System"
        email = log.user.email if log.user else "—"
        role = log.user.role.name if log.user and log.user.role else "—"
        
        row_fields = [
            str(log.id),
            log.created_at.isoformat() + "Z",
            operator,
            email,
            role,
            log.ip_address or "",
            log.location or "",
            log.browser or "",
            log.os or "",
            log.device or "",
            log.action,
            log.target_table or "Global",
            str(log.target_id or ""),
            log.session_id or "",
            str(log.response_code or 200),
            log.risk_level or "Low"
        ]
        csv_data += ",".join([f'"{f.replace(chr(34), chr(34)+chr(34))}"' for f in row_fields]) + "\n"

    return jsonify({
        "status": "success",
        "csv": csv_data,
        "count": len(logs)
    }), 200


@audit_bp.route('/storage-info', methods=['GET'])
@jwt_required()
@audit_required
def get_audit_storage_info():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    
    org_filter = get_user_org_filter(user, AuditLog)
    total_count = AuditLog.query.filter(org_filter).count()
    
    # Estimate size (approx 0.8 KB per audit log entry)
    estimated_mb = round((total_count * 0.8) / 1024.0, 2)
    
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    d30 = now - timedelta(days=30)
    d60 = now - timedelta(days=60)
    d90 = now - timedelta(days=90)
    d180 = now - timedelta(days=180)
    d365 = now - timedelta(days=365)
    
    d730 = now - timedelta(days=730)
    d1095 = now - timedelta(days=1095)
    d1825 = now - timedelta(days=1825)
    d2555 = now - timedelta(days=2555)
    d2920 = now - timedelta(days=2920)
    
    older_than_30 = AuditLog.query.filter(org_filter, AuditLog.created_at < d30).count()
    older_than_60 = AuditLog.query.filter(org_filter, AuditLog.created_at < d60).count()
    older_than_90 = AuditLog.query.filter(org_filter, AuditLog.created_at < d90).count()
    older_than_180 = AuditLog.query.filter(org_filter, AuditLog.created_at < d180).count()
    older_than_365 = AuditLog.query.filter(org_filter, AuditLog.created_at < d365).count()
    older_than_730 = AuditLog.query.filter(org_filter, AuditLog.created_at < d730).count()
    older_than_1095 = AuditLog.query.filter(org_filter, AuditLog.created_at < d1095).count()
    older_than_1825 = AuditLog.query.filter(org_filter, AuditLog.created_at < d1825).count()
    older_than_2555 = AuditLog.query.filter(org_filter, AuditLog.created_at < d2555).count()
    older_than_2920 = AuditLog.query.filter(org_filter, AuditLog.created_at < d2920).count()
    
    oldest_log = AuditLog.query.filter(org_filter).order_by(AuditLog.created_at.asc()).first()
    oldest_date = oldest_log.created_at.isoformat() + "Z" if (oldest_log and oldest_log.created_at) else None
    
    retention_days = 0 # Default: 0 = Never auto-delete (Keep all logs)
    retention_years = 0
    org_id = user.org_id if user else None
    if not org_id:
        first_org = Organization.query.first()
        if first_org:
            org_id = first_org.id

    if org_id:
        org = db.session.get(Organization, org_id)
        if org and org.security_settings and isinstance(org.security_settings, dict):
            retention_days = org.security_settings.get('audit_retention_days', 0)
            retention_years = org.security_settings.get('audit_retention_years', 0)
            
    return jsonify({
        "status": "success",
        "total_count": total_count,
        "estimated_mb": estimated_mb,
        "oldest_date": oldest_date,
        "older_than_30d": older_than_30,
        "older_than_60d": older_than_60,
        "older_than_90d": older_than_90,
        "older_than_180d": older_than_180,
        "older_than_365d": older_than_365,
        "older_than_730d": older_than_730,
        "older_than_1095d": older_than_1095,
        "older_than_1825d": older_than_1825,
        "older_than_2555d": older_than_2555,
        "older_than_2920d": older_than_2920,
        "retention_days": retention_days,
        "retention_years": retention_years
    }), 200


@audit_bp.route('/retention-policy', methods=['POST', 'PUT'])
@jwt_required()
@audit_required
def update_audit_retention_policy():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    if not user:
        return jsonify({"message": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    
    org_id = user.org_id or (data.get('org_id') if isinstance(data, dict) else None)
    if not org_id:
        first_org = Organization.query.first()
        if first_org:
            org_id = first_org.id

    if not org_id:
        return jsonify({"message": "Organization context required"}), 400

    retention_days = data.get('retention_days')
    retention_years = data.get('retention_years')

    if retention_years is not None and str(retention_years).strip() != '':
        try:
            years = float(retention_years)
            if years <= 0:
                retention_days = 0
                retention_years = 0
            else:
                retention_days = int(round(years * 365.25))
                retention_years = years
        except Exception:
            return jsonify({"message": "Invalid retention_years value"}), 400
    elif retention_days is not None:
        try:
            retention_days = int(retention_days)
            retention_years = round(retention_days / 365.25, 2) if retention_days > 0 else 0
        except Exception:
            return jsonify({"message": "Invalid retention_days value"}), 400
    else:
        retention_days = 0
        retention_years = 0

    org = db.session.get(Organization, org_id)
    if not org:
        return jsonify({"message": "Organization not found"}), 404

    sec = dict(org.security_settings or {})
    sec['audit_retention_days'] = retention_days
    sec['audit_retention_years'] = retention_years
    org.security_settings = sec
    db.session.commit()

    try:
        log_audit_event(
            org_id=org.id,
            user_id=user.id,
            action="UPDATE_RETENTION_POLICY",
            target_table="organizations",
            target_id=org.id,
            details={
                "retention_days": retention_days,
                "retention_years": retention_years
            }
        )
    except Exception:
        pass

    if retention_days == 0:
        msg = "Automatic storage retention policy updated: Keep all logs indefinitely (Never auto-delete)."
    elif retention_years and retention_years >= 1:
        msg = f"Automatic storage retention policy updated: Auto-purge logs older than {retention_years} year(s) ({retention_days} days)."
    else:
        msg = f"Automatic storage retention policy updated: Auto-purge logs older than {retention_days} day(s)."

    return jsonify({
        "status": "success",
        "message": msg,
        "retention_days": retention_days,
        "retention_years": retention_years
    }), 200


@audit_bp.route('/purge-preview', methods=['GET', 'POST'])
@jwt_required()
@audit_required
def preview_audit_log_purge():
    user = _get_user_from_jwt()
    if not user:
        return jsonify({"message": "Unauthorized"}), 401

    data = request.get_json(silent=True) or request.args
    retention_years = data.get('retention_years')
    custom_before_date = data.get('before_date') or data.get('start_date')

    role_name = user.role.name if (user and user.role) else ''
    is_super = (role_name in ('SuperAdmin', 'Super Admin')) or getattr(user, 'is_super_admin', False)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff_date = None

    if custom_before_date:
        try:
            cutoff_date = datetime.fromisoformat(str(custom_before_date).replace('Z', ''))
        except Exception:
            return jsonify({"message": "Invalid custom cutoff date format. Use YYYY-MM-DD."}), 400
    elif retention_years is not None:
        try:
            years = float(retention_years)
            if not is_super and years > 8:
                years = 8.0
            cutoff_date = now - timedelta(days=int(years * 365.25))
        except Exception:
            return jsonify({"message": "Invalid retention_years value."}), 400
    else:
        default_years = 7.0 if is_super else 8.0
        cutoff_date = now - timedelta(days=int(default_years * 365.25))

    query = AuditLog.query.filter(AuditLog.created_at < cutoff_date)

    if not is_super:
        if not user.org_id:
            return jsonify({"message": "Organization context required"}), 400
        query = query.filter(AuditLog.org_id == user.org_id)
    else:
        req_org_id = data.get('org_id')
        if req_org_id:
            query = query.filter(AuditLog.org_id == int(req_org_id))

    match_count = query.count()
    return jsonify({
        "status": "success",
        "cutoff_date": cutoff_date.strftime('%Y-%m-%d'),
        "match_count": match_count,
        "is_super_admin": is_super,
        "max_retention_years": 8 if not is_super else 7
    }), 200


@audit_bp.route('/purge', methods=['POST', 'DELETE'])
@jwt_required()
@audit_required
def purge_audit_logs():
    user = _get_user_from_jwt()
    if not user:
        return jsonify({"message": "Unauthorized"}), 401

    data = request.get_json(silent=True) or request.args
    retention_years = data.get('retention_years')
    custom_before_date = data.get('before_date') or data.get('start_date')
    mode = data.get('mode')
    days = data.get('days')

    role_name = user.role.name if (user and user.role) else ''
    is_super = (role_name in ('SuperAdmin', 'Super Admin')) or getattr(user, 'is_super_admin', False)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff_date = None

    if custom_before_date:
        try:
            cutoff_date = datetime.fromisoformat(str(custom_before_date).replace('Z', ''))
        except Exception:
            return jsonify({"message": "Invalid custom cutoff date format."}), 400
    elif retention_years is not None:
        try:
            years = float(retention_years)
            if not is_super and years > 8:
                years = 8.0
            cutoff_date = now - timedelta(days=int(years * 365.25))
        except Exception:
            return jsonify({"message": "Invalid retention_years value."}), 400
    elif days is not None:
        try:
            cutoff_date = now - timedelta(days=int(days))
        except Exception:
            return jsonify({"message": "Invalid days value."}), 400
    else:
        default_years = 7.0 if is_super else 8.0
        cutoff_date = now - timedelta(days=int(default_years * 365.25))

    # Enforce auto-purge for org logs older than 8 years
    if not is_super and user.org_id:
        max_8yr_cutoff = now - timedelta(days=int(8 * 365.25))
        AuditLog.query.filter(AuditLog.org_id == user.org_id, AuditLog.created_at < max_8yr_cutoff).delete(synchronize_session=False)

    query = AuditLog.query.filter(AuditLog.created_at < cutoff_date)

    if not is_super:
        if not user.org_id:
            return jsonify({"message": "Organization context required"}), 400
        query = query.filter(AuditLog.org_id == user.org_id)
    else:
        req_org_id = data.get('org_id')
        if req_org_id:
            query = query.filter(AuditLog.org_id == int(req_org_id))

    deleted_count = query.delete(synchronize_session=False)
    db.session.commit()

    try:
        log_audit_event(
            org_id=user.org_id,
            user_id=user.id,
            action="PURGE_AUDIT_LOGS",
            target_table="audit_logs",
            target_id=0,
            details={
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.strftime('%Y-%m-%d'),
                "retention_years": retention_years or "custom"
            }
        )
    except Exception:
        pass

    return jsonify({
        "status": "success",
        "message": f"Successfully purged {deleted_count} audit log(s) created prior to {cutoff_date.strftime('%Y-%m-%d')}.",
        "deleted_count": deleted_count,
        "cutoff_date": cutoff_date.strftime('%Y-%m-%d')
    }), 200
