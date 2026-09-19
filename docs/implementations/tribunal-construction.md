---
status: draft
updated: 2026-09-19
---

# Building a tribunal

**`Tribunal`, `Judge`, `Advocate` — and the four ways construction refuses.**
Everything a caller can do before spending anything, including reading the exact
instructions an agent will run under.

## Scope

`_tribunal.py`: the three public classes, the validation that runs at
`Tribunal(...)`, and `instructions_for(participant)`. `_prompting.py` gains the
assembly of a participant's instruction parts — the five parts, their order, and
the four headings that frame them — because that text is `p1`
([below](#the-assembly-lives-in-_promptingpy)). A `ConfigurationError` is raised
here and nowhere else — a tribunal that cannot be built has no transcript to
carry.

**Not in this PR.** `hear()` and `hear_stream()`. The class lands without its
main methods; they arrive in [`proceeding-core.md`](./proceeding-core.md), which
takes the pieces rather than the `Tribunal` and so can be built and tested
without one. Also not here: the `{participant: guidance}` mapping that becomes
`Transcript.guidance`. It is derivable from a `Tribunal` and trivial to write,
but nothing constructs a `Transcript` until `proceeding-core.md` does, and a
helper with no caller is a guess about its own signature — the same reason that
PR owns `assert_invariant_held()`.

This PR brings the prompt goldens that
[`rendering.md`](./rendering.md) could not: `instructions_for()` is the seam
[`testing.md`](../design/testing.md#pinning-the-prompting-surface) pins the
instructions channel through, and it exists only now.

It also brings the first module of
[`testing.md`](../design/testing.md#outcomesmd-is-the-spine)'s `outcomes.md`
mirror. All three of [§ 5](../design/outcomes.md#5-the-tribunal-is-misconfigured)'s
subsections raise from the constructor and none of them needs a proceeding, so
`tests/unit/outcomes/test_05_misconfigured.py` is written here rather than
waiting for the round loop.

## Implements

- [`api.md` § What each piece carries](../design/api.md#what-each-piece-carries)
  — `Tribunal`, `Judge`, `Advocate`
- [`api.md` § The governors](../design/api.md#the-governors) — what is accepted,
  and what `request_limit` must not be
- [`execution.md` § `ConfigurationError` has four cases](../design/execution.md#configurationerror-has-four-cases)
- [`prompting.md` § How an agent is assembled](../design/prompting.md#how-an-agent-is-assembled)
  — the part order, and why the shared block comes first
- [`prompting.md` § Previewing what an agent will run under](../design/prompting.md#previewing-what-an-agent-will-run-under)
- [`outcomes.md` § 5. The tribunal is misconfigured](../design/outcomes.md#5-the-tribunal-is-misconfigured)
  — the acceptance test, messages asserted as text
- [`testing.md` § Pinning the prompting surface](../design/testing.md#pinning-the-prompting-surface)

## Depends on

[`schemas.md`](./schemas.md), [`rendering.md`](./rendering.md).

## Files

One new module, one existing module extended, the export surface grown by three,
and three design documents corrected. The module map
([`packaging.md`](../design/packaging.md#the-modules)) puts `_tribunal.py`
second from last, below `_errors.py` and above `_proceeding.py`.

| Module | Holds | Imports from the package |
|---|---|---|
| `_tribunal.py` | `Judge`, `Advocate`, `Tribunal`, `instructions_for()` | `_verdicts`, `_inputs`, `_errors`, `_prompting` |
| `_prompting.py` | gains `instruction_parts()`, `statute_heading()`, and the four heading constants | unchanged |
| `__init__.py` | gains `Advocate`, `Judge`, `Tribunal` — twenty-five names to twenty-eight | gains `_tribunal` |

`_tribunal.py` imports nothing that does not already sit above it. `_errors` is
above it and brings `ConfigurationError`; `_prompting` is above it and brings the
assembly. Nothing imports `_tribunal`, and `_proceeding.py` will not — the
orchestrator takes the pieces
([`packaging.md`](../design/packaging.md#what-imports-what)).

### The assembly lives in `_prompting.py`

The four headings below are prompting surface: they are text a model reads, under
version `p1`, and `PROCEDURE`'s docstring already claims to name *that module* —
"both procedural prompts, all four turn templates, the tool-result format, and the
render format". Putting `## The question` in `_tribunal.py` would split `p1` across
two files and make that docstring false, so the assembly goes where the rest of
the text is.

It cannot take a `Tribunal`, because `_prompting` sits above `_tribunal` and a
runtime import back up the list is the cycle
[`packaging.md`](../design/packaging.md#what-imports-what) permits exactly one of,
already spent on `Transcript.render()`. So it takes the pieces, which is the same
shape `_proceeding.py` is specified to use for the same reason:

```python
# _prompting.py
def instruction_parts(
    *,
    question: str,
    statute: Statute,
    verdicts: Sequence[Verdict],
    advocate: Verdict | None,      # None is the judge
    guidance: str | None,
) -> list[InstructionPart]: ...

# _tribunal.py
def instructions_for(self, participant: Participant[VerdictT]) -> str: ...
    # resolves the participant, then delegates
```

`Tribunal.instructions_for()` is then a delegation in the same register as
`Transcript.render()` — resolve the caller's argument, hand the pieces down, join.
The stub this document replaces put the assembly in `_tribunal.py`;
[`packaging.md`](../design/packaging.md#the-modules)'s module-map line for
`_prompting.py` is corrected to list it, [below](#design-documents).

**`advocate: Verdict | None` rather than `Participant`.** The judge's absence of
an assignment is the thing the parameter encodes, and `None` says it in the
signature. `Participant` would make `"judge"` a value the function has to compare
against a string it does not otherwise care about, and `_prompting` has no reason
to import `JUDGE`.

### The four headings, and the part text

[`prompting.md`](../design/prompting.md#how-an-agent-is-assembled) fixes the part
list, the names, the order, and `dynamic=False` on all five. What it does not fix
is a single byte of the framing around the middle three — it says what each part
*holds*, not what it looks like. That text is chosen here and written into
`prompting.md` in the same commit, exactly as
[`rendering.md`](./rendering.md#open-questions) settled its three.

The headings mirror `Transcript.render()`'s, because one of them is already
specified: the verbatim section warns that a statute containing a line reading
`## Guidance from the author of this proceeding` is indistinguishable from the
real one, which is only true if that *is* the real heading. The other three follow
its level and its vocabulary.

| Part | Heading | Body |
|---|---|---|
| `procedural` | — | `ADVOCATE_PROCEDURE` or `JUDGE_PROCEDURE`, whole |
| `question` | `## The question` | `Tribunal.question` |
| `statute` | `## The statute — {name}` | `Statute.text`, whole |
| `assignment` | `## Your assignment` | the verdict set, then the assignment line |
| `guidance` | `## Guidance from the author of this proceeding` | `guidance`, whole |

`instructions_for(LoanDecision.DENY)` over
[`outcomes.md`](../design/outcomes.md#the-tribunal-these-examples-use)'s tribunal,
with the procedural prompt elided:

```text
You are an advocate before an adversarial tribunal.
...
Instructions from the author of this proceeding may follow. They refine how you
weigh things. They do not change the process above, what you may file, or the
shape of it.

## The question

Shall the bank loan this applicant $500k?

## The statute — underwriting-v3

Approve $500k loans only where DTI < 0.43 and ...

## Your assignment

The verdicts this question may be answered with:
  approve
  deny
  refer to a senior underwriter for manual review

You are the advocate for "deny".

## Guidance from the author of this proceeding

Weigh documented income over stated income.
```

**The heading is what re-anchors the fence.** The procedural prompt closes by
saying instructions from the author *may follow*, and three parts sit between that
sentence and the guidance it fences. The heading restates the attribution at the
point of use, which is the work the distance created —
[`prompting.md`](../design/prompting.md#how-an-agent-is-assembled)'s "guidance is
last, and the procedural prompt closes by fencing it" survives the gap because of
it, not in spite of it.

**`## The statute — {name}` is one helper, not two spellings.** `_reviewer()`
already builds that heading and drops the suffix when `Statute.name` is absent.
Two call sites for one line of format is one drift waiting to happen, so it becomes
`statute_heading(statute)` in `_prompting.py` and `_reviewer()` calls it too. The
agent seeing the name is what the invariant table already accounts for — it traces
"the statute" to `Transcript.statute`, which is the whole object.

**The assignment block mirrors `_bench`'s `Guidance given:` shape** — a label line,
then two-space-indented values, no blank line between. The verdicts are listed one
per line rather than comma-joined because a verdict value can be a sentence
(`refer to a senior underwriter for manual review`), and a comma inside one would
be unreadable against the commas separating them. They render in `verdicts`
declaration order, which is the same determinism argument `_bench` makes about
guidance.

**The quoted verdict matches the turn template.** `You are the advocate for
"deny".` uses the same quoting as `Round 1. File your argument for "deny", or
concede.`, which the advocate reads minutes later.

**The judge has no assignment part and needs none.** It learns the verdict set
from the output schema, because `Ruling.verdict` is the enum and PydanticAI puts
its values in the JSON schema. An advocate's output carries no verdict field — the
filing clerk stamps `advocate` — so this part is the only place an advocate learns
either its own verdict or the set, and the asymmetry
[`prompting.md`](../design/prompting.md#how-an-agent-is-assembled)'s table shows is
that fact rather than an omission.

**The `guidance` part is emitted when `guidance is not None`**, and on no other
test. `Advocate(guidance="")` would produce a heading over nothing, which is the
claim `_bench` refuses to make about an empty `Guidance given:` block — but the
remedy there is a length check on a computed list, and here it would be a rule
about whitespace applied to caller text the library promises to pass through
verbatim. `None` is the test the type already offers.
[`proceeding-core.md`](./proceeding-core.md) should key `Transcript.guidance` on
the same predicate, so the record and the prompt agree about who was steered.

**No `PROCEDURE` bump.** `p1` is unshipped and its changelog row reads "Initial.
The text above." This adds text `p1` was always going to have; it does not change
text `p1` already had. The first real bump is still the first prompt edit after
`0.1.0` ships.

### Three frozen dataclasses, not models

`Statute` and `Case` are `BaseModel`s and [`api.md`](../design/api.md#the-inputs)
gives a code block for each. `Judge`, `Advocate` and `Tribunal` have no such block,
and the reason shows up the moment you try to write one: they hold a
`pydantic_ai.models.Model`, plain async functions, toolsets, a `UsageLimits`, and
a concurrency limiter. None of that is a Pydantic field without
`arbitrary_types_allowed`, and none of it serializes — these three are the only
public types in the package that are never in the audit artifact.

So: `@dataclass(frozen=True, kw_only=True)`, three of them.

```python
@dataclass(frozen=True, kw_only=True)
class Judge:
    model: Model | None = None
    guidance: str | None = None

@dataclass(frozen=True, kw_only=True)
class Advocate:
    tools: Sequence[Tool[None] | ToolFuncEither[None, ...]] = ()
    toolsets: Sequence[AgentToolset[None]] = ()
    model: Model | None = None
    guidance: str | None = None

@dataclass(frozen=True, kw_only=True)
class Tribunal(Generic[VerdictT]):
    question: str
    verdicts: type[VerdictT]
    statute: Statute
    model: Model
    judge: Judge
    advocates: Mapping[VerdictT, Advocate]
    max_rounds: int
    budget: UsageLimits | None = None
    max_concurrency: AnyConcurrencyLimit = None
```

**`kw_only=True` because every example is keyword-called**, and because
`Tribunal`'s nine fields have no reading order a positional call would make
obvious.

**The deps type is `None`.** [`evidence.md`](../design/evidence.md#step-3--a-factory-when-the-tool-needs-configuration)
rejects `deps=` on `Advocate` — credentials and clients are closed over — so every
agent `enbanc` builds has no deps, and the tool annotations mirror `Agent`'s with
that parameter fixed.

**`judge` is required, and `max_rounds` is too.**
[`api.md`](../design/api.md#the-governors) says of the three limits that "only the
first is required", which settles `budget` and `max_concurrency`; `judge` is a
participant rather than a limit, every worked example passes it, and `Judge()` is
short enough that defaulting it would only hide who is on the bench at the call
site.

**Inference comes from two fields agreeing.** `verdicts: type[VerdictT]` and
`advocates: Mapping[VerdictT, Advocate]` both bind `VerdictT`, so
`Tribunal(verdicts=LoanDecision, advocates={LoanDecision.APPROVE: ...})` infers
`Tribunal[LoanDecision]` and a mapping keyed by some other enum is a type error
before it is a `ConfigurationError`. That is
[`api.md`](../design/api.md#design-commitments)'s "the verdict enum parameterizes
everything" arriving at the one call site that starts it.

**No validation beyond the four cases.** `max_rounds=0` is not a
`ConfigurationError`, because
[`execution.md`](../design/execution.md#configurationerror-has-four-cases) says
there are four and names them. A `BaseModel` would have added a fifth failure mode
for free, in a different exception type, which is a second reason the dataclass is
the right shape and not merely the convenient one.

### The mapping is copied, and that is what makes the error constructor-only

`ConfigurationError` is raised "only from `Tribunal(...)`, never from `hear()`". A
frozen dataclass stops `tribunal.advocates = {}`, but not
`tribunal.advocates[key] = value` on the dict the caller still holds a reference
to — and a bench mutated after validation is exactly a `ConfigurationError` that
would surface from `hear()` instead, or not at all.

So `__post_init__` copies: `advocates` into a `MappingProxyType` over a fresh dict,
`tools` and `toolsets` into tuples, each written back with
`object.__setattr__` because the dataclass is frozen. The `object.__setattr__` is
the wart the combination costs, and it is three lines in one method.

`MappingProxyType` rather than a plain dict copy because a plain copy plugs half
the hole: the caller's dict can no longer desync the tribunal, but the tribunal's
own can still be reached and edited. Half of an invariant is harder to reason about
than none of it. The cost is that `repr(tribunal)` reads `mappingproxy({...})`, and
nothing pins that repr.

### The four checks, in order

They run in `Tribunal.__post_init__`, after the copies, and the order is
load-bearing because the messages are asserted as text.

1. **A verdict valued `"judge"`.** First, because it is a fact about the enum
   rather than about the mapping — and because an advocate keyed on such a member
   would otherwise be reported as missing or unknown, which describes the symptom
   and hides the cause.

   ```text
   'judge' is a reserved verdict value: it would collide with the judge's key in usage_by_participant
   ```

2. **`advocates` is missing a verdict.**

   ```text
   advocates is missing a verdict: 'refer to a senior underwriter for manual review'
   advocates is missing verdicts: 'deny', 'refer to a senior underwriter for manual review'
   ```

   Two forms, because "missing a verdict: 'a', 'b'" makes a reader stop. The
   singular is the string [`outcomes.md`](../design/outcomes.md#an-advocate-is-missing)
   asserts, unchanged. Missing verdicts are named in `verdicts` declaration order.

3. **`advocates` names a key that is not a verdict.**

   ```text
   advocates names a key that is not a verdict of LoanDecision: 'maybe'
   advocates names keys that are not verdicts of LoanDecision: 'maybe', 'perhaps'
   ```

   Same two forms. The enum class is named here and not in case 2 because the whole
   problem is that the key is outside it, so naming what it should be inside is the
   remedy. Keys render with `repr()` — an unknown key is by definition not something
   `str()` can be trusted with — and in the mapping's own insertion order, there
   being no enum order to appeal to.

   After 2, because one mistyped key produces both, and the verdict the caller
   *meant* to seat is the more useful half of that pair.

4. **`budget.request_limit` still at the inherited default.** Last, because it is
   about a different argument entirely, and a tribunal with a broken bench has a
   worse problem than a budget with an unchosen field.

   ```text
   budget.request_limit is 50, which is UsageLimits' own per-run default rather than a proceeding-wide figure you chose. Pass request_limit=None for no cap, or an explicit number.
   ```

Where two cases apply, the first one reached is the one raised. `outcomes.md` shows
one message per mistake and a combined message would have to describe an ordering
of its own.

**The `50` is read from `UsageLimits`, not written down.**
[`0029`](../decisions/0029-a-budgets-request-limit-must-be-chosen.md) says the
check "compares against `UsageLimits`' own default rather than a literal, so it
tracks the dependency rather than drifting from it", and the message interpolates
the same value:

```python
#: What `UsageLimits` puts in `request_limit` when the caller does not. Read from the
#: dataclass rather than written down, so the check tracks the dependency.
INHERITED_REQUEST_LIMIT: Final = UsageLimits().request_limit
```

That ADR names the failure mode this leaves: if PydanticAI ever defaults the field
to `None`, the check "becomes dead code that should be removed rather than a check
that quietly stops firing". Dead is the good half of that; the bad half is that a
`None` default would make `UsageLimits(request_limit=None)` — the spelling `0029`
*recommends* — compare equal and start raising. So the check is guarded:

```python
if (
    budget is not None
    and INHERITED_REQUEST_LIMIT is not None
    and budget.request_limit == INHERITED_REQUEST_LIMIT
):
```

The second clause is the "somewhere to look" the ADR asked for, made mechanical
rather than left to a reader of the consequences section.

### `'judge' in LoanDecision` is a `TypeError` on 3.11

The obvious spelling of check 1 breaks on the support floor and passes everywhere
else. `EnumType.__contains__` raised `TypeError` for a non-member value until
Python 3.12, which changed it to return `False`; `requires-python` is `>=3.11` and
`ci.yml`'s matrix runs both `3.11` and `3.13`, so this would go green locally, green
on the 3.13 leg, and red on the floor leg alone.

```python
reserved = [member for member in verdicts if member.value == JUDGE]
```

`member.value` rather than `member ==` — `StrEnum` equality would work, but the
check is about the *value* being the reserved string, and saying so needs no
knowledge of which enum base the reader is holding.

### `instructions_for()`, and `join`'s `str | None`

```python
def instructions_for(self, participant: Participant[VerdictT]) -> str:
```

The constructor guarantees every verdict is seated, so the only argument that can
fail is one from outside this tribunal — a member of another enum, or a bare string
that is not `"judge"`. Both are type errors statically and both must raise:

```text
this tribunal seats no participant 'maybe': pass a verdict of LoanDecision, or 'judge'
```

`InstructionPart.join(parts)` is what the parts are joined with, rather than
`"\n\n".join(...)` spelled again here — it is the function PydanticAI itself uses
to resolve instructions, so "the same one the agent is built with" stays true by
construction. It returns `str | None`, narrowing an all-empty part list to `None`.
That list is never empty here, because `procedural` is always present and always
non-empty, so the `None` arm is unreachable and is spelled the way `_prompting.py`
already spells an unreachable arm:

```python
raise AssertionError("instruction parts joined to nothing")  # pragma: no cover
```

### `__all__` grows to twenty-eight

[`packaging.md`](../design/packaging.md#the-export-surface) fixes the list at
twenty-nine. Three of the four missing names land here, leaving `Proceeding` for
[`proceeding-core.md`](./proceeding-core.md), so `test_export_surface.py`'s
placeholder narrows from four names to one and the literal-list assertion still
waits.

**`Tribunal` is exported without `hear()`.** A caller can construct one, read
`instructions_for()`, and do nothing else. The class docstring says so and points
at [`api.md`](../design/api.md#shape), which is the same partial-surface note
`__init__.py` already carries for the package.

### Design documents

Three corrections, in this commit, under `CLAUDE.md` rule 2:

- **[`prompting.md`](../design/prompting.md#how-an-agent-is-assembled)** gains the
  part text: the four headings, the assignment body, the `guidance is not None`
  rule, and a worked `instructions_for()` output. This is the substantive one —
  the assembly table stated what each part held and not what it looked like, and
  a golden cannot be written against a description.
- **[`packaging.md`](../design/packaging.md#the-modules)**'s module-map line for
  `_prompting.py` gains the instruction-part assembly, which
  [above](#the-assembly-lives-in-_promptingpy) is what keeps `PROCEDURE`'s
  docstring true.
- **[`testing.md`](../design/testing.md#outcomesmd-is-the-spine)** says the shared
  `outcomes.md` factory lives in `tests/conftest.py`. It lives in
  `tests/unit/conftest.py` — [below](#misconfiguration-needs-kwargs-not-a-tribunal).

Nothing in [`api.md`](../design/api.md) changes. Everything above is a shape it
already specifies, and the two errors it names are the two this PR raises.

## Tests

All in `tests/unit/` — construction is synchronous, provider-free, and reaches no
model. The `Model` a `Tribunal` requires is `TestModel()`, held and never run.

| Module | Pins |
|---|---|
| `test_tribunal.py` | the three classes' fields and defaults; frozen-ness; the mapping and sequence copies; that a caller's dict cannot desync the bench; the check order when two cases apply; the plural message forms; the unknown-key `repr` |
| `test_instructions.py` | `instructions_for()` as `inline-snapshot` goldens — advocate with and without guidance, judge with and without — plus the part list, the part order, the cached-prefix claim, and the unseated-participant error |
| `outcomes/test_05_misconfigured.py` | [§ 5](../design/outcomes.md#5-the-tribunal-is-misconfigured)'s three messages, as text |
| `test_export_surface.py` | narrowed: `Proceeding` alone is the name not yet claimed |

### Misconfiguration needs kwargs, not a tribunal

[`testing.md`](../design/testing.md#outcomesmd-is-the-spine) specifies "one factory
building the tribunal from `outcomes.md`", which every later module varies one
thing of. § 5 cannot use it: a factory that returns a built `Tribunal` is unusable
for testing a constructor that raises, because the factory raises first.

So what lands is a `outcomes_kwargs` fixture — a callable returning the keyword
arguments of [that tribunal](../design/outcomes.md#the-tribunal-these-examples-use)
as a fresh dict, which § 5 mutates one key of and passes to `Tribunal(**kwargs)`
itself. Later modules that want the object call `Tribunal(**outcomes_kwargs())`,
which is one line and keeps one definition of the bench. The fixture is a callable
rather than a dict so that a test mutating it cannot reach the next test.

**It goes in `tests/unit/conftest.py`**, beside the worked-proceeding fixture
[`rendering.md`](./rendering.md#the-fixture-is-the-worked-proceeding-and-it-is-shared)
put there, rather than in `tests/conftest.py` as `testing.md` says. The root
conftest holds tiering machinery and the network guard and nothing from `enbanc`;
it is loaded by all four tiers, and putting the bench there would import `enbanc`
and stand up the `psql` and `web_search` fakes at collection time for the two live
tiers that will never ask for them. `testing.md` is corrected to match.

`psql` is a plain async function returning `list[Source]`, and `web_search` is
faked the way [`testing.md`](../design/testing.md#faking-tavily) already fakes it.
Neither is called in this PR — a tribunal holds its tools and nothing runs them
until [`proceeding-core.md`](./proceeding-core.md) — but they have to be the real
objects, because what § 5 asserts is that construction refuses for the reason it
names and not because a tool was wrong.

`tests/unit/outcomes/` needs no `__init__.py`; no directory under `tests/` has one,
and the tier marker comes from the path
([`0031`](../decisions/0031-tests-are-tiered.md)), so a new subdirectory is
collected and marked `unit` with nothing to configure.

### The goldens pin assembly, and `rendering.md`'s pin text

[`rendering.md`](./rendering.md#what-is-deliberately-not-asserted) says it: the two
sets of goldens pin different things and neither makes the other redundant. A
prompt edited fails both; an assembly reordered fails only these.

What `test_instructions.py` adds beyond the snapshot itself:

- **The part list and order**, asserted against `instruction_parts()` directly
  rather than read out of the joined string. Five parts for a steered advocate,
  four for an unsteered one, four for a steered judge, three for an unsteered one —
  which is exactly the four rows
  [`execution.md`](../design/execution.md#approves-history--two-runs-eight-messages)
  reports from the wire for `APPROVE`, `DENY` and the judge.
- **`name` and `dynamic` on every part.** The names are `procedural`, `question`,
  `statute`, `assignment`, `guidance`, and `dynamic` is `False` on all of them —
  the flag [`prompting.md`](../design/prompting.md#how-an-agent-is-assembled) says
  is what lets a provider cache the prefix. PydanticAI rejects a part named `agent`
  or containing a colon; none of these is either, and the test is what would say so
  if one were renamed.
- **The cached-prefix claim, asserted as bytes.** "The first three parts are
  byte-identical across every advocate in a tribunal" is a claim about a tribunal
  with three differently-configured advocates, and it is one `==` over a slice. It
  is the sentence that justifies the part order, so it gets a test rather than a
  comment.
- **`## The statute` without a name**, since `statute_heading()` now has two
  callers and the transcript golden only covers one of them.

### What is deliberately not asserted

**That an `Agent` built with these parts resolves to this string.**
`instructions_for()` uses `InstructionPart.join`, which is PydanticAI's own joiner,
so the two agree by construction rather than by luck. What is *not* covered is that
`enbanc` hands the agent these same parts — and nothing builds an agent until
[`proceeding-core.md`](./proceeding-core.md), so that assertion lands there, beside
the capturing `FunctionModel` that can see what actually went over the wire.

**That `Tribunal(verdicts=LoanDecision)` infers `Tribunal[LoanDecision]`.** That is
pyright's, and `make typecheck` runs it in `check-all` and in CI. A runtime test
would assert something the runtime does not know.

**`max_rounds`, `budget` and `max_concurrency` doing anything.** They are held and
not read until the round loop. A test asserting a field round-trips through a
frozen dataclass asserts the dataclass decorator.

## Open questions

*None open.* Three were settled before the code was written, and each answer is in
the prose above with the reasoning that chose it: the instruction parts are
[framed with `##` headings mirroring the reviewer render](#the-four-headings-and-the-part-text),
the assembly [lives in `_prompting.py` and takes the pieces](#the-assembly-lives-in-_promptingpy),
and the `outcomes.md` bench is
[a kwargs builder in the unit tier's conftest](#misconfiguration-needs-kwargs-not-a-tribunal).
The first is an edit to `prompting.md` in this commit, and the other two are edits
to `packaging.md` and `testing.md`.
