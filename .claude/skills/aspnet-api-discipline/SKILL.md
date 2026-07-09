---
name: aspnet-api-discipline
description: >-
  STACK TIER. Load this skill when building or reviewing anything that crosses an
  ASP.NET Core API's HTTP wire — adding/changing an endpoint (controller action or
  MapGet/MapPost), shaping a DTO or response body ("DateTime or DateTimeOffset?",
  "why does the front end get a number for my enum?"), returning errors (what a
  400/404/500 should look like, ProblemDetails/IExceptionHandler), setting up or
  consuming the OpenAPI document, versioning an API, deciding whether a change breaks
  clients, or when a React/TS consumer reports wrong dates, missing fields, or
  mismatched types. Delivers DTOs-as-wire-contracts (never entities), a breaking-change
  taxonomy mapped to change-control classes, verified System.Text.Json wire behavior,
  the single ProblemDetails error contract, status-code and route discipline, and the
  OpenAPI-as-CI-artifact gate react-frontend-discipline generates clients from. Load
  csharp-code-discipline ALONGSIDE for the C# inside the handlers (both apply to "add
  an endpoint"); dotnet-ef-discipline for the data layer; "the API is slow" is
  diagnostics-and-tooling / sql-server-operations territory, not this skill's.
---

# aspnet-api-discipline — The API Surface Is a Published Contract

## Purpose

This skill makes you able to (1) treat every byte an ASP.NET Core API emits as a published
contract whose consumers you must enumerate — and treat as un-enumerable unless proven
otherwise (§1), (2) classify any API change as
breaking/non-breaking before shipping it, (3) control exactly what System.Text.Json puts
on the wire (casing, dates, enums, nulls) instead of discovering it from a bug report,
(4) return one error shape — ProblemDetails — for the whole API, leaking nothing in
Production, and (5) make the OpenAPI document a build artifact that CI diffs, so contract
drift fails the build instead of failing the front end.

Version ground truth: everything marked **[verified]** was executed against
**.NET SDK 10.0.301 / ASP.NET Core 10.0.9 (`dotnet new webapi` templates, net10.0) on
2026-07-08**, with wire output captured via `curl` against running Kestrel processes in
both Development and Production environments. Facts from official docs not executed here
are marked **[docs]**.

## When to use / When NOT to use

Use when: adding or changing any endpoint, DTO, status code, route, or error response;
reviewing a diff that touches anything serialized to HTTP; setting up OpenAPI, error
handling, or serializer options in a new API; a front-end consumer reports a
type/date/enum mismatch; deciding if an API change needs consumer coordination.

This skill owns the space **between the HTTP wire and the application code**: what
serializes, what status codes mean, what errors look like, what the OpenAPI document
promises. It does not own what happens on either side of that boundary:

| If instead you need... | Use sibling skill |
|---|---|
| C# craft inside handlers/services: smallest diff, pattern judgment, async idiom, DTO-mapping style (its U4) | `csharp-code-discipline` |
| The data layer behind the endpoint: EF entities, migrations, query traps, DbContext lifetime | `dotnet-ef-discipline` |
| The consuming React/TS client: generated types, runtime validation, date parsing on the JS side | `react-frontend-discipline` |
| Classifying and gating the change itself (M/B/C/X classes, review requirements) | `change-control` |
| What counts as proof the endpoint works; contract-test placement | `validation-and-qa` |
| Running/deploying the API, environment variables, where logs land | `run-and-operate` |
| Whether the API's layering/versioning strategy is a recorded decision | `architecture-contract` |
| Measuring latency/throughput claims about an endpoint | `diagnostics-and-tooling`, `proof-and-analysis` |
| Whether this wire-format battle was fought before | `failure-archaeology` |

**Out of scope — authentication/authorization DEPTH**: identity providers, OIDC flows,
token validation internals, cookie vs JWT trade-offs. This skill covers only the
fail-closed `[Authorize]`-by-default posture (§5.5). For the rest, use the official
ASP.NET Core security docs for your exact .NET version — auth details rot fast and
half-remembered auth guidance is dangerous. Also out of scope: gRPC and GraphQL surfaces
(different contract mechanics entirely).

## Core doctrine

### Definitions (used throughout)

- **Wire contract**: the exact bytes a consumer can observe — JSON property names, types,
  formats, status codes, headers, error shapes. Not your C# types; what serialization
  *does* to them.
- **DTO** (data transfer object): a type that exists solely to define a wire shape.
  Its properties are promises.
- **ProblemDetails**: the standard machine-readable error body defined by **RFC 9457**
  (which obsoletes the older RFC 7807 — cite 9457, the format is the same);
  content type `application/problem+json`. ASP.NET Core ships first-class support.
- **OpenAPI document**: the machine-readable description of the whole API surface
  (paths, schemas, status codes). ASP.NET Core generates one at runtime via the built-in
  `Microsoft.AspNetCore.OpenApi` package [verified — template default].
- **Tolerant reader**: a consumer that ignores unknown fields. The default
  System.Text.Json consumer is tolerant [verified: POSTing an extra unknown field to a
  minimal-API endpoint bound fine and echoed 200]; strictly-generated or
  strictly-validating clients are not.
- **Minimal APIs vs controllers**: the two endpoint styles — `app.MapGet(...)` lambdas
  in `Program.cs` vs `[ApiController]` classes with action methods. Decision rule in
  §5.1; the wire rules here apply to both.

### Find your symptom

| You are seeing / asking | Go to |
|---|---|
| Front end gets a NUMBER for my enum | §3.2 |
| Dates shift by hours depending on the user's timezone | §3.3 |
| TS client can't find keys in `errors` (casing mismatch) | §3.1 trap, §4.3 |
| Stack trace / connection string in a client-visible body | §4.1, §4.4 |
| Empty 500/400 body in Production | §4.1 → fix in §4.2 |
| Invalid body returns 201 from a minimal API | §4.3 silent-skip trap |
| "Is this API change breaking?" / "it's just a rename" | §2 |
| Generated TS types wrong, missing, or `number \| string` money | §6, §3.5 |
| Monitoring says success while users see failures | §4.4 catch-and-200 |

### 1. The contract-first prime rule

**Every response body, status code, and route is a published contract.** Default class
**C — Contract-breaking** when any consumer lives outside this repo (public API, mobile
app, another team's service) — `change-control`'s class-C litmus: "someone who never sees
this PR can be broken by it" — with its gates (contract-owner review, consumer-side
compatibility evidence, written rollback plan). **When the API is internal-only, every
consumer lives in this repo (e.g. the React app beside it), and client+server deploy in
lockstep, the same change is class B** — all call sites are enumerable with a repo-wide
search and the consumer updates in the same PR (`csharp-code-discipline` applies the
identical rule to public C# surface). Two escalations back to C even in-repo:
(a) deployment is not lockstep — a user's cached SPA bundle is an out-of-repo consumer at
runtime until it expires; (b) nobody has actually enumerated the consumers in writing.
When in doubt, take the higher class (`change-control` §1). Additive changes may drop
to B *only* if the project has a written compatibility policy saying consumers ignore
unknown fields (`change-control` §1 rule of thumb); no written policy → C.

Three rules follow:

1. **DTOs are wire contracts — never expose EF entities or domain types directly.**
   An entity's shape is owned by the data layer and changes for data-layer reasons
   (`dotnet-ef-discipline`); the moment it serializes, every column rename becomes a
   class-C API break, navigation properties drag in object cycles and over-fetching, and
   persistence concerns leak to every client. Every endpoint returns and accepts types
   that exist *only* for the wire. Whether the entity→DTO mapping is a static `From`
   method or a mapping library is `csharp-code-discipline`'s U4 judgment call — this
   skill only demands that the boundary type exists.
2. **The OpenAPI document is the single source of truth clients generate from.**
   `react-frontend-discipline` §3.6 generates the front end's TypeScript types and client
   from your OpenAPI document. Anything wrong or missing in the document is a lie told to
   every consumer. A CI drift check (§6.3) makes the document law instead of decoration.
3. **The contract can only be changed through the taxonomy in §2.** "It's just a rename"
   does not exist on the API surface.

#### 1.1 PRE-SHAPE CHECKLIST — run BEFORE writing any DTO or endpoint

Every row cites the section that owns the rule; a "no" without written evidence is a
finding, not a style choice.

| # | Check | Owner |
|---|---|---|
| 1 | The type going on the wire exists ONLY for the wire — not an EF entity or domain type | §1 rule 1 |
| 2 | The diff is classified against the breaking-change table: which row, which class, and can the §6.3 OpenAPI diff even see it? | §2 |
| 3 | Every moment-in-time field is `DateTimeOffset`; calendar dates are `DateOnly`; zero `DateTime` in the DTO | §3.3 |
| 4 | Enums cross the wire as strings — global converter configured (BOTH configs in a mixed controllers+minimal repo) | §3.2 |
| 5 | Null handling matches the API-wide written policy (emitted `T \| null` vs omitted `t?:`) | §3.4 |
| 6 | Route: plural noun, no verb, ≤1 nesting level, parameters constrained (`{id:int}`) | §5.3 |
| 7 | Status codes per the §5.2 table; non-obvious ones declared so they enter the OpenAPI document | §5.2 |
| 8 | Every non-2xx this endpoint can produce comes out of the ProblemDetails pipeline — no hand-rolled envelope, no catch-and-200 | §4 |
| 9 | Collection responses are a paginated envelope from day one, never a bare array | §5.4 |

**POST-SHAPE — before declaring done:**

- [ ] curl ONE invalid request and see ValidationProblemDetails 400 — validated DTOs must
      be `public` or minimal-API validation silently does not run (§4.3).
- [ ] curl the failure paths with `ASPNETCORE_ENVIRONMENT=Production` — no stack, no
      exception text, `application/problem+json` (§4.1–4.2).
- [ ] Regenerate and commit the OpenAPI document; read ITS diff as the contract review
      surface (§6.3). A document diff you didn't expect = you broke §2 somewhere.

### 2. API breaking-change taxonomy

Classify every API-surface diff against this table BEFORE writing code. "Class" is the
`change-control` class; "OpenAPI diff?" says whether a mechanical diff of the generated
document (§6.3) can catch it — the rows where it can't are the dangerous ones. The Class
column assumes out-of-repo consumers; under §1's in-repo/lockstep condition read C as B
(rows 7 and 10 stay maximally suspicious — semantic breaks hurt in-repo consumers just as
silently).

| # | Change | What breaks, concretely | Class | OpenAPI diff? |
|---|---|---|---|---|
| 1 | **Add optional/nullable response field** | Nothing, for tolerant readers. Consumers using strict deserialization (fail-on-unknown-member settings, some generated clients) reject the payload | B with a written tolerant-reader policy; C without one | Yes |
| 2 | **Add required request field** | Every existing client's requests start failing validation (400) | C | Yes |
| 3 | **Remove or rename a field** | Tolerant readers get `undefined`/default silently — often a *silent data bug*, worse than a crash; strict readers throw | C | Yes |
| 4 | **Widen a type** (int → decimal, non-null → nullable in a response) | Consumers typed to the narrow shape (TS `number` vs `number \| null`) break or mishandle | C | Yes |
| 5 | **Narrow a type / tighten validation** (accept less than before) | Requests that used to succeed now 400 | C | Partly — only if the constraint surfaces in the schema; runtime-only validation (FluentValidation rules, handler checks) is invisible |
| 6 | **Change nullability** of an existing field | Same as 4/5 depending on direction | C | Yes — the .NET 10 generator emits `"type": ["null","string"]` for nullable properties [verified] |
| 7 | **Semantic change without shape change** (field meaning, units, timezone assumption, ordering guarantee, side effects) | Everything type-checks; behavior is silently wrong. The worst row | C — and **invisible to all tooling**: requires written changelog + direct consumer notice; no diff can catch it | **No** |
| 8 | **Route or verb change** | 404/405 for every existing caller | C | Yes |
| 9 | **Status-code change** (200→204, 400→409, new 4xx) | Client branching logic (`if (res.status === 409)`) breaks; 204 has no body where one was expected | C | Yes, if response codes are declared on the endpoint; undeclared codes never made it into the document — see §5.2 |
| 10 | **Enum value ADDITION** | Breaks exhaustive TS `switch` statements the moment the new value arrives (the `react-frontend-discipline` seam), and strict enum deserializers. Safe only with a written open-enum policy ("clients must handle unknown values") | C by default | Only if enums are strings — a numeric enum appears in the document as bare `{"type": "integer"}` with **no member names at all** [verified], so even the diff is blind |

Row 10's verified evidence is the reason for §3.2's enum-as-string rule: with numeric
enums, the contract document doesn't even know the values exist.

Detection method summary: rows 1–4, 6, 8, 9 → the §6.3 CI OpenAPI diff catches them
mechanically. Rows 5, 7, 10-numeric → tooling-blind; they ride on review discipline and
the class-C consumer-notification gate. That asymmetry is why semantic changes (row 7)
deserve the most suspicion in review, not the least.

### 3. Serialization discipline

Everything in this section was **observed on the wire** (curl against ASP.NET Core
10.0.9, 2026-07-08), not recalled. Both minimal APIs and MVC controllers use
System.Text.Json "web defaults" (camelCase, case-insensitive binding) [verified on both
templates].

#### 3.1 Property-name casing — stated once

C# `PascalCase` properties serialize as **camelCase**. Observed: `TwoWordName` →
`"twoWordName"`, and the pathological `ALLCapsCASING` → `"allCapsCASING"` [verified].
Binding is case-insensitive on input [verified: camelCase request bodies bound to
PascalCase records]. Policy: never fight this with per-property `[JsonPropertyName]`
sprinkles; the global default IS the convention. A `[JsonPropertyName]` is reserved for
matching an external contract you don't own, with a comment saying whose.

Trap [verified]: `ValidationProblemDetails.errors` keys do NOT follow the body-property
convention — the captured 400 body (§4.2) shows `"errors":{"Quantity":[...],
"CustomerName":[...]}` in **PascalCase** while everything else is camelCase. TS clients
that index `errors` by their camelCase field names find nothing. (Key casing here follows
the model-binding name, not the JSON naming policy.)

#### 3.2 Enums: opt in to strings, globally

Default: enums serialize as **numbers** — observed `"enumDefault":1` [verified] — and the
OpenAPI schema for that enum is `{"type":"integer"}` with no member names [verified],
so generated TS clients get `number` and the contract is unreadable. Also observed:
POSTing the string `"Shipped"` into a numeric-enum field fails the request (400)
[verified] — the default is not lenient.

With `JsonStringEnumConverter` the same value serializes as `"status":"Shipped"`
[verified via `[JsonConverter(typeof(JsonStringEnumConverter))]` on the property].

**Rule: enum-as-string, configured once, globally** — per-property attributes drift.
Where to configure it (this is the one place serializer options live):

```csharp
// Minimal APIs — ConfigureHttpJsonOptions governs Map* endpoints:
builder.Services.ConfigureHttpJsonOptions(o =>
    o.SerializerOptions.Converters.Add(new JsonStringEnumConverter()));

// MVC controllers — AddJsonOptions governs controller responses:
builder.Services.AddControllers().AddJsonOptions(o =>
    o.JsonSerializerOptions.Converters.Add(new JsonStringEnumConverter()));
```

Both wirings [verified 2026-07-08]: with `ConfigureHttpJsonOptions` the minimal-API probe
flipped from `"enumDefault":1` to `"enumDefault":"Shipped"`, and with `AddJsonOptions`
the controller response emitted `"status":"Shipped"` — each observed on the wire. A repo
with BOTH controllers and minimal endpoints needs BOTH calls: they are separate option
objects. Bonus [verified]: with string enums the OpenAPI schema becomes
`{"enum":["Pending","Shipped","Cancelled"]}` — the member names finally exist in the
contract document. It is still a class-C change to add a value unless the open-enum
policy exists (§2 row 10).

#### 3.3 Moments in time: DateTimeOffset, not DateTime

Observed wire strings for the same clock time 14:30:00 [verified]:

| C# type / Kind | On the wire | Verdict |
|---|---|---|
| `DateTime`, `Kind=Utc` | `"2026-07-08T14:30:00Z"` | Unambiguous, but only if you *guarantee* Kind=Utc everywhere |
| `DateTime`, `Kind=Local` | `"2026-07-08T14:30:00+03:00"` | Offset is the **server machine's** timezone — the contract now depends on where you deploy |
| `DateTime`, `Kind=Unspecified` | `"2026-07-08T14:30:00"` | **No offset, no Z.** JavaScript's `new Date()` parses this as the *client's local time* (`react-frontend-discipline` §3.6) — every consumer in a different timezone reads a different instant |
| `DateTimeOffset` (+02:00) | `"2026-07-08T14:30:00+02:00"` | Always explicit, always unambiguous |
| `DateOnly` | `"2026-07-08"` | Correct for calendar dates (birthdays, due dates) — no time, no timezone lie |
| `TimeOnly` | `"14:30:00"` | Correct for wall-clock times |

The round-trip trap [verified]: POSTing `"2026-07-08T14:30:00"` (no offset) into a
`DateTime` property binds as `Kind=Unspecified` and re-serializes bare — the ambiguity is
*sticky*; nothing in the pipeline ever repairs it.

**Rules:**
- Anything that is a *moment in time* (created-at, expires-at, occurred-at) is
  `DateTimeOffset` on every DTO. It is the only type in the table that cannot emit an
  ambiguous string.
- Anything that is a *calendar date* with no time component is `DateOnly` → serializes
  `yyyy-MM-dd` [verified]. (Consumers must still format it as UTC/plain-date on the JS
  side — that trap is owned and documented by `react-frontend-discipline` §3.6.)
- `DateTime` in a DTO is a review finding. Entities may use what the data layer needs
  (`dotnet-ef-discipline`); the DTO boundary converts.

#### 3.4 Nulls: emitted, not omitted (know which your consumers assume)

Default: a null property is serialized as `"nullableString":null` [verified], not
dropped. The OpenAPI document declares it `"type":["null","string"]` [verified]. So by
default consumers see `T | null`, not an absent key. If you switch to
`JsonIgnoreCondition.WhenWritingNull`, the same field becomes *absent* — a different
contract: TS `t?: T` (optional) instead of `T | null`, and generated clients change shape
(labeled consumer-behavior fact: what a generator emits depends on the generator — check
the one your front end uses). Pick one policy for the whole API, write it down, and never
flip it casually — flipping it is a §2 row-6-adjacent change to every nullable field at
once. Write it down WHERE: the API-wide wire policies (casing, enum-as-string, null
emission, date types) are load-bearing decisions — record them as `architecture-contract`
entries (serialization/wire formats are its §3.2 highest-tier signal), with the §6.3
drift gate as the entry's Verify hook.

#### 3.5 DTO round-trip sanity

A C# `record` round-trips cleanly as a DTO [verified: full record POSTed and echoed
byte-consistent, camelCase both ways]. `decimal` preserved trailing zeros (`19.90` in,
`19.90` out) [verified]. Note the OpenAPI schema for `decimal` is
`{"type":["number","string"], "pattern":...}` [verified] — generated TS types may be
`number | string`; decide how your client generator handles money and record it (or put
money in integer minor units / string — a contract decision, route it through
`architecture-contract` if it outlives the diff).

### 4. Error contract — one shape for the whole API

**Rule: every non-2xx response body across the entire API is ProblemDetails (RFC 9457,
`application/problem+json`).** One shape means one client-side error handler, one
generated error type, one log correlation field. Mixed shapes mean every endpoint teaches
consumers a new failure dialect.

#### 4.1 What ASP.NET Core does with no wiring (observed)

| Situation | Development | Production |
|---|---|---|
| Unhandled exception, minimal API | **500, `text/plain`, full stack trace + exception message on the wire** — including anything sensitive in the message (observed: our planted fake connection string went straight to the client) [verified] | 500, **completely empty body** (`Content-Length: 0`) [verified] |
| Malformed request JSON, minimal API | 400, `text/plain`, full `BadHttpRequestException` + inner `JsonException` stack trace [verified] | 400, empty body [verified] |

Two failure modes, one per environment: Development *leaks* (never expose a Development
API publicly; never copy Dev error output into a contract test), Production is *mute*
(clients get nothing machine-readable to act on). Both are fixed by the same wiring:

#### 4.2 The standard wiring [verified end to end]

```csharp
builder.Services.AddProblemDetails();                          // IProblemDetailsService
builder.Services.AddExceptionHandler<GlobalExceptionHandler>();

var app = builder.Build();
app.UseExceptionHandler();   // no args — uses the registered IExceptionHandler chain
app.UseStatusCodePages();    // bodiless 4xx (404 route miss, binding 400) get ProblemDetails too
```

```csharp
internal sealed class GlobalExceptionHandler(IProblemDetailsService problemDetailsService)
    : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext, Exception exception, CancellationToken cancellationToken)
    {
        httpContext.Response.StatusCode = exception switch
        {
            // map only exceptions that ARE contract outcomes (e.g. a concurrency
            // conflict => 409); everything else is 500. Not-found should be a
            // returned 404, not an exception — see §4.4 trap 5
            _ => StatusCodes.Status500InternalServerError
        };
        return await problemDetailsService.TryWriteAsync(new ProblemDetailsContext
        {
            HttpContext = httpContext,
            ProblemDetails = new ProblemDetails
            {
                Status = httpContext.Response.StatusCode,
                Title = "An unexpected error occurred.",
                Extensions = { ["traceId"] = httpContext.TraceIdentifier }
            }
        });
    }
}
```

Captured Production wire output with this wiring [verified 2026-07-08]:

```
HTTP/1.1 500 Internal Server Error
Content-Type: application/problem+json

{"type":"https://tools.ietf.org/html/rfc9110#section-15.6.1",
 "title":"An unexpected error occurred.","status":500,
 "traceId":"00-748605edf6ec7cd94a280ca035077be3-34d51a9969dbf326-00"}
```

No exception type, no message, no stack — and the `traceId` (W3C trace context) lets
operators find the full exception in the server logs (`run-and-operate` owns where those
land). Unknown routes and binding 400s also became ProblemDetails
(`"title":"Not Found","status":404` / `"title":"Bad Request","status":400`) [verified via
`UseStatusCodePages` + `AddProblemDetails`].

#### 4.3 Validation errors = ValidationProblemDetails

`[ApiController]` controllers reject invalid models automatically before the action runs.
Captured 400 body for a request violating `[Required]` + `[Range(1,100)]` [verified]:

```
HTTP/1.1 400 Bad Request
Content-Type: application/problem+json; charset=utf-8

{"type":"https://tools.ietf.org/html/rfc9110#section-15.5.1",
 "title":"One or more validation errors occurred.","status":400,
 "errors":{"Quantity":["The field Quantity must be between 1 and 100."],
           "CustomerName":["The CustomerName field is required."]},
 "traceId":"00-b905b7fdc066413afe66ccd81c425ab7-0fdc9a05fe8009b2-00"}
```

That `errors` dictionary-of-arrays IS the validation contract; hand-rolled
`{ "message": ... }` validation responses fork the contract for no gain. Remember the
§3.1 trap: the keys are PascalCase.

Two validation traps caught live:
- **Record DTO + `[property:]` attributes = runtime 500** [verified]: on a positional
  record, `[property: Required]` compiles but MVC throws
  `InvalidOperationException: ... validation metadata must be associated with the
  constructor parameter` at request time. Put the attribute on the parameter:
  `public record CreateOrderRequest([Required] string? CustomerName, [Range(1,100)] int Quantity);`
  [verified working].
- **Minimal APIs did not historically run DataAnnotations at all. .NET 10's built-in
  validation works** [verified end to end 2026-07-08 on the stock template]: add ONE
  line, `builder.Services.AddValidation();` (in-box on net10.0 — no package reference
  needed). With it, an invalid body produced the same ValidationProblemDetails 400 as
  MVC (`"errors":{"Quantity":["The field Quantity must be between 1 and 100."]}`
  captured), for a record with the attribute on the positional parameter OR
  `[property:]`-targeted (both observed working — minimal APIs are more forgiving than
  MVC here), and for `[Range]` directly on an endpoint parameter (whose `errors` key was
  the camelCase parameter name `"quantity"` — note the inconsistency with PascalCase
  property keys). Then run one invalid request through the trap check below before
  trusting any of it.

**TRAP [verified 2026-07-08] — silent validation skip: a non-`public` DTO means
minimal-API validation does not run at all.**

- **Symptom**: an endpoint that "has validation" returns **201 Created for an invalid
  body** — no error, no warning.
- **Cause**: the validated DTO is not `public` — the default for top-level types in
  `Program.cs` is `internal`, and validation silently does not exist for non-`public`
  types. (Mechanism per docs: discovery is a compile-time source generator [docs]; the
  observed fact is the silent skip itself.)
- **Fix**: make every validated DTO `public` — observed: `public` alone flipped the same
  invalid request from 201 to the ValidationProblemDetails 400.
- **Tell**: a validated DTO declared with no access modifier in `Program.cs`; an
  endpoint whose logs show no 400s ever. Prove one invalid request with curl before
  declaring validation present.

  Asides: NuGet warns NU1510 "likely unnecessary" if you add an explicit
  `Microsoft.Extensions.Validation` reference [verified]; `[ValidatableType]` for
  non-endpoint types is experimental — compiling it is an ASP0029 *error* until
  suppressed [verified]; skip it. FluentValidation is the established third-party
  alternative [docs — package existence verified, see Provenance; wiring not executed
  here].

#### 4.4 Error-contract trap catalog

| Trap | Symptom | Cause | Fix | Tell |
|---|---|---|---|---|
| **Mixed error shapes** | Client error handling is a per-endpoint special case; front end shows "[object Object]" | Each endpoint hand-rolls `{ "error": ... }` / `{ "message": ... }` / bare string | One ProblemDetails pipeline (§4.2); delete local shapes endpoint-by-endpoint as a gated cleanup (class C/B per §1's consumer condition) | `git grep -n "new { error" -- '*.cs'` and friends (§Instantiate step 3) |
| **Catch-and-200** | Monitoring sees 100% success while users see failures; clients must parse bodies to detect errors | `try { ... } catch { return Ok(new { success = false }); }` | Status codes carry the outcome; 2xx means success, full stop. Map the failure to 4xx/5xx ProblemDetails | grep for `success = false`, `IsSuccess` properties on response DTOs |
| **Exception details in Production** | Stack traces / connection strings / SQL in client-visible bodies | Copying Dev behavior into a custom handler (`Detail = ex.ToString()`), or `app.UseDeveloperExceptionPage()` unconditionally | §4.2 wiring: generic title + traceId out; full exception to logs only | grep `ex.Message`, `ex.ToString()` inside anything that writes a response |
| **EF exceptions surfacing raw** | `DbUpdateException`/`SqlException` text reaches clients — schema and query details leak, and the client is coupled to your ORM | No exception boundary; data-layer exceptions treated as contract | Handler maps known conflict cases (unique violation → 409 ProblemDetails); everything else → generic 500. Entity/constraint naming stays server-side (`dotnet-ef-discipline`) | grep `DbUpdateException` in controllers; 500 bodies mentioning table names |
| **Throwing for expected outcomes** | 500s in logs for "order not found" | Domain uses exceptions as flow control for misses | Not-found is a *result* (404 return), not an exception; reserve the §4.2 handler for the unexpected | `KeyNotFoundException` thrown per-request in hot paths |

### 5. Endpoint discipline

#### 5.1 Controllers vs minimal APIs — the decision rule

Both are current, fully supported models in ASP.NET Core 10 [verified: `dotnet new
webapi` scaffolds minimal by default; `--use-controllers` scaffolds MVC]. The rule is the
same as `csharp-code-discipline`'s instantiation rule: **consistency beats preference** —
within one service, use the style the repo already uses; do not introduce the second
style inside a feature diff. For a new service (heuristic): minimal APIs are the template
default and are leaner for endpoint-shaped services; controllers still carry the most
batteries (model validation out of the box [verified §4.3], filters, conventions).
Whichever you pick, record it. A mixed repo needs BOTH serializer configs (§3.2) and both
styles reviewed against the same contract rules — the wire does not care which style
produced it.

#### 5.2 Status codes per operation

| Operation | Success | Notes and verified behavior |
|---|---|---|
| GET item | 200 | 404 (ProblemDetails) when absent — controller `NotFound()` under `[ApiController]` already emits `application/problem+json` [verified] |
| GET collection | 200 with empty array | Never 404 for "no results" — an empty list is a successful answer |
| POST create | **201 + `Location` header** | `CreatedAtAction(nameof(GetById), new { id }, dto)` → absolute URL Location [verified]; `TypedResults.Created($"/orders/{id}", dto)` → the URI you gave [verified]. A 200-with-body create loses the canonical-URL contract |
| POST action (non-create) | 200 with result / 202 accepted-for-async | Document which |
| PUT replace | 200 with body or 204 without | PUT is **full replace** and idempotent — same request twice, same end state. Partial update via PUT corrupts fields the client didn't send |
| PATCH partial | 200/204 | PATCH is the partial-update verb; body format (merge patch vs JSON Patch) is itself contract — declare it |
| DELETE | 204 (or 200 with a body if you return the deleted resource) | Idempotent from the consumer's view: second DELETE → 404 or 204, pick one and keep it |
| Any write conflict | 409 ProblemDetails | Duplicate key, concurrency token mismatch |
| Validation failure | 400 ValidationProblemDetails (§4.3) | |
| Not authenticated / not permitted | 401 / 403 | Emitted by the auth middleware; do not fake them from handlers |

Verb idempotency (safe to retry blind): GET, PUT, DELETE yes; POST no; PATCH not
guaranteed. Retry policies on the consumer side are built on this — breaking it (a POST
that's "basically a GET", a PUT that appends) is a §2 row-7 semantic break.

Declare non-obvious status codes on the endpoint (`[ProducesResponseType(...)]` /
`.Produces<T>(...)`) — undeclared codes never enter the OpenAPI document, which blinds
the §6.3 diff to row 9 of §2 [docs — attribute/extension names; the
document-only-knows-what-you-declare mechanism follows from §6.1's verified doc output].

#### 5.3 Route conventions (labeled convention — pick once, write it down)

- Plural nouns for collections: `/api/orders`, `/api/orders/{id}`. No verbs in routes
  (`/api/orders/create` → `POST /api/orders`); the HTTP method is the verb.
- Nesting depth limit (heuristic): one relationship level —
  `/api/orders/{id}/lines` is fine; three-deep paths encode your object graph into every
  consumer's URL builder. Cross-cutting lookups get their own top-level resource.
- Kebab-case multi-word segments (`/api/purchase-orders`); route casing is
  contract too.
- Route parameters constrained where cheap: `{id:int}` / `{id:guid}` turns garbage input
  into 404 before binding [docs — constraint syntax].

#### 5.4 Pagination and filtering (labeled convention)

Unbounded collection endpoints are future incidents (the day the table hits a million
rows, every client times out at once — and *fixing* it then is a contract-breaking
change, class per §1's consumer condition).
Convention to adopt from day one: query parameters `?page=1&pageSize=50` (server-enforced
max) or cursor-based `?after=<TOKEN>&limit=50` for feeds; the response is an envelope
DTO — `{"items":[...],"totalCount":123,"page":1,"pageSize":50}` — never a bare array,
because adding pagination metadata to a bare-array contract later is §2 row 3-shaped
surgery. Filtering via named query parameters (`?status=shipped`), not a query-language
string, until proven otherwise.

#### 5.5 Fail-closed authorization posture

Default-deny at the framework level, allow-list per endpoint — so a forgotten attribute
fails closed (401) instead of leaking data:

```csharp
builder.Services.AddAuthorization(options =>
{
    options.FallbackPolicy = new AuthorizationPolicyBuilder()
        .RequireAuthenticatedUser()
        .Build();   // applies to every endpoint with no explicit authorization metadata
});
```

Public endpoints then opt out explicitly with `[AllowAnonymous]` /
`.AllowAnonymous()` — greppable, reviewable, intentional. The wiring compiles and
enforces [verified 2026-07-08: with the FallbackPolicy added to the controllers template,
a previously-200 anonymous GET stopped succeeding]. Observed caveat [verified]: with a
FallbackPolicy but NO authentication scheme registered, the challenge throws —
500 `InvalidOperationException: No authenticationScheme was specified, and there was no
DefaultChallengeScheme found` — so the posture only produces clean 401s once a real
scheme exists ([docs] for scheme setup). The templates ship NO authentication at all
[verified: template `Program.cs`]; this posture is something you add, not something you
get. Everything deeper — token validation, providers, schemes — is out of scope per
When-NOT.

### 6. OpenAPI as artifact

#### 6.1 The built-in document [verified]

Both .NET 10 `webapi` templates reference exactly one package —
`Microsoft.AspNetCore.OpenApi` 10.0.9 — and wire `builder.Services.AddOpenApi()` +
`app.MapOpenApi()` inside `if (app.Environment.IsDevelopment())` [verified]. Observed:

- Document served at **`/openapi/v1.json`** in Development (200) [verified];
  `/openapi.json` and `/swagger/v1/swagger.json` are 404 [verified].
- In Production the endpoint is 404 [verified] — the template maps it Dev-only. Whether
  to expose it in other environments is a deliberate decision (internal APIs usually yes,
  public ones maybe not); don't discover it as a prod surprise either way.
- The generated document declares `"openapi": "3.1.1"` [verified] — OpenAPI 3.1. Check
  your client generator supports 3.1 before wiring codegen
  (`react-frontend-discipline` §3.6 lists the generator options).
- No UI is included. Swashbuckle (`Swashbuckle.AspNetCore`) — "Swagger" is the
  historical name of OpenAPI and survives as the brand of the browsable UI, which is why
  Step 4 greps both spellings — is the long-lived
  alternative/UI provider, still actively published [verified on nuget.org 2026-07-08:
  10.2.3] but **volatile** as a recommendation [docs: it was dropped from the template
  in the .NET 9 era]; if the repo needs a browsable UI, verify the current recommended
  package before adding one (re-verify command in Provenance).

#### 6.2 Generate the document at build time

Runtime-only documents can't gate CI. The mechanism [verified 2026-07-08]:

```sh
dotnet add package Microsoft.Extensions.ApiDescription.Server   # 10.0.9 at verification
dotnet build
# → emits obj/<PROJECT>.json (observed: obj/minapi.json, "openapi": "3.1.1",
#   identical path set to the runtime /openapi/v1.json document)
dotnet build -p:OpenApiDocumentsDirectory=<DOC-DIR>
# → redirects the output to a committable folder (observed: <DOC-DIR>/minapi.json)
```

Put `OpenApiDocumentsDirectory` in the csproj so every *compiling* build refreshes the
committed document (emission runs with compilation — an up-to-date incremental build
skips it [observed]; clean CI builds are unaffected). Alternative that always works: a
CI step that boots the API in Development and
curls `/openapi/v1.json` to a file [verified mechanism — that exact curl ran today].

#### 6.3 The CI drift gate — change-control made mechanical

Commit the generated document next to the code. CI regenerates it and diffs:

```sh
# regenerate (build-time mechanism per §6.2, or boot-and-curl), then:
git diff --exit-code -- <PATH-TO-COMMITTED-OPENAPI>.json
# non-zero exit = the API surface changed without the committed contract changing
```

A dirty diff fails the build. That failure IS the contract tripwire: the author must
regenerate, commit the document, and the *document diff in the PR* becomes the
contract-owner's review surface and the **input to** the consumer-impact analysis — the
drift failure *triggers* `change-control`'s gates for the class you assigned per §1/§2
(for class C: consumer-side compatibility evidence, rollback plan, announcement); a
reviewed document diff satisfies none of them by itself, and §2 rows 5, 7, and
numeric-enum row 10 never appear in it at all. (`react-frontend-discipline` runs the
same gate from the consuming side — the two gates meet in the middle.)

#### 6.4 Versioning: additive evolution first

- Default strategy: **evolve additively** (new optional fields, new endpoints) under a
  written tolerant-reader policy, and never repurpose an existing field (§2 row 7).
  Most internal APIs never need more than this.
- When a genuine break is unavoidable and consumers can't migrate in lockstep, version
  explicitly. The maintained package family is **`Asp.Versioning.Http`** (+
  `Asp.Versioning.Mvc` for controllers) [verified on nuget.org 2026-07-08: 10.0.0;
  volatile]; wiring (URL-segment vs header versioning, version sets) is [docs] — follow
  the package's current README. URL-segment versioning (`/api/v2/...`)
  is the most cache- and log-friendly convention (labeled convention).
- A new API version is a project-level decision with a deprecation window for the old
  one — route it through `architecture-contract` (ADR) and `change-control` (class C,
  announce gate), not through a lone PR.

## Worked example

**Illustrative example — all facts fictional.** Project "Tidewatch", endpoint: get a
mooring reservation. (Wire shapes below follow the [verified] serialization rules of §3;
the fictional parts are the project and data.)

**Done wrong** — the PR exposes the EF entity, uses `DateTime`, hand-rolls errors, and
returns 200 for everything:

```csharp
app.MapGet("/api/getReservation", async (int id, TidewatchDbContext db) =>
{
    try
    {
        var r = await db.Reservations.Include(x => x.Berth).FirstAsync(x => x.Id == id);
        return Results.Ok(r);                       // EF entity on the wire
    }
    catch (Exception ex)
    {
        return Results.Ok(new { error = ex.Message }); // catch-and-200
    }
});
```

Wire output, success — entity internals, numeric enum, ambiguous timestamp, cycle-prone
navigation:

```json
{"id":7,"berthId":3,"berth":{"id":3,"dockCode":"D-11","reservations":null},
 "status":2,"startsAt":"2026-07-08T14:30:00","rowVersion":"AAAAAAAAB9E="}
```

Wire output, "failure" — HTTP 200, so the front end's error path never runs and
monitoring sees success:

```json
{"error":"Sequence contains no matching elements"}
```

Four §2/§4 violations before any feature bug: `startsAt` is §3.3's Unspecified trap (a
Seattle browser and a Hamburg browser display different instants); `status:2` is
§3.2's unreadable enum; the entity shape means the next EF refactor is an accidental
contract break (class per §1); the error shape is trap 1 + 2 of §4.4. Verb in route,
too (§5.3).

**Done right:**

```csharp
public sealed record ReservationDto(
    int Id, string BerthCode, ReservationStatus Status, DateTimeOffset StartsAt);

app.MapGet("/api/reservations/{id:int}", async Task<Results<Ok<ReservationDto>, NotFound>>
    (int id, TidewatchDbContext db) =>
{
    var dto = await db.Reservations
        .Where(r => r.Id == id)
        .Select(r => new ReservationDto(r.Id, r.Berth.Code, r.Status, r.StartsAt))
        .FirstOrDefaultAsync();
    return dto is null ? TypedResults.NotFound() : TypedResults.Ok(dto);
});
```

Wire output, success (enum-as-string configured globally per §3.2):

```json
{"id":7,"berthCode":"D-11","status":"Confirmed","startsAt":"2026-07-08T14:30:00+02:00"}
```

Wire output, absent — 404 with the API-wide shape (bodiless `NotFound()` upgraded by
`UseStatusCodePages` + `AddProblemDetails`; captured for route-miss 404 — §4.2; the same
mechanism applies to handler-returned bodiless 404s, not separately captured):

```json
{"type":"https://tools.ietf.org/html/rfc9110#section-15.5.5","title":"Not Found",
 "status":404,"traceId":"00-…-00"}
```

Unhandled exceptions now surface as the §4.2 generic 500 ProblemDetails; the typed
`Results<Ok<…>, NotFound>` return puts both status codes into the OpenAPI document, so
the generated TS client knows `404` is a possible outcome — the whole change is visible
in the §6.3 document diff, which is what the contract-owner reviews.

## Instantiate for your project

Produce `.claude/skills/<PROJECT>-api-discipline/SKILL.md`. Executable by a Sonnet-class
model unaided. Governing rule (same as siblings): **the instantiated skill records the
repo's CURRENT conventions as law — consistency beats preference**; divergences from this
skill's defaults are flagged as proposed gated changes (class per §2), never fixed
silently inside feature diffs.

### Step 0 — Find the API surface(s)

```sh
git grep -ln "WebApplication.CreateBuilder" -- '*.cs'          # entry points
git grep -ln "AddControllers\|MapControllers" -- '*.cs'        # controller style in use?
git grep -c "Map\(Get\|Post\|Put\|Patch\|Delete\)" -- '*.cs'   # minimal-API endpoints
git grep -ln "\[ApiController\]" -- '*.cs'                     # attribute-routed controllers
git grep -ln "AddGrpc\|MapGrpcService\|GraphQL" -- '*.cs'      # OUT OF SCOPE surfaces
```

gRPC/GraphQL hits → note "non-REST surface present, out of this skill's scope" and stop
for those surfaces. Multiple REST services → one instantiated section per service.

### Step 1 — Serializer configuration in force

```sh
git grep -n "ConfigureHttpJsonOptions\|AddJsonOptions\|JsonSerializerOptions" -- '*.cs'
git grep -n "JsonStringEnumConverter\|JsonNamingPolicy\|JsonIgnoreCondition" -- '*.cs'
git grep -n "JsonPropertyName" -- '*.cs' | head -30    # per-property overrides = contract debt list
git grep -nE "public .*(DateTime)[^O]" -- '*Dto*.cs' '*Request*.cs' '*Response*.cs'  # §3.3 audit
git grep -nE "public .*(DateTime)[^O]" -- '*.cs'   # fallback pass (noisier) — inline DTOs in Program.cs are in scope too
```

Record: enum policy (number vs string), null policy, casing overrides — each with
file:line. No config found → web defaults are in force; record the §3.1/§3.2/§3.4
defaults as the current contract (they are law now, whether chosen or not).

### Step 2 — DTO boundary audit

```sh
git grep -ln "DbSet<" -- '*.cs'                                # entity types
# then for each entity name E:
git grep -n "Ok(.*\bE\b\|Results\..*\bE\b\|ActionResult<E>" -- '*.cs'
```

Every entity type appearing in an endpoint return is a §1-rule-1 violation: list them as
findings with file:line. Fixing one is a gated contract change — class C/B per §1's
consumer condition (the wire shape changes) — flag, don't fix inline.

### Step 3 — Error shapes actually in force

```sh
git grep -n "AddProblemDetails\|UseExceptionHandler\|IExceptionHandler\|UseStatusCodePages" -- '*.cs'
git grep -nE "new \{ *(error|message|success)" -- '*.cs'       # custom envelopes
git grep -n "UseDeveloperExceptionPage" -- '*.cs'              # unconditional use = §4.4 trap 3
```

Then OBSERVE, don't infer: run the API locally (`run-and-operate` for how), curl a
missing route, an invalid body, and (if a debug endpoint exists) a thrown exception, in
both `ASPNETCORE_ENVIRONMENT=Development` and `Production`. Paste the captured bodies
into the instantiated skill — the §4.1 table for THIS repo. Do not write an error-shape
row you have not curled. If no exception path can be triggered safely, write
"unhandled-exception shape UNOBSERVED" in the instantiated §4.1 table — never infer it.

### Step 4 — OpenAPI and drift status

```sh
git grep -n "AddOpenApi\|MapOpenApi\|SwaggerGen\|UseSwagger" -- '*.cs'
git grep -n "OpenApi\|Swashbuckle\|ApiDescription.Server" -- '*.csproj' 'Directory.Packages.props'
git ls-files | grep -iE "openapi.*\.(json|yaml)|swagger.*\.json"   # committed document?
# CI drift gate present?
git grep -n "openapi" -- '<CI-CONFIG>'
```

Outcomes: (a) document + CI gate exist → record the command and the document path;
(b) document generated but never committed/diffed → the gap IS the finding; propose §6.3
as a class-B pipeline change; (c) **no OpenAPI setup at all → that IS the finding** — the
front end is hand-maintaining types against an undocumented contract
(`react-frontend-discipline` §3.6's top migration risk); it becomes the instantiated
skill's first recommendation, sized per `change-control`.

### Step 5 — Versioning and auth posture

```sh
git grep -n "Asp.Versioning\|ApiVersion" -- '*.cs' '*.csproj'
git grep -n "FallbackPolicy\|RequireAuthorization\|\[Authorize\]\|AllowAnonymous" -- '*.cs'
```

Record the incumbent versioning strategy (or "additive-only, no policy written" — a gap).
Count `[AllowAnonymous]` vs `[Authorize]`: attribute-per-endpoint with no fallback policy
= fail-open posture; flag per §5.5, propose as a gated change (fail-closed flips can
break legitimate anonymous consumers — class C/B per §1's consumer condition).

### Step 6 — Fill the skeleton

```markdown
---
name: <PROJECT>-api-discipline
description: <triggers naming this repo's services, DTO conventions, and error contract>
---
# <PROJECT> — API Surface Discipline
## Surface map                 # services, style (minimal/controllers), endpoint counts (Step 0)
## Serialization law           # enum/null/casing/date policy in force, file:line (Step 1)
## DTO boundary findings       # entities-on-the-wire list, each a flagged C/B fix per §1 (Step 2)
## Error contract as observed  # captured curl bodies Dev + Prod; the wiring in force (Step 3)
## OpenAPI status              # document path, generation command, drift gate or its absence (Step 4)
## Versioning + auth posture   # incumbent strategy; fallback policy present? (Step 5)
## Known gaps                  # every divergence from aspnet-api-discipline defaults, as PROPOSED gated changes
## Provenance                  # date, SDK/ASP.NET versions, commands run, captured outputs
```

Evidence gates: no serialization-law row without file:line or a captured wire sample; no
error-shape claim without a curl capture from THIS repo; no "we version with X" from a
README — only from packages/code; no Known-gap without its change-control class.

## Provenance and maintenance

- Authored 2026-07-08 against no specific project (authoring wave dated 2026-07-06).
  Stack facts verified by execution: **.NET SDK 10.0.301, ASP.NET Core 10.0.9**
  (`dotnet new webapi` minimal + `--use-controllers` templates, net10.0,
  `Microsoft.AspNetCore.OpenApi` 10.0.9), Kestrel on Windows 11, wire output captured
  with curl 8.17.0.
- **[verified] by execution 2026-07-08** (probe endpoints on the scaffolded apps; every
  quoted wire string is a captured response): OpenAPI at `/openapi/v1.json` in
  Development (200; `openapi: 3.1.1`) and 404 in Production; camelCase casing incl.
  `ALLCapsCASING`→`allCapsCASING`; DateTime Local/Utc/Unspecified, DateTimeOffset,
  DateOnly, TimeOnly wire strings and the bare-string round-trip stickiness; enum default
  number + `{"type":"integer"}` schema + string-into-numeric-enum 400 +
  `JsonStringEnumConverter` output; nulls emitted; decimal round-trip and its
  `["number","string"]` schema; unknown-field tolerance; Dev 500/400 stack-trace leak;
  Prod empty 500/400; full §4.2 wiring producing `application/problem+json` for 500/404/
  400 in Production with no leak; `[ApiController]` automatic ValidationProblemDetails
  (PascalCase `errors` keys); record-`[property:]`-validation runtime 500 and its
  parameter-target fix; `CreatedAtAction` and `TypedResults.Created` 201+Location;
  controller `NotFound()` auto-ProblemDetails.
- **[verified] Stage-4 additions, same date/SDK**: `ConfigureHttpJsonOptions` and
  `AddJsonOptions` enum-converter wiring, each observed flipping the wire output (§3.2);
  string-enum OpenAPI schema `{"enum":[...]}`; .NET 10 minimal-API validation end to end
  — in-box `AddValidation()`, ValidationProblemDetails 400 for record (param- and
  property-targeted attributes) and endpoint-parameter attributes, the internal-DTO
  silent skip (201-for-invalid observed, flipped to 400 by `public` alone), NU1510 on an
  explicit `Microsoft.Extensions.Validation` reference, ASP0029 error on
  `[ValidatableType]` (§4.3); FallbackPolicy compile + enforcement + the
  no-auth-scheme 500 (§5.5); `Microsoft.Extensions.ApiDescription.Server` build-time
  document at `obj/<PROJECT>.json` and `OpenApiDocumentsDirectory` redirect (§6.2).
- **Package versions from `dotnet package search <ID> --exact-match` against nuget.org,
  2026-07-08 — ALL VOLATILE**: Asp.Versioning.Http 10.0.0; Swashbuckle.AspNetCore
  10.2.3; FluentValidation 12.1.1; FluentValidation.AspNetCore 11.3.1;
  Microsoft.Extensions.ApiDescription.Server 10.0.9; Microsoft.Extensions.Validation
  10.0.9.
- **[docs] — NOT executed here; verify on first use**:
  `[ProducesResponseType]`/`.Produces` document effects (§5.2); route-constraint syntax
  (§5.3); authentication-scheme setup for clean 401s under FallbackPolicy (§5.5);
  `Asp.Versioning.Http` wiring (§6.4); FluentValidation wiring; Swashbuckle's
  current-recommendation status; `JsonIgnoreCondition.WhenWritingNull` consumer-side
  effects (§3.4 — generator-dependent).
- Volatile parts, each with a copy-paste re-verify one-liner:
  - Template shape and OpenAPI path (changed across recent majors):
    `dotnet new webapi -o /tmp/probe && grep -rn "MapOpenApi" /tmp/probe`
  - Package versions (checked via `dotnet package search <ID> --exact-match`, run these
    before quoting a version):
    `dotnet package search Asp.Versioning.Http --exact-match`
    `dotnet package search Swashbuckle.AspNetCore --exact-match`
    `dotnet package search FluentValidation.AspNetCore --exact-match`
    `dotnet package search Microsoft.Extensions.ApiDescription.Server --exact-match`
  - Minimal-API validation status: scaffold a probe, add a `[Range]` DTO +
    `builder.Services.AddValidation()`, POST an invalid body:
    `curl -s -i -X POST http://localhost:<PORT>/<EP> -H "Content-Type: application/json" -d '{"quantity":0}'`
  - OpenAPI document version + path: `curl -s http://localhost:<PORT>/openapi/v1.json | head -c 200`
  - RFC status (9457 obsoletes 7807 — stable, but if citing formally; verified output
    `Obsoletes: 7807`, 2026-07-09):
    `curl -s https://www.rfc-editor.org/rfc/rfc9457.txt | grep -i "^Obsoletes"`
- Serialization/wire doctrine (§3) tracks System.Text.Json web defaults and ages slowly;
  the fastest-rotting sections are §6.1 (tooling/template) and every package name.
  Heuristics are labeled inline (nesting depth, pagination convention, new-service style
  choice); none are measurements.
- Instantiated copies must add their own provenance: date, SDK/runtime versions, the
  Step-3 captured error bodies, and file:line citations behind every law/finding row.
