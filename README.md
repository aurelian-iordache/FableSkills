# FableSkills — a discipline pack for Claude Code

**20 engineering-discipline skills that make an AI coding assistant (or a junior/mid-level engineer) work like a very senior developer: smallest honest diffs, evidence over vibes, gated changes, measured claims, and no unnecessary code.**

## Why this exists

Claude Fable 5 — Anthropic's most powerful, Mythos-class model — is leaving subscription plans and becoming pay-as-you-go only. For most developers, that means day-to-day coding moves back to less powerful models like Opus and Sonnet.

So before it went, Fable 5 was put to work at high reasoning effort on one job: **writing down how a very senior software developer actually works — so that smaller models can act like one.** This pack is what it left behind. Expensive to build once, cheap to run forever: install it, and Opus- or Sonnet-class sessions start producing smallest-honest-diff PRs, evidence-backed claims, and gated changes instead of over-engineered scaffolding — debugging, extending, validating, and operating software at a principal-engineer standard without the senior person in the room.

Every command that could be run on the authoring machine was verified by execution against the real tools; the handful that couldn't be are explicitly labeled as such — and every skill tells you exactly how to re-verify it later. The authoring itself was a multi-agent workflow: a dedicated Fable 5 authoring agent per skill, three independent review agents (factual, doctrine, usability) over every skill, and a fixer pass.

*Last verified: 2026-07-09 — tool baseline and re-verification commands in [Provenance and maintenance](#provenance-and-maintenance).*

---

## Table of contents

- [Why this exists](#why-this-exists)
- [What is a skill?](#what-is-a-skill)
- [What's in the pack](#whats-in-the-pack)
- [Installation](#installation)
- [Six rules the pack installs](#six-rules-the-pack-installs)
- [The keystone workflow: bootstrapping a project](#the-keystone-workflow-bootstrapping-a-project)
- [Skill reference](#skill-reference)
  - [The keystone](#the-keystone)
  - [Core discipline (project-agnostic)](#core-discipline-project-agnostic)
  - [Knowledge and documentation (project-agnostic)](#knowledge-and-documentation-project-agnostic)
  - [Advanced discipline (project-agnostic)](#advanced-discipline-project-agnostic)
  - [Stack tier (C# / .NET / EF Core / SQL Server / ASP.NET Core / React)](#stack-tier-c--net--ef-core--sql-server--aspnet-core--react)
- [How the skills work together](#how-the-skills-work-together)
- [Included scripts](#included-scripts)
- [Conventions used inside the skills](#conventions-used-inside-the-skills)
- [Provenance and maintenance](#provenance-and-maintenance)

---

## What is a skill?

A **skill** is a Markdown file (`SKILL.md`) that [Claude Code](https://claude.com/claude-code) — Anthropic's AI coding agent that runs in your terminal and IDE — loads automatically when it becomes relevant to the task at hand. Each skill starts with a YAML header containing a `description` — a list of the situations, symptoms, and phrasings that should trigger it. When you ask Claude to "add a migration" or "figure out why this test is flaky", it matches your request against those descriptions and pulls the right skill into context **before** doing the work.

A skill is not a chat prompt and not documentation you have to remember to read. It is a runbook the assistant is *bound by* while working: checklists it must run, commands it must use, traps it must avoid, and gates it must not route around. You install it once; it applies every session, automatically.

Each skill in this pack follows the same six-section structure:

1. **Purpose** — what the skill makes you able to do.
2. **When to use / When NOT to use** — including a routing table: "if you actually need X → use sibling skill Y."
3. **Core doctrine** — the methodology: decision tables, checklists, trap catalogs, verified commands.
4. **Worked example** — a compact, clearly-labeled fictional walk-through.
5. **Instantiate for your project** — step-by-step instructions for generating a *project-specific* version of the skill by mining a real repository (git history, CI config, manifests), with evidence gates so nothing gets written down that wasn't proven.
6. **Provenance and maintenance** — when it was verified, against which tool versions, and one-line commands to re-verify anything that may have drifted.

## What's in the pack

Two tiers, twenty skills:

| Tier | Count | What it covers |
|---|---|---|
| **Project-agnostic** | 15 | Universal engineering discipline: how changes are gated, how bugs are diagnosed, what counts as proof, how environments are rebuilt, how docs stay true — any codebase, any language. |
| **Stack tier** | 5 | Deep, verified discipline for a specific stack: **C#/.NET**, **ASP.NET Core**, **Entity Framework Core**, **SQL Server**, and **React + TypeScript**. Stack facts were verified against the real tools (SDK 10.0.301, EF Core 10.0.9, ASP.NET Core 10.0.9, SQL Server LocalDB, npm registry as of 2026-07-06) or explicitly tagged `[docs]` with a re-verification command. |

The project-agnostic tier is useful even if your stack is Go, Python, or Java — the stack tier is what makes the pack immediately powerful for .NET + React shops.

## Installation

The pack is a directory of folders, one per skill:

```text
.claude/
  skills/
    architecture-contract/SKILL.md
    aspnet-api-discipline/SKILL.md
    build-and-env/SKILL.md
    ...
    diagnostics-and-tooling/SKILL.md
    diagnostics-and-tooling/scripts/...
    ...
```

**Option A — per project.** Copy the `.claude/skills/` directory into the root of a repository.

Linux/macOS/Git Bash:

```sh
git clone https://github.com/aurelian-iordache/FableSkills.git fableskills
mkdir -p <your-project>/.claude
cp -r fableskills/.claude/skills <your-project>/.claude/
```

Windows PowerShell:

```powershell
git clone https://github.com/aurelian-iordache/FableSkills.git fableskills
New-Item -ItemType Directory -Force <your-project>\.claude | Out-Null
Copy-Item -Recurse fableskills\.claude\skills <your-project>\.claude\
```

Every Claude Code session opened in that project now has all 20 skills. Commit the directory so your whole team (and their AI sessions) share the same discipline.

**Option B — per machine (all projects).** Copy the skills into your user-level Claude directory instead.

Linux/macOS/Git Bash:

```sh
mkdir -p ~/.claude/skills
cp -r fableskills/.claude/skills/* ~/.claude/skills/
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills" | Out-Null
Copy-Item -Recurse fableskills\.claude\skills\* "$env:USERPROFILE\.claude\skills\"
```

Now every project on the machine gets the pack, with no per-repo setup. This is the right choice for a new machine: install Claude Code, copy one folder, done.

**Both at once** also works: user-level for the generic tier, per-project for stack skills or project-specific instantiated skills (see the keystone workflow below). If the same skill name exists in both places, the project-level copy wins per Claude Code's precedence rules.

There is nothing to build and no dependency to install — skills are plain Markdown. The four bundled scripts require only Python 3.

**Try it.** Open Claude Code in a project with the pack installed and ask for something ordinary — "add a migration" or "why is this test flaky?". You'll see the session load the matching skill (e.g. `dotnet-ef-discipline`) and follow its checklists and pre-flights instead of improvising.

## Six rules the pack installs

Every skill enforces some part of the same philosophy. If you remember nothing else, remember these:

1. **Smallest honest diff.** Solve the stated problem with the fewest files and lines that leave the code healthy. No drive-by refactors, no speculative abstractions, no code without a caller. AI assistants are *notorious* for generating interface + factory + mapper scaffolding for a two-line need; this pack makes the assistant justify every new file and type before writing it.

2. **Evidence over vibes.** "Looks good", "should work", and "feels faster" are banned as acceptance criteria. Claims are graded on an evidence hierarchy (reproduced-and-observed > automated test > recorded manual test > reasoning > vibes), timings come from N runs with percentiles instead of one lucky run, and hypotheses must predict numbers *before* the experiment runs.

3. **Changes are classified and gated.** Every diff is classed — **M**echanical, **B**ehavioral, **C**ontract-breaking, or irreversible (**X**) — and each class has a proportionate gate. Golden files never change "to make tests pass"; acceptance thresholds never move after seeing results; production schemas never receive an unreviewed migration. No skill in the pack is allowed to route around these gates, and several exist specifically to feed them.

4. **Measure, don't eyeball.** Recurring questions ("is it faster?", "did the output change?") get purpose-built diagnostic tools with interpretation guides, not scrolling and squinting. The pack ships runnable scripts for run-comparison, timing statistics, benchmark verdicts, and git-history mining.

5. **History is evidence.** Before any non-trivial investigation, check whether the battle was fought before. Closed investigations, dead ends, and reverts are recorded as chronicle entries (symptom → root cause → evidence → status) so nobody — human or AI — re-tries an approach that already failed.

6. **Docs that can't rot silently.** Every volatile fact carries a date stamp and a one-line re-verification command. Runbooks are proven by execution, not by review. Each fact lives in exactly one home; everything else links to it.

The practical effect: sessions produce smaller PRs, fewer reverts, reproducible claims, and a paper trail that survives team and model changes.

## The keystone workflow: bootstrapping a project

The pack's most important skill is **skill-factory**. The 20 skills here are deliberately *generic* — they teach method, not the facts of your codebase. When you start long-term work on a real repository, you say:

> "Bootstrap the skill library for this repo."

skill-factory runs a principal-engineer discovery protocol: README/manifests, how tests are *actually* run (CI config as ground truth, not docs), git history mining (what churned, what got reverted, what stalled on dead branches), TODO/FIXME hotspots. It then asks you **at most five questions** about what the repo cannot tell it. Finally it authors a set of 10–16 *project-specific* skills (`<PROJECT>-debugging-playbook`, `<PROJECT>-build-and-env`, …) using the generic skills as templates, and puts them through a three-reviewer verification pass (factual / doctrine / usability) plus a fix round.

The evidence rule is strict: nothing goes into a project skill that doesn't trace to a file:line, a commit SHA, or a command the session actually ran. A wrong runbook is worse than none.

The result: from then on, sessions in that repo load skills containing *your* project's build commands, *your* known traps, *your* failure history — at the quality bar this pack sets.

---

## Skill reference

For each skill: **Loads when** (what triggers it), **Checks / enforces** (the discipline it applies), and **How it improves development**.

### The keystone

#### `skill-factory`
- **Loads when:** you're dropped into a repository with no project-specific skills — "bootstrap skills for this repo", "onboard this project", or starting long-term work on an unfamiliar codebase.
- **Checks / enforces:** an ordered discovery protocol (docs → build system → tests-as-CI-runs-them → git history mining → TODO hotspots → deploy conventions); an evidence ledger where every stated fact must trace to file:line, commit SHA, or an executed command; a five-question budget for the human; taxonomy adaptation rules (merge thin categories, split deep ones, never reinvent what a stack-tier skill already owns); a parallel authoring + three-reviewer + fixer workflow with verbatim reviewer briefs.
- **How it improves development:** turns "AI session in an unfamiliar repo" from guesswork into a repeatable onboarding procedure that produces a durable, verified knowledge base — the difference between an assistant that asks you everything twice and one that already knows how your project actually works.

### Core discipline (project-agnostic)

#### `change-control`
- **Loads when:** deciding how risky a change is and what gate it must pass — "does this need review?", "can I just push this?", "we keep reverting things", "emergency deploy", or setting up branch protection for a new repo.
- **Checks / enforces:** the M/B/C/X change taxonomy (mechanical / behavioral / contract-breaking / irreversible) with a gate table per class (CI, approvals, evidence, rollback plans, cooling-off); a NON-NEGOTIABLES registry format where every rule carries its rationale *and* the incident behind it; per-class reviewer checklists; a break-glass protocol that reorders gates in time instead of deleting them; a failure-mode table for the control system itself (rubber-stamping, gate inflation, routing-around).
- **How it improves development:** risk-proportionate process — trivial changes stop being over-reviewed, dangerous ones stop slipping through, and "add a rule so this never happens again" produces a written rule with teeth instead of tribal memory.

#### `debugging-playbook`
- **Loads when:** a bug, test failure, regression, crash, or "it worked yesterday" needs diagnosing; "debug", "figure out why", "track down", "bisect".
- **Checks / enforces:** a seven-step debugging loop centered on **discriminating experiments** (experiments whose outcome cleanly separates competing hypotheses — the opposite of confirmatory poking); full `git bisect` discipline including `bisect run` automation; hard rules against shotgun debugging and fix-by-coincidence (the un-fix/re-fix closing gate: a fix you can't turn back off isn't understood); a symptom→triage table format where a row may only be written if it was reproduced or is backed by a commit/issue; trap records with their stories and time cost.
- **How it improves development:** investigations converge instead of wandering. The evidence gate on triage tables means the project accumulates *reliable* diagnostic knowledge, and every closed investigation feeds a regression test and a chronicle entry.

#### `failure-archaeology`
- **Loads when:** before starting any non-trivial investigation (has this been fought before?), when a fix feels familiar, when someone proposes retrying something that "didn't work last time", or when writing up a closed investigation or revert.
- **Checks / enforces:** the chronicle entry format — symptom → root cause → evidence → status (exactly `fixed | mitigated | wontfix | open | superseded`) — with dead ends recorded explicitly ("we tried X, it failed because Y, do not retry unless Z changes"); rules of evidence (entries cite commits/issues/repro logs, never memory); a verified git-history mining toolkit (revert hunting, `-S`/`-G` pickaxe, fix-of-a-fix chains, abandoned branches) plus a runnable miner script.
- **How it improves development:** settled battles stay settled. One of the most expensive failure modes of team+AI development — re-investigating something someone already solved or already disproved — gets a mechanical check.

#### `build-and-env`
- **Loads when:** recreating a dev environment from scratch, writing or fixing setup runbooks, "works on my machine", "builds in CI but not locally", pinning toolchains, auditing dependencies.
- **Checks / enforces:** the FROM-SCRATCH RUNBOOK format (each step has a verify command and expected output); the **clean-room proof rule** — a setup runbook is not done until it has been executed on a machine that never had the project (with a 4-level ladder of cheap clean-room approximations); a known-traps catalog (version conflicts, PATH shadowing, CRLF, proxy/cert, lockfile drift) in Symptom/Cause/Fix/Tell format; toolchain pinning (`global.json`, `.nvmrc`, lockfiles, local `dotnet tool` manifests); the rule that **CI config is the real build documentation**.
- **How it improves development:** onboarding a new machine or engineer drops from days of folklore to an executable checklist, and "works on my machine" becomes a diagnosable class of bug instead of a shrug.

#### `run-and-operate`
- **Loads when:** running, deploying, or operating a project day to day — "how do I run this", "where does the output go", "is it safe to re-run", "roll back the deploy", or any command touching a production path.
- **Checks / enforces:** COMMAND ANATOMY blocks (what it does, flags that matter, output paths, expected duration, success/failure signatures, idempotency); artifact classification (REGENERABLE / PRECIOUS / EXPENSIVE) with retention rules; the OUTPUT MAP (artifact → producing command → path → consumer); deploy runbooks with pre-flight, post-deploy verification, and a **rehearsed** (date-stamped) rollback; six unconditional safety rails (dry-run first, the irreversibility test, echo-the-prod-target before acting, and more).
- **How it improves development:** operational actions stop being tribal knowledge, and the safety rails specifically prevent the catastrophic category — an assistant or junior running a destructive command against the wrong environment.

#### `config-and-flags`
- **Loads when:** adding/flipping/retiring a feature flag, env var, CLI switch, or default; "make it configurable"; "why is this flag on in prod"; "the config docs are out of date".
- **Checks / enforces:** an 11-field catalog entry per configuration axis (default, prod-vs-experimental status, guard/kill-switch, owner, interaction warnings, per-row verify command); the ADD-A-FLAG checklist — new behavior defaults **OFF**, the OFF path is the literal old code path, retirement plan written at creation; a 4-stage lifecycle where flag *removal* is a gated contract-breaking change; config drift as a first-class problem with mechanical re-verification sweeps.
- **How it improves development:** kills the two classic flag disasters — the experimental flag that silently became load-bearing, and the config catalog that lies about defaults.

#### `diagnostics-and-tooling`
- **Loads when:** you're about to eyeball program output instead of measuring — comparing runs by scrolling, quoting a timing from a single run, saying "looks the same" — or the same question about speed/correctness/what-changed comes up twice.
- **Checks / enforces:** the prime rule — eyeballing is allowed for *forming* hypotheses, never for accepting them; the DIAGNOSTIC TOOL SPEC format (question answered, how to run, an interpretation guide mapping output ranges to actions, known blind spots); baseline discipline (a measurement means nothing without a recorded baseline; re-baselining anything that gates CI routes through change control); an anomaly log; a trap catalog of measurement itself (observer effect, averaging away the tail, comparing across changed conditions).
- **How it improves development:** replaces "I think it's faster now" with numbers, and turns recurring manual checks into reusable tools. Ships two scripts: a JSON-aware run comparator and a timing-stats harness (min/median/p95 with warmup discard).

#### `validation-and-qa`
- **Loads when:** deciding whether a change is actually proven — "tests pass", "looks good", "should work" — or adding/updating/deleting tests, moving acceptance thresholds, updating golden files, handling flaky tests.
- **Checks / enforces:** the five-grade evidence hierarchy and what each grade is sufficient *for*; thresholds set in writing **before** running (loosening one afterward is a gated change; tightening is ungated but recorded); the certified/golden inventory — goldens change only through explicit re-certification, never as a side effect of "updating tests to pass"; tests that pay rent (every test names the bug class it defends against; a test that can't fail is deleted); flaky-test quarantine (flakiness is a bug with a root cause, never retry-until-green as policy).
- **How it improves development:** "done" gets an objective definition. The golden-inventory rule alone prevents the slow corruption of test suites that plagues long-lived projects — especially ones where an AI is asked to "fix the failing tests".

### Knowledge and documentation (project-agnostic)

#### `architecture-contract`
- **Loads when:** documenting, auditing, or recovering a system's load-bearing design decisions — "why is it built this way?", "what can we safely change?", "write an ADR", or inheriting an undocumented codebase.
- **Checks / enforces:** the contract entry format — decision, the WHY (constraints and rejected alternatives), checkable invariants each with a verify hook, and blast radius; the flip test for what counts as load-bearing ("what breaks if we flip this?"); a euphemism-free KNOWN-WEAK-POINTS section (banned phrasings; you must be able to predict the failure); minimal ADR practice with strict superseding rules; a reverse-engineering procedure for undocumented systems (import fan-in, schema/wire boundaries, what the tests defend hardest) with an "UNKNOWN over fabricated WHY" honesty rule.
- **How it improves development:** the difference between architecture folklore and an architecture *contract* — newcomers and AI sessions learn what must not be broken and why, and weak points are stated plainly instead of discovered in production.

#### `domain-reference`
- **Loads when:** authoring or extending a project's domain-theory knowledge pack — "why is this constant 86400", "what does the spec say here", unexplained magic numbers, or onboarding into a standards-heavy codebase (payments, networking, medical, DSP…).
- **Checks / enforces:** the governing-line scoping test (a domain fact earns its place only if it governs a specific line of code or config); a five-part entry structure (concept → why it matters here → governing rule with section-level citation → code it touches → the mistake made without it); citation tiers (primary sources cited to section numbers; runnable checks preferred; `UNVERIFIED` labels where confirmation isn't possible); the anti-textbook-dump rule.
- **How it improves development:** captures exactly the knowledge that mid-level engineers and small models silently get wrong — the field math and standards behind the code — without turning docs into a textbook nobody reads.

#### `docs-and-writing`
- **Loads when:** creating, auditing, or reorganizing documentation; docs described as "stale", "wrong", "duplicated", "scattered"; "where should this be documented?"
- **Checks / enforces:** the doc-of-record rule (one home per fact, links everywhere else); a four-type taxonomy — runbook / reference / explanation / onboarding — each with its own verification method (runbooks are verified by *execution*); rot detection — every doc carries `Last verified:` and `Re-verify:` lines, plus six mechanical audit commands (dead-path detection, date audits, missing-provenance greps); runbook house style (imperative voice, expected output after every command, one action per step); the write-at-the-moment rule.
- **How it improves development:** documentation becomes falsifiable. Rot gets *detected* by commands instead of discovered by a failed 2 a.m. runbook.

### Advanced discipline (project-agnostic)

#### `campaign-design`
- **Loads when:** a problem is too big for one session — a persistent regression, memory leak, flaky-test epidemic, or a migration that has already burned multiple attempts — and needs to become a written, executable campaign; "plan the investigation", "make this resumable".
- **Checks / enforces:** the campaign document anatomy — numbered phases with exact commands, **numeric gates** with expected observations, and explicit branch rules ("if you see X instead of Y → go to phase N"); a ranked solution menu where each candidate carries its proof obligations; fenced wrong paths (approaches already known to fail, with the evidence); kill criteria fixed at design time; a status block so a fresh session can resume mid-campaign from the document alone; success promoted only through change control — measured, never judged by eye.
- **How it improves development:** hard problems stop resetting to zero every session. A campaign doc is the difference between "attempt #5, again from scratch" and a decision-gated march where even a context-free session knows exactly where things stand.

#### `proof-and-analysis`
- **Loads when:** a claim needs first-principles verification instead of trust — "is this actually faster", "will this scale", "is this correct for all inputs", "should we adopt this library", "benchmark says X — is that real".
- **Checks / enforces:** six recipes, each with a worked example: (1) invariant arguments backed by property-based testing (Hypothesis / fast-check / FsCheck); (2) complexity analysis validated by measurement at two scales (predicted ratio vs observed); (3) statistically honest benchmarks — a claimed speedup must exceed run-to-run noise, with a runnable verdict script that says CONCLUSIVE or INCONCLUSIVE; (4) Fermi estimation against written budgets; (5) FMEA-lite failure enumeration at boundaries; (6) the prove-it-before-adopting checklist for any new dependency.
- **How it improves development:** "prove it, don't just install it." Performance work and dependency choices get the same rigor as code review, and single-run benchmark theater dies.

#### `research-discipline`
- **Loads when:** a hunch or optimization idea needs to become an accepted result — "I have a theory", "this should be faster", "let's try" — or someone wants to claim novelty or publish a benchmark number.
- **Checks / enforces:** the evidence bar — one mechanism must explain **all** observations including the negatives; hypotheses must predict numbers in writing *before* the experiment (post-hoc reinterpretation kills the hypothesis); assigned adversarial refutation (someone is explicitly tasked with breaking the result before acceptance); the idea lifecycle from experiment-behind-a-flag to adopted change *or documented retirement* (retirement is a success outcome, recorded in the chronicle); honest external-claim standards — a novelty audit before "novel" is written anywhere, and a reproducibility bar for any published number.
- **How it improves development:** protects the project from its own enthusiasm. Ideas get a fair, fast, falsifiable trial — and dead ideas stay dead instead of resurrecting quarterly.

### Stack tier (C# / .NET / EF Core / SQL Server / ASP.NET Core / React)

Stack-tier skills may state facts about their stack — but only facts verified against the real tools and version-stamped, or explicitly tagged `[docs]` with a re-verification command. Verified baseline: **.NET SDK 10.0.301 / C# 14**, **EF Core 10.0.9**, **ASP.NET Core 10.0.9**, **SQL Server LocalDB 17.0.4025**, npm registry as of 2026-07-06.

#### `csharp-code-discipline`
- **Loads when:** *before writing or reviewing any C# code* — even when the language isn't named: any task touching `.cs` files ("add a feature", "fix this bug", "refactor this method"), plus "should I use a pattern here?", "this PR feels over-engineered", "set up analyzers".
- **Checks / enforces:**
  - The **smallest-honest-diff** prime directive: a pre-write checklist (new file? new type? new interface? new package? — each defaults to NO until evidence flips it) and a post-write self-review (every public member has a caller; every abstraction has ≥2 implementations or a written reason; zero unrelated diff lines).
  - The **U1–U10 unnecessary-code catalog**: interface-with-one-implementation disease, repository-over-EF, delegating wrappers, premature `Result<T>`, god Utils classes, and five more — each in Symptom/Cause/Fix/Tell format.
  - A **GoF-pattern decision table** mapping each pattern to its .NET-idiomatic form — Observer = events, Strategy = delegates/DI, Singleton = container lifetime. The platform already ships most patterns; the skill teaches recognizing when the idiom replaces the textbook version.
  - A **version-stamped modern C# baseline** (records, pattern matching, nullable reference types, async rules) and per-diff architecture rules (dependency-direction smells, internal-by-default, constructor-injection limits).
  - **Analyzer enforcement verified live**: `.editorconfig` severities, `EnableNETAnalyzers`/`AnalysisLevel`, `dotnet format --verify-no-changes`, `dotnet build -warnaserror --no-incremental` — including the discovered trap that incremental builds false-pass `-warnaserror`.
- **How it improves development:** directly attacks the quality problem AI-generated C# is most notorious for — over-engineering. Output shifts from 5 files of ceremony to the 2 files the task needed, and "good practices" become analyzer rules that fail the build instead of review-comment nagging.

#### `aspnet-api-discipline`
- **Loads when:** anything crossing an ASP.NET Core API's HTTP wire — adding or changing an endpoint, shaping a DTO ("DateTime or DateTimeOffset?"), returning errors, setting up or consuming the OpenAPI document, versioning, "does this change break clients?", or when a React consumer reports wrong dates or mismatched types. Co-loads with `csharp-code-discipline` on "add an endpoint" — this skill owns the wire, that one owns the code.
- **Checks / enforces:**
  - The **contract-first prime rule**: DTOs are wire contracts, EF entities never cross the wire — with a PRE-SHAPE/POST-SHAPE checklist run before shaping any DTO or endpoint.
  - A 10-row **API breaking-change taxonomy** (field removal, type changes, nullability, enum additions that break exhaustive TypeScript switches, semantic changes invisible to tooling) mapped to change-control classes, with an honest consumer condition: out-of-repo consumers → contract-breaking; same-repo lockstep consumers → behavioral; cached SPA bundles count as out-of-repo at runtime.
  - **Observed System.Text.Json wire law** with captured evidence: camelCase, `DateTime` Local serializing with the *server machine's* offset, enum-as-number by default, null emission.
  - One **ProblemDetails (RFC 9457) error contract** for the whole API, with verified `IExceptionHandler` wiring and captured proof that Development leaks stack traces while Production goes silent.
  - **OpenAPI as a CI artifact**: the document generated at build time and diffed in CI as a breaking-change tripwire feeding change-control review.
  - A discovered .NET 10 trap, independently reproduced: minimal-API validation **silently skips non-`public` DTOs** — an invalid request returns 201.
- **How it improves development:** the API stops breaking its consumers by accident. Wire-format questions that usually get folklore answers ("dates are weird sometimes") get captured-output answers, and contract changes become visible, classified, gated events.

#### `dotnet-ef-discipline`
- **Loads when:** any Entity Framework Core work — "add a migration", "the model snapshot has a merge conflict", "can I edit this migration?", "which database is this pointing at?", N+1/slow LINQ queries, DbContext lifetime errors.
- **Checks / enforces:**
  - The **full verified migration lifecycle**: `add` / `remove` / `list` / `database update` / `script --idempotent` / `bundle` / `has-pending-model-changes`.
  - **Migrations as gated changes**: destructive migrations are irreversible-class; production never sees `dotnet ef database update` — idempotent scripts or bundles, reviewed as artifacts.
  - An **8-trap catalog with a symptom index**: snapshot merge conflicts, out-of-order migrations across branches (with the rebase recipe), never-edit-an-applied-migration, the scaffold-time data-loss warning, untested `Down()` methods, provider differences.
  - The **which-database pre-flight**: `dotnet ef dbcontext info` before any update — connection source printed and confirmed.
  - **Query and DbContext discipline**: `AsNoTracking` decision rule, N+1 detection via command logging, `AsSplitQuery`, scoped lifetime rules, and entity-shape rules (why records are wrong for EF entities).
- **How it improves development:** EF migrations are where junior mistakes destroy data. This skill converts the entire migration workflow into verified commands with explicit gates, and makes "wrong database" — the most expensive class of accident — a checked pre-flight instead of a hope.

#### `sql-server-operations`
- **Loads when:** operating SQL Server beyond CRUD — "the database is slow", "queries are timing out", "something is blocking", "should I add this index?", "is our backup any good?", reading execution plans, or ad-hoc UPDATE/DELETE against shared data.
- **Checks / enforces:**
  - A **verified DMV (dynamic management view) diagnostic query pack**, each query with an interpretation guide: top queries by CPU/reads, blocking chains, wait stats with a benign-exclusion list, missing-index DMVs with the mandatory "suggestions are naive" warning.
  - **Plan reading for non-experts**: scans vs seeks, key lookups, spills, and the nvarchar implicit-conversion classic — with a measured 59-vs-256-reads reproduction.
  - **Index discipline**: every index change is a measured before/after and a gated change; statistics staleness; when NOT to add an index.
  - **Backup/restore as proof**: a backup that has never been restored is a hope, not a backup — restore rehearsals, recovery models, `RESTORE VERIFYONLY` as necessary-not-sufficient.
  - The **mandatory ad-hoc DML ritual**: SELECT-first with the same WHERE, predict the row count *before* running, `BEGIN TRAN`, check `@@ROWCOUNT` against the prediction, then commit or roll back — with the *decision* to run it classified through change control.
- **How it improves development:** database operations get the same evidence discipline as code, and the ad-hoc DML ritual makes the classic careless-UPDATE data-loss accident a checked procedure instead of a hope.

#### `react-frontend-discipline`
- **Loads when:** React + TypeScript work — "should this be useState / context / Redux?", writing or reviewing a `useEffect`, adding data fetching, sprinkling `useMemo`/`React.memo`, writing component tests, typing an API client against a .NET backend.
- **Checks / enforces:**
  - The **state-ownership decision table**, with the load-bearing rule **server state is not client state**: fetch-cache libraries own server data; copying it into `useState` is the root of most staleness bugs.
  - The **effect trap catalog**: derived-state-in-effect, fetch race conditions (with the abort/cleanup pattern), dependency-array lies, StrictMode double-invocation "fixes" that break correct code.
  - **Measured memoization**: `React.memo`/`useMemo`/`useCallback` only after the React DevTools Profiler shows a real problem — measured, not guessed.
  - **Testing doctrine**: React Testing Library (test what the user sees, query by role), MSW at the network boundary, snapshots labeled low-value.
  - The **.NET API boundary**: client types generated from the backend's OpenAPI document (never hand-maintained parallel DTOs), runtime validation at the boundary, and a date-handling story consistent with `aspnet-api-discipline`'s captured wire behavior.
  - A **version-stamped tooling baseline** with re-verification commands — the React ecosystem rots fastest, so every package claim carries its check.
- **How it improves development:** front-end code stops accumulating the two classic React pathologies — effect spaghetti and premature memoization — and the .NET↔React boundary becomes generated + validated instead of hand-synced and silently drifting.

---

## How the skills work together

The skills form a system, not a list. Three mechanisms connect them:

**Routing tables.** Every skill's "When NOT to use" section names the sibling that owns the neighboring concern. Ask about a slow EF query and land in `sql-server-operations`? Its routing table sends you to `dotnet-ef-discipline`, and vice versa — the boundary (what EF generates vs how SQL Server executes it) is stated on both sides. A mis-routed session self-corrects in one read.

**Deliberate co-loading.** Some tasks are two disciplines at once. "Add an endpoint" loads both `csharp-code-discipline` (the code inside the handler) and `aspnet-api-discipline` (the wire contract) — both descriptions say so explicitly.

**Gates.** Anything that changes behavior routes through `change-control`'s classification — skills feed the gates; none bypasses them. Closed investigations feed `failure-archaeology`; accepted results feed regression tests via `validation-and-qa`; wire policies feed `architecture-contract`.

A typical full-stack change touches five skills without you asking for any of them: the C# checklist keeps the diff minimal, the API skill classifies the contract impact, the EF skill gates the migration, validation-and-qa defines what proof of correctness looks like, and change-control decides who must look at it before it ships.

## Included scripts

Four portable Python 3 scripts ship inside the skills (stdlib only, no dependencies), each verified by execution:

| Script | Home | What it does |
|---|---|---|
| `mine_incidents.py` | failure-archaeology | Mines a git repo's history for chronicle candidates: reverts, fix-of-a-fix chains, high-churn files. |
| `compare_runs.py` | diagnostics-and-tooling | Diffs two run outputs (JSON-aware, with numeric tolerances) and reports structured differences. |
| `timing_stats.py` | diagnostics-and-tooling | Runs a command N times with warmup discard, reports min/median/p95/max. |
| `bench_verdict.py` | proof-and-analysis | Applies the overlap decision rule to two benchmark sample files → CONCLUSIVE / INCONCLUSIVE with exit codes for CI. |

Run them with `python3` (Linux/macOS) or `py` (Windows).

## Conventions used inside the skills

- **`<ALL-CAPS>` placeholders** (`<PROJECT>`, `<TEST-CMD>`, `<MAIN-BRANCH>`) mark everything project-dependent. If a command contains one, substitute your value; nothing with a placeholder is meant to run verbatim.
- **`[verified]` vs `[docs]` tags** in the stack tier: `[verified]` means the behavior was observed by execution on the stated version; `[docs]` means it comes from official documentation and carries a re-verification command. (`react-frontend-discipline` uses inline dated stamps — "verified 2026-07-06 via `npm view`" — instead of bracket tags.) Nothing is stated as observed that wasn't.
- **Labeled heuristics.** Judgment calls are marked `heuristic` or `candidate practice` — defensible defaults, not laws. Unlabeled rules are the load-bearing ones.
- **Illustrative examples** use obviously fictional projects and are labeled as such; no example is a claim about a real system.

## Provenance and maintenance

- Built 2026-07-06 → 2026-07-09 with **Claude Fable 5** (model ID `claude-fable-5`) at high reasoning effort, orchestrating parallel authoring agents (one per skill). Every skill was then reviewed by three independent Fable 5 reviewer agents (**factual** — commands re-executed against real tools; **doctrine** — cross-skill contradictions and gate integrity; **usability** — trigger quality and zero-context executability), then fixed. Per the build's review records (not included in this repo), the four review waves surfaced 4 blocking and ~55 important findings, all fixed before release.
- Verified tool baseline: .NET SDK 10.0.301 (C# 14), EF Core 10.0.9, ASP.NET Core 10.0.9, SQL Server LocalDB 17.0.4025, git 2.52, npm 11.12, Node 24. Facts tied to these versions are stamped in place.
- Commands for tools not present on the authoring machine (`gh`, docker, kubectl, aws, make) are knowledge-checked, explicitly labeled as not-locally-verified, and carry re-check one-liners.
- Every skill ends with its own **Provenance and maintenance** section: what may drift, and the exact command that re-verifies it. If you adopt this pack months from now, run those one-liners for the skills you rely on — especially `react-frontend-discipline`, whose ecosystem moves fastest.
