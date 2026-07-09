---
name: diagnostics-and-tooling
description: Load this skill when you are about to eyeball program output instead of measuring it — comparing two runs by scrolling, quoting a timing from a single run, saying "looks the same" or "feels faster" — or when the same question about speed, output correctness, or "what changed between runs" has been asked twice and deserves a purpose-built diagnostic tool. Delivers the measure-don't-eyeball doctrine, the DIAGNOSTIC TOOL SPEC format (interpretation guide and blind spots), instrumentation and baseline discipline, and two runnable stdlib-Python scripts: a run-output comparator and a timing-stats harness. For whether a measured number supports a claim, load proof-and-analysis; for root-causing a defect, load debugging-playbook.
---

# diagnostics-and-tooling — Measure, Don't Eyeball

## Purpose

This skill makes you replace visual inspection with measurement. It teaches you to
(a) recognize when a question is being answered by eyeball, (b) build or reuse a small
diagnostic tool that answers it mechanically, (c) document that tool so the next person
can interpret its output without you, and (d) avoid the classic traps of measurement itself.

## When to use / When NOT to use

**Use when:**
- You catch yourself (or a teammate) saying "it looks faster", "the output seems fine",
  "I don't see a difference", or "it usually takes about a second".
- The same question has been asked twice ("how slow is X?", "did Y change the output?").
  Twice is the threshold: a recurring question deserves a tool.
- You are about to compare two runs of anything by scrolling through their output.
- You are adding logging/timing to code and want it to survive past the current bug hunt.

**Do NOT use when:**

| If instead you need... | Use sibling skill |
|---|---|
| Statistical rigor for benchmark claims (sample sizes, significance, "prove it") | proof-and-analysis |
| What counts as acceptance evidence; golden/certified test inventories | validation-and-qa |
| A symptom→triage table for an active bug hunt | debugging-playbook |
| Run/deploy commands and where artifacts land | run-and-operate |
| Designing a multi-phase investigation campaign with decision gates | campaign-design |
| SQL Server-specific instruments (DMVs, SET STATISTICS IO, plans) | sql-server-operations |
| React rendering/bundle measurement (Profiler, build-size baseline) | react-frontend-discipline |

Boundary: this skill builds the *instruments*. proof-and-analysis governs what
*claims* the instrument readings can support; validation-and-qa governs whether a
reading counts as *acceptance evidence*.

## Core doctrine

### 1. The prime rule: eyeballing is for hypotheses only

Eyeballing (reading output, watching a progress bar, "feeling" latency) is permitted for
exactly one purpose: **forming a hypothesis**. It is never permitted for **accepting or
rejecting** one. The moment you move from "I suspect X" to "therefore X" — or to any
action based on X — you need a number, a diff, or a mechanical check.

| Question you keep asking | Eyeball answer (forbidden as evidence) | Tool answer (required) |
|---|---|---|
| "How slow is it?" | "feels like ~2 seconds" | timing harness: median/p95 over N runs (`scripts/timing_stats.py`) |
| "Is the output right?" | "looks the same as before" | mechanical diff vs a recorded baseline (`scripts/compare_runs.py`) |
| "What changed?" | scroll two logs side by side | run comparator with noise (timestamps) filtered out |
| "How often does it fail?" | "happens sometimes" | counter at the failure site, read after N runs |
| "Is it getting worse?" | "seems worse lately" | today's measurement vs recorded baseline |

Corollary (the tooling threshold): **the second time a question is asked, build the tool.**
The first time, a manual measurement is acceptable — but record the command and the number.
The second time, wrap it in a script with a DIAGNOSTIC TOOL SPEC (below). A question asked
twice will be asked ten times.

### 2. The DIAGNOSTIC TOOL SPEC format

Every diagnostic tool — script, dashboard query, log filter — carries this spec, in its
header comment or a `tools.md` beside it. A tool without an interpretation guide produces
numbers nobody can act on; that is eyeballing with extra steps.

```
DIAGNOSTIC TOOL SPEC
  Question it answers : one sentence, phrased as the question users actually ask.
  How to run          : exact copy-pasteable command(s), including where to run them.
  INTERPRETATION GUIDE: for each output (or output range) -> what it means -> what to DO.
                        e.g. "p95 > 2x median -> unstable tail -> do not quote a single
                        number; investigate caching/GC/contention first."
  Known blind spots   : what this tool CANNOT see, so nobody over-trusts it.
                        e.g. "wall clock only; cannot separate CPU from I/O."
```

Checklist for a finished spec — all four must pass:
- [ ] A zero-context reader can run it from the "How to run" line alone (verify: paste the
  command into a fresh shell; it runs).
- [ ] Every output range in the interpretation guide names an *action*, not just a meaning.
- [ ] At least one blind spot is listed. A tool with "no blind spots" was not thought through.
- [ ] The spec lives with the tool (same file or same directory), not in a wiki that will rot.

Both shipped scripts (`scripts/compare_runs.py`, `scripts/timing_stats.py`) carry this spec
in their docstrings — use them as the reference implementations of the format.

### 3. Instrumentation discipline

*Instrumentation* = code you add to a system so it reports on itself (log lines, counters,
timers). Rules:

1. **Structured logging over printf archaeology.** *Printf archaeology* is the anti-pattern
   of sprinkling ad-hoc `print("HERE 3", x)` statements, then deleting them after the hunt —
   so the next hunt starts from zero. Instead, log lines that a machine can filter:
   one event per line, stable event name, `key=value` pairs (or JSON). Illustrative example:
   `EVT=cache_lookup outcome=miss key_hash=a1b2 elapsed_ms=4.2` beats
   `print("cache miss!", key)`.
2. **Counters and timers at boundaries.** Place them where subsystems meet — entry/exit of
   a module, before/after I/O, request in/response out — not scattered through inner logic.
   Boundaries are where blame is assigned ("the 900ms is inside the DB call, not our code"),
   and boundary hooks survive refactors of the interior.
3. **Cheap enough to leave in.** A diagnostic hook you must remove before shipping will be
   removed, and the next incident starts blind. Targets (heuristics, not guarantees):
   a disabled hook should cost roughly a branch check; an enabled counter/timer should stay
   well under ~1% of the operation it wraps. If you cannot make it that cheap, gate it
   behind a config flag (see the config-and-flags approach if that skill is instantiated)
   rather than deleting it.
4. **Every temporary print has a deadline.** If you do resort to a raw print during a hunt,
   either promote it to a structured event or delete it in the same change that closes the
   hunt. Grep-able tag convention for temporaries: mark them `DIAG-TEMP` so
   `grep -rn "DIAG-TEMP" <SRC-DIR>` finds strays. (Candidate practice — adopt the tag your
   project prefers, but have one.)

### 4. Baseline discipline

A *baseline* is a recorded measurement of the system in a known-good, known-configuration
state. **A measurement without a baseline is a number without a meaning** — "median 340ms"
tells you nothing until you know it was 210ms last month on the same input.

| Rule | Practice |
|---|---|
| Baselines are files, not memories | Commit them to the repo, e.g. `<PROJECT>/diag/baselines/` — one file per tool, machine-readable (both shipped scripts have `--json`/`--report json` for this). |
| Every baseline records its conditions | Alongside the numbers: date, commit hash (`git rev-parse HEAD`), machine/OS, input dataset, relevant config. A baseline missing conditions is invalid — you cannot know later whether a change is real or environmental. |
| Re-take on legitimate change | Re-baseline when: hardware/OS/runtime changes, the input dataset changes, or a deliberate accepted change moves the number. Re-baselining to make a regression disappear is falsifying evidence — the re-take commit message must say *why* the old baseline no longer applies. If the baseline or reference output gates CI or acceptance, re-taking it is equivalent to moving an acceptance threshold: re-certify per validation-and-qa and route it through change-control — the commit message alone is not the gate. |
| Compare mechanically | Current run vs baseline goes through the comparator (with explicit tolerances), never through eyeballs. |

Illustrative example of a baseline record (fictional project "Orrery"):

```json
{"tool": "timing_stats", "command": ["orrery", "render", "--scene", "bench1.orr"],
 "median_s": 0.212, "p95_s": 0.239, "runs": 20,
 "taken": "2026-07-06", "commit": "3f9e2ab", "machine": "ci-runner-linux-8core",
 "reason": "initial baseline after v2 renderer accepted"}
```

**Anomaly log.** Keep a dated, append-only file next to the baselines (e.g.
`<PROJECT>/diag/ANOMALIES.md`) recording reproducible-but-unexplained readings — a number
that moved with no known cause, a diff that appears on only one machine. One line each:
date, tool, reading, conditions, and `unexplained`. Do not delete entries when they stop
reproducing; mark them. Review the log when hunting for causes — research-discipline
treats these entries as its primary source of candidate hypotheses.

### 5. Comparison tooling

Never compare two runs' outputs by reading them. Mechanical comparison rules:

1. **Canonicalize first.** Strip or normalize legitimate run-to-run noise — timestamps,
   PIDs, temp paths, random seeds — *by declared rule* (an ignore-pattern list checked into
   the repo), not by squinting past it. `compare_runs.py --ignore-regex` is the mechanism;
   the pattern list is the policy.
2. **Structure-aware beats byte-diff for structured data.** For JSON, compare the parsed
   structure (key order is not a difference; a float 1e-9 off may not be either — but make
   tolerance an explicit flag, defaulting to exact).
3. **Exit codes are the API.** Comparator returns 0 = same, 1 = different, 2 = error, so it
   can gate CI and scripts. A comparator whose result must be read by a human is half a tool.
4. **Every declared tolerance is a decision.** `--abs-tol 1e-4` says "differences below
   1e-4 are noise" — that claim needs a justification recorded next to the baseline
   (what makes it noise: float nondeterminism? measured run-to-run jitter?). See
   validation-and-qa for what counts as an acceptable-difference justification.

### 6. Trap catalog — failure modes of measurement itself

| Trap | What it looks like | Countermeasure |
|---|---|---|
| **Measuring the wrong layer** | Timing the whole CLI (startup + parse + work) when the question is about the work; concluding "the algorithm is slow" from a number dominated by process startup. | State which layer the question is about *before* measuring. Measure one layer deeper too; if the outer number ≈ inner number, fine — if not, your conclusion only applies to the layer you measured. `timing_stats.py` measures whole-process wall clock; that is its documented blind spot. |
| **Observer effect** | Verbose logging enabled *during* the timing run; profiler attached; output piped to a slow terminal — the measurement changes the thing measured. | Measure with production-equivalent settings. Suppress diagnostic output during timing (the harness suppresses child output by default for this reason). If you must observe heavily, report "instrumented" numbers as such. |
| **Averaging away the tail** | "Mean latency improved 10%" while p95 doubled; the mean hides the users having a terrible time. | Always report min / median / p95 (the harness prints all three, and warns when p95 > 2× median). Quote the mean only alongside the distribution, never instead of it. For whether N runs even support a claim about the tail, see proof-and-analysis. |
| **Comparing across changed conditions** | Baseline taken on a laptop on battery, candidate on a desktop; different dataset; different config flag; "it got faster" — no, the machine did. | Baselines carry their conditions (§4). Before comparing, check condition fields match; if any differ, the comparison is void — re-take the baseline under current conditions first. |
| **One-run anecdotes** | A single timing quoted as "the" number; first run includes cold caches. | N runs with warmup discard (`--runs`, `--warmup`). One run is a hypothesis (§1), never a result. |
| **Tool trusted past its blind spots** | Using a wall-clock harness to argue about CPU efficiency; using a JSON comparator to assert byte-identical files. | Read the tool's "Known blind spots" line before citing it. If the spec has none, write them before trusting it. |

## Shipped scripts

Both are stdlib-only Python 3.8+, tested on Windows; paths below are relative to this skill.

| Script | Question it answers | Typical invocation |
|---|---|---|
| `scripts/compare_runs.py` | "Did run B's output differ from run A, and where?" JSON-aware structural diff (with numeric tolerance) or line diff with ignore-patterns. Exit 0 same / 1 different / 2 error. | `python3 scripts/compare_runs.py baseline.json current.json --abs-tol 1e-6` |
| `scripts/timing_stats.py` | "How long does this command take, as a distribution?" N runs, warmup discard, min/median/p95/max/mean/stdev, `--json` for baseline files. Exit 3 if any measured run failed. | `python3 scripts/timing_stats.py --runs 10 --warmup 2 -- <TEST-CMD>` |

On Windows without a `python3` alias, use `py` in place of `python3`. Full specs
(interpretation guide, blind spots) are in each script's docstring: run either with `-h`,
or read the header.

## Worked example (illustrative — all facts fictional)

Project "Orrery" renders planetary scenes. A teammate reports: "the renderer feels slower
since the shading rewrite, and I think the output changed slightly."

1. **Both claims are eyeball claims.** Permitted as hypotheses; now measure.
2. **Timing.** Baseline exists at `diag/baselines/render_bench1.json` (median 0.212s,
   commit 3f9e2ab, ci-runner-linux-8core). We are on the same runner and dataset —
   conditions match, comparison is valid.
   ```
   python3 scripts/timing_stats.py --runs 20 --warmup 3 --json -- orrery render --scene bench1.orr
   ```
   Result: median 0.219s, p95 0.246s. Against baseline median 0.212s that is +3% — within
   this benchmark's recorded run-to-run jitter of ±5% (noted in the baseline file).
   Per interpretation guide: no action; "feels slower" is not supported.
3. **Output.** Render a scene to JSON scene-graph on old and new commits, then:
   ```
   python3 scripts/compare_runs.py old_scene.json new_scene.json --abs-tol 1e-9
   ```
   Exit 1: `[changed] $.nodes[14].shade.specular: A=0.35 B=0.41`. The *second* eyeball
   claim was right — output did change, and now we know exactly where, without reading
   two 40,000-line files.
4. **Close the loop.** The specular change turns out to be intended; the golden output is
   re-certified through the validation-and-qa process, and the timing baseline is *not*
   re-taken (nothing legitimate moved). The teammate's next "feels slower" costs one
   command instead of an afternoon of argument.

## Instantiate for your project

Produce `<PROJECT>-diagnostics-and-tooling` in the target repo. A Sonnet-class model can
follow these steps unaided.

1. **Mine the repo for existing diagnostics** (evidence before writing):
   ```
   git grep -n -i -E "time\.perf_counter|stopwatch|prometheus|statsd|metrics|telemetry" -- .
   git grep -n -E "print\(|console\.log|println!|fmt\.Print" -- <SRC-DIR> | head -50
   git log --oneline --grep="benchmark" --grep="perf" --grep="profil" -i -n 30
   ls <PROJECT>/diag <PROJECT>/bench <PROJECT>/scripts 2>/dev/null
   ```
   Classify what you find: real diagnostic tools (keep, spec them), printf archaeology
   (schedule for cleanup), dormant benchmark harnesses (revive or delete).
2. **List the recurring questions.** From issues/PRs/team chat exports available in the
   repo, collect questions asked ≥2 times about speed, correctness-of-output, or "what
   changed". Each becomes a row in the project skill's tool inventory — with a tool, or a
   marked gap. Do not invent questions; every row cites its source (issue #, commit, doc).
   If no issue/PR/chat sources exist in the repo, record "no recurring-question sources
   found on <DATE>" in the Known-gaps section and seed the inventory from step 1's found
   diagnostics only.
3. **Copy the shipped scripts** into `<PROJECT>/diag/` (or the repo's script home) and run
   each once against a real command/output of the project. Do not list a tool in the
   project skill until you have run it there and captured real output.
4. **Take initial baselines.** For each timing-shaped question: pick the command, run the
   harness with `--json`, save to `<PROJECT>/diag/baselines/<NAME>.json`, and add the
   condition fields (commit, machine, dataset, date, reason). For each output-shaped
   question: capture a current-good output as the comparison reference, and record *why*
   it is believed good (link to the validation-and-qa evidence).
5. **Fill the template skeleton:**
   ```markdown
   ---
   name: <PROJECT>-diagnostics-and-tooling
   description: <triggers specific to this project's recurring questions>
   ---
   # <PROJECT> Diagnostics
   ## Tool inventory        <!-- one DIAGNOSTIC TOOL SPEC per tool; only tools you ran -->
   ## Baselines             <!-- where they live, what conditions each records, re-take log -->
   ## Noise/ignore policy   <!-- the declared ignore-regex list and tolerances, each justified -->
   ## Instrumentation map   <!-- which boundaries have counters/timers; how to enable; cost -->
   ## Known gaps            <!-- recurring questions still lacking a tool, with source refs -->
   ## Provenance            <!-- who instantiated, when, from which commit -->
   ```
   Evidence rule for every blank: a tool row requires a captured run; a baseline row
   requires the committed baseline file; a tolerance requires a written justification;
   a gap row requires the source where the question recurred. No exceptions.
6. **Wire one comparison into CI** (candidate practice): a job that runs the comparator
   against the reference output and fails on exit 1. Start with one high-value output;
   expand only when the noise policy is stable. Once wired, that reference output gates
   CI — changing it follows the gated re-take rule in doctrine §4 (validation-and-qa
   re-certification through change-control).

## Provenance and maintenance

- Authored 2026-07-06 against no specific project; all project facts herein are labeled
  illustrative and fictional.
- Both scripts were executed on Windows 11 with Python 3.10.11 (stdlib only) at authoring
  time: JSON-diff, text-diff-with-ignore-regex, tolerance, `--report json`, identical-input
  (exit 0), timing table, timing `--json`, and failing-command (exit 3) paths all verified.
- Volatile parts and one-line re-verification:
  - Script behavior after any edit: re-run the smoke tests —
    `python3 scripts/compare_runs.py <A> <A>` (expect `IDENTICAL`, exit 0) and
    `python3 scripts/timing_stats.py --runs 2 -- python3 -c "pass"` (expect a stats table).
  - Python availability/launcher name (`python3` vs `py`): `python3 --version || py --version`.
  - Percentile note: `p95` here is linear interpolation over sorted samples; if your
    project standardizes on a different percentile method, document the delta in the
    instantiated skill.
- Instantiated copies must add their own provenance block: date, commit mined, who ran the
  scripts, and where the captured proof runs live.
