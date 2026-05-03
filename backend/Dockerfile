# ── Stage 1: base ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps needed by asyncpg, cryptography, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency manifests
COPY pyproject.toml ./

# ── Stage 2: development ───────────────────────────────────────────────────────
FROM base AS development

# Install all deps including dev extras
RUN uv pip install --system -e ".[dev]"

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Stage 3: production ────────────────────────────────────────────────────────
FROM base AS production

# Install only production deps
RUN uv pip install --system .

COPY . .

# Non-root user for security
RUN addgroup --system app && adduser --system --group app
USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
