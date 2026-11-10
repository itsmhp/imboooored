# Progress

Keep under 80 lines. Update at the end of every task and before starting a fresh chat (playbook Prompt C4).

## Current spec

- Spec: S01 Foundation, `.kiro/specs/01-foundation/`
- Stage: requirements.md and design.md APPROVED 2026-11-10, all design §3 dependencies approved (recorded in DECISIONS). tasks.md drafted, WAITING FOR OWNER APPROVAL. Next after approval: task 0 (optional repo move) then task 1 in a fresh chat.
- Branch: none (git initialized on `main`, no commits yet)

## Last completed task

- Phase 0 spike partially run on 2026-11-10 (see `docs/00-spotify-spike-results.md`).
- Phase 1 repo setup done: `.kiro/steering/security.md`, `.gitignore`, `git init`, reference moved to `docs/reference/`.
- Nothing committed yet.

## Done so far

| Date | Spec / task | Commit | Notes |
|---|---|---|---|
| 2026-11-09 | Prompt A planning docs | none | docs/00-09, openapi draft, steering |
| 2026-11-10 | Spike (partial), Phase 1 repo setup | none | |
| 2026-11-10 | S01 requirements draft | none | awaiting approval |

## Gate status (do not skip)

- Spike item 3 and 4 with the Spotify **host** token: DEFERRED by the owner on 2026-11-10 (no participant available; ADR-021). Only proven as a Jam participant. Blocks S03 onward, not S01 or S02.
- Spotify MCP server installed outside the repo (3 scopes). Use it for observations; `spike.ps1` stays the evidence source.
- Spike item 6 (403 for a non-allowlisted account): NOT TESTED (account B is on the allowlist).
- Spike item 5 `limit=11`, default limit, `/tracks/{id}`: re-run needed.

## Decisions pending (owner)

- See [DECISIONS.md](./DECISIONS.md) "Open questions for the owner" (OQ-0 is now done: security.md committed to the working tree).

## Exact next step

1. Owner reviews `.kiro/specs/01-foundation/requirements.md` and approves or edits it.
2. Owner finishes the host-token spike when convenient (needed before S03).
3. Owner commits `docs: planning baseline` after reading the docs.

## How to resume in a fresh chat

1. Paste: "Read the steering files, docs/PROGRESS.md, and the active spec in .kiro/specs/<spec>/. Then do task <N> only."
2. Confirm the branch is clean and existing tests pass before starting.
3. After the task: read the full diff, run tests yourself, commit small.

## Commands to run tests locally

```text
(filled in during S01)
```
