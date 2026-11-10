# S01 Foundation: Requirements

Status: DRAFT, waiting for owner approval · Written 2026-11-10 · Next: design.md only after approval

Sources read: `.kiro/steering/*`, [docs/00](../../../docs/00-PROJECT_BRIEF.md), [01](../../../docs/01-SPOTIFY_CONSTRAINTS.md), [02](../../../docs/02-ARCHITECTURE.md), [03](../../../docs/03-DATA_MODEL.md), [04](../../../docs/04-API_AND_EVENTS.md), [05](../../../docs/05-SECURITY_THREAT_MODEL.md), [07](../../../docs/07-ROADMAP.md), [PROGRESS](../../../docs/PROGRESS.md).

## Goal

A developer clones the repo, runs one command, and gets api, worker, web, Postgres, and Redis running locally with secure defaults, and every pull request is blocked by CI unless lint, types, tests, dependency audits, secret scan, and the no-console and no-raw-SQL gates pass. No product feature exists yet.

## Scope

In scope:
- Monorepo skeleton per `.kiro/steering/structure.md`.
- Docker Compose for local development.
- Settings loader with fail-fast validation.
- Structured logging with redaction.
- API baseline: request ids, error envelope, body limit, security headers, explicit CORS allow-list, Redis-backed rate-limit module, `/healthz`, route registry.
- Worker skeleton (starts, holds the leader lock, exposes an internal health signal, does nothing else).
- Web skeleton (placeholder page, security headers, CSP baseline, lint rules).
- Alembic baseline with DB roles and a default-deny RLS proof.
- CI workflow, Dependabot, secret scan config.
- Docs updates (09, DECISIONS dependency approvals, PROGRESS).

Not doing (explicit):
- Clerk, JWT verification, users table, roles (S02).
- Any Spotify code, MusicProvider, token vault (S03).
- Any product table other than the baseline `app_meta` table (S02+).
- Socket.IO handlers (S05). The Socket.IO server object may exist only if needed by the health or CORS wiring; no events.
- Cloud deployment, Cloudflare provisioning, production secret manager (blocked by OQ-5; documented only, see R16).
- Kiro hooks and MCP configuration.
- Any UI beyond one placeholder page.

Security rules touched: 3, 4, 5, 6, 7, 9, 10, 11, 13, 15, 16, 23.
Depends on: M0 (planning baseline committed). Note: spike items 3 and 4 as host are still open, but S01 does not use any Spotify behavior.

## Requirements (EARS)

### R1 Repository layout and hygiene

- R1.1 The repository shall contain top-level directories `apps/web`, `apps/api`, `apps/worker`, `packages/contracts`, `packages/py-shared`, `infra`, `docs`, `.kiro` and no other top-level source directories.
- R1.2 The repository shall commit lockfiles for every package manager in use and pin dependency versions exactly (no `^`, `~`, `>=`, or `latest`).
- R1.3 `.gitignore` shall exclude `.env*` (except `.env.example`), `*.env.ps1`, `node_modules`, `.venv`, `__pycache__`, `.next`, and token or config files containing credentials.
- R1.4 A committed `.env.example` shall list every required setting with a placeholder value and no real secrets.

### R2 Local environment

- R2.1 When a developer runs `docker compose up` from `infra/`, the system shall start api, worker, web, Postgres, and Redis.
- R2.2 Each service shall define a health check and Compose shall start dependents only after their dependencies are healthy.
- R2.3 Compose shall publish ports only on `127.0.0.1`.
- R2.4 Redis shall require a password in every environment, including dev.
- R2.5 Compose files shall contain no secret values; all secrets shall come from environment variables or an untracked env file.
- R2.6 When the developer stops the stack and runs `docker compose down -v`, no data shall remain.

### R3 Settings and environments

- R3.1 Each Python service shall load settings from environment variables into a typed schema.
- R3.2 If a required setting is missing or invalid, then the service shall exit with a non-zero status before accepting traffic and shall name the failing keys without printing any values.
- R3.3 The setting `APP_ENV` shall accept only `dev`, `staging`, `prod`.
- R3.4 While `APP_ENV` is `staging` or `prod`, the service shall refuse to start if `ALLOWED_ORIGINS` contains `*` or any non-`https` origin, or if debug mode is enabled.
- R3.5 The `ALLOWED_ORIGINS` value shall be a comma-separated list of exact origins and shall be the single source for REST CORS and the future Socket.IO origin list.
- R3.6 Settings shall never be read from files committed to the repository.

### R4 Logging

- R4.1 Every Python service shall emit one JSON object per log line with at least `timestamp`, `level`, `service`, `event`, and `request_id` when present.
- R4.2 When a log record contains a key named `authorization`, `cookie`, `set-cookie`, `access_token`, `refresh_token`, `code`, `code_verifier`, `client_secret`, `email`, or any key ending in `_token` or `_secret`, the logger shall replace its value with `[REDACTED]`.
- R4.3 When a log message string contains a value that matches a bearer-token or JWT shape, the logger shall redact it.
- R4.4 Production code in `apps/` and `packages/` shall contain no `print(` and no `console.log`, `console.debug`, or `console.info`; a CI gate shall enforce this (test files and `scripts/` excluded).
- R4.5 ESLint shall enforce `no-console` for the web app and Python lint shall forbid `print` outside tests.

### R5 API baseline

- R5.1 When a request arrives, the API shall assign `X-Request-Id` (reuse a valid incoming value of at most 64 characters from `[A-Za-z0-9_-]`, otherwise generate one) and return it in the response.
- R5.2 When the API returns an error, the body shall use the envelope in docs/04 §2 (`error.code`, `error.message`, `error.request_id`) and shall not include stack traces or internal details.
- R5.3 If a request body exceeds 8 KB, then the API shall return HTTP 413 with code `PAYLOAD_TOO_LARGE`.
- R5.4 Every API response shall include `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, and shall omit server version headers.
- R5.5 While `APP_ENV` is `staging` or `prod`, API responses shall include `Strict-Transport-Security` with `max-age` of at least 31536000.
- R5.6 If an unhandled exception occurs, then the API shall return HTTP 500 with code `INTERNAL` and log the exception with the request id and no request body.

### R6 CORS

- R6.1 When a request carries an `Origin` header that is in `ALLOWED_ORIGINS`, the API shall echo that exact origin in `Access-Control-Allow-Origin`.
- R6.2 If the `Origin` header is not in `ALLOWED_ORIGINS`, then the API shall not send any `Access-Control-Allow-*` header.
- R6.3 The API shall never send `Access-Control-Allow-Origin: *` and shall not send `Access-Control-Allow-Credentials`.
- R6.4 When a preflight request arrives from an allowed origin, the API shall allow only the methods and headers declared in code and shall set `Access-Control-Max-Age` of at most 600.

### R7 Rate-limit module

- R7.1 The system shall provide a Redis-backed rate-limit module usable by REST routes now and by Socket.IO events later through the same function.
- R7.2 When a caller exceeds a limit, the API shall return HTTP 429 with code `RATE_LIMITED` and a `Retry-After` header of at least 1 second.
- R7.3 If Redis is unavailable, then limits on mutating routes shall fail closed (HTTP 503 `DEPENDENCY_UNAVAILABLE`) and limits on read-only routes shall be configurable to fail open or closed per route.
- R7.4 Limit keys shall be built from a fixed prefix, the rule name, and the subject; subject strings shall be length-capped and hashed when they derive from user input.
- R7.5 Time-dependent behavior shall be testable with an injected clock.

### R8 Route registry

- R8.1 Every route shall declare, in code, its authentication requirement, authorization rule, and rate-limit rule, or be explicitly marked `public` with a reason.
- R8.2 When a route lacks any of those declarations, then the route-registry test shall fail the build.
- R8.3 Until S02 exists, the authentication hook shall reject every non-public request with HTTP 401 `UNAUTHENTICATED`.
- R8.4 The only `public` route in S01 shall be `GET /healthz`, and the exception shall be recorded in `docs/DECISIONS.md` (ADR-013 already exists; the registry reason shall reference it).
- R8.5 The route-registry test shall fail if any route accepts `multipart/form-data` (security rule 16).

### R9 Health endpoint

- R9.1 When `GET /healthz` is called, the API shall return HTTP 200 with body `{"status":"ok"}` and nothing else.
- R9.2 `/healthz` shall not report versions, dependency state, hostnames, or configuration.
- R9.3 The worker shall expose its health signal only on an internal interface that is not published by Compose to the host.

### R10 Database baseline and RLS

- R10.1 The repository shall contain an Alembic migration `0001` that creates a table `app_meta(key text primary key, value text not null)`, enables and forces row-level security on it, and defines no policy that grants rows to `imb_api` or `imb_worker`.
- R10.2 The infrastructure bootstrap shall create roles `imb_migrator` (owner, no login in app services), `imb_api`, `imb_worker`, `imb_ops_ro`, none with `SUPERUSER` or `BYPASSRLS`, with passwords supplied from environment variables.
- R10.3 When a connection as `imb_api` or `imb_worker` selects from `app_meta`, the result shall contain zero rows even if rows exist.
- R10.4 A test shall query the catalog and fail if any table in the application schema, other than the explicit migration-tool table `alembic_version`, lacks `relrowsecurity` and `relforcerowsecurity`.
- R10.5 The API shall provide one helper that opens a transaction and sets `app.user_id` and `app.role` with bound parameters (`set_config(..., true)`); no code path shall build that statement with string formatting.
- R10.6 Application services shall connect only as `imb_api` or `imb_worker`; migrations shall run only as `imb_migrator`.
- R10.7 A grep gate shall fail CI if Python code contains an f-string, `%`, or `.format(` inside a SQL execution call outside `apps/api/migrations`.

### R11 Worker skeleton

- R11.1 When the worker starts, it shall acquire the Redis lock `imb:lock:worker_leader` with a 15-second TTL and renew it every 5 seconds.
- R11.2 If the worker fails to acquire the lock, then it shall stay idle and retry with jitter.
- R11.3 If the worker loses the lock, then it shall stop work within one renewal interval.
- R11.4 The worker shall perform no Spotify calls and no database writes in S01.

### R12 Web skeleton

- R12.1 When a user requests `/`, the web app shall render a placeholder page containing the wordmark "imbooored" and no data, statistics, links to nonexistent pages, or fake content.
- R12.2 The web app shall send a Content-Security-Policy with at least `default-src 'self'`, `object-src 'none'`, `base-uri 'self'`, and `frame-ancestors 'none'`, and shall send `X-Content-Type-Options`, `Referrer-Policy`, and `Permissions-Policy` headers.
- R12.3 ESLint shall fail on `dangerouslySetInnerHTML` and on `console.*` calls.
- R12.4 The web app shall use the Inter typeface self-hosted and the design tokens from docs/06 §2 for background and text colors.

### R13 CI

- R13.1 When a pull request is opened or updated, or a commit lands on `main`, CI shall run: lint (ruff, ESLint), type checks (mypy, `tsc --noEmit`), unit and integration tests with Postgres and Redis services, `pip-audit`, the JavaScript package audit at `high` level, OSV-Scanner, the secret scan, the no-console gate, the raw-SQL gate, and the dependency-approval gate.
- R13.2 If any CI job fails, then the pull request shall not be mergeable (branch protection is a manual owner step, recorded in docs/09).
- R13.3 CI shall fail on any high or critical finding from the dependency audits.
- R13.4 CI and repository scripts shall never run `npm audit fix`, `pnpm audit --fix`, or equivalent auto-fix commands.
- R13.5 Third-party GitHub Actions shall be pinned to full commit SHAs, and workflow `permissions` shall default to `contents: read`.
- R13.6 If a change touches a dependency manifest or lockfile without a matching row in the "Dependency approvals" table of `docs/DECISIONS.md`, then the dependency-approval gate shall fail.
- R13.7 CI shall not receive production or staging secrets.

### R14 Dependabot and secret scanning

- R14.1 The repository shall include `.github/dependabot.yml` covering the JavaScript, Python, GitHub Actions, and Docker ecosystems with a weekly schedule and no auto-merge.
- R14.2 The repository shall include a gitleaks configuration; the CI secret scan shall scan the diff on pull requests and the full history on `main`.
- R14.3 Enabling GitHub secret scanning, Dependabot alerts, and branch protection on `main` shall be listed as owner steps in docs/09 with a checkbox each.

### R15 Dependencies

- R15.1 The implementation shall add only packages listed in `.kiro/steering/tech.md`.
- R15.2 Before any package is added, the owner shall approve it, and the approval (package, exact version, registry URL, date) shall be recorded in `docs/DECISIONS.md` "Dependency approvals".
- R15.3 No task shall add a package that is not in `tech.md` without first updating `tech.md` and obtaining approval.

### R16 Edge and origin protection (documentation only)

- R16.1 `docs/09-OPS_RUNBOOK.md` shall contain a Cloudflare checklist (proxy on, WAF managed rules, rate rules for `/api/*`, WebSocket support, bot protection) and the origin-lock method for the chosen hosting platform.
- R16.2 If the hosting platform is not yet chosen (OQ-5), then the checklist shall be marked OPEN and rule 15 shall remain "open" in docs/05.

### R17 Environment separation

- R17.1 Configuration shall define separate variable sets for `dev`, `staging`, and `prod`, with no value shared between staging and prod.
- R17.2 `docs/09-OPS_RUNBOOK.md` shall list, per environment, the database, Redis, Clerk instance, Spotify Client ID, secrets store, and domain, and mark undecided items OPEN (ADR-010, OQ-2, OQ-5).
- R17.3 The settings loader shall reject, in `prod`, any `DATABASE_URL` or `REDIS_URL` that points to `localhost`, `127.0.0.1`, or a Docker-internal hostname.

### R18 Documentation

- R18.1 The implementation shall update docs/09 (environments, Cloudflare checklist, owner steps), docs/07 (S01 status), `docs/DECISIONS.md` (dependency approvals, any new ADR), and `docs/PROGRESS.md`.

## Non-functional

- N1 Cold `docker compose up` shall reach all services healthy in at most 5 minutes on the owner's machine after images are cached.
- N2 The unit test suite for `apps/api` and `packages/py-shared` shall finish in at most 60 seconds without Docker; integration tests in at most 5 minutes.
- N3 The CI workflow shall finish in at most 15 minutes.
- N4 `/healthz` shall respond in at most 50 ms p95 locally.
- N5 Request bodies, headers, and log fields shall be size-limited so a single request cannot produce a log line over 8 KB.

## Failure modes covered

| Failure | Required behavior |
|---|---|
| Missing/invalid setting | R3.2 |
| Redis down | R7.3, R11.2 |
| Postgres down | `/healthz` still 200 (liveness only); readiness is out of scope for S01 |
| Oversized body | R5.3 |
| Unknown Origin | R6.2 |
| Forged `X-Request-Id` | R5.1 |
| Secret in log | R4.2, R4.3 |
| Table without RLS | R10.4 |
| String-built SQL | R10.7 |
| New dependency without approval | R13.6 |
| Spotify 401/403/429/204/5xx | Not applicable in S01 (no Spotify calls) |

## Assumptions

- A1. Python and Node versions, and the package managers (pnpm and uv), are fixed in design.md after reading current official release notes (OQ-10 pending for pnpm vs npm).
- A2. GitHub is the code host and Actions is the CI.
- A3. The owner applies repository settings (secret scanning, Dependabot alerts, branch protection) manually.
- A4. The first Alembic migration can be applied by a bootstrap that runs as a database superuser only in dev; staging and prod roles are created by the owner (OQ-5).

## Open questions for the owner

- OQ-10: pnpm or npm? (default pnpm)
- OQ-5: hosting platform (only affects R16 and R17 documentation in S01)
- Is a mandatory second reviewer on PRs needed, or is solo merge after green CI acceptable for the alpha?
