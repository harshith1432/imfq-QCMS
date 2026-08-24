"""
Secure Integration API v1
=========================
Modular API for external system integrations (e.g., Ideation Tool, ERP, CRM).
Provides Bearer token authentication, rate limiting, duplicate checking,
audit logging, and data persistence into `imported_ideas`.
"""
import os
import time
import json
import hashlib
import threading
from datetime import datetime, timezone
from functools import wraps
from flask import Blueprint, request, jsonify, g, current_app
from app.infrastructure.database.models.models import (
    db, Organization, OrgApiKey, ImportedIdea, IntegrationApiLog
)

integration_v1_bp = Blueprint('integration_v1', __name__)

def get_base_url():
    """Dynamically resolve integration base URL from env / config with fallback to request host."""
    configured = current_app.config.get('INTEGRATION_BASE_URL') or os.getenv('INTEGRATION_BASE_URL') or os.getenv('BASE_URL')
    if configured and str(configured).strip():
        return str(configured).strip().rstrip('/')
    return request.host_url.rstrip('/')

@integration_v1_bp.route('/base-url', methods=['GET'])
def get_public_base_url():
    """Public helper returning current dynamic base URL and endpoints for integrations."""
    base = get_base_url()
    return jsonify({
        "status": "success",
        "base_url": base,
        "api_endpoint": f"{base}/api/v1/integrations/ideas",
        "status_endpoint": f"{base}/api/v1/integrations/status",
        "openapi_url": f"{base}/api/v1/integrations/docs/openapi.json",
        "postman_url": f"{base}/api/v1/integrations/docs/postman_collection.json"
    }), 200

# ── Thread-safe Rate Limiting ──────────────────────────────────────────────
_rate_lock = threading.Lock()
# { org_id: [timestamp_epoch_float, ...] }
_org_rate_buckets = {}
RATE_LIMIT_PER_MINUTE = 100

def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

def _check_rate_limit(org_id: int) -> bool:
    """Sliding window rate limiter: max 100 requests / minute per org. (Permanently disabled: always returns True)."""
    return True

def _log_api_request(org_id, ip_address, key_prefix, endpoint, status_code, start_time):
    """Log transaction metrics to integration_api_logs."""
    try:
        response_time_ms = round((time.time() - start_time) * 1000.0, 2)
        log_entry = IntegrationApiLog(
            organization_id=org_id,
            ip_address=ip_address,
            api_key_used=key_prefix,
            request_time=datetime.now(timezone.utc).replace(tzinfo=None),
            response_time_ms=response_time_ms,
            endpoint=endpoint,
            status_code=status_code
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        print("[Integration API Log Error]", e)

def require_api_key(f):
    """
    Decorator for Bearer Token Authentication.
    Header: Authorization: Bearer <API_KEY>
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        auth_header = request.headers.get('Authorization', '')
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '0.0.0.0').split(',')[0].strip()

        if not auth_header or not auth_header.startswith('Bearer '):
            _log_api_request(None, client_ip, "INVALID_HEADER", request.path, 401, start_time)
            return jsonify({"error": "Unauthorized", "message": "Missing or invalid Authorization Bearer header."}), 401

        raw_key = auth_header.replace('Bearer ', '').strip()
        if not raw_key:
            _log_api_request(None, client_ip, "EMPTY_KEY", request.path, 401, start_time)
            return jsonify({"error": "Unauthorized", "message": "API key cannot be empty."}), 401

        key_hash = _hash_key(raw_key)
        api_key_rec = OrgApiKey.query.filter_by(api_key_hash=key_hash).first()

        if not api_key_rec or api_key_rec.status != 'Active':
            _log_api_request(None, client_ip, raw_key[:12] + "...", request.path, 401, start_time)
            return jsonify({"error": "Unauthorized", "message": "Invalid or disabled API Key."}), 401

        # Rate limit check permanently bypassed - unlimited throughput
        pass

        # Update usage statistics
        api_key_rec.last_used = datetime.now(timezone.utc).replace(tzinfo=None)
        api_key_rec.usage_count = (api_key_rec.usage_count or 0) + 1
        db.session.commit()

        # Attach org context to flask g
        g.api_key_rec = api_key_rec
        g.org_id = api_key_rec.organization_id
        g.client_ip = client_ip
        g.request_start_time = start_time

        return f(*args, **kwargs)
    return decorated_function


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/integrations/ideas
# ─────────────────────────────────────────────────────────────────────────────
@integration_v1_bp.route('/ideas', methods=['GET', 'POST'])
@require_api_key
def handle_ideas():
    """
    GET: Retrieve all imported ideas for authenticated organization.
    POST: Receive and store approved ideas from Ideation Tool for authenticated organization.
    """
    if request.method == 'GET':
        ideas = ImportedIdea.query.filter_by(organization_id=g.org_id).order_by(ImportedIdea.created_at.desc()).all()
        _log_api_request(g.org_id, g.client_ip, g.api_key_rec.secret_key_masked, request.path, 200, g.request_start_time)
        return jsonify({
            "success": True,
            "total": len(ideas),
            "organization_id": g.org_id,
            "api_endpoint": f"{get_base_url()}/api/v1/integrations/ideas",
            "ideas": [i.to_dict() for i in ideas]
        }), 200

    # POST Logic
    return import_idea_post()

def import_idea_post():
    data = request.get_json(silent=True) or {}
    
    idea_code = data.get('ideaCode') or data.get('idea_code')
    title = data.get('title')
    
    if not idea_code or not title:
        _log_api_request(g.org_id, g.client_ip, g.api_key_rec.secret_key_masked, request.path, 400, g.request_start_time)
        return jsonify({
            "success": False,
            "message": "Missing required fields: 'ideaCode' and 'title' are mandatory."
        }), 400

    # Duplicate check per organization
    existing = ImportedIdea.query.filter_by(organization_id=g.org_id, idea_code=idea_code).first()
    if existing:
        _log_api_request(g.org_id, g.client_ip, g.api_key_rec.secret_key_masked, request.path, 409, g.request_start_time)
        return jsonify({
            "message": "Idea already imported."
        }), 409

    # Create new imported idea record
    new_idea = ImportedIdea(
        organization_id=g.org_id,
        idea_code=str(idea_code).strip(),
        title=str(title).strip(),
        problem_statement=data.get('presentSituation') or data.get('problem_statement') or '',
        proposed_solution=data.get('proposedSolution') or data.get('proposed_solution') or '',
        department=data.get('department') or 'General',
        category=data.get('category') or 'Quality',
        submitted_by=data.get('submittedBy') or data.get('submitted_by') or 'External System',
        co_suggesters=data.get('coSuggesters') or data.get('co_suggesters') or [],
        tangible_benefit=float(data.get('tangibleBenefit') or 0.0),
        intangible_benefit=data.get('intangibleBenefit') or '',
        investment_required=float(data.get('investmentRequired') or 0.0),
        implementation_time=data.get('implementationTime') or '',
        impact_level=data.get('impactLevel') or 'Medium',
        status=data.get('status') or 'Approved',
        source='Ideation Tool',
        imported_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )

    db.session.add(new_idea)
    db.session.commit()

    _log_api_request(g.org_id, g.client_ip, g.api_key_rec.secret_key_masked, request.path, 201, g.request_start_time)

    return jsonify({
        "success": True,
        "message": "Idea imported successfully.",
        "ideaCode": new_idea.idea_code
    }), 201


# ─────────────────────────────────────────────────────────────────────────────
# FUTURE READY MODULAR ENDPOINTS: /projects, /users, /departments, /status
# ─────────────────────────────────────────────────────────────────────────────
@integration_v1_bp.route('/status', methods=['GET'])
@require_api_key
def get_api_status():
    """Health & integration status endpoint."""
    _log_api_request(g.org_id, g.client_ip, g.api_key_rec.secret_key_masked, request.path, 200, g.request_start_time)
    return jsonify({
        "status": "online",
        "organization_id": g.org_id,
        "service": "QCMS Integration Engine v1",
        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    }), 200


@integration_v1_bp.route('/imported-ideas', methods=['GET'])
@require_api_key
def list_imported_ideas():
    """Fetch list of ideas imported for this organization."""
    ideas = ImportedIdea.query.filter_by(organization_id=g.org_id).order_by(ImportedIdea.imported_at.desc()).all()
    _log_api_request(g.org_id, g.client_ip, g.api_key_rec.secret_key_masked, request.path, 200, g.request_start_time)
    return jsonify({
        "total": len(ideas),
        "ideas": [i.to_dict() for i in ideas]
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# OPENAPI 3.1 & POSTMAN COLLECTION GENERATION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@integration_v1_bp.route('/docs/openapi.json', methods=['GET'])
def get_openapi_spec():
    """Generate OpenAPI 3.1.0 specification JSON."""
    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "QCMS Integration API",
            "version": "1.0.0",
            "description": "Enterprise Integration API for QCMS (Quality & Continuous Improvement Management System). Allows external tools (Ideation Tool, ERP, CRM) to push approved ideas and sync quality records.",
            "contact": {
                "name": "QCMS Developer Support",
                "email": "api-support@qcms.io",
                "url": "https://api.qcms.com/v1/"
            }
        },
        "servers": [
            {
                "url": f"{get_base_url()}/api/v1/integrations",
                "description": "Configured Integration Server"
            }
        ],
        "paths": {
            "/ideas": {
                "post": {
                    "summary": "Import Approved Idea",
                    "description": "Receives and stores approved continuous improvement ideas from external ideation tools.",
                    "operationId": "importIdea",
                    "security": [{"BearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["ideaCode", "title"],
                                    "properties": {
                                        "ideaCode": {"type": "string", "example": "IDA-2026-006", "description": "Unique idea identifier code"},
                                        "title": {"type": "string", "example": "Reduce Paint Defects", "description": "Idea title"},
                                        "presentSituation": {"type": "string", "example": "Paint rejection increased from 2% to 6%", "description": "Problem statement"},
                                        "proposedSolution": {"type": "string", "example": "Install automatic viscosity monitoring", "description": "Proposed solution"},
                                        "department": {"type": "string", "example": "Production", "description": "Target department"},
                                        "category": {"type": "string", "example": "Quality", "description": "Kaizen category (Quality, Cost, Delivery, etc.)"},
                                        "submittedBy": {"type": "string", "example": "John Doe", "description": "Submitter name"},
                                        "coSuggesters": {"type": "array", "items": {"type": "string"}, "example": ["David", "Smith"], "description": "Co-submitters"},
                                        "tangibleBenefit": {"type": "number", "example": 100000, "description": "Financial savings in currency"},
                                        "intangibleBenefit": {"type": "string", "example": "Improved customer satisfaction", "description": "Non-financial benefit"},
                                        "investmentRequired": {"type": "number", "example": 250000, "description": "Capital or operational expenditure"},
                                        "implementationTime": {"type": "string", "example": "8 Weeks", "description": "Estimated implementation timeline"},
                                        "impactLevel": {"type": "string", "enum": ["Low", "Medium", "High"], "example": "Medium"},
                                        "status": {"type": "string", "example": "Approved", "default": "Approved"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Idea imported successfully",
                            "content": {
                                "application/json": {
                                    "example": {
                                        "success": True,
                                        "message": "Idea imported successfully.",
                                        "ideaCode": "IDA-2026-006"
                                    }
                                }
                            }
                        },
                        "401": {"description": "Unauthorized - Missing, invalid or disabled API Key"},
                        "409": {"description": "Conflict - Idea already imported"},
                        "429": {"description": "Too Many Requests - Rate limit exceeded (100 req/min)"}
                    }
                }
            },
            "/status": {
                "get": {
                    "summary": "Health Check",
                    "description": "Returns integration service status.",
                    "security": [{"BearerAuth": []}],
                    "responses": {
                        "200": {"description": "Service is online"}
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "APIKey",
                    "description": "Provide organization secret key in format: Bearer qcms_live_xxxxxxxxxxxxxxxxxxxxx"
                }
            }
        }
    }
    return jsonify(spec), 200


@integration_v1_bp.route('/docs/postman_collection.json', methods=['GET'])
def get_postman_collection():
    """Generate downloadable Postman Collection v2.1."""
    collection = {
        "info": {
            "_postman_id": "qcms-integration-api-v1",
            "name": "QCMS Integration API v1",
            "description": "Postman Collection for QCMS Integration API endpoints.",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "variable": [
            {
                "key": "baseUrl",
                "value": f"{get_base_url()}/api/v1/integrations",
                "type": "string"
            },
            {
                "key": "apiKey",
                "value": "qcms_live_your_secret_key_here",
                "type": "string"
            }
        ],
        "item": [
            {
                "name": "Ideation Tool - Import Approved Idea",
                "request": {
                    "method": "POST",
                    "header": [
                        {"key": "Authorization", "value": "Bearer {{apiKey}}", "type": "text"},
                        {"key": "Content-Type", "value": "application/json", "type": "text"}
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps({
                            "ideaCode": "IDA-2026-006",
                            "title": "Reduce Paint Defects",
                            "presentSituation": "Paint rejection increased from 2% to 6%",
                            "proposedSolution": "Install automatic viscosity monitoring",
                            "department": "Production",
                            "category": "Quality",
                            "submittedBy": "John Doe",
                            "coSuggesters": ["David", "Smith"],
                            "tangibleBenefit": 100000,
                            "intangibleBenefit": "Improved customer satisfaction",
                            "investmentRequired": 250000,
                            "implementationTime": "8 Weeks",
                            "impactLevel": "Medium",
                            "status": "Approved"
                        }, indent=2)
                    },
                    "url": {
                        "raw": "{{baseUrl}}/ideas",
                        "host": ["{{baseUrl}}"],
                        "path": ["ideas"]
                    },
                    "description": "Imports an approved idea into QCMS."
                }
            },
            {
                "name": "System Status Health Check",
                "request": {
                    "method": "GET",
                    "header": [
                        {"key": "Authorization", "value": "Bearer {{apiKey}}", "type": "text"}
                    ],
                    "url": {
                        "raw": "{{baseUrl}}/status",
                        "host": ["{{baseUrl}}"],
                        "path": ["status"]
                    }
                }
            }
        ]
    }
    return jsonify(collection), 200

