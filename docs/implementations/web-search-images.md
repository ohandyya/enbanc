---
status: draft
updated: 2026-10-18
---

# Images in `web_search`, on request

**`web_search` can return Tavily's image results as sources, when the caller
asks for them.** Tavily can return images for a query, each with a description
written by its own model. A description is text, so it fits `Source` as it
stands: `Source(reference=<image url>, content=<description>)`.

## Scope

**Opt-in, not the default.** The factory gains parameters along the lines of
`include_images: bool = False`; whether there is one parameter or two is
settled when the PR starts. Two reasons it stays off by default:

- **Provenance.** Every other ledger row is the source's own text, verbatim.
  An image description is a third party's model summarizing a picture, so an
  advocate would be citing a caption, and a reviewer following the URL sees an
  image that may not match it. This weakens the README's "taken from what the
  tool actually returned" claim in a way that is easy to miss, so evidence.md
  documents it.
- **It would change a released default.** `max_results=5` is defended as a
  decision about the size of the record. Turning images on by default would
  enlarge every record of every `0.1.0` caller who upgrades.

**Tavily's images belong to the query, not to a result.** They arrive as a
top-level list rather than per result, so each one becomes its own source.

**Not in this PR:** genuinely multimodal evidence, where the advocate's model
sees the image bytes. That changes `Source.content` from `str` and is a
separate decision.

## Implements

- [`evidence.md` § The default tool](../design/evidence.md#the-default-tool):
  the new parameters, the field mapping for an image, and the provenance
  caveat.
- An ADR recording why images are opt-in.

## Depends on

Nothing open. It extends [`web-search-tool.md`](./web-search-tool.md) (#21).

## Files

*Filled in when this PR starts.*

## Tests

*Filled in when this PR starts.*

## Open questions

*Filled in when this PR starts.*
