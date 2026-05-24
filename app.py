"""
MovStok ERP - Application entry point.

This file keeps backward compatibility with the existing Procfile / hosting setup
(`gunicorn app:app` and `gunicorn "app:create_app()"`) and simply delegates to the
real application package located in ./app/.
"""
from app import create_app

# Backwards-compatible WSGI handle: `gunicorn app:app`
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
