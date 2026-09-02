"""Interview flow for Trip Brief capture.

Accepts freeform trip description, identifies missing required fields,
asks adaptive bounded follow-ups, and writes the Trip Brief file.

Required fields: destinations, dates, interests, travel_style
Optional fields: budget, group_size, mobility, dietary
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from travelminion.models import (
    DEFAULT_INTERESTS,
    TravelStyle,
    TripBrief,
)


@dataclass
class InterviewState:
    """Tracks interview progress and collected data.
    
    Attributes:
        destinations: List of destination cities/countries
        start_date: Trip start date (YYYY-MM-DD)
        end_date: Trip end date (YYYY-MM-DD)
        interests: List of interests
        travel_style: Packed, casual, or nothing
        budget: Optional budget info
        group_size: Optional number of travellers
        mobility: Optional mobility constraints
        dietary: Optional dietary restrictions
        travellers_to_share: Optional emails for calendar sharing
        round_count: How many question rounds we've done
        max_rounds: Maximum rounds before forcing completion
    """

    destinations: list[str] = field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    interests: list[str] = field(default_factory=list)
    travel_style: TravelStyle | None = None
    budget: str | None = None
    group_size: int | None = None
    mobility: str | None = None
    dietary: list[str] = field(default_factory=list)
    travellers_to_share: list[str] = field(default_factory=list)
    round_count: int = 0
    max_rounds: int = 3  # Cap at 3 rounds to avoid interrogation feeling

    def missing_required(self) -> list[str]:
        """Return list of missing required field names."""
        missing = []
        if not self.destinations:
            missing.append("destinations")
        if not self.start_date:
            missing.append("start_date")
        if not self.end_date:
            missing.append("end_date")
        if not self.interests:
            missing.append("interests")
        if not self.travel_style:
            missing.append("travel_style")
        return missing

    def is_complete(self) -> bool:
        """Check if all required fields are collected."""
        return len(self.missing_required()) == 0

    def can_ask_more(self) -> bool:
        """Check if we can ask another round of questions."""
        return self.round_count < self.max_rounds and not self.is_complete()


def _parse_date(text: str) -> str | None:
    """Extract a date from text in YYYY-MM-DD format.
    
    Handles common formats:
    - "2027-04-15" → "2027-04-15"
    - "April 15, 2027" → "2027-04-15"
    - "15th April 2027" → "2027-04-15"
    """
    # ISO format
    iso_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if iso_match:
        return iso_match.group(0)

    # Month name formats
    months = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12"
    }

    # "April 15, 2027" or "April 15 2027"
    month_pattern = (
        r"(january|february|march|april|may|june|july|august|"
        r"september|october|november|december)\s+(\d{1,2}),?\s*(\d{4})"
    )
    match = re.search(month_pattern, text.lower())
    if match:
        month = months[match.group(1)]
        day = match.group(2).zfill(2)
        year = match.group(3)
        return f"{year}-{month}-{day}"

    # "15th April 2027" or "15 April 2027"
    day_month_pattern = (
        r"(\d{1,2})(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|"
        r"july|august|september|october|november|december)\s+(\d{4})"
    )
    match = re.search(day_month_pattern, text.lower())
    if match:
        day = match.group(1).zfill(2)
        month = months[match.group(2)]
        year = match.group(3)
        return f"{year}-{month}-{day}"

    return None


def _parse_destinations(text: str) -> list[str]:
    """Extract destinations from text.
    
    Looks for patterns like:
    - "Tokyo, Kyoto, and Seoul"
    - "Japan (Tokyo and Osaka)"
    - "Paris and London"
    """
    destinations = []

    # Work with original case to find capitalized proper nouns
    original = text.strip()
    
    # Remove common prefixes (case-insensitive)
    cleaned = original
    for prefix in ["traveling to", "travelling to", "visiting", "trip to", "going to", 
                   "plan a trip to", "planning a trip to", "travel to"]:
        pattern = re.compile(rf"(?i){prefix}\s+")
        match = pattern.search(cleaned)
        if match:
            cleaned = cleaned[match.end():]
            break

    # Now extract capitalized words/sequences (potential destinations)
    # Skip common non-destination words
    skip_words = {"I", "A", "The", "An", "In", "At", "To", "From", "And", "Or", "But", 
                  "Just", "Want", "Wants", "Visit", "Visiting", "Travel", "Traveling",
                  "Relax", "Relaxing", "See", "Seeing", "Explore", "Exploring"}

    # Find sequences of capitalized words
    # Match: word boundaries with capital letter followed by lowercase
    candidates = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', cleaned)
    
    for candidate in candidates:
        # Skip common words
        if candidate in skip_words:
            continue
        # Skip if it's only 1-2 chars
        if len(candidate) < 3:
            continue
        # Skip duplicates
        if candidate not in destinations:
            destinations.append(candidate)

    return destinations[:5]  # Cap at 5 destinations


def _parse_interests(text: str) -> list[str]:
    """Extract interests from text.
    
    Looks for interest keywords or phrases.
    """
    common_interests = [
        "local culture", "food", "dining", "restaurants", "cuisine",
        "history", "historical sites", "museums", "art", "galleries",
        "nature", "hiking", "outdoors", "beaches", "mountains",
        "shopping", "nightlife", "bars", "clubs", "photography",
        "architecture", "landmarks", "temples", "shrines",
        "wildlife", "adventure", "sports", "relaxation"
    ]

    found = []
    text_lower = text.lower()

    for interest in common_interests:
        if interest in text_lower:
            found.append(interest)

    # Deduplicate and normalize
    normalized = []
    seen = set()
    for interest in found:
        # Map synonyms to canonical terms
        canonical = interest
        if interest in ["restaurants", "cuisine", "dining"]:
            canonical = "food"
        elif interest in ["historical sites", "museums"]:
            canonical = "history"
        elif interest in ["art", "galleries"]:
            canonical = "art"
        elif interest in ["hiking", "outdoors", "beaches", "mountains"]:
            canonical = "nature"

        if canonical not in seen:
            normalized.append(canonical)
            seen.add(canonical)

    return normalized[:8]  # Cap at 8 interests


def _parse_travel_style(text: str) -> TravelStyle | None:
    """Extract travel style from text.
    
    Maps keywords to packed/casual/nothing.
    """
    text_lower = text.lower()

    # Packed indicators
    packed_words = ["packed", "busy", "full", "maximize", "everything", 
                    "as much as possible", "intense", "action-packed"]
    for word in packed_words:
        if word in text_lower:
            return TravelStyle.PACKED

    # Nothing/rest indicators
    nothing_words = ["relax", "relaxation", "rest", "chill", "free", 
                     "nothing", "slow", "leisurely", "unwind"]
    for word in nothing_words:
        if word in text_lower:
            return TravelStyle.NOTHING

    # Casual indicators (default middle ground)
    casual_words = ["casual", "moderate", "balanced", "mix", "some"]
    for word in casual_words:
        if word in text_lower:
            return TravelStyle.CASUAL

    return None


def parse_freeform(text: str) -> InterviewState:
    """Parse a freeform trip description into an InterviewState.
    
    Args:
        text: User's freeform description of their trip
        
    Returns:
        InterviewState with extracted fields populated
    """
    state = InterviewState()

    # Try to extract dates - first look for date ranges
    # Handle "April 1 to April 10, 2027" where year only appears once
    months_pattern = (
        r"(?:january|february|march|april|may|june|july|august|"
        r"september|october|november|december)"
    )
    range_pattern = (
        rf"({months_pattern}\s+\d{{1,2}}(?:st|nd|rd|th)?)(?:,\s*\d{{4}})?"
        r"\s+(?:to|-)\s+("
        rf"{months_pattern}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s*\d{{4}}"
        r"|\d{{4}}-\d{{2}}-\d{{2}})"
    )
    range_match = re.search(range_pattern, text, re.IGNORECASE)
    
    if range_match:
        start_str = range_match.group(1).strip()
        end_str = range_match.group(2).strip()
        
        # Parse end date first (it has the year)
        end_date = _parse_date(end_str)
        
        # Parse start date - infer year from end date
        if end_date:
            start_with_year = f"{start_str}, {end_date[:4]}"
            start_date = _parse_date(start_with_year)
            if not start_date:
                start_with_year = f"{start_str} {end_date[:4]}"
                start_date = _parse_date(start_with_year)
        else:
            start_date = None
        
        state.start_date = start_date
        state.end_date = end_date
    else:
        # Try ISO date ranges: 2027-04-01 to 2027-04-10
        iso_range = re.search(r"(\d{4}-\d{2}-\d{2})\s+(?:to|-)\s+(\d{4}-\d{2}-\d{2})", text)
        if iso_range:
            state.start_date = iso_range.group(1)
            state.end_date = iso_range.group(2)
        else:
            # No range found, look for individual dates
            dates_found = []
            individual_date_pattern = (
                r"\d{4}-\d{2}-\d{2}|"
                rf"{months_pattern}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s*\d{{4}}|"
                r"\d{1,2}(?:st|nd|rd|th)?"
                rf"\s+{months_pattern}\s+\d{{4}}"
            )
            for match in re.finditer(individual_date_pattern, text, re.IGNORECASE):
                date_str = _parse_date(match.group(0))
                if date_str:
                    dates_found.append(date_str)

            if len(dates_found) >= 2:
                state.start_date = dates_found[0]
                state.end_date = dates_found[1]
            elif len(dates_found) == 1:
                state.start_date = dates_found[0]

    # Extract destinations
    state.destinations = _parse_destinations(text)

    # Extract interests
    state.interests = _parse_interests(text)

    # Extract travel style
    state.travel_style = _parse_travel_style(text)

    # Extract optional fields
    # Budget
    budget_match = re.search(
        r"budget[:\s]+(\$?\w+|low|moderate|high|luxury)",
        text,
        re.IGNORECASE
    )
    if budget_match:
        state.budget = budget_match.group(1)

    # Group size - multiple patterns
    group_pattern = (
        r"(?:group(?:\s*size)?|party|travellers?|people)[:\s]+(\d+)"
    )
    group_match = re.search(group_pattern, text, re.IGNORECASE)
    if not group_match:
        group_match = re.search(
            r"(\d+)\s*(?:travellers?|people|passengers)",
            text,
            re.IGNORECASE
        )
    if group_match:
        state.group_size = int(group_match.group(1))

    # Mobility
    mobility_pattern = (
        r"(?:mobility|accessibility|wheelchair|disabled)[:\s]+([^\n,]+)"
    )
    mobility_match = re.search(mobility_pattern, text, re.IGNORECASE)
    if mobility_match:
        state.mobility = mobility_match.group(1).strip()

    # Dietary
    dietary_pattern = (
        r"(?:dietary|diet|food restrictions|allergies)[:\s]+([^\n]+)"
    )
    dietary_match = re.search(dietary_pattern, text, re.IGNORECASE)
    if dietary_match:
        dietary_str = dietary_match.group(1)
        dietary_split = r"[,\s]+(?:and|&)?\s*"
        state.dietary = [
            d.strip()
            for d in re.split(dietary_split, dietary_str)
            if d.strip()
        ]

    return state


def build_question(missing: list[str], state: InterviewState) -> str:
    """Build a targeted question for missing required fields.
    
    Args:
        missing: List of missing field names
        state: Current interview state for context
        
    Returns:
        A natural language question string
    """
    questions = []

    if "destinations" in missing:
        questions.append(
            "Where do you want to travel? "
            "(e.g., 'Tokyo and Kyoto, Japan' or 'Paris, France')"
        )

    if "start_date" in missing and "end_date" in missing:
        questions.append(
            "What are your travel dates? Please provide both start and end "
            "dates (e.g., '2027-04-01 to 2027-04-10' or 'April 1-10, 2027')."
        )
    elif "start_date" in missing:
        questions.append(
            "When does your trip start? (e.g., '2027-04-01' or 'April 1, 2027')"
        )
    elif "end_date" in missing:
        questions.append(
            "When does your trip end? (e.g., '2027-04-10' or 'April 10, 2027')"
        )

    if "interests" in missing:
        questions.append(
            "What are you interested in experiencing? "
            "(e.g., 'local culture, food, history, nature' - or I can use defaults)"
        )

    if "travel_style" in missing:
        style_desc = (
            "How packed do you want your days? Choose: "
            "'packed' (5-6 activities/day), 'casual' (2-3/day), "
            "or 'nothing' (mostly rest/free days)"
        )
        questions.append(style_desc)

    # Combine into a single question block
    if len(questions) == 1:
        return questions[0]
    else:
        parts = [f"{i+1}. {q}" for i, q in enumerate(questions)]
        return "I need a few more details:\n\n" + "\n\n".join(parts)


def answer_question(answer: str, state: InterviewState) -> InterviewState:
    """Parse an answer and update the interview state.
    
    Args:
        answer: User's answer text
        state: Current interview state
        
    Returns:
        Updated InterviewState
    """
    # Re-run parsing on the answer
    extracted = parse_freeform(answer)

    # Merge extracted data into state - only if field is empty
    if extracted.destinations and not state.destinations:
        state.destinations = extracted.destinations
    if extracted.start_date and not state.start_date:
        state.start_date = extracted.start_date
    if extracted.end_date and not state.end_date:
        state.end_date = extracted.end_date
    if extracted.interests and not state.interests:
        state.interests = extracted.interests
    if extracted.travel_style and not state.travel_style:
        state.travel_style = extracted.travel_style
    if extracted.budget and not state.budget:
        state.budget = extracted.budget
    if extracted.group_size and not state.group_size:
        state.group_size = extracted.group_size
    if extracted.mobility and not state.mobility:
        state.mobility = extracted.mobility
    if extracted.dietary and not state.dietary:
        state.dietary = extracted.dietary

    state.round_count += 1
    return state


def _parse_date_object(text: str | None) -> date | None:
    """Parse a date string to a date object."""
    if not text:
        return None
    date_str = _parse_date(text)
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        return None


def finalize_brief(state: InterviewState) -> TripBrief:
    """Create a TripBrief from the interview state.
    
    Args:
        state: Completed (or forced-complete) interview state
        
    Returns:
        Validated TripBrief model
        
    Raises:
        ValueError: If required fields are still missing and cannot be defaulted
    """
    # Apply defaults for any still-missing fields
    destinations = state.destinations if state.destinations else ["TBD"]
    
    # Convert to DestinationStop format
    from travelminion.models import DestinationStop
    destination_stops = [
        DestinationStop(destination=d, days=1, order=i)
        for i, d in enumerate(destinations)
    ] if destinations and isinstance(destinations[0], str) else destinations
    
    # Parse dates from strings to date objects
    start_date: date | None = _parse_date_object(state.start_date)
    end_date: date | None = _parse_date_object(state.end_date)
    interests = state.interests if state.interests else DEFAULT_INTERESTS
    travel_style = state.travel_style if state.travel_style else TravelStyle.CASUAL

    # Handle missing dates - use placeholder dates 6 months out
    if not start_date:
        start_date = date.today() + timedelta(days=180)
    if not end_date:
        end_date = start_date + timedelta(days=7)

    return TripBrief(
        destinations=destination_stops,
        start_date=start_date,
        end_date=end_date,
        interests=interests,
        travel_style=travel_style,
        budget=state.budget,
        group_size=state.group_size,
        mobility=state.mobility,
        dietary=state.dietary if state.dietary else None,
        travellers_to_share=state.travellers_to_share if state.travellers_to_share else None,
    )
