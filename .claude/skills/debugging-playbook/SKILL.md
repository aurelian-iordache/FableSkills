---
name: debugging-playbook
description: Load this when a bug, test failure, regression, crash, wrong output, or "it worked yesterday" report needs diagnosing — or when the user asks to "debug", "figure out why", "track down", "bisect", or "build a triage table" for a project. Delivers the discipline of systematic debugging (discriminating experiments, git bisect, anti-shotgun rules) plus the format and evidence rules for building a project-specific symptom→triage table and trap records.
---

# Debugging Playbook

## Purpose

This skill makes you able to (1) run a debugging investigation as a sequence of
discriminating experiments instead of guesswork, (2) use `git bisect` correctly to
localize regressions, and (3) build and maintain a project's **symptom→triage table**
and **trap records** so the next person starts from the second rung of the ladder,
not the ground.

## When to use / When NOT to use

**Use when:** something behaves wrongly and the cause is unknown; a regression appeared
between two known states; you are about to guess-and-edit code hoping the bug goes away
(stop — use this instead); or you are instantiating this library for a project and need
its `<PROJECT>-debugging-playbook`.

**Do NOT use when** the cause is already known and you just need to fix and verify it,
or when the real task is one of these:

| If instead you need... | Use sibling skill |
|---|---|
| A permanent chronicle of closed investigations (root cause + evidence) | failure-archaeology |
| To build a measurement tool because eyeballing is failing | diagnostics-and-tooling |
| To decide what counts as proof that a fix works | validation-and-qa |
| A multi-week attack plan on one hard live problem | campaign-design |
| Environment/build breakage (not product behavior) | build-and-env |
| Evidence standards for a research-grade hypothesis | research-discipline |
| Cause known — classifying and gating the fix so it can land | change-control |

## Core doctrine

### 1. The debugging loop

Every investigation is this loop. Write each step down (a scratch file is fine — it
becomes the raw material for the triage table later):

1. **Reproduce.** Get a command that fails on demand. If you cannot reproduce, your
   only job is making it reproducible — nothing else you do is trustworthy.
2. **State the symptom precisely.** "Output is wrong" is not a symptom.
   "`<TEST-CMD>` fails with `AssertionError: expected 200 got 503` on the 3rd retry"
   is a symptom.
3. **List competing hypotheses.** Minimum two. If you can only think of one, you are
   pattern-matching, not diagnosing — check the triage table (section 3) for others.
4. **Design a discriminating experiment** (section 2) whose outcome eliminates at
   least one hypothesis whichever way it comes out.
5. **Run it. Record the outcome BEFORE interpreting it.** Predict the result in
   writing first; a surprise is information (see research-discipline for the
   predict-before-running standard).
6. **Repeat until one hypothesis survives.** Then confirm by fixing and un-fixing:
   the bug must disappear with the fix and reappear without it.
7. **Close out:** update the triage table, write a trap record if you fell into one,
   and promote the investigation to failure-archaeology (section 8).

### 2. Discriminating experiments — the core skill

**Definition.** A *discriminating experiment* is an experiment whose possible outcomes
cleanly separate competing hypotheses: outcome A is consistent with hypothesis 1 and
inconsistent with hypothesis 2, and outcome B the reverse. Either result teaches you
something. Contrast with **confirmatory poking**: running things that can only agree
with the hypothesis you already favor ("I added a log line and yes, the function runs"
— which almost every hypothesis also predicted).

**The test for whether your experiment is discriminating:** before running it, fill in
this sentence for EVERY live hypothesis — "If hypothesis H is true, this experiment
will show ___." If two hypotheses fill the blank identically, the experiment cannot
tell them apart. Redesign it.

**Recipe for designing one:**

1. Write the hypotheses as concrete, falsifiable claims about mechanism
   ("the cache returns stale entries after TTL expiry", not "the cache is broken").
2. Find a variable the hypotheses *disagree* about: a timing, an input, an
   environment, a code path, an intermediate value.
3. Build the cheapest intervention that reads or forces that variable:
   - **Read an intermediate:** print/log the value where the hypotheses diverge.
   - **Force a branch:** hardcode an input that makes one hypothesis's mechanism
     impossible (disable the cache, pin the clock, run single-threaded).
   - **Swap a component:** replace the suspect with a known-good stub. If the
     symptom persists, the suspect is exonerated.
   - **Vary one axis:** same code, different data; same data, different machine;
     same everything, different commit (that last one is bisection, section 4).
4. Predict the outcome under each hypothesis, in writing, before running.
5. Run once. Change nothing else between runs — one variable per experiment.

**Cost ordering (heuristic):** prefer experiments that are cheap to run AND kill the
most hypotheses per run. A 5-second log-line check that splits the hypothesis space in
half beats a 40-minute full-suite run that only confirms what you suspected.

### 3. The symptom→triage table

The triage table is the project artifact this skill exists to produce. It maps a
symptom, as a newcomer would observe it, to the *first check that discriminates among
its likely causes*. Format — one row per symptom, exactly these columns:

| Column | Content rules |
|---|---|
| **Symptom** | Verbatim observable: the error text, exit code, or wrong-output description someone would paste into search. Not an interpretation. |
| **First check** | ONE command or observation that best splits the causes below. Must be copy-pasteable or a one-line "look at X" instruction. |
| **Likely causes (ranked)** | Numbered, most-frequent first, with the check outcome that points to each ("if the check shows A → cause 1"). |
| **Trap** | The seductive wrong path people take from this symptom, with a pointer to its trap record (section 5). Write "none recorded" if none. |
| **Source** | Where this row's knowledge comes from: commit hash, issue/PR number, or failure-archaeology entry ID. Never blank. |

**What earns a row (hard rule):** a row may be added ONLY if the author either
(a) personally reproduced the symptom and verified the first check discriminates, or
(b) sourced the row from a specific commit, issue, or failure-archaeology entry cited
in the Source column. Plausible-sounding rows from memory or general knowledge are
forbidden — an unverified triage row sends the next debugger confidently in the wrong
direction, which is worse than no row.

**Row hygiene:**
- If a "first check" ever misleads someone, fix or delete the row that same day.
- Rank causes by observed frequency, not by severity. Re-rank when evidence changes.
- Keep symptoms in the reader's vocabulary (what the terminal shows), not the
  expert's ("stale IR cache" is a cause, not a symptom).

### 4. Bisection discipline

Bisection is the discriminating experiment "same everything, different commit",
applied logarithmically. Use it when the symptom is a **regression**: some past state
verifiably lacked it.

**Preconditions — do not start without all three:**
1. A deterministic reproducer script (flaky reproducers poison bisection; stabilize
   first or wrap the check in enough retries to make the verdict reliable).
2. A verified-bad commit AND a verified-good commit. *Run the reproducer on both* —
   "it worked last month" is a rumor until you check out that commit and see it pass.
3. A build that works across the range (know your `<BUILD-CMD>`; be ready to `skip`).

**Manual bisect:**

```sh
git bisect start <BAD-COMMIT> <GOOD-COMMIT>   # note the order: bad first, then good
# git checks out a midpoint; build and run your reproducer, then:
git bisect good        # this commit does NOT show the bug
git bisect bad         # this commit DOES show the bug
git bisect skip        # this commit cannot be tested (build broken, etc.)
# ...repeat until git prints "<HASH> is the first bad commit"
git bisect log > bisect-log.txt   # save the evidence trail
git bisect reset       # ALWAYS reset when done — returns to your original HEAD
```

**Automated bisect** — write the reproducer as a script whose exit code is the verdict:

- exit **0** → commit is good
- exit **1–127 (except 125)** → commit is bad
- exit **125** → commit untestable, skip it

```sh
git bisect start <BAD-COMMIT> <GOOD-COMMIT>
git bisect run ./repro.sh
git bisect reset
```

Illustrative `repro.sh` skeleton:

```sh
#!/bin/sh
<BUILD-CMD> || exit 125          # can't build here -> skip, don't blame
<TEST-CMD>                       # its exit code becomes the verdict
```

**Bisect judgment calls (heuristics):**
- On heavily-merged histories, `git bisect start --first-parent <BAD> <GOOD>` tests
  only mainline merge points — faster and usually the answer you want ("which merge
  broke it") before drilling into the branch.
- The "first bad commit" is where the symptom *appeared*, which is not always where
  the defect *lives* (a latent bug can be exposed by an innocent change). Read the
  blamed commit's diff and explain the mechanism before declaring root cause.
- If bisect converges on a huge commit, bisect *within* it by reverting hunks, or
  fall back to discriminating experiments on the commit's individual changes.

### 5. Trap records

A **trap** is a symptom→conclusion shortcut that feels right and is wrong, and that
has already cost someone real time. Traps are the most valuable and least recorded
debugging knowledge. Each trap gets its own short story, in this format:

```markdown
### TRAP-<N>: <one-line name>
- What it looked like: <the misleading evidence, verbatim where possible>
- What it actually was: <the real mechanism>
- Time cost: <honest estimate, e.g. "2 days across 2 people">
- The tell: <the observation that SHOULD have discriminated earlier —
  i.e., the discriminating experiment nobody ran>
- Source: <commit / issue / archaeology entry>
```

The "tell" line is mandatory and is the point of the record: it converts a war story
into a reusable first-check. Every trap record should cause either a new triage-table
row or an update to an existing row's Trap column — if it doesn't, ask why not.

### 6. Anti-patterns — hard rules

- **No shotgun debugging.** *Shotgun debugging* = changing several things at once and
  re-running to see if the symptom goes away. It destroys the information each change
  would have given you and produces fixes nobody can explain. Rule: one variable per
  experiment. If you notice you've made two speculative edits without running in
  between, revert to the last known state and restart the loop.
- **No fix-by-coincidence.** If the symptom vanished and you cannot state the
  mechanism by which your change fixed it, it is not fixed — it is dormant. Rule:
  before closing, (a) state the causal chain from defect to symptom in one paragraph,
  and (b) demonstrate un-fix/re-fix: revert the change, watch the symptom return,
  re-apply, watch it disappear. If reverting does NOT bring the symptom back, you
  changed the wrong thing (or the reproducer is unstable) — reopen.
- **No silent timebox overruns.** If 30 minutes of unstructured poking has produced
  no eliminated hypothesis, stop and formally restart the loop at step 3 with written
  hypotheses. (30 min is a heuristic default; instantiated skills may tune it.)

### 7. When to stop and instrument instead

Switch from experimenting to *building instrumentation* (see diagnostics-and-tooling
for how) when any of these holds:

- You have run **3+ experiments and eliminated nothing** — your observables are too
  coarse to discriminate; you need a finer-grained measurement, not another guess.
- The bug is **timing/concurrency/load-dependent** and adding ad-hoc prints changes
  the behavior — you need low-overhead, always-on instrumentation.
- You keep re-deriving the **same intermediate values by hand** every session — that
  computation should be a permanent diagnostic script with an interpretation guide.
- Reproduction requires **rare production conditions** — you need capture/replay or
  logging at the boundary, because interactive experiments can't reach the state.

Instrumentation built during a debugging session is a candidate permanent tool: hand
it to diagnostics-and-tooling discipline (name it, script it, document how to read
its output) rather than deleting it with the branch.

### 8. Closing out: promotion to failure-archaeology

An investigation is **closed** when the fix is merged and un-fix/re-fix was
demonstrated, or when it is consciously abandoned. On close:

1. Write/update the failure-archaeology entry: symptom → root cause → evidence
   (bisect log, experiment outcomes, the causal-chain paragraph) → status. The
   archaeology entry is the *full story*; the triage row is the *fast index into it*.
2. Add or update the triage-table row, citing the new archaeology entry ID in Source.
3. If you fell into a trap, write the trap record (section 5) and link it.
4. If you built instrumentation, promote it per section 7.

Rule of thumb: raw observations live in your scratch notes; only *verified* claims
(reproduced, or evidenced by the merged fix) get promoted into the table, the trap
records, or archaeology. Speculation dies with the scratch file.

## Worked example (illustrative — all names and facts fictional)

Project "Orrery" is a fictional order-matching service. Its instantiated
`orrery-debugging-playbook` triage table, done right:

| Symptom | First check | Likely causes (ranked) | Trap | Source |
|---|---|---|---|---|
| `pytest tests/matching` fails only in CI with `TimeoutError: fill not confirmed after 5.0s` | Run `pytest tests/matching -p no:randomly` locally 10x. Fails? → cause 1. Passes? → cause 2. | 1. Test-order dependency: `test_cancel_all` leaks a paused clock fixture. 2. CI runner CPU throttling pushes confirm past 5 s. | TRAP-3: raising the timeout "fixes" it (see below). | archaeology #14, commit `a3f9c21` |
| API returns HTTP 503 on `/orders` under load, logs show `pool exhausted` | `SELECT count(*) FROM pg_stat_activity WHERE state = 'idle in transaction';` — >20? → cause 1. Near 0? → cause 2. | 1. Leaked transaction in the audit middleware (missing commit on early return). 2. Pool size (10) genuinely too small for the load profile. | none recorded | issue #212 |
| Fill prices off by exactly 1 tick on ~0.1% of orders | Log raw `price_int` at ingress and at match for one failing order ID: differ? → cause 1. Same? → cause 2. | 1. Round-half-even vs round-half-up mismatch between gateway and matcher. 2. Stale tick-size table after instrument reconfig. | TRAP-1: blaming float error — prices are integers end to end. | archaeology #9, commit `77d0b4e` |
| Service exits with code 137 within minutes of deploy | `docker inspect <CONTAINER> --format '{{.State.OOMKilled}}'` — `true`? → cause 1. `false`? → cause 2. | 1. OOM-killed: order-book snapshot cache unbounded since `2c8e1f0`. 2. External SIGKILL from the orchestrator's failed health probe. | none recorded | issue #198 |
| Replay of day `2026-03-14` produces different fills than production did | Diff event *counts* per instrument first (`replay --counts`): counts differ? → cause 1. Counts equal, order differs? → cause 2. | 1. Capture gap: UDP feed drops during capture, replay is missing events. 2. Nondeterministic iteration over the instrument map in the matcher. | TRAP-2: diffing full fills first — 40k-line diffs hide the one missing event. | archaeology #11 |

And one of its trap records:

```markdown
### TRAP-3: The timeout raise that "fixed" CI
- What it looked like: matching tests timed out only in CI; raising the timeout
  5.0 -> 15.0 made CI green for three weeks.
- What it actually was: test_cancel_all leaked a paused fake-clock fixture; any
  test scheduled after it ran against a frozen clock. The 15 s timeout merely
  outlasted the fixture's teardown-by-GC most of the time.
- Time cost: ~3 days total — 0.5 day for the false fix, 2.5 days when it
  resurfaced as "random" failures and had to be re-diagnosed from scratch.
- The tell: failures correlated with test ORDER, not with runner load.
  `pytest -p no:randomly` (fixed order) failed deterministically — a 2-minute
  discriminating check nobody ran.
- Source: archaeology #14, fix commit a3f9c21
```

Why these rows are "done right": every symptom is verbatim-observable; every first
check is one action with an outcome→cause mapping; causes are ranked; sources are
cited; and the traps carry their stories.

## Instantiate for your project

Produce `.claude/skills/<PROJECT>-debugging-playbook/SKILL.md` in the target repo.
A Sonnet-class model can execute these steps unassisted:

**Step 1 — Mine the history for symptoms and fixes.**

```sh
git log --oneline --grep="fix" -i -n 100
git log --oneline --grep="revert" -i -n 50
git log --oneline --grep="flaky\|intermittent\|race\|regression" -i -n 50
git log --stat --follow -n 20 -- <MOST-FIXED-FILE>   # after identifying hotspots:
git log --format=%H --grep="fix" -i | head -50        # candidates for deep reading
```

Identify fix-dense files: `git log --format= --name-only --grep="fix" -i | sort |
uniq -c | sort -rn | head -20`. For each promising fix commit, read the full message
and diff (`git show <HASH>`) and extract: what was the observable symptom, what was
the root cause, what would have discriminated.

**Step 2 — Mine issues/PRs if available.**

```sh
gh issue list --state closed --label bug --limit 100 --json number,title,closedAt
gh pr list --state merged --search "fix" --limit 100 --json number,title
gh issue view <NUMBER> --comments     # for candidates with real diagnosis threads
```

If failure-archaeology has already been instantiated for this project, start from its
entries instead — they are pre-verified sources.

**Step 3 — Draft triage rows, evidence-gated.** For each candidate row, fill the
five columns. HARD GATE before writing any row: either reproduce the symptom now and
verify the first check discriminates, or cite the exact commit/issue in Source. If
you can do neither, the row goes in a `## Unverified candidates` appendix clearly
marked "do not trust until reproduced" — never in the main table.

**Step 4 — Write trap records** for any fix commit whose message or thread shows a
false trail (look for "turned out", "actually", "red herring", reverted-then-refixed
pairs). Estimate time cost from issue open→close dates if not stated; label the
estimate as such.

**Step 5 — Fill the template skeleton:**

```markdown
---
name: <PROJECT>-debugging-playbook
description: Symptom→triage table, traps, and debugging procedure for <PROJECT>.
---
# <PROJECT> Debugging Playbook
## How to debug here
<Reproducer conventions: exact <TEST-CMD>, log locations, how to get a debug build.>
## Triage table
<Rows from Step 3 — main table verified-only.>
## Trap records
<From Step 4.>
## Bisection notes for this repo
<Verified <BUILD-CMD> for repro.sh, known unbuildable ranges to skip,
whether --first-parent is appropriate for this branch topology.>
## When to instrument
<Project-specific thresholds and pointers to <PROJECT>-diagnostics-and-tooling.>
## Unverified candidates
<Quarantined rows awaiting reproduction.>
## Provenance
<Date, commit range mined, which rows are reproduced vs commit-sourced.>
```

**Step 6 — Prove one row end to end.** Before shipping the instantiated skill,
pick one triage row, reproduce its symptom, and run its first check exactly as
written. If the check's outcome does not point to the documented cause, fix the row.
An instantiated playbook with zero proven rows does not ship.

## Provenance and maintenance

- Authored 2026-07-06 against no specific project; all project facts in the worked
  example are fictional and labeled as such.
- **Volatile parts and re-verification:**
  - `git bisect` syntax and `run` exit-code semantics (0 good; 1–127 bad except
    125 = skip): re-verify with `git bisect -h` and the git-bisect man/HTML page.
  - `--first-parent` availability (git ≥ 2.29): `git bisect -h | grep first-parent`.
  - `gh` command flags: `gh issue list --help`, `gh pr list --help`.
  - `pytest -p no:randomly` assumes the `pytest-randomly` plugin (worked example
    only, fictional context).
- The 30-minute timebox and cost-ordering guidance are heuristics, not guarantees.
- Instantiated copies MUST add their own provenance section recording the commit
  range mined, which rows were reproduced vs commit-sourced, and the date — and must
  re-verify rows whose Source commits get reverted.
