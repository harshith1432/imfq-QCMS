import sys
import os
import json
import traceback

sys.path.insert(0, os.path.dirname(__file__))

try:
    from app import create_app
    app = create_app()
except Exception as e:
    tb = traceback.format_exc()
    err_str = str(e)
    def err_app(environ, start_response):
        body = json.dumps({"status": "error", "message": f"Flask Init Failed: {err_str}", "traceback": tb}).encode('utf-8')
        start_response('200 OK', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
        return [body]
    app = err_app

if __name__ == "__main__":
    if hasattr(app, 'run'):
        print("\n" + "=" * 50)
        print("  QCMS Enterprise — Quality Management System")
        print("  Server: http://127.0.0.1:5000")
        print("  API:    http://127.0.0.1:5000/api/*")
        print("=" * 50 + "\n")
        app.run(debug=True, host='127.0.0.1', port=5000)
