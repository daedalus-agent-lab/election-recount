#!/usr/bin/env python3
"""Which lies does the assembler actually catch, one shape at a time?

The assembler refuses a set of shapes by name, and every one of those refusals
was found by meeting it -- mostly on a real page, once by rehearsing on a live
roll. What was never done is the other direction: take the real page pair and
the real election record, produce each shape of lie a *self-consistent* page can
tell, and see which gate fires and which shape walks through.

A shape here is deliberately internally consistent: it does not contradict
itself, it does not announce that it is partial, and it is not a broken chain on
its face. Those are the ones a reader has to be defended against, because a
reader who checks the page against itself is checking the liar against the liar.

    python3 experiments/lie_shapes.py [--verbose]

Exit 0 when every shape is either refused by a named gate or listed in
UNCOVERED with what it costs. A shape that passes and changes the count is the
interesting one; a shape that passes and changes nothing is named too, because
the number is what a reader acts on.
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
NEWEST = HERE / "fixtures/page_election1_newest30_asof1790195433.json"
OLDEST = HERE / "fixtures/page_election1_oldest7_asof1790195441.json"
OBJECT = HERE / "captures/election1/object_election1_1790209805.json"
DRIVER = HERE / "election1_recount.py"


def load():
    return (json.loads(OBJECT.read_text(encoding="utf-8")),
            json.loads(NEWEST.read_text(encoding="utf-8")),
            json.loads(OLDEST.read_text(encoding="utf-8")))


# ---------------------------------------------------------------- the shapes
# Every mutation is applied to a fresh copy of (object, newest, oldest) and must
# leave the page internally consistent: the flag, the count, the chain and the
# record are made to agree with each other, which is exactly what makes the shape
# hard. A mutation that a reader could spot by reading the page alone is not
# interesting here.

def shape_one_element(obj, new, old):
    """A page that reports itself complete and whole while holding one ballot."""
    new["items"] = new["items"][:1]
    new["complete"] = True
    new["next_before"] = None
    return obj, new, None


def shape_gap_in_the_middle(obj, new, old):
    """One ballot dropped from the middle; every flag left honest."""
    new["items"] = [it for it in new["items"] if it["seq"] != 19]
    return obj, new, old


def shape_drop_the_oldest_page(obj, new, old):
    """The page that reaches seq 1 is simply not supplied."""
    new["next_before"] = None
    new["complete"] = True
    return obj, new, None


def shape_tail_still_has_next_before(obj, new, old):
    """The oldest page admits that older ballots exist and is passed anyway."""
    old["next_before"] = 8
    return obj, new, old


def shape_tail_not_complete(obj, new, old):
    old["complete"] = False
    return obj, new, old


def shape_duplicate_seq_across_pages(obj, new, old):
    """One ballot counted twice, once on each page, everything else agreeing."""
    old["items"] = old["items"] + [copy.deepcopy(new["items"][-1])]
    return obj, new, old


def shape_votes_cast_inflated(obj, new, old):
    """The page agrees with itself on a count one larger than it holds."""
    for p in (new, old):
        p["votes_cast"] = 38
    obj["votes_cast"] = 38
    return obj, new, old


def shape_votes_cast_deflated(obj, new, old):
    for p in (new, old):
        p["votes_cast"] = 36
    obj["votes_cast"] = 36
    new["items"] = [it for it in new["items"] if it["seq"] != 37]
    return obj, new, old


def shape_count_moved_with_its_field_only(obj, new, old):
    """The page and the record's votes_cast moved together; the record's tally did not.

    This is the shape that walked through the previous round's fix: the two
    witnesses named in the code agree with each other, and the disagreement is
    inside the record, between the number it states and the round counts it
    states, which add up to the number it was.
    """
    new["items"] = [it for it in new["items"] if it["seq"] != 37]
    for p in (new, old):
        p["votes_cast"] = 36
    obj["votes_cast"] = 36
    return obj, new, old


def shape_count_moved_in_every_stated_field(obj, new, old):
    """The count moved on the page and in every field where the record states it.

    The only thing left disagreeing is the record's arithmetic: the round counts
    still add up to what the count was, and a sum is not a field anyone moves by
    hand. This is the shape that needs the tally as its witness -- without it,
    nothing here contradicts anything.
    """
    new["items"] = [it for it in new["items"] if it["seq"] != 37]
    for p in (new, old):
        p["votes_cast"] = 36
    obj["votes_cast"] = 36
    for key in ("votes_cast", "ballots_cast"):
        if key in obj["result"]:
            obj["result"][key] = 36
    return obj, new, old


def shape_record_contradicts_itself(obj, new, old):
    """The record states the count one way and again, differently."""
    obj["result"]["votes_cast"] = 36
    return obj, new, old


def shape_record_candidate_count_wrong(obj, new, old):
    """The record says the ballot carried one candidate more than it did."""
    obj["result"]["candidates"] = obj["result"]["candidates"] + 1
    return obj, new, old


def shape_record_disagrees(obj, new, old):
    """The page pair is intact; the election record was read at another moment."""
    obj["votes_cast"] = 36
    return obj, new, old


def shape_electorate_wrong_on_the_page(obj, new, old):
    """N moved on both pages; the record is left exactly as it was published.

    Nothing on the page contradicts anything on the page: the ballot count is
    right, the chain is whole, the flags are honest, and both pages agree with
    each other. Only the number the floor and the strict majority are computed
    from has moved -- so the shape changes who can win while reading as a
    perfectly consistent read.
    """
    for p in (new, old):
        p["electorate_size"] = 40
    return obj, new, old


def shape_electorate_wrong_everywhere(obj, new, old):
    """N moved on the pages and in the record together, so no local witness is left."""
    for p in (new, old):
        p["electorate_size"] = 40
    obj["electorate_size"] = 40
    obj["floor"] = 12
    return obj, new, old


def shape_ranking_option_not_on_the_ballot(obj, new, old):
    """A ballot ranks an account that was never frozen onto the ballot."""
    new["items"][0]["ranking"] = ["deadbeef-0000-4000-8000-000000000000"] + \
        new["items"][0]["ranking"]
    return obj, new, old


def shape_option_repeated(obj, new, old):
    """One option appears twice in one ranking; the best of them is the same."""
    it = new["items"][0]
    it["ranking"] = it["ranking"][:1] + it["ranking"]
    return obj, new, old


def shape_name_swapped(obj, new, old):
    """A voter's displayed name is another voter's; the id is untouched.

    The record never names an ordinary voter, so for this ballot there is no
    witness at all -- the shape is listed with that cost rather than pretended
    away. Compare the next shape, where the record does name the account.
    """
    it = new["items"][0]
    it["name"] = "hermione"
    return obj, new, old


def shape_candidate_name_swapped(obj, new, old):
    """The same swap on an account the record does name, which is checkable."""
    cand = obj["candidates"]
    cand = cand.get("items") if isinstance(cand, dict) else cand
    known = {c["agent_id"] for c in cand}
    for p in (new, old):
        for it in p["items"]:
            if it["agent_id"] in known:
                it["name"] = "not-that-account"
                return obj, new, old
    raise AssertionError("no ballot was cast by a candidate")


# name, mutation, which witnesses the mutation touches ("page" / "page+record")
SHAPES = [
    ("one element, complete true", shape_one_element, "page"),
    ("gap in the middle of the chain", shape_gap_in_the_middle, "page"),
    ("the oldest page not supplied", shape_drop_the_oldest_page, "page"),
    ("oldest page still has next_before", shape_tail_still_has_next_before, "page"),
    ("oldest page complete false", shape_tail_not_complete, "page"),
    ("one ballot on both pages", shape_duplicate_seq_across_pages, "page"),
    ("votes_cast above what is held", shape_votes_cast_inflated, "page+record"),
    ("votes_cast below what is held", shape_votes_cast_deflated, "page+record"),
    ("record read at another moment", shape_record_disagrees, "record"),
    ("count moved with its own field", shape_count_moved_with_its_field_only,
     "page+record field"),
    ("count moved in every stated field", shape_count_moved_in_every_stated_field,
     "page+record"),
    ("the record contradicts itself", shape_record_contradicts_itself, "record"),
    ("the record's candidate count wrong", shape_record_candidate_count_wrong, "record"),
    ("N moved on the page only", shape_electorate_wrong_on_the_page, "page"),
    ("N moved on page and record", shape_electorate_wrong_everywhere, "page+record"),
    ("ranking names a non-candidate", shape_ranking_option_not_on_the_ballot, "page"),
    ("an option repeated in a ranking", shape_option_repeated, "page"),
    ("the voter's name swapped", shape_name_swapped, "page"),
    ("a candidate's name swapped", shape_candidate_name_swapped, "page"),
]


def run_capture(tmp: Path, obj, new, old) -> tuple[int, str]:
    files = {}
    for name, blob in (("obj.json", obj), ("new.json", new), ("old.json", old)):
        p = tmp / name
        p.write_text(json.dumps(blob, indent=1, ensure_ascii=False), encoding="utf-8")
        files[name] = p
    cmd = [sys.executable, str(HERE / "capture_roll.py"), "--object", str(files["obj.json"]),
           "--page", str(files["new.json"]), "--out", str(tmp / "snap.json")]
    if old is not None:
        cmd += ["--page", str(files["old.json"])]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=HERE)
    line = next((l for l in (r.stdout + r.stderr).splitlines() if l.startswith("REFUSED")), "")
    return r.returncode, line[len("REFUSED  "):] if line else ""


def run_driver(tmp: Path, snap: Path) -> str:
    r = subprocess.run([sys.executable, str(DRIVER), "--roll", str(snap)],
                       capture_output=True, text=True, cwd=HERE)
    for line in (r.stdout + r.stderr).splitlines():
        if line.startswith("INDEPENDENT_") or "outcome" in line and "winner" in line:
            return line.strip()
    return (r.stdout + r.stderr).strip().splitlines()[-1] if r.returncode else "?"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    print("gate coverage against the real page pair and the real record")
    print(f"  pages  {NEWEST.name} (30) + {OLDEST.name} (7)   N=67 votes_cast=37")
    print(f"  record {OBJECT.name}")
    print()
    print(f"{'shape':<36} {'touched':<12} {'exit':>4}  gate / outcome")
    print("-" * 110)

    uncovered: list[tuple[str, str, str]] = []
    with tempfile.TemporaryDirectory(dir=str(HERE)) as td:
        tmp = Path(td)
        for name, fn, touched in SHAPES:
            obj, new, old = load()
            obj, new, old = fn(obj, new, old)
            rc, why = run_capture(tmp, obj, new, old)
            if rc == 0:
                verdict = run_driver(tmp, tmp / "snap.json")
                note = f"PASSES — recount says {verdict}"
                uncovered.append((name, verdict, note))
            else:
                verdict = why or "(exit != 0 without a REFUSED line)"
                note = verdict
            print(f"{name:<36} {touched:<12} {rc:>4}  {verdict}")
    print()
    if uncovered:
        print("UNCOVERED — a self-consistent page that no gate stops:")
        for name, verdict, _ in uncovered:
            touched = next(t for n, _, t in SHAPES if n == name)
            note = ("  (the record was mutated too: no local witness is left alive, "
                    "which is what the published digest is for)"
                    if touched == "page+record" else
                    "  (the record is authentic: a gate is missing here)")
            print(f"  * {name:<34} recount: {verdict[:40]}{note}")
        print()
    print(f"shapes {len(SHAPES)}   refused {len(SHAPES) - len(uncovered)}   "
          f"uncovered {len(uncovered)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
