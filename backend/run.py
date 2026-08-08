import sys
import os
import json
import traceback

sys.path.insert(0, os.path.dirname(__file__))

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
        body = json.dumps({"status": "error", "message": f"Flask Init Failed: {err_msg}", "traceback": tb}).encode('utf-8')
        start_response('200 OK', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
        return [body]

    try:
        return a(environ, start_response)
    except Exception as e:
        tb = traceback.format_exc()
        body = json.dumps({"status": "error", "message": str(e), "traceback": tb}).encode('utf-8')
        start_response('200 OK', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
        return [body]

if __name__ == "__main__":
    a = get_app()
    if a:
        a.run(debug=True, host='127.0.0.1', port=5000)
