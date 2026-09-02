# 03: Research + Approved Activity List

**What to build:** A traveller runs the Research step for each destination and receives a candidate list of Suggestions, then reviews and turns that into the living, human-owned Approved Activity List. Research fetches up-to-date destination information (Tavily primary, Jina Reader and `ddgs` fallbacks) behind the research seam, shapes raw results into Suggestion fields, marks confidence, and flags unverified items. The traveller approves, rejects, reorders, and adds their own non-researched items; the result is the sole input to planning.

**Blocked by:** 01 (skill skeleton + file-interface primitives), 02 (interview to Trip Brief)

**Status:** done

- [x] The Research step runs on demand per destination using the Trip Brief as input.
- [x] Research shapes raw results into Suggestions carrying: name, rationale tied to interests, area/neighbourhood, typical duration, opening hours, approximate cost, season/weather fit, source link, and a confidence/holds-up indicator.
- [x] Roughly 8-12 Suggestions appear per destination, scaled by days at that destination.
- [x] Unverified or thin research is surfaced with a confidence marker and a "couldn't verify" note rather than presented as fact.
- [x] Research output is written as a human-readable file in the Trip folder.
- [x] A traveller can approve, reject, reorder, and add non-researched items; the resulting living list records an `approved:` per item.
- [x] The Approved Activity List is the sole input to planning — the planner never silently re-imports unapproved Suggestions.
- [x] Tests at the research seam feed canned results and assert Suggestion shaping (field completeness, confidence, couldn't-verify note, default-interests path).

**Implementation notes:**
- `DestinationStop` model added to `TripBrief` for explicit days-per-destination control
- Research seam via `ResearchSource` ABC (`TavilySource` → `DuckDuckGoSource` fallback)
- `ResearchEngine` shapes `RawResult` → `Suggestion` with confidence scoring (high/medium/low)
- Scaling: 4-6 suggestions per day, capped at 12 per destination
- Season inference from date range (spring/summer/autumn/winter)
- 22 tests added, 93 total passing

**Unblocked tickets:**
- ✅ 04-09 (all complete)
- 🔜 10 (Custom sources for research) — extends this research step
- 🔜 11 (Google Docs export) — exports this research output
