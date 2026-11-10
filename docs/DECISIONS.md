# Decisions (ADR log) and open questions

Status: DRAFT · Written 2026-11-09 · All ADRs are **Proposed** until the owner marks them Accepted.

## Purpose

Record every architectural decision, especially where we deviate from the reference design chat ([`reference/Panduan Vibe Coding Bebas Slop.md`](./reference/Panduan%20Vibe%20Coding%20Bebas%20Slop.md)), plus the questions only the owner can answer. Format per ADR: context, decision, alternatives, consequences.

## Content

### Open questions for the owner (ordered by how much they block)

| ID | Question | Blocks | Proposed default |
|---|---|---|---|
| OQ-0 | `.kiro/steering/security.md` is not in the repo (Phase 1 not run). Commit it from playbook §4? | Everything (it is the rule source) | Yes, verbatim |
| OQ-1 | Run the spike now. If K1/K2 pass, accept that imbooored stays a ≤ 5-host closed alpha for as long as Spotify Dev Mode rules hold (no realistic path to Extended Quota for an individual)? | All specs | Yes, build the alpha; revisit at M5 |
| OQ-2 | Spotify Client IDs per environment. Security rule 23 wants separate IDs; Spotify Developer Policy §VII says one Security Code per SDA and no more than one per SDA; quota is shared per developer account anyway | S01, S03, rule 23 | ADR-010 option B |
| OQ-3 | Vibe Points vs policy "Do not create a game". Keep as private tally, defer, or drop? | S07 scope | Private tally, no ranking (ADR-011) |
| OQ-4 | Feed and rooms require sign-in, or public read-only? | S06, rule 13 exceptions | Sign-in required (ADR-006) |
| OQ-5 | Hosting platform, domain, and secret manager | S01 (CI/CD, rule 3, 15, 22) | Owner choice; requirements: containers for api/worker with WebSockets, managed Postgres with PITR + roles, managed Redis with TLS, secret store, private networking or Cloudflare-only ingress |
| OQ-6 | Alert channel (Telegram, email, push) | S05, S10 | Whatever reaches the owner's phone in < 1 min |
| OQ-7 | Minimum user age | S02 | 18+ self-declared |
| OQ-8 | Retention: audit log, closed rooms, suggestions | S10a | Audit 400 days; suggestions anonymized after 180 days |
| OQ-9 | Who is the data controller in the privacy policy (person or entity)? Get legal review for UU PDP? | S10a | Owner as individual; legal review before invites |
| OQ-10 | Package manager pnpm or npm | S01 | pnpm workspaces |
| OQ-11 | Light theme in MVP? | S08 | No, dark only, revisit after alpha |

### Dependency approvals

CI gate in [08](./08-TEST_STRATEGY.md) §5 item 11 checks this table. Empty until S01. Each row: package, registry URL, version, reason, owner approval date.

| Package | Registry URL | Version | Reason | Approved (date) |
|---|---|---|---|---|
| (none yet) | | | | |

### ADR-001 Closed alpha with ≤ 5 hosts; listeners never authorize Spotify

- Context: Dev Mode allows 5 allowlisted users; Extended Quota is organization-only with 250k MAU ([01](./01-SPOTIFY_CONSTRAINTS.md) C2, C4). The reference design assumed hundreds of rooms.
- Decision: Only hosts connect Spotify. Max 5 hosts including the owner. Listeners use Clerk accounts only.
- Alternatives: every user connects Spotify (hits the 5-user wall immediately); multiple Client IDs to multiply allowlists (likely policy violation, §VII).
- Consequences: product ceiling is 5 concurrent rooms. Listener features must not need a Spotify user token.

### ADR-002 Identity via Clerk; backend verifies tokens with a maintained library

- Context: Reference used custom JWT cookie `app_session`. Rule 2 forbids hand-built auth.
- Decision: Clerk for sign-in. Flask verifies Clerk session tokens from `Authorization: Bearer` using Clerk's official Python SDK (`clerk-backend-api`, `authenticate_request`) or PyJWT's JWKS client if the SDK does not fit Flask. Checks: signature, `iss`, `exp`, `nbf`, `azp` allow-list. Choice made in S02 after reading current SDK docs.
- Alternatives: Supabase Auth, Auth0 (both allowed by rule 2; Clerk chosen in the brief).
- Consequences: Clerk outage blocks new sessions; cached JWKS keeps verification working until key rotation.

### ADR-003 Flask-SocketIO in threaded mode, single instance, no eventlet

- Context: Reference ran `gunicorn -k eventlet -w 1`. The eventlet project discourages new usage; Flask-SocketIO docs list a threaded worker with `simple-websocket`; gunicorn supports only one Socket.IO worker per instance.
- Decision: `gunicorn -w 1 --threads N` + `simple-websocket`, one API instance for MVP, Redis message queue enabled from day one so the worker can emit.
- Alternatives: gevent (monkey patching; WebSocket support via gevent-websocket, which looks unmaintained, UNVERIFIED); python-socketio ASGI server (changes the stack).
- Consequences: one thread per WebSocket; fine for ≤ 100 sockets, not for 6,000 ([02](./02-ARCHITECTURE.md) §7). Scale-out path documented.

### ADR-004 Worker owns host tokens and all Player calls; access tokens live in worker memory only

- Context: Reference stored host access tokens in Redis plaintext and refresh tokens plaintext in DB; poller, refresher, and Flask all called Spotify.
- Decision: Refresh tokens encrypted in Postgres (ADR-016). Only the worker decrypts them and holds access tokens in memory. API calls Spotify only for the OAuth code exchange (stores ciphertext, discards access token) and for client-credentials search/track lookup. Approved suggestions reach the worker through a Redis Stream.
- Alternatives: separate token-refresher process (reference): more moving parts for 5 hosts.
- Consequences: API compromise does not expose refresh tokens (API role cannot SELECT ciphertext). Worker restart costs ≤ 5 refresh calls. Client secret is needed in both api and worker.

### ADR-005 MusicProvider abstraction with Fake and Replay implementations

- Decision: Interface in [01](./01-SPOTIFY_CONSTRAINTS.md) §4. Spotify, Fake, Replay implementations; demo mode uses Replay.
- Consequences: tests and load tests never hit Spotify; a future provider can be added without touching rooms/votes.

### ADR-006 Feed requires sign-in

- Context: Reference had an open feed with no auth or limit. Rule 13 requires authn on every endpoint unless an ADR lists an exception.
- Decision: All `/api/v1` endpoints except `/healthz` and the Clerk webhook require a Clerk session.
- Alternatives: public read-only feed with IP limits and Cloudflare bot rules (better discovery, scraping risk on Spotify metadata).
- Consequences: landing page shows no live data. Revisit with OQ-4.

### ADR-007 Normalized tags with exact match

- Context: Reference used `ilike('%tag%')` on a comma-separated string.
- Decision: `tags(slug)` + `room_tags`, slug `^[a-z0-9_]{2,30}$`, exact match with bound parameter.
- Consequences: `#PostPunk` and `#postpunk` are the same tag; display is lowercase.

### ADR-008 Votes and thresholds in Postgres; accept rare duplicate queue pushes

- Context: Reference used Redis Hash/Set (`HINCRBY`, `SADD`) as the vote store, creating a Redis/DB split.
- Decision: `votes` PK + `cast_vote` SQL function that inserts and flips `pending → approved` once. Redis only fans out events. Worker claims `approved → pushing` before calling Spotify. If Spotify succeeded but our commit failed, a retry may queue the track twice; we log `queue.duplicate_suspected`.
- Alternatives: Redis Lua for votes (faster, not needed at this volume).
- Consequences: one source of truth; vote latency is a DB round trip (target p95 ≤ 300 ms).

### ADR-009 Alembic migrations with SQLAlchemy Core

- Decision: Alembic revisions containing explicit SQL for tables, RLS, policies, partial indexes, triggers. SQLAlchemy Core (not ORM sessions) for queries with bound parameters.
- Alternatives: dbmate/sqitch (plain SQL, no Python coupling); SQLAlchemy ORM (implicit queries make RLS `SET LOCAL` handling easier to forget).
- Consequences: one migration tool for api and worker, owned by `imb_migrator`.

### ADR-010 Spotify Client IDs per environment (pending OQ-2)

- Context: Rule 23 requires separate Spotify Client IDs per env. Developer Policy §VII: separate Security Code per SDA, no more than one per SDA. Quota is per developer account, shared by all its Client IDs (C5). Each Client ID has its own 5-user allowlist.
- Options:
  - A. One Client ID for all envs: policy-safe, but dev/staging tokens and secrets are prod-grade, violates rule 23.
  - B. Prod Client ID + one non-prod Client ID (dev and staging share), non-prod allowlist contains only the owner's test accounts, never real hosts. Treat staging/dev as the "same SDA in development"; ask Spotify support/community to confirm.
  - C. One Client ID per env (rule 23 literal). Highest policy risk; looks like multiplying allowlists.
- Proposed: B, with written confirmation sought from Spotify before M3. Status: open.
- Consequences: staging traffic draws from the same quota as prod; non-prod workers must stop during quota incidents.

### ADR-011 Vibe Points are a private, non-competitive tally (pending OQ-3)

- Context: Developer Policy III forbids creating a game. Points plus leaderboards look like gamification.
- Decision: Append-only ledger; a user sees only their own balance; no ranking, no rewards, no badges in MVP.
- Consequences: low risk, low motivation value. Dropping it entirely shrinks S07.

### ADR-012 Mutations over REST; Socket.IO for fan-out and presence

- Context: Reference sent `suggest_track` and `upvote_track` over sockets, trusting client `room_id`/`track_id` and with no per-event authz or limits.
- Decision: Suggest, vote, reject, close are REST. Socket inbound events: `room:join`, `room:leave`, `presence:heartbeat`, `auth:refresh` only, each schema-validated, rate-limited, and authorized.
- Consequences: one authz/rate-limit/idempotency path; slightly higher latency for votes (HTTP vs socket), acceptable.

### ADR-013 `/healthz` is exempt from authn/authz (rule 13 exception)

- Decision: `GET /healthz` returns `{"status":"ok"}` with no auth. Rate-limited at the edge (Cloudflare) at 60/min/IP. Exposes no versions, no dependency status. Worker health is an internal port not routed publicly.
- Second exception: `POST /api/v1/webhooks/clerk` has no user authn; it is authenticated by Svix signature (rule 18) and IP rate-limited.

### ADR-014 Spotify OAuth callback lands on the web app; API exchanges via POST

- Context: The API cannot see the Clerk session on a top-level redirect to the API domain.
- Decision: `redirect_uri` = `https://<web-domain>/spotify/callback` (exact, per env). That page POSTs `{code, state}` with the Clerk token to the API. API checks state belongs to that user, single use, ≤ 10 min, and uses the stored PKCE verifier.
- Consequences: authorization code passes through the browser (normal for this flow); never logged; page strips query from history immediately.

### ADR-015 Presence via heartbeat-scored sorted sets

- Context: Reference used plain Sets of sids and flushed them on server start; a crash left ghost sids keeping rooms "occupied".
- Decision: ZSet `sid → last_seen_ms`, heartbeat every 30 s, entries older than 90 s ignored and trimmed. No startup flush needed.
- Consequences: listener counts lag reality by up to 90 s.

### ADR-016 Token vault with AES-256-GCM and key ids

- Decision: `cryptography` AESGCM, 96-bit random nonce per encryption, AAD = `user_id‖key_id`, keys loaded from the secret store as `key_id → key`, active key id configurable, re-encrypt job for rotation.
- Alternatives: Fernet (simpler, AES-128-CBC+HMAC, also allowed by the rules); cloud KMS envelope encryption (better, depends on OQ-5).
- Consequences: losing keys forces all hosts to reconnect (offline sealed copy in [09](./09-OPS_RUNBOOK.md)).

### ADR-017 Monorepo with pnpm workspaces and uv workspaces

- Decision: `apps/web` + `packages/contracts` under pnpm; `apps/api`, `apps/worker`, `packages/py-shared` under uv. Layout in `.kiro/steering/structure.md`.
- Consequences: two lockfiles to audit; both in CI.

### ADR-018 Rate limiting with Flask-Limiter and the `limits` library on Redis

- Decision: REST via Flask-Limiter (Redis storage, moving window). Socket events call the same `limits` strategies directly. Mutations fail closed if Redis is down; `GET /feed` fails open behind Cloudflare limits.
- Alternatives: hand-written INCR/EXPIRE limiter (small, but one more security-relevant thing to maintain).
- Consequences: two new dependencies (approval needed).

### ADR-019 Socket authentication and lifetime

- Decision: Clerk token in the Socket.IO `auth` payload (not cookies), verified on connect; Origin allow-list check; `auth:refresh` extends a 60-minute socket max age; Clerk `session.ended`/`session.revoked` webhooks disconnect that session's sockets.
- Consequences: revoked sessions lose realtime within seconds (webhook delivery time, UNVERIFIED) or at most 60 min.

### ADR-020 Cover art shown unaltered

- Context: Policy requires attribution and link-back; artwork guidance says do not distort (third-party summary, UNVERIFIED).
- Decision: No blurred/tinted artwork backgrounds, no animation of artwork. Solid zinc surfaces.

### Deviations from the reference design (index)

| Reference behavior | Replaced by |
|---|---|
| Custom JWT cookie auth | ADR-002, ADR-019 |
| `cors_allowed_origins="*"` | env allow-list ([05](./05-SECURITY_THREAT_MODEL.md) rule 11) |
| Plaintext access tokens in Redis, refresh tokens in DB | ADR-004, ADR-016 |
| Socket handlers trusting client ids, no authz/limits | ADR-012, [04](./04-API_AND_EVENTS.md) §4 |
| `ilike('%tag%')` on CSV | ADR-007 |
| Raw Spotify search payload with user token | client credentials + DTO + cache ([04](./04-API_AND_EVENTS.md)) |
| Open feed | ADR-006 |
| One-active-room in app code | partial unique index ([03](./03-DATA_MODEL.md) I1) |
| Ghost cleanup order, plaintext keys, startup flush | ADR-015, shared `close_room`, reconcile loop |
| eventlet `-w 1` | ADR-003 |
| Vote/queue without idempotency or retry | ADR-008, push retry policy ([02](./02-ARCHITECTURE.md) §6) |
| APScheduler / separate token refresher | single asyncio worker (ADR-004) |

## Assumptions

- The owner reviews and accepts/rejects each ADR before S01 starts.

## Open questions

See the table at the top.

## Verified sources

| Fact | Source | Accessed |
|---|---|---|
| Spotify policy §III (games), §VII (Security Codes) | https://developer.spotify.com/policy | 2026-11-09 |
| Eventlet discourages new users | https://eventlet.readthedocs.io/en/latest/asyncio/migration.html | 2026-11-09 |
| Flask-SocketIO deployment options | https://flask-socketio.readthedocs.io/en/latest/deployment.html | 2026-11-09 |
| Clerk Python SDK exists | https://github.com/clerk/clerk-sdk-python (page did not load content; API UNVERIFIED) | 2026-11-09 |
