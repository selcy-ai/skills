---
name: selcy-check
allowed-tools: Bash, Read, Grep, Glob, Write, Agent
description: "Run /selcy-check before closing a feature. verify mode runs the real app and proves the feature behaves per its spec's Check When Done; review mode reads the diff on a fresh model and ranks findings. Read only, never edits code. Points failures at /selcy-debug or /selcy-implement."
---

## What this skill does

The gate before a feature is called done. Two modes, separate jobs:

- **verify** (runtime proof): run the real app and watch the feature behave. Proves it conforms to its spec, which green tests never reveal. Read only on code, writes nothing.
- **review** (fresh model code review): a senior read of the diff on a different model than the one that wrote it, because a model reviewing its own output shares its own blind spots. Writes ranked findings to `context/.reviews/`.

Neither mode edits code. verify points failures at `/selcy-debug` or `/selcy-implement`; review reports findings for the engineer to fix.

Green tests do not close a feature. A test suite proves the code does what the tests say; verify proves the tests say what the spec says.

## Pick the mode

First step, before reading anything. Look at what followed `/selcy-check`:

- Starts with **verify** (or `run`) → verify mode, fully.
- Starts with **review** → review mode, fully.
- No mode word, or a feature name with no mode → do not guess, do not default. Show the options as plain text and stop:

```
Which check do you want? Type one:
  • verify  run the real app and prove the feature works against its spec
  • review  a fresh model senior read of the diff, ranked findings
  • both    verify first, then review
```

Route on the typed word. Do not mix modes in one run; on `both`, verify first, then offer review.

## Resolving the feature

Same resolution as `/selcy-implement`: read `context/progress-tracker.md`, then match the argument (number or name) against `context/feature-specs/`. No argument → the current feature, the one progress-tracker lists as In Progress, else the last Completed. No bundle → stop, and tell the engineer to run `/selcy-sdd` first on a new project, or `/selcy-audit` on a codebase that already exists.

## verify mode

1. Read the feature spec, then the context files the spec depends on. The acceptance contract is the spec's `## Check When Done`; that is what you prove.
2. Get the app running for real. Dev server, production build, or whatever runtime the stack uses. Not a mock, not a dry run.
3. For each `Check When Done` item: exercise it, and report pass or fail with what you actually observed. "Should work" is not a result; the observed behavior is.
4. Also check the surfaces the spec names that no checklist item covers: a page that must render, a state the spec lists (loading, empty, error, success). A checklist can miss a surface; the spec's own sections cannot.
5. **Features with a `## Design Reference` must be verified in a real browser at every breakpoint the reference names** (desktop 1360, mobile 390, tablet 820 when the spec asks). A builder screenshot is a claim, not proof — the builder renders its own viewport once and cannot see what a real user sees: elements covered by fixed UI (a FAB overlapping the last list row), horizontal overflow that only appears at real viewport width, text clipped at 390px that looks fine in a cropped frame. Open the running app at each width, scroll the page, and confirm: no horizontal overflow (`scrollWidth <= clientWidth`), no content hidden behind fixed elements (scroll to bottom and check the last row is fully visible), every label readable. Report what you observed per breakpoint, not "looks fine."
6. Report: passes, failures with observed versus expected behavior, and anything you had to exercise that the spec never specified. That last group is owed decisions, and it goes back to `/selcy-implement`'s gate.

Read only. Never fix, never edit, never commit. A failure points at `/selcy-debug` if it is a bug, or `/selcy-implement` if it is work the feature still owes. A failure in a surface this feature did not build is a pre-existing bug, not a regression: record it with `/selcy-debt` and keep this feature's verdict honest.

## review mode

1. Resolve the feature, then get its diff: uncommitted changes, plus the commits since the feature went In Progress.
2. Spawn a reviewer on a different model than the one that wrote the code, on the cheapest tier that can read a diff. Give it the diff, the feature spec, and the standards files. It returns findings; it writes nothing.
3. Rank what comes back by severity: blocks close, should fix before close, nit. Drop findings that contradict a standards file the code correctly follows; the standards file is the contract, not the reviewer's taste.
4. Write the ranked findings to `context/.reviews/<feature>.md`, and report them in plain language.

A finding that reveals a real standards violation goes to `/selcy-implement` to fix. A finding that reveals the standards file itself is wrong is an owed decision: report it, do not edit the standards file here.

**A grep is not a finding.** When you check code by pattern — `grep`, `rg`, a custom
regex — the match is a *candidate*, never a verdict. Bare greps produce the classic
false positive: a gate looking for `device_hash|hidden_reason` fires four times, all
four in a documentation comment explaining *why* those fields are excluded — the gate
calls it a violation, the engineer loses an hour. Two rules:

1. **Strip comments before matching.** Run the source through a comment stripper
   (or match with a parser-aware tool) so documentation cannot trigger a code rule.
   If the stack has no stripper handy, drop the matches that fall inside comment
   regions — but do it mechanically (line position against lexer state), not by
   eyeballing the match and deciding it "looks like a comment."
2. **A match is evidence, not a conclusion.** Read the matched region before
   reporting it. A finding whose entire basis is "the pattern matched" is a finding
   that has not been verified; say what the code actually does in the matched region,
   or drop the finding.

The same rule applies to verify mode: any `Check When Done` item you prove with a
pattern match must show the stripped match and the surrounding code, not the raw
grep count.

## What this skill never does

- Never edits code, in either mode.
- Never marks a feature Completed; that is `/selcy-implement`'s, on the evidence this skill provides.
- Never guesses a mode.
- Never reviews on the same model that wrote the code.

## Portability

Any Agent Skills client on macOS, Linux, Windows. `git` is the only required CLI. Other shell snippets are POSIX reference; use your agent's cross platform file, process, and browser tools. No subagent support falls back to an inline review by the main thread, noted in the report.
