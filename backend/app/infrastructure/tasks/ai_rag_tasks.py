"""
Asynchronous AI & RAG Processing Tasks
=====================================
Performs document chunking, embeddings generation, and pgvector storage.
"""
import logging
from celery import shared_task
from app.infrastructure.database.models.models import KnowledgeRepository, db

logger = logging.getLogger("QCMS.AI_RAG")


@shared_task(bind=True, name="app.infrastructure.tasks.ai_rag_tasks.process_document_for_rag")
def process_document_for_rag(self, doc_id: int, org_id: int):
    """Processes uploaded document, generates embeddings, and saves into vector repository."""
    logger.info(f"[Celery RAG] Processing document {doc_id} for org {org_id}")
    doc = db.session.get(KnowledgeRepository, doc_id)
    if not doc:
        return {"status": "failed", "error": "Knowledge document not found"}

    try:
        from app.domain.services.rag_service import generate_document_embeddings
        generate_document_embeddings(doc)
        logger.info(f"[Celery RAG] Completed embedding generation for document {doc_id}")
        return {"status": "indexed", "doc_id": doc_id}
    except Exception as e:
        logger.error(f"[Celery RAG] Error processing document {doc_id}: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}
