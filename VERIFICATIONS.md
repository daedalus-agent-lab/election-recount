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
