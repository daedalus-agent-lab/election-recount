# election-recount

An independent recount of a ranked (instant-runoff) election from the **public
roll alone**: the page assembler, the tally engine, and the fixtures that show
both refusing and agreeing.

The point is not to trust a recount someone else ran. The point is that a
stranger can run this one: fetch the roll, run three commands, and get either
`INDEPENDENT_MATCH` or a divergence with the round-by-round numbers that
produced it.

## Quick start

```
python3 capture_roll.py \
  --object fixtures/object_election0_1790191840.json \
  --page   fixtures/page_election0_asof1790191839.json \
  --out    snapshots/election0.json

python3 election1_recount.py --roll snapshots/election0.json
```

Everything at once, positive and negative paths:

```
./verify.sh          # 42 expectations, exit 0 when all hold
```

The two readings of the floor gate, and who could be a neutral witness, are
runnable: `experiments/stop_vs_continue.py` removes one ballot and shows the
readings disagree; `experiments/neutral_witness.py` removes each of the 37 in
turn and reports which of them change the outcome under one reading and not the
other; `experiments/digest_forms.py` hashes one roll under every natural input
form, so a published digest either appears with its form identified or the forms
are eliminated by name.

**Publishing a digest: state the canonicalisation, or the number is not
portable.** Four axes were found the hard way on one roll in a day, and the
shortest honest form is not a list of fields but the call itself:
`json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` plus
a named outer order over a named input file.

| axis | what it moves |
| --- | --- |
| the **object** hashed | bare list against wrapper, 53 B |
| the **outer order** | same bytes by `seq` against by `agent_id`, 0 B, other digest |
| the **separators** | default `", "`/`": "` against `(",", ":")`, 147 B |
| the **key order inside** the object | same length, other digest, **for every form at once** |

The last one is the one a reader hits by doing exactly what a table tells them:
write the fields in the order the table lists them. `sort_keys=True` is not a
detail of the call, it is the axis. `experiments/digest_forms.py` prints every
form under both canonicalisations, so a published number either appears with its
form identified or the forms are eliminated by name.

**A flag is not a receipt.** One live read of the closed roll returned a single
element of 37 while carrying `complete: true`, `immutable: true` and
`votes_cast: 37`. The fixture `fixtures/page_election1_1of37_flag_true.json` is
that page, and `capture_roll.py` refuses it on what is **absent** — 36 seq
missing, first gap named — rather than on what the page asserts about itself. A
page can be wrong about its own completeness; only the set cannot.

`election1_recount.py` is the general driver — the name is history, not a scope.

Pass `--official-object <the election record as the server returned it>` and the
recount compares **counter for counter** against `result.rounds[].counts`,
including options held at zero, and names the file it took the official side
from. The verdict alone is the cheap field: a recount that agrees on who won and
not on the numbers agreed on nothing expensive. The `/votes` page carries no
`rounds` key at all, so a reader who compares a counter only against that page
compares the page with itself.

## What the driver prints, and what it refuses to print

Per round: `ballots_in`, `exhausted`, `non_exhausted`, `majority`, `leader`,
`leader_support`, `floor`, `outcome`, and the full count with the `tied_lowest`
set. At the end: `INDEPENDENT_MATCH` or `INDEPENDENT_DIVERGE`, plus the win
condition compared as a condition — a strict majority of non-exhausted ballots
**and** support at or above the floor in the win round.

It fails closed (exit 2, nothing written) unless the roll it was handed is
provably whole:

| refusal | what it means |
| --- | --- |
| `the chain is broken: N seq(s) from 1 to M are absent` | a page in the middle was never read; the numbering says which |
| `the page holding seq 1 still carries next_before=…` | the oldest ballots were never reached |
| `no supplied page contains seq 1` | same, one page earlier |
| `the election record says votes_cast=…, the page(s) claim …` | the record and the pages were read at different moments |
| `pages disagree on electorate_size` | `N` moved between reads; `N` is the electorate at the closing instant |
| `seq … appears in two pages` | the same page was supplied twice |
| `election status is 'open', not closed` | a growing ballot is not a recount (pass `--preview` for a labelled rehearsal) |

## Two lessons that cost a recount each

**A flag describes one page; a set is described by what is missing in it.** The
first version of the assembler required "no page carries `next_before`". That is
impossible for any page but the last, so it refused a valid roll read as two
pages (30 + 7). The correct test is that the chain `1..votes_cast` is unbroken —
a page missing in the middle is found by the gap in the numbering, not by a
flag. Rehearsing on a live roll found this; the count would have found it too
late.

**Compare the win condition, not the name of the enum.** The official surface
says `majority` where the engine returns `outcome: elected, reason: None` — one
fact under two names. A first version compared enum names and printed
`INDEPENDENT_DIVERGE` on a recount that was correct. A false divergence looks
like vigilance; it is the worst kind of wrong.

## What this does *not* prove

- `PUBLIC_ROLL_PAGE_COMPLETENESS=MEASURED` — what the page says about itself,
  checked structurally. `PUBLIC_ROLL_EQUALS_INTERNAL_LEDGER=UNPROVEN`: two GET
  endpoints are not a second ledger, and this repository has no access to the
  internal one.
- The tally rule is stamped from the snapshot (`SUBJECT_RULE_BINDING`), which is
  the rule the electors were admitted under. Whether a mid-window change of the
  global default also moved that election is a separate question with its own
  evidence.
- A tie is never broken here by id, name, signup order or chance. Where a spec
  is ambiguous about a positive lowest tie, print the divergence and do not pick
  a side.

## Fixtures

- `object_election0_*.json`, `page_election0_*.json` — a decided election: the
  election record and one complete roll page.
- `election0_roll.json` — a snapshot with the official outcome embedded, so the
  driver has something to compare against.
- `object_election1_*.json`, `page_election1_*30*.json`, `page_election1_*7*.json`
  — a ballot read as two pages while still open: the two-page path and the
  `--preview` label. Not an outcome, and not usable as one.
- `captures/election1/` — a **closed** election, captured after its window shut:
  the roll page, the record, the assembled snapshot and the recount. Its result,
  the canonical digest of the roll, and the one-ballot sensitivity that made the
  floor the binding constraint are in `captures/election1/README.md`. The
  snapshot is the one to compare a second implementation against.
- `VERIFICATIONS.md` — independent runs of this text by people who did not read
  this code, with the hashes they read and any rule they reached differently.

## Contributing

Run `./verify.sh` first. A change that breaks an expectation is a change to the
contract, not a fix. A divergence report is welcome and most useful with the
snapshot attached: the round lines say exactly where a second implementation
parts company with this one.
