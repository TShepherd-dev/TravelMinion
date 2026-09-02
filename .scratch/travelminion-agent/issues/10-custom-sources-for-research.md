# 10: Custom sources for research

**What to build:** Allow travellers to specify preferred websites or URLs that the research step should prioritize or scrape directly. These custom sources are fetched via Jina AI Reader (URL → Markdown) and merged with Tavily search results. Useful for official tourism sites, specific blogs, or attraction websites the traveller already knows about.

**Blocked by:** 03 (Research + Approved Activity List)

**Status:** ready-for-agent

- [ ] Trip Brief accepts an optional `preferred_sources: list[str]` field (URLs)
- [ ] ResearchEngine fetches each preferred source via JinaSource (URL → Markdown extraction)
- [ ] Custom source results are shaped into RawResult objects (same as search results)
- [ ] Custom sources are merged with search results (or boost ranking if duplicate)
- [ ] research-output.md clearly marks which suggestions came from custom sources vs. search
- [ ] Tests verify: empty sources list, single URL, multiple URLs, malformed URL handling, merge with Tavily results
- [ ] SKILL.md updated to document the preferred_sources field

## Implementation Notes

**Models change:**
- Add `preferred_sources: list[str] = []` to TripBrief in `travelminion/models.py`
- Optional validator to ensure URLs are well-formed

**Research change:**
- `ResearchEngine.research_destination()` accepts optional `sources: list[str]`
- `JinaSource.fetch_url(url: str) -> RawResult` method
- Merge logic: custom sources first, then Tavily/ddgs results
- Mark source provenance in RawResult.source_name ("custom" vs "tavily" vs "ddgs" vs "jina")

**Tests:**
- Test JinaSource.fetch_url() with real URLs (mocked HTTP)
- Test merge logic (custom + search)
- Test malformed URL handling (skip gracefully)
- End-to-end: Trip Brief with preferred_sources → research-output.md

---
