# Stage 1: build frontend
FROM docker.io/node:24-alpine AS frontend-builder
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# Stage 2: build Python deps
FROM docker.io/python:3.14-slim AS python-builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Stage 3: final image
FROM docker.io/python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app

# Copy virtualenv from builder
COPY --from=python-builder /app/.venv /app/.venv

# Copy app and built frontend
COPY main.py ./
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8001

CMD ["python", "main.py"]
