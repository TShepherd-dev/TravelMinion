# 06: Weather fallbacks

**What to build:** Weather-exposed activities in the Itinerary carry indoor fallback notes, so a traveller knows what to swap to when weather turns. Research already tags each Suggestion with its season/weather fit; this ticket turns that into planning annotations (not new events).

**Blocked by:** 04 (base Itinerary planner)

**Status:** ready-for-agent

- [ ] Weather-exposed activities in the Itinerary are annotated with an indoor fallback note.
- [ ] The annotation consumes the Suggestion's season/weather-fit tag from the Approved Activity List.
- [ ] Fallback notes appear as annotations in the Itinerary and do not create extra calendar events.
- [ ] Covered by a test at the file-interface seam asserting the fallback note on a weather-exposed activity.
