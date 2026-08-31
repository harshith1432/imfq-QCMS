"""
QCMS Feature Engine REST & Streaming Routes
============================================
Provides client-side endpoints for:
- /api/feature-engine/flags (cached flag list for logged-in user's org)
- /api/feature-engine/stream (SSE stream for live hot-reload)
- /api/feature-engine/track-usage (track page view/button actions)
- /api/feature-engine/coverage-report (SuperAdmin diagnostic endpoint)
- /api/feature-engine/invalidate (cache bust)
"""

from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from app.domain.services.feature_engine import FeatureEngine
from app.infrastructure.database.models.models import db, User, Module
from app.presentation.middleware.middleware import super_admin_required

feature_engine_bp = Blueprint('feature_engine', __name__, url_prefix='/api/feature-engine')


@feature_engine_bp.route('/flags', methods=['GET'])
def get_user_flags():
    """
    Returns full feature flag dict {module_code: bool} for current authenticated user's org.
    Unauthenticated users get public default flags.
    """
    user = None
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            user = db.session.get(User, int(user_id))
    except Exception:
        pass

    org_id = user.org_id if user else None
    flags = FeatureEngine.get_all_flags(org_id)
    details = FeatureEngine.get_all_details(org_id)

    return jsonify({
        "status": "success",
        "org_id": org_id,
        "flags": flags,
        "details": details
    }), 200


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: check_single_flag (Lines 48-67)
# Reason: Single flag check; frontend client evaluates flags in-memory from /flags dictionary.
# ==============================================================================
# @feature_engine_bp.route('/flags/<module_code>', methods=['GET'])
# def check_single_flag(module_code):
#     """Checks a single feature module flag."""
#     user = None
#     try:
#         verify_jwt_in_request(optional=True)
#         user_id = get_jwt_identity()
#         if user_id:
#             user = db.session.get(User, int(user_id))
#     except Exception:
#         pass

#     org_id = user.org_id if user else None
#     enabled = FeatureEngine.is_enabled(org_id, module_code)

#     return jsonify({
#         "status": "success",
#         "module_code": module_code,
#         "enabled": enabled
#     }), 200
# [END DEAD CODE: check_single_flag]



@feature_engine_bp.route('/invalidate', methods=['POST'])
@jwt_required()
@super_admin_required()
def invalidate_cache():
    """Manually busts the FeatureEngine cache."""
    data = request.json or {}
    org_id = data.get('org_id')
    FeatureEngine.invalidate(org_id)
    return jsonify({
        "status": "success",
        "message": f"FeatureEngine cache invalidated for {'org ' + str(org_id) if org_id else 'all orgs'}."
    }), 200


@feature_engine_bp.route('/track-usage', methods=['POST'])
def track_usage():
    """Tracks page views, exports, and actions from the frontend."""
    user = None
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            user = db.session.get(User, int(user_id))
    except Exception:
        pass

    data = request.json or {}
    module_code = data.get('module_code')
    event_type = data.get('event_type', 'page_view')

    if module_code:
        org_id = user.org_id if user else None
        FeatureEngine.track_usage(module_code, org_id, event_type)

    return jsonify({"status": "success"}), 200


@feature_engine_bp.route('/stream', methods=['GET'])
def sse_stream():
    return jsonify({"status": "disabled", "message": "SSE stream is disabled to optimize performance."}), 501


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: get_coverage_report (Lines 112-141)
# Reason: Unused module coverage diagnostics.
# ==============================================================================
# @feature_engine_bp.route('/coverage-report', methods=['GET'])
# @jwt_required()
# @super_admin_required()
# def get_coverage_report():
#     """Generates an audit report of feature modules and their mapping status across the platform."""
#     all_modules = Module.query.filter_by(is_archived=False).all()
#     total = len(all_modules)

#     active_count = sum(1 for m in all_modules if m.status == 'Active')
#     inactive_count = sum(1 for m in all_modules if m.status in ('Inactive', 'Disabled'))
#     beta_count = sum(1 for m in all_modules if m.beta_feature)
#     ai_count = sum(1 for m in all_modules if m.ai_enabled)
#     system_count = sum(1 for m in all_modules if m.system_module)

#     categories = {}
#     for m in all_modules:
#         categories[m.category] = categories.get(m.category, 0) + 1

#     return jsonify({
#         "status": "success",
#         "total_modules": total,
#         "active_modules": active_count,
#         "inactive_modules": inactive_count,
#         "beta_modules": beta_count,
#         "ai_modules": ai_count,
#         "system_core_modules": system_count,
#         "categories_breakdown": categories,
#         "mapped_coverage_pct": 100.0,
#         "message": "All 144 modules are connected to the central FeatureEngine."
#     }), 200
# [END DEAD CODE: get_coverage_report]

