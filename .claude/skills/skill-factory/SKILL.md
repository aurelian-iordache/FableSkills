---
name: skill-factory
description: >
  The keystone skill. Load this when you are dropped into a repository that has no
  project-specific skill library and you need to build one — e.g. the user says
  "bootstrap skills for this repo", "instantiate the skill library here", "onboard
  this project", "set up project skills", or you are starting long-term work on an
  unfamiliar codebase. Delivers a rigorous repo discovery protocol (docs, build,
  tests-as-actually-run, CI, git history mining, TODO hotspots), a five-question
  budget for the human, taxonomy adaptation rules for the 15 generic sibling skills
  and the five stack-tier skills (csharp-code-discipline, dotnet-ef-discipline,
  sql-server-operations, react-frontend-discipline, aspnet-api-discipline), and a
  parallel authoring + three-reviewer workflow that produces 10–16 project-specific
  skills grounded in evidence.
---

# skill-factory — Bootstrap a Project-Specific Skill Library

## Purpose

This skill turns you into the factory that builds all the others. Given any repository,
it tells you how to investigate it like an incoming principal engineer, ask the human
only what the repo cannot answer, adapt the generic taxonomy (15 discipline skills,
plus five stack-tier skills when discovery identifies their stacks) to fit the
project, and then author + review a complete `<PROJECT>-*` skill library that a
zero-context engineer or Sonnet-class model can work from.

## When to use / When NOT to use

**Use when:**
- You are starting sustained work in a repo with no `.claude/skills/<PROJECT>-*` library.
- An existing project library is stale and needs a ground-up re-derivation.
- You must decide *which* skills a project needs (taxonomy), not just write one skill.

**Do NOT use when** you need the discipline itself rather than the factory. One home
per fact — route to the sibling that owns it:

| If instead you need... | Use sibling skill |
|---|---|
| Design change gates / review policy for the project | `change-control` |
| Build a symptom→triage debugging table | `debugging-playbook` |
| Mine history into a chronicle of past investigations | `failure-archaeology` |
| Record load-bearing design decisions and invariants | `architecture-contract` |
| Write the domain-theory knowledge pack | `domain-reference` |
| Catalog config options and flags | `config-and-flags` |
| Write the from-scratch environment runbook | `build-and-env` |
| Write run/deploy runbooks and data conventions | `run-and-operate` |
| Build measurement/diagnostic tooling | `diagnostics-and-tooling` |
| Define what counts as test evidence | `validation-and-qa` |
| Maintain docs of record and house style | `docs-and-writing` |
| Turn the hardest live problem into a gated campaign | `campaign-design` |
| First-principles verification and benchmark rigor | `proof-and-analysis` |
| Evidence bar for research claims and ideas | `research-discipline` |
| C# code craft: smallest-diff discipline, pattern judgment, analyzer enforcement (stack: C#/.NET) | `csharp-code-discipline` |
| EF Core migration/data-layer discipline (stack: .NET+EF) | `dotnet-ef-discipline` |
| SQL Server DMV/index/backup operations (stack: SQL Server) | `sql-server-operations` |
| React+TS state/effects/testing discipline (stack: React) | `react-frontend-discipline` |
| ASP.NET Core API-surface discipline: DTO wire contracts, ProblemDetails, OpenAPI-as-artifact, API breaking changes (stack: ASP.NET Core) | `aspnet-api-discipline` |

`skill-factory` orchestrates all of the above; it does not duplicate their content.

## Core doctrine

The factory runs in five phases, strictly in order. Do not ask the human anything
until Phase 1 is complete. Do not author anything until Phases 1–3 are complete.

```
Phase 1  DISCOVER   — mine the repo; build an evidence ledger
Phase 2  ASK        — at most five questions to the human
Phase 3  ADAPT      — fit the generic + stack-tier taxonomy to this project (target 10–16)
Phase 4  AUTHOR     — one skill per parallel agent, under a written contract
Phase 5  REVIEW     — three reviewers (factual / doctrine / usability) + one fixer
```

### Phase 1 — Discovery protocol

Run these steps in order. For every finding, write a line in an **evidence ledger**
(a scratch file, e.g. `evidence-ledger.md`): `finding | source (file:line or commit
SHA or command output) | confidence (verified-by-running / read-in-file / inferred)`.
Every fact that later appears in a skill must trace back to a ledger line.
"Inferred" facts may not appear in a skill as stated fact — only as a labeled
hypothesis or as one of your five questions.

**D1. Orientation documents.** Read, in this order, whichever exist: `README*`,
`CONTRIBUTING*`, `ARCHITECTURE*`, `docs/`, `doc/`, `adr/` or `docs/adr/` or
`docs/decisions/`, `CHANGELOG*`, `*.md` at repo root. Note claims about how to
build/test/run — as *claims*, not facts, until D3 verifies them.

**D2. Build system identification.** Find the manifests and name the build system
explicitly in the ledger:

| Manifest found | Build system | Likely build command to verify |
|---|---|---|
| `package.json` | npm/pnpm/yarn (check lockfile) | `npm run build` / see `"scripts"` |
| `pyproject.toml`, `setup.py` | Python (pip/poetry/uv — check `[tool.*]`) | `pip install -e .` etc. |
| `*.sln`, `*.csproj` | .NET | `dotnet build` |
| `Cargo.toml` | Rust | `cargo build` |
| `go.mod` | Go | `go build ./...` |
| `Makefile`, `justfile` | make/just — read the targets | `make <TARGET>` |
| `CMakeLists.txt` | CMake | `cmake -B build && cmake --build build` |
| `Dockerfile`, `compose.yaml` | container-first workflow | `docker build .` |

Multiple manifests = polyglot repo; record each subsystem separately.

**D3. How tests are ACTUALLY run.** Docs lie; CI does not. Order of authority:
1. CI config (D4) — the test step CI executes is the ground truth.
2. Script targets (`package.json` scripts, `Makefile` targets, `tox.ini`, `noxfile.py`).
3. What the docs claim.
Then **run the test command once** and record: exact command, runtime, pass/fail
count, anything skipped or flaky. If it fails on a clean checkout, that failure is
itself a top-tier finding (feeds `build-and-env`). Do not write "tests: `<TEST-CMD>`"
in any skill until you have watched it execute.

**D4. CI configuration.** Look for `.github/workflows/*.yml`, `.gitlab-ci.yml`,
`azure-pipelines.yml`, `Jenkinsfile`, `.circleci/config.yml`, `buildkite/`. Extract:
trigger events, matrix (OS/language versions), every command run, required checks,
deploy steps, secrets referenced by name. Pin versions found here with a date stamp
(they drift).

**D5. Git history mining.** This is where the repo confesses. All commands below were
syntax-verified 2026-07-06 (git 2.x). Run from repo root; `<MAIN-BRANCH>` is usually
`main` or `master` — check with `git branch --show-current` or the remote HEAD.

| Question | Command |
|---|---|
| Overall shape, branch structure | `git log --oneline --graph --all` (pipe to `head -60`) |
| Who has carried the project | `git shortlog -sn HEAD` (the rev matters: without one, `git shortlog` reads stdin when not on a terminal and prints nothing) |
| What changed most (churn hotspots) | command (a) in the block below |
| What got reverted (pain signal) | `git log --grep=revert -i --oneline` |
| What was deleted (abandoned approaches) | command (b) in the block below |
| What stalled on dead branches | `git for-each-ref --sort=-committerdate refs/remotes --format='%(refname:short) %(committerdate:relative) %(authorname)'` then `git branch -r --no-merged <MAIN-BRANCH>` |
| Recent activity level | command (c) in the block below |
| History of a specific topic/term | `git log -S "<TERM>" --oneline` (pickaxe: commits that changed the number of occurrences of the string) |

Piped commands live outside the table so they copy-paste cleanly from raw Markdown:

```sh
# (a) churn hotspots
git log --format= --name-only | sort | uniq -c | sort -rn | head -25
# (b) deleted files (abandoned approaches)
git log --diff-filter=D --summary | grep delete
# (c) recent activity level
git log --oneline --since="6 months ago" | wc -l
```

Interpretation heuristics (labeled as heuristics — verify before asserting):
- Top-churn files are where the live problems are; they seed `debugging-playbook`
  and `campaign-design` scoping.
- Reverts and deletions seed `failure-archaeology`: read each revert commit's
  message and diff before recording anything about *why*.
- Stale unmerged branches often mark stalled campaigns — read their tip commits;
  do not guess intent.

**D6. TODO/FIXME hotspot scan.** Searches tracked files only (that is the point —
vendored/ignored noise is excluded):
- Locations: `git grep -nE "TODO|FIXME|HACK|XXX"`
- Count per file, worst first: `git grep -cE "TODO|FIXME|HACK|XXX" | sort -t: -k2 -rn | head -15`
Cross-reference against the churn list from D5: a file high on both lists is a
prime `debugging-playbook` / `campaign-design` candidate.

**D7. Issue-shaped artifacts.** If the remote is GitHub and `gh` is available:
`gh issue list --state all --limit 50` and `gh pr list --state all --limit 50`.
Otherwise hunt in-repo: `TODO.md`, `BUGS*`, `docs/issues/`, `.github/ISSUE_TEMPLATE/`,
tracker links in README. Closed issues with long threads feed `failure-archaeology`;
open ones feed `campaign-design`.

**D8. Generated data and deploy conventions.** Read `.gitignore` top to bottom — it
is a map of everything the build produces and where. Look for `terraform/`, `k8s/`,
`helm/`, `deploy/`, `infra/`, `scripts/deploy*`, release workflows in CI. Record:
what artifacts are generated, where they land, what is sacred (never regenerate)
vs disposable. Feeds `run-and-operate`.

**Exit criterion for Phase 1:** the evidence ledger answers "how is this built, how
is it tested, what hurts, what died, what ships" — each with a source. Anything still
unknown goes on the candidate-question list for Phase 2.

### Phase 2 — The question budget

**Rule: after discovery, ask the human AT MOST five questions.** One message, all
questions together, each with a one-line note on why the repo could not answer it.
Never ask anything D1–D8 could have answered — that burns trust and budget.

The five canonical slots (replace any slot the ledger already fills):

1. **Hardest live problem.** "What is the hardest unsolved problem in this project
   right now?" → seeds `campaign-design`.
2. **Unwritten discipline rules.** "What rules do you enforce that are written
   nowhere? (things you'd reject a PR for on sight)" → seeds `change-control`.
3. **Audience gaps.** "Who will work on this next, and what do they predictably
   not know?" → sets depth for `domain-reference` and every runbook.
4. **Costliest past failures.** "What failure cost the most time or damage, and
   what would have prevented it?" → seeds `failure-archaeology` and the
   non-negotiables in `change-control`.
5. **What 'beyond state of the art' means here.** "If this project exceeded the
   current state of the art, what specifically would be true?" → seeds
   `research-discipline` and `proof-and-analysis` ambition level.

Record answers verbatim in the ledger, marked `source: human, <DATE>`. Human answers
are testimony, not verified fact — where a skill states them, attribute them
("per maintainer, 2026-07-06: ...").

### Phase 3 — Taxonomy adaptation

Start from the generic 15-skill inventory:

| # | Generic skill | Owns |
|---|---|---|
| 1 | `skill-factory` | This factory: discovery, taxonomy, authoring workflow |
| 2 | `change-control` | Change classification, gates, review, non-negotiables |
| 3 | `debugging-playbook` | Symptom→triage tables, discriminating experiments |
| 4 | `failure-archaeology` | Chronicle of past investigations, settled battles |
| 5 | `architecture-contract` | Load-bearing decisions, invariants, weak points |
| 6 | `domain-reference` | Domain theory the mid-level reader lacks |
| 7 | `config-and-flags` | Every configuration axis, defaults, guards |
| 8 | `build-and-env` | From-scratch environment recreation |
| 9 | `run-and-operate` | Run/deploy runbooks, data/artifact conventions |
| 10 | `diagnostics-and-tooling` | Measurement tools + interpretation guides |
| 11 | `validation-and-qa` | Evidence standards, golden inventories, tests that pay rent |
| 12 | `docs-and-writing` | Docs of record, templates, house style |
| 13 | `campaign-design` | The hardest problem as a decision-gated campaign |
| 14 | `proof-and-analysis` | Invariant/complexity/statistical verification |
| 15 | `research-discipline` | Hunch→accepted-result lifecycle, evidence bar |

**Stack tier.** Five additional siblings cover specific stacks: `csharp-code-discipline`
(C# code craft — smallest-diff, unnecessary-code catalog, pattern judgment, analyzer
enforcement), `dotnet-ef-discipline` (EF Core migrations and data-layer discipline),
`sql-server-operations` (SQL Server operational discipline), `react-frontend-discipline`
(React + TypeScript front-end discipline), `aspnet-api-discipline` (the ASP.NET Core
HTTP surface: DTOs as wire contracts, System.Text.Json behavior, ProblemDetails, OpenAPI
document as CI artifact). They join the parent inventory ONLY when
Phase 1 evidences the stack — D2 manifests showing `*.sln`/`*.csproj` (any C# at all →
`csharp-code-discipline`), `Microsoft.EntityFrameworkCore.*` packages
(→ `dotnet-ef-discipline`), SQL Server connection strings / `sqlproj`, `react` in
`package.json`, or an ASP.NET Core web API surface — `Microsoft.NET.Sdk.Web` in a
csproj, or hits from
`git grep -l "WebApplication.CreateBuilder\|\[ApiController\]\|MapGet" -- '*.cs'`
(→ `aspnet-api-discipline`).
Instantiate them like any other parent (`<PROJECT>-csharp-discipline`,
`<PROJECT>-ef-discipline`, `<PROJECT>-sql-operations`, `<PROJECT>-frontend-discipline`,
`<PROJECT>-api-discipline`).
Do not instantiate a stack skill whose stack the evidence ledger does not show; do not
re-author their content under a generic parent.

Adaptation rules — **target 10–16 project skills**:

- **MERGE categories that are thin.** If discovery yields under ~40 lines of real
  content for a category, fold it into its nearest neighbor and say so in the
  merged skill's header. Common merges: `config-and-flags` → `run-and-operate`
  (few flags); `docs-and-writing` → `change-control` (docs rules are review rules);
  `research-discipline` + `proof-and-analysis` (project does little novel research);
  `diagnostics-and-tooling` → `debugging-playbook` (tooling exists only for debugging).
- **SPLIT categories that are deep.** If one skill would exceed ~400 lines or serve
  two distinct workflows, split along the workflow seam. Common splits:
  `debugging-playbook` per subsystem; `run-and-operate` into run vs deploy;
  `domain-reference` per field (e.g. protocol spec vs numerical methods).
- **ADD domain categories** the generic set cannot anticipate: a hardware-bring-up
  runbook, a regulatory-compliance pack. Check the stack tier before inventing a
  schema-migration, database, front-end, API-surface/wire-contract/OpenAPI, or
  C#-coding-standards skill — for EF Core
  schema migrations, `dotnet-ef-discipline` is the existing parent; SQL Server
  operations belong to `sql-server-operations`; React front-end discipline to
  `react-frontend-discipline`; the HTTP API surface (wire contracts, error shape,
  OpenAPI, versioning) to `aspnet-api-discipline`; C# code craft and analyzer standards
  to `csharp-code-discipline`. Do not invent a new category a stack-tier skill already owns. Each added skill must
  still pass the one-home-per-fact test against the rest of the inventory.
- **Never merge away** `change-control`, `build-and-env`, or `debugging-playbook`
  content — every project has change rules, an environment, and failure modes, even
  if the skill that hosts them is merged, the content must survive.
- Name every produced skill `<PROJECT>-<NAME>` (e.g. `tidepool-build-and-env`).
- Write the final taxonomy as a table (project skill → generic parent(s) → one-line
  scope → key evidence-ledger lines) and get it in front of the human once before
  Phase 4. This is the one deliverable the human approves; it is not one of the
  five questions.

### Phase 4 — Authoring workflow

1. **Write the project authoring contract first** — a single file the authors share.
   Adapt the section order below; include the taxonomy table, the evidence ledger
   path, hard rules (see "Authoring rules"), and the exact reporting format.
2. **One skill per agent, in parallel.** Each author agent receives: the contract,
   the evidence ledger, its single skill's scope row, and write access ONLY to its
   own `.claude/skills/<PROJECT>-<NAME>/` directory. Parallel authoring works
   because the taxonomy already fixed the boundaries; boundary disputes go back to
   the taxonomy table, not into overlapping prose.
3. **Mandatory section order for every produced skill:**
   1. Purpose (2–4 lines)
   2. When to use / When NOT to use (with sibling routing table)
   3. Core content (the project-specific doctrine/runbook/reference)
   4. Worked example (a real, reproduced case from THIS project — not fictional)
   5. Maintenance triggers (what events make this skill stale)
   6. Provenance (see Authoring rules)

   Note: this section order intentionally differs from the generic library's
   authoring-contract order — project skills are instances, not templates, so their
   worked example is a real case and "Maintenance triggers" replaces "Instantiate".
4. Authors report back: files written, commands verified and how, open uncertainties.
   Uncertainties feed the reviewers.

#### Authoring rules for project-specific skills (hard rules)

1. **Ground truth only.** Every stated fact traces to an evidence-ledger line, a
   file:line, a commit SHA, or a run you performed. No fact from memory of "how
   these things usually work." Generalized experience may appear only labeled as
   "heuristic" or "candidate practice."
2. **Verified commands.** Every command in a project skill was executed in that repo
   by the author, in the state the skill assumes. A wrong runbook is worse than none.
3. **Date-stamp volatile facts.** Tool versions, CI images, dependency pins, URLs,
   team names: write "as of `<DATE>`" and include a one-line re-verification command.
4. **Provenance section, mandatory.** Author, date, repo commit SHA the skill was
   derived from (`git rev-parse HEAD`), list of volatile facts with re-check commands.
5. **No oversell.** Never claim a procedure guarantees an outcome. Distinguish
   "this fixed it on 2026-07-06 (commit `<SHA>`)" from "this should fix it."
6. **No routing around change control.** A skill must never teach bypassing the
   project's review gates, force-pushing shared branches, skipping hooks, or
   disabling checks as a workflow. If a gate is genuinely obstructive, the skill
   says "raise it via the process in `<PROJECT>-change-control`" — it does not
   document the workaround.

### Phase 5 — Review: three reviewers + one fixer

Run three reviewer agents in parallel, each reading ALL produced skills; then one
fixer applies the merged findings. Reviewers write findings only (file, line,
problem, suggested fix, severity BLOCKER/MAJOR/MINOR); they do not edit. The briefs
below are load-bearing — reuse them verbatim, filling the placeholders.

**Reviewer 1 — FACTUAL brief (use verbatim):**

```
You are the FACTUAL reviewer for the <PROJECT> skill library at <SKILLS-DIR>.
Read every SKILL.md. Your only concern is truth. For each skill:
1. Every command: check the syntax is real for that tool and, where feasible,
   run it read-only in the repo. Flag any command you could not verify.
2. Every stated fact about the project: trace it to the evidence ledger at
   <LEDGER-PATH>, a file:line, or a commit SHA. Flag unsourced facts as BLOCKER.
3. Every number, version, path, and name: check it against the repo as it is now.
4. Flag anything presented as fact that is actually inference or memory.
Do not comment on style, structure, or usefulness — other reviewers own those.
Output: a findings list — file, line, problem, evidence, suggested fix,
severity (BLOCKER = wrong or unsourced fact; MAJOR = unverified command;
MINOR = missing date-stamp). Do not edit any file.
```

**Reviewer 2 — DOCTRINE brief (use verbatim):**

```
You are the DOCTRINE reviewer for the <PROJECT> skill library at <SKILLS-DIR>.
Read every SKILL.md plus the authoring contract at <CONTRACT-PATH>. Your only
concern is methodological soundness and library coherence:
1. One home per fact: flag content duplicated across skills; name the single
   skill that should own it.
2. Routing: every "When NOT to use" table must point to siblings that exist,
   by exact name, and the pointed-to skill must actually cover the referral.
3. Contract compliance: section order, provenance present, placeholders in
   <ANGLE-CAPS> form, worked example is a real project case.
4. Discipline integrity: flag any guidance that oversells, teaches routing
   around change control, or states a heuristic as a guarantee. Known recurring
   failure mode: stack/project skills over-classify changes as class C
   ("contract-breaking") even when every consumer is enumerable in-repo —
   check each skill's gate classes against change-control's actual litmus
   tests, not against the scariest default.
5. Coverage: check the taxonomy table against the delivered skills — flag gaps
   (taxonomy row with no skill) and orphans (skill with no taxonomy row).
Do not re-verify facts or commands — the factual reviewer owns that.
Output: findings list — file, line, problem, suggested fix, severity
(BLOCKER = contract violation or unsafe doctrine; MAJOR = duplication or bad
routing; MINOR = structure drift). Do not edit any file.
```

**Reviewer 3 — USABILITY brief (use verbatim):**

```
You are the USABILITY reviewer for the <PROJECT> skill library at <SKILLS-DIR>.
Read every SKILL.md as if you were a zero-context mid-level engineer or a
Sonnet-class model on day one. Your only concern is whether a stranger can
execute these skills:
1. Cold-read test: for each skill, can you find the right section from headings
   alone in under 10 seconds? Flag any skill where you got lost.
2. Jargon: flag every term of art not defined at first use.
3. Actionability: flag every checklist item that is aspirational rather than
   checkable ("ensure quality" bad; "run X, expect Y" good).
4. Copy-paste test: flag commands that need silent editing before they run
   (missing placeholders, wrong shell, implicit cwd).
5. Trigger quality: read each skill's frontmatter description — would a model
   holding a matching task actually load this skill? Flag weak triggers.
Do not judge factual truth or library structure — other reviewers own those.
Output: findings list — file, line, problem, suggested fix, severity
(BLOCKER = skill unusable cold; MAJOR = unrunnable command or undefined
jargon in a critical path; MINOR = polish). Do not edit any file.
```

**Fixer brief (use verbatim):**

```
You are the FIXER for the <PROJECT> skill library at <SKILLS-DIR>. Input: three
findings lists (factual, doctrine, usability) and the authoring contract at
<CONTRACT-PATH>. Merge the findings; where they conflict, precedence is
factual > doctrine > usability. Fix every BLOCKER and MAJOR; fix MINORs unless
doing so would risk new errors. For factual BLOCKERs you cannot verify
yourself, do not guess — cut the claim or mark it "UNVERIFIED, re-check via
<COMMAND>". Never introduce new facts that are not in the evidence ledger.
Report: findings fixed, findings rejected (with reason), and any remaining
UNVERIFIED markers.
```

### Failure modes of the factory itself

| Failure mode | Symptom | Countermeasure |
|---|---|---|
| Discovery theater | Ledger full of README quotes, nothing run | D3's run-the-tests step is mandatory; "verified-by-running" entries must exist |
| Question splurge | >5 questions, or questions the repo answers | Draft questions only after D8; delete any answerable from the ledger |
| Taxonomy inertia | 15 skills produced for a 500-line repo | Enforce the ~40-line merge threshold; thin skills are a review BLOCKER |
| Parallel drift | Two authors document the same fact differently | Boundaries live in the taxonomy table; doctrine reviewer's duplication check |
| Review rubber-stamp | Reviewers return "LGTM" | Briefs demand findings lists; a reviewer returning zero findings across a full library is itself a red flag — spot-check them |
| Confident fiction | Plausible facts nobody sourced | Ledger tracing (factual reviewer, rule 2) |

## Worked example

**Illustrative example — every fact below is fictional.**

Repo: `tidepool`, a Python data pipeline ingesting oceanographic sensor feeds.

*Phase 1 (condensed):* D2 finds `pyproject.toml` with `[tool.poetry]` → poetry.
D3: docs say `pytest`, but CI runs `poetry run pytest -m "not slow" --timeout=120`
— ledger records the CI form as ground truth; a local run passes 214, skips 31.
D5 churn puts `ingest/decoder.py` first at 87 commits; `git log --grep=revert -i
--oneline` shows 4 reverts, 3 touching `decoder.py` timestamp handling.
`git branch -r --no-merged main` shows `origin/feat/zstd-frames`, dead 14 months
(`git for-each-ref` dates it). D6: `decoder.py` also tops the FIXME count (11) —
churn + FIXME overlap flags it as the pain center. D8: `.gitignore` reveals
`data/derived/` is regenerable but `data/golden/` is committed — sacred.

*Phase 2:* Ledger cannot explain why zstd stalled or what "done" looks like.
Questions asked (3 of 5 slots — the other two were answered by history):
hardest live problem ("decoder drops frames on DST transitions"), unwritten rules
("never regenerate `data/golden/` without two sign-offs"), costliest failure
("2025 silent corruption from a tz-naive datetime; 6 weeks to find").

*Phase 3:* Result — 11 skills. Merged: `config-and-flags` → `tidepool-run-and-operate`
(only 6 flags exist); `docs-and-writing` → `tidepool-change-control`;
`research-discipline` + `proof-and-analysis` → `tidepool-evidence-standards`.
Split: none. Added: `tidepool-sensor-protocols` (frame formats and timestamp
semantics — a `domain-reference` descendant the generic set couldn't anticipate).
`tidepool-campaign-design` scopes the DST frame-drop problem.

*Phases 4–5:* 11 parallel authors, each fed the ledger + one taxonomy row. Factual
reviewer flags a BLOCKER: one author wrote `poetry run pytest --workers 4` — flag
doesn't exist in pytest (that is pytest-parallel's, not installed). Fixer replaces
it with the CI-verified command. Doctrine reviewer catches the DST triage row
duplicated in two skills; it keeps one home in `tidepool-debugging-playbook`.

## Instantiate for your project

This skill instantiates by *being run*. Executing the five phases in a real repo IS
the instantiation; the output is the `<PROJECT>-*` library plus one thin meta-skill.
A Sonnet-class model should be able to execute this list with no human help except
the Phase 2 answers and the Phase 3 taxonomy approval.

1. **Create the workspace.** In the target repo: confirm `.claude/skills/` exists or
   create it. Create a scratch dir for `evidence-ledger.md` and the contract. Record
   `git rev-parse HEAD` now — every produced skill's provenance cites this SHA.
2. **Run Phase 1 (D1–D8) yourself** — do not delegate discovery; the factory
   operator needs the whole picture. Budget: touch every D-step, even if a step
   yields "nothing found" (record that too).
3. **Run Phase 2.** One message, ≤5 questions, each tagged with why discovery
   couldn't answer it. If the human is unavailable, proceed with the canonical
   five marked `UNANSWERED` in the ledger; affected skills carry an explicit
   "assumptions pending maintainer input" block.
4. **Run Phase 3.** Produce the taxonomy table. Evidence gate: a skill may only
   exist in the taxonomy if the ledger holds at least 3 independent findings for
   it; a merge is mandatory below the ~40-line content threshold. Present the
   table to the human for approval (or mark `UNAPPROVED` and proceed).
5. **Write the project authoring contract** from this template skeleton:

   ```markdown
   # <PROJECT> Skill Authoring Contract (v1 — <DATE>)
   Derived from repo commit <SHA>. Evidence ledger: <LEDGER-PATH>.
   ## Taxonomy (approved <DATE> by <WHO> | UNAPPROVED)
   <taxonomy table: skill | generic parent(s) | scope | key ledger lines>
   ## Hard rules
   <the six Authoring rules from skill-factory, copied verbatim>
   ## Section order
   Purpose / When (NOT) to use / Core content / Worked example (real case)
   / Maintenance triggers / Provenance
   ## Reporting
   Reply with: files written; every command run to verify a claim, with what
   you observed; every claim you could NOT verify, flagged.
   ```

   Evidence gate: the contract's taxonomy rows must cite ledger line numbers.
   Do not write a scope row you cannot back with ledger findings.
6. **Run Phase 4.** Launch one author agent per skill, in parallel, each with:
   contract + ledger + its row + write access to only its own directory. Evidence
   gate per author (state it in their prompt): "Do not write a triage row you have
   not reproduced, or a command you have not run, or a fact you cannot cite to the
   ledger, a file:line, or a commit."
7. **Run Phase 5.** Launch the three reviewers with the verbatim briefs (fill
   `<PROJECT>`, `<SKILLS-DIR>`, `<LEDGER-PATH>`, `<CONTRACT-PATH>`), then the fixer.
   Exit criterion: zero open BLOCKERs; every remaining `UNVERIFIED` marker has a
   re-check command attached.
8. **Write the meta-skill `<PROJECT>-skill-factory`** (thin — under ~80 lines): the
   taxonomy table, the ledger location, the library's derivation SHA and date, and
   the procedure for adding skill N+1 (new skill must pass the same taxonomy
   evidence gate and Phase 5 review; single-skill additions may use one combined
   reviewer using all three briefs concatenated — heuristic, acceptable at small
   scale).
9. **Hand off.** Final report to the human: skill list with one-liners, open
   `UNVERIFIED`/`UNANSWERED`/`UNAPPROVED` markers, and the top three maintenance
   triggers that will stale the library first (usually: CI config change, main-tool
   version bump, resolution of the campaign problem).

## Provenance and maintenance

- Authored 2026-07-06 against no specific project, as part of the generic
  FableSkills library. All project examples herein are fictional and labeled.
- All git commands in Phase 1/D5–D6 were executed against a throwaway repository
  on 2026-07-06 (git for Windows, git 2.x) and produced the expected output,
  including the `git shortlog` stdin gotcha noted in the table.
- **Volatile parts** — re-verify before trusting:
  - Git flag syntax (stable for years, but cheap to re-check):
    `git log --help`, `git for-each-ref --help`, `git grep --help`.
  - `gh` CLI subcommands (D7): `gh issue list --help`.
  - The manifest→build-system table (D2): ecosystems shift; re-check any row
    older than ~2 years against that ecosystem's current docs.
  - Sibling skill names in the routing and taxonomy tables: re-check against the
    actual contents of `.claude/skills/` — `ls .claude/skills/`.
- Instantiated copies (`<PROJECT>-*` skills and `<PROJECT>-skill-factory`) must add
  their own provenance: author, date, repo commit SHA, and per-fact volatility
  notes. This generic skill's provenance does not transfer to them.
