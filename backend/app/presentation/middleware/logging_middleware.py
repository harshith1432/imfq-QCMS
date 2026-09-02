"""
Structured JSON Logging & Request Correlation ID Middleware
============================================================
Provides unified request tracking with X-Request-ID, execution timing,
client metadata, and structured JSON formatting for Azure Monitor,
Datadog, and VPS log collectors.
"""
import uuid
import time
import json
import logging
import sys
from flask import request, g, has_request_context

logger = logging.getLogger("QCMS")


class StructuredJSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects with correlation IDs."""
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if has_request_context():
            log_obj["request_id"] = getattr(g, 'request_id', '-')
            log_obj["method"] = getattr(request, 'method', None)
            log_obj["path"] = getattr(request, 'path', None)
            log_obj["client_ip"] = request.headers.get('X-Forwarded-For', request.remote_addr)
            if hasattr(g, 'user_id'):
                log_obj["user_id"] = g.user_id
        
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj)


def get_current_request_id() -> str:
    """Returns the current request's correlation ID or '-' if outside request context."""
    if has_request_context():
        return getattr(g, 'request_id', '-')
    return '-'


def init_logging_middleware(app):
    """Attaches request correlation ID and response duration logging to the Flask app."""
    # Ensure QCMS logger has a clean handler configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        # Check if JSON logging is explicitly requested or default to structured text with JSON formatter option
        formatter = logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    @app.before_request
    def start_timer_and_request_id():
        incoming_id = request.headers.get('X-Request-ID')
        g.request_id = incoming_id if incoming_id else str(uuid.uuid4())[:8]
        g.start_time = time.time()

    @app.after_request
    def log_response(response):
        # Skip static assets or health checks if needed, or log all API endpoints
        if request.path.startswith('/static'):
            response.headers['X-Request-ID'] = getattr(g, 'request_id', '')
            return response

        duration = round((time.time() - getattr(g, 'start_time', time.time())) * 1000, 2)
        raw_req_id = str(getattr(g, 'request_id', '-'))
        safe_req_id = raw_req_id.replace('\r', '').replace('\n', '')
        safe_method = str(request.method).replace('\r', '').replace('\n', '')
        safe_path = str(request.path).replace('\r', '').replace('\n', '')
        
        # Log structured request completion
        logger.info(
            "[%s] %s %s -> %s (%sms)",
            safe_req_id,
            safe_method,
            safe_path,
            response.status_code,
            duration
        )
        
        response.headers['X-Request-ID'] = safe_req_id
        return response
