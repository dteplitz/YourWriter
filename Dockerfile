# ── Dev stage: backend ───────────────────────────────────────────────────────
# Used by docker-compose for local development (source code mounted as volume)
FROM python:3.11-slim AS dev-backend

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]


# ── Dev stage: frontend ───────────────────────────────────────────────────────
# Used by docker-compose for local development (source code mounted as volume)
FROM node:20-slim AS dev-frontend

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

CMD ["npx", "vite", "--port", "3000", "--host", "0.0.0.0"]


# ── Production stage 1: Build the React frontend ─────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ── Production stage 2: Python runtime ───────────────────────────────────────
FROM python:3.11-slim AS production

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY agents/ ./agents/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

RUN mkdir -p data

EXPOSE 8000

CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
