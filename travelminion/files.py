"""File-interface primitives for TravelMinion.

This module provides the Trip-folder file interface - the primary test seam.
All trip state is plain Markdown files with YAML frontmatter/content.

Files:
- trip-brief.md: TripBrief
- activities.md: ApprovedActivityList  
- itinerary.md: Itinerary
- research-output.md: list of Suggestions (read-only output)
"""

from __future__ import annotations

import re
from datetime import date, time
from pathlib import Path
from typing import Any, TypeVar

import frontmatter
from pydantic import ValidationError as PydanticValidationError

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
from travelminion.templates import TEMPLATES

T = TypeVar("T")


class FileError(Exception):
    """Base exception for file operations."""

    pass


class ParseError(FileError):
    """Failed to parse file content."""

    pass


class ValidationError(FileError):
    """File content failed validation."""

    pass


def _parse_date(value: Any) -> date | None:
    """Parse a date from various formats."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _parse_time(value: Any) -> time | None:
    """Parse a time from various formats."""
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        value = value.strip().strip('"').strip("'")
        if not value:
            return None
        # Handle HH:MM format
        match = re.match(r"^(\d{1,2}):(\d{2})(?::\d{2})?$", value)
        if match:
            return time(int(match.group(1)), int(match.group(2)))
        return None
    return None


def _serialize_date(d: date | None) -> str | None:
    """Serialize date to ISO format string."""
    return d.isoformat() if d else None


def _serialize_time(t: time | None) -> str | None:
    """Serialize time to HH:MM format string."""
    return t.strftime("%H:%M") if t else None


class TripFiles:
    """File-interface for a Trip folder.
    
    Provides read/write operations for all trip files with:
    - Typed structures via Pydantic models
    - Graceful handling of malformed/missing files
    - Validation of field values
    - Lossless round-tripping where possible
    """

    # Canonical file names per CONTEXT.md vocabulary
    TRIP_BRIEF = "trip-brief.md"
    ACTIVITIES = "activities.md"
    ITINERARY = "itinerary.md"
    RESEARCH_OUTPUT = "research-output.md"

    def __init__(self, trip_folder: Path | str) -> None:
        """Initialize with path to Trip folder."""
        self.folder = Path(trip_folder)

    def exists(self) -> bool:
        """Check if the Trip folder exists."""
        return self.folder.exists() and self.folder.is_dir()

    def ensure_folder(self) -> None:
        """Create the Trip folder if it doesn't exist."""
        self.folder.mkdir(parents=True, exist_ok=True)

    def seed_templates(self) -> list[str]:
        """Lay down seed templates for all trip files.
        
        Only creates files that don't already exist.
        Returns list of created file names.
        """
        self.ensure_folder()
        created = []
        for filename, content in TEMPLATES.items():
            filepath = self.folder / filename
            if not filepath.exists():
                filepath.write_text(content, encoding="utf-8")
                created.append(filename)
        return created

    def _read_file(self, filename: str) -> tuple[dict[str, Any], str]:
        """Read a markdown file with YAML content.
        
        Returns (parsed_data, raw_content).
        Raises ParseError if file is malformed.
        Raises FileError if file doesn't exist.
        """
        filepath = self.folder / filename
        if not filepath.exists():
            raise FileError(f"File not found: {filename}")

        try:
            raw = filepath.read_text(encoding="utf-8")
        except OSError as e:
            raise FileError(f"Cannot read {filename}: {e}") from e

        try:
            post = frontmatter.loads(raw)
            # Merge frontmatter metadata with content parsed as YAML
            # For our files, the main data is in the content as YAML-like structure
            data = dict(post.metadata)
            
            # Parse the content body for YAML-style data
            content_data = self._parse_yaml_content(post.content)
            data.update(content_data)
            
            return data, raw
        except Exception as e:
            raise ParseError(f"Cannot parse {filename}: {e}") from e

    def _parse_yaml_content(self, content: str) -> dict[str, Any]:
        """Parse YAML-like content from markdown body.
        
        Handles our template format where data is in the body.
        """
        import yaml

        # Find YAML-like blocks (lines starting with field names)
        # Skip comment lines
        lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(line)

        if not lines:
            return {}

        yaml_text = "\n".join(lines)
        try:
            parsed = yaml.safe_load(yaml_text)
            return parsed if isinstance(parsed, dict) else {}
        except yaml.YAMLError:
            return {}

    def _write_file(self, filename: str, data: dict[str, Any]) -> None:
        """Write data to a markdown file with YAML content."""
        import yaml

        self.ensure_folder()
        filepath = self.folder / filename

        # Get the template header comments
        template = TEMPLATES.get(filename, "")
        header_lines = []
        for line in template.split("\n"):
            if line.startswith("---") or line.startswith("#"):
                header_lines.append(line)
            elif line.strip() and not line.startswith("#"):
                break
        header = "\n".join(header_lines[:5]) + "\n\n"  # Keep first few header lines

        # Serialize data to YAML
        yaml_content = yaml.dump(
            data, default_flow_style=False, allow_unicode=True, sort_keys=False
        )

        filepath.write_text(header + yaml_content, encoding="utf-8")

    # =========================================================================
    # Trip Brief
    # =========================================================================

    def read_trip_brief(self) -> TripBrief:
        """Read and validate trip-brief.md.
        
        Raises:
            FileError: If file doesn't exist
            ParseError: If file is malformed
            ValidationError: If content fails validation
        """
        data, _ = self._read_file(self.TRIP_BRIEF)

        # Parse dates
        data["start_date"] = _parse_date(data.get("start_date"))
        data["end_date"] = _parse_date(data.get("end_date"))

        # Handle travel_style enum
        style = data.get("travel_style", "casual")
        if isinstance(style, str):
            try:
                data["travel_style"] = TravelStyle(style.lower())
            except ValueError:
                data["travel_style"] = TravelStyle.CASUAL

        # Apply default interests if empty
        interests = data.get("interests", [])
        if not interests or interests == [None] or interests == [""]:
            data["interests"] = DEFAULT_INTERESTS

        # Clean up empty list items
        for field in ["destinations", "interests", "dietary", "travellers_to_share"]:
            if field in data and isinstance(data[field], list):
                data[field] = [x for x in data[field] if x]

        try:
            return TripBrief(**data)
        except PydanticValidationError as e:
            raise ValidationError(f"Invalid trip brief: {e}") from e

    def write_trip_brief(self, brief: TripBrief) -> None:
        """Write trip-brief.md from a TripBrief model."""
        data = brief.model_dump(exclude_none=True)
        data["start_date"] = _serialize_date(brief.start_date)
        data["end_date"] = _serialize_date(brief.end_date)
        data["travel_style"] = brief.travel_style.value
        self._write_file(self.TRIP_BRIEF, data)

    def trip_brief_exists(self) -> bool:
        """Check if trip-brief.md exists."""
        return (self.folder / self.TRIP_BRIEF).exists()

    # =========================================================================
    # Approved Activity List
    # =========================================================================

    def read_activities(self) -> ApprovedActivityList:
        """Read and validate activities.md.
        
        Raises:
            FileError: If file doesn't exist
            ParseError: If file is malformed
            ValidationError: If content fails validation
        """
        data, _ = self._read_file(self.ACTIVITIES)

        activities_data = data.get("activities", [])
        if not activities_data:
            return ApprovedActivityList(activities=[])

        activities = []
        for item in activities_data:
            if not isinstance(item, dict):
                continue
            try:
                activities.append(ApprovedActivity(**item))
            except PydanticValidationError:
                # Log but continue - graceful handling
                continue

        return ApprovedActivityList(activities=activities)

    def write_activities(self, activity_list: ApprovedActivityList) -> None:
        """Write activities.md from an ApprovedActivityList model."""
        data = {
            "activities": [
                a.model_dump(exclude_none=True) for a in activity_list.activities
            ]
        }
        self._write_file(self.ACTIVITIES, data)

    def activities_exists(self) -> bool:
        """Check if activities.md exists."""
        return (self.folder / self.ACTIVITIES).exists()

    # =========================================================================
    # Itinerary
    # =========================================================================

    def read_itinerary(self) -> Itinerary:
        """Read and validate itinerary.md.
        
        Raises:
            FileError: If file doesn't exist
            ParseError: If file is malformed
            ValidationError: If content fails validation
        """
        data, _ = self._read_file(self.ITINERARY)

        days_data = data.get("days", [])
        if not days_data:
            return Itinerary(
                days=[],
                calendar_id=data.get("calendar_id"),
                last_posted=_parse_date(data.get("last_posted")),
            )

        days: list[ActivityDay | TravelDay | FreeDay] = []
        for item in days_data:
            if not isinstance(item, dict):
                continue

            day_type = item.get("day_type", "activity")
            item["date"] = _parse_date(item.get("date"))

            try:
                if day_type == "travel":
                    # Parse travel leg
                    leg_data = item.get("travel_leg", {})
                    item["travel_leg"] = TravelLeg(**leg_data)
                    # Parse optional afternoon activity
                    if item.get("afternoon_activity"):
                        aa = item["afternoon_activity"]
                        aa["start_time"] = _parse_time(aa.get("start_time"))
                        aa["end_time"] = _parse_time(aa.get("end_time"))
                        item["afternoon_activity"] = TimeBlock(**aa)
                    days.append(TravelDay(**item))

                elif day_type == "free":
                    days.append(FreeDay(**item))

                else:  # activity
                    # Parse time blocks
                    blocks = []
                    for block in item.get("time_blocks", []):
                        block["start_time"] = _parse_time(block.get("start_time"))
                        block["end_time"] = _parse_time(block.get("end_time"))
                        blocks.append(TimeBlock(**block))
                    item["time_blocks"] = blocks
                    days.append(ActivityDay(**item))

            except PydanticValidationError:
                # Skip malformed days gracefully
                continue

        return Itinerary(
            days=days,
            calendar_id=data.get("calendar_id"),
            last_posted=_parse_date(data.get("last_posted")),
        )

    def write_itinerary(self, itinerary: Itinerary) -> None:
        """Write itinerary.md from an Itinerary model."""
        days_data = []
        for day in itinerary.days:
            day_dict = day.model_dump(exclude_none=True)
            day_dict["date"] = _serialize_date(day.day_date)

            if isinstance(day, ActivityDay):
                for block in day_dict.get("time_blocks", []):
                    block["start_time"] = _serialize_time(
                        time.fromisoformat(block["start_time"])
                        if isinstance(block["start_time"], str)
                        else block["start_time"]
                    )
                    block["end_time"] = _serialize_time(
                        time.fromisoformat(block["end_time"])
                        if isinstance(block["end_time"], str)
                        else block["end_time"]
                    )
            elif isinstance(day, TravelDay) and day_dict.get("afternoon_activity"):
                aa = day_dict["afternoon_activity"]
                aa["start_time"] = _serialize_time(
                    time.fromisoformat(aa["start_time"])
                    if isinstance(aa["start_time"], str)
                    else aa["start_time"]
                )
                aa["end_time"] = _serialize_time(
                    time.fromisoformat(aa["end_time"])
                    if isinstance(aa["end_time"], str)
                    else aa["end_time"]
                )

            days_data.append(day_dict)

        data = {
            "days": days_data,
            "calendar_id": itinerary.calendar_id,
            "last_posted": _serialize_date(itinerary.last_posted),
        }
        self._write_file(self.ITINERARY, data)

    def itinerary_exists(self) -> bool:
        """Check if itinerary.md exists."""
        return (self.folder / self.ITINERARY).exists()

    # =========================================================================
    # Research Output (read-only, written by research step)
    # =========================================================================

    def read_suggestions(self) -> list[Suggestion]:
        """Read research-output.md and return list of Suggestions.
        
        Raises:
            FileError: If file doesn't exist
            ParseError: If file is malformed
        """
        data, _ = self._read_file(self.RESEARCH_OUTPUT)

        suggestions_data = data.get("suggestions", [])
        if not suggestions_data:
            return []

        suggestions = []
        for item in suggestions_data:
            if not isinstance(item, dict):
                continue
            try:
                suggestions.append(Suggestion(**item))
            except PydanticValidationError:
                # Skip malformed suggestions gracefully
                continue

        return suggestions

    def write_suggestions(self, suggestions: list[Suggestion]) -> None:
        """Write research-output.md from a list of Suggestions."""
        data = {"suggestions": [s.model_dump(exclude_none=True) for s in suggestions]}
        self._write_file(self.RESEARCH_OUTPUT, data)

    def research_output_exists(self) -> bool:
        """Check if research-output.md exists."""
        return (self.folder / self.RESEARCH_OUTPUT).exists()

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def all_files_exist(self) -> dict[str, bool]:
        """Check existence of all trip files."""
        return {
            self.TRIP_BRIEF: self.trip_brief_exists(),
            self.ACTIVITIES: self.activities_exists(),
            self.ITINERARY: self.itinerary_exists(),
            self.RESEARCH_OUTPUT: self.research_output_exists(),
        }

    def is_blank(self) -> bool:
        """Check if this is a blank Trip folder (no trip files yet)."""
        return not any(self.all_files_exist().values())

    def validate_all(self) -> dict[str, str | None]:
        """Validate all existing files, returning errors per file.
        
        Returns dict of filename -> error message (None if valid).
        """
        results: dict[str, str | None] = {}

        for filename, check_fn, read_fn in [
            (self.TRIP_BRIEF, self.trip_brief_exists, self.read_trip_brief),
            (self.ACTIVITIES, self.activities_exists, self.read_activities),
            (self.ITINERARY, self.itinerary_exists, self.read_itinerary),
            (self.RESEARCH_OUTPUT, self.research_output_exists, self.read_suggestions),
        ]:
            if not check_fn():
                results[filename] = None  # File doesn't exist, no error
                continue
            try:
                read_fn()
                results[filename] = None  # Valid
            except (FileError, ParseError, ValidationError) as e:
                results[filename] = str(e)

        return results
