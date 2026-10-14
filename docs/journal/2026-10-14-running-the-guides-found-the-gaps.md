---
status: current
updated: 2026-10-14
---

# Running the guides found the gaps

Writing `docs/guides/loan_assessment.py` and `docs/guides/content_moderation.py`
was meant to be the easy end of the plan: the public surface was complete, so a
guide would only arrange calls that already existed. Running each against a real
model turned up four things neither the design nor the offline suite had shown.
It is the sixth instance of the pattern the earlier entries record: running the
artifact finds what reviewing it does not.

## What was decided

- **The ledger records the call.** Asking a guide to list each tool call — who,
  the input, the output — found that `Retrieval` kept everything but the input.
  A `Source`'s reference points at the document, so the record showed what a
  search *found* and not what it *asked*, though the advocate's own context held
  the string. Split out as its own PR before the guide merged (#32,
  [`0042`](../decisions/0042-a-retrieval-names-its-call.md)), with `p1` amended
  rather than bumped because nothing had shipped.
- **A live test closes the model too.** The first `e2e` run passed and then
  failed the session: an OpenAI HTTP client outlived pytest's per-test event loop
  and surfaced as a `ResourceWarning` under `filterwarnings = ["error"]`. No live
  test had made a model request before. `closed_models` in `tests/conftest.py`
  wraps `infer_model` and enters and exits each built model afterwards;
  `closed_after` moved beside it from the integration tier.
- **A case must be built to be argued, and checked by running it.** Both guides'
  first cases were too easy for the procedure to show anything. The loan
  statute let any documented income count, and `DENY` conceded at once; with no
  loan quote on file the judge then denied on the undocumented payment instead
  of the dispute. The moderation guide's weed-killer post had a checkable false
  claim, and `ALLOW` conceded in every run.

## Alternatives rejected

- **Wrapping tools in the guide to log their arguments.** Possible without any
  library change, and wrong: it would teach readers to work around a gap in the
  audit record in the file meant to sell it.
- **Structured `args` on `Retrieval`, and grouping the ledger by call.** Both in
  `0042`.
- **Pinning `pydantic-ai`'s floor to 2.56.0.** The guide's default
  `openai:gpt-6-luna` is unknown to 2.36.0 and unpriced by `genai-prices` 0.1.4,
  so its cost cap could not be enforced; the lockfile moved instead and the
  floor stayed, because the library needs nothing newer.

## Dead ends

- **Fixing a too-easy case by only rewording the statute.** The canning case
  with a neutral judge still saw `ALLOW` concede in one of two runs. What held
  was one guidance line shared by every advocate — argue the strongest
  good-faith reading, concede only if none exists — after which all three
  argued in each of three runs.
- **`hear_stream` output labelled by verdict value.** A value like
  `escalate to a human moderator` makes `…/s7` unreadable; the loop prints the
  member name.

## Found, not settled

Two gaps the guides exposed and nobody has filed in `docs/design/`:

- **A `Ruling` names no evidence.** It carries `verdict` and `reasoning` only, so
  "what the judge relied on" is an inference from prose. The moderation guide
  prints what the judge *saw* — every filed exhibit — and says so.
- **An exhibit's excerpt is not checked against its source.** One live excerpt
  rewrote "it can build up in the soil" as "salt can build up", unmarked. The
  design accepts this as findable rather than prevented; nothing finds it yet.
