# Weather Data Analyzer

**Being rebuilt** as a FastAPI + PostgreSQL backend with a React frontend. The original Streamlit
version is in [`legacy/`](legacy/) until the new one is complete.

| Phase | Status |
|---|---|
| 1. Backend skeleton, database, accounts (register, login, logout, change password, rate limit) | ✅ done |
| 2. Weather (OpenWeatherMap): city search, current weather, forecast, favourites, history, caching | ✅ done |
| 3. Analytics (Open-Meteo history, pandas) | next |
| 4. Frontend (React + TypeScript + Vite) | |
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

See [CLAUDE.md](CLAUDE.md) for the structure and conventions.
