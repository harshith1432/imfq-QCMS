"""
QCMS Idempotency Domain Service
Wraps RedisIdempotency to support both programmatic and middleware-level idempotency operations.
"""

import hashlib
import json
from typing import Tuple, Optional, Any, Dict
from app.infrastructure.cache.redis_adapter import cache

IDEMPOTENCY_DEFAULT_TTL = 3600  # 1 hour


class IdempotencyService:
    """Domain service for checking and storing idempotent execution results."""

    @staticmethod
    def compute_hash(payload: Any) -> str:
        if isinstance(payload, dict):
            raw = json.dumps(payload, sort_keys=True)
        elif isinstance(payload, bytes):
            raw = payload.decode('utf-8', errors='ignore')
        else:
            raw = str(payload)
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    @classmethod
    def get(cls, key: str, payload: Any = None) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
        """Retrieve cached idempotent result if payload hash matches.
        
        Returns:
            (cached_data, status_code) or (None, 422) on payload mismatch.
        """
        record = cache.get(key)
        if not record:
            return None, None

        if isinstance(record, str):
            try:
                record = json.loads(record)
            except Exception:
                return None, None

        if payload is not None:
            expected_hash = cls.compute_hash(payload)
            actual_hash = record.get('payload_hash')
            if actual_hash and actual_hash != expected_hash:
                return None, 422

        if record.get('status') == 'COMPLETED':
            return record.get('data'), record.get('status_code', 200)

        return None, None

    @classmethod
    def set(cls, key: str, data: Any, status_code: int = 200, payload: Any = None, ttl: int = IDEMPOTENCY_DEFAULT_TTL) -> bool:
        """Store completed idempotent execution result."""
        payload_hash = cls.compute_hash(payload) if payload is not None else None
        record = {
            'status': 'COMPLETED',
            'payload_hash': payload_hash,
            'status_code': status_code,
            'data': data
        }
        return cache.set(key, record, timeout=ttl)
