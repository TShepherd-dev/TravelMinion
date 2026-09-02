# TravelMinion

An agent workflow (an opencode skill) that live-researches a trip's destinations against a traveller's goals, proposes a human-reviewed activity list, and plans that list into a day-by-day itinerary posted to a shared Google Calendar.

## Language

**TravelMinion**:
A skill (agent workflow) invoked inside opencode that researches, plans, and calendar-publishes a trip.
_Avoid_: TravelMinon (old spelling)

**Trip folder**:
The single named directory (e.g. `JapanKorea2027`) that a trip lives in. Holds all trip files; opened blank and is where TravelMinion is invoked.
_Avoid_: Workspace, project

**Trip Brief**:
The persisted capture of the clarifying interview — destinations, dates, interests, travel style, and other inputs — stored in the trip folder.

**Research step**:
The first runnable phase. Live web research (Tavily primary, Jina Reader and `ddgs` as fallbacks) that turns the Trip Brief into a list of attraction suggestions.

**Suggestion**:
A single researched attraction/activity candidate in the research output, carrying details (hours, cost, duration, area, season/weather fit, rationale).
_Avoid_: Item, result, hit

**Approved Activity List**:
The human-owned, living list in the trip folder. Formed by the traveller approving/editing Suggestions and adding their own items. The sole source for itinerary planning. May change over time, forcing itinerary re-generation.
_Avoid_: Final list, chosen list

**Itinerary**:
A time-blocked day-by-day plan built from the Approved Activity List, organized as Activity Days, Travel Days, and Free Days.
_Avoid_: Schedule, plan

**Activity Day**:
An itinerary day with time-blocked activities (start/end, place, duration, transit-to-next).

**Travel Day**:
An itinerary day devoted to moving between destinations.

**Free Day**:
An itinerary day with no planned activities (the "nothing" travel style).

**Travel Leg**:
A single move between two destinations, with a mode and duration, embedded as a block inside a day rather than a standalone day.

**Travel Style**:
The traveller's desired daily density (packed / casual / nothing), mapped to a target number of daily time-blocks.

**Per-trip Calendar**:
A dedicated Google Calendar created for the trip, shared read-only with the travellers. Distinct from the traveller's primary calendar.
_Avoid_: Shared calendar, primary calendar

**Rebuild**:
Re-generating the itinerary (and overwriting affected calendar events instead of duplicating) after the Approved Activity List changes.