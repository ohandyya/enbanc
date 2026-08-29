---
name: create-pr-summary
description: Write a PR title and description for the current branch to local/pr_summary.md, ready to copy into GitHub. Use when the user asks for a PR summary, PR description, to describe this branch, to write up the changes for a pull request, or says "create pr summary".
---

# Create a PR summary

Reads the current branch's committed changes and commit messages, then writes
`local/pr_summary.md` at the repo root: a one-line title plus a PR description the user
copies into GitHub's two fields by hand.

This skill **only writes the file**. It never commits, pushes, or touches a PR on
GitHub — the user does that themselves.

`local/pr_summary.md` is already in `.gitignore`, so it stays a local scratch file.

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

## Step 3 — Write `local/pr_summary.md`

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

## Step 4 — Report

Tell the user the file was written, show them the title, and note anything they need to
know before pasting: uncommitted files excluded, an unusually large diff, or a Testing
section that says nothing ran.

## Rules

- Overwrite `local/pr_summary.md` entirely; never append.
- Never run `gh pr create`, `gh pr edit`, `git commit`, or `git push` from this skill.
- Never commit `local/pr_summary.md`. It is gitignored — keep it that way.
- Do not describe uncommitted changes as part of the PR.
- Do not claim tests passed unless a run is actually in evidence.
