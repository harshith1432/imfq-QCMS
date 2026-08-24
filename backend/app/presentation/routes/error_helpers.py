"""
Standardized Production Error Response Helper
============================================
Ensures zero internal database or runtime exception details leak to API clients,
while logging full exception details (with traceback and correlation request_id) server-side.
"""
import logging
from flask import jsonify, g, has_request_context

logger = logging.getLogger("QCMS")


def internal_server_error(
    e: Exception = None,
    user_message: str = "An internal server error occurred.",
    code: str = "INTERNAL_SERVER_ERROR",
    status_code: int = 500
):
    """
    Logs the exception with traceback server-side and returns a sanitized JSON response.
    
    Response format:
    {
        "status": "error",
        "message": "An internal server error occurred.",
        "msg": "An internal server error occurred.",
        "code": "INTERNAL_SERVER_ERROR",
        "request_id": "<request_id>"
    }
    """
    req_id = getattr(g, 'request_id', '-') if has_request_context() else '-'
    if e:
        logger.error(f"[{req_id}] {user_message} - Exception: {e}", exc_info=True)
    else:
        logger.error(f"[{req_id}] {user_message}")

    return jsonify({
        "status": "error",
        "message": user_message,
        "msg": user_message,
        "code": code,
        "request_id": req_id
    }), status_code
