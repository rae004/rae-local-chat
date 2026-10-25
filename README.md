# rae-local-chat

Classic AI chat UI (sidebar of chats, streaming main pane, model selector) over a
local Ollama server. React/Vite SPA + FastAPI + Postgres, all in docker compose.

## Requirements

- Docker + Compose v2
- Node >= 24.22.1 (pnpm via corepack: `corepack enable`)
- [uv](https://docs.astral.sh/uv/) — Python 3.14 is fetched automatically
- An Ollama server reachable at `http://workhorse:11434` (set `WORKHORSE_IP` in `.env`)

## Dev

```sh
cp .env.example .env         # edit WORKHORSE_IP if needed
pnpm dev                     # api :8000, frontend :5173, postgres :5432
```

The api container runs `alembic upgrade head` on start.

| Script            | Does                                             |
| ----------------- | ------------------------------------------------ |
| `pnpm dev`        | `docker compose up --build`                      |
| `pnpm down`       | stop everything                                  |
| `pnpm migrate`    | apply migrations inside the api container        |
| `pnpm migration`  | autogenerate a new migration (`-- "message"`)    |
| `pnpm lint`       | ruff + eslint                                    |
| `pnpm typecheck`  | mypy + tsc                                       |
| `pnpm test`       | pytest + vitest                                  |

## Layout

- `api/` — FastAPI app (`rae_api`), depends on `db/`
- `db/` — SQLAlchemy models, async session, Alembic migrations (`rae_db`)
- `frontend/` — Vite + React + TanStack Router/Query + Tailwind/DaisyUI

Python is a single uv workspace rooted here (`uv sync` installs both packages).
