# falk project Dockerfile (scaffold)
# 
# Builds a container that:
# - Installs falk from PyPI (package: falk-ai)
# - Copies your falk project files into /app
# - Exposes port 8000 for web or HTTP MCP
# 
# Usage:
#   docker build -t my-falk-project .
#   docker run --env-file .env -p 8000:8000 my-falk-project
# 
# Default command: falk chat (web UI at http://localhost:8000)
# You can change this to:
#   CMD ["falk", "mcp", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
# or:
#   CMD ["falk", "slack"]

FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Optional system dependencies for chart export (Plotly + Kaleido)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Install falk from PyPI
RUN pip install --no-cache-dir "falk-ai"

# Copy project files (config, knowledge, evals, etc.)
COPY . /app

EXPOSE 8000

# Default: web chat for local / simple deployments.
# Change this CMD to "falk mcp ..." or "falk slack" as needed.
CMD ["falk", "chat"]

