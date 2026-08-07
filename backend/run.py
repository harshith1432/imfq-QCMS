import sys
import os

# Ensure the backend directory is in the Python path so 'app' module is found
# This is needed when Vercel runs this file from the project root
sys.path.insert(0, os.path.dirname(__file__))

import json
import traceback

class CatchAllMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        try:
            return self.wsgi_app(environ, start_response)
        except Exception as e:
            tb = traceback.format_exc()
            body = f'{{"status":"error","message":{json.dumps(str(e))},"traceback":{json.dumps(tb)}}}'.encode('utf-8')
            start_response('500 Internal Server Error', [
                ('Content-Type', 'application/json'),
                ('Content-Length', str(len(body)))
            ])
            return [body]

app = create_app()
app.wsgi_app = CatchAllMiddleware(app.wsgi_app)

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  QCMS Enterprise — Quality Management System")
    print("  Server: http://127.0.0.1:5000")
    print("  API:    http://127.0.0.1:5000/api/*")
    print("=" * 50 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
