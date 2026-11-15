# rae-local-chat — "Rae Bot"

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
pnpm dev                     # api :8000, frontend :5173, postgres :5433
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

## Tools (MCP)

The model can call tools from MCP servers that run as compose services:

| server | what | how |
|---|---|---|
| `filesystem` | read/search files under `MCP_WORKSPACE` (default: this repo) | `@modelcontextprotocol/server-filesystem` via supergateway |
| `memory` | knowledge-graph notes that persist across chats | `@modelcontextprotocol/server-memory` via supergateway |
| `github` | repos, issues, PRs | GitHub's hosted server; set `GITHUB_PERSONAL_ACCESS_TOKEN` in `.env` |

Read-only tools run automatically and show up as collapsible cards in the chat. Tools that
modify state pause the reply and show **Approve** / **Deny** on their card; no click within
5 minutes (`TOOL_APPROVAL_TIMEOUT`) counts as deny, and the model is told either way so it
can carry on. Decisions are stored with the chat. `GET /tools` lists the catalogue and
per-server status; the **Tools** toggle in the composer turns tool use off per message.
Only models whose Ollama `capabilities` include `tools` can use them. `SYSTEM_PROMPT` sets
the opening system message; tool-use guidance is appended automatically when tools are on.

## Repo settings

GitHub settings for this repo (merge options, Actions permissions, the `main` ruleset) are
files in [`.github/repo/`](.github/repo/). `pnpm repo:diff` shows drift, `pnpm repo:apply`
pushes the files. CI diffs on every PR that touches them.
