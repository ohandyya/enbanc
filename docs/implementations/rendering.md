---
status: draft
updated: 2026-09-19
---

# Prompting and rendering

**One renderer, three viewpoints, and every word `enbanc` puts in front of a
model.** `_prompting.py`: procedure `p1`, both procedural prompts, the four turn
templates, the projections, and the body behind `Transcript.render()`.

## Scope

The whole of [`prompting.md`](../design/prompting.md) that does not need a live
proceeding: the two procedural prompts verbatim, the turn templates, the
`ReviewerView` / `JudgeView` / `AdvocateView` projections and their `since`
filter, the `p1` constant, and `Transcript.render()` — which is where the one
forced import cycle is broken, `_prompting` importing `_transcript` under
`TYPE_CHECKING` only.

**Not in this PR.** `instructions_for()` and the goldens that run through it.
Assembling instruction parts needs a `Tribunal`, so both land in
[`tribunal-construction.md`](./tribunal-construction.md) — the prompt *text* is
here, the assembly of it is there. The tool-result format is specified here and
implemented in [`ledgering-toolset.md`](./ledgering-toolset.md), where
`render_call` and `render_results` live.

## Implements

- [`prompting.md` § One renderer, three viewpoints](../design/prompting.md#one-renderer-three-viewpoints)
- [`prompting.md` § The advocate's procedural prompt](../design/prompting.md#the-advocates-procedural-prompt)
  and [§ The judge's](../design/prompting.md#the-judges-procedural-prompt)
- [`prompting.md` § The turns](../design/prompting.md#the-turns) — all four
- [`prompting.md` § `Transcript.render()`](../design/prompting.md#transcriptrender)
- [`prompting.md` § Procedure versions](../design/prompting.md#procedure-versions)
  — `p1`, and the bump discipline this PR is the first to owe
- [`execution.md` § `since` advances once per run](../design/execution.md#since-advances-once-per-run-not-once-per-round)
  — the filter half; the state that feeds it is
  [`proceeding-core.md`](./proceeding-core.md)
- [`packaging.md` § What imports what](../design/packaging.md#what-imports-what)
  — the cycle break

## Depends on

[`schemas.md`](./schemas.md).

## Files

One new module, one method added to an existing one, and two design documents
corrected. The module map
([`packaging.md`](../design/packaging.md#the-modules)) puts `_prompting.py`
fifth, between `_filings.py` and `_transcript.py`, and that position is the
whole of its import story.

| Module | Holds | Imports from the package |
|---|---|---|
| `_prompting.py` | `PROCEDURE`, `ADVOCATE_PROCEDURE`, `JUDGE_PROCEDURE`, `LEDGER_PREAMBLE`, `NONE`, `ReviewerView`, `JudgeView`, `AdvocateView`, `View`, `indent`, `render_source`, `render`, `argument_turn`, `response_turn`, `deliberation_turn` | `_verdicts`, `_inputs`, `_evidence`, `_filings` at runtime; `_transcript` under `TYPE_CHECKING` |
| `_transcript.py` | `Transcript.render()` — the one public name this PR reaches | gains `_prompting` |
| `pyproject.toml` | two scoped `per-file-ignores`, [below](#two-lint-rules-scoped-off-the-goldens) | — |

Nothing in `_prompting.py` carries a leading underscore and everything in it is
private, because the module does
([`0034`](../decisions/0034-the-export-surface-is-the-package.md)). The
underscore-prefixed *names* in this package are the ones that sit beside a
public counterpart and could be mistaken for it — `_Exhibit` next to `Exhibit` —
and this module has no such pair.

**No new public names.** `render()` is a method on a class `__all__` already
exports and [`api.md`](../design/api.md#the-record) already declares, so
`test_export_surface.py` is untouched and the twenty-nine-name literal still
waits on [`proceeding-core.md`](./proceeding-core.md).

### The cycle break

The one exception to *imports run down the module list and never back up it*,
and it is forced: [`0026`](../decisions/0026-one-renderer-serves-both-audiences.md)
puts one renderer behind both the agents' views and `Transcript.render()`, so
the renderer needs `Transcript` for its signature and `Transcript` needs the
renderer for its method.

```python
# _prompting.py
from typing import TYPE_CHECKING, Any

from ._filings import Argument, Concession, Continuance, Response, Ruling  # runtime

if TYPE_CHECKING:
    from ._transcript import Transcript                                    # annotation only

def render(transcript: "Transcript[Any]", view: View) -> str: ...
```

```python
# _transcript.py
from ._prompting import ReviewerView, render                               # runtime

class Transcript(BaseModel, Generic[VerdictT]):
    def render(self) -> str:
        return render(self, ReviewerView())
```

`_prompting` imports `_filings` for real, because it dispatches on filing type.
It imports `_transcript` only for annotations — and `Retrieval` and `ToolFailure`
are read by attribute alone, never by `isinstance`, which is what keeps that
import annotation-only rather than merely wished to be.

`from __future__ import annotations` is **not** used to buy this. The module's
annotations are quoted where they name a `TYPE_CHECKING` import, which is three
signatures; a file-wide future import would change how every annotation in the
module is evaluated to solve a problem three quotes already solve.

### `render` is the renderer's name

[`prompting.md`](../design/prompting.md#one-renderer-three-viewpoints) and
`0026` both spell the renderer `render(transcript, view)`.
[`packaging.md`](../design/packaging.md#what-imports-what)'s cycle-break snippet
illustrates it as `render_transcript(transcript)`, taking no viewpoint. Those are
the same function under two names, and the two-argument form is the one that
carries `0026`'s whole argument — a viewpoint is the only thing that varies, so
it has to be a parameter. `packaging.md`'s snippet is corrected to match
([below](#design-documents)).

### `p1`, and the two prompts

```python
PROCEDURE: Final = "p1"
```

The constant `Tribunal` will stamp onto `Transcript.procedure`. It lives here
rather than in `_tribunal.py` because
[`prompting.md`](../design/prompting.md#procedure-versions) scopes it to *this*
surface — both procedural prompts, all four turn templates, the tool-result
format, and the render format, every one of which is in this module. A version
that named the package version, or sat beside the thing that stamps it, would
drift from the text it claims to identify.

`ADVOCATE_PROCEDURE` and `JUDGE_PROCEDURE` are the two prompts, transcribed from
[`prompting.md`](../design/prompting.md#the-advocates-procedural-prompt) as
module-level `str` constants, byte for byte including the blank lines and the
closing guidance-fencing paragraph. Nothing formats them and nothing
interpolates into them — they are the same text for every proceeding, which is
what makes them cacheable and what makes storing them in each transcript
unnecessary
([`0025`](../decisions/0025-the-record-includes-what-steered-it.md)).

**This PR is the first to owe the bump discipline.** Changing either string is
three edits in one commit: the text in `prompting.md`, a new row in its version
table, and `PROCEDURE`. The golden ([below](#tests)) is what makes forgetting
one of them a failing test rather than a false transcript.

### The viewpoints

```python
@dataclass(frozen=True, slots=True)
class ReviewerView: ...

@dataclass(frozen=True, slots=True)
class JudgeView:
    since: int

@dataclass(frozen=True, slots=True)
class AdvocateView:
    advocate: Verdict
    since: int

View = ReviewerView | JudgeView | AdvocateView
```

Frozen dataclasses, not Pydantic models: nothing validates them, nothing
serializes them, and they never leave the process. Non-generic for the same
reason `Exhibit` is — `AdvocateView` names an advocate, and the only thing done
with that name is read it.

**`AdvocateView.advocate` is carried and not read by the filter, and that is
worth saying out loud.** `prompting.md` requires an agent view to hold "never
`ledger`, never `failures`, never another advocate's retrievals" — and a
retrieval appears in exactly one place, `## The ledger`, which both agent views
drop whole. Every *filing* is visible to every participant: an advocate sees the
continuance entire, including questions put to peers, and the judge sees
everything filed. So `JudgeView(since=n)` and `AdvocateView(v, since=n)` emit
identical bytes today.

That is 0026's subset property being complete rather than a field with no job.
The argument for keeping the parameter is that it is the design's signature and
that the day a projection grows a per-advocate rule, the rule has somewhere to
go and every call site already passes what it needs. The test suite asserts the
equality rather than leaving a reader to discover it
([below](#tests)) — a surprising sameness that is deliberate should fail loudly
when it stops being true.

### `render()` — the reviewer's viewpoint

Section order and heading text are
[`prompting.md`](../design/prompting.md#transcriptrender)'s, and sections are
separated by one blank line:

```text
# Proceeding

## The question

{question}

## The statute — {statute.name}

{statute.text}

## The case

{case.model_dump_json(indent=2)}

## The bench

Verdicts: {", ".join(str(v) for v in verdicts)}
Deliberations allowed: {max_rounds}
Procedure: {procedure}

Guidance given:
  {participant}: {text}

## The record

{entry blocks, one blank line between}

## The ledger

Everything the advocates' tools returned. A retrieval no exhibit cites is one
the record did not rest on.

{ledger rows, one blank line between}

## Failed calls

{failure rows, one blank line between}
```

Four rules the design's worked example could not show, because its transcript is
fully populated. Each is a sharpening of
[`prompting.md`](../design/prompting.md#transcriptrender) rather than a
departure from it, and each is paid into that document in this commit
([below](#design-documents)):

- **`## The statute — {name}` loses its suffix when `name is None`**, leaving
  `## The statute`. `Statute.name` is optional and the heading is the only place
  it renders.
- **`Guidance given:` and its block are absent when `guidance` is empty.** The
  heading is a claim that someone was steered; an empty one would be a claim
  that nobody was, made in the same words.
- **`## The record` and `## The ledger` are always emitted**, with `(none)` under
  them when the list is empty. Both are standing halves of the artifact —
  [`api.md`](../design/api.md#the-record) has `entries` saying what the ruling
  rests on and `ledger` saying what was available to rest on, and *nothing was
  available* is a fact about the proceeding, not an absence of one.
- **`## Failed calls` is emitted only when `failures` is non-empty.** It is an
  exception log, and `api.md` is explicit that a populated `failures` "is not a
  finding" — so an empty one is nothing at all, and a standing heading over it
  would give prominence to an absence.

**Guidance renders judge-first, then in `verdicts` order**, skipping
participants that were given none. `Transcript.guidance` is a dict and its
iteration order is whatever the `Tribunal` happened to insert in; a rendered
artifact that is the same bytes for the same proceeding cannot depend on that.
The order matches the design's worked example, which shows `judge` above `deny`.

### The entry blocks

One block per `Entry`, dispatched on the filing with a `match`. The header line
is flush; everything under it is indented.

| Filing | Header line | Under it |
|---|---|---|
| `Argument` | `[round {n}] {advocate} argued:` | `claim` at 2, then the exhibits block |
| `Concession` | `[round {n}] {advocate} conceded:` | `reason` at 2 |
| `Response` | `[round {n}] {advocate} responded to {answering}:` | `answer` at 2, then the exhibits block |
| `Continuance` | `[round {n}] the judge issued a continuance:` | one line per interrogatory at 2: `{id} -> {to}: {question}` |
| `Ruling` | `[round {n}] the judge ruled — {verdict}:` | `reasoning` at 2 |

The exhibits block is emitted only when `exhibits` is non-empty:

```text
  Exhibits:
    [{advocate}/{exhibit.source}] {label or reference}
      {reference}
      {content}
```

The advocate qualifying the id comes from the enclosing filing, never from the
exhibit — `Exhibit` is not generic and names no advocate, because the filing
around it already does. `content` here is the advocate's *excerpt*, not
`Retrieval.content`; the two are different facts and
[`api.md`](../design/api.md#the-record) keeps them that way.

### One three-line source shape, in three dressings

`[id]`-and-label, then the reference, then the content — the shape
[`prompting.md`](../design/prompting.md#how-ledger-ids-reach-the-model) fixes —
appears in three places with three different id forms, so it is one helper:

```python
def render_source(
    *, id: str, label: str | None, reference: str, content: str, note: str | None = None
) -> str: ...
```

| Caller | `id` | `note` | Where |
|---|---|---|---|
| The exhibits block | `approve/s1` | — | here |
| `## The ledger` | `approve/s1` | `cited` / `not cited` | here |
| A tool result | `s1` | — | [`ledgering-toolset.md`](./ledgering-toolset.md) |

`render_source` returns unindented text and the caller indents it, which is how
the same helper serves a ledger row at column 0 and an exhibit at column 4.
`_ledgering.py` imports it: the module sits below `_prompting` in
[the map](../design/packaging.md#the-modules), so that import runs downhill like
every other. **That is what "the tool-result format is specified here and
implemented there" means mechanically** — the shape is one function in this PR,
and the next PR writes the call line and the counting around it.

**When `label is None`, the reference takes the label's place on the first line
and the reference line is dropped.** That is the worked example in
[`prompting.md`](../design/prompting.md#how-ledger-ids-reach-the-model) —
`[s3] dti_for(applicant="A. Okonkwo")` over `dti: 0.51`, two lines rather than
three — and it is the shape
[`evidence.md`](../design/evidence.md#step-1--any-async-function-is-already-a-tool)'s
anonymous-source walkthrough produces. The alternative reading, a bare `[s3]`
line with the reference below it, keeps every row three lines and is what the
prose in that section literally says; it is rejected because the first line
would then carry nothing, and because an anonymous source would print its
reference in a position no labelled source ever uses. The prose is corrected to
match its own example ([below](#design-documents)).

The ledger's row is `render_source` with the id qualified and the note attached
to the first line:

```text
[approve/s1] Schedule C, 2024 — cited
  s3://underwriting-docs/okonkwo/schedule-c-2024.pdf
  net profit: 182,000
```

**`cited` is computed, never stored.** The set of `(entry.filing.advocate,
exhibit.source)` over every `Argument` and `Response` in `entries`, tested
against each row's `(advocate, id)`. [`api.md`](../design/api.md#the-record) is
explicit that there is no `cited: bool` on `Retrieval` and why — a flag would
have to be rewritten when a later round cites a round-1 source, and a transcript
whose rows change after they are appended is not append-only. A renderer runs
after the fact and has the whole proceeding, so it computes what the row must
not store.

A failure row is its own shape, and shows the reference rather than the tool —
the reference *is* the call, and `ToolFailure.tool` is the field a caller
filters on:

```text
[round 1] deny — find_filings(applicant="A. Okonkwo")
  Timed out after 30.0 seconds.
```

### Indentation, and what verbatim does not mean

Every indented value — a claim, a reason, an answer, a ruling's reasoning, an
exhibit's excerpt, a retrieval's content, a failure's detail — is model- or
tool-authored text that may contain newlines. **Every line of it takes the
block's indent**, not only the first.

This is not the wrapping
[`prompting.md`](../design/prompting.md#caller-text-is-emitted-verbatim-and-never-escaped)
forbids. Nothing is reflowed, nothing is truncated, no line break is added or
removed, and stripping a fixed prefix recovers the original exactly. What it
buys is that a block stays one visual unit: under the alternative, the second
line of a two-line claim starts at column 0 and is indistinguishable from the
header of the next entry, and an excerpt's second line reads as though it
belonged to the filing rather than to the exhibit. It also costs one class of
confusion the design already accepts for caller text — a model-authored claim
cannot accidentally emit something that parses as a record header, because
nothing it writes reaches column 0.

**A blank line inside such a value stays blank**, rather than becoming the
indent's worth of trailing spaces. Trailing whitespace in an artifact is noise,
and in an `inline-snapshot` golden it is noise a formatter will eventually eat,
turning a passing test into a failing one for no reason that is about `enbanc`.

**No wrapping, anywhere.** `prompting.md`'s worked examples are hand-wrapped to
80 columns because they sit inside Markdown, and the long interrogatory that
breaks across two lines there is one line here. The two-line standing sentence
under `## The ledger` is the exception that proves it: that text is `enbanc`'s
own, its line break is authored into the constant, and it is reproduced as
written.

### The projections

```python
def render(transcript: "Transcript[Any]", view: View) -> str:
    match view:
        case ReviewerView():
            ...                                    # the whole artifact, above
        case JudgeView(since=since) | AdvocateView(since=since):
            ...                                    # the delta, and nothing else
```

The agent arm is the entry blocks for `e for e in transcript.entries if
e.round > since`, in transcript order, joined by one blank line — no header, no
`##` heading, no closing instruction. **The heading belongs to the turn
template**, which is
[`prompting.md`](../design/prompting.md#the-turns)'s "a turn is the renderer's
output plus the template around it" and is precisely what makes every agent view
a strict subset of the reviewer's rather than a subset with instructions mixed
in. `0026` rejected the alternative by name.

The filter is a comparison on `Entry.round` and nothing else. It does not carve
out the participant's own filings: what the advocate emitted was a bare id and
an excerpt, and what entered the record has the tool and the reference stamped
beside them, so showing it back is showing it something it has not seen.

**`(none)` belongs to the reviewer's section, not to the record rendering** — a
distinction the subset test found rather than the design. The obvious first
implementation puts the placeholder inside the helper that joins entry blocks,
which is shared, so an empty agent delta rendered as `(none)` — a word the
reviewer's record section does not contain at that position, and therefore an
*addition*, which is the one thing the subset property forbids. The helper now
returns the empty string and `_reviewer` supplies the placeholder at the single
place it means something.

An empty delta is unreachable in a real proceeding: a continuance carries at
least one interrogatory, so every dispatched run has something new to read. The
test that caught this renders a `since` past the last round, which is why it is
worth keeping even though no orchestrator will ever produce that call.

**`since` is the only state this PR reads, and the snapshot is the state it does
not own.** [`execution.md`](../design/execution.md#since-advances-once-per-run-not-once-per-round)
splits them deliberately — `since` selects *which rounds*, the snapshot decides
*which filings of those rounds exist to select from* — and run 7 of its
eight-row table is the case that needs both. Producing snapshots is
[`proceeding-core.md`](./proceeding-core.md)'s; consuming one is this module's,
and the tests build them by hand.

**A snapshot is a `Transcript`.** `render` takes one type, so the orchestrator
constructs its per-round base with `model_copy(update={"entries": [...]})` and an
advocate's task extends its local copy the same way. That is a shallow copy with
no validation, and it keeps the renderer from growing a second signature for a
shape that differs from a transcript only in which entries it holds.

### The turns

Three functions for the four templates:

```python
def argument_turn(case: Case, advocate: Verdict) -> str: ...

def response_turn(
    snapshot: "Transcript[Any]", *,
    advocate: Verdict, since: int, round: int, interrogatory: Interrogatory[Any],
) -> str: ...

def deliberation_turn(
    snapshot: "Transcript[Any]", *,
    since: int, deliberation: int, max_rounds: int,
) -> str: ...
```

Each is named for the filing it asks for, which is also what distinguishes them:
`argument_turn` asks for an `Argument` or a `Concession`, `response_turn` for a
`Response`, `deliberation_turn` for a `Deliberation`.

**Three functions, not four, and the asymmetry is the templates'.** The judge's
two turns differ by one heading — `## Round 1` when `since == 0`, `## Filed since
you last deliberated` otherwise — and are otherwise the same lines in the same
order, so splitting them would duplicate a template to vary a string. The
advocate's two share no line at all: one carries the case and no record, the
other carries a record, a continuance, an addressed question, and no case.

Each builds its own viewpoint rather than accepting one. The viewpoints stay
internal to the module, callers pass what they know — a round, a `since`, an
interrogatory — and a test that wants a projection on its own calls `render`
directly.

`round` shadows the builtin inside `response_turn`, which is deliberate and
matches `Entry.round`: the field is the design's word for the thing, the builtin
is not used in this module, and renaming the parameter would make the call site
say something other than what the record says.

### `_transcript.py`

Two lines: the `_prompting` import, and the method. The docstring notes that
`render()` is the reviewer's viewpoint of a renderer shared with the agents and
that its output is versioned by `Transcript.procedure` — which is the one fact
about this method a reader is liable to guess wrong, because a `render()` on a
model usually means *however it prints today*.

### Two lint rules scoped off the goldens

`pyproject.toml` gains a `[tool.ruff.lint.per-file-ignores]` table with two
entries, and both are about goldens rather than about style.

**`E501` on `test_transcript_render.py` and `test_turns.py`.** A golden holds
rendered output, and the prompting surface contains lines longer than this
repository's 100-column limit — a judge's reasoning, a statute, an excerpt.
Re-wrapping one inside the snapshot would make the test assert something the
renderer does not emit, which is the one thing a golden may not do. The rule is
about reading code; these strings are a picture of what `enbanc` printed. Only
the two modules whose snapshots embed a rendered proceeding are listed, so the
limit still holds over every line of test code in them that is code.

**`SIM300` on `test_procedural_prompts.py`.** Ruff reads
`ADVOCATE_PROCEDURE == snapshot(...)` as a Yoda condition, because the name is
upper-case. It is not one: `inline-snapshot`'s convention is actual on the left
and expected on the right, and that is the form `--inline-snapshot=fix` writes
back. Satisfying the rule would put the expected value first and the next `fix`
run would undo it.

### Deleted

`tests/unit/test_transcript.py::test_the_transcript_holds_no_renderer_yet`,
which asserted `not hasattr(Transcript, "render")` and pointed at this document.
It was [`schemas.md`](./schemas.md)'s placeholder for exactly this PR, and its
successor is `tests/unit/test_transcript_render.py`.

### Design documents

Three edits, all of them `CLAUDE.md` rule 2 paid in this commit.

[`prompting.md` § How ledger ids reach the model](../design/prompting.md#how-ledger-ids-reach-the-model)
— the "three lines per source" sentence is sharpened so that it describes the
worked example directly under it: the reference takes the first line when there
is no label, and the row is two lines. The example is unchanged; the prose was
the half that was wrong.

[`prompting.md` § `Transcript.render()`](../design/prompting.md#transcriptrender)
— gains the four rules a fully-populated worked example cannot show: the statute
heading without a name, the absent guidance block, `(none)` under `## The
record` and `## The ledger`, and `## Failed calls` omitted when empty. Gains one
paragraph on indentation: every line of a multi-line value takes its block's
indent, blank lines stay blank, and neither is the wrapping the verbatim rule
forbids.

[`packaging.md` § What imports what](../design/packaging.md#what-imports-what)
— the cycle-break snippet's `render_transcript(transcript)` becomes
`render(transcript, view)`, matching `prompting.md` and `0026`.

**No version bump.** `PROCEDURE` stays `p1`. Nothing above changes text that
`prompting.md` already fixed — the prompts, the turn templates and the worked
render output are transcribed as written. The edits describe cases the document
did not reach, which is a document completed rather than a surface changed, and
`p1` has never been stamped on a transcript because nothing stamps one yet.

Every design document keeps `status: draft` and its *none of this exists yet*
banner; making the documentation stop lying is
[`zero-one-zero.md`](./zero-one-zero.md)'s scope.

### Nothing in `api.md`

[`api.md`](../design/api.md#the-record) already declares
`def render(self) -> str: ...` on `Transcript` and already delegates the format
to `prompting.md`. This PR fills in a method the public surface had already
promised, so the surface does not move.

## Tests

All in `tests/unit/` — `enbanc`'s own behaviour, and none of it needs a model.
The socket guard has nothing to block and neither `TestModel` nor
`FunctionModel` appears: every input is a `Transcript` built by hand, which is
the point of a renderer that takes only a transcript.

| Module | Pins |
|---|---|
| `test_procedural_prompts.py` | both prompts as `inline-snapshot` goldens, with `PROCEDURE == "p1"` asserted in each — the bump discipline, made a failing test |
| `test_transcript_render.py` | the reviewer view as a golden over the worked proceeding; the `cited` / `not cited` join; the statute heading with and without a name; the guidance block's order and its absence; `(none)` under an empty record and an empty ledger; `## Failed calls` present only when something failed |
| `test_entry_blocks.py` | the five filing shapes; a multi-line claim and a multi-line excerpt indented line by line; a blank line inside one staying blank; a source with no label rendering two lines; an exhibit-less argument emitting no `Exhibits:` |
| `test_turns.py` | all four templates as goldens, including the second run of a twice-questioned advocate whose delta is its own stamped response |
| `test_projections.py` | the invariant's half that lives here — see below |
| `test_cycle_break.py` | that `_prompting` binds no `Transcript` at runtime |

### Three fixtures, and why they are fixtures

`tests/unit/conftest.py` gains `case`, `deny`, and `proceeding`. A `conftest.py`
is not a module a test may import from, so anything a test needs out of it
arrives as a fixture value — including `deny`, which is a verdict *member*
rather than the enum class. `type[Verdict]` has no members to a type checker:
the base declares none, which is exactly what makes it subclassable
([`0004`](../decisions/0004-verdicts-are-a-strenum.md)), so `loan_decision.DENY`
is a pyright error rather than a style choice. A test that needs the whole bench
reads `proceeding.verdicts`, which is the same list and is typed.

### The fixture is the worked proceeding, and it is shared

[`execution.md` § The transcript this produces](../design/execution.md#the-transcript-this-produces)
is eight entries, two rounds, three advocates and a twice-questioned `deny`, and
[`prompting.md`](../design/prompting.md#the-turns)'s rendered examples are the
same proceeding — the two documents are written to be the same fixture so they
cannot drift. Four of the six modules above need it, so it is a fixture in
`tests/unit/conftest.py` rather than a `_transcript()` helper copied into each,
which is the shape `test_transcript.py` uses for its own smaller one.

**This sets a precedent, deliberately.**
[`tribunal-construction.md`](./tribunal-construction.md) pins
`instructions_for()` over the same tribunal and
[`proceeding-core.md`](./proceeding-core.md) drives the same proceeding through
a `FunctionModel`; a fixture in the tier's conftest is what lets all three
assert against one record. The alternative — three copies of an eight-entry
transcript — is three places for `outcomes.md`'s spine to rot.

### The projections are the highest-value tests here

[`testing.md` § The transcript invariant](../design/testing.md#the-transcript-invariant)
says the risk moved to the viewpoints and that the viewpoints are enumerable.
This module is that enumeration:

- **The subset property, asserted.** Every line an agent view emits appears in
  the `ReviewerView` of the same transcript. Line-wise rather than substring,
  because the agent view is a *contiguous* subset of the record section and a
  substring test would pass on a rendering that reordered it.
- **No ledger, no failures, no peer retrieval.** Over a transcript whose ledger
  and failures hold strings that appear nowhere else, so their absence is
  assertable by search rather than by reading the code that drops them.
- **`JudgeView(since=n)` and `AdvocateView(v, since=n)` emit the same bytes**,
  for every `v` and every `n` in the fixture. The surprising sameness
  [above](#the-viewpoints), asserted so that the day a projection grows a
  per-advocate rule, this is the test that says so.
- **`since` selects the right delta**, against
  [`execution.md`](../design/execution.md#since-and-the-snapshot-run-by-run)'s
  eight-row table, parameterized row by row. **Run 7 is the row that constrains
  everything**: `since=1` over a hand-built snapshot holding entries 1–4 and 6,
  rendering entry 6 alone. Its sibling case — the same `since` over a snapshot
  that also holds entry 5 — is asserted to render both, which is what proves the
  exclusion is the snapshot's doing and not something `since` accidentally
  covers.

Rows 1–3 of that table have no `since` and no snapshot, so they are
`argument_turn`'s golden in `test_turns.py` rather than a projection case. The
table is reproduced in the test module's docstring with a link back, because a
parameterized list of integers is unreadable without it.

### What is deliberately not asserted

**That `Transcript.procedure` reproduces the prompt.**
[`testing.md`](../design/testing.md#what-must-not-be-asserted) names this: the
field stores a version and not the text, on purpose, and a test asserting
otherwise would assert a design `0025` rejected. The goldens cover the text.

**`assert_invariant_held()`.** The helper
[`testing.md`](../design/testing.md#the-transcript-invariant) specifies takes
what a capturing `FunctionModel` recorded and the transcript that resulted.
There is no proceeding to capture from until
[`proceeding-core.md`](./proceeding-core.md), and a helper with no caller is a
guess about its own signature. What lands here is the half that needs no
proceeding — the projections, tested directly.

**The assembled instruction string.** `instructions_for()` is
[`tribunal-construction.md`](./tribunal-construction.md)'s, and that PR pins the
*assembly*: the five parts, their order, and the cached-prefix claim that the
first three are byte-identical across advocates. This PR pins the *text* of the
one part it owns. The two goldens pin different things and neither makes the
other redundant — a prompt edited here fails both, an assembly reordered there
fails only its own.

**The cycle break, beyond one `hasattr`.** `test_cycle_break.py` asserts that
`enbanc._prompting` has no runtime `Transcript` attribute, which is the half a
test can see. That the annotation still resolves is `make typecheck`'s, and
pyright runs in `check-all` and in CI. A subprocess test that imported
`_prompting` alone would prove more and cannot be written: importing it goes
through `enbanc/__init__.py`, which imports `_transcript` regardless.

## Open questions

*None open.* Three were settled before the code was written, and each answer is
in the prose above with the reasoning that chose it: a source with no label
[promotes its reference](#one-three-line-source-shape-in-three-dressings) to the
first line, a multi-line value
[takes its block's indent on every line](#indentation-and-what-verbatim-does-not-mean),
and an empty ledger [renders `(none)`](#render--the-reviewers-viewpoint) while an
empty `## Failed calls` renders nothing at all. All three are edits to
`prompting.md` in this commit rather than facts that live only here.
