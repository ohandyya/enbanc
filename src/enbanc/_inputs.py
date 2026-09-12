"""What the caller supplies: the rule being judged against, and the facts of one decision.

Both are nouns in the record — authored by you, never by an agent — and both are frozen, so
what the transcript says was applied and decided on cannot change under it.

See `docs/design/api.md` ("The inputs"),
`docs/decisions/0001-statute-carries-no-model.md`,
`docs/decisions/0007-a-statute-is-opaque-text.md`, and
`docs/decisions/0013-a-case-is-a-subclassable-base.md`.
"""

from pydantic import BaseModel, ConfigDict


class Statute(BaseModel):
    """The rule being judged against, and nothing else.

    `text` is **opaque to `enbanc`**: you write it in whatever form suits the rule, and the
    library does not parse it, validate its shape, split it into parts, or require any
    structure. A paragraph, numbered clauses, Markdown, a pasted policy document — all are a
    statute, and all reach the judge and the advocates whole and appear in the transcript
    verbatim. The only constraint is the one the annotation states.

    `name` is what a transcript cites when a reviewer asks which version of the policy
    produced a decision. It labels the text; it claims nothing about it. The field only earns
    its place because the transcript is self-contained, and it is the reason a statute is a
    type rather than a bare `str`.

    Frozen, because it is shared across tribunals and across concurrent proceedings, and
    because a rule that could be edited mid-hearing would make the transcript's account of
    what was applied unfalsifiable.

    Turning a statute into prompt text is `enbanc`'s job, not the statute's. There is no
    `render()` here and no `Statute.draft()`: drafting needs a target representation to
    compile prose into, and a statute has none by design.
    """

    model_config = ConfigDict(frozen=True)

    text: str
    name: str | None = None


class Case(BaseModel):
    """The facts of a single decision.

    No fields, because the facts are yours. **Subclass it** to give them a schema — that is
    the path for anything that runs twice: the fields are validated at construction, the facts
    the statute talks about are named in one place, and a reviewer reading the transcript back
    sees that shape rather than whatever the call site happened to pass.

        class LoanApplication(Case):
            applicant: str
            income: int
            dti: float

    **The base is open, so it is usable as it is.** `extra="allow"` makes
    `Case(applicant="A. Okonkwo", income=182000)` a case — the shortest thing that works while
    a tribunal is still being sketched. It also does a second job that matters more than
    convenience: when a persisted transcript is validated back, a subclass's fields land on the
    base `Case` as extras rather than being rejected, so the artifact survives a round trip
    even where the static type does not. Recovering the subclass is
    `LoanApplication.model_validate(hearing.transcript.case.model_dump())`.

    **`Case` is not a type parameter.** `Transcript.case` is typed `Case`, and nothing here is
    keyed on the case the way everything is keyed on the verdict enum: `enbanc` renders a case
    and records it, and reads no field of it.

    Frozen, like a statute, and for the same reason.
    """

    model_config = ConfigDict(frozen=True, extra="allow")
