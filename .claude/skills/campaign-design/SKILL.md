---
name: campaign-design
description: Load this skill when a problem is too big for one debugging session — a persistent performance regression, memory leak, flaky-test epidemic, data-corruption hunt, or data/platform migration that has already burned multiple attempts — and you need to turn it into a written, executable, decision-gated campaign that a junior engineer or Sonnet-class model can run without judgment calls. Also load it when asked to "plan an investigation", "write a campaign doc", "make this resumable", or when a fresh session must pick up a half-finished multi-day effort. Delivers the campaign document format: numbered phases with exact commands, numeric gates, branch rules, a ranked solution menu, fenced wrong paths, kill criteria, and a promotion protocol.
---

# Campaign Design

## Purpose

This skill teaches you to convert a project's hardest live problem into a **campaign**: a written plan of numbered phases where every step is a copy-pasteable command, every checkpoint is a number compared against a pre-written expectation, and every possible outcome — including failure — has a pre-decided next move. A correctly designed campaign can be executed, paused, and resumed by someone with zero context, because all judgment was spent at design time, not run time.

## When to use / When NOT to use

**Use when ALL of these hold:**
- The problem has survived at least one ordinary debugging session (or is obviously multi-session).
- Progress is measurable by a command, at least in principle (latency, RSS, failure rate, byte diff).
- More than one person/session/model may work on it, or work will span days.

**Do NOT use when:** the problem is a single-session bug (just debug it), the fix is already known (just do it under change-control), or the problem cannot yet be measured (build the measurement first — see diagnostics-and-tooling).

| If instead you need... | Use sibling skill |
|---|---|
| A symptom→triage table for everyday bugs | debugging-playbook |
| To find out what was already tried and why it failed | failure-archaeology |
| To build the measurement tool a campaign needs | diagnostics-and-tooling |
| To discharge a theory obligation before implementing a fix | proof-and-analysis |
| To land the winning change in the codebase | change-control |
| To decide whether a raw hunch deserves investigation at all | research-discipline |
| Evidence standards and golden/certified baselines | validation-and-qa |

Pipeline position: research-discipline vets the hunch → **campaign-design structures the hunt** → proof-and-analysis proves the chosen fix's theory → change-control lands it → failure-archaeology records what the campaign learned.

## Core doctrine

### 1. Vocabulary (defined once, used exactly)

| Term | Definition |
|---|---|
| **Campaign** | A written document (`docs/campaigns/<SLUG>.md` or equivalent) that fully specifies a multi-phase investigation/fix effort. The doc IS the campaign; work not in the doc did not happen. |
| **Phase** | A numbered unit of work with one objective, exact commands, and exactly one gate at its end. |
| **Gate** | A pass/fail checkpoint decided by comparing command output against a number or string written down BEFORE the command was run. |
| **Branch rule** | A pre-written instruction of the form "if you observe X instead of the expected Y → go to phase N / abandon this branch / kill the campaign". |
| **Solution menu** | The ranked list of candidate fixes, each with its theory obligations, written before any fix is attempted. |
| **Theory obligation** | A thing that must be PROVEN (per proof-and-analysis) before a candidate fix may be implemented — e.g. "derive the expected query count and show the fix achieves it". |
| **Fence** | An explicit do-not-enter marker around a path already known to fail, with the evidence for why. |
| **Promotion** | Moving a campaign result (a fix, a config change, a new baseline) into the real codebase. Always via change-control. |
| **Kill criteria** | Conditions, fixed at design time, under which the campaign is stopped and written off. |

### 2. Entry check — does this problem deserve a campaign?

Run this checklist. If any item fails, do not write a campaign yet; do the prerequisite instead.

1. **Measurable:** There is a command whose output number/string tracks the problem. If not → build it first (diagnostics-and-tooling), because every gate depends on it.
2. **Reproducible enough:** You can trigger or observe the symptom on demand, or on a known schedule. Intermittent-only symptoms need a detection harness before phase design.
3. **Archaeology done:** You have searched history for prior attempts (see failure-archaeology). Every prior failed attempt becomes a fence (section 6). Skipping this step is how campaigns re-fight settled battles.
4. **Worth it:** Estimated cost (sessions) is written down, and someone accountable agreed the problem justifies it.

### 3. Campaign document anatomy

Every campaign doc has these sections in this order. The skeleton below is the format; copy it verbatim when starting a campaign.

```markdown
# Campaign: <one-line problem statement with the current bad NUMBER in it>

## Status block   <!-- updated every session; a fresh session reads ONLY this to resume -->
- State: DESIGN | RUNNING | BLOCKED | KILLED | PROMOTED
- Current phase: <N> (<phase status>)
- Phase ledger: 0=PASSED 1=PASSED 2=IN-PROGRESS 3=NOT-STARTED ...
- Last session: <DATE> — <one line of what happened>
- Next action: <the exact next command to run>

## Problem statement
- Symptom, with the measured number: <e.g. "p95 GET /orders = 412 ms; SLO is 200 ms">
- Measurement command: <exact command that produces the number>
- First seen / suspected window: <date or commit range, with evidence>

## Success criteria (numeric, fixed now, never edited after RUNNING)
- <METRIC> <COMPARATOR> <NUMBER> measured by <COMMAND>, over <SAMPLE-SIZE/RUNS>

## Kill criteria (fixed now)
- <e.g. "more than 6 sessions consumed", "phase 1 fails twice", "premise P invalidated">

## Fenced wrong paths          <!-- section 6 format -->
## Solution menu               <!-- section 5 format -->

## Phase 0..N                  <!-- each phase: Objective / Commands / EXPECTED / Gate / Branch rules -->

## Session log                 <!-- append-only: date, commands run, numbers observed, decision taken -->
```

**Phase format** — every phase must contain all five parts:

```markdown
### Phase 2: <objective in one line>
Status: NOT-STARTED | IN-PROGRESS | PASSED | FAILED→<branch taken>
Commands:
    <exact copy-pasteable commands, in order>
EXPECTED:
    <the numbers/strings you predict the commands will print, written BEFORE running>
Gate: PASS if <output condition, mechanically checkable>.
Branch rules:
    - If <specific other observation> → <go to phase N / abandon branch / kill>.
    - If output matches neither EXPECTED nor any branch → STOP, log verbatim output,
      return to DESIGN state. (This rule is mandatory in every phase.)
```

Predicting the EXPECTED numbers before running is not decoration — it is the discipline that catches wrong mental models early. This is the same predict-before-run rule as research-discipline; a campaign phase is a small pre-registered experiment.

### 4. Gate design rules

1. **Command-checkable, never judgment-checkable.** A gate must be decidable from command output by string/number comparison. "Profile looks better" is not a gate. "`p95 <= 190` printed by `scripts/measure_p95.sh`" is a gate. If you catch yourself writing "verify that it seems", stop and build the measurement (diagnostics-and-tooling).
2. **Numbers set in advance, with tolerance.** Every numeric gate states the threshold AND the sample size / repetition ("p95 ≤ 190 ms on 3 consecutive 200-request runs"), because single-shot numbers lie. For what a statistically honest threshold looks like, see proof-and-analysis.
3. **Every gate has at least one failure branch.** A campaign whose every phase assumes success is a fantasy, not a plan. If you cannot say what you'd do when a gate fails, you have not understood the phase.
4. **The catch-all branch is mandatory.** Reality will produce outputs you did not enumerate. Every phase ends with: "matches nothing above → stop, log verbatim, back to DESIGN." Improvising at run time is the failure mode this whole skill exists to prevent.
5. **Gates are one-way doors forward, not backward.** A PASSED phase is never silently re-opened. If a later phase invalidates it, the campaign returns to DESIGN state and the doc records why.

### 5. Solution menu format

Write the menu during DESIGN, before any fix is attempted, ranked by (expected effectiveness × confidence) ÷ cost — this ranking is a heuristic, and the doc must record the reasoning, not just the order. Format:

```markdown
## Solution menu
| Rank | Candidate | Theory obligations (prove BEFORE implementing) | Est. cost | Risk if wrong |
|---|---|---|---|---|
| 1 | <APPROACH-A> | <derivation/invariant/measurement that must hold — see proof-and-analysis> | <SESSIONS> | <BLAST-RADIUS> |
| 2 | <APPROACH-B> | ... | ... | ... |
```

Rules:
- **No candidate may be implemented until its theory obligations are discharged** and the discharge (a derivation, a measurement, an invariant argument) is linked from the doc. "It'll probably help" discharges nothing. proof-and-analysis owns the recipes for discharging.
- A candidate whose obligation is refuted moves to Fenced wrong paths with the refutation as evidence. This is a success, not a failure — the menu shrank for a reason.
- The menu is append-allowed (new ideas get added with obligations) but never silently reordered; re-ranking is a logged decision.

### 6. Fenced wrong paths

A fence marks a path that history has already shown to fail, so that a tired engineer or a fresh model does not walk it again. Fences come from failure-archaeology (prior commits/issues/incidents) or from refuted menu candidates. Format — all three parts are required:

```markdown
## Fenced wrong paths
### FENCE: <the tempting action, phrased as the temptation> 
- What it looks like when you're tempted: <the observation that makes this path attractive>
- Why it fails: <the mechanism>
- Evidence: <commit hash / issue link / archaeology entry / campaign session-log line>
```

A fence without evidence is just an opinion and will (rightly) be ignored; if you cannot cite evidence, either go get it or don't write the fence. Conversely, an executor who wants to cross a fence must first refute its evidence in writing in the session log — that is the only legal crossing.

### 7. Validation-and-promotion protocol

1. **Success criteria are numeric and frozen at design time.** They live in the doc's "Success criteria" section and are never edited once the campaign is RUNNING. If they turn out to be wrong, the campaign is killed and a new one designed — moving goalposts inside a live campaign destroys the evidence trail.
2. **Measured, never judged by eye.** The final validation runs the SAME measurement command as the baseline (same machine class, same sample size, same flags), and the doc records both numbers side by side. "It feels faster" has zero evidentiary weight; see validation-and-qa for what counts as evidence.
3. **Validation is repeated.** Minimum 3 independent runs meeting the criterion, or whatever repetition the criterion itself specifies. One green run is an anecdote.
4. **Promotion routes through change-control, never around it.** A campaign confers zero special landing rights: the winning change is classified, reviewed, and gated exactly like any other change of its class. The campaign doc links the change; the change links the campaign doc.
5. **After promotion:** set State: PROMOTED, write the closing summary (root cause, what was measured, what was fenced), and file the whole campaign into failure-archaeology so the next hunt starts warmer.

### 8. Campaign hygiene

- **Session log is append-only** and every session appends: date, phases touched, exact commands run, verbatim key numbers, decision taken and which branch rule justified it. A number observed but not logged does not exist.
- **The resumability test:** at the end of every session, ask "could a fresh session with ONLY this doc continue correctly?" Concretely: the Status block names the exact next command, the phase ledger is current, and no needed context lives only in a terminal scrollback or someone's head. If the answer is no, the session is not over — fix the doc first.
- **Status tracking per phase** uses only the four states NOT-STARTED / IN-PROGRESS / PASSED / FAILED→branch. No "mostly done".
- **One campaign, one doc, one problem.** If a campaign discovers a second problem, that spawns a new entry in the backlog (or its own campaign), never a side-quest inside this doc.

### 9. Kill criteria

Defined at design time, because at run time sunk cost makes everyone a bad judge. Standard kill triggers (pick and instantiate at least two):

- **Budget:** more than `<N>` sessions or `<H>` hours consumed.
- **Premise invalidation:** a phase observation contradicts the problem statement (e.g. the regression reproduces on the "good" baseline too).
- **Repeated gate failure:** the same gate fails `<K>` times after redesign.
- **Menu exhaustion:** every solution-menu candidate is fenced or refuted.

Killing a campaign is a defined, respectable outcome: set State: KILLED, write the closing summary, file to failure-archaeology. A killed campaign with a clean evidence trail is worth more than a zombie campaign nobody dares to stop.

### 10. Failure modes of campaign design itself

| Failure mode | Symptom | Correction |
|---|---|---|
| Fantasy plan | No failure branches; every phase assumes success | Rule 4.3 — add a failure branch to every gate or the design is rejected |
| Judgment gates | Gates like "confirm it looks healthy" | Rewrite as command-output comparison; build tooling if needed |
| Retroactive expectations | EXPECTED filled in after running the commands | EXPECTED is written in the doc, committed/saved, before execution; the session log timestamps both |
| Goalpost drift | Success criteria edited mid-campaign | Freeze rule 7.1; kill and redesign instead |
| Scrollback amnesia | Key numbers only in the terminal, doc stale | Resumability test at end of every session |
| Fence trampling | Re-trying a known-failed approach | Fences with evidence + the written-refutation crossing rule |
| Zombie campaign | No kill criteria, effort dribbles on for weeks | Kill criteria at design time, at least two |

## Worked example — Illustrative example (all names, numbers, and history are fictional)

Project: **Lanternfish**, a fictional HTTP order service. Problem: p95 latency of `GET /orders` regressed from ~160 ms to ~410 ms sometime in the last two weeks. SLO is 200 ms. Below is the campaign doc, abridged to show the format with real command patterns.

```markdown
# Campaign: p95 GET /orders = 410 ms (SLO 200 ms), regressed in last 2 weeks

## Status block
- State: RUNNING · Current phase: 1 (IN-PROGRESS)
- Phase ledger: 0=PASSED 1=IN-PROGRESS 2=NOT-STARTED
- Last session: 2026-07-05 — baseline reproduced, bisect started (4 of ~9 steps done)
- Next action: `git bisect run ./scripts/p95_gate.sh` (continue)

## Problem statement
- Measurement command (200 sequential requests against a locally run rev):
    for i in $(seq 1 200); do
      curl -s -o /dev/null -w '%{time_total}\n' http://localhost:8080/orders?id=42
    done > times.txt
    sort -n times.txt | awk '{a[NR]=$1} END{print "p95_s:", a[int(NR*0.95)]}'
- Observed on HEAD: p95_s ≈ 0.41. First bad window: tag v2.31 (2026-06-20) .. HEAD (~480 commits).

## Success criteria (frozen 2026-07-04)
- p95_s ≤ 0.190 by the measurement command above, on 3 consecutive runs, warm service, same machine.

## Kill criteria (frozen 2026-07-04)
- >5 sessions consumed, OR Phase 0 shows v2.31 is also ≥ 0.30 (premise dead), OR menu exhausted.

## Fenced wrong paths
### FENCE: "Just raise the DB connection pool from 20 to 100"
- Tempting when: pool-wait warnings appear in logs during load, so a bigger pool "obviously" helps.
- Why it fails: pool waits are a downstream symptom; the regression is per-request work, and a
  larger pool only moves the queue into the database and worsens tail latency under load.
- Evidence: failure-archaeology entry FA-0142 — commit `a1b2c3d` (fictional) tried pool=100 in a
  prior incident; p95 unchanged (0.40 → 0.39), DB CPU +35%, reverted in `d4e5f6a`.

## Solution menu (design-time; obligations per proof-and-analysis)
| Rank | Candidate | Theory obligations (prove BEFORE implementing) | Cost | Risk |
|---|---|---|---|---|
| 1 | Fix/revert offending commit found by bisect | Show mechanism: derive expected per-request DB round-trips before vs after the commit and confirm by query log count | 1 session | low |
| 2 | Cache order lookups (TTL 30 s) | Prove hit rate ≥ 80% from access-log key distribution AND prove 30 s staleness is acceptable per order-state invariants | 2 sessions | medium (staleness) |

### Phase 0: Reproduce and pin the baseline
Status: PASSED (2026-07-04)
Commands:
    git checkout v2.31 && <BUILD-CMD> && <RUN-CMD> &      # then run measurement command
    git checkout <HEAD-SHA> && <BUILD-CMD> && <RUN-CMD> & # then run measurement command
EXPECTED:
    v2.31: p95_s in 0.14–0.19        HEAD: p95_s in 0.35–0.50
Gate: PASS if v2.31 p95_s ≤ 0.20 AND HEAD p95_s ≥ 0.30 (each on 2 runs).
Branch rules:
    - If v2.31 ALSO ≥ 0.30 → environment/premise problem, not a code regression → KILL per criteria.
    - If HEAD ≤ 0.20 → not reproducible locally → abandon local branch; redesign around
      production profiling (new Phase 0b) before any bisect.
    - Matches nothing above → stop, log verbatim, back to DESIGN.
Observed (session log 2026-07-04): v2.31 p95_s = 0.162, 0.158; HEAD = 0.407, 0.415 → PASS.

### Phase 1: Localize the offending commit by bisect
Status: IN-PROGRESS
Commands:
    # scripts/p95_gate.sh — builds, starts service, measures; exits 0 if p95_s <= 0.25, else 1,
    # exit 125 if the rev fails to build (tells bisect to skip).
    git bisect start <HEAD-SHA> v2.31
    git bisect run ./scripts/p95_gate.sh
EXPECTED:
    ~9 bisect steps (log2 of ~480 commits); final line "<SHA> is the first bad commit".
Gate: PASS if bisect names exactly one first-bad commit AND re-measuring that commit vs its
      parent shows a p95_s jump ≥ 0.15 (confirmation run, 2 runs each side).
Branch rules:
    - If bisect result does NOT confirm (jump < 0.15 on re-measure) → threshold flapping; raise
      sample to 500 requests, `git bisect reset`, rerun ONCE. Second flap → abandon bisect,
      go to Phase 1b (differential profiling of v2.31 vs HEAD) — do NOT bisect a noisy metric a third time.
    - If >15 steps or many `skip`s (broken builds) → abandon bisect, go to Phase 1b.
    - Matches nothing above → stop, log verbatim, back to DESIGN.

### Phase 2: Implement from menu, validate, promote
Status: NOT-STARTED
Commands (menu rank 1 path):
    # 1. Discharge obligation: count queries per request on bad commit vs parent:
    #    grep -c 'SELECT' <QUERY-LOG> per single request, both revs; derive expected counts first.
    # 2. Implement fix on a branch; run measurement command 3 times.
EXPECTED:
    Query count: parent = 3/request, bad commit = 3 + N (N = order line items → N+1 pattern).
    After fix: 3/request; p95_s ≤ 0.190 on 3 consecutive runs.
Gate: PASS if success criteria met verbatim (§ Success criteria) — measured, never judged by eye.
Branch rules:
    - If obligation fails (query counts equal) → mechanism wrong → return menu rank 1 to DESIGN,
      attempt rank 2 only after ITS obligations are discharged.
    - If p95_s ∈ (0.190, 0.25] → partial win is NOT a pass; back to DESIGN with the new numbers.
    - Matches nothing above → stop, log verbatim, back to DESIGN.
Promotion: open the change through change-control as class <CHANGE-CLASS>; link this doc in the
change description; do not merge on campaign authority. After merge: State→PROMOTED, closing
summary written, doc filed to failure-archaeology.
```

Note what makes this executable by a zero-context session: every command is literal, every gate is a number fixed in advance, both failure branches per phase are pre-decided, the fence carries evidence, and the Status block names the exact next command.

## Instantiate for your project

Goal: produce `.claude/skills/<PROJECT>-campaign-design/SKILL.md` containing (a) the house campaign template with project-real commands, and (b) the live campaign backlog. Steps:

1. **Find the hardest live problems (candidates for campaigns).** Run and record:
   ```
   git log --oneline --since="3 months ago" | wc -l                  # activity level
   git log --format="%h %ad %s" --date=short --since="6 months ago" | grep -iE 'revert|fix.*again|workaround|flaky|leak|regress' 
   grep -rn -iE 'TODO|FIXME|HACK' --include=<SOURCE-GLOB> | wc -l    # then eyeball the top files
   ```
   Plus the issue tracker: oldest open P1/P2s, issues reopened more than once. Cross-check against the project's failure-archaeology skill if it exists.
2. **For each candidate, run the entry check (doctrine §2).** Evidence rule: you may not list a problem as campaign-worthy unless you can paste (i) a measurement command you actually ran and its output, and (ii) at least one citation (issue, commit, incident) showing prior cost. No reproduced measurement → it goes in a "needs measurement first" list pointing at diagnostics-and-tooling instead.
3. **Bind the template to the project.** Copy the §3 skeleton into the project skill and replace every placeholder with real values you have verified by running them once: `<BUILD-CMD>`, `<RUN-CMD>`, the measurement command(s), where campaign docs live (create `docs/campaigns/` if the project has no convention), and the change-control class table reference for the Promotion line.
4. **Harvest fences.** From the project's failure-archaeology (or, lacking one, from `git log --grep="revert" --oneline` plus linked issues), write the standing fences that apply project-wide (approaches tried and reverted). Evidence rule: every fence cites a real commit hash or issue ID you have opened and read — no folklore fences.
5. **Write one real campaign** for the top candidate, through DESIGN state only (problem statement, frozen success + kill criteria, fences, solution menu with obligations, Phase 0). Do not start RUNNING it inside the instantiation task.
6. **Skeleton for the project skill:**
   ```markdown
   ---
   name: <PROJECT>-campaign-design
   description: House campaign format and live campaign backlog for <PROJECT>. Load before starting/resuming any multi-session investigation.
   ---
   # <PROJECT> Campaigns
   ## House rules (deltas from library campaign-design, if any)
   ## Where campaigns live: <PATH>; naming: <SLUG-CONVENTION>
   ## Verified command bindings: <BUILD-CMD>=..., <RUN-CMD>=..., measurement commands (each run once, output pasted)
   ## Standing fences (project-wide, each with commit/issue evidence)
   ## Live campaigns: <table: slug | state | current phase | next action>
   ## Backlog: <table: candidate | measurement + output | prior-cost citation | est. sessions>
   ## Provenance: instantiated <DATE> from library campaign-design; evidence sources listed per entry
   ```
7. **Review gate before committing the instantiated skill:** every command in it was executed once with output captured; every fence and backlog citation resolves to a real artifact; the one DESIGN-state campaign passes doctrine §10's failure-mode table (walk it row by row).

## Provenance and maintenance

- Authored 2026-07-06 against no specific project; all examples fictional and labeled.
- Verified on the authoring machine: `git bisect start/run` usage and exit-125 skip convention (`git bisect -h`), `git log --oneline --since=... `, `git log -S<STRING>`, `git log --format="%h %ad %s" --date=short` (throwaway repo), `curl -s -o /dev/null -w '%{time_total}\n'` (live request), and the `sort -n | awk` p95 snippet (returns 95 for input 1..100).
- Volatile parts and re-verification one-liners:
  - curl `--write-out` variables: `curl --help all | grep -A1 write-out` (or `man curl`).
  - git bisect flags / exit-code convention: `git bisect -h` and `git help bisect`.
  - The p95 awk snippet uses nearest-rank on a sorted file; for anything load-bearing prefer a tested script from diagnostics-and-tooling.
- The p95 measurement loop (sequential curl) measures single-client latency only; it is an illustrative pattern, not a benchmarking method — real campaigns should bind a proper load tool and consult proof-and-analysis for statistical treatment.
- Instantiated copies must add their own provenance block: date, repo commit at instantiation, and per-entry evidence sources.
