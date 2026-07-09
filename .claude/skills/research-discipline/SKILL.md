---
name: research-discipline
description: Load this skill when an idea, hunch, optimization, or "I think X is causing Y" claim needs to become an accepted result — or when someone wants to claim novelty, publish a benchmark, write a README boast, or identify where a project could advance the state of the art. Triggers include "I have a theory", "this should be faster", "let's try", "is this novel?", "can we publish this number?", and any experiment being proposed without a written prediction. Delivers the evidence bar (predict numbers first, one mechanism explains everything), assigned adversarial refutation, the hunch-to-adoption lifecycle, frontier-entry format, and honest external-claim standards.
---

# research-discipline — From Hunch to Accepted Result

## 1. Purpose

This skill is the discipline that turns "I think..." into an accepted result — or an
honest, documented retirement. It sets the evidence bar for accepting a mechanism,
forces numeric predictions before experiments run, assigns someone to break every
result before it is believed, defines where frontier (state-of-the-art) opportunities
come from and how they are tracked, and sets the bar for what may be claimed publicly.

## 2. When to use / When NOT to use

Use this skill when:
- Someone proposes a hypothesis about behavior, performance, or root cause and wants to act on it.
- An experiment is about to run and nobody has written down what number it should produce.
- A result is about to be "accepted" (merged, announced, built upon) and no one has tried to break it.
- The project wants to identify where it could advance the state of the art.
- A paper, release note, README, or blog post is about to claim something externally.

Do NOT use it for routine bug fixing, ordinary feature work, or verifying that a
library does what its docs say — those have cheaper, dedicated disciplines:

| If instead you need... | Use sibling skill |
|---|---|
| First-principles verification recipes, statistical rigor for benchmarks, invariant arguments | **proof-and-analysis** |
| Symptom→triage tables for an active bug | **debugging-playbook** |
| The record of past investigations and retired ideas | **failure-archaeology** |
| Gating and review for landing an adopted change | **change-control** |
| Flag mechanics for running an experiment safely in-tree | **config-and-flags** |
| Building the instruments that produce your measurements | **diagnostics-and-tooling** |
| Acceptance thresholds and test evidence for ordinary changes | **validation-and-qa** |
| Turning one hard problem into a phased, gated campaign | **campaign-design** |

Boundary rule: **proof-and-analysis** owns *how to measure and analyze correctly*
(warmups, variance, significance, invariants). **research-discipline** owns *what the
measurement must clear before anyone believes the idea*. When this skill says
"measure", it means "measure per proof-and-analysis" — do not reinvent statistics here.

## 3. Core doctrine

Definitions used throughout:

- **Hunch** — an unwritten suspicion. Zero evidentiary weight. Cheap, welcome, plentiful.
- **Hypothesis** — a written statement of a *mechanism* plus at least one numeric prediction it entails.
- **Mechanism** — the causal story ("X happens because Y does Z"), as opposed to a correlation ("X and Y co-occur").
- **Accepted result** — a hypothesis that survived assigned adversarial refutation and was adopted via change-control, or recorded as an accepted finding.
- **Retirement** — the documented death of a hypothesis, filed in failure-archaeology. A success outcome: it prevents the idea being re-fought.

---

### PART A — THE EVIDENCE BAR

#### A1. One mechanism must explain ALL observations — including the negatives

A hypothesis is not "consistent with the data" if it explains the three observations
you like and is silent on the two you don't. Before acceptance, build the observation
ledger:

| # | Observation | Predicted by the mechanism? | Notes |
|---|---|---|---|
| 1 | (each thing you saw, positive or negative) | yes / no / contradicts | |

Rules for the ledger:
1. **Negatives are observations.** "The slowdown did NOT appear on the small dataset"
   is a row. "Disabling the cache did NOT fix it" is a row. A mechanism that predicts
   the positives but not the negatives is at best half a mechanism.
2. **One mechanism.** If you need mechanism 1 for observations 1–3 and mechanism 2 for
   observation 4, you do not have an explanation yet — you have two open hypotheses.
   (Exception: genuinely independent co-occurring causes are real but rare; if you
   claim two causes, each must independently clear this entire evidence bar.)
3. **Any "contradicts" row kills or forks the hypothesis.** You may not annotate it
   away ("probably noise") without a measurement showing it is noise — see
   proof-and-analysis for what "showing it is noise" requires.

#### A2. Predict NUMBERS before the experiment runs

Before running any experiment, write down — in the hypothesis document, timestamped
or committed, not in your head:

1. **The quantity** you will measure and the exact command/instrument that produces it
   (build the instrument per diagnostics-and-tooling if it doesn't exist).
2. **The predicted value or range** if the hypothesis is true. A number or interval,
   not a direction. "Faster" is not a prediction; "wall time drops from ~90 s to
   45–60 s because the mechanism removes roughly half the I/O" is.
3. **The kill condition**: what result means the hypothesis is false. Write this
   BEFORE seeing data, because afterward everything looks survivable.

Then run the experiment and compare.

**The post-hoc reinterpretation rule (non-negotiable):** a hypothesis that survives
only by reinterpreting its prediction after seeing the result is dead. "Well, 5% is
still an improvement" after predicting 50% is not a partial success — it is a refuted
prediction plus an undischarged mystery (why only 5%?). The honest moves after a
missed prediction are exactly two:
- **Retire** the hypothesis into failure-archaeology, or
- **Fork** it: write a NEW hypothesis with a NEW numeric prediction that explains
  both the old observations and the miss, and run a NEW experiment. The fork is a
  new entry in the lifecycle, not an edit to the old one — the miss stays on the record.

Why numbers: a directional prediction ("it'll get better") is compatible with almost
any mechanism and therefore tests nothing. Magnitude is where mechanisms differ. Two
mechanisms that both predict "faster" rarely predict the same *amount* faster.

#### A3. Assigned adversarial refutation

Before a result is accepted, someone — a teammate, or a **fresh session/agent with no
stake in the result** — is explicitly assigned to break it. Not "reviewed", not
"looked at": assigned, named in the hypothesis document, and tasked with refutation.
The author is disqualified from this role. If the refuter cannot break it after
working the checklist below, the result may proceed to adoption.

**Refuter's checklist** (each item is a concrete task; record the outcome of each):

1. **Alternative mechanisms.** Write down at least two other mechanisms that would
   produce the same headline observation. For each: what observation would
   discriminate between it and the claimed mechanism? Has that observation been made?
   If not, the result is not accepted until it is (see "discriminating experiments"
   in debugging-playbook for the technique).
2. **Confound hunting.** Check, minimally:
   - Did anything else change between baseline and treatment (dependency versions,
     data, config, hardware, ambient load)? Run `git diff <BASELINE-REF> <TREATMENT-REF> --stat`
     and account for every file touched beyond the intended change.
   - Is the baseline itself reproducible? Re-run it. If baseline variance overlaps
     the claimed effect, the effect is not established (statistical bar:
     proof-and-analysis).
   - Ordering/warm-cache effects: does the effect survive swapping the order in
     which baseline and treatment run?
3. **Fresh data.** Does the result survive on inputs the author never saw while
   developing the idea — a different dataset, a later time window, a machine the
   author didn't tune on? A result that only holds on the development inputs is a
   description of those inputs, not a mechanism.
4. **Prediction audit.** Pull up the written prediction from A2. Was the predicted
   number hit within its stated range? If the claim narrative has drifted from the
   written prediction, flag it — that is post-hoc reinterpretation (A2).
5. **Ledger audit.** Walk the A1 observation ledger. Is any known observation
   missing? Interview: "what did you see during this work that surprised you and
   isn't in the ledger?" Surprises omitted from ledgers are where dead hypotheses hide.

The refuter's findings go in the hypothesis document verbatim, including "attempted X,
result Y, could not break it" entries. A refutation report that only says "LGTM" is a
failed refutation — re-assign it.

#### A4. The idea lifecycle

Every idea is in exactly one of these states. State lives in the hypothesis document
(one file per idea, e.g. `docs/research/<IDEA-SLUG>.md` — adjust path to your
project's docs convention per docs-and-writing).

| State | Entry criteria | Exit paths |
|---|---|---|
| 1. Hunch | Someone suspects something. No file yet. | Write it up → Hypothesis. Or drop it (no record needed). |
| 2. Written hypothesis | File exists with: mechanism, observation ledger (A1), numeric predictions + kill condition (A2). | Run experiment → Experiment. Kill condition already known false → Retired. |
| 3. Experiment behind a flag | The experimental change is in-tree but OFF by default, behind a flag registered per **config-and-flags** (guard, default, owner, expiry). Never run research code by editing constants on a branch nobody can reproduce. | Prediction hit → Adversarial review. Prediction missed → Retired or Forked (A2). |
| 4. Adversarial review | Refuter assigned by name; checklist A3 worked and recorded. | Survives → Adoption. Broken → Retired or Forked. |
| 5a. Adopted | Change lands via **change-control** (its gates, its review). Flag graduates or is removed per config-and-flags. Hypothesis doc marked ACCEPTED with a link to the landing commit/PR. | Later contradicting evidence → reopen as a new hypothesis; never silently edit an ACCEPTED doc. |
| 5b. Retired | Hypothesis doc marked RETIRED with: what was predicted, what was observed, why the mechanism is dead, and what would reopen it. Filed/indexed in **failure-archaeology**. Experimental flag and code removed. | Reopening requires new evidence, cited. |

**Retirement is a success outcome.** A retired idea with a written cause of death is
worth more than an abandoned branch: it is the only thing that stops the same idea
consuming another week next year. Track retirements as delivered work, not as waste.

Skipping states is the classic failure: hunch → merged change with no written
prediction and no refuter. When you find such a change, treat its claimed benefit as
unestablished and backfill states 2–4 before building on it.

---

### PART B — FRONTIER IDENTIFICATION

A **frontier opportunity** is a place where this project could plausibly advance the
state of the art (SOTA) — do something the field's current best methods cannot.
Frontier work is high-variance; the discipline below keeps it from contaminating the
project's claims before it has earned anything.

#### B1. Where good ideas historically come from (hunting guide)

These are heuristics, not guarantees — but they are where results have historically
been found, so hunt here first:

1. **Anomalies in diagnostics output.** A number that is reproducibly "wrong" but
   harmless — a counter that shouldn't be that high, a distribution with an
   unexplained second mode, a phase that takes 10x its complexity estimate (see
   proof-and-analysis for complexity estimates). Anomalies are unpaid-for
   information; most people annotate them away. Keep an anomaly log next to your
   diagnostics (a dated append-only file beside the baselines — format defined in
   diagnostics-and-tooling's baseline-discipline section); review it when hunting.
2. **Recurring pain.** Anything the team has now worked around three or more times.
   Repeated workarounds mean the standard tooling/method genuinely doesn't fit this
   project's shape — which is exactly the precondition for a frontier: everyone else
   has the same pain, or nobody else has your workload.
3. **Cross-domain transfer.** A technique that is standard in field A and unknown in
   field B (e.g., a compiler optimization applied to a query planner, a
   bioinformatics index applied to log search). The novelty audit (C1) matters
   double here: transfers usually turn out to be "known-but-recombined", which is
   still valuable but must be labeled honestly.

#### B2. The frontier entry format

Every frontier opportunity is one entry in a tracked file (e.g.
`docs/research/FRONTIER.md`). An entry that cannot fill all five fields is not an
entry yet — keep it as a hunch. Required fields:

```markdown
## <FRONTIER-SLUG> — status: candidate | open | met | retired

**Why current SOTA fails here.** Name the specific best existing method/tool and the
specific input/regime where it breaks or underperforms. "X is slow" is not enough;
"X's published results assume <PROPERTY> and our workload violates it because
<REASON>" is the bar. Cite the prior art you checked (C1).

**What specific asset this project has.** The unfair advantage: a dataset nobody else
has, an invariant our domain guarantees that the general method can't assume, an
instrument we already built. If the answer is "we're smart", there is no asset —
someone with the same idea and no asset publishes first or was right to not bother.

**First three concrete steps IN THE REPO.** Three actions naming real paths, real
commands, real flags — e.g. "1. Add `--emit-histogram` to `<DIAG-TOOL>` (see
diagnostics-and-tooling); 2. Extract the 50 worst cases from `<DATASET>` into
`bench/frontier/<SLUG>/`; 3. Prototype behind flag `<FLAG-NAME>` per config-and-flags."
If you cannot name three in-repo steps, the entry is a paper review, not a frontier
entry for THIS project.

**"You have a result when…" milestone.** One falsifiable sentence with a number and
a comparison target: "…when the prototype beats <SOTA-BASELINE> by ≥<N>% on
<BENCHMARK> under the measurement protocol in proof-and-analysis, and the result
survives A3 refutation." The milestone is written before work starts and is not
edited to fit results (same rule as A2).
```

#### B3. Frontier label discipline

- Every entry starts as **candidate** (idea drafted, prior-art check not done) or
  **open** (prior-art check done, milestone set, work may proceed).
- An entry stays labeled **candidate/open** — everywhere it is mentioned, internal
  or external — until its milestone is met AND the result has survived A3. Only then
  may it be marked **met**, and only then do PART C claims become available.
- Frontier entries that miss their milestone are **retired** into failure-archaeology
  with the same honors as any hypothesis (A4, state 5b).
- Never let "we are working on beating SOTA at X" drift into "we beat SOTA at X" in
  READMEs, slide decks, or conversation. The status field exists so this drift is
  checkable: audit external text against `FRONTIER.md` statuses before anything ships.

---

### PART C — EXTERNAL POSITIONING

External = anything a stranger can read: papers, release notes, README claims, blog
posts, conference talks, marketing copy. The bar is higher than for internal
acceptance because strangers cannot ask follow-up questions and the project's
credibility is a shared, slow-to-rebuild asset.

#### C1. The novelty audit

Before the word "novel" (or "first", "new approach", "unlike prior work") appears
anywhere externally, classify the claim into exactly one bucket — and the
classification requires a literature/prior-art check, not a memory check:

| Bucket | Definition | What you may write |
|---|---|---|
| Genuinely novel | Prior-art check found no prior statement or implementation of the core mechanism. | "novel", WITH the search recorded (where you searched, what queries, date) so a challenger can be answered. |
| Known-but-recombined | Every component exists in prior work; the combination or the application domain is new. | "we apply/combine <KNOWN-A> and <KNOWN-B> to <DOMAIN>", citing the components. This is most real-world value — do not be ashamed of it, and do not dress it up as bucket 1. |
| Known | The thing exists in prior work as-is. | Cite it. Claiming it as yours is the fastest way to lose all credibility for the claims that ARE yours. |

Minimum prior-art check (record all of it in the hypothesis or frontier doc):
1. Search scholarly indexes (e.g. Google Scholar, arXiv) for 3+ phrasings of the
   mechanism — including the other field's vocabulary if it's a cross-domain transfer
   (B1.3); the same idea usually has a different name elsewhere.
2. Search code hosts (e.g. GitHub) for implementations.
3. Check the obvious survey/textbook for the area.
4. Ask the most senior domain person available "has anyone done this?" — and record
   their answer either way.

No hits does not prove novelty (absence of evidence); it earns the label "novel to
the best of our knowledge, based on the recorded search" — which is the honest
maximum any prior-art check can deliver.

#### C2. The reproducibility bar for external claims

**Rule: a stranger with the repo and the writeup can reproduce the headline number.**
Not "could in principle" — you verify it, before publication, by the clean-room test:

1. A person or fresh agent session that did NOT produce the result starts from a
   clean clone (`git clone <REPO-URL>` into an empty directory; environment built
   only from the repo's own runbook — see build-and-env).
2. They follow ONLY the writeup plus what is in the repo. No side-channel questions
   answered except by fixing the writeup/repo and restarting.
3. They must land within the claim's own stated tolerance of the headline number
   (the tolerance comes from the variance analysis — proof-and-analysis).

If step 3 fails, the claim does not ship until it passes. If the data cannot be
included (size, licensing), the writeup must say exactly what is missing and what a
stranger CAN reproduce without it — claim only the reproducible part in the headline.

#### C3. Benchmark publication checklist

No benchmark result is published without ALL of the following recorded alongside the
number (in the repo, referenced from the writeup):

- [ ] Exact commit hash of the code that produced the number (`git rev-parse HEAD`).
- [ ] Exact configuration: every flag and config value in effect, dumped
      mechanically (via the config-dump facility per config-and-flags), not
      reconstructed from memory.
- [ ] Exact command line(s) run, copy-pasteable.
- [ ] Dataset/workload identity: name, version, and a checksum
      (e.g. `sha256sum <DATASET-FILE>` on Linux/GNU coreutils, `shasum -a 256 <DATASET-FILE>` on macOS, `certutil -hashfile <DATASET-FILE> SHA256` on Windows).
- [ ] Hardware and OS description of the measurement machine.
- [ ] Measurement protocol: warmup, repetition count, and variance/spread reported
      with the headline number — protocol per proof-and-analysis.
- [ ] Baseline provenance: the compared-against system's version and configuration,
      held to the same standard as your own. A benchmark against a misconfigured
      baseline is the most common form of accidental dishonesty.
- [ ] The A3 refutation record for this specific number.

#### C4. Failure modes of external positioning (name them to catch them)

| Failure mode | Symptom | Countermeasure |
|---|---|---|
| Status drift | "Working toward" becomes "achieved" in a README edit. | Audit external text against FRONTIER.md statuses (B3) before release. |
| Novelty inflation | "Novel" written with no recorded search. | C1: no search record → the word comes out. |
| Best-run reporting | Headline is the best of N runs; variance unmentioned. | C3 checklist requires spread; proof-and-analysis defines it. |
| Strawman baseline | SOTA comparison uses defaults the SOTA authors would never use. | C3 baseline-provenance item; have the refuter (A3) configure the baseline. |
| Ghost configuration | Number is real but depended on an uncommitted local tweak. | C3: mechanical config dump at measurement time, committed. |

## 4. Worked example

**Illustrative example — all names, numbers, and facts are fictional.**

Project "Kelpie" is a log-indexing service. During routine profiling, the
diagnostics histogram (built per diagnostics-and-tooling) shows query latency has a
second mode near 400 ms that no one can explain — an anomaly (B1.1).

**State 1→2.** Engineer writes `docs/research/bloom-skip.md`: *Mechanism:* the 400 ms
mode is queries whose term misses every segment; each miss still opens and scans the
segment footer. A per-segment Bloom filter (a probabilistic set-membership structure)
would skip those opens. *Ledger:* (1) second mode ≈400 ms — predicted; (2) mode absent
on the small tenant — predicted (few segments, few misses); (3) mode did NOT shrink
when the OS page cache was warmed — predicted (cost is syscalls + footer parse, not
cold reads). All rows "yes". *Prediction:* with filters at 1% false-positive rate,
p99 for miss-heavy queries drops from ~400 ms to 40–80 ms; index build time rises
≤5%. *Kill condition:* if p99 stays above 200 ms, the mechanism is wrong.

**State 3.** Prototype lands behind `--enable-bloom-skip` (default off, registered
per config-and-flags). Benchmark per proof-and-analysis (10 repetitions, warmup,
spread reported): miss-heavy p99 goes 397 ms → 61 ms (predicted 40–80 — hit); build
time +3.8% (predicted ≤5% — hit).

**State 4.** A fresh agent session is assigned as refuter. Checklist: *Alternative
mechanisms* — could the win be from the incidental footer-parse refactor in the same
branch? Refuter reruns with filters allocated but bypassed: 389 ms, so the refactor
is not the cause. *Confounds* — `git diff v1.8.2 HEAD --stat` shows only the two
intended files. Baseline re-run overlaps original baseline. *Fresh data* — on a
tenant dataset the author never used: 55 ms. Could not break it; findings recorded
in the doc.

**State 5a.** Adopted via change-control; doc marked ACCEPTED, linked to the PR.

**Frontier check (B).** Someone proposes a FRONTIER.md entry: "novel learned
replacement for Bloom filters". The C1 prior-art check (Scholar: "learned bloom
filter", "learned index membership"; GitHub search) finds substantial prior work —
the entry is drafted as *candidate*, bucket "known-but-recombined" at best, and its
milestone is written as "beats our tuned classical filter by ≥20% memory at equal
false-positive rate on `bench/frontier/learned-bf/`". The README meanwhile says only
what is true: "segment-skipping via Bloom filters (p99 miss-query latency 397→61 ms;
reproduction: `bench/README.md`)" — with commit hash, config dump, and dataset
checksum per C3.

## 5. Instantiate for your project

Produce `<PROJECT>-research-discipline` in the target repo. Steps:

1. **Mine the repo for existing research practice.** Run, from the repo root:
   - `git log --oneline --grep="experiment" -i -20`, and repeat with
     `--grep="hypothesis"`, `--grep="benchmark"`, `--grep="prototype"`,
     `--grep="revert"` — find past experiments and how (or whether) they were gated.
   - `git log --diff-filter=D --oneline -- "*bench*" "*experiment*"` — deleted
     experiments are candidate retirement records for failure-archaeology.
   - Search for existing research artifacts: docs/notes directories
     (`docs/`, `notes/`, `rfcs/`, `adr/`), benchmark directories (`bench/`,
     `benchmarks/`, `perf/`), and any `FRONTIER`/`ROADMAP`/`IDEAS` files.
   - Inventory experiment flags: grep the flag registry (per the project's
     config-and-flags instantiation) for experimental/off-by-default entries.
   - Check external claims already made: read the README, release notes, and any
     paper/blog links for claims of "novel", "fastest", "first", or benchmark
     numbers. These are your audit backlog (step 4).
2. **Fix the locations.** Decide and write into the instantiated skill:
   - hypothesis docs live at `<HYPOTHESIS-DIR>` (e.g. `docs/research/`),
   - the frontier file at `<FRONTIER-FILE>` (e.g. `docs/research/FRONTIER.md`),
   - the retirement index location (defer to the project's failure-archaeology
     instantiation — one home per fact).
3. **Fill the template skeleton:**

   ```markdown
   ---
   name: <PROJECT>-research-discipline
   description: <project-specific triggers: the actual experiment areas, bench dirs, and claim surfaces of this repo>
   ---
   # <PROJECT> Research Discipline
   ## Evidence bar (project constants)
   - Measurement protocol: <link to <PROJECT>-proof-and-analysis section>
   - Experiment flag convention: <link to <PROJECT>-config-and-flags; naming pattern for experimental flags>
   - Refuter assignment convention: <who/what gets assigned; how a fresh session is spawned>
   ## Idea lifecycle in this repo
   - Hypothesis doc template lives at: <PATH> (copy the A1/A2 fields verbatim)
   - Current in-flight hypotheses: <TABLE: slug | state | flag | refuter | prediction>
   ## Frontier register
   - <FRONTIER-FILE> entries: <TABLE: slug | status | milestone | evidence-so-far>
   ## External claims register
   - <TABLE: claim | where published | bucket (C1) | repro verified on <DATE> by <WHO> | C3 record location>
   ## Past retirements
   - Pointer to <PROJECT>-failure-archaeology entries originating from research.
   ```

4. **Evidence requirements before filling blanks** (do not skip):
   - An "in-flight hypothesis" row may be written only from an actual hypothesis
     doc containing a pre-registered numeric prediction — not from someone's verbal
     description of what they're trying.
   - A frontier entry may be marked **open** (vs **candidate**) only after the C1
     prior-art search is recorded in the entry.
   - An external-claims row may be marked "repro verified" only after a clean-room
     reproduction (C2) actually ran; record who/what ran it and the number obtained.
   - Existing README/paper claims found in step 1 that lack a C3 record get a row
     marked **UNVERIFIED — legacy claim**; the instantiated skill must list them as
     an explicit audit backlog rather than silently blessing them.
5. **Prove the pipeline once.** Take one live hunch from the team (there is always
   one), walk it to state 2 (written hypothesis with numeric prediction and kill
   condition) using the template, and link it as the instantiated skill's first
   worked example. Do not ship the instantiation with zero real entries.
   If no human is available, mine a candidate hunch from the repo itself — the top
   `TODO`/`FIXME` carrying a performance or correctness claim, or a commit message
   containing "should be faster" / "probably because"
   (`git log -i --grep='should\|probably' --oneline -30`) — and write it up as a
   state-2 hypothesis labeled `seeded-from-repo, unconfirmed by team`. If even that
   yields nothing, ship with an empty hypothesis ledger and say so explicitly in the
   instantiated skill's provenance — an honest empty register beats an invented entry.

## 6. Provenance and maintenance

- Authored 2026-07-06 against no specific project, per the FableSkills authoring
  contract. All examples are fictional and labeled as such.
- Volatile parts and re-verification:
  - Git commands used here (`git log --grep`, `git log --diff-filter=D`,
    `git diff <A> <B> --stat`, `git rev-parse HEAD`, `git clone`): stable core git;
    re-verify with `git log --help` / `git diff --help` if a flag errors.
  - Checksum commands: `sha256sum --help` (Linux/GNU coreutils), `shasum -a 256`
    (macOS default) and `certutil -hashfile -?` (Windows) — re-verify per platform.
  - Prior-art sources named in C1 (Google Scholar, arXiv, GitHub search) are
    ecosystem examples and may change; the four-step search *structure* is the
    stable part.
  - The "where ideas come from" list (B1) is a heuristic hunting guide, not a
    guarantee — labeled as such by design; extend it with your project's own hit
    history over time.
- Instantiated copies (`<PROJECT>-research-discipline`) must add their own
  provenance block: date, repo commit at instantiation, which registers were
  populated from real artifacts vs created empty, and the legacy-claim audit backlog.
