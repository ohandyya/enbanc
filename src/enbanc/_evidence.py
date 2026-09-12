"""Evidence, before and after it is filed.

A `Source` is what a tool returns. An `Exhibit` is what an advocate files, and four of its
five fields are stamped by the tribunal from the ledger rather than written by the model —
`_Exhibit` is the shape the advocate actually emits, and it holds only the two it may author.

None of the three is generic: an exhibit names no advocate, because the filing around it
already does.

See `docs/design/evidence.md` and
`docs/decisions/0016-exhibits-are-stamped-citations.md`.
"""

from pydantic import BaseModel


class Source(BaseModel):
    """One piece of evidence a tool found, together with the locator for it.

    The pre-filing thing: sources are what tools return, exhibits are what advocates file,
    and most sources never become exhibits.

    **`reference` is opaque to `enbanc`.** It is a string, and the library does not parse it,
    validate its shape, resolve it, or fetch it. Each tool defines what a locator means for
    the evidence it returns — a result URL, an object key, a file path and line range, the
    query that produced a row. The only test is whether a human holding the string can find
    the evidence again.

    **`label` is for reading, `reference` is for checking.** A rendered transcript citing
    *"Schedule C, 2024"* is legible in a way one citing an S3 key is not, but the label is a
    convenience and the reference is the claim. A tool with no natural title leaves it `None`.

    **A tool does not have to return `Source`.** It may return a string, a dict, a Pydantic
    model, an MCP server's payload — anything. Such a return is ledgered as one anonymous
    source whose reference is the call itself, so it is still first-class and still citable;
    it just gets a coarser reference. Returning `Source` is an upgrade, not an entry fee.
    """

    reference: str
    content: str
    label: str | None = None


class _Exhibit(BaseModel):
    """What an advocate emits: a ledger id and the excerpt it relies on.

    The advocate is asked only for what it knows. Every field whose correctness the record
    depends on is filled by the tribunal from something it observed, so a fabricated citation
    is not a state the library can reach — an id the ledger does not hold fails output
    validation against the `output` retry budget.

    Private, and the exact parallel of `_Interrogatory` in `_filings.py`.
    """

    source: str
    content: str


class Exhibit(BaseModel):
    """A filed citation: the advocate's excerpt, beside the reference a reviewer can follow.

    Four of the five fields are the tribunal's, resolved from the ledger when the filing is
    made. The one the advocate writes is `content`, the one that says what mattered, and the
    stamped `reference` is how a reviewer checks whether it says it fairly.

    `source` is kept rather than consumed, because the ledger is part of the record and the id
    is what joins an exhibit to the `Retrieval` behind it. The join key is `(advocate, id)`:
    ids are numbered within an advocate, so `APPROVE`'s `s1` and `DENY`'s `s1` are different
    retrievals.

    **`Exhibit.content` is the advocate's excerpt; `Retrieval.content` is verbatim.** They are
    different facts about the same source and both are load-bearing: the excerpt says what the
    advocate claimed mattered, the verbatim text is what it actually had in front of it.
    Reading them side by side is how a misquote is caught.
    """

    source: str
    tool: str
    reference: str
    content: str
    label: str | None = None
