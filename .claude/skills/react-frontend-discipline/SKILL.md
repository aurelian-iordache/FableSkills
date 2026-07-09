---
name: react-frontend-discipline
description: STACK TIER. Load when working on a React + TypeScript front end — deciding where a piece of state lives ("should this be useState / context / Redux?"), writing or reviewing a useEffect, adding fetch/data-loading code, sprinkling useMemo/useCallback/React.memo, writing component tests, typing an API client against a C#/.NET backend, or standing up a new front-end project. Delivers the state-ownership decision table (server state is not client state), the effect trap catalog, measured-not-guessed memoization rules, React Testing Library + MSW doctrine, OpenAPI-generated boundary types with runtime validation, and a version-stamped tooling baseline.
---

# react-frontend-discipline — React + TypeScript Front-End Discipline

STACK TIER skill: unlike the project-agnostic siblings, this file states facts about the
React/TypeScript ecosystem as ground truth — each one version-stamped and, where volatile,
paired with a re-verification command. Ecosystem facts were verified 2026-07-06 against the
live npm registry and a scaffolded Vite React-TS project (see §6 for exactly what was run).
Project-specific facts remain `<PLACEHOLDERS>`.

## 1. Purpose

This skill makes you able to (a) decide mechanically where any piece of state belongs,
(b) recognize and fix the classic `useEffect` misuses that cause most React staleness and
double-render bugs, (c) apply rendering optimizations only when a profiler shows a problem,
(d) test components by user-visible behavior, and (e) keep the TypeScript boundary to a
C#/.NET backend generated and runtime-validated instead of hand-maintained and lying.

## 2. When to use / When NOT to use

**Use when:** adding or reviewing React components, hooks, or data fetching; choosing a
state-management approach; a component re-renders "too much"; a list reorders and its inputs
scramble; writing front-end tests; wiring the front end to an ASP.NET Core API; starting a
new React project.

| If instead you need... | Use sibling skill |
|---|---|
| What counts as proof a change works; test-taxonomy placement; snapshot/golden rules | validation-and-qa |
| Measurement discipline, baselines, "is it actually slower?" | diagnostics-and-tooling |
| Statistical rigor for a performance claim | proof-and-analysis |
| Feature flags / environment config catalog (front-end `.env` included) | config-and-flags |
| Toolchain pinning, from-scratch environment recreation | build-and-env |
| The C#/.NET data layer behind the API (EF Core, migrations) | dotnet-ef-discipline |
| The server side of the wire contract: DTO wire shapes, System.Text.Json behavior (casing/dates/enums/nulls), ProblemDetails error contract, OpenAPI document generation/drift, API versioning | aspnet-api-discipline |
| C# craft on the backend itself (implementation idioms, service design, mapping style) | csharp-code-discipline |
| Gating a risky change (e.g., swapping state libraries, regenerating the API client) | change-control |
| Root-causing a live front-end bug | debugging-playbook |

## 3. Core doctrine

### 3.1 State ownership: the decision table

Definition — **state**: any value that changes over time and drives what renders.
Run every new piece of state through this table **in order**; stop at the first row that
matches. (Verified against React 19.2 semantics, 2026-07-06.)

| # | Question | If yes → owner | Notes |
|---|---|---|---|
| 0 | Does the value originate on the **server** (fetched over HTTP; the backend or another user could change it)? | A fetch-cache library (TanStack Query or equivalent) — see §3.2. **Never** `useState`/a store as the system of record. | This row outranks all others. Most React staleness bugs are server state miscategorized as client state. |
| 1 | Can it be **computed** from existing props/state? | Nobody — derive it during render (`const fullName = first + ' ' + last`). Not state at all. | Storing derived values creates two sources of truth that drift. `useMemo` only if the computation is measured-expensive (§3.4). |
| 2 | Should it survive **refresh / back button / link sharing** (filters, page number, selected tab, search text)? | The **URL** — router search params or path. | `useState` here breaks the back button and makes bug reports unreproducible ("send me the link" stops working). |
| 3 | Is it a **form** with more than ~2 fields or any validation? | A form library (`react-hook-form` 7.x, verified 2026-07-06) with a schema (§3.6). | Per-field `useState` + hand-rolled validation is the high-churn path. (~2 fields is a heuristic threshold.) |
| 4 | Used by **one component** only? | `useState` (or `useReducer` for multi-field transitions) in that component. | The default. Do not reach past this row without a concrete reason. |
| 5 | Used by **siblings / a small subtree**? | Lift to the **nearest common parent**; pass down via props. | "Prop drilling" through 2–3 levels is fine and grep-able. It is not a problem to engineer around until it demonstrably hurts. |
| 6 | Needed **subtree-wide**, changes **rarely** (theme, locale, authenticated-user identity, feature flags)? | React **context**. | Every consumer re-renders on every context value change — context is for low-frequency data. High-frequency data in context is a measured-performance bug factory (§3.4). |
| 7 | Needed **app-wide**, changes **often**, and rows 0–6 demonstrably failed (written evidence: profiler capture or a concrete drilling-depth problem)? | External store (e.g., `zustand`, `redux`/RTK). | Adopting a store is an architecture decision: record the evidence and the WHY per architecture-contract, gate per change-control, and run proof-and-analysis' prove-it-before-adopting checklist first (its Recipe 6). "We might need it later" is not evidence. |

Failure mode of the table itself: applying rows top-down to state that already exists
without checking row 0 first. When refactoring, re-ask row 0 for every field in every
existing store — server data hiding in a client store is the usual find.

### 3.2 Server state is not client state

Definition — **server state**: data whose source of truth is the backend (entities, lists,
lookups). Properties: it can be stale the moment you receive it, others can mutate it, and
it needs caching, deduplication, refetching, and retry — none of which `useState` provides.

Rules (library facts verified against `@tanstack/react-query` 5.x, 2026-07-06):

1. **The fetch-cache library owns server data.** Components read it with `useQuery`; the
   cache key (e.g., `['orders', orderId]`) is the identity. There is no `setOrders` anywhere.
2. **Copying query results into `useState` is the root staleness bug.** Symptom: data on
   screen doesn't update after a mutation or refetch elsewhere. Cause: the copy froze a
   snapshot. Fix: delete the copy; read from the query. The **one legitimate copy** is an
   explicit *edit draft* (form initial values from server data) — and then the reconciliation
   rule must be stated: on save, mutate then invalidate the query
   (`queryClient.invalidateQueries({ queryKey: ['orders', orderId] })`); the draft is
   discarded, never written back into the cache by hand-merge.
3. **Mutations invalidate, they do not hand-patch state.** After `useMutation` succeeds,
   invalidate the affected keys and let refetch restore truth. Optimistic updates are an
   opt-in advanced pattern — only with rollback (`onError` restoring the previous cache
   snapshot), and only where measured latency justifies it.
4. **Loading/error states come from the query object** (`isPending`, `isError`), not from
   parallel `useState<boolean>` flags you set around a `fetch` call.
5. Lint support exists: `@tanstack/eslint-plugin-query` (5.x, verified 2026-07-06) catches
   malformed keys and common misuse — wire it in if you adopt the library.

### 3.3 Effect discipline

Doctrine — **effects synchronize React with external systems** (subscriptions, DOM APIs the
framework doesn't own, analytics, non-React widgets). They are NOT for deriving state and
NOT for responding to user events. Before writing `useEffect`, answer: *which external
system is this synchronizing with?* No answer → you don't need an effect. (This is the
official React position — react.dev, "You Might Not Need an Effect" — and verified behavior
on React 19.2.)

Trap catalog — Symptom / Cause / Fix / Tell:

| Trap | Symptom | Cause | Fix | Tell (grep-able) |
|---|---|---|---|---|
| **Derived state in an effect** | UI shows a value one render stale; components render twice per change | `useEffect` watches `a`, calls `setB(f(a))` — a second render pass per update | Compute during render; `useMemo` only if measured-expensive | `useEffect` whose body is only `setX(...)` with deps it reads |
| **Fetch-in-effect race** | Fast navigation between items shows the *previous* item's data; intermittent, worse on slow networks | Two in-flight requests; the older one resolves last and its `setData` wins (stale closure) | Preferred: move to the fetch-cache library (§3.2). If a raw effect is truly required: create `AbortController` in the effect, pass `signal` to `fetch`, `abort()` in cleanup, and ignore `AbortError` | `fetch(` inside `useEffect` with no `AbortController`/ignore flag |
| **Dependency lies** | Handler/effect uses stale values; "works after I click twice" | `// eslint-disable-next-line react-hooks/exhaustive-deps` to silence the linter instead of restructuring | Restructure: move the function inside the effect, wrap in `useCallback`, split the effect, or lift the value out. The dep array is not a re-run scheduler — it is the list of values the effect reads | grep `exhaustive-deps` — every hit is a suspect |
| **setState-in-render / effect chains** | Console: `Maximum update depth exceeded`; or a cascade of N renders per change | Calling a state setter unconditionally during render, or chained effects each setting state the next effect watches | Setter calls belong in handlers/effects with conditions; collapse effect chains into a single event handler or derived values | multiple effects in one file whose deps are each other's set targets |
| **StrictMode "double-run bug"** | Dev-only: effects run twice on mount, components render twice; a junior "fixes" it with a `useRef` did-run guard or by deleting `<StrictMode>` | React StrictMode intentionally double-invokes render and runs mount→cleanup→mount in development (React 18+ documented behavior — react.dev) to expose missing cleanup | Neither guard nor removal. Make the effect idempotent with a correct cleanup function; the double-run then becomes invisible. If double-run breaks something, that something was already broken for real remounts | `useRef(false)` named `didRun`/`mounted` guarding an effect |
| **Event logic in an effect** | Action fires at odd times (on mount, on unrelated re-render), or a boolean "trigger" state exists | A handler sets `setSubmitted(true)`; an effect watches `submitted` and does the work | Do the work in the event handler. State that exists only to trigger an effect is a code smell | boolean state whose only reader is an effect dep array |

### 3.4 Rendering performance, measured

What actually causes a component to re-render (React 19.2 semantics, verified 2026-07-06):
its own state changed, a context it consumes changed, or **its parent re-rendered** — by
default children re-render with the parent *regardless of whether their props changed*.
Props identity (`{}`, `[]`, arrow functions recreated per render) only matters once a
component is wrapped in `React.memo` — unstable props then silently defeat the memo.

Rules:

1. **No speculative memoization** (memoization: caching a computation, or skipping a
   re-render, while its inputs are unchanged). `React.memo` / `useMemo` / `useCallback` are applied only
   after the React DevTools Profiler (browser extension; record → interact → read flame
   chart with "why did this render") shows a specific component re-rendering measurably
   too often or too expensively. "This list looks like it might be slow" is eyeballing —
   banned per diagnostics-and-tooling. Capture the profiler evidence in the PR.
2. **Fix the cause before memoizing.** Cheaper structural fixes, in order: move the state
   down (into the component that uses it, so the parent stops re-rendering); pass expensive
   subtrees as `children` (a parent re-render does not re-render element props it received
   already-created); split a high-churn context value from a low-churn one. Memoization is
   the last resort because every memo adds an invariant (all props stable) that future edits
   silently break.
3. **React Compiler caveat (volatile).** React 19-era tooling includes an optimizing
   compiler that auto-memoizes; whether it is enabled changes whether manual memo is ever
   warranted. Check the project's build config before adding manual memoization; re-verify
   ecosystem status with `npm view babel-plugin-react-compiler version`.
4. **Keys discipline.** `key` tells React which list item is *the same item* across renders.
   `key={index}` on a list that can reorder, insert, filter, or delete corrupts item-bound
   state. Concrete symptom: a list of rows each containing a text input — delete row 2, and
   row 3's typed text now appears inside row 2; or after a sort, checkboxes stay put while
   labels move. Fix: key by stable identity (`item.id` from the backend). Index keys are
   acceptable only for append-only, never-reordered, stateless rows — and even then an id
   is safer against future edits.
5. **Bundle size is measured, not guessed.** `npm run build` in a Vite project prints
   per-asset raw and gzip sizes (verified: fresh react-ts scaffold builds to a 193.35 kB /
   60.67 kB gzip JS bundle, 2026-07-06). Record that as a baseline per
   diagnostics-and-tooling; investigate jumps with `rollup-plugin-visualizer` (7.x,
   verified 2026-07-06) before adding dependencies. A numeric budget gate in CI is
   candidate practice; the baseline-and-compare habit is the non-negotiable part.

### 3.5 Testing doctrine

Stack facts verified 2026-07-06: `vitest` 4.x is the de-facto standard runner for Vite
projects (not bundled by the scaffold — you add it); `@testing-library/react` (RTL —
React Testing Library) 16.x, `@testing-library/user-event` 14.x, `msw` (MSW — Mock
Service Worker) 2.x. A vitest + jsdom (a simulated browser DOM for Node test runs) +
RTL + user-event test was executed green in the scaffold (§6).

1. **Test what the user sees and does.** Assert on rendered text, roles, and states — never
   on component internals, hook state, or "the setter was called".
2. **Query priority:** `getByRole` (with accessible name) > `getByLabelText` >
   `getByPlaceholderText`/`getByText` > `getByTestId` as last resort. If you cannot find an
   element by role or label, that is an accessibility finding, not a reason for a test-id.
3. **`userEvent` over `fireEvent`.** `await userEvent.setup().click(button)` dispatches the
   full browser-like event sequence (pointer, focus, keyboard); `fireEvent.click` fires one
   synthetic event and misses focus/keyboard behavior. `fireEvent` is for the rare raw-event
   edge case only.
4. **Async by `findBy*` / `waitFor`, never sleeps.** `await screen.findByRole('heading', ...)`
   polls until appearance or timeout. Arbitrary `setTimeout` waits are the flaky-test seed
   validation-and-qa §3.6 quarantines.
5. **Mock at the network boundary with MSW.** MSW intercepts requests at the
   fetch/XHR level, so components, the fetch-cache library, and serialization all run for
   real; only the wire is fake. Mocking `fetch`/`axios` internals or the query hooks
   themselves tests your mocks, not your code — and breaks on every refactor.
6. **Placement** (cross-ref validation-and-qa §3.5 — lowest layer that exercises the failure
   mechanism): pure logic → plain vitest unit tests, no DOM; component behavior (render,
   interact, assert, MSW-backed) → vitest + jsdom component tests, the workhorse layer;
   full-browser flows (routing, real auth, visual layout, file download) → few E2E tests
   (Playwright et al.). Do not push to E2E what a component test can catch.
7. **Snapshot tests are low-rent** per validation-and-qa §3.4: they fail on any markup
   change, so "update snapshot" becomes reflexive and the test certifies nothing. Prefer
   targeted assertions. If a snapshot exists, it follows the golden re-certification rule —
   the diff is reviewed as a behavior change, never regenerated to green.

### 3.6 TypeScript at the API boundary (the .NET-shop section)

Principle: **the backend contract is the source of truth.** An ASP.NET Core backend exposes
an OpenAPI document (built-in `Microsoft.AspNetCore.OpenApi` or Swashbuckle — server-side
OpenAPI setup, build-time document generation, and the server-side CI drift gate are owned
by `aspnet-api-discipline` §6; this rule's client-side drift check pairs with that skill's
§6.3 gate); the front end
*generates* its types and client from that document. Hand-maintained parallel DTO interfaces are a standing lie: they
compile forever and drift silently.

Generator options (all package existence and versions verified via `npm view` 2026-07-06;
the *choice* among them is volatile — re-verify before adopting, and run
proof-and-analysis' prove-it-before-adopting checklist (Recipe 6) on the one you pick):

| Package | Version (2026-07-06) | What it generates | Notes |
|---|---|---|---|
| `openapi-typescript` | 7.x | Types only, from an OpenAPI URL/file | Minimal, fast; pairs with `openapi-fetch` (0.17.x) for a typed client. Good default when you want thin dependencies. |
| `nswag` (npm) / NSwag toolchain | 14.x | Full TS client + DTO classes | The C#-shop native: same tool can run from MSBuild on the backend, keeping generation next to the contract owner. |
| `orval` | 8.x | Typed client **plus TanStack Query hooks plus optional zod schemas** | Most batteries-included; couples you to its output shapes. |
| `@hey-api/openapi-ts` | 0.x (pre-1.0 — extra-volatile) | Types + client, plugin ecosystem | Successor lineage of older axios-client generators. |
| `swagger-typescript-api` | 13.x | Types + fetch/axios client | Long-lived alternative. |

Rules:

1. **Generation is wired, not manual.** A script (`"generate:api": "openapi-typescript
   <OPENAPI-URL> -o src/api/schema.d.ts"` or the project's equivalent) plus a CI drift
   check: regenerate and `git diff --exit-code` — a dirty diff means the backend contract
   changed and the front end hasn't caught up. Regenerating the client after a contract
   change is a gated, reviewed change (change-control): the diff *is* the impact analysis.
2. **Runtime validation at the boundary.** TypeScript types are erased at runtime — a
   generated type asserts nothing about what the server actually sent (wrong environment,
   old API version, proxy error page as JSON). Validate responses you act on with `zod`
   (4.x, verified 2026-07-06) or equivalent at the API-client layer: parse once at the
   edge, trust types everywhere inside. Depth is a judgment call — heuristic: validate
   money, dates, discriminated unions, and anything feeding writes; skip display-only
   strings if the noise outweighs the risk.
3. **Dates across the boundary.** JSON has no date type; everything is an ISO 8601 string.
   The traps (stated carefully — JS side verified against ECMA-262 parsing rules,
   2026-07-06; the .NET serialization side is verified on the wire in
   `aspnet-api-discipline` §3.3, ASP.NET Core 10.0.9, 2026-07-08):
   - C# `DateTimeOffset` serializes with an explicit offset (`2026-07-06T10:00:00+02:00`)
     and is unambiguous — prefer it on the wire (a backend-contract decision owned by
     `aspnet-api-discipline` §3.3, whose rule is `DateTimeOffset` on every DTO for
     moments in time — raise it with the backend owners).
     C# `DateTime` is ambiguous by Kind: `Kind=Utc` → `Z` suffix; `Kind=Local` → the
     **server machine's** offset (the contract changes with the deploy region);
     `Kind=Unspecified` → a bare string with no offset at all, which `new Date()` parses
     as the *client's* local time. Verified wire table: `aspnet-api-discipline` §3.3.
   - JavaScript `new Date(s)` parses a string **with** `Z`/offset as that exact instant;
     a date-**time** string **without** offset as *local* time; a date-**only** string
     (`"2026-07-06"`) as *UTC midnight*. Consequence: a C# `DateOnly` ("2026-07-06")
     naively `new Date()`-ed displays as **the previous day** for every user west of UTC.
   - Discipline: keep boundary values as ISO strings in state and caches; convert to `Date`
     (or a date library) only at the display/input edge; format with `Intl.DateTimeFormat`;
     zod's `z.iso.datetime()` / string checks can enforce shape at parse time (zod 4 API —
     verify against installed version's docs).

### 3.7 Tooling baseline — as of 2026-07-06, ALL VOLATILE

Every row: re-verify with `npm view <PKG> version` before relying on a major version.

| Concern | Baseline (verified 2026-07-06) | Notes |
|---|---|---|
| Build/dev | **Vite** 8.x (`npm create vite@latest <APP> -- --template react-ts`) | Scaffold executed and built green today. create-react-app: sunset by its maintainers for new apps (React blog, Feb 2025); npm package still published (5.1.0, not npm-`deprecated`, last modified 2025-05) — do not start new projects on it. |
| Runtime | React / ReactDOM 19.2.x, TypeScript 6.0.x | |
| Test runner | **vitest** 4.x + `jsdom` + Testing Library | Executed green today. Not bundled by the scaffold — you add it (§6 lists the exact packages). |
| Lint | Rules-of-hooks + exhaustive-deps enforcement is **non-negotiable** | Two routes: ESLint 10.x + `eslint-plugin-react-hooks` 7.x, or **oxlint** (the current create-vite react-ts template ships `"lint": "oxlint"` — verified in the scaffold). Observed fact (scaffold of 2026-07-06, re-checked on oxlint 1.72.0): the generated `.oxlintrc.json` enables `react/rules-of-hooks` as `error` but does NOT configure exhaustive-deps; oxlint reports missing deps only as a default *warning*, and a plain `oxlint` run exits 0 on warnings — so nothing fails the build. Fix: add `"react/exhaustive-deps": "error"` to the config's `rules` (verified: a missing dep then exits 1), or run ESLint + `eslint-plugin-react-hooks` in CI as well. Re-verify: `cat .oxlintrc.json`, then lint a file with a deliberately missing effect dep and check the exit code. |
| Server state | `@tanstack/react-query` 5.x | Adoption per §3.1 row 0. |
| Forms/validation | `react-hook-form` 7.x + `zod` 4.x | zod 4 changed APIs vs the long-lived zod 3 — check which major the project pins before copying snippets. |
| Network mocks | `msw` 2.x | |
| API types | Table in §3.6 | |
| Bundle analysis | `npm run build` gzip readout; `rollup-plugin-visualizer` 7.x | |

## 4. Worked example (illustrative — all project facts fictional)

Project **Larkspur**, a fictional parcel-tracking dashboard (ASP.NET Core backend). A PR
adds a "shipments" screen; review through this skill:

1. The PR fetches shipments in a `useEffect` into `const [shipments, setShipments] =
   useState<Shipment[]>([])`, with `isLoading` state alongside. §3.1 row 0 + §3.3 trap 2:
   server state in `useState`, fetch-in-effect with no abort. Rewritten as
   `useQuery({ queryKey: ['shipments', filters], queryFn: ... })`; both `useState`s and the
   effect are deleted (−31 lines).
2. The filter panel state (`carrier`, `status`, page) is `useState` in the page component.
   §3.1 row 2: filters should survive refresh and be shareable — moved to URL search params.
   A tester's bug report can now include the exact link.
3. `Shipment` was a hand-written interface; the backend had renamed `eta` →
   `estimatedArrival` and the field was silently `undefined`. §3.6 rule 1: types regenerated
   via `npm run generate:api` (openapi-typescript against `/openapi/v1.json`); the compile
   error surfaces the rename. A zod schema on the response now rejects the payload loudly
   in staging when the contract drifts.
4. `estimatedArrival` is a C# `DateOnly` → `"2026-07-11"`. The UI showed July 10 for a
   Seattle user (§3.6 rule 3, date-only-parses-as-UTC). Fixed by formatting the ISO string
   directly (`Intl.DateTimeFormat` with `timeZone: 'UTC'` for the date-only case).
5. The author wrapped every row in `React.memo` "for performance". §3.4 rule 1: no profiler
   evidence — removed. Profiler capture attached to the PR shows the table renders in 4 ms;
   nothing to fix. The rows *were* keyed by `key={index}` on a sortable table — that, not
   memo, was the real hazard (§3.4 rule 4); rekeyed to `shipment.id`.
6. Tests: one component test — MSW handler returns two shipments, `await
   screen.findByRole('row', { name: /LRK-1042/i })`, then `userEvent` drives the status
   filter and asserts the row count. Placed at the component layer; the E2E suite gets
   nothing (no full-browser mechanism involved). Evidence grade 2 per validation-and-qa.

## 5. Instantiate for your project

Produce `<PROJECT>-frontend-discipline` in the target repo. Executable by a Sonnet-class
model unaided; every blank requires the listed evidence.

0. **Locate the front end(s).** `git ls-files "*package.json"` — ignore `node_modules`
   paths. One React app → set `<FRONTEND-DIR>` and run every later command from there
   (in a C#/.NET repo the front end rarely sits at repo root — expect `ClientApp/`,
   `src/Web/client/`, or an npm workspace). Multiple apps / npm workspaces → instantiate
   one "Stack of record" + "State ownership map" block per app; the lockfile may live at
   the workspace root — take versions from the root lockfile, scripts from each app's
   `package.json`.
1. **Mine the manifest.** Read `package.json` (and lockfile for exact versions):
   - Build tool: `vite`? CRA remnant (`react-scripts`)? Next.js? Record version and scripts.
   - `npm ls react react-dom typescript --depth=0` — pinned versions.
   - Grep deps for state libraries: `@tanstack/react-query`, `swr`, `redux`, `@reduxjs/toolkit`,
     `zustand`, `mobx`, `jotai`, `recoil`. Each found = a decision already made; document it
     as the incumbent in the state table (row 0 / row 7 owners), do not relitigate without
     change-control.
   - Forms/validation: `react-hook-form`, `formik`, `zod`, `yup`. Test stack: `vitest` or
     `jest`, `@testing-library/*`, `msw`, `cypress`/`playwright`.
2. **Find the API-client setup.**
   `git grep -n -E "openapi|swagger|nswag|orval|hey-api" -- '*.json' '*.ts' '*.config.*'`
   plus a scripts scan of `package.json`. Outcomes: (a) generator found → record the
   command, the OpenAPI source URL, and whether CI checks drift; (b) hand-written DTO
   interfaces found (grep `interface .*Dto|type .*Response`) → list them as the top
   migration risk with file paths; (c) nothing → the instantiated skill's first
   recommendation is §3.6 rule 1, sized per change-control. If the backend serves no
   OpenAPI document at all, record that as the blocking prerequisite (server-side work —
   route to `aspnet-api-discipline` §6.2/§6.3, which owns standing the document up and
   gating it in CI) rather than recommending a generator that has nothing to read.
3. **Audit effects and suppressions.** Run and record counts:
   `git grep -c "useEffect" -- <SRC-DIR>`,
   `git grep -n "exhaustive-deps" -- <SRC-DIR>` (every hit is a §3.3 trap-3 suspect — list
   them), `git grep -n "fetch(" -- <SRC-DIR> | grep -v <API-CLIENT-DIR>` (raw fetches
   outside the client layer). Do not write a trap row you have not confirmed in the code.
4. **Capture the test reality.** Run `<TEST-CMD>` once; record runtime, count, and the
   querying style actually used (`git grep -c "getByTestId"` vs `"getByRole"` is an honest
   baseline of RTL discipline). Note snapshot count (`git ls-files "*.snap" | wc -l`) and
   route them into the validation-and-qa golden inventory.
5. **Take a bundle baseline.** `npm run build`; record the gzip sizes into
   `<PROJECT>/diag/baselines/` per diagnostics-and-tooling, with commit and date.
6. **Fill the skeleton:**

   ```markdown
   ---
   name: <PROJECT>-frontend-discipline
   description: <triggers naming this project's screens, state libs, and API client>
   ---
   # <PROJECT> Front-End Discipline
   ## Stack of record            <!-- exact versions from lockfile; date verified -->
   ## State ownership map        <!-- table §3.1 with the incumbents filled in: what owns server state, URL state, forms, and any store WITH its recorded justification -->
   ## API boundary               <!-- generator command, OpenAPI source, drift check, zod coverage; or the migration plan if hand-written DTOs -->
   ## Effect watchlist           <!-- file:line of every exhaustive-deps suppression and raw fetch-in-effect found in step 3 -->
   ## Test conventions           <!-- real <TEST-CMD>, MSW setup location, placement rules, snapshot policy -->
   ## Bundle baseline            <!-- link to baseline file; current sizes; visualizer command -->
   ## Provenance                 <!-- date, commit, commands run, versions -->
   ```

7. **Evidence bar:** no version not read from the lockfile; no command not run in this repo
   with output captured; no watchlist entry without file:line; no "we use X" claim sourced
   from a README instead of the manifest.

## 6. Provenance and maintenance

Authored 2026-07-06 against no specific project. Verification performed on Windows 11,
npm against the public registry, same date:

- **Versions via `npm view <PKG> version`** (2026-07-06): react 19.2.7, react-dom 19.2.7,
  typescript 6.0.3, vite 8.1.3, create-vite 9.1.1, vitest 4.1.10, @testing-library/react
  16.3.2, @testing-library/user-event 14.6.1, @tanstack/react-query 5.101.2,
  @tanstack/eslint-plugin-query 5.101.2, react-hook-form 7.81.0, zod 4.4.3,
  eslint-plugin-react-hooks 7.1.1, eslint 10.6.0, typescript-eslint 8.63.0 (re-checked
  2026-07-07; was 8.62.1 the day before — this list drifts daily), msw 2.14.6,
  openapi-typescript 7.13.0, openapi-fetch 0.17.0, nswag 14.7.1, orval 8.20.0,
  @hey-api/openapi-ts 0.99.0, swagger-typescript-api 13.12.4, @vitejs/plugin-react 6.0.3,
  rollup-plugin-visualizer 7.0.1, oxlint 1.71.x (from scaffold).
- **Executed in a scratch scaffold** (2026-07-06): `npm create vite@latest <APP> --
  --template react-ts --no-interactive` → `npm install` → `npm run build` (green, gzip
  sizes printed) → added vitest/jsdom/Testing Library → one RTL + userEvent component test
  via `npx vitest run` (1 passed). The scaffold's lint script is oxlint, not ESLint.
  Re-checked 2026-07-07 in the same scaffold (oxlint 1.72.0): generated `.oxlintrc.json`
  has `react/rules-of-hooks: error` and no exhaustive-deps entry; a component with a
  deliberately missing effect dep produced only a default `react-hooks(exhaustive-deps)`
  *warning* and exit 0; after adding `"react/exhaustive-deps": "error"` to the config's
  `rules`, the same lint exited 1. (`npx oxlint --rules` printed nothing on 1.72.0 —
  do not rely on it as the check.)
- **CRA status**: `npm view create-react-app version deprecated` → 5.1.0, no npm
  deprecation flag; maintainer sunsetting per the React blog (Feb 2025) is stated from
  pre-cutoff knowledge — re-verify at react.dev before quoting it in writing.
- **Volatility map**: §3.7 rows and the §3.6 generator table are the fastest-rotting parts
  — re-verify each with `npm view <PKG> version` at instantiation time; a major-version
  jump means re-read that tool's migration notes before trusting this file's snippets.
  §3.4 rule 3 (React Compiler) may invert the memoization guidance — check
  `npm view babel-plugin-react-compiler version` and the project's build config. zod 3→4
  and ESLint 9+ flat-config transitions are known snippet-breakers. Doctrine sections
  (state table, effect traps, keys, RTL query priority, date parsing rules) track React
  and ECMA-262 semantics and age slowly.
- Instantiated copies must add their own provenance: date, commit, lockfile versions, and
  the captured outputs of every command in §5.
