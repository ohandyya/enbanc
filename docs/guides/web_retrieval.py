"""Web retrieval: does this restaurant offer hookah? The web is the only evidence.

What this shows, beyond `loan_assessment.py` (read that one first):

- Answering a factual question about the world with `web_search` as the only tool.
- One tribunal, many cases: the question is fixed, the case says *which* business.
- Hearing several cases at once with `asyncio.gather` — a tribunal holds no state between them.
- Pulling out just what you need: the verdict, the reasoning, the confidence, the web pages.

Run it:

    export OPENAI_API_KEY=... TAVILY_API_KEY=...
    uv run docs/guides/web_retrieval.py

Any other provider: set `ENBANC_MODEL` to a pydantic-ai model string, plus that provider's key.
"""

import asyncio
import os
import sys
from decimal import Decimal

from pydantic_ai.models import infer_model
from pydantic_ai.usage import UsageLimits

from enbanc import (
    Advocate,
    Argument,
    Case,
    Hearing,
    Judge,
    Response,
    Ruling,
    Statute,
    Tribunal,
    Undecided,
    Verdict,
)
from enbanc.tools import web_search


# 1. A yes/no question is two verdicts, and so two advocates: one looks for proof that hookah
#    is served, the other for proof that it is not. Neither can stop at the first search hit.
class OffersHookah(Verdict):
    YES = "offers hookah"
    NO = "does not offer hookah"


# 2. The judge's rule — what counts as "offers hookah". Keep it short and concrete.
STATUTE = Statute(
    name="hookah-check-v1",
    text=(
        "A business offers hookah if current web sources — its own website, menu, social "
        "media, listings, or recent reviews — show that hookah (shisha) is served on its "
        "premises. A name or category alone is a hint, not proof. Sources about a different "
        "business, or saying hookah was discontinued, count against."
    ),
)


# 3. The case: which business. The question stays the same for every case.
class Business(Case):
    name: str
    address: str


BUSINESSES = [
    # This is a real hookah bar, and the judge should find it so.
    Business(
        name="Moustache Hookah Bar",
        address="7855 Roswell Rd l, Unit, Sandy Springs, GA 30350",
    ),
    # This is a real restaurant, and the judge should find it does not serve hookah.
    Business(
        name="Fly Chef Restaurant",
        address="6470 Spalding Dr suite b, Peachtree Corners, GA 30092",
    ),
]


def cited_pages(hearing: Hearing[OffersHookah], side: OffersHookah) -> list[str]:
    """The web pages one side put in front of the judge, deduplicated, in filing order."""
    pages: dict[str, None] = {}
    for entry in hearing.transcript:
        if isinstance(entry.filing, Argument | Response) and entry.filing.advocate == side:
            for exhibit in entry.filing.exhibits:
                pages[exhibit.reference] = None
    return list(pages)


async def main() -> list[Hearing[OffersHookah]]:
    model = infer_model(os.environ.get("ENBANC_MODEL", "openai:gpt-6-luna"))
    tavily_key = os.environ.get("TAVILY_API_KEY") or sys.exit("Set TAVILY_API_KEY to run this.")
    search = web_search(api_key=tavily_key, max_results=3)

    tribunal = Tribunal(
        question="Does the business in this case offer hookah to its customers?",
        verdicts=OffersHookah,
        statute=STATUTE,
        model=model,
        # 4. Your prompts. The statute above is the rule; `guidance` is how each participant
        #    should go about it. The judge's goes here...
        judge=Judge(guidance="Prefer the business's own pages and recent sources."),
        # ...and each advocate's here. Both search the same web; what differs is what they
        # look for.
        advocates={
            OffersHookah.YES: Advocate(
                tools=[search],
                guidance="Search for the business's menu, website and reviews mentioning hookah.",
            ),
            OffersHookah.NO: Advocate(
                tools=[search],
                guidance="Check that pages found are about this exact address, and look for "
                "menus or reviews with no sign of hookah.",
            ),
        },
        # The envelope applies to each hearing, not to the whole batch.
        max_rounds=3,
        budget=UsageLimits(cost_limit=Decimal("0.50"), request_limit=None),
        max_concurrency=4,
    )

    # 5. Hear every business at once. `hear()` parks nothing on the tribunal, so one tribunal
    #    serves them all; results come back in the order the cases went in.
    hearings = await asyncio.gather(*(tribunal.hear(business) for business in BUSINESSES))

    # 6. Just the answer. A ruling carries the verdict, the judge's reasoning, and its
    #    confidence (0 to 1, the judge's own estimate — not a calibrated probability).
    for business, hearing in zip(BUSINESSES, hearings, strict=True):
        print(f"\n{business.name} — {business.address}")
        match hearing.outcome:
            case Ruling(verdict=verdict, reasoning=reasoning, confidence=confidence):
                print(f"  Offers hookah: {verdict.name}")
                print(f"  Confidence:    {confidence}")
                print(f"  Reasoning:     {reasoning}")
                print("  Pages the winning side cited:")
                for page in cited_pages(hearing, verdict):
                    print(f"    - {page}")
            case Undecided(reason=reason):
                print(f"  UNDECIDED: the {reason} ran out before a ruling.")
        print(f"  ({hearing.rounds} round(s), cost ${hearing.usage.cost})")

    # Returned so `tests/e2e/` can run this exact file and check each hearing.
    return hearings


if __name__ == "__main__":
    asyncio.run(main())
