import hashlib
import time
import threading
from typing import Dict, Any, Tuple, Optional

class IdempotencyService:
    """
    Thread-safe Idempotency Store for Backend Write Operations.
    Prevents duplicate database mutations, notifications, and transactions
    if duplicate HTTP requests arrive concurrently or rapidly.
    """

    _lock = threading.Lock()
    # Cache format: key -> { status: 'PROCESSING'|'COMPLETED', status_code: int, data: dict, created_at: float }
    _cache: Dict[str, Dict[str, Any]] = {}
    TTL_SECONDS = 60 # 60 second window for idempotency deduplication

    @classmethod
    def generate_key(cls, user_id: Any, org_id: Any, method: str, path: str, raw_body: bytes) -> str:
        """Computes a SHA-256 fingerprint for the request."""
        hasher = hashlib.sha256()
        hasher.update(str(user_id or '').encode('utf-8'))
        hasher.update(str(org_id or '').encode('utf-8'))
        hasher.update(method.upper().encode('utf-8'))
        hasher.update(path.encode('utf-8'))
        if raw_body:
            hasher.update(raw_body)
        return hasher.hexdigest()

    @classmethod
    def check_and_lock(cls, key: str) -> Tuple[str, Optional[Tuple[Dict[str, Any], int]]]:
        """
        Atomically checks request status.
        Returns:
            ('NEW', None) -> First execution, proceed.
            ('PROCESSING', None) -> Identical request currently processing, block duplicate.
            ('COMPLETED', (data, status_code)) -> Completed request, return cached response.
        """
        now = time.time()

        with cls._lock:
            # Clean expired keys
            cls._cleanup(now)

            record = cls._cache.get(key)
            if not record:
                # Register new processing lock
                cls._cache[key] = {
                    'status': 'PROCESSING',
                    'status_code': None,
                    'data': None,
                    'created_at': now
                }
                return 'NEW', None

            if record['status'] == 'PROCESSING':
                return 'PROCESSING', None

            if record['status'] == 'COMPLETED':
                return 'COMPLETED', (record['data'], record['status_code'])

            return 'NEW', None

    @classmethod
    def complete(cls, key: str, data: Any, status_code: int = 200):
        """Stores the response of a completed idempotent request."""
        with cls._lock:
            if key in cls._cache:
                cls._cache[key]['status'] = 'COMPLETED'
                cls._cache[key]['data'] = data
                cls._cache[key]['status_code'] = status_code

    @classmethod
    def release(cls, key: str):
        """Releases lock upon error/rollback so user can retry."""
        with cls._lock:
            if key in cls._cache:
                del cls._cache[key]

    @classmethod
    def _cleanup(cls, now: float):
        """Removes entries older than TTL."""
        expired = [k for k, v in cls._cache.items() if now - v['created_at'] > cls.TTL_SECONDS]
        for k in expired:
            del cls._cache[k]
