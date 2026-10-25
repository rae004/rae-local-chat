FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app

# Dependency layer: workspace manifests only, no project sources.
COPY pyproject.toml uv.lock .python-version ./
COPY api/pyproject.toml api/
COPY db/pyproject.toml db/
RUN uv sync --frozen --no-dev --all-packages --no-install-workspace

COPY api/ api/
COPY db/ db/
RUN uv sync --frozen --no-dev --all-packages

EXPOSE 8000
CMD ["sh", "-c", "uv run --no-sync alembic -c db/alembic.ini upgrade head && uv run --no-sync uvicorn rae_api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir api/src --reload-dir db/src"]
