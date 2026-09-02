# 09: Convenience wrapper

**What to build:** A traveller can run the whole pipeline with a single convenience invocation — from a fresh Trip folder through interview, research, planning, and posting — while the separate phases remain individually invokable. The wrapper is the thin convenience layer, not the architecture.

**Blocked by:** 02 (interview to Trip Brief), 03 (research + Approved Activity List), 04 (base Itinerary planner), 05 (Travel Days + Travel Legs), 06 (weather fallbacks), 07 (calendar boundary + post step), 08 (rebuild)

**Status:** done

- [x] A single command takes a traveller from a blank Trip folder to a posted Per-trip Calendar.
- [x] Each phase (research, plan, post, rebuild) remains separately invokable on demand.
- [x] The end-to-end flow works with an in-memory fake calendar and canned research, verified by a test through the file-interface seam.

**Implementation notes:**
- `TravelMinionOrchestrator` class in `travelminion/wrapper.py`
- Injectable calendar service (FakeCalendarService default, GoogleCalendarService for production)
- Injectable research engine (ResearchEngine with optional Tavily API key)
- `run_full_pipeline()` method for end-to-end execution
- Individual `phase1_interview()`, `phase2_research()`, `phase3_plan()`, `phase4_post()` methods
- `rebuild()` method for calendar updates
- `PipelineResult` dataclass with summary reporting
- 15 tests in `tests/test_wrapper.py`
- All tests pass, ruff clean
