# One image for Render: builds the React client, then runs FastAPI, which serves the API and the
# built client from the same origin (simple cookie auth, no CORS).

# --- 1. build the client --------------------------------------------------------------
FROM node:22-slim AS client
WORKDIR /app/client
COPY client/package.json client/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY client/ ./
RUN npm run build

# --- 2. the server ----------------------------------------------------------------------
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 ENVIRONMENT=production
WORKDIR /app/server
COPY server/requirements.txt ./
RUN pip install -r requirements.txt
COPY server/ ./
# app/core/config.py looks for the client at <repo>/client/dist
COPY --from=client /app/client/dist /app/client/dist

RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app

# Migrations first, then the server. --proxy-headers: behind Render's proxy, request.client is the
# real visitor (the login rate limit counts per IP).
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
