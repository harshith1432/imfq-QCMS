from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.presentation.middleware.middleware import feature_required
from app.infrastructure.vector_db import vector_service as rag_chat, vector_ingest as rag_ingestion
from app.infrastructure.database.models.models import KnowledgeRepository, User, Organization
from app import db
from sqlalchemy import text

rag_bp = Blueprint('rag', __name__)

@rag_bp.route('/chat', methods=['POST'])
@jwt_required(optional=True)
def chat():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, int(current_user_id)) if current_user_id else None

    # Fallback to cookie if Authorization header was not attached
    if not user:
        from flask_jwt_extended import decode_token
        cookie_token = request.cookies.get('access_token_cookie')
        if cookie_token:
            try:
                decoded = decode_token(cookie_token)
                uid = decoded.get('sub')
                if uid:
                    user = db.session.get(User, int(uid))
            except Exception:
                pass

    if not user:
        import os
        if os.getenv('FLASK_ENV') == 'development':
            user = User.query.filter_by(is_active=True).first()

    if not user:
        return jsonify({
            "error": "Authentication required. Please sign in to use the Quality AI Assistant.",
            "message": "Authentication required."
        }), 401

    org_id = user.org_id
    if not org_id:
        first_org = Organization.query.first()
        if first_org:
            org_id = first_org.id

    if not org_id:
        return jsonify({"error": "Organization context required"}), 403

    data = request.get_json() or {}
    query = data.get('query')
    
    if not query:
        return jsonify({"error": "Query is required"}), 400
        
    try:
        from app.domain.services.quality_ai_assistant import QualityAIAssistant
        result = QualityAIAssistant.get_response(query, user_id=user.id, org_id=org_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[RAG ROUTE] Chat error: {e}")
        return jsonify({"error": "An unexpected error occurred while querying the quality assistant."}), 500

# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: ingest (Lines 43-55)
# Reason: Unused manual RAG document ingestion endpoint.
# ==============================================================================
# @rag_bp.route('/ingest', methods=['POST'])
# @jwt_required()
# @feature_required('ai_assistant')
# def ingest():
#     current_user_id = get_jwt_identity()
#     user = db.session.get(User, current_user_id) if current_user_id else None
#     try:
#         org_id = user.org_id if user else None
#         rag_ingestion.ingest_data(org_id=org_id)
#         return jsonify({"message": "Ingestion completed successfully"}), 200
#     except Exception as e:
#         print(f"[RAG ROUTE] Ingest error: {e}")
#         return jsonify({"error": "Failed to ingest data."}), 500
# [END DEAD CODE: ingest]


@rag_bp.route('/status', methods=['GET'])
@jwt_required()
def status():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id) if current_user_id else None
    org_id = user.org_id if user else None
    try:
        query = db.session.query(KnowledgeRepository).filter(KnowledgeRepository.embedding.isnot(None))
        if org_id:
            query = query.filter(KnowledgeRepository.org_id == org_id)
        has_embeddings = query.first() is not None
    except Exception:
        has_embeddings = False

    return jsonify({
        "index_initialized": has_embeddings,
        "model": getattr(rag_chat, 'MODEL_NAME', 'all-MiniLM-L6-v2')
    }), 200

@rag_bp.route('/health', methods=['GET'])
@jwt_required()
def health():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id) if current_user_id else None
    org_id = user.org_id if user else None

    status_info = {
        "database_connected": False,
        "pgvector_installed": False,
        "knowledge_entries_count": 0,
        "embeddings_populated_count": 0,
        "fallback_mode_active": False,
        "model_loaded": False
    }
    
    try:
        db.session.execute(text("SELECT 1"))
        status_info["database_connected"] = True
    except Exception as e:
        print(f"[RAG HEALTH] DB check error: {e}")
        status_info["database_connected"] = False
        
    if status_info["database_connected"]:
        try:
            result = db.session.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).first()
            status_info["pgvector_installed"] = (result is not None)
        except Exception as e:
            print(f"[RAG HEALTH] pgvector check skipped: {e}")
            status_info["pgvector_installed"] = False
        
    try:
        kr_query = KnowledgeRepository.query
        if org_id:
            kr_query = kr_query.filter_by(org_id=org_id)
        total_count = kr_query.count()
        status_info["knowledge_entries_count"] = total_count
        
        populated_query = KnowledgeRepository.query.filter(KnowledgeRepository.embedding.isnot(None))
        if org_id:
            populated_query = populated_query.filter_by(org_id=org_id)
        populated_count = populated_query.count()
        status_info["embeddings_populated_count"] = populated_count
    except Exception as e:
        print(f"[RAG HEALTH] Count check error: {e}")
        
    status_info["model_loaded"] = rag_chat._model is not None
    status_info["fallback_mode_active"] = not status_info["pgvector_installed"]
    
    return jsonify(status_info), 200
