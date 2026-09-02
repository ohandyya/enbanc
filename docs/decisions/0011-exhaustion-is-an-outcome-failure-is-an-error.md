---
status: accepted
updated: 2026-09-02
---

# 0011. Exhaustion is an outcome; failure is an error

## Context

[`../design/api.md`](../design/api.md) described a proceeding that always
succeeds. Two things that will happen in production had nowhere to land.

**The judge never rules.** `max_rounds` deliberations pass and the record still
ends in a `Continuance`. This was the round-limit exhaustion question in
[`../design/tribunal.md`](../design/tribunal.md), and `Hearing.ruling` was typed
`Ruling | None` *solely* because of it.
[`0005`](./0005-hear-returns-a-hearing.md) left the question open on purpose —
"Exhaustion is not decided here" — and recorded the resulting
`if hearing.ruling is not None:` at every call site as the visible cost of
leaving it open.

**An external service fails.** The provider is unreachable, a caller's tool
raises, or output-validation retries are exhausted. Nothing in the design said
what happens, which meant a raw provider exception escaping `enbanc` and the
partial transcript going with it — for a library whose product *is* the
transcript.

They arrived as one question and they are settled together, because the answer
is a single line drawn between them.

## Decision

**The line is whether the tribunal finished.** A proceeding that deliberated
`max_rounds` times and could not rule *ran the whole process*; "no verdict" is a
finding about the case, and a reviewer must be able to persist it and read it
back. A proceeding that lost a participant to an outage never ran; nothing was
adjudicated, and handing back a `Hearing` for it invites a caller to file one
outcome as the other.

So **exhaustion is a record, and failure is an exception.**

### `Hearing.outcome` replaces `Hearing.ruling`

```python
class Undecided(BaseModel):
    kind: Literal["undecided"] = "undecided"

Outcome = TypeAliasType(
    "Outcome",
    Annotated[Ruling[VerdictT] | Undecided, Field(discriminator="kind")],
    type_params=(VerdictT,),
)

class Hearing(BaseModel, Generic[VerdictT]):
    outcome: Outcome[VerdictT]
    transcript: Transcript[VerdictT]
    usage: RunUsage
    rounds: int
```

**A discriminated union rather than an optional.** A type checker forces
narrowing before an attribute access, so the exhaustion branch cannot be skipped
the way `is not None` can be forgotten. This is the move `Ruling | Continuance`
already makes one level down, applied to the result.

**`Undecided` carries nothing.** No round count — that is `Hearing.rounds`. No
pending interrogatories — those are the last entry of the transcript. Either
would be the duplication that kept `position` off `Argument`.

**`Undecided` is not generic.** It carries no verdict, so there is no verdict
type to key it on.

**The outcome is the final entry's filing only when it is a `Ruling`.** When it
is `Undecided` nothing filed it: the transcript ends on the judge's last
`Continuance`, and the outcome is the tribunal's statement that no round
followed. This narrows what `0005` promised about `Hearing.ruling`.

### The exception hierarchy

```python
class EnbancError(Exception):
    """Base for everything enbanc raises."""

class ConfigurationError(EnbancError):
    """A tribunal that cannot be constructed."""

class ProceedingFailed(EnbancError, Generic[VerdictT]):
    """A participant could not be heard, so no ruling was reached."""
    participant: VerdictT | Literal["judge"]
    round: int
    transcript: Transcript[VerdictT]
    usage: RunUsage

class ProceedingUnfinished(EnbancError):
    """proceeding.hearing before there is one."""
```

**`ProceedingFailed` carries the record, not a `Hearing`.** It cannot carry one:
`outcome` is required, and a failed proceeding has no outcome. That falls out of
the field above rather than being an independent choice.

**`round`, and no `rounds`.** `Hearing` carries `rounds` because a completed
proceeding is asked how much of its budget it spent. A failure is asked *where*
it stopped, and the two are not independent: a round completes when its
deliberation is filed, so a failure in round *N* — in the advocate fan-out or in
the deliberation itself — always leaves exactly *N-1* rounds behind it. Carrying
both would store one fact twice, which is the objection that kept `position` off
`Argument` and an `author` off every filing.

**One exception, three causes.** A provider that is unreachable, a caller's tool
that raises, and output validation that exhausts its retries all mean the same
thing to a caller: an agent could not file, so the proceeding cannot continue.
The specific error is `__cause__`. `enbanc` does not build a taxonomy on top of
the one PydanticAI and httpx already raise.

**Failure is terminal for the whole proceeding**, including one advocate's
failure while the judge and its peers are healthy. The transcript keeps
everything filed up to that point and rides on the exception.

**`enbanc` retries nothing.**
[`0009`](./0009-model-settings-live-on-the-model.md) put HTTP retry and backoff
on the httpx client inside the caller's `Model`, so an error reaching `enbanc`
means the caller's own policy has already given up. The library's own retry
budget is `Agent(retries=...)`, which guards the `Ruling | Continuance` contract
and is exhausted before `ProceedingFailed` is raised.

**`usage` on a failure is best-effort**, summed over the runs that completed.
A run that died mid-flight may not report what it spent.

**`EnbancError` is the common ancestor**
[`0010`](./0010-streaming-yields-the-record.md) said the two exceptions would
need. Exhaustion did not become one — but `ProceedingFailed` did, which settles
the question `0010` deferred.

### Streaming

**Exhaustion does not raise from the stream.** The `async for` ends after the
final `Continuance` and `proceeding.hearing.outcome` is `Undecided`, which is
what `0010` anticipated when it said the stream's shape is the same either way.

**`ProceedingFailed` propagates out of the `async with`**, as `0010` already
specified for a provider failure, and `proceeding.transcript` survives it.
`proceeding.hearing` then re-raises that `ProceedingFailed` rather than masking
it; `ProceedingUnfinished` is reserved for a proceeding still running or
abandoned by the caller.

## Consequences

**The `if` is gone, and the case it guarded is not.** Every call site now reads
`match hearing.outcome:` with a `Ruling` arm and an `Undecided` arm. `0005`
argued the optional was the wrong shape because a caller could skip the check;
the answer was not to delete the state but to make the type system insist on it.

**Rejected: both cases raise, so a `Hearing` always means a verdict.** The
tidiest call site — `hearing.outcome.verdict` with no narrowing at all — and the
reading `0005` and `docs/progress.md` both leaned toward. It fails on the
artifact: an exception is not a `BaseModel`, so a hung proceeding could not be
dumped to JSON and read back, and preserving one would mean pulling
`e.transcript` out by hand and inventing somewhere to record *why* it stopped.
For a library whose deliverable is an auditable record, the outcome a reviewer
most needs to examine is the one that would not serialize.

**Rejected: neither case raises; `Ruling | Undecided | Failure`.** Literally
never throws, and every terminal state becomes one serializable record. It makes
an outage come back looking like a completed proceeding — `hearing.usage` and
`hearing.transcript` read normally, and only the third branch says nothing was
decided. A caller who logs the hearing and moves on has filed an infrastructure
failure as an adjudication. The exception exists precisely so that cannot be the
quiet path.

**Rejected: keeping `ruling: Ruling | None`.** The status quo, already argued
against in `0005` and named as the next thing to fix in `docs/progress.md`.

**Rejected: record the absence and let the judge rule anyway.** A sixth filing
kind naming the advocate that could not be heard, after which the judge
deliberates on what it has. This is the robust option: a transient blip in round
3 would not discard three rounds of paid work, and it fits the rule that if one
participant should see what another said, it goes in the record. It was rejected
because the ruling it produces is one-sided — the advocate for the losing answer
was silenced by an outage rather than answered — and it is indistinguishable at
the type level from a ruling reached on a full bench. Defensibility is the
product; a degraded ruling that only the transcript reveals is worse than no
ruling at all. It would also have put a filing in the record that no participant
filed, which [`0006`](./0006-the-transcript-schema.md) does not allow.

**Rejected: an `on_absence="end" | "continue"` knob.** Both behaviours, chosen
per tribunal. Two settings with materially different guarantees about what a
ruling means, which the library would document and neither of which it could
promise.

**Rejected: a forced verdict on the final round** — narrowing the judge's output
type to `Ruling` when the round limit is one away. `../design/tribunal.md`
already called this the least defensible option, and it is: it converts "we
could not decide" into a decision, which is the one transformation an audit
artifact must never make silently.

**Rejected: `ModelUnavailable` as the failure name.** Narrower than the thing it
names — it would be a lie for a caller's tool raising, and for validation
retries running out.

**Rejected: courtroom naming** (`Mistrial` for the base, `Deadlock` for
exhaustion). Consistent with the glossary, and `Mistrial` is genuinely the right
legal word for a proceeding terminated without a verdict. But exception names
are read in stack traces by people debugging at speed, often before they have
read the glossary, and a metaphor that must be decoded there costs more than it
returns. `Undecided` keeps the record vocabulary plain for the same reason it
sits next to `Ruling`. This is the one place the metaphor is deliberately
dropped, and `../glossary.md` says so.

**This closes `0005`'s deferral rather than reversing it.** `0005` chose a
wrapper type explicitly so that exhaustion would have somewhere to live, and
accommodated both answers without picking one. It picked the container; this
picks the contents.

**This does not decide cost control.** Whether a budget can halt a proceeding
mid-round is still open in
[`../design/tribunal.md`](../design/tribunal.md#open-questions). What is now
fixed is where its answer would sit: a `UsageLimits` pass-through would either
let `UsageLimitExceeded` propagate or wrap it as a `ProceedingFailed` — and
which of those is right depends on whether a budget stop is a finding about the
case or a fact about the caller's wallet, which is the same line drawn here.

**`ConfigurationError` names something the design already asserted.**
`../design/api.md` said a missing or unknown key in the `advocates` mapping is
"an error at construction" without naming a type. It is not a proceeding
failure — there is no transcript, because nothing ran — so it sits beside
`ProceedingFailed` rather than under it.

**Cost: one more concept than the optional had.** `Undecided`, `Outcome`,
`EnbancError`, `ConfigurationError`, and `ProceedingFailed` are five exported
names where `Ruling | None` was zero. Accepted, because the alternative is a
surface on which an outage and a hung proceeding and a clean denial are all
reachable through the same attribute.
