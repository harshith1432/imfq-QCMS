import sys
import os
import json
import traceback

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def app(environ, start_response):
    try:
        from run import app as flask_app
        raw_uri = environ.get('HTTP_X_MATCHED_PATH') or environ.get('REQUEST_URI') or environ.get('PATH_INFO', '')
        if '?' in raw_uri:
            raw_uri = raw_uri.split('?')[0]
        if raw_uri and raw_uri.startswith('/api'):
            environ['PATH_INFO'] = raw_uri

        return flask_app(environ, start_response)
    except Exception as e:
        tb = traceback.format_exc()
        body = json.dumps({"status": "error", "message": str(e), "traceback": tb}).encode('utf-8')
        start_response('200 OK', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
        return [body]

handler = app
