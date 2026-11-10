---
inclusion: always
---

# Product: imbooored

- Name is always lowercase: "imbooored".
- imbooored is a web app for discovering music through strangers' public Spotify Jams. Hosts publish a room linking to their Jam with hashtags; listeners browse, watch the current track live, suggest tracks, and vote; tracks that reach the threshold go to the host's Spotify queue.
- Personas: Host (≤ 5, Spotify-allowlisted), Listener (Clerk account, never connects Spotify), Admin (owner).
- MVP is a closed alpha. Do not design features that need more than 5 Spotify-authorized users.
- Source of truth: `docs/00-PROJECT_BRIEF.md` (scope), `docs/01-SPOTIFY_CONSTRAINTS.md` (what Spotify allows), `docs/DECISIONS.md` (ADRs). If a request conflicts with them, say so before acting.
- UI copy is Indonesian. Code, comments, docs, commit messages are English.
- Look: dark, zinc surfaces, one emerald accent, Inter. Cover art shown unaltered. Tokens in `docs/06-UX_SPEC.md`.
- Every place that shows Spotify metadata or artwork shows Spotify attribution and links back to Spotify.
- Never build: games/leaderboards, ML on Spotify content, analysis or profiling from Spotify data, ads or payments, features aimed at children, audio playback.
- Vibe Points are a private tally (ADR-011) until the owner decides otherwise.
- Treat every Spotify behavior as UNVERIFIED unless `docs/00-spotify-spike-results.md` or a cited official doc proves it.
