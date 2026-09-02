#!/usr/bin/env python3
"""Integration test: blank folder -> itinerary (manual data, no live research)."""

import sys
from pathlib import Path
from datetime import date

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from travelminion.files import TripFiles
from travelminion.models import (
    TripBrief, DestinationStop, TravelStyle,
    ApprovedActivity, ApprovedActivityList
)
from travelminion.planner import ItineraryPlanner
from travelminion.calendar import FakeCalendarService

# Test trip folder - change this to your actual trip folder
TRIP_FOLDER = Path("C:/Users/TimShepherd/Documents/My_Dev_Stuff/TravelPlans/JapanKoreaFebMar2027")

def main():
    print("=" * 60)
    print("TRAVELMINION INTEGRATION TEST")
    print("=" * 60)
    
    # Setup
    trip = TripFiles(TRIP_FOLDER)
    trip.ensure_folder()
    
    print(f"\n1. Seeding templates in {TRIP_FOLDER}...")
    created = trip.seed_templates()
    print(f"   Created: {', '.join(created)}")
    
    # Phase 1: Create Trip Brief manually
    print("\n2. PHASE 1: Create Trip Brief")
    brief = TripBrief(
        destinations=[
            DestinationStop(destination="Tokyo", days=5, order=0),
            DestinationStop(destination="Kyoto", days=5, order=1, transit_from_previous="flight 2h"),
        ],
        start_date=date(2027, 4, 1),
        end_date=date(2027, 4, 10),
        interests=["temples", "food", "photography"],
        travel_style=TravelStyle.CASUAL
    )
    trip.write_trip_brief(brief)
    print(f"   -> Trip Brief: Tokyo (5 days) + Kyoto (5 days)")
    print(f"   -> Dates: {brief.start_date} to {brief.end_date}")
    print(f"   -> Style: {brief.travel_style.value}")
    
    # Phase 2: Create Approved Activity List manually
    print("\n3. PHASE 2: Create Approved Activity List")
    activities = [
        ApprovedActivity(
            name="Senso-ji Temple",
            area="Asakusa",
            typical_duration="2-3 hours",
            destination="Tokyo",
            approved=True,
            opening_hours="24 hours (temple grounds), 9am-5pm (main hall)",
            indoor_fallback=None
        ),
        ApprovedActivity(
            name="Tsukiji Outer Market",
            area="Central Tokyo",
            typical_duration="2-3 hours",
            destination="Tokyo",
            approved=True,
            opening_hours="5am-2pm",
            indoor_fallback=None
        ),
        ApprovedActivity(
            name="Meiji Shrine",
            area="Shibuya",
            typical_duration="1-2 hours",
            destination="Tokyo",
            approved=True,
            opening_hours="Sunrise to sunset",
            indoor_fallback=None
        ),
        ApprovedActivity(
            name="Fushimi Inari Shrine",
            area="Southern Kyoto",
            typical_duration="2-3 hours",
            destination="Kyoto",
            approved=True,
            opening_hours="24 hours",
            indoor_fallback=None
        ),
        ApprovedActivity(
            name="Kinkaku-ji (Golden Pavilion)",
            area="Northern Kyoto",
            typical_duration="1-2 hours",
            destination="Kyoto",
            approved=True,
            opening_hours="9am-5pm",
            indoor_fallback=None
        ),
        ApprovedActivity(
            name="Arashiyama Bamboo Grove",
            area="Western Kyoto",
            typical_duration="1-2 hours",
            destination="Kyoto",
            approved=True,
            opening_hours="24 hours",
            indoor_fallback="Visit nearby Tenryu-ji Temple (indoor halls)"
        ),
    ]
    activity_list = ApprovedActivityList(activities=activities)
    trip.write_activities(activity_list)
    print(f"   -> Approved {len(activities)} activities")
    for a in activities:
        print(f"      - {a.name} ({a.destination})")
    
    # Phase 3: Plan Itinerary
    print("\n4. PHASE 3: Plan -> Itinerary")
    planner = ItineraryPlanner(brief, activity_list)
    itinerary = planner.plan()
    trip.write_itinerary(itinerary)
    print(f"   -> Itinerary: {len(itinerary.days)} days")
    
    for i, day in enumerate(itinerary.days, 1):
        day_type = day.__class__.__name__.replace("Day", "").lower()
        print(f"      Day {i} ({day.day_date}): {day_type} in {day.destination}")
    
    # Phase 4: Post to Calendar (fake)
    print("\n5. PHASE 4: Post -> Calendar (Fake)")
    calendar = FakeCalendarService()
    calendar_id = calendar.create_calendar("Trip to Japan 2027")
    result = calendar.post_itinerary(itinerary, calendar_id)
    print(f"   -> Calendar ID: {calendar_id}")
    print(f"   -> Events posted: {result.events_posted}")
    
    # Test rebuild
    print("\n6. REBUILD TEST")
    impact = calendar.calculate_rebuild_impact(itinerary, calendar_id)
    print(f"   -> Impact: {impact.summary}")
    
    # Summary
    print("\n" + "=" * 60)
    print("INTEGRATION TEST COMPLETE")
    print("=" * 60)
    print(f"\nFiles created in {TRIP_FOLDER}:")
    for filename, exists in trip.all_files_exist().items():
        status = "OK" if exists else "MISSING"
        print(f"   [{status}] {filename}")
    
    print(f"\nDestinations: {len(brief.destinations)}")
    print(f"Activities: {len(activities)}")
    print(f"Days planned: {len(itinerary.days)}")
    print(f"Events posted: {result.events_posted}")
    print("\nOK - All phases executed successfully!")

if __name__ == "__main__":
    main()
