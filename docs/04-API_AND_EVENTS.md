# 04 · API and Realtime Events

Status: DRAFT · Written 2026-11-09 · Machine-readable contract: [api/openapi.yaml](./api/openapi.yaml)

## Purpose

Define every REST endpoint and Socket.IO event with its authentication, authorization, rate limit, schema, and errors. `packages/contracts` is generated from `openapi.yaml`; Socket.IO payload schemas live in `packages/contracts/events` as JSON Schema (hand-written, reviewed with this doc).

## Content

### 1. Principles

- Base path `/api/v1`. Breaking changes get `/api/v2`; additive changes do not.
- **Mutations go over REST. Socket.IO carries server → client fan-out plus join/leave/heartbeat** (ADR-012). The reference design sent suggest/vote over sockets; REST gives us one place for authz, rate limits, idempotency, and audit.
- Authentication: `Authorization: Bearer <Clerk session token>`. The API verifies signature against Clerk JWKS, `exp`, `nbf`, `iss` (our Clerk instance), and `azp` against the allow-listed web origins (Clerk manual verification guide). Then it loads `users` by `sub` → `clerk_user_id`.
- Authorization is server-side for every call (rule 19). Roles: `listener` < `host` < `admin`. "Member" = has a live presence entry in the room within 90 s.
- Every request gets `X-Request-Id` (generated if absent, echoed back, logged).
- Request bodies: JSON only, max 8 KB (`MAX_CONTENT_LENGTH`), validated by Pydantic models with `extra="forbid"`.
- Responses never contain raw Spotify payloads, tokens, or emails.

### 2. Error envelope

```json
{ "error": { "code": "ROOM_NOT_LIVE", "message": "Room ini sudah ditutup.", "request_id": "01J...", "details": {} } }
```

`message` is Indonesian and safe to show. `details` never includes stack traces or upstream bodies.

| HTTP | code | When |
|---|---|---|
| 400 | `VALIDATION_FAILED` | schema error (`details.fields`) |
| 400 | `INVALID_JAM_LINK`, `INVALID_TAG`, `TOO_MANY_TAGS` | room input |
| 401 | `UNAUTHENTICATED` | missing/invalid/expired token |
| 403 | `FORBIDDEN` | role or ownership check failed |
| 403 | `SPOTIFY_NOT_ALLOWLISTED` | Spotify returned 403 after connect ([01](./01-SPOTIFY_CONSTRAINTS.md) C3) |
| 404 | `NOT_FOUND` | also used instead of 403 where existence would leak (other users' resources) |
| 409 | `ROOM_ALREADY_LIVE` | I1 violated (`details.room_id` = caller's own live room) |
| 409 | `ROOM_NOT_LIVE` | action on closed room |
| 409 | `SPOTIFY_NOT_CONNECTED`, `SPOTIFY_NEEDS_REAUTH` | host action without a usable connection |
| 409 | `IDEMPOTENCY_CONFLICT` | same `Idempotency-Key`, different body |
| 413 | `PAYLOAD_TOO_LARGE` | body > 8 KB |
| 429 | `RATE_LIMITED` | our limit; `Retry-After` header set |
| 503 | `SPOTIFY_UNAVAILABLE`, `SPOTIFY_QUOTA` | breaker open |
| 503 | `DEPENDENCY_UNAVAILABLE` | Postgres/Redis down |

### 3. REST endpoints

Rate limits are per authenticated user unless marked "IP". Implemented with Redis-backed counters (rule 13). Cloudflare adds a coarse per-IP limit in front of everything.

| Method | Path | Authn | Authz | Rate limit | Notes |
|---|---|---|---|---|---|
| GET | `/healthz` | none | none | IP 60/min (edge) | ADR-013 exception. Returns `{status}` only, no versions or dependency detail |
| GET | `/api/v1/me` | Clerk | self | 60/min | profile, role, spotify connection status, vibe points balance |
| PATCH | `/api/v1/me` | Clerk | self | 10/min | `display_name`, `age_confirmed` |
| POST | `/api/v1/webhooks/clerk` | Svix signature | n/a | IP 300/min | verify **before** parsing; reject timestamps older than 5 min; idempotent on `svix-id` |
| POST | `/api/v1/spotify/connect` | Clerk | role ≥ host | 5/10 min | returns `{authorize_url}`; stores state + PKCE verifier (10 min) |
| POST | `/api/v1/spotify/callback` | Clerk | state belongs to caller | 10/10 min | body `{code, state}` posted by the web callback page; exchanges code, calls `GET /me` to detect allowlist 403, encrypts refresh token |
| DELETE | `/api/v1/spotify/connection` | Clerk | self | 5/10 min | closes caller's live room, deletes vault row, audit |
| GET | `/api/v1/feed` | Clerk | any role | 60/min + IP 120/min | `?tag=slug&cursor=&limit≤20`; cursor = opaque base64 of `(created_at,id)` |
| GET | `/api/v1/tags/trending` | Clerk | any | 30/min | top 20 slugs by live rooms, from our tables only |
| POST | `/api/v1/rooms` | Clerk | role ≥ host, connection active | 5/hour | `Idempotency-Key` header required |
| GET | `/api/v1/rooms/{room_id}` | Clerk | any (live) / host or admin (closed) | 120/min | room + now-playing snapshot |
| PATCH | `/api/v1/rooms/{room_id}` | Clerk | owner host | 10/min | `vote_threshold` only |
| POST | `/api/v1/rooms/{room_id}/close` | Clerk | owner host or admin | 10/min | idempotent: 200 `{status:"closed"}` if already closed; admin path audits `room.force_close` |
| GET | `/api/v1/rooms/{room_id}/suggestions` | Clerk | any (live) | 60/min | `?status=pending,approved,queued&limit≤50` |
| GET | `/api/v1/search/tracks` | Clerk | member of ≥ 1 live room in last 10 min | 20/min, 200/day | `?q=` 1–100 chars, NFKC-normalized; returns ≤ 10 `TrackDTO` |
| POST | `/api/v1/rooms/{room_id}/suggestions` | Clerk | member, room live, account age ≥ 10 min | 5/10 min per room, 30/day | body `{track_id}`; metadata resolved server-side; returns existing item (200) if already active |
| PUT | `/api/v1/rooms/{room_id}/suggestions/{id}/vote` | Clerk | member, room live | 60/10 min | idempotent; 200 `{vote_count, status, voted:true}` |
| POST | `/api/v1/rooms/{room_id}/suggestions/{id}/reject` | Clerk | owner host | 30/10 min | `pending`/`approved` → `rejected`; audit |
| GET | `/api/v1/me/vibe-points` | Clerk | self | 30/min | balance + last 50 entries |
| POST | `/api/v1/me/exports` | Clerk | self | 1/day | 202, creates `deletion_requests(kind=export)` |
| GET | `/api/v1/me/exports/{id}` | Clerk | self | 30/min | status + short-lived download URL when done |
| POST | `/api/v1/me/deletion` | Clerk | self | 3/day | 202; requires body `{confirm:"HAPUS"}`; Clerk user deletion triggered by the job |
| GET | `/api/v1/admin/rooms` | Clerk | admin | 60/min | live rooms + breaker/budget state |
| PUT | `/api/v1/admin/users/{user_id}/role` | Clerk | admin | 10/min | `{role}`; audit `role.change`; host count capped at 5 |

#### Core schemas (summary; full in openapi.yaml)

- `TrackDTO`: `id, title, artists[], album, cover_url|null, duration_ms, spotify_url`.
- `NowPlayingDTO`: `track: TrackDTO|null, progress_ms, is_playing, observed_at_ms, state: playing|paused|nothing|stale`.
- `RoomCardDTO`: `id, host: {id, display_name}, tags[], jam_link, listener_count, now_playing, created_at`.
- `SuggestionDTO`: `id, track: TrackDTO, status, vote_count, threshold, suggested_by: {id, display_name}|null, voted_by_me, created_at`.
- `CreateRoomRequest`: `jam_link (≤200), tags[1..5] (raw, normalized server-side), vote_threshold 2..10 (default 3)`.

### 4. Socket.IO events

Namespace `/`. Server option `max_http_buffer_size` = 4 KB (inbound). `cors_allowed_origins` = explicit list from env (rule 11). Ping interval 25 s, timeout 20 s (library defaults, UNVERIFIED).

**Connect.** Client sends `auth: {token}` (Clerk session token). The `connect` handler: (1) checks `Origin` header is in the allow-list (CSWSH), (2) verifies the token as in §1, (3) rate-limits connects to 10/min per user and 30/min per IP, (4) stores `imb:sid:{sid}`. Any failure → `ConnectionRefusedError({"code": ...})`. Sockets are force-disconnected after 60 min (client reconnects with a fresh token) and immediately when Clerk sends `session.ended`/`session.revoked` for that session.

| Event | Direction | Authz | Payload schema | Rate limit | Ack |
|---|---|---|---|---|---|
| `room:join` | C→S | authenticated; room live (`SISMEMBER imb:rooms:live` + DB fallback) | `{room_id: uuid}` | 30/min per sid | `{ok:true, snapshot: RoomSnapshot}` or `{ok:false, code}` |
| `room:leave` | C→S | joined to that room | `{room_id: uuid}` | 30/min | `{ok:true}` |
| `presence:heartbeat` | C→S | joined | `{}` | 4/min | none; refreshes presence ZSet score |
| `auth:refresh` | C→S | connected | `{token}` | 4/min | `{ok}`; re-verifies, extends socket max age to 60 min from now |
| `track:changed` | S→C | room members | `NowPlayingDTO + room_id` | n/a | n/a |
| `playback:state` | S→C | room members | `{room_id, is_playing, progress_ms, observed_at_ms}` | n/a | n/a |
| `suggestion:created` | S→C | room members | `SuggestionDTO + room_id` (no `voted_by_me`) | n/a | n/a |
| `vote:updated` | S→C | room members | `{room_id, suggestion_id, vote_count}` | coalesced, max 2/s per room | n/a |
| `suggestion:status` | S→C | room members | `{room_id, suggestion_id, status, reason_code?}` | n/a | n/a |
| `room:stale` | S→C | room members | `{room_id, reason: "spotify_rate_limited"|"spotify_quota"|"spotify_down"|"worker_down"}` | n/a | n/a |
| `room:closed` | S→C | room members | `{room_id, reason: close_reason}` | n/a | n/a |
| `error` | S→C | the sid | `{code}` | n/a | n/a |

Rules for every inbound handler: validate payload with the JSON Schema (unknown fields rejected), check the per-event limit, re-check authz from server state (never trust a client `room_id` for anything except "which room do you want"), then act. One socket is in at most one room; `room:join` leaves the previous room first.

`RoomSnapshot` = `{room: RoomCardDTO, now_playing: NowPlayingDTO, suggestions: SuggestionDTO[≤50], server_now_ms}`. `server_now_ms` lets the client compute clock offset for the progress bar ([06](./06-UX_SPEC.md)).

### 5. Idempotency

- `POST /rooms` requires `Idempotency-Key` (UUID). Stored 24 h in Redis as `imb:idem:{user_id}:{key}` → response hash. Same key + different body → 409.
- Votes are naturally idempotent (PUT + PK).
- Suggestions: duplicate active track returns the existing item with 200.
- Close: idempotent by state.
- Worker push: claim by status transition before calling Spotify.

## Assumptions

- Clerk session tokens are short-lived (refreshed about every 60 s by the Clerk frontend SDK), so the web app fetches a fresh token per request and for `auth:refresh`.
- Socket.IO server can read the `Origin` header in the connect handler via the WSGI environ (UNVERIFIED for threaded mode; Flask-SocketIO also enforces `cors_allowed_origins` itself).

## Open questions

- Should listeners see who suggested a track (display name)? Proposed yes, with the host able to hide names per room later.
- Search gate "member of a live room in the last 10 min" reduces scraping but blocks searching from the feed. Acceptable for MVP?

## Verified sources

| Fact | Source | Accessed |
|---|---|---|
| Clerk session tokens are JWTs, in `__session` cookie or `Authorization` header, verify with instance public key; `azp` check | https://clerk.com/docs/guides/sessions/manual-jwt-verification (search snippet) | 2026-11-09 |
| Clerk refreshes session token every 60 s | https://clerk.com/docs/guides/sessions/customize-session-tokens (search snippet) | 2026-11-09 |
| Clerk webhooks are delivered via Svix / Standard Webhooks and must be verified | https://clerk.com/docs/webhooks/sync-data, https://clerk.com/docs/references/backend/verify-webhook (snippets) | 2026-11-09 |
| Flask-SocketIO same-origin default, `cors_allowed_origins` list, `*` risks CSRF | https://flask-socketio.readthedocs.io/en/latest/deployment.html | 2026-11-09 |
| Spotify search limit ≤ 10 | https://developer.spotify.com/documentation/web-api/references/changes/february-2026 (UNVERIFIED at runtime) | 2026-11-09 |
