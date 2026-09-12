---
name: walkthrough
description: Walk the user through code an agent wrote, one logical step at a time, pausing after each step so they can read the files and ask follow-ups. Use when asked to walk through, explain, or step through recent changes, a commit, a branch, or uncommitted work — or when the user says they want to understand what was just written.
---

# Walk a human through the changes

The user did not write this code — you did, or another agent did, possibly in a session
this one remembers nothing about. They are reading it to *own* it, not to approve it. That
inverts the usual reporting job: the goal is not to summarize what happened, it is to hand
over understanding, in the order a person can absorb it, at a pace they set.

**Read-only.** Do not edit, fix, stage, or commit anything during a walkthrough. If the user
wants a change made, that is a separate request after the walkthrough ends.

**This is not a code review.** `/code-review` exists and finds bugs. This skill explains.
See [§8](#8-when-the-code-looks-wrong) for the one narrow exception.

**This repo can tell you *why*.** Most codebases cannot, so most walkthroughs guess at
intent. Here `docs/design/` is the spec, `docs/decisions/` says why a shape was chosen, and
`docs/implementations/` says what one PR was meant to build. Use them —
[§2](#2-find-the-why-before-you-write-the-steps) is the step that separates a good
walkthrough in this repo from a narrated diff.

## 1. Establish the scope

**Look before you ask.** `CLAUDE.md` forbids opening with `AskUserQuestion`, and it is right
to: a scope question asked cold makes the user do the triage.

```bash
git rev-parse --abbrev-ref HEAD
git status --porcelain
git log --oneline -10
git diff main...HEAD --stat          # three dots — from the merge base
```

Then say in prose what you found — the branch, whether the tree is dirty, how many commits
and files are in play — and ask. Recommend one and mark it `(Recommended)`; put each
option's actual diffstat in its `preview` so the user is choosing between sizes, not labels.

| Option | Command | Note |
| --- | --- | --- |
| **Uncommitted work** | `git diff` **plus** `git ls-files --others --exclude-standard` | The second half is not optional. New files an agent just wrote are untracked and appear in *neither* `git diff` nor `--cached`. Omitting them silently drops the most important changes |
| **Staged work** | `git diff --cached` | |
| **The most recent commit** | `git show HEAD` | |
| **This branch vs. `main`** | `git diff main...HEAD` | Three dots. Usually right on a feature branch, and the same scope `create-pr-summary` uses |
| **Pick specific commits** | see below | |

For **pick specific commits**, print `git log --oneline -25` as a plain list and ask the
user to reply with hashes or a range (`d6dcfd4..HEAD`). Do not try to squeeze commits into
`AskUserQuestion` — it caps at four options and the list is always longer.

**Skip the question entirely when the user already answered it** — "walk me through the last
commit", or a session that just built one branch. `CLAUDE.md` rule 7: a question is not a
checkpoint to clear. Decide, and say in one line what you assumed.

Then read the full diff for the chosen scope. **Read the actual files too, not only the
diff.** A diff shows what moved; it does not show what the surrounding module now does, and
you cannot explain a change you only saw as a hunk.

## 2. Find the *why* before you write the steps

Read these before carving up anything. Each answers a question the diff cannot.

| Read | Tells you | Trust level |
| --- | --- | --- |
| [`docs/implementations/`](../../../docs/implementations/) — the doc for this PR | What this slice was *meant* to build, in what order, and what it deliberately left out | A **plan**, never a spec. After merge it is history |
| [`docs/design/`](../../../docs/design/) — the sections that doc names under `Implements` | How the system is meant to work. The source of every "why" you will give | **Current truth** |
| [`docs/decisions/`](../../../docs/decisions/) — ADRs the code or design cites | Why a shape was chosen and what was rejected | Immutable, and the best material in the repo for a walkthrough |
| [`docs/glossary.md`](../../../docs/glossary.md) | The courtroom vocabulary: filings, continuance, interrogatory, tribunal | Current |

Find the implementation doc by branch name, or by `Scope`:

```bash
head -8 docs/implementations/*.md          # status:, updated:, pr:
```

Two ways this pays off, and both are repo-specific:

- **A step's `Purpose` comes from the design doc, not from your reading of the code.** Link
  the section. "This exists because [`api.md` § Schemas](docs/design/api.md#schemas) requires
  an invalid record to be unrepresentable" beats any intent you could reconstruct.
- **A shape that looks arbitrary usually has an ADR.** Underscore-prefixed modules are
  [`0034`](../../../docs/decisions/0034-the-export-surface-is-the-package.md); injected models are
  [`0003`](../../../docs/decisions/0003-models-and-guidance-are-injected.md); the test tiers are
  [`0031`](../../../docs/decisions/0031-tests-are-tiered.md). Cite it rather than explaining it twice.

**Where the plan and the code disagree, the code is what shipped.** Note the drift in one
line inside the step it belongs to and keep walking — chasing it is [§8](#8-when-the-code-looks-wrong)'s
rule, not a detour. Where the *design doc* and the code disagree, that is a bigger deal
(`CLAUDE.md` rule 2 puts the design update in the same commit), but it is still one line
during a walkthrough. Gather it at the end.

Never read `notes/` or `local/`. Those reads are denied in `.claude/settings.json` and are
human-only.

## 3. Break it into steps

This is the part that makes the walkthrough worth doing, and the part most likely to be done
lazily. A file-by-file or commit-by-commit listing is not a walkthrough — the user could
have run `git show` themselves.

**Order the steps by dependency and narrative, not by path, not by commit order, not by
size.** The spine that usually works in this package:

> types and their invariants → the logic that moves them → how it is wired together →
> the export surface → configuration and packaging → docs

Ask of every ordering: *could someone understand step N without having read step N-1?* If
not, N-1 comes first, whatever the commit history says. The implementation doc's own order
is a strong first draft of this — it was written to be built in order — but it is a build
order, and a reading order is not always the same thing.

Rules that hold:

- **A step is one idea, not one file.** A step routinely spans several modules (a new type
  and the three filings that carry it); one module routinely appears in two steps (it gained
  two unrelated things).
- **3–7 steps.** Below three, just explain it in one pass and say so. Above eight, the scope
  is too big to absorb in one sitting — say so, and offer to split it or walk a subset.
- **Tests fold into the step they pin.** Present the behavior, then what locks it: *"here's
  the rule, and here's the test that fails if it breaks."* A test explained apart from its
  subject teaches nothing. Name its tier and what the tier means —
  [§5](#5-the-shape-of-each-step) has the wording.
- **The export surface is a real step, not churn.** A change to `__all__` or to
  `src/enbanc/__init__.py` is a change to the public contract
  ([`0034`](../../../docs/decisions/0034-the-export-surface-is-the-package.md)), and
  `tests/unit/test_export_surface.py` is what makes that deliberate. Treat it as an idea,
  usually late in the walk.
- **Docs get one small step at the end**, if the scope touched any. In this repo that step
  is worth more than it looks: a design-doc edit *is* a behavior change under `CLAUDE.md`
  rule 2, and an ADR is the reasoning the code cannot carry.
- **Collapse mechanical churn.** `uv.lock`, ruff reformatting, import reshuffles, and
  version bumps are one step at most, often a single line in the map saying they exist and
  can be skimmed. Never spend a real step on a lockfile.

Write the step plan to a file in the session scratchpad directory before starting — never
inside the repo. A walkthrough spans many turns and may outlive this context window; the
plan is what lets you resume mid-way without renumbering or losing a step.

## 4. Step 0 — the map

Open with the shape of the whole thing, so the user knows what they are committing to and
can jump:

1. **One paragraph**: what this change set does and why it exists, and which
   `docs/design/` area it serves. Not a file inventory.
2. **Vocabulary, but only if it is load-bearing.** If the change introduces domain terms the
   user may not hold — *continuance*, *interrogatory*, *filing*, *exhibit* — give them one
   line each from [`docs/glossary.md`](../../../docs/glossary.md) here. Three terms at most;
   this is a courtesy, not a lecture, and a term the user already uses does not need
   defining back at them.
3. **The numbered step list**, one line each, titles only.
4. **The count** — "5 steps" — and a note that they can say *"skip to step 3"* or *"stop"*
   at any point.

Then pause. Do not run step 1 in the same turn. The map is itself a step the user gets to
react to, and it is where they redirect you if you carved the change up wrong.

## 5. The shape of each step

Every step, without exception, has these five parts in this order:

**1 — Where you are.** `**Step 2 of 5 — <short title>**`. Always. The user has been reading
files between turns and has lost the thread; this is one line and it restores it.

**2 — Purpose.** What problem this step solves, in two or three sentences, and the design
section or ADR it comes from. Lead with the *why*. A user who understands why a change
exists can read the code themselves; one who doesn't is just proofreading syntax.

**3 — The change itself.** Prose, plus the **three to ten lines that carry the idea** — the
one model field and its validator, the one signature, the one constraint that makes an
invalid state unrepresentable. Never paste a whole hunk. They are about to read the file;
quoting it back to them wastes the turn. Quote the line that would otherwise take them five
minutes to find.

**4 — What to read.** Markdown links, in reading order, each with a note on what to look for
and which to open first:

> Read [_verdicts.py:37](src/enbanc/_verdicts.py#L37) first — `VerdictT`, and why the bound
> is `Verdict` rather than `Enum`. Then [_filings.py:23](src/enbanc/_filings.py#L23) for the
> first filing that binds it.

Bare file lists are the failure mode here. "Read these four files" makes the user do the
triage the step was supposed to do for them.

When the step includes a test, say what its tier means rather than only naming it — the tier
*is* the claim ([`0031`](../../../docs/decisions/0031-tests-are-tiered.md)):

> [tests/unit/test_filings.py](tests/unit/test_filings.py) pins `enbanc`'s own behavior and
> runs offline — a socket guard enforces that. Run it with `make unit-tests`.

> [tests/contract/test_max_concurrency_is_set_at_construction.py](tests/contract/test_max_concurrency_is_set_at_construction.py)
> pins a claim `docs/design/execution.md` makes about `pydantic-ai`. If it goes red, the
> dependency moved — `enbanc` did not break.

**5 — The pause.** One short line inviting them to read, and to say *next* when ready.

## 6. The pause is the whole point

**End your turn after each step. Every time.**

This is the rule the skill exists to enforce, and the one an agent will erode first — two
steps look adjacent, or a step feels "too small to stop on," or you have already loaded the
files so continuing feels efficient. It is not efficient. It defeats the entire purpose: the
user is reading source code between your turns, and a turn containing steps 2 and 3 means
step 3 is read with no memory of step 2's files.

Concretely:

- One step per turn. Never two, no matter how small.
- End with no pending tool calls and nothing queued.
- Never anticipate. Do not add "and in the next step we'll see…" — the next step is theirs
  to ask for.
- **Only these advance the walkthrough: an explicit "next", "continue", "go on", or a jump
  like "skip to step 4".** A follow-up question is not permission to advance. Silence is not
  permission. A "thanks, that makes sense" is not permission — answer, then wait.

## 7. Follow-up questions

Answer them fully, then **stay in the current step**. End by restoring position: *"Still on
step 2 of 5 — say next when you're ready."*

Follow-ups are the walkthrough working, not an interruption of it. A question that pulls in
a file outside the current scope is fine — go read it and answer. Do not steer back to the
script; the user's question is better evidence of what they need than your step plan is.

If a follow-up reveals a step landed badly, re-explain it differently rather than defending
the first attempt. And when you don't know — an agent wrote this, possibly not in this
conversation — go read `docs/design/` and `docs/decisions/` before answering, and if the
reason is genuinely not recorded anywhere, **say so rather than reconstructing plausible
intent.** "I can see what this does, and nothing in the design docs accounts for why it was
written this way" is a useful and honest thing for the user to hear — and in this repo it is
also a finding, because a binding choice with no ADR is a gap.

Running the **offline** suite to answer a question is fine — `make unit-tests`,
`make contract-tests`, `make test`, `make typecheck` are free and reach nothing. **Never run
`make integration-tests` or `make e2e-tests`**: those hit real providers and cost the user
money, and nothing in a walkthrough justifies that.

## 8. When the code looks wrong

Flag it in **one line**, inside the step, then keep walking:

> ⚠️ Worth noting: this validator rejects the empty list but not a list of duplicates —
> probably fine given the one caller, but you may want to check. Not chasing it now.

Then continue. Do not open an investigation, do not fix it, do not stack up a findings list.
The user decides whether it's worth chasing; if they say so, chase it, and resume the step
afterward.

The same one-line treatment covers the two drifts this repo makes visible: code that
contradicts [`docs/design/`](../../../docs/design/), and code that diverges from the
[`docs/implementations/`](../../../docs/implementations/) doc that planned it. Both are
worth naming and neither is worth a detour.

Bugs are not the job here. A walkthrough that turns into an audit stops being a handover.

## 9. Finish

After the last step, close in a few lines:

- **The through-line** — the one or two sentences that tie the steps together, now that
  they've seen all of them. This is the part they'll remember a week from now.
- **What you skipped** and why (lockfiles, churn, anything out of scope).
- **Any ⚠️ flags** from [§8](#8-when-the-code-looks-wrong), gathered in one place, so they
  aren't scattered across turns. Separate the design-doc contradictions from the rest — those
  are the ones with a rule attached.
- **Where this sits in the plan** — one line, from
  [`docs/implementations/README.md`](../../../docs/implementations/README.md): which numbered
  row this was and what unblocks next.

Nothing else. Do not offer next actions, do not commit, and do not write to
[`docs/progress.md`](../../../docs/progress.md) or [`docs/journal/`](../../../docs/journal/)
— those belong to [`wrap-up`](../wrap-up/SKILL.md), and a walkthrough is not a session
checkpoint.

## Rules

- Read-only. Never edit, stage, or commit during a walkthrough.
- Never run the live test tiers. They cost money.
- Never read `notes/` or `local/`.
- One step per turn, and end the turn. A question is not permission to advance.
- Never invent a rationale. Read `docs/design/` and `docs/decisions/` first; say "not
  recorded" if it isn't.
- Never treat `docs/journal/` as current truth, and never read a `docs/implementations/` doc
  to learn how the system behaves now — the code is the truth about the code.
- Never spend a step on generated files or formatting churn.
- Never let the walkthrough become a review. One line per flag, then keep walking.
