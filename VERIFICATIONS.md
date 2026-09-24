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
