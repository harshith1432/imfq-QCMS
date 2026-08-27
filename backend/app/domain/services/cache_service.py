"""
QCMS Multi-Tier Distributed Caching Engine
==========================================
Provides structured multi-tier caching across Global Metadata, Tenant Configurations,
and Real-time Aggregates with proactive invalidation hooks.

Tier 1: Global Platform & Metadata (TTL: 300s)
  - cache:global:roles
  - cache:global:modules
  - cache:global:platform_settings

Tier 2: Tenant Configuration Caching (TTL: 120s)
  - cache:org:{org_id}:branding
  - cache:org:{org_id}:plan_limits
  - cache:org:{org_id}:custom_fields

Tier 3: Dashboard & KPI Aggregates Caching (TTL: 30s - 60s)
  - cache:org:{org_id}:kpi_summary:...
  - cache:org:{org_id}:dept_comparison
  - cache:org:{org_id}:analytics_overview
"""

import logging
from typing import Any, Optional, Callable
from app.infrastructure.cache.redis_adapter import cache

logger = logging.getLogger("QCMS.CacheService")


class CacheService:
    # TTL Configurations (in seconds)
    TIER1_GLOBAL_TTL = 300      # 5 minutes for platform settings & catalogs
    TIER2_TENANT_TTL = 120      # 2 minutes for tenant branding & limits
    TIER3_AGGREGATE_TTL = 60    # 1 minute for dashboard KPI aggregations

    # ─────────────────────────────────────────────────────────────────────────
    # Tier 1: Global Metadata & Platform Settings
    # ─────────────────────────────────────────────────────────────────────────
    @classmethod
    def get_global_platform_settings(cls, fetcher_fn: Callable[[], Any]) -> Any:
        key = "cache:global:platform_settings"
        cached = cache.get(key)
        if cached is not None:
            return cached
        val = fetcher_fn()
        if val is not None:
            cache.setex(key, cls.TIER1_GLOBAL_TTL, val)
        return val

    @classmethod
    def invalidate_global_platform_settings(cls):
        cache.delete("cache:global:platform_settings")
        logger.info("[CacheService] Invalidated global platform settings cache")

    @classmethod
    def get_global_modules(cls, fetcher_fn: Callable[[], Any]) -> Any:
        key = "cache:global:modules"
        cached = cache.get(key)
        if cached is not None:
            return cached
        val = fetcher_fn()
        if val is not None:
            cache.setex(key, cls.TIER1_GLOBAL_TTL, val)
        return val

    @classmethod
    def invalidate_global_modules(cls):
        cache.delete("cache:global:modules")
        logger.info("[CacheService] Invalidated global modules catalog cache")

    @classmethod
    def get_global_roles(cls, fetcher_fn: Callable[[], Any]) -> Any:
        key = "cache:global:roles"
        cached = cache.get(key)
        if cached is not None:
            return cached
        val = fetcher_fn()
        if val is not None:
            cache.setex(key, cls.TIER1_GLOBAL_TTL, val)
        return val

    @classmethod
    def invalidate_global_roles(cls):
        cache.delete("cache:global:roles")
        logger.info("[CacheService] Invalidated global roles cache")

    # ─────────────────────────────────────────────────────────────────────────
    # Tier 2: Tenant Configuration Caching
    # ─────────────────────────────────────────────────────────────────────────
    @classmethod
    def get_tenant_branding(cls, org_id: Optional[int], fetcher_fn: Callable[[], Any]) -> Any:
        clean_org = str(org_id) if org_id is not None else "platform"
        key = f"cache:org:{clean_org}:branding"
        cached = cache.get(key)
        if cached is not None:
            return cached
        val = fetcher_fn()
        if val is not None:
            cache.setex(key, cls.TIER2_TENANT_TTL, val)
        return val

    @classmethod
    def invalidate_tenant_branding(cls, org_id: Optional[int] = None):
        if org_id is not None:
            cache.delete(f"cache:org:{org_id}:branding")
        else:
            cache.delete("cache:org:platform:branding")
        logger.info(f"[CacheService] Invalidated branding cache for org {org_id}")

    @classmethod
    def get_tenant_plan_limits(cls, org_id: int, fetcher_fn: Callable[[], Any]) -> Any:
        key = f"cache:org:{org_id}:plan_limits"
        cached = cache.get(key)
        if cached is not None:
            return cached
        val = fetcher_fn()
        if val is not None:
            cache.setex(key, cls.TIER2_TENANT_TTL, val)
        return val

    @classmethod
    def invalidate_tenant_plan_limits(cls, org_id: int):
        cache.delete(f"cache:org:{org_id}:plan_limits")
        logger.info(f"[CacheService] Invalidated plan limits for org {org_id}")

    # ─────────────────────────────────────────────────────────────────────────
    # Tier 3: Dashboard & KPI Aggregates Caching
    # ─────────────────────────────────────────────────────────────────────────
    @classmethod
    def get_dashboard_kpi_summary(cls, org_id: int, role_name: str, dept_id: Optional[int], category: Optional[str], fetcher_fn: Callable[[], Any]) -> Any:
        key = f"cache:org:{org_id}:kpi_summary:{role_name}:{dept_id or 'all'}:{category or 'all'}"
        cached = cache.get(key)
        if cached is not None:
            return cached
        val = fetcher_fn()
        if val is not None:
            cache.setex(key, cls.TIER3_AGGREGATE_TTL, val)
        return val

    @classmethod
    def get_dept_comparison(cls, org_id: int, fetcher_fn: Callable[[], Any]) -> Any:
        key = f"cache:org:{org_id}:dept_comparison"
        cached = cache.get(key)
        if cached is not None:
            return cached
        val = fetcher_fn()
        if val is not None:
            cache.setex(key, cls.TIER3_AGGREGATE_TTL, val)
        return val

    @classmethod
    def invalidate_project_cache(cls, org_id: Optional[int]):
        """Proactively invalidates all dashboard aggregates and KPI caches for an organization."""
        if not org_id:
            return
        pattern = f"cache:org:{org_id}:*"
        if cache.is_redis and cache._redis_client:
            try:
                keys = cache._redis_client.keys(pattern)
                if keys:
                    cache._redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"[CacheService] Redis pattern invalidation notice: {e}")
        
        # Local memory fallback purge
        with cache._lock:
            keys_to_del = [k for k in cache._memory_store.keys() if k.startswith(f"cache:org:{org_id}:")]
            for k in keys_to_del:
                cache._memory_store.pop(k, None)
        logger.info(f"[CacheService] Invalidated all aggregate caches for org {org_id}")
