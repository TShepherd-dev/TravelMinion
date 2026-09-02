"""Seed templates for trip files.

When TravelMinion is invoked in a blank Trip folder, these templates
are laid down to give the traveller a starting structure.
"""

TRIP_BRIEF_TEMPLATE = """\
---
# Trip Brief
# Fill in the required fields below. The skill will use this to research and plan your trip.
---

# Destinations
# List the places you want to visit with days at each (required)
# Format: destination (name), days (number), order (optional, for explicit ordering)
destinations:
  - destination: 
    days: 3
    order: 0
  - destination: 
    days: 4
    order: 1

# Dates
# When does your trip start and end? (required, format: YYYY-MM-DD)
start_date: 
end_date: 

# Interests
# What do you want to see/do? (required - or leave for defaults)
# Examples: local culture, food, history, nature, art, nightlife, shopping
interests:
  - 

# Travel Style
# How packed do you want your days? (required)
# Options: packed (5-6 activities), casual (2-3 activities), nothing (rest days)
travel_style: casual

# Optional Fields
# budget: moderate
# group_size: 2
# mobility: 
# dietary:
#   - 

# Travellers to Share Calendar With
# Email addresses for read-only calendar access
# travellers_to_share:
#   - 
"""

ACTIVITIES_TEMPLATE = """\
---
# Approved Activity List
# This is the living list that feeds your itinerary.
# Edit, reorder, approve/reject items, or add your own.
---

# Activities
# Each activity has: name, area, typical_duration, destination, approved
# Set approved: true to include in planning, false to exclude

activities: []

# Example:
# activities:
#   - name: Visit the Louvre
#     area: 1st arrondissement
#     typical_duration: 3-4 hours
#     destination: Paris
#     approved: true
#     opening_hours: "9am-6pm, closed Tuesdays"
#     notes: Must see Mona Lisa
#     indoor_fallback: null
"""

ITINERARY_TEMPLATE = """\
---
# Itinerary
# Your day-by-day plan. Generated from the Approved Activity List.
# Feel free to edit before posting to calendar.
---

# Days
# Each day is one of: activity (with time_blocks), travel (moving between places), free (rest)

days: []

# Example activity day:
# days:
#   - date: 2027-04-01
#     destination: Tokyo
#     day_type: activity
#     time_blocks:
#       - start_time: "09:00"
#         end_time: "12:00"
#         activity_name: Senso-ji Temple
#         place: Asakusa
#         duration: 3 hours
#         transit_to_next: 20 min walk
#         indoor_fallback: null

# Example travel day:
#   - date: 2027-04-05
#     destination: Kyoto
#     day_type: travel
#     travel_leg:
#       from_destination: Tokyo
#       to_destination: Kyoto
#       mode: shinkansen
#       duration: 2h 15m
#     afternoon_activity:
#       start_time: "15:00"
#       end_time: "17:00"
#       activity_name: Explore Gion
#       place: Gion district
#       duration: 2 hours

# Example free day:
#   - date: 2027-04-10
#     destination: Seoul
#     day_type: free
#     notes: Recovery day after long travel

# Calendar metadata (set after posting)
# calendar_id: null
# last_posted: null
"""

RESEARCH_OUTPUT_TEMPLATE = """\
---
# Research Output
# Suggestions from live research. Review and approve items to add to your Activity List.
---

# Suggestions by Destination
# Each suggestion has: name, rationale, area, typical_duration, opening_hours,
# approximate_cost, season_weather_fit, source_link, confidence, couldnt_verify

suggestions: []

# Example:
# suggestions:
#   - name: Fushimi Inari Shrine
#     destination: Kyoto
#     rationale: Matches your interest in local culture and photography
#     area: Southern Kyoto
#     typical_duration: 2-3 hours
#     opening_hours: 24 hours (torii gates), shrine buildings 7am-6pm
#     approximate_cost: Free
#     season_weather_fit: Beautiful year-round, early morning best for photos
#     source_link: https://inari.jp/en/
#     confidence: high
#     couldnt_verify: null
"""

# All templates as a dict for easy access
TEMPLATES = {
    "trip-brief.md": TRIP_BRIEF_TEMPLATE,
    "activities.md": ACTIVITIES_TEMPLATE,
    "itinerary.md": ITINERARY_TEMPLATE,
    "research-output.md": RESEARCH_OUTPUT_TEMPLATE,
}
