# 03: Research + Approved Activity List

**What to build:** A traveller runs the Research step for each destination and receives a candidate list of Suggestions, then reviews and turns that into the living, human-owned Approved Activity List. Research fetches up-to-date destination information (Tavily primary, Jina Reader and `ddgs` fallbacks) behind the research seam, shapes raw results into Suggestion fields, marks confidence, and flags unverified items. The traveller approves, rejects, reorders, and adds their own non-researched items; the result is the sole input to planning.

**Blocked by:** 01 (skill skeleton + file-interface primitives), 02 (interview to Trip Brief)

**Status:** ready-for-agent

- [ ] The Research step runs on demand per destination using the Trip Brief as input.
- [ ] Research shapes raw results into Suggestions carrying: name, rationale tied to interests, area/neighbourhood, typical duration, opening hours, approximate cost, season/weather fit, source link, and a confidence/holds-up indicator.
- [ ] Roughly 8-12 Suggestions appear per destination, scaled by days at that destination.
- [ ] Unverified or thin research is surfaced with a confidence marker and a "couldn't verify" note rather than presented as fact.
- [ ] Research output is written as a human-readable file in the Trip folder.
- [ ] A traveller can approve, reject, reorder, and add non-researched items; the resulting living list records an `approved:` per item.
- [ ] The Approved Activity List is the sole input to planning — the planner never silently re-imports unapproved Suggestions.
- [ ] Tests at the research seam feed canned results and assert Suggestion shaping (field completeness, confidence, couldn't-verify note, default-interests path).
