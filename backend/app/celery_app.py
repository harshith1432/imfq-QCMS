"""
Celery Distributed Worker Factory for QCMS Enterprise
======================================================
Binds Celery task execution with Flask application context and database session lifecycle.
"""
from celery import Celery, Task
from flask import Flask


def make_celery(flask_app: Flask) -> Celery:
    """
    Constructs and configures a Celery instance bound to the provided Flask app.
    Wraps task calls inside flask_app.app_context() and handles database session teardowns.
    """
    class FlaskContextTask(Task):
        abstract = True

        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                from app.infrastructure.database.models.models import db
                try:
                    return self.run(*args, **kwargs)
                finally:
                    try:
                        db.session.remove()
                    except Exception:
                        pass

    celery_app = Celery(
        flask_app.import_name,
        task_cls=FlaskContextTask,
        broker=flask_app.config.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0'),
        backend=flask_app.config.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
    )

    celery_app.conf.update(
        task_serializer=flask_app.config.get('CELERY_TASK_SERIALIZER', 'json'),
        result_serializer=flask_app.config.get('CELERY_RESULT_SERIALIZER', 'json'),
        accept_content=flask_app.config.get('CELERY_ACCEPT_CONTENT', ['json']),
        timezone=flask_app.config.get('CELERY_TIMEZONE', 'UTC'),
        enable_utc=flask_app.config.get('CELERY_ENABLE_UTC', True),
        task_track_started=flask_app.config.get('CELERY_TASK_TRACK_STARTED', True),
        task_time_limit=flask_app.config.get('CELERY_TASK_TIME_LIMIT', 600),
        task_soft_time_limit=flask_app.config.get('CELERY_TASK_SOFT_TIME_LIMIT', 540),
        worker_prefetch_multiplier=flask_app.config.get('CELERY_WORKER_PREFETCH_MULTIPLIER', 1),
        task_routes=flask_app.config.get('CELERY_TASK_ROUTES', {}),
        beat_schedule={
            'cleanup-expired-sessions-every-hour': {
                'task': 'app.infrastructure.tasks.maintenance_tasks.cleanup_expired_sessions_and_tokens',
                'schedule': 3600.0,
            },
            'cleanup-soft-deleted-tenants-daily': {
                'task': 'app.infrastructure.tasks.maintenance_tasks.cleanup_soft_deleted_tenants',
                'schedule': 86400.0,
            },
            'aggregate-daily-analytics-nightly': {
                'task': 'app.infrastructure.tasks.maintenance_tasks.aggregate_daily_analytics',
                'schedule': 86400.0,
            }
        }
    )

    celery_app.set_default()
    flask_app.extensions['celery'] = celery_app

    # Auto-register all task modules
    try:
        import app.infrastructure.tasks.report_tasks
        import app.infrastructure.tasks.email_tasks
        import app.infrastructure.tasks.ai_rag_tasks
        import app.infrastructure.tasks.maintenance_tasks
    except Exception as e:
        import logging
        logging.getLogger('QCMS').warning(f"[Celery] Task registration notice: {e}")

    return celery_app
