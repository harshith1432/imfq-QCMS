import sys
import os
import json
import logging

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
_startup_logger = logging.getLogger('qcms.startup')

flask_app = None
_init_failed = False


def get_app():
    global flask_app, _init_failed
    if flask_app is None and not _init_failed:
        try:
            from app import create_app
            flask_app = create_app()
        except BaseException as exc:
            _init_failed = True
            _startup_logger.exception('[QCMS FATAL] Application failed to initialize: %s', exc)
    return flask_app


def app(environ, start_response):
    a = get_app()
    if _init_failed or a is None:
        body = json.dumps({
            'status': 'error',
            'message': 'Service temporarily unavailable. Please try again later.',
            'code': 'SERVICE_UNAVAILABLE'
        }).encode('utf-8')
        start_response('503 Service Unavailable', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
        return [body]
    try:
        return a(environ, start_response)
    except BaseException as exc:
        _startup_logger.exception('[QCMS] Unhandled WSGI exception: %s', exc)
        body = json.dumps({
            'status': 'error',
            'message': 'An internal server error occurred.',
            'code': 'INTERNAL_ERROR'
        }).encode('utf-8')
        start_response('500 Internal Server Error', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
        return [body]


try:
    _preloaded_app = get_app()
except Exception:
    _preloaded_app = None

if __name__ == '__main__':
    a = get_app()
    if a and hasattr(a, 'run'):
        a.run(debug=False, host='127.0.0.1', port=5000)
