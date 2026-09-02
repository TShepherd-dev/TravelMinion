# 04: Base Itinerary planner

**What to build:** A traveller runs the plan phase and the Approved Activity List becomes an Itinerary of time-blocked Activity Days. The base planner produces ordered days where each activity has start/end, place, duration, and transit-to-next; respects opening hours; keeps geographically coherent groupings; leaves room for rest and meals; and maps travel style to a sensible daily density (packed ≈ 5-6 blocks, casual ≈ 2-3, nothing ≈ 0-1). The output is a proposal the traveller edits before anything is posted.

**Blocked by:** 01 (skill skeleton + file-interface primitives), 03 (research + Approved Activity List)

**Status:** ready-for-agent

- [ ] The plan phase runs on demand, consuming only the Approved Activity List.
- [ ] Activity Days are produced in order with each activity time-blocked (start/end, place, duration, transit-to-next).
- [ ] The plan respects opening hours and groups activities for geographic coherence.
- [ ] The plan leaves room for rest and meals.
- [ ] Travel style maps to a target daily density of blocks as above.
- [ ] The Itinerary is written as a diff-able Markdown proposal the traveller can edit.
- [ ] Tests at the Trip-folder file interface feed a known Approved Activity List and assert the produced Itinerary (ordered days, time-blocks, density, coherence, opening-hours respect, rest/meals).
