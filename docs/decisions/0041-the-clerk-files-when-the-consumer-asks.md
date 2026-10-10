---
status: accepted
updated: 2026-10-10
---

# 0041. The clerk files when the consumer asks

## Context

[`0010`](./0010-streaming-yields-the-record.md) promises that *the entry just
received is the last entry of `proceeding.transcript`*, and
[`api.md`](../design/api.md#watching-it-live) repeats it as *live: the entry
just yielded is its last*. [`execution.md`](../design/execution.md#the-filing-clerk)
makes one coroutine, the clerk, the transcript's only writer, so no sibling can
append between another filer's append and send.

That did not make the sentence true. The clerk appended an entry and then
blocked on the rendezvous send to the stream. A consumer busy with entry *N*,
for example `await`ing a database write, therefore let the clerk take the next
filing, append *N*+1, and block again. Probed with three concurrent filers and a
consumer that `await`s in its body:

```text
slow consumer (len, entry is transcript[-1]): [(2, False), (3, False), (4, False), (4, True)]
abandoned after seeing 1, transcript holds: 2
```

The promise held only for a consumer whose loop body never `await`s, which is
every streaming test that existed and not the consumer the stream exists for.
Abandoning inherited the defect: walking away could leave an entry in the record
that the consumer never received.

## Decision

**The clerk appends only once a consumer has asked for the next entry.**
`Proceeding.__anext__` sends a token on a second rendezvous stream, `ready`, and
then receives the entry. The clerk takes a filing, waits for a token, and only
then stamps, appends, sends and acknowledges, as one sequence:

```python
async def clerk(inbox, ready, transcript, out):
    async for filing, round_no, done in inbox:
        await ready.receive()             # a consumer has asked for the next entry
        entry = Entry(round=round_no, filed_at=datetime.now(UTC), filing=filing)
        transcript.entries.append(entry)
        await out.send(entry)
        done.set()
```

The consumer is parked in `receive()` when the append happens, so its body
cannot run in between. It asks again only after that body has finished, so
*N*+1 cannot be appended while it holds *N*. The same probe, run against this:

```text
slow consumer (len, entry is transcript[-1]): [(1, True), (2, True), (3, True), (4, True)]
abandoned after seeing 1, transcript holds: 1
```

The clerk stays the transcript's only writer. `filed_at` is still read at the
moment the record changes, and the stream still carries `Entry`.

## Consequences

**Abandoning by `break` or by raising leaves exactly what was received.** A
consumer that leaves never asks again, and the clerk never appends what nobody
will receive. A stream that is entered and never iterated files nothing.

**A cancel from outside can leave at most one more entry.** Asking and receiving
are two awaits, and the clerk can take the ask before the consumer receives. A
cancel can reach the consumer in that window, such as a caller's timeout around
the `async with`. It can land at the checkpoint that opens anyio's `receive()`,
or while the consumer's send waits for the clerk to take it. The clerk then holds
a token, appends an entry the consumer never received, and is cancelled on its
own send. It never gets a second token, so it never appends a second entry.
This gap is accepted, because closing it would mean the consumer appends, which
is the option rejected below. `break` and an exception from the loop body cannot
reach that point, so the abandoning promise is exact for them.
[`api.md`](../design/api.md#watching-it-live) states the gap.

**`ProceedingFailed.transcript` is what the consumer had received.** A failure
is still raised out of the `async with` with the record as it stood, and the
record now stands where the stream does. For `hear()`, which consumes every
entry, that is everything filed.

**A slow consumer holds the filers.** The acknowledgment follows the append,
and the append follows the consumer's ask. So an advocate whose next run waits on
the acknowledgment
([`0027`](./0027-an-advocate-answers-its-interrogatories-in-order.md)) also
waits on the reader. `0027` is unaffected, because the acknowledgment still
means *in the record*.

**`0010`'s backpressure paragraph is corrected here.** It says *a consumer slower
than the tribunal means entries wait in memory* and that *there is no bound to
configure*. That was already false under the rendezvous stream, where the clerk
blocked on its send and the filers blocked on the acknowledgment. Under this
decision it is false by design: nothing waits in memory, and the proceeding moves
at the reader's pace. The conclusion still stands, since there is nothing to
configure and no drop policy, but the reason is that nothing is buffered, not
that the buffer is free. `0010` is immutable and is not edited.

## Alternatives considered

**The consumer appends on receipt.** The clerk sends the entry with an event,
`Proceeding.__anext__` appends it before yielding and sets the event, and the
clerk acknowledges the filer once the event is set. It fixes the defect equally
well, and it is the only route to narrowing the cancellation gap above, because
the append would move into the task that yields. Rejected for two reasons. First,
the public handle would write the record, which strains `api.md`'s
*`Proceeding` holds no fact of its own*, and `hear()` would build the record by
consuming it. Second, `filed_at` would be stamped by the clerk before a slow
consumer appended, so the stamp would no longer be the moment the entry entered
the record.

**Swapping the append and the send.** Send first, then append. Rejected because
a receiver taking from a blocked sender may run its loop body before the clerk
resumes to append, so the consumer would see the record one entry *behind*
rather than ahead.

**A buffered out stream.** Rejected because it moves the defect rather than
fixing it: the clerk would append further ahead of a slow consumer, not less.
