#!/usr/bin/env python3
"""Assemble a roll snapshot from raw public-roll pages, or refuse to.

The recount driver (`election1_recount.py`) takes a snapshot; this is the other
half, and it is deliberately the half that does *not* fetch. Fetching is the one
thing only an authenticated caller can do, and it is also the step whose result
must be inspected before it is believed. So the pages arrive as files, exactly as
the API returned them, and everything after that — ordering, pair counting,
completeness, the voting-object stamp — is done here, where it can be checked.

    python3 capture_roll.py --object object_election1.json \
        --page page1.json --page page2.json --out election1_roll.json

Refusals (exit 2), each with the reason printed:
  * the seq chain 1..votes_cast is broken (a page in the middle was never read)
  * the page holding seq 1 still carries next_before, or does not report itself
    complete: the oldest ballots were never reached
  * the pages disagree on votes_cast / electorate_size / ballot_id
  * two items share a seq, or a seq is above votes_cast
  * the election object is not closed and --preview was not asked for: an open
    election's electorate_size is not the governing N, and a mid-window snapshot
    of a ballot that is still growing is not a recount

Note on `complete`: the field is per page and means "this page reached the end".
A page that was cut off by `limit` says false while still being part of an unbroken
chain, so the snapshot's own `complete` is the oldest page's flag, and the raw
flags are kept in `page_flags` — a reader can see which page said what.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def fail(msg: str) -> None:
    print(f"REFUSED  {msg}")
    raise SystemExit(2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--object", required=True, help="read_politics action=election, saved verbatim")
    ap.add_argument("--page", action="append", required=True, help="roll page(s), saved verbatim")
    ap.add_argument("--out", required=True)
    ap.add_argument("--preview", action="store_true",
                    help="allow an election that is still open (writes a preview, never a recount)")
    args = ap.parse_args()

    obj = json.loads(Path(args.object).read_text(encoding="utf-8"))
    pages = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.page]

    ballot = {p["ballot_id"] for p in pages}
    votes_cast = {p["votes_cast"] for p in pages}
    n = {p["electorate_size"] for p in pages}
    if len(ballot) != 1:
        fail(f"pages name different ballots: {sorted(ballot)}")
    if len(votes_cast) != 1:
        fail(f"pages disagree on votes_cast: {sorted(votes_cast)} — the ballot moved between reads")
    if len(n) != 1:
        fail(f"pages disagree on electorate_size: {sorted(n)} — N is not a constant, re-read in one pass")
    # The pages and the election record must tell the same count. A page that
    # undercounts against the record passes every flag check and every gap check
    # (its own claims are internally consistent), so the record is the second
    # witness — after the close nothing moves and the two must agree.
    if "votes_cast" in obj and obj["votes_cast"] not in votes_cast:
        fail(f"the election record says votes_cast={obj['votes_cast']}, the page(s) claim "
             f"{sorted(votes_cast)} — one of them was read at another moment")

    items: dict[int, dict] = {}
    for p in pages:
        for it in p["items"]:
            if it["seq"] in items:
                fail(f"seq {it['seq']} appears in two pages")
            items[it["seq"]] = it

    claimed = votes_cast.pop()
    # The roll is a chain, not one page: the newest page carries next_before, the
    # page that reaches the oldest ballot carries none. So the test is not "no page
    # has next_before" — it is that the chain is unbroken: every seq from 1 to
    # votes_cast is present, and the page holding seq 1 says nothing is older.
    seqs = sorted(items)
    missing = [s for s in range(1, claimed + 1) if s not in items]
    if missing:
        fail(f"the chain is broken: {len(missing)} seq(s) from 1 to {claimed} are absent, "
             f"first missing {missing[0]}")
    if seqs and seqs[-1] > claimed:
        fail(f"a page carries seq {seqs[-1]} above votes_cast={claimed}")
    tail = [p for p in pages if any(it["seq"] == 1 for it in p["items"])]
    if not tail:
        fail("no supplied page contains seq 1: the oldest ballot was never read")
    if any(p.get("next_before") not in (None, 0) for p in tail):
        fail(f"the page holding seq 1 still carries next_before="
             f"{tail[0]['next_before']} — older pages exist and were not supplied")
    if not all(p.get("complete") for p in tail):
        fail("the page holding seq 1 does not report itself complete")

    closed = str(obj.get("status", "")).lower() in {"closed", "decided", "counted", "final"}
    if not closed and not args.preview:
        fail(f"election status is {obj.get('status')!r}, not closed: an open ballot is not a recount. "
             "Pass --preview if this really is a rehearsal.")

    frozen = obj.get("candidates") or []
    if isinstance(frozen, dict):
        frozen = frozen.get("items") or []
    if not obj.get("candidates_complete", True):
        fail("the candidate list is not complete in the supplied object")

    snap = {
        "election_id": obj["id"],
        "as_of": max(p["as_of"] for p in pages),
        "complete": all(p["complete"] for p in tail),
        "page_flags": [p["complete"] for p in pages],
        "next_before": None,
        "votes_cast": claimed,
        "electorate_size": n.pop(),
        "tally_version": obj.get("tally_version"),
        "status": obj.get("status"),
        "preview": bool(not closed),
        "official": {"outcome": obj.get("outcome") or "", "reason": obj.get("reason") or "",
                     "winner_id": obj.get("winner_id")},
        "candidates": [{"id": c["agent_id"], "name": c.get("name")} for c in frozen],
        "ballots": [items[s]["ranking"] for s in sorted(items, reverse=True)],
    }
    Path(args.out).write_text(json.dumps(snap, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")

    # A digest of the roll itself, under a recipe simple enough to repeat: the
    # items as read, reduced to (seq, agent_id, ranking), sorted by agent_id,
    # dumped with sort_keys and separators (",", ":"), UTF-8, sha256.
    # It fingerprints one read at one moment: two captures taken at different
    # as_of values differ for that reason alone and must not be compared as if
    # one of them were wrong.
    canon_items = [
        {"seq": it["seq"], "agent_id": it["agent_id"], "ranking": it["ranking"]}
        for it in items.values()
    ]
    canon_items.sort(key=lambda x: (x["agent_id"], x["seq"]))
    # The read time is deliberately NOT part of the digest. An immutable closed
    # roll read twice at two moments is the same roll, and a digest that moves
    # with the clock fingerprints the reading rather than the thing read: two
    # readers comparing captures would see a difference they cannot act on. The
    # moment is printed beside the digest instead.
    canon = {"election_id": snap["election_id"], "votes_cast": snap["votes_cast"],
             "items": canon_items}
    blob = json.dumps(canon, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")
    print(f"canonical       {len(blob)} B  sha256[:16] {hashlib.sha256(blob).hexdigest()[:16]}"
          "   (the roll's content only: items reduced to seq/agent_id/ranking,"
          " sorted by agent_id, sort_keys, separators (\',\', \':\');"
          " the read time is not part of it — see as_of above)")
    print(f"ballot          {snap['election_id']}   status={snap['status']}"
          f"{'   PREVIEW — not a recount' if snap['preview'] else ''}")
    print(f"as_of           {snap['as_of']}   newest page as_of={snap['as_of']}")
    print(f"votes_cast      {snap['votes_cast']}   items={len(snap['ballots'])}   pages={len(pages)}")
    print(f"electorate_size {snap['electorate_size']}"
          f"{'   NOT the governing N while the window is open' if snap['preview'] else ''}")
    print(f"tally_version   {snap['tally_version']}")
    print(f"candidates      {len(snap['candidates'])}")
    print(f"page complete   {snap['complete']}  chain 1..{claimed} unbroken, "
          f"oldest page next_before=None")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
