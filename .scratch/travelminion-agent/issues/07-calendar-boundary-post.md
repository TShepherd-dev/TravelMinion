# 07: Calendar boundary + post step

**What to build:** A traveller confirms and the Itinerary is posted to a dedicated Per-trip Calendar shared read-only with the travellers, as one time-blocked event per activity. A thin, testable abstraction wraps the Google Calendar API so tests use an in-memory fake with no network. One-time Desktop-app OAuth writes a reusable `token.json` (non-expiring refresh token) stored outside the Trip folder. Posting happens only on explicit confirmation.

**Blocked by:** 04 (base Itinerary planner), 05 (Travel Days + Travel Legs)

**Status:** ready-for-agent

- [ ] Posting runs only on explicit confirmation and creates a dedicated Per-trip Calendar.
- [ ] The Per-trip Calendar is shared read-only with the listed travellers.
- [ ] One event per itinerary activity is posted, time-blocked with correct start/end, place, and duration.
- [ ] A thin Calendar abstraction over the Google Calendar API is testable via an in-memory fake (no real network in tests).
- [ ] One-time Desktop-app OAuth writes a reusable `token.json` with a non-expiring refresh token, stored outside the Trip folder so trips reuse the same auth.
- [ ] Tests at the calendar seam feed a sample Itinerary and assert calendar creation, read-only sharing, and correct per-activity events.
