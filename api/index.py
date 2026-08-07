from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/api/auth/login', methods=['POST'])
def test_login():
    return jsonify({"access_token": "test_token_12345", "status": "success"}), 200

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return jsonify({"status": "ok", "path": path}), 200
