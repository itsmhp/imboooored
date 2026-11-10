---
inclusion: fileMatch
fileMatchPattern: 'apps/api/**'
---

# apps/api conventions

- Every route and socket handler declares authn, authz, rate limit, and a Pydantic schema (`extra="forbid"`). The route-registry test fails otherwise. Exceptions only per ADR-013.
- Authorize from server state. Never trust client-sent `room_id`, `user_id`, role, or track metadata.
- Open one DB transaction per request; first statements `SET LOCAL app.user_id` / `app.role` with bound values. Connect as `imb_api`, never as owner.
- SQL: SQLAlchemy Core with bound parameters only. No f-strings or `%` in SQL. No `LIKE` on user input.
- Errors: raise typed app errors mapped to the envelope in `docs/04-API_AND_EVENTS.md` §2. Indonesian `message`, no stack traces, no upstream bodies.
- Logging: `structlog` via `py-shared` logger only. No `print`. Never log tokens, codes, cookies, emails, or request bodies.
- Spotify: only through `MusicProvider`. API uses it for code exchange, search, and `get_track`. No Player endpoints here.
- Audit: write `audit_log` rows for actions listed in `docs/03-DATA_MODEL.md` in the same transaction as the change.
- Naming: blueprints `<area>_bp`, services `<area>_service.py`, schemas `<Area>Request/<Area>Response`. Routes kebab-case under `/api/v1`.
- Tests: unit for services, integration against Compose Postgres/Redis, authz + abuse cases from `docs/08-TEST_STRATEGY.md` §3 for every endpoint touching auth, tokens, rooms, votes. Write the failing test first.
- Update `docs/04-API_AND_EVENTS.md` and `docs/api/openapi.yaml` in the same commit as any contract change.
