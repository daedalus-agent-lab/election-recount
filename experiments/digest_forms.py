#!/usr/bin/env python3
"""Every natural input shape for one roll, hashed, in one table.

A published digest is checkable only when its input form is named, and the
exchange around this roll has now produced several digests that are each correct
under their own recipe and cannot be compared to one another. This prints the
table: for each plausible way of turning the same 37 ballots into bytes, the
length and the sha256. A published number either appears in the table — and then
its form is identified — or it does not, and the report says which forms were
eliminated rather than that the number is wrong.

    python3 experiments/digest_forms.py [--roll <snapshot>] [--target <hex>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ASC = (",", ":")
SORTED = dict(sort_keys=True, separators=ASC)

# The key order inside an object is an axis of its own, and the one a reader
# follows most naturally: write the fields in the order the published table
# lists them. That gives the right length and the wrong digest, for every form,
# because nothing in the table says whether the objects were sorted.
LITERAL = dict(separators=ASC)


def items_from_snapshot(snap: dict) -> list[dict]:
    """The page shape: one entry per ballot with seq, agent_id and ranking.

    The assembled snapshot keeps only bare rankings, so the seq/agent_id pairs
    are rebuilt from the stored page when the snapshot does not carry them.
    """
    page = Path("captures/election1/roll_page_election1_asof1790209816.json")
    if page.exists():
        raw = json.loads(page.read_text(encoding="utf-8"))
        return [{"seq": it["seq"], "agent_id": it["agent_id"], "ranking": it["ranking"]}
                for it in raw["items"]]
    return snap["items"]


def forms(items: list[dict]) -> dict[str, bytes]:
    by_seq = sorted(items, key=lambda x: x["seq"])
    by_agent = sorted(items, key=lambda x: (x["agent_id"], x["seq"]))
    triples = [{"seq": i["seq"], "agent_id": i["agent_id"], "ranking": i["ranking"]}
               for i in by_agent]
    out: dict[str, bytes] = {}

    def dump(name, obj, **kw):
        out[name] = json.dumps(obj, **kw).encode("utf-8")

    dump("items sorted by agent_id, json(sort_keys, \",\", \":\")", triples, **SORTED)
    dump("items sorted by agent_id, json default separators", triples, sort_keys=True)
    dump("items sorted by seq, json(sort_keys, \",\", \":\")",
         [{"seq": i["seq"], "agent_id": i["agent_id"], "ranking": i["ranking"]} for i in by_seq],
         **SORTED)
    dump("items order as read, json(sort_keys, \",\", \":\")", items, **SORTED)
    dump("items sorted by agent_id, json(default separators), ensure_ascii=False",
         triples, sort_keys=True, ensure_ascii=False)
    dump("wrapped {election_id, votes_cast, items}", {
        "election_id": "election:1", "votes_cast": len(items), "items": triples}, **SORTED)

    # The same objects, keys in the order the table writes them, no sort_keys —
    # and no separators sorting either, so this is the row a reader reaches by
    # transcribing the table literally. Reported in full because a whole family
    # failing together, at the right lengths, is what made it look like a
    # disagreement about the ballots rather than about the recipe.
    out["LITERAL KEY ORDER triples by agent_id, tight"] = json.dumps(
        [{"seq": i["seq"], "agent_id": i["agent_id"], "ranking": i["ranking"]}
         for i in by_agent], **LITERAL).encode("utf-8")
    out["LITERAL KEY ORDER wrapped {election_id, items, votes_cast}"] = json.dumps(
        {"election_id": "election:1", "items": triples, "votes_cast": len(items)},
        **LITERAL).encode("utf-8")
    out["LITERAL KEY ORDER triples by seq, tight"] = json.dumps(
        [{"seq": i["seq"], "agent_id": i["agent_id"], "ranking": i["ranking"]}
         for i in by_seq], **LITERAL).encode("utf-8")
    sf = [{"seq": i["seq"], "first": i["ranking"][0] if i["ranking"] else None}
          for i in by_seq]
    out["LITERAL KEY ORDER {seq, first} by seq, default separators"] = json.dumps(
        sf, ensure_ascii=False).encode("utf-8")
    out["LITERAL KEY ORDER {seq, first} by seq, tight"] = json.dumps(
        sf, separators=ASC, ensure_ascii=False).encode("utf-8")
    seen = {i["seq"]: i["agent_id"] for i in items}
    out["LITERAL KEY ORDER {seq, first} by agent_id, default separators"] = json.dumps(
        sorted(sf, key=lambda x: seen[x["seq"]]), ensure_ascii=False).encode("utf-8")

    # Projections onto (seq, first preference), the shape that was published by
    # another seat and not reproduced in four tries there.
    first_by_seq = {}
    for i in by_seq:
        ranking = i["ranking"]
        first_by_seq[str(i["seq"])] = ranking[0] if ranking else None
    dump("dict str(seq) -> first", first_by_seq, **SORTED)
    dump("dict seq -> first (int keys, json makes them strings)", 
         {i["seq"]: (i["ranking"][0] if i["ranking"] else None) for i in by_seq}, **SORTED)
    dump("list of [seq, first]",
         [[i["seq"], i["ranking"][0] if i["ranking"] else None] for i in by_seq], **SORTED)
    dump("list of {seq, first}",
         [{"seq": i["seq"], "first": i["ranking"][0] if i["ranking"] else None} for i in by_seq],
         **SORTED)
    # The same records, the same order, the same fields — and the default
    # separators. This row was missing for a day, and a published number looked
    # unreproducible because of it: the separator is an axis of the recipe, as
    # independent as the object and the order, and it is invisible in every
    # description that does not name it.
    dump("list of {seq, first}, json default separators",
         [{"seq": i["seq"], "first": i["ranking"][0] if i["ranking"] else None} for i in by_seq],
         sort_keys=True, ensure_ascii=False)
    dump("list of {seq, first_choice}",
         [{"seq": i["seq"], "first_choice": i["ranking"][0] if i["ranking"] else None}
          for i in by_seq], **SORTED)

    # Line-oriented shapes: the separators that are usually implied and never written.
    for label, sep, fields in (
        ("lines seq,agent_id,ranking", ",", lambda i: [str(i["seq"]), i["agent_id"], ",".join(i["ranking"])]),
        ("lines seq,first", ",", lambda i: [str(i["seq"]), i["ranking"][0] if i["ranking"] else ""]),
        ("lines seq<TAB>first", "\t", lambda i: [str(i["seq"]), i["ranking"][0] if i["ranking"] else ""]),
        ("lines seq:first", ":", lambda i: [str(i["seq"]), i["ranking"][0] if i["ranking"] else ""]),
    ):
        out[label] = "\n".join(sep.join(fields(i)) for i in by_seq).encode("utf-8")

    out["just the seq numbers, comma joined"] = ",".join(str(i["seq"]) for i in by_seq).encode()
    out["json list of seq numbers"] = json.dumps([i["seq"] for i in by_seq], **SORTED).encode()
    dump("list of {seq, agent_id} (no ranking)", 
         [{"seq": i["seq"], "agent_id": i["agent_id"]} for i in by_seq], **SORTED)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roll", default="captures/election1/election1_roll.json")
    ap.add_argument("--target", default="787b7489b52d9a08",
                    help="a published digest prefix to look for, or '' to list only")
    args = ap.parse_args()

    snap = json.loads(Path(args.roll).read_text(encoding="utf-8"))
    items = items_from_snapshot(snap)
    table = forms(items)

    print(f"{len(items)} ballots; target {args.target or '(none)'}")
    hit = None
    for name, blob in table.items():
        digest = hashlib.sha256(blob).hexdigest()
        star = ""
        if args.target and digest.startswith(args.target):
            star, hit = "  <-- MATCH", name
        print(f"  {len(blob):>6} B  {digest[:16]}  {name}{star}")

    print()
    if args.target and hit:
        print(f"MATCH  the published number is the form: {hit}")
        return 0
    if args.target:
        print(f"NO MATCH  {args.target} is none of these {len(table)} forms. "
              "The number is not wrong: its input form was not published, and the "
              "forms above are eliminated, not the number.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
