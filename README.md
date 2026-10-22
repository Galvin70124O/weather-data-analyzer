# Weather Data Analyzer

**Being rebuilt** as a FastAPI + PostgreSQL backend with a React frontend. The original Streamlit
version is in [`legacy/`](legacy/) until the new one is complete.

| Phase | Status |
|---|---|
| 1. Backend skeleton, database, accounts (register, login, logout, change password, rate limit) | ✅ done |
| 2. Weather (OpenWeatherMap): city search, current weather, forecast, favourites, history, caching | ✅ done |
| 3. Analytics: 30/90/365-day history, rolling means, 1991-2020 normals, anomalies, extremes, compare cities | ✅ done |
| 4. Frontend (React + TypeScript + Vite): step 1 = design system, app shell, login/register, City page | step 1 done, waiting for review |
| 4. Frontend step 2: Dashboard, Compare, History, Account, Ctrl+K search | |
| 5. CI + Render deploy + full README | |

## Run the backend locally (Windows PowerShell)

```powershell
python -m venv server\.venv
server\.venv\Scripts\activate
pip install -r server\requirements-dev.txt
copy .env.example .env      # fill in DATABASE_URL, TEST_DATABASE_URL (separate!), JWT_SECRET
cd server
alembic upgrade head
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/api/docs. Run the tests with `pytest` (from `server/`).

## Run the frontend locally

With the backend running on port 8000, in a second PowerShell window:

```powershell
cd client
npm.cmd install
npm.cmd run dev            # http://localhost:5173 (proxies /api to :8000, same origin for the cookie)
npm.cmd test               # Vitest: units, CSV, API client, components, WCAG contrast of every theme
npm.cmd run build          # type-check + production build into client/dist
npm.cmd run screenshots    # Playwright (uses installed Edge): 375px + 1440px, light + dark -> docs/screenshots/v2/
```

See [CLAUDE.md](CLAUDE.md) for the structure and conventions.

## Data sources

- Current weather, forecasts and city search: [OpenWeatherMap](https://openweathermap.org/) (API key on the server only).
- Historical weather and 1991-2020 normals: [Open-Meteo](https://open-meteo.com/) Historical Weather API, data licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Open-Meteo's free API is for **non-commercial use** and has daily limits, so the app stores past days and only refreshes the most recent week.
