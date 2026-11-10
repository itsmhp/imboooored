# Progress

Keep under 80 lines. Update at the end of every task and before starting a fresh chat (playbook Prompt C4).

## Current spec

- Spec: S01 Foundation, `.kiro/specs/01-foundation/`
- Stage: requirements, design, and tasks APPROVED 2026-11-10. Task 0 skipped (owner keeps the OneDrive workspace). Task 1 DONE.
- Branch: `s01/task-1-scaffold`

## Last completed task

- S01 task 1: workspace scaffold, approved dependencies installed, lockfiles committed, failing tests written.
- Installed and verified: Python 3.14.7, all 15 Python and 13 web packages at the approved exact versions (no patch updates were available on 2026-11-10).
- `ruff check` and `ruff format --check`: clean. `pytest`: fails only with `ModuleNotFoundError` for `imb_shared.{settings,logging,clock,ratelimit}` and the three gate scripts, as intended.
- `pnpm install --frozen-lockfile`: ok, lockfile passed pnpm's supply-chain check.

## Done so far

| Date | Spec / task | Commit | Notes |
|---|---|---|---|
| 2026-11-09 | Prompt A planning docs | 8bc31d6 | docs 00-09, openapi draft, steering |
| 2026-11-10 | S01 requirements, design | 47da3cb | dependency approvals recorded |
| 2026-11-10 | S01 tasks approved | e166eb1 | |
| 2026-11-10 | S01 task 1 | (this branch) | scaffold + failing tests |

## Gate status (do not skip)

- Spike items 3 and 4 with the host token: DEFERRED (ADR-021). Blocks S03 onward.
- Spike item 6 (403 for a non-allowlisted account): not tested.

## Decisions pending (owner)

- ESLint major version (needed before task 8): `eslint-config-next@16.4.6` pulls plugins that only support ESLint up to 9. Proposal: replace `eslint@10.14.0` with `eslint@9.39.5`. Needs approval (major change). Details in design section 14.
- OQ-5 hosting (before S02 design).

## Local tool notes

- uv 0.13.7 lives at `%USERPROFILE%\.imbooored\tools\uv-0.13.7\uv.exe` (checksum verified). The global `uv` is still 0.12.19 because `uvx.exe` was locked by a running MCP server; update it with `uv self update 0.13.7` after closing Kiro if wanted.
- Node 26.13.0 portable and pnpm 12.18.0 (`%APPDATA%\npm`) are on PATH. System Node 25 is end of life.
- The network to PyPI and npm was slow on 2026-11-10 (pnpm install took 11 min). Use `UV_HTTP_TIMEOUT=300` if uv times out.

## Exact next step

- S01 task 2: implement `imb_shared/settings.py` and `imb_shared/logging.py` until `test_settings.py` and `test_logging.py` pass.

## How to resume in a fresh chat

1. Paste: "Read the steering files, docs/PROGRESS.md, and .kiro/specs/01-foundation/. Then do task 2 only."
2. Confirm the branch is clean and the expected tests still fail only on missing modules.
3. After the task: read the full diff, run tests yourself, commit small.

## Commands to run tests locally

```text
.venv\Scripts\ruff.exe check .
.venv\Scripts\ruff.exe format --check .
.venv\Scripts\python.exe -m pytest -q
%USERPROFILE%\.imbooored\tools\uv-0.13.7\uv.exe sync --all-packages --frozen
pnpm install --frozen-lockfile
```
