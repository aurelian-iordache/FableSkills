---
name: build-and-env
description: Load this skill when you must recreate a project's development environment from scratch, write or fix a setup/onboarding runbook, diagnose "works on my machine" / "builds in CI but not locally" failures, pin toolchain versions, or audit dependencies. Delivers the FROM-SCRATCH RUNBOOK format, the CLEAN-ROOM PROOF rule for validating it, a KNOWN TRAPS catalog format, and toolchain-pinning discipline with verified npm/dotnet/python commands.
---

# build-and-env — From-Scratch Environment Recreation

## Purpose

This skill makes you able to (1) write a setup runbook that takes a machine that has
never seen the project to a passing build, (2) *prove* that runbook works via a
clean-room rebuild instead of assuming it, (3) capture environment traps so the next
person loses minutes instead of days, and (4) pin the toolchain so "it built yesterday"
stays true tomorrow.

## When to use / When NOT to use

Use when: onboarding a new machine, container, CI runner, or engineer; the build fails
only on some machines; you are writing or reviewing `SETUP.md`/`CONTRIBUTING.md`; a
dependency or toolchain upgrade broke the build; you suspect the documented build steps
have drifted from what CI actually runs.

| If instead you need... | Use sibling skill |
|---|---|
| To run/deploy the already-built system, or know where outputs land | `run-and-operate` (running comes after building) |
| The full new-repo discovery protocol (CI mining is one part of it) | `skill-factory` |
| To debug product behavior, not environment/build failures | `debugging-playbook` |
| To catalog runtime configuration options and flags | `config-and-flags` |
| To decide whether a build change needs review/gating | `change-control` |
| EF Core migration tooling and lifecycle (dotnet-ef, migrations) | `dotnet-ef-discipline` |
| C# analyzer/style enforcement content: .editorconfig rules, warnings-as-errors posture, `dotnet format` gate | `csharp-code-discipline` (§6 owns which checks; this skill owns wiring them into CI) |
| React/TS front-end tooling baseline (Vite, vitest, versions) | `react-frontend-discipline` |
| What the build-time OpenAPI document step is for and its CI drift gate | `aspnet-api-discipline` §6.2–6.3 (this skill owns wiring checks into CI) |

Boundary rule: this skill ends the moment `<BUILD-CMD>` and `<TEST-CMD>` pass on a
clean machine. Everything after that (launching, data, deploys) is `run-and-operate`.

## Core doctrine

### 1. The FROM-SCRATCH RUNBOOK format

A setup runbook ("runbook" = an ordered, copy-pasteable procedure with verification
at every step) MUST contain these four blocks, in this order:

**Block A — Prerequisites table.** Exact versions and a check command for each.
"Latest" is not a version. A prerequisite without a check command is a guess.

| Prerequisite | Required version | Check command | Expected output |
|---|---|---|---|
| `<TOOL>` | `<EXACT-OR-RANGE>` | `<TOOL> --version` | `<VALUE>` or range |

Rules for Block A:
- The required version comes from the repo's pin files (see §4), never from
  whatever the author happens to have installed.
- Include OS/arch constraints if any ("x64 only", "requires WSL2") as table rows.
- Include credentials/access prerequisites (private registry token, VPN) as rows
  with a check command (e.g. `npm ping` for registry reachability, or an
  authenticated `curl`/`gh auth status` style probe).

**Block B — Ordered setup steps.** Every step has three parts:

```
Step N: <imperative instruction, one action>
    Command:  <copy-pasteable command>
    Verify:   <command that proves the step worked>
    Expect:   <the exact-enough output: a string to see, an exit code, a file that now exists>
```

A step without Verify/Expect is a hope, not a step. If a step can fail silently
(env var exported in the wrong shell, installer that "succeeds" without adding to
PATH), the Verify line is where you catch it.

**Block C — Final acceptance.** The runbook ends with `<BUILD-CMD>` and `<TEST-CMD>`
plus their expected outputs (e.g. "exit code 0, N tests passed, artifact appears at
`<ARTIFACT-PATH>`"). Passing Block C is the definition of done for setup.

**Block D — Total expected time.** One line: "Fresh machine to green build:
~X minutes (Y of which is downloads)." Measure it during the clean-room proof
(§2) — do not estimate. When a reader is at 3× the stated time, that is their
signal that something is wrong and they should check KNOWN TRAPS.

### 2. The CLEAN-ROOM PROOF rule

**A setup runbook is not done until it has been executed, exactly as written, on a
machine that never had the project.** Author-machine success proves nothing: your
machine has years of accreted global tools, caches, env vars, and PATH entries that
silently satisfy undocumented prerequisites.

Clean-room options, strongest to cheapest:

| Level | Method | What it catches | Cost |
|---|---|---|---|
| 1 | Fresh VM or brand-new physical machine | Everything, incl. OS-level deps | High |
| 2 | Docker container from a base image | Everything except host-OS specifics | Low (if Docker available) |
| 3 | New OS user account on your machine | User-level config, HOME-dir caches, user PATH | Low |
| 4 | Faked clean room (below) | Repo-local and cache-level drift only | Minutes |

**Level 2 recipe (preferred when Docker is available).** Mount nothing but the
runbook; clone inside the container so no host state leaks:

```
docker run --rm -it <BASE-IMAGE> bash
# inside: follow the runbook literally, starting from "install git" if the image lacks it
```

Real base images to start from: `ubuntu:24.04` (forces you to document toolchain
install), or ecosystem images like `node:22-bookworm`, `mcr.microsoft.com/dotnet/sdk:8.0`,
`python:3.12-slim` (skips toolchain install — only use these if your runbook's scope
starts after toolchain install, and say so in the runbook).

**Level 3 recipe (no Docker, e.g. locked-down Windows).** Create a new local user
(Windows: `net user cleanroom <PASSWORD> /add`, or Settings > Accounts; Linux/macOS:
`useradd`/System Settings), log in as that user, follow the runbook. This gets a
fresh HOME, fresh user PATH, fresh per-user caches.

**Level 4 — how to fake a clean room cheaply.** Not a substitute for Levels 1–3 on
first authorship, but good for re-verification after runbook edits:

1. Clone fresh into a new directory — never reuse your working copy:
   `git clone <REPO-URL> <FRESH-DIR>` .
2. If you must reuse a checkout, nuke everything untracked first:
   `git clean -xdf` (removes ignored + untracked files: node_modules, bin/obj,
   .venv, local caches). WARNING: destroys uncommitted untracked work — run
   `git clean -xdn` (dry run) first.
3. Point package caches somewhere empty so cached downloads can't mask a broken
   registry config: npm `npm_config_cache=<EMPTY-DIR>`, NuGet
   `NUGET_PACKAGES=<EMPTY-DIR>`, pip `PIP_CACHE_DIR=<EMPTY-DIR>` (all as
   environment variables for the session).
4. Run the runbook in a shell with a minimal PATH (only OS dirs plus the tools the
   runbook itself installs) to catch reliance on stray global installs.

What Level 4 does NOT catch: missing OS packages, globally installed tools your
runbook forgot (compilers, make, openssl headers), machine-wide env vars, certs.
Record which level you proved at, and the date, at the top of the runbook.

### 3. KNOWN TRAPS — a first-class section

Every instantiated build-and-env skill MUST contain a `## Known traps` section.
It is not an appendix; it is the highest-value part, because environment failures
are almost always a repeat of a known trap. Entry format — all four fields required:

```
### Trap: <short name>
- Symptom: <what the victim sees, verbatim error text if possible>
- Cause:   <the actual mechanism>
- Fix:     <copy-pasteable resolution>
- Tell:    <the fast discriminating check that confirms THIS trap and not a lookalike>
```

Seed categories every project should check for (generic instances; verify which
apply to yours before copying):

**Version conflicts.**
- Symptom: build works for one person, fails for another with syntax/API errors.
- Tell: compare `<TOOL> --version` on both machines against the pin file (§4).

**PATH shadowing.** Two installs of the same tool; the wrong one wins.
- Tell: list *all* resolutions, not just the first —
  Windows PowerShell: `Get-Command <TOOL> -All` or `where.exe <TOOL>`;
  POSIX: `which -a <TOOL>`. If two paths appear, you likely have this trap.
- Classic instances: system Python vs venv Python; Windows Store `python.exe`
  alias stub shadowing a real install (Symptom: `Python was not found; run without
  arguments to install from the Microsoft Store` — Fix: disable the alias under
  Settings > Apps > Advanced app settings > App execution aliases, or invoke via
  `py -3`); an old global tool shadowing the repo-local one.

**Platform differences (Windows / WSL / macOS / Linux).**
- Line endings: git `core.autocrlf` turning LF scripts into CRLF breaks shell
  scripts inside containers/WSL ("`/bin/bash^M: bad interpreter`"). Tell:
  `git config core.autocrlf`; Fix: enforce via `.gitattributes` (`* text=auto` plus
  `*.sh text eol=lf`).
- Case sensitivity: builds pass on Windows/macOS (case-insensitive FS), fail on
  Linux CI with "file not found" for a file that "exists". Tell: exact-case grep of
  the import vs `git ls-files`.
- Path separators and max-path: hardcoded `/` or `\` in scripts; Windows 260-char
  MAX_PATH failures deep in `node_modules` (Fix: enable long paths or shorten the
  clone path, e.g. clone to a drive root).
- WSL boundary: invoking Windows tools from WSL (or vice versa) mixes two
  toolchains and two file systems; keep the whole build on one side. Tell: paths
  like `/mnt/c/...` appearing in build output.

**Proxy / certificate issues.** Corporate TLS interception breaks every package
manager differently.
- Symptom: `SELF_SIGNED_CERT_IN_CHAIN`, `UNABLE_TO_VERIFY_LEAF_SIGNATURE`,
  pip `SSLError: certificate verify failed`, NuGet restore timeouts.
- Fixes by ecosystem (point at your corporate CA bundle, never disable
  verification): Node: set env var `NODE_EXTRA_CA_CERTS=<CA-BUNDLE.pem>` and
  `npm config set cafile <CA-BUNDLE.pem>`; pip:
  `pip config set global.cert <CA-BUNDLE.pem>`; git:
  `git config --global http.sslCAInfo <CA-BUNDLE.pem>`; most tools also honor
  `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` env vars.
- Tell: same command succeeds off-VPN / on a phone hotspot.

**Lockfile vs manifest drift.** The manifest (declared ranges: `package.json`,
`*.csproj`, `pyproject.toml`/`requirements.in`) and the lockfile (exact resolved
graph: `package-lock.json`, `packages.lock.json`, `uv.lock`/`poetry.lock`/compiled
`requirements.txt`) disagree.
- Symptom: fresh install resolves different versions than a teammate has; or
  `npm ci` aborts with a lockfile-out-of-sync error.
- Cause: someone edited the manifest without regenerating the lock, or ran an
  install command that silently rewrote the lock.
- Fix: regenerate the lockfile deliberately, review its diff, commit both files
  together.
- Tell: `npm ci` failing is itself the tell for npm; for NuGet, restore with
  `--locked-mode` and see if it errors; for pip-tools/uv, re-run the lock command
  and check `git diff` is empty.

### 4. Toolchain pinning discipline

Two layers must both be pinned; they answer different questions:

| Layer | Question it answers | Mechanism |
|---|---|---|
| Toolchain | "Which compiler/SDK/runtime builds this?" | Version-manager pin files (below) |
| Dependencies | "Exactly which package versions are used?" | Lockfiles, committed to the repo |

Real pin files (filenames verified as of 2026-07): `.nvmrc` (nvm, Node),
`global.json` (.NET SDK selection — generate with
`dotnet new globaljson --sdk-version <VERSION> --roll-forward latestFeature`),
`rust-toolchain.toml` (rustup), `.python-version` (pyenv), `.tool-versions` (asdf/mise),
`"packageManager"` field in `package.json` (Corepack pins the npm/yarn/pnpm version
itself), `.config/dotnet-tools.json` (dotnet local tool manifest — pins repo-local CLI
tools such as `dotnet-ef`; restore with `dotnet tool restore`; the EF-specific workflow
lives in `dotnet-ef-discipline`). If the repo has none, adding one is the first
improvement to propose.

Rules:
- The pin file, not tribal knowledge, is the source of truth for Block A of the
  runbook. CI must read the same pin file (e.g. setup actions that accept a
  version-file input) — a CI matrix hardcoding versions is drift waiting to happen.
- Lockfiles are always committed, including for applications AND internal tools.
  (Publishing a broad-range *library* is the one classic exception — judgment call.)
- Use the install command that *respects* the lock, not the one that *updates* it
  (table in §6). CI must use the respecting form.
- Upgrades are deliberate: change manifest → regenerate lock → review lock diff →
  clean-room build (Level 4 minimum) → commit both files in one commit.

### 5. How builds actually get invoked — CI is ground truth

Docs claim `make build`; CI runs three env exports, a codegen step, and *then*
`make build`. When they disagree, **CI wins, because CI is executed on a clean
machine dozens of times a day — the CI config IS the working from-scratch runbook,
minus prose.** (`skill-factory` covers CI mining as part of full-repo discovery;
this section is the build-specific extract.)

Mining procedure:
1. Find the CI config: `.github/workflows/*.yml`, `.gitlab-ci.yml`,
   `azure-pipelines.yml`, `Jenkinsfile`, `.circleci/config.yml`, or `<CI-CONFIG>`.
2. Extract, in order, for the build job: base image / runner OS → toolchain setup
   steps and the versions or version-files they reference → env vars set → every
   command in `run:`/`script:` blocks before the build → the build command itself →
   cache keys (they reveal which lockfiles matter).
3. Diff that sequence against the README/setup docs. Every step CI does that docs
   omit is either (a) a missing runbook step or (b) CI-only — decide which,
   explicitly, per step.
4. Also mine wrapper scripts CI calls (`./build.sh`, `Makefile`, `*.ps1`,
   `package.json` `"scripts"`) — the real invocation is often two layers down.
5. Record the result in the runbook as: "Canonical build invocation (source:
   `<CI-CONFIG>` line N): `<BUILD-CMD>`". Cite the line so the next auditor can
   re-diff cheaply.

### 6. Ecosystem quick tables (commands verified 2026-07 unless noted)

**Install: lock-respecting vs lock-updating.** Always know which one you are typing.

| Ecosystem | Respects lock (use in CI/runbooks) | May update lock (use only for deliberate upgrades) |
|---|---|---|
| npm | `npm ci` | `npm install` |
| .NET (with `packages.lock.json`) | `dotnet restore --locked-mode` | `dotnet restore` |
| Python (pip-tools) | `pip install -r requirements.txt` (compiled) | editing `requirements.in` + `pip-compile` |
| Python (uv) | `uv sync --frozen` (unverified here — re-check against uv docs) | `uv lock` |

**npm** (verified against npm 11):
- Toolchain check: `node --version`, `npm --version`; engine constraint:
  `npm pkg get engines`; package-manager pin: Corepack (`corepack --version`;
  bundled with Node ≤24, removed from the distribution on newer Node — install via
  `npm i -g corepack` there; re-check `corepack --version`).
- Clean install: `npm ci` (deletes `node_modules`, installs exactly the lockfile;
  errors if lock and manifest disagree — that error is a feature).
- Environment health: `npm doctor`; registry reachability: `npm ping`;
  effective registry: `npm config get registry`.

**.NET** (verified against SDK 10):
- Toolchain check: `dotnet --list-sdks` (all installed), `dotnet --version`
  (the one `global.json` selects — run it *in the repo*), `dotnet --info`.
- Lockfiles: opt in per project with MSBuild property
  `RestorePackagesWithLockFile=true` (generates `packages.lock.json`); then CI
  restores with `dotnet restore --locked-mode`.
- Cache inspection/reset: `dotnet nuget locals all --list`,
  `dotnet nuget locals all --clear`.

**Python** (commands are standard pip/venv syntax; not executable on the authoring
machine — re-verify on first use):
- Toolchain check: `python --version` (Windows: prefer `py -3 --version`);
  pin with `.python-version`.
- Isolate ALWAYS: `python -m venv .venv`, then activate
  (POSIX `source .venv/bin/activate`; PowerShell `.venv\Scripts\Activate.ps1`).
  A runbook step that pip-installs outside a venv is a defect.
- Consistency check after install: `pip check` (verifies installed packages have
  compatible dependencies); snapshot: `pip freeze`.

### 7. Dependency hygiene — required vs accreted

Dependencies accrete ("accreted" = added for a reason that no longer exists).
Audit cadence: at minimum whenever this skill is re-verified (see Provenance).

Procedure:
1. **List what's declared.** npm: `npm ls --depth=0` (top-level only, matching
   syntax `npm ls --all` for the full tree); .NET: `dotnet list package`
   (add `--include-transitive` for the full graph); Python: `pip freeze` vs the
   manifest.
2. **Find unused declarations.** npm: `npx depcheck` (third-party tool — inspect
   before trusting; static analysis, so verify hits manually: config-file-loaded
   plugins are false positives). .NET/Python: no single standard tool — grep for
   `using`/namespace usage per package, or remove-and-build in a branch.
3. **Find risk.** npm: `npm audit`, `npm outdated`; .NET:
   `dotnet list package --vulnerable`, `--deprecated`, `--outdated` (mutually
   exclusive flags — run separately).
4. **For each candidate removal:** delete from manifest → regenerate lock →
   `<BUILD-CMD>` + `<TEST-CMD>` on a Level-4 clean room → commit with the reason.
   Never batch removals you haven't individually verified.
5. **Record intent.** For every non-obvious dependency, one line in the
   instantiated skill: package → why it exists → what breaks without it. Unknown
   purpose = investigation ticket, not silent tolerance.

## Worked example

**Illustrative example — all project facts fictional.** Project "Quartzline", a
.NET 8 web API with a Node-based asset pipeline.

CI mining (§5): `.github/workflows/build.yml` showed the build job runs
`npm ci && npm run assets` *before* `dotnet build -c Release`, and sets
`QL_CODEGEN=1`. The README only said "run `dotnet build`" — two missing steps and
one missing env var found without touching a compiler.

Runbook produced (abridged):

| Prerequisite | Version | Check | Expect |
|---|---|---|---|
| .NET SDK | per `global.json` (8.0.4xx) | `dotnet --version` (in repo) | `8.0.4xx` |
| Node | per `.nvmrc` (22.x) | `node --version` | `v22.*` |
| Registry access | Artifactory token | `npm ping` | `PONG` / no ENOTFOUND |

```
Step 1: Clone.
    Command:  git clone <REPO-URL> quartzline && cd quartzline
    Verify:   git status
    Expect:   "working tree clean" on branch <MAIN-BRANCH>
Step 2: Install JS deps.
    Command:  npm ci
    Verify:   echo $? (POSIX) / $LASTEXITCODE (PowerShell)
    Expect:   0; node_modules/ exists
Step 3: Build assets.
    Command:  npm run assets
    Verify:   test presence of wwwroot/dist/app.css
    Expect:   file exists, non-empty
Step 4: Build API.
    Command:  QL_CODEGEN=1 dotnet build -c Release   (PowerShell: $env:QL_CODEGEN='1'; dotnet build -c Release)
    Verify:   exit code
    Expect:   0, "Build succeeded"
Final acceptance: dotnet test → "Passed! - 212 tests". 
Total expected time: ~14 min fresh (9 min downloads). Proven: Level 2,
mcr.microsoft.com/dotnet/sdk:8.0 + Node install step, 2026-07-06.
```

Clean-room run caught one defect: inside the container, Step 3 failed with
`/bin/sh: 1: sass: not found` — the author had a global sass masking a missing
devDependency. Trap entry written:

```
### Trap: global sass masked missing devDependency
- Symptom: `npm run assets` fails with "sass: not found" on fresh machines only
- Cause: sass was globally installed on the original dev machine, never declared
- Fix: declared in devDependencies; lockfile regenerated and committed
- Tell: `npm ls sass` says "(empty)" while `which -a sass` / `Get-Command sass -All` finds a global one
```

## Instantiate for your project

Produce `.claude/skills/<PROJECT>-build-and-env/SKILL.md`. Steps (a Sonnet-class
model can execute these unaided):

1. **Mine the ground truth** (evidence gathering — do not write runbook prose yet):
   - Pin files: check for `.nvmrc`, `global.json`, `rust-toolchain.toml`,
     `.python-version`, `.tool-versions`, `package.json` `"packageManager"` field.
   - Lockfiles: `git ls-files` and look for `package-lock.json`, `yarn.lock`,
     `pnpm-lock.yaml`, `packages.lock.json`, `uv.lock`, `poetry.lock`,
     `requirements*.txt`, `Cargo.lock`.
   - CI config per §5 step 1; extract the build job command sequence per §5 step 2.
   - Setup docs: `README*`, `CONTRIBUTING*`, `docs/` — these are *claims* to be
     diffed against CI, not sources of truth.
   - History of pain: `git log --oneline -- <CI-CONFIG> Dockerfile* *.lock` plus
     `git log --grep="build" --grep="setup" --grep="env" -i --oneline` — commits
     that fixed environment breakage are trap entries waiting to be written
     (see `failure-archaeology` for deep mining).
2. **Write Block A** from pin files + CI toolchain-setup steps only. Evidence rule:
   every version cell must cite a file (pin file or CI line), not an installed
   version on your machine.
3. **Write Blocks B–C** by replaying the CI sequence locally, converting each CI
   step into Step/Command/Verify/Expect form. Evidence rule: you may only write a
   step you have executed and whose Verify output you have seen.
4. **Run the clean-room proof** at the highest level available (§2 table); record
   level + date + measured time (Block D). Every failure during the proof becomes
   either a runbook fix or a Known Traps entry — never a private workaround.
5. **Write Known Traps** using the four-field format (§3). Evidence rule: do not
   write a trap you have not either reproduced yourself or sourced from a specific
   commit/issue/CI failure (cite it: hash or issue number in the entry).
6. **Run the dependency-hygiene audit** (§7) once; record the package→purpose table
   and any open investigation tickets.
7. **Fill this skeleton** (delete unused ecosystem parts):

```markdown
---
name: <PROJECT>-build-and-env
description: From-scratch environment setup, build invocation, and known
  environment traps for <PROJECT>.
---
# <PROJECT> — Build & Environment
## Runbook status
Proven at clean-room Level <N> on <DATE>; measured time <X> min.
## Prerequisites            <!-- Block A table -->
## Setup steps              <!-- Block B: Step/Command/Verify/Expect -->
## Acceptance               <!-- Block C: <BUILD-CMD>, <TEST-CMD>, expected outputs -->
## Canonical build invocation
Source: <CI-CONFIG> line <N>. Command: <BUILD-CMD>. Divergences from README: <LIST>.
## Toolchain pins           <!-- file → what it pins → CI step that reads it -->
## Known traps              <!-- four-field entries; each cites a repro or commit/issue -->
## Dependency intent        <!-- package → why → what breaks without it -->
## Provenance               <!-- who proved it, when, at what clean-room level -->
```

8. **Re-verification triggers** (write these into the instantiated copy): any edit
   to CI config, pin files, lockfiles, or Dockerfiles ⇒ re-run at least a Level-4
   clean room; quarterly ⇒ re-run the full proof at the original level.

## Provenance and maintenance

- Authored 2026-07-06 against no specific project; all project-flavored content is
  labeled illustrative.
- Verified by execution on the authoring machine (Windows 11): `npm ci`,
  `npm pkg get engines`, `npm doctor`, `npm ls`, `corepack --version` (npm 11 /
  Node 24); `dotnet --list-sdks`, `dotnet restore --locked-mode` (flag confirmed in
  help), `dotnet nuget locals` argument set, `dotnet new globaljson --sdk-version
  --roll-forward`, `dotnet list package --vulnerable/--deprecated/--outdated`
  (SDK 10); `git --version` 2.52.
- NOT executed here (standard syntax, re-verify on first use): all Python commands
  (`python -m venv`, `pip check`, `pip config set global.cert`, pip-tools, uv —
  uv flags explicitly marked unverified above); Docker recipes (`docker run`, image
  tags); `npx depcheck` (third-party).
- Volatile parts and one-line re-checks: install-command table §6
  (`npm help ci`, `dotnet restore --help`, `pip --help`); pin-file conventions §4
  (check current nvm/rustup/pyenv/asdf docs); CI config filenames §5 (check the CI
  vendor docs); vulnerability-audit flags §7 (`dotnet list package --help`,
  `npm audit --help`).
- Instantiated copies must add their own provenance block: prover, date,
  clean-room level, measured setup time, and the CI-config line cited for the
  canonical build command.
