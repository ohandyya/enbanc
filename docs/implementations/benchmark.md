---
status: draft
updated: 2026-10-18
---

# A benchmark against simpler ways of deciding

**Measure whether an adversarial proceeding decides better than one model
does, and what that costs.** The README says the structure is designed for
decisions that must be defensible. Nothing measures whether it decides more
accurately than a single prompt, or whether its confidence means anything. This
PR is the first evidence either way.

## Scope

**It lives in this repository, in a top-level `benchmarks/`, and never ships.**
The build backend ships only `src/enbanc/` plus `README.md`, `LICENSE` and
`pyproject.toml`; everything else is left out unless it is added on purpose.
This was confirmed on 2026-10-18 by building `0.1.0` and listing both
artifacts. Three rules keep it that way:

- **Nothing benchmark-related goes under `src/enbanc/`.** Anything there ships.
- **Its dependencies go in a `benchmark` dependency group**, next to `dev`.
  Dependency groups are never published. An extra under
  `[project.optional-dependencies]` would be published, and is the wrong tool.
- **A CI check builds the package and fails if either artifact holds a file
  outside the expected list.** Today the only check is a command in a
  `pyproject.toml` comment, run by hand. The guard also catches a future edit
  to `[tool.uv.build-backend]` that widens the build.

**Datasets.** The shape that fits is a rule, a set of facts, and a labelled
verdict, ideally with evidence that must be retrieved. The candidates are:

| Dataset | Verdicts | Why it fits |
|---|---|---|
| FEVER, AVeriTeC | supported, refuted, not enough info | Evidence must be retrieved; AVeriTeC's is real-world and web-based, which exercises `web_search` |
| LegalBench (rule-application tasks) | yes / no, and others | Nearly the `Statute` plus `Case` shape |
| ContractNLI | entailed, contradicted, not mentioned | The contract is a document, so it pairs with [`local-file-tool.md`](./local-file-tool.md) |
| PubMedQA | yes, no, maybe | Three verdicts, grounded in evidence |

Credit datasets such as German Credit and Lending Club are excluded. Their
labels are outcomes (did the loan default?), not decisions against a rule.

**Baselines,** each given the same model:

1. A single prompt, no tools.
2. **A single agent with the same tools.** This is the comparison that
   matters: without it, a gain cannot be credited to the adversarial structure
   rather than to the tools.
3. Self-consistency, a majority vote over N samples, **at matched cost**.
4. Multi-agent debate (Du et al., 2023), the nearest published method.

**Metrics:**

- Accuracy and macro-F1.
- Cost and wall-clock time per decision. `enbanc` is expected to lose here, and
  the write-up says so.
- Selective accuracy: accuracy on the cases it rules on, beside its
  `Undecided` rate. Abstaining is only worth something if it happens on the
  hard cases.
- Calibration of the ruling's `confidence`. This bears on
  [`api.md`'s open question](../design/api.md#open-questions) about whether a
  confidence is ever measured.
- Citation faithfulness, using [`excerpt-check.md`](./excerpt-check.md)'s
  helper.

**Start small.** One dataset and about 200 items, run on the current prompts
as a baseline. It is re-run after
[`ruling-cites-evidence.md`](./ruling-cites-evidence.md) so that a prompting
change shows up as a measured difference.

**Not in this PR:** a benchmark in the test tiers or in CI. It costs money and
is not a pass/fail check; [`0033`](../decisions/0033-live-tiers-run-in-ci-on-demand.md)'s
reasoning about live runs applies, and more strongly.

## Implements

- [`packaging.md` § One distribution](../design/packaging.md#one-distribution):
  what a build ships, now stated and checked. The design doc gains that
  statement in this PR.
- [`api.md` § Open questions](../design/api.md#open-questions): the confidence
  bullet is *sharpened* with data, not settled. Whether `enbanc` should help a
  caller measure confidence is still a separate decision.

## Depends on

[`excerpt-check.md`](./excerpt-check.md), for the citation-faithfulness metric.

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*Filled in when this PR starts.*
