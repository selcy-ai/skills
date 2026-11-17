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
- When `context/architecture-context.md` names a deploy target (Dokploy, Cloudflare Pages, Workers, Supabase) but no deploy has ever been run.

## The knowledge base

These are the facts, each with the failure it prevents. None of them is general documentation look-up; each one was paid for in debugging hours.

### Cloudflare Pages — env build vs CI secrets

`.env.local` and friends are **build-time** inputs for a Vite app: Vite bakes `VITE_*` vars into the production bundle at build time. On Cloudflare Pages, the build runs in CI, where `.env.local` does not exist — so you must configure the vars in the Pages project (dashboard or `wrangler pages secret put`), or pass them explicitly to the local build command when you need a preview build.

The failure: you build locally with `.env.local`, deploy, and the app silently points at the wrong (or empty) backend because the CI build had different vars baked in. **Rule: whatever env the deployed bundle runs with must be decided explicitly at build time — never inherited from the developer's machine.** The same rule makes test builds deterministic (see `/selcy-test`'s build-env-leak section; this is the production side of that same fact).

### Dokploy + Traefik — the ingress is host-based, not port-based

An application deployed by Dokploy is reachable **only through Traefik host rules**. `ports: []` is the normal configuration, not a misconfiguration: the container publishes nothing to the host. A **404 on the Dokploy server's 80/443** means "no router registered for that Host" — almost always no domain attached — not "the app is down". Do not look for an `IP:port` to hand to the engineer; there is none until a domain routes to the container. `previewPort`/`previewHttps` configure preview deployments, a separate feature that is not a production access path.

**Domains are attached in the dashboard or through the MCP.** The Dokploy MCP does expose `domain.create`/`domain.update` (write) alongside read and validate endpoints (`domain.byApplicationId`, `domain.validateDomain`) — but prefer the dashboard for a first attach, since a domain created via MCP arrives with `certificateType: none` and no HTTPS router until you set `https: true` and `certificateType: letsencrypt` yourself. `validateDomain` is the useful one even when it fails: the error lists the server's accepted IPs — its public/WAN addresses, never the LAN address of the host. DNS must point at one of those, and the router must forward **80 + 443** to the Dokploy host: 80 for the ACME challenge, 443 for traffic. The LAN address answers only from inside the LAN. To exercise a router before DNS lands, hit the Traefik LAN address with a `Host:` header (`curl -k -H "Host: <domain>" https://<dokploy-lan-ip>/`): a 404 means no router, a 502 means the router is up and the backend is not reachable. A domain attached with **HTTPS off** registers its router on port 80 only — 443 keeps answering 404 until HTTPS is enabled in the domain settings, which is also what arms the Let's Encrypt cert resolver.

**A 502 is the mirror-image case: the router exists, the backend port is wrong.** Dokploy sets the container's `PORT` env at runtime to its own assignment, overriding whatever the Dockerfile declared — the app listens on that port regardless of `ENV PORT`/`EXPOSE`. The domain's **port field must match the runtime port, not the Dockerfile's**: a container that is healthy and serving still answers 502 through the domain when they differ. Find the runtime port from the Traefik API (`GET http://<dokploy-host>:8080/api/http/services` — the service URL shows `http://<appName>:<port>`) or on the host with `docker exec <container> env | grep PORT`, then fix the domain port in the dashboard. Minimal images ship no curl or wget — probe the backend from inside with `docker exec <container> node -e "fetch('http://localhost:<port>/').then(r => console.log(r.status))"`, not with a shell client that is not there.

**A 502 that survives a correct port means the DNS name answers to an orphaned VIP.** Dokploy runs the app as a Docker *service*: the name Traefik routes to resolves to a virtual IP, not to the task container. Deleting a container by hand (`docker rm -f`) removes the IPVS route while the service keeps the VIP — later deploys land on fresh container IPs that the dead VIP never forwards to, so a green `serverStatus: UP` and a healthy container coexist with a permanent 502. Recover by removing the service and letting Dokploy recreate it (`docker service rm <appName>` on the host, then redeploy), or switch the service to `--endpoint-mode dnsrr` so the name resolves straight to the container IP. `references/dokploy-deploy.md` carries the full diagnosis ladder, the host-access path, and the recovery commands.

**`applicationStatus: done` means the image built and the deployment record finished — not that the app answers requests.** A deploy call that returns `success: true` is not proof a build ran; read the application's `deployments` list and confirm a new entry with the expected commit instead of trusting the status field. `server.all` can legitimately return an empty list on a working single-node instance that runs on the main Dokploy node — treat `serverId: null` as "main node", not as an unconfigured server.

### Cloudflare Tunnel — hostname routing cannot be wired up over the API alone

A tunnel is the standard answer when the origin sits on a LAN with no public port forward, and creating the tunnel itself works over the API (`POST /accounts/{id}/cfd_tunnel` with `config_src: cloudflare`, then `tunnels_config_update` for the ingress rules — the last ingress rule must be a hostname-less catch-all such as `http_status:404`). But **the DNS record that routes a public hostname into the tunnel can only be created from the Zero Trust dashboard.** Over the API, every shape is closed: a proxied CNAME to `<tunnel-id>.cloudflareaccess.com` returns **1016** early on and **1014** once the record exists; an unproxied CNAME still 1014s because the record resolves to Cloudflare's own edge IPs; a proxied A record to a placeholder IP returns **522** because Cloudflare treats it as an ordinary unreachable origin and never consults the tunnel's ingress table. The dashboard creates the same record through an internal path that also stamps the routing metadata.

Working shape when the engineer must stay in the loop: **you configure the ingress, they click one button.** Write the ingress rule over the API (`tunnels_config_update`, hostname → `https://<dokploy-lan-ip>:443` with `noTLSVerify: true` and `httpHostHeader` set to the public hostname, which is what makes host-based Traefik routing match), verify the tunnel reaches `healthy` with 4 connections, and hand the engineer a single dashboard step: *Zero Trust → Networks → Tunnels → the tunnel → Public Hostnames → Add a public hostname* with the same hostname. Cloudflared is a single static binary with no install step (`curl -sL -o /usr/local/bin/cloudflared …/cloudflared-linux-amd64 && chmod +x`); run it with `tunnel run --token-file <path>` and it picks up remote config changes on its own, so a config written over the API applies without a restart.

 **A tunnel that reports `healthy` with live connections proves only the control plane.** It says nothing about whether a request for the hostname reaches the origin — the DNS record is the only thing that connects the two, and the tunnel can be green from the moment it starts while every request 404s or 522s at the edge. Verify end-to-end (the `Host:`-header probe against the Traefik LAN address, or the public URL once the record lands) before reporting the tunnel as the access path.

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

### PaaS (Dokploy/Coolify) — image pull needs registry auth, not git auth

A PaaS "Deploy from GitHub repo" button authenticates the **git clone** only (OAuth or GitHub App). The build container it spawns then runs `docker compose pull` with a fresh, unauthenticated Docker daemon — a completely separate credential. The failure looks like this in the deploy log:

```
Importing <owner>/<repo>:main ...            <- clone OK, git auth fine
Image ghcr.io/<owner>/<name>:latest Pulling
error from registry: unauthorized            <- daemon has no registry login
```

The gap is invisible until the first deploy because repo access works and CI
(`GITHUB_TOKEN` with `packages: write`) pushes the image fine. Then the PaaS
daemon asks GHCR for it anonymously and is rejected.

Rules:

- **A GHCR package pushed by CI inherits the repo's visibility** — private repo
  → private package, always. An anonymous pull of a private package is
  `unauthorized`; git OAuth does nothing for the Docker daemon.
- Before reporting a deploy failure as a code or config problem, read the log
  far enough to distinguish **clone/import** failure from **pull** failure.
  Import succeeded + pull `unauthorized` = registry visibility/login problem.
  Do not chase app config, env vars, or the Dockerfile at that point.
- Fixes, in order of preference: **switch the compose file to `build: .` so
  the PaaS builds from source** (the git clone already works — the PaaS has
  git auth — and the build needs no registry at all; the repo stays private,
  this is the proven default), or register the registry login on the PaaS
  server (Coolify MCP: `manage_registry` action `create`), or make the image
  public. Note on making it public: `GITHUB_TOKEN` **cannot** change package
  visibility — the API endpoint returns 404 from CI — so visibility is a
  manual dashboard step done by a human, not something a workflow can
  automate. A private GHCR image is only usable on hosts you can log in
  from.

### PaaS git auth — GitHub App is per-account, and the credential must match the URL scheme

A `docker-compose.yml` that references an image is what made the section above
fail; the same file referencing `build: .` is what makes the PaaS succeed. But
once git auth *is* the path, its own failure modes appear:

- **A PaaS can hold one GitHub App per GitHub account, and several apps can be
  installed side by side — so a missing install is a candidate, never a
  conclusion.** The failure reads `could not read Username for
  'https://github.com'`, which looks like a network error but means *no
  credential covers this repo through the path this deploy used* — and several
  shapes produce it: no app installed for that account, an app installed but
  the deploy attached the repo by URL instead of the dropdown, or a "Public
  GitHub" source pointed at a private repo. The message does not divide them.
  Before recommending an install, **prove the gap**: the Coolify MCP's
  `list_github_apps` + `list_github_repositories` lists every repo each
  installed app can already see. If the failing repo is on the list, the
  install is fine and a dashboard trip is the wrong fix.
- **Reproduce the credential path end to end before blaming the user's
  creation flow.** `create_application` (action `github_app`, with
  `github_app_uuid`, `git_repository`, `git_branch`, `build_pack`, and the
  project/server/environment UUIDs) creates the same app the dashboard creates
  from the dropdown, and one deploy settles the question: an `Importing …`
  line means the credential path works — whatever the user's failing app
  showed, the cause is elsewhere (source selection on the failing app, or the
  repo's own content — see the drift rule below). The repro costs three curl
  calls and never requires the user to justify how they clicked.
- **How the repo was attached decides which credential the PaaS uses.** A
  repo picked from the GitHub App's own repository dropdown clones through
  the app. A repo attached by typing its git URL into the repository field
  falls back to the PaaS's SSH credential — and against an `https://` URL
  that path is dead: the log shows `GIT_SSH_COMMAND="ssh -i …" git
  ls-remote 'https://github.com/<owner>/<repo>.git'` → `could not read
  Username`, because `GIT_SSH_COMMAND` never applies to https URLs and the
  non-interactive container cannot answer the prompt. The successful deploy
  log shows `Importing <repo>:<branch>` with **no `git ls-remote` line at
  all**. The fix is to attach the repo from the app's dropdown; when a deploy
  key is genuinely what you have, switch the URL to the SSH form
  `git@github.com:<owner>/<repo>.git` to match it. When offering the user a
  manual fix, name the form that matches the credential: deploy key → SSH
  URL, app/token → https URL.
- **Do not infer repo visibility from a deploy succeeding.** A private repo
  clones fine through the installed app while an anonymous clone fails — and
  the failure message is identical to the no-auth case. Before reporting why
  any clone worked or failed, check visibility with an anonymous probe
  (`git ls-remote https://github.com/<owner>/<repo>.git`, no token): it fails
  on private *and* unauthenticated-public-that-is-actually-private cases, and
  its success is the only cheap proof the repo is public. Claiming a repo was
  public because a clone worked is a mistake that takes a whole turn to walk
  back.
- **Multi-repo drift: the fix must land in the repo the app actually deploys
  from.** A project can live under two owners (a personal account and an
  org) with the same name, and a deploy fix pushed to one never reaches an
  app attached to the other — the apps are separate, the repos are separate,
  and each has its own commit history. A deploy from one of them failing
  after you fixed the other is not a fix that did not work; it is a fix that
  was never in front of that app. Confirm which `<owner>/<repo>` the failing
  app points at (`get_application`), then `git ls-remote` *that* repo and
  compare the commit to the one you fixed — before concluding anything about
  the credential or the platform. This same drift happens between a working
  copy left on the agent host and the GitHub repo the user deploys from:
  when the change exists only locally, the user's next deploy still fails and
  the fix looks broken. Whenever a fix touches deployment config, push it to
  the deployment repo in the same step, not after verification, and name that
  repo — "pushed to `<owner>/<repo>`" — in the report, so the user can see
  which one moved.

### Client-side traps — hosts file and origin allowlists ( verified by server probes, broken by the client )

A domain can be green on every server-side check — edge reachable, tunnel healthy,
origin serving 200, streaming SSE end-to-end — and still unreachable from exactly
one client machine. Before touching the server again, check the client.

**`ERR_CONNECTION_TIMED_OUT` / `ERR_CERT_AUTHORITY_INVALID` on one machine only.**
The Windows `hosts` file (`C:\Windows\System32\drivers\etc\hosts`) overrides
DNS for *every* resolver the browser and VS Code (Electron/Chromium) use, and a
stale entry pinning the domain to an old origin IP produces exactly these two
errors: a timeout when the old origin no longer listens, `CERT_AUTHORITY_INVALID`
when it serves a self-signed default cert. The trap: `nslookup` reads DNS
directly and **ignores** the hosts file, so `nslookup` shows healthy Cloudflare
IPs while the browser connects somewhere else entirely — two tools, same
machine, contradictory answers. Diagnose by reading the hosts file (`type
C:\Windows\System32\drivers\etc\hosts`), fix by deleting the stale line
(Notepad as admin) and `ipconfig /flushdns`. `192.168.1.30 crearoute.domainbot.my.id`
survived a full origin migration this way and looked like a Coolify bug for
hours. Same rule for any PaaS- or tunnel-migrated domain: the hosts file is a
client-side DNS override, and a migration leaves it stale with no warning.

**`403 Invalid origin` on correct credentials is an origin allowlist, not auth.**
Many app frameworks (Fastify/Better-Auth guard, Django ALLOWED_HOSTS, CORS
lists) compare the request `Origin` header against a fixed allowlist — typically
`APP_URL` plus localhost variants. Accessing the app through a LAN IP
(`http://192.168.x.y:port`) sends that IP as the origin, the guard 403s before
auth runs, and the login screen reports a wrong password. The credentials were
never checked. Two fixes, and the choice is a security decision: use the
registered `APP_URL` ( the domain — the intended path, keeps the allowlist
tight ), or extend the allowlist with the LAN origin ( convenient, widens the
CSRF surface ). Default to the domain; never widen the allowlist silently.

## Preflight checks

Follow this sequence. Report each check as pass/fail with what was actually observed.

1. **Read the deploy target.** `context/architecture-context.md` names it; if it does not, stop and say so — that is a bundle gap, not a deploy guess.
2. **Env table check.** Every `VITE_*` / env var the code reads must have a named value for the target environment (local, staging, production). Any var with no value for the target → fail, list it.
3. **Build with the target env, explicitly.** Build once with the exact env the deployed bundle will use — no `.env.local` inheritance. If the build output differs from a default local build, say so: that difference is the thing that would have broken in CI.
4. **CORS origin audit.** For every backend the app calls (Supabase Edge Functions, API routes), confirm the allowed origins include every domain that will serve the app, including the new one if a domain was added. Missing origin → fail.
5. **Domain registration.** If a custom domain is in play, confirm it was registered through the platform's own path (Workers `workers/domains`, Pages custom domains, **the Dokploy dashboard or its `domain.create` MCP call**), not a manual CNAME to a workers.dev hostname. On Dokploy, run `validateDomain` first: its error names the IPs Traefik accepts, which is the checklist for both the DNS record and the router port-forward. If a domain is already attached, also confirm its port field equals the container's runtime `PORT` — Dokploy overrides the Dockerfile's, so the domain port is the one that must match (see the Dokploy section) — and that HTTPS is enabled on it, since a web-only router answers 404 on 443. When the origin has no public port forward and a Cloudflare Tunnel is the access path, confirm who wires the hostname: the tunnel's ingress can be written over the API, but the public hostname's DNS record is dashboard-only (see the Tunnel section) — name that step to the engineer instead of reporting the tunnel as done.
6. **Secure-context features.** List any feature the app uses that requires a secure context (geolocation, clipboard, service workers on some paths, Web Crypto in some browsers). Each must either be on HTTPS in production, or have a user-facing fallback message. Silent absence → fail.
7. **Secret inventory.** For Supabase: `ALLOWED_ORIGINS` and any function secrets. For Cloudflare: Pages vars, Worker bindings. For Dokploy: the application's env vars (read MCP-side as `[REDACTED]` — confirm their names, and confirm in the deployment log that the container received them). List them; a missing secret is the most common post-deploy breakage.
8. **Path env vars must resolve inside the container.** Any env var the app uses as a filesystem path (database file, upload dir, cache dir) must be an **absolute path that exists and is writable by the container user**, and must land inside a mounted volume if the data must survive a redeploy. A relative path like `./data/crearoute.sqlite` resolves against the container's working directory, which for a non-root image (`USER node`, `/app`) is typically not writable and not the volume — the app fails to open its database on every start and the container **restart-loops** (`status: restarting` / `unhealthy`) with no useful log line. Check each path env var against the volume mounts and the image's `USER`/`WORKDIR` before declaring the deploy healthy; a container that restart-loops right after a successful build is almost always this, not a build problem.

Any fail → stop. Report the failure and the fix from the knowledge base above. Do not deploy around a failed preflight; the preflight exists because each check maps to a real, expensive failure.

## Verify before attributing a cause

Every failure class above has a cheap live probe that settles it, and the
user reads an unverified explanation as guesswork — especially when the
explanation implies they missed a setup step they in fact completed. The
discipline is part of the workflow, not a style choice:

1. **Enumerate the candidate causes as a list, then probe each one before
   naming it.** When the next explanation you are about to send would have
   the user do something in a dashboard (install an app, flip a setting),
   check the PaaS-side state first — the Coolify MCP exposes it (see
   `references/coolify-mcp.md`), and the GitHub API exposes the rest. A claim
   like "the app is not installed" or "the repo is public" is never safe to
   make from the failure message alone, because the message is identical
   across several causes.
2. **Cross-check claims about repo visibility against an anonymous probe** —
   `git ls-remote https://github.com/<owner>/<repo>.git` with no token. Both
   a private repo and a missing-credential case fail identically, so a
   successful clone tells you nothing about which one you have; only the
   anonymous probe's success is cheap proof the repo is public.
3. **Prefer building from source over pulling a prebuilt image when the PaaS
   has git access.** `build: .` in the compose file removes the entire
   registry-credential failure class — the git clone already works, the build
   needs no registry login, and the repo can stay private. Reach for a
   registry only when the build itself cannot run on the PaaS.
4. **Do not tell the user "the repo is connected, so deployment should work"
   or "the repo must be public, then"** — both are exactly the assumptions
   that waste an hour and that the checks above exist to refute. Verify the
   registry and credential state independently before reporting either.

## Artifact

Write the runbook to `docs/DEPLOY.md` (or append to the project's existing runbook): the stack, the env table per environment, the secrets inventory, the domain registration state, and the preflight results with dates. This is the handoff document — a client receiving the project should be able to re-run the deploy from it without asking you anything.

Cross-reference `context/architecture-context.md` when its env var table changes; `/selcy-sync` catches the specs that go stale when you edit it.

## What this skill never does

- Never deploys itself. It prepares and audits; the engineer (or CI) runs the deploy command.
- Never edits `context/` contracts directly; it reports gaps and lets `/selcy-sync` propagate.
- Never guesses a deploy target. If the bundle does not name one, that is an owed decision.
- Never treats a failed preflight as a warning. A fail is a stop.

## Portability

Any Agent Skills client on macOS, Linux, Windows. `git` and (optionally) the platform CLIs (`wrangler`, `supabase`) are the tools; shell snippets are POSIX reference. The knowledge base is stack-specific (Dokploy + Cloudflare + Supabase + Vite) — on a different stack, the preflight sequence still applies, and the knowledge base should be extended with that stack's paid-for facts as the team learns them.
