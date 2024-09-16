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
# Install Poetry
ARG POETRY_VERSION=1.8.3
ENV POETRY_HOME=/opt/poetry
ENV VIRTUAL_ENV=/app/.venv
ENV POETRY_NO_INTERACTION=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_VIRTUALENVS_IN_PROJECT=false

RUN pip install "poetry==${POETRY_VERSION}"

# Set working directory
WORKDIR /app

# Copy pyproject.toml and poetry.lock to install dependencies
COPY pyproject.toml poetry.lock /app/

# Install dependencies without the application code
RUN --mount=type=cache,target=/root/.cache \
    python3 -m venv ${VIRTUAL_ENV} && \
    poetry install --no-root

# Copy the application code to install the app itself
COPY . /app

# Install only the application (no dependencies)
RUN --mount=type=cache,target=/root/.cache \
    poetry install --no-dev --no-interaction --no-ansi

# Runtime Stage
FROM python:3.12

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"


# Set working directory
WORKDIR /app

# Copy only the necessary files from the build stage
# Copy the virtual environment and application code from the build stage
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app /app


# Set the entrypoint to the qabot command line tool
ENTRYPOINT ["python", "-m", "qabot.cli"]
