---
status: current
updated: 2026-10-14
---

# Guides

**Each guide is one Python file you can run.** Not a page about `enbanc`: the shortest
program that uses it to make one real decision, with comments explaining why each piece is
there. Read it top to bottom, then run it.

| Guide | The decision | What it teaches | Reads |
|---|---|---|---|
| [`loan_assessment.py`](./loan_assessment.py) | Approve or deny a $60,000 personal loan | The core loop: verdicts, statute, case; one advocate per answer with its own tools; writing your own tool that returns citable `Source`s; reading the audit trail, including every tool call with its input; handling `Ruling` and `Undecided`; a cost budget | `OPENAI_API_KEY`, `TAVILY_API_KEY`; optionally `ENBANC_MODEL` |
| [`content_moderation.py`](./content_moderation.py) | Allow, remove, or escalate a flagged forum post | Watching a proceeding live with `hear_stream`; matching on each filing as it arrives — argument, concession, the judge's questions, the answers, the ruling; three verdicts and so three advocates, with a verdict's value carrying its meaning | `OPENAI_API_KEY`, `TAVILY_API_KEY`; optionally `ENBANC_MODEL` |

```sh
uv run docs/guides/loan_assessment.py
uv run docs/guides/content_moderation.py
```

`ENBANC_MODEL` takes any pydantic-ai model string — `anthropic:claude-sonnet-5`,
`google-gla:gemini-2.5-pro` — with that provider's own key in place of `OPENAI_API_KEY`.

## What a guide is

- **One file, runnable as it stands.** No local imports, no CLI arguments, no helper module
  beside it. A guide that needs a second file has become an application.
- **Run by the `e2e` tier, every one, on every live run.** `tests/e2e/test_guides.py` loads
  each file from this directory and awaits its `main()`, so what a reader runs is what CI
  proves. A script nothing executes is a snippet, and snippets rot.
- **A different use, and something new.** Each guide is a different real decision, and each
  after the first shows at least one part of the surface no earlier guide did — the same
  three calls with a different noun is a file to maintain for nothing.

Design intent belongs in [`../design/`](../design/), not here. A guide shows how to use
`enbanc`; the design documents say what it is.
