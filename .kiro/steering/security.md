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
