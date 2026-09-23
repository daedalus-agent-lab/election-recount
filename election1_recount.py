#!/usr/bin/env python3
"""Recount a closed election from a roll snapshot, without editing the script.

The election:0 recount carries its roll inside the file. That is fine once, and
wrong the second time: a recount whose inputs are typed by hand is a recount of
the typist's memory. This driver takes the snapshot instead.

Snapshot (`--roll`, default `election1_roll.json`), written after close from the
public roll page:

    {
      "election_id": "election:1",
      "as_of": 1790208000,
      "complete": true,          # public roll page said complete=true
      "next_before": null,       # and there was no older page left
      "votes_cast": 0,           # and len(items) == votes_cast
      "electorate_size": 0,      # at the closing instant, not at opening
      "tally_version": "irv-2",  # stamped on the live election object
      "official": {"outcome": "", "reason": "", "winner_id": null},   # as the server returned it; empty if unknown
      "candidates": [{"id": "...", "name": "..."}],
      "ballots": [["..."], ["...", "vacancy"]]
    }

It fails closed on the page-completeness evidence: recounting a page that is not
proven complete would turn a partial read into an official-looking number.

    python3 election1_recount.py --roll election1_roll.json
    python3 election1_recount.py --roll election0_roll.json      # re-derivation

Labels, printed for the record:
  PUBLIC_ROLL_PAGE_COMPLETENESS=MEASURED   (from the snapshot's own fields)
  PUBLIC_ROLL_EQUALS_INTERNAL_LEDGER=UNPROVEN
  SUBJECT_RULE_BINDING=<snapshot tally_version>
Nothing here replaces the server's own tally; it is a stranger's re-derivation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from irv_2 import recount

HERE = Path(__file__).resolve().parent


def strict_ballots(rankings, candidates) -> list[list[str]]:
    """Drop ids that are not a frozen candidate and not the vacancy literal."""
    allowed = set(candidates) | {"vacancy"}
    return [[opt for opt in ranking if opt in allowed] for ranking in rankings]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roll", default=str(HERE / "election1_roll.json"))
    ap.add_argument("--strict", action="store_true",
                    help="also drop ballots that ranked a non-candidate (reported)")
    args = ap.parse_args()

    snap = json.loads(Path(args.roll).read_text(encoding="utf-8"))
    ballots = snap["ballots"]
    candidates = [c["id"] for c in snap["candidates"]]
    names = {c["id"]: c.get("name", c["id"][:8]) for c in snap["candidates"]}
    names["vacancy"] = "vacancy"

    print(f"roll            {Path(args.roll).name}")
    print(f"election        {snap['election_id']}")
    print(f"as_of           {snap['as_of']}")
    print(f"page complete   {snap['complete']}  next_before={snap['next_before']!r}")
    print(f"votes_cast      {snap['votes_cast']}  items={len(ballots)}")
    if not snap["complete"] or snap["next_before"] is not None or len(ballots) != snap["votes_cast"]:
        print("REFUSED  the roll page is not proven complete; refusing to recount")
        print("PUBLIC_ROLL_PAGE_COMPLETENESS=NOT_PROVEN")
        return 2
    print("PUBLIC_ROLL_PAGE_COMPLETENESS=MEASURED")
    print("PUBLIC_ROLL_EQUALS_INTERNAL_LEDGER=UNPROVEN")

    n = snap["electorate_size"]
    f = max(5, -(-3 * n // 10)) if n >= 10 else 5
    print(f"N               {n}   (electorate at the closing instant)")
    print(f"F               {f}   max(5, ceil(0.30 * N))")
    print(f"tally_version   {snap['tally_version']}")
    print(f"SUBJECT_RULE_BINDING={snap['tally_version']}")

    extra = [b for b in ballots if any(o not in candidates and o != "vacancy" for o in b)]
    if extra:
        print(f"note            {len(extra)} ballot(s) rank an id that is not a frozen candidate;"
              " irv-2 skips it when exhausted (not an error)")

    result = recount(n, candidates, strict_ballots(ballots, candidates))
    # The official surface says "majority" where the engine's enum says "elected" and
    # leaves `reason` empty: the same fact under two names. So derive the reason from
    # the win condition instead of comparing enum names, which would invent a
    # divergence out of a vocabulary.
    mine_reason = result.get("reason")
    if mine_reason is None and result["outcome"] == "elected" and result["rounds"]:
        last = result["rounds"][-1]
        won_by_majority = (
            last["leader_support"] * 2 > last["non_exhausted"]
            and last["leader_support"] >= last["floor"]
        )
        mine_reason = "majority" if won_by_majority else "outcome_without_majority"
    print(f"outcome         {result['outcome']}  reason={result.get('reason')}"
          f"  win_condition={mine_reason}"
          f"  winner={names.get(result.get('winner_id'), result.get('winner_id'))}")
    for i, row in enumerate(result["rounds"], 1):
        # Print the whole continuing set, zeros included. Filtering zeros out of
        # this line is how a reader of the output (its author) came to believe
        # that no public round ever held an option at zero, while the engine's
        # own round row carried exactly one.
        counts = {names.get(k, k): v for k, v in row["counts"].items()}
        tied = [names.get(x, x) for x in row.get("tied_lowest") or []]
        print(
            f"R{i} ballots_in={row['ballots_in']} exhausted={row['exhausted']} "
            f"non_exh={row['non_exhausted']} majority={row['majority']} "
            f"leader={names.get(row['leader'], row['leader']) if row['leader'] else None} "
            f"leader_support={row['leader_support']} floor={row['floor']} "
            f"counts={counts} tied_lowest={tied}"
        )

    official = snap.get("official") or {}
    if official.get("outcome") or official.get("winner_id") or official.get("reason"):
        # The official surface reports an outcome, a reason and a winner. Compare
        # the fields it actually carries and say which ones were compared: an
        # enum name that differs between the two surfaces is not a divergence.
        same_winner = result.get("winner_id") == official.get("winner_id")
        want_reason = official.get("reason")
        same_reason = not want_reason or want_reason == mine_reason
        print(
            "OFFICIAL        "
            + " ".join(f"{k}={v}" for k, v in official.items() if v not in (None, ""))
        )
        print("COMPARED        winner_id" + (" reason" if want_reason else ""))
        print("INDEPENDENT_MATCH" if (same_winner and same_reason) else "INDEPENDENT_DIVERGE")
    else:
        print("OFFICIAL        unknown — no official outcome in the snapshot")
    print(json.dumps(
        {"outcome": result["outcome"], "reason": result.get("reason"),
         "winner_id": result.get("winner_id"), "n": n, "floor": f},
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
