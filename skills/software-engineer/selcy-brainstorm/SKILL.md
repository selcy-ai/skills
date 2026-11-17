---
name: selcy-brainstorm
allowed-tools: Bash, Read, Grep, Glob, Write, AskUserQuestion
version: 1.0.0
author: selcy
license: MIT
metadata:
  hermes:
    tags: [planning, product, prd, sdd, greenfield]
    related_skills: [selcy-sdd, selcy-grill, selcy-audit]
description: "Vague idea to clear PRD, then /selcy-sdd. Use before sdd."
---

## When to Use

- The idea is abstract — "something like X for Y" — and you cannot yet state the **problem**, the **user**, and the **scope** in one sentence each.
- Before `/selcy-sdd` on anything you have not yet said out loud as a product.
- When you want to know whether an idea is worth building at all, or whether it is a serious product or a trial MVP.

Do not run it when:
- A `context/` bundle already exists — you are past this door. Use `/selcy-sdd change` for a deliberate change, `/selcy-grill` for one open decision.
- The idea is already mature (problem, users, scope each in one sentence) — go straight to `/selcy-sdd`.
- Only one decision is open and the rest is settled — `/selcy-grill` settles it in one line, not a document.

## What this skill does

The door before all doors. `/selcy-sdd` assumes the idea is already mature — its first rounds ask for the problem, the users, the success metrics, and then it **freezes a feature list into stable numbering that never renumbers**. Running it on an idea that is still a feeling produces a bundle built on a guess, and every downstream skill (implement, test, orchestrator) then builds on that guess. This skill is what turns the feeling into something sdd can safely freeze.

It is a **conversation, not an interview**. `/selcy-grill` and `/selcy-sdd` run decision panels: 2–4 already-formed options with a recommendation, the engineer picking. Brainstorm is the mode *before* options exist. You have half a picture; the agent restates it back in words a layperson would follow, names what is missing, and converges on a Product Requirements Document it writes to `docs/prd.md`.

**Output: one file, `docs/prd.md`.** It never writes anything under `context/` — the bundle is `/selcy-sdd`'s to author. The PRD is the input sdd reads; the contract is still sdd's to make.

## When to run

- The idea is abstract — "something like X for Y" — and you cannot yet state the **problem**, the **user**, and the **scope** in one sentence each.
- Before `/selcy-sdd` on anything you have not yet said out loud as a product.
- When you want to know whether an idea is worth building at all, or whether it is a serious product or a trial MVP.

Do not run it when:
- A `context/` bundle already exists — you are past this door. Use `/selcy-sdd change` for a deliberate change, `/selcy-grill` for one open decision.
- The idea is already mature (problem, users, scope each in one sentence) — go straight to `/selcy-sdd`.
- Only one decision is open and the rest is settled — `/selcy-grill` settles it in one line, not a document.

## The explaining rule — this skill's core

Everything the agent says must be understandable to someone who has never built software. This is not a style choice; it is the gate the whole skill runs on, because an idea the engineer cannot say in plain words is an idea that is not yet clear.

- **Every technical term gets unpacked on first use.** "Rate limiter — that's a turnstile at the door: only so many requests per minute get in, the rest wait." Not "we add a rate limiter".
- **Every proposal is explained at two levels**: what it does in plain words, and what it costs ( build hours, a running service, a paid plan, a maintenance burden ). A suggestion whose cost is invisible is a suggestion the engineer cannot actually evaluate.
- **Analogy first, name second.** Say the thing in the familiar shape, then give it the name everyone calls it. The name alone teaches nothing.
- **Restate before you build on it.** Each round starts with the idea as the agent now understands it, in one plain paragraph, so the engineer watches it sharpen and can correct a wrong reading at the cheapest moment.
- **Mark whose idea is whose.** "What you said, in clearer words:" versus "My suggestion, not yours yet:" — a suggestion that blends into a restatement is the agent quietly authoring the product. The engineer decides what the product is; the agent only proposes.

## Step 0: Restate the idea

Ask one open question: "tell me what you have in mind." Then write the idea back in **one plain paragraph** — no bullet points, no jargon — and end with: "is that what you mean? Anything I got wrong, say it now."

Do not advance until the engineer confirms the restatement. A brainstorm that builds on a misreading spends the whole session sharpening the wrong idea.

## Step 1: The exploring rounds

Work the five questions, one or two per round, in **plain conversation** — not panels. This is the difference from grill: here the answers are *discovered together*, and the agent is allowed to propose what the engineer has not considered.

1. **Who** — who is this for? Name the person, not a demographic. "Small-shop owners who invoice from a phone" beats "SMB users".
2. **What problem** — what is broken or missing for them today? If the answer is "they don't have this app yet", the idea is a feature looking for a problem, and you say so.
3. **Why now / why you** — what makes this the right time or the right person to build it. A weak answer here is the most common reason a product quietly dies, and it is a kindness to name it early.
4. **The smallest version** — if all of this vanished except one thing, which one thing would still be worth shipping? This is the MVP seed; keep it.
5. **What would make it serious** — what turns a trial into a real product? Named users, data that must not be lost, money moving, uptime that matters. Whatever is missing is exactly what makes it an MVP today.

**The agent may propose** — that is half the value. Proposals must:
- be anchored to something the engineer already said, never abstract,
- state what they **cost** in plain terms,
- be labeled as suggestions the engineer can drop without explanation.

**The agent may also push back.** "You described two products there — an invoice tool and a time tracker. Building both doubles the work and neither ships sooner. Which one is the real one?" Conflict named early is scope saved later.

When a round's answer drifts vague ("everyone", "it's just nice to have"), ask the question again with two concrete framings to pick between. Never accept a vague answer into the PRD — a vague line in the PRD becomes an invented feature in the build.

## Step 2: Scope analysis — serious or MVP

Summarize what the exploring rounds produced, then give the scope verdict as an analysis, not a guess:

- **Serious** — there are users who will rely on it, data that must survive, or money/uptime involved. Named consequences: auth that matters, backups, error handling a user will actually see.
- **MVP / trial** — the goal is to learn whether the idea holds. Skipping the production-grade pieces is **the correct call here, not a shortcut** — but say which ones are being skipped, so nobody is surprised when they are missing.

This verdict maps onto sdd's tier choice, and stating the evidence for it is the whole point: the engineer decides the tier with the tradeoff visible. See the handoff rule below — this skill never picks.

## Step 3: Write `docs/prd.md`

One file, this shape. Every heading plain; every line something the engineer said or approved in the rounds.

```markdown
# <product name>

## The problem
Who has it, in plain words. One paragraph.

## The people
The named user, what they do today, what is broken for them.

## The product in plain words
What it does. No architecture, no stack. A layperson who reads this can explain it back.

## What's in it
The capabilities, as a list the engineer can check. Mark the MVP seed from question 4.

## What's deliberately out
Everything decided not to build, with the one-line why. This section is what keeps the build honest.

## Scope verdict
Serious or MVP, and the evidence: which production-grade pieces are in, which are skipped for now.

## Open questions
Anything the rounds could not settle, each with the exact decision that closes it.
```

Write it, show the engineer the file path, and read it back in the reply — not as a summary, as the actual contents, so the engineer approves **the document** and not a paraphrase of it. Fix anything they mark. Do not write a second document; the PRD is the artifact.

## Step 4: Handoff to `/selcy-sdd`

After the engineer approves the document, state the tier **recommendation** and the exact command — then stop, and let the engineer run it:

```
PRD ready: docs/prd.md

Scope: MVP — the data is a single user's, nothing money-moving yet.
Recommendation: /selcy-sdd lite — same bundle, shorter interview.

Next step ( you pick, this is your call ):
  • /selcy-sdd lite
  • /selcy-sdd
```

**Never pick the tier.** `/selcy-sdd`'s own rule is absolute on this: tier detection is never automatic, the engineer names it. This skill recommends with the evidence, the engineer decides with the command. Do not run `/selcy-sdd` yourself, from this skill or from a spawned session — authoring the bundle is the engineer's door to open, same rule the orchestrator follows.

If `docs/prd.md` already exists from an earlier brainstorm, read it first and say so. Overwriting it without asking destroys the previous session's only artifact.

## What this skill never does

- **Never writes under `context/`.** The bundle is `/selcy-sdd`'s. This skill's only artifact is `docs/prd.md`.
- **Never picks the tier**, never runs `/selcy-sdd`, never invokes it via subagent.
- **Never freezes feature numbering or a feature list.** Numbering is sdd's Step 2, and numbering wrong is the expensive failure this skill exists to prevent.
- **Never turns a vague answer into a PRD line.** A line the engineer did not actually say is a feature the build will invent.
- **Never runs when a `context/` bundle exists.** Past this door, the bundle is the source of truth, and a brainstorm that ignores it is the agent authoring the product again.

## Portability

Any Agent Skills client on macOS, Linux, Windows. Shell snippets are POSIX reference. No interactive question picker → ask every round as plain conversation and let the engineer answer in their own words; that is the mode this skill runs in anyway.
