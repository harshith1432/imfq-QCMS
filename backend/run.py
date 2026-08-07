import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

_app = None

def app(environ, start_response):
    global _app
    if _app is None:
        from app import create_app
        _app = create_app()
    return _app(environ, start_response)

if __name__ == "__main__":
    from app import create_app
    print("\n" + "=" * 50)
    print("  QCMS Enterprise — Quality Management System")
    print("  Server: http://127.0.0.1:5000")
    print("  API:    http://127.0.0.1:5000/api/*")
    print("=" * 50 + "\n")
    _app = create_app()
    _app.run(debug=True, host='127.0.0.1', port=5000)
