---
name: csharp-code-discipline
description: >-
  STACK TIER. Load this skill BEFORE writing or reviewing any C# code — and load it even
  when the language is not named: any task that adds or edits .cs files in a .NET
  solution ("add an endpoint", "write a class for X", "add this feature", "fix this bug",
  "refactor this method") qualifies, as do "implement this in C#", "add a
  service/interface/factory", "should I use a pattern here?", "should this be a new
  project/assembly?", "this PR feels over-engineered", "clean up this class", "set up
  analyzers/.editorconfig", "why is there an interface with one implementation?", "make
  this code follow best practices". Delivers senior-level output discipline: the
  smallest-honest-diff pre-write and post-write checklists, an unnecessary-code trap
  catalog (U1–U10), a pattern-vs-.NET-idiom decision table, a version-stamped modern C#
  baseline, per-diff architecture rules (dependency direction, public/internal,
  constructor injection), and verified analyzer enforcement (.editorconfig, CA/IDE rule
  IDs, dotnet format, -warnaserror). For EF Core migration/query mechanics load
  dotnet-ef-discipline alongside; for the HTTP surface of an endpoint (DTOs on the wire,
  status codes, error shapes, OpenAPI) load aspnet-api-discipline alongside — both apply
  to "add an endpoint"; for decisions that outlive one diff (new layers, wire-format
  policy, ADRs) use architecture-contract.
---

# csharp-code-discipline — Writing C# Like a Senior With Architect Vision

## Purpose

This skill makes you able to solve C# tasks with the smallest honest diff, recognize and
delete the ten classic forms of unnecessary C# code before they ship, reach for a design
pattern only when its problem signature is present (in its .NET-idiomatic form), write
current-idiom C#, and make all of it machine-enforced so the standard survives you.

Version ground truth: everything marked **[verified]** was executed against
**.NET SDK 10.0.301 / C# language version 14.0 (compiler-reported) on 2026-07-07** in a
scratch console project with `<Nullable>enable</Nullable>`, `EnableNETAnalyzers`,
`AnalysisLevel=latest-all`, and `EnforceCodeStyleInBuild=true`. Facts sourced from official
docs (Microsoft Learn, Framework Design Guidelines) but not executed here are marked **[docs]**.

## When to use / When NOT to use

Use when: about to generate or review any C# diff; tempted to add an interface, factory,
mapper, base class, or new project; choosing between a pattern and a delegate; setting up
analyzers and formatting enforcement for a C# repo; auditing a codebase for over-engineering.

| If instead you need... | Use sibling skill |
|---|---|
| Classifying/gating the change itself (mechanical vs behavioral vs contract-breaking) | `change-control` |
| System-scale decisions: which layers exist, storage/wire formats, ADRs, invariants | `architecture-contract` |
| EF Core specifics: migrations, DbContext lifetime, query traps, repository-over-EF detail | `dotnet-ef-discipline` |
| Proving a performance claim (ValueTask, struct, Span, "this is faster") | `proof-and-analysis` |
| Measuring instead of eyeballing (allocation counts, timings, before/after) | `diagnostics-and-tooling` |
| What counts as evidence that the change works; test placement and rent | `validation-and-qa` |
| SDK pinning, restoring a buildable environment, CI wiring beyond the checks named here | `build-and-env` |
| Where a convention should be documented; doc-of-record placement | `docs-and-writing` |
| The HTTP wire surface of an API: DTO wire shapes, serialization behavior, status codes, ProblemDetails, OpenAPI, API breaking changes | `aspnet-api-discipline` |
| React/TypeScript side of a C# API | `react-frontend-discipline` |

Boundary rule: this skill governs the code inside one diff — types, members, idioms,
per-diff structure. The moment a decision cascades across components or outlives the diff
(new storage format, new layer, new external contract), it is `architecture-contract`
territory and classified per `change-control` (typically C, X if irreversible).

## Core doctrine

### Definitions (used throughout)

- **Smallest honest diff**: the minimal set of changed files/lines that solves the stated
  problem AND leaves the touched code healthy — "honest" excludes both gold-plating and
  hacks that create immediate debt.
- **Speculative generality**: code that exists for callers that do not exist — unused
  parameters, unexercised branches, interfaces with one implementation "for flexibility".
- **Seam**: a place where behavior can be substituted without editing the code under test
  (an interface, delegate, or virtual member introduced for substitution).
- **Public surface**: everything reachable from outside the assembly — `public` types and
  members. Changing it is class C per `change-control` when consumers outside the repo
  exist (published package, shared assembly); in a single-repo application it is B — but
  every needless `public` is a future C waiting to happen, which is why §5.2 defaults to
  `internal`.

### 1. The prime directive — smallest honest diff

Three rules, all checkable:

1. **One intent per diff.** A functional change contains zero renames, zero reformatting,
   zero "while I'm here" refactors. Mechanical cleanups are their own class-M commits per
   `change-control` — a reviewer must be able to say "every hunk serves the stated task."
   Tell: `git diff --stat` lists files the task description cannot explain.
2. **YAGNI ("you aren't gonna need it") as a deletion rule, not a slogan.** Any code path no current caller exercises
   gets deleted before commit: unused parameters, config options nobody sets, branches for
   "future" inputs, virtual members nobody overrides. Check: for each added public/internal
   member, name the caller in this diff or an existing one. No caller → delete it.
3. **The second-use rule** (heuristic, widely known as the rule of three): duplicating a
   small block once is cheaper than the wrong abstraction. Extract a shared helper at the
   second or third *proven* use, when the duplication is genuinely the same concept — not
   at the first use "because we'll need it". A wrong abstraction couples every caller to a
   shape that fits none of them; duplication is trivially fixed later, coupling is not.

**PRE-WRITE CHECKLIST** — run before generating any code. Every question defaults to NO;
write the evidence that flips it, or don't do it:

| Question | Default | Evidence that flips it to yes |
|---|---|---|
| Does this need a NEW FILE? | No — extend the file that owns the concept | The type is a new concept no existing file owns, or the owning file is already past the repo's size norm |
| Does this need a NEW TYPE? | No — a method, local function, or delegate parameter | State that must travel together across calls, or a contract someone else implements |
| Does this need a NEW INTERFACE? | No — call the concrete type | A second implementation exists in this diff, OR a genuine boundary seam is needed (see U1 for what qualifies) |
| Does this need a NEW PACKAGE? | No — BCL (the .NET Base Class Library, i.e. what ships in the box) first | The BCL genuinely lacks it, the package is vetted per `proof-and-analysis` Recipe 6 ('prove it before adopting it'), and the cost of owning the dependency is written in the PR |
| Does this need a NEW PROJECT/ASSEMBLY? | No — a folder + namespace | See §5.3 decision rule |
| Does this need a PATTERN? | No — the direct call | The problem signature in §3's table is actually present, in this diff, today |

**POST-WRITE SELF-REVIEW** — run on the diff before declaring done:

- [ ] Every added public or internal member has a caller you can name. (Zero-caller members
  are speculative generality — delete.)
- [ ] Every added abstraction (interface, base class, generic parameter) has ≥2 concrete
  uses in the codebase, or a one-line written reason in the PR ("seam for the SMTP boundary,
  faked in tests X").
- [ ] The diff contains zero hunks unrelated to the task (no reformat-on-save damage, no
  drive-by renames — `git diff` and read every hunk).
- [ ] Nothing was made `public` that could be `internal`, nothing `virtual` that isn't
  overridden (§5.2).
- [ ] You can state in one sentence what a reader now understands more easily than before.
  If the sentence starts with "in the future...", revert that part.

### 2. Unnecessary-code catalog (Symptom / Cause / Fix / Tell)

Index — find your smell by what you are seeing:

| You are seeing | Trap |
|---|---|
| `IFoo` + `Foo`, forever one implementation | U1 |
| `IRepository<T>`/`IUnitOfWork` wrapping EF Core | U2 |
| A class whose every method just calls another class | U3 |
| A mapping library + profile classes for 4 properties | U4 |
| `#region` folds hiding dead or shameful code | U5 |
| `catch (Exception ex) { _log.Error(ex); throw; }` everywhere | U6 |
| `Task.Run` around sync work, or `.Result`/`.Wait()` | U7 |
| `Result<T>`/`Either<T,E>` in an exception-based codebase | U8 |
| `Utils`/`Helpers`/`Common` classes accreting members | U9 |
| An abstract base class with one descendant, or "BaseService" | U10 |

Scope rule: on NEW code in the current diff, apply these fixes before commit. On
PRE-EXISTING code, a catalog hit is a finding to flag — removing it is its own class-M/B
change per `change-control`, never a rider on a feature diff (§1 rule 1); in a repo whose
recorded house convention IS the smell (e.g. IFoo-everywhere), consistency governs until
the convention itself is changed (see §Instantiate governing rule).

**U1 — Interface with one implementation forever (IFoo/Foo disease).**
- Symptom: every class ships with a same-named interface; DI (dependency injection)
  registrations read `services.AddScoped<IOrderService, OrderService>()` for types
  nothing ever substitutes.
- Cause: cargo-cult "program to interfaces" + the belief DI requires interfaces (it does
  not — containers inject concrete types fine **[docs]**).
- Fix: delete the interface, inject the class. Extract an interface at the second
  implementation (rule of three, §1) — the IDE does it in seconds when the day comes.
- **When a single-impl interface IS justified** (labeled judgment): a seam at a *genuine
  boundary* — out-of-process I/O (SMTP, payment gateway, clock, file system) that tests must
  fake, or a contract consumed by another team/assembly you don't control. The test:
  "would a test that exercises this code otherwise hit the network/disk/clock?" Yes → seam
  earns its keep. "We might swap the database someday" is not a boundary; it's a wish.
- Tell: `grep` for the interface name finds exactly one `: IFoo` and zero test fakes.

**U2 — Hand-rolled Repository/UnitOfWork over EF Core.**
- Symptom: `IRepository<T>` with `GetById/Add/Save`, an `IUnitOfWork` wrapping
  `SaveChangesAsync`, layered on a `DbContext`.
- Cause: pattern applied by name. `DbContext` already *is* a Unit of Work and `DbSet<T>`
  already *is* a repository — Microsoft's own docs say so **[docs]**. The wrapper usually
  ends up leaking `IQueryable` anyway (so nothing is abstracted) or blocking the EF features
  you need (`Include`, split queries, bulk operations).
- Fix: use `DbContext` directly in the layer that owns data access; for testability prefer
  a real test database on the production provider; SQLite only if you have read
  `dotnet-ef-discipline` T7 (provider differences) and accepted its limits — that skill
  owns the query/DbContext discipline. A thin *query class* per aggregate
  (a concrete class with intention-revealing methods) is fine — that's organization, not a
  repository abstraction.
- Tell: the repository interface has a method returning `IQueryable<T>`, or it grew a
  `GetByNameAndStatusWithOrders` method — the abstraction is already lost.

**U3 — Wrapper class that only delegates.**
- Symptom: `FooManager` calls `_fooClient.X()` in every method, adding nothing but a stack
  frame; often introduced "to isolate the dependency".
- Cause: layering by habit; fear of using a vendor type directly.
- Fix: delete the wrapper; call the underlying type. Wrap only what you actually change:
  if two call sites need retry + mapping around one vendor call, wrap *that call*, not the
  whole client surface.
- Tell: the wrapper's method list is a subset of the wrapped type's, names included.

**U4 — Mapping layer where a constructor would do** (labeled judgment call).
- Symptom: a mapping library (AutoMapper-style), profile classes, and runtime-configured
  projections — for DTOs with a handful of properties.
- Cause: "we'll have lots of mappings" (speculative) or dislike of "boring" code.
- Fix / decision rule: default to an explicit static method (`OrderDto.From(Order o)`) or a
  constructor — it is compile-checked, debuggable, and greppable. A mapping library is
  worth its config-over-code cost roughly when you have dozens of near-identical mappings
  AND the team commits to the library's conventions repo-wide (heuristic — decide once,
  record it per `docs-and-writing`, don't mix both styles). Reflection-based mapping also
  hides broken mappings until runtime; explicit mapping breaks the build.
- Tell: a mapping profile class is longer than the hand-written mapping would be.

**U5 — Regions hiding dead code.**
- Symptom: `#region Old implementation`, `#region Commented out — keep for reference`.
- Cause: fear of deletion; not trusting git.
- Fix: delete the code. Git is the archive — `git log -S "<IDENTIFIER>"` resurrects it in
  seconds (`failure-archaeology` owns the mining discipline). `#region` around live code is
  a smell too: a class that needs folding to be readable needs splitting, not folding.
- Tell: any `#region` whose content is entirely comments or `#if false`.

**U6 — Catch-log-rethrow that adds nothing.**
- Symptom: `try { ... } catch (Exception ex) { _logger.LogError(ex, "error"); throw; }`
  wrapping every method; the same exception logged four times up the stack.
- Cause: "defensive" habit; not knowing where the real exception boundary is.
- Fix: catch only where you can (a) handle it, (b) add real context (`throw new
  <SPECIFIC>Exception($"order {id}...", ex)`), or (c) at the process boundary where one
  middleware/handler logs everything once. Everywhere else: no try at all. When you do
  rethrow, use bare `throw;` — `throw ex;` resets the stack trace **[docs]**.
- Tell: the catch block's only statements are a log call and `throw;`.

**U7 — Async-over-sync and sync-over-async.**
- Symptom (async-over-sync): `Task.Run(() => syncWork)` inside a library method to "make it
  async" — burns a thread pool thread to fake asynchrony **[docs]**.
- Symptom (sync-over-async): `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` bridging
  async into sync — deadlock and thread-starvation classic.
- Fix: expose sync work as sync; only genuinely async I/O gets an async signature. Bridge
  sync→async by going async all the way up the call chain (§4.3), not by blocking.
- Tell **[verified]**: both `t.Result` and `Task.Delay(1).Wait()` inside an async method
  fire **CA1849** ("synchronously blocks. Use await instead") — under `latest-all`, or
  once §6.3's `CA1849.severity` line enables it (confirmed at `latest` and
  `latest-recommended`). Repo-wide:
  `git grep -nE "\.Result\b|\.Wait\(\)|GetAwaiter\(\).GetResult" -- "*.cs"`.

**U8 — Premature Result<T>/railway-oriented error handling.**
- Symptom: a hand-rolled or imported `Result<T, TError>` threaded through a codebase whose
  BCL calls, EF calls, and frameworks all throw exceptions — every boundary now needs
  translation glue in both directions.
- Cause: pattern imported from F#/Rust blog posts without the language support (no
  exhaustive matching enforcement on class-based Results in C#) or codebase-wide commitment.
- Fix: follow the codebase's existing policy (§4.6). Exceptions for exceptional failure;
  the built-in Try-pattern (`bool TryX(out T result)`) for expected, high-frequency "no"
  answers. Adopting Result-style across a codebase is an `architecture-contract` decision,
  not a per-diff one.
- Tell: `.Value` accessed without checking `.IsSuccess` anywhere — the pattern's one
  guarantee, silently forfeited.

**U9 — God helpers / Utils classes.**
- Symptom: `Utils.cs`, `Helpers.cs`, `Extensions.cs` (the thousand-line one), `Common` —
  members accrete because "there was nowhere else to put it".
- Cause: naming the *bucket* instead of the *concept*.
- Fix: every member either moves next to its single caller (then becomes private), or into
  a type named for the concept (`SlugGenerator`, `IbanValidator`). A static class of
  extension methods is fine when it is *cohesive* (all about one type, e.g.
  `StringSlugExtensions`).
- Tell: the class name says nothing about the domain; members share no noun.

**U10 — Unnecessary base class.**
- Symptom: `BaseService`/`BaseController` with a grab-bag of protected members; abstract
  classes with one descendant; inheritance used to share a helper method.
- Cause: inheritance as the default reuse tool.
- Fix: composition — inject the shared dependency, or pass a delegate (§3 Template Method
  row). For interface evolution, default interface members exist (C# 8+) **[docs]** but are
  for API versioning, not code sharing — prefer composition first. One descendant → inline
  the base class.
- Tell: the base class is never used polymorphically (no variable typed as it) — it's a
  code closet, not a type.

### 3. Design patterns with senior judgment

Rule: a pattern is a *vocabulary for a solution you already need*, never a starting point.
.NET ships most GoF (Gang of Four — the classic *Design Patterns* book) patterns as
language/runtime features — use those forms. Try the
"simpler first" column before the pattern; escalate only when its limits actually bite.

| Pattern | Problem signature (must be TRUE today) | .NET-idiomatic form | Misuse tell | Simpler first |
|---|---|---|---|---|
| **Observer** | Multiple independent parties must react to events from a source that must not know them | C# `event` for in-process notification; `IObservable<T>`/`IObserver<T>` (BCL) for composable streams **[verified: `IObservable<Money>` implemented and compiled]** | Hand-rolled `Subscribe/Notify` lists re-implementing what `event` does | A direct method call — if there's exactly one, known reactor |
| **Strategy** | The SAME operation has multiple interchangeable algorithms, selected at runtime | A `Func<>`/delegate parameter **[verified compile]**; or multiple DI registrations of one interface resolved by key/`IEnumerable<T>` injection **[docs]** | One strategy class, forever; strategy chosen by a `switch` that never changes | A `switch` expression over an enum — readable and exhaustiveness-checked |
| **Factory** | Construction requires logic/dependencies the caller must not know | DI container registration (the container IS the factory); `IServiceProvider`-based factory delegates in registrations; a static `Create(...)` method for validation-heavy construction **[docs]** | `FooFactory` whose `Create()` is one `new Foo()` | `new` — construction without logic needs no factory |
| **Decorator** | Cross-cutting behavior (caching, retry, logging) layered onto an existing contract WITHOUT editing it | DI decoration (register wrapper resolving inner — no built-in Decorate in MS.DI: use a factory registration or a library like Scrutor, package name volatile); for HTTP: `DelegatingHandler` in the `HttpClient` pipeline **[docs]** | Decorator + interface invented in the same diff (nothing existed to decorate) | Put the 3 lines in the method — one call site doesn't need a layer |
| **Singleton** | One instance per process, genuinely (cache, connection pool) | Container lifetime: `services.AddSingleton<T>()` — in container-hosted code, never a hand-rolled `static Instance` (untestable, hides the dependency, lifetime invisible) **[docs]** | `public static readonly Foo Instance` in new DI-era code | Ask whether it must be single at all — statelessness usually removes the requirement |
| **Template Method** | An algorithm skeleton with one varying step | Usually just a delegate parameter: `decimal Total(items, Func<Money, decimal> valuation)` **[verified compile]** | An abstract base class + one override per "step" with a single descendant (U10) | Pass the varying part as an argument |
| **Command / Mediator** | You need queueing, undo, or dispatch of requests as first-class objects; OR (mediator) dozens of handlers where pipeline behaviors (validation, logging) genuinely pay | MediatR-style `IRequest`/`IRequestHandler` **(labeled judgment: it buys pipeline uniformity at the cost of go-to-definition and an indirection layer — a team-level adoption decision, not per-diff)** | A "mediator" whose every `Send` has exactly one handler called from exactly one controller — a method call with extra steps | Call the service method. Controllers may call services directly; that is not a sin |

Escalation rule (heuristic): delegate → interface with 2+ impls → pattern infrastructure.
Each step requires the previous one to have actually hurt.

### 4. Modern C# idiom baseline

Stamped: **C# 14.0 on .NET SDK 10.0.301, verified 2026-07-07** — every idiom below marked
[verified] compiled in the scratch project. On older repos, honor the repo's pinned
`LangVersion`/SDK (`build-and-env` owns pinning); never upgrade the language in a feature
diff (that's a separate class-M/B change per `change-control`).

#### 4.1 Records for immutable data

[verified: `public sealed record Money(decimal Amount,
string Currency);`]. Use for DTOs, value objects, messages — value equality and
`with`-expressions for free. NOT for: EF Core entities (value equality and immutability
fight change tracking — see `dotnet-ef-discipline` §6), types with identity semantics, or
mutable aggregates. Default to `sealed`.

#### 4.2 Pattern matching over type-switch chains

[verified: switch expression with type,
property, `when`, and `null` patterns]. Replace `if (x is Foo) { var f = (Foo)x; ... }`
chains with a `switch` expression; the compiler warns on non-exhaustive matches
(**CS8509** [verified]). A
`switch` expression is for *computing a value*; keep statement `switch` for side effects.

#### 4.3 Async discipline

- Async all the way: an async call is awaited by an async caller, to the top (controller,
  endpoint, `Main`). Never `.Result`/`.Wait()` — **CA1849** fires [verified], and the
  patterns deadlock under synchronization contexts.
- Every public async API takes a `CancellationToken` (last parameter, default allowed on
  the outermost public surface) and passes it down [verified: plumbed through
  `Stream.ReadAsync`]. A public async method that can't be cancelled is a hung request
  you can't shed.
- `ValueTask`/`ValueTask<T>` only behind a measured allocation problem on a hot path —
  route the measurement through `proof-and-analysis`; it has real usage restrictions
  (single await) **[docs]**.
- Suffix async methods `Async` — enforceable as a naming rule: **IDE1006 "Missing suffix:
  'Async'"** fired at build [verified, with the .editorconfig rule in §6].
- `CA2007` (ConfigureAwait) fired under `latest-all` [verified]: apply it in *libraries*;
  disable it in application code (ASP.NET Core has no synchronization context) **[docs]**
  — an example of tuning, not obeying, the analyzer set (§6).

#### 4.4 Nullable reference types — required default on new code

(Candidate NN entry for the instantiated skill per `change-control` §3 — "non-negotiable"
is that skill's registered term, not rhetoric.) `<Nullable>enable</Nullable>`
on every new project; new files in mixed repos get `#nullable enable`. Dereferencing a
possibly-null value warns **CS8602** [verified]; §6 promotes it to an error. Do not
null-scatter: `!` (null-forgiving) requires a justifying comment; `?? throw` at
construction beats null checks at every use.

#### 4.5 Disposal

`using`/`await using` for everything `IDisposable`/`IAsyncDisposable`
[verified: `await using var stream = File.OpenRead(...)`]. Prefer `using` declarations
(no braces) over statements. Implementing `IDisposable` yourself is rare — owning an
unmanaged resource or composing owned disposables; otherwise don't.

#### 4.6 Exceptions vs return values — one policy per codebase

Exceptions for exceptional
failure (broken invariant, unavailable dependency); the Try-pattern
(`bool TryParseCode(string input, out string code)` [verified compile]) for expected,
high-frequency misses (parsing, cache lookup). Never exceptions for control flow on hot
paths; never error codes that callers can silently ignore. Whichever the repo does, match
it (§Instantiate consistency rule); changing policy is an `architecture-contract` decision.

#### 4.7 Current idiom, verified on this SDK

[all compiled]: file-scoped namespaces
(`namespace Probe;`), primary constructors on classes
(`class PriceService(TimeProvider clock)`), collection expressions
(`List<string> _codes = ["USD", "EUR", "CHF"]`). Use them in new code; do not retrofit
them across old files in a feature diff (`dotnet format`/IDE can do it as a class-M sweep).

#### 4.8 LINQ readability rules

- LINQ for *queries* (filter/project/aggregate); `foreach` when there are side effects,
  early exits with work in between, or the query needs a comment to be understood.
  Heuristic: if you're chaining more than ~4 operators or nesting lambdas two deep, a
  `foreach` or an intermediate variable with a name is clearer.
- No multiple enumeration of expensive sequences. Tell: the same `IEnumerable<T>` variable
  consumed twice (e.g. `.Any()` then `.First()`, or two `foreach`es) when it's backed by a
  generator or EF query — each consumption re-executes. Fix: materialize once
  (`.ToList()`) or restructure. EF-side query shaping belongs to `dotnet-ef-discipline`.

#### 4.9 `struct` / `Span<T>` / `stackalloc` — measurement-gated

Reach for value types and spans
only with a profiler/benchmark showing the allocation or copy cost matters, per
`proof-and-analysis` (benchmark honesty) and `diagnostics-and-tooling` (measure, don't
eyeball). Default: classes and arrays; correctness first.

### 5. Architect-vision layer (per-diff scale)

System-scale structure belongs to `architecture-contract`. This section is the architecture
judgment you exercise inside a single diff.

#### 5.1 Dependency direction

The rule: dependencies point from volatile toward stable —
domain logic depends on nothing above it. Per-diff DEPENDENCY SMELL LIST — reject the diff
if it introduces any of:

| Smell | Example tell |
|---|---|
| UI/transport type in a domain signature | A domain method takes `HttpContext`, returns `IActionResult`, or throws a framework exception |
| Data-layer type leaking upward | `DbContext`, `DbSet<T>`, or an EF-attached entity in a controller/domain signature above the layer that owns data access (`dotnet-ef-discipline`) |
| Static reach-around | Domain code calling a static service/locator (`ServiceRegistry.Get<T>()`, static config, `DateTime.Now` instead of injected `TimeProvider`) — hidden dependency, untestable |
| Sideways grab | One feature folder `using` another feature's internals instead of its public seam |

#### 5.2 Public vs internal

Default every new type and member to `internal` (top-level C#
types already default internal — keeping them so is free). `public` is an API commitment:
anything public can grow external callers; once they exist outside the repo, changing it
is class C per `change-control` (in-repo-only callers: class B). The analyzer agrees:
**CA1515** ("types can be made internal") fired on
every needlessly-public type in the scratch build [verified — application projects only;
libraries with intended consumers disable it]. Tests reach internals via
`[InternalsVisibleTo]` **[docs]**. Never `virtual` without a designed override story
(Framework Design Guidelines: unsealed + virtual is an extensibility contract you must
then honor forever **[docs]**).

#### 5.3 New project/assembly vs folder — decision rule

A new project is justified only
when you need a *compiler-enforced* boundary: different deployment unit, different
dependency set (domain project must not reference EF/web packages), or a genuinely
independent consumer. Otherwise a folder + namespace costs nothing and restructures freely.
Heuristic: if the new project would be referenced by exactly one other and ship with it
always, it's a folder.

#### 5.4 Constructor injection discipline

- Constructor injection only — no service locator (`IServiceProvider` injected into
  ordinary classes and dotted into), no property injection, no statics (§5.1).
- Heuristic threshold: more than ~5 constructor dependencies is a design smell — the class
  has too many responsibilities. Refactor menu, in order: (a) split the class along the
  dependency clusters (the deps that are used by disjoint method sets ARE the split line);
  (b) group parameters that always travel together into a small immutable type;
  (c) replace two deps with the one thing actually consumed (inject `TimeProvider`, not a
  config service you only read one value from — options pattern **[docs]**). Do NOT "fix"
  it by injecting a facade/locator that hides the same deps.

#### 5.5 API design basics

Primary source: *Framework Design Guidelines* (Cwalina &
Abrams, Microsoft) and Microsoft Learn's naming guidelines **[docs]**; naming-rule
enforcement verified in §6.

| Rule | Right | Wrong |
|---|---|---|
| Async suffix | `LoadOrdersAsync` | `LoadOrders` returning `Task` (IDE1006-enforceable, §6) |
| Try-pattern shape | `bool TryParse(string s, out T value)` — no exception on miss | `Parse` returning null on miss, undocumented |
| Interfaces `I`-prefixed, PascalCase types/members, camelCase parameters/locals | `IOrderStore.GetById(orderId)` | `iOrderStore`, `get_by_id` |
| Flags enums plural, non-flags singular | `[Flags] enum BindingFlags`; `enum DayOfWeek` (BCL examples) **[docs]** | A plural non-flags enum, or a `[Flags]` enum whose members aren't powers of two |
| No boolean traps | `Publish(PublishOptions.DraftOnly)` or two named methods | `Publish(true, false)` — unreadable at every call site |
| Options object | ≥3 optional/config parameters → a settings record | 6-parameter method with 4 defaults |
| No abbreviations in public names | `GetWindowHandle` | `GetWinHndl` |

### 6. Enforcement — make good practice checkable

Standards that live in review comments die; standards that live in the build survive. All
of the following was executed on SDK 10.0.301, 2026-07-07 [verified].

**6.1 The csproj block** (or better, repo-wide in `Directory.Build.props`):

```xml
<PropertyGroup>
  <Nullable>enable</Nullable>
  <EnableNETAnalyzers>true</EnableNETAnalyzers>
  <AnalysisLevel>latest-recommended</AnalysisLevel>
  <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
</PropertyGroup>
```

Warnings-as-errors is a posture choice — pick ONE and record it: (a) hard everywhere:
add `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>` to the block above (local
builds fail on any warning; §6.4's `-warnaserror` becomes redundant belt-and-braces);
or (b) fluid locally, hard in CI: leave the property out and rely on §6.4's
`dotnet build -warnaserror` as the CI gate. The .editorconfig severities in §6.3 assume
posture (b).

- `EnableNETAnalyzers` + `AnalysisLevel` turn on the CA rule set. Observed per level on
  the same planted violations [verified]: `latest` (default) → only compiler warnings
  (CS0414/CS0649/CS8602) plus the .editorconfig-driven IDE rules; `latest-recommended` →
  adds CA1822; `latest-all` → the full §6.2 table, including noise you must tune (observed:
  CA1303 demanding resource tables for `Console.WriteLine("Hello")`, CA2007 in app code).
  Key mechanism [verified]: a `dotnet_diagnostic.<ID>.severity` line in .editorconfig
  ENABLES an off-by-default rule — with `latest-recommended`, adding
  `CA1849.severity = error` / `CA1823.severity = warning` made both fire at exactly those
  severities. So: run `latest-recommended`, then opt IN to the specific stricter rules you
  want (§6.3) rather than running `latest-all` and suppressing noise.
- `EnforceCodeStyleInBuild=true` is what makes IDE-prefixed style rules (naming, readonly)
  fail the BUILD, not just squiggle in the editor — without it, only CA rules fire at build
  **[docs; behavior consistent with the verified runs]**.

**6.2 Planted violations → observed rule IDs** [verified — this exact table was produced
by building the scratch project under `AnalysisLevel=latest-all`; the CA1849/CA1823 rows
were additionally reproduced under `latest-recommended` via the §6.3 .editorconfig lines]:

| Planted violation | Fired at build |
|---|---|
| Unused private field `_unusedField = 42` | **CA1823** ("Unused field") + compiler **CS0414** |
| Never-assigned private field | **CS0649** |
| Mutable field never mutated | **IDE0044** ("Make field readonly") |
| Private field named `BadName` (naming rule: `_camelCase`) | **IDE1006** ("Missing prefix: '_'") |
| `async` method not suffixed `Async` | **IDE1006** ("Missing suffix: 'Async'") |
| `t.Result` and `.Wait()` inside async method | **CA1849** (×2, "synchronously blocks") |
| Dereference of nullable parameter under `<Nullable>enable</Nullable>` | **CS8602** |
| Needlessly-public types in an application | **CA1515** |
| Instance method using no instance state | **CA1822** |

**6.3 Starter .editorconfig** — the load-bearing rules with severity rationale (full
naming-rule syntax verified by the IDE1006 firings above):

```ini
root = true

[*.cs]
indent_style = space
indent_size = 4

# ERRORS: correctness — a broken build is the point
dotnet_diagnostic.CS8602.severity = error   # null dereference (under posture (a) of §6.1 this is belt-and-braces)
dotnet_diagnostic.CA1849.severity = error   # sync-over-async in async code (off by default — this line ENABLES it, verified)
dotnet_diagnostic.CA2007.severity = none    # app code; set to warning in library projects — decide per repo, comment why

# WARNINGS: hygiene — visible locally, gated in CI via -warnaserror (§6.4)
dotnet_diagnostic.CA1823.severity = warning # unused private field
dotnet_diagnostic.IDE0044.severity = warning # make field readonly
dotnet_diagnostic.IDE1006.severity = warning # naming violations
csharp_style_namespace_declarations = file_scoped:warning

# Naming: private fields _camelCase
dotnet_naming_rule.private_fields_underscore.symbols = private_fields
dotnet_naming_rule.private_fields_underscore.style = underscore_camel
dotnet_naming_rule.private_fields_underscore.severity = warning
dotnet_naming_symbols.private_fields.applicable_kinds = field
dotnet_naming_symbols.private_fields.applicable_accessibilities = private
dotnet_naming_style.underscore_camel.capitalization = camel_case
dotnet_naming_style.underscore_camel.required_prefix = _

# Naming: async methods end in Async
dotnet_naming_rule.async_suffix.symbols = async_methods
dotnet_naming_rule.async_suffix.style = async_style
dotnet_naming_rule.async_suffix.severity = warning
dotnet_naming_symbols.async_methods.applicable_kinds = method
dotnet_naming_symbols.async_methods.required_modifiers = async
dotnet_naming_style.async_style.capitalization = pascal_case
dotnet_naming_style.async_style.required_suffix = Async
```

Severity philosophy: `error` for rules where a violation is a bug (null deref, blocking in
async); `warning` for hygiene, promoted wholesale in CI by `dotnet build -warnaserror`
(§6.4, posture (b)) so local iteration stays fluid. Suppressions (`#pragma warning disable`, `.editorconfig` `none`)
require an inline comment with the reason — an unexplained suppression is a review reject.

**6.4 The CI gate — two commands** [verified]:

```sh
dotnet build -warnaserror --no-incremental
# Observed: the scratch project's 20 warnings became errors; exit code 1; Build FAILED.
# Trap [verified]: without --no-incremental (or a clean), an up-to-date build SKIPS
# compilation and reports 0 errors — the gate silently passes. Always build clean in CI.

dotnet format --verify-no-changes
# Observed on a deliberately misformatted file: per-hunk lines
#   error WHITESPACE: Fix whitespace formatting. Insert '\r\n'. ...
# and EXIT CODE 2. Zero drift = exit 0. Developers run plain `dotnet format` to fix.
```

Note [verified]: `--verify-no-changes` also fails (exit 2) on enabled style/analyzer
diagnostics that `dotnet format` cannot auto-fix (observed: IDE1006 naming, CA1849) —
running plain
`dotnet format` and re-verifying still exits 2; the remaining failures are code changes
(rename etc.) that must be fixed by hand. Use `dotnet format whitespace
--verify-no-changes` if the gate should test pure formatting only.

`dotnet format` ships in the SDK (no install) **[docs; the verified runs used the in-box
tool]**. A formatting-only sweep across old files is a class-M change per `change-control`
— its own commit, never mixed into a feature diff (§1).

## Worked example

**Illustrative example — all facts fictional.** Project "Harborline". Task: "when a docket
closes, send a confirmation email."

**Naive implementation — 5 files, ~140 lines added:**

```text
INotificationService.cs      interface, 1 method, 1 implementation ever        (U1)
NotificationService.cs       implements it; wraps SmtpMailer 1:1               (U3)
NotificationFactory.cs       Create() => new NotificationService(...)          (§3 Factory misuse — DI already constructs it)
DocketEmailMapper.cs         mapping profile: Docket -> DocketClosedEmail, 4 properties (U4)
DocketService.cs             +12 lines: factory lookup, mapper call, try/catch-log-rethrow (U6)
```

Pre-write checklist verdicts: new interface? — no second implementation, and the real
boundary (SMTP) already has a seam: the existing `ISmtpMailer` and `EmailTemplates`
helpers used by tests. New factory?
— construction has no logic. New mapper? — four properties.

**Senior implementation — 2 files, ~20 lines changed:**

```csharp
// DocketClosedEmail.cs (new file — a new concept, so it passes the checklist)
public sealed record DocketClosedEmail(string To, string DocketNumber, DateTimeOffset ClosedAtUtc)
{
    public static DocketClosedEmail From(Docket d) =>
        new(d.OwnerEmail, d.Number, d.ClosedAtUtc ?? throw new InvalidOperationException($"Docket {d.Number} is not closed."));
}

// DocketService.cs — inside the existing CloseAsync, 3 lines:
var email = DocketClosedEmail.From(docket);
await mailer.SendAsync(email.To, EmailTemplates.DocketClosed(email), cancellationToken);
// no try/catch: the endpoint middleware already logs failures once (U6)
```

Diff-size comparison: 5 files/~140 lines vs 2 files/~20 lines; 4 types vs 1; behavior
identical; the SMTP seam already existed so testability is unchanged. Post-write review:
every added member has a caller (`From` — one; the record — the mailer call), the one new
type has a written reason (new concept), zero unrelated hunks. Extension point deferred:
when SMS notifications actually arrive (second use), *that* diff extracts the seam — and
the IDE does the extraction mechanically.

## Instantiate for your project

Produce `.claude/skills/<PROJECT>-csharp-discipline/SKILL.md`. A Sonnet-class model can
execute these steps unaided. **The governing rule: the instantiated skill records the
repo's CURRENT conventions as law, even where they differ from this skill's defaults.
Consistency beats preference** — a style divergence you dislike gets flagged as a proposed
(gated, class-M/B per `change-control`) change in the skill's Known gaps section; it is
never "fixed" silently inside feature diffs.

### Step 1 — Mine the enforcement surface

```sh
# .editorconfig: exists? which rules and severities?
git ls-files | grep -i "\.editorconfig"
# Repo-wide build law
git ls-files | grep -iE "Directory\.Build\.(props|targets)|Directory\.Packages\.props"
# Per-project posture: nullable, analyzers, warnings-as-errors, LangVersion
git grep -n "Nullable\|TreatWarningsAsErrors\|AnalysisLevel\|AnalysisMode\|EnableNETAnalyzers\|EnforceCodeStyleInBuild\|LangVersion" -- "*.csproj" "*.props"
# Third-party analyzer packages
git grep -n "StyleCop\|Roslynator\|SonarAnalyzer\|Meziantou.Analyzer\|xunit.analyzers" -- "*.csproj" "*.props"
# SDK pin
cat global.json 2>/dev/null
```

**If Step 1 finds no .editorconfig and no analyzer settings:** the repo's enforcement
section records "none in force" as fact. Do NOT silently adopt §6.3 — propose it as a
Known-gaps entry (class-M/B per `change-control`). Conventions then come from the code
itself: sample mechanically, e.g. private-field naming (per-file counts) by
`git grep -chE "private\s+(readonly\s+)?\S+\s+_[a-z][A-Za-z0-9]*\s*[=;]" -- "*.cs"` vs
`git grep -chE "private\s+(readonly\s+)?\S+\s+[a-z][A-Za-z0-9]*\s*[=;]" -- "*.cs"`
(majority wins; within ~60/40, label `inconsistent — decision needed`).

**If projects within one solution disagree** (different LangVersion, nullable posture,
or house style): record conventions PER PROJECT in the skeleton's baseline and
house-conventions sections, and state the rule: *a diff follows the conventions of the
project it touches*, never a blend, never the skill author's preference.

### Step 2 — Mine the current pattern usage (the unnecessary-code audit)

```sh
# IFoo/Foo single-implementation candidates (U1): list interfaces, then count implementors
git grep -lE "^\s*public interface I[A-Z]" -- "*.cs"
git grep -c ": I<NAME>\b" -- "*.cs"        # per candidate; 1 hit + no test fake = U1 candidate
# Is the interface faked in tests? (a fake/mock/substitute = working seam, NOT U1)
git grep -nE "Mock<I<NAME>>|Substitute\.For<I<NAME>>|Fake<NAME>|: I<NAME>" -- "*Test*" "*Tests*" "*.Tests*"
# Repository/UoW over EF (U2)
git grep -nE "interface I.*Repository|IUnitOfWork" -- "*.cs"
# Sync-over-async (U7)
git grep -nE "\.Result\b|\.Wait\(\)|GetAwaiter\(\)\.GetResult" -- "*.cs"
# Regions and dead code (U5)
git grep -n "#region" -- "*.cs" | head -30
# God helpers (U9)
git ls-files "*.cs" | grep -iE "utils|helpers|common"
# Mediator/mapping libraries present? (§3, U4 — record as CURRENT LAW if used consistently)
git grep -n "MediatR\|AutoMapper\|Mapster" -- "*.csproj"
# Exceptions-vs-results policy in force (U8/§4.6)
git grep -lE "class Result<|OneOf<|ErrorOr" -- "*.cs"
```

### Step 3 — Prove the gates in THIS repo

Run `dotnet build -warnaserror --no-incremental` and `dotnet format --verify-no-changes`
at the repo root. Record verbatim: exit codes, warning/error counts, and the top recurring
rule IDs. A repo that fails these today gets that fact in Known gaps — the instantiated
skill documents reality, and cleanup is a proposed campaign (`campaign-design` if large),
not a silent side effect.

### Step 4 — Fill the skeleton

```markdown
---
name: <PROJECT>-csharp-discipline
description: <triggers naming this repo's projects, conventions, and known smells>
---
# <PROJECT> — C# Code Discipline
## Language/SDK baseline       # LangVersion, SDK from global.json, nullable status PER PROJECT (Step 1)
## Enforcement in force        # actual .editorconfig rules, analyzer packages, CI commands + observed exit codes (Steps 1, 3)
## House conventions as law    # naming, mapper/mediator/result policy AS PRACTICED, with file citations (Step 2)
## Unnecessary-code audit      # U1–U10 instances found, each with file:line evidence — candidates, not verdicts
## Pattern usage map           # which §3 patterns the repo uses deliberately, and the team decision behind each (or UNKNOWN)
## Dependency direction        # the layering that actually holds, from project references: `dotnet list <PROJ> reference`
## Known gaps                  # divergences from this skill's defaults, each as a PROPOSED gated change
## Provenance                  # date, SDK, commands run, SHAs cited
```

### Step 5 — Evidence gates (do not fill a blank without its evidence)

- Do not call an interface U1 without the implementor count from Step 2 AND a search for
  test fakes/mocks of it (a faked interface is a working seam, not disease).
- Do not write "nullable is enabled" repo-wide from one csproj — enumerate per project.
- Do not record an enforcement command you have not run in this repo with its observed
  exit code (Step 3).
- Do not write a house convention from one file — cite ≥3 occurrences or label it
  `inconsistent — decision needed`.
- Do not list a Known-gap "fix" as pending work without routing it: style sweep →
  class M per `change-control`; policy change (Result-adoption, mapper removal) →
  `architecture-contract` decision first.

## Provenance and maintenance

- Authored 2026-07-07 against no specific project (authoring wave dated 2026-07-06;
  execution timestamps local). Stack facts verified by execution in a
  scratch console project: **.NET SDK 10.0.301, C# language version 14.0** (reported by the
  compiler via a deliberate `#error version` probe: "Language version: 14.0"), Windows 11.
- Verified by execution 2026-07-07: records, primary constructors on classes, collection
  expressions, file-scoped namespaces, switch expressions with type/property/null patterns,
  `IObservable<T>`/`IObserver<T>` implementation, `Func<>` strategy parameters, Try-pattern
  signature, `await using` + `CancellationToken` plumbing (all compiled); planted-violation
  build with `EnableNETAnalyzers` + `AnalysisLevel=latest-all` +
  `EnforceCodeStyleInBuild=true` + `.editorconfig` naming rules producing exactly the IDs
  in §6.2 (CA1823, CS0414, CS0649, IDE0044, IDE1006 ×2 forms, CA1849 ×2 forms, CS8602,
  CA1515, CA1822, plus CA1303/CA2007 noted as tune-out examples); `dotnet build
  -warnaserror --no-incremental` (exit 1, warnings promoted, and the incremental-build
  false-pass trap); `dotnet format --verify-no-changes` (exit 2, `error WHITESPACE:` lines
  on a misformatted file).
- [docs] items NOT executed here — re-verify on first use: DI decoration/keyed
  registration mechanics, `DelegatingHandler` wiring, `AddSingleton` lifetime semantics,
  `[InternalsVisibleTo]`, options pattern, default interface members, `ValueTask`
  restrictions, ConfigureAwait guidance, `throw ex;` stack-trace reset, Task.Run
  thread-pool cost, `EnforceCodeStyleInBuild` exact gating semantics, DbContext-is-a-UoW
  (this skill's U2 is its home; `dotnet-ef-discipline` owns the query/DbContext
  discipline around it), Framework Design Guidelines naming details (flags-enum
  pluralization).
- Analysis-level membership verified 2026-07-07 by rebuilding the same violations at
  `latest`, `latest-recommended`, and `latest-all`, and by enabling CA1849/CA1823 via
  .editorconfig severity lines under `latest-recommended` (both fired, CA1849 as error).
- Fix-pass re-verification 2026-07-08 (same SDK 10.0.301): CA1849-via-severity-line
  confirmed at `latest` as well as `latest-recommended`; CS8509 fired on a planted
  non-exhaustive switch expression; full-scope `dotnet format --verify-no-changes`
  exited 2 with only non-auto-fixable diagnostics remaining (IDE1006, CA1849) after a
  plain `dotnet format`, while `dotnet format whitespace --verify-no-changes` exited 0;
  the §Instantiate Step 1 convention-sampling greps and the Step 2 test-fake grep were
  executed against a scratch git repo with planted declarations and fakes.
- Volatile parts, each with its re-verification one-liner:
  - `AnalysisLevel` values and per-level rule membership shift each SDK release —
    re-verify: `dotnet build --no-incremental -v q` on the §6.2 planted-violation probe.
  - `dotnet format` exit codes and in-box status — re-verify:
    `dotnet format --verify-no-changes; echo $?`
  - C# idiom set (§4.7) moves with LangVersion — re-verify: compile a file using the
    §4.7 idioms on the repo's pinned SDK (`dotnet build`).
  - MediatR-style library licensing/ecosystem status — re-verify:
    `dotnet package search MediatR --exact-match`
  The ~5-dependency threshold (§5.4), the >4-operator LINQ rule (§4.8), and the rule of
  three (§1) are labeled heuristics, not measurements.
- Instantiated copies must add their own provenance: repo SDK/LangVersion, the Step-3
  observed exit codes, and file:line citations behind every audit row and convention.
