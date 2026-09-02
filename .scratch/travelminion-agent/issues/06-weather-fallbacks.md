# 06: Weather fallbacks

**What to build:** Weather-exposed activities in the Itinerary carry indoor fallback notes, so a traveller knows what to swap to when weather turns. Research already tags each Suggestion with its season/weather fit; this ticket turns that into planning annotations (not new events).

**Blocked by:** 04 (base Itinerary planner)

**Status:** done

- [x] Weather-exposed activities in the Itinerary are annotated with an indoor fallback note.
- [x] The annotation consumes the Suggestion's season/weather-fit tag from the Approved Activity List.
- [x] Fallback notes appear as annotations in the Itinerary and do not create extra calendar events.
- [x] Covered by a test at the file-interface seam asserting the fallback note on a weather-exposed activity.

**Implementation notes:**
- OUTDOOR_KEYWORDS: beach, hiking, garden, park, outdoor, viewpoint, terrace, rooftop, boat, cruise, waterfront, zoo, etc.
- INDOOR_KEYWORDS: museum, gallery, indoor, theater, aquarium, cathedral, castle, tower, etc.
- INDOOR_FALLBACKS: context-aware suggestions (beach→aquarium, hiking→visitor center, garden→conservatory)
- _get_indoor_fallback() analyzes activity.name + area + notes
- Planner auto-populates TimeBlock.indoor_fallback during scheduling
- 17 tests added, 145 total passing
