# How to Run TravelMinion

## Quick Start

### 1. Register the Skill

Add TravelMinion to your opencode config (`opencode.json`):

```json
{
  "skills": {
    "paths": ["C:/Users/TimShepherd/Documents/My_Dev_Stuff/TravelMinion"]
  }
}
```

**Restart opencode** after editing the config.

### 2. Create a Trip Folder

Create a blank folder for your trip:

```powershell
mkdir C:\path\to\JapanKorea2027
```

### 3. Open in opencode

Open the trip folder as your opencode workspace:

```powershell
cd C:\path\to\JapanKorea2027
opencode
```

### 4. Invoke the Skill

Run:

```
/skill travelminion
```

Or use the phases individually (recommended for control):

---

## Phase-by-Phase Workflow

### Phase 1: Interview → Trip Brief

Give a freeform description:

> "Two weeks in Tokyo and Kyoto, April 1-14 2027. Love temples, food, photography. Casual pace."

The skill will ask clarifying questions for missing required fields:
- Destinations
- Dates (start/end)
- Interests (defaults provided if omitted)
- Travel style: `packed` (5-6/day), `casual` (2-3/day), `nothing` (rest days)

Optional fields you can provide:
- Budget
- Group size
- Mobility constraints
- Dietary restrictions
- Traveller emails (for calendar sharing)

**Output:** `trip-brief.md` in your Trip folder

---

### Phase 2: Research → Suggestions → Approved Activity List

Run research on demand. The skill fetches live destination data and produces suggestions in `research-output.md`:

Each suggestion includes:
- Name, rationale (tied to your interests)
- Area/neighbourhood, typical duration
- Opening hours, approximate cost
- Season/weather fit, source link
- Confidence marker (high/medium/low)
- "Couldn't verify" notes where applicable

**You then edit `activities.md`:**
- Set `approved: true` for items you want
- Set `approved: false` to exclude
- Add your own items (reservations, family visits, etc.)
- Reorder as desired

The Approved Activity List is the **sole input** to planning.

**Output:** `activities.md` (you own this file)

---

### Phase 3: Plan → Itinerary

Run planning on demand. The skill reads `activities.md` and generates `itinerary.md`:

**Day types:**
- **Activity Day**: time-blocked activities with start/end, place, duration, transit-to-next
- **Travel Day**: moving between destinations with lighter afternoon activity
- **Free Day**: no planned activities (rest/recovery)

**Planning respects:**
- Opening hours
- Geographic coherence (clusters nearby activities)
- Rest and meal breaks
- Your travel style (daily density)
- Indoor fallback notes for weather-exposed activities

The itinerary is a **proposal** — edit freely before posting.

**Output:** `itinerary.md`

---

### Phase 4: Post → Per-trip Calendar

On explicit confirmation, the skill:
1. Creates a dedicated Per-trip Calendar
2. Shares it read-only with listed travellers
3. Posts one event per activity with time blocks

**Calendar Setup (One-Time):**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable **Google Calendar API**
4. Configure OAuth consent screen:
   - User type: **External**
   - Add your email as a test user
   - Add scope: `https://www.googleapis.com/auth/calendar`
   - **Set publishing status to "In Production"** (critical for non-expiring refresh token)
5. Create credentials:
   - OAuth client ID
   - Application type: **Desktop app**
   - Download `credentials.json`
6. Store `credentials.json` in `~/.travelminion/` (outside trip folders)

First run opens browser for consent, saves `token.json`. Both files are reused across all trips.

**Output:** Calendar events posted, `calendar_id` saved to `itinerary.md`

---

### Rebuild

After editing `activities.md`, run rebuild to regenerate affected days:

1. Skill shows which days will be overwritten
2. Asks for confirmation
3. Updates calendar events in place (no duplicates)

---

## File Structure

**Agent code** lives in one place:
```
C:/Users/TimShepherd/Documents/My_Dev_Stuff/TravelMinion/
├── travelminion/     # Python package
├── tests/            # Test suite
├── SKILL.md          # Skill definition
└── ...
```

**Trip folders** live completely separately — anywhere you want:
```
C:/Users/TimShepherd/Documents/My_Dev_Stuff/TravelPlans/
├── JapanKoreaFebMar2027/
│   ├── trip-brief.md
│   ├── activities.md
│   ├── itinerary.md
│   └── research-output.md
├── EuropeSummer2027/
└── ...
```

The agent is **stateless** — it reads/writes plain files in your Trip folder. You can:
- Store trips anywhere (Documents, OneDrive, Dropbox, etc.)
- Version control them separately (or not at all)
- Share them via Google Calendar only (no need to share files)
- Keep the agent code frozen and upgrade it independently

---

## Running the Integration Test

To verify everything works end-to-end:

```powershell
cd C:\Users\TimShepherd\Documents\My_Dev_Stuff\TravelMinion
.venv\Scripts\Activate.ps1
python workspace\test_integration.py
```

This runs the full pipeline with fake data (no live research, no real calendar).

---

## Running Unit Tests

```powershell
cd C:\Users\TimShepherd\Documents\My_Dev_Stuff\TravelMinion
.venv\Scripts\Activate.ps1
pytest -v
```

Expected: ~192 tests pass, 1 skipped (DuckDuckGo requires `ddgs` library)

---

## Troubleshooting

### "Skill not found"
- Check `opencode.json` `skills.paths` points to the repo root
- Restart opencode after editing config

### "Refresh token expired"
- Your OAuth consent screen is in "Testing" mode
- Switch to "In Production" (no verification needed for self-use)
- Delete `token.json` and re-authenticate

### "No module named 'ddgs'"
- DuckDuckGo fallback not installed
- Install: `pip install ddgs`
- Or rely on Tavily (requires API key)

---

## Key Files

- `SKILL.md` — Skill definition and workflow
- `CONTEXT.md` — Domain glossary (all vocabulary)
- `travelminion/` — Python package with all logic
- `tests/` — Test suite (192+ tests)
