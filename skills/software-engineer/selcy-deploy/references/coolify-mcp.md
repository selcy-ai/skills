# Coolify MCP — verification reference

Depth file for `/selcy-deploy`, the Coolify half of the PaaS knowledge base.
The Coolify instance is reachable as an MCP server (listed in the profile's
`mcp_servers` config, {"jsonrpc":"2.0"} over HTTP with a team Bearer token from
the profile env). Call it with plain `curl` when a MCP tool is easier to
script than to invoke — every read below is a `tools/call` request.

The MCP is the **verification surface**: it answers, in one call each, the
questions that otherwise become a wrong guess followed by a user correction.
Use it before attributing any deploy failure to git auth, source config, or
repo visibility.

## Answering "which git credential covers this repo?"

`list_github_apps` → `list_github_repositories` (needs `github_app_uuid`)
is the definitive check. It returns every repo each installed app can see,
with `private` flags.

- The failing repo **is** on the list → the GitHub App install is fine; the
  failure is elsewhere (most often how the repo was attached — see the
  git-auth section of the skill). Do **not** ask the user to install
  anything.
- The failing repo is **not** on the list → the install really is missing for
  that account; that is the one case where an install is the fix.

Do not infer either answer from the failure message: `could not read Username
for 'https://github.com'` is produced by a missing install, by a repo
attached with the wrong URL scheme for its credential, and by a private repo
probed anonymously.

## Answering "did the deploy fail at git or at the registry?"

`get_deployment` (with `include_log_summary: true`) holds the full deploy log.
Read it for the dividing line:

- `Importing <owner>/<repo>:<branch> (commit sha …)` with **no
  `git ls-remote` line** → git auth worked (app path).
- `GIT_SSH_COMMAND="ssh -i …" git ls-remote 'https://…'` → repo was attached
  by URL with an SSH credential, which cannot work against an https URL.
- `Importing …` succeeded, then `error from registry: unauthorized` → git is
  fine; the Docker daemon pulled the image anonymously. Registry problem, not
  git — see the image-pull rules in the skill (compose `build: .` removes it).

Deployment list pagination watch-out: `list_deployments` (application_uuid,
page) returns rows whose per-row UUID field is named `deployment_uuid` —
`get_deployment` wants *that* value, not the commit sha that also appears in
the rows. Fetch the list, extract `deployment_uuid`, then fetch the log.

## Answering "is the container actually running?"

`get_application` → `status` is the source of health (`running:healthy`,
`restarting:unknown`, `exited:unhealthy`), and `list_unhealthy_resources`
aggregates it across the server. A container whose env points at a path it
cannot write takes a few polls to leave `restarting` — poll the deployment to
`finished` first, then read app state, then probe the port with
`curl -o /dev/null -w '%{http_code}'`.

## Reproducing a failed app creation with a test app

When a user's deploy fails at the git stage and the cause is in dispute, do
not argue about how they created the app — build the same app yourself and
read the log. `create_application` with `action: "github_app"` is the
dropdown path in API form:

```json
{"name":"create_application","arguments":{"action":"github_app","data":{
  "project_uuid":"<from list_projects>",
  "environment_name":"production",
  "server_uuid":"<from list_servers>",
  "github_app_uuid":"<from manage_git_source list / list_github_apps>",
  "git_repository":"<owner>/<name>",
  "git_branch":"main",
  "build_pack":"dockercompose",
  "name":"<throwaway-name>",
  "docker_compose_location":"/docker-compose.yml"}}}
```

Response is `{"data":{"uuid":"…"}}` — the app UUID; then `deploy` → poll
`get_deployment` as in the sequence above. Interpretation:

- `Importing <owner>/<repo>:<branch> (commit sha …)` → the credential path
  (GitHub App, dropdown attachment, repo visibility) is **fine**. The user's
  failing app differs in source selection, or the cause is the repo's own
  content — check the compose file at the imported commit and the image
  namespace it references (a compose naming an image that was only ever
  pushed under a *different* owner namespace fails with the same
  `error from registry: denied` as a private package).
- `GIT_SSH_COMMAND … git ls-remote 'https://…'` → the repo reached the PaaS
  attached by URL, not via the app — the fix is re-attachment, not install.

Also: `list_github_apps` and `list_github_repositories` need no arguments
(the latter needs `github_app_uuid`) and the repo list carries `private`
flags — it double-checks both the install state *and* visibility in one
read.

## Fixing env from the MCP

`get_env_values` (with `action: "list"`) enumerates the app's environment
with per-key UUIDs; `manage_env` (`action: "update"`, `resource:
"application"`, `data: {key, value, is_runtime: true, …}`) writes a value by
that UUID. Use it for the path-env fix: a database path env must be an
absolute path inside a mounted volume (`/data/crearoute.sqlite`, not
`./data/…`) or the container restart-loops forever with no useful log line.

## Crearoute verified shape

For reference, the deployment that reached `running:healthy` end-to-end:

- `build_pack: dockercompose`, `docker_compose_location: /docker-compose.yml`
- compose file with `build: .` (not `image: ghcr.io/…`)
- `DATABASE_PATH=/data/crearoute.sqlite` (absolute, inside the volume mount)
- source: GitHub App dropdown (never a typed URL)

Deployment sequence from the MCP: `deploy` (uuid, resource_type
"application", force, confirm) → poll `get_deployment` to `finished` →
`get_application` for health → port probe → env fix with `manage_env` →
redeploy.
