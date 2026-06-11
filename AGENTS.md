# AGENTS.md

## Cursor Cloud specific instructions

This is **Redash** — a Flask (Python 3.13 / Poetry) backend plus a React (Node 24 / pnpm) frontend, backed by **PostgreSQL** and **Redis**. The repo's root `compose.yaml` is a production setup that points at an external GCP Cloud SQL instance, so the cloud dev environment runs the services **natively** (no Docker) instead.

The update script keeps dependencies fresh (`poetry install` + `pnpm install`). Everything below is about running/testing, which the update script intentionally does not do.

### Services are NOT auto-started

PostgreSQL and Redis are installed but do not start on their own (no systemd in the VM). Start them at the beginning of a session:

```
sudo pg_ctlcluster 16 main start    # PostgreSQL 16
sudo redis-server --daemonize yes    # Redis 7
```

The `postgres` role password is `postgres`. Databases `redash` (dev) and `tests` already exist with schema created; their data persists in the VM snapshot.

### Environment file

A `.env` (gitignored) is required and already present with local connection strings:
`REDASH_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/redash` and `REDASH_REDIS_URL=redis://localhost:6379/0`. Load it before running backend commands: `set -a; . ./.env; set +a`.

### Node version gotcha

A daemon-provided `node` v22 (`/exec-daemon/node`) can shadow the project's Node 24 in non-login shells. A login shell (or `nvm use 24`) selects Node 24 (the nvm default) plus the matching global `pnpm`. Node 22 still satisfies `engines` (`>=18 <26`) if it slips through, but prefer Node 24 to match `.nvmrc`/CI.

### Running the app (development mode)

Run each in its own shell/tmux session after loading `.env`:

- Backend API (Flask, auto-reload): `poetry run python manage.py runserver --debugger --reload -h 0.0.0.0 -p 5000`
- RQ worker (executes queries): `poetry run python manage.py rq worker`
- RQ scheduler: `poetry run python manage.py rq scheduler`
- Frontend dev server (webpack, port 8080): `REDASH_BACKEND=http://localhost:5000 pnpm start`

Open the app at `http://localhost:8080`. The dev server proxies `/api`, `/login`, `/setup`, etc. to the backend (default proxy target is `http://localhost:5001`, so set `REDASH_BACKEND=http://localhost:5000` to match the native backend port). First run redirects to `/setup` to create the admin user + organization. To create tables on a fresh DB: `poetry run python manage.py database create_tables`.

### Tests

- Backend tests use a **separate `tests` database**; set `REDASH_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tests` when invoking pytest. Run with `poetry run pytest tests/...` (Postgres + Redis must be running).
- Frontend: `pnpm run test` (runs `tsc` type-check then jest) and `pnpm --filter @redash/viz test`.

### Lint / build

- Backend lint: `poetry run ruff check .` (ruff is in the `dev` group). `black` is **not** a Poetry dependency — CI installs `black==23.1.0` separately (`pip install black==23.1.0`). Note the fork currently has pre-existing ruff/black violations in some custom query runners and tests.
- Frontend lint: `pnpm run lint` (clean).
- Production build: `pnpm run build` (slow, ~1–2 min; emits to `client/dist`).
