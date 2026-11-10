# imbooored — Kiro Vibe-Coding Playbook

Versi 1.0 · 9 Nov 2026 · Penjelasan: Indonesia. Prompt untuk Kiro: English (agent lebih konsisten), copy UI aplikasi tetap Indonesia.

Isi:
1. Alur kerja (fase 0–7)
2. Fase 0 — Spotify Spike (manual, wajib sebelum Kiro)
3. Fase 1 — Setup repo
4. `.kiro/steering/security.md` (salin persis)
5. PROMPT A — Kickoff: docs + steering (NO CODE)
6. PROMPT B — Template spec + seed S01–S10
7. PROMPT C — Review & gate prompts
8. Hooks & MCP
9. Aturan main harian

---

## 1. Alur kerja

| Fase | Tujuan | Output | Peranmu |
|---|---|---|---|
| 0. Spotify Spike | Buktikan asumsi paling berisiko sebelum menulis spec | `docs/00-spotify-spike-results.md` | Jalankan manual, tanpa AI |
| 1. Setup repo | Git, folder, file referensi, steering security | repo kosong + `security.md` | Copy-paste |
| 2. Planning (Prompt A) | Kiro menulis dokumen perencanaan + steering, tanpa kode | `docs/00–09`, `.kiro/steering/*` | Review, edit, commit |
| 3. Plan review (Prompt C1/C2) | Cari lubang sebelum ada kode | daftar temuan | Putuskan, update docs |
| 4. Spec per fitur (Prompt B) | requirements.md → design.md → tasks.md, satu fitur satu spec | `.kiro/specs/<fitur>/` | Approve tiap dokumen, jangan auto-lanjut |
| 5. Eksekusi task | Satu task per sesi, diff kecil | commit per task | Baca diff, jalankan test, commit |
| 6. Gate sebelum merge/deploy | Security + kualitas | checklist lulus | Prompt C3 + SCA + review manual |
| 7. Operate | Bugfix spec, rotasi secret, restore drill | runbook terpakai | Jadwalkan |

Prinsip yang menjaga hasil tetap bersih dari slop:

- **Docs adalah sumber kebenaran, kode adalah turunannya.** Kalau keputusan berubah, update docs di commit yang sama.
- **Satu spec = satu irisan vertikal** yang bisa didemokan (UI → API → DB → test), bukan satu layer.
- **Approval gate.** Requirements disetujui dulu, baru design, baru tasks. Jangan pakai Quick Spec untuk fitur yang menyentuh auth, token, atau data user.
- **Satu task per sesi chat.** Konteks baru tiap spec; kalau konteks sudah panjang, minta Kiro menulis `docs/PROGRESS.md` lalu mulai sesi baru.
- **AI mengusulkan, kamu memutuskan.** Terutama: dependency baru, skema DB, dan apa pun yang menyentuh auth/token.
- **Model terkuat untuk planning/design/review, model lebih ringan untuk eksekusi task** yang sudah jelas.
- **Tes dulu atau bersamaan**, bukan belakangan. Task pertama tiap spec = tes/kontrak yang gagal.

---

## 2. Fase 0 — Spotify Spike (manual)

Alasan: keputusan terbesar proyek ini ada di akses Spotify, bukan di kode. Per pengecekan 9 Nov 2026:

- App Development Mode: pemilik app wajib Premium, maksimal **5 user ter-otorisasi** lewat allowlist manual di Developer Dashboard; user di luar allowlist dapat 403.
- Extended Quota (tanpa batas 5 user): hanya untuk organisasi terdaftar dengan ≥250.000 MAU dan layanan sudah live (aturan sejak 15 Mei 2025).
- Sejak Feb 2026: `GET /search` maksimum `limit=10` (default 5); beberapa endpoint dihapus/dikonsolidasi (cek migration guide).
- Sejak 23 Jul 2026: kuota Dev Mode dihitung per akun developer (maks 25 Client ID berbagi satu kuota); 429 karena kuota membawa `reason: QUOTA_EXCEEDED`, beda dengan rate limit biasa.
- Dilaporkan (sumber sekunder, verifikasi sendiri): refresh token perlu otorisasi ulang tiap ±6 bulan.
- Developer Terms v10 melarang memakai konten Spotify untuk melatih model ML.

Artinya, arsitektur ratusan room dari dokumen referensi tidak bisa dilayani di Dev Mode. Rencana realistis: **M0 = closed alpha dengan ≤5 host (termasuk kamu)**; listener tidak perlu otorisasi Spotify. Kode dirancang lewat abstraksi `MusicProvider` supaya tidak terkunci.

Checklist spike (catat hasilnya di `docs/00-spotify-spike-results.md`, tulis tanggal & bukti):

1. Buat Spotify app (akun Premium), tambahkan 1–2 akun tes ke allowlist.
2. OAuth Authorization Code + PKCE dengan akunmu; simpan scope minimal yang dibutuhkan (`user-read-currently-playing`, `user-read-playback-state`, `user-modify-playback-state`).
3. Mulai Spotify Jam sebagai host. Panggil `GET /me/player/currently-playing` — apakah track Jam muncul? Apa isi `item`, `progress_ms`, `is_playing`? Bagaimana saat pause, iklan, file lokal, tidak ada device (204)?
4. Panggil `POST /me/player/queue` — apakah track masuk antrean Jam? Error apa jika tidak ada active device / akun bukan Premium?
5. Panggil `GET /search` dengan **client credentials** (tanpa user) — apakah jalan di Dev Mode? Berapa result per request?
6. Coba dengan akun yang **tidak** ada di allowlist — konfirmasi 403 dan bentuk error-nya.
7. Uji refresh token: apakah respons refresh menyertakan refresh_token baru?
8. Catat header rate limit / `Retry-After` yang kamu lihat.
9. Baca ulang: Quota modes, February 2026 migration guide, Developer Terms & Design Guidelines (atribusi/link kembali ke Spotify).

Kriteria lanjut: poin 3 dan 4 berhasil. Kalau poin 3 gagal (Jam tidak terbaca), hentikan dan pikirkan ulang konsep sebelum membuang waktu di spec.

---

## 3. Fase 1 — Setup repo

```
git init imbooored && cd imbooored
mkdir -p docs/reference .kiro/steering
cp /path/ke/Panduan_Vibe_Coding_Bebas_Slop.md docs/reference/
# hasil spike:
#   docs/00-spotify-spike-results.md
# lalu buat .kiro/steering/security.md dengan isi dari Bagian 4
```

`.gitignore` minimal: `.env*`, `node_modules`, `.venv`, `__pycache__`, `.next`. Aktifkan GitHub secret scanning + Dependabot, dan branch protection di `main` sebelum kode pertama.

Di chat Kiro, lampirkan file dengan mengetik `#` lalu pilih file.

---

## 4. `.kiro/steering/security.md` (salin persis)

````markdown
---
inclusion: always
---

# Security Rules (non-negotiable)

If any request, spec, or task conflicts with a rule below, STOP and tell me which rule and why.
Do not silently comply and do not silently skip. Disagreement and risk warnings are required output.

## Auth & sessions
1. Session lifetime: sessions/JWT <= 7 days with refresh-token rotation. Configure in the identity provider, not hand-rolled.
2. No hand-built auth. Identity = Clerk (or Supabase Auth / Auth0). Backend only VERIFIES tokens via the provider's JWKS using a maintained library. Spotify OAuth is an *integration* (not login) and still must use state + PKCE.
3. Secrets only via environment/secret manager. Never hard-code, never commit, never paste real secrets into chat, never log them. MVP: platform secret store. Target: a secret manager (AWS Secrets Manager / Vault / Doppler) with programmatic rotation.
   A `.env` file alone is the minimum, not the goal.

## Dependencies
4. Rotate every secret at least every 90 days; keep the schedule in docs/09-OPS_RUNBOOK.md.
5. Never add a dependency without: exact registry URL, maintainer/last release/downloads sanity check, a one-line reason, and my explicit approval. Do NOT claim a package is "secure" from your own knowledge — AI cannot audit dependencies. Real checks = SCA tooling (GitHub Dependabot/Advanced Security or Snyk, `pip-audit`, `npm audit`, OSV-Scanner). Beware hallucinated/typosquatted package names.
6. Prefer current patched versions; commit lockfiles; pin exact versions.
7. `npm audit` / `pip-audit` run in CI and FAIL on high/critical. NEVER run `npm audit fix` (or `--force`) automatically in CI/CD. Fixes arrive as Dependabot/Renovate PRs, tested in staging first.
8. Database access only through parameterized queries / ORM bound params. No string-built SQL. LIKE/ILIKE input must be escaped or replaced by exact matches on normalized columns.

## API & access control
9. Row-Level Security enabled on every table from the first migration (deny-by-default). The API uses a least-privilege DB role; RLS is defense-in-depth even though the API enforces authorization.
10. No `console.log`/`print` in production code. Use a structured logger with a redaction filter (tokens, emails, cookies). ESLint `no-console` + a CI grep gate.
11. CORS and Socket.IO `cors_allowed_origins` = explicit allow-list of our domains. Never `*`. Validate `Origin` on WebSocket handshake.
12. Every redirect URL (OAuth redirect_uri, `next`/`return_to` params) is validated against a strict allow-list. Never fetch a user-supplied URL server-side (SSRF).
13. Every endpoint AND every Socket.IO event: authentication + authorization + rate limiting (Redis-backed). Any exception (e.g. /health) is listed explicitly in docs/DECISIONS.md.

## Data & infrastructure
14. Cost controls: spend caps/alerts in each provider dashboard AND in code. For this app the metered resource is the Spotify API quota: global request budget, per-room budget, circuit breaker on 429. If an AI API is ever added: hard per-user and global token caps.
15. DDoS/WAF in front of the app (Cloudflare or Vercel edge). Origin accepts traffic only from the edge where the platform allows.
16. Storage isolation: no user file uploads in MVP. If added later, per-user prefixes + signed URLs + server-side ownership checks.
17. Upload validation (only if uploads are ever added): size limits and MIME validation by file signature (magic bytes), not extension.
18. Verify webhook signatures (Clerk/Svix, payment, anything) BEFORE parsing/acting. Idempotent handlers. Reject stale timestamps.

## Operations & compliance
19. Authorization is enforced server-side for every action (host-only, owner-only, membership). UI checks are cosmetic.
20. Audit-log critical actions: deletions, role changes, room close/force-close, token connect/disconnect, data exports, account deletion. Logs without alerts are useless: define alert rules (e.g. bulk deletes, repeated auth failures, token-vault errors, 429 storms) with notification to me within seconds/minutes.
21. Working account-deletion and data-export flows (Indonesia UU PDP, GDPR, CCPA): delete/anonymize DB rows, revoke Spotify tokens, purge Redis keys, keep only what law requires.
22. Automated backups AND a documented, rehearsed restore drill. An untested backup counts as no backup. Redis is treated as rebuildable cache/state, never the only copy of truth.
23. Strict dev / staging / prod separation: separate DBs, Redis, Clerk instances, Spotify Client IDs (note: Spotify Dev Mode quota is shared across Client IDs of one developer account), secrets, domains.
24. Webhooks from non-prod never reach prod; prod webhook secrets differ from all others.

## Project-specific hardening
- Spotify refresh tokens: encrypted at rest (AES-256-GCM or Fernet, key id for rotation, key from secret store). Access tokens are short-lived, kept encrypted or only in memory, never in logs, never sent to browsers.
- Host's Spotify token is used only server-side, only for that host's room.
- Search proxy returns a minimal whitelisted field set, never raw Spotify payloads.
- All user-generated text (hashtags, track titles) is rendered escaped; hashtags normalized to `[a-z0-9_]{2,30}`.
- WebSocket: authenticate on connect, authorize every join/emit, validate payload schemas, cap payload size, per-event rate limits, CSWSH protection via Origin check.
- Jam link: strict allow-list regex, stored as data, never fetched.
- Invariants like "one active room per host" are enforced by the DB (partial unique index), not only by app code.

## Agent behavior
- Tests for authorization and abuse cases are mandatory for any task touching auth, tokens, rooms, votes.
- Do not expand scope. Do not refactor unrelated code in a feature task.
- When unsure, mark the fact UNVERIFIED and ask me; never present guesses about Spotify/Clerk/library behavior as facts. Verify with official docs (context7/web) and cite the URL in the doc.
````

---

## 5. PROMPT A — Kickoff (docs + steering, tanpa kode)

Paste ke chat Kiro (bukan spec) setelah Fase 0 dan 1. Lampirkan `docs/reference/Panduan_Vibe_Coding_Bebas_Slop.md` dan `docs/00-spotify-spike-results.md`.

````text
ROLE
You are lead architect + technical writer for "imbooored". This is the PLANNING phase.
Do NOT write application code, do NOT install packages, do NOT scaffold apps. Only create the markdown (and one OpenAPI YAML) files listed below.
Follow .kiro/steering/security.md strictly. If anything conflicts with it, say so.

INPUTS
1. docs/reference/Panduan_Vibe_Coding_Bebas_Slop.md: a prior design chat (Next.js + Flask-SocketIO + Redis + PostgreSQL + Spotify). Treat as DRAFT IDEAS, not truth. Where you deviate, record an ADR in docs/DECISIONS.md.
2. docs/00-spotify-spike-results.md: my manual Spotify test results. If a Spotify behavior is not proven there or in official docs you just read, label it UNVERIFIED.

PRODUCT
imbooored is a responsive social web app for discovering music through strangers' public Spotify Jams. Hosts publish a "room" that links to their Spotify Jam and tag it with hashtags (#PostPunk, #Darkwave...). Visitors browse a live feed of rooms, see the currently playing track update in real time (cover, title, artist, progress bar), swipe between rooms to change "vibe", suggest tracks, and vote; when a suggestion reaches the vote threshold it is added to the host's Spotify queue. Participation earns "Vibe Points". UI: modern, minimal, dark (zinc/emerald), Inter typeface, copy in Indonesian. Name is lowercase "imbooored" (the boredom of algorithmic playlists).
Personas: Host, Listener, Admin (me).

STACK (propose changes only with an ADR)
Next.js (App Router, TypeScript, Tailwind) · Flask + Flask-SocketIO · asyncio worker (httpx) for Spotify polling · Redis · PostgreSQL with RLS · Clerk for identity · Cloudflare in front · Docker for local/dev parity · pytest, vitest, Playwright.

HARD CONSTRAINTS FROM SPOTIFY (verified Nov 2026; re-verify with official docs/context7 and cite URLs)
- Development Mode: owner needs Premium; max 5 authorized users via allowlist; others get 403. Extended Quota is organization-only with 250k+ MAU. So the MVP is a CLOSED ALPHA with <=5 hosts. Listeners must NOT need to authorize Spotify.
- Search limit max 10 (default 5). Several endpoints were removed in Feb 2026 — only use endpoints confirmed in the current API reference/migration guide.
- Dev-mode quota is per developer account (shared across Client IDs). Distinguish 429 QUOTA_EXCEEDED from rate-limit 429; honor Retry-After.
- Design everything behind a `MusicProvider` interface (Spotify implementation + a Fake/Replay implementation for tests and demo mode).
- Developer Terms: no ML training on Spotify content; follow attribution/design guidelines.

KNOWN ISSUES IN THE REFERENCE (fix in design, do not copy)
- Custom JWT cookie auth -> replace with Clerk + backend JWKS verification.
- `cors_allowed_origins="*"` -> allow-list.
- Host access tokens plaintext in Redis; refresh tokens plaintext in DB -> encrypted token vault.
- Socket handlers trust client-sent room_id/track_id; no per-event authz or rate limits -> add.
- `ilike('%tag%')` on a comma-separated string -> normalized `tags` + `room_tags` tables, exact match.
- `/api/spotify/search` returns raw Spotify payload with a user token -> server-side credentials, minimal DTO, cache, rate limit.
- Open feed with no auth/rate limit -> auth + rate limit (or an explicit ADR exception).
- "One active room per host" only in app code -> partial unique index.
- Ghost-room cleanup order bug risk and plaintext keys -> reconcile on startup, TTLs, deterministic key map.
- Single-process assumptions (-w 1, eventlet) -> check current Flask-SocketIO deployment guidance and the Redis message queue for scale-out.
- Vote/queue path lacks idempotency, abuse limits, and a retry story for 429/no-device -> define.

DELIVERABLES (create all; each doc: Purpose, Content, Assumptions, Open questions, Verified sources [URL + date] or UNVERIFIED tags; max ~400 lines each, split if longer; relative links between docs)
1. docs/00-PROJECT_BRIEF.md: problem, personas, core loop, MVP in/out of scope, non-goals, success metrics, glossary.
2. docs/01-SPOTIFY_CONSTRAINTS.md: access model & quotas, endpoint inventory (endpoint, scope, available in Dev Mode?, used for what, failure modes), verified-vs-unverified table, MusicProvider contract, rollout stages (closed alpha -> waitlist -> what would unlock more), policy/attribution checklist, kill criteria.
3. docs/02-ARCHITECTURE.md: Mermaid component + sequence diagrams (track change, suggest -> vote -> queue, room create/close, token refresh), process topology, failure & degradation modes, capacity assumptions with numbers for 5 hosts and for a hypothetical 300 rooms, scale-out path.
4. docs/03-DATA_MODEL.md: Postgres tables (users, spotify_connections [encrypted], rooms, tags, room_tags, queue_items, votes, vibe_points_ledger [append-only], audit_log, deletion_requests), columns/types/constraints/indexes, soft-close, RLS policy plan per table, migration tool choice; Redis key map table (key, type, TTL, writer, cleanup); invariants list.
5. docs/04-API_AND_EVENTS.md + docs/api/openapi.yaml: REST endpoints (method, path, authn, authz role, rate limit, request/response schema, error codes) and Socket.IO events (direction, authn/authz, payload schema, rate limit, ack). Standard error envelope. Versioning (/api/v1).
6. docs/05-SECURITY_THREAT_MODEL.md: assets, trust boundaries, STRIDE table, abuse cases (vote brigading, room spam, token theft, SSRF via jam link, stored XSS via tags/titles, CSWSH, quota exhaustion DoS, enumeration), and a table mapping ALL 24 rules in security.md to concrete control, where implemented (spec id), test, status.
7. docs/06-UX_SPEC.md: screens and flows (feed, room, host console, suggest modal, onboarding/connect Spotify, alpha-waitlist/403 state), every state (loading, empty, error, offline/reconnect, room closed), swipe navigation incl. keyboard/a11y, progress-bar interpolation behavior, design tokens, Indonesian microcopy, responsive breakpoints.
8. docs/07-ROADMAP.md: milestones M0..M5 with exit criteria; spec list S01..S10 with dependencies, size (S/M/L), risk, and which security rules each touches. Use the seed list below as a starting point; challenge it.
9. docs/08-TEST_STRATEGY.md: test pyramid, tools, Spotify contract tests with recorded fixtures + FakeMusicProvider, authz/abuse test catalog, load-test plan and targets, CI gates (lint, types, tests, pip-audit, npm audit, secret scan, no-console gate).
10. docs/09-OPS_RUNBOOK.md: environments (dev/staging/prod) and what differs, secrets inventory + 90-day rotation table, backup + restore-drill procedure, monitoring & alert rules (who gets notified, thresholds), incident playbooks (429 storm, Redis loss, token leak, ghost-room flood), release checklist, spend caps.
11. docs/DECISIONS.md: ADR log (context, decision, alternatives, consequences) + "Open questions for the owner" list ordered by how much they block.
12. .kiro/steering/product.md, tech.md, structure.md (use Kiro's steering conventions; always-included), plus scoped steering with fileMatch for apps/api/**, apps/web/**, apps/worker/** (conventions, patterns, testing rules, error handling, naming). Keep each short and imperative.
13. docs/PROGRESS.md: empty template (current spec, last completed task, decisions pending, how to resume in a fresh chat).

REPO LAYOUT TO PROPOSE (in structure.md): monorepo with apps/web, apps/api, apps/worker, packages/contracts (types generated from openapi.yaml), infra/, docs/, .kiro/.

PROCESS RULES
- Use web search / context7 to read CURRENT official docs for Spotify, Clerk, Next.js, Flask-SocketIO, python-socketio, Redis, Postgres RLS before stating behavior. Put URL + date next to each external fact.
- For every dependency named in tech.md: registry URL, why needed, alternatives considered, tag "NEEDS HUMAN VERIFICATION". Do not assert any package is safe.
- Do not stop to ask me questions mid-way. Make the most defensible assumption, record it under Assumptions and Open questions, and continue.
- Prefer simple over clever. Single-instance MVP first; describe scale-out but do not design for it prematurely.
- Do not create anything outside the listed files.

WHEN DONE, print: (a) files created, (b) the 10 biggest risks ranked, (c) the 5 decisions only I can make, (d) anything in security.md you could not fully satisfy and why.
````

Setelah Prompt A selesai: baca semua dokumen sendiri (bukan hanya ringkasan Kiro), edit yang salah, jawab Open questions di `DECISIONS.md`, lalu commit `docs: planning baseline`.

---

## 6. PROMPT B — Template spec + seed S01–S10

Gunakan Kiro **Feature Spec** (Requirements-First untuk sebagian besar; Design-First bila arsitektur sudah jelas dari docs). Satu spec per sesi chat baru.

### Template

````text
Create a feature spec named "<NN-feature-name>".

READ FIRST: steering files, docs/00-PROJECT_BRIEF.md, docs/01-SPOTIFY_CONSTRAINTS.md, docs/02-ARCHITECTURE.md, docs/03-DATA_MODEL.md, docs/04-API_AND_EVENTS.md, docs/05-SECURITY_THREAT_MODEL.md, docs/07-ROADMAP.md (entry for this spec), docs/PROGRESS.md.

GOAL: <1-2 sentences, user-visible outcome>
IN SCOPE: <bullets>
OUT OF SCOPE: <bullets>
SECURITY RULES TOUCHED: <rule numbers from security.md>
DEPENDS ON: <previous specs that must be done>

REQUIREMENTS (requirements.md):
- EARS notation, IDs R1, R1.1..., each independently testable.
- Include: happy path, abuse cases, failure modes (Spotify 401/403/429/204/5xx, Redis down, DB conflict), non-functional (latency, rate limits, limits on payload size).
- Include an explicit "Not doing" list.
STOP after requirements.md and wait for my approval.

(after approval) DESIGN (design.md): reuse docs/03 and docs/04; if you must change them, list the exact edits and apply them in the same spec. Include sequence diagrams for non-trivial flows, error handling, and a test plan mapped to requirement IDs.
STOP and wait for approval.

(after approval) TASKS (tasks.md):
- Task 1 = failing tests / contract tests.
- Each task <= ~1-2 hours of work, cites requirement IDs, lists files touched, and ends with "run lint + tests".
- Dependencies are explicit. No task adds a dependency without my approval.
- Last tasks: update docs (03/04/05/09 as needed), run security checklist (Prompt C3), update docs/PROGRESS.md.
````

Definition of Done per task: tes hijau, lint/type bersih, tidak ada `console.log`/`print`, tidak ada secret, authz + rate limit ada di endpoint/event baru, docs ikut diperbarui, diff kecil dan sudah kamu baca, commit message jelas.

### Seed per spec

**S01 Foundation** — Monorepo skeleton, Docker Compose (api, worker, redis, postgres), env validation (fail fast), structured logging + redaction, CORS allow-list, security headers, Redis-backed rate limiter skeleton, `/healthz` (ADR exception), CI (lint, types, tests, pip-audit, npm audit fail on high/critical, secret scan, no-console gate), Dependabot config, dev/staging/prod env naming. Rules: 3, 4, 6, 7, 10, 11, 13, 15, 23.

**S02 Identity** — Clerk in Next.js (middleware, protected routes), Flask JWT verification via JWKS with a maintained library, `users` table synced via Clerk webhook (Svix signature verified, idempotent, stale-timestamp rejection), roles (listener/host/admin), RLS baseline + least-privilege DB role, session lifetime configured <= 7 days with rotation. Tests: expired/forged/wrong-audience tokens. Rules: 1, 2, 9, 18, 19, 24.

**S03 Spotify connect (host only)** — Authorization Code + PKCE, `state` bound to session, redirect allow-list, minimal scopes, encrypted token vault with key id, refresh with lock + grace period, handle rotation of refresh token, disconnect/revoke, `invalid_grant` handling, friendly state when the account is not on the alpha allowlist (403), `MusicProvider` interface + Fake provider. Rules: 3, 4, 12, 14, 19, 20.

**S04 Room lifecycle** — Create/close (soft close), jam-link allow-list regex (never fetched), normalized tags, partial unique index for one active room per host, audit log entries, host-only authorization on close, idempotent close, cleanup helper shared by all closers. Rules: 8, 12, 13, 19, 20.

**S05 Realtime core** — Socket.IO auth on connect, Origin check, join authorization, presence in Redis with TTL, per-event rate limits and payload schema validation, asyncio poller (presence-based + adaptive interval, global Spotify budget, circuit breaker, Retry-After), `track_changed` broadcast through the message queue, client-side progress interpolation. Rules: 11, 13, 14, 19.

**S06 Feed & discovery** — Cursor pagination, exact tag filter via normalized tables, trending tags, room card data from Redis snapshot + DB, response caching, anti-scrape rate limits, auth required (or ADR). Rules: 8, 13.

**S07 Suggest, vote, queue, Vibe Points** — Search proxy (server credentials, whitelisted DTO, cache, rate limit), suggest, idempotent atomic vote (Redis transaction/Lua), threshold -> add-to-queue with retry/backoff, handling of no-active-device / non-Premium / 429, anti-brigading (per-user caps, account-age gate), append-only Vibe Points ledger. Rules: 8, 13, 14, 19, 20.

**S08 Frontend UX polish** — Swipe navigation between rooms (touch + keyboard), loading/empty/error/reconnect/room-closed states, a11y pass, Indonesian copy, responsive layout, Lighthouse budget, Spotify attribution/link-back per guidelines, escaped rendering of all user text. Rules: 10.

**S09 Resilience & ghost rooms** — Host-disconnect grace period, empty/idle auto-close, startup reconciliation (Redis <-> DB), restart recovery, chaos tests (kill Redis / worker, Spotify 5xx storm), load test against the targets in docs/08. Rules: 14, 20, 22.

**S10 Compliance & Ops** — Account deletion + data export (UU PDP/GDPR/CCPA) incl. Spotify token revoke, Redis purge, ledger anonymization; audit-log alert rules wired to notifications; backup automation + **executed** restore drill; secret rotation runbook rehearsal; privacy policy/ToS drafts (not legal advice); production cutover checklist. Rules: 4, 20, 21, 22, 23, 24.

Urutan disarankan: S01 → S02 → S03 → S04 → S05 → S07 (search/vote butuh S05) → S06 → S08 → S09 → S10. Mintalah Kiro menantang urutan ini di `docs/07-ROADMAP.md`.

---

## 7. PROMPT C — Review & gate

**C1 — Review requirements (sebelum approve)**

````text
Act as a skeptical senior reviewer. Read #.kiro/specs/<spec>/requirements.md plus steering and docs/05. Do NOT edit files.
List: (1) ambiguous or untestable requirements, (2) missing abuse cases and failure modes, (3) conflicts with security.md or docs/01 constraints, (4) scope creep, (5) anything that assumes unverified Spotify behavior. Rank by severity and propose the exact wording fix for the top 10.
````

**C2 — Review design**

````text
Review #.kiro/specs/<spec>/design.md against requirements.md, docs/03, docs/04, docs/05. Do NOT edit files.
Find: authorization gaps (who can call what, checked where), race conditions, idempotency holes, Redis/DB inconsistency windows, token exposure paths, unbounded loops or payloads, missing rate limits, missing tests per requirement ID. Output a table: finding | severity | requirement affected | proposed fix.
````

**C3 — Security gate (sebelum merge / deploy)**

````text
Security review of the current diff (git diff main...HEAD). Do NOT fix yet.
For EACH of the 24 rules in security.md answer: applicable? satisfied? evidence (file:line / test name). Additionally check: every new endpoint/event has authn + authz + rate limit + schema validation; no secrets/tokens in logs or responses; no console.log/print; no string-built SQL; no new dependency without approval; tests for abuse cases exist. Output a pass/fail table and a list of blockers. If you cannot verify something, mark UNVERIFIED.
````

Lalu jalankan di luar AI: SCA (Dependabot/Snyk, `pip-audit`, `npm audit`, OSV-Scanner), secret scan (gitleaks atau GitHub secret scanning), dan deploy dulu ke **staging**.

**C4 — Reset konteks**

````text
Update docs/PROGRESS.md: current spec and task, what is done (with commit hashes), decisions made since last update (and ADR ids), open questions, exact next step, commands to run tests locally. Keep it under 80 lines.
````

---

## 8. Hooks & MCP

Hooks Kiro (opt-in, jangan terlalu banyak — tiap hook menambah latensi dan noise):

- Saat file `*.py` / `*.ts(x)` disimpan: jalankan lint/typecheck + test terkait.
- Pra-commit: secret scan, gate `no-console`/`print`, tolak perubahan manifest dependency tanpa entri di `docs/DECISIONS.md` atau catatan persetujuan.
- Saat `docs/api/openapi.yaml` berubah: regenerasi `packages/contracts` dan cek `docs/04` sinkron.
- Saat task spec selesai: update `docs/PROGRESS.md`.

MCP (config workspace Kiro; cek lokasi file terbaru di docs Kiro):

- `context7` — dokumentasi library versi terbaru (Next.js, Flask-SocketIO, Clerk, Spotify).
- `github` — token read-only/minimal untuk issue & PR.
- `playwright` — e2e dan smoke test UI.
- `sequential-thinking` — untuk fase design/review.
- Aturan keras: **jangan beri MCP kredensial production**. DB dev saja, token dengan scope minimum, dan jangan paste secret asli ke chat.

---

## 9. Aturan main harian

1. Mulai sesi: "baca steering + `docs/PROGRESS.md` + spec aktif, lalu kerjakan task N saja."
2. Sebelum task: pastikan branch bersih dan tes lama hijau.
3. Setelah task: baca diff sampai habis, jalankan tes sendiri, commit kecil.
4. Kiro menawarkan dependency baru? Cek registry dan repo-nya sendiri; pakai SCA, bukan pendapat model.
5. Kiro "memperbaiki" tes agar lulus? Curigai — periksa apakah ia mengubah perilaku atau melemahkan asersi.
6. Bug muncul: gunakan **Bugfix Spec** (analisis perilaku saat ini / diharapkan / tidak boleh berubah), jangan tambal lewat chat acak.
7. Konteks panjang atau agent mulai berputar: Prompt C4, buka sesi baru.
8. Fakta eksternal (Spotify/Clerk/library) selalu minta URL docs resmi; tandai UNVERIFIED bila tidak ada.
9. Jadwalkan di kalender: rotasi secret tiap 90 hari, restore drill tiap kuartal, review Dependabot mingguan, cek ulang changelog Spotify bulanan.
10. Jangan deploy ke production sebelum Prompt C3 + SCA + staging lulus.
