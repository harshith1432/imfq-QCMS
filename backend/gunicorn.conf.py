import os

# Bind to the PORT env var Render provides
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Single worker - avoids per-worker migration re-runs
# Render's free tier only has 1 CPU anyway
workers = 1

# Worker timeout: 300 seconds to allow the first-boot DB migration
# (100+ ALTER TABLE statements against Neon) to complete without killing the worker
timeout = 300

# Keepalive for persistent connections
keepalive = 5

# Worker class - sync is fine for this workload
worker_class = "sync"

# Preload the app in the master process BEFORE forking workers.
# With preload_app=True, run.py's module-level `_preloaded_app = get_app()`
# executes once, sets _DB_AUTO_MIGRATED=True, and workers inherit that state.
preload_app = True

# Log level
loglevel = "info"

# Access log to stdout
accesslog = "-"
errorlog = "-"
