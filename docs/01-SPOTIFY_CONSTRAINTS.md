# 01 · Spotify Constraints

Status: DRAFT · Written 2026-11-09 · Spike results: **MISSING**

## Purpose

List what Spotify allows, what it forbids, and what we have not proven. The product only exists if two behaviors hold: the host's Jam is readable through the host's token, and a queue push lands in the Jam. Neither is proven yet.

## Labeling rule

`docs/00-spotify-spike-results.md` does not exist. Per the owner's instruction, **every Spotify behavior in this repo is UNVERIFIED** until the spike records evidence. The "Doc" column below says whether an official Spotify page we read on 2026-11-09 states the behavior. Doc-backed is still UNVERIFIED for runtime: docs and the Feb–Jul 2026 changes have been inconsistent (the March 2026 changelog reverted parts of February).

## Content

### 1. Access model and quotas

| # | Constraint | Doc | Status | Design consequence |
|---|---|---|---|---|
| C1 | App owner must have active Premium; app stops working if it lapses | [quota-modes], [feb-2026-guide] | UNVERIFIED | Owner Premium is a production dependency. Alert in [09](./09-OPS_RUNBOOK.md). |
| C2 | Dev Mode: up to 5 authenticated users, each added by hand to the allowlist | [quota-modes] | UNVERIFIED | Max 5 hosts including the owner. Listeners never authorize Spotify. |
| C3 | Users not on the allowlist can log in but API calls return 403 | [quota-modes] | UNVERIFIED | Connect flow must detect 403 after callback and show the "alpha penuh" state ([06](./06-UX_SPEC.md)). |
| C4 | Extended Quota only for registered organizations with ≥ 250k MAU and a launched service (since 2025-05-15) | [quota-modes] | UNVERIFIED | No path out of Dev Mode for an individual. See kill criteria. |
| C5 | Dev Mode quota counted per developer account; up to 25 Client IDs share one quota (since 2026-07-23) | [quota-blog-jul], [changelog-jul] | UNVERIFIED | Dev, staging, prod drain one pool if they use the same developer account. |
| C6 | Quota 429 body: `{"error":{"status":429,"message":"Too many requests","reason":"QUOTA_EXCEEDED"}}` | [quota-modes] | UNVERIFIED | Separate handling from rate-limit 429. Quota bucket sizes are not published. |
| C7 | Rate limit is computed over a rolling 30 s window; 429 responses include `Retry-After` | [rate-limits] | UNVERIFIED | Global circuit breaker honoring `Retry-After`. |
| C8 | Endpoints grouped into quota buckets; groupings and limits "subject to change" | [quota-modes] | UNVERIFIED | Budgets in our code are configuration, not constants. |
| C9 | Access tokens live 1 hour; refresh tokens live 6 months from authorization; refreshing does not extend them | [refresh] | UNVERIFIED | Track `authorized_at`; warn host at 150 days; force reconnect at expiry (`invalid_grant`). |
| C10 | Refresh response may or may not include a new refresh token; if absent keep the old one | [refresh] | UNVERIFIED | Vault update is conditional. |
| C11 | `invalid_grant` means discard the token and re-authorize; do not retry | [refresh] | UNVERIFIED | Connection → `needs_reauth`, close live room with reason `token_revoked`. |
| C12 | Dev Mode endpoint access changes for existing integrations were postponed on 2026-03-09 "with updated timelines to follow" | [blog-feb] | UNVERIFIED | Player endpoints could become restricted later. Kill criterion K3. |
| C13 | No public endpoint to revoke a user's grant | none (community issue only) | UNVERIFIED | Disconnect = delete our copy + show the user how to remove access in their Spotify account settings. |
| C14 | `product` (premium/free) and `email` were removed from the user object | [changelog-feb] | UNVERIFIED | We cannot pre-check Premium. Detect on first queue push failure. |

### 2. Endpoint inventory

Only endpoints listed as still available in [changelog-feb] are allowed. Anything else needs a doc link and an ADR.

| Endpoint | Auth / scope | In Dev Mode list? | Used for | Expected failure modes |
|---|---|---|---|---|
| `GET https://accounts.spotify.com/authorize` | PKCE + state | Yes | Host connect | user denies → `error=access_denied` on redirect |
| `POST https://accounts.spotify.com/api/token` (authorization_code, refresh_token, client_credentials) | client id + secret | Yes | Code exchange, refresh, server search token | 400 `invalid_grant`, 400 `invalid_client`, 429, 5xx |
| `GET /v1/me` | any user token | Yes | Read Spotify user id at connect; detect 403 non-allowlisted | 403 not allowlisted (C3), 401 |
| `GET /v1/me/player/currently-playing` | `user-read-currently-playing` | Yes | Now-playing poll | 200 with `item`; 204 nothing playing; `item` null for ads; `is_local` true with null id; 401; 403; 429; 5xx. Jam visibility UNVERIFIED |
| `GET /v1/me/player/devices` | `user-read-playback-state` | Yes | Check active device before push | empty list → host has no active device |
| `POST /v1/me/player/queue?uri=` | `user-modify-playback-state` | Yes | Push approved suggestion | Premium only per [add-to-queue]; no active device (404, reason `NO_ACTIVE_DEVICE` UNVERIFIED); 403; 429. Ordering not guaranteed with other player calls. Whether it lands in the Jam queue: UNVERIFIED |
| `GET /v1/search?type=track&limit≤10` | client credentials (preferred) or user token | Yes, `limit` max 10, default 5 | Suggest modal search | 400 if limit > 10; 429; client credentials in Dev Mode UNVERIFIED (spike item 5) |
| `GET /v1/tracks/{id}` | client credentials | Yes | Resolve a suggested track id to trusted metadata | 404 bad id; 429 |
| `GET /v1/me/player` | `user-read-playback-state` | Yes | Not used in MVP (currently-playing is enough) | n/a |
| `GET /v1/me/player/queue` | `user-read-currently-playing`, `user-read-playback-state` | Yes | Not used in MVP (quota cost) | n/a |
| `GET /v1/tracks` (several) | n/a | **Removed** Feb 2026 | Do not use | n/a |
| `GET /v1/users/{id}` | n/a | **Removed** Feb 2026 | Do not use | n/a |

Scopes requested: `user-read-currently-playing user-read-playback-state user-modify-playback-state`. Nothing else.

### 3. Verified vs unverified summary

| Claim | Spike item | Status |
|---|---|---|
| Currently-playing with the host token returns the Jam's track | 3 | UNVERIFIED (blocking) |
| Queue push with the host token adds to the Jam queue | 4 | UNVERIFIED (blocking) |
| Client-credentials search works in Dev Mode, ≤ 10 results | 5 | UNVERIFIED |
| Non-allowlisted account gets 403, error shape | 6 | UNVERIFIED |
| Refresh may rotate refresh token | 7 | UNVERIFIED (doc-backed) |
| `Retry-After` present, value in seconds | 8 | UNVERIFIED (doc-backed) |
| Free users can join a Jam from a link | n/a | UNVERIFIED, not documented in Web API docs |
| Behavior when host leaves or ends the Jam (does currently-playing still return host's own playback?) | 3 | UNVERIFIED |

### 4. MusicProvider contract

All Spotify access goes through this interface. Python, async, used by `apps/worker` and the search path in `apps/api`. Types are dataclasses; field names match the DTOs in [04](./04-API_AND_EVENTS.md).

```text
interface MusicProvider:
  get_now_playing(conn: HostConnection) -> NowPlaying | Nothing | ProviderError
  list_devices(conn: HostConnection) -> list[Device] | ProviderError
  add_to_queue(conn: HostConnection, track_id: TrackId, idempotency_key: str) -> Queued | ProviderError
  search_tracks(query: str, limit: int<=10) -> list[TrackDTO] | ProviderError
  get_track(track_id: TrackId) -> TrackDTO | ProviderError
  exchange_code(code: str, code_verifier: str, redirect_uri: str) -> TokenSet | ProviderError
  refresh(refresh_token: Secret) -> TokenSet | ProviderError

NowPlaying  { track: TrackDTO, progress_ms: int, is_playing: bool, observed_at_ms: int }
Nothing     { reason: "no_playback" | "ad" | "local_file" | "episode" }
TrackDTO    { id: str[22], title: str<=300, artists: list[str]<=10, album: str<=300,
              cover_url: https URL on allow-listed image host | null, duration_ms: int,
              spotify_url: https://open.spotify.com/track/{id} }
ProviderError { kind: "unauthorized" | "forbidden" | "not_allowlisted" | "invalid_grant"
                | "rate_limited" | "quota_exceeded" | "no_active_device" | "premium_required"
                | "not_found" | "bad_request" | "upstream_5xx" | "network",
                retry_after_s: int | null, raw_status: int }
```

Rules:

- Implementations never return raw Spotify JSON. They map to the DTOs above and drop all other fields.
- Implementations never log tokens, `Authorization` headers, or response bodies.
- `FakeMusicProvider`: deterministic, scripted per test (sequence of NowPlaying/Nothing/errors). Default for unit tests and local dev without Spotify.
- `ReplayMusicProvider`: replays recorded, scrubbed fixtures from the spike (status, headers we care about, body mapped to DTO). Used for contract tests and "demo mode".
- `SpotifyProvider`: the only class that knows Spotify URLs.

### 5. Rollout stages

| Stage | Who | Spotify limits | Unlock condition |
|---|---|---|---|
| R0 Spike | Owner only | Dev Mode | Spike items 3 and 4 pass |
| R1 Closed alpha | ≤ 5 hosts (incl. owner), invited listeners (cap 100 accounts) | Dev Mode, shared quota | M3 exit criteria in [07](./07-ROADMAP.md) |
| R2 Waitlist | Same 5 hosts, listener waitlist opened in batches | Dev Mode | Quota headroom ≥ 50% at R1 peak; no QUOTA_EXCEEDED for 2 weeks |
| R3 More hosts | Needs Extended Quota (organization, 250k MAU) or a different provider | n/a | Not reachable for an individual today. Would require a registered company and an existing audience, or a non-Spotify `MusicProvider` (not researched, UNVERIFIED) |

Listeners do not consume allowlist slots. Their cost is search and suggestion lookups, which are cached and rate-limited per user ([04](./04-API_AND_EVENTS.md)).

### 6. Policy and attribution checklist

From [policy] and [design] (read 2026-11-09). Each item maps to a spec in [07](./07-ROADMAP.md).

- [ ] Every place we show track title, artist, album, or cover shows the Spotify logo/attribution and links back to the track on Spotify (S08).
- [ ] Cover art shown unaltered (no blur-as-background, no crop that hides content, no animation). Background blur of artwork is **not allowed** under this reading; use solid zinc surfaces (S08). UNVERIFIED nuance: the Design Guidelines page has more detail than we read; owner to review.
- [ ] Metadata is never offered standalone (no public track-metadata API, no export of other users' Spotify data) (S07, S10).
- [ ] App name does not begin with "Spot" and does not imply Spotify endorsement. "imbooored" passes (S08 copy review).
- [ ] Privacy policy describes Spotify data use; users can disconnect Spotify any time, and on disconnect we delete that user's Spotify data (S03, S10).
- [ ] No ML training on, or ingestion of, Spotify content into any ML/AI model, including future AI features (all specs).
- [ ] No analysis of Spotify content for listenership metrics or user profiling. Trending tags are computed from our own room tags, not from Spotify data (S06).
- [ ] No game mechanics. Vibe Points are a private tally without ranking until OQ-3 is decided (S07).
- [ ] No ads, sponsorships, payments while we display Spotify content (policy IV).
- [ ] Not targeted at children; minimum age gate (S02).
- [ ] One Client ID ("Security Code") per SDA. This conflicts with security rule 23. See ADR-010 and OQ-2.
- [ ] Not mimicking a core Spotify experience: we never control playback beyond queue add, never show the Jam's full queue, and always send people to Spotify to listen (S05, S08).
- [ ] Not "non-interactive webcasting": imbooored streams no audio. Listeners listen inside Spotify via the Jam (S08 copy).

### 7. Kill criteria

Stop and rethink the product (not just the code) if any of these hold:

- K1. Spike item 3 fails: currently-playing with the host token does not reflect the Jam.
- K2. Spike item 4 fails: queue push with the host token does not reach the Jam queue, and no documented alternative exists.
- K3. Spotify restricts Player endpoints for Dev Mode (C12) or revokes the app for policy reasons.
- K4. After 4 weeks of R1, fewer than 2 hosts open rooms weekly.
- K5. Normal R1 load hits `QUOTA_EXCEEDED` more than once per week after budget tuning.

## Assumptions

- Hosts start the Jam in the Spotify app themselves. imbooored never starts, joins, or ends a Jam.
- Polling the host's currently-playing is the only realtime signal (Spotify has no webhooks). Confirmed in the reference chat, not by Spotify docs we read: UNVERIFIED.
- Image hosts for cover art are Spotify CDN domains; exact allow-list comes from spike fixtures (UNVERIFIED).

## Open questions

- Does a Jam invite link expire or require the host to approve joiners? (spike, UNVERIFIED)
- Does the Developer Policy accept separate Client IDs for dev/staging/prod of the same app? (OQ-2)
- Do Vibe Points count as a "game" under policy III? (OQ-3)

## Verified sources

All accessed 2026-11-09. Reading a doc does not upgrade a claim from UNVERIFIED (see labeling rule).

- [quota-modes]: https://developer.spotify.com/documentation/web-api/concepts/quota-modes
- [feb-2026-guide]: https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide
- [changelog-feb]: https://developer.spotify.com/documentation/web-api/references/changes/february-2026
- [changelog-jul]: https://developer.spotify.com/documentation/web-api/references/changes/july-2026
- [quota-blog-jul]: https://developer.spotify.com/blog/2026-07-23-web-api-quota-updates
- [blog-feb]: https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security
- [rate-limits]: https://developer.spotify.com/documentation/web-api/guides/rate-limits/
- [refresh]: https://developer.spotify.com/documentation/web-api/tutorials/refreshing-tokens
- [refresh-expiry-blog]: https://developer.spotify.com/blog/2026-06-18-refresh-token-expiration (search snippet only)
- [add-to-queue]: https://developer.spotify.com/documentation/web-api/reference/add-to-queue
- [policy]: https://developer.spotify.com/policy (effective 2025-05-15)
- [terms]: https://developer.spotify.com/terms (not read in full; ML clause confirmed via policy III)
- [design]: https://developer.spotify.com/design/ (search snippet only, not read in full)
- C13 basis: https://github.com/spotify/web-api/issues/600 (community, not official)
