# falk - Governed data agent powered by semantic layers
# Supports: falk slack, falk mcp
# Base: bookworm (not Alpine) for Kaleido chart export compatibility
FROM python:3.11-slim-bookworm AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build

# Copy dependency manifests
COPY pyproject.toml uv.lock ./

# Copy package sources (hatch needs these for editable/sync)
COPY src/ src/
COPY app/ app/

# Install falk (no dev extras)
RUN uv sync --frozen --no-dev --no-install-project && \
    uv sync --frozen --no-dev

# Runtime stage
FROM python:3.11-slim-bookworm

# Optional: libgl1 for Kaleido if chart export fails in minimal images
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for production
RUN adduser --disabled-password --gecos "" falk

# Copy project and install venv at final path (avoids shebang breakage from relocation)
WORKDIR /build
COPY --from=builder /build/pyproject.toml /build/uv.lock ./
COPY --from=builder /build/src ./src
COPY --from=builder /build/app ./app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT="/home/falk/.venv"
RUN uv sync --frozen --no-dev && chown -R falk:falk /home/falk/.venv

USER falk
WORKDIR /app
ENV PATH="/home/falk/.venv/bin:$PATH"

# Project dir is mounted at /app at runtime
# falk discovers config from cwd (falk_project.yaml, semantic_models.yaml, .env)
EXPOSE 8000

# Default: Slack bot. Override for web chat or MCP:
#   docker run ... falk falk mcp
CMD ["falk", "slack"]
