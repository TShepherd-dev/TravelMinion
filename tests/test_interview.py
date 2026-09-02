"""Tests for Interview flow."""

from datetime import date

from travelminion.interview import (
    InterviewState,
    _parse_date,
    _parse_destinations,
    _parse_interests,
    _parse_travel_style,
    answer_question,
    build_question,
    finalize_brief,
    parse_freeform,
)
from travelminion.models import DEFAULT_INTERESTS, TravelStyle, TripBrief


class TestInterviewState:
    """Test InterviewState dataclass."""

    def test_initial_state_has_all_fields_empty(self) -> None:
        state = InterviewState()
        assert state.destinations == []
        assert state.start_date is None
        assert state.end_date is None
        assert state.interests == []
        assert state.travel_style is None
        assert state.round_count == 0

    def test_missing_required_returns_all_when_empty(self):
        state = InterviewState()
        missing = state.missing_required()
        assert len(missing) == 5
        assert "destinations" in missing
        assert "start_date" in missing
        assert "end_date" in missing
        assert "interests" in missing
        assert "travel_style" in missing

    def test_missing_required_returns_empty_when_complete(self):
        state = InterviewState(
            destinations=["Tokyo"],
            start_date="2027-04-01",
            end_date="2027-04-10",
            interests=["culture"],
            travel_style=TravelStyle.CASUAL,
        )
        assert state.missing_required() == []
        assert state.is_complete() is True

    def test_can_ask_more_respects_max_rounds(self):
        state = InterviewState(max_rounds=3)
        state.round_count = 2
        assert state.can_ask_more() is True

        state.round_count = 3
        assert state.can_ask_more() is False

    def test_can_ask_more_false_when_complete(self):
        state = InterviewState(
            destinations=["Paris"],
            start_date="2027-05-01",
            end_date="2027-05-10",
            interests=["art"],
            travel_style=TravelStyle.PACKED,
        )
        assert state.is_complete() is True
        assert state.can_ask_more() is False


class TestParseDate:
    """Test date extraction from text."""

    def test_iso_format(self):
        assert _parse_date("2027-04-15") == "2027-04-15"

    def test_month_name_format(self):
        assert _parse_date("April 15, 2027") == "2027-04-15"

    def test_day_month_year_format(self):
        assert _parse_date("15th April 2027") == "2027-04-15"

    def test_without_comma(self):
        assert _parse_date("April 15 2027") == "2027-04-15"

    def test_ordinal_days(self):
        assert _parse_date("1st January 2027") == "2027-01-01"
        assert _parse_date("2nd February 2027") == "2027-02-02"
        assert _parse_date("3rd March 2027") == "2027-03-03"
        assert _parse_date("22nd December 2027") == "2027-12-22"

    def test_returns_none_for_invalid(self):
        assert _parse_date("next week") is None
        assert _parse_date("sometime in spring") is None


class TestParseDestinations:
    """Test destination extraction from text."""

    def test_simple_list(self):
        dests = _parse_destinations("I want to visit Tokyo, Kyoto, and Seoul")
        assert "Tokyo" in dests
        assert "Kyoto" in dests
        assert "Seoul" in dests

    def test_with_country(self):
        dests = _parse_destinations("Traveling to Japan (Tokyo and Osaka)")
        assert "Japan" in dests or "Tokyo" in dests

    def test_two_cities(self):
        dests = _parse_destinations("Paris and London")
        assert "Paris" in dests
        assert "London" in dests

    def test_removes_prefixes(self):
        dests = _parse_destinations("Going to Bangkok and Chiang Mai")
        assert "Bangkok" in dests
        assert "Chiang Mai" in dests or "Chiang" in dests

    def test_caps_at_five(self):
        text = (
            "Tokyo, Kyoto, Osaka, Seoul, Busan, Taipei, "
            "Hong Kong, Singapore, Bangkok, Chiang Mai"
        )
        dests = _parse_destinations(text)
        assert len(dests) <= 5


class TestParseInterests:
    """Test interest extraction from text."""

    def test_finds_common_interests(self):
        interests = _parse_interests("I love local culture, food, and history")
        assert "local culture" in interests or "culture" in interests
        assert "food" in interests
        assert "history" in interests

    def test_maps_synonyms(self):
        interests = _parse_interests("I'm into restaurants and cuisine")
        assert "food" in interests

    def test_finds_nature_interests(self):
        interests = _parse_interests("I want hiking and outdoors")
        assert "nature" in interests

    def test_caps_at_eight(self):
        text = (
            "culture food history art nature shopping nightlife "
            "photography architecture temples wildlife adventure "
            "sports relaxation"
        )
        interests = _parse_interests(text)
        assert len(interests) <= 8


class TestParseTravelStyle:
    """Test travel style extraction from text."""

    def test_packed_keywords(self):
        assert _parse_travel_style("I want a packed itinerary") == TravelStyle.PACKED
        assert _parse_travel_style("maximize every moment") == TravelStyle.PACKED
        assert _parse_travel_style("as much as possible") == TravelStyle.PACKED

    def test_nothing_keywords(self):
        assert _parse_travel_style("I want to relax and unwind") == TravelStyle.NOTHING
        assert _parse_travel_style("just chill") == TravelStyle.NOTHING
        assert _parse_travel_style("rest days") == TravelStyle.NOTHING

    def test_casual_keywords(self):
        assert _parse_travel_style("casual pace") == TravelStyle.CASUAL
        assert _parse_travel_style("moderate schedule") == TravelStyle.CASUAL

    def test_returns_none_for_unknown(self):
        assert _parse_travel_style("I don't know") is None


class TestParseFreeform:
    """Test full freeform parsing."""

    def test_extracts_all_fields(self):
        text = """
        I'm traveling to Tokyo and Kyoto, Japan from 2027-04-01 to 2027-04-10.
        I'm interested in local culture, food, and history.
        I want a packed schedule to maximize our time.
        Budget: moderate
        Group size: 2
        """
        state = parse_freeform(text)
        assert "Tokyo" in state.destinations
        assert state.start_date == "2027-04-01"
        assert state.end_date == "2027-04-10"
        assert "local culture" in state.interests or "culture" in state.interests
        assert "food" in state.interests
        assert state.travel_style == TravelStyle.PACKED
        assert state.budget == "moderate"
        assert state.group_size == 2

    def test_handles_natural_dates(self):
        text = "Visiting Paris from April 1, 2027 to April 10, 2027"
        state = parse_freeform(text)
        assert state.start_date == "2027-04-01"
        assert state.end_date == "2027-04-10"

    def test_handles_partial_info(self):
        text = "Just want to relax in Bali"
        state = parse_freeform(text)
        assert "Bali" in state.destinations
        assert state.travel_style == TravelStyle.NOTHING
        assert state.start_date is None  # Not provided

    def test_empty_text_returns_empty_state(self):
        state = parse_freeform("")
        assert state.destinations == []
        assert state.interests == []
        assert state.travel_style is None


class TestBuildQuestion:
    """Test question generation for missing fields."""

    def test_single_missing_field(self):
        q = build_question(["destinations"], InterviewState())
        assert "Where" in q or "travel" in q.lower()

    def test_both_dates_together(self):
        q = build_question(["start_date", "end_date"], InterviewState())
        assert "start" in q.lower() and "end" in q.lower()

    def test_only_start_date_missing(self):
        state = InterviewState(end_date="2027-04-10")
        q = build_question(["start_date"], state)
        assert "start" in q.lower()
        assert "end" not in q.lower()

    def test_multiple_fields_numbered(self):
        q = build_question(["destinations", "interests"], InterviewState())
        assert "1." in q and "2." in q

    def test_travel_style_explains_options(self):
        q = build_question(["travel_style"], InterviewState())
        assert "packed" in q.lower()
        assert "casual" in q.lower()


class TestAnswerQuestion:
    """Test answer parsing and state merging."""

    def test_updates_destinations(self):
        state = InterviewState()
        state = answer_question("I want to go to Tokyo", state)
        assert "Tokyo" in state.destinations
        assert state.round_count == 1

    def test_updates_dates(self):
        state = InterviewState()
        state = answer_question("April 1 to April 10, 2027", state)
        assert state.start_date == "2027-04-01"
        assert state.end_date == "2027-04-10"
        assert state.round_count == 1

    def test_does_not_overwrite_existing(self):
        state = InterviewState(destinations=["Paris"], start_date="2027-05-01")
        state = answer_question("Actually Tokyo from 2027-04-01", state)
        # Should not overwrite existing
        assert "Paris" in state.destinations
        assert state.start_date == "2027-05-01"

    def test_increments_round_count(self):
        state = InterviewState()
        for _ in range(3):
            state = answer_question("Tokyo", state)
        assert state.round_count == 3


class TestFinalizeBrief:
    """Test TripBrief creation from interview state."""

    def test_creates_valid_brief_with_all_data(self):
        state = InterviewState(
            destinations=["Tokyo", "Kyoto"],
            start_date="2027-04-01",
            end_date="2027-04-10",
            interests=["culture", "food"],
            travel_style=TravelStyle.PACKED,
            budget="moderate",
            group_size=2,
        )
        brief = finalize_brief(state)
        assert isinstance(brief, TripBrief)
        assert len(brief.destinations) == 2
        assert brief.destinations[0].destination == "Tokyo"
        assert brief.destinations[1].destination == "Kyoto"
        assert brief.start_date == date(2027, 4, 1)
        assert brief.end_date == date(2027, 4, 10)
        assert brief.travel_style == TravelStyle.PACKED
        assert brief.budget == "moderate"
        assert brief.group_size == 2

    def test_applies_default_interests_when_empty(self):
        state = InterviewState(
            destinations=["Paris"],
            start_date="2027-06-01",
            end_date="2027-06-10",
            interests=[],
            travel_style=TravelStyle.CASUAL,
        )
        brief = finalize_brief(state)
        assert brief.interests == DEFAULT_INTERESTS

    def test_handles_missing_dates_with_placeholders(self):
        state = InterviewState(
            destinations=["Bali"],
            start_date=None,
            end_date=None,
            interests=["relaxation"],
            travel_style=TravelStyle.NOTHING,
        )
        brief = finalize_brief(state)
        assert isinstance(brief, TripBrief)
        assert brief.start_date > date.today()
        assert brief.end_date >= brief.start_date

    def test_handles_minimal_state(self):
        state = InterviewState()
        brief = finalize_brief(state)
        assert isinstance(brief, TripBrief)
        assert len(brief.destinations) == 1
        assert brief.destinations[0].destination == "TBD"
        assert brief.interests == DEFAULT_INTERESTS
        assert brief.travel_style == TravelStyle.CASUAL


class TestInterviewIntegration:
    """Test full interview flow."""

    def test_complete_interview_loop(self):
        # Round 1: User gives partial info
        state = parse_freeform("Planning a trip to Japan")
        assert "Japan" in state.destinations
        assert not state.is_complete()

        # Build question for missing fields
        missing = state.missing_required()
        assert "start_date" in missing
        assert "end_date" in missing

        question = build_question(missing, state)
        assert "dates" in question.lower()

        # User answers
        state = answer_question("April 1 to April 10, 2027", state)
        assert state.start_date == "2027-04-01"
        assert state.end_date == "2027-04-10"

        # Check if complete now
        if not state.is_complete():
            missing = state.missing_required()
            question = build_question(missing, state)
            state = answer_question("local culture and food, casual pace", state)

        # Finalize
        brief = finalize_brief(state)
        assert isinstance(brief, TripBrief)
        destination_names = [d.destination for d in brief.destinations]
        assert "Japan" in destination_names

    def test_forces_completion_after_max_rounds(self):
        state = InterviewState(max_rounds=2)
        state.round_count = 2

        # Even with missing fields, can't ask more
        assert state.can_ask_more() is False
        assert not state.is_complete()

        # Finalize should still work with defaults
        brief = finalize_brief(state)
        assert isinstance(brief, TripBrief)
