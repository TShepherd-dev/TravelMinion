# 01: Skill skeleton + file-interface primitives

**What to build:** TravelMinion becomes an opencode skill — a `SKILL.md` that describes the workflow and how to invoke its phases, plus the seed templates and the validation-safe primitives for reading and writing this trip's plain Markdown files. A traveller can invoke the skill in a blank Trip folder and have it lay down an empty, structured workspace (the seed files for the Trip Brief, research output, Approved Activity List, and Itinerary) and read/write those files without corrupting them. Sets up the test runner so every later slice can assert behaviour at the seams.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Invoking the skill in a blank Trip folder lays down the seed file templates for the trip's plain Markdown files.
- [x] The file-interface primitives read each of the trip's files into a typed structure and write them back losslessly.
- [x] Malformed or missing files are handled gracefully (reported, not crashed), and validation rejects invalid field values.
- [x] A test runner is installed and a first suite passes at the Trip-folder file-interface seam.
- [x] The skill's file names and field names use the `CONTEXT.md` glossary vocabulary (Trip Brief, Suggestion, Approved Activity List, Itinerary, Activity Day, Travel Day, Free Day, Travel Leg, Travel Style, Per-trip Calendar, Rebuild).

## Implementation Notes

Created Python package `travelminion/` with:
- `models.py`: Pydantic models for TripBrief, Suggestion, ApprovedActivity, ApprovedActivityList, Itinerary, ActivityDay, TravelDay, FreeDay, TravelLeg, TimeBlock, TravelStyle
- `files.py`: TripFiles class with read/write primitives for all trip files, graceful error handling
- `templates.py`: Seed templates for trip-brief.md, activities.md, itinerary.md, research-output.md
- `__init__.py`: Public exports

Test suite: `tests/test_files.py` with 29 tests covering:
- Folder operations and seed template creation
- Trip Brief read/write with validation
- Approved Activity List operations
- Itinerary (Activity/Travel/Free days) read/write
- Suggestions (research output) read/write
- Validation and graceful malformed file handling

All tests pass, ruff lint clean, mypy type check clean.
