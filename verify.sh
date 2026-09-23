#!/usr/bin/env bash
# One command that shows the recount working and the refusals refusing.
# Usage: ./verify.sh     (exit 0 = every expectation held)
set -u
cd "$(dirname "$0")"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

pass=0
fail=0

ok() { # ok <name> <exit> <expected exit> <file> <grep>
  local name="$1" rc="$2" want="$3" file="$4" pat="$5"
  if [ "$rc" != "$want" ]; then
    printf 'FAIL %-34s exit %s, expected %s\n' "$name" "$rc" "$want"; sed -n 1,3p "$file"; fail=$((fail+1)); return
  fi
  if ! grep -q "$pat" "$file"; then
    printf 'FAIL %-34s output lacks: %s\n' "$name" "$pat"; sed -n 1,3p "$file"; fail=$((fail+1)); return
  fi
  printf 'ok   %-34s %s\n' "$name" "$(grep -m1 "$pat" "$file" | cut -c1-58)"
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

python3 election1_recount.py --roll "$tmp/e1.json" >"$tmp/4.log" 2>&1
ok "rehearsal says no official" $? 0 "$tmp/4.log" "OFFICIAL        unknown"

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
[ "$fail" = 0 ]
