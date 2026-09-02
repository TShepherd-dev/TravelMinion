# 05: Travel Days + Travel Legs

**What to build:** A traveller moving between destinations gets Travel Days with the transit leg embedded rather than wasted as a standalone day: a morning depart with a lighter afternoon/evening activity, and a full Free Day reserved only for long hauls. Rough transit-leg details (mode + duration) are accepted as an optional traveller input.

**Blocked by:** 04 (base Itinerary planner)

**Status:** done

- [x] A Travel Day embeds the travel leg (mode + duration) during the day rather than occupying a full day.
- [x] A Travel Day carries a lighter afternoon/evening activity so the day is not wasted.
- [x] A long-haul leg reserves a full Free Day with no planned activities.
- [x] Rough transit-leg details are accepted as optional input and appear in the Itinerary.
- [x] The resulting Travel Days and Free Days are written to the same diff-able Itinerary and covered by tests at the file-interface seam.

**Implementation notes:**
- Added `transit_from_previous` field to DestinationStop model
- `_parse_transit_duration()` extracts minutes from strings like "flight 3h", "train 2h15m"
- LONG_HAUL_THRESHOLD = 360 minutes (6 hours) → creates FreeDay for recovery
- Short trips: TravelDay with afternoon activity (3-5pm "Explore {destination}")
- Mode extraction via regex (flight/train/bus/car/ferry/boat)
- 7 new tests, 128 total passing
