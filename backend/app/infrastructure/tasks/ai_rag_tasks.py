"""
Asynchronous AI & RAG Processing Tasks
=====================================
Performs document chunking, embeddings generation, and vector indexing off the HTTP thread.
"""
import logging
from celery import shared_task
from app.infrastructure.database.models.models import KnowledgeRepository, db

logger = logging.getLogger("QCMS.AI_RAG")


@shared_task(bind=True, name="app.infrastructure.tasks.ai_rag_tasks.process_document_for_rag")
def process_document_for_rag(self, doc_id: int, org_id: int):
    """Processes uploaded knowledge document, generates embeddings, and saves into vector repository."""
    logger.info(f"[Celery RAG] Processing document {doc_id} for org {org_id}")
    doc = db.session.get(KnowledgeRepository, doc_id)
    if not doc:
        return {"status": "failed", "error": "Knowledge document not found"}

    try:
        from app.infrastructure.vector_db.vector_ingest import get_embedding_model
        model = get_embedding_model()
        content = f"Title: {doc.title or ''}\n"
        content += f"Category: {doc.category or ''}\n"
        content += f"Problem: {doc.problem_summary or ''}\n"
        content += f"Root Cause: {doc.root_cause or ''}\n"
        content += f"Solution: {doc.solution_summary or ''}\n"
        raw_emb = model.encode(content)
        doc.embedding = raw_emb.tolist() if hasattr(raw_emb, 'tolist') else list(raw_emb)
        db.session.commit()
        logger.info(f"[Celery RAG] Completed embedding generation for document {doc_id}")
        return {"status": "indexed", "doc_id": doc_id}
    except Exception as e:
        logger.error(f"[Celery RAG] Error processing document {doc_id}: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}
