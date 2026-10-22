# Weather Data Analyzer v2

Rebuild of a Streamlit app as FastAPI + React. Work happens in phases, with a commit after each:
1. backend skeleton + DB + auth ✅  2. weather + caching  3. analytics + tests  4. frontend  5. CI + Render deploy + README.
The old Streamlit app lives in `legacy/` until v2 works. Don't edit it; don't delete it yet.

## Structure

```
server/                 FastAPI (Python 3.12)
  app/main.py           create_app(): routers + security headers
  app/core/config.py    Settings (pydantic-settings) from env vars / repo-root .env
  app/core/security.py  bcrypt hashing, JWT session tokens
  app/db/               Base (naming convention), engine/session, get_db
  app/models/           SQLAlchemy 2 models (one file per table)
  app/schemas/          Pydantic v2 request/response bodies (validation lives here)
  app/routers/          thin route handlers
  app/services/         logic that talks to the DB or outside APIs (rate_limit, later weather/cache)
  app/deps.py           DbSession, CurrentUser, client_ip
  migrations/           Alembic (env.py reads DATABASE_URL from settings)
  tests/                pytest against a real Postgres (TEST_DATABASE_URL)
client/                 React 18 + TS + Vite (phase 4)
legacy/                 old Streamlit app
docker-compose.yml      OPTIONAL local Postgres 16 (default is Neon dev/test branches)
```

## Commands (PowerShell, from the repo root)

```powershell
# one-time setup
python -m venv server\.venv
server\.venv\Scripts\activate
pip install -r server\requirements-dev.txt
copy .env.example .env            # then fill in DATABASE_URL, TEST_DATABASE_URL, JWT_SECRET

# run (from server/)
cd server
alembic upgrade head              # apply migrations to DATABASE_URL
uvicorn app.main:app --reload     # http://127.0.0.1:8000/api/health, docs at /api/docs
pytest                            # needs TEST_DATABASE_URL (a separate DB: it gets wiped)

# new migration after changing a model
alembic revision --autogenerate -m "what changed"
alembic check                     # fails if models and migrations differ
```

## Conventions

- **Scoping:** user-owned data is always loaded via `CurrentUser` and filtered on `user.id`. Never accept a user id from the URL/body. `tests/test_scoping.py` fails if a new `/api` route works without a login (add truly public routes to `PUBLIC_ROUTES` there on purpose).
- **Auth:** JWT in an httpOnly, SameSite=Lax cookie (`wa_session`), never in localStorage. Claims: `sub` (user id), `tv` (token_version). Changing the password bumps `token_version` → other sessions are signed out. bcrypt directly (no passlib), cost 12, passwords 8-72 bytes.
- **Rate limit:** failed logins are stored in `login_attempts` (5 per account, 20 per IP, per 15 min) so restarts don't reset them. Same for change-password.
- **Units:** the server stores and computes in metric only. `users.units` (metric/imperial) is a display preference; the client converts.
- **Secrets:** only in env vars / `.env` (git-ignored). The OpenWeatherMap key stays on the server and must never be sent to the browser.
- **Tests:** refuse to run unless `TEST_DATABASE_URL` is set and differs from `DATABASE_URL`. The schema is built with the real Alembic migrations; tables are truncated before every test. Outside APIs get mocked (respx), never called.
- **Code:** small typed functions, type hints everywhere. Pure analysis functions (phase 3) go in their own module with unit tests and no DB/HTTP.
- **Windows:** use `npm.cmd` in PowerShell, `server\.venv\Scripts\activate`.

## Decisions (agreed with the user)

- Local DB = a Neon dev branch; tests = a separate Neon branch; docker-compose is optional; CI uses a postgres:16 service.
- One Render service serves both the API and the built client (same origin → simple cookie auth, no CORS).
- 1991-2020 climate normals are fetched lazily the first time a city's analytics are opened, then stored.
- No import of legacy users (start fresh).
