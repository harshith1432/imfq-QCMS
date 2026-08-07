import sys
import os
import json
import traceback

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

flask_app = None
init_err = None

def get_app():
    global flask_app, init_err
    if flask_app is None and init_err is None:
        try:
            from app import create_app
            flask_app = create_app()
        except Exception as e:
            init_err = (str(e), traceback.format_exc())
    return flask_app

def app(environ, start_response):
    a = get_app()
    if init_err:
        err_msg, tb = init_err
        body = json.dumps({"status": "error", "message": err_msg, "traceback": tb}).encode('utf-8')
        start_response('200 OK', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
        return [body]

    try:
        raw_uri = environ.get('HTTP_X_MATCHED_PATH') or environ.get('REQUEST_URI') or environ.get('PATH_INFO', '')
        if '?' in raw_uri:
            raw_uri = raw_uri.split('?')[0]
        if raw_uri and raw_uri.startswith('/api'):
            environ['PATH_INFO'] = raw_uri
        return a(environ, start_response)
    except Exception as e:
        tb = traceback.format_exc()
        body = json.dumps({"status": "error", "message": str(e), "traceback": tb}).encode('utf-8')
        start_response('200 OK', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
        return [body]

handler = app
