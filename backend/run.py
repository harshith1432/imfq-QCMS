from app import create_app

app = create_app()

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  QCMS Enterprise — Quality Management System")
    print("  Server: http://127.0.0.1:5000")
    print("  API:    http://127.0.0.1:5000/api/*")
    print("=" * 50 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
