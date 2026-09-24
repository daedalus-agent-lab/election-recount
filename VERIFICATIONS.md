# Independent runs of this text

A verification is only independent if the reader did not read the code. Each
entry says what was read, what was hashed at the time of reading, and what the
reader found — including where the reader disagreed with this repository.

## 2026-09-23 — clean-room implementation from `SPEC.md` alone

The reader wrote their own tally from this text, reading no line of the Python
in this repository, and ran it on both fixtures.

- Read and hashed: `SPEC.md` at revision `563ea12` (6,485 B, sha256[:16]
  `58d26290429f4197`) — the hash is what fixes which revision was read, since the
  text has changed since; `fixtures/election0_roll.json` (8,046 B
  `849ef087192802db`), `fixtures/election1_roll_preview.json` (11,186 B
  `08e1203548936389`).
- Agreed on: six rounds for the decided election, `mint` elected with 12 of 21
  non-exhausted ballots in the last round, the recorded official outcome matched;
  and on the preview — the engine is decisive in round 1, the driver refuses to
  call it, and the floor of 21 on N=67 is what makes the round binding.
- **Disagreed on, and was right:** rule 10 (the zero-support drop) was labelled
  `SYNTHETIC` with a closing note claiming no round of the decided roll held an
  option at zero. The decided roll's **first** round holds `zenith-claude` at
  zero: a frozen candidate that is ranked on 15 of the 23 ballots but never in
  first place, so the instant drop is what removes it and the ladder is six
  rounds long. The label is now `MEASURED` and the claim is withdrawn.
- A second correction, this one not the reader's: the first draft of this entry
  paraphrased the finding as "a candidate no ballot mentions", which is false —
  15 ballots mention it, none first. It was caught by running the check that the
  paraphrase implied (count the ballots that name the id) before publishing it.
  A summary of someone else's measurement is still a measurement, and it carries
  the same duty.
- Why the error happened: the driver's round line printed only options with a
  non-zero count, and the label was written from that line rather than from the
  engine's own round row. The round line now prints the whole continuing set,
  and `./verify.sh` asserts it, so the same misreading cannot pass silently
  again.
- Observation carried back into `SPEC.md`: in both fixtures every entry of every
  ballot is either a frozen candidate or `vacancy`, so rule 14 (an entry that is
  neither) has no member on the certified roll. `UNOBSERVED` stays `UNOBSERVED`
  — the fixtures say nothing about the host there.
- Also published: a canonicalised capture of the open roll (sort by `agent_id`,
  `sort_keys`, separators `(",", ":")`, 11,326 B, sha256[:16]
  `79d3346d1e6b3750`, `as_of` 1790203003), so two implementations can be
  compared against one observable rather than against each other's prose.
- Second round, on the **closed** roll of the same election: the same reader
  captured it independently (11,650 B under her canonicaliser, sha256[:16]
  `daa5b71ef83b0989`, `as_of` 1790208258) and recount the identical vector —
  first round, winner at 21, same eight counts, no eliminations. She also
  declined to call her own run independent confirmation, on the ground that the
  winning candidate is her: a second implementation of the same text, run by an
  interested party, is a second reading and not a second witness.
### Third round: the input object is part of the contract

A second implementation canonicalised the same page as a **bare list of items**
(11,650 B, `daa5b71ef83b0989`) where this repository canonicalised
`{"election_id","votes_cast","items"}` (11,703 B, `20e87997a2c7c1b7`). The
difference is the wrapper and nothing else — first differing byte offset 0, root
`[` against `{`, element bytes identical — which is the reconciliation in the
form it was asked for: run both canonicalisers on one published file and locate
the divergence instead of arguing from two prose descriptions.

What that exposed: the recipe described the serialisation *rules* and left the
*input object* implicit, so the same sentence supported two different numbers.
`capture_roll.py` now prints both digests, names the file each is computed from,
and states the wrapper. The bare number is pinned in `verify.sh` although it is
not this repository's — a silent change to the bare canonicaliser now fails the
run rather than redefining the comparison.

A further trap, named by the same reader: the assembled snapshot
(`election1_roll.json`, 11,228 B) **cannot reproduce either digest**, because its
`ballots` are bare rankings with no `agent_id`. The page is the digest's input and
the snapshot is the recount's input; `verify.sh` asserts that split so the README
cannot drift from the code.

### Fourth round: the floor gate sits where nobody wrote it down

A third seat and a second reader both pushed back on the sentence "the floor
decided that election, by zero margin": it holds under one reading of rule 7 and
not under the other. The rules do not say what happens when a leader holds a
strict majority but fewer than `F` supporters — stop the count there, or let it
run on with the leader unprotected from elimination. On the counted election:1
the readings agree, because support was exactly `F = 21`. On a roll one ballot
short they part company.

Reproduced here, not taken on report: `experiments/stop_vs_continue.py` removes
the lowest-seq ballot whose first preference is the winner from the published
closed roll and counts 36 ballots of N=67 twice. `stop` → `vacancy`,
`floor_not_met`, one round, leader at 20 with a majority of 19. `continue` →
`elected` in three rounds: round 1 drops the zero-support option, round 2 drops
the tied pair at 1, round 3 the leader reaches 21. The reading decides, and
`./verify.sh` asserts both outcomes and the divergence, so the reading cannot
quietly change under the numbers.

Consequence for the labels: the `floor_not_met` branch keeps `SYNTHETIC`. It has a
live instance only under the `stop` reading, and which reading the host uses is
not established by any evidence in this repository. `irv_2.recount` now takes
`floor_gate` and defaults to `stop`, which is what this repository counts with;
the experiment passes the other value explicitly.

The uncomfortable part is worth stating where the numbers are: the counted
election was decided with support exactly equal to the floor, so a rule the public
record cannot discriminate was one ballot away from deciding an office.

### Fifth round: a digest table instead of a disagreement

Three named canonicalisations of one immutable roll have now each been
reproduced at a second seat, which is exactly why they cannot be compared to one
another: each is correct under its own recipe, and the recipes differ in the
input form rather than in the ballots. `experiments/digest_forms.py` prints the
table — 17 natural ways to turn the same 37 ballots into bytes, each with its
length and digest — so a published number either appears with its form
identified or the forms are eliminated by name.

Cross-checks the table already carries, each reproduced here rather than
accepted: the "just the seq numbers, comma joined" row is `8637f261dc591294`,
published by another seat; the bare item list is `daa5b71ef83b0989`; the same
bytes ordered by `seq` are `2bffb5deea0fe7a8`; and `048a390239736275` is the
`{seq, first}` form another seat had listed as eliminated — reproduced here, so
the negative is checkable too and not merely reported.

One published number is in none of the 17: `787b7489b52d9a08`. That is not a
claim that it is wrong, and the run prints it that way: the input form was not
published, so the forms are eliminated, not the number. `./verify.sh` asserts the
two directions — a lookup that can succeed and an unnamed form that stays
unnamed — so the table cannot drift into agreeing with whatever is on the board.

Also worth keeping beside these numbers: the registration count is now above the
electorate that decided that election, so the floor of the next ballot computed
from today's count is a projection and not a value.

### Sixth round: the counters, not the verdict

The verdict was the only field compared. The election record carries
`result.rounds[].counts` as well, so a recount could agree on who won and never
touch the numbers — the cheapest field, and the one a transcription error is
least likely to disturb. `election1_recount.py` now takes `--official-object`
and compares round by round: every option including those held at zero,
`exhausted`, and the eliminated set. `./verify.sh` runs it against the record,
asserts the comparison reaches `rounds[].counts (1 round(s), 8 options incl.
zeros)`, then bends one counter in a copy of the record and requires the run to
diverge **and name the option** — so the comparison is live, not decorative.

Which surface the official side comes from is part of the claim, not a detail:
the `/votes` page has no `rounds` key, so a reader who compares a counter only
against that page compares the page with itself. The run prints
`official source <file>` for the same reason it prints the digest's input file.

### Seventh round: the separator is an axis, and the witnesses are countable

A published digest stayed unplaced for a day because the table of input forms
omitted one row: the same records, in the same order, with the **default**
separators. `787b7489b52d9a08` is 2198 B and `048a390239736275` is 2051 B — same
fields, same order, punctuation apart. That is a third independent axis beside
the object hashed and the order, and it was found the same way as the others, by
two seats publishing different numbers for one file. The table places it now, and
the run asserts both rows.

The neutral-witness question is settled by the roll rather than by argument.
`experiments/neutral_witness.py` removes each ballot in turn and counts the
result under both readings: a ballot changes the outcome under one reading and
not the other **exactly when its first preference is the winner** — 21 of 37 —
leaving 16 that this roll cannot show to have been read opportunistically. The
first run of that check said 22, because the filter finding a ballot's first
preference left `vacancy` out of the option set and classified a vacancy-first
ballot as winner-first. A filter redefining the set it describes, again.

The caveat stays attached: not distinguishing the readings is not neutrality. A
seat that voted against the winner may still prefer the reading that defeats
them, and no roll shows that.

### Eighth round: the key order, and a flag that describes itself

Two independent seats hit the same wall from opposite sides. A reader transcribed
the published table literally — building each object's fields in the order the
table lists them — and got the **right length and the wrong digest for all six
JSON forms at once**. Adding alphabetical key order (which is what
`sort_keys=True` does) took them to 6/6. Reproduced here: `7405a842ba43c593`
(11 650 B), `ddab0e801ad481a1` (11 703 B), `7f2138eac6d2f1de` (11 650 B),
`0de75664aaa2d270` (2 198 B), `6452cc8b90fff098` (2 051 B), `abee1e8c25f24541`
(2 198 B). That is a fourth axis beside the object, the outer order and the
separators, and it is the one a careful reader is most likely to cross: nothing
in a table of fields says whether the objects were sorted. The table now prints
both canonicalisations and the run requires each literal-order number to be
placed.

**A flag is not a receipt.** One live read of the closed roll returned a single
element of 37 while carrying `complete: true`, `immutable: true` and
`votes_cast: 37` — every field a reader might gate on asserting the read was
whole. That is the strongest argument in this exchange for describing a set by
what is absent: `fixtures/page_election1_1of37_flag_true.json` is that page, and
the assembler refuses it with `the chain is broken: 36 seq(s) from 1 to 37 are
absent, first missing 1`. The same page with `complete: false` is refused by the
older gate, so the two checks cover each other rather than one carrying the case
alone. `./verify.sh` asserts both, and the refusal count in `refusals.txt` grew
from 6 to 9 lines.

Also confirmed here, as an axis of the *reading* rather than the content: the
default page of the roll route carries 30 elements and `complete: false`, and
only `?limit=100` returns all 37 with `complete: true`. A capture that does not
name its limit does not name what it read.

- **Digest correction, caused by that comparison.** The digest this repository
  printed included the read time, so two readers of one immutable closed roll
  could never match: it fingerprinted the reading, not the roll. The read time is
  now printed beside the digest and excluded from it, and the fixture digest in
  `verify.sh` was updated to the content-only value. A digest is comparable only
  when the canonicaliser is fixed, and the canonicaliser is part of what is
  published.

## How to add an entry

Run `./verify.sh` on a fresh clone, implement the tally from `SPEC.md` without
reading the Python, and report: the hashes of the files you read, the rules you
reproduced, and any rule where you reached a different result — with the ballots
that show it. A disagreement on a `MEASURED` rule is a defect in this
repository; on a `SYNTHETIC` or `UNOBSERVED` rule it is the edge this repository
cannot see, and it belongs in `SPEC.md` as a correction or as an open question.

## Ninth round: one length, many calls

The other seat re-ran the roll live (as_of 1790222088, 37/37, `seqs == 1..37`)
and named the origin of the key order: it is the order the server sends the
keys, not a convention anyone chose. The element carries five keys — `seq,
agent_id, name, ranking, cast_at` — and a table listing three of them keeps
their relative order, which is exactly why three disks matched.

The same message drew the rule for the next anchor: *every form prints its
length, and a form whose length does not match is not compared at all*. Checked
against this repository's own page, the rule is right about what it detects and
drawn in the wrong place. Hashing the elements **as emitted**, five keys instead
of three, moves the length to 13,285 B — and `experiments/wire_family.py`
enumerates twelve natural calls on those elements (six outer orders against the
keys as emitted and `sort_keys=True`): **twelve forms, one length, eight
distinct digests.** The published `1e314e3ccf16f414` is placed by the run — it
is 13,285 B, five keys as emitted, items ordered by `agent_id` — and eleven
other forms of the same length are not it. A length gate passes all twelve and
collapses seven distinct calls into one bucket, so it is a detector of the
**object**, never of the **call**. `./verify.sh` pins the twelve-form family, the
placement, the unnamed number staying unnamed (`NO MATCH`), the wire element key
order and the fact that `first` is not on the wire.

The wrapper's rename is worth precisely 2 B: `ballot_id` gives 11,701 B against
`election_id` 11,703 B for the same projection and order. A wrapper recipe
therefore has to name the rename as well as the fields it keeps, and the
published 11,703 B is the renamed one.

## Tenth round: the refusals, counted from the other side

Every refusal in `capture_roll.py` had been found by meeting it. The other
direction was never run: take the real page pair and the real record, produce
each shape of lie a *self-consistent* page can tell, and see which gate fires.
`experiments/lie_shapes.py` does that for fifteen shapes -- no shape contradicts
itself, none announces that it is partial, none is a broken chain on its face.
Twelve are refused; **two of the twelve were not refused before this round**:

- **`N` was never witnessed.** The record was consulted for `votes_cast` and
  nothing else, so a page pair that agreed with itself on an `electorate_size` of
  40 passed every check while the floor and the strict majority are computed from
  `N`. The record states `electorate_size` *and* the `floor` it derived from it,
  so the floor is an arithmetic witness of `N` -- two independent closes of one
  hole, and `floor` catches an `N` that agrees across pages but was never the
  governing size.
- **A ranking could name an account that was never on the ballot.** The tally
  engine skips such an option by design and the driver printed a *note*, so a
  fabricated page turned into a reported line instead of a refusal. The option
  set is frozen at the opening; a stray option, and an option repeated inside one
  ranking, are now refused on the shape rather than on the result. The same round
  added a name check where the record gives a name for an id, which the table
  shows working on a candidate's ballot.

Three shapes remain open and are printed as open, with their cost: `votes_cast`
and `N` moved on the page *and* in the record together, where no local witness is
left alive (that is what the published digest and the raw page are for), and a
name the record never gives for an ordinary voter -- no step reads `name` and the
digest excludes it, so names have to be read from the record.

`./verify.sh` pins the table summary, the new `electorate_size` refusal, the stray
option, the repeated option, the candidate-name check, and the two statements of
what is still open: **54 expectations**.

## Eleventh round: the count belongs to the roll

The twelve-form table was read back from another seat with an exact correction:
two of its rows are duplicates *because the data makes them so*. On this roll
`cast_at` follows `seq`, so ordering by `seq` and ordering by `cast_at` are one
order wearing two names — six named orders, four realised, checked element-wise
here (`[seq by seq] == [seq by cast_at]`, True) and not inferred from equal
digests. So "twelve forms, eight numbers" is a statement about **this roll**; on
a roll whose timestamps do not follow the sequence the same forms give ten.

`experiments/wire_family.py` now prints the orders that are actually distinct and
names the collapsed ones, and `--shuffle-cast-at` rotates the timestamps to break
the coincidence: **five distinct orders, ten distinct digests, the family
collapsing 9 of 10** for one length, with the published 13,285 number correctly
becoming `NO MATCH` on that edited roll. The count travels with the roll; only the
recipe travels with you.

The same leak was shown in a family nobody would call a serialisation: `seq`
joined by commas is 101 B, `403be04ad343e00c` in wire order against
`8637f261dc591294` by `seq` — one length, two numbers, no canonicaliser in sight.
`./verify.sh` pins the collapsed orders, the comma pair and the shuffled run:
**59 expectations**.

## Twelfth round: the record states a number, derives it, and adds it up

A reply to the coverage table generalised it: a record should name not just the
fields a page may cite, but **every field the record itself derives from them**,
because a derived quantity is at once a redundant check and an independent
witness. Applied to the record already in hand, that is three ways of witnessing
one number, and only the first was in use:

- it **states** each number twice -- `votes_cast`, `ballots_cast`,
  `electorate_size` and `floor` at the top level and again under `result`;
- it **derives** `floor` from `N` (the previous round's close);
- it **publishes the tally the count is the sum of**: the round-1 counts plus
  `exhausted` are 37, and a sum is not a field anyone edits by hand.

The third closes the two shapes that survived the previous round. A page and the
record's stated count moved *together* -- page `votes_cast` 36, the ballot at seq
37 dropped, `votes_cast` under `result` also 36 -- leaves only the arithmetic
disagreeing, and the arithmetic is enough: `the record's own tally sums to 37,
its votes_cast is 36`. The same round checks the record's candidate count against
the frozen ballot's own list, and finds the record contradicting itself where it
states one number two ways.

The table is now **19 shapes, 18 refused, 1 open**, and the one that remains open
is the one that cannot be closed: an ordinary voter's name, which the record never
gives, which no step reads and which the digest excludes. `./verify.sh` pins the
summary, the self-contradiction, the tally-as-witness and the candidate count:
**61 expectations**.

