"""
Celery Distributed Worker Factory for QCMS Enterprise
======================================================
Binds Celery task execution with Flask application context and database session lifecycle.
"""
import os
import logging
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

    is_testing = (
        flask_app.config.get('TESTING', False)
        or os.getenv('TESTING', '').lower() in ('true', '1')
        or bool(os.getenv('PYTEST_CURRENT_TEST'))
    )
    broker_url = 'memory://' if is_testing else flask_app.config.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
    result_backend = 'cache+memory://' if is_testing else flask_app.config.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')

    celery_app = Celery(
        flask_app.import_name,
        task_cls=FlaskContextTask,
        broker=broker_url,
        backend=result_backend
    )

    celery_app.conf.update(
        task_always_eager=is_testing,
        task_eager_propagates=is_testing,
        task_store_eager_result=is_testing,
        task_serializer=flask_app.config.get('CELERY_TASK_SERIALIZER', 'json'),
        result_serializer=flask_app.config.get('CELERY_RESULT_SERIALIZER', 'json'),
        accept_content=flask_app.config.get('CELERY_ACCEPT_CONTENT', ['json']),
        timezone=flask_app.config.get('CELERY_TIMEZONE', 'UTC'),
        enable_utc=flask_app.config.get('CELERY_ENABLE_UTC', True),
        task_track_started=flask_app.config.get('CELERY_TASK_TRACK_STARTED', True),
        task_time_limit=flask_app.config.get('CELERY_TASK_TIME_LIMIT', 600),
        task_soft_time_limit=flask_app.config.get('CELERY_TASK_SOFT_TIME_LIMIT', 540),
        worker_prefetch_multiplier=flask_app.config.get('CELERY_WORKER_PREFETCH_MULTIPLIER', 1),
        broker_connection_retry=False,
        broker_connection_retry_on_startup=False,
        broker_connection_max_retries=0,
        broker_connection_timeout=0.5,
        broker_transport_options={
            'socket_timeout': 0.5,
            'socket_connect_timeout': 0.5,
            'retry_on_timeout': False,
            'max_retries': 0,
        },
        result_backend_transport_options={
            'socket_timeout': 0.5,
            'socket_connect_timeout': 0.5,
            'retry_on_timeout': False,
            'max_retries': 0,
        },
        redis_socket_connect_timeout=0.5,
        redis_socket_timeout=0.5,
        redis_retry_on_timeout=False,
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
