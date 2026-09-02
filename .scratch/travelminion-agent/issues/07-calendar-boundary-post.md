# 07: Calendar boundary + post step

**What to build:** A traveller confirms and the Itinerary is posted to a dedicated Per-trip Calendar shared read-only with the travellers, as one time-blocked event per activity. A thin, testable abstraction wraps the Google Calendar API so tests use an in-memory fake with no network. One-time Desktop-app OAuth writes a reusable `token.json` (non-expiring refresh token) stored outside the Trip folder. Posting happens only on explicit confirmation.

**Blocked by:** 04 (base Itinerary planner), 05 (Travel Days + Travel Legs)

**Status:** done

- [x] Posting runs only on explicit confirmation and creates a dedicated Per-trip Calendar.
- [x] The Per-trip Calendar is shared read-only with the listed travellers.
- [x] One event per itinerary activity is posted, time-blocked with correct start/end, place, and duration.
- [x] A thin Calendar abstraction over the Google Calendar API is testable via an in-memory fake (no real network in tests).
- [x] One-time Desktop-app OAuth writes a reusable `token.json` with a non-expiring refresh token, stored outside the Trip folder so trips reuse the same auth.
- [x] Tests at the calendar seam feed a sample Itinerary and assert calendar creation, read-only sharing, and correct per-activity events.

## Implementation Notes

Created `travelminion/calendar.py`:
- `CalendarService` ABC with create_calendar, share_calendar, create/update/delete/list events, post_itinerary
- `FakeCalendarService` - in-memory for tests (no network)
- `GoogleCalendarService` - real OAuth + google-api-client implementation
- `CalendarEvent` dataclass for event representation
- `CalendarResult` dataclass for operation results
- OAuth: Desktop-app flow, token.json stored in `~/.travelminion/` (outside Trip folder)
- Per-trip calendar via `calendars.insert`, shared via `acl.insert` (role=reader)
- Rebuild semantics: updates events in place by date+index, no duplicates

Tests (`tests/test_calendar.py` - 27 tests):
- CalendarEvent creation
- FakeCalendarService: calendar CRUD, sharing, event CRUD, list in range
- TimeBlock to CalendarEvent conversion
- Post itinerary: activity days, travel days, free days, mixed
- Rebuild: updates existing events, adds new days, no duplication
- CalendarResult creation

Verification:
- All 27 calendar tests pass
- Total suite: 172 tests pass, 1 skipped
- Ruff check clean

Dependencies added to pyproject.toml:
- google-api-python-client>=2.0
- google-auth-httplib2>=0.1
- google-auth-oauthlib>=0.5
