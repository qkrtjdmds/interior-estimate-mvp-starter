# Alembic

Alembic is the official path for schema creation and schema changes. Keep real
connection values in `.env`; `alembic.ini` intentionally does not contain a DB
URL or password.

Run these commands from `backend` in Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic history
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe change"
```

Use downgrade only in a disposable development database, after checking the
migration file and current data:

```powershell
.\.venv\Scripts\python.exe -m alembic downgrade -1
```

For an existing database that already has the baseline reference tables, verify
schema compatibility first, then stamp the baseline and upgrade later revisions:

```powershell
.\.venv\Scripts\python.exe -m alembic stamp 0001_reference_baseline
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Do not use `python -m app.db.init_db` on an Alembic-managed database except for
short-lived local experiments.