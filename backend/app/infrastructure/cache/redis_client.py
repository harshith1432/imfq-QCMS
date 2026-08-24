"""
QCMS Enterprise Unified Redis Client Re-export
===============================================
Redirects all cache operations to the unified CacheAdapter in redis_adapter.py.
Maintains 100% backward compatibility for all legacy imports.
"""

from app.infrastructure.cache.redis_adapter import (
    cache,
    redis_client,
    CacheAdapter,
    SecurityDependencyUnavailableError
)

__all__ = ['cache', 'redis_client', 'CacheAdapter', 'SecurityDependencyUnavailableError']
