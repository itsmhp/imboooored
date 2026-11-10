# S01 Foundation: Tasks

Status: APPROVED by the owner on 2026-11-10 · [requirements](./requirements.md) and [design](./design.md) approved 2026-11-10

Rules for every task:
- One task per chat session. Start with: "Read the steering files, docs/PROGRESS.md, and .kiro/specs/01-foundation/. Then do task N only."
- Write or update the tests first, see them fail, then implement.
- Add no dependency outside design §3 and the approvals table in docs/DECISIONS.md.
- Finish with: run lint + tests, read the full diff, update docs/PROGRESS.md, commit on a feature branch.
- Definition of Done: tests green, lint and types clean, no `print`/`console.*`, no secrets, docs updated, small diff.

## Task 0 (owner, optional, before task 1): move the repo out of OneDrive

- [x] 0. (Done 2026-11-10 by a fresh `git clone` to `C:\dev\imbooored`; the OneDrive copy was left untouched for the owner to delete.) Move the working copy to a non-synced path (for example `C:\dev\imbooored`) before the first dependency install, because `node_modules` and `.venv` hold tens of thousands of small files.
  - Steps: close editors, move the folder, reopen it in Kiro, run `git status` (must be clean).
  - Not required for correctness; skipping it only risks slow sync and file locks.

## Tasks

- [ ] 1. Workspace scaffold, approved dependencies, and failing tests
  - Create root `pyproject.toml` (uv workspace), `apps/api`, `apps/worker`, `packages/py-shared` `pyproject.toml` files with exact pins from design §3; root `package.json` (`packageManager: pnpm@12.18.0`), `pnpm-workspace.yaml`, `apps/web/package.json`, `packages/contracts/package.json` + README.
  - Re-read each registry before installing; if a newer patch exists, use it and update the approvals table in the same commit.
  - Run `uv lock`, `pnpm install`; commit `uv.lock` and `pnpm-lock.yaml`.
  - Write failing unit tests: `packages/py-shared/tests/test_settings.py`, `test_logging.py`, `test_ratelimit.py`, `test_clock.py`; `infra/ci/tests/test_gates.py` (fixtures for no-console, raw-SQL, dep-approval, version ranges).
  - Requirements: R1.1, R1.2, R1.3, R1.4 (stub `infra/.env.example`), R15.1, R15.2.
  - Files: root manifests and lockfiles, `apps/*/pyproject.toml`, `packages/*`, tests listed above.
  - Done when: `uv run pytest` fails only on missing modules, `pnpm install --frozen-lockfile` succeeds, no ranges in any manifest.
  - Run lint + tests.

- [ ] 2. Settings and logging in py-shared
  - Implement `settings.py` and `logging.py` per design §5 until task 1's settings and logging tests pass.
  - Requirements: R3.1 to R3.6, R4.1 to R4.3, R17.3, N5.
  - Files: `packages/py-shared/src/imb_shared/{settings,logging}.py`.
  - Depends on: 1.
  - Run lint + tests.

- [ ] 3. Clock, rate limiter, and DB helper in py-shared
  - Implement `clock.py`, `ratelimit.py` (Lua fixed window, hashed subjects, fail modes), `db.py` (`make_engine`, `app_transaction`).
  - Add integration tests (pytest marker `integration`) for the limiter against real Redis and for `app_transaction` against Postgres; they run in CI and with Compose locally.
  - Requirements: R7.1 to R7.5, R10.5.
  - Files: `packages/py-shared/src/imb_shared/{clock,ratelimit,db}.py`, `packages/py-shared/tests/integration/`.
  - Depends on: 2.
  - Run lint + tests.

- [ ] 4. API baseline: app factory, request id, errors, body limit, headers, CORS
  - Tests first: `apps/api/tests/unit/test_api_baseline.py`, `test_cors.py` with a probe blueprint passed through `extra_blueprints`.
  - Implement `create_app`, `errors.py` (Indonesian messages), `middleware.py` (request id, security headers, CORS).
  - Requirements: R5.1 to R5.6, R6.1 to R6.4.
  - Files: `apps/api/src/imb_api/{__init__,errors,middleware}.py`, tests above.
  - Depends on: 3.
  - Run lint + tests.

- [ ] 5. Route registry, auth placeholder, health endpoint, gunicorn config
  - Tests first: `test_registry.py` (spec required, reason required for Public/EdgeOnly, 401 for non-public, no multipart, AST scan for `request.files`), `test_health.py` (exact body, headers, no version string in any header).
  - Implement `registry.py`, `routes/health.py`, `wsgi.py`, `gunicorn.conf.py`. Read gunicorn 26 docs for the `Server` header before choosing a fix; cite the URL in the commit message and in design §14.
  - Requirements: R8.1 to R8.5, R9.1, R9.2, N4.
  - Files: `apps/api/src/imb_api/{registry,wsgi}.py`, `apps/api/src/imb_api/routes/health.py`, `apps/api/gunicorn.conf.py`, tests.
  - Depends on: 4.
  - Run lint + tests.

- [ ] 6. Postgres bootstrap, Alembic baseline, RLS proof
  - Tests first: `apps/api/tests/integration/test_rls.py` (migrator sees 1 row, `imb_api` and `imb_worker` see 0, catalog check for RLS + FORCE with `alembic_version` as the only exception, no SUPERUSER/BYPASSRLS on app roles).
  - Implement `infra/postgres/init/00-roles.sh` (passwords via `psql -v`), `alembic.ini`, `migrations/env.py`, `versions/0001_baseline.py`.
  - Requirements: R10.1 to R10.4, R10.6.
  - Files: listed above.
  - Depends on: 3.
  - Run lint + tests (integration against a local Postgres container).

- [ ] 7. Worker skeleton: leader lock and heartbeat
  - Tests first: `apps/worker/tests/unit/test_leader.py` (timing math with `FakeClock`), `tests/integration/test_leader_redis.py` (acquire, renew, second instance idle, lose lock stops within 5 s, release on shutdown).
  - Implement `main.py`, `leader.py`, `heartbeat.py`. No Spotify calls, no DB writes.
  - Requirements: R11.1 to R11.4, R9.3.
  - Files: `apps/worker/src/imb_worker/*`, tests.
  - Depends on: 3.
  - Run lint + tests.

- [ ] 8. Web skeleton: placeholder page, CSP nonce, headers, tokens, lint rules
  - Tests first: `apps/web/tests/csp.test.ts` (directives, nonce, `unsafe-eval` only in dev); ESLint fixtures that must fail on `console.log` and `dangerouslySetInnerHTML`.
  - Implement `src/lib/csp.ts`, `src/proxy.ts`, `next.config.ts`, `layout.tsx`, `page.tsx`, `globals.css` (docs/06 tokens), `eslint.config.mjs`, `postcss.config.mjs`, `tsconfig.json`.
  - Re-read the Next.js CSP guide before writing `proxy.ts` and cite it in the commit.
  - Requirements: R12.1 to R12.4.
  - Files: `apps/web/**`.
  - Depends on: 1.
  - Run lint + typecheck + tests + `pnpm --filter web build`.

- [ ] 9. Dockerfiles and Compose
  - Write `apps/api/Dockerfile`, `apps/worker/Dockerfile`, `apps/web/Dockerfile` (non-root, digests pinned), `infra/compose.yaml`, `infra/.env.example` (complete), Redis config generation without the password on the command line.
  - Add a small compose config check (`infra/ci/check_compose.py`, stdlib only): every published port binds `127.0.0.1`, worker publishes none, no inline secret values.
  - Owner smoke test: `docker compose up --wait`, all healthy, `curl 127.0.0.1:8000/healthz`, open `127.0.0.1:3000`, `docker compose down -v`. Record timings (N1) in PROGRESS.
  - Requirements: R2.1 to R2.6, R1.4, N1.
  - Files: Dockerfiles, `infra/compose.yaml`, `infra/.env.example`, `infra/redis/`, `infra/ci/check_compose.py`.
  - Depends on: 5, 6, 7, 8.
  - Run lint + tests + compose check.

- [ ] 10. CI gate scripts
  - Implement `infra/ci/check_no_console.py`, `check_raw_sql.py`, `check_dep_approvals.py` until task 1's gate tests pass. Stdlib only.
  - Requirements: R4.4, R4.5 (ruff `T20` config), R10.7, R13.6, R1.2.
  - Files: `infra/ci/*.py`, root `pyproject.toml` ruff config.
  - Depends on: 1.
  - Run lint + tests, then run each gate on the repo (must pass).

- [ ] 11. CI workflow, Dependabot, gitleaks
  - Resolve each action's latest release tag and full commit SHA with `git ls-remote`; pin SHAs with the tag in a comment. Download gitleaks and OSV-Scanner release binaries in CI with checksum verification.
  - Check GitHub's current docs for Dependabot `uv` support; fall back per design §11 if needed and cite the URL.
  - Write `.github/workflows/ci.yml` (jobs per design §11, `permissions: contents: read`, no secrets), `.github/dependabot.yml`, `.gitleaks.toml`.
  - Open the S01 PR; CI must be green. Then open a throwaway PR adding an unapproved package and confirm the gates job fails; close it.
  - Requirements: R13.1 to R13.7, R14.1, R14.2, N3.
  - Files: `.github/**`, `.gitleaks.toml`.
  - Depends on: 9, 10.
  - Run CI.

- [ ] 12. Documentation updates
  - `docs/09-OPS_RUNBOOK.md`: local setup commands, environment table with OPEN items, Cloudflare checklist marked OPEN, owner checklist (secret scanning, Dependabot alerts, branch protection requiring the CI checks).
  - `docs/05`: rule 13 control text (own limiter, ADR-022); rule 15 stays open.
  - `docs/07`: S01 status. `.kiro/steering/tech.md`: dropped Flask-Limiter/limits, pinned versions. `README.md`: real "Getting started" commands.
  - Requirements: R14.3, R16.1, R16.2, R17.1, R17.2, R18.1.
  - Depends on: 11.
  - Check links; no em dashes.

- [ ] 13. Security gate and progress
  - Run playbook Prompt C3 on `git diff main...HEAD`; fix blockers in a follow-up commit; record the pass/fail table in the PR description.
  - Run `pip-audit`, `pnpm audit`, OSV-Scanner, gitleaks locally and confirm they match CI.
  - Update `docs/PROGRESS.md` (Prompt C4) with commit hashes and the exact next step (S02 requirements).
  - Depends on: 12.

## Owner-only steps (not code)

- [ ] Enable GitHub secret scanning and push protection, Dependabot alerts, and branch protection on `main` requiring the CI checks (after task 11 creates them).
- [ ] Decide OQ-5 (hosting) before S02 design, because Clerk instances and domains depend on it.
- [ ] Run the deferred host-with-participant spike before S03 (ADR-021).
