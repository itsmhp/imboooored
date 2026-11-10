# 09 · Ops Runbook

Status: DRAFT · Written 2026-11-09 · Hosting platform not chosen (OQ-5): steps are written platform-neutral

## Purpose

How to run imbooored: environments, secrets and rotation, backups and restore drills, alerts, incident playbooks, releases, and spend caps. Anything marked "rehearsed" must have a dated log entry in §8 before it counts.

## Content

### 1. Environments

| Item | dev (laptop) | staging | prod |
|---|---|---|---|
| Domain | `localhost` | `staging.<domain>` / `api.staging.<domain>` | `<domain>` / `api.<domain>` |
| Postgres | Compose container | managed, own instance | managed, own instance, PITR on |
| Redis | Compose container | managed, own instance, AUTH+TLS | managed, own instance, AUTH+TLS |
| Clerk | dev instance A | dev instance B (or staging instance) | production instance |
| Spotify Client ID | see ADR-010 / OQ-2 | see ADR-010 / OQ-2 | prod Client ID |
| MusicProvider default | Fake | Spotify (real, owner account) | Spotify |
| Secrets | `.env.local` (git-ignored), dummy values where possible | platform secret store | platform secret store → secret manager (target) |
| Webhooks | Clerk dev → tunnel (never prod URL) | Clerk staging → staging API | Clerk prod → prod API |
| Data | synthetic | synthetic + owner test accounts | real |
| Cloudflare | none | proxied | proxied, WAF managed rules on |

Rule: no environment holds another environment's secret. Prod secrets never on the laptop except during a documented rotation.

### 2. Secrets inventory and 90-day rotation

| Secret | Used by | Rotation method | Every | Next due |
|---|---|---|---|---|
| `SPOTIFY_CLIENT_SECRET` | api, worker | Dashboard "rotate"/regenerate (UNVERIFIED UI), deploy new, verify, revoke old | 90 days | set at first deploy |
| `CLERK_SECRET_KEY` | api | Create new key in Clerk dashboard, deploy, delete old | 90 days | set at first deploy |
| `CLERK_WEBHOOK_SIGNING_SECRET` | api | Rotate in Clerk webhook settings, deploy | 90 days | set at first deploy |
| `TOKEN_VAULT_KEYS` (map `key_id → 32-byte key`) + `TOKEN_VAULT_ACTIVE_KEY_ID` | api, worker | Add new key id, set active, deploy, run re-encrypt job, remove old key after 0 rows use it | 90 days | set at first deploy |
| `DATABASE_URL` passwords (`imb_api`, `imb_worker`, `imb_migrator`, `imb_ops_ro`) | api, worker, CI | `ALTER ROLE ... PASSWORD`, update secret, rolling restart | 90 days | set at first deploy |
| `REDIS_URL` password | api, worker | Provider rotation, rolling restart | 90 days | set at first deploy |
| `IP_HASH_SALT` | api | Rotate monthly; old hashes become unlinkable (intended) | 30 days | set at first deploy |
| Cloudflare API token (CI only, if used) | CI | Re-issue scoped token | 90 days | n/a |
| GitHub deploy credentials / OIDC | CI | Prefer OIDC (no static secret) | n/a | n/a |

Calendar entries: rotation day every 90 days, quarterly restore drill, weekly Dependabot review, monthly Spotify changelog check (playbook §9).

### 3. Backups and restore drill

Backups:

- Postgres: provider PITR (≥ 7 days) plus nightly `pg_dump --format=custom` to a separate storage bucket in another account/project, encrypted, 30-day retention.
- Redis: no backup needed (rebuildable). Verify the rebuild path in the drill.
- Secrets: kept in the secret store; a sealed offline copy of the vault keys held by the owner (password manager), because losing vault keys means every host reconnects.

Restore drill (quarterly, and before M3):

1. Pick the latest nightly dump. Note its timestamp.
2. Create a fresh Postgres instance in staging. Restore with `pg_restore`.
3. Run Alembic `current` and compare with the expected head.
4. Run the RLS test subset against the restored DB as `imb_api`.
5. Point a staging API + worker at it with empty Redis. Confirm the worker reconcile rebuilds `imb:rooms:live` and snapshots within 60 s.
6. Decrypt one test host's refresh token with the restored key set (proves keys and data match).
7. Record: date, dump age, time to restore, issues, in §8.

Target: RPO ≤ 24 h (nightly) or ≤ 5 min with PITR; RTO ≤ 2 h.

### 4. Monitoring and alert rules

All alerts go to the owner (single person). Channel is OQ-6; proposed: Telegram or email-to-push from the log/metrics platform. Every alert has a playbook link.

| Alert | Condition | Severity | Notify within |
|---|---|---|---|
| Spotify quota | any 429 with `QUOTA_EXCEEDED` | high | 1 min |
| Spotify 429 storm | > 10 rate-limit 429 in 5 min | high | 2 min |
| Spotify budget near cap | > 80% of global budget for 10 min | medium | 10 min |
| Token vault errors | any decrypt failure or > 3 `invalid_grant` in 1 h | high | 1 min |
| Auth failures | > 50 `401` per IP in 5 min, or > 200 total | medium | 5 min |
| Webhook signature failures | > 5 in 10 min | high | 2 min |
| Bulk actions | > 3 `room.force_close` or any `account.delete` batch > 5 in 1 h | medium | 5 min |
| Ghost-room flood | > 5 auto-closes in 15 min | medium | 10 min |
| Worker down | leader lock missing > 60 s | high | 2 min |
| API errors | 5xx rate > 2% for 5 min | high | 5 min |
| DB / Redis down | health probe fails 3× | high | 2 min |
| Owner Premium lapse (inferred) | all Spotify calls 403 for 5 min | high | 5 min |
| Spend | provider spend alert at 50%/80%/100% of monthly cap | medium | provider default |

Logs: structured JSON, redaction filter for `authorization`, `cookie`, `set-cookie`, `access_token`, `refresh_token`, `code`, `code_verifier`, `client_secret`, `email`, any key ending in `_token` or `_secret`. Retention 30 days.

### 5. Incident playbooks

**429 storm / QUOTA_EXCEEDED**

1. Confirm in admin view: breaker state, calls/min, which call types.
2. If quota: leave breaker open; check whether staging or dev drained the shared developer-account quota (C5). Stop non-prod workers.
3. Lower `SPOTIFY_GLOBAL_BUDGET_PER_MIN` and raise min poll interval via config; restart worker.
4. Post a short status in rooms (automatic `room:stale`). Note the time window for the ADR on budgets.

**Redis loss**

1. API keeps serving REST from Postgres; realtime stops.
2. Restore Redis (provider restart or new instance), update `REDIS_URL` if changed.
3. Restart worker → reconcile rebuilds live set and snapshots; clients reconnect and re-join.
4. Verify presence counts after 90 s. Rate-limit counters restart from zero (accepted).

**Token leak suspected** (refresh token, vault key, client secret)

1. Rotate the leaked secret now (§2). For vault keys: new key, re-encrypt, delete old.
2. If host refresh tokens may be exposed: mark all connections `needs_reauth`, close live rooms (`token_revoked`), ask hosts to remove imbooored in their Spotify account apps page and reconnect.
3. Search logs for the token prefix (hashed search if possible). Find the leak path; add a test.
4. Audit-log `incident.token_leak`. UU PDP: assess whether notification to users and the authority is required (owner + legal advice; deadline rules not researched, UNVERIFIED).

**Ghost-room flood**

1. Admin view: list live rooms with `host_gone_since` / `empty_since`.
2. Force-close via admin endpoint (audited).
3. Check worker logs for reconcile errors; check API restart history (presence not expiring?).

**Postgres outage**: follow provider status; if data loss, restore per §3 and record RPO hit.

### 6. Release checklist

- [ ] Prompt C3 security gate run on `git diff main...HEAD`, blockers fixed
- [ ] CI green incl. pip-audit, pnpm audit, OSV, gitleaks, no-console
- [ ] Alembic migration tested on a staging copy; rollback plan written
- [ ] Deployed to staging; Playwright smoke passed with real Spotify (owner account)
- [ ] Clerk session max lifetime still ≤ 7 days in prod dashboard
- [ ] CORS/Socket.IO origin lists match prod domains only
- [ ] Origin not reachable except through Cloudflare (external check)
- [ ] Spend caps and alerts present
- [ ] `docs/` updated in the same PR; `PROGRESS.md` updated
- [ ] Tag release, note in [DECISIONS.md](./DECISIONS.md) if behavior changed

### 7. Spend caps

| Provider | Cap (proposal) | Alert |
|---|---|---|
| Hosting (api, worker, web) | owner to set (OQ-5) | 50/80/100% |
| Managed Postgres + Redis | owner to set | 50/80/100% |
| Clerk | free tier during alpha if it allows custom session lifetime; else paid (custom max lifetime needs paid plan in prod) | plan limit |
| Cloudflare | free/pro | n/a |
| Spotify | quota, not money: global budget 120 calls/min default (config), breaker | §4 alerts |

### 8. Rehearsal log

| Date | Drill | Result | Follow-ups |
|---|---|---|---|
| (none yet) | | | |

## Assumptions

- Managed Postgres provides PITR and role management; managed Redis provides TLS and AUTH.
- The owner is the only on-call person; alerts outside waking hours wait unless high severity.

## Open questions

- OQ-5 hosting platform and secret manager.
- OQ-6 alert channel.
- Spotify client secret rotation flow in the Dashboard (UNVERIFIED).

## Verified sources

| Fact | Source | Accessed |
|---|---|---|
| Spotify Dev Mode quota shared per developer account | https://developer.spotify.com/blog/2026-07-23-web-api-quota-updates (UNVERIFIED at runtime) | 2026-11-09 |
| Clerk custom maximum lifetime requires paid plan in production | https://clerk.com/docs/guides/secure/session-options.md | 2026-11-09 |
| Provider-specific backup/PITR features | not researched (platform not chosen): UNVERIFIED | n/a |
