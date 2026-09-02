"""Convenience wrapper for TravelMinion.

This module provides a single-command interface that runs the entire pipeline:
interview → research → approve → plan → post

While keeping all phases separately invokable on demand.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from travelminion.calendar import CalendarService, FakeCalendarService
from travelminion.files import TripFiles
from travelminion.interview import (
    InterviewState,
    build_question,
    finalize_brief,
    parse_freeform,
)
from travelminion.planner import ItineraryPlanner
from travelminion.research import ResearchEngine


@dataclass
class PipelineResult:
    """Result of running the full pipeline."""

    trip_brief_created: bool = False
    research_completed: bool = False
    activities_approved: int = 0
    itinerary_planned: bool = False
    calendar_posted: bool = False
    calendar_id: str | None = None
    events_posted: int = 0
    errors: list[str] | None = None

    def has_errors(self) -> bool:
        return bool(self.errors)

    def summary(self) -> str:
        """Human-readable summary of what was accomplished."""
        parts = []
        if self.trip_brief_created:
            parts.append("✓ Trip Brief created")
        if self.research_completed:
            parts.append("✓ Research completed")
        if self.activities_approved:
            parts.append(f"✓ {self.activities_approved} activities approved")
        if self.itinerary_planned:
            parts.append("✓ Itinerary planned")
        if self.calendar_posted:
            parts.append(f"✓ Calendar posted ({self.events_posted} events)")
        if self.has_errors():
            parts.append(f"✗ Errors: {', '.join(self.errors)}")
        return "\n".join(parts) if parts else "No actions taken"


class TravelMinionOrchestrator:
    """Orchestrates the full TravelMinion pipeline.
    
    Provides both end-to-end execution and individual phase control.
    """

    def __init__(
        self,
        trip_folder: Path | str,
        calendar_service: CalendarService | None = None,
        research_engine: ResearchEngine | None = None,
    ) -> None:
        """Initialize orchestrator.
        
        Args:
            trip_folder: Path to the Trip folder
            calendar_service: Inject calendar service (fake for tests, real for production)
            research_engine: Inject research engine (fake for tests, real for production)
        """
        self.trip_folder = Path(trip_folder)
        self.files = TripFiles(trip_folder)
        
        # Inject or default calendar service
        self.calendar_service = calendar_service or FakeCalendarService()
        
        # Inject or default research engine (no Tavily by default - tests use fake)
        self.research_engine = research_engine or ResearchEngine(tavily_api_key=None)
        
        self.state: InterviewState | None = None
        self.result = PipelineResult()

    # =========================================================================
    # Individual Phases
    # =========================================================================

    def phase1_interview(self, freeform_prompt: str) -> bool:
        """Phase 1: Interview → Trip Brief.
        
        Args:
            freeform_prompt: User's initial trip description
            
        Returns:
            True if Trip Brief was created successfully
        """
        # Initialize interview state
        self.state = InterviewState()
        
        # Parse freeform prompt - returns InterviewState with extracted fields
        parsed = parse_freeform(freeform_prompt)
        
        # Merge parsed fields into state
        for field_name in ["destinations", "start_date", "end_date", "interests", "travel_style",
                          "budget", "group_size", "mobility", "dietary", "travellers_to_share"]:
            value = getattr(parsed, field_name, None)
            if value:
                setattr(self.state, field_name, value)
        
        # Ask clarifying questions (max 3 rounds)
        rounds = 0
        max_rounds = 3
        while not self.state.is_complete() and rounds < max_rounds:
            missing = self.state.missing_required()
            if not missing:
                break
            
            # In the skill context, present question to user
            build_question(missing, self.state)
            rounds += 1
        
        # Finalize and write Trip Brief
        brief = finalize_brief(self.state)
        self.files.write_trip_brief(brief)
        
        self.result.trip_brief_created = True
        return True

    def phase2_research(self) -> bool:
        """Phase 2: Research → Suggestions.
        
        Returns:
            True if research completed successfully
        """
        brief = self.files.read_trip_brief()
        
        # Run research for each destination
        suggestions = self.research_engine.research_all(brief)
        
        # Write research output
        self.files.write_suggestions(suggestions)
        
        # Auto-approve all for the wrapper flow (user can edit after)
        from travelminion.models import ApprovedActivity
        
        activities = [
            ApprovedActivity(
                name=s.name,
                area=s.area,
                typical_duration=s.typical_duration,
                destination=s.destination,
                approved=True,
                opening_hours=s.opening_hours,
                notes=None,
                indoor_fallback=None,
            )
            for s in suggestions
        ]
        
        from travelminion.models import ApprovedActivityList
        
        activity_list = ApprovedActivityList(activities=activities)
        self.files.write_activities(activity_list)
        
        self.result.research_completed = True
        self.result.activities_approved = len(activities)
        return True

    def phase3_plan(self) -> bool:
        """Phase 3: Plan → Itinerary.
        
        Returns:
            True if itinerary was planned successfully
        """
        brief = self.files.read_trip_brief()
        activities = self.files.read_activities()
        
        planner = ItineraryPlanner(brief, activities)
        itinerary = planner.plan()
        self.files.write_itinerary(itinerary)
        
        self.result.itinerary_planned = True
        return True

    def phase4_post(self, confirm: bool = True) -> bool:
        """Phase 4: Post → Per-trip Calendar.
        
        Args:
            confirm: If False, skip posting (dry run)
            
        Returns:
            True if calendar was posted successfully
        """
        if not confirm:
            return False
        
        itinerary = self.files.read_itinerary()
        
        # Create calendar first
        calendar_id = self.calendar_service.create_calendar(
            f"Trip {itinerary.days[0].day_date if itinerary.days else 'Calendar'}"
        )
        
        # Post itinerary to the created calendar
        calendar_result = self.calendar_service.post_itinerary(
            itinerary, calendar_id, rebuild=False
        )
        
        self.result.calendar_posted = True
        self.result.calendar_id = calendar_result.calendar_id
        self.result.events_posted = calendar_result.events_posted
        return True

    def rebuild(self, confirm: bool = True) -> bool:
        """Rebuild: Regenerate affected calendar days.
        
        Args:
            confirm: If False, only calculate impact without applying
            
        Returns:
            True if rebuild was completed successfully
        """
        itinerary = self.files.read_itinerary()
        
        # Calculate impact
        impact = self.calendar_service.calculate_rebuild_impact(
            itinerary, "default-calendar"
        )
        
        if not confirm:
            # Just report impact
            return True
        
        # Confirm and rebuild
        calendar_result = self.calendar_service.confirm_and_rebuild(
            itinerary, "default-calendar", impact
        )
        
        self.result.calendar_posted = True
        self.result.events_posted = calendar_result.events_posted + calendar_result.events_updated
        return True

    # =========================================================================
    # End-to-End Pipeline
    # =========================================================================

    def run_full_pipeline(
        self,
        freeform_prompt: str,
        auto_confirm: bool = True,
    ) -> PipelineResult:
        """Run the entire pipeline from blank folder to posted calendar.
        
        Args:
            freeform_prompt: User's initial trip description
            auto_confirm: If True, proceed through all phases without pauses
            
        Returns:
            PipelineResult with summary of what was accomplished
        """
        self.result = PipelineResult()
        errors = []
        
        try:
            # Phase 1: Interview
            if not self.phase1_interview(freeform_prompt):
                errors.append("Failed to create Trip Brief")
                self.result.errors = errors
                return self.result
            
            # Phase 2: Research
            if not self.phase2_research():
                errors.append("Research failed")
                self.result.errors = errors
                return self.result
            
            # Phase 3: Plan
            if not self.phase3_plan():
                errors.append("Planning failed")
                self.result.errors = errors
                return self.result
            
            # Phase 4: Post
            if not self.phase4_post(confirm=auto_confirm):
                errors.append("Calendar posting failed or declined")
                self.result.errors = errors
                return self.result
                
        except Exception as e:
            errors.append(str(e))
        
        self.result.errors = errors if errors else None
        return self.result
