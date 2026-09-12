"""The five filings, the judge's private emit-pair, and two of the three generic aliases.

An entry in the transcript is a filing, and there are exactly five: an advocate argues,
concedes, or responds; the judge continues or rules. Each private emit-shape sits beside its
public counterpart, because the conversion between them happens at one seam — the filing
clerk — and holding both shapes of one concept in one file is what keeps the pair from
drifting apart.

See `docs/design/api.md` ("What participants file", "The judge's output", "Where ids come
from"), `docs/decisions/0015-interrogatory-ids-are-stamped-on-filing.md`, and
`docs/decisions/0036-a-continuance-carries-at-least-one-interrogatory.md`.
"""

from typing import Annotated, Generic, Literal

from pydantic import BaseModel, Field
from typing_extensions import TypeAliasType

from ._evidence import Exhibit
from ._verdicts import VerdictT


class Argument(BaseModel, Generic[VerdictT]):
    """An advocate's case for the verdict it was assigned.

    **No `position` field.** The filing already names its `advocate`, and an advocate is
    assigned exactly one verdict, so the position it argues for is not an independent fact —
    storing it twice would only create two places that can disagree.

    **No `author` field either.** `Argument`, `Concession` and `Response` name an advocate;
    `Continuance` and `Ruling` are the judge's by construction. A single
    `author: VerdictT | Literal["judge"]` would make a ruling issued by an advocate
    expressible, and that is the kind of state this design keeps unrepresentable.
    """

    kind: Literal["argument"] = "argument"
    advocate: VerdictT
    claim: str
    exhibits: list[Exhibit] = []


class Concession(BaseModel, Generic[VerdictT]):
    """An advocate declining to argue its assigned verdict.

    A concession is how an advocate withdraws, and it is not a failure: a participant that
    *cannot be heard* ends the proceeding, while one that concedes has filed. A conceded
    advocate stays addressable — the judge may still put an interrogatory to it. See
    `docs/decisions/0037-a-conceded-advocate-stays-addressable.md`.
    """

    kind: Literal["concession"] = "concession"
    advocate: VerdictT
    reason: str


class Interrogatory(BaseModel, Generic[VerdictT]):
    """One question the judge put to one advocate, as it appears in the record.

    `id` is required and has no default, because `Response.answering` is a link and a
    transcript whose link does not resolve is not an audit artifact. The judge cannot fill
    that field — it does not know its own round number, and nothing would stop it issuing the
    same id in two rounds — so it is never asked to: the tribunal stamps the id when it files
    the deliberation, and `_Interrogatory` below is what the judge actually emits.

    Ids are `r{round}-q{n}`, `n` numbered from 1 within the continuance that issued them. The
    round prefix carries uniqueness, so numbering restarts each round and the id says where to
    look: a reviewer holding `answering="r1-q1"` knows the question is in round 1.

    Not a filing in its own right — it nests inside the `Continuance` that issued it, so each
    question appears in the record exactly once, which is also why it carries no `kind`.
    """

    id: str
    to: VerdictT
    question: str


class _Interrogatory(BaseModel, Generic[VerdictT]):
    """What the judge emits: a question with no id on it.

    The second type is what buys the public `id` its required-no-default. A single class would
    need a default for the judge's output to validate, and a defaulted id is one a malformed
    transcript reconstructs silently. **Nothing the judge wrote is altered** — `to` and
    `question` are recorded verbatim and the id is added beside them.
    """

    to: VerdictT
    question: str


class Response(BaseModel, Generic[VerdictT]):
    """An advocate's answer to one interrogatory.

    **`answering` links back by id** rather than by position. Pairing on round-and-advocate
    alone breaks the moment the judge asks one advocate two questions in a round, which it is
    free to do. Neither end of that link is model-authored: the tribunal dispatches one
    advocate run per interrogatory, so it knows which question that run answers and fills the
    link from the dispatch rather than from the model. A response citing a question nobody
    asked is not a state the library can reach.
    """

    kind: Literal["response"] = "response"
    advocate: VerdictT
    answering: str
    answer: str
    exhibits: list[Exhibit] = []


class Ruling(BaseModel, Generic[VerdictT]):
    """The judge's decision, and the end of the proceeding.

    A verdict and reasoning and nothing else, because there is nothing else the judge could
    know. The round it was issued in, what it cost, and what came before it are the tribunal's
    facts, and they live on the `Entry` and the `Hearing` instead.
    """

    kind: Literal["ruling"] = "ruling"
    verdict: VerdictT
    reasoning: str


class Continuance(BaseModel, Generic[VerdictT]):
    """The judge declining to rule yet, and the questions it wants answered first.

    **At least one interrogatory.** `min_length=1` is half of what the `Ruling | Continuance`
    union is for: a `Ruling` cannot hold pending questions, and a `Continuance` cannot be a
    non-decision with nothing to ask. An empty one is not a harmless no-op — the round that
    followed it would dispatch nobody and the judge would deliberate again on an empty delta,
    so it could only repeat itself until `max_rounds` ran out, leaving a transcript of
    identical empty continuances that records a broken proceeding as though it were a hard one.

    The constraint sits on this shape and on `_Continuance`, because they are checked at
    different moments: this one validates a persisted transcript read back, which is the half
    that makes the invariant a property of the artifact rather than of a live proceeding.
    """

    kind: Literal["continuance"] = "continuance"
    interrogatories: list[Interrogatory[VerdictT]] = Field(min_length=1)


class _Continuance(BaseModel, Generic[VerdictT]):
    """What the judge emits: a continuance whose questions carry no ids yet.

    The judge agent's `output_type` is `Ruling[VerdictT] | _Continuance[VerdictT]`, so
    `min_length=1` here validates the judge's output during a run: an empty emission is a
    retry against the **`output`** budget, carrying Pydantic's own message back to a model
    that was shown `minItems: 1` in the first place, and exhausting that budget is a
    participant whose output will not validate — `ProceedingFailed`.
    """

    kind: Literal["continuance"] = "continuance"
    interrogatories: list[_Interrogatory[VerdictT]] = Field(min_length=1)


Deliberation = TypeAliasType(
    "Deliberation",
    Annotated[Ruling[VerdictT] | Continuance[VerdictT], Field(discriminator="kind")],
    type_params=(VerdictT,),
)
"""What the judge produces at the end of a round: it rules, or it asks.

Declared with `TypeAliasType` rather than as a plain alias, and that is forced rather than
cosmetic. Pydantic's `__class_getitem__` returns the origin class when a generic model is
parameterized with a bare `TypeVar` — `Ruling[VerdictT] is Ruling` is `True` — so a plain
`Deliberation = Ruling[VerdictT] | Continuance[VerdictT]` collapses to `Ruling | Continuance`,
loses its parameters, and `Deliberation[VerdictT]` raises `TypeError: ... is not a generic
class` when Pydantic evaluates the annotation. A type checker does not catch this; only
running it does. See `docs/design/api.md` ("A note on generic aliases").

When the support floor moves to 3.12 this becomes `type Deliberation[V: Verdict] = ...` and
the `typing_extensions` import goes away.
"""

Filing = TypeAliasType(
    "Filing",
    Annotated[
        Argument[VerdictT]
        | Concession[VerdictT]
        | Response[VerdictT]
        | Continuance[VerdictT]
        | Ruling[VerdictT],
        Field(discriminator="kind"),
    ],
    type_params=(VerdictT,),
)
"""Anything a participant can put into the record. Exactly five things.

The `kind` tags are defaulted, so a model never has to produce them, and they are what lets a
persisted transcript be read back without Pydantic guessing a union member from field shape.
That matters more here than for most unions: the whole point of the artifact is that someone
reads it later.

Narrowing works by `isinstance` or `match`, against the unparameterized class. Note that
`type(entry.filing) is Ruling` is **False** — Pydantic makes `Ruling[LoanDecision]` a genuine
subclass — so identity checks against the origin class do not work.

`TypeAliasType` for the same forced reason as `Deliberation` above.
"""
