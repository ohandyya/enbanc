---
name: create-pr-summary
description: Write a PR title and description for the current branch to pr_summary.md, then offer to apply it on GitHub — updating an existing PR's title and description, or opening a new PR — and stamp the matching docs/implementations/ document with the PR number. Use when the user asks for a PR summary, PR description, to describe this branch, to write up the changes for a pull request, or says "create pr summary".
---

# Create a PR summary

Reads the current branch's committed changes and commit messages, then writes
`pr_summary.md` at the repo root: a one-line title plus a PR description. Step 5 then
offers to put that title and description onto GitHub directly, and Step 6 records the PR
number in the `docs/implementations/` document that planned it.

Steps 1–4 are read-only — they write `pr_summary.md` and change nothing else. **Step 5 is
the only step that touches GitHub**, it runs `gh` and `git push` only after the user
confirms, and the user can decline it and keep the file alone. Step 6 edits documents in
the repo and runs only if Step 5 produced a PR number.

`pr_summary.md` is already in `.gitignore`, and stays uncommitted either way.

## Step 1 — Establish scope

```bash
git rev-parse --abbrev-ref HEAD          # current branch
git status --porcelain                   # note if dirty, but do not summarize it
git log main..HEAD --oneline             # commits this PR would contain
git diff main...HEAD --stat              # files touched (three dots = merge-base)
```

Always use the **three-dot** form `main...HEAD` for diffs — it compares against the
merge base, so changes that landed on `main` after the branch started do not leak in.
Two-dot `main..HEAD` is correct for `git log` and wrong for `git diff`.

Stop and report, without writing the file, if:

- **The branch is `main`** — there is nothing to summarize. Ask which branch they meant.
- **`git log main..HEAD` is empty** — no commits to describe. If the working tree has
  uncommitted work, say so: it will be summarized only after they commit it.

If the working tree is **dirty**, carry on but tell the user at the end which files were
excluded. Uncommitted work is deliberately out of scope — a PR contains commits, and a
summary that describes unstaged code describes something reviewers cannot see.

## Step 2 — Read the change

Read both halves. They answer different questions.

```bash
git log main..HEAD --format='%h %s%n%b'  # commit messages — the "why"
git diff main...HEAD                     # the actual change — the "what"
```

The diff is the source of truth for *what* changed; commit messages are the best
available evidence of *why*. Where they disagree, trust the diff and describe the code.

For anything the diff alone does not explain — a function whose callers are elsewhere, a
config value consumed somewhere else, a removed branch of logic — **read the surrounding
files** to see how the changed code is used. Grep for a renamed symbol before claiming a
rename is complete. A summary that misdescribes a change is worse than a short one.

If the diff is large, work file group by file group and keep notes, rather than
skimming the whole thing at once.

## Step 3 — Write `pr_summary.md`

Overwrite the file completely. Never merge with, append to, or preserve anything from a
previous run — a stale section from an earlier branch is a real hazard here.

Exact layout:

```markdown
## Title

<one line, imperative mood, no trailing period>

---

## Description

### Summary

<2–4 sentences: what this PR does and why, in terms a reviewer who has not seen the
branch can follow.>

### What changed

- `path/or/area` — what changed there and why
- `path/or/area` — ...

### Why

<The motivation: the problem, bug, or requirement behind the change. Skip this section
if the Summary already fully covers it.>

### Testing

<What was run and what it showed — or state plainly that nothing was run.>

### Notes

<Risks, follow-ups, deliberate omissions, anything a reviewer should look at closely.>
```

Rules for the body:

- **Omit any section with nothing real to say.** An empty or filler section costs the
  reviewer time. Summary and What changed are effectively always present; Why, Testing,
  and Notes come and go.
- **Never invent a Testing section.** If no test run is visible in the conversation or the
  diff, write what the branch's tests cover, or say "No tests were run as part of this
  change." Do not claim a suite passed.
- Group What-changed bullets by area or concern, not one bullet per file, when several
  files serve one purpose.
- Describe behavior, not diff mechanics. "Retries 429s with exponential backoff" beats
  "added a `for` loop in `judge.py`".
- Reference files as inline code spans (`` `src/enbanc/judge.py` ``) — this file is
  destined for GitHub, where the repo-relative link syntax used in chat does not apply.
- Write for a reviewer who knows the project but not this branch. No first person, no
  "I refactored"; describe the change, not the process of making it.

### The title

One line, imperative mood, ideally under ~70 characters. It should name the change, not
the area: "Add retry backoff to the judge loop", not "Judge loop changes" or "Updates".
If the branch is one coherent change, the title is that change; if it is several, the
title names the largest and the Summary covers the rest.

## Step 4 — Report the file

Tell the user the file was written, show them the title, and note anything they need to
know before it goes anywhere: uncommitted files excluded, an unusually large diff, or a
Testing section that says nothing ran.

Then continue to Step 5 — do not stop here.

## Step 5 — Put it on GitHub

Offer to apply the title and description to a PR. Everything in this step is confirmed
with the user first; nothing here runs silently.

### Preconditions

```bash
gh auth status                    # not authenticated?
git remote get-url origin         # no remote?
```

If either fails, report it and stop **without** treating the run as failed — `pr_summary.md`
is written and is still the deliverable. Say so explicitly.

### Find the PR

`gh pr view` exits non-zero when the branch has no PR, so tolerate the failure rather than
reading it as an error:

```bash
gh pr view --json number,title,url,state,isDraft,body 2>/dev/null
```

Then ask with `AskUserQuestion`. Every variant includes a **Skip — file only** option, and
choosing it is a clean, complete ending:

| What `gh pr view` showed | Options, recommended first |
|---|---|
| An **`OPEN`** PR | *Update PR #N* — quote its number, title, and URL / *Create a new PR* / *Skip* |
| **Nothing** | *Create a new PR* / *Update an existing PR* (then ask which number) / *Skip* |
| A **`MERGED`** or **`CLOSED`** PR | Say which it is, then *Create a new PR* / *Skip*. Never default to updating a PR that is no longer open. |
| **Any other failure** | Fall back to asking whether a PR exists and, if so, for its number |

### Build the body file

The PR body is the **Description only**. Everything from `## Title` down to and including
the `## Description` heading is scaffolding for the local file and must not reach GitHub —
the body starts at `### Summary`.

Write that portion to a temp file in the session scratchpad directory — **never inside the
repo** — and pass it as `--body-file`. Use `--body-file` rather than `--body`: the body
contains backticks, quotes, and blank lines that do not survive a shell argument intact.

### Update an existing PR

Check the `body` field from `gh pr view` first. `gh pr edit` **replaces the description
wholesale**, so if the current body holds hand-written content — a checklist, review notes,
a linked issue — show the user what will be lost and confirm before overwriting.

```bash
gh pr edit <N> --title "<the title line>" --body-file <scratchpad>/pr_body.md
```

### Create a new PR

`gh pr create` needs the branch on `origin` first:

```bash
git rev-parse --abbrev-ref --symbolic-full-name @{u}   # fails → branch was never pushed
git log @{u}..HEAD --oneline                            # non-empty → commits not on origin
```

If either shows work missing from `origin`, tell the user exactly what will run and get a
yes before running it:

```bash
git push -u origin HEAD
```

Then open it — ready for review, not a draft:

```bash
gh pr create --base main --title "<the title line>" --body-file <scratchpad>/pr_body.md
```

If this fails because a PR already exists for the branch, do not retry — report the
existing PR and offer to update it instead.

### Report

Say which PR was created or updated, and give its URL. Then continue to Step 6.

## Step 6 — Stamp the implementation doc

Only when Step 5 actually created or updated a PR. If the user chose **Skip — file only**
there is no number to write, so stop after Step 5.

[`docs/implementations/`](../../../docs/implementations/README.md) holds one document per
planned PR. Opening a PR is the moment two facts about that document become knowable for
the first time: its number, and that the work is built rather than planned.

### Find the matching document

```bash
head -6 docs/implementations/*.md        # status: and pr: for each
git rev-parse --abbrev-ref HEAD          # the branch usually names it
```

Consider only documents that are **`status: draft` and carry no `pr:`**. Match on the
branch name and on whether this PR's diff delivers what that document's `Scope` describes.

**Propose one and confirm with `AskUserQuestion` before editing.** Name the document, say
what in the diff matches it, and offer the other draft documents plus a *None of these*
option. Never infer silently — stamping the wrong document is a false record of what a PR
built, and nothing downstream will catch it.

If none matches — a release PR, a docs fix, a hotfix — say so in one line and stop. That is
the common case and is not a failure.

### Make the three edits

They are one unit of work. The third is the one that gets skipped, and
[the README](../../../docs/implementations/README.md) says outright that it is the edit
that earns deferring `Files` and `Tests` in the first place.

1. **The document's frontmatter** — `status: current`, add `pr: <N>`, set `updated:` to
   today.
2. **The plan table** in `docs/implementations/README.md` — that row's `PR` column gains
   the number and its `Status` column becomes `current`.
3. **Every document listing this one under `Depends on`** — re-read its `Scope` against
   what the build actually taught.

```bash
grep -l "(\./<doc>\.md)" docs/implementations/*.md    # who depends on it
```

For the third edit, **report and ask rather than rewriting**. Name each dependent document
and say either that its `Scope` still reads true or exactly what the build invalidated in
it. A scope correction is a judgment about the plan, and it is the user's to make.

### Say what was assumed

Stamping at open rather than at merge buys the number and the status in the one session
that holds both, and it costs an assumption. **State it plainly in the report** — do not
let it pass silently:

> Marked `docs/implementations/<doc>.md` as `current` with `pr: <N>`, assuming #<N> merges
> essentially as it stands. If review changes the shape of the PR, that document is what
> needs correcting before it lands.

## Rules

- Overwrite `pr_summary.md` entirely; never append.
- Never commit `pr_summary.md`. It is gitignored — keep it that way.
- Do not describe uncommitted changes as part of the PR.
- Do not claim tests passed unless a run is actually in evidence.
- Never `git commit` from this skill. Step 5 pushes commits that already exist; it never
  creates one, and it never pushes uncommitted work.
- Push only after the user confirms, and only the current branch to its own name on
  `origin`. Never force-push.
- Never `gh pr merge`, `gh pr close`, or `gh pr ready`. This skill writes a title and a
  description; it does not change a PR's state.
- Never write the body file inside the repo.
- **Skip is a valid answer.** If the user declines Step 5, stop cleanly — the file is the
  deliverable and the run succeeded, and Step 6 does not run.
- Never stamp an implementation doc without confirming the match with the user first.
- Never touch a document that is already `current` or `superseded`, or one that already
  carries a `pr:`. Those record a PR that is not this one.
- Never rewrite a dependent document's `Scope` unprompted — name the drift and ask.
- Never commit the document edits. The user stages their own work, here as everywhere.
