"""Content moderation: three advocates argue a flagged post, and you watch it happen.

What this shows, beyond `loan_assessment.py` (read that one first):

- Watching a proceeding live with `hear_stream`: each filing prints the moment it is made.
- Matching on what was filed — an argument, a concession, the judge's questions, a ruling.
- Each advocate's confidence in its own case, which the judge weighs beside the exhibits.
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


# 2. The policy, as written for the moderators. Its rules pull against each other on purpose:
#    real moderation is weighing them, not looking one up.
STATUTE = Statute(
    name="community-safety-v3",
    text=(
        "1. Remove a post that states a safety claim as established fact when the claim is "
        "false and following it could cause serious harm.\n"
        "2. Allow personal experience, opinion, and criticism of official guidance, framed as "
        "such — even when moderators disagree with it.\n"
        "3. Escalate to a human moderator when a post mixes the two and the record cannot "
        "settle which rule governs, or when the harm would be severe but its likelihood is "
        "genuinely unclear."
    ),
)


# 3. The case: a post with no easy answer. It is personal experience from a trusted member,
#    it describes a precaution, and it criticises official guidance — all allowed. It also
#    ends in "it's fine" about a practice the USDA advises against, where the rare failure is
#    botulism. Each advocate has a real case to make.
class FlaggedPost(Case):
    post_id: str
    community: str
    author: str
    text: str
    reports: int


POST = FlaggedPost(
    post_id="p-8812",
    community="r/HomeCanning",
    author="heirloom_hal",
    text=(
        "For 30 years I've water-bath canned my own heirloom tomatoes without adding lemon "
        "juice or citric acid. I test every batch with pH strips and only can if it reads "
        "under 4.2. Never had a bad jar. The USDA's 'always acidify' rule is written for "
        "low-acid modern hybrids and, honestly, for liability. If you grow acidic heirlooms "
        "and test, it's fine."
    ),
    reports=4,
)

# 4. The moderation file: the thread and the author's history. Same factory shape as the loan
#    guide's tool — any async function returning `Source`s is a tool.
RECORDS = {
    "p-8812": {
        "reports.txt": (
            "User reports",
            "4 reports: 'dangerous advice' (3), 'misinformation' (1). "
            "2 users also replied 'reported, but this is legit experience'.",
        ),
        "replies.txt": (
            "Thread replies",
            "u/jar_nerd: 'Botulism doesn't care about your 30 years. NCHFP says acidify every "
            "tomato.' u/grandmas_pantry: 'Same here, my family never acidified and we test "
            "too.' u/heirloom_hal: 'I'm not telling beginners to copy me — I'm saying test.'",
        ),
        "author-history.txt": (
            "Author history",
            "Account age 9 years, 2,140 posts, 'Trusted Canner' flair. Has posted many "
            "tested-recipe walkthroughs. No warnings or removals.",
        ),
        "community-rules.txt": (
            "Community sidebar",
            "We follow tested recipes. Discussion of untested methods is allowed with the "
            "'Untested method' flair so newcomers can tell the difference.",
        ),
    }
}


def moderation_file(records: dict[str, dict[str, tuple[str, str]]]):
    async def find_context(post_id: str) -> list[Source]:
        """Return the reports, replies, author history, and community rules for a post."""
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
        judge=Judge(
            guidance="Weigh how the post frames its claim, how severe and how likely the harm "
            "is, and who is likely to read it. Escalation is a decision, not a default."
        ),
        # Every advocate gets the same tools and the same instruction: make the best case the
        # record allows. A gray case is only worth hearing if each side is actually argued.
        advocates={
            verdict: Advocate(
                tools=tools,
                guidance="Argue the strongest good-faith reading of the statute for your "
                "verdict. Concede only if no reasonable reading supports it.",
            )
            for verdict in ModerationDecision
        },
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
                # An argument and a response carry the advocate's confidence that the record
                # supports its verdict, 0 to 1. The judge reads it as one side's own estimate
                # and tests it against the exhibits, and so should you.
                case Argument(advocate=advocate, claim=claim, exhibits=exhibits, confidence=c):
                    print(f"{tag} {advocate.name} argues (confidence {c}):\n  {claim}")
                    print_citations(proceeding.transcript, advocate, exhibits)
                    print()
                case Concession(advocate=advocate, reason=reason):
                    print(f"{tag} {advocate.name} concedes:\n  {reason}\n")
                case Continuance(interrogatories=questions):
                    print(f"{tag} the judge asks:")
                    for q in questions:
                        print(f"  {q.id} -> {q.to.name}: {q.question}")
                    print()
                case Response(
                    advocate=advocate, answering=qid, answer=answer, exhibits=exhibits, confidence=c
                ):
                    print(f"{tag} {advocate.name} answers {qid} (confidence {c}):\n  {answer}")
                    print_citations(proceeding.transcript, advocate, exhibits)
                    print()
                case Ruling(verdict=verdict, reasoning=reasoning, confidence=c):
                    print(
                        f"{tag} the judge rules: {verdict.name} (confidence {c})\n  {reasoning}\n"
                    )

    # Once the loop ends the hearing exists — the same object `hear()` would have returned.
    hearing = proceeding.hearing
    match hearing.outcome:
        case Ruling(verdict=verdict, reasoning=reasoning, confidence=confidence):
            # The judge's own estimate, not a calibrated probability: `loan_assessment.py`
            # shows routing a low one to a person.
            print(f"DECISION: {verdict.name} (confidence {confidence})\n {reasoning}")
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
