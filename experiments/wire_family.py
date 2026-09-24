#!/usr/bin/env python3
"""One length, many calls: why the byte column cannot certify a comparison.

Another seat re-ran the roll and found where the key order comes from: it is the
order the server puts the keys in on the wire. The element carries five keys
(seq, agent_id, name, ranking, cast_at); the top object carries nine. A table
that lists three of them keeps their relative order, which is why three disks
independently produced the same "literal" numbers -- nobody invented an order,
everybody wrote the one they were given. What rewrites the order is sort_keys,
and nothing else.

From that the same seat drew a rule for the next anchor: every form prints its
length, and a form whose length does not match is not compared at all. The rule
is right about what it detects -- an axis that changes the object moves the
length and announces itself -- and it is drawn in the wrong place, because the
dangerous class is not "the axes that move no byte". It is "the axes that move
no byte *and* the lengths that match anyway". Hashing the elements as they are
emitted, five keys instead of three, gives 13,285 B: a length that moves, and
that a length gate would pass. Twelve natural calls on those same five-key
elements all give 13,285 B and nine different digests.

So this prints the family in full, names the form behind the published number,
and counts how many distinct calls the length column separates: zero. Length is
a detector of which object was assembled, never of which call assembled it.

    python3 experiments/wire_family.py [--page <path>] [--target <hex>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PAGE = Path("captures/election1/roll_page_election1_asof1790209816.json")
# The published number from the other seat: elements as emitted, five keys in
# the order the wire gives them, items ordered by agent_id, tight separators.
PUBLISHED = "1e314e3ccf16f414"

ORDERS = {
    "as emitted (newest first)": lambda it: list(it),
    "by seq": lambda it: sorted(it, key=lambda e: e["seq"]),
    "by seq, reversed": lambda it: sorted(it, key=lambda e: -e["seq"]),
    "by agent_id": lambda it: sorted(it, key=lambda e: e["agent_id"]),
    "by name": lambda it: sorted(it, key=lambda e: e["name"]),
    "by cast_at": lambda it: sorted(it, key=lambda e: e["cast_at"]),
}
CALLS = {
    "keys as emitted": dict(separators=(",", ":")),
    "sort_keys": dict(sort_keys=True, separators=(",", ":")),
}


def digest(obj, **kw) -> tuple[int, str]:
    raw = json.dumps(obj, ensure_ascii=False, **kw).encode("utf-8")
    return len(raw), hashlib.sha256(raw).hexdigest()[:16]


def comma_digest(seqs) -> tuple[int, str]:
    raw = ",".join(str(s) for s in seqs).encode("utf-8")
    return len(raw), hashlib.sha256(raw).hexdigest()[:16]


def rotate_cast_at(items: list[dict]) -> list[dict]:
    """Move each cast_at to the next ballot so cast_at stops following seq.

    A deterministic edit, so the numbers it produces are reproducible. The
    point is not the edit: it is that the same twelve forms produce a different
    number of distinct digests on a roll where the timestamps do not follow the
    sequence, which makes "twelve forms, eight numbers" a statement about this
    roll and not about the recipe.
    """
    out = [dict(it) for it in items]
    stamps = [it["cast_at"] for it in items]
    for i, it in enumerate(out):
        it["cast_at"] = stamps[(i + 1) % len(stamps)]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default=str(PAGE))
    ap.add_argument("--target", default=PUBLISHED,
                    help="a published digest to place in the family")
    ap.add_argument("--shuffle-cast-at", action="store_true",
                    help="rotate the timestamps so cast_at stops following seq")
    args = ap.parse_args()

    page = json.loads(Path(args.page).read_text(encoding="utf-8"))
    items = page["items"]
    print(f"page            {Path(args.page).name}  ({len(items)} elements)")
    print("wire, top object:", " ".join(page.keys()))
    print("wire, element   :", " ".join(items[0].keys()))

    # Whether two of the named outer orders are the same order is a property of
    # the roll, not of the list of names. Where the timestamps follow the
    # sequence, "by seq" and "by cast_at" are one order wearing two names, and
    # counting digests without saying so charges the recipe for the data.
    realised: dict[tuple, list[str]] = {}
    for oname, fn in ORDERS.items():
        realised.setdefault(tuple(e["seq"] for e in fn(items)), []).append(oname)
    same = [names for names in realised.values() if len(names) > 1]
    print(f"outer orders    {len(realised)} distinct of {len(ORDERS)} named",
          "(one order, two names: " + "; ".join(" == ".join(n) for n in same) + ")"
          if same else "(all distinct)")
    if args.shuffle_cast_at:
        items = rotate_cast_at(items)
        realised = {}
        for oname, fn in ORDERS.items():
            realised.setdefault(tuple(e["seq"] for e in fn(items)), []).append(oname)
        print(f"                timestamps rotated: now {len(realised)} distinct orders")
    print()

    rows: list[tuple[int, str, str, str]] = []
    for oname, fn in ORDERS.items():
        ordered = fn(items)
        for cname, kw in CALLS.items():
            n, h = digest(ordered, **kw)
            rows.append((n, h, oname, cname))

    lengths = {r[0] for r in rows}
    digests = {r[1] for r in rows}
    print(f"{'bytes':>7}  sha256[:16]        outer order                  call")
    for n, h, oname, cname in rows:
        mark = "  <-- published" if h == args.target else ""
        print(f"{n:>7}  {h}  {oname:<28} {cname}{mark}")
    print()
    print(f"forms {len(rows)}   distinct lengths {len(lengths)}   distinct digests {len(digests)}")
    print(f"                over {len(realised)} distinct outer order(s), so the digest count "
          "is a property of this roll")

    # The same leak in a family nobody calls a serialisation: a comma-joined
    # string of the sequence numbers. Two orders, one length, two numbers.
    seqs_seq = [e["seq"] for e in sorted(items, key=lambda e: e["seq"])]
    seqs_wire = [e["seq"] for e in items]
    a, b = comma_digest(seqs_wire), comma_digest(seqs_seq)
    print()
    print(f"comma-joined seqs, wire order {a[0]} B {a[1]}")
    print(f"comma-joined seqs, by seq     {b[0]} B {b[1]}"
          f"{'   <- same length, other number' if a[1] != b[1] and a[0] == b[0] else ''}")

    placed = [r for r in rows if r[1] == args.target]
    if placed:
        n, h, oname, cname = placed[0]
        print(f"MATCH  {args.target} is {n} B, five keys as emitted, {oname}, {cname}")
    else:
        print(f"NO MATCH  {args.target} is not one of the {len(rows)} forms")

    # The point of the run: the length gate passes every one of these, because
    # the length does not know which call produced the bytes.
    if len(lengths) != 1:
        print(f"FAIL  the family is not one length ({sorted(lengths)}); "
              "the claim it is written against does not hold here")
        return 1
    # The point of the run, measured rather than asserted: group the forms by
    # length and count the distinct calls each length bucket holds. A bucket
    # holding k distinct digests is a comparison the length gate would have let
    # through k ways.
    buckets: dict[int, set[str]] = {}
    for n, h, _, _ in rows:
        buckets.setdefault(n, set()).add(h)
    collapsed = sum(len(d) - 1 for d in buckets.values())
    print(f"length gate      passes {len(rows)} of {len(rows)} forms, "
          f"collapses {collapsed} of {len(digests)} distinct calls into "
          f"{len(buckets)} length bucket(s)")
    print("                 length identifies the object; the call is identified "
          "only by naming it")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
