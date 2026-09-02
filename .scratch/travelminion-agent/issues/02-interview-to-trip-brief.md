# 02: Interview to Trip Brief

**What to build:** A traveller describes the trip in freeform prose and is asked a short, adaptive clarifying interview that fills only the missing required fields. The captured answers are persisted to the Trip Brief file. The interview branches on the traveller's answers rather than following a fixed checklist, and stays bounded so it never becomes an endless interrogation. When only a one-liner is given, a default interest set still yields a usable brief.

**Blocked by:** 01 (skill skeleton + file-interface primitives)

**Status:** done

- [x] A freeform prompt is accepted as the starting point for the interview.
- [x] The interview asks only for genuinely missing required fields: destination(s), dates, interests, travel style/pace.
- [x] Optional fields (budget, group size, mobility, dietary) are captured when volunteered, without being forced.
- [x] Follow-up questions branch adaptively on the traveller's answers and the interview terminates within a few rounds.
- [x] The final answers are written to the Trip Brief, readable and diff-able, and a one-line prompt still yields a usable brief via the default interest set.

**Implementation notes:**
- travelminion/interview.py: InterviewState, parse_freeform(), build_question(), answer_question(), finalize_brief()
- 43 tests in tests/test_interview.py covering parsing, question building, answer merging, finalization
- Handles date ranges with inferred year ("April 1 to April 10, 2027")
- Extracts destinations from capitalized proper nouns
- Maps interest synonyms to canonical terms
- Caps interviews at 3 rounds max
- Defaults: DEFAULT_INTERESTS, placeholder dates 6 months out
