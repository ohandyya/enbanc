"""Every word `enbanc` puts in front of a model, and the record it puts in front of a human.

One renderer, three viewpoints. An agent's context is this renderer over a *filtered
projection* of the transcript, and `Transcript.render()` is the same renderer over the whole
of it. That is what makes the context invariant — *nothing enters an agent's context that is
not also in the transcript* — true by construction rather than true by review: there is no
code path that can render for an agent something the transcript does not hold, because the
only input is a transcript and the only difference between views is which rows are dropped.

Everything here is versioned by `PROCEDURE`. Changing any of this text is three edits in one
commit: the text in `docs/design/prompting.md`, a new row in its version table, and the
constant below. A prompt edited without a bump makes every transcript that claims `p1` a
false record of what ruled, and `tests/unit/test_procedural_prompts.py` is what turns that
into a failing test.

See `docs/design/prompting.md`, which is the spec for every byte below,
`docs/decisions/0026-one-renderer-serves-both-audiences.md`, and
`docs/decisions/0025-the-record-includes-what-steered-it.md`.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from pydantic_ai.messages import InstructionPart

from ._evidence import Exhibit
from ._filings import Argument, Concession, Continuance, Interrogatory, Response, Ruling
from ._inputs import Case, Statute
from ._verdicts import JUDGE, Verdict

if TYPE_CHECKING:
    # Annotation-only, and the break in the one forced import cycle
    # (`docs/design/packaging.md`, "What imports what"). The renderer needs `Transcript` for
    # its signature and `Transcript` needs the renderer for its method; this direction is the
    # one that does not run at import time. It stays annotation-only because nothing here
    # dispatches on a transcript type — `Retrieval` and `ToolFailure` are read by attribute
    # and never by `isinstance`, which is the property that keeps the cycle broken rather
    # than merely wished broken.
    from ._transcript import Entry, Retrieval, ToolFailure, Transcript

#: The prompting surface a proceeding runs under, stamped onto `Transcript.procedure`. It
#: names *this module* — both procedural prompts, all four turn templates, the tool-result
#: format, and the render format — and not the package version, so two hearings under 0.1.0
#: and 0.1.1 stay comparable when no prompt moved between them.
PROCEDURE: Final = "p1"

ADVOCATE_PROCEDURE: Final = """\
You are an advocate before an adversarial tribunal.

A tribunal decides one question against one statute. It seats one advocate for
each verdict the question may be answered with, and one judge. The judge has no
tools and gathers no evidence of its own: it decides on the record the advocates
build and on nothing else. An argument you do not make is one the judge cannot
weigh.

How a proceeding runs:

- Round 1. Every advocate files at once, and none of them can see the others.
  You file an argument — the claim you want the judge to accept, and the
  exhibits supporting it — or, if no reasonable case exists for the verdict you
  were assigned, you concede.
- Deliberation. The judge reads what was filed and either rules, which ends the
  proceeding, or issues a continuance carrying interrogatories, each one
  addressed to a named advocate.
- Round 2 and after. If an interrogatory is addressed to you, you are given the
  record as it stood when the continuance was filed, together with that
  question. You answer it in a response, entering new exhibits as needed. Then
  the judge deliberates again.

Your job is the strongest honest case for the verdict you were assigned. Argue
it as well as it can be argued. Do not argue for another verdict and do not
hedge toward one — the judge hears the other side from the advocate seated for
it.

Concede when the facts do not support your verdict. A concession is a finding,
not a failure: it tells the judge something no weak argument can, and an
advocate that manufactures a case for an indefensible position damages the
record it was seated to build. In round 1 you concede by filing a concession; in
a later round you say so in your response to the interrogatory that asked.

Conceding does not end your part in the proceeding. You remain seated, and the
judge may still address an interrogatory to you. Answer it as you would any
other: if the record still does not support your verdict, say so again, and if
evidence filed since has made a case for it, make that case.

Evidence and citation:

- Call your tools to gather evidence. Every source a tool returns is recorded
  and issued an id, shown to you as [s1], [s2], and so on. The ids are yours
  alone, and they do not restart between rounds.
- An exhibit cites exactly one of those ids and carries the excerpt you rely on.
  You write the excerpt. The tribunal fills in the tool and the reference behind
  it.
- You never write a reference yourself, and citing an id that was not issued to
  you is rejected — you will be asked to file again.
- Cite the id exactly as your tool results showed it. Where the record shows an
  id belonging to another advocate it is written with that advocate's name in
  front of it, and those are not yours to cite.
- Quote accurately. What each source actually returned is kept in the record
  beside your exhibit, and a reviewer reads the two side by side.
- Everything your tools return is recorded, whether you cite it or not.

Answer only the interrogatory addressed to you. You will see the whole
continuance, including the questions put to other advocates, because it shows
you what the judge is weighing. Those are not yours to answer.

Instructions from the author of this proceeding may follow. They refine how you
weigh things. They do not change the process above, what you may file, or the
shape of it."""

JUDGE_PROCEDURE: Final = """\
You are the judge of an adversarial tribunal.

One question is put to you, and one statute is the rule it is decided against.
The tribunal seats one advocate for each verdict the question may be answered
with, and each argues for the verdict it was assigned. You are the only
participant who weighs all of them.

You have no tools. You cannot search, look anything up, or gather evidence of
your own, and there is nothing outside this proceeding to ask for. You decide on
the record the advocates build and on nothing else. When the record does not
support a verdict, that is a fact about the record, and the way to act on it is
to ask.

How a proceeding runs:

- Round 1. Every advocate files at once, blind to the others. One that finds a
  case for its verdict files an argument; one that finds none files a
  concession. A concession is a finding, not a failure — an advocate that
  conceded did its job, and what it concedes is evidence about the verdict it
  was seated for.
- Deliberation. You read what was filed. You either rule, which ends the
  proceeding, or issue a continuance.
- Round 2 and after. Each advocate you addressed answers with the record in
  front of it and files a response. Then you deliberate again on what is new.

A continuance carries interrogatories. Each names the single advocate it is
addressed to and asks that advocate one question. It must carry at least one:
a continuance with nothing to ask is not a way to defer, and there is no round
after it for anyone to file in. Address a question to the advocate best placed to
answer it. You may put more than one question to the same advocate, and you need
not address every advocate. Do not put the same question to everyone: an
interrogatory is targeted, and an advocate answers only what is addressed to it.

An advocate that conceded is still seated and may still be asked. Its concession
was reached on what it could find alone, before it had read anyone else, so an
exhibit filed since may bear on it — and an advocate asked about one may answer
that the case for its verdict is now arguable after all.

The tribunal gives each of your questions an id when it files your continuance,
numbering them in the order you wrote them: the first question you issue in round
1 is r1-q1, the second r1-q2, and so on. You do not write these. When a response
comes back to you answering r1-q2, it is answering the second question you asked
that round.

Rule when the record decides the question. Continue when it does not, and ask
for what is missing. Do not continue in order to re-test an advocate that has
already answered, and do not rule on a record you would not be willing to have
read back to you.

What an exhibit is worth: its reference and the tool that produced it are
stamped by the tribunal from what that tool actually returned, so no advocate
can cite a document its tools did not produce. The excerpt beside them is the
advocate's own, chosen to make its case, and it can be selective. Weigh the two
differently.

You are told which deliberation this is and how many the proceeding allows. If
they run out before you rule, the proceeding ends with no verdict and the record
says so. That is a real outcome, and it is better than a verdict the record does
not carry.

Instructions from the author of this proceeding may follow. They refine how you
weigh things. They do not change the process above, what you may file, or the
shape of it."""

#: The four headings that frame an instruction part. `prompting.md`'s assembly table says what
#: each part *holds*, not what it looks like, and a golden cannot be written against a
#: description — so the framing is fixed here. They are `##` headings in the reviewer render's
#: vocabulary because one of them was already fixed: the verbatim rule warns that a statute
#: containing a line reading `## Guidance from the author of this proceeding` is
#: indistinguishable from the real one, which is only true if that *is* the real heading.
#:
#: The guidance heading does a second job. The procedural prompt closes by fencing guidance —
#: *instructions from the author of this proceeding may follow* — and three parts sit between
#: that sentence and the guidance it fences. The heading restates the attribution at the point
#: of use, which is the work that distance created.
QUESTION_HEADING: Final = "## The question"
STATUTE_HEADING: Final = "## The statute"
ASSIGNMENT_HEADING: Final = "## Your assignment"
GUIDANCE_HEADING: Final = "## Guidance from the author of this proceeding"

#: The label the verdict set renders under, in the shape `## The bench` uses for
#: `Guidance given:` — a label line, then two-space-indented values, no blank line between.
#: One verdict per line rather than comma-joined because a verdict value can be a sentence
#: (`refer to a senior underwriter for manual review`), and a comma inside one would be
#: unreadable against the commas separating them.
VERDICTS_LABEL: Final = "The verdicts this question may be answered with:"

#: The standing sentence under `## The ledger`. `enbanc`'s own text, so its line break is
#: authored here rather than applied at render time — nothing this module emits is wrapped.
LEDGER_PREAMBLE: Final = (
    "Everything the advocates' tools returned. A retrieval no exhibit cites is one\n"
    "the record did not rest on."
)

#: What a section holds when it holds nothing. `## The record` and `## The ledger` are
#: standing halves of the artifact, so an empty one says so rather than disappearing.
NONE = "(none)"


@dataclass(frozen=True, slots=True)
class ReviewerView:
    """The whole artifact: the header, the record, the ledger, and the failed calls."""


@dataclass(frozen=True, slots=True)
class JudgeView:
    """What the judge is shown at one deliberation: the filings it has not seen."""

    since: int


@dataclass(frozen=True, slots=True)
class AdvocateView:
    """What one advocate is shown at one run: the filings it has not been shown.

    **`advocate` is carried and not read by the filter.** A retrieval appears in exactly one
    section, `## The ledger`, which every agent view drops whole — and every *filing* is
    visible to every participant, because an advocate sees the continuance entire (including
    questions put to peers) and the judge sees everything filed. So this view and `JudgeView`
    emit identical bytes, and `tests/unit/test_projections.py` asserts that rather than
    leaving a reader to discover it.

    That is `0026`'s subset property being complete, not a field with no job. It is kept
    because it is the design's signature and because the day a projection grows a
    per-advocate rule, every call site already passes what the rule needs.
    """

    advocate: Verdict
    since: int


#: Any way of reading the record. Internal: `render()` is not public surface, and
#: `Transcript.render()` is the only way to reach it from outside.
View = ReviewerView | JudgeView | AdvocateView


def indent(text: str, spaces: int) -> str:
    """Prefix every line of `text`, leaving blank lines blank.

    **This is not the wrapping the verbatim rule forbids.** Nothing is reflowed, truncated,
    or re-broken, and stripping a fixed prefix recovers the original exactly. What it buys is
    that a block stays one visual unit: the second line of a two-line claim would otherwise
    start at column 0 and be indistinguishable from the header of the next entry.

    A blank line stays blank rather than becoming `spaces` worth of trailing whitespace,
    which is noise in the artifact and noise a formatter eventually eats out of a golden.
    """
    prefix = " " * spaces
    return "\n".join(prefix + line if line else line for line in text.split("\n"))


def statute_heading(statute: Statute) -> str:
    """`## The statute — {name}`, losing the suffix when the statute is unnamed.

    Two callers — the reviewer render's header and an agent's `statute` instruction part — so
    it is a function rather than one line of format written twice. The heading is the only
    place a name renders, in either of them.
    """
    return f"{STATUTE_HEADING} — {statute.name}" if statute.name else STATUTE_HEADING


def render_source(
    *,
    id: str,
    label: str | None,
    reference: str,
    content: str,
    note: str | None = None,
) -> str:
    """One source, in the three-line shape `docs/design/prompting.md` fixes.

    `[id]` and the label, then the reference, then the content verbatim. The reference is
    shown even though an advocate never writes one, because where a source came from bears on
    how much weight it deserves.

    **With no label the reference takes the first line and the reference line is dropped**,
    so the row is two lines rather than three. That is what a tool returning something other
    than a `Source` produces — it is ledgered as one anonymous source whose reference is the
    call itself — and printing a bare `[s3]` above it would put nothing on the line that
    exists to identify the row. An empty-string label counts as no label for the same reason:
    it would render as a trailing space.

    One helper for three dressings. The exhibits block and `## The ledger` pass a qualified
    `advocate/id`; `_ledgering.py` passes a bare `s1` for what the model sees in a tool
    result. `## The ledger` is the only caller that passes a `note`, which is its computed
    `cited` / `not cited`. Output is unindented and the caller indents it.
    """
    head = f"[{id}] {label}" if label else f"[{id}] {reference}"
    if note is not None:
        head = f"{head} — {note}"
    lines = [head]
    if label:
        lines.append(indent(reference, 2))
    lines.append(indent(content, 2))
    return "\n".join(lines)


def _exhibits(advocate: Verdict, exhibits: list[Exhibit]) -> list[str]:
    """The `Exhibits:` block under an argument or a response, or nothing at all.

    **The advocate qualifying each id comes from the enclosing filing**, never from the
    exhibit: `Exhibit` is not generic and names no advocate, because the filing around it
    already does. Ids are qualified everywhere in the record — including the filer's own —
    because the join key for an exhibit and its retrieval is `(advocate, id)`, and because a
    qualified id cannot be pasted into a citation, which is the point.

    `content` here is the advocate's excerpt, not `Retrieval.content`. The two are different
    facts about the same source and reading them side by side is how a misquote is caught.
    """
    if not exhibits:
        return []
    lines = ["  Exhibits:"]
    for exhibit in exhibits:
        lines.append(
            indent(
                render_source(
                    id=f"{advocate}/{exhibit.source}",
                    label=exhibit.label,
                    reference=exhibit.reference,
                    content=exhibit.content,
                ),
                4,
            )
        )
    return lines


def _entry_block(entry: "Entry[Any]") -> str:
    """One filing, rendered. The header line is flush and everything under it is indented."""
    filing = entry.filing
    head = f"[round {entry.round}] "
    match filing:
        case Argument():
            return "\n".join(
                [f"{head}{filing.advocate} argued:", indent(filing.claim, 2)]
                + _exhibits(filing.advocate, filing.exhibits)
            )
        case Concession():
            return f"{head}{filing.advocate} conceded:\n{indent(filing.reason, 2)}"
        case Response():
            return "\n".join(
                [
                    f"{head}{filing.advocate} responded to {filing.answering}:",
                    indent(filing.answer, 2),
                ]
                + _exhibits(filing.advocate, filing.exhibits)
            )
        case Continuance():
            return "\n".join(
                [f"{head}the judge issued a continuance:"]
                + [indent(f"{q.id} -> {q.to}: {q.question}", 2) for q in filing.interrogatories]
            )
        case Ruling():
            return f"{head}the judge ruled — {filing.verdict}:\n{indent(filing.reasoning, 2)}"
    # Unreachable: `Filing` is a closed union of exactly the five above. It is here so that a
    # sixth filing fails loudly at the renderer rather than silently rendering as nothing.
    raise AssertionError(f"unrenderable filing: {type(filing).__name__}")


def _record(entries: "list[Entry[Any]]") -> str:
    """The entry blocks, in transcript order, one blank line between.

    **An empty list renders as the empty string, not as `NONE`.** `(none)` belongs to
    `## The record`, which is a section of the reviewer's artifact; an agent view is the
    blocks and nothing else, and adding a word to an empty delta would be exactly the
    addition the subset property forbids. `_reviewer` supplies the placeholder at the one
    place it means something.
    """
    return "\n\n".join(_entry_block(entry) for entry in entries)


def _ledger_rows(transcript: "Transcript[Any]") -> str:
    """The ledger, with `cited` computed at render time rather than stored.

    The join is the set of `(advocate, id)` pairs every argument and response cites, tested
    against each row's own pair. There is deliberately no `cited: bool` on `Retrieval`: a
    round-1 source can be cited in round 2, so the flag would be written on append and
    rewritten later, and a transcript whose rows change after they are appended is not
    append-only. A renderer runs after the fact and has the whole proceeding, so it computes
    what the row must not store.
    """
    cited: set[tuple[Verdict, str]] = set()
    for entry in transcript.entries:
        filing = entry.filing
        if isinstance(filing, Argument | Response):
            cited.update((filing.advocate, exhibit.source) for exhibit in filing.exhibits)
    rows: list[Retrieval[Any]] = transcript.ledger
    if not rows:
        return NONE
    return "\n\n".join(
        render_source(
            id=f"{row.advocate}/{row.id}",
            label=row.label,
            reference=row.reference,
            content=row.content,
            note="cited" if (row.advocate, row.id) in cited else "not cited",
        )
        for row in rows
    )


def _failure_rows(failures: "list[ToolFailure[Any]]") -> str:
    """The failed calls. The reference is shown rather than the tool, because it is the call.

    `ToolFailure.tool` is the field a caller filters on; `reference` is the one that says what
    was actually attempted, and it already carries the tool's name in front of it.
    """
    return "\n\n".join(
        f"[round {failure.round}] {failure.advocate} — {failure.reference}\n"
        f"{indent(failure.detail, 2)}"
        for failure in failures
    )


def _bench(transcript: "Transcript[Any]") -> str:
    """`## The bench`: the verdict set, the envelope, the procedure, and who was steered.

    **Guidance renders judge-first, then in `verdicts` order**, skipping anyone who was given
    none. `Transcript.guidance` is a dict and its iteration order is whatever the `Tribunal`
    happened to insert in; a rendered artifact that is the same bytes for the same proceeding
    cannot depend on that.

    The `Guidance given:` block is absent entirely when nobody was steered. The heading is a
    claim that someone was; an empty one would be a claim that nobody was, made in the same
    words.
    """
    lines = [
        f"Verdicts: {', '.join(str(verdict) for verdict in transcript.verdicts)}",
        f"Deliberations allowed: {transcript.max_rounds}",
        f"Procedure: {transcript.procedure}",
    ]
    steered = [
        (participant, transcript.guidance[participant])
        for participant in (JUDGE, *transcript.verdicts)
        if participant in transcript.guidance
    ]
    if steered:
        lines.append("")
        lines.append("Guidance given:")
        lines += [indent(f"{participant}: {text}", 2) for participant, text in steered]
    return "\n".join(lines)


def _reviewer(transcript: "Transcript[Any]") -> str:
    """The whole artifact. `## The bench`, `## The ledger` and `## Failed calls` are the
    three sections no agent ever sees, and dropping them *is* the projection."""
    sections = [
        "# Proceeding",
        f"{QUESTION_HEADING}\n\n{transcript.question}",
        f"{statute_heading(transcript.statute)}\n\n{transcript.statute.text}",
        f"## The case\n\n{transcript.case.model_dump_json(indent=2)}",
        f"## The bench\n\n{_bench(transcript)}",
        f"## The record\n\n{_record(transcript.entries) or NONE}",
        f"## The ledger\n\n{LEDGER_PREAMBLE}\n\n{_ledger_rows(transcript)}",
    ]
    if transcript.failures:
        # Emitted only when something failed. `failures` is an exception log rather than a
        # standing half of the artifact — a populated one is not a finding, so an empty one is
        # nothing at all, and a heading over it would give prominence to an absence.
        sections.append(f"## Failed calls\n\n{_failure_rows(transcript.failures)}")
    return "\n\n".join(sections)


def render(transcript: "Transcript[Any]", view: View) -> str:
    """The one renderer. A transcript, a viewpoint, and the text that viewpoint sees.

    `ReviewerView` is the whole artifact. `JudgeView` and `AdvocateView` are strict subsets
    of it: the entry blocks for every filing in the transcript from a round *after* `since`,
    in transcript order, and nothing else — no header, no `##` heading, no instruction. **The
    heading belongs to the turn template**, which is what keeps an agent's view a subset of
    the reviewer's rather than a subset with instructions mixed in.

    The filter is a comparison on `Entry.round` and nothing else. It does not carve out the
    participant's own filings: what an advocate emitted was a bare id and an excerpt, and what
    entered the record has the tool and the reference stamped beside them, so showing it back
    is showing it something it has not seen.

    **The transcript passed for an agent view is a snapshot, not the live record.** `since`
    selects which rounds; the snapshot decides which filings of those rounds exist to select
    from. Both are needed and neither substitutes for the other — building snapshots is the
    orchestrator's job, and `docs/design/execution.md` is where the two meet.
    """
    match view:
        case ReviewerView():
            return _reviewer(transcript)
        case JudgeView(since=since) | AdvocateView(since=since):
            return _record([entry for entry in transcript.entries if entry.round > since])
    raise AssertionError(f"unknown viewpoint: {type(view).__name__}")  # pragma: no cover


def instruction_parts(
    *,
    question: str,
    statute: Statute,
    verdicts: Sequence[Verdict],
    advocate: Verdict | None,
    guidance: str | None,
) -> list[InstructionPart]:
    """The instructions channel: what one participant runs under, as PydanticAI's own parts.

    Five parts for a steered advocate, four for an unsteered one, four for a steered judge,
    three for an unsteered one — which is exactly what `docs/design/execution.md` reports
    from the wire. Every part is static (`dynamic` defaults to `False`), which is what lets a
    provider cache the prefix, and the first three are **byte-identical across every advocate
    in a tribunal**. That is why the order is what it is: a cache prefix is a prefix, so the
    shared block comes first and only the assignment and the guidance differ.

    **It takes the pieces, not a `Tribunal`.** `_tribunal` sits below this module, so a
    runtime import of it would be a second cycle — and the one cycle `docs/design/packaging.md`
    permits is already spent on `Transcript.render()`. `Tribunal.instructions_for()` resolves
    a participant and hands the pieces down, in the same register `_proceeding.py` takes them.

    `advocate=None` is the judge, rather than `Participant`'s `"judge"`: the absence of an
    assignment is what the parameter encodes, `None` says so in the signature, and this module
    then has no reason to know the reserved string exists.

    **The case is not here.** It arrives in the round-1 turn, so a statute reused across many
    cases keeps its cached prefix warm across all of them — and so `instructions_for()` needs
    no case to render.
    """
    parts = [
        InstructionPart(
            JUDGE_PROCEDURE if advocate is None else ADVOCATE_PROCEDURE, name="procedural"
        ),
        InstructionPart(f"{QUESTION_HEADING}\n\n{question}", name="question"),
        InstructionPart(f"{statute_heading(statute)}\n\n{statute.text}", name="statute"),
    ]
    if advocate is not None:
        listed = indent("\n".join(str(verdict) for verdict in verdicts), 2)
        parts.append(
            InstructionPart(
                f"{ASSIGNMENT_HEADING}\n\n{VERDICTS_LABEL}\n{listed}\n\n"
                f'You are the advocate for "{advocate}".',
                name="assignment",
            )
        )
    if guidance is not None:
        # `is not None` and no other test. `Advocate(guidance="")` would put a heading over
        # nothing, which is the claim `_bench` refuses to make about an empty `Guidance given:`
        # block — but the remedy there is a length check on a computed list, and here it would
        # be a rule about whitespace applied to caller text the library promises to pass
        # through verbatim. `Transcript.guidance` is keyed on the same predicate, so the record
        # and the prompt agree about who was steered.
        parts.append(InstructionPart(f"{GUIDANCE_HEADING}\n\n{guidance}", name="guidance"))
    return parts


def argument_turn(case: Case, advocate: Verdict) -> str:
    """Round 1, advocate. The only turn that carries the case, and the only one with no record.

    A case renders as `model_dump_json(indent=2)`. `enbanc` reads no field of a `Case`, so the
    rendering has to be generic, and JSON is the one form that handles nesting and lists
    without inventing a flattening rule that would then have to be kept faithful to
    `model_dump`. It is also exactly what `Transcript.case` serializes to, so the text the
    advocate read and the artifact a reviewer reads cannot disagree.
    """
    return (
        f"## The case\n\n{case.model_dump_json(indent=2)}\n\n"
        f'Round 1. File your argument for "{advocate}", or concede.'
    )


def response_turn(
    snapshot: "Transcript[Any]",
    *,
    advocate: Verdict,
    since: int,
    round: int,
    interrogatory: "Interrogatory[Any]",
) -> str:
    """Round 2+, advocate. The record delta, the whole continuance, and the one question.

    The whole continuance is in the delta, including questions put to peers: it is one filing,
    and *targeted* is a duty about who must **answer**, not a rule about who may **read**.
    Seeing what the judge is asking elsewhere is what lets a rebuttal meet the case rather
    than the paraphrase of it.

    `round` shadows the builtin deliberately. It is `Entry.round`'s word for the thing, the
    builtin is not used in this module, and renaming it would make the call site say something
    other than what the record says.
    """
    return "\n\n".join(
        [
            f"## Filed since you last filed\n\n{render(snapshot, AdvocateView(advocate, since))}",
            f"## Addressed to you\n\n{interrogatory.id}: {interrogatory.question}",
            f"Round {round}. Answer {interrogatory.id} and file your response.",
        ]
    )


def deliberation_turn(
    snapshot: "Transcript[Any]",
    *,
    since: int,
    deliberation: int,
    max_rounds: int,
) -> str:
    """The judge's turn, both of `prompting.md`'s two templates.

    They differ by one heading — `## Round 1` at the first deliberation, `## Filed since you
    last deliberated` after — and are otherwise the same lines in the same order, so they are
    one function rather than two that would have to be kept in step.

    **The judge is told the deliberation count and never the budget.** *Deliberation 2 of 5*
    is two facts the record holds, so telling it opens no hole in the invariant. A budget is
    spend measured between rounds, it is not on the transcript, and disclosing it would push
    the judge to rule for reasons the record could never show.
    """
    heading = "## Round 1" if since == 0 else "## Filed since you last deliberated"
    return "\n\n".join(
        [
            f"{heading}\n\n{render(snapshot, JudgeView(since))}",
            f"Deliberation {deliberation} of {max_rounds}. Rule, or issue a continuance.",
        ]
    )
