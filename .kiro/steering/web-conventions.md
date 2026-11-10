---
inclusion: fileMatch
fileMatchPattern: 'apps/web/**'
---

# apps/web conventions

- Server Components by default; `"use client"` only for interactive parts (socket, progress bar, swipe, forms).
- Call the API only through typed clients built on `packages/contracts`. Attach a fresh Clerk token per request (`getToken()`).
- Never call Spotify from the browser. Never store tokens in `localStorage`/`sessionStorage`.
- Render all user and Spotify text as React text. `dangerouslySetInnerHTML` is forbidden (lint rule).
- No `console.*`. Report errors through the app's error boundary and a typed logger that drops PII.
- Every screen implements loading, empty, error, offline/reconnect, and closed states from `docs/06-UX_SPEC.md`.
- Every Spotify metadata/artwork display includes attribution and a link to `spotify_url`. Never blur, tint, or animate cover art.
- Accessibility: native elements, visible labels, focus ring token, keyboard paths (Tab/Enter/Space/Escape, ↑/↓ for rooms), `aria-live` polite and throttled, `prefers-reduced-motion` respected.
- Styling: Tailwind with tokens from `docs/06-UX_SPEC.md` §2. No zinc-500 text, no glow/glass/gradients.
- Copy in Indonesian, taken from `docs/06-UX_SPEC.md`; new strings get added there first. No em dashes in UI copy.
- External links: `target="_blank" rel="noopener noreferrer"`. Redirect params accept relative paths only.
- Naming: components `PascalCase.tsx`, hooks `useThing.ts`, route folders kebab-case.
- Tests: vitest for hooks/logic (progress interpolation, reconnect), Playwright for flows with `FakeMusicProvider`.
