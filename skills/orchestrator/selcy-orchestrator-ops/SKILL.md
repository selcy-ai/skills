---
name: selcy-orchestrator-ops
description: "Advance a stalled selcy-orchestrator kanban board."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Selcy, Kanban, Autonomous, Orchestrator]
    related_skills: [selcy-orchestrator, opencode]
---

# Selcy orchestrator ops

The on-call layer for a running `selcy-orchestrator` board. The orchestrator
skill drives one card per tick; this skill is what the human-facing agent
(holding the chat) does **around** those ticks: read the board, decide
whether a block is real, feed the chain, and keep the loop from stalling.
It never edits application code and never answers an owed decision — it
routes them.

## When to Use

- A selcy-orchestrator board is running and a card is `blocked` and you need
  to decide whether the block is real or the worker simply ran out of turn
  budget.
- A feature card just completed and the child cards have not promoted — the
  chain needs feeding.
- A worker seems hung and you need to tell a hang from a context-exhausted
  session from a dead process.

## The board is the state

Everything durable lives on the board or in the repo, never in chat:

- The board is per-project: `hermes kanban boards switch <project-slug>`.
  Verify the active board before reading or writing any card.
- A card's **comment thread** is its cross-tick memory: build/review/test
  session ids, the skill prefix, the model choices, every block reason and
  its resolution. Read it with `kanban_show` before acting on a card.
- `context/progress-tracker.md` is the other half of the state. Current Goal
  drives the next delegation; Completed holds the evidence trail.

## Reading the board

```
hermes kanban boards switch <project>
hermes kanban list --status ready
hermes kanban list --status blocked
hermes kanban show <card-id>      # body + comments + runs + events
hermes kanban log <card-id>       # the worker's full transcript
```

`kanban log` is the ground truth for "what is the worker doing right now".
`kanban show` gives you the durable decisions. A stuck card almost always
shows its reason in the last few `blocked`/`gave_up`/`timed_out` run entries.

## Is the board healthy? Three questions

**1. Is anything `ready` but not `running`?** The dispatcher ticks every 60s;
a card sitting in `ready` for minutes means the dispatcher is not spawning —
gateway problem, not a card problem.

**2. Is the chain actually advancing?** After a card completes, its children
should promote to `ready` automatically (all parents done). If they stay
`blocked` and the parent is `done`, the card-block form is `needs_input` with
no open parent — the dependency-link form (`kind=dependency`) is what
auto-promotes. Manual `hermes kanban unblock <card-id>` returns a blocked
card to `ready` when the block reason has been answered.

**3. Is the worker alive?** Check the process, not the log alone:

```
ps -eo pid,cmd | grep "opencode run"   # is a build/review/test running?
ps -p <pid> --no-headers               # is the specific worker alive?
```

A `gave_up`/`timed_out` run with `Iteration budget exhausted (150/150)` means
the worker turn ended, **not** that the feature failed — the work is usually
committed on disk; the next tick resumes from the tracker.

## Feeding the chain after a completion

When a feature card lands in `done`:

1. Verify the artifact, not the claim: the commit hash, the `feat-<NN>` tag
   (`git cat-file -t <hash>`, `git rev-parse feat-<NN>`), the review file at
   `context/.reviews/<feature>.md`, and the gate counts in the tracker's
   Completed line. A tag left pointing at a docs commit, or a review file
   that was written but never committed, is a *gate mismatch* — the loop
   will happily build the next feature on top of it.
2. Unsilence the chain: unblock the child cards whose dependency just
   completed, or the board sits idle with everything `blocked` and one card
   `done`.
3. Say state, not ETA: what phase the next feature is in, what is committed,
   what is in flight. A duration estimate expires; the state does not.

## The hallucinated commit

A builder exits zero and its transcript shows `git commit` tool output — a
hash, a tag move, files written — and none of it executed. The code on disk
is real, the gates are green, only the git step never happened. This is a
**gate mismatch**, not a done build, and it is not rare.

Verify every claimed artifact against the repo before trusting any of it:

```bash
git rev-parse <hash>            # must succeed for each claimed commit
git tag -l feat-<NN>            # must list the tag
git log --oneline -1            # must show the claimed commit at HEAD
test -f <each claimed file>     # must exist
git status --porcelain | wc -l  # 0 if the commit really landed
```

`git status` still showing the feature's files as modified or untracked is
the tell — the build is sitting in the working tree uncommitted. Do not
re-delegate from scratch and never `git stash`, clean, or reset the tree: the
uncommitted diff **is** the feature. The fix is a real commit in the resumed
build session (`opencode run --session <id>`, never a sibling), then unblock
the card with the verification results attached so the next tick does not
re-derive them.

## Contract drift — the builder edits the bundle

The hallucinated commit's meaner sibling. The builder hits an **owed
decision** mid-build — a spec promises a mechanism the code cannot deliver,
the reviewer flagged a contract violation — and instead of blocking and
surfacing the question, it edits `context/` to make its assumption the
answer. The signature is a statements diff, not a code diff: `git diff
"context/feature-specs/<NN>-*.md"` rewrites the sentence the reviewer quoted,
or `git diff context/progress-tracker.md` adds a line reading "keputusan
engineer" or "RESOLVED" for a question the engineer never answered. The
bundle is the contract; the worker's own rule is never to edit it, so a diff
there after a builder exit is never legitimate builder output.

Check it after **every** builder exit, before trusting anything else:

```bash
git diff --stat context/ | tail -3   # anything besides the review file is suspect
```

`context/.reviews/<feature>.md` is the reviewer's own artifact and expected.
A spec, the tracker, `debt.md`, or a standards file changing is not. On a
hit:

1. `git checkout -- <file>` each contract file the builder touched. The
   uncommitted code changes are still the builder's real work — leave them.
2. Surface the question to the engineer verbatim (it will be in the review or
   the builder's own reasoning). Do not accept the builder's self-written
   answer as the engineer's answer — a tracker line claiming a decision is
   **forgery** when the engineer never said it in chat or in the card.
3. After the engineer answers, apply the edit yourself as the named decision,
   commit it, and *then* resume the build session for the remaining rework.

This failure clusters on fallback models handed an unanswerable question.
When a card has blocked once on an owed decision, the next builder exit on
that card should be checked twice as hard.

## Build model is the engineer's call

A worker caught without a recorded build model picks one itself — and when
the provider's quota for the primary model runs out mid-project, it swaps in
whatever model it likes (the harness default, a free-tier filler) without
asking the engineer, then resumes the session on that model. The options
panel in the orchestrator skill covers review and test models, and the build
model is the same kind of decision: it is not the worker's to make.

The project's contract files carry the models. Read them before any
re-delegation, and check what the running process actually carries:

```bash
ps -eo pid,cmd | grep "opencode run" | sed 's/.*--auto//'   # see --model and prompt
grep -rn "model" context/ai-workflow-rules.md context/progress-tracker.md
```

When the primary build model is down, don't let the worker free-associate a
replacement. Probe the provider with a trivial completion first — a real
answer means the model is alive, the quota or maintenance text the provider
answers instead of a completion means it is dead; probe the named fallback
the same way before handing it over. A dead primary with no recorded
fallback is an **owed decision**, not a detour into the model list: surface
it to the engineer, name the living candidates you probed, and block the
card.

## Unauthorized decomposition

A worker tick that has run out of ideas calls `kanban decompose` and splits
the feature card into children. The giveaway is the child bodies: they
describe work that is not in `context/feature-specs/<NN>-*.md` — different
storage engines, different deploy targets, invented acceptance criteria. The
worker has hallucinated a project instead of reading the spec.

Cleanup is two steps because delete requires the archived state first:

```bash
hermes kanban archive <child-ids...>
hermes kanban archive --rm <child-ids...>
```

Then comment on the parent naming the deleted children and why, and return
the parent to the board — a card that reached `triage` needs the DB update
(see *Returning a `triage` card to the board*), a `blocked` one takes
`hermes kanban unblock`. A feature card is one spec worked end to end in one
build session; if the card looks too big, the answer is a bigger
`@selcy-implement` run in the same session — never a decomposition.

## Diagnosing a stuck run

Follow the session, not the log tail. `opencode` sessions live in
`~/.local/share/opencode/opencode.db`; query the `session_v2` table
(`title`, `directory`, `time_created`, `tokens_input`/`tokens_output`/`tokens_cache_read`,
`model`, `time_archived`) with a heredoc python script — an inline `python3 -c`
is rejected by the security scan for nested executable bodies. See the
`opencode` skill's context-ceiling section for reading `finish: stop` states.
`session_v2.directory` is the project path; the sibling `project` table's
`name` column is unreliably populated, so group by `session_v2.directory`
rather than joining.

**Session-id routing.** A worker turn that ends mid-run leaves the session id
in the card comments. The next tick must **resume** that session
(`opencode run --session <id>`), never fork a sibling — the session holds the
build's accumulated reasoning, and two sessions for one feature make the
evidence unreviewable. If a worker has already forked, the card comment
naming the original session is the tiebreaker.

**Working tree discipline.** While a build session is alive the working tree
is its — no `git stash`, no `git checkout`, no editing its files. To run a
baseline, clone to a scratch dir. And confirm with `ps` that the worker is
gone before treating a log's `EXIT=` line as the session's exit: internal
shell commands inside the session print their own EXIT lines.

## DB-hygiene pitfall (integration-test suites)

A suite that inserts into a **shared dev database** leaks rows: integration
tests written against the project's live Postgres container accumulate
`open`-state rows, and the next run times out on a sweep that walks every
open row (an N+1 cron sweep is the usual victim). Failure looks like a flaky
test in an unrelated feature; the cause is row accumulation across runs.

Rules:

- Before judging a suite flaky, check whether **isolation** passes while the
  **full** run fails — that split is the signature of cross-file DB
  contention or row pollution, not a logic bug.
- `--fileParallelism=false` turning the run green is a diagnostic, not a
  fix. Record it as a known-flaky marker, and clean the shared tables before
  the run instead:
  `docker exec <pg> psql -U <user> -d <db> -c "delete from queue_runs where status='open'; delete from orders;"`
  (after confirming the suite has no teardown that expects the rows).
- Write the cleanup requirement into the card comments so the worker runs it
  before its gate, or the suite goes red again two runs later and looks like
  a regression.

## Is the loop paying for itself? Attribute cost by stage

A slower-than-expected loop invites structural proposals — drop the review
stage, merge review and test into the build session, defer all testing to the
end. Check the spend before structurally changing the loop; intuition about
which stage is expensive is reliably wrong, because every stage feels slow
while it is the only thing being watched.

Run the attribution script against the project's session database:

```bash
python3 <skill-dir>/scripts/session-cost.py /root/workspaces/agent-build/<project>
python3 <skill-dir>/scripts/session-cost.py            # all projects, for comparison
```

It groups the project's sessions by loop stage (build / review / test / probe)
and totals each stage's tokens, then flags the two violations the aggregate
hides:

- **One feature with several build sessions** (`feat-04`, `feat-04-r1`, or a
  `-build2`/`-build3` series). The loop's own contract is one build session per
  feature, resumed after any interruption. A 4x or 6x build series is that
  contract breaking — the expensive problem is the rework loop, not the
  structure. Fixing it is the resume rule in *Diagnosing a stuck run*; it is
  not a reason to restructure the loop.
- **One feature with several review rounds** (`-review` x3 or more). Each
  round re-reads the whole codebase, so repeated review rounds dominate the
  review budget while suggesting a finding that was never actually fixed —
  traceable via `@selcy-implement`'s partial fix.

Two consistent findings across real projects: the **build stage is the vast
majority of the spend** (roughly 4-5x review and test combined), and **test
sessions are chronically under-run relative to the contract** — a project
with a review session per feature but a single test session total is skipping
the test stage without saying so. Name both in the report; the engineer decides
whether to accept the skip.

Do not use the aggregate to justify dropping a verification stage. Review and
test are a minority of the cost and they are the only stages that catch a
builder that commits a half-feature; the aggregate shows the rework loops are
the expensive part, not the verification.

## Answering a block

A card that blocks more than twice on the same reason lands in `triage` with
`block_loop_detected` — the board has stopped retrying, which is correct
behavior, not a bug. Only **owed decision** blocks stop with you. Surface the
question verbatim in the reply, not only in the card (a block written only to
the card is one the engineer finds hours later), name the consequence of each
option so the choice is informed, and do not pick the recommended option on
the engineer's behalf. Point at `@selcy-grill` then `@selcy-sync` so the
answer lands in the standards file instead of dying in chat.

The other three kinds go back to the build session without you. The
orchestrator names the skill that resolves each block kind — repeat that
name to the engineer rather than improvising an answer. `@selcy-grill` then
`@selcy-sync` settles an owed decision; `@selcy-debug` in the build session
fixes a bug; `@selcy-sdd specs <feature>` repairs a wrong checklist. Diagnose
the block kind from the card's `blocked` run entry, then surface it to the
engineer verbatim with the resume command.

## The owed-decision round-trip

An owed decision is not answered once — it is answered once **per round**, and
a single card can raise several in sequence: the first feature with real UI
typically surfaces an auth-client pattern, then a seed/fixture question, then
a spec-vs-engine conflict, each its own block. Treat every block as its own
round; the previous answer never covers the next question.

Per round, in order:

1. Surface the question verbatim with the consequence of each option — the
card's reason text already carries them, forward it rather than paraphrasing
(paraphrasing a spec question is how the nuance gets lost).
2. When the engineer answers in chat, write the answer to a **card comment**
before anything else. The worker has no cross-tick memory, so an answer that
lives only in chat is one the next tick never sees. Name the option chosen,
the reason, and every downstream feature it applies to.
3. Return the card to the board (below) and let the worker resume the
**same** build session.
4. The worker makes the answer permanent by delegating `@selcy-grill` then
`@selcy-sync` into an `opencode run` session — the skill suite is installed
in that harness, so the decision lands in the standards file instead of
dying in chat. Do not hand-write the standards file yourself; `context/` is a
contract.

An answer given only in chat forces the next tick to re-derive the question,
which is how the same card blocks on the same reason twice.

## Returning a `triage` card to the board

No kanban CLI command revives a `triage` card: `unblock`, `promote`, `claim`,
`reclaim`, and `schedule` all refuse on that status (the messages look like
"not blocked/scheduled?" or "promote only applies to 'todo' or 'blocked'").
The direct path is an UPDATE on the board's own database:

```bash
python3 - <<'EOF'
import sqlite3
db = sqlite3.connect('/root/.hermes/kanban/boards/<project>/kanban.db')
db.execute("update tasks set status='ready' where id='<card-id>'")
db.commit()
EOF
```

Use the heredoc form — an inline `python3 -c` is rejected by the security
scan for nested executable bodies. The dispatcher claims a `ready` card on
its next 60s tick; nothing else needs restarting. A card in `triage` still
holds its full comment history and session ids, so nothing is lost by the
detour.

## What this skill never does

- Never answers an owed decision. It surfaces the question and routes it.
- Never edits `context/` contracts.
- Never edits application code. Small infra repairs (progress-tracker
  restoration of a line lost to a `git commit --amend`, a review file that
  was written but not committed) are the boundary, and each one is reported
  in the chat as an after-the-fact audit trail.
- Never deletes a session it did not create.
- Never marks a feature complete. It reads the tracker; the builder writes it.
