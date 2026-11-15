FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

# The only binaries the tool may run that aren't in the base image.
RUN apt-get update && apt-get install -y --no-install-recommends git ripgrep \
    && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app

# Dependency layer: workspace manifests only, no project sources.
COPY pyproject.toml uv.lock .python-version ./
COPY api/pyproject.toml api/
COPY db/pyproject.toml db/
COPY mcp-servers/shell/pyproject.toml mcp-servers/shell/
RUN uv sync --frozen --no-dev --package rae-mcp-shell --no-install-workspace

COPY mcp-servers/shell/ mcp-servers/shell/
RUN uv sync --frozen --no-dev --package rae-mcp-shell

# Unprivileged; the workspace is mounted read-only at /workspace by compose.
RUN useradd --system --uid 10001 --home /tmp shell
USER shell
ENV WORKSPACE=/workspace HOST=0.0.0.0 PORT=8000
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "rae-mcp-shell"]
