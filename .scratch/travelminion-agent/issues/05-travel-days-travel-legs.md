# 05: Travel Days + Travel Legs

**What to build:** A traveller moving between destinations gets Travel Days with the transit leg embedded rather than wasted as a standalone day: a morning depart with a lighter afternoon/evening activity, and a full Free Day reserved only for long hauls. Rough transit-leg details (mode + duration) are accepted as an optional traveller input.

**Blocked by:** 04 (base Itinerary planner)

**Status:** ready-for-agent

- [ ] A Travel Day embeds the travel leg (mode + duration) during the day rather than occupying a full day.
- [ ] A Travel Day carries a lighter afternoon/evening activity so the day is not wasted.
- [ ] A long-haul leg reserves a full Free Day with no planned activities.
- [ ] Rough transit-leg details are accepted as optional input and appear in the Itinerary.
- [ ] The resulting Travel Days and Free Days are written to the same diff-able Itinerary and covered by tests at the file-interface seam.
