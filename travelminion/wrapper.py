"""Convenience wrapper for TravelMinion.

This module provides a single-command interface that runs the entire pipeline:
interview → research → approve → plan → post

While keeping all phases separately invokable on demand.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from travelminion.files import TripFiles
from travelminion.interview import (
    InterviewState,
    build_question,
    finalize_brief,
    parse_freeform,
)
from travelminion.planner import ItineraryPlanner
from travelminion.research import ResearchEngine


def load_config() -> dict:
    """Load configuration from travelminion.config.json.
    
    Looks in:
    1. Same directory as this file (installed package)
    2. Repository root (development)
    
    Returns empty dict if file doesn't exist.
    """
    config_paths = [
        Path(__file__).parent.parent / "travelminion.config.json",
        Path(__file__).parent / "travelminion.config.json",
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
    
    return {}


def get_google_credentials() -> tuple[str | None, str | None]:
    """Get Google OAuth credentials from config or env vars.
    
    Returns:
        (client_id, client_secret) tuple, both None if not configured
    """
    config = load_config()
    
    # Try config file first
    google_config = config.get("google", {})
    client_id = google_config.get("client_id", "")
    client_secret = google_config.get("client_secret", "")
    
    if client_id and client_secret:
        return client_id, client_secret
    
    # Fallback to environment variables
    env_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    env_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    
    if env_id and env_secret:
        return env_id, env_secret
    
    return None, None


@dataclass
class PipelineResult:
    """Result of running the full pipeline."""

    trip_brief_created: bool = False
    research_completed: bool = False
    activities_approved: int = 0
    itinerary_planned: bool = False
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
        if self.has_errors():
            parts.append(f"✗ Errors: {', '.join(self.errors)}")
        return "\n".join(parts) if parts else "No actions taken"


class TravelMinionOrchestrator:
    """Orchestrates the full TravelMinion pipeline.
    
    Provides both end-to-end execution and individual phase control.
    """

    def __init__(
        self,
        trip_folder: Path | str | None = None,
        research_engine: ResearchEngine | None = None,
    ) -> None:
        """Initialize orchestrator.
        
        Args:
            trip_folder: Path to the Trip folder (defaults to current working directory)
            research_engine: Inject research engine (fake for tests, real for production)
        """
        self.trip_folder = Path(trip_folder) if trip_folder else Path.cwd()
        self.files = TripFiles(self.trip_folder)
        
        # Load config and initialize research engine with Tavily API key
        config = load_config()
        if research_engine is not None:
            self.research_engine = research_engine
        else:
            # Try config file first, then environment variable
            tavily_key = config.get("tavily_api_key", "") or os.environ.get("TAVILY_API_KEY")
            self.research_engine = ResearchEngine(tavily_api_key=tavily_key)
        
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
        import sys
        
        # Check for existing Trip Brief
        if self.files.trip_brief_exists():
            brief = self.files.read_trip_brief()
            
            # Only show interactive prompt if stdin is a TTY (not in tests)
            if sys.stdin.isatty():
                print("\n⚠️  Existing trip brief found!")
                print("=" * 50)
                print(f"Destinations: {[d.destination for d in brief.destinations]}")
                print(f"Dates: {brief.start_date} to {brief.end_date}")
                print(f"Travel style: {brief.travel_style.value}")
                print(f"Interests: {', '.join(brief.interests)}")
                if brief.budget:
                    print(f"Budget: {brief.budget}")
                if brief.group_size:
                    print(f"Group size: {brief.group_size}")
                print("=" * 50)
                print("\nDo you want to: (1) Use this brief, (2) Edit it, or (3) Start over?")
                print("Type 1, 2, or 3 and press Enter.")
                
                choice = input("> ").strip()
                
                if choice == "3":
                    # Start over - delete existing
                    (self.files.folder / self.files.TRIP_BRIEF).unlink()
                    print("Starting fresh...\n")
                elif choice == "2":
                    # Use existing but allow editing - continue to interview
                    print("Continuing with edits...\n")
                    # Pre-populate state with existing values
                    self.state = InterviewState(
                        destinations=[d.destination for d in brief.destinations],
                        start_date=brief.start_date,
                        end_date=brief.end_date,
                        interests=brief.interests,
                        travel_style=brief.travel_style.value,
                        budget=brief.budget,
                        group_size=brief.group_size,
                        mobility=brief.mobility,
                        dietary=brief.dietary,
                        travellers_to_share=brief.travellers_to_share,
                    )
                else:  # choice == "1" or default
                    # Use as-is
                    print("Using existing brief.\n")
                    return True
            # Non-interactive mode (tests, scripts): just use existing brief
            else:
                # Set result to indicate brief was "loaded" (not created)
                self.result.trip_brief_created = True
                return True
        
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
        
        # Write research output (system file - user reviews this)
        self.files.write_suggestions(suggestions)
        
        # Auto-create activities.md as a starting point (user edits this)
        # Copies all research suggestions with source="research"
        from travelminion.models import ApprovedActivity, ApprovedActivityList
        
        activities = [
            ApprovedActivity(
                name=s.name,
                area=s.area,
                typical_duration=s.typical_duration,
                destination=s.destination,
                approved=True,
                opening_hours=s.opening_hours,
                notes=s.couldnt_verify,  # Include any verification notes
                indoor_fallback=None,
                source="research",
            )
            for s in suggestions
        ]
        
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

    # =========================================================================
    # End-to-End Pipeline
    # =========================================================================

    def run_full_pipeline(
        self,
        freeform_prompt: str,
    ) -> PipelineResult:
        """Run the entire pipeline from blank folder to itinerary.
        
        Args:
            freeform_prompt: User's initial trip description
            
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
            
            self.result.errors = errors
            return self.result
            
        except Exception as e:
            errors.append(str(e))
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
            
        except Exception as e:
            errors.append(str(e))
        
        self.result.errors = errors if errors else None
        return self.result
