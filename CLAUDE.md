# Weather Data Analyzer v2

Rebuild of a Streamlit app as FastAPI + React. Work happens in phases, with a commit after each:
1. backend skeleton + DB + auth ✅  2. weather + caching ✅  3. analytics + tests ✅  4. frontend (step 1 ✅ shell/auth/City page; step 2 Dashboard/Compare/History/Account/Ctrl+K after the user approves the look)  5. CI + Render deploy + README.
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
  app/services/         logic that talks to the DB or outside APIs: rate_limit, cache, openweather (HTTP), cities
  app/services/openweather_parse.py  PURE parsing of OpenWeatherMap JSON (no DB/HTTP), unit-tested
  app/core/logging.py   redacts appid=... from httpx/httpcore log lines
  app/analytics/        PURE pandas functions (daily.py, normals.py, compare.py): DataFrame in, DataFrame/dict out
  app/services/openmeteo.py  archive fetch + daily_weather storage; normals.py lazy 1991-2020 normals; analytics.py glue
  app/deps.py           DbSession, CurrentUser, client_ip
  migrations/           Alembic (env.py reads DATABASE_URL from settings)
  tests/                pytest against a real Postgres (TEST_DATABASE_URL)
client/                 React 18 + TS + Vite + Tailwind v4 + shadcn-style Radix components
  src/styles/globals.css  ALL design tokens (colours, radius, shadows) + weather themes ([data-wx], [data-tod])
  src/styles/tokens.test.ts  WCAG AA check of every token pair in every mode x weather theme
  src/lib/api.ts        the only code that calls the server (JSON on every write, same-origin cookie)
  src/lib/units.ts      metric -> user's units, display only; time.ts = city-local times via utc offset
  src/components/ui/    primitives (button, card, tabs, segmented control, menu, skeleton, states)
  src/components/charts/chart-kit.tsx  shared palette/axes/tooltip/ChartCard (Export CSV) for every chart
  src/components/weather/  hero, forecast, Meteocons icons (src/assets/weather-icons, MIT)
  src/pages/            route pages; placeholder-pages.tsx is replaced in phase 4 step 2
  scripts/screenshots.mjs  Playwright design self-check (Edge channel, no browser download)
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

# client (from client/, API running on :8000)
npm.cmd run dev                   # http://localhost:5173, proxies /api
npm.cmd test                      # Vitest
npm.cmd run build                 # tsc -b + vite build
npm.cmd run screenshots           # needs dev server + API; writes docs/screenshots/v2/

# new migration after changing a model
alembic revision --autogenerate -m "what changed"
alembic check                     # fails if models and migrations differ
```

## Conventions

- **Scoping:** user-owned data is always loaded via `CurrentUser` and filtered on `user.id`. Never accept a user id from the URL/body. `tests/test_scoping.py` fails if a new `/api` route works without a login (add truly public routes to `PUBLIC_ROUTES` there on purpose).
- **Auth:** JWT in an httpOnly, SameSite=Lax cookie (`wa_session`), never in localStorage. Claims: `sub` (user id), `tv` (token_version). Changing the password bumps `token_version` → other sessions are signed out. bcrypt directly (no passlib), cost 12, passwords 8-72 bytes.
- **Secure cookie:** `settings.secure_cookies` = Secure flag exactly when `ENVIRONMENT=production` (override with `COOKIE_SECURE`; `false` is refused in production).
- **Cross-site requests:** besides SameSite=Lax, a middleware rejects POST/PUT/PATCH/DELETE to `/api/` without `Content-Type: application/json` (415). The client must send that header on every write, logout included. Never add CORS.
- **Rate limit:** failed logins are stored in `login_attempts` (5 per account, 20 per IP, per 15 min) so restarts don't reset them. Same for change-password.
- **Cities:** rows in `cities` are only created from geocoding results (search upserts them and returns ids). The browser only ever sends a `city_id`, never names or coordinates.
- **Outside APIs:** always through `services/cache.cached_fetch(db, key, ttl, fetch)`. TTLs: geocode 7 d, current 10 min, forecast 1 h (settings). The raw API answer is cached; parsing runs on every request, so parser fixes apply to cached data too. If the API fails and an expired row exists → return it with `stale: true`; otherwise `UpstreamError` → friendly 503 (`UpstreamNotFound` → 404, never served stale).
- **API key safety:** the key is added only in `openweather._get`. Never log or re-raise httpx exceptions (their text contains the URL with the key): log the endpoint + a reason, `raise ... from None`. httpx loggers are filtered (`appid=***`) and default to WARNING. Tests assert the key never appears in responses or logs.
- **Cache clean-up:** rows expired more than 30 days ago are deleted at startup (lifespan) and at most every 10 min during cache writes (`maybe_prune`). Never on every request.
- **Parallel work:** a SQLAlchemy Session is not thread-safe. Work in worker threads (the dashboard and analytics compare: `asyncio.gather` + `Semaphore(5)` + `asyncio.to_thread`) opens its own session from `SessionFactory` and re-loads its rows there. Dashboard cards catch their own errors; compare fails as a whole (503) if a city has no history at all.
- **Side effects:** `GET /api/cities/{id}/weather` records a recent search and a weather snapshot (de-duplicated on observed_at). Forecast and dashboard don't.
- **Analytics (phase 3):**
  - Pure functions only in `app/analytics/` (no DB/HTTP), unit-tested on small hand-made data with known answers.
  - Missing data is explicit: `daily_frame` has one row per calendar day (missing = NaN row); averages skip NaN but summaries report `days_with_data`, `coverage`, `missing_dates`, `low_coverage` (<80%). Rolling 7-day mean needs ≥5 real values. NaN → JSON null, never 0.
  - Open-Meteo (free tier = non-commercial, daily limits): one archive request covers exactly the missing/due span. Days older than 7 days are final and never refetched; newer days at most every 6 h. Dates are the city's local calendar; analytics end at the city's local yesterday (`cities.utc_offset_s`). Today is never stored.
  - 1991-2020 normals: fetched lazily on a city's first analytics view, stored in `climate_normals` (365 rows), never refetched. If the fetch fails, analytics still work (`normals.available=false`) and the next view retries. 15-day window (±7, wraps the year), 29 Feb = 28 Feb, p10/p90 of daily mean = the "normal range".
  - `days` is 30/90/365 (checked in `period_days`; a `Literal` would reject query strings). Compare takes 2-3 different `city_id`s.
- **Units:** the server stores and computes in metric only. `users.units` (metric/imperial) is a display preference; the client converts (`lib/units.ts`). Differences (anomalies) convert without +32; values already converted are formatted with `signedDegrees`, never converted twice.
- **Frontend look:**
  - No hex/rgb values in components: add a token to `globals.css` (light + `.dark`), map it in `@theme`, and `tokens.test.ts` must still pass (text 4.5:1, graphics 3:1, also on glass and the gradient stops).
  - Weather theme: `useWeatherTheme(weather)` sets `<html data-wx data-tod>`; clear skies switch to `clear-night` after sunset.
  - Figures use the `num` class (tabular numbers). Loading = `Skeleton`, never spinners for content; errors = `ErrorState` with retry; nothing = `EmptyState`.
  - Every chart is built from `chart-kit.tsx` (same colours, axes, tooltip, Export CSV, sr-only summary). Recharts is lazy-loaded with the analytics section.
  - Grids that hold a sideways-scrolling strip need `minmax(0,1fr)` columns, or the page scrolls sideways at 375px. The screenshot script prints `OVERFLOW` when that happens.
  - Respect reduced motion: `MotionConfig reducedMotion="user"`, CSS media query, and `stillSvg()` strips the icons' `<animate>` tags.
  - Login redirects only to in-app paths (`safeNext`).
- **Secrets:** only in env vars / `.env` (git-ignored). The OpenWeatherMap key stays on the server and must never be sent to the browser.
- **Tests:** refuse to run unless `TEST_DATABASE_URL` is set and differs from `DATABASE_URL`. The schema is built with the real Alembic migrations; tables are truncated before every test. Outside APIs get mocked (respx), never called.
- **Code:** small typed functions, type hints everywhere. Pure analysis functions (phase 3) go in their own module with unit tests and no DB/HTTP.
- **Windows:** use `npm.cmd` in PowerShell, `server\.venv\Scripts\activate`.

## Decisions (agreed with the user)

- Local DB = a Neon dev branch; tests = a separate Neon branch; docker-compose is optional; CI uses a postgres:16 service.
- One Render service serves both the API and the built client (same origin → simple cookie auth, no CORS).
- 1991-2020 climate normals are fetched lazily the first time a city's analytics are opened, then stored.
- No import of legacy users (start fresh).
