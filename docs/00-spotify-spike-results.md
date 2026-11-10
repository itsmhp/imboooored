# 00 · Spotify Spike Results

Status: PARTIAL RUN 2026-11-10. Host-with-participant test DEFERRED by the owner (no participant available). Item 6 not tested; item 5 needs a re-run. · Owner fills this in · Evidence = scrubbed JSON from `%USERPROFILE%\.imbooored\spike\evidence` (outside the repo)

While a row says NOT RUN, the related claim in [01-SPOTIFY_CONSTRAINTS.md](./01-SPOTIFY_CONSTRAINTS.md) stays UNVERIFIED. Change a claim only after its row has a date and an evidence file name.

## Setup

| Item | Value |
|---|---|
| Date (UTC) | |
| App name / mode | imbooored / Development Mode |
| Account A (host, Premium, allowlisted) | yes / no, Premium confirmed: |
| Account B (not allowlisted) | |
| Device used for playback | type only (Computer / Phone), no ids |
| Jam started by | A friend's account (the Jam host; never authorized imbooored, not on the allowlist). Account A joined as a **participant** with control and queue rights. The host's own token was NOT tested. |
| Script | `spike.ps1`, PowerShell 7.6.9 |

## Items

Result values: PASS, FAIL, PARTIAL, NOT RUN. Keep "Observed" to facts you saw, not guesses.

| # | Check | Command | Date (UTC) | Evidence file | Result | Observed |
|---|---|---|---|---|---|---|
| 1 | App created, allowlist works | dashboard | 2026-11-10 | n/a | PASS | App `imbooored` created in Development Mode; owner account in User Management (1/5 at that time). Whether account B was also listed: see item 6. |
| 2 | OAuth Authorization Code + PKCE, 3 scopes, token returned | `spike.ps1 auth -Account A` | 2026-11-10 | `20261110-034007_A_auth-token.json` | PASS | Granted exactly the 3 requested scopes. `token_type` Bearer, `expires_in` 3600, refresh token returned. Callback `state` matched. Code exchange used PKCE with no client secret. |
| 3a | `currently-playing` while a Jam is active (host plays) | `spike.ps1 now` | 2026-11-10 | `20261110-034039_A_now.json` | PARTIAL | HTTP 200. `is_playing` true, `progress_ms` present, `item` present (type track, `is_local` false, `id` present, `duration_ms` present). `context` is null. `actions.disallows.resuming` true. Owner reports a Jam was running, hosted by a friend, with A as a participant. So this shows a **participant's** token returns the playing track; it does NOT show that the **host's** token does, which is what the product design uses. Re-test with A as host (see next steps). |
| 3b | Same, Jam paused | `spike.ps1 now` | | | NOT RUN | |
| 3c | Same, ad playing (needs Free account host or ad tier) | `spike.ps1 now` | | | NOT RUN | `item` null? `currently_playing_type`? |
| 3d | Same, local file | `spike.ps1 now` | | | NOT RUN | `is_local`, `item.id`? |
| 3e | Same, no active device / nothing playing | `spike.ps1 now` | | | NOT RUN | expect 204? |
| 3f | `GET /me/player` shows Jam context? | `spike.ps1 player` | 2026-11-10 | `20261110-034048_A_player.json` | PARTIAL | HTTP 200, `context` null, so no Jam marker is visible in the playback state (even if a Jam was active; see 3a). Device fields: id, is_active, is_private_session, is_restricted, name, supports_volume, type, volume_percent. Device type Computer, active. |
| 3g | Host leaves / ends the Jam: what does the API return? | `spike.ps1 now` | | | NOT RUN | |
| 4a | `POST /me/player/queue` lands in the Jam queue (check in the Spotify app) | `spike.ps1 queue -TrackId <id>` | 2026-11-10 | `20261110-034551_A_queue.json` | PARTIAL | HTTP 200 (not 204). No `Content-Type`; body is a short opaque text string of 27 characters (meaning UNVERIFIED; the first run stored it as byte values, fixed in the script). Pushed with a participant's token in a friend's Jam. Owner reports the track was added in Spotify. Not yet confirmed: that it showed in the Jam queue for all participants, and whether it also works when the token owner is the host. Repeat with A as host. |
| 4b | Queue push with no active device | `spike.ps1 queue ...` | | | NOT RUN | status, `reason` |
| 4c | Queue push by non-Premium host | `spike.ps1 queue ...` | | | NOT RUN | status, `reason` |
| 5 | Client-credentials search works in Dev Mode; limit 10 / 11 / default | `spike.ps1 search` | 2026-11-10 | `20261110-034651_A_search-cc-token.json`, `20261110-034652_A_search-limit10.json` | PARTIAL | Client-credentials token: HTTP 200. `limit=10`: HTTP 200, exactly 10 items. Cover images served from host `i.scdn.co`. Track item fields: album, artists, disc_number, duration_ms, explicit, external_ids, external_urls, href, id, is_local, is_playable, name, track_number, type, uri. The `limit=11` and default-limit calls and the `/tracks/{id}` lookup did not run (script bug, fixed). Re-run `spike.ps1 search -TrackId <id>`. |
| 5b | `GET /tracks/{id}` with client credentials | `spike.ps1 search -TrackId <id>` | | | NOT RUN | |
| 6 | Account B (not allowlisted): login ok, API call 403, error shape | `spike.ps1 auth -Account B`, then `whoami -Account B`, `now -Account B` | 2026-11-10 | `20261110-034837_B_auth-token.json`, `20261110-034850_B_whoami.json`, `20261110-034858_B_now.json` | NOT RUN | The run did not test the 403 case. Account B is a newly created Free account, different from A (compared by hashing `account_id`), and the owner's dashboard screenshot shows B in User Management (2/5 added). So `GET /me` 200 and `currently-playing` 204 are the expected results for an allowlisted account. Observed with an allowlisted Free account: login and token exchange work, `/me` 200, `currently-playing` 204 (nothing playing). To test the 403: remove B from the allowlist (or use a third account), re-run `auth -Account B`, `whoami -Account B`, `now -Account B`. |
| 7 | Refresh grant: new refresh token returned? | `spike.ps1 refresh` | 2026-11-10 | `20261110-034659_A_refresh.json` | PASS | HTTP 200. `returned_new_refresh_token` false, so keep the stored one. Scope unchanged, `expires_in` 3600. |
| 8 | Rate-limit headers / `Retry-After` seen | any, `header_names` in evidence | 2026-11-10 | `20261110-034039_A_now.json` | PARTIAL | No `Retry-After` and no rate-limit headers on 200 responses (no 429 was triggered on purpose). Header names seen: Cache-Control, x-robots-tag, Server-Timing, Strict-Transport-Security, X-Content-Type-Options, Alt-Svc, Date, Server, Via, Transfer-Encoding, Content-Type. `Retry-After` format on a real 429 stays UNVERIFIED. |
| 9 | Re-read: Quota modes, Feb 2026 migration guide, Developer Terms, Design Guidelines | manual | | n/a | NOT RUN | notes on attribution/link-back |

## Go / no-go

| Criterion | Result |
|---|---|
| 3a passes (Jam track readable with host token) | DEFERRED. Only proven with a participant token. |
| 4a passes (queue push lands in Jam queue) | DEFERRED. Only proven with a participant token. |
| Kill criteria K1 or K2 triggered? (see [01](./01-SPOTIFY_CONSTRAINTS.md) §7) | Not triggered by any result so far, but not cleared for the host case. |

Decision (owner), 2026-11-10: DEFER the host-with-participant test because no second participant is available. Proceed with S01 and S02, which use no Spotify behavior. S03 and every later Spotify-facing spec stay blocked until 3a and 4a pass with A as host and at least one participant in the Jam. Accepted risk: if the host test fails later, S01 and S02 remain useful, but the product concept may change (see ADR-021).

## Tooling note (2026-11-10)

- The Spotify MCP server (`marcelmarais/spotify-mcp-server`, commit `7d7e400`, local patch: 3 scopes) is installed outside the repo after the owner accepted the SkillSpector HIGH findings. It summarizes responses, so it does not record HTTP status or headers. Use `spike.ps1` for evidence; treat MCP reads as observations only.
- Observation via MCP with account A's token: `getNowPlaying` returned the playing track and an active Computer device. The call did not show whether a Jam was active at that moment, so it does not change row 3a.

## Facts to carry into the docs after the spike

Fill only from evidence above.

- Jam invite link format (for the allow-list regex in [05](./05-SECURITY_THREAT_MODEL.md) §4): the invite shared by the owner was a `https://spotify.link/<11 alphanumeric characters>` short link. It was not fetched, so the URL it resolves to is unknown. The draft pattern accepts this shape. The `open.spotify.com/socialsession/...` form is still UNVERIFIED.
- Image CDN hostnames seen in `cover_url`:
- Error body shapes (401, 403, 204 cases, no-device, premium-required):
- Headers present on responses:
- Anything that contradicts the docs (list doc, section, and what changed):

## Cleanup checklist

- [ ] `spike.ps1 clean` run for accounts A and B
- [ ] imbooored removed from each tested account's Spotify "Apps" page
- [ ] Evidence reviewed for personal data before any file is copied into the repo as a fixture
- [ ] Client secret reset in the dashboard if it was ever exposed
