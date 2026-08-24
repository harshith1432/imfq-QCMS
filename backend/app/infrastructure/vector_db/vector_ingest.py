import logging
logger = logging.getLogger('qcms.vector_ingest')
from app import db
from app.infrastructure.database.models.models import KnowledgeRepository

_model = None

def get_embedding_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("[RAG] Loading embedding model 'all-MiniLM-L6-v2'...")
            _model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.info(f"[RAG] SentenceTransformer load warning or missing: {e}")
            _model = None
    return _model

def ingest_data(org_id=None):
    model = get_embedding_model()
    if not model:
        logger.info("[RAG] Embedding model unavailable for vector ingestion.")
        return

    query = KnowledgeRepository.query
    if org_id:
        query = query.filter_by(org_id=org_id)
        
    entries = query.all()
    if not entries:
        logger.info(f"[RAG] No KnowledgeRepository data found for org_id={org_id}.")
        return

    logger.info(f"[RAG] Generating embeddings for {len(entries)} documents (org_id={org_id})...")
    for entry in entries:
        content = f"Title: {entry.title or ''}\n"
        content += f"Category: {entry.category or ''}\n"
        content += f"Problem: {entry.problem_summary or ''}\n"
        content += f"Root Cause: {entry.root_cause or ''}\n"
        content += f"Solution: {entry.solution_summary or ''}\n"
        content += f"Keywords: {entry.keywords or ''}"
        
        try:
            entry.embedding = model.encode(content).tolist()
        except Exception as e:
            logger.info(f"[RAG] Error encoding entry ID {entry.id}: {e}")

    try:
        db.session.commit()
        logger.info("[RAG] Ingestion committed successfully.")
    except Exception as e:
        db.session.rollback()
        logger.info(f"[RAG] Error committing embeddings: {e}")
