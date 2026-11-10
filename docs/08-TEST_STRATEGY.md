# 08 · Test Strategy

Status: DRAFT · Written 2026-11-09 · Tools listed here are proposals; each needs owner approval per security rule 5 (see `.kiro/steering/tech.md`)

## Purpose

Say what we test, with which tools, at which layer, and which CI gates block a merge. The first task of every spec is a failing test or contract test ([07](./07-ROADMAP.md)).

## Content

### 1. Pyramid

| Layer | Share | Tools (proposed) | Runs |
|---|---|---|---|
| Unit | ~60% | pytest (api, worker), vitest (web) | every push |
| Integration (real Postgres + Redis in Docker Compose) | ~25% | pytest with fixtures that create a schema per test run; migrations applied as `imb_migrator`, tests connect as `imb_api` / `imb_worker` | every push |
| Contract (Spotify) | ~5% | pytest + `ReplayMusicProvider` fixtures; respx for httpx-level mapping tests | every push |
| Contract (API ↔ web) | ~5% | schema tests: Flask responses validated against `docs/api/openapi.yaml`; `packages/contracts` regenerated and diff-checked | every push |
| E2E | ~5% | Playwright against Docker Compose with `FakeMusicProvider` and Clerk test instance | PR to `main`, nightly |
| Load | separate | Locust with a python-socketio client (proposed; k6 lacks native Socket.IO framing, UNVERIFIED) | before M3, before M5 |

### 2. Spotify contract tests

- The spike records real responses. Before committing, a scrub script removes tokens, user ids, emails, device ids, and `Authorization` headers; a CI check greps fixtures for `Bearer `, `access_token`, `refresh_token`, and 22+ char base64-like strings outside allowed fields.
- Fixture set (minimum): currently-playing 200 playing / paused / ad / local file / episode; 204; 401; 403 not allowlisted; 429 rate limit with `Retry-After`; 429 `QUOTA_EXCEEDED`; 5xx; queue add 204 / no device / premium required; token refresh 200 with and without new refresh token; `invalid_grant`; search 200 with 10 items; `GET /tracks/{id}` 200/404.
- Each fixture has a test asserting the mapped `MusicProvider` result (DTO or `ProviderError.kind`) and that no unexpected field passes through.
- Fixtures marked with spike date. Monthly reminder ([09](./09-OPS_RUNBOOK.md)) to re-record against the live API and diff.

`FakeMusicProvider` drives all worker logic tests (adaptive interval, breaker, budget, ghost rooms, push retries) with a fake clock.

### 3. Authorization and abuse test catalog

Mandatory for any task touching auth, tokens, rooms, votes (security.md "Agent behavior"). Names are the target test names.

| Area | Tests |
|---|---|
| Token verification | `test_missing_token_401`, `test_expired_token_401`, `test_forged_signature_401`, `test_wrong_issuer_401`, `test_wrong_azp_401`, `test_unknown_kid_401`, `test_jwks_cached_when_clerk_down` |
| Webhooks | `test_webhook_bad_signature_401_before_parse`, `test_webhook_stale_timestamp_rejected`, `test_webhook_replay_ignored`, `test_webhook_cannot_set_role` |
| Roles | `test_listener_cannot_connect_spotify`, `test_listener_cannot_create_room`, `test_host_cap_five`, `test_only_admin_changes_roles`, `test_role_change_audited` |
| Rooms | `test_second_live_room_409`, `test_close_other_hosts_room_403`, `test_close_idempotent`, `test_admin_force_close_audited`, `test_jam_link_rejects_ip`, `test_jam_link_rejects_javascript_scheme`, `test_jam_link_rejects_other_domain`, `test_jam_link_never_fetched` (HTTP client mock asserts zero calls) |
| Tags | `test_tag_normalization`, `test_tag_rejects_unicode_lookalikes`, `test_tag_filter_exact_no_like` |
| Sockets | `test_socket_rejects_missing_token`, `test_socket_rejects_foreign_origin`, `test_join_closed_room_rejected`, `test_one_room_per_socket`, `test_payload_over_4kb_rejected`, `test_unknown_fields_rejected`, `test_event_rate_limit`, `test_socket_kicked_on_session_revoked` |
| Votes | `test_vote_requires_presence`, `test_double_vote_counts_once`, `test_concurrent_votes_threshold_once` (50 parallel), `test_vote_on_closed_room_409`, `test_vote_rate_limit` |
| Suggestions | `test_metadata_from_server_not_client`, `test_duplicate_active_suggestion_returns_existing`, `test_new_account_cannot_suggest`, `test_suggestion_caps` |
| Search | `test_search_requires_recent_membership`, `test_search_returns_whitelisted_fields_only`, `test_search_budget_enforced`, `test_search_cache_hit_no_upstream_call` |
| Tokens | `test_refresh_token_stored_encrypted`, `test_ciphertext_bound_to_user_aad`, `test_api_role_cannot_select_ciphertext`, `test_access_token_never_in_redis`, `test_logs_redact_tokens`, `test_no_token_in_any_response`, `test_invalid_grant_closes_room` |
| RLS | `test_rls_denies_without_app_user`, `test_api_role_not_owner_no_bypassrls`, `test_user_reads_only_own_votes`, `test_ledger_update_delete_blocked` |
| Privacy | `test_export_idor_404`, `test_export_contents_complete`, `test_deletion_end_to_end` (DB, Redis, vault, Clerk call mocked) |
| Redirects | `test_redirect_allowlist`, `test_oauth_state_single_use`, `test_oauth_state_bound_to_user` |
| Registry | `test_every_route_has_auth_and_limit`, `test_every_socket_handler_has_schema_and_limit`, `test_no_multipart_routes` |

### 4. Load-test plan

| Scenario | Target (alpha, staging-sized instance) | Pass criteria |
|---|---|---|
| 100 sockets across 5 rooms, heartbeat every 30 s, 1 track change per room per 3.5 min | sustained 30 min | p95 event delivery ≤ 500 ms from worker emit; 0 dropped connections; API CPU < 60% |
| Reconnect storm: kill API, 100 sockets reconnect | within 30 s | all re-joined; presence correct after 90 s |
| Vote burst: 50 users vote the same suggestion in 1 s | once | exactly 1 push enqueued; p95 vote latency ≤ 300 ms |
| Feed: 20 rps for 5 min | sustained | p95 ≤ 200 ms; cache hit ≥ 80% |
| Spotify budget: Fake provider returns 429 storms | 10 min | breaker opens, no call above budget, recovers |

Load tests use `FakeMusicProvider`. Never point load tests at the real Spotify API (shared quota).

### 5. CI gates (block merge to `main`)

1. Lint: ruff (Python), ESLint with `no-console` and `react/no-danger` (web).
2. Types: mypy strict on `apps/api`, `apps/worker`; `tsc --noEmit` on web and contracts.
3. Tests: unit + integration + contract (Compose services in CI).
4. `pip-audit` on each Python lockfile: fail on any known vuln with fix available at high/critical (exact flag behavior UNVERIFIED, confirm in S01).
5. `pnpm audit --audit-level=high` (or `npm audit` if npm chosen). Never `audit fix` in CI.
6. OSV-Scanner on all lockfiles.
7. Secret scan: gitleaks on the diff and full history on `main`; GitHub secret scanning enabled.
8. No-console gate: `git grep -nE "console\.(log|debug|info)|\bprint\(" -- apps packages` must be empty outside `scripts/` and test files.
9. Raw-SQL gate: grep for `text(f"`, `execute(f"`, `% (` near SQL; reviewed allow-list for Alembic files.
10. OpenAPI drift: regenerate `packages/contracts`, fail on diff.
11. Dependency gate: any change to `package.json`, `pnpm-lock.yaml`, `pyproject.toml`, `uv.lock` requires a matching entry in [DECISIONS.md](./DECISIONS.md) "Dependency approvals" (checked by script).

Playwright and load tests are required for release, not for every PR.

## Assumptions

- GitHub Actions is the CI (playbook mentions GitHub Dependabot and secret scanning).
- Clerk provides a test instance and test tokens for E2E (UNVERIFIED; check Clerk testing docs in S02).

## Open questions

- Coverage threshold? Proposed: no global number; every requirement ID in a spec maps to at least one test (enforced in design.md test plans).
- Locust vs k6 for Socket.IO load: decide in S09 after a 1-hour spike.

## Verified sources

| Fact | Source | Accessed |
|---|---|---|
| Tool behaviors (pip-audit flags, pnpm audit levels, OSV-Scanner, gitleaks, Locust, Playwright) | not re-read this session: UNVERIFIED, confirm during S01 | n/a |
