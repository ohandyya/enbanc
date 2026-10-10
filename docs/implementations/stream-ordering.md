---
status: draft
updated: 2026-10-10
---

# The stream never runs behind the record

**What the live handle promises, made true for a consumer that does real work.**
A consumer holding entry *N* finds *N* at `proceeding.transcript[-1]`, however
long it spends on it, and walking away leaves the record at what the consumer
had received.

## Scope

Found while planning [`failures.md`](./failures.md), in code merged with
[`proceeding-core.md`](./proceeding-core.md). The clerk appends an entry to the
transcript and then blocks on the rendezvous send. So while a consumer is busy
with entry *N*, for example `await`ing a database write, the clerk has already
appended *N*+1:

```text
slow consumer (len, entry is transcript[-1]): [(2, False), (3, False), (4, False), (4, True)]
abandoned after seeing 1, transcript holds: 2
```

[`0010`](../decisions/0010-streaming-yields-the-record.md)'s promise, that *the
entry just received is the last entry of `proceeding.transcript`*, holds today
only for a consumer whose loop body never `await`s. Every existing streaming
test is one of those, which is why none of them caught it.

This PR changes who appends an entry, or when, so that the promise holds for
any consumer, and so that abandoning leaves the transcript at the entry the
consumer last received. **The mechanism is chosen: the clerk waits for the
consumer to ask.** `Proceeding.__anext__` sends a ready token on a second
rendezvous stream before it receives, and the clerk appends only once it holds
one. That answers
[`execution.md`'s open question](../design/execution.md#open-questions), and
settling it is that document's three moves: the answer goes into § The filing
clerk, [`0041`](../decisions/0041-the-clerk-files-when-the-consumer-asks.md)
records why and what was rejected, and the bullet leaves the list. Those land
as this PR's first commit, before its code.

A probe of both options against the defect, with three concurrent filers and a
consumer that `await`s in its body, fixed it either way:

```text
today      slow: [(2, False), (3, False), (4, False), (4, True)] | abandoned after 1, holds: 2
consumer   slow: [(1, True), (2, True), (3, True), (4, True)]   | abandoned after 1, holds: 1
ready      slow: [(1, True), (2, True), (3, True), (4, True)]   | abandoned after 1, holds: 1
```

The ready token was chosen because it leaves the clerk as the only writer, so
§ The filing clerk's first sentence and `0010`'s *the stream is a view of the
transcript being written* stay literally true. It also keeps `filed_at` as the
moment of the append and the out stream's item type as `Entry`. The rejected
option, appending in `Proceeding.__anext__`, would have the public handle write
the record, and it would stamp `filed_at` before a slow consumer appended.

Whichever mechanism is chosen, two things are fixed already and constrain it:

- **The filer's acknowledgment still means *in the record*.**
  [`0027`](../decisions/0027-an-advocate-answers-its-interrogatories-in-order.md)
  dispatches an advocate's next run on it, and
  [`round-loop.md`](./round-loop.md) built run 7's snapshot on the stamped entry
  the acknowledgment carries back.
- **One sequence for the record and the stream.** No sibling may append between
  another filer's entry and its delivery. A single owner already rules that out,
  and the fix must not reintroduce it.

**Not in this PR.** Anything about failure. [`failures.md`](./failures.md) leaves
the clerk alone, and this PR leaves the failure path alone. The one place they
meet is that a failed proceeding's transcript is also *what had been filed*, and
that follows from whatever this PR settles about abandonment.

## Implements

- [`execution.md` § The filing clerk](../design/execution.md#the-filing-clerk) —
  as amended by the answer to its open question
- [`api.md` § Watching it live](../design/api.md#watching-it-live) — *live: the
  entry just yielded is its last*, and what abandoning leaves behind
- [`outcomes.md` § 6. The same endings, watched live](../design/outcomes.md#6-the-same-endings-watched-live)
  — the walking-away case, for a consumer that awaits

## Depends on

[`proceeding-core.md`](./proceeding-core.md), merged as
[PR #26](https://github.com/ohandyya/enbanc/pull/26), which built the clerk and
the handle; and [`failures.md`](./failures.md), sequenced first only so the two
PRs do not both rewrite `proceed()` at once. Neither depends on the other's
behaviour.

## Files

**First commit: the decision, with no code.** These are rule 7's three moves,
plus the docs the answer makes untrue.

- **`docs/design/execution.md`**
  - § The filing clerk: the sketch gains `ready` and the line that waits on it:

    ```python
    async def clerk(inbox, ready, transcript, out):
        async for filing, round_no, done in inbox:
            await ready.receive()             # a consumer has asked for the next entry
            entry = Entry(round=round_no, filed_at=datetime.now(UTC), filing=filing)
            transcript.entries.append(entry)
            await out.send(entry)
            done.set()
    ```

  - The *That is not yet the whole sentence* paragraph is replaced by the answer.
    The consumer asks before it receives, so it is parked in `receive()` when the
    clerk appends, and its loop body cannot run between the append and the send.
    It asks again only once that body has finished, so *N*+1 cannot be appended
    while it holds *N*. Say why a rendezvous stream needs the second channel: it
    has no "wait for a receiver" of its own. Say why swapping the append and the
    send was not enough.
  - The acknowledgment paragraph gains one sentence: a slow consumer now holds
    the filers, because the ack waits on the consumer's ask. `0027` is unaffected,
    since the ack still follows the append.
  - `## Open questions`: the bullet goes and `*None open.*` stands in its place,
    worded as in `packaging.md`.
- **`docs/decisions/0041-the-clerk-files-when-the-consumer-asks.md`** — new. It
  covers:
  - **Context:** the defect and the probe.
  - **Decision:** the ready token.
  - **Rejected:**
    - the consumer appending on receipt: the handle writes the record, and
      `filed_at` predates the append;
    - swapping the append and the send: the receiver's body can run before the
      append;
    - a buffered out stream: the consumer runs further behind.
  - **Consequences:**
    - Abandoning by `break` or by raising leaves exactly what was received.
    - A cancel from outside can leave at most one more entry. Anyio's `send()`
      checkpoints after it hands its item to a waiting receiver. A cancel at
      that checkpoint reaches the consumer after the clerk already holds its
      token, so the clerk appends and is then cancelled on its own send. This
      gap is accepted: closing it would mean the consumer appends, which is the
      option this ADR rejects.
    - `ProceedingFailed.transcript` is what the consumer had received. For
      `hear()` that is everything filed.
    - `0010`'s *Backpressure is not a question here… entries wait in memory* was
      already false under the rendezvous stream, because the filers wait, not the
      entries. That paragraph is corrected here, not edited there.
- **`docs/README.md`** — `0041`'s row in the decisions index.
- **`docs/design/api.md` § Watching it live**
  - *Abandoning is allowed* says what is left: everything the consumer received,
    and nothing it did not.
  - A sentence states that a consumer slower than the tribunal slows the
    proceeding rather than falling behind the record.
  - A sentence states the one gap. A cancel from outside the loop, such as a
    caller's timeout, can land while the consumer is asking for the next entry.
    In that case the record may hold one entry the consumer never received.
    `break`, or an exception from the loop body, cannot reach that point.
- **`docs/design/outcomes.md` § 6** — the walking-away comment changes from
  *everything filed before you left* to *every entry you received*. The count of
  4 stands.

**Second commit: the code.**

- **`src/enbanc/_proceeding.py`**
  - **`proceed()`** creates a second rendezvous stream,
    `ready_send, ready_receive = anyio.create_memory_object_stream[None](0)`. It
    closes all four ends in its `async with`, on every path, for the same
    `__del__`-warning reason the entry stream's comment gives. `ready_receive`
    goes to `orchestrator.run`, and `ready_send` to `Proceeding`.
  - **`_Orchestrator.run(out, ready)`** passes `ready` through to the clerk.
    Nothing else in it changes: the hearing is still bound before `out` closes.
  - **`_Orchestrator._clerk(inbox, ready, out)`**
    - Opens `async with inbox, ready:` and waits `await ready.receive()` after
      taking a filing, before `Entry(...)` is built. The stamp therefore reads
      the clock when the record changes.
    - The filing is taken first and the token second, in that order, so that
      `async for filed in inbox` stays the loop. Holding a token while idle would
      behave the same.
    - The docstring's *one uninterrupted sequence* is extended to say the
      sequence starts only once someone has asked.
  - **`Proceeding`**
    - `__init__` takes `ready` as well as `entries`.
    - `__aiter__` returns `self`.
    - `__anext__` sends the token, then receives the entry.
    - `BrokenResourceError` from the send (the clerk has exited and closed
      `ready`) and `EndOfStream` from the receive (`run` closed `out`) both
      become `StopAsyncIteration`. Probed on anyio 4.14.2: a send blocked on a
      rendezvous stream raises `BrokenResourceError` when the receive end closes.
    - The class docstring's *Abandoning is allowed* paragraph matches
      `api.md`'s.
  - **The `transcript` attribute comment** (*the entry just yielded is its last*)
    stands. It is now true for any consumer.

## Tests

All in `tests/unit/`. The defect lives in the seam between the clerk and the
handle, and both are reachable offline. Each new test makes the consumer
`await anyio.wait_all_tasks_blocked()` inside its loop body instead of sleeping.
That runs every other task until it blocks, which is the most a clerk could ever
run ahead, and it does so deterministically.

- **`test_hear_stream.py`**
  - `test_a_consumer_that_awaits_still_holds_the_last_entry` covers a bench
    whose advocates file concurrently. After the await, each entry is still
    `transcript[-1]` and `len(transcript)` equals the count received. This is
    the probe's first line as an assertion, and it fails on `main`.
  - `test_walking_away_after_awaiting_leaves_only_what_was_received` awaits, then
    breaks on the first entry, and asserts `len(transcript) == 1`. It fails on
    `main` with 2.
  - `test_a_stream_never_iterated_files_nothing` enters `hear_stream()`, awaits
    `wait_all_tasks_blocked()` without iterating, and exits. The transcript is
    empty and `hearing` raises `ProceedingUnfinished`. Today the clerk appends
    entry 1 and then blocks.
  - `test_an_external_cancel_leaves_at_most_the_entry_in_hand` cancels the
    consumer from an outer scope while it waits for the next entry. Afterwards,
    `len(transcript)` is either the count received or one more, never further
    ahead. If the cancel can be landed on the post-handoff checkpoint
    deterministically, the test pins the "one more" case exactly. Otherwise it
    asserts the bound.
  - The existing abandoning and exception tests stay unchanged. They must still
    exit rather than hang, now that the clerk can also be blocked on `ready`.
- **`test_filing_clerk.py`**
  - `_file_through_the_clerk` gains the `ready` stream, and its `consume()` asks
    before each receive. It also awaits `wait_all_tasks_blocked()` before its
    `transcript[-1]` assertion, so that
    `test_each_entry_is_the_last_one_at_the_moment_it_is_yielded` bites on a slow
    consumer, not only a fast one.
  - `test_the_clerk_appends_nothing_until_a_consumer_asks` drives the clerk
    directly. It files once and waits until everything is blocked, then checks
    that the transcript is empty and the filer is unacknowledged. After one ask,
    the transcript has one entry and the filer is acknowledged.
  - `test_the_acknowledgment_still_follows_the_append`: when the filer's `done`
    fires, the stamped entry it carries back is already `transcript[-1]`. This is
    `0027`'s condition, restated against the new ordering.
- **`outcomes/test_06_watched_live.py`**
  - The module docstring drops its *loop bodies here never `await`* caveat,
    which pointed at this PR.
  - `test_walking_away_leaves_the_record_and_no_hearing` awaits in its body
    before the `break`, so the § 6 mirror covers the consumer it was written for.

There is no contract test. The one anyio behaviour this PR leans on is that a
blocked send raises `BrokenResourceError` when the receive end closes, and the
`contract/` tier is for claims about `pydantic-ai`
([`0031`](../decisions/0031-tests-are-tiered.md)). The unit tests that end a
stream exercise it on every run.

## Open questions

*None open.* One question came up: an external cancel inside `__anext__` can
leave one entry the consumer never received. It is settled as an accepted gap.
`api.md` states it, `0041` records it among its consequences, and
`test_an_external_cancel_leaves_at_most_the_entry_in_hand` pins it.
