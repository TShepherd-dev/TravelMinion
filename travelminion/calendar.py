"""Calendar boundary for TravelMinion.

Thin abstraction over Google Calendar API with testable seam.
- CalendarService ABC defines the interface
- GoogleCalendarService: real OAuth + API implementation
- FakeCalendarService: in-memory for tests

Per spec:
- One-time Desktop-app OAuth writes token.json outside Trip folder
- Per-trip Calendar created via calendars.insert
- Shared read-only via acl.insert (role=reader)
- One event per activity time-block
- Rebuild updates events in place (no duplicates)
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import datetime
from typing import Literal

from travelminion.models import ActivityDay, Itinerary, TimeBlock, TravelDay


@dataclass
class CalendarEvent:
    """A calendar event representation.
    
    Maps 1:1 to a TimeBlock in the itinerary.
    """
    event_id: str | None = None
    summary: str = ""
    description: str = ""
    location: str = ""
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    day_date: str = ""
    activity_index: int = 0
    calendar_id: str = ""


@dataclass
class CalendarResult:
    """Result of calendar operations."""
    calendar_id: str
    summary: str
    events_posted: int = 0
    events_updated: int = 0
    events_deleted: int = 0
    shares_created: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class RebuildImpact:
    """Impact analysis before a rebuild.
    
    Shows what will change before confirming.
    """
    days_to_update: list[str]  # ISO date strings
    events_to_update: int
    events_to_add: int
    events_to_delete: int
    summary: str


class CalendarService(ABC):
    """Abstract calendar service interface.
    
    Test seam for calendar posting. Implementations:
    - GoogleCalendarService: real OAuth + API
    - FakeCalendarService: in-memory for tests
    """

    @abstractmethod
    def create_calendar(self, name: str, description: str = "") -> str:
        """Create a new calendar and return its ID.
        
        Args:
            name: Calendar name (e.g., "Japan & Korea 2027")
            description: Optional description
        
        Returns:
            Calendar ID string
        """
        pass

    @abstractmethod
    def share_calendar(
        self,
        calendar_id: str,
        email: str,
        role: Literal["reader", "writer"] = "reader",
    ) -> bool:
        """Share a calendar with a user.
        
        Args:
            calendar_id: Calendar to share
            email: User's email address
            role: "reader" (read-only) or "writer"
        
        Returns:
            True if share created successfully
        """
        pass

    @abstractmethod
    def create_event(self, calendar_id: str, event: CalendarEvent) -> str:
        """Create a calendar event.
        
        Args:
            calendar_id: Calendar to post to
            event: Event details
        
        Returns:
            Event ID string
        """
        pass

    @abstractmethod
    def update_event(self, calendar_id: str, event: CalendarEvent) -> bool:
        """Update an existing event.
        
        Args:
            calendar_id: Calendar containing the event
            event: Event with event_id set
        
        Returns:
            True if updated successfully
        """
        pass

    @abstractmethod
    def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """Delete a calendar event.
        
        Args:
            calendar_id: Calendar containing the event
            event_id: ID of event to delete
        
        Returns:
            True if deleted successfully
        """
        pass

    @abstractmethod
    def list_events(self, calendar_id: str, start_date: str, end_date: str) -> list[CalendarEvent]:
        """List events in a date range.
        
        Args:
            calendar_id: Calendar to query
            start_date: ISO format date string
            end_date: ISO format date string
        
        Returns:
            List of events in the range
        """
        pass

    @abstractmethod
    def post_itinerary(
        self, itinerary: Itinerary, calendar_id: str, rebuild: bool = False
    ) -> CalendarResult:
        """Post an entire itinerary to a calendar.
        
        Args:
            itinerary: Itinerary to post
            calendar_id: Calendar to post to
            rebuild: If True, update/replace existing events
        
        Returns:
            CalendarResult with counts
        """
        pass

    @abstractmethod
    def calculate_rebuild_impact(
        self, itinerary: Itinerary, calendar_id: str
    ) -> RebuildImpact:
        """Calculate what a rebuild will change.
        
        Args:
            itinerary: New itinerary to compare
            calendar_id: Calendar to check
        
        Returns:
            RebuildImpact showing days/events affected
        """
        pass

    @abstractmethod
    def confirm_and_rebuild(
        self, itinerary: Itinerary, calendar_id: str, impact: RebuildImpact
    ) -> CalendarResult:
        """Execute a rebuild after impact analysis.
        
        Args:
            itinerary: New itinerary to post
            calendar_id: Calendar to rebuild
            impact: Previously calculated impact (validation)
        
        Returns:
            CalendarResult with counts
        """
        pass


class FakeCalendarService(CalendarService):
    """In-memory fake for tests.
    
    Stores calendars and events in memory. No network calls.
    Useful for testing calendar logic without credentials.
    """

    def __init__(self) -> None:
        self.calendars: dict[str, str] = {}  # id -> name
        self.events: dict[str, dict[str, CalendarEvent]] = {}  # calendar_id -> event_id -> event
        self.shares: dict[str, list[tuple[str, str]]] = {}  # calendar_id -> [(email, role)]

    def create_calendar(self, name: str, description: str = "") -> str:
        calendar_id = f"cal_{len(self.calendars)}"
        self.calendars[calendar_id] = name
        self.events[calendar_id] = {}
        self.shares[calendar_id] = []
        return calendar_id

    def share_calendar(
        self, calendar_id: str, email: str, role: Literal["reader", "writer"] = "reader"
    ) -> bool:
        if calendar_id not in self.calendars:
            return False
        self.shares[calendar_id].append((email, role))
        return True

    def create_event(self, calendar_id: str, event: CalendarEvent) -> str:
        if calendar_id not in self.calendars:
            raise ValueError(f"Calendar {calendar_id} does not exist")
        
        event_id = f"evt_{calendar_id}_{len(self.events[calendar_id])}"
        event.event_id = event_id
        event.calendar_id = calendar_id
        self.events[calendar_id][event_id] = event
        return event_id

    def update_event(self, calendar_id: str, event: CalendarEvent) -> bool:
        if calendar_id not in self.calendars:
            return False
        if not event.event_id:
            return False
        if event.event_id not in self.events[calendar_id]:
            return False
        
        # Update in place
        self.events[calendar_id][event.event_id] = event
        return True

    def delete_event(self, calendar_id: str, event_id: str) -> bool:
        if calendar_id not in self.calendars:
            return False
        if event_id not in self.events[calendar_id]:
            return False
        
        del self.events[calendar_id][event_id]
        return True

    def list_events(self, calendar_id: str, start_date: str, end_date: str) -> list[CalendarEvent]:
        if calendar_id not in self.calendars:
            return []
        
        from datetime import date
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        
        result = []
        for event in self.events[calendar_id].values():
            if event.start_datetime:
                event_date = event.start_datetime.date()
                if start <= event_date <= end:
                    result.append(event)
        return result

    def post_itinerary(
        self, itinerary: Itinerary, calendar_id: str, rebuild: bool = False
    ) -> CalendarResult:
        if calendar_id not in self.calendars:
            return CalendarResult(
                calendar_id="",
                summary="Calendar does not exist",
                errors=[f"Calendar {calendar_id} does not exist"],
            )

        result = CalendarResult(
            calendar_id=calendar_id,
            summary=f"Posted {itinerary.date_range()} to {self.calendars[calendar_id]}",
        )

        for day in itinerary.days:
            if isinstance(day, ActivityDay):
                for i, block in enumerate(day.time_blocks):
                    event = _timeblock_to_event(block, day.day_date, i)
                    event.calendar_id = calendar_id
                    
                    if rebuild and day.day_date:
                        # Try to find existing event for this day/index
                        existing = self._find_existing_event(calendar_id, day.day_date, i)
                        if existing:
                            event.event_id = existing.event_id
                            if self.update_event(calendar_id, event):
                                result.events_updated += 1
                            else:
                                result.errors.append(f"Failed to update event {event.event_id}")
                        else:
                            self.create_event(calendar_id, event)
                            result.events_posted += 1
                    else:
                        self.create_event(calendar_id, event)
                        result.events_posted += 1

            elif isinstance(day, TravelDay) and day.afternoon_activity:
                event = _timeblock_to_event(day.afternoon_activity, day.day_date, 0)
                event.calendar_id = calendar_id
                travel_desc = f"{day.travel_leg.mode or 'Transit'}"
                event.summary = f"Travel: {travel_desc} + {day.afternoon_activity.activity_name}"
                
                if rebuild and day.day_date:
                    existing = self._find_existing_event(calendar_id, day.day_date, 0)
                    if existing:
                        event.event_id = existing.event_id
                        if self.update_event(calendar_id, event):
                            result.events_updated += 1
                        else:
                            result.errors.append("Failed to update travel event")
                    else:
                        self.create_event(calendar_id, event)
                        result.events_posted += 1
                else:
                    self.create_event(calendar_id, event)
                    result.events_posted += 1

        return result

    def calculate_rebuild_impact(
        self, itinerary: Itinerary, calendar_id: str
    ) -> RebuildImpact:
        """Calculate what will change in a rebuild."""
        if calendar_id not in self.calendars:
            return RebuildImpact(
                days_to_update=[],
                events_to_update=0,
                events_to_add=0,
                events_to_delete=0,
                summary="Calendar does not exist",
            )

        days_to_update = []
        events_to_update = 0
        events_to_add = 0

        for day in itinerary.days:
            if not day.day_date:
                continue

            day_str = day.day_date.isoformat()
            days_to_update.append(day_str)

            if isinstance(day, ActivityDay):
                for i in range(len(day.time_blocks)):
                    existing = self._find_existing_event(calendar_id, day.day_date, i)
                    if existing:
                        events_to_update += 1
                    else:
                        events_to_add += 1

            elif isinstance(day, TravelDay) and day.afternoon_activity:
                existing = self._find_existing_event(calendar_id, day.day_date, 0)
                if existing:
                    events_to_update += 1
                else:
                    events_to_add += 1

        summary = f"{events_to_update} updated, {events_to_add} added"
        summary += f" across {len(days_to_update)} days"
        return RebuildImpact(
            days_to_update=days_to_update,
            events_to_update=events_to_update,
            events_to_add=events_to_add,
            events_to_delete=0,
            summary=summary,
        )

    def confirm_and_rebuild(
        self, itinerary: Itinerary, calendar_id: str, impact: RebuildImpact
    ) -> CalendarResult:
        """Execute rebuild after impact analysis (validation step)."""
        # Just call post_itinerary with rebuild=True
        # The impact was already calculated and confirmed by user
        return self.post_itinerary(itinerary, calendar_id, rebuild=True)

    def _find_existing_event(
        self, calendar_id: str, day_date: date_type | None, index: int
    ) -> CalendarEvent | None:
        """Find existing event for a day/index (for rebuild)."""
        if not day_date or calendar_id not in self.events:
            return None
        
        for event in self.events[calendar_id].values():
            if not event.start_datetime:
                continue
            if event.start_datetime.date() != day_date:
                continue
            if event.activity_index != index:
                continue
            return event
        return None


class GoogleCalendarService(CalendarService):
    """Real Google Calendar API via OAuth.
    
    Uses google-api-python-client with Desktop-app OAuth flow.
    Token stored in ~/.travelminion/token.json (outside Trip folder).
    Non-expiring refresh token when OAuth consent screen is "In Production".
    """

    def __init__(self, token_dir: str | None = None) -> None:
        """Initialize with optional custom token directory.
        
        Args:
            token_dir: Directory for credentials/token.json (default: ~/.travelminion)
        """
        self._token_dir = token_dir or os.path.join(os.path.expanduser("~"), ".travelminion")
        self._credentials = None
        self._calendar_service = None

    def _ensure_credentials(self) -> None:
        """Ensure we have valid OAuth credentials."""
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        token_path = os.path.join(self._token_dir, "token.json")
        creds_path = os.path.join(self._token_dir, "credentials.json")

        # Load existing token or flow through OAuth
        if os.path.exists(token_path):
            self._credentials = Credentials.from_authorized_user_file(token_path, ["https://www.googleapis.com/auth/calendar"])
        
        if not self._credentials or not self._credentials.valid:
            if self._credentials and self._credentials.expired and self._credentials.refresh_token:
                self._credentials.refresh(Request())
                self._save_token(token_path)
            else:
                if not os.path.exists(creds_path):
                    msg = (
                        f"Credentials file not found at {creds_path}. "
                        "Set up OAuth credentials at "
                        "https://console.cloud.google.com/apis/credentials "
                        "(Desktop app type) and download as credentials.json"
                    )
                    raise FileNotFoundError(msg)
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    creds_path,
                    ["https://www.googleapis.com/auth/calendar"],
                )
                self._credentials = flow.run_local_server(port=0)
                self._save_token(token_path)

        # Build the service
        if not self._calendar_service:
            self._calendar_service = build("calendar", "v3", credentials=self._credentials)

    def _save_token(self, token_path: str) -> None:
        """Save token to disk."""
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, "w") as f:
            f.write(self._credentials.to_json())

    def create_calendar(self, name: str, description: str = "") -> str:
        """Create a new Google Calendar."""
        self._ensure_credentials()
        
        calendar = {
            "summary": name,
            "description": description,
        }
        
        created = self._calendar_service.calendars().insert(body=calendar).execute()
        return created["id"]

    def share_calendar(
        self, calendar_id: str, email: str, role: Literal["reader", "writer"] = "reader"
    ) -> bool:
        """Share a Google Calendar with a user."""
        self._ensure_credentials()
        
        acl_rule = {
            "scope": {
                "type": "user",
                "value": email,
            },
            "role": role,
        }
        
        try:
            self._calendar_service.acl().insert(calendarId=calendar_id, body=acl_rule).execute()
            # Insert into calendarList so it shows up for the user
            self._calendar_service.calendarList().insert(calendarId=calendar_id).execute()
            return True
        except Exception:
            return False

    def create_event(self, calendar_id: str, event: CalendarEvent) -> str:
        """Create a Google Calendar event."""
        self._ensure_credentials()
        
        body = {
            "summary": event.summary,
            "description": event.description,
            "location": event.location,
            "start": {
                "dateTime": event.start_datetime.isoformat() if event.start_datetime else None,
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": event.end_datetime.isoformat() if event.end_datetime else None,
                "timeZone": "UTC",
            },
        }
        
        created = self._calendar_service.events().insert(
            calendarId=calendar_id, body=body
        ).execute()
        return created["id"]

    def update_event(self, calendar_id: str, event: CalendarEvent) -> bool:
        """Update a Google Calendar event."""
        if not event.event_id:
            return False
        
        self._ensure_credentials()
        
        body = {
            "summary": event.summary,
            "description": event.description,
            "location": event.location,
            "start": {
                "dateTime": event.start_datetime.isoformat() if event.start_datetime else None,
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": event.end_datetime.isoformat() if event.end_datetime else None,
                "timeZone": "UTC",
            },
        }
        
        try:
            self._calendar_service.events().update(
                calendarId=calendar_id, eventId=event.event_id, body=body
            ).execute()
            return True
        except Exception:
            return False

    def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """Delete a Google Calendar event."""
        self._ensure_credentials()
        
        try:
            self._calendar_service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            return True
        except Exception:
            return False

    def list_events(self, calendar_id: str, start_date: str, end_date: str) -> list[CalendarEvent]:
        """List Google Calendar events in a date range."""
        self._ensure_credentials()
        
        result = []
        page_token = None
        
        while True:
            events = self._calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=f"{start_date}T00:00:00Z",
                timeMax=f"{end_date}T23:59:59Z",
                singleEvents=True,
                orderBy="startTime",
                pageToken=page_token
            ).execute()
            
            for item in events.get("items", []):
                start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
                end = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
                
                start_dt = None
                end_dt = None
                if start:
                    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                if end:
                    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                
                result.append(CalendarEvent(
                    event_id=item["id"],
                    summary=item.get("summary", ""),
                    description=item.get("description", ""),
                    location=item.get("location", ""),
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    calendar_id=calendar_id,
                ))
            
            page_token = events.get("nextPageToken")
            if not page_token:
                break
        
        return result

    def post_itinerary(
        self, itinerary: Itinerary, calendar_id: str, rebuild: bool = False
    ) -> CalendarResult:
        """Post an itinerary to Google Calendar."""
        self._ensure_credentials()
        
        result = CalendarResult(
            calendar_id=calendar_id,
            summary=f"Posted {itinerary.date_range()} to calendar",
        )

        for day in itinerary.days:
            if isinstance(day, ActivityDay):
                for i, block in enumerate(day.time_blocks):
                    event = _timeblock_to_event(block, day.day_date, i)
                    
                    if rebuild and day.day_date:
                        existing = self._find_existing_event(calendar_id, day.day_date, i)
                        if existing:
                            event.event_id = existing.event_id
                            if self.update_event(calendar_id, event):
                                result.events_updated += 1
                            else:
                                result.errors.append(f"Failed to update event {event.event_id}")
                        else:
                            self.create_event(calendar_id, event)
                            result.events_posted += 1
                    else:
                        self.create_event(calendar_id, event)
                        result.events_posted += 1

            elif isinstance(day, TravelDay) and day.afternoon_activity:
                event = _timeblock_to_event(day.afternoon_activity, day.day_date, 0)
                travel_desc = f"{day.travel_leg.mode or 'Transit'}"
                event.summary = f"Travel: {travel_desc} + {day.afternoon_activity.activity_name}"
                
                if rebuild and day.day_date:
                    existing = self._find_existing_event(calendar_id, day.day_date, 0)
                    if existing:
                        event.event_id = existing.event_id
                        if self.update_event(calendar_id, event):
                            result.events_updated += 1
                        else:
                            result.errors.append("Failed to update travel event")
                    else:
                        self.create_event(calendar_id, event)
                        result.events_posted += 1
                else:
                    self.create_event(calendar_id, event)
                    result.events_posted += 1

        return result

    def calculate_rebuild_impact(
        self, itinerary: Itinerary, calendar_id: str
    ) -> RebuildImpact:
        """Calculate what will change in a rebuild (Google Calendar version)."""
        self._ensure_credentials()
        
        days_to_update = []
        events_to_update = 0
        events_to_add = 0

        for day in itinerary.days:
            if not day.day_date:
                continue

            day_str = day.day_date.isoformat()
            days_to_update.append(day_str)

            if isinstance(day, ActivityDay):
                for i in range(len(day.time_blocks)):
                    existing = self._find_existing_event(calendar_id, day.day_date, i)
                    if existing:
                        events_to_update += 1
                    else:
                        events_to_add += 1

            elif isinstance(day, TravelDay) and day.afternoon_activity:
                existing = self._find_existing_event(calendar_id, day.day_date, 0)
                if existing:
                    events_to_update += 1
                else:
                    events_to_add += 1

        summary = f"{events_to_update} updated, {events_to_add} added"
        summary += f" across {len(days_to_update)} days"
        return RebuildImpact(
            days_to_update=days_to_update,
            events_to_update=events_to_update,
            events_to_add=events_to_add,
            events_to_delete=0,
            summary=summary,
        )

    def confirm_and_rebuild(
        self, itinerary: Itinerary, calendar_id: str, impact: RebuildImpact
    ) -> CalendarResult:
        """Execute rebuild after impact analysis."""
        return self.post_itinerary(itinerary, calendar_id, rebuild=True)


def _find_existing_event(
    calendar_service: CalendarService, calendar_id: str, day_date: date_type | None, index: int
) -> CalendarEvent | None:
    """Find existing event for rebuild (shared helper)."""
    if not day_date:
        return None
    
    # Search events on that date
    events = calendar_service.list_events(calendar_id, day_date.isoformat(), day_date.isoformat())
    
    # Find event at this index (assumes ordering by start time)
    sorted_events = sorted(events, key=lambda e: e.start_datetime or datetime.min)
    if index < len(sorted_events):
        return sorted_events[index]
    
    return None


def _timeblock_to_event(block: TimeBlock, day_date: date_type | None, index: int) -> CalendarEvent:
    """Convert a TimeBlock to a CalendarEvent.
    
    Combines date + time from the block.
    """
    from datetime import datetime, time
    
    # Parse times if strings
    start_time = block.start_time
    end_time = block.end_time
    
    if isinstance(start_time, str):
        start_time = time.fromisoformat(start_time)
    if isinstance(end_time, str):
        end_time = time.fromisoformat(end_time)
    
    # Combine date + time
    if day_date:
        start_dt = datetime.combine(day_date, start_time)
        end_dt = datetime.combine(day_date, end_time)
    else:
        start_dt = datetime.now()
        end_dt = datetime.now()
    
    # Build description from block details
    desc_parts = []
    if block.duration:
        desc_parts.append(f"Duration: {block.duration}")
    if block.transit_to_next:
        desc_parts.append(f"Next: {block.transit_to_next}")
    if block.indoor_fallback:
        desc_parts.append(f"Weather fallback: {block.indoor_fallback}")
    
    return CalendarEvent(
        summary=block.activity_name,
        description="\n".join(desc_parts),
        location=block.place,
        start_datetime=start_dt,
        end_datetime=end_dt,
        day_date=day_date.isoformat() if day_date else "",
        activity_index=index,
    )
