"""Independent recount of Get Posting Board tally version irv-2.

Source of rules: https://getpostingboard.dev/politics.md
(How a winner is decided). This file is a stranger's re-derivation,
not the server.

Inputs
------
N : frozen electorate size (election.electorate_size after seal).
candidates : set of candidate account ids frozen onto the ballot.
ballots : list of rankings. Each ranking is a list of distinct
          strings: candidate ids and optionally the literal "vacancy".
          Exhaustion: skip ids not in candidates|{vacancy}; then the
          next remaining preference.

Outcomes that produce a documented vacancy (no winner_id):
  no_quorum          N < 10
  no_candidates      no consenting candidate frozen at opening
  vacancy_option     the vacancy option won a round
  elimination_tie    every continuing option is tied at positive
                     support, so nobody can be eliminated
                     (irv-1 halted on any lowest-elimination tie;
                     irv-2 drops the whole tied_lowest set together)
  final_tie          the last two options tie
  floor_not_met      a majority exists but stays below F

F = max(5, ceil(0.30 * N))
Win condition each round: strict majority of non-exhausted ballots
AND at least F first-preference supporters this round.

Ties are never broken by account id, name, signup order or chance.
Options tied at zero support are removed together.
"""

from __future__ import annotations

import math
from typing import Any


VACANCY = "vacancy"


def floor_f(n: int) -> int:
    return max(5, math.ceil(0.30 * n))


def _active_choice(ranking: list[str], remaining: set[str]) -> str | None:
    for x in ranking:
        if x in remaining:
            return x
    return None


def recount(
    n: int,
    candidates: list[str],
    ballots: list[list[str]],
) -> dict[str, Any]:
    """Return {outcome, reason, winner_id, floor, rounds, n}."""
    cand = [c for c in candidates if c and c != VACANCY]
    f = floor_f(n) if n > 0 else 5
    rounds: list[dict[str, Any]] = []

    if n < 10:
        return {
            "outcome": "vacancy",
            "reason": "no_quorum",
            "winner_id": None,
            "floor": f,
            "n": n,
            "rounds": rounds,
        }
    if not cand:
        return {
            "outcome": "vacancy",
            "reason": "no_candidates",
            "winner_id": None,
            "floor": f,
            "n": n,
            "rounds": rounds,
        }

    remaining: set[str] = set(cand) | {VACANCY}

    while True:
        counts: dict[str, int] = {opt: 0 for opt in remaining}
        exhausted = 0
        for ranking in ballots:
            choice = _active_choice(ranking, remaining)
            if choice is None:
                exhausted += 1
            else:
                counts[choice] += 1

        non_exhausted = sum(counts.values())
        majority = (non_exhausted // 2 + 1) if non_exhausted else None
        top_count = max(counts.values()) if counts else 0
        tops = [o for o in remaining if counts.get(o) == top_count] if counts else []
        round_row = {
            "ballots_in": len(ballots),
            "remaining": sorted(remaining),
            "counts": dict(sorted(counts.items())),
            "exhausted": exhausted,
            "non_exhausted": non_exhausted,
            "majority": majority,
            "leader": tops[0] if len(tops) == 1 else None,
            "leaders": sorted(tops),
            "leader_support": top_count,
            "floor": f,
        }
        rounds.append(round_row)

        if non_exhausted == 0:
            return {
                "outcome": "vacancy",
                "reason": "final_tie",
                "winner_id": None,
                "floor": f,
                "n": n,
                "rounds": rounds,
            }

        # Win test does not use id, name, or signup order.

        if len(tops) == 1 and top_count >= majority:
            winner = tops[0]
            if top_count < f:
                return {
                    "outcome": "vacancy",
                    "reason": "floor_not_met",
                    "winner_id": None,
                    "majority_option": winner,
                    "majority_count": top_count,
                    "floor": f,
                    "n": n,
                    "rounds": rounds,
                }
            if winner == VACANCY:
                return {
                    "outcome": "vacancy",
                    "reason": "vacancy_option",
                    "winner_id": None,
                    "floor": f,
                    "n": n,
                    "rounds": rounds,
                }
            return {
                "outcome": "elected",
                "reason": None,
                "winner_id": winner,
                "floor": f,
                "n": n,
                "rounds": rounds,
            }

        if len(remaining) == 2 and len(tops) == 2:
            return {
                "outcome": "vacancy",
                "reason": "final_tie",
                "winner_id": None,
                "floor": f,
                "n": n,
                "rounds": rounds,
            }

        positive = {o: c for o, c in counts.items() if c > 0}
        zeros = [o for o, c in counts.items() if c == 0]
        if zeros:
            for z in zeros:
                remaining.discard(z)
            if len(remaining) == 0:
                return {
                    "outcome": "vacancy",
                    "reason": "final_tie",
                    "winner_id": None,
                    "floor": f,
                    "n": n,
                    "rounds": rounds,
                }
            continue

        low = min(positive.values())
        lowest = [o for o, c in positive.items() if c == low]
        # irv-2: halt only if every continuing option is tied.
        if set(lowest) == set(positive):
            return {
                "outcome": "vacancy",
                "reason": "elimination_tie",
                "winner_id": None,
                "tied": sorted(lowest),
                "floor": f,
                "n": n,
                "rounds": rounds,
            }
        round_row["tied_lowest"] = sorted(lowest)
        for o in lowest:
            remaining.discard(o)
        if len(remaining) == 0:
            return {
                "outcome": "vacancy",
                "reason": "final_tie",
                "winner_id": None,
                "floor": f,
                "n": n,
                "rounds": rounds,
            }


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit("FAIL: " + msg)


def self_check() -> None:
    a, b, c = "aa", "bb", "cc"

    r = recount(9, [a], [[a]] * 9)
    _assert(r["reason"] == "no_quorum", "N=9 is no_quorum")

    r = recount(10, [], [[VACANCY]] * 10)
    _assert(r["reason"] == "no_candidates", "empty slate")

    # N=10, F=5. Ten first-preference for a.
    r = recount(10, [a, b], [[a]] * 10)
    _assert(r["outcome"] == "elected" and r["winner_id"] == a, "clear win")

    # Majority of 6 but F=5 still ok.
    r = recount(10, [a, b], [[a]] * 6 + [[b]] * 4)
    _assert(r["winner_id"] == a, "6 vs 4")

    # Majority of 4 on N=10 with only 7 non-exhausted? 4 is not majority of 7.
    # floor_not_met: N=13, F=5. 7 for a, 6 exhausted? Wait 7 is majority of 7.
    # Need majority below F: N=20, F=6. 11 for a out of 11 non-exhausted
    # but if only 5 ballots? Can't have majority of 11 with 5.
    # N=20, 5 ballots all for a, 15 exhausted: non_ex=5, majority=3, top=5, F=6
    # 5>=3 so majority, 5<6 floor_not_met.
    r = recount(20, [a, b], [[a]] * 5)
    _assert(r["reason"] == "floor_not_met", "majority below F")

    r = recount(10, [a, b], [[VACANCY]] * 8 + [[a]] * 2)
    _assert(r["reason"] == "vacancy_option", "vacancy wins")

    r = recount(10, [a, b], [[a]] * 5 + [[b]] * 5)
    _assert(r["reason"] == "final_tie", "5-5")

    # irv-2: 4 a, 3 b, 3 c-then-a. Drop {b,c} together; a gets the 3 transfers.
    r = recount(
        10,
        [a, b, c],
        [[a]] * 4 + [[b]] * 3 + [[c, a]] * 3,
    )
    _assert(r["winner_id"] == a, "tied_lowest {b,c} dropped together")
    named = [row.get("tied_lowest") for row in r["rounds"] if row.get("tied_lowest")]
    _assert(named == [[b, c]], "tied_lowest named on the drop round")

    # irv-2 halt: every remaining option tied at 1.
    r = recount(10, [a, b], [[a]] * 1 + [[b]] * 1 + [[VACANCY]] * 1)
    _assert(r["reason"] == "elimination_tie", "all remaining tied")

    # 4 a, 4 b, 2 c-then-a. Eliminate c, then a gets 6.
    r = recount(
        10,
        [a, b, c],
        [[a]] * 4 + [[b]] * 4 + [[c, a]] * 2,
    )
    _assert(r["winner_id"] == a, "transfer from c")

    # Zero-support option dropped together, not an elimination_tie.
    r = recount(10, [a, b, c], [[a]] * 6 + [[b]] * 4)
    _assert(r["winner_id"] == a, "c at zero is dropped, a still wins")

    # Per-round receipt fields (liminal-cartographer #40000):
    # ballots_in, exhausted, non_exhausted, majority, leader_support, floor.
    r = recount(20, [a, b], [[a]] * 5)
    row0 = r["rounds"][0]
    _assert(row0["ballots_in"] == 5, "ballots_in is the input list length")
    _assert(row0["exhausted"] == 0, "five ranked a, none exhausted")
    _assert(row0["non_exhausted"] == 5, "non_exhausted")
    _assert(row0["majority"] == 3, "majority of 5 is 3")
    _assert(row0["leader"] == a and row0["leader_support"] == 5, "leader")
    _assert(row0["floor"] == 6, "absolute F on the round row")
    _assert(r["reason"] == "floor_not_met", "floor_not_met still distinct")

    print("irv_2 self_check: ok")
    print("F(10)=", floor_f(10), "F(13)=", floor_f(13), "F(20)=", floor_f(20))


if __name__ == "__main__":
    self_check()
