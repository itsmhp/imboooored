# 03 · Data Model

Status: DRAFT · Written 2026-11-09

## Purpose

Define every Postgres table, its constraints and RLS policy, every Redis key, and the invariants the database enforces. Specs reuse this doc; changes land here in the same commit as the migration.

## Content

### 1. Conventions

- Postgres 16+ (exact version per hosting provider, UNVERIFIED). UUID v4 primary keys via `gen_random_uuid()` except append-only logs (`bigint generated always as identity`).
- All timestamps `timestamptz`, UTC. Every table has `created_at timestamptz not null default now()`.
- Enums as `text` + `CHECK` (simpler migrations than Postgres enum types).
- No `ON DELETE CASCADE` from `users`; deletion goes through the deletion job ([09](./09-OPS_RUNBOOK.md)) so every step is audited.
- Migration tool: **Alembic** with SQLAlchemy Core (ADR-009). Migrations are plain SQL inside Alembic revisions, so RLS, policies, and partial indexes are explicit. Migrations run as role `imb_migrator` (table owner). Apps never run as owner.

### 2. Tables

#### users

| Column | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| clerk_user_id | text | NOT NULL, UNIQUE, CHECK length ≤ 64 |
| display_name | text | NOT NULL, CHECK char_length 1–40 |
| role | text | NOT NULL DEFAULT 'listener', CHECK in ('listener','host','admin') |
| age_confirmed_at | timestamptz | NULL until the 18+ confirmation (OQ-7) |
| deleted_at | timestamptz | NULL; set when anonymized |
| created_at, updated_at | timestamptz | NOT NULL |

Indexes: unique `clerk_user_id`. No email column: email lives in Clerk only.

#### spotify_connections (encrypted)

| Column | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | NOT NULL, UNIQUE, FK users(id) |
| spotify_user_id | text | NOT NULL, UNIQUE (one Spotify account → one imbooored host) |
| scopes | text[] | NOT NULL |
| refresh_token_ct | bytea | NOT NULL, AES-256-GCM ciphertext + tag |
| refresh_token_nonce | bytea | NOT NULL, 12 bytes, unique per encryption |
| key_id | text | NOT NULL, identifies the data key in the secret store |
| authorized_at | timestamptz | NOT NULL; start of the 6-month refresh-token life ([01](./01-SPOTIFY_CONSTRAINTS.md) C9) |
| status | text | NOT NULL, CHECK in ('active','needs_reauth','disconnected') |
| last_refreshed_at | timestamptz | NULL |
| created_at, updated_at | timestamptz | NOT NULL |

AAD for encryption = `user_id || key_id`, so a ciphertext copied to another row fails to decrypt. Access tokens are never stored (worker memory only, ADR-004). On disconnect the row's ciphertext columns are overwritten and the row is deleted.

#### rooms

| Column | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| host_id | uuid | NOT NULL, FK users(id) |
| jam_link | text | NOT NULL, CHECK `jam_link ~ '<allow-list regex, see 05>'`, CHECK length ≤ 200 |
| vote_threshold | smallint | NOT NULL DEFAULT 3, CHECK 2–10 |
| status | text | NOT NULL DEFAULT 'live', CHECK in ('live','closed') |
| close_reason | text | NULL, CHECK in ('host_closed','admin_force_closed','host_gone','empty_timeout','idle_timeout','token_revoked','reconciled','account_deleted') |
| closed_at | timestamptz | CHECK `(status='live') = (closed_at IS NULL)` |
| created_at | timestamptz | NOT NULL |

Indexes:

- `CREATE UNIQUE INDEX rooms_one_live_per_host ON rooms(host_id) WHERE status = 'live';` (invariant I1)
- `CREATE INDEX rooms_live_created ON rooms(created_at DESC, id DESC) WHERE status = 'live';` (feed cursor)

Soft close only. Rows are never deleted (suggestions, ledger, and audit reference them). Account deletion anonymizes `host_id` via the deletion job.

#### tags, room_tags

| tags column | Type | Constraints |
|---|---|---|
| id | bigint identity | PK |
| slug | text | NOT NULL, UNIQUE, CHECK `slug ~ '^[a-z0-9_]{2,30}$'` |
| created_at | timestamptz | NOT NULL |

| room_tags column | Type | Constraints |
|---|---|---|
| room_id | uuid | FK rooms(id) |
| tag_id | bigint | FK tags(id) |
| | | PK (room_id, tag_id); index (tag_id, room_id) |

Normalization (API, before insert): strip leading `#`, Unicode NFKC, lowercase, reject anything not matching the slug regex (no silent transliteration). 1–5 tags per room, enforced in the API and by a constraint trigger. Tag filter is `WHERE tags.slug = :slug` (exact match, bound parameter). No `LIKE`.

#### queue_items (suggestions)

| Column | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| room_id | uuid | NOT NULL, FK rooms(id) |
| suggested_by | uuid | NULL after anonymization, FK users(id) |
| spotify_track_id | text | NOT NULL, CHECK `~ '^[A-Za-z0-9]{22}$'` |
| title | text | NOT NULL, CHECK char_length ≤ 300 |
| artists | text[] | NOT NULL, CHECK cardinality 1–10 |
| cover_url | text | NULL, CHECK `~ '^https://'` and host in image allow-list (app check) |
| duration_ms | integer | NOT NULL, CHECK > 0 |
| status | text | NOT NULL DEFAULT 'pending', CHECK in ('pending','approved','pushing','queued','failed','rejected','cancelled') |
| vote_count | integer | NOT NULL DEFAULT 0, CHECK ≥ 0 |
| threshold_at_creation | smallint | NOT NULL (copy of room threshold, so a later change does not re-trigger) |
| push_attempts | smallint | NOT NULL DEFAULT 0, CHECK ≤ 5 |
| last_error_code | text | NULL |
| approved_at, queued_at, updated_at | timestamptz | NULL / NOT NULL |
| created_at | timestamptz | NOT NULL |

Indexes:

- `UNIQUE (room_id, spotify_track_id) WHERE status IN ('pending','approved','pushing')` (I3: no duplicate active suggestion)
- `(room_id, status, created_at DESC)` for room queue view
- `(suggested_by, created_at DESC)` for per-user caps

Metadata comes from Spotify via our server (search cache or `GET /tracks/{id}`), never from the client.

#### votes

| Column | Type | Constraints |
|---|---|---|
| queue_item_id | uuid | FK queue_items(id) |
| user_id | uuid | NOT NULL, FK users(id) |
| created_at | timestamptz | NOT NULL |
| | | PK (queue_item_id, user_id): I4 one vote per user per suggestion |

On account deletion the user's vote rows are deleted (counts on `queue_items.vote_count` stay; they hold no personal data).

Upvote only, no unvote in MVP. A suggester's own suggestion counts as their vote (inserted in the same transaction).

#### vibe_points_ledger (append-only)

| Column | Type | Constraints |
|---|---|---|
| id | bigint identity | PK |
| user_id | uuid | NULL after anonymization, FK users(id) |
| delta | integer | NOT NULL, CHECK delta BETWEEN -100 AND 100 |
| reason | text | NOT NULL, CHECK in ('suggestion_queued','vote_on_queued','host_room_hour','admin_adjust') |
| ref_type, ref_id | text, uuid | NOT NULL |
| idempotency_key | text | NOT NULL, UNIQUE (e.g. `suggestion_queued:{queue_item_id}`) |
| created_at | timestamptz | NOT NULL |

Append-only: `REVOKE UPDATE, DELETE` from app roles plus a `BEFORE UPDATE OR DELETE` trigger that raises. The only exception is the anonymization function (`SECURITY DEFINER`, owned by `imb_migrator`, sets `user_id = NULL`, writes an audit row). Balance = `SUM(delta)`; cached nowhere in MVP.

#### audit_log (append-only)

| Column | Type | Constraints |
|---|---|---|
| id | bigint identity | PK |
| actor_type | text | CHECK in ('user','admin','system') |
| actor_user_id | uuid | NULL |
| action | text | NOT NULL, e.g. `room.create`, `room.close`, `room.force_close`, `role.change`, `token.connect`, `token.disconnect`, `token.rotate`, `token.invalid_grant`, `export.create`, `account.delete`, `suggestion.reject`, `queue.duplicate_suspected` |
| target_type, target_id | text, text | NULL |
| metadata | jsonb | NOT NULL DEFAULT '{}', CHECK pg_column_size ≤ 4096; redacted before insert |
| request_id | text | NULL |
| ip_hash | text | NULL, HMAC-SHA256(ip, rotating salt) |
| created_at | timestamptz | NOT NULL |

Same append-only trigger as the ledger. Retention 400 days, then purge job (OQ-8).

#### deletion_requests

| Column | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | NOT NULL (kept: it is the anonymized user row id) |
| kind | text | CHECK in ('delete','export') |
| status | text | CHECK in ('pending','processing','done','failed') |
| export_object_key | text | NULL (export file location, signed URL generated on demand, expires 24 h) |
| requested_at, completed_at | timestamptz | |
| failure_code | text | NULL |

Unique `(user_id, kind) WHERE status IN ('pending','processing')`.

#### webhook_events (addition, needed for rule 18 idempotency)

| Column | Type | Constraints |
|---|---|---|
| svix_id | text | PK |
| event_type | text | NOT NULL |
| received_at | timestamptz | NOT NULL |

Rows older than 30 days are purged.

### 3. RLS plan

Roles:

| Role | Login | Owner | BYPASSRLS | Used by |
|---|---|---|---|---|
| `imb_migrator` | yes | owns all tables | no | Alembic only (CI/deploy job) |
| `imb_api` | yes | no | no | apps/api |
| `imb_worker` | yes | no | no | apps/worker |
| `imb_ops_ro` | yes | no | no | owner read-only debugging, no `spotify_connections` grant |

Every table: `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY` in the migration that creates it. No policy = no rows (Postgres default-deny when RLS is on).

The API opens a transaction per request and runs `SET LOCAL app.user_id = :uuid` and `SET LOCAL app.role = :role` (bound values, from the verified Clerk token → `users` lookup). Policies read `current_setting('app.user_id', true)::uuid`. If unset, policies match nothing.

| Table | imb_api | imb_worker |
|---|---|---|
| users | SELECT own row; SELECT `id, display_name` of others via a view `public_profiles`; UPDATE own `display_name`; admin: UPDATE `role` | SELECT `id, role` |
| spotify_connections | SELECT/INSERT/DELETE own row (status, scopes, authorized_at only; ciphertext columns INSERT-only via column grants) | SELECT all columns WHERE status='active'; UPDATE ciphertext/status/last_refreshed_at |
| rooms | SELECT where status='live' or host_id = me or admin; INSERT where host_id = me and role in (host, admin); UPDATE status/close fields where host_id = me or admin | SELECT live; UPDATE close fields |
| tags | SELECT all; INSERT | SELECT |
| room_tags | SELECT where room visible; INSERT where room.host_id = me | SELECT |
| queue_items | SELECT where room visible; INSERT where suggested_by = me and room live; UPDATE `vote_count/status/approved_at` only through `SECURITY DEFINER` function `cast_vote(queue_item_id)`; host UPDATE status='rejected' where room.host_id = me | SELECT status in (approved, pushing); UPDATE status/push fields |
| votes | SELECT where user_id = me; INSERT via `cast_vote` | none |
| vibe_points_ledger | SELECT where user_id = me | INSERT |
| audit_log | INSERT; admin SELECT | INSERT |
| deletion_requests | SELECT/INSERT own | SELECT/UPDATE (deletion job runs in worker) |
| webhook_events | INSERT, SELECT | none |

`cast_vote` runs the insert + threshold update in one statement set and returns `(vote_count, became_approved)`. It is the only path to change `vote_count`.

### 4. Redis key map

Prefix `imb:`. One Redis per environment (rule 23), so no env prefix. Redis requires AUTH + TLS in staging/prod. Nothing here is the only copy of truth; every key is rebuildable from Postgres or from a fresh poll.

| Key | Type | TTL | Writer | Cleanup |
|---|---|---|---|---|
| `imb:rooms:live` | Set of room_id | none | API (create), close_room | SREM in close_room; worker reconcile every 30 s sets it equal to `SELECT id FROM rooms WHERE status='live'` |
| `imb:room:{id}:now` | Hash: track_id, title, artists_json, album, cover_url, duration_ms, progress_ms, is_playing, observed_at_ms, spotify_url | 1 h, refreshed each poll | worker | DEL in close_room |
| `imb:room:{id}:poll` | Hash: next_poll_at_ms, empty_since_ms, idle_since_ms, host_gone_since_ms, error_streak | 24 h | worker | DEL in close_room |
| `imb:room:{id}:presence` | ZSet sid → last_seen_ms | 2 h, refreshed on heartbeat | API | ZREMRANGEBYSCORE older than 90 s on each read; DEL in close_room |
| `imb:room:{id}:host_presence` | ZSet sid → last_seen_ms | 2 h | API | same |
| `imb:sid:{sid}` | Hash: user_id, clerk_session_id, room_id, connected_at_ms | 2 h | API | DEL on disconnect; TTL covers crashes |
| `imb:session:{clerk_session_id}:sids` | Set of sid | 2 h | API | used to kick sockets when Clerk session ends |
| `imb:oauth:state:{state}` | Hash: user_id, code_verifier, created_at_ms | 10 min | API | GETDEL-style single use (Lua: HGETALL + DEL) |
| `imb:spotify:breaker` | Hash: state, open_until_ms, reason | until open_until + 60 s | worker, API | expires |
| `imb:spotify:budget:{epoch_min}` | String counter | 120 s | worker, API | expires |
| `imb:spotify:room_budget:{room_id}:{epoch_min}` | String counter | 120 s | worker | expires |
| `imb:rl:{rule}:{subject}:{window}` | counters (owned by the rate-limit library) | window + slack | API | expires |
| `imb:search:{sha256(normalized_q)}` | String: JSON list of TrackDTO | 10 min | API | expires |
| `imb:track:{track_id}` | String: TrackDTO JSON | 24 h | API | expires |
| `imb:stream:queue_push` | Stream {queue_item_id}; consumer group `worker` | MAXLEN ~ 10,000 | API | XACK after commit; reconcile re-adds `approved` rows older than 60 s |
| `imb:lock:room_close:{id}` | String NX | 15 s | API, worker | expires / DEL |
| `imb:lock:worker_leader` | String NX (instance id) | 15 s, renewed every 5 s | worker | expires |
| `imb:idem:{user_id}:{key}` | Hash: body_sha256, status, response_json | 24 h | API | expires |
| `imb:feed:{tag or _}:{cursor or _}` | String: JSON page | 5 s | API | expires |
| `imb:trending` | String: JSON top 20 tags | 5 min | API | expires |
| Socket.IO channel `imb-socketio` | Pub/Sub channel | n/a | API, worker | n/a |

Rules: no `KEYS`/`SCAN` in request paths. `close_room` deletes a fixed list built from the room id. No per-track dynamic keys.

### 5. Invariants

| ID | Invariant | Enforced by |
|---|---|---|
| I1 | A host has at most one live room | partial unique index `rooms_one_live_per_host` |
| I2 | `closed_at` set iff status closed | CHECK |
| I3 | No duplicate active suggestion of the same track in a room | partial unique index on queue_items |
| I4 | One vote per user per suggestion | PK on votes |
| I5 | A suggestion becomes `approved` at most once | `UPDATE ... WHERE status='pending'` inside `cast_vote` |
| I6 | Ledger and audit rows are never updated or deleted (except anonymization function) | REVOKE + trigger |
| I7 | One Spotify account maps to one imbooored user | UNIQUE spotify_user_id |
| I8 | Only hosts/admins own rooms | RLS INSERT policy + API check |
| I9 | Tags match `^[a-z0-9_]{2,30}$` | CHECK |
| I10 | Jam links match the allow-list regex | CHECK + API validation |
| I11 | Redis live set ⊆ DB live rooms | worker reconcile (eventually, ≤ 30 s) |
| I12 | Refresh tokens exist only as ciphertext | schema (no plaintext column) + log redaction tests |

## Assumptions

- `SET LOCAL` per transaction works with our pooling. With PgBouncer in transaction mode it does; with session pooling it also does as long as we always use a transaction. (UNVERIFIED for the chosen host.)
- A 22-character base62 Spotify track id format holds (UNVERIFIED, confirm with spike fixtures).

## Open questions

- Retention for `audit_log` and closed rooms (OQ-8). Proposed 400 days audit, closed rooms kept, suggestions older than 180 days anonymized.
- Should hosts be able to change `vote_threshold` while live? Proposed yes, affects new suggestions only.

## Verified sources

| Fact | Source | Accessed |
|---|---|---|
| RLS default-deny when enabled with no policy; owners bypass unless FORCE; superusers/BYPASSRLS bypass | https://www.postgresql.org/docs/current/ddl-rowsecurity.html | 2026-11-09 |
| Spotify refresh token 6-month life | https://developer.spotify.com/documentation/web-api/tutorials/refreshing-tokens (UNVERIFIED at runtime) | 2026-11-09 |
| Alembic, SQLAlchemy behavior | not re-read this session: UNVERIFIED | n/a |
