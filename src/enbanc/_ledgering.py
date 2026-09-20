"""Every tool call an advocate makes, intercepted, recorded, and rewritten.

`execution.md`'s piece 2. One `WrapperToolset` over one `CombinedToolset` is the whole of it:
every call an advocate makes goes through `call_tool`, each source that comes back is issued
an id and written to `Transcript.ledger`, each call that returned nothing is written to
`Transcript.failures`, and what the model reads is the same rows with their ids attached — so
it can cite one, and so the tribunal can stamp the citation from something it observed rather
than from something the model wrote.

**The wrapper is rebuilt for every run, and that shapes the whole module.**
`CombinedToolset.for_run` returns `replace(self, toolsets=...)` unconditionally, so
`WrapperToolset.for_run` always replaces too, and `dataclasses.replace` re-constructs this
instance from its fields. The object `call_tool` runs on is therefore never the one the
orchestrator holds. Two rules follow: every piece of state is a dataclass field, and anything
that has to accumulate is a mutable container shared by reference — `replace()` is shallow, so
a `list` field is the *same list* in the copy while an `int` field is a value the copy mutates
alone. That is why ids are counted out of the ledger rather than into a counter, and it is
`docs/decisions/0016-exhibits-are-stamped-citations.md`'s closing constraint — the ledger is
owned by the proceeding, not by this object. `tests/contract/`'s
`test_a_wrapper_toolset_is_rebuilt_per_run.py` pins the dependency's half of it.

See `docs/design/evidence.md`, `docs/design/execution.md` ("Piece 2 — the ledgering toolset"),
`docs/design/prompting.md` ("How ledger ids reach the model"),
`docs/decisions/0019-the-ledger-is-part-of-the-record.md`, and
`docs/decisions/0022-tool-failures-are-recorded.md`.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Generic

from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.toolsets import ToolsetTool, WrapperToolset

from ._evidence import Source, _Exhibit
from ._filings import _Argument, _Response
from ._prompting import render_source
from ._transcript import Retrieval, ToolFailure
from ._verdicts import VerdictT


def render_call(name: str, tool_args: dict[str, Any]) -> str:
    """The call, as a reference a reviewer can re-run: `find_filings(applicant="A. Okonkwo")`.

    `json.dumps` rather than `repr`, because `docs/design/evidence.md` spells a string
    argument in double quotes and an integer bare, and a reference that does not match the
    format the design fixed is one nobody can grep for. `ensure_ascii=False` keeps a
    non-ASCII locator legible instead of escaping it into an audit artifact, and
    `default=repr` keeps a validated `datetime` or model from raising inside the ledger — a
    tool call must never fail because `enbanc` could not print it.

    Arguments are emitted in the order PydanticAI handed them over, never sorted. They are
    also the *validated* ones, so a parameter the tool defaults appears here even when the
    model omitted it: the reference is then the call as it actually ran, which is what makes
    it reproducible.
    """
    args = ", ".join(
        f"{key}={json.dumps(value, ensure_ascii=False, default=repr)}"
        for key, value in tool_args.items()
    )
    return f"{name}({args})"


def as_sources(result: Any, *, fallback_reference: str) -> list[Source]:
    """What a tool returned, as the sources it will be ledgered as.

    A `Source`, or a sequence of them, is taken as written. Anything else — a string, a dict,
    a model, an MCP payload — becomes one anonymous source whose reference is the call itself
    and whose content is the value stringified. `enbanc` sniffs the shape rather than
    requiring a declaration, which is what keeps every existing PydanticAI tool usable with no
    adaptation: returning `Source` is an upgrade, not an entry fee.

    Three edges, each decided rather than fallen into:

    * **`str` and `bytes` are excluded from the sequence branch explicitly.** A string is a
      `Sequence`, and `all(...)` over an empty one is vacuously true, so the ordinary spelling
      would ledger `""` as zero sources.
    * **A mixed sequence is anonymous as a whole.** Ledgering the `Source`s in it and dropping
      the rest would put half a tool result in the record under its own ids and the other half
      nowhere, which is the one thing `0019` does not tolerate.
    * **An empty sequence is zero sources**, and so no rows at all. A tool that expects to come
      up empty returns an empty result; that is neither a retrieval nor a failure.
    """
    if isinstance(result, Source):
        return [result]
    if (
        isinstance(result, Sequence)
        and not isinstance(result, str | bytes)
        and all(isinstance(item, Source) for item in result)
    ):
        return [item for item in result if isinstance(item, Source)]
    return [Source(reference=fallback_reference, content=str(result))]


def render_results(call: str, rows: Sequence[Retrieval[Any]]) -> str:
    """The tool result the advocate reads, in `docs/design/prompting.md`'s format.

    The header line naming the call and the count, then one three-line source block per row.
    `render_source` is the shape an exhibit and a ledger row already use; a tool result is the
    dressing that passes a **bare** id and no note.

    **The rows are rendered from the `Retrieval`s, never from the `Source`s they came from.**
    They hold the same values, and rendering the persisted row is what makes what the model
    read and what the record holds the same bytes by construction rather than by review.

    Zero sources is the header alone — the count is a fact about the call, and an advocate
    that searched and found nothing is not one that did not search.
    """
    noun = "source" if len(rows) == 1 else "sources"
    header = f"{call} returned {len(rows)} {noun}."
    blocks = [
        render_source(id=row.id, label=row.label, reference=row.reference, content=row.content)
        for row in rows
    ]
    return "\n\n".join([header, *blocks])


@dataclass(kw_only=True)
class Ledgering(WrapperToolset[None], Generic[VerdictT]):
    """One advocate's toolset, wrapped so that everything it returns enters the record.

    Constructed by the orchestrator, one per advocate, living the whole proceeding:

        Ledgering(
            wrapped=CombinedToolset([
                FunctionToolset(tools=advocate.tools),
                *advocate.toolsets,
            ]),
            advocate=verdict,
            ledger=transcript.ledger,
            failures=transcript.failures,
        )

    Routing everything through one wrapper over one combined toolset is what makes *intercepts
    every call* true of an MCP server as well as of a plain function — `enbanc` never sees the
    difference, because `CombinedToolset` has already erased it.

    **The two lists are the transcript's own**, passed in rather than built here. A row is in
    the record the instant it is written, so a proceeding that fails mid-round still carries a
    ledger complete as far as it got, and the lists survive the per-run `replace()` described
    in this module's docstring because the proceeding is what holds them.

    **`round` is a mutable field and that is the seam between two lifetimes.** This object
    outlives every round, because the id sequence has to; `Retrieval.round` does not. The
    orchestrator sets it before each dispatch and `for_run` copies it into the run, so it
    flows one way and is safe for the reason `0027` protects: an advocate's runs are
    sequential.

    Deps are fixed at `None` — an `Advocate` has no `deps=`, because a tool closes over what
    it needs.
    """

    advocate: VerdictT
    ledger: list[Retrieval[VerdictT]]
    failures: list[ToolFailure[VerdictT]]
    round: int = 1

    async def call_tool(
        self,
        name: str,
        tool_args: dict[str, Any],
        ctx: RunContext[None],
        tool: ToolsetTool[None],
    ) -> Any:
        """Intercept one call: record what came back, and hand the model the ids.

        The call is rendered before the `try`, because both arms need it — it is the failed
        call's reference, the anonymous source's reference, and the result's header line, and
        a reviewer reading a failure beside a retrieval sees the same call spelled the same
        way.

        **`except ModelRetry` and nothing wider.** That is what a `Tool` timeout becomes
        inside `FunctionToolset.call_tool`, and it is also what a tool raises to correct the
        model deliberately; both are calls that returned nothing. It is recorded and re-raised
        untouched, so PydanticAI still turns it into the `RetryPromptPart` the advocate adapts
        to, and the `detail` stored is PydanticAI's own string rather than one composed here.
        Anything else propagates, ends the round, and surfaces as `ProceedingFailed`: that one
        `except` clause is the whole difference between a degraded advocate and an unheard one.

        `get_tools` is deliberately not overridden. The wrapper changes nothing about which
        tools the model is offered or what their schemas say — only what comes back.
        """
        call = render_call(name, tool_args)
        try:
            result = await super().call_tool(name, tool_args, ctx, tool)
        except ModelRetry as e:
            self.failures.append(
                ToolFailure[VerdictT](
                    round=self.round,
                    advocate=self.advocate,
                    tool=name,
                    reference=call,
                    detail=str(e),
                )
            )
            raise
        rows = self._ledger_rows(name, as_sources(result, fallback_reference=call))
        self.ledger.extend(rows)
        return render_results(call, rows)

    def _ledger_rows(self, tool: str, sources: Sequence[Source]) -> list[Retrieval[VerdictT]]:
        """Number this call's sources and build their rows, without writing them.

        **The count is derived from the ledger rather than held in a counter**, which is what
        survives the per-run `replace()`. A counter field would renumber `s1` at the top of
        every round, silently, and the id is the join key an exhibit resolves through.

        **`base` is read once, before any row is built.** A `next_id()` that counted the list
        per row would give every source of a two-source call the same id, because nothing is
        appended until the caller's `extend` — the one bug here a single-source test cannot
        see.

        **The filter is this advocate's rows.** The list is transcript-wide, and ids are
        numbered within an advocate: `APPROVE`'s `s1` and `DENY`'s `s1` are different
        retrievals, which is why the join key is `(advocate, id)`. Counting the whole list
        would number one bench-wide sequence and break that premise.
        """
        base = sum(1 for row in self.ledger if row.advocate == self.advocate)
        return [
            Retrieval[VerdictT](
                id=f"s{base + n}",
                round=self.round,
                advocate=self.advocate,
                tool=tool,
                reference=source.reference,
                content=source.content,
                label=source.label,
            )
            for n, source in enumerate(sources, start=1)
        ]

    def issued(self) -> list[str]:
        """The ids this advocate has been issued, in order."""
        return [row.id for row in self.ledger if row.advocate == self.advocate]

    def check_citations(self, filing: _Argument[VerdictT] | _Response[VerdictT]) -> None:
        """Reject a citation this advocate was never issued, as an output validator.

        An advocate that cites an id the ledger does not hold has invented a citation, which is
        the failure the whole mechanism exists to prevent. Raising `ModelRetry` spends the
        **`output`** budget rather than the `tools` one, so a flapping search tool cannot eat
        the budget that guards citation integrity and a healthy tool cannot mask an advocate
        inventing citations.

        It sees the rows the run just wrote because the validator closes over the
        orchestrator's instance while `call_tool` ran on a `replace()` copy, and the two share
        one list.

        The message uses the procedural prompt's own words — *issued to you* — and names the
        two mistakes separately: a qualified id is one copied out of the rendered record, where
        another advocate's ids are written with that advocate's name in front of them.

        Registering this on an agent is the orchestrator's; `_proceeding.py` is where the
        advocate's agent is built.
        """
        issued = self.issued()
        for exhibit in filing.exhibits:
            if exhibit.source in issued:
                continue
            raise ModelRetry(self._unresolvable(exhibit, issued))

    def _unresolvable(self, exhibit: _Exhibit, issued: Sequence[str]) -> str:
        citable = ", ".join(issued) if issued else "(none) — your tools have returned no sources"
        if "/" in exhibit.source:
            return (
                f"[{exhibit.source}] belongs to another advocate and is not yours to cite. "
                f"The ids you may cite are: {citable}."
            )
        return f"[{exhibit.source}] was not issued to you. The ids you may cite are: {citable}."
