---
inclusion: fileMatch
fileMatchPattern: 'apps/worker/**'
---

# apps/worker conventions

- One asyncio process. Hold the Redis leader lock before polling; stop work when the lock is lost.
- All Spotify calls go through `MusicProvider`. Every call first checks the breaker and takes from the global and per-room budget.
- Honor `Retry-After` on 429 for all rooms. `QUOTA_EXCEEDED` opens the breaker for 15 min and raises an alert. Never retry in a tight loop; use capped exponential backoff with jitter.
- Access tokens live in process memory only. Never write them to Redis, Postgres, logs, or exceptions. Refresh under a per-host `asyncio.Lock` plus a `SELECT ... FOR UPDATE` row lock.
- `invalid_grant` → connection `needs_reauth`, `close_room(reason="token_revoked")`. Do not retry.
- Poll only rooms with presence in the last 90 s. Use the adaptive intervals in `docs/02-ARCHITECTURE.md` §2.
- Close rooms only through the shared `close_room` in `py-shared` (DB first, then fixed Redis key list, then emit).
- Emit through `AsyncRedisManager(write_only=True)` on the shared channel. Payloads are DTOs from `docs/04-API_AND_EVENTS.md`, never raw Spotify JSON.
- Blocking DB calls run in a thread (`asyncio.to_thread`) or use an async driver; never block the loop.
- Connect to Postgres as `imb_worker`. Bound parameters only.
- Every loop iteration is wrapped so one room's error cannot stop others; log with room id, never with tokens.
- Tests: drive everything with `FakeMusicProvider` and a fake clock (intervals, breaker, budgets, ghost timers, push retries, reconcile). Never hit real Spotify in tests.
