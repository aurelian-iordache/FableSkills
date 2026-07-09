---
name: validation-and-qa
description: Load when deciding whether a change is actually proven correct, when someone says "tests pass" / "looks good" / "should work", when setting or moving acceptance thresholds, when adding/updating/deleting tests, when a golden file or snapshot "needs updating", or when a test is flaky (for stack-specific test-writing mechanics — e.g. React component tests — the stack-tier skill owns the how; this skill owns what counts as proof). Delivers the evidence hierarchy (what counts as proof and for what), acceptance-threshold discipline, the certified/golden inventory system, rules for tests that pay rent, a test-taxonomy placement guide, flaky-test quarantine protocol, and coverage-as-a-map practice.
---

# Validation and QA: What Counts as Evidence

## 1. Purpose

This skill makes you able to answer, rigorously, the question "how do we KNOW this change is correct?" — and to build the project machinery (thresholds, golden inventories, test suites) that answers it repeatably. It replaces "tests pass, ship it" and "looks right to me" with a graded evidence standard and a maintained QA system.

## 2. When to use / When NOT to use

Use this skill when:

- You are about to claim a change works, or reviewing someone else's claim.
- You are adding, modifying, or deleting tests, snapshots, or golden files.
- A numeric acceptance criterion (accuracy, latency, error rate) is being set or challenged.
- A test fails intermittently and someone proposes "just re-run it".
- You are standing up QA infrastructure for a new project.

| If instead you need... | Use sibling skill |
|---|---|
| To find WHY something is failing (root-cause hunt) | debugging-playbook |
| To decide whether a change even needs this level of proof, or to gate a threshold change | change-control |
| Mathematical/statistical proof techniques, benchmark rigor, invariant arguments | proof-and-analysis |
| To build measurement tools that produce the observations this skill grades | diagnostics-and-tooling |
| Hypothesis-to-accepted-result discipline for research claims (not code changes) | research-discipline |
| To mine past failures into a searchable record | failure-archaeology |
| Whether a C# dependency deserves an interface/seam so tests can fake it | csharp-code-discipline (its U1 rule) |
| Stack-specific API contract-test mechanics: what an ASP.NET Core error body/status code/OpenAPI drift gate should assert | aspnet-api-discipline (placement rules stay here) |

## 3. Core doctrine

### 3.1 The evidence hierarchy

Definition — **evidence**: an observation, artifact, or argument offered to support the claim "this change does what it is supposed to do and breaks nothing else." Evidence comes in grades. Every claim of correctness must state which grade backs it.

From strongest to weakest:

| Rank | Grade | What it is | Sufficient FOR | NOT sufficient for |
|---|---|---|---|---|
| 1 | **Reproduced-and-observed** | You reproduced the original failing condition (or exercised the new behavior) on the real system, observed the bad outcome, applied the change, and observed the good outcome — with the observations recorded (log excerpt, screenshot, diff of outputs). | Closing a bug; certifying a golden entry; releasing a fix for a production incident. | Proving the change is safe for inputs you did NOT exercise — pair with tests. |
| 2 | **Automated test** | A deterministic test in the suite that failed before the change and passes after (or a new test that pins the new behavior), runnable by anyone via `<TEST-CMD>`. | Regression protection; merge gating; refactor safety. | Behavior the test doesn't reach (environment, config, integration seams the test fakes). A passing test proves only what the test asserts. |
| 3 | **Manual test with recorded output** | A human ran a documented procedure and pasted the actual output (command + result, not a paraphrase) into the PR/issue. | One-off verification of hard-to-automate paths (installer flows, visual layout, third-party sandboxes) — as a stopgap with a follow-up ticket to automate. | Anything that will be touched again. Unrecorded manual tests ("I clicked around, it's fine") are grade 5, not grade 3. |
| 4 | **Reasoning** | A written argument: "this change cannot affect X because Y." Includes code reading, type-system arguments, invariant arguments (see proof-and-analysis). | Justifying scope of testing (why untested paths are safe); trivial mechanical changes (rename with compiler enforcement); prioritizing which experiments to run first. | Anything with runtime behavior, concurrency, external systems, or arithmetic. Reasoning tells you where to look; observation tells you what is true. |
| 5 | **Vibes** | "Should work", "looks right", "it's a small change", pattern-matching to similar past changes. | Deciding what to investigate next. Nothing else. | Everything else. Vibes are a search heuristic, never evidence. |

Operating rules:

- **State the grade.** Every PR description or verification note names its evidence grade explicitly: "Evidence: grade 2 — new test `test_refund_rounds_half_even` fails on main, passes on branch."
- **Match grade to stakes.** The required grade is set by the change class (see change-control for the classification). Heuristic default: user-visible behavior changes need grade 1 or 2; internal refactors need grade 2 plus a grade-4 argument for untested surface; doc/comment changes need none.
- **Grades don't average.** Ten grade-4 arguments do not sum to a grade-2. If the stakes demand grade 2, produce grade 2.
- **Record or it didn't happen.** An observation that isn't captured (output pasted, artifact linked) decays to grade 5 the moment the terminal scrolls.

### 3.2 Acceptance-threshold discipline

Definition — **acceptance threshold**: a numeric pass/fail line for a measured quantity (e.g., "p95 latency ≤ 250 ms", "extraction F1 ≥ 0.92", "binary size delta ≤ +1%").

Rules:

1. **Set BEFORE running, in writing, with rationale.** Before you run the measurement, write down: the metric, the threshold, why that number (derived from a requirement, an SLO, a baseline measurement — not from what you expect the run to produce), and the measurement procedure. Commit this to the repo (e.g., `docs/thresholds.md` or the test itself) or paste it in the tracking issue — somewhere timestamped and diffable.
2. **Run, then compare.** The run either meets the written threshold or it doesn't. No interpretation step.
3. **Loosening a threshold after seeing results is a gated change.** It is sometimes legitimate (the original number was guessed, requirements changed) — but it is never a unilateral edit. It goes through the project's change-control gate: written justification, reviewer sign-off, and the old value + reason for change preserved in the threshold's history. The failure mode this prevents has a name — **ratcheting to green**: quietly loosening thresholds one "reasonable" step at a time until they gate nothing. (Tightening is the ungated direction — see rule 5.)
4. **Thresholds need a measurement spec.** A threshold without a defined procedure (dataset, environment, run count, aggregation) is unenforceable. For statistical questions — how many runs, what variance is acceptable, when a difference is real — see proof-and-analysis.
5. **Direction matters.** Tightening a threshold after seeing results (you did better than required, so you lock in the gain) is allowed without a gate — but it must still be recorded: new value, date, and rationale appended to the threshold's history, and confirm the run you are locking in was not a lucky outlier (a threshold tightened onto one lucky run becomes a permanent flaky gate). Loosening is the gated direction: change-control per rule 3.

### 3.3 The certified/golden inventory

Definition — **golden entry**: a specific input paired with its certified-correct output (a "golden file" / "golden output"), or a certified end-to-end scenario, that the system must keep reproducing. Definition — **certified**: a human (or a documented procedure) verified the output is correct against ground truth — not merely that the system currently produces it.

The trap this system exists to prevent: snapshot-style tests where "the test failed" is routinely resolved by regenerating the snapshot. Within months the goldens certify nothing except "the code does what the code does."

**The inventory.** Maintain one file — `<PROJECT>/tests/golden/INVENTORY.md` (or equivalent) — listing every golden entry. An entry without an inventory row is not golden; it's just a stale fixture. Entry format:

| Field | Content |
|---|---|
| **Scenario** | What input/flow this covers, one line. Link to the input + golden files. |
| **Why golden** | What makes this output ground truth: hand-verified against spec §X, matched a reference implementation, signed off by domain expert, reproduces incident #N's fix. |
| **How to regenerate** | Exact command that produces a candidate output (e.g., `<REGEN-CMD> --case <SCENARIO-ID>`), plus the verification step that promotes candidate → golden. |
| **What breakage means** | The prior: "a diff here usually means X". Tells the investigator whether to suspect the change or the golden. |
| **Last verified** | Date + who/what re-certified it against ground truth (not just "last regenerated"). |

**The re-certification rule (non-negotiable):** golden files change ONLY through an explicit re-certification step — someone verifies the NEW output against ground truth (spec, reference, expert) and updates the inventory row (why-golden and last-verified). Regenerating goldens to make a failing suite pass, with no independent verification of the new output, is forbidden. "Update snapshots" is a review-flagged operation: the PR must show the golden diff and the re-certification evidence, gated per change-control.

**When a golden test fails,** exactly three outcomes exist:
1. The change is wrong → fix the change.
2. The change is a deliberate behavior change → re-certify: verify new output against ground truth, update golden + inventory row, record evidence in the PR.
3. The golden was wrong all along → treat as a found bug; re-certify with a note in the inventory row's history.

**Inventory hygiene:** entries with a last-verified date older than the project's staleness window (heuristic: 12 months, or after any major dependency/format migration) get re-certified or demoted to ordinary fixtures.

### 3.4 Tests that pay rent

Definition — a test **pays rent** when it has a realistic way to fail that would catch a bug someone could plausibly introduce. Rent is paid in failure potential, not in coverage percentage or line count.

Rules:

- **Every test states its bug class.** A one-line comment or docstring: "Defends against: <the specific mistake this catches>." If you cannot complete that sentence, do not add the test. Illustrative example: `# Defends against: off-by-one at page boundary — pagination returned item 0 twice (bug #214).`
- **Prove new tests can fail.** Before a new test lands, demonstrate it failing: run it against the pre-fix code, or temporarily break the code under test and watch it go red. A test born green against both correct and broken code is asserting nothing. (Mutation testing tools automate this check where available — candidate practice, ecosystem-dependent.)
- **Delete tests that can't fail.** Tests that assert tautologies, duplicate a stronger test's coverage, or test the mock instead of the code are negative-value: they cost run time and maintenance and manufacture false confidence. Deleting a test is a reviewed change (state what coverage, if any, is lost) — but "we never delete tests" is not a policy, it's hoarding.
- **Regression tests come from closed investigations.** Every root-caused bug (see debugging-playbook) yields a regression test that (a) reproduces the original failure mechanism — not just the symptom, (b) failed against the pre-fix code (grade-1 evidence of that goes in the PR), (c) names the bug/incident in its rationale. This is the single highest-rent test category: each one defends against a bug proven to occur in practice.

### 3.5 Test taxonomy and the placement decision

Definitions, what each layer is FOR, and its blind spot:

| Layer | Definition | FOR | Blind spot |
|---|---|---|---|
| **Unit** | Exercises one function/class in isolation; collaborators faked where needed. Milliseconds each. | Pinning logic, edge cases, arithmetic, branching. Cheap enough to enumerate cases exhaustively. | Integration seams — the fakes may not behave like the real thing. |
| **Integration** | Exercises 2+ real components together (code + real DB, service + real queue), environment partially real. | Contract/wiring bugs: serialization, schema, config, transactions, auth between components. | Whole-system flows and anything faked at the boundary you didn't include. |
| **End-to-end (e2e)** | Drives the deployed/assembled system through a user-visible flow. | Proving the critical paths work at all, wired together, in a production-like environment. | Expensive, slow, and coarse — a failure says "something in this flow broke", not what. Keep few. |
| **Property** | Asserts an invariant over generated inputs (e.g., `decode(encode(x)) == x` for random `x`), via a framework like Hypothesis (Python) / fast-check (JS) / QuickCheck-family. | Bug classes you can't enumerate: parsers, serializers, arithmetic, anything with an invariant or round-trip law. Finds inputs you'd never write by hand. | Behavior with no crisp invariant; needs a shrinking-friendly input model. |
| **Regression** | A test (at any layer) that pins the fix for a specific, previously observed bug. | Ensuring settled battles stay settled. See 3.4. | Only defends the bug it encodes. |

**Placement decision rule** — put the test at the LOWEST layer that can genuinely exercise the failure mechanism:

1. Can a unit test reproduce the mechanism without faking away the very thing that broke? → unit.
2. Did the bug live in a seam between components (wire format, schema, config, real-dependency behavior)? → integration, with the real dependency on that seam.
3. Did the bug only manifest in the assembled system (deployment, routing, real auth, timing across services)? → e2e — and also ask what cheaper test COULD have caught it, and add that too.
4. Is the bug an instance of a violated invariant? → add a property test for the invariant in addition to the point regression test.

Heuristic shape: many units, some integration, few e2e. But the rule above outranks the shape — never demote a test to a layer where its failure mechanism can't occur just to keep a pyramid pretty.

### 3.6 Flaky-test discipline

Definition — **flaky test**: a test that passes and fails across runs with no code change. Doctrine: **flakiness is a bug with a root cause** — in the test, the harness, or (worst and most valuable to find) the product code. It is never weather.

Quarantine protocol:

1. **Detect and log.** On the first observed flake, file a ticket with the failure output, environment, and frequency if known. A flake without a ticket will be "discovered" fresh five more times.
2. **Quarantine, don't delete, don't retry.** Move the test to a quarantine set: excluded from merge-gating, still executed and reported (e.g., a separate CI job or the framework's skip/xfail-with-reason mechanism, tagged with the ticket ID). This keeps the signal flowing while unblocking the pipeline.
3. **Time-box the quarantine.** Each quarantined test has an owner and a deadline (heuristic: 2–4 weeks). At deadline: root-caused and fixed, or escalated, or — if the test is judged not to pay rent — deleted via the reviewed-deletion path in 3.4. Quarantine is a hospital, not a hospice.
4. **Root-cause with debugging-playbook.** Usual suspects, roughly in order: test-order dependence / shared state, time and timezone assumptions, unseeded randomness, real-network or real-clock dependence, resource races (ports, temp files), genuine product race conditions. That last one is the payoff: a flaky test is sometimes the only witness to a real concurrency bug.
5. **Never retry-until-green as policy.** Auto-retry (rerun failures N times, pass if any run passes) as a standing CI policy converts your suite's flakiness signal into silence and lets real intermittent bugs through the gate. Narrow exception, gated per change-control: a per-test, ticket-linked, expiring retry annotation on a known-flaky test already in the quarantine workflow — never a suite-wide default.

### 3.7 Coverage as a map, not a score

Definition — **code coverage**: the fraction of code executed by the test suite, per line/branch/etc. Doctrine: coverage tells you what is definitely NOT tested; it cannot tell you what IS tested well (executed ≠ asserted).

- **Use it as a map.** Run the coverage report and read it like terrain: "the retry logic and the money-rounding branch have zero coverage" is actionable intelligence. Aim tests at uncovered code whose failure would matter.
- **Do not use it as a target.** A coverage-percentage gate ("must be ≥ N%") invites assertion-free tests written to touch lines — negative-rent tests per 3.4 (Goodhart's law: when a measure becomes a target, it ceases to be a good measure).
- **Acceptable gate (candidate practice):** a no-new-uncovered-code check on changed lines in a PR, applied with reviewer judgment — it directs attention without incentivizing line-touching, but still requires review of whether the covering tests assert anything.
- **Prioritize by consequence.** Rank uncovered regions by (likelihood of change) × (cost of silent failure). Uncovered dead code is a deletion candidate, not a testing candidate.

## 4. Worked example (illustrative — all names and facts fictional)

Project: **Ledgerbird**, a fictional invoice-parsing service. Command placeholders: `<TEST-CMD>` = `pytest`, `<REGEN-CMD>` = `python tools/regen_golden.py`.

### 4.1 Golden inventory excerpt — `tests/golden/INVENTORY.md`

| ID | Scenario | Why golden | How to regenerate | What breakage means | Last verified |
|---|---|---|---|---|---|
| G-01 | `inputs/acme_2025.pdf` → `golden/acme_2025.json`: 3-page invoice, EU VAT, line-item discounts | Totals hand-checked against the source spreadsheet by finance reviewer; VAT per fictional EU-VAT worked examples doc | `python tools/regen_golden.py --case G-01`, then re-verify totals against `inputs/acme_2025_source.xlsx` before committing | Usually a parser layout regression; if only `tax` fields differ, suspect rounding-mode changes first | 2026-05-02 (R. Ferro) |
| G-02 | `inputs/kiwi_scanned.pdf` → `golden/kiwi_scanned.json`: low-DPI scan, OCR path | Reproduces incident LB-88 (silent OCR garbage accepted as amounts); expected output hand-transcribed from the paper original | `python tools/regen_golden.py --case G-02` + hand-compare all `amount` fields to the transcription in `inputs/kiwi_transcript.md` | OCR-confidence-threshold logic changed, or the OCR engine was upgraded — check dependency lockfile first | 2026-03-11 (LB-88 closeout) |
| G-03 | Scenario: round-trip `parse → export → parse` on all G-01 inputs yields identical JSON | Certifies the export format is lossless — relied on by the archival feature | Not regenerated: this is an invariant, re-run via `pytest tests/golden/test_roundtrip.py` | Export serializer dropped or reordered a field; check schema migrations | 2026-05-02 (R. Ferro) |

Threshold on file BEFORE the last model change, from `docs/thresholds.md`: "Field-level extraction F1 ≥ 0.95 on the frozen 200-invoice eval set, single run, seed 7. Rationale: baseline commit `f3a9c21` measured 0.958; requirement LB-REQ-4 demands ≤ 5% field error. Set 2026-04-19." When a later change scored 0.949, the threshold was not moved; the change was rejected and reworked. (Loosening it would have required the change-control gate.)

### 4.2 A well-written regression test rationale

```python
def test_ocr_low_confidence_amounts_rejected():
    """Defends against: incident LB-88 — OCR text below confidence 0.6
    was passed straight into amount parsing, producing a syntactically
    valid but wrong total (parsed '8OO.00' as 800.00 on a scanned page
    whose true amount was 890.00).

    Mechanism, not symptom: asserts the confidence gate fires and the
    field is flagged NEEDS_REVIEW — not merely that this one PDF now
    yields 890.00 (which a lucky OCR upgrade could fake).

    Evidence at introduction: failed on pre-fix commit a1b2c3d
    (output pasted in PR #412), passes after the gate was added.
    """
    result = parse_invoice("tests/inputs/kiwi_scanned.pdf")
    field = result.field("total_amount")
    assert field.status == FieldStatus.NEEDS_REVIEW
    assert field.ocr_confidence < 0.6  # the triggering condition still holds
```

Why this is well-written: it names the incident, states the bug class (unvalidated low-confidence OCR), pins the mechanism (the gate) rather than the symptom (one correct number), and records grade-2 evidence that the test could fail. The second assertion guards the test itself: if a future OCR upgrade raises confidence above 0.6, the test's premise is gone and it fails loudly for re-evaluation instead of passing vacuously.

## 5. Instantiate for your project

Produce `<PROJECT>-validation-and-qa` in the target repo. Steps:

1. **Discover the existing test system.** Run and record outputs:
   - `git ls-files | grep -iE 'test|spec|golden|snapshot|fixture' | head -50` — where tests and fixtures live.
   - Read the manifest (`package.json` scripts, `pyproject.toml`/`tox.ini`/`Makefile`, `*.csproj` + CI config) to find the real `<TEST-CMD>` and any coverage/threshold tooling already wired.
   - `git log --oneline -20 -- <TEST-DIR>` and `git log --oneline --grep="snapshot" --grep="golden" --grep="flaky" -i` — history of test churn, snapshot-regen habits, known flakes.
   - Search CI config for retry flags (e.g., `--reruns`, `retry`, `flaky`) and coverage gates — these are existing policy, good or bad, and must be documented before being changed.
2. **Inventory current evidence practice.** Sample the last 10 merged PRs (no PRs or no forge access? sample the last 10 merge commits instead: `git log --merges --first-parent -10 --oneline`, reading each merged branch's message for evidence claims): what evidence grade did each actually present? Record the distribution honestly — this is the baseline the instantiated skill improves on.
3. **Build the golden inventory.** For every existing snapshot/golden/fixture directory, create `INVENTORY.md` rows using the 3.3 format. Evidence rule: you may fill "Why golden" ONLY from a source (commit message, PR, issue, or a human who certifies it now). Any entry whose ground truth cannot be established is listed with why-golden = "UNCERTIFIED — inherited, treat diffs as informational" until someone re-certifies it. Do not invent certification.
4. **Write the thresholds file.** Collect every numeric gate currently in CI/tests into `docs/thresholds.md` with metric, value, measurement spec, rationale, and set-date. Where rationale is unknown, write "UNKNOWN — inherited from commit <SHA>; re-derive before next change." Wire future loosening edits of this file into the project's change-control gate per §3.2 rule 3 (tightening is recorded in the file's history per rule 5).
5. **Fill the project SKILL.md skeleton:**

   ```markdown
   ---
   name: <PROJECT>-validation-and-qa
   description: <trigger phrases for this project's QA decisions>
   ---
   # <PROJECT> Validation and QA
   ## Evidence requirements by change class   <!-- map grades (3.1) to this project's change classes; cross-ref <PROJECT>-change-control -->
   ## How to run the suites                   <!-- real commands per taxonomy layer: unit / integration / e2e / property, with runtimes -->
   ## Thresholds of record                    <!-- link docs/thresholds.md; state the gate for moving one -->
   ## Golden inventory                        <!-- link INVENTORY.md; the re-certification procedure with this repo's <REGEN-CMD> -->
   ## Flaky quarantine                        <!-- where the quarantine set lives, ticket tag, current deadline owner list -->
   ## Coverage map                            <!-- how to generate the report; current known-uncovered high-consequence areas -->
   ## Provenance                              <!-- date, commit range examined, PRs sampled -->
   ```

6. **Evidence bar for every blank:** do not write a command you have not run in this repo (paste its output in the PR that adds the skill); do not write a why-golden you cannot source; do not state a suite runtime you did not measure. Each section of the instantiated skill carries the same graded-evidence standard it teaches.
7. **Prove the instantiation.** Pick one recent bug fix from `git log`, and walk it through the doctrine: name the evidence grade it shipped with, write (or locate) its regression test with a bug-class rationale, and file the gaps found. This shakedown is the acceptance test for the instantiated skill.

## 6. Provenance and maintenance

- Authored 2026-07-06 against no specific project. All project facts in §4 are fictional (Ledgerbird, LB-88, all IDs and numbers).
- Volatile elements and re-verification:
  - Property-testing framework names (Hypothesis, fast-check) — verify current ecosystem choice: `pip index versions hypothesis` / `npm view fast-check version`.
  - Pytest retry-plugin flag name (`--reruns` is from the `pytest-rerunfailures` plugin, not core pytest) — verify with `pytest --help` after installing, or check the plugin's docs.
  - Coverage tooling conventions per language — confirm against the target repo's manifest, not this document.
- Doctrine sections (3.1–3.7) are method, not tool facts; they age slowly. Items marked "heuristic" or "candidate practice" (staleness window, quarantine time-box, changed-lines coverage gate, mutation testing) are judgment calls — revisit against project experience.
- Instantiated copies must add their own provenance section: date, commit range examined, PRs sampled, and who certified each golden entry.
