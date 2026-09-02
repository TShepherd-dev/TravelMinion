"""Base itinerary planner for TravelMinion.

Takes an Approved Activity List and Trip Brief, produces a time-blocked
Itinerary respecting:
- Opening hours
- Geographic coherence (group by area)
- Rest and meals
- Travel style density (packed≈5-6, casual≈2-3, nothing≈0-1 blocks/day)
"""

from __future__ import annotations

from datetime import date, time, timedelta

from travelminion.models import (
    ActivityDay,
    ApprovedActivity,
    ApprovedActivityList,
    FreeDay,
    Itinerary,
    TimeBlock,
    TravelDay,
    TravelLeg,
    TravelStyle,
    TripBrief,
)

# Time constants (all in minutes)
MORNING_START = 9 * 60  # 9:00 AM
EVENING_END = 18 * 60  # 6:00 PM
LUNCH_START = 12 * 60  # 12:00 PM
LUNCH_END = 13 * 60  # 1:00 PM
DINNER_START = 17 * 60  # 5:00 PM
DEFAULT_ACTIVITY_DURATION = 120  # 2 hours
DEFAULT_TRANSIT = 30  # 30 minutes
MEAL_BREAK = 60  # 1 hour


def _parse_duration(duration_str: str) -> int:
    """Parse duration string to minutes.
    
    Examples:
    - "2-3 hours" → 150 (average)
    - "2 hours" → 120
    - "30 min" → 30
    - "half day" → 240
    """
    if not duration_str:
        return DEFAULT_ACTIVITY_DURATION
    
    duration_str = duration_str.lower().strip()
    
    # Handle "X-Y hours" format
    if "-" in duration_str and "hour" in duration_str:
        parts = duration_str.replace("hours", "").replace("hour", "").split("-")
        try:
            avg = (int(parts[0].strip()) + int(parts[1].strip())) / 2
            return int(avg * 60)
        except (ValueError, IndexError):
            return DEFAULT_ACTIVITY_DURATION
    
    # Handle "X hours" format
    if "hour" in duration_str:
        try:
            hours = float(duration_str.replace("hours", "").replace("hour", "").strip())
            return int(hours * 60)
        except ValueError:
            return DEFAULT_ACTIVITY_DURATION
    
    # Handle "X min" format
    if "min" in duration_str:
        try:
            return int(duration_str.replace("min", "").strip())
        except ValueError:
            return DEFAULT_ACTIVITY_DURATION
    
    # Handle "half day", "full day"
    if "half" in duration_str:
        return 240  # 4 hours
    if "full" in duration_str:
        return 480  # 8 hours
    
    return DEFAULT_ACTIVITY_DURATION


def _parse_opening_hours(hours_str: str | None) -> tuple[time, time] | None:
    """Parse opening hours to (open, close) times.
    
    Examples:
    - "9am-6pm" → (time(9,0), time(18,0))
    - "9:00-18:00" → (time(9,0), time(18,0))
    - "24 hours" → None (always open)
    """
    if not hours_str:
        return None
    
    hours_str = hours_str.lower().strip()
    
    # Handle "24 hours" or "always open"
    if "24" in hours_str or "always" in hours_str:
        return None
    
    # Try to parse "Xam-Ypm" or "X:00-Y:00"
    import re
    
    pattern = r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*-\s*"
    pattern += r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?"
    match = re.match(pattern, hours_str)
    if match:
        start_hour = int(match.group(1))
        start_min = int(match.group(2) or 0)
        start_ampm = match.group(3)
        end_hour = int(match.group(4))
        end_min = int(match.group(5) or 0)
        end_ampm = match.group(6)
        
        # Convert to 24-hour format
        if start_ampm == "pm" and start_hour != 12:
            start_hour += 12
        if end_ampm == "pm" and end_hour != 12:
            end_hour += 12
        
        return (time(start_hour, start_min), time(end_hour, end_min))
    
    return None


def _minutes_to_time(minutes: int) -> time:
    """Convert minutes since midnight to time object."""
    hours = minutes // 60
    mins = minutes % 60
    return time(hours, mins)


def _get_target_density(travel_style: TravelStyle) -> int:
    """Get target number of activity blocks per day."""
    if travel_style == TravelStyle.PACKED:
        return 5  # Aim for 5-6
    elif travel_style == TravelStyle.CASUAL:
        return 2  # Aim for 2-3
    else:  # NOTHING
        return 0  # Free days only


def _group_by_area(activities: list[ApprovedActivity]) -> dict[str, list[ApprovedActivity]]:
    """Group activities by area/neighbourhood for geographic coherence."""
    groups: dict[str, list[ApprovedActivity]] = {}
    for activity in activities:
        area = activity.area.strip().lower()
        if area not in groups:
            groups[area] = []
        groups[area].append(activity)
    return groups


def _schedule_activity(
    start_minutes: int,
    activity: ApprovedActivity,
    transit_minutes: int = DEFAULT_TRANSIT,
) -> TimeBlock | None:
    """Schedule a single activity starting at the given time.
    
    Returns TimeBlock or None if activity can't fit (e.g., outside opening hours).
    """
    duration = _parse_duration(activity.typical_duration)
    end_minutes = start_minutes + duration
    
    # Check opening hours if available
    if activity.opening_hours:
        hours = _parse_opening_hours(activity.opening_hours)
        if hours:
            open_time, close_time = hours
            open_minutes = open_time.hour * 60 + open_time.minute
            close_minutes = close_time.hour * 60 + close_time.minute
            
            # Activity should fit within opening hours
            if start_minutes < open_minutes or end_minutes > close_minutes:
                # Try to adjust start time to opening
                if end_minutes <= close_minutes:
                    start_minutes = open_minutes
                    end_minutes = start_minutes + duration
                else:
                    # Doesn't fit at all
                    return None
    
    # Check if we're past dinner time - wrap up for the day
    if start_minutes >= DINNER_START:
        return None
    
    # Check if activity would extend too late
    if end_minutes > EVENING_END:
        end_minutes = min(end_minutes, EVENING_END)
    
    return TimeBlock(
        start_time=_minutes_to_time(start_minutes),
        end_time=_minutes_to_time(end_minutes),
        activity_name=activity.name,
        place=activity.area,
        duration=activity.typical_duration,
        transit_to_next=f"{transit_minutes} min",
        indoor_fallback=activity.indoor_fallback,
    )


class ItineraryPlanner:
    """Plans an Itinerary from a Trip Brief and Approved Activity List."""
    
    def __init__(self, trip_brief: TripBrief, activities: ApprovedActivityList):
        self.trip_brief = trip_brief
        self.activities = activities
        self.target_density = _get_target_density(trip_brief.travel_style)
    
    def plan(self) -> Itinerary:
        """Generate the full itinerary.
        
        Returns:
            Itinerary with ordered days (Activity Days, Travel Days, Free Days)
        """
        days = []
        current_date = self.trip_brief.start_date
        
        # Process each destination in order
        sorted_destinations = sorted(
            self.trip_brief.destinations,
            key=lambda d: d.order if d.order is not None else float("inf"),
        )
        
        for dest_idx, dest_stop in enumerate(sorted_destinations):
            dest_name = dest_stop.destination
            dest_days = dest_stop.days
            
            # Get approved activities for this destination
            dest_activities = self.activities.by_destination(dest_name)
            
            if not dest_activities:
                # No activities - create free days
                for _ in range(dest_days):
                    days.append(
                        FreeDay(
                            date=current_date,
                            destination=dest_name,
                            notes="No planned activities",
                        )
                    )
                    current_date += timedelta(days=1)
                continue
            
            # Handle travel day if this isn't the first destination
            if dest_idx > 0:
                prev_dest = sorted_destinations[dest_idx - 1].destination
                travel_leg = TravelLeg(
                    from_destination=prev_dest,
                    to_destination=dest_name,
                    mode=None,  # User can fill in
                    duration=None,  # User can fill in
                )
                travel_day = TravelDay(
                    date=current_date,
                    destination=dest_name,
                    day_type="travel",
                    travel_leg=travel_leg,
                    afternoon_activity=None,  # Can be filled in later
                )
                days.append(travel_day)
                current_date += timedelta(days=1)
            
            # Plan activity days for this destination
            activity_days = self._plan_destination_days(
                dest_activities, dest_days, current_date, dest_name
            )
            days.extend(activity_days)
            current_date += timedelta(days=len(activity_days))
        
        return Itinerary(days=days)
    
    def _plan_destination_days(
        self,
        activities: list[ApprovedActivity],
        num_days: int,
        start_date: date,
        destination: str,
    ) -> list[ActivityDay]:
        """Plan activity days for a single destination.
        
        Groups activities by area for geographic coherence,
        distributes across days based on travel style density.
        """
        if not activities or num_days <= 0:
            return []
        
        # Group activities by area
        area_groups = _group_by_area(activities)
        
        # Flatten into a list of activities, grouped by area
        # Activities in same area stay together
        ordered_activities = []
        for _area, area_activities in area_groups.items():
            ordered_activities.extend(area_activities)
        
        # Distribute activities across days based on target density
        days = []
        activity_idx = 0
        
        for day_num in range(num_days):
            current_date = start_date + timedelta(days=day_num)
            
            # For "nothing" style, create free days
            if self.target_density == 0:
                days.append(
                    FreeDay(
                        date=current_date,
                        destination=destination,
                        notes="Rest day",
                    )
                )
                continue
            
            # Schedule activities for this day
            time_blocks = []
            current_time = MORNING_START
            
            # How many activities should we aim for today?
            remaining_days = num_days - day_num
            remaining_activities = len(ordered_activities) - activity_idx
            
            # Adjust target based on what's left
            if remaining_days > 0:
                target_today = max(1, remaining_activities // remaining_days)
                target_today = min(target_today, self.target_density + 1)
            else:
                target_today = self.target_density
            
            activities_scheduled = 0
            
            while activity_idx < len(ordered_activities) and activities_scheduled < target_today:
                activity = ordered_activities[activity_idx]
                
                # Add lunch break if we're at lunch time
                if current_time >= LUNCH_START and current_time < LUNCH_END:
                    current_time = LUNCH_END
                
                # Schedule the activity
                time_block = _schedule_activity(current_time, activity)
                
                if time_block:
                    time_blocks.append(time_block)
                    # Update current time: end of activity + transit
                    end_minutes = time_block.end_time.hour * 60 + time_block.end_time.minute
                    current_time = end_minutes + DEFAULT_TRANSIT
                    activity_idx += 1
                    activities_scheduled += 1
                else:
                    # Activity couldn't be scheduled, skip to next
                    activity_idx += 1
            
            # If we have activities, create an ActivityDay
            if time_blocks:
                days.append(
                    ActivityDay(
                        date=current_date,
                        destination=destination,
                        day_type="activity",
                        time_blocks=time_blocks,
                    )
                )
            else:
                # No activities scheduled - free day
                days.append(
                    FreeDay(
                        date=current_date,
                        destination=destination,
                        notes="No activities scheduled",
                    )
                )
        
        return days


def plan_itinerary(trip_brief: TripBrief, activities: ApprovedActivityList) -> Itinerary:
    """Convenience function to plan an itinerary.
    
    Args:
        trip_brief: The trip brief with dates, destinations, travel style
        activities: The approved activity list
        
    Returns:
        Generated Itinerary
    """
    planner = ItineraryPlanner(trip_brief, activities)
    return planner.plan()
