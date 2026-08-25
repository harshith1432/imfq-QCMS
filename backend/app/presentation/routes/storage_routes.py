# QCMS Enterprise Storage & Signed URL Download Routes
import os
import mimetypes
import logging
from flask import Blueprint, request, jsonify, Response, redirect, send_from_directory, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.infrastructure.database.models.models import User
from app.infrastructure.storage import storage
from app.domain.services.file_access_service import verify_file_access_authorization, sanitize_file_path

logger = logging.getLogger("QCMS.Storage.Routes")
storage_bp = Blueprint('storage_bp', __name__)

@storage_bp.route('/signed-url', methods=['POST', 'GET'])
@jwt_required()
def get_signed_download_url():
    """
    Generates a secure, 15-minute time-limited signed URL (Azure SAS or Supabase signed URL)
    only after verifying: user + organization + resource + permission + file ownership.
    """
    try:
        user_id = get_jwt_identity()
        if isinstance(user_id, dict):
            user_id = user_id.get('id') or user_id.get('user_id')
        user = db.session.get(User, int(user_id)) if user_id else None
    except Exception:
        return jsonify({"status": "error", "message": "Invalid authentication token.", "code": "UNAUTHORIZED"}), 401

    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        file_path = payload.get('file_path') or payload.get('path') or payload.get('filename')
        resource_type = payload.get('resource_type')
        resource_id = payload.get('resource_id')
    else:
        file_path = request.args.get('file_path') or request.args.get('path') or request.args.get('filename')
        resource_type = request.args.get('resource_type')
        resource_id = request.args.get('resource_id')
        if resource_id:
            try:
                resource_id = int(resource_id)
            except Exception:
                resource_id = None

    if not file_path:
        return jsonify({"status": "error", "message": "file_path parameter is required.", "code": "BAD_REQUEST"}), 400

    clean_path = sanitize_file_path(file_path)
    if not clean_path:
        return jsonify({"status": "error", "message": "Invalid or unsafe file path.", "code": "BAD_REQUEST"}), 400

    # Execute 5-Factor Verification Matrix
    is_authorized, reason, status_code = verify_file_access_authorization(
        user=user,
        file_path=clean_path,
        resource_type=resource_type,
        resource_id=resource_id
    )

    if not is_authorized:
        return jsonify({
            "status": "error",
            "message": reason,
            "code": "ACCESS_DENIED",
            "file_path": clean_path
        }), status_code

    # Check if file exists in active storage backend
    if not storage.exists(clean_path):
        return jsonify({"status": "error", "message": "File not found in storage.", "code": "NOT_FOUND"}), 404

    # If backend is Azure Blob or Supabase Storage, generate 15-minute signed URL
    if storage.backend in ('azure', 'supabase'):
        signed_url = storage.generate_signed_url(clean_path, expiry_minutes=15)
        if signed_url:
            return jsonify({
                "status": "success",
                "backend": storage.backend,
                "signed_url": signed_url,
                "expires_in_seconds": 900,
                "file_path": clean_path,
                "auth_status": reason
            }), 200

    # Local Disk Fallback / Development URL
    return jsonify({
        "status": "success",
        "backend": storage.backend,
        "download_url": f"/api/storage/download/{clean_path}",
        "file_path": clean_path,
        "auth_status": reason
    }), 200


@storage_bp.route('/download/<path:file_path>', methods=['GET'])
@jwt_required()
def secure_download_file(file_path):
    """
    Enforces 5-factor authorization and either redirects to signed access URL or streams file bytes.
    """
    try:
        user_id = get_jwt_identity()
        if isinstance(user_id, dict):
            user_id = user_id.get('id') or user_id.get('user_id')
        user = db.session.get(User, int(user_id)) if user_id else None
    except Exception:
        return jsonify({"status": "error", "message": "Authentication required.", "code": "UNAUTHORIZED"}), 401

    clean_path = sanitize_file_path(file_path)
    if not clean_path:
        return jsonify({"status": "error", "message": "Invalid file path.", "code": "BAD_REQUEST"}), 400

    is_authorized, reason, status_code = verify_file_access_authorization(user, clean_path)
    if not is_authorized:
        return jsonify({"status": "error", "message": reason, "code": "FORBIDDEN"}), status_code

    if storage.backend in ('azure', 'supabase'):
        signed_url = storage.generate_signed_url(clean_path, expiry_minutes=15)
        if signed_url:
            return redirect(signed_url, code=302)

    content_bytes, content_type = storage.get_file_bytes(clean_path)
    if content_bytes is None:
        return jsonify({"status": "error", "message": "File not found.", "code": "NOT_FOUND"}), 404

    resp = Response(content_bytes, mimetype=content_type or 'application/octet-stream')
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
    filename = os.path.basename(clean_path)
    resp.headers['Content-Disposition'] = f'inline; filename="{filename}"'
    return resp


@storage_bp.route('/<path:file_path>', methods=['DELETE'])
@jwt_required()
def secure_delete_file(file_path):
    """
    Enforces 5-factor authorization and deletes file from the active storage backend.
    """
    try:
        user_id = get_jwt_identity()
        if isinstance(user_id, dict):
            user_id = user_id.get('id') or user_id.get('user_id')
        user = db.session.get(User, int(user_id)) if user_id else None
    except Exception:
        return jsonify({"status": "error", "message": "Authentication required.", "code": "UNAUTHORIZED"}), 401

    clean_path = sanitize_file_path(file_path)
    if not clean_path:
        return jsonify({"status": "error", "message": "Invalid file path.", "code": "BAD_REQUEST"}), 400

    # User must have write/delete permissions for the resource
    is_authorized, reason, status_code = verify_file_access_authorization(user, clean_path)
    if not is_authorized:
        return jsonify({"status": "error", "message": reason, "code": "FORBIDDEN"}), status_code

    # If file does not exist, return 404 gracefully
    if not storage.exists(clean_path):
        return jsonify({"status": "error", "message": "File not found in storage.", "code": "NOT_FOUND"}), 404

    try:
        deleted = storage.delete_file(clean_path)
        if deleted:
            logger.info(f"[StorageRoutes] User #{user.id} deleted file: {clean_path}")
            return jsonify({
                "status": "success",
                "message": "File deleted successfully from storage.",
                "file_path": clean_path,
                "backend": storage.backend
            }), 200
        else:
            return jsonify({"status": "error", "message": "Could not delete file from storage backend.", "code": "DELETE_FAILED"}), 500
    except Exception as e:
        logger.error(f"[StorageRoutes] Error deleting file {clean_path}: {e}")
        return jsonify({"status": "error", "message": "Internal storage deletion error.", "code": "INTERNAL_ERROR"}), 500


@storage_bp.route('/info', methods=['GET'])
@jwt_required()
def get_storage_info():
    """Returns active storage backend metadata (sanitized, no secrets)."""
    return jsonify(storage.get_info()), 200
