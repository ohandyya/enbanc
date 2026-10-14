"""Content moderation: three advocates argue a flagged post, and you watch it happen.

What this shows, beyond `loan_assessment.py` (read that one first):

- Watching a proceeding live with `hear_stream`: each filing prints the moment it is made.
- Matching on what was filed — an argument, a concession, the judge's questions, a ruling.
- Three answers, so three advocates — and a verdict whose value tells the model what it means.

Run it:

    export OPENAI_API_KEY=... TAVILY_API_KEY=...
    uv run docs/guides/content_moderation.py

Any other provider: set `ENBANC_MODEL` to a pydantic-ai model string, plus that provider's key.
To keep the whole hearing as JSON, set `ENBANC_HEARING_FILE` to the path to write it to.
"""

import asyncio
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic_ai.models import infer_model
from pydantic_ai.usage import UsageLimits

from enbanc import (
    Advocate,
    Argument,
    Case,
    Concession,
    Continuance,
    Exhibit,
    Hearing,
    Judge,
    Response,
    Ruling,
    Source,
    Statute,
    Transcript,
    Tribunal,
    Undecided,
    Verdict,
)
from enbanc.tools import web_search


# 1. Three answers, so three advocates. The value is what the model reads, so a value can
#    carry its meaning: an advocate for ESCALATE argues for handing off, not for a third rule.
#    The member name is the code's handle — it is what the loop below prints.
class ModerationDecision(Verdict):
    ALLOW = "allow"
    REMOVE = "remove"
    ESCALATE = "escalate to a human moderator"


# 2. The policy, as written for the moderators.
STATUTE = Statute(
    name="community-safety-v2",
    text=(
        "1. Remove a post that presents a false safety claim as established or official fact.\n"
        "2. Allow opinion, personal experience, and disputed advice, even when it is wrong.\n"
        "3. Escalate to a human moderator when real harm is plausible but the record cannot "
        "settle whether rule 1 applies."
    ),
)


# 3. The case: one flagged post. Checkable (does the EPA say this?), harmful-ish (salt
#    sterilises soil, and this is a vegetable bed), and plausibly just bad home advice.
class FlaggedPost(Case):
    post_id: str
    community: str
    author: str
    text: str
    reports: int


POST = FlaggedPost(
    post_id="p-5531",
    community="r/VegetableGardening",
    author="greenthumb_42",
    text=(
        "Stop buying weed killer! Mix 1 gallon vinegar, 1 cup salt and a squirt of dish soap. "
        "It's 100% safe for vegetable beds — the EPA even recommends it as the organic option."
    ),
    reports=3,
)

# 4. The moderation file: the thread and the author's history. Same factory shape as the loan
#    guide's tool — any async function returning `Source`s is a tool.
RECORDS = {
    "p-5531": {
        "reports.txt": (
            "User reports",
            "3 reports: 'misinformation' (2), 'harmful advice' (1).",
        ),
        "replies.txt": (
            "Thread replies",
            "u/soil_nerd: 'Salt will wreck your bed for years, please don't.' "
            "u/greenthumb_42: 'Worked for me on my patio cracks, no problems.'",
        ),
        "author-history.txt": (
            "Author history",
            "Account age 4 years, 610 posts, mostly well-received. One warning (2025) for "
            "an unsourced pesticide claim, no removals since.",
        ),
    }
}


def moderation_file(records: dict[str, dict[str, tuple[str, str]]]):
    async def find_context(post_id: str) -> list[Source]:
        """Return the reports, the thread replies, and the author's history for a post."""
        return [
            Source(reference=f"mod-file://{post_id}/{name}", label=label, content=text)
            for name, (label, text) in records.get(post_id, {}).items()
        ]

    return find_context


# 5. What each citation rests on. An exhibit names its ledger row; the row holds the tool call
#    that produced it (the input) and where the result came from (the output). Only cited
#    sources are shown — everything retrieved, cited or not, stays on `transcript.ledger`.
def print_citations(transcript: Transcript[Any], advocate: Verdict, exhibits: list[Exhibit]):
    rows = {(row.advocate, row.id): row for row in transcript.ledger}
    for exhibit in exhibits:
        row = rows[(advocate, exhibit.source)]
        print(f"    {exhibit.source}: {row.call}  (round {row.round})")
        where = f"{exhibit.label} — {exhibit.reference}" if exhibit.label else exhibit.reference
        print(f"      -> {where}")
        print(f'      "{exhibit.content}"')


async def main() -> Hearing[ModerationDecision]:
    model = infer_model(os.environ.get("ENBANC_MODEL", "openai:gpt-6-luna"))
    tavily_key = os.environ.get("TAVILY_API_KEY") or sys.exit("Set TAVILY_API_KEY to run this.")
    tools = [moderation_file(RECORDS), web_search(api_key=tavily_key, max_results=2)]

    tribunal = Tribunal(
        question=f"What should moderators do with post {POST.post_id}?",
        verdicts=ModerationDecision,
        statute=STATUTE,
        model=model,
        judge=Judge(guidance="Remove only on a clear violation; when unsure, escalate."),
        advocates={verdict: Advocate(tools=tools) for verdict in ModerationDecision},
        max_rounds=3,
        budget=UsageLimits(cost_limit=Decimal("0.50"), request_limit=None),
        max_concurrency=4,
    )

    # 6. Watch it live. Each `entry` is the filing just added to `proceeding.transcript` — the
    #    stream *is* the record, with no separate events, so what you show is what is kept.
    #    It moves at your pace: a slow loop body (writing to a dashboard, say) holds the
    #    tribunal rather than falling behind it. Breaking out is allowed — in-flight runs are
    #    cancelled and `proceeding.hearing` raises `ProceedingUnfinished`. `hear()` is this
    #    loop, consumed to the end.
    async with tribunal.hear_stream(POST) as proceeding:
        async for entry in proceeding:
            tag = f"[round {entry.round}]"
            match entry.filing:
                case Argument(advocate=advocate, claim=claim, exhibits=exhibits):
                    print(f"{tag} {advocate.name} argues:\n  {claim}")
                    print_citations(proceeding.transcript, advocate, exhibits)
                    print()
                case Concession(advocate=advocate, reason=reason):
                    print(f"{tag} {advocate.name} concedes:\n  {reason}\n")
                case Continuance(interrogatories=questions):
                    print(f"{tag} the judge asks:")
                    for q in questions:
                        print(f"  {q.id} -> {q.to.name}: {q.question}")
                    print()
                case Response(advocate=advocate, answering=qid, answer=answer, exhibits=exhibits):
                    print(f"{tag} {advocate.name} answers {qid}:\n  {answer}")
                    print_citations(proceeding.transcript, advocate, exhibits)
                    print()
                case Ruling(verdict=verdict, reasoning=reasoning):
                    print(f"{tag} the judge rules: {verdict.name}\n  {reasoning}\n")

    # Once the loop ends the hearing exists — the same object `hear()` would have returned.
    hearing = proceeding.hearing
    match hearing.outcome:
        case Ruling(verdict=verdict, reasoning=reasoning):
            print(f"DECISION: {verdict.name} \n {reasoning}")
        case Undecided(reason=reason):
            # Running out ends the stream quietly, after the judge's last questions.
            print(f"UNDECIDED: the {reason} ran out before a ruling.")

    # The evidence the judge had in front of it: every exhibit an advocate filed. The judge has
    # no tools and never sees the ledger, so a source an advocate found but did not cite was
    # never before it. This is what the ruling could rest on — the ruling itself names none.
    seen = {
        (entry.filing.advocate, exhibit.source): exhibit
        for entry in hearing.transcript
        if isinstance(entry.filing, Argument | Response)
        for exhibit in entry.filing.exhibits
    }
    print("\nEVIDENCE BEFORE THE JUDGE")
    for (advocate, source), exhibit in seen.items():
        where = exhibit.label or exhibit.reference
        print(f"  {advocate.name}/{source}  [{exhibit.tool}] {where}")
        print(f"    {exhibit.content}")

    print(f"{hearing.rounds} round(s), cost ${hearing.usage.cost}")

    # Optionally keep the whole hearing: set ENBANC_HEARING_FILE to a path. A `Hearing` is a
    # Pydantic model, so the record — transcript, ledger, usage — is one JSON dump away.
    if path := os.environ.get("ENBANC_HEARING_FILE"):
        Path(path).write_text(hearing.model_dump_json(indent=2, exclude_none=True))
        print(f"Wrote the complete hearing to {path}")

    # Returned so `tests/e2e/` can run this exact file and check the hearing.
    return hearing


if __name__ == "__main__":
    asyncio.run(main())
