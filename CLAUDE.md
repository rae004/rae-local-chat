# CLAUDE.md

Agent guide for rae-local-chat. Read fully before changing anything.

## What this is

A React Vite SPA + FastAPI + Postgres chat UI talking to a local Ollama server at
`http://workhorse:11434`. Streaming responses, persisted history, `docker compose up`
is dev.

## Stack (locked)

- **Frontend** (`frontend/`): React, Vite, TypeScript, TanStack Query, TanStack Router,
  Tailwind 4 + DaisyUI 5. Themes `cyberpunk` (light) / `dracula` (dark).
- **Backend** (`api/`): FastAPI, Pydantic schemas, SQLAlchemy async. Proxies Ollama NDJSON
  → SSE.
- **Data layer** (`db/`): SQLAlchemy ORM models, async engine/session, Alembic. No Dockerfile,
  no compose service — `api/` depends on it as a uv workspace member.
- **DB**: Postgres in compose.

## Decisions — do not relitigate

1. **No pnpm workspaces.** One Node package (`frontend/`). Root `package.json` scripts are the
   orchestrator. **Never add a Makefile.**
2. **No TanStack Form.** The prompt box is `useState` + `onSubmit`.
3. **Query owns persisted history, not the stream.** Streaming is `fetch` + `ReadableStream`
   in a plain hook (`useChatStream`). Query owns `useChats()` / `useMessages(chatId)`. On
   stream end, `queryClient.setQueryData(['messages', chatId], …)` splices the finished
   message in.
4. **Python `requires-python = ">=3.14"`**, runtime image `python:3.14-slim`. Node `>= 24.22.1`.

## House rules

- Python: **uv only**, never bare `pip`. `uv add --package rae-api …` / `--package rae-db …`.
  One lockfile at the root.
- Node: **pnpm** via corepack. Lockfile committed.
- Branch per milestone (`milestone-a-scaffold`), small commits, PR to `main`, human reviews
  every diff. CI (ruff, mypy, pytest, oxlint, tsc, vitest) must be green.
- **Never stack PRs.** Every PR targets `main`; the next milestone branch is cut only after
  the previous PR is merged. Delete the branch after merge. (A stacked PR once merged into
  its feature branch instead of `main`.)
- Frontend deps live in the container's anonymous `node_modules` volume, which compose
  keeps across rebuilds. After `pnpm add`, run `pnpm frontend:deps`
  (`docker compose up -d --build -V frontend`) — without `-V` pnpm's deps check fails on
  start and the container crash-loops.
- Commits end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
  PR descriptions end with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- rae004 is terse-decisive and learning-first: recommend, then confirm. Keep answers short.

## Commands

See `package.json` scripts: `pnpm dev | down | migrate | migration | lint | typecheck | test`.

## Milestones

- **A** scaffold + echo endpoint ✅ · **B** SSE streaming ✅ · **C** history + sidebar ✅
  · **D** polish: theme toggle, model selector (`/models` ← Ollama `/api/tags`), markdown.
- App display name is **Rae Bot**; repo stays `rae-local-chat`.
