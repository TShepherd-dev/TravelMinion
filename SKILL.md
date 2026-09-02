---
name: travelminion
description: Plan a multi-destination trip with live research, human-reviewed activity list, and Google Calendar posting. Use when the user wants to research a trip, plan an itinerary, or post a trip to calendar.
---

# TravelMinion

An opencode skill that live-researches trip destinations, proposes a human-reviewed activity list, and plans that list into a day-by-day itinerary posted to a shared Google Calendar.

## Quick Start

1. Create a new Trip folder (e.g., `JapanKorea2027/`)
2. Open it in opencode
3. Run `/skill travelminion` to invoke this skill
4. Follow the phases below

## Phases

TravelMinion has three separately-invokable phases plus a convenience wrapper. Run each phase explicitly, or use the wrapper for a single-command flow.

### Phase 1: Interview → Trip Brief

Start with a freeform description of your trip:

> "Two weeks in Japan and Korea next April, interested in temples, food, and local culture. Casual pace."

The skill asks targeted follow-up questions for anything missing (destinations, dates, interests, travel style). Your answers are captured in `trip-brief.md`.

**Required inputs:**
- Destinations (one or more)
- Dates (start and end)
- Interests (defaults provided if omitted)
- Travel style: `packed` (5-6 activities/day), `casual` (2-3), or `nothing` (rest days)

**Optional inputs:**
- Budget
- Group size
- Mobility constraints
- Dietary restrictions
- Traveller emails (for calendar sharing)
- **Preferred sources**: URLs to research directly (official tourism sites, specific blogs, attraction websites)

### Phase 2: Research → Suggestions → Approved Activity List

Run research on demand. The skill fetches live destination information and produces Suggestions in `research-output.md`:

- Name, rationale (tied to your interests), area, duration
- Opening hours, approximate cost, season/weather fit
- Source link, source name (custom/tavily/ddgs), confidence marker, "couldn't verify" notes

**Custom sources:** If you provided preferred source URLs, these are fetched first via Jina AI Reader and appear at the top of your suggestions list, marked with `source_name: custom`.

**Google Docs export (via MCP):** If Google MCP servers are configured in opencode.json, export `research-output.md` to a Google Doc for collaborative review. Uses opencode's built-in OAuth handling - no code setup needed.

Review the suggestions, then edit `activities.md`:
- Set `approved: true` for items you want in the plan
- Set `approved: false` to exclude
- Add your own items (reservations, family visits, etc.)
- Reorder as desired

The Approved Activity List is the **sole input** to planning.

### Phase 3: Plan → Itinerary

Run planning on demand. The skill reads `activities.md` and generates `itinerary.md`:

**Day types:**
- **Activity Day**: time-blocked activities with start/end, place, duration, transit-to-next
- **Travel Day**: moving between destinations with a lighter afternoon activity
- **Free Day**: no planned activities (rest, recovery)

**Planning respects:**
- Opening hours
- Geographic coherence (cluster nearby activities)
- Rest and meal breaks
- Your travel style (daily density)
- Indoor fallback notes for weather-exposed activities

The itinerary is a proposal — edit freely before posting.

### Phase 4: Post → Per-trip Calendar

On explicit confirmation, the skill:
1. Creates a dedicated Per-trip Calendar
2. Shares it read-only with listed travellers
3. Posts one event per activity with time blocks

Calendar auth is set up once and reused across trips.

### Rebuild

After editing `activities.md`, run a rebuild to regenerate affected days. The skill shows which days will be overwritten and asks for confirmation. Events are updated in place (not duplicated).

## File Structure

All trip state lives as plain, human-readable, diff-able Markdown files:

```
YourTrip/
├── trip-brief.md        # Your trip parameters (destinations, dates, style)
├── research-output.md   # Suggestions from live research
├── activities.md        # Your approved activity list (you edit this)
└── itinerary.md         # Day-by-day plan (generated, editable)
```

## Vocabulary

See `CONTEXT.md` for the full glossary. Key terms:

- **Trip folder**: the directory where your trip lives
- **Trip Brief**: your captured trip parameters
- **Suggestion**: a researched attraction candidate
- **Approved Activity List**: your curated list (sole input to planning)
- **Itinerary**: the day-by-day plan
- **Per-trip Calendar**: dedicated Google Calendar for this trip
- **Rebuild**: regenerate itinerary after list changes

## Installation

### Option 1: Add to skills.paths

In your `opencode.json`:

```json
{
  "skills": {
    "paths": ["C:/path/to/TravelMinion"]
  }
}
```

### Option 2: Symlink to skills directory

```bash
# Windows (PowerShell as Admin)
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.agents\skills\travelminion" -Target "C:\path\to\TravelMinion"

# Unix
ln -s /path/to/TravelMinion ~/.agents/skills/travelminion
```

## Calendar Setup (One-Time)

1. Create a Google Cloud project
2. Enable Google Calendar API
3. Configure OAuth consent screen (External, add your email as test user)
4. Set publishing status to "In Production" (for non-expiring refresh token)
5. Create OAuth client ID (Desktop app type)
6. Download `credentials.json`
7. First run opens browser for consent, saves `token.json`

Store `credentials.json` and `token.json` outside trip folders (e.g., `~/.config/travelminion/`).
