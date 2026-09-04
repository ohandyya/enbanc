---
status: draft
updated: 2026-09-04
---

# Degenerate deliberations

**PLACEHOLDER — not yet designed. Left for future: not needed for `0.1.0`.**

These are behaviours the schemas in [`api.md`](./api.md) permit but no document
rules on. They are one-paragraph answers each, and the right home for each
answer is an ADR in [`../decisions/`](../decisions/) plus a sentence in
[`tribunal.md`](./tribunal.md) — not this file. It exists so the questions are
not lost, and it should be deleted once they are answered.

Not MVP-blocking: none of them changes a type, and each can be settled at the
moment the implementation first reaches it.

## The holes

- **An empty `Continuance`.** `interrogatories: list[Interrogatory[VerdictT]]`
  admits `[]`. A judge that files one burns a round with nothing dispatched and
  nothing filed, and repeats until `max_rounds` is spent. Whether that is a
  validation failure, a silently-tolerated no-op round, or something the
  procedural prompt is trusted to prevent, is unsettled.
- **An interrogatory to an advocate that conceded.**
  [`tribunal.md`](./tribunal.md#constraints-that-define-the-design) implies it
  is allowed — "an advocate persuaded by the record it reads in a later round
  says so in its response" — but never says a conceded advocate stays
  addressable, and nothing states whether a concession is revisable.
- **Two interrogatories to the same advocate in one round.**
  [`api.md`](./api.md#what-participants-file) says the judge is free to do it
  and that the dispatch is one run per interrogatory. What that means for the
  advocate's single message history — two runs against one conversation, in
  what order, seeing what of each other — is the
  [`execution.md`](./execution.md) question this touches.

## Open questions

*Not yet opened.* Settling any of these is rule 7 in
[`../../CLAUDE.md`](../../CLAUDE.md): the answer into
[`tribunal.md`](./tribunal.md), an ADR recording why, indexed in
[`../README.md`](../README.md).
