"""Loan assessment: two advocates argue a loan, a judge rules on the record.

What this shows, in one file:

- The decision as types: the answers (`Verdict`), the rule (`Statute`), the facts (`Case`).
- One advocate per answer, each with its own evidence tools — including one you write.
- A ruling you can audit: every claim cites a document, and what was left uncited is kept.
- A hard budget: a debate that runs long ends as `Undecided`, not as a surprise bill.

Run it:

    export OPENAI_API_KEY=... TAVILY_API_KEY=...
    uv run docs/guides/loan_assessment.py

Any other provider: set `ENBANC_MODEL` to a pydantic-ai model string, such as
`anthropic:claude-sonnet-5`, plus that provider's own key.
"""

import asyncio
import os
import sys
from decimal import Decimal

from pydantic_ai.models import infer_model
from pydantic_ai.usage import UsageLimits

from enbanc import (
    Advocate,
    Case,
    Hearing,
    Judge,
    Ruling,
    Source,
    Statute,
    Tribunal,
    Undecided,
    Verdict,
)
from enbanc.tools import web_search


# 1. The answers you accept. One advocate is seated per value, and the ruling's verdict is
#    typed as this enum — the judge cannot answer anything else.
class LoanDecision(Verdict):
    APPROVE = "approve"
    DENY = "deny"


# 2. The rule. Plain text you write; every participant reads it exactly as written.
STATUTE = Statute(
    name="underwriting-v3",
    text=(
        "Approve a personal loan only if all of the following hold:\n"
        "1. Debt-to-income ratio — existing monthly debts plus the new monthly payment, divided "
        "by documented monthly gross income — is below 0.43.\n"
        "2. Only documented income counts. Where current pay exceeds the most recent tax "
        "return, the higher figure counts only if the increase is shown to be stable.\n"
        "3. Credit score is at least 660.\n"
        "Otherwise, deny."
    ),
)


# 3. The facts of one decision. Subclass `Case` to give them a schema; enbanc records it
#    whole in the transcript and never reads a field itself.
class LoanApplication(Case):
    applicant_id: str
    amount: int
    term_months: int
    monthly_payment: int
    stated_annual_income: int
    monthly_debts: int
    employer: str


APPLICATION = LoanApplication(
    applicant_id="A-1027",
    amount=60_000,
    term_months=60,
    monthly_payment=1_200,
    stated_annual_income=120_000,
    monthly_debts=2_900,
    employer="Copperline Logistics",
)

# 4. The evidence. Built to be argued: this year's pay stub puts the debt-to-income ratio at
#    4,100 / 9,800 ≈ 0.42 (approve), last year's tax return at 4,100 / 8,667 ≈ 0.47 (deny).
#    Whether a seven-month-old raise is "stable" is what the advocates fight over.
DOCUMENTS = {
    "A-1027": {
        "loan-quote.pdf": (
            "Loan quote",
            "Principal $60,000, 60 months, 7.4% APR. Monthly payment: $1,200.",
        ),
        "pay-stub-2026-09.pdf": (
            "Pay stub, September 2026",
            "Copperline Logistics. Gross monthly pay: $9,800. Base salary raised from $8,600 "
            "per month, effective 2026-03-01. Employed since 2019.",
        ),
        "form-1040-2025.pdf": (
            "Form 1040, tax year 2025",
            "Wages, salaries, tips: $104,000. No other income reported.",
        ),
        "credit-report-2026-10.pdf": (
            "Credit report, October 2026",
            "Score: 694. Open obligations: mortgage $2,300/month, auto loan $600/month. "
            "No delinquencies in the last 24 months.",
        ),
    }
}


# 5. Your own tool. Any async function is a tool — no enbanc base class, no decorator.
#    Returning `Source`s makes each document separately citable, so an exhibit points at
#    `loan-file://A-1027/form-1040-2025.pdf` rather than at "the tool said so". Configuration
#    (here the documents; in real code a DB pool or client) is closed over by a factory —
#    the same shape as the `web_search` enbanc ships.
def loan_file(documents: dict[str, dict[str, tuple[str, str]]]):
    async def find_documents(applicant_id: str) -> list[Source]:
        """Return every document in the applicant's loan file."""
        return [
            Source(reference=f"loan-file://{applicant_id}/{name}", label=label, content=text)
            for name, (label, text) in documents.get(applicant_id, {}).items()
        ]

    return find_documents


async def main() -> Hearing[LoanDecision]:
    # The model is yours to build and inject; enbanc works with any pydantic-ai Model.
    model = infer_model(os.environ.get("ENBANC_MODEL", "openai:gpt-6-luna"))
    tavily_key = os.environ.get("TAVILY_API_KEY") or sys.exit("Set TAVILY_API_KEY to run this.")
    find_documents = loan_file(DOCUMENTS)

    tribunal = Tribunal(
        question="Shall the bank lend applicant A-1027 $60,000 over 60 months?",
        verdicts=LoanDecision,
        statute=STATUTE,
        model=model,
        # The judge has no tools: it rules only on what the advocates put in the record.
        judge=Judge(guidance="Where the record is ambiguous, deny."),
        # The toolboxes differ on purpose — each side brings the evidence it needs.
        advocates={
            LoanDecision.APPROVE: Advocate(
                tools=[find_documents, web_search(api_key=tavily_key, max_results=2)],
                guidance="Use web search to show the employer, and so the raise, is stable.",
            ),
            LoanDecision.DENY: Advocate(
                tools=[find_documents],
                guidance="Weigh documented income over stated income.",
            ),
        },
        # The envelope: at most 3 rounds and $0.50, whichever runs out first.
        max_rounds=3,
        budget=UsageLimits(cost_limit=Decimal("0.50"), request_limit=None),
        max_concurrency=4,
    )

    hearing = await tribunal.hear(APPLICATION)

    # The audit trail: every filing in order, each exhibit with the source it cites, and the
    # ledger of everything the tools returned — including what nobody chose to cite.
    print(hearing.transcript.render())

    # Running out of rounds or budget is an outcome, not an exception — so it is a case you
    # must handle. (A broken provider or tool raises `ProceedingFailed` instead.)
    match hearing.outcome:
        case Ruling(verdict=verdict, reasoning=reasoning):
            print(f"\nRULING: {verdict}\n{reasoning}")
        case Undecided(reason=reason):
            print(f"\nUNDECIDED: the {reason} ran out before a ruling.")

    # Every tool call, read back from the ledger: who called it, with what input, and what it
    # returned. You logged nothing — the transcript keeps this for audit, so a reviewer sees
    # what each side searched for, not only what it found. A call's rows sit together.
    print("\nTOOL CALLS")
    last = None
    for row in hearing.transcript.ledger:
        if (row.round, row.advocate, row.call) != last:
            last = (row.round, row.advocate, row.call)
            print(f"  round {row.round}, {row.advocate}: {row.call}")
        print(f"    -> [{row.id}] {row.label or row.reference}")

    # What it cost, in total and per participant. `cost is None` means unpriced, not free.
    usage = hearing.usage
    print(f"\n{hearing.rounds} round(s), {usage.requests} requests, cost ${usage.cost}")
    for participant, spent in hearing.usage_by_participant.items():
        print(f"  {participant}: {spent.requests} requests, {spent.total_tokens} tokens")

    # Returned so `tests/e2e/` can run this exact file and check the hearing.
    return hearing


if __name__ == "__main__":
    asyncio.run(main())
