web: gunicorn "app:create_app()" --workers 2 --threads 4 --timeout 120
release: flask db upgrade && python -c "from app import create_app; app=create_app(); ctx=app.app_context(); ctx.push(); from app.seed import seed_initial; seed_initial(); ctx.pop()"
