# S01 Foundation: Design

Status: APPROVED by the owner on 2026-11-10, including every dependency in §3 · Requirements: [requirements.md](./requirements.md) (approved 2026-11-10) · Next: [tasks.md](./tasks.md)

## 1. Decisions in this spec

| Topic | Decision | Reason |
|---|---|---|
| JS package manager | pnpm workspaces (OQ-10 answered by owner) | One lockfile, strict dependency resolution |
| Python tooling | uv workspace, one `uv.lock` at the repo root | One lockfile for api, worker, py-shared |
| Rate limiter | Own fixed-window limiter on Redis (new ADR-022), not Flask-Limiter/limits | One function for REST and sockets, injectable clock (R7.5), two fewer dependencies |
| Merge policy | Solo merge after CI is green; branch protection requires the CI checks (owner answer) | Solo alpha project |
| Web CSP | Per-request nonce set in `proxy.ts` with `strict-dynamic`, pages rendered dynamically | Next.js docs: nonces require dynamic rendering; SRI hashes are experimental |
| Compose web service | Runs a production build (`next start`); hot reload runs outside Compose with `pnpm dev` | Parity in Compose, speed for UI work |
| Hosting (OQ-5) | Still open. S01 only documents it (R16, R17) | No platform picked |

## 2. Runtimes and tools

Facts read on 2026-11-10 from endoflife.date, nodejs.org, the npm registry, and PyPI.

| Item | Version | Why this one |
|---|---|---|
| Node.js | 26.13.0 (26.x LTS since 2026-10-28) | Current LTS. The owner's system Node 25.7.0 reached end of life on 2026-06-01, so it is not used. |
| Python | 3.14 (latest patch at build time) | Supported until 2030-10. 3.15.2 also has the needed binary wheels, but it is one month old; 3.14 lowers the risk of missing wheels for later specs (cryptography, etc.). |
| pnpm | 12.18.0 | Pinned via `packageManager` in the root `package.json` |
| uv | 0.13.7 | Pinned in CI and documented for local use |
| PostgreSQL | 18 (image `postgres:18-alpine`, digest pinned in task) | Current major, EOL 2030-11 |
| Redis | 8.10 (image `redis:8.10-alpine`, digest pinned in task) | Current minor. Note: Redis 8 is tri-licensed (RSALv2/SSPLv1/AGPLv3); self-hosted dev and a managed service are fine. Valkey is the drop-in alternative if the license matters later. |
| TypeScript | 6.0.3 | TypeScript 7.0 (native compiler) is current, but whether Next.js 16's build-time type check works with it is UNVERIFIED. Revisit in a Dependabot PR. |
| gitleaks, OSV-Scanner | latest release at task time, binary checksum verified | Tag and SHA resolution deferred: the GitHub API was rate-limited on 2026-11-10 |

## 3. Dependencies to approve (S01 only)

Every row is NEEDS HUMAN VERIFICATION. The facts below are a sanity check, not a security claim. Real checks are the CI audits (rule 5, 7). Versions are pinned exactly; the task re-reads the registry and uses the latest patch if one appeared.

Python (PyPI):

| Package | Version | Released | Weekly downloads | Source | Used by | Reason |
|---|---|---|---|---|---|---|
| Flask | 3.1.3 | 2026-02-19 | ~54.1M | github.com/pallets/flask | api | HTTP framework (brief) |
| gunicorn | 26.2.0 | 2026-08-24 | ~29.1M | github.com/benoitc/gunicorn | api | WSGI server |
| redis | 8.1.0 | 2026-07-30 | ~58.1M | pypi.org/project/redis | api, worker | Redis client, sync and asyncio |
| SQLAlchemy | 2.1.8 | 2026-11-04 | ~96.8M | github.com/sqlalchemy/sqlalchemy | api, migrations | Core with bound parameters |
| alembic | 1.20.1 | 2026-10-22 | ~54.5M | github.com/sqlalchemy/alembic | migrations | Migrations (ADR-009) |
| psycopg[binary] | 3.3.8 | 2026-11-04 | ~52.7M | pypi.org/project/psycopg | api, worker, migrations | Postgres driver |
| pydantic | 2.14.3 | 2026-11-05 | ~279M | github.com/pydantic/pydantic | all | Schemas |
| pydantic-settings | 2.16.2 | 2026-10-28 | ~116M | github.com/pydantic/pydantic-settings | all | Fail-fast settings (R3) |
| structlog | 26.1.0 | 2026-06-06 | ~30.1M | pypi.org/project/structlog | all | JSON logs with a redaction processor (R4) |
| pytest (dev) | 9.2.0 | 2026-10-27 | ~232M | github.com/pytest-dev/pytest | tests | Test runner |
| pytest-asyncio (dev) | 1.4.1.post1 | 2026-11-01 | ~66.9M | github.com/pytest-dev/pytest-asyncio | tests | Worker async tests |
| ruff (dev) | 0.17.4 | 2026-11-05 | ~100M | docs.astral.sh/ruff | CI | Lint, `print` ban (T20) |
| mypy (dev) | 2.4.1 | 2026-10-28 | ~48.7M | pypi.org/project/mypy | CI | Types |
| pip-audit (dev) | 2.10.1 | 2026-06-10 | ~9.5M | github.com/pypa/pip-audit | CI | SCA |

npm:

| Package | Version | Released | Weekly downloads | Source | Used by | Reason |
|---|---|---|---|---|---|---|
| next | 16.4.6 | 2026-11-09 | ~92.1M | github.com/vercel/next.js | web | Framework (brief) |
| react, react-dom | 19.3.1 | 2026-10-14 | ~253M / ~237M | github.com/react/react | web | Required by Next.js |
| typescript (dev) | 6.0.3 | see §2 | ~418M (all versions) | github.com/microsoft/TypeScript | web | Types |
| tailwindcss, @tailwindcss/postcss | 4.3.5 | 2026-11-06 | ~176M / ~61M | github.com/tailwindlabs/tailwindcss | web | Styling (brief) |
| postcss (dev) | 8.5.32 | 2026-10-26 | ~412M | github.com/postcss/postcss | web | Required by the Tailwind PostCSS plugin |
| eslint (dev) | 10.14.0 | 2026-10-30 | ~205M | github.com/eslint/eslint | web | Lint, `no-console`, `react/no-danger` |
| eslint-config-next (dev) | 16.4.6 | 2026-11-09 | ~47.8M | github.com/vercel/next.js | web | Next.js lint rules (peer: eslint >= 9) |
| @types/react, @types/react-dom (dev) | 19.3.0 | 2026-09-09 | ~226M / ~191M | DefinitelyTyped | web | Types |
| @types/node (dev) | 26.6.6 | 2026-10-28 | ~630M | DefinitelyTyped | web | Types |
| vitest (dev) | 5.1.0 | 2026-11-02 | ~180M | github.com/vitest-dev/vitest | web | Unit tests (engines: node >= 26 ok) |

Not added in S01 (deferred to the spec that needs them): flask-socketio, simple-websocket, python-socketio (S05), httpx, respx (S03), cryptography (S03), clerk-backend-api, PyJWT, svix, @clerk/nextjs (S02), socket.io-client, zod (S05), openapi-typescript (S02, first typed API call), @playwright/test (S02), locust (S09). Flask-Limiter and limits are dropped (ADR-022).

## 4. Repository layout after S01

```text
.
├─ .github/
│  ├─ workflows/ci.yml
│  └─ dependabot.yml
├─ apps/
│  ├─ api/
│  │  ├─ pyproject.toml
│  │  ├─ Dockerfile
│  │  ├─ gunicorn.conf.py
│  │  ├─ alembic.ini
│  │  ├─ migrations/            env.py, versions/0001_baseline.py
│  │  ├─ src/imb_api/           __init__.py (create_app), errors.py, middleware.py,
│  │  │                         registry.py, routes/health.py, wsgi.py
│  │  └─ tests/{unit,integration}/
│  ├─ worker/
│  │  ├─ pyproject.toml, Dockerfile
│  │  ├─ src/imb_worker/        main.py, leader.py, heartbeat.py
│  │  └─ tests/{unit,integration}/
│  └─ web/
│     ├─ package.json, next.config.ts, eslint.config.mjs, postcss.config.mjs, tsconfig.json, Dockerfile
│     ├─ src/proxy.ts, src/lib/csp.ts, src/app/{layout.tsx,page.tsx,globals.css}
│     └─ tests/csp.test.ts
├─ packages/
│  ├─ contracts/                package.json + README (generation starts in S02)
│  └─ py-shared/
│     ├─ pyproject.toml
│     ├─ src/imb_shared/        settings.py, logging.py, db.py, ratelimit.py, clock.py
│     └─ tests/
├─ infra/
│  ├─ compose.yaml
│  ├─ .env.example
│  ├─ postgres/init/00-roles.sh
│  └─ ci/                       check_no_console.py, check_raw_sql.py, check_dep_approvals.py
├─ .gitleaks.toml
├─ package.json                 private root, packageManager pnpm@12.18.0, workspace scripts
├─ pnpm-workspace.yaml, pnpm-lock.yaml
├─ pyproject.toml               uv workspace root (members: apps/api, apps/worker, packages/py-shared)
└─ uv.lock
```

`.github` is repository configuration, not a source directory, so it does not break R1.1.

## 5. packages/py-shared

### settings.py (R3, R17)

`BaseServiceSettings(pydantic_settings.BaseSettings)` with `extra="forbid"`, env-only sources (no dotenv loading in code; Compose injects the env). Fields:

| Field | Type | Rule |
|---|---|---|
| `APP_ENV` | `Literal["dev","staging","prod"]` | required |
| `LOG_LEVEL` | `Literal["DEBUG","INFO","WARNING","ERROR"]` | default `INFO`; `DEBUG` rejected unless `dev` |
| `DATABASE_URL` | `SecretStr` | required; parsed to check host |
| `REDIS_URL` | `SecretStr` | required; must contain a password (R2.4) |
| `ALLOWED_ORIGINS` | `list[str]` from comma-separated text | each must be `scheme://host[:port]`, no path, no `*` |
| `SERVICE_NAME` | `str` | set per app |

Model validators: in `staging`/`prod`, every origin must be `https` (R3.4); in `prod`, DB and Redis hosts must not be `localhost`, `127.0.0.1`, `::1`, or a single-label Docker name (R17.3). `load_settings()` catches `ValidationError`, writes one JSON line listing only the failing field names and error types to stderr, and exits with code 78 (R3.2). Values are never included.

### logging.py (R4)

structlog configured once by `configure_logging(service, level)`. Processor chain: contextvars merge (request id), add timestamp (ISO, UTC), add level, add `service`, **redact**, truncate, JSON renderer. Stdlib logging (gunicorn, alembic) is routed through the same chain.

Redact processor:
- Keys: exact match (case-insensitive) on the R4.2 list, plus any key ending in `_token` or `_secret`. Value becomes `[REDACTED]`. Walks nested dicts and lists.
- Strings: regexes for `Bearer <token>`, JWT shape `eyJ[\w-]+\.[\w-]+\.[\w-]+`, and `Basic <base64>` replaced with `[REDACTED]`.
- Truncate: any string field over 2,000 characters is cut; the whole line is capped at 8 KB (N5).

### db.py (R10.5, R10.6)

- `make_engine(url)`: SQLAlchemy engine, `pool_pre_ping=True`, statement timeout 5 s via connect args.
- `app_transaction(engine, user_id: str | None, role: str | None)`: context manager that begins a transaction and runs exactly one statement with bound parameters: `SELECT set_config('app.user_id', :uid, true), set_config('app.role', :role, true)`. Empty strings when not set, so policies match nothing.

### clock.py and ratelimit.py (R7, ADR-022)

- `Clock` protocol with `now_ms()`. `SystemClock` and `FakeClock` (tests).
- `Rule(name, limit, window_s, fail_mode: "closed" | "open")`.
- `RateLimiter(redis, clock).hit(rule, subject) -> Decision(allowed, remaining, retry_after_s)`.
- Key: `imb:rl:{rule.name}:{subject_part}:{window_index}` where `window_index = now_ms // (window_s*1000)` and `subject_part` is the raw subject if it matches `[A-Za-z0-9_-]{1,64}`, otherwise the first 32 hex characters of its SHA-256 (R7.4).
- Atomic Lua script: `INCR`, then `PEXPIRE` to `window_s*1000 + 1000` on first hit; returns the count. `retry_after_s = max(1, ceil(window_end - now))` (R7.2).
- Redis errors raise `RateLimitUnavailable`; the API maps it to 503 `DEPENDENCY_UNAVAILABLE` for `fail_mode="closed"` and allows the request for `"open"` (R7.3).
- Known trade-off: a fixed window allows up to 2x the limit across a window boundary. Acceptable for the alpha; recorded in ADR-022.

## 6. apps/api

### App factory and request flow

`create_app(settings, *, extra_blueprints=())` builds the Flask app. `extra_blueprints` exists so tests can mount probe routes without shipping them.

Order per request:
1. `before_request`: request id (R5.1). Accept an incoming `X-Request-Id` only if it matches `^[A-Za-z0-9_-]{1,64}$`, else generate `uuid4().hex`. Bind to structlog contextvars.
2. Body limit: `MAX_CONTENT_LENGTH = 8192`; Werkzeug raises 413, mapped to `PAYLOAD_TOO_LARGE` (R5.3).
3. Registry enforcement: the route's declared auth runs (S01: `RequireAuth` always raises 401 `UNAUTHENTICATED`, R8.3), then the declared rate-limit rule.
4. Handler.
5. `after_request`: security headers and CORS.
6. Error handlers: `AppError` subclasses, `HTTPException`, and a catch-all producing 500 `INTERNAL` (R5.6). The catch-all logs `exc_info` with the request id and never the body.

### errors.py (R5.2)

`AppError(code, http_status, message_id)`. Messages come from a dict of Indonesian strings keyed by code (for example `UNAUTHENTICATED: "Kamu perlu masuk dulu."`, `RATE_LIMITED: "Terlalu banyak permintaan. Coba lagi sebentar lagi."`, `INTERNAL: "Terjadi kesalahan. Coba lagi."`). Body: `{"error": {"code", "message", "request_id", "details": {}}}`.

### Headers (R5.4, R5.5)

Always: `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, `X-Frame-Options: DENY`, `Cross-Origin-Resource-Policy: same-site`. In staging/prod: `Strict-Transport-Security: max-age=31536000; includeSubDomains`. Server header: whether gunicorn 26 sends a version in `Server` is UNVERIFIED; the task writes a test that fails if any response header contains a version string, then chooses the fix from gunicorn's current docs.

### CORS (R6)

Own small middleware, no dependency. If `Origin` is in the allow-list: set `Access-Control-Allow-Origin: <origin>` and `Vary: Origin`. Preflight (`OPTIONS` with `Access-Control-Request-Method`): allow methods `GET, POST, PUT, PATCH, DELETE`, headers `Authorization, Content-Type, Idempotency-Key, X-Request-Id`, `Access-Control-Max-Age: 600`, status 204. Otherwise no `Access-Control-*` headers. Never `*`, never `Allow-Credentials` (auth uses bearer tokens, not cookies).

### registry.py (R8)

```text
@api_route(bp, "/healthz", methods=["GET"],
           auth=Public(reason="ADR-013 liveness probe"),
           authz=NoAuthz(reason="ADR-013"),
           limit=EdgeOnly(reason="Cloudflare 60/min/IP, ADR-013"))
```

The decorator stores a `RouteSpec` on the view function. `test_every_route_has_auth_authz_limit` walks `app.url_map`, loads each view function, and fails if `RouteSpec` is missing or any of the three fields is unset; `Public` and `EdgeOnly` require a non-empty reason. A second test fails if any `RouteSpec` declares `multipart/form-data` or a view reads `request.files` (R8.5, checked by AST scan of `src/`).

### Health (R9)

`GET /healthz` returns `{"status":"ok"}` with the standard headers. It does not touch Postgres or Redis (liveness only).

### Process

`gunicorn -c gunicorn.conf.py imb_api.wsgi:app` with `workers = 1`, `threads = 8`, `bind = 0.0.0.0:8000` inside the container, access log off (the app logs requests itself, redacted). Socket.IO arrives in S05 with ADR-003's threaded mode.

## 7. Database bootstrap and migration 0001 (R10)

`infra/postgres/init/00-roles.sh` runs once on an empty dev volume (Postgres entrypoint `docker-entrypoint-initdb.d`). It reads passwords from env and runs SQL through `psql -v` variables (bound, not string-built):

- Roles `imb_migrator` (LOGIN, owner of database `imbooored` and schema `app`), `imb_api`, `imb_worker`, `imb_ops_ro` (all LOGIN, `NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS`).
- `REVOKE ALL ON SCHEMA public FROM PUBLIC; REVOKE CREATE ON SCHEMA public FROM PUBLIC;`
- `GRANT USAGE ON SCHEMA app TO imb_api, imb_worker, imb_ops_ro;`
- Default privileges are not granted; every migration grants explicitly.

Staging and prod roles are created by the owner with the same script against the managed instance (documented in docs/09).

Migration `0001_baseline` (runs as `imb_migrator`, `search_path = app`):
1. `CREATE TABLE app.app_meta (key text PRIMARY KEY, value text NOT NULL);`
2. `ALTER TABLE app.app_meta ENABLE ROW LEVEL SECURITY; ALTER TABLE app.app_meta FORCE ROW LEVEL SECURITY;`
3. `CREATE POLICY app_meta_migrator ON app.app_meta TO imb_migrator USING (true) WITH CHECK (true);`
4. `GRANT SELECT ON app.app_meta TO imb_api, imb_worker;` The grant is deliberate: the test proves that RLS, not a missing grant, hides the rows.
5. `INSERT INTO app.app_meta VALUES ('schema_baseline', '0001');`

`alembic_version` lives in schema `app`, has no grants to app roles, and is the single allowed exception in the RLS catalog test (R10.4).

Compose service `migrate` runs `alembic upgrade head` as `imb_migrator` and exits; `api` and `worker` start only after it completes successfully.

## 8. apps/worker (R11)

`main.py`: load settings, configure logging, start `LeaderLock` and `Heartbeat`, then an idle loop that does nothing else in S01 (R11.4).

`LeaderLock`:
- Acquire: `SET imb:lock:worker_leader <instance_id> NX PX 15000`, where `instance_id = uuid4().hex`.
- Renew every 5 s with a Lua compare-and-`PEXPIRE` (only if the value is still ours).
- If renew returns 0 or Redis errors twice in a row: mark not-leader, stop work (R11.3), and go back to acquiring with jitter 2 to 5 s (R11.2).
- On shutdown (SIGTERM): Lua compare-and-`DEL`.

`Heartbeat`: touches `/tmp/imb-worker-heartbeat` every 5 s. Compose health check fails if the file is older than 30 s. No port is opened (R9.3).

## 9. apps/web (R12)

- `src/lib/csp.ts`: `buildCsp(nonce, isDev)` returns `default-src 'self'; script-src 'self' 'nonce-<n>' 'strict-dynamic'` (+ `'unsafe-eval'` in dev only, per Next.js docs); `style-src 'self' 'nonce-<n>'`; `img-src 'self' data:`; `font-src 'self'`; `connect-src 'self'`; `object-src 'none'`; `base-uri 'self'`; `form-action 'self'`; `frame-ancestors 'none'`; `upgrade-insecure-requests` (not in dev).
- `src/proxy.ts`: generates a 16-byte random nonce per request, sets `Content-Security-Policy` and `x-nonce` on the request and the CSP on the response; matcher skips `_next/static`, `_next/image`, `favicon.ico`, and prefetch requests.
- `next.config.ts`: static headers `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()`, `X-Frame-Options: DENY`; `poweredByHeader: false`.
- `layout.tsx`: `<html lang="id">`, Inter via `next/font/google` (downloaded at build time and served from our origin), body classes from the zinc tokens. Page is dynamic (`await headers()`), as nonces require.
- `page.tsx`: the wordmark `imbooored` in lowercase and one line of copy: "Sedang disiapkan." Nothing else (R12.1).
- `globals.css`: Tailwind v4 import plus the tokens from docs/06 §2 as CSS variables (`--bg`, `--surface`, `--text`, `--text-muted`, `--accent`, focus ring).
- `eslint.config.mjs`: flat config extending `eslint-config-next`, plus `no-console: error` and `react/no-danger: error` (R12.3).

## 10. infra/compose.yaml (R2)

| Service | Image / build | Ports (host) | Health check | Depends on |
|---|---|---|---|---|
| postgres | `postgres:18-alpine@<digest>` | `127.0.0.1:5432` | `pg_isready -U imb_migrator -d imbooored` | none |
| redis | `redis:8.10-alpine@<digest>` | `127.0.0.1:6379` | `redis-cli ping` with `REDISCLI_AUTH` env (password not on the command line of the check) | none |
| migrate | `apps/api` image | none | exits 0 | postgres healthy |
| api | `apps/api` image | `127.0.0.1:8000` | Python `urllib` GET `/healthz` | migrate completed, redis healthy |
| worker | `apps/worker` image | none | heartbeat file age < 30 s | migrate completed, redis healthy |
| web | `apps/web` image | `127.0.0.1:3000` | Node `fetch('/')` returns 200 | api healthy |

- Secrets come from `infra/.env` (untracked; `infra/.env.example` committed with placeholders). Redis gets its password through a generated config file mounted read-only, not a command-line flag, so it does not show in process listings.
- Images run as non-root users; Python images use `python:3.14-slim@<digest>`, web uses `node:26-alpine@<digest>`.
- Named volumes for Postgres and Redis data; `docker compose down -v` removes them (R2.6).

## 11. CI (R13, R14)

`.github/workflows/ci.yml`, triggers `pull_request` and `push` to `main`. Top-level `permissions: contents: read`. All third-party actions pinned to full commit SHAs, resolved with `git ls-remote` during the task and noted with the tag in a comment.

| Job | Steps |
|---|---|
| python | setup Python 3.14 and uv; `uv sync --frozen`; `ruff check`; `ruff format --check`; `mypy --strict` on src; `pytest` unit then integration (service containers Postgres 18 and Redis 8.10 with test-only passwords generated per run) |
| web | setup Node 26 and pnpm; `pnpm install --frozen-lockfile`; `pnpm -r lint`; `pnpm -r typecheck`; `pnpm -r test`; `pnpm --filter web build` |
| audit | `uv export --frozen --no-hashes > req.txt` then `pip-audit -r req.txt --strict`; `pnpm audit --audit-level high`; OSV-Scanner on `uv.lock` and `pnpm-lock.yaml` |
| secrets | gitleaks binary (checksum verified): `--log-opts` diff range on PRs, full history on `main` |
| gates | `python infra/ci/check_no_console.py`, `check_raw_sql.py`, `check_dep_approvals.py` |

Gate scripts (stdlib only, no new dependencies):
- `check_no_console.py`: scans `apps/**` and `packages/**` excluding `tests/`, `e2e/`, `scripts/`; fails on `print(` in `.py` and `console.log|debug|info` in `.ts/.tsx/.js/.mjs` (R4.4).
- `check_raw_sql.py`: Python AST scan outside `apps/api/migrations`; fails when the first argument to `execute`, `exec_driver_sql`, or `text` is an f-string, a `%` BinOp, a `.format()` call, or string concatenation (R10.7).
- `check_dep_approvals.py`: reads direct dependencies from every `pyproject.toml` and `package.json`, reads the "Dependency approvals" table in `docs/DECISIONS.md`, and fails if a direct dependency or its exact version is missing (R13.6). Transitive dependencies are covered by the audits.

The workflow never runs `audit fix` (R13.4) and receives no environment secrets (R13.7).

`.github/dependabot.yml`: ecosystems `uv`, `npm` (pnpm lockfile), `github-actions`, `docker`; weekly; grouped minor/patch updates; no auto-merge (R14.1). Whether Dependabot reads `uv.lock` directly is UNVERIFIED; the task checks GitHub's current docs and falls back to `pip` on the `pyproject.toml` files if not.

`.gitleaks.toml`: default rules plus a custom rule for 32-hex Spotify client secrets next to the word `spotify`; allow-list only `infra/.env.example` placeholder values (R14.2).

## 12. Test plan

| Req | Test (type) |
|---|---|
| R1.2 | `check_dep_approvals.py` also rejects ranges (`^`, `~`, `>=`) in manifests (unit test of the script) |
| R2.1-R2.6 | Manual smoke on the owner's machine: `docker compose up --wait`, `docker compose ps` all healthy, `docker compose down -v` (recorded in PROGRESS) |
| R3.1-R3.4, R17.3 | `test_settings.py`: missing key exits 78 and names the key without its value; `*` origin rejected in prod; http origin rejected in staging; DEBUG rejected outside dev; localhost DB rejected in prod (unit) |
| R4.1-R4.3 | `test_logging.py`: JSON fields present; nested `access_token`, `Authorization`, `client_secret`, `*_token` redacted; JWT and Bearer strings redacted in messages; 8 KB cap (unit) |
| R4.4, R4.5 | gate script unit tests with fixture files; ruff `T20`; ESLint `no-console` |
| R5.1-R5.6 | `test_api_baseline.py` with a probe blueprint: request id reuse and replacement; envelope shape; 413 at 8,193 bytes; headers present; HSTS only in staging/prod; 500 hides details and logs request id (unit) |
| R6.1-R6.4 | `test_cors.py`: allowed origin echoed with `Vary`; unknown origin gets no `Access-Control-*`; never `*`; preflight max-age 600 (unit) |
| R7.1-R7.5 | `test_ratelimit.py` with `FakeClock`: limit, retry-after >= 1, window reset, hashed long subjects (unit); same against real Redis (integration); Redis down gives 503 for closed and pass for open (integration) |
| R8.1-R8.5 | `test_registry.py`: every route has a spec; a probe route without a spec fails the check; non-public probe returns 401; no multipart (unit) |
| R9.1-R9.3 | `test_health.py`: exact body, no extra fields, required headers (unit); worker exposes no port (compose config check script) |
| R10.1-R10.6 | `test_rls.py` against Postgres: migrator sees 1 row, `imb_api` and `imb_worker` see 0; catalog check for RLS + FORCE; roles have no SUPERUSER/BYPASSRLS; `app_transaction` sets both settings (integration) |
| R10.7 | `check_raw_sql.py` unit tests: f-string, `%`, `.format`, concatenation rejected; bound parameters accepted |
| R11.1-R11.4 | `test_leader.py`: acquire, renew, lose lock stops work within 5 s, second instance stays idle, release on shutdown (integration with real Redis, `FakeClock` for timing math in unit) |
| R12.1-R12.4 | `csp.test.ts`: directives present, nonce included, `unsafe-eval` only in dev (vitest); ESLint fixture fails on `dangerouslySetInnerHTML` and `console.log`; build passes |
| R13-R14 | CI run on the S01 PR is the test; a throwaway PR adding an unapproved dependency must fail the gates job |

N1-N4 are measured once and written to PROGRESS; N5 is covered by the logging test.

## 13. Docs to update in this spec

- `docs/DECISIONS.md`: ADR-022 (own rate limiter), OQ-10 answered (pnpm), merge policy answered, Dependency approvals table filled after owner approval.
- `.kiro/steering/tech.md`: Flask-Limiter and limits marked dropped (ADR-022); versions pinned in S01 added.
- `docs/09-OPS_RUNBOOK.md`: local setup, environment table with OPEN items (R17.2), Cloudflare checklist marked OPEN (R16), owner steps checklist (secret scanning, Dependabot alerts, branch protection requiring CI) (R14.3).
- `docs/05-SECURITY_THREAT_MODEL.md`: rule 13 control text (own limiter), rule 15 stays open.
- `docs/07-ROADMAP.md`: S01 status.
- `README.md`: "Getting started" with real commands once they work.
- `docs/PROGRESS.md`: per task.

## 14. Risks and open items

| Item | Handling |
|---|---|
| gunicorn `Server` header version | Test first, fix per current gunicorn docs (§6) |
| TypeScript 7 compatibility | Stay on 6.0.3; revisit via Dependabot |
| Dependabot support for `uv.lock` | Check docs in the task (§11) |
| Action and tool SHAs | Resolve with `git ls-remote` in the CI task (GitHub API was rate-limited) |
| Inter download at build time needs network | CI has network; if blocked later, vendor the font files under `apps/web/src/fonts` |
| OneDrive sync of `node_modules` and `.venv` | Recommend moving the repo outside OneDrive before the first install; not a blocker |
| OQ-5 hosting | Only docs in S01 |
| Python workspace members are virtual (task 1) | `apps/api`, `apps/worker`, `packages/py-shared` use `[tool.uv] package = false` and are imported through `pythonpath` (pytest, mypy, and later the Dockerfiles), because an installable member needs a build backend (hatchling or uv_build) that is not approved. Revisit if a build backend is approved. |
| ESLint 10 vs Next.js lint plugins (found in task 1) | `pnpm peers check` on 2026-11-10: `eslint-config-next@16.4.6` pulls `eslint-plugin-import@2.32.0`, `eslint-plugin-jsx-a11y@6.10.2`, and `eslint-plugin-react@7.37.5`, whose peer ranges stop at ESLint 9. Proposed fix: use `eslint@9.39.5` (latest 9.x, released 2026-07-10) instead of 10.14.0. That is a major-version change, so it needs owner approval before task 8. Until then ESLint 10.14.0 stays installed and unused (no lint config exists yet). |

## Verified sources

| Fact | Source | Accessed |
|---|---|---|
| Runtime versions and EOL dates | https://endoflife.date/api/python.json, nodejs.json, postgresql.json, redis.json | 2026-11-10 |
| Node 26.13.0 checksum and LTS | https://nodejs.org/dist/index.json | 2026-11-10 |
| npm versions, dates, downloads, peer deps | https://registry.npmjs.org, https://api.npmjs.org/downloads | 2026-11-10 |
| PyPI versions, dates, wheels; download counts | https://pypi.org/pypi/{name}/json, https://pypistats.org/api | 2026-11-10 |
| Next.js nonce CSP via proxy, dynamic rendering required, `unsafe-eval` only in dev, SRI experimental | https://nextjs.org/docs/app/guides/content-security-policy | 2026-11-10 |
| Flask-SocketIO deployment constraints (for S05) | https://flask-socketio.readthedocs.io/en/latest/deployment.html | 2026-11-09 |
| Postgres RLS semantics, FORCE for owners | https://www.postgresql.org/docs/current/ddl-rowsecurity.html | 2026-11-09 |
| gunicorn `Server` header, Dependabot `uv` support, GitHub Action SHAs | UNVERIFIED, resolved in tasks | n/a |
