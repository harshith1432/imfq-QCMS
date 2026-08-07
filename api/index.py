import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app

app = create_app()

@app.route('/api/health', methods=['GET'])
def health_check():
    return {"status": "healthy", "service": "QCMS Enterprise API"}, 200

handler = app
