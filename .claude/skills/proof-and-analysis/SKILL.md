---
name: proof-and-analysis
description: Load when a claim needs first-principles verification instead of trust — "is this actually faster", "will this scale / fit in memory", "is this algorithm correct for all inputs", "should we adopt this library/tool/pattern", "benchmark says X — is that real", or before building anything with a performance or capacity budget. Delivers six analysis recipes: invariant arguments with property-based testing, complexity validated by measurement, statistically honest benchmarks (with a runnable verdict script), Fermi estimation, FMEA-lite failure enumeration, and a prove-it-before-adopting checklist for dependencies.
---

# Proof and Analysis — "Prove it, don't just install it"

## 1. Purpose

This skill turns "it seems fine / the README says so / it passed once" into
demonstrated fact. It gives you six recipes for arguing and measuring that a
claim is true **in your project**: correctness across all inputs, complexity
that survives scale, speedups that exceed noise, designs that fit their
budgets, failure modes enumerated before they fire, and dependencies proven
before adoption.

## 2. When to use / When NOT to use

Use this skill when:
- Someone (including you) is about to claim "faster", "correct", "scales", or
  "fits" without evidence produced *on this project's workload*.
- You are choosing whether to adopt a dependency, tool, or pattern.
- A design is about to be built against an unstated memory/latency/throughput
  budget.
- A test passed but you cannot say *why* the code is correct for inputs the
  test did not cover.

Do NOT use it for:

| If instead you need... | Use sibling skill |
|---|---|
| How to build timers, profilers, diff tools — the measurement *mechanics* | diagnostics-and-tooling |
| Hypothesis lifecycle, predict-before-run discipline, refuting your own idea | research-discipline |
| What counts as acceptance evidence; golden/certified test inventories | validation-and-qa |
| Finding *why* something is currently broken | debugging-playbook |
| Structuring a weeks-long investigation with gates | campaign-design |
| Recording the invariants a design must preserve, once proven | architecture-contract |

Rule of thumb: diagnostics-and-tooling tells you **how to measure**; this
skill tells you **what to measure, how many times, and when a number is
allowed to become a claim**.

## 3. Core doctrine

**Definitions (used throughout):**
- **Invariant** — a property that must hold for *every* input/state, not just
  test cases (e.g. "output is always sorted").
- **Claim** — any sentence of the form "X is faster / correct / sufficient".
  Claims are liabilities until backed by a demonstration you ran.
- **Noise** — run-to-run variation in a measurement with *nothing changed*.
- **Fermi estimate** — an order-of-magnitude calculation from rough known
  quantities, written down before building.

Every recipe below has the same shape: **Reach for it when → Steps →
Illustrative micro-example → Done means**. A recipe is not finished until
every item under "Done means" exists in writing (commit message, PR
description, ADR, or analysis note — see docs-and-writing conventions if the
project has them).

---

### Recipe 1 — Invariant arguments (with property-based testing)

**Reach for it when:** you wrote or reviewed an algorithm/data transformation
and want to claim it is correct beyond the 3 examples in the unit tests.

**Steps:**
1. State each invariant formally enough that a program could check it. Bad:
   "dedupe works". Good: "for all lists xs: (I1) output has no duplicates,
   (I2) output's element set equals input's element set, (I3) output is a
   subsequence of the input (first occurrences, in order)".
2. Argue it by cases: walk every code path (each branch, each early return,
   each loop exit) and state why the invariant survives that path. If a path
   resists a one-sentence argument, that path is where the bug is.
3. Make it executable with a property-based test: a test that generates
   hundreds of random inputs and checks the invariant on each, shrinking any
   failure to a minimal counterexample. Real libraries by ecosystem
   (names verified against their registries, 2026-07-06):
   - Python: `hypothesis` — `pip install hypothesis`
   - JS/TS: `fast-check` — `npm install --save-dev fast-check`
   - .NET: `FsCheck` — `dotnet add package FsCheck`
4. Also encode one *intentionally wrong* variant of the code and confirm the
   property test catches it (a property test that cannot fail proves nothing).

**Illustrative micro-example** (fictional; the test below was executed at
authoring time against a reference `dedupe_keep_first` implementation — not
shown — and passed; to run it yourself, define or import that function first):

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_dedupe_invariants(xs):
    out = dedupe_keep_first(xs)
    assert len(out) == len(set(out))   # I1: no duplicates
    assert set(out) == set(xs)         # I2: same element set
    it = iter(xs)                      # I3: order-preserving subsequence
    assert all(any(x == y for y in it) for x in out)
```

Same idea in fast-check: `fc.assert(fc.property(fc.array(fc.integer()), xs => { ... }))`.

**Done means:** invariants written as I1..In in checkable form; a per-path
argument (even three bullet points); a property test in the suite; evidence
the test can fail (the sabotaged run's output).

---

### Recipe 2 — Complexity and capacity analysis (big-O, then validated)

**Reach for it when:** code will run on inputs larger than today's, or anyone
says "that loop is fine".

**Steps:**
1. Derive complexity from the code: annotate each loop/recursion with what it
   iterates over; multiply nested ones. Include hidden costs: `list.contains`
   inside a loop is O(n) per call; string concatenation in a loop is often
   O(n²) total.
2. Predict the scaling ratio: if O(n), 10× input → ~10× time; if O(n²),
   10× input → ~100× time; if O(n log n) → ~13× time (10 × log-factor ≈ 1.3
   when going 1k→10k).
3. Measure at two-plus scales at least 10× apart (see diagnostics-and-tooling
   for timer construction). Compare **predicted ratio vs observed ratio** —
   never a single absolute number.
4. If observed disagrees with predicted by more than ~2×, your model of the
   code is wrong. Find the hidden loop or the cache effect before trusting
   either number.
5. Capacity variant: do the same for memory — predict bytes per item ×
   item count, then measure RSS (resident memory) at two scales.

**Illustrative micro-example:** the fictional `larkspur` report generator is
"believed linear". Predicted for 1k→10k orders: ~10×. Measured: 0.8 s at 1k,
77 s at 10k — observed ratio 96×, which matches n² (100×), not n (10×).
Reading with that lens finds `if customer in seen_list` (a list, not a set)
inside the order loop. Fix, re-measure: 0.8 s → 8.3 s, ratio 10.4× ≈
predicted. The analysis is complete *only after* the re-measurement matches
the model.

**Done means:** a stated complexity with the per-loop derivation; a predicted
ratio written **before** measuring (see research-discipline on
predict-before-run); measurements at ≥2 scales; predicted vs observed side by
side; discrepancies explained, not shrugged at.

---

### Recipe 3 — Statistical rigor for benchmarks

**Reach for it when:** anyone is about to compare two timings — before/after
an optimization, library A vs library B, old query vs new query.

**Why single runs lie:** one run mixes the code's cost with cold caches, JIT
warmup, other processes, CPU frequency scaling, and GC pauses. On a normal
dev machine, run-to-run spread of 5–20% with *no code change* is common. Any
"speedup" smaller than that spread is indistinguishable from luck.

**Steps:**
1. Warm up: run the workload ≥3 times and discard those timings (fills
   caches, JITs code, opens connections).
2. Collect ≥10 measured runs per variant, interleaved with as little else
   running as possible. More runs if the effect looks small.
3. Report **min, median, p95** — never the mean alone (one GC pause wrecks a
   mean) and never a single number. Min approximates the code's floor; median
   is the honest typical; p95 shows the tail users feel.
4. Apply the decision rule below. Only a CONCLUSIVE result may be phrased as
   "faster"; everything else is reported as "no demonstrated difference".

**The decision rule (heuristic a non-statistician can apply):**

> Compute [min, p95] for each variant. **If the two intervals overlap, the
> result is INCONCLUSIVE — do not claim a speedup.** If they do not overlap,
> report the ratio of medians as the effect size.

This is deliberately conservative: it will miss real small effects, and it is
not a formal significance test. Escalation path when it says INCONCLUSIVE but
the difference matters: double the run count and retry; reduce noise (close
apps, disable turbo/power-saving, use a quiet CI runner); or, if the claimed
effect is still under ~10%, get a proper test (Mann-Whitney U) or accept the
honest answer "no demonstrated difference".

**Runnable form — this skill ships the rule as a script** (tested 2026-07-06;
one timing per line per file, any consistent unit):

```
python3 scripts/bench_verdict.py old_ms.txt new_ms.txt --unit ms
# Windows without a python3 alias: use  py scripts\bench_verdict.py ...
# exit 0 = conclusive, 1 = inconclusive, 2 = usage error / too few runs
```

**Illustrative micro-example** (fictional numbers; both actually run through
the script): a "6% faster" JSON parser shows medians 403.5 ms → 390.5 ms, but
intervals [380, 445] vs [370, 430] overlap → `VERDICT: INCONCLUSIVE`. The
same script on a real rewrite — [380, 445] vs [192, 230] — prints
`CONCLUSIVE -- B is 2.00x faster`. The first claim dies; the second ships.

For whole-command benchmarks, the CLI tool `hyperfine` automates warmup and
repetition and reports min/median for you: `hyperfine --warmup 3 --runs 20
'<CMD-A>' '<CMD-B>'` (flags verified against its README, 2026-07-06;
`--export-markdown FILE` writes a shareable table). Measurement mechanics
beyond this — in-process timers, isolating the machine — live in
diagnostics-and-tooling.

**Done means:** run count and warmup count stated; min/median/p95 for both
variants; the verdict from the rule (or script output pasted); any speedup
claim accompanied by the noise it exceeds.

---

### Recipe 4 — Back-of-envelope estimation (Fermi discipline)

**Reach for it when:** *before* building anything with an implicit budget —
"cache it in memory", "we'll batch nightly", "one service instance is
enough" — and before any capacity-related purchase.

**Steps:**
1. Write down the budget first: available memory, latency target, requests/s,
   storage, cost ceiling. If nobody can state the budget, that is the finding
   — stop and get one.
2. Estimate the demand from rough knowns, each with its source: user counts
   from analytics, bytes-per-record from a sampled real record, rates from
   logs. Round aggressively (1 significant figure); chase orders of
   magnitude, not decimals.
3. Multiply out. Compare demand vs budget. Verdicts: **fits with ≥4× headroom**
   (proceed), **fits within ~4×** (proceed, but instrument and set an alarm —
   see diagnostics-and-tooling), **does not fit** (redesign now, cheaply).
4. Write the estimate down where the implementation will live (design doc,
   ticket, ADR). An unwritten estimate cannot be falsified; a written one
   turns production reality into a free experiment: when real numbers arrive,
   compare and update your inputs.

**Illustrative micro-example:** proposal — "keep every active session in the
`larkspur` API pod's memory". Budget: 4 GB pod limit, ~1 GB already used.
Demand: 2M registered users × ~40% daily active × ~3 KB/session (measured by
serializing one real session ≈ 2.7 KB, rounded up) ≈ 800k × 3 KB ≈ **2.4 GB**.
Verdict: 2.4 GB into 3 GB free — fits with only 1.25× headroom, and one
marketing spike breaks it. Redesign (external cache or TTL eviction) chosen
*before* a line was written. Estimate recorded in the design doc; three
months later production showed 2.1 GB peak — model validated.

**Done means:** budget stated with source; each input quantity sourced (one
line each); the arithmetic shown; the verdict and headroom factor; the whole
thing written somewhere a future reader will find when reality diverges.

---

### Recipe 5 — Failure-mode enumeration (FMEA-lite for software)

FMEA = Failure Mode and Effects Analysis: systematically listing what can go
wrong, how bad, how likely, and how you'd know. The lite version fits in a
table and an hour.

**Reach for it when:** a change touches a **boundary** — network call, file
I/O, user input, third-party API, queue, cron trigger, cross-service schema,
process restart — or before declaring an error-handling story "done".

**Steps:**
1. List the boundaries the change touches (use the list above as the prompt).
2. For each boundary, enumerate modes mechanically — for every input/call
   ask: *missing? malformed? duplicated? delayed? out of order? too large?
   permission denied? partial (died halfway)?* That 8-question prompt is the
   core of the method.
3. Score each mode 1–3 on Severity (S: annoyance → data loss/outage),
   Likelihood (L: yearly → daily), Detection (D: alarmed → silent). Multiply
   into a risk number, 1–27.
4. For every mode scoring ≥ 8, name the mitigation (retry, idempotency key,
   validation, timeout, alert) or explicitly write "accepted risk" with a
   one-line reason. Silent-failure modes (D=3) get priority regardless of
   score — see diagnostics-and-tooling for making failures observable.
5. Turn the top modes into tests or injected-fault drills where practical
   (validation-and-qa owns what counts as sufficient test evidence).

**Illustrative micro-example** (fictional CSV-upload feature, 3 of 9 rows):

| Boundary: uploaded file | S | L | D | Risk | Mitigation |
|---|---|---|---|---|---|
| File > 500 MB (too large) | 2 | 2 | 1 | 4 | reject > 50 MB pre-parse |
| Row valid UTF-8 but wrong column order (malformed) | 3 | 2 | **3** | 18 | header validation + import report |
| Upload dies at row 40k of 80k (partial) | 3 | 2 | 2 | 12 | import is transactional; all-or-nothing |

The wrong-column-order row (silent data corruption, D=3) drove the design
change; without the table it would have shipped as "we parse CSV, done".

**Done means:** the boundary list; the mode table with S/L/D scores; every
mode ≥ 8 has a named mitigation or an explicit accepted-risk line; the silent
modes called out separately.

---

### Recipe 6 — "Prove it before adopting it" (dependency/tool/pattern checklist)

**Reach for it when:** anyone proposes adding a library, framework, build
tool, database, or architectural pattern — especially when the argument is a
benchmark from the project's own README.

**The checklist** (all items answered in writing before the dependency is added):

1. **What exact claim justifies adoption?** One sentence with a number or a
   property ("10× faster reads than our current cache", "eliminates class of
   bug X"). "It's popular / modern" is not a claim; return to sender.
2. **What would demonstrate that claim HERE?** Design a demonstration on
   *your* workload shape: your data sizes, your access pattern, your runtime
   version. A README benchmark demonstrates the vendor's workload, not yours.
3. **Run the demonstration.** Timebox it (half a day is usually enough for a
   spike). Apply Recipe 3 to any performance comparison and Recipe 4 to any
   capacity claim.
4. **What does it cost?** Transitive dependencies added, binary/bundle size
   delta, license, maintenance signal (last release date, open critical
   issues), the learning tax on the team, and the exit cost if it is wrong.
5. **Verdict, recorded.** Adopt / reject / adopt-with-revised-expectation —
   with the measured numbers — in an ADR or the PR description
   (architecture-contract owns ADR form). The recorded verdict is what stops
   the same debate recurring in six months.

**Illustrative micro-example:** the fictional `TurboCache` library claims
"10× faster reads". Demonstration designed for HERE: 1M keys, 2 KB values
(project's real median value size, sampled), 90/10 read/write, same runtime.
Result via Recipe 3: median read 41 µs vs current 58 µs, intervals
non-overlapping → CONCLUSIVE, but effect is **1.4×, not 10×** (the 10× was
measured on 16-byte values). Cost: +7 transitive deps, +2.1 MB image.
Verdict recorded: rejected — 1.4× does not buy the migration risk. Total
spike cost: 4 hours. Cost of adopting on faith: a quarter.

**Done means:** the five answers written down, including the demonstration's
raw numbers, in a place the next proposer will find.

---

### Failure modes of this skill itself

| Trap | Symptom | Counter |
|---|---|---|
| Proof theater | Property test whose property is `result == result` | Recipe 1 step 4: sabotage the code, watch it fail |
| Benchmarking the wrong thing | Micro-benchmark conclusive, production unchanged | Demonstration must use project workload shape (Recipe 6 step 2) |
| Estimate never revisited | Fermi doc says 2.4 GB, prod at 9 GB, nobody noticed | Estimate must name the metric to compare and who checks (Recipe 4 step 4) |
| Analysis as delay tactic | Week-long FMEA for a log-message change | Recipes trigger on boundaries/claims/budgets, not on every change |
| Ratio without model | "It got 96× slower at 10×" with no complexity claim | Predicted ratio written before measuring, always |

## 4. Worked example

**Illustrative example — all names and numbers fictional.** The `larkspur`
ingest service (Python) must start accepting 50k-row vendor CSV uploads;
a teammate proposes adopting the `SpeedRows` parsing library "because it's
much faster than the stdlib".

1. **Recipe 4 first (does the design fit?):** budget = 30 s upload-to-ack
   SLA, 4 GB pod. Demand: 50k rows × ~400 B ≈ 20 MB per file, ≤ 5 concurrent
   uploads ≈ 100 MB peak. Verdict: memory is a non-issue (30× headroom);
   the SLA is the only real budget. Written into the ticket.
2. **Recipe 6 (prove SpeedRows):** claim = "much faster" → sharpened to
   "parses our 50k-row file at least 2× faster than `csv` stdlib, else not
   worth a dependency". Demonstration: parse one real-shaped 50k-row file,
   both parsers, same pod image.
3. **Recipe 3 (run it honestly):** 3 warmup + 12 measured runs each.
   stdlib: min 1.91 s, median 2.02 s, p95 2.31 s. SpeedRows: min 1.74 s,
   median 1.88 s, p95 2.19 s. `bench_verdict.py` → intervals [1.91, 2.31] vs
   [1.74, 2.19] overlap → **INCONCLUSIVE**. Recorded verdict: rejected; the
   stdlib parse is 2 s against a 30 s SLA anyway. Two claims died for the
   price of one afternoon.
4. **Recipe 5 (what breaks at the boundary?):** the 8-question prompt on the
   upload boundary yields 9 modes; top scorer (18) is "columns reordered by
   vendor, silently mis-mapped". Mitigation: strict header validation +
   per-import summary report. Added as acceptance tests.
5. **Recipe 1 (the one algorithm written by hand):** row-dedup keeps first
   occurrence per vendor key. Invariants I1–I3 stated; `hypothesis` property
   test added; sabotage check (dropping the `seen` update) fails the test in
   0.2 s with a 2-element counterexample.

Outcome recorded in the PR: no new dependency, two invariant-backed tests,
an FMEA table in the design note, and a written estimate the on-call can
falsify. That PR description *is* the proof artifact.

## 5. Instantiate for your project

Produce `<PROJECT>-proof-and-analysis` in the target repo. A Sonnet-class
model can execute these steps unaided.

**Step 1 — Discover the project's claim surface (run, don't guess):**

```bash
git log --oneline -50                          # recent change themes
git log -i --grep="perf\|faster\|optimi" --oneline   # past performance claims
grep -ri "TODO\|FIXME" --include="*.md" -l docs/ 2>/dev/null  # stated-but-unproven intents
ls *.csproj *.sln package.json pyproject.toml setup.py go.mod Cargo.toml 2>/dev/null
```

From the manifest(s), record: language(s), test framework, whether a
property-based library (`hypothesis`, `fast-check`, `FsCheck`, or ecosystem
equivalent) is already a dependency, and any existing benchmark harness
(`benchmarks/`, `pytest-benchmark`, `BenchmarkDotNet`, `criterion`, etc.).

**Step 2 — Find the hot paths and boundaries.** List the ≤5 code paths where
performance or correctness claims actually matter (entry points, per-request
loops, batch jobs) and every external boundary (Recipe 5's list). Evidence
bar: each entry cites a file path that exists in the repo, verified by
opening it — no path may be listed from memory.

**Step 3 — Fill the skeleton:**

```markdown
---
name: <PROJECT>-proof-and-analysis
description: <project-specific triggers: the actual hot paths and recurring claim types>
---
## Property-testing setup        # exact install + run commands FOR THIS REPO, executed once
## Benchmark protocol            # <BENCH-CMD>, warmup/run counts, where samples land,
                                 # bench_verdict.py invocation used here
## Standing budgets              # real memory/latency/throughput budgets WITH SOURCE
## Boundary register             # this repo's Recipe-5 boundary list
## Adoption log                  # Recipe-6 verdicts to date (link ADRs)
## Estimates on record           # live Fermi estimates + the metric that falsifies each
```

**Step 4 — Evidence before ink.** Do not fill a section you have not
executed: the property-testing section requires one passing property test
committed and one sabotage run observed failing; the benchmark protocol
requires one full run of `bench_verdict.py` on real project samples with its
output pasted; every budget line requires a source (config file, SLA doc,
infra console) named. Copy `scripts/bench_verdict.py` into the instantiated
skill's `scripts/` and re-run it there once (`python3 scripts/bench_verdict.py
--help` at minimum) to prove the copy works.

**Step 5 — Wire cross-references** to the project's instantiated
diagnostics-and-tooling (measurement mechanics), research-discipline
(predict-before-run), and validation-and-qa (acceptance thresholds) skills,
then add a provenance section (date, repo commit, what was actually run).

## 6. Provenance and maintenance

- Authored 2026-07-06 against no specific project; all project facts in
  examples are fictional and labeled.
- Verified at authoring time:
  - `hypothesis` (PyPI), `fast-check` (npm, v4.8.0 current), `FsCheck`
    (NuGet) — names checked against their registries; the Recipe 1 Python
    example was executed and passed under hypothesis on Python 3.10, in a
    since-discarded environment and with a reference `dedupe_keep_first`
    supplied (the printed snippet alone does not define it) — re-verify by
    installing hypothesis and supplying an implementation.
  - `scripts/bench_verdict.py` executed in all modes (conclusive,
    inconclusive, too-few-samples error, `--report json`) on Python 3.10.
  - `hyperfine` flags `--warmup`, `--runs`, `--export-markdown` checked
    against its upstream README.
- Volatile parts — re-verify before relying on them:
  - Library names/majors: `pip index versions hypothesis` (or
    `pip install hypothesis==` to list), `npm view fast-check version`,
    NuGet search for `FsCheck`.
  - `hyperfine` flags: `hyperfine --help`.
  - The overlap decision rule is a **heuristic**, deliberately conservative;
    the S/L/D scoring in Recipe 5 and the "≥4× headroom" threshold in
    Recipe 4 are judgment-call defaults (candidate practice) — tune per
    project and record the tuning.
- Windows note: on machines where `python` is a Microsoft Store stub, invoke
  the script with `py` instead of `python3`.
- Instantiated copies must add their own provenance: date, commit hash, and
  the list of demonstrations actually run.
