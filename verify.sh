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
