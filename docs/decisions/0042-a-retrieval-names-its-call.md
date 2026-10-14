---
status: accepted
updated: 2026-10-14
---

# 0042. A retrieval names its call

## Context

[`0019`](./0019-the-ledger-is-part-of-the-record.md) put every source an
advocate's tools returned on the transcript, so the record answers *what was
left out?* as well as *what was this decided on?*. Each `Retrieval` carried who
made the call, in which round, with which tool, and what came back.

It did not carry what was asked. A tool that returns `Source`s gives each one a
`reference` that points at the document — a result URL, an `s3://` key — and
the call that produced it, `web_search(query="…")`, was rendered by the
ledgering wrapper, put at the head of the tool result the advocate read, and
then dropped. It survived only where the reference *was* the call: an anonymous
source, or a `ToolFailure`.

Writing the first runnable guide made the gap concrete. Listing an advocate's
tool calls from the transcript — who, which tool, the input, the output — could
fill every column but the input. For an audit artifact that is the column that
matters most for a search: a reviewer holding the record could see that the
approving advocate found two trade-press articles, and could not see whether it
searched for the employer's stability or for its layoffs. The advocate's own
context held that string; the record did not, which is the shape of gap the
transcript invariant exists to close.

## Decision

**`Retrieval` gains a required `call: str`**: the call that produced the row,
rendered by the same `render_call` that writes the tool result's header and a
failed call's `reference` — `find_filings(applicant="A. Okonkwo")`. Every row a
call produced carries the same string. `tool` stays beside it as the field a
caller filters on, the same split `ToolFailure` makes between `tool` and
`reference`.

**`## The ledger` renders it** on one line per row, between the reference and
the content: `via {call} in round {n}`. An anonymous source drops the line,
because its reference already is the call. The tool result the advocate reads
is unchanged — the call is already its header.

**`p1` is amended rather than bumped.** The render format is part of the
procedure ([`prompting.md`](../design/prompting.md#procedure-versions)), and the
rule is that changing it is a new version. That rule protects transcripts that
claim a version. `0.1.0` has not shipped, so no transcript outside development
claims `p1`, and bumping now would ship `0.1.0` with a `p1` row nobody ever ran.
From the first release on, the rule holds as written.

## Consequences

- A reviewer can read what each advocate asked for beside what it got back, and
  judge whether a search was fair as well as whether a find was buried.
- The record now holds the call string the advocate read, closing part of the
  `ToolCallPart` / `ToolReturnPart` escape
  [`testing.md`](../design/testing.md#the-transcript-invariant) enumerates. The
  escape itself stays: the message parts are still not byte-identical to the
  ledger rows.
- The field is required, with no default. A transcript serialized before this
  change no longer validates; none exists outside development, and a default
  would make a row that does not say how it was produced representable.
- The ledger grows by one line per named source. The cost is a few dozen bytes
  per row beside content that is usually far larger.
- A call's arguments are kept only as rendered text, so finding every search
  for a term means matching a string, not reading a field.

## Alternatives considered

- **Structured `args: dict[str, Any]`.** Easier to query, but it duplicates what
  the rendered string says, has to be re-rendered for every display, and would
  not be the bytes the advocate read — the property that makes the record and
  the context agree by construction.
- **Grouping the ledger under one header per call.** Reads like the tool result,
  but two identical calls in one round would merge into one group, and the row
  shape the exhibits block and the tool result share would diverge.
- **Capturing arguments in the caller's code**, by wrapping each tool. Possible
  today, and wrong: it moves part of the audit record out of the transcript and
  into whatever the caller remembered to log.
- **Bumping to `p2`.** The literal rule, rejected for this one change because
  nothing has shipped under `p1`; see the Decision.
