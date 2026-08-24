"""
QCMS Enterprise Redis & Distributed Cache Adapter
=================================================
Provides a unified interface for distributed caching, rate-limiting, login protection,
distributed locking, and idempotency tracking.

Fail-Closed Architecture:
- In PRODUCTION (ENVIRONMENT == 'production'), security-critical operations (rate limiting,
  distributed lockout, session checks, distributed locks) fail-closed if Redis is unavailable
  by raising SecurityDependencyUnavailableError (HTTP 503).
- In DEVELOPMENT / TESTING, a thread-safe in-memory cache adapter ensures zero-dependency operation.
"""

import os
import time
import json
import secrets
import threading
import logging
from typing import Any, Optional, Dict, Tuple, List
from contextlib import contextmanager

logger = logging.getLogger("QCMS.Cache")

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


class SecurityDependencyUnavailableError(Exception):
    """Raised when a security-critical cache operation fails closed in production."""
    pass


class CacheAdapter:
    def __init__(self):
        self._lock = threading.Lock()
        self._memory_store: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expiry_timestamp)
        self._sliding_windows: Dict[str, list] = {}            # key -> [timestamps]
        self._locks_held: Dict[str, str] = {}                  # lock_name -> token
        self._redis_client = None
        self._init_redis()

    @property
    def is_production(self) -> bool:
        env = os.getenv('ENVIRONMENT') or os.getenv('FLASK_ENV', 'development')
        return env.lower() == 'production'

    def _init_redis(self):
        redis_url = os.getenv('REDIS_URL') or os.getenv('REDISCLOUD_URL')
        if not redis_url:
            host = os.getenv('REDIS_HOST')
            if host:
                port = int(os.getenv('REDIS_PORT', 6379))
                password = os.getenv('REDIS_PASSWORD')
                redis_url = f"redis://{(':' + password + '@') if password else ''}{host}:{port}/0"

        if HAS_REDIS and redis_url:
            try:
                client = redis.from_url(redis_url, decode_responses=True, socket_timeout=2.0, socket_connect_timeout=2.0)
                client.ping()
                self._redis_client = client
                logger.info(f"[QCMS Cache] Connected to Redis at {redis_url.split('@')[-1] if '@' in redis_url else 'configured endpoint'}")
            except Exception as e:
                logger.warning(f"[QCMS Cache] Redis connection failed ({e}).")
                self._redis_client = None
        else:
            self._redis_client = None

    @property
    def is_redis(self) -> bool:
        return self._redis_client is not None

    def _ensure_security_available(self, operation_name: str):
        """Fail closed in production if Redis is explicitly configured/required but became unreachable."""
        require_redis = os.getenv('REQUIRE_REDIS_SECURITY', '').lower() in ('true', '1')
        has_redis_configured = bool(os.getenv('REDIS_URL') or os.getenv('REDISCLOUD_URL') or os.getenv('REDIS_HOST'))

        if (require_redis or has_redis_configured) and self.is_production and not self._redis_client:
            # Attempt a quick reconnect if client dropped
            self._init_redis()
            if not self._redis_client:
                logger.critical(f"[QCMS Security Critical] FAIL CLOSED: Redis unavailable during {operation_name} in production.")
                raise SecurityDependencyUnavailableError(
                    f"Security-critical service unavailable ({operation_name}). Distributed cache unreachable."
                )

    def get(self, key: str, is_security_critical: bool = False) -> Optional[Any]:
        if is_security_critical:
            self._ensure_security_available(f"cache_get:{key}")

        if self._redis_client:
            try:
                val = self._redis_client.get(key)
                if val is not None:
                    try:
                        return json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        return val
                return None
            except Exception as e:
                if is_security_critical and self.is_production:
                    raise SecurityDependencyUnavailableError(f"Redis get failed: {e}")

        now = time.time()
        with self._lock:
            if key in self._memory_store:
                val, exp = self._memory_store[key]
                if exp == 0 or now < exp:
                    return val
                else:
                    del self._memory_store[key]
        return None

    def set(self, key: str, value: Any, ex: Optional[int] = None, timeout: Optional[int] = None, is_security_critical: bool = False) -> bool:
        ttl = timeout if timeout is not None else (ex if ex is not None else 300)
        return self.setex(key, ttl, value, is_security_critical=is_security_critical)

    def setex(self, key: str, ttl_seconds: int, value: Any, is_security_critical: bool = False) -> bool:
        if is_security_critical:
            self._ensure_security_available(f"cache_setex:{key}")

        serialized = json.dumps(value) if not isinstance(value, (str, int, float, bool)) else str(value) if isinstance(value, (int, float, bool)) else value

        if self._redis_client:
            try:
                if ttl_seconds > 0:
                    self._redis_client.setex(key, ttl_seconds, serialized)
                else:
                    self._redis_client.set(key, serialized)
                return True
            except Exception as e:
                if is_security_critical and self.is_production:
                    raise SecurityDependencyUnavailableError(f"Redis setex failed: {e}")

        now = time.time()
        exp = (now + ttl_seconds) if ttl_seconds > 0 else 0
        with self._lock:
            self._memory_store[key] = (value, exp)
            if len(self._memory_store) > 10000:
                stale = [k for k, (_, x_exp) in self._memory_store.items() if x_exp and now > x_exp]
                for k in stale:
                    del self._memory_store[k]
        return True

    def delete(self, *keys: str, is_security_critical: bool = False) -> int:
        if not keys:
            return 0
        if is_security_critical:
            self._ensure_security_available(f"cache_delete:{keys}")

        count = 0
        if self._redis_client:
            try:
                return self._redis_client.delete(*keys)
            except Exception as e:
                if is_security_critical and self.is_production:
                    raise SecurityDependencyUnavailableError(f"Redis delete failed: {e}")

        with self._lock:
            for k in keys:
                if self._memory_store.pop(k, None) is not None:
                    count += 1
                self._sliding_windows.pop(k, None)
        return count

    def exists(self, key: str) -> bool:
        if self._redis_client:
            try:
                return bool(self._redis_client.exists(key))
            except Exception:
                pass
        return self.get(key) is not None

    def incr(self, key: str, amount: int = 1, ttl_seconds: Optional[int] = None, timeout: Optional[int] = None, is_security_critical: bool = False) -> int:
        """Atomically increments a counter and sets TTL on first creation."""
        effective_ttl = timeout if timeout is not None else ttl_seconds
        if is_security_critical:
            self._ensure_security_available(f"cache_incr:{key}")

        if self._redis_client:
            try:
                val = self._redis_client.incrby(key, amount)
                if val == amount and effective_ttl:
                    self._redis_client.expire(key, effective_ttl)
                return val
            except Exception as e:
                if is_security_critical and self.is_production:
                    raise SecurityDependencyUnavailableError(f"Redis incr failed: {e}")

        now = time.time()
        with self._lock:
            entry = self._memory_store.get(key)
            current_val = 0
            exp = (now + ttl_seconds) if ttl_seconds else 0
            if entry:
                raw_v, exp = entry
                if exp == 0 or now < exp:
                    try:
                        current_val = int(raw_v)
                    except (ValueError, TypeError):
                        current_val = 0
            new_val = current_val + amount
            self._memory_store[key] = (new_val, exp)
            return new_val

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int, is_security_critical: bool = True) -> Tuple[bool, int, int]:
        """
        Sliding-window rate limiter.
        Returns: (is_limited: bool, current_count: int, retry_after_seconds: int)
        """
        if is_security_critical:
            self._ensure_security_available(f"rate_limit:{key}")

        now = time.time()
        window_start = now - window_seconds

        if self._redis_client:
            try:
                pipe = self._redis_client.pipeline()
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zadd(key, {f"{now}:{secrets.token_hex(4)}": now})
                pipe.zcard(key)
                pipe.expire(key, window_seconds * 2)
                results = pipe.execute()
                current_count = results[2]

                if current_count > max_requests:
                    oldest = self._redis_client.zrange(key, 0, 0, withscores=True)
                    retry_after = int(window_seconds - (now - oldest[0][1])) if oldest else window_seconds
                    return True, current_count, max(1, retry_after)
                return False, current_count, 0
            except Exception as e:
                if is_security_critical and self.is_production:
                    raise SecurityDependencyUnavailableError(f"Redis rate limiter failed: {e}")

        # Thread-safe in-memory sliding window fallback
        with self._lock:
            timestamps = self._sliding_windows.get(key, [])
            timestamps = [ts for ts in timestamps if ts > window_start]
            timestamps.append(now)
            self._sliding_windows[key] = timestamps

            if len(timestamps) > max_requests:
                oldest_ts = timestamps[0]
                retry_after = int(window_seconds - (now - oldest_ts))
                return True, len(timestamps), max(1, retry_after)
            return False, len(timestamps), 0

    # ─────────────────────────────────────────────────────────────────────────
    # Distributed Locking Implementation (Item 35, 36)
    # ─────────────────────────────────────────────────────────────────────────
    def acquire_lock(self, lock_name: str, ttl_seconds: int = 60, timeout_seconds: float = 5.0, ttl: Optional[int] = None, timeout: Optional[float] = None) -> Optional[str]:
        """
        Acquires a distributed lock.
        Returns token string if acquired, None if acquisition failed.
        """
        eff_ttl = ttl if ttl is not None else ttl_seconds
        eff_timeout = timeout if timeout is not None else timeout_seconds
        token = secrets.token_hex(16)
        key = f"lock:{lock_name}"
        start_time = time.time()

        while True:
            if self._redis_client:
                try:
                    acquired = self._redis_client.set(key, token, nx=True, ex=eff_ttl)
                    if acquired:
                        self._locks_held[lock_name] = token
                        return token
                except Exception:
                    pass
            else:
                with self._lock:
                    now = time.time()
                    existing = self._memory_store.get(key)
                    if not existing or (existing[1] and now > existing[1]):
                        self._memory_store[key] = (token, now + eff_ttl)
                        self._locks_held[lock_name] = token
                        return token

            if time.time() - start_time >= eff_timeout:
                break
            time.sleep(0.05)

        return None

    def release_lock(self, lock_name: str, token: Optional[str] = None) -> bool:
        """Safely releases a distributed lock only if the token matches."""
        key = f"lock:{lock_name}"
        tok = token or self._locks_held.get(lock_name)
        if not tok:
            with self._lock:
                self._memory_store.pop(key, None)
                self._locks_held.pop(lock_name, None)
            return True

        if self._redis_client:
            try:
                lua_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                res = bool(self._redis_client.eval(lua_script, 1, key, tok))
                self._locks_held.pop(lock_name, None)
                return res
            except Exception:
                pass

        with self._lock:
            existing = self._memory_store.get(key)
            if existing and (token is None or existing[0] == tok):
                self._memory_store.pop(key, None)
                self._locks_held.pop(lock_name, None)
                return True
        return False

    @contextmanager
    def distributed_lock(self, lock_name: str, ttl_seconds: int = 60, timeout_seconds: float = 5.0, ttl: Optional[int] = None, timeout: Optional[float] = None):
        """Context manager for distributed locking."""
        eff_ttl = ttl if ttl is not None else ttl_seconds
        eff_timeout = timeout if timeout is not None else timeout_seconds
        token = self.acquire_lock(lock_name, ttl_seconds=eff_ttl, timeout_seconds=eff_timeout)
        if not token:
            raise TimeoutError(f"Could not acquire distributed lock for '{lock_name}' within {eff_timeout}s.")
        try:
            yield token
        finally:
            self.release_lock(lock_name, token)

    # ─────────────────────────────────────────────────────────────────────────
    # Multi-Tenant Key Helpers & Cache Invalidation (Items 33, 34)
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def build_org_key(org_id: Any, resource: str, identifier: str = "") -> str:
        """Generates tenant-scoped cache key: org:<org_id>:<resource>:<identifier>"""
        clean_org = str(org_id) if org_id is not None else "platform"
        if identifier:
            return f"org:{clean_org}:{resource}:{identifier}"
        return f"org:{clean_org}:{resource}"

    def invalidate_org_cache(self, org_id: Any, pattern: str = "*"):
        """Invalidates all cached keys for a specific organization matching pattern."""
        prefix = f"org:{org_id}:"
        if self._redis_client:
            try:
                keys = self._redis_client.keys(f"{prefix}{pattern}")
                if keys:
                    self._redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Error invalidating org cache for {org_id}: {e}")

        with self._lock:
            keys_to_del = [k for k in self._memory_store.keys() if k.startswith(prefix)]
            for k in keys_to_del:
                self._memory_store.pop(k, None)

    def flush(self) -> bool:
        if self._redis_client:
            try:
                self._redis_client.flushdb()
                return True
            except Exception:
                pass
        with self._lock:
            self._memory_store.clear()
            self._sliding_windows.clear()
        return True

    def info(self, section=None) -> dict:
        if self._redis_client:
            try:
                return self._redis_client.info(section)
            except Exception:
                pass
        with self._lock:
            return {
                "redis_version": "7.0-qcms-unified",
                "mode": "in_memory_fallback" if not self._redis_client else "redis_cluster",
                "total_keys": len(self._memory_store),
                "is_redis": bool(self._redis_client)
            }


# Unified Global Singleton Cache Instance
cache = CacheAdapter()
redis_client = cache
