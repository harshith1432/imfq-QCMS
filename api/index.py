import sys
import os
import json
import traceback

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

flask_app = None
init_error = None
init_tb = None

try:
    from app import create_app
    flask_app = create_app()
except Exception as e:
    init_error = str(e)
    init_tb = traceback.format_exc()

def app(environ, start_response):
    global flask_app, init_error, init_tb
    if flask_app is None and init_error is None:
        try:
            from app import create_app
            flask_app = create_app()
        except Exception as e:
            init_error = str(e)
            init_tb = traceback.format_exc()

    if init_error:
        body = json.dumps({"status": "error", "message": f"Flask Init Failed: {init_error}", "traceback": init_tb}).encode('utf-8')
        start_response('200 OK', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
        return [body]

    try:
        return flask_app(environ, start_response)
    except Exception as e:
        tb = traceback.format_exc()
        body = json.dumps({"status": "error", "message": str(e), "traceback": tb}).encode('utf-8')
        start_response('200 OK', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
        return [body]
