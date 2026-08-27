"""
gunicorn.conf.py — QCMS Enterprise production server configuration
Optimized for memory efficiency on cloud containers (Render, Railway, AWS, Heroku).
Prevents Out-Of-Memory (OOM) errors on 512MB RAM instances.
"""
import multiprocessing
import os

# ── Bind ───────────────────────────────────────────────────────────────────────
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# ── Workers ───────────────────────────────────────────────────────────────────
# Respect WEB_CONCURRENCY / GUNICORN_WORKERS if set by hosting platform (e.g. Render).
# Render Free/Starter has a 512MB RAM limit. 2 workers is the optimal balance:
# 2 workers × 4 threads = 8 concurrent connections using only ~120MB total memory.
env_workers = os.environ.get("WEB_CONCURRENCY") or os.environ.get("GUNICORN_WORKERS") or os.environ.get("WORKERS")
if env_workers:
    try:
        workers = max(1, min(int(env_workers), 3))
    except ValueError:
        workers = 2
else:
    # Auto-calculate safely: max 2 workers to strictly prevent OOM on 512MB instances
    workers = min(max(1, multiprocessing.cpu_count()), 2)

# ── Worker class & threads ────────────────────────────────────────────────────
# Use 'gthread' (multi-threaded sync) to handle concurrent requests per worker
# without spawning multiple heavy Python processes.
worker_class = "gthread"
threads = int(os.environ.get("GUNICORN_THREADS", "4"))

# ── Memory Leak Prevention & Worker Recycling ─────────────────────────────────
# Automatically recycle workers after N requests to release Python memory fragmentation.
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", "100"))

# ── Timeouts ─────────────────────────────────────────────────────────────────
timeout = 120          # kill stuck workers after 2 minutes
graceful_timeout = 30  # allow in-flight requests 30 s to complete during reload
keepalive = 5          # HTTP keep-alive seconds

# ── Preload ───────────────────────────────────────────────────────────────────
# Preloading runs app initialisation once in the master process before forking.
# Workers share copy-on-write memory, saving ~40% RAM and preventing duplicate migrations.
preload_app = True

# ── Logging ──────────────────────────────────────────────────────────────────
loglevel = os.environ.get("LOG_LEVEL", "info").lower()
accesslog = "-"        # stdout
errorlog = "-"         # stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sus'

# ── Process naming ────────────────────────────────────────────────────────────
proc_name = "qcms-gunicorn"
