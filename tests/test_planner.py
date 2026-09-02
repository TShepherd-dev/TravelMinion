"""Tests for the base itinerary planner."""

from datetime import date, time

import pytest

from travelminion.models import (
    ActivityDay,
    ApprovedActivity,
    ApprovedActivityList,
    DestinationStop,
    FreeDay,
    TravelDay,
    TravelStyle,
    TripBrief,
)
from travelminion.planner import plan_itinerary


class TestDurationParsing:
    """Test duration string parsing."""
    
    def test_range_hours(self):
        """Parse '2-3 hours' format."""
        from travelminion.planner import _parse_duration
        assert _parse_duration("2-3 hours") == 150
        assert _parse_duration("1-2 hours") == 90
    
    def test_single_hour(self):
        """Parse 'X hours' format."""
        from travelminion.planner import _parse_duration
        assert _parse_duration("2 hours") == 120
        assert _parse_duration("3 hours") == 180
    
    def test_minutes(self):
        """Parse 'X min' format."""
        from travelminion.planner import _parse_duration
        assert _parse_duration("30 min") == 30
        assert _parse_duration("45 min") == 45
    
    def test_half_full_day(self):
        """Parse half/full day."""
        from travelminion.planner import _parse_duration
        assert _parse_duration("half day") == 240
        assert _parse_duration("full day") == 480
    
    def test_empty_defaults(self):
        """Empty duration returns default."""
        from travelminion.planner import _parse_duration
        assert _parse_duration("") == 120
        assert _parse_duration(None) == 120


class TestOpeningHoursParsing:
    """Test opening hours parsing."""
    
    def test_am_pm_format(self):
        """Parse '9am-6pm' format."""
        from travelminion.planner import _parse_opening_hours
        result = _parse_opening_hours("9am-6pm")
        assert result is not None
        open_time, close_time = result
        assert open_time == time(9, 0)
        assert close_time == time(18, 0)
    
    def test_24hour_format(self):
        """Parse '9:00-18:00' format."""
        from travelminion.planner import _parse_opening_hours
        result = _parse_opening_hours("9:00-18:00")
        assert result is not None
        open_time, close_time = result
        assert open_time == time(9, 0)
        assert close_time == time(18, 0)
    
    def test_24_hours(self):
        """Handle '24 hours' as always open."""
        from travelminion.planner import _parse_opening_hours
        assert _parse_opening_hours("24 hours") is None
        assert _parse_opening_hours("always open") is None
    
    def test_no_hours(self):
        """None returns None."""
        from travelminion.planner import _parse_opening_hours
        assert _parse_opening_hours(None) is None
        assert _parse_opening_hours("") is None


class TestTargetDensity:
    """Test travel style to density mapping."""
    
    def test_packed(self):
        """Packed = 5-6 blocks."""
        from travelminion.planner import _get_target_density
        assert _get_target_density(TravelStyle.PACKED) == 5
    
    def test_casual(self):
        """Casual = 2-3 blocks."""
        from travelminion.planner import _get_target_density
        assert _get_target_density(TravelStyle.CASUAL) == 2
    
    def test_nothing(self):
        """Nothing = 0-1 blocks."""
        from travelminion.planner import _get_target_density
        assert _get_target_density(TravelStyle.NOTHING) == 0


class TestGeographicGrouping:
    """Test geographic coherence (grouping by area)."""
    
    def test_groups_by_area(self):
        """Activities in same area stay together."""
        from travelminion.planner import _group_by_area
        
        activities = [
            ApprovedActivity(name="A1", area="Downtown", typical_duration="2 hours", destination="Paris"),
            ApprovedActivity(name="A2", area="Downtown", typical_duration="2 hours", destination="Paris"),
            ApprovedActivity(name="A3", area="Montmartre", typical_duration="2 hours", destination="Paris"),
            ApprovedActivity(name="A4", area="Downtown", typical_duration="2 hours", destination="Paris"),
        ]
        
        groups = _group_by_area(activities)
        
        assert len(groups) == 2
        assert len(groups["downtown"]) == 3
        assert len(groups["montmartre"]) == 1


class TestItineraryPlanner:
    """Test the itinerary planner end-to-end."""
    
    def create_brief(
        self,
        destinations: list[DestinationStop],
        style: TravelStyle = TravelStyle.CASUAL,
    ) -> TripBrief:
        """Helper to create a TripBrief."""
        return TripBrief(
            destinations=destinations,
            start_date=date(2027, 4, 1),
            end_date=date(2027, 4, sum(d.days for d in destinations)),
            interests=["culture", "food"],
            travel_style=style,
        )
    
    def create_activities(self, activities: list[ApprovedActivity]) -> ApprovedActivityList:
        """Helper to create an ApprovedActivityList."""
        return ApprovedActivityList(activities=activities)
    
    def test_single_destination_casual(self):
        """Casual style at single destination produces 2-3 blocks/day."""
        dest = DestinationStop(destination="Paris", days=3, order=0)
        brief = self.create_brief([dest], TravelStyle.CASUAL)
        
        activities = [
            ApprovedActivity(name="Louvre", area="1st", typical_duration="3 hours", destination="Paris"),
            ApprovedActivity(name="Notre-Dame", area="Latin Quarter", typical_duration="2 hours", destination="Paris"),
            ApprovedActivity(name="Eiffel Tower", area="7th", typical_duration="2 hours", destination="Paris"),
        ]
        activity_list = self.create_activities(activities)
        
        itinerary = plan_itinerary(brief, activity_list)
        
        assert len(itinerary.days) == 3
        activity_days = [d for d in itinerary.days if isinstance(d, ActivityDay)]
        
        # Casual should have ~2 activities per day
        for day in activity_days:
            assert len(day.time_blocks) <= 3
    
    def test_single_destination_packed(self):
        """Packed style produces 5-6 blocks/day."""
        dest = DestinationStop(destination="Tokyo", days=2, order=0)
        brief = self.create_brief([dest], TravelStyle.PACKED)
        
        # Create enough activities for packed schedule
        activities = [
            ApprovedActivity(name=f"Activity {i}", area="Shibuya", typical_duration="2 hours", destination="Tokyo")
            for i in range(10)
        ]
        activity_list = self.create_activities(activities)
        
        itinerary = plan_itinerary(brief, activity_list)
        
        assert len(itinerary.days) == 2
        activity_days = [d for d in itinerary.days if isinstance(d, ActivityDay)]
        
        # Packed should have ~5 activities per day
        for day in activity_days:
            assert len(day.time_blocks) >= 3  # At least 3, aim for 5-6
    
    def test_nothing_style_creates_free_days(self):
        """Nothing style creates free days."""
        dest = DestinationStop(destination="Bali", days=3, order=0)
        brief = self.create_brief([dest], TravelStyle.NOTHING)
        
        activities = [
            ApprovedActivity(name="Beach", area="Kuta", typical_duration="2 hours", destination="Bali"),
        ]
        activity_list = self.create_activities(activities)
        
        itinerary = plan_itinerary(brief, activity_list)
        
        # All days should be free days
        free_days = [d for d in itinerary.days if isinstance(d, FreeDay)]
        assert len(free_days) == 3
    
    def test_multi_destination_with_travel_days(self):
        """Multi-destination trip inserts travel days."""
        destinations = [
            DestinationStop(destination="Tokyo", days=3, order=0),
            DestinationStop(destination="Kyoto", days=2, order=1),
        ]
        brief = self.create_brief(destinations, TravelStyle.CASUAL)
        
        activities = [
            ApprovedActivity(name="Tokyo Activity", area="Shibuya", typical_duration="2 hours", destination="Tokyo"),
            ApprovedActivity(name="Kyoto Activity", area="Gion", typical_duration="2 hours", destination="Kyoto"),
        ]
        activity_list = self.create_activities(activities)
        
        itinerary = plan_itinerary(brief, activity_list)
        
        # Should have: 3 Tokyo days + 1 travel day + 2 Kyoto days = 6 days
        assert len(itinerary.days) == 6
        
        # Day 4 should be a travel day (0-indexed: day 3)
        travel_days = [d for d in itinerary.days if isinstance(d, TravelDay)]
        assert len(travel_days) == 1
        assert travel_days[0].travel_leg.from_destination == "Tokyo"
        assert travel_days[0].travel_leg.to_destination == "Kyoto"
    
    def test_empty_activities_creates_free_days(self):
        """No approved activities results in free days."""
        dest = DestinationStop(destination="Paris", days=2, order=0)
        brief = self.create_brief([dest], TravelStyle.CASUAL)
        
        activity_list = self.create_activities([])
        
        itinerary = plan_itinerary(brief, activity_list)
        
        free_days = [d for d in itinerary.days if isinstance(d, FreeDay)]
        assert len(free_days) == 2
    
    def test_time_blocks_have_start_end_transit(self):
        """Time blocks include all required fields."""
        dest = DestinationStop(destination="Paris", days=1, order=0)
        brief = self.create_brief([dest], TravelStyle.CASUAL)
        
        activities = [
            ApprovedActivity(
                name="Louvre",
                area="1st arrondissement",
                typical_duration="2-3 hours",
                destination="Paris",
                opening_hours="9am-6pm",
            ),
        ]
        activity_list = self.create_activities(activities)
        
        itinerary = plan_itinerary(brief, activity_list)
        
        activity_days = [d for d in itinerary.days if isinstance(d, ActivityDay)]
        assert len(activity_days) == 1
        
        blocks = activity_days[0].time_blocks
        assert len(blocks) >= 1
        
        block = blocks[0]
        assert block.start_time is not None
        assert block.end_time is not None
        assert block.activity_name == "Louvre"
        assert block.place == "1st arrondissement"
        assert block.duration == "2-3 hours"
        assert block.transit_to_next is not None
    
    def test_activities_grouped_by_area(self):
        """Activities in same area are scheduled together."""
        dest = DestinationStop(destination="Paris", days=1, order=0)
        brief = self.create_brief([dest], TravelStyle.CASUAL)
        
        activities = [
            ApprovedActivity(name="A1", area="Downtown", typical_duration="2 hours", destination="Paris"),
            ApprovedActivity(name="A2", area="Downtown", typical_duration="2 hours", destination="Paris"),
            ApprovedActivity(name="A3", area="Far Away", typical_duration="2 hours", destination="Paris"),
        ]
        activity_list = self.create_activities(activities)
        
        itinerary = plan_itinerary(brief, activity_list)
        
        activity_days = [d for d in itinerary.days if isinstance(d, ActivityDay)]
        assert len(activity_days) == 1
        
        # Downtown activities should be scheduled consecutively
        blocks = activity_days[0].time_blocks
        if len(blocks) >= 2:
            # First two should be downtown (same area)
            assert blocks[0].place == "Downtown"
            assert blocks[1].place == "Downtown"
    
    def test_itinerary_date_range(self):
        """Itinerary covers correct date range."""
        destinations = [
            DestinationStop(destination="Tokyo", days=3, order=0),
            DestinationStop(destination="Kyoto", days=2, order=1),
        ]
        brief = self.create_brief(destinations, TravelStyle.CASUAL)
        activity_list = self.create_activities([])
        
        itinerary = plan_itinerary(brief, activity_list)
        
        date_range = itinerary.date_range()
        assert date_range is not None
        start, end = date_range
        assert start == date(2027, 4, 1)
        # 3 Tokyo days + 1 travel day + 2 Kyoto days = 6 days total
        assert end == date(2027, 4, 6)
    
    def test_get_day_helper(self):
        """Can retrieve day by date."""
        dest = DestinationStop(destination="Paris", days=2, order=0)
        brief = self.create_brief([dest], TravelStyle.CASUAL)
        activity_list = self.create_activities([])
        
        itinerary = plan_itinerary(brief, activity_list)
        
        day1 = itinerary.get_day(date(2027, 4, 1))
        assert day1 is not None
        assert day1.destination == "Paris"
        
        day2 = itinerary.get_day(date(2027, 4, 2))
        assert day2 is not None
        
        # Non-existent day
        day3 = itinerary.get_day(date(2027, 4, 10))
        assert day3 is None


class TestTransitDurationParsing:
    """Test transit duration string parsing."""
    
    def test_flight_duration(self):
        """Parse 'flight 3h' format."""
        from travelminion.planner import _parse_transit_duration
        assert _parse_transit_duration("flight 3h") == 180
        assert _parse_transit_duration("Flight 2h30m") == 150
    
    def test_train_duration(self):
        """Parse 'train 2h15m' format."""
        from travelminion.planner import _parse_transit_duration
        assert _parse_transit_duration("train 2h15m") == 135
        assert _parse_transit_duration("Train 4 hours") == 240
    
    def test_bus_duration(self):
        """Parse bus duration."""
        from travelminion.planner import _parse_transit_duration
        assert _parse_transit_duration("bus 5h") == 300
        assert _parse_transit_duration("Bus 1h45m") == 105
    
    def test_hours_only(self):
        """Parse hours without minutes."""
        from travelminion.planner import _parse_transit_duration
        assert _parse_transit_duration("3h") == 180
        assert _parse_transit_duration("6 hours") == 360
    
    def test_minutes_only(self):
        """Parse minutes without hours."""
        from travelminion.planner import _parse_transit_duration
        assert _parse_transit_duration("45 min") == 45
        assert _parse_transit_duration("90 minutes") == 90
    
    def test_invalid_or_empty(self):
        """Invalid or empty returns None."""
        from travelminion.planner import _parse_transit_duration
        assert _parse_transit_duration(None) is None
        assert _parse_transit_duration("") is None
        assert _parse_transit_duration("invalid") is None


class TestTravelDaysAndLegs:
    """Test travel day handling with transit legs."""
    
    def create_brief(
        self,
        destinations: list[DestinationStop],
        style: TravelStyle = TravelStyle.CASUAL,
    ) -> TripBrief:
        """Helper to create a TripBrief."""
        return TripBrief(
            destinations=destinations,
            start_date=date(2027, 4, 1),
            end_date=date(2027, 4, sum(d.days for d in destinations) + len(destinations) - 1),
            interests=["culture", "food"],
            travel_style=style,
        )
    
    def create_activities(self, activities: list[ApprovedActivity]) -> ApprovedActivityList:
        """Helper to create an ApprovedActivityList."""
        return ApprovedActivityList(activities=activities)
    
    def test_short_flight_creates_travel_day_with_afternoon(self):
        """Short flight (<6h) creates TravelDay with afternoon activity."""
        destinations = [
            DestinationStop(destination="Paris", days=2, order=0),
            DestinationStop(destination="Rome", days=2, order=1, transit_from_previous="flight 2h"),
        ]
        brief = self.create_brief(destinations)
        activity_list = self.create_activities([])
        
        itinerary = plan_itinerary(brief, activity_list)
        
        # Day 3 should be a travel day (0-indexed: day 2)
        travel_days = [d for d in itinerary.days if isinstance(d, TravelDay)]
        assert len(travel_days) == 1
        assert travel_days[0].travel_leg.from_destination == "Paris"
        assert travel_days[0].travel_leg.to_destination == "Rome"
        assert travel_days[0].travel_leg.mode == "flight"
        assert travel_days[0].afternoon_activity is not None
        assert travel_days[0].afternoon_activity.start_time == time(15, 0)
        assert travel_days[0].afternoon_activity.end_time == time(17, 0)
    
    def test_long_haul_creates_free_day(self):
        """Long haul (>=6h) creates FreeDay for recovery."""
        destinations = [
            DestinationStop(destination="Los Angeles", days=2, order=0),
            DestinationStop(destination="Tokyo", days=3, order=1, transit_from_previous="flight 11h"),
        ]
        brief = self.create_brief(destinations)
        activity_list = self.create_activities([])
        
        itinerary = plan_itinerary(brief, activity_list)
        
        # Day 3 should be a free day (0-indexed: day 2)
        free_days = [d for d in itinerary.days if isinstance(d, FreeDay)]
        assert len(free_days) >= 1
        
        # Find the recovery day
        recovery_day = None
        for day in itinerary.days:
            if isinstance(day, FreeDay) and "Recovery" in (day.notes or ""):
                recovery_day = day
                break
        
        assert recovery_day is not None
        assert recovery_day.destination == "Tokyo"
    
    def test_train_travel_day(self):
        """Train transit creates TravelDay (if under 6 hours)."""
        # Use a shorter train ride that's under the long-haul threshold
        destinations = [
            DestinationStop(destination="Paris", days=2, order=0),
            DestinationStop(destination="Barcelona", days=2, order=1, transit_from_previous="train 5h30m"),
        ]
        brief = self.create_brief(destinations)
        activity_list = self.create_activities([])
        
        itinerary = plan_itinerary(brief, activity_list)
        
        travel_days = [d for d in itinerary.days if isinstance(d, TravelDay)]
        assert len(travel_days) == 1
        assert travel_days[0].travel_leg.mode == "train"
        assert travel_days[0].afternoon_activity is not None
    
    def test_bus_travel_day(self):
        """Bus transit creates TravelDay."""
        destinations = [
            DestinationStop(destination="Tokyo", days=2, order=0),
            DestinationStop(destination="Kyoto", days=2, order=1, transit_from_previous="bus 5h"),
        ]
        brief = self.create_brief(destinations)
        activity_list = self.create_activities([])
        
        itinerary = plan_itinerary(brief, activity_list)
        
        travel_days = [d for d in itinerary.days if isinstance(d, TravelDay)]
        assert len(travel_days) == 1
        assert travel_days[0].travel_leg.mode == "bus"
    
    def test_transit_with_duration_string(self):
        """Transit leg stores duration string."""
        destinations = [
            DestinationStop(destination="London", days=2, order=0),
            DestinationStop(destination="Amsterdam", days=2, order=1, transit_from_previous="train 4h15m"),
        ]
        brief = self.create_brief(destinations)
        activity_list = self.create_activities([])
        
        itinerary = plan_itinerary(brief, activity_list)
        
        travel_days = [d for d in itinerary.days if isinstance(d, TravelDay)]
        assert len(travel_days) == 1
        # Duration should be stored (without the mode)
        assert travel_days[0].travel_leg.duration is not None
    
    def test_threshold_exactly_6_hours(self):
        """Exactly 6 hours (360 min) triggers FreeDay."""
        destinations = [
            DestinationStop(destination="A", days=1, order=0),
            DestinationStop(destination="B", days=1, order=1, transit_from_previous="6h"),
        ]
        brief = self.create_brief(destinations)
        activity_list = self.create_activities([])
        
        itinerary = plan_itinerary(brief, activity_list)
        
        # Should have a free day (recovery)
        free_days = [d for d in itinerary.days if isinstance(d, FreeDay) and "Recovery" in (d.notes or "")]
        assert len(free_days) == 1
    """Test planner through the file interface (end-to-end)."""
    
    @pytest.fixture
    def temp_trip_folder(self, tmp_path):
        """Create a temporary trip folder with files."""
        from travelminion.files import TripFiles
        from travelminion.models import DestinationStop, TripBrief
        
        trip_folder = tmp_path / "test_trip"
        trip_folder.mkdir()
        
        files = TripFiles(trip_folder)
        files.seed_templates()
        
        # Write a trip brief
        brief = TripBrief(
            destinations=[DestinationStop(destination="Paris", days=2, order=0)],
            start_date=date(2027, 4, 1),
            end_date=date(2027, 4, 2),
            interests=["culture"],
            travel_style=TravelStyle.CASUAL,
        )
        files.write_trip_brief(brief)
        
        return files
    
    def test_plan_and_write_itinerary(self, temp_trip_folder):
        """Plan itinerary and write to file, then read back."""
        from travelminion.models import ApprovedActivity, ApprovedActivityList
        
        # Write activities
        activities = ApprovedActivityList(
            activities=[
                ApprovedActivity(
                    name="Louvre",
                    area="1st",
                    typical_duration="3 hours",
                    destination="Paris",
                    approved=True,
                ),
            ]
        )
        temp_trip_folder.write_activities(activities)
        
        # Plan and write
        brief = temp_trip_folder.read_trip_brief()
        itinerary = plan_itinerary(brief, activities)
        temp_trip_folder.write_itinerary(itinerary)
        
        # Read back and verify
        read_itinerary = temp_trip_folder.read_itinerary()
        assert len(read_itinerary.days) == 2
        
        activity_days = [d for d in read_itinerary.days if isinstance(d, ActivityDay)]
        # Should have at least one activity day with the Louvre
        assert len(activity_days) >= 1
