"""The record: every filing in order, plus everything the tribunal saw on the way.

A `Transcript` is the audit artifact and it is self-contained — it carries the question, the
statute and the case alongside the entries, so a transcript dumped to JSON is a complete
account on its own rather than a fragment that needs the `Hearing` to be legible.

See `docs/design/api.md` ("The record"),
`docs/decisions/0006-the-transcript-schema.md`,
`docs/decisions/0019-the-ledger-is-part-of-the-record.md`,
`docs/decisions/0022-tool-failures-are-recorded.md`, and
`docs/decisions/0025-the-record-includes-what-steered-it.md`.
"""

from collections.abc import Iterator
from datetime import datetime
from typing import Generic

from pydantic import BaseModel, SerializeAsAny

from ._filings import Filing
from ._inputs import Case, Statute
from ._prompting import ReviewerView, render
from ._verdicts import Participant, VerdictT


class Entry(BaseModel, Generic[VerdictT]):
    """One filing, with the two facts the filer did not know.

    An envelope rather than fields spread onto each filing, for the same reason `Hearing`
    wraps `Ruling`: `round` and `filed_at` are things the tribunal knows and the filer does
    not. Putting `round` on `Ruling` would put a field on the judge's own output schema that
    the judge cannot fill.
    """

    round: int
    filed_at: datetime
    filing: Filing[VerdictT]


class Retrieval(BaseModel, Generic[VerdictT]):
    """One source a tool returned, recorded whether or not any advocate filed it.

    The ledger is the second half of the audit artifact: `entries` says what the ruling rests
    on, and `ledger` says what was available to rest on. An advocate that pulls damaging
    evidence and quietly declines to file it leaves a trace here.

    **Suppression is found by joining, not by a flag.** The retrievals nothing rests on are
    the ledger rows no `Exhibit.source` names, joined on `(advocate, id)` — ids are numbered
    within an advocate, so `APPROVE`'s `s1` and `DENY`'s `s1` are different retrievals.
    Per-advocate numbering is deliberate: an advocate's tool calls are sequential, so its ids
    are deterministic, whereas one counter shared across advocates running concurrently would
    assign different ids on every run of the same proceeding.

    There is deliberately no `cited: bool`. Whether a round-1 source is ever cited is not
    known until the proceeding ends, so the field would be written on append and rewritten
    when a later round cites it — and a transcript whose rows change after they are appended
    is not append-only. The join is exact anyway, because both sides carry the same
    tribunal-stamped id.

    `content` is verbatim, as the tool returned it. `enbanc` truncates nothing: a truncated
    retrieval could cut the exact sentence an audit turns on. The lever is the tool — return
    the snippet you want the advocate to reason over, not the document it came from.
    """

    id: str
    round: int
    advocate: VerdictT
    tool: str
    reference: str
    content: str
    label: str | None = None


class ToolFailure(BaseModel, Generic[VerdictT]):
    """One tool call that returned nothing.

    A timed-out call produces no source, so it produces no `Retrieval` and would otherwise
    appear nowhere — leaving an advocate that was blocked from its best source
    indistinguishable from one that did not look. One row per attempt, because timing out
    three times is a different fact from timing out once.

    **No `id`, and that is the point.** A `Retrieval` carries one so an `Exhibit.source` can
    name it; a failed call produced nothing and can never be cited. Keeping failures in their
    own list rather than as `Retrieval`s with an `outcome` flag is what keeps the ledger's
    rows meaning one thing: a successful call yields a row per source, and a failed call
    yields no source at all.

    **A populated `failures` is not a finding.** It records that a tool failed, not that the
    ruling turned on it. `enbanc` does not mark a hearing degraded, warn, or adjust the
    outcome — whether the judge should have weighed a gap is the reviewer's call, and the
    record's job is to make it askable.
    """

    round: int
    advocate: VerdictT
    tool: str
    reference: str
    detail: str


class Transcript(BaseModel, Generic[VerdictT]):
    """The append-only record of a proceeding, and the audit artifact.

    **`verdicts`, `max_rounds`, `guidance` and `procedure` are the standing record too.** They
    are here for the same reason `question` and `statute` are: each one reaches a
    participant's context, and a transcript that did not hold it would make the invariant
    *nothing enters an agent's context that is not also in the transcript* false. `verdicts`
    names the bench an advocate was told it faced, including values nobody argued to.
    `max_rounds` is the envelope, and the judge is told where it stands in it. `guidance` is
    the caller's steer, stored in full, keyed by the participant it was given to and holding
    only those that got one — absence means none was given. `procedure` names the prompting
    surface the proceeding ran under, by version rather than by text.

    **`case` is `SerializeAsAny[Case]`, and has to be.** Pydantic v2 serializes a field by its
    *declared* type, so a `LoanApplication` sitting in a plain `case: Case` field dumps as a
    bare `Case` and every subclass field disappears — silently, out of the artifact whose
    whole job is to be complete. `SerializeAsAny` switches that one field to duck-typed
    serialization. It is the price of `Case` not being a type parameter.

    **`guidance`'s participant key is not the `author` field the filings reject.** That
    rejection is about *filings*: one carrying `VerdictT | Literal["judge"]` would make a
    ruling issued by an advocate expressible. This is the tribunal's accounting of who was
    steered, and it enters no filing.
    """

    question: str
    statute: Statute
    case: SerializeAsAny[Case]
    verdicts: list[VerdictT]
    max_rounds: int
    guidance: dict[Participant[VerdictT], str] = {}
    procedure: str
    entries: list[Entry[VerdictT]] = []
    ledger: list[Retrieval[VerdictT]] = []
    failures: list[ToolFailure[VerdictT]] = []

    # The three below make a transcript readable as the sequence of entries it is. Two
    # consequences of that are worth knowing, and neither is a defect:
    #
    #   * `dict(transcript)` no longer works. `BaseModel.__iter__` yields (field, value)
    #     pairs and this overrides it; `model_dump()` is the supported path and is untouched.
    #   * An entry-less transcript is **falsy**, because `__len__` says it is empty. So
    #     `if failure.transcript:` on a `ProceedingFailed` from round 1 reads as "there is no
    #     record" when there is one. That is what `__len__` means on a sized object; test for
    #     the record with `is not None`, and for filings with `len(...)`.

    def __iter__(self) -> Iterator[Entry[VerdictT]]:  # type: ignore[override]
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __getitem__(self, i: int) -> Entry[VerdictT]:
        return self.entries[i]

    def render(self) -> str:
        """The proceeding as readable text: the header, the record, the ledger, the failures.

        **This is the reviewer's viewpoint of a renderer the agents share**, so what it emits
        is specified rather than left to implementation — `docs/design/prompting.md` has it in
        full. An agent's view is this view minus rows, never plus text, which is what makes
        the context invariant checkable by construction
        (`docs/decisions/0026-one-renderer-serves-both-audiences.md`).

        Its output is therefore **versioned**, by `self.procedure` rather than by the package
        version. A `render()` on a model usually means *however it prints today*; this one
        does not, and changing what it emits is a procedure bump.

        The delegation to `_prompting` is where the package's one import cycle is broken:
        `_transcript` imports the renderer for real, and the renderer imports `_transcript`
        under `TYPE_CHECKING` only. See `docs/design/packaging.md` ("What imports what").
        """
        return render(self, ReviewerView())
