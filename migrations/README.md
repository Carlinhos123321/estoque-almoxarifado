IMA Stock uses Flask-Migrate/Alembic for schema migrations.

Production flow:

```bash
flask db upgrade
```

Railway should provide `DATABASE_URL`; the app normalizes `postgres://` to
`postgresql://` automatically.

The first revision (`20260617_0001`) is an idempotent baseline so databases that
were previously created with `db.create_all()` can be adopted safely. New schema
changes must be generated with:

```bash
flask db migrate -m "describe schema change"
flask db upgrade
```
