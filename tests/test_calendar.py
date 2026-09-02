"""Tests for calendar boundary.

Tests at the calendar seam:
- CalendarService interface contract
- FakeCalendarService for in-memory testing
- Calendar event creation from itinerary
- Rebuild semantics (update vs duplicate)
- Calendar sharing
"""

from datetime import date, datetime, time

import pytest

from travelminion.calendar import (
    CalendarEvent,
    CalendarResult,
    FakeCalendarService,
    _timeblock_to_event,
)
from travelminion.models import (
    ActivityDay,
    FreeDay,
    Itinerary,
    TimeBlock,
    TravelDay,
    TravelLeg,
)


class TestCalendarEvent:
    """Test CalendarEvent dataclass."""

    def test_create_minimal_event(self) -> None:
        """Create event with minimal fields."""
        event = CalendarEvent(summary="Test Event")
        assert event.summary == "Test Event"
        assert event.event_id is None

    def test_create_full_event(self) -> None:
        """Create event with all fields."""
        event = CalendarEvent(
            event_id="evt_123",
            summary="Museum Visit",
            description="Art museum",
            location="Downtown",
            start_datetime=datetime(2027, 4, 1, 9, 0),
            end_datetime=datetime(2027, 4, 1, 12, 0),
            day_date="2027-04-01",
            activity_index=0,
            calendar_id="cal_456",
        )
        assert event.event_id == "evt_123"
        assert event.activity_index == 0


class TestFakeCalendarService:
    """Test in-memory fake calendar service."""

    def test_create_calendar(self) -> None:
        """Create a new calendar."""
        fake = FakeCalendarService()
        cal_id = fake.create_calendar("Test Calendar", "A test calendar")
        assert cal_id.startswith("cal_")
        assert cal_id in fake.calendars
        assert fake.calendars[cal_id] == "Test Calendar"

    def test_create_multiple_calendars(self) -> None:
        """Create multiple calendars with unique IDs."""
        fake = FakeCalendarService()
        id1 = fake.create_calendar("Cal 1")
        id2 = fake.create_calendar("Cal 2")
        assert id1 != id2
        assert len(fake.calendars) == 2

    def test_share_calendar_reader(self) -> None:
        """Share calendar as read-only."""
        fake = FakeCalendarService()
        cal_id = fake.create_calendar("Shared Calendar")
        result = fake.share_calendar(cal_id, "user@example.com", "reader")
        assert result is True
        assert (cal_id, [("user@example.com", "reader")]) in fake.shares.items()

    def test_share_calendar_writer(self) -> None:
        """Share calendar with write access."""
        fake = FakeCalendarService()
        cal_id = fake.create_calendar("Collab Calendar")
        result = fake.share_calendar(cal_id, "collab@example.com", "writer")
        assert result is True

    def test_share_nonexistent_calendar(self) -> None:
        """Share calendar that doesn't exist."""
        fake = FakeCalendarService()
        result = fake.share_calendar("fake_cal", "user@example.com")
        assert result is False

    def test_create_event(self) -> None:
        """Create an event in a calendar."""
        fake = FakeCalendarService()
        cal_id = fake.create_calendar("Events Calendar")
        event = CalendarEvent(summary="Test Event", start_datetime=datetime(2027, 4, 1, 10, 0))
        event_id = fake.create_event(cal_id, event)
        assert event_id.startswith("evt_")
        assert event.event_id == event_id
        assert event_id in fake.events[cal_id]

    def test_create_event_in_nonexistent_calendar(self) -> None:
        """Create event in calendar that doesn't exist."""
        fake = FakeCalendarService()
        event = CalendarEvent(summary="Orphan Event")
        with pytest.raises(ValueError, match="does not exist"):
            fake.create_event("fake_cal", event)

    def test_update_event(self) -> None:
        """Update an existing event."""
        fake = FakeCalendarService()
        cal_id = fake.create_calendar("Update Calendar")
        event = CalendarEvent(summary="Original")
        event_id = fake.create_event(cal_id, event)
        
        # Modify and update
        event.summary = "Updated Summary"
        result = fake.update_event(cal_id, event)
        assert result is True
        assert fake.events[cal_id][event_id].summary == "Updated Summary"

    def test_update_nonexistent_event(self) -> None:
        """Update event that doesn't exist."""
        fake = FakeCalendarService()
        cal_id = fake.create_calendar("Calendar")
        event = CalendarEvent(event_id="fake_evt", summary="Test")
        result = fake.update_event(cal_id, event)
        assert result is False

    def test_update_event_without_id(self) -> None:
        """Update event without event_id."""
        fake = FakeCalendarService()
        cal_id = fake.create_calendar("Calendar")
        event = CalendarEvent(summary="Test")  # No event_id
        result = fake.update_event(cal_id, event)
        assert result is False

    def test_delete_event(self) -> None:
        """Delete an event."""
        fake = FakeCalendarService()
        cal_id = fake.create_calendar("Delete Calendar")
        event = CalendarEvent(summary="To Delete")
        event_id = fake.create_event(cal_id, event)
        
        result = fake.delete_event(cal_id, event_id)
        assert result is True
        assert event_id not in fake.events[cal_id]

    def test_delete_nonexistent_event(self) -> None:
        """Delete event that doesn't exist."""
        fake = FakeCalendarService()
        cal_id = fake.create_calendar("Calendar")
        result = fake.delete_event(cal_id, "fake_evt")
        assert result is False

    def test_list_events_empty(self) -> None:
        """List events from empty calendar."""
        fake = FakeCalendarService()
        cal_id = fake.create_calendar("Empty Calendar")
        events = fake.list_events(cal_id, "2027-04-01", "2027-04-30")
        assert events == []

    def test_list_events_in_range(self) -> None:
        """List events within date range."""
        fake = FakeCalendarService()
        cal_id = fake.create_calendar("Range Calendar")
        
        # Create events on different dates
        event1 = CalendarEvent(
            summary="Event 1",
            start_datetime=datetime(2027, 4, 5, 10, 0),
            day_date="2027-04-05",
        )
        event2 = CalendarEvent(
            summary="Event 2",
            start_datetime=datetime(2027, 4, 15, 10, 0),
            day_date="2027-04-15",
        )
        fake.create_event(cal_id, event1)
        fake.create_event(cal_id, event2)
        
        # Query partial range
        events = fake.list_events(cal_id, "2027-04-01", "2027-04-10")
        assert len(events) == 1
        assert events[0].summary == "Event 1"


class TestTimeBlockToEvent:
    """Test TimeBlock to CalendarEvent conversion."""

    def test_convert_basic_block(self) -> None:
        """Convert a basic TimeBlock to CalendarEvent."""
        block = TimeBlock(
            start_time=time(9, 0),
            end_time=time(12, 0),
            activity_name="Museum Visit",
            place="City Museum",
            duration="3 hours",
        )
        day_date = date(2027, 4, 1)
        
        event = _timeblock_to_event(block, day_date, 0)
        
        assert event.summary == "Museum Visit"
        assert event.location == "City Museum"
        assert event.start_datetime == datetime(2027, 4, 1, 9, 0)
        assert event.end_datetime == datetime(2027, 4, 1, 12, 0)
        assert event.activity_index == 0

    def test_convert_block_with_transit(self) -> None:
        """Convert block with transit info."""
        block = TimeBlock(
            start_time=time(14, 0),
            end_time=time(16, 0),
            activity_name="Park Walk",
            place="Central Park",
            duration="2 hours",
            transit_to_next="10 min walk",
        )
        day_date = date(2027, 4, 1)
        
        event = _timeblock_to_event(block, day_date, 1)
        
        assert "Next: 10 min walk" in event.description
        assert event.activity_index == 1

    def test_convert_block_with_fallback(self) -> None:
        """Convert block with weather fallback."""
        block = TimeBlock(
            start_time=time(10, 0),
            end_time=time(12, 0),
            activity_name="Beach Time",
            place="Sunny Beach",
            duration="2 hours",
            indoor_fallback="Visit aquarium instead",
        )
        day_date = date(2027, 4, 1)
        
        event = _timeblock_to_event(block, day_date, 0)
        
        assert "Weather fallback: Visit aquarium instead" in event.description


class TestPostItinerary:
    """Test posting full itinerary to calendar."""

    def test_post_activity_day(self) -> None:
        """Post an activity day with multiple time blocks."""
        fake = FakeCalendarService()
        cal_id = fake.create_calendar("Trip Calendar")
        
        itinerary = Itinerary(
            days=[
                ActivityDay(
                    date=date(2027, 4, 1),
                    destination="Tokyo",
                    time_blocks=[
                        TimeBlock(
                            start_time=time(9, 0),
                            end_time=time(12, 0),
                            activity_name="Senso-ji Temple",
                            place="Asakusa",
                            duration="3 hours",
                        ),
                        TimeBlock(
                            start_time=time(14, 0),
                            end_time=time(17, 0),
                            activity_name="Meiji Shrine",
                            place="Shibuya",
                            duration="3 hours",
                        ),
                    ],
                )
            ]
        )
        
        result = fake.post_itinerary(itinerary, cal_id)
        
        assert result.events_posted == 2
        assert result.events_updated == 0
        assert len(result.errors) == 0

    def test_post_travel_day_with_afternoon(self) -> None:
        """Post a travel day with afternoon activity."""
        fake = FakeCalendarService()
        cal_id = fake.create_calendar("Trip Calendar")
        
        itinerary = Itinerary(
            days=[
                TravelDay(
                    date=date(2027, 4, 5),
                    destination="Kyoto",
                    travel_leg=TravelLeg(
                        from_destination="Tokyo",
                        to_destination="Kyoto",
                        mode="shinkansen",
                        duration="2h 15m",
                    ),
                    afternoon_activity=TimeBlock(
                        start_time=time(15, 0),
                        end_time=time(17, 0),
                        activity_name="Explore Gion",
                        place="Gion district",
                        duration="2 hours",
                    ),
                )
            ]
        )
        
        result = fake.post_itinerary(itinerary, cal_id)
        
        assert result.events_posted == 1
        first_event_key = list(fake.events[cal_id].keys())[0]
        assert "Travel: shinkansen" in fake.events[cal_id][first_event_key].summary

    def test_post_free_day(self) -> None:
        """Post a free day (no events created)."""
        fake = FakeCalendarService()
        cal_id = fake.create_calendar("Trip Calendar")
        
        itinerary = Itinerary(
            days=[
                FreeDay(
                    date=date(2027, 4, 10),
                    destination="Tokyo",
                    notes="Recovery day",
                )
            ]
        )
        
        result = fake.post_itinerary(itinerary, cal_id)
        
        assert result.events_posted == 0

    def test_post_mixed_itinerary(self) -> None:
        """Post itinerary with all day types."""
        fake = FakeCalendarService()
        cal_id = fake.create_calendar("Trip Calendar")
        
        itinerary = Itinerary(
            days=[
                ActivityDay(
                    date=date(2027, 4, 1),
                    destination="Tokyo",
                    time_blocks=[
                        TimeBlock(
                            start_time=time(9, 0),
                            end_time=time(12, 0),
                            activity_name="Temple Visit",
                            place="Asakusa",
                            duration="3 hours",
                        )
                    ],
                ),
                TravelDay(
                    date=date(2027, 4, 5),
                    destination="Kyoto",
                    travel_leg=TravelLeg(
                        from_destination="Tokyo",
                        to_destination="Kyoto",
                        mode="train",
                    ),
                    afternoon_activity=TimeBlock(
                        start_time=time(15, 0),
                        end_time=time(17, 0),
                        activity_name="Gion Walk",
                        place="Gion",
                        duration="2 hours",
                    ),
                ),
                FreeDay(
                    date=date(2027, 4, 10),
                    destination="Osaka",
                ),
            ]
        )
        
        result = fake.post_itinerary(itinerary, cal_id)
        
        assert result.events_posted == 2  # 1 activity + 1 travel afternoon
        assert result.calendar_id == cal_id

    def test_rebuild_updates_events(self) -> None:
        """Rebuild updates existing events instead of duplicating."""
        fake = FakeCalendarService()
        cal_id = fake.create_calendar("Trip Calendar")
        
        # Initial post
        itinerary1 = Itinerary(
            days=[
                ActivityDay(
                    date=date(2027, 4, 1),
                    destination="Tokyo",
                    time_blocks=[
                        TimeBlock(
                            start_time=time(9, 0),
                            end_time=time(12, 0),
                            activity_name="Old Activity",
                            place="Old Place",
                            duration="3 hours",
                        )
                    ],
                )
            ]
        )
        
        result1 = fake.post_itinerary(itinerary1, cal_id)
        assert result1.events_posted == 1
        
        # Rebuild with changed activity
        itinerary2 = Itinerary(
            days=[
                ActivityDay(
                    date=date(2027, 4, 1),
                    destination="Tokyo",
                    time_blocks=[
                        TimeBlock(
                            start_time=time(9, 0),
                            end_time=time(12, 0),
                            activity_name="New Activity",
                            place="New Place",
                            duration="3 hours",
                        )
                    ],
                )
            ]
        )
        
        result2 = fake.post_itinerary(itinerary2, cal_id, rebuild=True)
        
        assert result2.events_updated == 1
        assert result2.events_posted == 0
        
        # Verify event was updated, not duplicated
        events = fake.list_events(cal_id, "2027-04-01", "2027-04-01")
        assert len(events) == 1
        assert events[0].summary == "New Activity"

    def test_rebuild_adds_new_days(self) -> None:
        """Rebuild adds new days while updating existing."""
        fake = FakeCalendarService()
        cal_id = fake.create_calendar("Trip Calendar")
        
        # Initial post
        itinerary1 = Itinerary(
            days=[
                ActivityDay(
                    date=date(2027, 4, 1),
                    destination="Tokyo",
                    time_blocks=[
                        TimeBlock(
                            start_time=time(9, 0),
                            end_time=time(12, 0),
                            activity_name="Day 1 Activity",
                            place="Tokyo",
                            duration="3 hours",
                        )
                    ],
                )
            ]
        )
        
        fake.post_itinerary(itinerary1, cal_id)
        
        # Rebuild with additional day
        itinerary2 = Itinerary(
            days=[
                ActivityDay(
                    date=date(2027, 4, 1),
                    destination="Tokyo",
                    time_blocks=[
                        TimeBlock(
                            start_time=time(9, 0),
                            end_time=time(12, 0),
                            activity_name="Day 1 Activity",
                            place="Tokyo",
                            duration="3 hours",
                        )
                    ],
                ),
                ActivityDay(
                    date=date(2027, 4, 2),
                    destination="Tokyo",
                    time_blocks=[
                        TimeBlock(
                            start_time=time(10, 0),
                            end_time=time(13, 0),
                            activity_name="New Day 2 Activity",
                            place="Shibuya",
                            duration="3 hours",
                        )
                    ],
                ),
            ]
        )
        
        result = fake.post_itinerary(itinerary2, cal_id, rebuild=True)
        
        assert result.events_updated == 1  # Day 1 updated
        assert result.events_posted == 1  # Day 2 added
        
        # Verify both days present
        all_events = fake.list_events(cal_id, "2027-04-01", "2027-04-02")
        assert len(all_events) == 2


class TestCalendarResult:
    """Test CalendarResult dataclass."""

    def test_create_result(self) -> None:
        """Create result with default values."""
        result = CalendarResult(calendar_id="cal_1", summary="Test")
        assert result.events_posted == 0
        assert result.events_updated == 0
        assert result.events_deleted == 0
        assert result.shares_created == 0
        assert result.errors == []

    def test_create_result_with_counts(self) -> None:
        """Create result with event counts."""
        result = CalendarResult(
            calendar_id="cal_1",
            summary="Posted itinerary",
            events_posted=5,
            events_updated=2,
            events_deleted=1,
            shares_created=3,
            errors=["Warning 1"],
        )
        assert result.events_posted == 5
        assert result.events_updated == 2
        assert len(result.errors) == 1
