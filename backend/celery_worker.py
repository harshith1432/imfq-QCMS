"""
QCMS Distributed Celery Worker Entrypoint
========================================
CLI invocation examples:
  Worker:  celery -A celery_worker.celery worker --loglevel=info -Q default,reports,emails,ai_rag
  Beat:    celery -A celery_worker.celery beat --loglevel=info
"""
import os
from app import create_app
from app.celery_app import make_celery

flask_app = create_app()
celery = make_celery(flask_app)

if __name__ == '__main__':
    celery.start()
