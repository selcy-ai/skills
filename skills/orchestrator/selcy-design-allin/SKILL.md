---
name: selcy-design-allin
allowed-tools: Bash, Read, Grep, Glob, Write, Edit, AskUserQuestion
description: "Run /selcy-design-allin once, after /selcy-sdd and before any /selcy-implement, to design every UI feature's screens in one pass instead of one /selcy-design NN per feature. Reads context/feature-specs/, filters the specs carrying a ## Design Reference, runs the same per-feature design loop sequentially inside one chat, and hands the engineer a single review of all screens before any build starts. The per-feature /selcy-design NN stays the default inside the loop; this is the upfront alternative for products whose data model is already stable."
---

# selcy-design-allin — design every screen upfront, in one pass

The design phase, batched. `/selcy-sdd` writes the specs; this skill
designs **every feature that carries a `## Design Reference`** in one
run, then hands the engineer one review covering all screens before any
builder starts. After the review, the loop continues exactly as it
would have: `/selcy-implement NN` per feature, review, test.

`/selcy-design NN` remains the default way to design — one feature per
chat, inside the loop, after the previous feature's build has fed back.
This skill exists for the case where that ordering costs more than it
returns: a product whose data model is already settled, where the
engineer wants to see and approve the whole surface before code exists.

## When this skill runs

Once per project, after `/selcy-sdd` (or `/selcy-audit`) has written
the bundle and **before the first `/selcy-implement`**. It is a
replacement for the design stage of the loop, not an addition to it —
running it and then also running `/selcy-design NN` per feature
duplicates work.

It is not for every project. The per-feature loop exists because a
mockup built before build feedback goes stale the moment a later
feature changes the data model. **This skill designs all screens before
any build feedback exists**, so it accepts that risk deliberately. Use
it when the data model is stable; use `/selcy-design NN` when it is
not. If you are unsure, that is the signal it is not stable — use the
per-feature loop.

## What it reads

1. `context/feature-specs/` — every spec, to find the ones carrying a
   `## Design Reference`.
2. `context/ui-context.md` — the design system, and the recorded
   `design backend:` line. **This skill never re-detects the backend.**
   It reads the recorded line and uses it verbatim; if the line is
   missing it stops and points the engineer at `/selcy-design`, which
   owns detection. One backend per project, chosen once.
3. The project's design collection — the `.pen` file, the Open Design
   `collectionId`, or the OD `projectId`, whichever the recorded
   backend names.
4. Prior `design/NN-*.md` notes, for consistency.

## The trade-off, stated up front

Every screen is designed before any build feedback exists. The
per-feature loop designs feature 05 **after** feature 03 has been
built, so the mockup for 05 reflects the data model 03 actually
produced. This skill designs 03 and 05 in the same morning, so 05's
mockup reflects what the spec **said** 03 would produce. When those
differ, some screens come back stale and are redrawn.

That is the cost. What it buys: one review covering the whole product
surface, consistent tokens across every screen by construction, and no
context-switching between design and build per feature. The engineer
approves one thing, not seven.

**The engineer must confirm they accept this trade-off before the run
starts.** It is the first question this skill asks, with the per-feature
loop as the recommended default. Do not start designing on a silent
assumption — a run that designs 8 screens the engineer wanted designed
per-feature is a run that has to be thrown away.

## Execution

### Step 0: Gate

1. `context/feature-specs/` exists and contains specs? Tidak → stop,
   the bundle is not ready. Name `/selcy-sdd`.
2. `context/ui-context.md` records a `design backend:` line? Tidak →
   stop. Name `/selcy-design` (which owns detection) and say the
   engineer can also answer the backend question there and come back.
   Ya → use that backend verbatim for every screen.
3. Scan every spec for `## Design Reference`. **Zero specs carry it** →
   stop and say so: this product needs no mockups, and this skill has
   nothing to do. That is not a failure.
4. Specs carrying it: **N**. List them to the engineer with their
   numbers and names, state the trade-off above, and ask one question:
   batch all N now (this skill), or design per feature inside the loop
   (`/selcy-design NN`)? Default is per feature. Only after the
   engineer picks batch does the run continue.

### Step 1: Kickoff (sekali per proyek)

Identical to `/selcy-design` Step 1, on the recorded backend: tokens
from `ui-context.md` become the design system, the navigation shell is
designed, and the engineer approves it **before any feature screen**.
The kickoff approval gate is not optional here — it is the one chance
to correct the design system while only one screen exists. On backend
A this is frame `00 · Panduan` + `30 · Komponen`; on backend B/C it is
the design system bridge plus a navigation-shell run. See the
corresponding section of `/selcy-design`.

### Step 2: Design each feature, sequentially, in this one chat

For each spec carrying a `## Design Reference`, **in feature order**:

1. Read the spec's `## Design Reference` + `ui-context.md` + the
   screens already designed in this run (consistency across features
   matters more here than in the per-feature loop, because no build
   feedback will arrive between them).
2. Apply the quality bar — `antislop`, `antislop-ui`,
   `antislop-layoutmobile`, `antislop-copywriting`, `ui-ux-pro-max`,
   and the ready-made component references. Same bar as `/selcy-design`.
3. Design the feature's screens on the recorded backend, using the
   backend's own per-screen workflow. This skill does not re-invent
   that workflow; it follows `/selcy-design` Step 2 for the backend
   recorded in `ui-context.md`.
4. **Stop on the first failure.** A backend error, a gate mismatch, an
   unresolvable inconsistency — the run halts there and reports which
   feature stopped it. Do not continue to the next feature in the hope
   that it goes better; a failure mid-batch is a failure of the batch.
   The engineer resolves it and re-runs from that feature.
5. Export per the recorded backend (PNG + `-ref.html` per screen, or
   previewUrl + symlink on backend C) and update the index
   (`design/<project>-ref.html` or frame `00 · Panduan`).

**One feature's screens are fully done before the next starts.** Not
interleaved. The batch is a sequence of complete per-feature designs,
not a single design of all screens at once — the isolation that makes
a mistake in one feature not reach the others is kept, only the
chat-boundary between them is removed.

### Step 3: Write the notes

One `design/NN-<nama>.md` per feature, same format as `/selcy-design`
(frame index, tokens, inconsistency decisions, ready-made components,
states not drawn, artifact locations). Plus one line per feature in
`progress-tracker.md`: `feature NN designed, artifacts at design/NN-*.md
+ -ref.html`.

### Step 4: The single review — this is the point of the skill

All screens done, the engineer sees them **together, once**:

- Every `design/NN-*.md`, concatenated into one report grouped by
  feature, with the inconsistency decisions and the ready-made
  components used.
- The index (`design/<project>-ref.html` or frame `00 · Panduan`),
  which now lists every screen of the product — this is the only
  artifact that shows the whole surface at once, and here it is
  complete rather than half-filled.
- Every PNG or previewUrl, one path per line.
- The trade-off reminder: these screens reflect the spec, not built
  behavior, and any feature whose build changes the data model may
  invalidate the screens after it.

The engineer approves, requests changes, or rejects the batch. Changes
go back to Step 2 for the affected features only — the approved ones
are not redrawn. Rejection sends the engineer back to the per-feature
loop, and that is a legitimate outcome, not a failure of this run.

**Pengiriman tidak pernah otomatis:** skill wajib menulis pesan ini,
satu path per baris. Tanpa pesan ini, engineer tidak menerima apa-apa.

### Step 5: Hand back to the loop

After approval, the product designs exactly like a per-feature project
would: the next step is `/selcy-implement NN` per feature, in feature
order, each in its own chat. The orchestrator (if used) picks up the
cards as normal — it does not run `/selcy-design NN` for features
whose `design/NN-*.md` already exists and whose tracker line says
designed; see the routing note below.

## What this skill never does

- Never re-detects the design backend. It reads `design backend:` from
  `ui-context.md` and uses it verbatim. Detection belongs to
  `/selcy-design`.
- Never designs a spec without a `## Design Reference`. The scan in
  Step 0 filters them out and they are never mentioned again.
- Never continues past a failed feature. One failure stops the batch.
- Never interleaves features. One feature's screens complete before the
  next begins.
- Never writes application code — that is `/selcy-implement`'s. Same
  rule as `/selcy-design`: the output is `design/`, not `src/`.
- Never edits `ui-context.md` directly — token changes go through
  `/selcy-sync`.
- Never runs twice on the same project. A second run after the bundle
  changed is `/selcy-sdd change` territory; this skill is the one
  upfront pass.
- Never skips the kickoff approval gate. With no build feedback to
  catch a wrong design system, the kickoff approval is the only gate
  that does.

## Portability

Any Agent Skills client on macOS, Linux, Windows. This skill needs
whatever its recorded backend needs (see `/selcy-design` Portability):
backend A the `pen` CLI, backend B the Open Design MCP on
Windows/VS Code/opencode, backend C the Open Design daemon on Linux.
It adds no tool requirement of its own — it drives the recorded
backend's workflow per feature.
