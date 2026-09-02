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

from pydantic import BaseModel, Field, field_validator, model_validator

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


class DestinationStop(BaseModel):
    """A destination with explicit days and order.
    
    Replaces simple list[str] to allow:
    - Explicit ordering (Japan -> Korea vs Korea -> Japan)
    - Days per destination for research scaling
    - Optional transit leg from previous destination
    """

    destination: str = Field(..., description="Destination name (city/country)")
    days: int = Field(..., ge=1, description="Number of days at this destination")
    order: int | None = Field(None, description="Explicit order (0-indexed, optional)")
    
    # Optional transit from the previous destination
    transit_from_previous: str | None = Field(
        None,
        description="Rough transit (e.g., 'flight 3h', 'train 2h15m')",
    )


class TripBrief(BaseModel):
    """Persisted capture of the clarifying interview.
    
    Required: destinations, dates, interests, travel_style
    Optional: budget, group_size, mobility, dietary
    """

    # Required fields
    destinations: list[DestinationStop] = Field(
        ..., min_length=1, description="List of destination stops with days"
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
    preferred_sources: list[str] = Field(
        default_factory=list,
        description="Preferred URLs to research (official sites, blogs, guides)",
    )

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

    @field_validator("destinations")
    @classmethod
    def validate_destinations(
        cls, v: list[DestinationStop] | list[str] | str
    ) -> list[DestinationStop]:
        """Handle backward compatibility: allow list[str] or single str.
        
        If old format (list[str]), convert to DestinationStop with even days.
        """
        if not v:
            raise ValueError("destinations must not be empty")

        # Handle single string (legacy edge case)
        if isinstance(v, str):
            return [DestinationStop(destination=v, days=1, order=0)]

        # Handle list of strings (legacy format)
        if isinstance(v, list):
            if len(v) == 0:
                raise ValueError("destinations must not be empty")
            
            # Check if it's list[str] (old format)
            if all(isinstance(x, str) for x in v):
                # Convert to DestinationStop with even split
                # Days will be calculated later from date range
                return [
                    DestinationStop(destination=str(dest), days=1, order=i)
                    for i, dest in enumerate(v)
                ]
            
            # It's already list[DestinationStop] - cast to satisfy mypy
            return [
                DestinationStop(
                    destination=d.destination,
                    days=d.days,
                    order=d.order,
                    transit_from_previous=d.transit_from_previous,
                )
                for d in v
            ]

        raise ValueError("destinations must be a list")

    @model_validator(mode="after")
    def calculate_days(self) -> TripBrief:
        """Calculate and distribute days if not explicitly set.
        
        If DestinationStop days don't sum to trip duration, redistribute evenly.
        """
        if not self.destinations:
            return self

        total_days = (self.end_date - self.start_date).days + 1
        if total_days < 1:
            return self

        current_sum = sum(d.days for d in self.destinations)
        
        # If days already sum correctly, keep explicit values
        if current_sum == total_days:
            return self

        # Redistribute evenly, giving remainder to first destinations
        base_days = total_days // len(self.destinations)
        remainder = total_days % len(self.destinations)
        
        for i, stop in enumerate(self.destinations):
            stop.days = base_days + (1 if i < remainder else 0)

        return self


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
    source_name: Literal["custom", "tavily", "jina", "ddgs"] = Field(
        default="tavily", description="Which source this came from"
    )
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
