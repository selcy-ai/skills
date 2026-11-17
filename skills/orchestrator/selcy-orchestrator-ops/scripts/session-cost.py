#!/usr/bin/env python3
"""Attribute an opencode project's spend by loop stage.

Read-only query over the opencode session database. Use it before proposing
any structural change to a running loop (drop a stage, defer review to the
end, merge sessions): intuition about which stage is expensive is reliably
wrong, because every stage feels slow while it is the only thing watched.

Usage:
    session-cost.py [project-dir]      # all projects when omitted

Output: per project, session counts and token totals by stage class, plus the
two violations the aggregate hides — one feature costing several build
sessions, and one feature costing several review rounds.

Schema (opencode >= schema with session_v2):
    session_v2: title, directory (the project path), tokens_input,
                tokens_output, tokens_reasoning, tokens_cache_read
    project:    name is NOT reliably populated — group on session_v2.directory
                instead of joining to project.name.
"""

import os
import re
import sqlite3
import sys
from collections import defaultdict

DB = os.path.expanduser("~/.local/share/opencode/opencode.db")


def classify(title):
    t = (title or "").strip().lower()
    if not t:
        return "untitled"
    if "review" in t:
        return "review"
    if t.endswith("-test") or re.search(r"(^|\s|-)test(\s|-|$)", t):
        return "test"
    if (
        t.startswith(("feat-", "bmkg-cp", "ui-change", "cp"))
        or "implement" in t
        or "build" in t
    ):
        return "build"
    if any(k in t for k in ("probe", "smoke", "greeting", "say ok", "quick")):
        return "probe"
    return "other"


# -r2, -v4, -build3, -review-r2, -test-r1 — the sibling-session suffixes a
# feature accumulates when the one-build-session rule keeps breaking.
SIBLING = re.compile(r"(-r\d+)?(-v\d+)?(-build\d+)?(-review(-r\d+)?)?(-test(-r\d+)?)?$")


def base_name(title):
    return SIBLING.sub("", (title or "").strip().lower()).rstrip("-")


def main():
    if not os.path.exists(DB):
        sys.exit(f"no opencode database at {DB}")
    want = sys.argv[1] if len(sys.argv) > 1 else None

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        rows = con.execute(
            """
            select coalesce(directory, path), title,
                   tokens_input, tokens_output, tokens_reasoning,
                   tokens_cache_read
            from session_v2
            """
        ).fetchall()
    finally:
        con.close()

    per_proj = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0, 0, 0]))
    for directory, title, ti, to, tr, tc in rows:
        if want and not (directory or "").startswith(want):
            continue
        k = classify(title)
        a = per_proj[directory or "?"][k]
        a[0] += 1
        a[1] += ti or 0
        a[2] += to or 0
        a[3] += tr or 0
        a[4] += tc or 0
        a[5] += (ti or 0) + (to or 0)

    if not per_proj:
        sys.exit(f"no sessions under {want}")

    def fmt(x):
        return f"{x / 1e6:.1f}M" if x >= 1e6 else f"{x / 1e3:.0f}K"

    for directory in sorted(per_proj, key=lambda d: -sum(v[5] for v in per_proj[d].values())):
        classes = per_proj[directory]
        total = sum(v[5] for v in classes.values())
        print(f"\n=== {directory}  ({sum(v[0] for v in classes.values())} sessions, {fmt(total)} in+out)")
        for k in sorted(classes, key=lambda k: -classes[k][5]):
            n, ti, to, tr, tc, tot = classes[k]
            print(f"  {k:9s} n={n:3d}  in={fmt(ti):>7s} out={fmt(to):>6s} reasoning={fmt(tr):>6s} cache={fmt(tc):>7s}  ({tot / (total or 1) * 100:3.0f}% of in+out)")

        # Sibling detection: a feature with several build or review sessions
        # is the one-build-session-per-feature rule breaking.
        titles_by_class = defaultdict(list)
        for directory2, title, *_ in rows:
            if (directory2 or "?") != directory:
                continue
            titles_by_class[classify(title)].append((title or "").strip())
        counts = defaultdict(lambda: defaultdict(int))
        for k, titles in titles_by_class.items():
            for t in titles:
                counts[k][base_name(t)] += 1
        for k in ("build", "review"):
            dupes = {b: c for b, c in counts.get(k, {}).items() if c > 1}
            if dupes:
                worst = sorted(dupes.items(), key=lambda kv: -kv[1])[:5]
                named = ", ".join(f"{b} x{c}" for b, c in worst)
                print(f"  !! repeated {k} sessions for one feature: {named}")


if __name__ == "__main__":
    main()
