# The tally, written out

This is what the code in this repository computes, rule by rule, so that a
second implementation can be written **from this text** rather than from the
code. A divergence between two independent readings of this text is evidence;
two runs of the same code are not.

Every rule carries a status, because the rules do not all rest on the same
evidence:

| status | meaning |
| --- | --- |
| `MEASURED` | the rule is exercised by the public roll of a decided election and reproduces its official outcome (see `fixtures/election0_roll.json`) |
| `SYNTHETIC` | the rule is covered only by an in-repo self-check with constructed ballots; the public roll never reached it |
| `UNOBSERVED` | the host's behaviour is not established by the evidence in this repository; the code makes a choice and says so |

## Inputs

An **election record**: `electorate_size` (N), `votes_cast`, the frozen
candidates, `tally_version`. A **roll**: one ranking per elector, ordered best
first. The literal `vacancy` is a legal entry in a ranking and means "an empty
office".

## Rules

1. `SYNTHETIC` — **Quorum.** `N < 10` → no election: outcome `vacancy`, reason
   `no_quorum`. No rounds are run. (The decided roll had N=30, so this branch is
   exercised only by self-checks; the reading of the threshold itself comes from
   the board's own notes, not from a public roll.)
2. `SYNTHETIC` — **Empty slate.** No candidates (every ranking is `vacancy` or
   empty) → outcome `vacancy`, reason `no_candidates`.
3. `MEASURED` — **Floor.** `F = max(5, ceil(0.30 * N))`, computed from N, the
   same number in every round of one election.
4. `MEASURED` — **Continuing options.** The continuing set is the candidates plus
   the literal `vacancy`.
5. `MEASURED` — **A ballot's active choice** is the first entry of its ranking
   that is still in the continuing set. A ballot with no such entry is
   **exhausted** and counts for nothing. Exhausted ballots are not reallocated
   and are not errors.
6. `MEASURED` — **Majority is recomputed every round** from the ballots that are
   not exhausted: `majority = non_exhausted // 2 + 1`. It shrinks as ballots
   exhaust; it is never a fixed fraction of N or of `votes_cast`.
7. `MEASURED` — **The win test.** If exactly one option has the highest count
   **and** that count reaches the round's majority, then:
   - count `< F` → outcome `vacancy`, reason `floor_not_met`, and the round
     names the `majority_option` and its `majority_count`;
   - the option is `vacancy` → outcome `vacancy`, reason `vacancy_option`;
   - otherwise → outcome `elected`, the option is the winner, and the reason
     field of the engine's enum is **empty**.

   One branch of this rule is `MEASURED` (a winner above the floor, election:0),
   the other is `SYNTHETIC` here: the `floor_not_met` case was observed on a
   permuted sensitivity run, not on the certified roll, so it is not counted as
   evidence for the host's behaviour.

   The official surface calls this last case `majority` where the engine leaves
   `reason` empty. They are one fact under two names; a comparison of enum names
   invents a divergence out of a vocabulary.
8. `SYNTHETIC` — **Two left, tied.** Exactly two options remain and both carry the
   highest (equal) count → outcome `vacancy`, reason `final_tie`.
9. `SYNTHETIC` — **Nothing left to count.** `non_exhausted == 0` → outcome
   `vacancy`, reason `final_tie`.
10. `SYNTHETIC` — **Zero-support options go first, together.** Every continuing
    option with count 0 leaves at once. This is a drop, not an elimination tie,
    and it is not reported as one. (In every round of the decided roll every
    option held at least one ballot, so the public evidence never reached this.)
11. `MEASURED` — **Elimination.** Otherwise the lowest positive count leaves, and
    **every option tied at that count leaves together** (this is the difference
    between the tally versions called `irv-1` and `irv-2` in the board's own
    history). The dropped set is reported on that round as `tied_lowest`.
12. `SYNTHETIC` — **Halt on a uniform tie.** If every continuing option with a
    positive count is tied — that is, the drop set would be the whole field —
    → outcome `vacancy`, reason `elimination_tie`, with the tied set named. The
    rule bundle changed under a live window once before (the board's own notes
    call the two readings `irv-1` and `irv-2`); what this repository reproduces
    is the reading stamped on the election record as `tally_version`, never a
    global default.
13. `SYNTHETIC` — **Ties are never broken** by id, name, signup order, chance or
    the order the options appear in. A tie either drops a set or produces a
    vacancy.
14. `UNOBSERVED` — **Entries that are not frozen candidates.** The driver drops
    them from a ranking (the rest of the ranking stays intact) and prints a note
    saying how many ballots were affected. Whether the host does the same, drops
    the whole ballot, or refuses to count it, is not established here.
15. `UNOBSERVED` — **Who is admitted.** `electorate_size` grows while a window is
    open. Whether a ballot cast before a late arrival still governs N is not
    established here; this repository stamps N from the record at computation
    time and labels it as the electorate at the closing instant.

## Output per round

`ballots_in`, `exhausted`, `non_exhausted`, `majority`, `leader` (or `leaders`
when tied), `leader_support`, `floor`, the full `counts`, and `tied_lowest` on a
round that dropped a set.

## What a second implementation must reproduce

On `fixtures/election0_roll.json` (N=30, F=9, 23 ballots): six rounds, winner
`mint` with support 12 of 21 non-exhausted in the last round, `INDEPENDENT_MATCH`
against the official outcome recorded in the fixture. On
`fixtures/election1_roll_preview.json`: the run must **not** claim an outcome —
the ballot was still open when it was read, so the driver prints a rehearsal and
`OFFICIAL unknown`.

`./verify.sh` also writes `refusals.txt`: the five refusals as lines rather than
as a claim, so that a consumer of this repository can import the refusals
together with the results. Run it for all ten expectations. A second
implementation that reproduces every `MEASURED` rule but parts company on a
`SYNTHETIC` or `UNOBSERVED` one has found the interesting edge: say which rule
and with which ballots, and the fixtures go next to it.
