# 02: Interview to Trip Brief

**What to build:** A traveller describes the trip in freeform prose and is asked a short, adaptive clarifying interview that fills only the missing required fields. The captured answers are persisted to the Trip Brief file. The interview branches on the traveller's answers rather than following a fixed checklist, and stays bounded so it never becomes an endless interrogation. When only a one-liner is given, a default interest set still yields a usable brief.

**Blocked by:** 01 (skill skeleton + file-interface primitives)

**Status:** ready-for-agent

- [ ] A freeform prompt is accepted as the starting point for the interview.
- [ ] The interview asks only for genuinely missing required fields: destination(s), dates, interests, travel style/pace.
- [ ] Optional fields (budget, group size, mobility, dietary) are captured when volunteered, without being forced.
- [ ] Follow-up questions branch adaptively on the traveller's answers and the interview terminates within a few rounds.
- [ ] The final answers are written to the Trip Brief, readable and diff-able, and a one-line prompt still yields a usable brief via the default interest set.
