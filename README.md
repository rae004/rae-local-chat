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
| `filesystem` | read/search/write files under `MCP_WORKSPACE` (default: this repo), runs as `MCP_UID:MCP_GID` so writes are owned by you | `@modelcontextprotocol/server-filesystem` via supergateway |
| `memory` | knowledge-graph notes that persist across chats | `@modelcontextprotocol/server-memory` via supergateway |
| `github` | repos, issues, PRs | GitHub's hosted server; set `GITHUB_PERSONAL_ACCESS_TOKEN` in `.env` |
| `shell` | `ls cat head tail grep rg find wc git` inside the workspace, read-only mount, always asks | built in-tree: `mcp-servers/shell/` |

Read-only tools run automatically and show up as collapsible cards in the chat. Tools that
modify state pause the reply and show **Approve** / **Deny** on their card; no click within
5 minutes (`TOOL_APPROVAL_TIMEOUT`) counts as deny, and the model is told either way so it
can carry on. **Always allow** on a card approves and records a standing rule for that tool
(`tool_allow_rules` table), so it runs without asking from then on, including later in the
same reply; such calls are badged `auto · allowed`. Rules are listed and revoked under the
Tools gear, or via `GET`/`DELETE /tools/allow-rules`. Decisions are stored with the chat. `GET /tools` lists the catalogue and
per-server status; the **Tools** toggle in the composer turns tool use off per message.
The gear next to it switches whole servers on or off: an off server's tools are left out of
the prompt entirely (the count on the toggle is what the model will actually see). Choices
are per browser; GitHub starts off because its 46 tools swamp the catalogue for small models.
Only models whose Ollama `capabilities` include `tools` can use them. `SYSTEM_PROMPT` sets
the opening system message; tool-use guidance is appended automatically when tools are on.

## Repo settings

GitHub settings for this repo (merge options, Actions permissions, the branch ruleset) come
from the shared baseline in [`rae004/.github`](https://github.com/rae004/.github) and are
applied from there. The only part kept here is
[`.github/repo-settings.json`](.github/repo-settings.json), which lists the CI jobs that must
pass before a PR can merge.
