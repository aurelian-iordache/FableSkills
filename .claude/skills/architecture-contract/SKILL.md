---
name: architecture-contract
description: Load this skill when you need to document, audit, or recover a system's load-bearing design decisions — e.g. the user asks "why is it built this way?", "write an architecture doc / ADR", "what can we safely change?", "document the invariants", or you inherit an undocumented codebase and must reverse-engineer what actually holds it up. Delivers the contract format (decision + WHY + checkable invariants + blast radius), a KNOWN-WEAK-POINTS discipline, minimal ADR practice, and a reverse-engineering procedure for undocumented systems.
---

# Architecture Contract

## 1. Purpose

This skill makes you able to write and maintain an **architecture contract**: the short document that records which design decisions are load-bearing, WHY they were made, what invariants they imply (each with a way to verify it still holds), and what breaks if someone violates them. It also covers recovering that contract from an undocumented codebase.

## 2. When to use / When NOT to use

**Use when:**
- Starting or inheriting a project and no record exists of why it is shaped the way it is.
- A proposed change touches something "everyone is afraid of" and nobody can say why.
- You are about to make a decision that will be expensive to reverse (storage format, wire protocol, concurrency model, framework choice).
- An invariant was silently violated and you are writing it down so it cannot happen twice.

**Do NOT use when the real need is a sibling skill:**

| If instead you need... | Use sibling skill |
|---|---|
| To classify and gate a specific change (approval levels, review rules) | change-control |
| The history of a specific bug hunt or investigation | failure-archaeology |
| A catalog of config options, defaults, and flags | config-and-flags |
| House style, doc templates, doc-rot prevention in general | docs-and-writing |
| Domain theory (math, protocol specs, standards) behind the design | domain-reference |
| Proving an invariant holds by first-principles argument or measurement | proof-and-analysis |
| Per-diff C# code structure: patterns, interfaces, dependency direction inside one change (nothing load-bearing) | csharp-code-discipline |

The contract is the *what-and-why of structure*. Change gating for contract-breaking changes lives in change-control; the contract only marks which changes are contract-breaking.

## 3. Core doctrine

### 3.1 Definitions

- **Architecture contract**: a single document (recommended path: `docs/ARCHITECTURE-CONTRACT.md`) listing the load-bearing decisions of a system, in the entry format of §3.3. It records what **IS**, not what should be.
- **Load-bearing decision**: a decision whose reversal would cascade — flipping it forces rework in multiple other components, migrations of persisted data, or renegotiation with external parties.
- **Invariant**: a property of the system that must stay true for the decision to keep working, stated as a checkable assertion ("all writes go through `<GATEWAY-MODULE>`"), never as a wish ("writes should be centralized").
- **ADR (Architecture Decision Record)**: a small dated file recording one decision at the moment it is made. The contract is the *current* consolidated truth; ADRs are the *append-only* history feeding it.

### 3.2 What qualifies as LOAD-BEARING

Apply the flip test to every candidate decision: **"What breaks if we flip this tomorrow?"**

| Flip-test outcome | Verdict |
|---|---|
| One module changes, tests pass same day | Not load-bearing. Do not put it in the contract. |
| Several components must change together, or persisted/wire data must migrate | Load-bearing. Contract entry required. |
| External parties (clients, partner teams, on-disk files in the wild) must change | Load-bearing, highest tier. Contract entry + classify any change as class C (contract-breaking) per change-control's litmus tests — class X only if `git revert` cannot restore the world. |

Strong signals a decision is load-bearing (any one suffices to run the flip test seriously):
- **Serialization/wire/storage formats** — anything that outlives a process restart or crosses a network boundary.
- **Dependency direction rules** — "layer A never imports layer B".
- **Concurrency/ownership model** — who may mutate what, single-writer rules, lock ordering.
- **Identity and uniqueness rules** — what a primary key means, idempotency keys, ID formats.
- **Failure semantics** — at-least-once vs at-most-once, what is allowed to be lost.
- **The choice everything else was shaped around** — framework, database, message broker, language runtime version floor.

Anti-signals (keep these OUT of the contract to protect its signal-to-noise ratio): naming conventions, formatting, folder layout that tooling can rename in an afternoon, library choices swappable behind an existing interface. Those belong in docs-and-writing house style or ordinary docs. For C# code, the per-diff judgment behind those conventions lives in csharp-code-discipline.

Heuristic size limit: a healthy contract has roughly 5–20 entries. If you have 50, you diluted "load-bearing" and readers will skim past the real ones.

### 3.3 Contract entry format

Every entry has exactly four parts. An entry missing any part is not done.

```markdown
## C-<NN>: <Decision, stated as a present-tense fact>

**Decision.** One or two sentences of what IS. ("All inter-service messages
are Protobuf over <BROKER>; JSON never crosses a service boundary.")

**Why.** The constraints that forced it, and each alternative that was
rejected WITH the reason. Format:
- Constraint: <the real-world limit that applied>
- Rejected: <ALTERNATIVE> — because <reason, ideally with a link to the
  ADR, issue, or measurement>

**Invariants.** Checkable assertions this decision implies. Each one gets a
verification hook:
- INV-<NN>.1: <ASSERTION>.
  Verify: `<COMMAND>` — expect <OBSERVABLE-RESULT>.
  (or) Verify: test `<TEST-ID/path>` fails if this is violated.

**Blast radius if violated.** Concretely what breaks, who notices, and how
long recovery takes. ("Old readers crash on unknown field; requires
coordinated redeploy of N services plus a data backfill — days, not hours.")
```

Rules for the parts:
- **Why** is the most valuable and most often skipped part. A decision without its rejected alternatives WILL be relitigated by the next engineer, who will rediscover the rejection reason the expensive way. If you genuinely cannot recover the why, write `Why: UNKNOWN — recovered from code, not from a decision record` rather than inventing one.
- **Invariants** must be assertions a machine or a five-minute manual check can evaluate. "Verify:" must name a command with an expected output, or point at a specific test that defends it. An invariant nobody can check is decoration. If no check exists yet, write `Verify: NO AUTOMATED CHECK — candidate test:` and file it as debt (see validation-and-qa for how to add a test that pays rent).
- **Blast radius** is what turns the entry into a gating input: blast radius is a classification input for change-control — a change touching a contract entry is at least class C (contract-breaking), and class X if irreversible — and reviewers size the review by the stated blast radius.

### 3.4 KNOWN-WEAK POINTS — say it plainly

The contract ends with a section titled exactly `## Known-weak points`. This is where you write, without euphemism, what the system is held together by and everyone privately knows it.

Format per item:

```markdown
- **W-<NN>: <plain statement>.** Held together by <the actual mechanism:
  a sleep(5), a cron retry, one person's memory, an undocumented ordering>.
  Fails when: <TRIGGER>. Symptom when it fails: <what you'll see>.
  Fix would cost: <rough size>. Decision so far: accepted / scheduled / unknown.
```

Banned phrasings: "could be improved", "suboptimal", "technical debt exists in this area", "opportunities for enhancement". Required phrasing style: "Deploys are serialized by a shared lock file on one host; if that host is down, nobody can deploy." The test: a new engineer reading the item can predict the failure before it happens.

Why this section earns its place: it is the difference between a contract and a brochure. Readers trust the load-bearing entries *because* the document also admits what is weak. A contract with an empty weak-points section on a system older than six months is presumptively dishonest — dig harder.

### 3.5 Contract vs aspirational architecture docs

| | Architecture contract | Aspirational architecture doc |
|---|---|---|
| Records | What IS and WHY it is | What someone wishes it were |
| Tense | Present-tense facts | Future/conditional ("will", "should") |
| Invariants | Checkable today | Not checkable (target state) |
| Lies detected by | Running the Verify commands | Nothing — it cannot be falsified |
| Belongs | `docs/ARCHITECTURE-CONTRACT.md` | A separate roadmap/RFC doc, clearly labeled |

Enforcement rule: if a sentence in the contract cannot survive the question "is this true in `<MAIN-BRANCH>` right now, and how would I check?", it either moves to a roadmap doc or gets rewritten as a Known-weak point. Mixing the two destroys the contract's authority — the first time a reader catches the contract describing a wish as a fact, they stop trusting all of it. Doc-of-record placement and review cadence follow docs-and-writing.

### 3.6 Lightweight ADR discipline

**When a change requires an ADR** (any one triggers it):
1. It adds, changes, or violates a contract entry or its invariants.
2. It picks between alternatives that a future engineer could plausibly relitigate (new datastore, new protocol, new concurrency model).
3. It accepts a new Known-weak point on purpose ("we ship with the race; here's why").
4. A reviewer asks "why this way?" and the answer is longer than a code comment.

Everything else does not need an ADR. Over-ADRing kills the practice as surely as under-ADRing.

**Minimal template** — one file per decision at `docs/adr/NNNN-<SLUG>.md`, numbered sequentially:

```markdown
# ADR-NNNN: <decision as a short imperative sentence>
Date: YYYY-MM-DD
Status: Accepted        # Proposed | Accepted | Superseded by ADR-MMMM | Amended by ADR-MMMM

## Context
2–6 lines: the forces and constraints that made a decision necessary.

## Decision
What we are doing. Present tense, one paragraph max.

## Alternatives rejected
- <ALTERNATIVE> — <REASON-REJECTED>

## Consequences
What becomes easier, what becomes harder, new invariants (add them to the
contract entry), new weak points (add to Known-weak points).
```

**Superseding vs amending — never edit an accepted ADR's Decision:**

| Situation | Action |
|---|---|
| Decision reversed or replaced | New ADR; old one gets `Status: Superseded by ADR-MMMM`. Old file's body is untouched — it is history. |
| Decision stands, scope/details refined (e.g. "Protobuf everywhere" → "Protobuf everywhere except the legacy `<PARTNER>` endpoint") | New ADR marked as amending; old one gets `Status: Amended by ADR-MMMM`. |
| Typo / broken link / clarity fix, meaning unchanged | Edit in place, no status change. |

After any Accepted ADR: update the contract in the same pull request. The contract mirrors current ADR state; an ADR merged without a contract update is the #1 way the contract rots. Make this a review checklist item under change-control.

### 3.7 Reverse-engineering the contract from an undocumented codebase

You inherited a system with no contract. The code cannot tell you WHY, but it can tell you WHAT is load-bearing. Run these four analyses, then draft entries with `Why: UNKNOWN` where history gives nothing.

**Step 1 — Find what everything imports (dependency direction analysis).**
The modules with the highest fan-in are load-bearing by definition: flipping them cascades.

```sh
# Illustrative for Python; adapt the regex per language (import/require/using/use).
grep -rhoE '^(from|import) [A-Za-z0-9_.]+' <SRC-DIR>/ | sort | uniq -c | sort -rn | head -20
```

Prefer a real dependency-graph tool when the ecosystem has one (`pydeps`, `madge`, `go mod graph`, `dotnet list package --include-transitive`) — availability varies, so verify the tool exists before citing its output. Record both the top fan-in modules and the *direction rules* you observe (does anything low-level import something high-level? if never, that's a candidate invariant).

**Step 2 — Find the schema/wire-format boundaries.**
Anything persisted or transmitted is load-bearing because old data/old clients exist.

```sh
# Schema and format definition files:
find <SRC-DIR> -name '*.proto' -o -name '*.avsc' -o -name '*.graphql' \
  -o -name '*migration*' -o -name '*schema*'
# Serialization call sites (adapt terms per stack):
grep -rniE 'serialize|marshal|to_json|parse|decode|ParseFrom' <SRC-DIR> -l | head -20
```

Every distinct format found is a candidate contract entry with tier-highest blast radius (§3.2).

**Step 3 — Find what the tests defend hardest.**
Tests concentrate around what previously broke or must never break.

```sh
# Which source files' tests are largest / most numerous:
find <TEST-DIR> -name '*test*' | sed -E 's/.*(test[s]?[_/.-])//' | sort | uniq -c | sort -rn | head -20
# Which tests are touched most often (battle scars):
git log --format=%H --since="2 years ago" -- <TEST-DIR> | wc -l   # overall churn baseline
git shortlog -sn HEAD -- <TEST-DIR>                                # who defends them (interview targets)
```

Golden files, snapshot tests, and property-based tests are the strongest signal: someone froze that behavior on purpose. Each cluster of hard-defended behavior is a candidate invariant. Cross-check with failure-archaeology if issue history exists — the incident behind a test is often the missing WHY.

**Step 4 — Mine history for the decision moments.**

```sh
git log --oneline --follow -- <SUSPECTED-LOAD-BEARING-FILE>   # its whole life
git log --oneline -S'<KEY-TERM>' -- <SRC-DIR>                  # when a concept appeared/vanished
git log -1 --format=%ad --date=short -- <FILE>                 # last touched (stability signal)
git blame -L <START>,<END> <FILE>                              # who wrote the scary block; read that commit's message
```

Files with high fan-in and LOW churn are your most load-bearing candidates: everything depends on them and nobody dares touch them. Read the commit messages at their creation and at any large rewrite — that is where WHYs hide. If original authors are reachable, a 30-minute interview per candidate entry beats a day of archaeology; bring the flip test as your question list.

**Output of the exercise:** a draft contract where every entry is marked either `Why: <recovered, with source>` or `Why: UNKNOWN — recovered from code`. Do not fabricate rationale to make the document look complete. An honest UNKNOWN invites correction; a plausible fabrication gets defended forever.

### 3.8 Failure modes of this method

| Failure mode | Symptom | Countermeasure |
|---|---|---|
| Contract bloat | 50+ entries, readers skim | Re-run the flip test on every entry annually; demote non-cascading ones |
| Aspirational leakage | "should"/"will" appearing in entries | §3.5 enforcement rule at review time |
| Invariant rot | Verify commands fail or point at deleted tests | Run every Verify hook on a schedule; treat a red hook like a failing test |
| Orphaned ADRs | ADR accepted, contract unchanged | Same-PR rule (§3.6); change-control checklist item |
| Euphemized weak points | Weak-points section reads like a press release | Banned-phrasing list in §3.4; reviewer applies the "predict the failure" test |
| Fabricated WHYs | Confident rationale with no source | Require a source link or `UNKNOWN` label per §3.7 |

## 4. Worked example

**Illustrative example — every fact below is fictional.** Project "Orrery", a telemetry pipeline.

```markdown
## C-03: Ingest writes raw events to append-only NDJSON segments before any parsing

**Decision.** The ingest daemon appends each raw event, unmodified, to an
NDJSON segment file and fsyncs before ACKing the sender. Parsing happens in a
separate stage reading those segments.

**Why.**
- Constraint: senders are field devices with 8 KB buffers; an unACKed event
  is lost after 30 s.
- Rejected: parse-then-store — because a parser bug in 2024 (ADR-0007) would
  have silently destroyed 6 h of unreparseable data; raw-first made the bug
  replayable instead.
- Rejected: writing to the message broker directly — because broker retention
  (72 h) is shorter than our reprocessing window (30 d).

**Invariants.**
- INV-03.1: Ingest ACKs only after fsync returns.
  Verify: test `tests/ingest/test_ack_after_fsync.py` fails if reordered.
- INV-03.2: No code path modifies a segment after its `.closed` marker exists.
  Verify: `grep -rn "open(.*segment" src/ --include='*.py'` — expect matches
  only in `src/ingest/writer.py` and read-only opens elsewhere.

**Blast radius if violated.** Field events are unrecoverable once lost —
there is no upstream copy. A violation shows up days later as gaps in
customer dashboards; restitution has contractual penalties.
```

And its Known-weak point, stated plainly:

```markdown
- **W-02: Segment rollover is not crash-safe.** Held together by a startup
  scan that quarantines the last segment if no `.closed` marker exists.
  Fails when: crash during the ~50 ms rename window AND the startup scan is
  skipped (operator uses `--fast-start`). Symptom: parser stage reads a
  truncated final line and logs `JSONDecodeError` once per replay.
  Fix would cost: ~1 week (two-phase rollover). Decision so far: accepted,
  revisit if `--fast-start` becomes the default.
```

How the flip test played out (fictional): "What breaks if we flip C-03 and parse before storing?" — replay tooling (reads raw segments), the 30-day reprocessing guarantee, and the sender ACK latency budget all break; three components plus a contractual promise → load-bearing, contract entry required. By contrast "segments are named `seg-<epoch>.ndjson`" flips with one function and a glob update → not in the contract.

## 5. Instantiate for your project

Produce `docs/ARCHITECTURE-CONTRACT.md` (plus `docs/adr/`) in the target repo, and optionally a project skill `<PROJECT>-architecture-contract` that tells future agents where the contract lives and how to keep it honest. Steps:

1. **Mine the repo.** Run the §3.7 discovery battery and save raw outputs to a scratch file:
   ```sh
   grep -rhoE '<IMPORT-REGEX-FOR-LANGUAGE>' <SRC-DIR>/ | sort | uniq -c | sort -rn | head -20
   find <SRC-DIR> -name '*schema*' -o -name '*.proto' -o -name '*migration*'
   git shortlog -sn HEAD -- <SRC-DIR> | head -10
   git log --oneline --follow -- <TOP-FAN-IN-FILE> | head -30
   ```
   Evidence rule: a module may be called high-fan-in only with the count next to it; a WHY may be written only with a commit hash, ADR, issue link, or named-interview source next to it. Otherwise write `UNKNOWN`.

2. **Shortlist candidates.** Take: top-5 fan-in modules, every schema/wire format found, every golden/snapshot test cluster, every high-fan-in low-churn file. Run the flip test (§3.2) on each; keep only the cascading ones. Target 5–20 entries.

3. **Draft entries** using the §3.3 skeleton verbatim. For each invariant, either point at an existing test (run it once to confirm it exists and passes: `<TEST-CMD> <TEST-ID>`) or a command you have actually executed in this repo with the expected output recorded. Do not ship a Verify hook you have not run.

4. **Draft Known-weak points.** Sources: `grep -rniE 'HACK|FIXME|XXX|workaround|race' <SRC-DIR>` hits, the oldest open bugs, anything the flip test flagged as fragile, and (if humans are available) the question "what do you check manually before every release?". Apply the banned-phrasing filter from §3.4.

5. **Seed the ADR log.** Create `docs/adr/0001-adopt-architecture-contract.md` from the §3.6 template recording this very adoption. Backfill ADRs only for decisions whose WHY you actually recovered — do not manufacture history.

6. **Wire the enforcement hooks.**
   - Add "touches a contract entry" as a project-specific litmus test on class C (contract-breaking) in the project's change-control instantiation — change-control's Instantiate step already provides for adding project litmus tests; a contract-touching change escalates to class X only if it is irreversible. Add "ADR merged ⇒ contract updated in same PR" to its review checklist.
   - Add a scheduled job or checklist item that runs every `Verify:` command; a failing hook is treated as a failing test.
   - Register the contract as a doc of record per docs-and-writing (owner, review cadence).

7. **Fill the template skeleton** for the project doc:
   ```markdown
   # <PROJECT> Architecture Contract
   Last verified: <DATE> against <COMMIT>. Owner: <ROLE-OR-TEAM>.
   Scope: what this covers / explicitly does not cover.
   ## Contract entries        (C-01 ... from step 3)
   ## Known-weak points       (W-01 ... from step 4)
   ## ADR index               (table: ADR # | title | status | contract entries touched)
   ## How to change this document (pointer to <PROJECT>-change-control gates)
   ```
   Blanks may be filled only with step-1 evidence attached; entries lacking evidence ship as `UNKNOWN`, never as guesses.

## 6. Provenance and maintenance

- Authored 2026-07-06 against no specific project; all project facts in §4 are fictional and labeled.
- Volatile parts and re-verification:
  - `git log --follow`, `--diff-filter`, `-S`, `-L`, `git shortlog -sn`, `git blame -L` — verified by execution 2026-07-06 (git for Windows). Re-verify: run each against any repo; consult `git help log`.
  - The grep/sort/uniq import-count pipeline — verified by execution 2026-07-06 (POSIX tools). Re-verify: run it on any source tree.
  - Ecosystem dependency-graph tools named in §3.7 (`pydeps`, `madge`, `go mod graph`, `dotnet list package`) — NOT executed here; availability and flags are heuristic. Verify locally (`<TOOL> --help`) before citing their output.
  - The 5–20 entry size limit and ADR trigger list are heuristics, not proven thresholds.
- Instantiated copies must add their own provenance line: date, commit verified against, and which Verify hooks were actually executed.
