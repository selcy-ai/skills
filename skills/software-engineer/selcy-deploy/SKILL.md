---
name: selcy-deploy
allowed-tools: Bash, Read, Grep, Glob, Write, Agent
description: "Run /selcy-deploy when deploying or handing off a project: Cloudflare Pages/Workers, Supabase Edge Functions, env build vs CI secrets, GPS/HTTPS and browser-context requirements. Captures the operational knowledge that cost real hours to learn, so the next deploy does not rediscover it. Deploy playbook + preflight checks."
---

## What this skill does

The deploy half of the SELCy loop. It runs when a project is ready to ship, stage, or hand off — after the last feature's `Check When Done` is green and before (or alongside) any actual deployment.

It exists because operational knowledge in this domain is expensive and transferable: each fact below cost hours of debugging on a real project (BMKG Smart Multi-Hazard Hub), and each one applies to any future project on the same stack. A deploy that reads this skill first does not rediscover them.

Scope: **read the project's stack, run preflight checks, and report what will break in production before it breaks.** It does not replace the deploy command; it prepares the engineer (and the orchestrator) for the deploy and catches the common failure classes.

## When to run

- Staging or production deploy of any project.
- Handoff to a client: the runbook this skill produces is the handoff document.
- After a domain change (custom domain, CORS origin, redirect) — the two most common post-deploy breakages live here.
- When `context/architecture-context.md` names a deploy target (Cloudflare Pages, Workers, Supabase) but no deploy has ever been run.

## The knowledge base

These are the facts, each with the failure it prevents. None of them is general documentation look-up; each one was paid for in debugging hours.

### Cloudflare Pages — env build vs CI secrets

`.env.local` and friends are **build-time** inputs for a Vite app: Vite bakes `VITE_*` vars into the production bundle at build time. On Cloudflare Pages, the build runs in CI, where `.env.local` does not exist — so you must configure the vars in the Pages project (dashboard or `wrangler pages secret put`), or pass them explicitly to the local build command when you need a preview build.

The failure: you build locally with `.env.local`, deploy, and the app silently points at the wrong (or empty) backend because the CI build had different vars baked in. **Rule: whatever env the deployed bundle runs with must be decided explicitly at build time — never inherited from the developer's machine.** The same rule makes test builds deterministic (see `/selcy-test`'s build-env-leak section; this is the production side of that same fact).

### Cloudflare Workers — custom domains

A custom domain on a Worker must be registered through the Workers API (`workers/domains`), not by writing a CNAME to `*.workers.dev` manually. A manual CNAME to the workers.dev hostname produces **522** (origin unreachable) and looks like a DNS problem while being a registration problem.

### Supabase Edge Functions — CORS

`ALLOWED_ORIGINS` is a **secret**, and it must be set (and updated) every time the production domain changes. The failure mode: you add a domain, the function starts returning CORS errors on the new origin, and the cause is a secret that has not been re-set — not a code bug. Check the secret before debugging the code.

### Browser context — geolocation and secure contexts

`navigator.geolocation` is **blocked on plain HTTP unless the host is localhost**. An app that relies on GPS must either be served over HTTPS, or show a clear message explaining why the feature is unavailable in the current context. Do not let the feature silently do nothing: tell the user what is wrong and what would fix it.

### Local env discovery (Vite-specific)

Vite's `envDir` defaults to the app directory (e.g. `apps/web`), so a `.env.local` at the repo root is **not read**. When a build seems to be missing env vars that are definitely on disk, check `envDir` before assuming the vars are wrong.

### Next.js: static export means no Vercel, no `npm run dev`

The Vite rule above generalizes to Next.js, and the single decision is the render mode:

- **`output: 'export'` in `next.config.js`** → `next build` emits a static `out/` folder, deployable to Cloudflare Pages exactly like a Vite `dist/`. This covers dashboards and apps whose data flows through a client-side Supabase (or any API) client. No Vercel, no Node process, no PM2 — free on the Pages free tier.
- **SSR / Server Components** → a runtime is required. Options: `@cloudflare/next-on-pages` (runs on the edge worker; no full Node API, needs `nodejs_compat`), Vercel (one click, smoothest), or a VPS with `next build && next start` behind PM2 + nginx + HTTPS. `npm run dev` is **never** a production answer for either mode — it is the dev server (HMR, source maps, no hardening, dies when the process dies).

**Vercel's own deploy model, for contrast.** What Vercel does behind "one click" is the same thing the Pages commands do manually: it runs your build, takes the static output, and serves it from an edge network — plus, for SSR apps, it keeps a managed Node runtime alive to run server components. `npm run dev` on Vercel is only ever the local development command; production there is a built and served artifact, exactly like the Pages path above. Understanding this is what makes the Cloudflare alternative legible: for a static export the two host the same bytes, Cloudflare just does it free.

The frontend/backend split is the same pattern this whole skill serves: static frontend on Pages, backend on Supabase, the three rules below held.

### General pattern

Behind each fact above is one rule: **the environment the code runs in is part of the build, not part of the machine.** Env vars, domains, and origins are configuration that must be stated at build/deploy time. Anything left implicit will, on the next deploy or the next developer's machine, be wrong.

## Preflight checks

Follow this sequence. Report each check as pass/fail with what was actually observed.

1. **Read the deploy target.** `context/architecture-context.md` names it; if it does not, stop and say so — that is a bundle gap, not a deploy guess.
2. **Env table check.** Every `VITE_*` / env var the code reads must have a named value for the target environment (local, staging, production). Any var with no value for the target → fail, list it.
3. **Build with the target env, explicitly.** Build once with the exact env the deployed bundle will use — no `.env.local` inheritance. If the build output differs from a default local build, say so: that difference is the thing that would have broken in CI.
4. **CORS origin audit.** For every backend the app calls (Supabase Edge Functions, API routes), confirm the allowed origins include every domain that will serve the app, including the new one if a domain was added. Missing origin → fail.
5. **Domain registration.** If a custom domain is in play, confirm it was registered through the platform's API (Workers `workers/domains`, Pages custom domains), not a manual CNAME to a workers.dev hostname.
6. **Secure-context features.** List any feature the app uses that requires a secure context (geolocation, clipboard, service workers on some paths, Web Crypto in some browsers). Each must either be on HTTPS in production, or have a user-facing fallback message. Silent absence → fail.
7. **Secret inventory.** For Supabase: `ALLOWED_ORIGINS` and any function secrets. For Cloudflare: Pages vars, Worker bindings. List them; a missing secret is the most common post-deploy breakage.

Any fail → stop. Report the failure and the fix from the knowledge base above. Do not deploy around a failed preflight; the preflight exists because each check maps to a real, expensive failure.

## Artifact

Write the runbook to `docs/DEPLOY.md` (or append to the project's existing runbook): the stack, the env table per environment, the secrets inventory, the domain registration state, and the preflight results with dates. This is the handoff document — a client receiving the project should be able to re-run the deploy from it without asking you anything.

Cross-reference `context/architecture-context.md` when its env var table changes; `/selcy-sync` catches the specs that go stale when you edit it.

## What this skill never does

- Never deploys itself. It prepares and audits; the engineer (or CI) runs the deploy command.
- Never edits `context/` contracts directly; it reports gaps and lets `/selcy-sync` propagate.
- Never guesses a deploy target. If the bundle does not name one, that is an owed decision.
- Never treats a failed preflight as a warning. A fail is a stop.

## Portability

Any Agent Skills client on macOS, Linux, Windows. `git` and (optionally) the platform CLIs (`wrangler`, `supabase`) are the tools; shell snippets are POSIX reference. The knowledge base is stack-specific (Cloudflare + Supabase + Vite) — on a different stack, the preflight sequence still applies, and the knowledge base should be extended with that stack's paid-for facts as the team learns them.
