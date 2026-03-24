FROM python:3.12-slim AS base

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY src/ src/
COPY scripts/ scripts/
COPY config.example.yaml ./

# Install the project itself
RUN uv sync --frozen --no-dev

EXPOSE 8080

# Run with uvicorn
CMD ["uv", "run", "uvicorn", "clawhub_mirror.main:app", "--host", "0.0.0.0", "--port", "8080"]
