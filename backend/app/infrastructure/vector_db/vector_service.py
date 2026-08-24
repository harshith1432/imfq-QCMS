import math
import json
import logging
try:
    import numpy as np
except ImportError:
    np = None

from sqlalchemy import text
from app import db
from app.infrastructure.database.models.models import KnowledgeRepository, Project

logger = logging.getLogger("QCMS.RAG")

MODEL_NAME = 'all-MiniLM-L6-v2'
_model = None

def _cosine_similarity(vec1, vec2):
    """Pure-python fallback for cosine similarity calculation"""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    if np is not None:
        try:
            q_vec = np.array(vec1, dtype=np.float32)
            doc_vec = np.array(vec2, dtype=np.float32)
            q_norm = np.linalg.norm(q_vec)
            doc_norm = np.linalg.norm(doc_vec)
            if q_norm > 0 and doc_norm > 0:
                return float(np.dot(q_vec, doc_vec) / (q_norm * doc_norm))
        except Exception:
            pass
    try:
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 > 0 and norm2 > 0:
            return float(dot / (norm1 * norm2))
    except Exception:
        pass
    return 0.0

def get_embedding_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("[RAG] Loading embedding model 'all-MiniLM-L6-v2'...")
            _model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"[RAG] SentenceTransformer load notice / running lightweight fallback: {e}")
            _model = None
    return _model

class VectorSearchService:
    @staticmethod
    def search_similar_solutions(org_id, query_embedding, limit=5):
        """
        Database-native vector cosine similarity search.
        Works seamlessly on both Local SQLite and Cloud PostgreSQL without local disk files.
        """
        if not org_id or query_embedding is None:
            return []

        # 1. Query all active knowledge records for this organization tenant
        records = KnowledgeRepository.query.filter_by(org_id=org_id).all()
        if not records:
            return []

        results = []
        try:
            for rec in records:
                if rec.embedding is not None:
                    try:
                        emb = rec.embedding
                        if isinstance(emb, str):
                            emb = json.loads(emb)
                        similarity = _cosine_similarity(query_embedding, emb)
                        if similarity > 0:
                            results.append({
                                "id": rec.id,
                                "project_id": rec.project_id,
                                "title": rec.title or "Untitled Project",
                                "category": rec.category or "Quality",
                                "problem_summary": rec.problem_summary or "",
                                "root_cause": rec.root_cause or "",
                                "solution_summary": rec.solution_summary or "",
                                "kpi_improvement_pct": rec.kpi_improvement_pct or 0,
                                "similarity_score": round(similarity, 4),
                                "content": f"{rec.title or ''} - {rec.solution_summary or rec.problem_summary or ''}"
                            })
                    except Exception as parse_err:
                        logger.debug(f"[RAG] Error processing vector for record {rec.id}: {parse_err}")

            # Sort descending by highest similarity
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            return results[:limit]
        except Exception as e:
            logger.error(f"[RAG] Vector cosine search error: {e}")
            return []

    @classmethod
    def search_by_text(cls, query_text: str, org_id: int, limit: 5):
        """
        Calculates query vector and performs database-native cosine search with keyword fallback.
        """
        model = get_embedding_model()
        query_vector = model.encode(query_text).tolist() if model else None

        if query_vector:
            vector_results = cls.search_similar_solutions(org_id, query_vector, limit=limit)
            if vector_results:
                return vector_results

        # Keyword Fallback when embeddings are not yet generated
        query_words = [w.lower() for w in query_text.split() if len(w) > 2]
        records = KnowledgeRepository.query.filter_by(org_id=org_id).all()
        scored = []
        for r in records:
            corpus = f"{r.title or ''} {r.category or ''} {r.problem_summary or ''} {r.root_cause or ''} {r.solution_summary or ''} {r.keywords or ''}".lower()
            score = sum(1 for w in query_words if w in corpus)
            if score > 0 or not query_words:
                scored.append({
                    "id": r.id,
                    "project_id": r.project_id,
                    "title": r.title or "Untitled Project",
                    "category": r.category or "Quality",
                    "problem_summary": r.problem_summary or "",
                    "root_cause": r.root_cause or "",
                    "solution_summary": r.solution_summary or "",
                    "kpi_improvement_pct": r.kpi_improvement_pct or 0,
                    "cost_savings": r.cost_savings or 0,
                    "similarity_score": round(score / max(len(query_words), 1), 4),
                    "content": f"{r.title or ''} - {r.solution_summary or r.problem_summary or ''}"
                })
        scored.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored[:limit]

def get_chat_response(query, org_id=None):
    if not org_id:
        return {
            "answer": "Organization context is required to query your Quality AI Assistant.",
            "sources": []
        }

    results = VectorSearchService.search_by_text(query, org_id, limit=5)

    if not results:
        return {
            "answer": "I could not find any historical quality projects or knowledge entries for your organization matching your query. As new projects are archived in your Knowledge Repository, answers will automatically populate here.",
            "sources": []
        }

    formatted_answer = "Based on your organization's Knowledge Repository, here are the top relevant quality improvement insights:\n\n"
    sources = []

    for i, res in enumerate(results):
        title = res.get('title', 'Untitled Project')
        category = res.get('category', 'Quality')
        prob = res.get('problem_summary', '') or 'No summary recorded'
        cause = res.get('root_cause', '') or 'N/A'
        sol = res.get('solution_summary', '') or 'N/A'
        kpi = res.get('kpi_improvement_pct', 0)
        savings = res.get('cost_savings', 0)
        proj_id = res.get('project_id', res.get('id'))

        meta = {
            'project_id': proj_id,
            'title': title,
            'category': category,
            'summary': prob[:180] + ('...' if len(prob) > 180 else '')
        }
        sources.append(meta)

        formatted_answer += f"### {i+1}. {title}\n"
        formatted_answer += f"- **Category**: `{category}`\n"
        formatted_answer += f"- **Problem**: {prob[:220]}\n"
        if cause and cause != 'N/A':
            formatted_answer += f"- **Root Cause / 5-Why**: {cause[:220]}\n"
        if sol and sol != 'N/A':
            formatted_answer += f"- **Countermeasure / Solution**: {sol[:220]}\n"
        if kpi or savings:
            formatted_answer += f"- **Impact**: {f'{kpi}% KPI Improvement' if kpi else ''} {f'· ₹{savings:,.0f} Cost Savings' if savings else ''}\n"
        formatted_answer += "\n"

    return {
        "answer": formatted_answer + "*Note: These insights are strictly isolated to your organization's archived projects and quality repositories.*",
        "sources": sources
    }
