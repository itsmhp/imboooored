# 00 · Project Brief

Status: DRAFT for owner review · Written 2026-11-09 · Planning phase (no code)

## Purpose

Define what imbooored is, who it serves, what the first release contains, and how we will know it worked. Every other doc derives from this one. If this doc and another doc disagree, fix the other doc or record an ADR in [DECISIONS.md](./DECISIONS.md).

## Content

### Problem

Algorithmic playlists keep recommending what a listener already likes. The name "imbooored" (always lowercase) names that boredom. People who host a Spotify Jam are already curating music live, but nobody outside their circle can find those sessions.

imbooored is a responsive web app where hosts publish a "room" that points to their Spotify Jam, tag it with hashtags, and let strangers watch what is playing, suggest tracks, and vote. Suggestions that reach the vote threshold go into the host's Spotify queue.

### Personas

| Persona | Who | Needs | Spotify authorization |
|---|---|---|---|
| Host | One of at most 5 allowlisted people (closed alpha), Spotify Premium | Publish a room fast, keep control of their queue, not leak their account | Yes. Must be on the Spotify app allowlist. See [01-SPOTIFY_CONSTRAINTS.md](./01-SPOTIFY_CONSTRAINTS.md) |
| Listener | Anyone with an imbooored account (Clerk sign-in) | Browse live rooms by vibe, see the current track, suggest and vote | No. Listeners never connect Spotify |
| Admin | The owner | Grant/revoke host role, force-close rooms, watch quota and alerts, handle deletion requests | Owner's own account is one of the 5 allowlist slots |

### Core loop

1. Host connects Spotify once (OAuth, host only), pastes their Jam link, adds 1–5 hashtags, opens a room.
2. The worker polls the host's playback server-side and pushes `track:changed` to everyone in the room.
3. A listener opens the feed, filters by tag (for example `#postpunk`), and swipes between rooms.
4. In a room, the listener sees cover, title, artist, and a progress bar that moves locally between server updates.
5. The listener searches for a track and suggests it. Other listeners vote.
6. When votes reach the room threshold, the worker adds the track to the host's Spotify queue and the room sees it move to "Masuk antrean".
7. Participation earns Vibe Points (scope pending owner decision, see [DECISIONS.md](./DECISIONS.md) ADR-011).
8. The host closes the room, or the system closes it after the host leaves or playback stays idle.

### MVP scope (closed alpha, milestone M3 in [07-ROADMAP.md](./07-ROADMAP.md))

In scope:

- Clerk sign-in for everyone; role `listener` by default, `host` granted by admin only.
- Spotify connect for hosts (Authorization Code + PKCE, encrypted token vault).
- Room create/close, Jam link stored as data and never fetched, normalized hashtags.
- Live feed with exact tag filter and cursor pagination.
- Realtime now-playing per room with local progress interpolation.
- Track search through our server, suggest, vote, threshold push to the host queue.
- Host moderation: reject a suggestion, set the vote threshold (2–10).
- Vibe Points ledger (append-only), shown only to the user themself.
- Ghost-room auto-close, startup reconciliation.
- Account deletion and data export, privacy policy draft.
- Indonesian UI copy, dark zinc/emerald theme, Inter.

Out of scope for MVP:

- Audio playback inside imbooored (no Web Playback SDK, no previews).
- Listeners connecting Spotify, playlists, library writes.
- Chat, DMs, follows, profiles of other users, comments.
- Leaderboards, rewards, or anything that makes Vibe Points competitive.
- File uploads of any kind (security rule 16).
- Native mobile apps, push notifications, email marketing.
- Monetization of any kind (Spotify Developer Policy section IV, see [01](./01-SPOTIFY_CONSTRAINTS.md)).
- Multi-region, horizontal scale-out (described in [02](./02-ARCHITECTURE.md), not built).

### Non-goals

- Replacing Spotify Jam or replicating its UI. imbooored is a discovery layer around Jams.
- Recommendations, ML ranking, or analysis of Spotify content (prohibited by Spotify Developer Policy III).
- Growing past 5 hosts while the Spotify app is in Development Mode.

### Success metrics (closed alpha, 4 weeks after M3)

| Metric | Target | Measured by |
|---|---|---|
| Hosts active | ≥ 3 of 5 hosts open ≥ 2 rooms per week | `rooms` table |
| Listener return | ≥ 40% of listeners who joined a room come back the next week | `audit_log` + presence events (aggregated, no Spotify data) |
| Track-change latency (natural end of track) | p95 ≤ 4 s from Spotify change to listener screen | worker `observed_at` vs client receive time |
| Track-change latency (host skip) | p95 ≤ 12 s | same |
| Suggest → queued success | ≥ 95% of approved suggestions reach the queue, excluding host "no active device" | `queue_items.status` |
| Quota health | 0 `QUOTA_EXCEEDED` responses per week | worker metrics |
| Security | 0 secrets/tokens in logs (CI grep + log sampling), 0 open high/critical SCA findings | CI, log review |

### Glossary

| Term | Meaning |
|---|---|
| Room | A live listing that points to one host's Spotify Jam. One host has at most one live room. |
| Jam | Spotify's group listening session, owned by the host inside the Spotify app. imbooored does not create or control it. |
| Jam link | The invite URL the host pastes. Stored as text, validated by regex, never fetched by our servers. |
| Suggestion | A track proposed by a listener for a room (`queue_items` row). |
| Threshold | Votes needed before a suggestion is pushed to the host's Spotify queue. |
| Push | The worker calling Spotify "Add Item to Playback Queue" with the host's token. |
| Vibe Points | Per-user participation tally from an append-only ledger. Not a game, no ranking. |
| Ghost room | A room marked live whose host or playback is gone. |
| MusicProvider | Internal interface hiding Spotify. Implementations: `SpotifyProvider`, `FakeMusicProvider`, `ReplayMusicProvider`. |
| Dev Mode | Spotify "Development Mode": ≤ 5 allowlisted users per app, owner must have Premium. |
| UNVERIFIED | A fact not proven by the owner's spike or by a doc we read. Must not be treated as true in code. |

## Assumptions

- A1. The Phase 0 spike (`docs/00-spotify-spike-results.md`) has not been run yet. Every Spotify behavior is UNVERIFIED until it is.
- A2. The 5 hosts are people the owner knows personally and can add to the Spotify allowlist by email.
- A3. Listeners sign in with Clerk before using the feed (ADR-006). A public read-only feed is an owner decision.
- A4. Primary audience is Indonesia; UI copy is Indonesian, code and docs are English.
- A5. No revenue during alpha.
- A6. The reference design chat lives at [`reference/Panduan Vibe Coding Bebas Slop.md`](./reference/Panduan%20Vibe%20Coding%20Bebas%20Slop.md).

## Open questions

- Q1. Is a closed alpha of ≤ 5 hosts worth building if Spotify never grants more? (Blocks everything; see [DECISIONS.md](./DECISIONS.md) OQ-1.)
- Q2. Vibe Points: keep as plain tally, defer, or drop? (OQ-3)
- Q3. Public feed without sign-in? (OQ-4)
- Q4. Minimum age for users. Spotify policy forbids products targeted at children; UU PDP has rules for children's data. Proposed: 18+ self-declared at sign-up. (OQ-7)

## Verified sources

| Fact | Source | Accessed |
|---|---|---|
| Dev Mode is for non-commercial personal projects and "should not be relied on as a foundation for building or scaling a business" | https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security | 2026-11-09 |
| Developer Policy prohibitions (games, ML training, analysis, commercial use in streaming SDAs, children) | https://developer.spotify.com/policy | 2026-11-09 |
| All runtime Spotify behavior in this doc | UNVERIFIED (spike not run) | n/a |
