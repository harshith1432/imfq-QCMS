import pytest
import json
import uuid
import time
from app import db
from app.infrastructure.database.models import User, Role, Organization, Project
from app.infrastructure.database.models.workflow import Stage1ProblemDefinitionProjectInitiation
from app.infrastructure.cache.redis_adapter import cache, SecurityDependencyUnavailableError
from app.domain.services.stage_validation_engine import StageValidationEngine
from app.domain.services.tenant_context import require_permission, ROLE_PERMISSIONS
from app.domain.services.idempotency_service import IdempotencyService


def test_redis_cache_and_atomic_counters(app):
    """Verify atomic incr, ttl, and distributed lock capabilities."""
    with app.app_context():
        test_key = f"test_counter_{uuid.uuid4().hex}"
        count1 = cache.incr(test_key, amount=1, timeout=60)
        assert count1 == 1
        count2 = cache.incr(test_key, amount=1, timeout=60)
        assert count2 == 2

        # Test distributed lock
        lock_key = f"test_lock_{uuid.uuid4().hex}"
        with cache.distributed_lock(lock_key, ttl=5):
            # Inner lock on same key should fail to acquire with immediate timeout
            acquired = cache.acquire_lock(lock_key, ttl=5, timeout=0.1)
            assert acquired is None
        
        # After exit, lock should be released
        acquired_after = cache.acquire_lock(lock_key, ttl=5, timeout=0.1)
        assert acquired_after is not None
        cache.release_lock(lock_key, acquired_after)


def test_idempotency_payload_hash_validation(app):
    """Verify IdempotencyService returns cached response for identical payload and rejects modified payload with 422."""
    with app.app_context():
        idem_key = f"idem_test_{uuid.uuid4().hex}"
        payload_a = {"amount": 500, "currency": "INR"}
        payload_b = {"amount": 999, "currency": "USD"}
        resp_data = {"status": "success", "transaction_id": "tx_123"}

        # Store response
        saved = IdempotencyService.set(idem_key, resp_data, status_code=200, payload=payload_a)
        assert saved is True

        # Fetch with identical payload
        cached, status_code = IdempotencyService.get(idem_key, payload=payload_a)
        assert cached is not None
        assert status_code == 200
        assert cached.get("transaction_id") == "tx_123"

        # Fetch with altered payload -> payload mismatch detection (returns None, 422)
        cached_mismatch, status_code_mismatch = IdempotencyService.get(idem_key, payload=payload_b)
        assert cached_mismatch is None
        assert status_code_mismatch == 422


def test_stage_validation_engine_sequential_enforcement(app):
    """Verify StageValidationEngine enforces strictly sequential stage advancement and blocks skipping."""
    with app.app_context():
        class MockProject:
            id = 999999
            current_stage = 1
            status = 'In Progress'

        proj = MockProject()

        # Cannot skip Stage 2 directly to Stage 3
        is_allowed, err_msg, status_code = StageValidationEngine.validate_transition(proj, target_stage=3)
        assert is_allowed is False
        assert status_code == 400
        assert "sequential" in err_msg.lower() or "skip" in err_msg.lower()

        # Cannot advance backwards or to same stage
        is_allowed_back, _, status_code_back = StageValidationEngine.validate_transition(proj, target_stage=1)
        assert is_allowed_back is False
        assert status_code_back == 400


def test_role_permissions_engine_mapping():
    """Verify RBAC role capability mappings exist and grant appropriate rights."""
    assert 'projects.create' in ROLE_PERMISSIONS['Admin']
    assert 'projects.create' in ROLE_PERMISSIONS['Team Leader']
    assert 'projects.create' not in ROLE_PERMISSIONS['Reviewer']
    assert 'billing.manage' in ROLE_PERMISSIONS['Admin']
    assert 'billing.manage' not in ROLE_PERMISSIONS['Team Member']


def test_file_path_traversal_protection(client, auth_context):
    """Verify serve_uploads rejects directory traversal attempts."""
    resp = client.get('/uploads/../../etc/passwd', headers=auth_context['headers'])
    assert resp.status_code in (400, 404)
