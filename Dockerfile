FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv yt-dlp
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/ backend/
RUN uv sync --locked --no-dev --no-editable
COPY --from=frontend /app/frontend/dist frontend/dist
EXPOSE 8000
CMD uv run uvicorn backend.api.app:app --host 0.0.0.0 --port ${PORT:-8000}
