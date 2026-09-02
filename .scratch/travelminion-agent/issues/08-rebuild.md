# 08: Rebuild

**What to build:** When the Approved Activity List changes, a traveller explicitly re-plans and the affected calendar events are updated in place rather than duplicated. Before replacing, the traveller is shown exactly which days will be overwritten and must confirm.

**Blocked by:** 07 (calendar boundary + post step)

**Status:** done

- [x] Re-planning is triggered explicitly (no auto-detection of file changes).
- [x] Before replacing, the traveller is shown the number of days that will be overwritten and must confirm.
- [x] On confirmation, affected calendar events are updated in place rather than duplicated.
- [x] Covered by a test at the calendar seam asserting a Rebuild updates (not duplicates) the affected events.

## Implementation Notes

- `RebuildImpact` dataclass captures impact: days_to_update, events_to_update/add/delete, summary
- `CalendarService` ABC extended with `calculate_rebuild_impact()` and `confirm_and_rebuild()` methods
- `FakeCalendarService` implements both methods - impact analysis + execution
- `GoogleCalendarService` implements both methods - uses list_events to find existing
- 6 new tests in TestRebuildImpact class covering:
  - Empty calendar (all add)
  - Full calendar (all update)
  - Mixed (some update, some add)
  - confirm_and_rebuild execution
  - Travel day handling
