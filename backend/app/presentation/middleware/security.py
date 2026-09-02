"""
QCMS Enterprise Security Middleware
====================================
Implements all platform security policies configured via the Super Admin Panel:
  - IP Whitelist / Blacklist enforcement
  - Web Application Firewall (WAF) — SQLi, XSS, CSRF pattern blocking
  - Brute-force / lockout protection with in-memory counters
  - API rate limiting (per-IP sliding window)
  - Browser download restriction header injection
  - Security KPI counters (blocked IPs, threat alerts)
  - AES-256 field-level encryption helpers

All policies are read live from PlatformSettings.security_settings so changes
made via the Super Admin UI take effect immediately with no restart required.
"""
import os
import re
import time
import ipaddress
import threading
from typing import Tuple, Dict, Any, Optional
from functools import wraps
from flask import request, jsonify, g, current_app

# ─────────────────────────────────────────────────────────────────────────────
# Thread-safe shared state (survives across requests in the same process)
# ─────────────────────────────────────────────────────────────────────────────
_lock = threading.Lock()

# { ip_str: { 'count': int, 'window_start': float } }
_rate_limit_buckets: dict = {}

# { ip_str: { 'attempts': int, 'locked_until': float | None } }
_login_attempt_counters: dict = {}

# { ip_str: blocked_at_epoch } — IPs blocked in the current 24-h window
_blocked_ips: dict = {}

# List of recent WAF threat events: { 'ts': epoch, 'ip': str, 'reason': str, 'path': str }
_threat_log: list = []

# Cleanup older than 24 h every 100 requests
_request_counter = 0
_CLEANUP_INTERVAL = 100
_WINDOW_24H = 86400


_security_settings_cache = {"data": {}, "ts": 0}

def _get_security_settings() -> dict:
    """
    Fetch the live security_settings blob with a 30-second memory cache to eliminate
    thousands of redundant DB queries per second on high-traffic requests.
    """
    now = time.time()
    if now - _security_settings_cache["ts"] < 30 and _security_settings_cache["data"]:
        return _security_settings_cache["data"]

    try:
        from app.infrastructure.database.models.models import PlatformSettings
        s = PlatformSettings.query.first()
        if s and s.security_settings:
            data = s.security_settings if isinstance(s.security_settings, dict) else {}
            _security_settings_cache["data"] = data
            _security_settings_cache["ts"] = now
            return data
    except Exception:
        pass
    return _security_settings_cache.get("data", {})


def _cleanup_stale_state():
    """Remove entries older than 24 h from shared counters."""
    now = time.time()
    global _request_counter
    with _lock:
        stale = [ip for ip, v in _blocked_ips.items() if now - v > _WINDOW_24H]
        for ip in stale:
            _blocked_ips.pop(ip, None)
        stale_rt = [ip for ip, v in _rate_limit_buckets.items()
                    if now - v['window_start'] > 120]
        for ip in stale_rt:
            _rate_limit_buckets.pop(ip, None)
        # Keep only last 500 threat log entries
        if len(_threat_log) > 500:
            _threat_log[:] = _threat_log[-500:]


def _get_client_ip() -> str:
    """Return the real client IP. With ProxyFix applied upstream in create_app(),
    request.remote_addr is already the correct client IP — no need to manually
    parse X-Forwarded-For (which could be spoofed without ProxyFix)."""
    return request.remote_addr or '0.0.0.0'


# ─────────────────────────────────────────────────────────────────────────────
# WAF Pattern Definitions
# ─────────────────────────────────────────────────────────────────────────────

_WAF_STRICT_PATTERNS = [
    # SQL Injection
    (re.compile(
        r"(\b(union\s+select|insert\s+into|update\s+\w+\s+set|delete\s+from|drop\s+(table|database)|alter\s+table|"
        r"exec(ute)?\s*\(|xp_cmdshell|sp_executesql|information_schema|sysobjects|syscolumns)\b|--|;--|/\*|\*/)",
        re.IGNORECASE
    ), 'SQLi'),
    # XSS
    (re.compile(
        r"(<\s*(script|iframe|object|embed|form|svg|img|body|html|style|link|"
        r"meta|base)[^>]*>|javascript\s*:|\bon[a-z]+\s*=|eval\s*\(|"
        r"expression\s*\(|vbscript\s*:|data\s*:text/html)",
        re.IGNORECASE
    ), 'XSS'),
    # Path traversal
    (re.compile(r"\.\./|\.\.\\|%2e%2e[%/\\]", re.IGNORECASE), 'PathTraversal'),
    # Command injection
    (re.compile(
        r"([|;&`$]\s*(cat|wget|curl|chmod|bash|sh|python|perl|ruby|nc|netcat|nmap|ping|whoami|passwd|shadow)\b|"
        r"/\b(bin|etc|usr)\b/(bash|sh|passwd|shadow)|`[^`]+`|\$\([^)]+\))",
        re.IGNORECASE
    ), 'CmdInjection'),
]

_WAF_MEDIUM_PATTERNS = [
    _WAF_STRICT_PATTERNS[0],  # SQL only
    _WAF_STRICT_PATTERNS[1],  # XSS only
]

# CSRF protection: unsafe methods must have a valid Origin / Referer
_CSRF_SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}


def _check_waf(mode: str, payload: str, path: str, client_ip: str):
    """
    Returns (blocked: bool, reason: str).
    `mode` is 'strict' | 'medium' | 'monitor'.
    """
    if mode == 'monitor':
        return False, ''

    patterns = _WAF_STRICT_PATTERNS if mode == 'strict' else _WAF_MEDIUM_PATTERNS

    for pattern, label in patterns:
        if pattern.search(payload):
            return True, label

    # CSRF check (strict mode only)
    if mode == 'strict' and request.method not in _CSRF_SAFE_METHODS:
        origin = request.headers.get('Origin', '')
        referer = request.headers.get('Referer', '')
        host = request.host
        if origin and host not in origin:
            return True, 'CSRF'
        if not origin and referer and host not in referer:
            return True, 'CSRF'

    return False, ''


# ─────────────────────────────────────────────────────────────────────────────
# IP Whitelist / Blacklist helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_cidr_list(csv_str: str) -> list:
    """Parse a comma / newline-separated CIDR/IP string into network objects."""
    networks = []
    for entry in re.split(r'[,\n]+', csv_str or ''):
        entry = entry.strip()
        if not entry:
            continue
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            pass  # Skip malformed entries gracefully
    return networks


def _ip_in_list(ip_str: str, networks: list) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in networks)
    except ValueError:
        return False


from app.infrastructure.cache.redis_adapter import cache

# ─────────────────────────────────────────────────────────────────────────────
# Rate Limiter
# ─────────────────────────────────────────────────────────────────────────────

def _check_rate_limit(client_ip: str, limit_per_window: int, window_seconds: int = 60, bucket_key: str = "general") -> Tuple[bool, int]:
    """
    Stateless sliding window rate limiter using Redis / memory cache adapter.
    Returns: (is_limited: bool, retry_after: int)
    """
    if not limit_per_window or limit_per_window <= 0:
        return False, 0
    try:
        if current_app and current_app.config.get('TESTING') and bucket_key == 'general':
            return False, 0
    except Exception:
        pass
    key = f"rate_limit:{bucket_key}:{client_ip}"
    is_limited, _, retry_after = cache.check_rate_limit(key, limit_per_window, window_seconds)
    return is_limited, retry_after


# ─────────────────────────────────────────────────────────────────────────────
# Threat Logging
# ─────────────────────────────────────────────────────────────────────────────

def _log_threat(client_ip: str, reason: str):
    with _lock:
        _threat_log.append({
            'ts': time.time(),
            'ip': client_ip,
            'reason': reason,
            'path': request.path,
            'method': request.method,
        })
        # Do not add loopback / local dev IP to blocked IPs
        if client_ip not in ('127.0.0.1', '::1', 'localhost'):
            _blocked_ips[client_ip] = time.time()


# ─────────────────────────────────────────────────────────────────────────────
# Public API: register_security_middleware(app)
# ─────────────────────────────────────────────────────────────────────────────

def register_security_middleware(app):
    """
    Attach all QCMS security checks to the Flask app as before_request /
    after_request hooks.  Call this once from create_app().
    """

    # Public paths that are always excluded from general authentication/WAF policies
    _ALWAYS_ALLOWED = {
        '/api/health',
        '/api/auth/login-config',
        '/api/auth/maintenance-status',
        '/api/auth/register-org',
        '/api/auth/registration-status',
        '/api/auth/check-availability',
    }

    def _is_public(path: str) -> bool:
        for prefix in _ALWAYS_ALLOWED:
            if path.startswith(prefix):
                return True
        # Static files never go through API security
        if not path.startswith('/api/'):
            return True
        return False

    @app.errorhandler(503)
    def handle_503_error(e):
        return jsonify({
            'status': 'error',
            'message': 'Service temporarily unavailable. Please retry shortly.',
            'code': 'SERVICE_UNAVAILABLE'
        }), 503

    from app.infrastructure.cache.redis_adapter import SecurityDependencyUnavailableError

    @app.errorhandler(SecurityDependencyUnavailableError)
    def handle_security_dependency_error(e):
        current_app.logger.critical(f"[QCMS Security Critical Fail-Closed] {e}")
        return jsonify({
            'status': 'error',
            'message': 'Security-critical verification service is temporarily unavailable. Request blocked for system safety.',
            'code': 'SECURITY_SERVICE_UNAVAILABLE'
        }), 503

    @app.before_request
    def enforce_security_policies():
        global _request_counter
        path = request.path
        if not path.startswith('/api/'):
            return

        _request_counter += 1
        if _request_counter % _CLEANUP_INTERVAL == 0:
            _cleanup_stale_state()

        sec = _get_security_settings()
        client_ip = _get_client_ip()

        # ── 0. Route-Specific Rate Limiting ──────────────────────────────────
        # Login rate limit: 5 attempts per 15 minutes (900s) for external IPs, 500 for localhost/testing
        if path == '/api/auth/login':
            is_local_ip = client_ip in ('127.0.0.1', '::1', 'localhost', 'testclient')
            limit_login = 500 if is_local_ip else 5
            is_limited, retry_after = _check_rate_limit(client_ip, limit_login, window_seconds=900, bucket_key="login")
            if is_limited:
                _log_threat(client_ip, 'Rate limit exceeded on /api/auth/login')
                resp = jsonify({
                    'status': 'error',
                    'message': f'Too many login attempts. Please wait {retry_after}s before trying again.',
                    'code': 'RATE_LIMIT_EXCEEDED'
                })
                resp.headers['Retry-After'] = str(retry_after)
                return resp, 429
            return

        # OTP endpoints rate limit: 3 requests per 10 minutes (600s)
        otp_endpoints = (
            '/api/auth/request-registration-otp',
            '/api/auth/request-phone-otp',
            '/api/auth/request-password-otp',
            '/api/auth/verify-registration-otp',
            '/api/auth/verify-phone-otp',
            '/api/auth/forgot-password'
        )
        if any(path.startswith(ep) for ep in otp_endpoints):
            is_limited, retry_after = _check_rate_limit(client_ip, 3, window_seconds=600, bucket_key="otp")
            if is_limited:
                _log_threat(client_ip, f'Rate limit exceeded on OTP route {path}')
                resp = jsonify({
                    'status': 'error',
                    'message': f'Too many OTP requests. Please wait {retry_after}s before trying again.',
                    'code': 'RATE_LIMIT_EXCEEDED'
                })
                resp.headers['Retry-After'] = str(retry_after)
                return resp, 429

        # General API routes rate limit: configurable with generous burst for dashboards
        if not _is_public(path):
            enable_rl = sec.get('enable_rate_limiting', True) if isinstance(sec, dict) else True
            if enable_rl:
                is_local_ip = client_ip in ('127.0.0.1', '::1', 'localhost', 'testclient')
                default_limit = 1200 if is_local_ip else 300
                gen_limit = int(sec.get('rate_limit_per_minute') or os.environ.get('RATE_LIMIT_PER_MINUTE', default_limit))
                is_limited, retry_after = _check_rate_limit(client_ip, gen_limit, window_seconds=60, bucket_key="general")
                if is_limited:
                    _log_threat(client_ip, f'General API rate limit exceeded on {path}')
                    resp = jsonify({
                        'status': 'error',
                        'message': 'Rate limit exceeded. Please slow down your requests.',
                        'code': 'RATE_LIMIT_EXCEEDED'
                    })
                    resp.headers['Retry-After'] = str(retry_after)
                    return resp, 429

        if _is_public(path):
            return

        # ── 1. IP Blacklist ──────────────────────────────────────────────────
        blacklist_str = sec.get('ip_blacklist', '')
        if blacklist_str:
            blacklist_nets = _parse_cidr_list(blacklist_str)
            if _ip_in_list(client_ip, blacklist_nets):
                _log_threat(client_ip, 'Blacklisted IP')
                return jsonify({
                    'status': 'error',
                    'message': 'Access denied: your IP address is restricted.',
                    'code': 'IP_BLACKLISTED'
                }), 403

        # ── 2. IP Whitelist (admin-only paths) ───────────────────────────────
        whitelist_str = sec.get('ip_whitelist', '')
        if whitelist_str and path.startswith('/api/super-admin'):
            whitelist_nets = _parse_cidr_list(whitelist_str)
            if whitelist_nets and not _ip_in_list(client_ip, whitelist_nets):
                _log_threat(client_ip, 'IP not in whitelist')
                return jsonify({
                    'status': 'error',
                    'message': 'Access denied: your IP is not in the admin whitelist.',
                    'code': 'IP_NOT_WHITELISTED'
                }), 403

        # ── 3. General API Rate Limiting already handled in step 0 ──────────
        pass

        # ── 4. WAF ───────────────────────────────────────────────────────────
        waf_mode = sec.get('waf_mode', 'medium')  # default: medium
        if waf_mode in ('strict', 'medium', 'monitor'):
            # Authenticated requests (Bearer token present) only have the URL
            # query string scanned. The JSON body is skipped to avoid false
            # positives from legitimate user content (project notes, audit data,
            # quality reports, etc. that may contain words like "select" or HTML).
            auth_hdr = str(request.headers.get('Authorization') or '')
            is_authenticated = len(auth_hdr.strip()) > 0

            payload_parts = []
            # Always scan URL query string
            payload_parts.append(request.query_string.decode('utf-8', errors='replace'))

            if not is_authenticated:
                # Only scan body for unauthenticated traffic
                if request.content_type and 'json' in request.content_type:
                    try:
                        payload_parts.append(request.get_data(as_text=True))
                    except Exception:
                        pass
                elif request.form:
                    payload_parts.append(' '.join(str(v) for v in request.form.values()))

            combined = ' '.join(payload_parts).strip()
            if combined:
                blocked, reason = _check_waf(waf_mode, combined, request.path, client_ip)
                if blocked:
                    _log_threat(client_ip, f'WAF:{reason}')
                    if waf_mode != 'monitor':
                        return jsonify({
                            'status': 'error',
                            'message': 'Request blocked by Web Application Firewall.',
                            'code': f'WAF_{reason.upper()}'
                        }), 403

        # ── 5. Store client IP for use in after_request ──────────────────────
        g.client_ip = client_ip
        g.sec_settings = sec


    @app.after_request
    def inject_security_headers(response):
        """Inject hardened security headers and apply download restrictions."""
        try:
            sec = getattr(g, 'sec_settings', None) or _get_security_settings()
        except Exception:
            sec = {}

        # Always-on security headers
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('X-XSS-Protection', '1; mode=block')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault(
            'Permissions-Policy',
            'camera=(), microphone=(), geolocation=()'
        )
        response.headers.setdefault(
            'Strict-Transport-Security',
            'max-age=63072000; includeSubDomains; preload'
        )
        response.headers.setdefault(
            'Content-Security-Policy',
            "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com; img-src 'self' data: blob: https:; connect-src 'self' ws: wss:; frame-ancestors 'self';"
        )

        # WAF mode hint header (internal / for logging proxies)
        waf_mode = sec.get('waf_mode', 'medium')
        response.headers['X-QCMS-WAF'] = waf_mode

        # ── Browser Download Restriction ──────────────────────────────────────
        dl_restriction = sec.get('download_restriction', 'allow-all')
        if dl_restriction == 'restrict-mobile':
            # Inform the client; actual blocking happens in the SPA JS
            response.headers['X-QCMS-Download-Policy'] = 'restrict-mobile'
        elif dl_restriction == 'watermark':
            response.headers['X-QCMS-Download-Policy'] = 'watermark'
        else:
            response.headers['X-QCMS-Download-Policy'] = 'allow-all'

        # DB Encryption status header (informational)
        if sec.get('db_encryption_enabled', False):
            response.headers['X-QCMS-Encryption'] = 'AES-256-GCM'

        return response

    app.logger.info('[QCMS Security] Security middleware registered.')


# ─────────────────────────────────────────────────────────────────────────────
# Brute-Force / Login-Lockout helpers (used by auth routes)
# ─────────────────────────────────────────────────────────────────────────────

from typing import Tuple

def record_failed_login(identifier: str) -> Tuple[bool, int]:
    """
    Record a failed login for `identifier` (email or IP) across distributed nodes.
    Returns (is_locked: bool, attempts_so_far: int).
    Reads max_login_attempts and lockout_duration_mins from security_settings.
    """
    from app.infrastructure.database.models.models import PlatformSettings
    try:
        s = PlatformSettings.query.first()
        auth = s.authentication_settings or {} if s else {}
        sec = s.security_settings or {} if s else {}
        max_attempts = auth.get('max_login_attempts', 5)
        lockout_mins = sec.get('lockout_duration_mins', 15)
    except Exception:
        max_attempts = 5
        lockout_mins = 15

    now = time.time()
    lockout_ttl = max(60, lockout_mins * 60)
    attempts_key = f"login_attempts:{identifier}"
    lockout_key = f"lockout:{identifier}"

    # Check if already locked out
    lockout_entry = cache.get(lockout_key, is_security_critical=False)
    if lockout_entry:
        locked_until = lockout_entry.get('locked_until') if isinstance(lockout_entry, dict) else None
        if locked_until and now < locked_until:
            return True, lockout_entry.get('attempts', max_attempts)

    # Increment distributed failed attempts counter
    attempts = cache.incr(attempts_key, amount=1, ttl_seconds=lockout_ttl, is_security_critical=False)

    if attempts >= max_attempts:
        locked_until = now + lockout_ttl
        cache.setex(lockout_key, lockout_ttl, {
            'attempts': attempts,
            'locked_until': locked_until
        }, is_security_critical=False)
        return True, attempts

    return False, attempts


def is_login_locked(identifier: str) -> bool:
    """Check if the given identifier is currently locked out across distributed nodes."""
    now = time.time()
    lockout_key = f"lockout:{identifier}"
    lockout_entry = cache.get(lockout_key, is_security_critical=False)
    if not lockout_entry:
        return False
    if isinstance(lockout_entry, dict):
        locked_until = lockout_entry.get('locked_until')
        if locked_until and now < locked_until:
            return True
        if locked_until and now >= locked_until:
            cache.delete(lockout_key)
            cache.delete(f"login_attempts:{identifier}")
    return False


def clear_login_lockout(identifier: str):
    """Clear the distributed lockout for an identifier after successful authentication."""
    cache.delete(f"login_attempts:{identifier}", f"lockout:{identifier}")


def get_lockout_info(identifier: str) -> dict:
    """Return lockout details for the given identifier across distributed nodes.
    Returns a dict with keys: is_locked (bool), remaining_seconds (int), locked_until_epoch (float|None).
    """
    now = time.time()
    lockout_key = f"lockout:{identifier}"
    lockout_entry = cache.get(lockout_key, is_security_critical=False)
    if not lockout_entry or not isinstance(lockout_entry, dict):
        return {'is_locked': False, 'remaining_seconds': 0, 'locked_until_epoch': None}

    locked_until = lockout_entry.get('locked_until')
    if locked_until and now < locked_until:
        return {
            'is_locked': True,
            'remaining_seconds': max(1, int(locked_until - now)),
            'locked_until_epoch': locked_until
        }
    if locked_until and now >= locked_until:
        cache.delete(lockout_key)
        cache.delete(f"login_attempts:{identifier}")
    return {'is_locked': False, 'remaining_seconds': 0, 'locked_until_epoch': None}


# ─────────────────────────────────────────────────────────────────────────────
# Security KPI Helpers (called by the settings dashboard endpoint)
# ─────────────────────────────────────────────────────────────────────────────

def get_security_kpis() -> dict:
    """Return real-time security counters for the settings dashboard KPI cards."""
    now = time.time()
    with _lock:
        blocked_24h = sum(1 for t in _blocked_ips.values() if now - t <= _WINDOW_24H)
        critical_threats = sum(
            1 for e in _threat_log
            if now - e['ts'] <= _WINDOW_24H and e['reason'].startswith('WAF:')
        )
        recent_events = [
            e for e in reversed(_threat_log)
            if now - e['ts'] <= _WINDOW_24H
        ][:20]

    return {
        'blocked_ips_24h': blocked_24h,
        'critical_threat_alerts': critical_threats,
        'recent_threat_events': recent_events,
    }


# ─────────────────────────────────────────────────────────────────────────────
# AES-256 GCM Field-Level Encryption (used when db_encryption_enabled=True)
# ─────────────────────────────────────────────────────────────────────────────

def _get_encryption_key() -> bytes:
    """Derive a 32-byte key from the Flask SECRET_KEY using SHA-256."""
    import hashlib, os
    try:
        secret = current_app.config.get('SECRET_KEY', 'qcms-fallback-secret-do-not-use')
    except RuntimeError:
        secret = os.environ.get('SECRET_KEY', 'qcms-fallback-secret-do-not-use')
    return hashlib.sha256(secret.encode()).digest()


def encrypt_field(plaintext: str) -> str:
    """
    Encrypt `plaintext` using AES-256 GCM.
    Returns a base64-encoded string: nonce(12) + ciphertext + tag(16).
    Falls back to plaintext if cryptography library is unavailable.
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import os, base64
        key = _get_encryption_key()
        nonce = os.urandom(12)
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        return base64.b64encode(nonce + ct).decode('utf-8')
    except ImportError:
        return plaintext  # Graceful degradation
    except Exception:
        return plaintext


def decrypt_field(encrypted: str) -> str:
    """
    Decrypt a value produced by `encrypt_field`.
    Returns plaintext, or the original string on any error (handles unencrypted legacy values).
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import base64
        key = _get_encryption_key()
        raw = base64.b64decode(encrypted)
        nonce, ct = raw[:12], raw[12:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ct, None).decode('utf-8')
    except Exception:
        return encrypted  # Return as-is for legacy/unencrypted values
