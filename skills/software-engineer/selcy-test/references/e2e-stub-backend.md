# E2E stub-backend leaks — decision guide

Both leaks share one signature: **a test passes when its file runs alone, fails in the full suite**, and the code under test is not the cause. Check both before believing a test is flaky.

## Which leak do I have?

| Signal | Build env leak | Service worker leak |
|---|---|---|
| The app calls a real backend URL, not the stub domain | yes | |
| The stubbed route handler never fires (a `page.on('request')` log sees nothing) | yes (wrong host) | yes (SW bypassed the route) |
| Error reads "server cannot be reached" / DNS failure on the fictitious domain | | yes |
| Failure depends on which tests ran earlier (SW activation timing) | sometimes | yes |
| Failure persists even with a clean build | | yes |

## The build env leak

Vite bakes `.env.local` into the production bundle at build time. `.env.local` is where the developer's real backend URL lives. Once the real URL is in `dist`, the app calls it instead of the stub domain.

**Fix:** the script that builds for E2E must not inherit `.env.local` — pass the env vars explicitly to the build command (e.g. `VITE_SUPABASE_URL='' pnpm build`) or build from a clean env. Runtime overrides cannot help: the app's real backend URL is already baked in.

Confirm the leak: `grep -rl 'real-backend-host' dist/` should find nothing when the build is clean.

## The service worker leak

A PWA service worker intercepts page fetches. **Requests handled by the SW are not interceptable by `page.route`** — Playwright routes sit at the page's network layer and the SW's outgoing request bypasses them. Any spec that stubs a backend through `page.route` leaks the stub request to the real network whenever the SW is active in that context.

**Fix:** `test.use({ serviceWorkers: 'block' })` in every spec that stubs a backend or CDN via `page.route`. PWA behavior itself is tested in the specs that exercise offline caching; blocking the SW there would defeat them.

This is not disabling a feature to make a test pass — the SW precache is correct production behavior; the *test* opts out because it is not testing the PWA.

## The diagnostic path (when the cause is not yet known)

When the failure only appears in the full suite, do not bisect by deleting tests. Order of operations that finds the cause fastest:

1. **Run the failing test's file alone.** If it passes, the code under test is fine — the failure is interaction. If it fails alone too, the leak is baked into the build (see the build env section above).

2. **Run the file with a `page.route('**')` catch-all that logs request URLs.** If the stubbed request never appears in the log, the request never reached `page.route` — points at the SW leak. If it appears but with the wrong host, points at the build env leak.

3. **Grep the built bundle for the real backend host.** Non-empty → the build env leak. Clean → the SW leak.

4. Only now bisect by file pairs. The interaction is timing-dependent (SW activation is async), so pair results may vary — do not treat an inconsistent pair as a flaky test; the all-or-nothing signature in step 1 is the reliable signal.
