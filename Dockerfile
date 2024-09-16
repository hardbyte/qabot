# Multi-stage Dockerfile to build a lean Docker image for qabot

# Stage 1: Build stage
FROM python:3.11-slim AS build

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml poetry.lock ./
COPY qabot ./qabot

# Install dependencies
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

# Stage 2: Final stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy only the necessary files from the build stage
COPY --from=build /app /app

# Set the entrypoint to the qabot command line tool
ENTRYPOINT ["qabot"]
