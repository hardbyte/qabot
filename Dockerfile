# Multi-stage Dockerfile to build a lean Docker image for qabot

# Stage 1: Build stage
FROM python:3.12 AS build

# Install system dependencies
RUN <<EOT
apt-get update -qy
apt-get install -qyy \
    -o APT::Install-Recommends=false \
    -o APT::Install-Suggests=false \
    build-essential \
    ca-certificates
rm -rf /var/lib/apt/lists/*
EOT

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set environment variables
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=python3.12 \
    UV_PROJECT_ENVIRONMENT=/app

# Set working directory
WORKDIR /app

# Copy pyproject.toml and uv.lock to install dependencies
COPY pyproject.toml /_lock/
COPY uv.lock /_lock/

# Sync dependencies using UV, but don't install the project yet
RUN --mount=type=cache,target=/root/.cache \
    cd /_lock && \
    uv sync --frozen --no-dev --no-install-project

# Copy the application code to the build stage
COPY . /app

# Install only the application (without dependencies)
RUN --mount=type=cache,target=/root/.cache \
    uv pip install --no-deps /app

# Runtime Stage
FROM python:3.12

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/bin:$PATH"

# Set working directory
WORKDIR /app

# Install runtime dependencies (no build tools or UV)
RUN <<EOT
apt-get update -qy
apt-get install -qyy \
    -o APT::Install-Recommends=false \
    -o APT::Install-Suggests=false \
    python3.12 \
    libpython3.12
apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
EOT

# Copy the virtual environment and application from the build stage
COPY --from=build /app /app

# Set the entrypoint to the qabot command line tool
ENTRYPOINT ["python", "-m", "qabot.cli"]
