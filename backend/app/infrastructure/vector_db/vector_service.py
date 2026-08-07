import math
import json
from app import db
from app.infrastructure.database.models.models import KnowledgeRepository, Project
from sqlalchemy import text

MODEL_NAME = 'all-MiniLM-L6-v2'

_model = None

def get_embedding_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("[RAG] Loading embedding model 'all-MiniLM-L6-v2'...")
            _model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"[RAG] SentenceTransformer load warning or missing: {e}")
            _model = None
    return _model

def dot_product(v1, v2):
    return sum(x * y for x, y in zip(v1, v2))

def magnitude(v):
    return math.sqrt(sum(x * x for x in v))

def cosine_similarity(v1, v2):
    mag1 = magnitude(v1)
    mag2 = magnitude(v2)
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot_product(v1, v2) / (mag1 * mag2)

def get_chat_response(query, org_id=None):
    if not org_id:
        return {
            "answer": "Organization context is required to query your Quality AI Assistant.",
            "sources": []
        }

    results = []
    model = get_embedding_model()
    query_vector = model.encode(query).tolist() if model else None

    # 1. Attempt raw pgvector SQL query if available
    if query_vector:
        try:
            vec_str = f"[{','.join(str(f) for f in query_vector)}]"
            raw_sql = text("""
                SELECT id, project_id, title, category, problem_summary, root_cause, solution_summary, kpi_improvement_pct, cost_savings,
                       1 - (embedding <=> CAST(:vec AS vector)) AS similarity
                FROM knowledge_repository
                WHERE org_id = :org_id AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:vec AS vector) ASC
                LIMIT 5
            """)
            rows = db.session.execute(raw_sql, {"vec": vec_str, "org_id": org_id}).fetchall()
            if rows:
                class SQLResult:
                    def __init__(self, row):
                        self.id = row[0]
                        self.project_id = row[1]
                        self.title = row[2]
                        self.category = row[3]
                        self.problem_summary = row[4]
                        self.root_cause = row[5]
                        self.solution_summary = row[6]
                        self.kpi_improvement_pct = row[7]
                        self.cost_savings = row[8]
                        self.similarity = row[9]
                results = [SQLResult(r) for r in rows]
        except Exception as e:
            db.session.rollback()
            print(f"[RAG] Raw pgvector query skipped/fallback: {e}")

    # 2. In-memory vector similarity fallback strictly scoped by org_id
    if not results and query_vector:
        try:
            all_items = db.session.query(
                KnowledgeRepository.id,
                KnowledgeRepository.project_id,
                KnowledgeRepository.title,
                KnowledgeRepository.category,
                KnowledgeRepository.problem_summary,
                KnowledgeRepository.root_cause,
                KnowledgeRepository.solution_summary,
                KnowledgeRepository.kpi_improvement_pct,
                KnowledgeRepository.cost_savings,
                KnowledgeRepository.embedding
            ).filter(KnowledgeRepository.org_id == org_id).all()

            fallback_results = []
            for item in all_items:
                if item.embedding is not None:
                    emb = item.embedding
                    if isinstance(emb, str):
                        emb = json.loads(emb)
                    elif hasattr(emb, 'tolist'):
                        emb = emb.tolist()
                    elif not isinstance(emb, list):
                        emb = list(emb)

                    if emb and len(emb) == len(query_vector):
                        sim = cosine_similarity(query_vector, emb)
                        fallback_results.append((item, sim))

            fallback_results.sort(key=lambda x: x[1], reverse=True)
            top_results = fallback_results[:5]

            class MockResult:
                def __init__(self, item, similarity):
                    self.id = item.id
                    self.project_id = item.project_id
                    self.title = item.title
                    self.category = item.category
                    self.problem_summary = item.problem_summary
                    self.root_cause = item.root_cause
                    self.solution_summary = item.solution_summary
                    self.kpi_improvement_pct = item.kpi_improvement_pct
                    self.cost_savings = item.cost_savings
                    self.similarity = similarity

            results = [MockResult(item, sim) for item, sim in top_results if sim >= 0.2]
        except Exception as fallback_err:
            db.session.rollback()
            print(f"[RAG] In-memory vector fallback error: {fallback_err}")

    # 3. Hybrid Keyword Search Fallback strictly scoped by org_id
    if not results:
        try:
            query_words = [w.lower() for w in query.split() if len(w) > 2]
            kr_items = KnowledgeRepository.query.filter_by(org_id=org_id).all()
            scored_items = []

            for item in kr_items:
                score = 0
                text_corpus = f"{item.title or ''} {item.category or ''} {item.problem_summary or ''} {item.root_cause or ''} {item.solution_summary or ''} {item.keywords or ''}".lower()
                for qw in query_words:
                    if qw in text_corpus:
                        score += 1
                if score > 0 or not query_words:
                    scored_items.append((item, score))

            if not scored_items:
                org_projects = Project.query.filter_by(org_id=org_id).all()
                for proj in org_projects:
                    score = 0
                    p_title = getattr(proj, 'title', '') or ''
                    p_cat = getattr(proj, 'category', 'Quality') or 'Quality'
                    p_desc = getattr(proj, 'description', '') or ''
                    text_corpus = f"{p_title} {p_cat} {p_desc}".lower()
                    for qw in query_words:
                        if qw in text_corpus:
                            score += 1
                    if score > 0 or not query_words:
                        class MockProjItem:
                            def __init__(self, p):
                                self.id = p.id
                                self.project_id = p.id
                                self.title = p.title
                                self.category = p.category or 'Quality'
                                self.problem_summary = getattr(p, 'description', '') or ''
                                self.root_cause = ''
                                self.solution_summary = ''
                                self.kpi_improvement_pct = 0
                                self.cost_savings = 0
                                self.similarity = 0.8 if score > 0 else 0.5
                        scored_items.append((MockProjItem(proj), score))

            scored_items.sort(key=lambda x: x[1], reverse=True)
            results = [item[0] for item in scored_items[:5]]
        except Exception as kw_err:
            db.session.rollback()
            print(f"[RAG] Keyword fallback error: {kw_err}")

    if not results:
        return {
            "answer": "I'm sorry, I couldn't find any historical quality projects or knowledge entries for your organization matching your query. As new projects are archived in your Knowledge Repository, answers will automatically populate here.",
            "sources": []
        }

    formatted_answer = "Based on your organization's Knowledge Repository, here are the top relevant quality improvement insights:\n\n"
    sources = []

    for i, res in enumerate(results):
        title = getattr(res, 'title', 'Untitled Project')
        category = getattr(res, 'category', 'Quality')
        prob = getattr(res, 'problem_summary', '') or 'No summary recorded'
        cause = getattr(res, 'root_cause', '') or 'N/A'
        sol = getattr(res, 'solution_summary', '') or 'N/A'
        kpi = getattr(res, 'kpi_improvement_pct', 0)
        savings = getattr(res, 'cost_savings', 0)
        proj_id = getattr(res, 'project_id', res.id)

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
