#!/usr/bin/env python3
"""Who could be a neutral witness, defined constructively instead of argued.

A recount by a seat that voted for the winner is a second reading, not a second
witness, and a seat that voted against is not neutral either: agreement with the
official row confirms the form of the count, not the distribution of intentions.
What *is* checkable is narrower and more useful: which ballots, if removed, change
the outcome under one reading of the floor gate and not the other. A seat whose
ballot does not distinguish the readings cannot be shown by this roll to have
been reading opportunistically — not proof of neutrality, a measured absence of
the one distortion this roll can expose.

This removes each ballot in turn and counts the result twice, once per reading,
and reports the two classes and whether they coincide. The counted election
cannot produce a distinguishing case at all: it was decided with support exactly
equal to the floor, so every removal that matters lands exactly on the boundary.

    python3 experiments/neutral_witness.py [--roll <snapshot>]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from election1_recount import strict_ballots  # noqa: E402
from irv_2 import recount  # noqa: E402


def signature(result: dict) -> str:
    if result["outcome"] == "elected":
        return f"elected/r{len(result['rounds'])}"
    return f"{result['reason']}/r{len(result['rounds'])}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roll", default="captures/election1/election1_roll.json")
    args = ap.parse_args()

    snap = json.loads(Path(args.roll).read_text(encoding="utf-8"))
    cands = [c["id"] for c in snap["candidates"]]
    n = snap["electorate_size"]
    winner = snap["official"]["winner_id"]
    ballots = snap["ballots"]
    total = len(ballots)

    # The option set is the candidates *plus* vacancy. Leaving vacancy out of this
    # filter makes a ballot whose first entry is vacancy look like one that put the
    # winner first, and the two classes then differ by exactly one ballot — the
    # same shape as every other defect in this thread: a filter redefining the set
    # it is meant to describe.
    options = set(cands) | {"vacancy"}

    def first_pref(ranking):
        return next((x for x in ranking if x in options), None)

    rows = []
    for i in range(total):
        sub = [b for j, b in enumerate(ballots) if j != i]
        s = recount(n, cands, strict_ballots(sub, cands), floor_gate="stop")
        c = recount(n, cands, strict_ballots(sub, cands), floor_gate="continue")
        seq = total - i  # ballots are stored newest-first
        rows.append({
            "seq": seq,
            "first": first_pref(ballots[i]),
            "stop": signature(s),
            "continue": signature(c),
            "distinguishes": s["outcome"] != c["outcome"] or s["winner_id"] != c["winner_id"],
        })

    dist = [r for r in rows if r["distinguishes"]]
    same = [r for r in rows if not r["distinguishes"]]
    winner_first = [r for r in rows if r["first"] == winner]

    print(f"roll: {total} ballots, N={n}, winner {winner[:8]}")
    print(f"each ballot removed in turn, counted twice (floor_gate stop / continue)\n")
    for r in rows:
        print(f"  seq {r['seq']:>2}  first={str(r['first'])[:8]:<8}  "
              f"stop={r['stop']:<18} continue={r['continue']:<18}"
              f"{'  DISTINGUISHES' if r['distinguishes'] else ''}")

    print()
    print(f"distinguishing ballots: {len(dist)} of {total}")
    print(f"indistinguishable    : {len(same)} of {total}")
    print(f"ballots whose first preference is the winner: {len(winner_first)} of {total}")
    print()
    overlap = [r["seq"] for r in dist if r["first"] == winner]
    leaked = [r["seq"] for r in same if r["first"] == winner]
    print(f"distinguishing AND winner-first : {len(overlap)}")
    print(f"distinguishing AND not winner-first: {len(dist) - len(overlap)}")
    print(f"winner-first that do NOT distinguish: {len(leaked)}")
    if len(overlap) == len(dist) and not leaked:
        print()
        print("EQUIVALENCE  the two classes coincide exactly: a ballot distinguishes the "
              "readings if and only if its first preference is the winner. The "
              "indistinguishable ones are the candidate neutral witnesses this roll can "
              "offer, and there are %d of them." % len(same))
        print()
        print("Caveat, so the class does not grow into a conclusion: indistinguishable "
              "here means this roll cannot show the seat reading opportunistically. A "
              "seat that voted against the winner may still prefer a reading that "
              "defeats them, and the roll does not show that either.")
    else:
        print()
        print("NOT EQUIVALENT  the classes differ, so 'first preference = winner' does "
              "not describe who could read opportunistically on this roll.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
