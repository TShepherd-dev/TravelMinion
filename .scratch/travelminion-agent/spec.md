# TravelMinion Agent Spec

Status: ready-for-agent

## Problem Statement

Planning a multi-destination trip is research-heavy and tedious: a traveller must find candidate attractions, evaluate them against their interests and constraints, then sequence them into a coherent day-by-day plan that respects opening hours, geography, rest, and meals — and finally get that plan onto a shared calendar so fellow travellers can see it. Dozens of hotel and attraction lists abound, but nothing turns a rough idea ("Japan + Korea, two weeks, next spring") into an approved, time-blocked itinerary synchronised to a shared Google Calendar. The traveller wants one place they can hand a target trip to, pull out a researched list to approve, and learn back a posted calendar.

## Solution

TravelMinion is an opencode skill worked in a blank per-trip **Trip folder**. The traveller invokes it, gives a freeform prompt, and answers a short adaptive clarifying interview; the answers are captured in a **Trip Brief**. A **Research step** live-researches each destination and produces a list of **Suggestions**. The traveller reviews and edits these into an **Approved Activity List** (a living file they own). A **plan** phase turns the approved list into an **Itinerary** — ordered **Activity Days**, **Travel Days**, and **Free Days** with time-blocked activities. On explicit confirmation, a **Per-trip Calendar** is created, shared read-only with the travellers, and the itinerary is posted to it as one event per activity. Later edits to the approved list trigger a **Rebuild** that overwrites affected calendar events rather than duplicating them.

Everything the traveller can see and edit is a plain, human-readable file in the Trip folder. The skill never commits to a plan without the traveller's approval, and calendar posts only happen on explicit confirmation.

## User Stories

1. As a traveller, I want to invoke TravelMinion in a blank Trip folder, so that every trip gets its own self-contained workspace.
2. As a traveller, I want to describe my trip in freeform prose, so that I can start planning without filling in a rigid form.
3. As a traveller, I want the skill to ask me adaptive follow-up questions that fill only the gaps in my description, so that I'm not interrogated about things I already told it.
4. As a traveller, I want the interview to stay short and bounded, so that it never feels like an endless interrogation.
5. As a traveller, I want my answers captured into a persisted Trip Brief, so that I (or a future session) can see exactly what was agreed.
6. As a traveller planning a multi-destination trip, I want to list several destinations, so that a single run covers the whole trip.
7. As a traveller, I want to specify required inputs — destinations, dates, interests, and travel style — so that research and planning are grounded in what I actually want.
8. As a traveller, I want optional inputs — budget, group size, mobility, dietary — so that the plan respects constraints I care about without forcing them.
9. As a traveller who gives only a one-liner, I want a sensible default interest set, so that I still get a usable activity list.
10. As a traveller, I want a Research step I can run on demand, so that I control when the live research happens.
11. As a traveller, I want research to fetch up-to-date destination information, so that Suggestions reflect current opening hours, costs, and availability.
12. As a traveller, I want per-destination Suggestions each carrying a name, rationale tied to my interests, area/neighbourhood, typical duration, opening hours, approximate cost, season/weather fit, and a source link, so that I can judge each candidate without opening every page.
13. As a traveller, I want a coverage note like "couldn't verify" where research was thin or failed, so that I don't over-trust an unverified suggestion.
14. As a traveller, I want Suggestions marked with a confidence or holds-up indicator, so that I can weigh how solid each one is.
15. As a traveller, I want the research output written as a human-readable file, so that I can review it in the Trip folder or any editor.
16. As a traveller, I want to approve, reject, reorder, and edit Suggestions, so that the final list reflects my judgment, not the researcher's.
17. As a traveller, I want to add my own non-researched items to the list, so that the plan can include things research would never surface (family visits, reservations, personal commitments).
18. As a traveller, I want my approved and edited choices captured in a living Approved Activity List file, so that the source of truth is durable and diff-able.
19. As a traveller, I want the Approved Activity List to be the sole input to planning, so that the Itinerary never silently re-imports discarded suggestions.
20. As a traveller, I want a plan phase I can run on demand, so that I control when research turns into a schedule.
21. As a traveller, I want the Itinerary organised as ordered Activity Days, Travel Days, and Free Days, so that the plan reads naturally across the trip.
22. As a traveller, I want each activity time-blocked with start/end, place, duration, and transit-to-next, so that each day is realistically executable.
23. As a traveller, I want Travel Days to move between destinations with a lighter (afternoon/evening) activity, so that I don't waste a whole day on transit.
24. As a traveller on a long haul, I want a full Free Day reserved, so that I'm not scheduling too much around brutal travel.
25. As a traveller, I want Free Days to appear when my travel style calls for them, so that the trip has genuine rest.
26. As a traveller, I want the plan to respect opening hours, so that I'm not sent to a closed attraction.
27. As a traveller, I want the plan to keep geographically coherent groupings, so that I'm not criss-crossing the city all day.
28. As a traveller, I want the plan to leave room for rest and meals, so that the trip is sustainable rather than a gauntlet.
29. As a traveller, I want my travel style to map to a sensible daily density (packed ≈ 5-6 blocks, casual ≈ 2-3, nothing ≈ 0-1), so that the pace matches my preference.
30. As a traveller, I want indoor fallback notes on weather-exposed activities, so that I know what to swap to when it rains or turns cold.
31. As a traveller, I want the Itinerary to be a proposal I can freely edit, so that I keep final control over every day.
32. As a traveller, I want to review the Itinerary before anything is posted, so that nothing reaches the calendar without my sign-off.
33. As a traveller, I want a post step that creates a dedicated Per-trip Calendar, so that the trip is separate from my personal calendar.
34. As a traveller, I want the Per-trip Calendar shared read-only with my fellow travellers, so that they can see the plan without being able to change it.
35. As a traveller, I want the post step to run only on explicit confirmation, so that nothing is posted by accident.
36. As a traveller, I want one event per activity, so that my calendar shows a real time-blocked schedule.
37. As a traveller, I want the calendar auth to be set up once and reused across trips, so that I never reauthorise for every trip.
38. As a traveller, I want to trigger a Rebuild when the Approved Activity List changes, so that the calendar reflects my latest decisions.
39. As a traveller, I want a Rebuild to show me exactly which days will be overwritten and get my confirmation first, so that I never lose a day by surprise.
40. As a traveller, I want a Rebuild to overwrite affected calendar events instead of duplicating them, so that my calendar stays clean.
41. As a traveller, I want the trip's plain files to be diff-able, so that I can review what changed between versions.
42. As a traveller, I want to run research, plan, and post as separate explicit sub-phases, so that I can pause and think between each.
43. As a traveller, I want a single convenience invocation that runs the whole pipeline, so that I can get from idea to posted calendar with one command when I'm ready.

## Implementation Decisions

- **Skill structure**: TravelMinion is delivered as an opencode skill (a `SKILL.md` plus supporting scripts and seed templates) with three separately-invokable phases — research, plan, post — plus a thin single-call convenience wrapper. The phases are the architecture; the wrapper is not.
- **Trip folder as single source of truth**: all durable state is plain, human-readable, diff-able Markdown files inside the Trip folder: `trip-brief.md`, the research output, `activities.md` (the Approved Activity List), and `itinerary.md`. No database; the files are the system of record.
- **Trip Brief**: persisted capture of the interview. Required fields: destination(s), dates, interests, travel style/pace. Optional fields: budget, group size, mobility, dietary. A default interest set makes a one-line prompt still yield a usable list.
- **Interview mechanics**: freeform prompt captured first, then a targeted clarifying interview that asks only for genuinely missing required fields. Follow-ups branch adaptively on the traveller's answers (not a fixed checklist) and are capped after a few rounds. Each answer updates the Trip Brief.
- **Research tooling**: Tavily is the primary live-research source; Jina AI Reader (URL → Markdown) and a zero-key DuckDuckGo (`ddgs`) are fallbacks, in that order. Research is an opaque external fetch behind the research seam; the skill shapes raw results into Suggestions.
- **Suggestion fields**: name, rationale (tied to interests), area/neighbourhood, typical duration, opening hours, approximate cost, season/weather fit, source link, confidence/holds-up indicator. Roughly 8–12 Suggestions per destination, variable by days at that destination.
- **Uncertainty surfacing**: Suggestions carry a confidence/holds-up marker; research records a "couldn't verify" note where a source was thin or failed. No suggestion is silently presented as fact.
- **Approved Activity List**: the living, human-owned file. Formed by the traveller approving/editing Suggestions and adding non-researched items. It is the sole input to planning; a finished plan keeps no hidden reference back to unapproved Suggestions.
- **Itinerary**: ordered days of three kinds — Activity Day (time-blocked activities with start/end, place, duration, transit-to-next), Travel Day (a transit move with a lighter afternoon/evening activity), Free Day (no planned activities). Maps 1:1 to calendar events.
- **Travel Legs**: embedded inside a day rather than a standalone day. Morning depart plus afternoon/evening light activity is the default; a full Free Day is reserved sparingly for long hauls. Rough transit leg details (mode + duration) are an optional traveller input.
- **Planning strictness**: structured but editable. The planner respects opening hours, geographic coherence, and rest/meals. Travel style maps to daily density (packed ≈ 5-6 blocks, casual ≈ 2-3, nothing ≈ 0-1). The output is a proposal the traveller freely edits before posting.
- **Seasonality/weather**: research tags each attraction's season and weather fit; the plan offers indoor fallback notes for weather-exposed activities.
- **Calendar integration**: the official Google Calendar API driven through the Python `google-api-client`. One-time Desktop-app OAuth (loopback localhost) writes a `token.json` with a non-expiring refresh token. Credentials and tokens live outside the Trip folder so every trip (and a future monitoring agent) reuses the same auth. Uses the full `calendar` scope so the skill can create the Per-trip Calendar via `calendars.insert`, share it read-only per-user via `acl.insert` (role=reader), and insert/update/delete events.
- **Posting contract**: one calendar event per itinerary activity, time-blocked. A post creates the Per-trip Calendar, shares it read-only with listed travellers, and inserts the events — all only on explicit confirmation.
- **Rebuild semantics**: an explicit re-plan invocation (no auto-detection). Before replacing, it shows "these N days will be overwritten" and requires confirmation. On confirm, affected calendar events are updated in place rather than duplicated.
- **Testing seams** (the three agreed boundaries, highest first): (1) the Trip-folder file interface — the workflow is driven and asserted purely through the plain files; (2) the calendar-posting boundary — a thin abstraction (an interface named for the underlying Calendar capabilities) over `google-api-client` so tests inject a fake/in-memory calendar with no network; (3) the research boundary — an abstraction over the destination-query → Suggestions step so tests supply canned results and assert Suggestion shaping. Each seam's implementor is swappable; tests target the seam, never real external services.
- **Domain vocabulary**: all file names, field names, and prose use the terms defined in `CONTEXT.md` (Trip Brief, Suggestion, Approved Activity List, Itinerary, Activity Day, Travel Day, Free Day, Travel Leg, Travel Style, Per-trip Calendar, Rebuild).

## Testing Decisions

- **What makes a good test**: assert external behaviour through the seams, not internal implementation details. A test should feed a known Trip Brief in and assert the resulting `activities.md`/`itinerary.md` content, or feed a sample Itinerary into the calendar seam and assert the emitted events. Tests never call Tavily, Jina, ddgs, or the real Google Calendar API.
- **Seam 1 — Trip-folder file interface (primary, end-to-end)**: the suite drives the whole workflow through the plain files with no external dependencies. Fixtures are sample `trip-brief.md` inputs; assertions check the produced `activities.md` (approved flags, fields) and `itinerary.md` (ordered days, time-blocks, travel-style density, geographic coherence, meal/rest handling, opening-hours respect, indoor fallback notes).
- **Seam 2 — calendar-posting boundary**: tests target the thin abstraction over Google Calendar via an in-memory fake/contract double. A sample Itinerary is translated to events; assertions check one event per activity with correct start/end/place/duration, the Per-trip Calendar creation, read-only sharing, and that a Rebuild updates (not duplicates) affected events.
- **Seam 3 — research boundary**: lightweight. Canned research results feed the suggestion-shaping logic; assertions check field completeness, confidence markers, the "couldn't verify" note, and the default-interests fallback path.
- **Modules tested**: the file-interface workflow, the itinerary builder, the calendar-posting translator/abstraction, and the suggestion-shaped research output. The interview logic is exercised through the Trip Brief it produces.
- **Prior art**: this is a greenfield skill repo — there is no existing test suite. Tests should be set up under whichever test runner the implementation chooses, mirroring the repo's eventual conventions. Where behaviour is pure file/string transformation, prefer table-driven cases with clear fixtures.

## Out of Scope

- **Automatic change detection / a long-running monitoring agent** that watches the Trip folder and proactively proposes updates. Explicit re-plan invocation only. (The plain-file design and non-expiring tokens make this a natural future addition, but it is not part of this spec.)
- **Actual share-by-invite workflows** beyond the initial read-only share to listed travellers (e.g. later adding/removing travellers via the calendar UI).
- **Placement/hotel booking, flights, or reservations** — the plan schedules activities, not bookings. (Travel-leg transit details are rough inputs only.)
- **Weather forecasting** — only seasonality/weather-appropriateness tags and indoor fallback notes, not live weather.
- **Notifications / day-of reminders** to travellers (calendar-native reminders are left to the traveller's calendar settings).
- **The paid Google Gemini account** — noted as a future research option, not used here; it does not change the search tooling.
- **UI** — the interface is plain files, not a graphical app.
- **A mobile/companion app** for reading the plan (calendar sharing covers read access).

## Further Notes

- Reflecting on the design session: the boundary between "research" and "plan" is deliberately hard — research produces a candidate pool, the traveller owns the Approved Activity List, and planning consumes only that list. This keeps the human in the approval loop and makes the pipeline auditable.
- The `token.json` (non-expiring refresh token) should be treated as a secret: stored outside the Trip folder, never committed, and described in any setup instructions.
- Costs/quota: Tavily's free tier and the Google Calendar API free quota (600 req/min default) are assumed sufficient; no paid tiers are required.
- This spec is the system-of-record for the feature. Implementation tickets derive from it via the repo's issue tracker conventions; mark each with the triage role `ready-for-agent` (`Status: ready-for-agent`).
