"""
gunicorn.conf.py — QCMS Enterprise Production Server Configuration
Optimized for high-concurrency request throughput, process/thread balance,
and memory stability on container platforms (Render, Railway, AWS, Heroku, Kubernetes).
"""
import multiprocessing
import os

# ── Bind Address ─────────────────────────────────────────────────────────────
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# ── Worker & Thread Architecture ─────────────────────────────────────────────
# Use 'gthread' for lightweight, asynchronous thread-based I/O concurrency
worker_class = "gthread"

# Dynamic worker sizing: 2 to 4 workers based on CPU core availability
# allowing 8–16 simultaneous requests across workers with minimal memory overhead
workers = int(os.environ.get("GUNICORN_WORKERS", os.environ.get("WEB_CONCURRENCY", max(2, min(multiprocessing.cpu_count() * 2, 4)))))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))

# ── Memory & Lifecycle Management ────────────────────────────────────────────
# Preload application once in master process before forking workers
# Shares copy-on-write memory, reducing RAM footprint by ~40%
preload_app = True

# Automatically recycle workers after N requests to prevent memory fragmentation
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", "100"))

# ── Timeouts & Connection Keep-Alive ──────────────────────────────────────────
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "60"))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))

# ── Logging ──────────────────────────────────────────────────────────────────
loglevel = os.environ.get("LOG_LEVEL", "info").lower()
accesslog = "-"        # stdout
errorlog = "-"         # stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sus'

# ── Process Naming ───────────────────────────────────────────────────────────
proc_name = "qcms-gunicorn"
