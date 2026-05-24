MovStok uses Flask-Migrate/Alembic for schema migrations.

Production flow:

```bash
flask db init      # first time only, if the migrations folder was not created yet
flask db migrate -m "describe schema change"
flask db upgrade
```

Railway should provide `DATABASE_URL`; the app normalizes `postgres://` to
`postgresql://` automatically.
