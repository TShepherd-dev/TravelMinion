# 09: Convenience wrapper

**What to build:** A traveller can run the whole pipeline with a single convenience invocation — from a fresh Trip folder through interview, research, planning, and posting — while the separate phases remain individually invokable. The wrapper is the thin convenience layer, not the architecture.

**Blocked by:** 02 (interview to Trip Brief), 03 (research + Approved Activity List), 04 (base Itinerary planner), 05 (Travel Days + Travel Legs), 06 (weather fallbacks), 07 (calendar boundary + post step), 08 (rebuild)

**Status:** ready-for-agent

- [ ] A single command takes a traveller from a blank Trip folder to a posted Per-trip Calendar.
- [ ] Each phase (research, plan, post, rebuild) remains separately invokable on demand.
- [ ] The end-to-end flow works with an in-memory fake calendar and canned research, verified by a test through the file-interface seam.
