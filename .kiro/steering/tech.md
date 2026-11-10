---
inclusion: always
---

# Tech stack and dependency candidates

- Stack: Next.js (App Router, TypeScript, Tailwind) · Flask + Flask-SocketIO (threaded, ADR-003) · asyncio worker with httpx · Redis · PostgreSQL with RLS · Clerk · Cloudflare · Docker Compose for dev parity · pytest, vitest, Playwright.
- Change the stack only with an ADR in `docs/DECISIONS.md`.
- No eventlet. No APScheduler/Celery for polling. No ORM sessions for request handling (SQLAlchemy Core + bound params).
- Every package below is a **candidate**, tagged **NEEDS HUMAN VERIFICATION**. None is claimed safe. Before adding any: check the exact registry URL, maintainer, last release, download counts, typosquat lookalikes; run SCA; get the owner's written approval; record it in `docs/DECISIONS.md` "Dependency approvals". Pin exact versions and commit lockfiles.

## Web (npm registry)

| Package | Registry URL | Why | Alternatives considered |
|---|---|---|---|
| next | https://www.npmjs.com/package/next | framework (brief) | Remix, Vite SPA |
| react, react-dom | https://www.npmjs.com/package/react | required by Next.js | none |
| typescript | https://www.npmjs.com/package/typescript | types | none |
| tailwindcss | https://www.npmjs.com/package/tailwindcss | styling (brief) | CSS modules |
| @clerk/nextjs | https://www.npmjs.com/package/@clerk/nextjs | Clerk middleware, components, `getToken` | Clerk JS SDK directly |
| socket.io-client | https://www.npmjs.com/package/socket.io-client | Socket.IO protocol client | none for Socket.IO |
| zod | https://www.npmjs.com/package/zod | validate inbound socket payloads client-side | valibot, hand checks |
| openapi-typescript | https://www.npmjs.com/package/openapi-typescript | generate `packages/contracts` | orval |
| vitest | https://www.npmjs.com/package/vitest | unit tests | jest |
| @playwright/test | https://www.npmjs.com/package/@playwright/test | E2E | Cypress |
| eslint, eslint-config-next | https://www.npmjs.com/package/eslint | lint incl. `no-console`, `react/no-danger` | biome |
| pnpm (tool) | https://www.npmjs.com/package/pnpm | workspaces (OQ-10) | npm workspaces |

## Python (PyPI): api, worker, py-shared

| Package | Registry URL | Why | Alternatives considered |
|---|---|---|---|
| flask | https://pypi.org/project/Flask/ | API framework (brief) | FastAPI (stack change) |
| flask-socketio | https://pypi.org/project/Flask-SocketIO/ | sockets (brief) | python-socketio ASGI |
| simple-websocket | https://pypi.org/project/simple-websocket/ | WebSocket for threaded mode (ADR-003) | gevent-websocket |
| python-socketio | https://pypi.org/project/python-socketio/ | `AsyncRedisManager` in worker | none |
| gunicorn | https://pypi.org/project/gunicorn/ | WSGI server | waitress |
| httpx | https://pypi.org/project/httpx/ | async HTTP to Spotify | aiohttp |
| redis | https://pypi.org/project/redis/ | Redis client (sync + asyncio) | none |
| sqlalchemy | https://pypi.org/project/SQLAlchemy/ | Core queries, bound params | psycopg only |
| alembic | https://pypi.org/project/alembic/ | migrations (ADR-009) | dbmate |
| psycopg (v3) | https://pypi.org/project/psycopg/ | Postgres driver | psycopg2-binary |
| pydantic, pydantic-settings | https://pypi.org/project/pydantic/ | request/event schemas, env validation fail-fast | marshmallow |
| cryptography | https://pypi.org/project/cryptography/ | AES-256-GCM token vault (ADR-016) | PyNaCl |
| clerk-backend-api | https://pypi.org/project/clerk-backend-api/ | verify Clerk session tokens (ADR-002) | PyJWT |
| PyJWT | https://pypi.org/project/PyJWT/ | fallback JWKS verification | python-jose |
| svix | https://pypi.org/project/svix/ | verify Clerk webhooks | standardwebhooks |
| structlog | https://pypi.org/project/structlog/ | JSON logs + redaction processor | stdlib logging + json formatter |
| Flask-Limiter, limits | https://pypi.org/project/Flask-Limiter/ , https://pypi.org/project/limits/ | Redis-backed rate limits (ADR-018) | hand-written limiter |
| pytest, pytest-asyncio | https://pypi.org/project/pytest/ | tests | unittest |
| respx | https://pypi.org/project/respx/ | mock httpx in contract tests | pytest-httpx |
| ruff, mypy | https://pypi.org/project/ruff/ , https://pypi.org/project/mypy/ | lint, types | flake8, pyright |
| pip-audit | https://pypi.org/project/pip-audit/ | SCA in CI | safety |
| uv (tool) | https://pypi.org/project/uv/ | env + lockfile | poetry, pip-tools |
| locust | https://pypi.org/project/locust/ | load tests (S09) | k6 |

## Non-package tools

gitleaks (https://github.com/gitleaks/gitleaks), OSV-Scanner (https://github.com/google/osv-scanner), GitHub Dependabot + secret scanning. NEEDS HUMAN VERIFICATION.

## Version rules

- Use the current patched release at install time, pin exactly, record the version in the approvals table.
- Read the library's current official docs (context7 or web) before using an API; cite the URL in the spec's design.md.
