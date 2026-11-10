---
inclusion: always
---

# Repository structure

Proposed layout (created in S01, not before):

```text
imbooored/
├─ apps/
│  ├─ web/            Next.js App Router, TypeScript, Tailwind (UI only, no Spotify calls)
│  ├─ api/            Flask + Flask-SocketIO (REST /api/v1, sockets, OAuth exchange, search proxy)
│  └─ worker/         asyncio worker (polling, token manager, queue push, ghost rooms, reconcile)
├─ packages/
│  ├─ contracts/      TS types generated from docs/api/openapi.yaml + JSON Schemas for socket events
│  └─ py-shared/      Python code shared by api and worker: settings, logging/redaction, db roles,
│                     close_room, MusicProvider interface + Fake/Replay, token vault
├─ infra/             docker-compose.yml, Dockerfiles, CI workflows, Cloudflare/platform config
├─ docs/              planning docs (source of truth), api/openapi.yaml, reference/
└─ .kiro/             steering/, specs/, hooks/
```

Rules:

- Docs first. A change to behavior updates the matching doc in `docs/` in the same commit.
- `docs/api/openapi.yaml` is the REST contract. Regenerate `packages/contracts` from it; never hand-edit generated files.
- Shared Python logic lives in `packages/py-shared`. Do not copy code between `apps/api` and `apps/worker`.
- Only `packages/py-shared/.../music/spotify.py` (or equivalent single module) may contain Spotify URLs.
- Migrations live in `apps/api/migrations` (Alembic) and are the only place DDL is written.
- Tests sit next to the app: `apps/<app>/tests/{unit,integration,contract}`; E2E in `apps/web/e2e`.
- One spec per folder in `.kiro/specs/<NN-feature-name>/`. One task per chat session.
- Do not create files outside this layout without an ADR.
