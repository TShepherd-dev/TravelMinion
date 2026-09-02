"""Domain models for TravelMinion.

All terms follow CONTEXT.md glossary:
- TripBrief: persisted capture of the clarifying interview
- Suggestion: a single researched attraction/activity candidate
- ApprovedActivityList: the human-owned, living list (sole input to planning)
- Itinerary: time-blocked day-by-day plan
- ActivityDay, TravelDay, FreeDay: itinerary day types
- TravelLeg: a single move between destinations (embedded in a day)
- TravelStyle: traveller's desired daily density
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import time as time_type
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# Default interests when user gives only a one-liner
DEFAULT_INTERESTS: list[str] = [
    "local culture",
    "food and dining",
    "landmarks",
    "nature",
    "history",
]


class TravelStyle(str, Enum):
    """Traveller's desired daily density.
    
    Maps to target number of daily time-blocks:
    - packed: ~5-6 blocks
    - casual: ~2-3 blocks  
    - nothing: ~0-1 blocks (Free Days)
    """

    PACKED = "packed"
    CASUAL = "casual"
    NOTHING = "nothing"


class TripBrief(BaseModel):
    """Persisted capture of the clarifying interview.
    
    Required: destinations, dates, interests, travel_style
    Optional: budget, group_size, mobility, dietary
    """

    # Required fields
    destinations: list[str] = Field(
        ..., min_length=1, description="List of destination cities/countries"
    )
    start_date: date_type = Field(..., description="Trip start date")
    end_date: date_type = Field(..., description="Trip end date")
    interests: list[str] = Field(
        ..., min_length=1, description="Traveller interests (defaults provided if empty)"
    )
    travel_style: TravelStyle = Field(..., description="Desired daily density")

    # Optional fields
    budget: str | None = Field(None, description="Budget level or amount")
    group_size: int | None = Field(None, ge=1, description="Number of travellers")
    mobility: str | None = Field(None, description="Mobility constraints")
    dietary: list[str] | None = Field(None, description="Dietary restrictions")

    # Metadata
    travellers_to_share: list[str] | None = Field(
        None, description="Email addresses for read-only calendar sharing"
    )

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: date_type, info: Any) -> date_type:
        """Validate end_date is not before start_date."""
        start = info.data.get("start_date")
        if start and v < start:
            raise ValueError("end_date must not be before start_date")
        return v


class Suggestion(BaseModel):
    """A single researched attraction/activity candidate.
    
    Produced by the Research step, fields per spec:
    name, rationale, area, duration, hours, cost, season_weather_fit,
    source_link, confidence, couldnt_verify note.
    """

    name: str = Field(..., min_length=1, description="Attraction/activity name")
    rationale: str = Field(..., description="Why this matches traveller's interests")
    area: str = Field(..., description="Neighbourhood or area within the destination")
    typical_duration: str = Field(..., description="How long to spend (e.g., '2-3 hours')")
    opening_hours: str | None = Field(None, description="Opening hours if applicable")
    approximate_cost: str | None = Field(None, description="Cost level or amount")
    season_weather_fit: str | None = Field(
        None, description="When this is best visited, weather considerations"
    )
    source_link: str | None = Field(None, description="URL where info was found")
    confidence: Literal["high", "medium", "low"] = Field(
        "medium", description="How solid this suggestion is"
    )
    couldnt_verify: str | None = Field(
        None, description="Note about what couldn't be verified"
    )

    # Which destination this suggestion is for
    destination: str = Field(..., description="The destination this suggestion belongs to")


class ApprovedActivity(BaseModel):
    """An activity in the Approved Activity List.
    
    May originate from a Suggestion (approved) or be added by the traveller.
    The 'approved' flag marks it as ready for planning.
    """

    name: str = Field(..., min_length=1)
    area: str = Field(...)
    typical_duration: str = Field(...)
    opening_hours: str | None = Field(None)
    notes: str | None = Field(None, description="Traveller's notes or rationale")
    destination: str = Field(...)
    approved: bool = Field(True, description="Whether this is approved for planning")

    # Optional indoor fallback for weather-exposed activities
    indoor_fallback: str | None = Field(
        None, description="Alternative if weather is bad"
    )


class ApprovedActivityList(BaseModel):
    """The human-owned, living list in the trip folder.
    
    Sole input to itinerary planning. May change over time,
    forcing itinerary re-generation (Rebuild).
    """

    activities: list[ApprovedActivity] = Field(default_factory=list)

    def approved_only(self) -> list[ApprovedActivity]:
        """Return only activities marked as approved."""
        return [a for a in self.activities if a.approved]

    def by_destination(self, destination: str) -> list[ApprovedActivity]:
        """Return approved activities for a specific destination."""
        return [a for a in self.approved_only() if a.destination == destination]


class TravelLeg(BaseModel):
    """A single move between two destinations.
    
    Embedded as a block inside a day, not a standalone day.
    """

    from_destination: str = Field(...)
    to_destination: str = Field(...)
    mode: str | None = Field(None, description="e.g., 'flight', 'train', 'bus'")
    duration: str | None = Field(None, description="Estimated travel time")


class TimeBlock(BaseModel):
    """A time-blocked activity within a day."""

    start_time: time_type = Field(...)
    end_time: time_type = Field(...)
    activity_name: str = Field(...)
    place: str = Field(...)
    duration: str = Field(...)
    transit_to_next: str | None = Field(
        None, description="How to get to the next activity"
    )
    indoor_fallback: str | None = Field(None)


class ItineraryDay(BaseModel):
    """Base class for itinerary days."""

    model_config = {"populate_by_name": True}

    day_date: date_type = Field(..., alias="date")
    destination: str = Field(...)


class ActivityDay(ItineraryDay):
    """An itinerary day with time-blocked activities."""

    day_type: Literal["activity"] = "activity"
    time_blocks: list[TimeBlock] = Field(default_factory=list)


class TravelDay(ItineraryDay):
    """An itinerary day devoted to moving between destinations.
    
    Has a travel leg plus optional lighter afternoon/evening activity.
    """

    day_type: Literal["travel"] = "travel"
    travel_leg: TravelLeg = Field(...)
    afternoon_activity: TimeBlock | None = Field(
        None, description="Optional lighter activity after travel"
    )


class FreeDay(ItineraryDay):
    """An itinerary day with no planned activities.
    
    The 'nothing' travel style, or recovery after long travel.
    """

    day_type: Literal["free"] = "free"
    notes: str | None = Field(None, description="Optional notes for the free day")


class Itinerary(BaseModel):
    """Time-blocked day-by-day plan built from the Approved Activity List.
    
    Organized as Activity Days, Travel Days, and Free Days.
    Maps 1:1 to calendar events when posted.
    """

    days: list[ActivityDay | TravelDay | FreeDay] = Field(default_factory=list)

    # Metadata for calendar posting
    calendar_id: str | None = Field(
        None, description="Per-trip Calendar ID once created"
    )
    last_posted: date_type | None = Field(
        None, description="When itinerary was last posted to calendar"
    )

    def get_day(self, d: date_type) -> ActivityDay | TravelDay | FreeDay | None:
        """Get the itinerary day for a specific date."""
        for day in self.days:
            if day.day_date == d:
                return day
        return None

    def date_range(self) -> tuple[date_type, date_type] | None:
        """Return the date range covered by this itinerary."""
        if not self.days:
            return None
        dates = [d.day_date for d in self.days]
        return min(dates), max(dates)
