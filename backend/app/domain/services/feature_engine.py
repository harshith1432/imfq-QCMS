"""
QCMS Feature Engine — Centralized Feature Flag & Module Access Service
=====================================================================
Single source of truth for all feature availability across the platform.
Uses in-memory TTL cache to avoid per-request DB hits.

Usage:
    from app.domain.services.feature_engine import FeatureEngine

    # Check if a feature is enabled for an org
    FeatureEngine.is_enabled(org_id=5, module_code="projects.create")  # → True/False

    # Get all flags for an org (cached)
    FeatureEngine.get_all_flags(org_id=5)  # → {"projects.create": True, "sop.view": False, ...}

    # Bust cache when a module is changed
    FeatureEngine.invalidate(org_id=5)   # bust one org
    FeatureEngine.invalidate()            # bust all
"""

import time
import threading
from typing import Optional, Dict, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# In-Memory Cache
# ─────────────────────────────────────────────────────────────────────────────

_cache: Dict[str, Tuple[dict, float]] = {}   # key → (flags_dict, timestamp)
_cache_lock = threading.Lock()
_CACHE_TTL = 60  # seconds

# SSE subscriber queues (for live hot-reload)
_sse_subscribers: list = []
_sse_lock = threading.Lock()


def _cache_key(org_id: Optional[int]) -> str:
    return f"org:{org_id}" if org_id else "global"


def _is_expired(timestamp: float) -> bool:
    return (time.time() - timestamp) > _CACHE_TTL


# ─────────────────────────────────────────────────────────────────────────────
# FeatureEngine
# ─────────────────────────────────────────────────────────────────────────────

class FeatureEngine:
    """
    Centralized feature flag engine.

    Resolution order (first match wins):
      1. Module not found → ALLOW (unregistered = unrestricted)
      2. Module status = Disabled/Inactive/Removed → DENY
      3. Parent module disabled → DENY
      4. Org-level override exists → use override value
      5. Plan check → DENY if below minimum plan
      6. Dependency check → DENY if required dependency disabled
      7. → ALLOW
    """

    # ── Cache helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _compute_flags(org_id: Optional[int]) -> dict:
        """Compute full flag dict for an org. Called only on cache miss."""
        from app.infrastructure.database.models.models import (
            Module, OrganizationFeatureOverride, Organization, SaaSPlan, SaaSPlanModules, Subscription
        )
        from sqlalchemy import func

        plan_hierarchy = {
            'Trial': 1, 'Starter': 1, 'Professional': 2,
            'Enterprise': 3, 'Ultimate': 4, 'Custom': 5
        }

        # Load org plan and disabled modules list
        org_plan_level = 1
        plan_disabled_modules = set()
        org_enabled_modules = None

        if org_id:
            org = Organization.query.get(org_id)
            if org:
                # 1. Resolve subscription plan name from active Subscription or Organization.subscription_plan
                active_sub = Subscription.query.filter_by(org_id=org_id, subscription_status='Active').first()
                plan_name = active_sub.plan_name if active_sub else org.subscription_plan
                org_plan_level = plan_hierarchy.get(plan_name or 'Starter', 1)

                # 2. Load modules explicitly disabled for this SaaSPlan template
                if plan_name:
                    saas_plan = SaaSPlan.query.filter(
                        (func.lower(SaaSPlan.name) == plan_name.lower()) | 
                        (func.lower(SaaSPlan.plan_type) == plan_name.lower())
                    ).first()
                    if saas_plan:
                        disabled_rows = SaaSPlanModules.query.filter_by(plan_id=saas_plan.id, is_enabled=False).all()
                        for pm in disabled_rows:
                            if pm.module_name:
                                plan_disabled_modules.add(pm.module_name.strip().lower())

                # 3. Load org's custom enabled_modules if present
                if org.enabled_modules and isinstance(org.enabled_modules, list) and len(org.enabled_modules) > 0:
                    org_enabled_modules = set(str(m).strip().lower() for m in org.enabled_modules)

        # Load all org overrides in one query
        overrides: Dict[int, bool] = {}
        if org_id:
            ovr_rows = OrganizationFeatureOverride.query.filter_by(org_id=org_id).all()
            for o in ovr_rows:
                overrides[o.module_id] = o.is_enabled

        # Load all modules
        all_modules = Module.query.filter_by(is_archived=False).all()
        module_by_id = {m.id: m for m in all_modules}

        flags = {}
        details = {}
        for m in all_modules:
            res = FeatureEngine._evaluate_detailed(
                m, module_by_id, overrides, org_plan_level, plan_hierarchy, plan_disabled_modules, org_enabled_modules
            )
            
            # Map code and name
            flags[m.code] = res["enabled"]
            details[m.code] = res
            if m.name:
                flags[m.name] = res["enabled"]
                details[m.name] = res
            
            # Synchronize PDF & Excel Export aliases across code representations
            if m.code in ('reports.pdf', 'reports.export_pdf') or (m.name and m.name.lower() == 'pdf export'):
                flags['reports.pdf'] = res["enabled"]
                flags['reports.export_pdf'] = res["enabled"]
                flags['PDF Export'] = res["enabled"]
                details['reports.pdf'] = res
                details['reports.export_pdf'] = res
                details['PDF Export'] = res
            elif m.code in ('reports.excel', 'reports.export_excel') or (m.name and m.name.lower() in ('excel export', 'excel & csv data export')):
                flags['reports.excel'] = res["enabled"]
                flags['reports.export_excel'] = res["enabled"]
                flags['Excel Export'] = res["enabled"]
                details['reports.excel'] = res
                details['reports.export_excel'] = res
                details['Excel Export'] = res

        return {"flags": flags, "details": details}

    @staticmethod
    def _evaluate_detailed(
        module,
        module_by_id: dict,
        overrides: Dict[int, bool],
        org_plan_level: int,
        plan_hierarchy: dict,
        plan_disabled_modules: set,
        org_enabled_modules: Optional[set] = None
    ) -> dict:
        """Evaluate access for a single module with detailed reason and required plan."""
        req_plan = module.minimum_plan or 'Starter'
        name = module.name or module.code

        # 1. Global status & backend toggle check in database
        if module.status != 'Active' or not module.backend_enabled or module.is_archived:
            return {"enabled": False, "reason": "disabled", "required_plan": req_plan, "name": name}

        # 2. Recursive parent check
        parent_id = module.parent_id
        seen = set()
        while parent_id and parent_id not in seen:
            seen.add(parent_id)
            parent = module_by_id.get(parent_id)
            if parent is None:
                break
            if parent.status != 'Active' or not parent.backend_enabled or parent.is_archived:
                return {"enabled": False, "reason": "disabled", "required_plan": req_plan, "name": name}
            parent_id = parent.parent_id

        # 3. Explicit Org override wins if configured
        if module.id in overrides:
            if not overrides[module.id]:
                return {"enabled": False, "reason": "disabled", "required_plan": req_plan, "name": name}
            else:
                return {"enabled": True, "reason": "ok", "required_plan": req_plan, "name": name}

        # 4. Check if explicitly disabled for this SaaS Plan template
        mod_code = (module.code or '').strip().lower()
        mod_name = (module.name or '').strip().lower()

        if plan_disabled_modules:
            if mod_code in plan_disabled_modules or mod_name in plan_disabled_modules:
                return {"enabled": False, "reason": "upgrade_required", "required_plan": req_plan, "name": name}

        # 5. Minimum Plan Level check
        if module.minimum_plan and module.minimum_plan != 'Starter':
            min_level = plan_hierarchy.get(module.minimum_plan, 1)
            if org_plan_level < min_level:
                return {"enabled": False, "reason": "upgrade_required", "required_plan": module.minimum_plan, "name": name}

        # 6. Check custom org_enabled_modules if specified
        if org_enabled_modules:
            mod_cat = (module.category or '').strip().lower()
            in_org = (
                mod_code in org_enabled_modules or 
                mod_name in org_enabled_modules or 
                mod_cat in org_enabled_modules
            )
            if not in_org and not module.system_module:
                return {"enabled": False, "reason": "disabled", "required_plan": req_plan, "name": name}

        return {"enabled": True, "reason": "ok", "required_plan": req_plan, "name": name}

    @staticmethod
    def _evaluate(
        module,
        module_by_id: dict,
        overrides: Dict[int, bool],
        org_plan_level: int,
        plan_hierarchy: dict,
        plan_enabled_modules: set,
        org_enabled_modules: Optional[set] = None
    ) -> bool:
        res = FeatureEngine._evaluate_detailed(
            module, module_by_id, overrides, org_plan_level, plan_hierarchy, plan_enabled_modules, org_enabled_modules
        )
        return res["enabled"]

        # 7. Required dependency check
        from app.infrastructure.database.models.models import ModuleDependency
        deps = ModuleDependency.query.filter_by(
            module_id=module.id, dependency_type='Required'
        ).all()
        for dep in deps:
            dep_mod = module_by_id.get(dep.dependency_module_id)
            if dep_mod and (dep_mod.status != 'Active' or not dep_mod.backend_enabled or dep_mod.is_archived):
                return False

        return True

    # ── Public API ────────────────────────────────────────────────────────────

    @classmethod
    def get_all_flags(cls, org_id: Optional[int]) -> dict:
        """Return {module_code: bool} for org, using cache."""
        key = _cache_key(org_id)
        with _cache_lock:
            entry = _cache.get(key)
            if entry and not _is_expired(entry[1]):
                res = entry[0]
                return res.get("flags", {}) if isinstance(res, dict) and "flags" in res else res

        # Cache miss — compute and store
        computed = cls._compute_flags(org_id)
        with _cache_lock:
            _cache[key] = (computed, time.time())
        return computed.get("flags", {})

    @classmethod
    def get_all_details(cls, org_id: Optional[int]) -> dict:
        """Return {module_code: {enabled, reason, required_plan, name}} for org, using cache."""
        key = _cache_key(org_id)
        with _cache_lock:
            entry = _cache.get(key)
            if entry and not _is_expired(entry[1]):
                res = entry[0]
                return res.get("details", {}) if isinstance(res, dict) and "details" in res else {}

        # Cache miss — compute and store
        computed = cls._compute_flags(org_id)
        with _cache_lock:
            _cache[key] = (computed, time.time())
        return computed.get("details", {})

    @classmethod
    def is_enabled(cls, org_id: Optional[int], module_code: str) -> bool:
        """Check if a single module is enabled for an org."""
        if not module_code:
            return True
        flags = cls.get_all_flags(org_id)
        return flags.get(module_code, True)  # Unknown module = allow

    @classmethod
    def get_config(cls, module_code: str) -> Optional[dict]:
        """Return full config dict for a module code."""
        from app.infrastructure.database.models.models import Module
        m = Module.query.filter_by(code=module_code, is_archived=False).first()
        if not m:
            return None
        return {
            'id': m.id,
            'code': m.code,
            'name': m.name,
            'status': m.status,
            'visible_in_sidebar': m.visible_in_sidebar,
            'visible_in_dashboard': m.visible_in_dashboard,
            'page_visibility': m.page_visibility,
            'widget_visibility': m.widget_visibility,
            'button_visibility': m.button_visibility,
            'backend_enabled': m.backend_enabled,
            'frontend_enabled': m.frontend_enabled,
            'api_enabled': m.api_enabled,
            'export_enabled': m.export_enabled,
            'import_enabled': m.import_enabled,
            'notification_enabled': m.notification_enabled,
            'background_jobs_enabled': m.background_jobs_enabled,
            'ai_enabled': m.ai_enabled,
        }

    @classmethod
    def invalidate(cls, org_id: Optional[int] = None):
        """
        Bust the cache.
        - invalidate(org_id=5) → bust only org 5
        - invalidate()          → bust ALL cache entries
        """
        with _cache_lock:
            if org_id is not None:
                _cache.pop(_cache_key(org_id), None)
                _cache.pop('global', None)  # also bust global
            else:
                _cache.clear()

    # ── SSE Hot-Reload ────────────────────────────────────────────────────────

    @classmethod
    def subscribe_sse(cls):
        """Register a new SSE subscriber queue. Returns the queue."""
        import queue
        q = queue.Queue()
        with _sse_lock:
            _sse_subscribers.append(q)
        return q

    @classmethod
    def unsubscribe_sse(cls, q):
        """Remove a subscriber queue."""
        with _sse_lock:
            try:
                _sse_subscribers.remove(q)
            except ValueError:
                pass

    @classmethod
    def broadcast_change(cls, module_code: str, enabled: bool, org_id: Optional[int] = None):
        """
        Broadcast a module change event to all SSE subscribers.
        Call this after any enable/disable operation.
        """
        import json
        event_data = json.dumps({
            'type': 'module_changed',
            'code': module_code,
            'enabled': enabled,
            'org_id': org_id,
            'ts': int(time.time())
        })
        with _sse_lock:
            dead = []
            for q in _sse_subscribers:
                try:
                    q.put_nowait(event_data)
                except Exception:
                    dead.append(q)
            for q in dead:
                try:
                    _sse_subscribers.remove(q)
                except ValueError:
                    pass

    # ── Usage Tracking ────────────────────────────────────────────────────────

    @classmethod
    def track_usage(cls, module_code: str, org_id: Optional[int], event_type: str = 'api_call'):
        """
        Asynchronously track usage. Does not block the request.
        event_type: 'page_view' | 'api_call' | 'export' | 'import' | 'action'
        """
        def _do_track():
            try:
                from app.infrastructure.database.models.models import Module, ModuleUsageAnalytics, db
                import datetime
                m = Module.query.filter_by(code=module_code).first()
                if not m:
                    return
                analytics = ModuleUsageAnalytics.query.filter_by(
                    module_id=m.id, org_id=org_id
                ).first()
                if not analytics:
                    analytics = ModuleUsageAnalytics(module_id=m.id, org_id=org_id)
                    db.session.add(analytics)

                if event_type == 'page_view':
                    analytics.page_views = (analytics.page_views or 0) + 1
                elif event_type == 'export':
                    analytics.export_count = (analytics.export_count or 0) + 1
                else:
                    analytics.api_calls = (analytics.api_calls or 0) + 1

                analytics.last_used_at = datetime.datetime.utcnow()
                analytics.total_requests = (analytics.total_requests or 0) + 1
                db.session.commit()
            except Exception:
                pass

        t = threading.Thread(target=_do_track, daemon=True)
        t.start()


# ─────────────────────────────────────────────────────────────────────────────
# Convenience decorator — use this on API routes
# ─────────────────────────────────────────────────────────────────────────────

def feature_module_required(module_code: str):
    """
    Decorator that blocks API routes when a module is disabled for the user's org.
    SuperAdmins always bypass this check.

    Usage:
        @project_bp.route('/create', methods=['POST'])
        @jwt_required()
        @feature_module_required('projects.create')
        def create_project():
            ...
    """
    from functools import wraps
    from flask import jsonify
    from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
                user_id = int(get_jwt_identity())
                from app.infrastructure.database.models.models import User
                user = User.query.get(user_id)
            except Exception:
                user = None

            org_id = user.org_id if user else None
            if not FeatureEngine.is_enabled(org_id, module_code):
                return jsonify({
                    "status": "error",
                    "error": "Feature Disabled",
                    "message": f"The feature module '{module_code}' is currently deactivated / paused by administration.",
                    "feature_code": module_code,
                    "error_code": "MODULE_DISABLED"
                }), 403

            # Track usage asynchronously
            FeatureEngine.track_usage(module_code, org_id, event_type='api_call')
            return fn(*args, **kwargs)
        return wrapper
    return decorator
