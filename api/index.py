import sys
import os
import json
import traceback

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from app import create_app
    app = create_app()
except Exception as init_err:
    err_tb = traceback.format_exc()
    from flask import Flask, jsonify
    app = Flask(__name__)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        return jsonify({
            "status": "error",
            "message": f"Flask Init Error: {init_err}",
            "traceback": err_tb
        }), 500
