# 08: Rebuild

**What to build:** When the Approved Activity List changes, a traveller explicitly re-plans and the affected calendar events are updated in place rather than duplicated. Before replacing, the traveller is shown exactly which days will be overwritten and must confirm.

**Blocked by:** 07 (calendar boundary + post step)

**Status:** ready-for-agent

- [ ] Re-planning is triggered explicitly (no auto-detection of file changes).
- [ ] Before replacing, the traveller is shown the number of days that will be overwritten and must confirm.
- [ ] On confirmation, affected calendar events are updated in place rather than duplicated.
- [ ] Covered by a test at the calendar seam asserting a Rebuild updates (not duplicates) the affected events.
