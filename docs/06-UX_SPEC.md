# 06 · UX Spec

Status: DRAFT · Written 2026-11-09 · UI copy: Indonesian · Code/docs: English

## Purpose

Describe every screen, every state, navigation (including keyboard and screen readers), progress-bar behavior, design tokens, and the Indonesian copy, so S08 and earlier specs build the same thing.

## Content

### 1. Design read and dials

- Product feel: a dark listening room at night. Cover art is the only large color on screen; the UI stays quiet around it.
- Dials: **ENERGY 2 / RHYTHM 2 / MOTION 2** (calm, a little variation between feed and room, motion only where it carries meaning: room swipe and progress bar).
- Dark-only for MVP. Reason: the owner's brief sets a dark zinc/emerald identity, and cover art reads best on a near-black surface. Light theme is open question UX-Q1, not deferred silently.
- Identity motif: the three o's in "imbooored". Used once as the loading indicator (three dots that fill in sequence) and as the empty-state mark. Nowhere else.
- No glow, no glassmorphism, no gradients, no blurred cover-art backgrounds (Spotify artwork must be shown unaltered, [01](./01-SPOTIFY_CONSTRAINTS.md) §6).

### 2. Design tokens

| Token | Value | Use | Contrast on bg |
|---|---|---|---|
| `bg` | zinc-950 `#09090b` | page | n/a |
| `surface` | zinc-900 `#18181b` | cards, sheets | n/a |
| `surface-raised` | zinc-800 `#27272a` | hover, modal | n/a |
| `border-subtle` | zinc-800 | decorative dividers only | n/a |
| `border-input` | zinc-500 `#71717a` | inputs, focusable outlines | 4.12:1 (≥ 3:1 non-text) |
| `text` | zinc-100 `#f4f4f5` | body, titles | 18.1:1 |
| `text-muted` | zinc-400 `#a1a1aa` | secondary text | 7.76:1 on bg, 6.91:1 on surface |
| `accent` | emerald-500 `#10b981` | primary action, progress fill, live dot | 7.84:1 |
| `accent-text` | emerald-400 `#34d399` | links, active tag | 10.35:1 |
| `on-accent` | zinc-950 | text on accent buttons | 7.84:1 |
| `danger` | red-400 `#f87171` | errors, close room | 7.19:1 |
| `warning` | amber-300 `#fcd34d` | stale/tertunda badge | 13.8:1 |
| Focus ring | 2 px emerald-400 + 2 px offset bg | every focusable element | 10.35:1 |

zinc-500 is **not** allowed for text (4.12:1 fails AA for body text). Ratios computed 2026-11-09 with the WCAG 2.x formula.

Type: Inter (self-hosted via `next/font`), sizes 13/15/17/22/28 px, weights 400/500/600. Tabular numbers for times and vote counts. No monospace, no uppercase-tracked labels.

Radius: 6 px controls, 10 px cards and sheets, cover art 4 px (Spotify guideline mentions small radii, UNVERIFIED exact values). Spacing scale 4/8/12/16/24/32/48.

Breakpoints: `sm` 0–639 (single column, full-screen room), `md` 640–1023 (feed 2 columns, room with side sheet), `lg` ≥ 1024 (feed 3 columns max width 1200 px, room with fixed queue column). Tap targets ≥ 44×44 px. No horizontal overflow at 320 px width.

### 3. Screens and flows

```mermaid
flowchart TD
  Landing["/ (signed out)"] -->|Masuk| Clerk[Clerk sign-in]
  Clerk --> Age["Konfirmasi umur 18+"] --> Feed["/feed"]
  Feed -->|tap card| Room["/r/{room_id}"]
  Room -->|swipe / ↑↓| Room
  Room -->|Usulkan lagu| Suggest[Suggest sheet]
  Feed -->|Jadi host (role host)| HostConsole["/host"]
  HostConsole -->|Hubungkan Spotify| SpotifyAuth[Spotify authorize] --> Callback["/spotify/callback"] --> HostConsole
  Callback -->|403| AlphaFull["State: alpha penuh"]
  HostConsole -->|Buka room| Room
  Feed --> Settings["/akun (export, hapus akun, putuskan Spotify)"]
```

#### 3.1 Landing (signed out)

One screen: the wordmark, one line about what it is, one sign-in button. No feature grid, no fake stats.

- Headline: "Bosan sama playlist yang itu-itu aja?"
- Body: "Masuk ke Jam Spotify orang lain, lihat lagu yang lagi diputar, dan usulkan lagu berikutnya."
- Button: "Masuk"
- Footnote: "imbooored masih alpha tertutup. Data lagu dari Spotify."

#### 3.2 Feed (`/feed`)

- Top: wordmark, tag filter row (trending tags as toggle chips, plus a "Cari tag" input that accepts `#postpunk` or `postpunk`), account menu.
- Cards: cover (64 px sm / 96 px md+), title, artist, host name, tags, listener count ("12 pendengar"), live dot. Each card has the Spotify attribution mark and links the track to Spotify.
- Order: newest live rooms first. Cursor pagination with "Muat lagi" button (no infinite scroll, keeps focus order sane).

| State | Content |
|---|---|
| Loading | three-o loader + skeleton cards with reserved height (no layout shift) |
| Empty (no rooms) | "Belum ada room yang live. Coba lagi sebentar lagi." |
| Empty (tag filter) | "Belum ada room dengan #{tag}." + button "Hapus filter" |
| Error | "Feed gagal dimuat." + "Coba lagi" |
| Rate limited | "Pelan-pelan dulu. Coba lagi dalam {n} detik." |
| Offline | banner "Kamu sedang offline." Cards stay visible, actions disabled |

#### 3.3 Room (`/r/{room_id}`)

Layout `sm`: full-screen card. Cover (max 320 px, square), title (17/600), artist (15/400 muted), progress bar with elapsed/total, tags, host name, listener count, "Buka di Spotify" (track link), "Gabung Jam" (Jam link, opens Spotify in a new tab with `rel="noopener noreferrer"`). Bottom sheet: suggestions list with vote buttons and "Usulkan lagu".

Layout `md+`: cover and now-playing left, suggestions column right.

| State | Behavior and copy |
|---|---|
| Loading | reserved cover square + three-o loader |
| Playing | progress moves locally (§5) |
| Paused | bar frozen, label "Dijeda" |
| Nothing playing (204/ad/local) | cover placeholder, "Host belum memutar lagu." |
| Stale (no update > 30 s or `room:stale`) | amber badge "Data lagu tertunda" with reason tooltip: rate limit "Spotify membatasi permintaan", quota "Kuota Spotify habis sementara", down "Spotify sedang bermasalah" |
| Reconnecting | top banner "Menyambung ulang…" with attempt count; actions disabled; on success re-join and apply snapshot |
| Room closed | full overlay "Room ini sudah ditutup." + reason line + "Room berikutnya" and "Kembali ke feed" |
| Not found | "Room tidak ditemukan." + "Kembali ke feed" |
| Suggestions empty | "Belum ada usulan. Jadi yang pertama." |

Close reasons in copy: `host_closed` "Host mengakhiri sesi.", `host_gone` "Host terputus terlalu lama.", `empty_timeout` "Room kosong terlalu lama.", `idle_timeout` "Tidak ada musik diputar terlalu lama.", `token_revoked` "Koneksi Spotify host terputus.", `admin_force_closed` "Room ditutup admin.", `account_deleted` / `reconciled` "Room sudah tidak aktif."

Suggestion row: small cover, title, artist, suggester name, vote count "3/5", vote button "Dukung" (pressed state "Didukung", `aria-pressed`). Status chips: pending (none), approved "Menunggu antrean", queued "Masuk antrean", failed "Gagal masuk antrean" (+ reason: no device "Spotify host tidak aktif"), rejected "Ditolak host".

#### 3.4 Suggest sheet

- Input label (visible): "Cari lagu di Spotify". Placeholder: "Judul atau artis". Debounce 400 ms, min 2 chars, max 100.
- Results ≤ 10 rows: cover, title, artist, "Usulkan" button. Each row carries Spotify attribution and link.
- States: idle hint "Ketik judul lagu atau nama artis.", loading three-o, empty "Lagu tidak ditemukan.", rate limited "Terlalu banyak pencarian. Coba lagi dalam {n} detik.", quota "Pencarian sedang tidak tersedia.", already suggested "Lagu ini sudah diusulkan. Dukungan kamu ditambahkan."
- Success: sheet closes, toast "Usulan terkirim." (toast has `role="status"`).
- Escape closes, focus returns to "Usulkan lagu".

#### 3.5 Host console (`/host`)

- Not connected: "Hubungkan akun Spotify kamu supaya pendengar bisa melihat lagu yang diputar." Button "Hubungkan Spotify". Note: "Kami hanya meminta izin membaca lagu yang diputar dan menambah lagu ke antrean."
- Connected, no room: form with Jam link (label "Tautan Jam Spotify", help "Buka Jam di aplikasi Spotify, salin tautan undangan."), tags (label "Tag", help "1–5 tag, huruf kecil, angka, atau _"), vote threshold (label "Dukungan yang dibutuhkan", stepper 2–10, default 3). Button "Buka room".
- Live: room preview, threshold stepper, suggestion list with "Tolak", danger button "Tutup room" (confirm dialog "Tutup room sekarang? Pendengar akan keluar." / "Tutup room" / "Batal").
- Needs reauth: banner "Koneksi Spotify kamu perlu diperbarui." + "Hubungkan ulang". Shown 30 days before the 6-month expiry too: "Koneksi Spotify berakhir pada {tanggal}."
- No active device during push: banner "Buka Spotify di perangkatmu supaya usulan bisa masuk antrean."
- Validation copy: invalid link "Tautan Jam tidak dikenali. Pakai tautan undangan dari Spotify.", invalid tag "Tag hanya boleh huruf kecil, angka, dan _ (2–30 karakter).", already live "Kamu masih punya room yang live." + "Buka room itu".

#### 3.6 Onboarding / alpha states

- Listener trying host features: "Fitur host masih terbatas untuk alpha tertutup."
- Spotify callback 403 (not on allowlist): "Akun Spotify ini belum terdaftar di alpha imbooored. Hubungi admin untuk didaftarkan." Button "Kembali". Audit `token.connect_denied`.
- Spotify denied consent: "Kamu membatalkan koneksi Spotify." Button "Coba lagi".
- Host slots full (admin view): "Slot host penuh (5/5)."

#### 3.7 Account (`/akun`)

Display name edit, Vibe Points balance and recent entries (private), "Putuskan Spotify" (hosts), "Unduh data saya", "Hapus akun" (requires typing HAPUS). Disconnect copy also tells the user how to remove imbooored from Spotify's account apps page because we cannot revoke the grant for them ([01](./01-SPOTIFY_CONSTRAINTS.md) C13).

### 4. Swipe navigation between rooms

- Order: the feed list the user came from (same tag filter), cached client-side; next page fetched when 2 rooms remain.
- Touch: vertical swipe on the now-playing area (not on the suggestion sheet). Threshold 25% viewport height or velocity > 0.5 px/ms. Below threshold the card snaps back.
- Keyboard: `ArrowDown` / `J` next room, `ArrowUp` / `K` previous, only when focus is not inside an input or the sheet. Visible buttons "Room sebelumnya" / "Room berikutnya" always exist (switch and screen-reader users).
- Screen reader: on room change, focus moves to the room heading (`h1`: "{title} oleh {artist}, room {host}") and a polite live region announces "Room {n} dari {total}".
- `prefers-reduced-motion`: no slide animation, instant swap.
- Each swipe leaves the old Socket.IO room and joins the new one (`room:join` handles the switch).
- URL updates with `router.replace` so back goes to the feed, not through every room.

### 5. Progress-bar interpolation

Inputs from the server: `progress_ms`, `duration_ms`, `is_playing`, `observed_at_ms` (worker clock at poll time), `server_now_ms` (in snapshot).

1. Clock offset: `offset = server_now_ms - Date.now()` measured at snapshot receipt; re-measured on every reconnect.
2. Position: `pos = progress_ms + (is_playing ? (Date.now() + offset - observed_at_ms) : 0)`, clamped to `[0, duration_ms]`.
3. Render with `requestAnimationFrame`, updating the bar width and the elapsed label once per second (labels change at whole seconds).
4. At `pos >= duration_ms`: hold at full, label "Menunggu lagu berikutnya", no wrap-around.
5. On `track:changed` / `playback:state`: compute new `pos`. If same track and `|new - shown| < 1500 ms`, ease over 300 ms; otherwise snap.
6. Tab hidden (`visibilitychange`): stop rAF; on visible recompute from inputs.
7. Stale after 30 s without updates while playing: keep moving, show the amber badge.
8. Accessibility: the bar is `role="progressbar"` with `aria-valuemin=0`, `aria-valuemax={duration_s}`, `aria-valuenow={pos_s}`, `aria-valuetext="1:20 dari 3:45"`, updated at most every 5 s to avoid chatty screen readers.

### 6. Attribution

Every track title/artist/cover shows the Spotify logo mark per Branding Guidelines and links to `spotify_url`. Feed cards, room, suggestion rows, search results. Footer: "Data lagu dan sampul album disediakan oleh Spotify." Exact logo asset and size come from the Spotify Design Guidelines (not read in full: UNVERIFIED).

### 7. Accessibility checklist (S08)

Keyboard path through every screen (Tab, Enter, Space, Escape), visible focus ring, labels on every field, `alt` on covers ("Sampul {album}"), live regions for votes and status changes (polite, throttled), color is never the only signal (status chips have text), contrast per §2, `lang="id"` on `<html>`.

## Assumptions

- Hosts can copy a Jam invite link from the Spotify app (UNVERIFIED, spike).
- Listeners joining a Jam happens entirely in Spotify; imbooored only links out.

## Open questions

- UX-Q1: Light theme for MVP or later?
- UX-Q2: Vertical swipe can clash with page scroll on small screens. Alternative is horizontal swipe, which clashes with iOS back gesture. Prototype both in S08?
- UX-Q3: Show suggester names publicly? (see [04](./04-API_AND_EVENTS.md) open questions)

## Verified sources

| Fact | Source | Accessed |
|---|---|---|
| Metadata/cover must link back to Spotify and carry attribution | https://developer.spotify.com/policy §II | 2026-11-09 |
| Design guideline details (logo sizes, artwork radius) | https://developer.spotify.com/design/ (UNVERIFIED), read in full during S08 | n/a |
| WCAG contrast thresholds 4.5:1 text, 3:1 non-text | WCAG 2.2 (not re-read this session) | n/a |
