# One Dockerfile for the app repo.
# Use build targets from docker-compose:
#   - target: platform
#   - target: serving

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    VIRTUAL_ENV=/app/.venv \
    PATH=/app/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

WORKDIR /app

# Base: git for registry URIs, curl for healthchecks, uv for locked installs.
RUN apt-get update \
  && apt-get install -y --no-install-recommends git curl \
  && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /bin/

# Install from the locked root package definition.
COPY pyproject.toml /app/pyproject.toml
COPY uv.lock /app/uv.lock
COPY README.md /app/README.md
COPY configs /app/configs
COPY src /app/src

# Install the package and runtime dependencies from the root lockfile.
RUN uv sync --frozen --no-dev

# Serving image
FROM base AS serving

EXPOSE 8000
CMD ["uv", "run", "--no-dev", "uvicorn", "ml_lifecycle_platform.serving.app:app", "--host", "0.0.0.0", "--port", "8000"]

# Platform image (pipeline/promote/rollback one-shot jobs)
FROM base AS platform

# docker-compose overrides CMD per service.
CMD ["uv", "run", "--no-dev", "python", "-m", "ml_lifecycle_platform.pipeline.orchestrate"]
