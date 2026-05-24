web: gunicorn "app:create_app()" --workers 2 --threads 4 --timeout 120
release: python -c "from app import create_app; from app.extensions import db; app=create_app(); ctx=app.app_context(); ctx.push(); db.create_all(); from app.seed import seed_initial; seed_initial(); ctx.pop()"
