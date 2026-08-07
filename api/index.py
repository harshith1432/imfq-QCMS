import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app

flask_app = create_app()

def app(environ, start_response):
    # Restore original URI from Vercel's request header for Flask routing
    raw_uri = environ.get('HTTP_X_MATCHED_PATH') or environ.get('REQUEST_URI') or environ.get('PATH_INFO', '')
    if '?' in raw_uri:
        raw_uri = raw_uri.split('?')[0]
    if raw_uri and raw_uri.startswith('/api'):
        environ['PATH_INFO'] = raw_uri

    return flask_app(environ, start_response)
