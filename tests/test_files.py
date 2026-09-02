"""Tests for the Trip-folder file interface.

This is the primary test seam per the spec. Tests drive the workflow
through plain files with no external dependencies.
"""

from __future__ import annotations

from datetime import date, time
from pathlib import Path

import pytest

from travelminion.files import (
    FileError,
    TripFiles,
    ValidationError,
)
from travelminion.models import (
    DEFAULT_INTERESTS,
    ActivityDay,
    ApprovedActivity,
    ApprovedActivityList,
    FreeDay,
    Itinerary,
    Suggestion,
    TimeBlock,
    TravelDay,
    TravelLeg,
    TravelStyle,
    TripBrief,
)


class TestTripFilesInit:
    """Test TripFiles initialization and folder operations."""

    def test_exists_for_missing_folder(self, tmp_path: Path) -> None:
        files = TripFiles(tmp_path / "nonexistent")
        assert not files.exists()

    def test_exists_for_existing_folder(self, tmp_path: Path) -> None:
        files = TripFiles(tmp_path)
        assert files.exists()

    def test_ensure_folder_creates_missing(self, tmp_path: Path) -> None:
        folder = tmp_path / "new_trip"
        files = TripFiles(folder)
        assert not folder.exists()
        files.ensure_folder()
        assert folder.exists()

    def test_is_blank_for_new_folder(self, tmp_path: Path) -> None:
        files = TripFiles(tmp_path)
        assert files.is_blank()


class TestSeedTemplates:
    """Test seed template creation."""

    def test_seed_templates_creates_all_files(self, tmp_path: Path) -> None:
        files = TripFiles(tmp_path)
        created = files.seed_templates()

        assert len(created) == 4
        assert "trip-brief.md" in created
        assert "activities.md" in created
        assert "itinerary.md" in created
        assert "research-output.md" in created

        for filename in created:
            assert (tmp_path / filename).exists()

    def test_seed_templates_skips_existing_files(self, tmp_path: Path) -> None:
        # Create one file first
        (tmp_path / "trip-brief.md").write_text("existing content")

        files = TripFiles(tmp_path)
        created = files.seed_templates()

        # Should not recreate trip-brief.md
        assert "trip-brief.md" not in created
        assert len(created) == 3

        # Original content preserved
        assert (tmp_path / "trip-brief.md").read_text() == "existing content"

    def test_is_blank_after_seeding(self, tmp_path: Path) -> None:
        files = TripFiles(tmp_path)
        files.seed_templates()
        assert not files.is_blank()


class TestTripBrief:
    """Test Trip Brief read/write operations."""

    def test_read_valid_trip_brief(self, tmp_path: Path) -> None:
        
        content = """\
---
# Trip Brief
---
destinations:
  - destination: Tokyo
    days: 7
    order: 0
  - destination: Kyoto
    days: 7
    order: 1
start_date: 2027-04-01
end_date: 2027-04-14
interests:
  - temples
  - food
travel_style: casual
budget: moderate
group_size: 2
"""
        (tmp_path / "trip-brief.md").write_text(content)

        files = TripFiles(tmp_path)
        brief = files.read_trip_brief()

        assert len(brief.destinations) == 2
        assert brief.destinations[0].destination == "Tokyo"
        assert brief.destinations[0].days == 7
        assert brief.destinations[1].destination == "Kyoto"
        assert brief.start_date == date(2027, 4, 1)
        assert brief.end_date == date(2027, 4, 14)
        assert brief.interests == ["temples", "food"]
        assert brief.travel_style == TravelStyle.CASUAL
        assert brief.budget == "moderate"
        assert brief.group_size == 2

    def test_read_trip_brief_default_interests(self, tmp_path: Path) -> None:
        content = """\
---
# Trip Brief
---
destinations:
  - Paris
start_date: 2027-05-01
end_date: 2027-05-07
interests:
travel_style: packed
"""
        (tmp_path / "trip-brief.md").write_text(content)

        files = TripFiles(tmp_path)
        brief = files.read_trip_brief()

        # Should get default interests
        assert brief.interests == DEFAULT_INTERESTS

    def test_read_trip_brief_missing_file(self, tmp_path: Path) -> None:
        files = TripFiles(tmp_path)
        with pytest.raises(FileError, match="File not found"):
            files.read_trip_brief()

    def test_read_trip_brief_invalid_dates(self, tmp_path: Path) -> None:
        content = """\
---
# Trip Brief
---
destinations:
  - destination: Rome
    days: 5
start_date: 2027-05-10
end_date: 2027-05-01
interests:
  - history
travel_style: casual
"""
        (tmp_path / "trip-brief.md").write_text(content)

        files = TripFiles(tmp_path)
        with pytest.raises(ValidationError, match="end_date must not be before start_date"):
            files.read_trip_brief()

    def test_write_trip_brief_roundtrip(self, tmp_path: Path) -> None:
        files = TripFiles(tmp_path)
        
        from travelminion.models import DestinationStop

        original = TripBrief(
            destinations=[
                DestinationStop(destination="Seoul", days=5, order=0),
                DestinationStop(destination="Busan", days=5, order=1),
            ],
            start_date=date(2027, 6, 1),
            end_date=date(2027, 6, 10),
            interests=["K-pop", "street food"],
            travel_style=TravelStyle.PACKED,
            budget="luxury",
            group_size=4,
            dietary=["vegetarian"],
        )

        files.write_trip_brief(original)
        assert files.trip_brief_exists()

        loaded = files.read_trip_brief()
        assert loaded.destinations == original.destinations
        assert loaded.start_date == original.start_date
        assert loaded.end_date == original.end_date
        assert loaded.interests == original.interests
        assert loaded.travel_style == original.travel_style
        assert loaded.budget == original.budget
        assert loaded.group_size == original.group_size
        assert loaded.dietary == original.dietary


class TestApprovedActivityList:
    """Test Approved Activity List read/write operations."""

    def test_read_empty_activities(self, tmp_path: Path) -> None:
        content = """\
---
# Approved Activity List
---
activities: []
"""
        (tmp_path / "activities.md").write_text(content)

        files = TripFiles(tmp_path)
        activity_list = files.read_activities()

        assert len(activity_list.activities) == 0

    def test_read_activities_with_items(self, tmp_path: Path) -> None:
        content = """\
---
# Approved Activity List
---
activities:
  - name: Visit the Louvre
    area: 1st arrondissement
    typical_duration: 3-4 hours
    destination: Paris
    approved: true
    opening_hours: 9am-6pm
    notes: Must see Mona Lisa
  - name: Eiffel Tower
    area: 7th arrondissement
    typical_duration: 2 hours
    destination: Paris
    approved: false
"""
        (tmp_path / "activities.md").write_text(content)

        files = TripFiles(tmp_path)
        activity_list = files.read_activities()

        assert len(activity_list.activities) == 2
        assert activity_list.activities[0].name == "Visit the Louvre"
        assert activity_list.activities[0].approved is True
        assert activity_list.activities[1].approved is False

        # Test approved_only filter
        approved = activity_list.approved_only()
        assert len(approved) == 1
        assert approved[0].name == "Visit the Louvre"

    def test_write_activities_roundtrip(self, tmp_path: Path) -> None:
        files = TripFiles(tmp_path)

        original = ApprovedActivityList(
            activities=[
                ApprovedActivity(
                    name="Senso-ji Temple",
                    area="Asakusa",
                    typical_duration="2 hours",
                    destination="Tokyo",
                    approved=True,
                    indoor_fallback="Tokyo National Museum",
                ),
                ApprovedActivity(
                    name="Shibuya Crossing",
                    area="Shibuya",
                    typical_duration="30 minutes",
                    destination="Tokyo",
                    approved=True,
                ),
            ]
        )

        files.write_activities(original)
        loaded = files.read_activities()

        assert len(loaded.activities) == 2
        assert loaded.activities[0].name == "Senso-ji Temple"
        assert loaded.activities[0].indoor_fallback == "Tokyo National Museum"

    def test_activities_by_destination(self, tmp_path: Path) -> None:
        _ = TripFiles(tmp_path)  # Not used but validates folder setup

        activity_list = ApprovedActivityList(
            activities=[
                ApprovedActivity(
                    name="A", area="x", typical_duration="1h", destination="Tokyo", approved=True
                ),
                ApprovedActivity(
                    name="B", area="y", typical_duration="1h", destination="Kyoto", approved=True
                ),
                ApprovedActivity(
                    name="C", area="z", typical_duration="1h", destination="Tokyo", approved=False
                ),
            ]
        )

        tokyo = activity_list.by_destination("Tokyo")
        assert len(tokyo) == 1  # Only approved ones
        assert tokyo[0].name == "A"

        kyoto = activity_list.by_destination("Kyoto")
        assert len(kyoto) == 1
        assert kyoto[0].name == "B"


class TestItinerary:
    """Test Itinerary read/write operations."""

    def test_read_empty_itinerary(self, tmp_path: Path) -> None:
        content = """\
---
# Itinerary
---
days: []
"""
        (tmp_path / "itinerary.md").write_text(content)

        files = TripFiles(tmp_path)
        itinerary = files.read_itinerary()

        assert len(itinerary.days) == 0

    def test_read_activity_day(self, tmp_path: Path) -> None:
        content = """\
---
# Itinerary
---
days:
  - date: 2027-04-01
    destination: Tokyo
    day_type: activity
    time_blocks:
      - start_time: "09:00"
        end_time: "12:00"
        activity_name: Senso-ji Temple
        place: Asakusa
        duration: 3 hours
        transit_to_next: 20 min train
"""
        (tmp_path / "itinerary.md").write_text(content)

        files = TripFiles(tmp_path)
        itinerary = files.read_itinerary()

        assert len(itinerary.days) == 1
        day = itinerary.days[0]
        assert isinstance(day, ActivityDay)
        assert day.day_date == date(2027, 4, 1)
        assert day.destination == "Tokyo"
        assert len(day.time_blocks) == 1
        assert day.time_blocks[0].activity_name == "Senso-ji Temple"
        assert day.time_blocks[0].start_time == time(9, 0)
        assert day.time_blocks[0].end_time == time(12, 0)

    def test_read_travel_day(self, tmp_path: Path) -> None:
        content = """\
---
# Itinerary
---
days:
  - date: 2027-04-05
    destination: Kyoto
    day_type: travel
    travel_leg:
      from_destination: Tokyo
      to_destination: Kyoto
      mode: shinkansen
      duration: 2h 15m
    afternoon_activity:
      start_time: "15:00"
      end_time: "17:00"
      activity_name: Explore Gion
      place: Gion district
      duration: 2 hours
"""
        (tmp_path / "itinerary.md").write_text(content)

        files = TripFiles(tmp_path)
        itinerary = files.read_itinerary()

        assert len(itinerary.days) == 1
        day = itinerary.days[0]
        assert isinstance(day, TravelDay)
        assert day.travel_leg.from_destination == "Tokyo"
        assert day.travel_leg.to_destination == "Kyoto"
        assert day.travel_leg.mode == "shinkansen"
        assert day.afternoon_activity is not None
        assert day.afternoon_activity.activity_name == "Explore Gion"

    def test_read_free_day(self, tmp_path: Path) -> None:
        content = """\
---
# Itinerary
---
days:
  - date: 2027-04-10
    destination: Seoul
    day_type: free
    notes: Recovery day after flight
"""
        (tmp_path / "itinerary.md").write_text(content)

        files = TripFiles(tmp_path)
        itinerary = files.read_itinerary()

        assert len(itinerary.days) == 1
        day = itinerary.days[0]
        assert isinstance(day, FreeDay)
        assert day.notes == "Recovery day after flight"

    def test_write_itinerary_roundtrip(self, tmp_path: Path) -> None:
        files = TripFiles(tmp_path)

        original = Itinerary(
            days=[
                ActivityDay(
                    date=date(2027, 4, 1),
                    destination="Tokyo",
                    time_blocks=[
                        TimeBlock(
                            start_time=time(9, 0),
                            end_time=time(12, 0),
                            activity_name="Morning temple",
                            place="Asakusa",
                            duration="3 hours",
                        ),
                    ],
                ),
                TravelDay(
                    date=date(2027, 4, 2),
                    destination="Kyoto",
                    travel_leg=TravelLeg(
                        from_destination="Tokyo",
                        to_destination="Kyoto",
                        mode="train",
                        duration="2.5h",
                    ),
                ),
                FreeDay(
                    date=date(2027, 4, 3),
                    destination="Kyoto",
                    notes="Rest day",
                ),
            ],
            calendar_id="test-calendar-123",
        )

        files.write_itinerary(original)
        loaded = files.read_itinerary()

        assert len(loaded.days) == 3
        assert isinstance(loaded.days[0], ActivityDay)
        assert isinstance(loaded.days[1], TravelDay)
        assert isinstance(loaded.days[2], FreeDay)
        assert loaded.calendar_id == "test-calendar-123"

    def test_itinerary_get_day(self, tmp_path: Path) -> None:
        itinerary = Itinerary(
            days=[
                ActivityDay(date=date(2027, 4, 1), destination="Tokyo", time_blocks=[]),
                FreeDay(date=date(2027, 4, 2), destination="Tokyo"),
            ]
        )

        day1 = itinerary.get_day(date(2027, 4, 1))
        assert day1 is not None
        assert isinstance(day1, ActivityDay)

        day2 = itinerary.get_day(date(2027, 4, 2))
        assert day2 is not None
        assert isinstance(day2, FreeDay)

        day3 = itinerary.get_day(date(2027, 4, 3))
        assert day3 is None


class TestSuggestions:
    """Test research output (Suggestions) read/write operations."""

    def test_read_suggestions(self, tmp_path: Path) -> None:
        content = """\
---
# Research Output
---
suggestions:
  - name: Fushimi Inari Shrine
    destination: Kyoto
    rationale: Matches your interest in temples
    area: Southern Kyoto
    typical_duration: 2-3 hours
    opening_hours: 24 hours
    approximate_cost: Free
    season_weather_fit: Year-round
    source_link: https://inari.jp
    confidence: high
  - name: Uncertain Place
    destination: Kyoto
    rationale: Might be interesting
    area: Unknown
    typical_duration: 1 hour
    confidence: low
    couldnt_verify: Opening hours not confirmed
"""
        (tmp_path / "research-output.md").write_text(content)

        files = TripFiles(tmp_path)
        suggestions = files.read_suggestions()

        assert len(suggestions) == 2
        assert suggestions[0].name == "Fushimi Inari Shrine"
        assert suggestions[0].confidence == "high"
        assert suggestions[1].confidence == "low"
        assert suggestions[1].couldnt_verify == "Opening hours not confirmed"

    def test_write_suggestions_roundtrip(self, tmp_path: Path) -> None:
        files = TripFiles(tmp_path)

        original = [
            Suggestion(
                name="Test Place",
                destination="Tokyo",
                rationale="For testing",
                area="Shibuya",
                typical_duration="1 hour",
                confidence="medium",
            ),
        ]

        files.write_suggestions(original)
        loaded = files.read_suggestions()

        assert len(loaded) == 1
        assert loaded[0].name == "Test Place"
        assert loaded[0].confidence == "medium"


class TestValidation:
    """Test validation and error handling."""

    def test_validate_all_valid_files(self, tmp_path: Path) -> None:
        from travelminion.models import DestinationStop
        
        files = TripFiles(tmp_path)
        files.seed_templates()

        # Write valid data
        files.write_trip_brief(
            TripBrief(
                destinations=[DestinationStop(destination="Paris", days=7, order=0)],
                start_date=date(2027, 5, 1),
                end_date=date(2027, 5, 7),
                interests=["art"],
                travel_style=TravelStyle.CASUAL,
            )
        )
        files.write_activities(ApprovedActivityList(activities=[]))
        files.write_itinerary(Itinerary(days=[]))
        files.write_suggestions([])

        results = files.validate_all()

        # All should be None (no errors)
        for filename, error in results.items():
            assert error is None, f"{filename} had error: {error}"

    def test_validate_catches_malformed_file(self, tmp_path: Path) -> None:
        # Write malformed trip brief (end before start)
        content = """\
---
# Trip Brief
---
destinations:
  - Rome
start_date: 2027-05-10
end_date: 2027-05-01
interests:
  - history
travel_style: casual
"""
        (tmp_path / "trip-brief.md").write_text(content)

        files = TripFiles(tmp_path)
        results = files.validate_all()

        assert results["trip-brief.md"] is not None
        assert "end_date" in results["trip-brief.md"]

    def test_graceful_handling_malformed_activity(self, tmp_path: Path) -> None:
        """Malformed activities should be skipped, not crash."""
        content = """\
---
# Approved Activity List
---
activities:
  - name: Valid Activity
    area: Downtown
    typical_duration: 2 hours
    destination: Paris
    approved: true
  - invalid: this is not a valid activity format
  - name: Another Valid
    area: Uptown
    typical_duration: 1 hour
    destination: Paris
    approved: true
"""
        (tmp_path / "activities.md").write_text(content)

        files = TripFiles(tmp_path)
        activity_list = files.read_activities()

        # Should have 2 valid activities, skipping the malformed one
        assert len(activity_list.activities) == 2
        assert activity_list.activities[0].name == "Valid Activity"
        assert activity_list.activities[1].name == "Another Valid"


class TestAllFilesExist:
    """Test file existence checking."""

    def test_all_files_exist_empty_folder(self, tmp_path: Path) -> None:
        files = TripFiles(tmp_path)
        status = files.all_files_exist()

        assert status["trip-brief.md"] is False
        assert status["activities.md"] is False
        assert status["itinerary.md"] is False
        assert status["research-output.md"] is False

    def test_all_files_exist_after_seeding(self, tmp_path: Path) -> None:
        files = TripFiles(tmp_path)
        files.seed_templates()
        status = files.all_files_exist()

        assert all(status.values())
