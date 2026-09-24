#!/usr/bin/env python3
"""One perturbed roll, two readings of a rule the rules never settle.

The counted election:1 was decided in the first round by a support of exactly
F = 21, so it cannot show what the tally does when a leader holds a strict
majority but fewer than F supporters. This script builds a roll where that
happens — one ballot is removed from the published closed roll, the ballot with
the lowest seq whose first preference is the winner — and counts it twice, once
under each reading of where the floor gate sits.

  stop      a majority below the floor ends the count: reason `floor_not_met`
  continue  the majority is not a win and grants no protection, so elimination
            proceeds normally until someone clears the floor or the options run
            out

Neither reading is established by the evidence in this repository. The point of
the experiment is that a sentence absent from both `/politics.md` and the
election contract decides the outcome of a real ballot set, so the `floor_not_met`
branch has a live instance *only* under one of them.

    python3 experiments/stop_vs_continue.py [--roll <snapshot>]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from election1_recount import strict_ballots  # noqa: E402
from irv_2 import recount  # noqa: E402


def show(reading: str, result: dict, ballots_in: int) -> None:
    print(f"--- reading: {reading}")
    for i, row in enumerate(result["rounds"], 1):
        counts = ", ".join(f"{k[:8]}={v}" for k, v in row["counts"].items() if v)
        zeros = [k for k, v in row["counts"].items() if v == 0]
        print(f"  r{i}  non_exhausted={row['non_exhausted']}  majority={row['majority']}  "
              f"floor={row['floor']}  leader={str(row['leader'])[:8]}"
              f" at {row['leader_support']}")
        print(f"      counts {{{counts}}}   zero: {len(zeros)}"
              + (f"   majority_below_floor={str(row['majority_below_floor'])[:8]}"
                 if row.get("majority_below_floor") else ""))
        if row.get("tied_lowest"):
            print(f"      drops {[o[:8] for o in row['tied_lowest']]}")
    verdict = result["outcome"] if result["outcome"] != "elected" else "elected"
    print(f"  -> {verdict}   reason={result['reason']}   "
          f"winner={str(result['winner_id'])[:8]}   rounds={len(result['rounds'])}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roll", default="captures/election1/election1_roll.json")
    args = ap.parse_args()

    snap = json.loads(Path(args.roll).read_text(encoding="utf-8"))
    cands = [c["id"] for c in snap["candidates"]]
    n = snap["electorate_size"]
    winner = snap["official"]["winner_id"]

    # The published roll, recounted, as the control.
    base = recount(n, cands, strict_ballots(snap["ballots"], cands))
    print(f"control: the published closed roll, as it stands")
    show("as published", base, len(snap["ballots"]))
    if base["winner_id"] != winner:
        print("REFUSED  the control does not reproduce the official winner; "
              "the perturbation would prove nothing")
        return 2

    # Remove the lowest-seq ballot whose first preference is the winner. The
    # ballots list is newest-first, so the lowest seq is the last entry.
    def first_pref(ranking):
        return next((x for x in ranking if x in cands), None)

    victim = next((i for i in range(len(snap["ballots"]) - 1, -1, -1)
                   if first_pref(snap["ballots"][i]) == winner), None)
    if victim is None:
        print("REFUSED  no ballot puts the winner first; nothing to remove")
        return 2
    dropped = snap["ballots"][victim]
    ballots = [b for i, b in enumerate(snap["ballots"]) if i != victim]
    seq = len(snap["ballots"]) - victim  # ballots are stored newest-first
    print(f"\nperturbed: ballot with seq {seq} removed "
          f"(first preference = the winner); {len(ballots)} ballots remain, N stays {n}")

    rows = {}
    for reading in ("stop", "continue"):
        r = recount(n, cands, strict_ballots(ballots, cands), floor_gate=reading)
        rows[reading] = r
        print()
        show(reading, r, len(ballots))

    print()
    if {rows["stop"]["reason"], rows["continue"]["reason"]} == {"floor_not_met", None}:
        print("DIVERGENCE  the two readings disagree on this roll: "
              "the rule's placement of the floor gate is the deciding fact, "
              "not the ballots")
    else:
        print("AGREEMENT  the two readings reach the same verdict here, so this "
              "roll does not exercise the difference")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
