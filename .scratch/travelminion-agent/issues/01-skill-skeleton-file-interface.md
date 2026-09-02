# 01: Skill skeleton + file-interface primitives

**What to build:** TravelMinion becomes an opencode skill — a `SKILL.md` that describes the workflow and how to invoke its phases, plus the seed templates and the validation-safe primitives for reading and writing this trip's plain Markdown files. A traveller can invoke the skill in a blank Trip folder and have it lay down an empty, structured workspace (the seed files for the Trip Brief, research output, Approved Activity List, and Itinerary) and read/write those files without corrupting them. Sets up the test runner so every later slice can assert behaviour at the seams.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Invoking the skill in a blank Trip folder lays down the seed file templates for the trip's plain Markdown files.
- [ ] The file-interface primitives read each of the trip's files into a typed structure and write them back losslessly.
- [ ] Malformed or missing files are handled gracefully (reported, not crashed), and validation rejects invalid field values.
- [ ] A test runner is installed and a first suite passes at the Trip-folder file-interface seam.
- [ ] The skill's file names and field names use the `CONTEXT.md` glossary vocabulary (Trip Brief, Suggestion, Approved Activity List, Itinerary, Activity Day, Travel Day, Free Day, Travel Leg, Travel Style, Per-trip Calendar, Rebuild).
