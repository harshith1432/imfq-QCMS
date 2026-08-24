"""
gunicorn.conf.py — QCMS Enterprise production server configuration
BUG-06 fix: dynamic multi-worker scaling instead of a hardcoded single worker.
"""
import multiprocessing
import os

# ── Bind ───────────────────────────────────────────────────────────────────────
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# ── Workers ───────────────────────────────────────────────────────────────────
# Formula: (2 × CPU cores) + 1  — standard Gunicorn recommendation for I/O-bound apps.
# Capped at 9 workers to prevent OOM on smaller cloud instances.
_cpu_count = multiprocessing.cpu_count()
workers = min((2 * _cpu_count) + 1, 9)

# ── Worker class & threads ────────────────────────────────────────────────────
# Use 'gthread' (multi-threaded sync) to handle concurrent requests per worker
# without requiring async frameworks.
worker_class = "gthread"
threads = 2          # threads per worker; keeps memory sane

# ── Timeouts ─────────────────────────────────────────────────────────────────
timeout = 120        # kill stuck workers after 2 minutes
graceful_timeout = 30  # allow in-flight requests 30 s to complete during reload
keepalive = 5        # HTTP keep-alive seconds

# ── Preload ───────────────────────────────────────────────────────────────────
# Preloading runs app initialisation once in the master process before forking.
# Workers inherit _DB_AUTO_MIGRATED=True, preventing N duplicate seeding runs.
preload_app = True

# ── Logging ──────────────────────────────────────────────────────────────────
loglevel = "info"
accesslog = "-"      # stdout
errorlog = "-"       # stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sus'

# ── Process naming ────────────────────────────────────────────────────────────
proc_name = "qcms-gunicorn"
