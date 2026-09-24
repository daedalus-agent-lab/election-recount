#!/usr/bin/env bash
# One command that shows the recount working and the refusals refusing.
# Usage: ./verify.sh     (exit 0 = every expectation held)
# A clean-room implementation written from SPEC.md alone found the label on
# the zero-drop rule too modest, so this run now asserts the round line too.
set -u
cd "$(dirname "$0")"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

pass=0
fail=0
refusals="$tmp/refusals.txt"
: >"$refusals"

ok() { # ok <name> <exit> <expected exit> <file> <grep>
  local name="$1" rc="$2" want="$3" file="$4" pat="$5"
  if [ "$rc" != "$want" ]; then
    printf 'FAIL %-34s exit %s, expected %s\n' "$name" "$rc" "$want"; sed -n 1,3p "$file"; fail=$((fail+1)); return
  fi
  if ! grep -q "$pat" "$file"; then
    printf 'FAIL %-34s output lacks: %s\n' "$name" "$pat"; sed -n 1,3p "$file"; fail=$((fail+1)); return
  fi
  printf 'ok   %-34s %s\n' "$name" "$(grep -m1 "$pat" "$file" | cut -c1-58)"
  [ "$want" = 2 ] && printf '%s\t%s\n' "$name" "$(head -1 "$file")" >>"$refusals"
  pass=$((pass+1))
}

python3 capture_roll.py \
  --object fixtures/object_election0_1790191840.json \
  --page   fixtures/page_election0_asof1790191839.json \
  --out    "$tmp/e0.json" >"$tmp/1.log" 2>&1
ok "capture election:0 (one page)" $? 0 "$tmp/1.log" "chain 1..23 unbroken"

python3 capture_roll.py \
  --object fixtures/object_election1_1790195441.json \
  --page   fixtures/page_election1_newest30_asof1790195433.json \
  --page   fixtures/page_election1_oldest7_asof1790195441.json \
  --out    "$tmp/e1.json" --preview >"$tmp/2.log" 2>&1
ok "capture election:1 (two pages)" $? 0 "$tmp/2.log" "chain 1..37 unbroken"

python3 election1_recount.py --roll fixtures/election0_roll.json >"$tmp/3.log" 2>&1
ok "recount election:0 vs official" $? 0 "$tmp/3.log" "INDEPENDENT_MATCH"
# The round line must show the whole continuing set, zeros included: the
# engine's first round carries an option at zero, and this run is where the
# zero-drop rule is exercised. Same run, second assertion.
python3 election1_recount.py --roll fixtures/election0_roll.json >"$tmp/3b.log" 2>&1
ok "e0 round 1 shows the zero option" $? 0 "$tmp/3b.log" "zenith-claude': 0"

python3 election1_recount.py --roll "$tmp/e1.json" >"$tmp/4.log" 2>&1
ok "rehearsal says no official" $? 0 "$tmp/4.log" "OFFICIAL        unknown"

python3 capture_roll.py \
  --object fixtures/object_election0_1790191840.json \
  --page   fixtures/page_election0_asof1790191839.json \
  --out    "$tmp/e0b.json" >"$tmp/13.log" 2>&1
ok "canonical digest of the e0 roll" $? 0 "$tmp/13.log" "0e883a83512c200e"

# Two digests over one file, and the input named. The bare list and the wrapped
# object are different inputs, and the recipe line alone never said which one
# was hashed: a reader who canonicalised the list got 11,650 B where this
# program printed 11,703 B. Both numbers are now pinned, the bare one against a
# number produced independently by another implementation from the same file.
python3 capture_roll.py \
  --object captures/election1/object_election1_1790209805.json \
  --page   captures/election1/roll_page_election1_asof1790209816.json \
  --out    "$tmp/e1c.json" >"$tmp/15.log" 2>&1
ok "wrapped digest of the closed e1 roll" $? 0 "$tmp/15.log" "20e87997a2c7c1b77375d4836a545f6d6fa48e0dbc0fcc80b1ab2b333716ad4c"
# This number is not this repository's: it was published by a second
# implementation on the same file. Pinning it means a silent change to the bare
# canonicaliser fails the run instead of quietly redefining the comparison.
python3 capture_roll.py \
  --object captures/election1/object_election1_1790209805.json \
  --page   captures/election1/roll_page_election1_asof1790209816.json \
  --out    "$tmp/e1c.json" >"$tmp/16.log" 2>&1
ok "bare digest matches the other seat" $? 0 "$tmp/16.log" "daa5b71ef83b09892605d6284b1a2883ca1b880bc0991f026ec9d04f0783e5a9"
python3 capture_roll.py \
  --object captures/election1/object_election1_1790209805.json \
  --page   captures/election1/roll_page_election1_asof1790209816.json \
  --out    "$tmp/e1c.json" >"$tmp/17.log" 2>&1
ok "the digest names its input" $? 0 "$tmp/17.log" "roll_page_election1_asof1790209816.json"
# The snapshot must be reproducible *from the page*, and not only by the code
# that wrote it: the assembly drops agent_id, so the number can never come from
# the snapshot. Checked here so the README cannot drift back.
python3 - <<'PY' >"$tmp/18.log" 2>&1
import json, sys
page = json.load(open("captures/election1/roll_page_election1_asof1790209816.json"))
snap = json.load(open("captures/election1/election1_roll.json"))
if "agent_id" in json.dumps(snap["ballots"][0]):
    sys.exit("FAIL: the snapshot now carries agent_id; update the README")
if "agent_id" not in json.dumps(page["items"][0]):
    sys.exit("FAIL: the page no longer carries agent_id; the digest input changed")
print("the digest comes from the page (%d items with agent_id); the snapshot "
      "carries %d bare rankings and cannot reproduce it"
      % (len(page["items"]), len(snap["ballots"])))
PY
ok "digest rides the page, not the" $? 0 "$tmp/18.log" "cannot reproduce it"

python3 election1_recount.py --roll captures/election1/election1_roll.json >"$tmp/14.log" 2>&1
ok "recount election:1 (closed, captured)" $? 0 "$tmp/14.log" "INDEPENDENT_MATCH"

# Rule 10 is labelled MEASURED: the evidence must be checkable, not asserted.
python3 - <<'PY' >"$tmp/12.log" 2>&1
import json, sys
sys.path.insert(0, ".")
from election1_recount import strict_ballots
from irv_2 import recount
s = json.load(open("fixtures/election0_roll.json"))
cand = [c["id"] for c in s["candidates"]]
zen = "792e7b35-83d7-47de-8fb2-cdf7d789519e"
ranked = sum(1 for r in s["ballots"] if zen in r)
row = recount(s["electorate_size"], cand, strict_ballots(s["ballots"], cand))["rounds"][0]
zeros = [k for k, v in row["counts"].items() if v == 0]
if zen not in zeros:
    sys.exit("FAIL: the first round holds no option at zero, rule 10 is not exercised")
if row["counts"][zen] != 0:
    sys.exit("FAIL: zenith-claude is not at zero in round 1")
print("round 1: %d continuing options, %d at zero; zenith-claude has 0 first "
      "preferences, ranked on %d of %d ballots" % (len(row["counts"]), len(zeros),
                                                   ranked, len(s["ballots"])))
PY
ok "rule 10 has public evidence in R1" $? 0 "$tmp/12.log" "0 first preferences"

# --- refusals: each must exit 2 and say why --------------------------------
python3 - "$tmp" <<'PY'
import json, sys
tmp = sys.argv[1]
obj0 = json.load(open("fixtures/object_election0_1790191840.json"))
json.dump({**obj0, "votes_cast": obj0["votes_cast"] + 1}, open(f"{tmp}/o_bump.json", "w"))
json.dump({**obj0, "status": "open"}, open(f"{tmp}/o_open.json", "w"))
page0 = json.load(open("fixtures/page_election0_asof1790191839.json"))
# consistently bumped page and record: nothing disagrees, but seq 24 was never read
json.dump({**page0, "votes_cast": page0["votes_cast"] + 1}, open(f"{tmp}/p_bump.json", "w"))
obj1 = json.load(open("fixtures/object_election1_1790195441.json"))
json.dump(obj1, open(f"{tmp}/o_e1.json", "w"))
PY

python3 capture_roll.py --object "$tmp/o_bump.json" \
  --page "$tmp/p_bump.json" --out "$tmp/x.json" >"$tmp/5.log" 2>&1
ok "refuse: a seq is missing" $? 2 "$tmp/5.log" "the chain is broken"

python3 capture_roll.py --object "$tmp/o_bump.json" \
  --page fixtures/page_election0_asof1790191839.json --out "$tmp/x.json" >"$tmp/10.log" 2>&1
ok "refuse: record vs page count" $? 2 "$tmp/10.log" "read at another moment"

python3 capture_roll.py --object "$tmp/o_open.json" \
  --page fixtures/page_election0_asof1790191839.json --out "$tmp/x.json" >"$tmp/6.log" 2>&1
ok "refuse: election still open" $? 2 "$tmp/6.log" "not closed"

python3 capture_roll.py --object "$tmp/o_e1.json" \
  --page fixtures/page_election1_newest30_asof1790195433.json --out "$tmp/x.json" >"$tmp/7.log" 2>&1
ok "refuse: newest page alone" $? 2 "$tmp/7.log" "the chain is broken"

python3 capture_roll.py --object "$tmp/o_e1.json" \
  --page fixtures/page_election1_newest30_asof1790195433.json \
  --page fixtures/page_election1_newest30_asof1790195433.json --out "$tmp/x.json" >"$tmp/8.log" 2>&1
ok "refuse: the same page twice" $? 2 "$tmp/8.log" "appears in two pages"

python3 capture_roll.py --object "$tmp/o_e1.json" \
  --page fixtures/page_election1_oldest7_asof1790195441.json --out "$tmp/x.json" >"$tmp/9.log" 2>&1
ok "refuse: no seq 1 in sight" $? 2 "$tmp/9.log" "the chain is broken"

# A flag is not a receipt. One live read of the closed roll returned a single
# element of 37 while carrying complete: true, immutable: true and votes_cast: 37
# — every flag a reader might gate on said the read was whole. The fixture is that
# page, and the assembler must refuse it on what is *absent* rather than on what is
# asserted: a set of seq, not a self-description.
python3 capture_roll.py --object "$tmp/o_e1.json" \
  --page fixtures/page_election1_1of37_flag_true.json --out "$tmp/x.json" >"$tmp/27.log" 2>&1
kk=$?
ok "refuse: one element, every flag true" $kk 2 "$tmp/27.log" "the chain is broken: 36 seq(s) from 1 to 37 are absent"
ok "and the refusal names the first gap" $kk 2 "$tmp/27.log" "first missing 1"
# The same page with the flag set the other way is refused by the older check, so
# the two gates cover each other rather than one carrying the case alone.
python3 - "$tmp/liar.json" <<'PY'
import json, sys
p = json.load(open("fixtures/page_election1_1of37_flag_true.json"))
p["complete"] = False
json.dump(p, open(sys.argv[1], "w"))
PY
python3 capture_roll.py --object "$tmp/o_e1.json" \
  --page "$tmp/liar.json" --out "$tmp/x.json" >"$tmp/28.log" 2>&1
ok "one element, flag false: still refused" $? 2 "$tmp/28.log" "the chain is broken"

# The counted election cannot show where the floor gate sits: it was decided with
# support exactly equal to F. A perturbed roll can, and the two readings split.
python3 experiments/stop_vs_continue.py >"$tmp/19.log" 2>&1
rc=$?
ok "perturbed roll: control matches" $rc 0 "$tmp/19.log" "rounds=1"
ok "perturbed roll: stop voids it" $rc 0 "$tmp/19.log" "reason=floor_not_met"
ok "perturbed roll: continue elects" $rc 0 "$tmp/19.log" "rounds=3"
ok "perturbed roll: readings diverge" $rc 0 "$tmp/19.log" "DIVERGENCE"

# A published digest is checkable only when its input form is named. This table
# hashes the same ballots under every natural shape, so a published number either
# appears with its form identified, or the forms are eliminated by name.
python3 experiments/digest_forms.py >"$tmp/20.log" 2>&1
rc=$?
ok "digest forms: bare by agent_id" $rc 0 "$tmp/20.log" "daa5b71ef83b0989"
ok "digest forms: same bytes, by seq" $rc 0 "$tmp/20.log" "2bffb5deea0fe7a8"
ok "digest forms: a second seat's eliminated form" $rc 0 "$tmp/20.log" "048a390239736275"
# The pair that took a day to close: same records, same order, same fields, and
# only the separators differ. One axis, two numbers, both published.
python3 experiments/digest_forms.py --target 787b7489b52d9a08 >"$tmp/21.log" 2>&1
ok "digest forms: default separators" $? 0 "$tmp/21.log" "787b7489b52d9a08"
python3 experiments/digest_forms.py --target daa5b71ef83b0989 >"$tmp/22.log" 2>&1
ok "digest forms: a lookup can succeed" $? 0 "$tmp/22.log" "MATCH  the published number is the form"
python3 experiments/digest_forms.py --target deadbeefdeadbeef >"$tmp/23.log" 2>&1
ok "digest forms: an unnamed form stays unnamed" $? 0 "$tmp/23.log" "NO MATCH"
# The key order inside the object: right length, wrong digest, for every form at
# once. A whole family failing together at the correct byte counts is what makes
# this look like a disagreement about the ballots instead of about the recipe.
python3 experiments/digest_forms.py --target 7405a842ba43c593 >"$tmp/29.log" 2>&1
ok "digest forms: literal key order placed" $? 0 "$tmp/29.log" "LITERAL KEY ORDER"
python3 experiments/digest_forms.py --target ddab0e801ad481a1 >"$tmp/30.log" 2>&1
ok "digest forms: its wrapped sibling too" $? 0 "$tmp/30.log" "LITERAL KEY ORDER wrapped"
python3 experiments/digest_forms.py --target 0de75664aaa2d270 >"$tmp/31.log" 2>&1
ok "digest forms: literal order, default seps" $? 0 "$tmp/31.log" "LITERAL KEY ORDER {seq, first}"

# The key order is the wire order, and the length column is not a gate that can
# certify a comparison. Hashing the elements as they are emitted (five keys
# instead of three) moves the length to 13,285 B -- and twelve natural calls on
# those same five-key elements all give 13,285 B with eight different digests.
# A form that passes the length gate is not thereby the same call, so "print the
# length, compare only on a match" is a detector of the object, not of the call.
python3 experiments/wire_family.py >"$tmp/32.log" 2>&1
rc=$?
ok "wire family: the published 13285 number" $rc 0 "$tmp/32.log" "MATCH  1e314e3ccf16f414 is 13285 B"
ok "wire family: twelve forms, one length" $rc 0 "$tmp/32.log" "forms 12   distinct lengths 1"
ok "wire family: the length gate collapses" $rc 0 "$tmp/32.log" "collapses 7 of 8 distinct calls"
python3 experiments/wire_family.py --target deadbeefdeadbeef >"$tmp/33.log" 2>&1
ok "wire family: an unnamed call stays unnamed" $? 0 "$tmp/33.log" "NO MATCH"
# Whether two of the named orders are the *same* order is a property of the roll,
# not of the list of names: on this roll the timestamps follow the sequence, so
# "by seq" and "by cast_at" are one order wearing two names, and the digest count
# must not be read as a property of the recipe. Rotating the timestamps breaks
# the coincidence and the same twelve forms give ten numbers instead of eight.
ok "wire family: the orders coincide and say so" $? 0 "$tmp/32.log" "one order, two names: as emitted (newest first) == by seq, reversed; by seq == by cast_at"
ok "wire family: the count belongs to the roll" $? 0 "$tmp/32.log" "over 4 distinct outer order(s)"
ok "wire family: the comma string leaks too" $? 0 "$tmp/32.log" "403be04ad343e00c"
python3 experiments/wire_family.py --shuffle-cast-at >"$tmp/36.log" 2>&1
rc=$?
ok "wire family: rotating timestamps breaks it" $rc 0 "$tmp/36.log" "now 5 distinct orders"
ok "wire family: same forms, ten numbers" $rc 0 "$tmp/36.log" "distinct digests 10"
# Where the order comes from, and what the wrapper's rename is worth. The wire
# element carries five keys and no "first": that key is derived, ranking[0], and
# a recipe that names it names something the page never sent.
python3 - <<'PY' >"$tmp/34.log" 2>&1
import json, hashlib, sys
page = json.load(open("captures/election1/roll_page_election1_asof1790209816.json"))
el, it = page["items"][0], page["items"]
wire = list(el.keys())
if wire != ["seq", "agent_id", "name", "ranking", "cast_at"]:
    sys.exit(f"FAIL: the element key order moved: {wire}")
if "first" in json.dumps(el):
    sys.exit("FAIL: the page now sends 'first'; the derived-key note is stale")
def n(o):
    return len(json.dumps(o, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode())
tri = [{"seq": e["seq"], "agent_id": e["agent_id"], "ranking": e["ranking"]}
       for e in sorted(it, key=lambda e: e["agent_id"])]
a, b = n({"election_id": page["ballot_id"], "items": tri, "votes_cast": page["votes_cast"]}), \
       n({"ballot_id": page["ballot_id"], "items": tri, "votes_cast": page["votes_cast"]})
if a - b != 2:
    sys.exit(f"FAIL: the rename is worth {a - b} B, not 2")
print("wire element keys:", " ".join(wire), "| no 'first' on the wire (derived)")
print(f"the wrapper's rename ballot_id -> election_id is worth {a - b} B ({b} -> {a})")
PY
ok "the wire order and a rename" $? 0 "$tmp/34.log" "no 'first' on the wire"

# Coverage in the other direction: instead of meeting each shape by accident,
# produce every self-consistent lie the real page pair can tell and see which
# gate fires. A shape that passes while the record stays authentic is a missing
# gate, and two of them were -- N was never witnessed by the record, and a
# ranking could name an account that was never on the ballot.
python3 experiments/lie_shapes.py >"$tmp/35.log" 2>&1
rc=$?
ok "lie shapes: the coverage table runs" $rc 0 "$tmp/35.log" "shapes 15   refused 12   uncovered 3"
ok "lie shapes: N is witnessed by the record" $rc 0 "$tmp/35.log" "the election record says electorate_size=67"
ok "lie shapes: a ranking off the ballot is refused" $rc 0 "$tmp/35.log" "neither a frozen candidate"
ok "lie shapes: a repeated option is refused" $rc 0 "$tmp/35.log" "ranks 'vacancy' twice"
ok "lie shapes: a candidate's name is checked" $rc 0 "$tmp/35.log" "the record names"
ok "lie shapes: the remaining gap is named" $rc 0 "$tmp/35.log" "no local witness is left alive"
ok "lie shapes: an unverifiable name is listed" $rc 0 "$tmp/35.log" "the record is authentic: a gate is missing here"

# Who could be a neutral witness, defined by the roll instead of argued about: a
# ballot distinguishes the two readings exactly when its first preference is the
# winner, and the sixteen that do not are the witnesses this roll can offer.
# The official counters, compared counter for counter against the record the
# server returned — not against the snapshot, which carries only the verdict.
python3 election1_recount.py --roll captures/election1/election1_roll.json \
  --official-object captures/election1/object_election1_1790209805.json >"$tmp/25.log" 2>&1
rc=$?
ok "counters compared, not just the verdict" $rc 0 "$tmp/25.log" "rounds\[\]\.counts (1 round(s), 8 options incl. zeros)"
ok "the comparison is still a match" $rc 0 "$tmp/25.log" "INDEPENDENT_MATCH"
# And the comparison is live: one wrong counter has to fail it, by name.
python3 - "$tmp/bent.json" <<'PY'
import json, sys
rec = json.load(open("captures/election1/object_election1_1790209805.json"))
counts = rec["result"]["rounds"][0]["counts"]
key = next(k for k, v in counts.items() if v == 7)
counts[key] = 8
json.dump(rec, open(sys.argv[1], "w"))
PY
python3 election1_recount.py --roll captures/election1/election1_roll.json \
  --official-object "$tmp/bent.json" >"$tmp/26.log" 2>&1
ok "one bent counter diverges by name" $? 0 "$tmp/26.log" "INDEPENDENT_DIVERGE"
ok "and the diverging key is named" $? 0 "$tmp/26.log" "v2bot-agent: official 8 vs recount 7"

python3 experiments/neutral_witness.py >"$tmp/24.log" 2>&1
rc=$?
ok "neutral witness: 21 distinguish" $rc 0 "$tmp/24.log" "distinguishing ballots: 21 of 37"
ok "neutral witness: 16 do not" $rc 0 "$tmp/24.log" "indistinguishable    : 16 of 37"
ok "neutral witness: classes coincide" $rc 0 "$tmp/24.log" "EQUIVALENCE"
ok "neutral witness: no leak" $rc 0 "$tmp/24.log" "distinguishing AND not winner-first: 0"

printf '\n%d ok, %d failed\n' "$pass" "$fail"
if [ -s "$refusals" ]; then
  {
    printf '%s\n' "# Refusals, as this run produced them"
    printf '%s\n' "#"
    printf '%s\n' "# The successes above are portable as a claim; these lines are portable as"
    printf '%s\n' "# data. A consumer that keeps INDEPENDENT_MATCH and drops these keeps the"
    printf '%s\n' "# product and loses the procedure. Regenerate with ./verify.sh"
    printf '\n'
    cat "$refusals"
  } >refusals.txt
  printf 'wrote refusals.txt (%s lines)\n' "$(wc -l <"$refusals")"
fi
[ "$fail" = 0 ]
