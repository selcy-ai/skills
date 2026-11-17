# PaaS deployment troubleshooting — verifiable causes vs. failure-message lookalikes

Depth file for `/selcy-debug`. The recurring trap in PaaS deployment
debugging: five different causes produce the same few failure strings, so the
failure message alone never identifies the cause — and the fastest-looking
explanation ("the app is not installed", "the repo must be public") is
usually the wrong one and puts the user to work fixing something already
correct.

## The lookalike set

`could not read Username for 'https://github.com'` is produced by all of:

1. GitHub App installed on a different account than the repo's owner.
2. Repo attached to the PaaS by a **typed git URL** while the PaaS uses its
   SSH credential — `GIT_SSH_COMMAND` never applies to an `https://` URL, and
   the non-interactive container cannot answer the username prompt.
3. A private repo probed with no credential at all.

Distinguishing probes (each one is a single call, and each settles the
question the failure message cannot):

| Question | Probe | Reads |
|---|---|---|
| Does any installed app cover this repo? | Coolify MCP `list_github_apps` → `list_github_repositories` | per-app repo lists with `private` flags |
| Which credential path did this deploy actually use? | Coolify MCP `get_deployment` log | `Importing …` only (app path) vs a `GIT_SSH_COMMAND … git ls-remote 'https://…'` line (URL-attached path) |
| Is the repo actually public? | `git ls-remote https://github.com/<owner>/<repo>.git` with **no token** | success is the only cheap proof; failure means private *or* no credential |
| Did the deploy fail at git or at the registry? | `get_deployment` log | import succeeded + `error from registry: unauthorized` → registry, not git |
| Is the failing app looking at the repo I actually fixed? | `get_application` (`git_repository`) + `git ls-remote` that repo, compare commit sha | owner/name + head commit; a different owner/name or an older sha = drift |
| Does the image the compose names exist in that namespace? | `curl "https://ghcr.io/token?scope=repository:<owner>/<pkg>:pull"` (no auth) then `GET /v2/<owner>/<pkg>/tags/list` | empty/`denied` token = private-or-missing; a token that does not list the tag = the tag never existed there |

## Rules that fall out

- **Check the app-install state before recommending an install.** If the
  repo is already on the app's visible-repo list, the install is fine and the
  cause is how the repo was attached (case 2). Sending the user to install an
  app that is already installed is the correction that costs a whole turn.
- **Never infer visibility from a successful clone.** A clone through the
  installed app succeeds on a private repo; an anonymous probe fails on it.
  Only the anonymous probe tells you which world you are in.
- **An `unauthorized`/`denied` pull does not mean the image is private — it
  means the daemon could not pull it, and that has two causes that need
  different fixes.** A private package needs registry login; a compose
  referencing `ghcr.io/<owner>/<pkg>` where the image was only ever pushed
  under a *different* owner (the project lives under two GitHub accounts)
  needs the compose or the push fixed. Both read `denied`. The dividing
  probe is the anonymous token request above, or simply checking which
  namespace the CI/workflow pushed to. Prefer the `build: .` fix, which makes
  the question moot.
- **Same project name under two owners is multi-repo drift, not one repo.**
  A fix pushed to `org-a/name` never reaches an app attached to
  `org-b/name`. Before debugging a deploy that "still fails after the fix",
  confirm the app's `git_repository` and the head commit of *that* repo —
  the fix may never have been in front of it.
- **Prefer the explanation whose probe you have already run.** When two
  hypotheses fit the message, pick the one you can verify in one call, and run
  that call before writing the explanation — not after the user questions it.
  "I have not checked yet" is a better sentence to send than a confident wrong
  cause.
- **Reproduce the credential path with a test app before disputing the user's
  story.** `create_application` (action `github_app`) + `deploy` + read the
  log is the dropdown path replayed from the API; an `Importing …` line
  proves the credential path works and moves the cause to source selection
  or repo content. Do this instead of telling the user how they must have
  created the app — the log of a repro beats an argument about a dashboard.
- **Attraction rule for PaaS deploys: build from source when git auth works.**
  Switching the compose file to `build: .` removes the registry-credential
  failure class entirely — no GHCR visibility, no daemon login, no image
  public/private question. Reach for the registry only when the build cannot
  run on the PaaS host.
