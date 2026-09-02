"""Tests for the convenience wrapper.

Tests the end-to-end pipeline through the file-interface seam.
"""

import tempfile
from pathlib import Path

import pytest

from travelminion.wrapper import PipelineResult, TravelMinionOrchestrator


class TestPipelineResult:
    """Test PipelineResult dataclass."""

    def test_creation_minimal(self):
        result = PipelineResult()
        assert not result.trip_brief_created
        assert not result.research_completed
        assert result.activities_approved == 0
        assert not result.itinerary_planned
        assert not result.calendar_posted
        assert result.calendar_id is None
        assert result.events_posted == 0
        assert result.errors is None

    def test_creation_with_values(self):
        result = PipelineResult(
            trip_brief_created=True,
            research_completed=True,
            activities_approved=5,
            itinerary_planned=True,
            calendar_posted=True,
            calendar_id="cal123",
            events_posted=10,
        )
        assert result.trip_brief_created
        assert result.research_completed
        assert result.activities_approved == 5
        assert result.itinerary_planned
        assert result.calendar_posted
        assert result.calendar_id == "cal123"
        assert result.events_posted == 10

    def test_has_errors(self):
        result = PipelineResult()
        assert not result.has_errors()
        
        result.errors = ["Something went wrong"]
        assert result.has_errors()

    def test_summary_empty(self):
        result = PipelineResult()
        assert result.summary() == "No actions taken"

    def test_summary_with_actions(self):
        result = PipelineResult(
            trip_brief_created=True,
            research_completed=True,
            activities_approved=3,
            itinerary_planned=True,
            calendar_posted=True,
            events_posted=5,
        )
        summary = result.summary()
        assert "✓ Trip Brief created" in summary
        assert "✓ Research completed" in summary
        assert "✓ 3 activities approved" in summary
        assert "✓ Itinerary planned" in summary
        assert "✓ Calendar posted (5 events)" in summary

    def test_summary_with_errors(self):
        result = PipelineResult(errors=["Error 1", "Error 2"])
        summary = result.summary()
        assert "✗ Errors: Error 1, Error 2" in summary


class TestTravelMinionOrchestrator:
    """Test orchestrator with fake calendar and canned research."""

    @pytest.fixture
    def temp_trip_folder(self):
        """Create a temporary trip folder for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_init_with_fake_calendar(self, temp_trip_folder):
        """Orchestrator initializes with fake calendar by default."""
        orch = TravelMinionOrchestrator(temp_trip_folder)
        assert orch.trip_folder == temp_trip_folder
        assert orch.files.exists()
        assert not orch.result.has_errors()

    def test_phase1_interview_basic(self, temp_trip_folder):
        """Phase 1 creates Trip Brief from freeform prompt."""
        orch = TravelMinionOrchestrator(temp_trip_folder)
        
        prompt = "Two weeks in Japan starting April 1, 2027. Packed pace, love temples and food."
        success = orch.phase1_interview(prompt)
        
        assert success
        assert orch.result.trip_brief_created
        assert orch.files.trip_brief_exists()
        
        brief = orch.files.read_trip_brief()
        assert brief.destinations  # Should have parsed destinations

    def test_phase2_research_canned(self, temp_trip_folder):
        """Phase 2 runs research with canned data (fake)."""
        orch = TravelMinionOrchestrator(temp_trip_folder)
        
        # First create a Trip Brief
        orch.phase1_interview("Japan, April 1-15, 2027, casual, temples")
        
        # Research will use fake/canned data since we're not calling real Tavily
        orch.phase2_research()
        
        # Research completes (may have empty suggestions in test mode)
        assert orch.result.research_completed
        assert orch.files.research_output_exists()

    def test_phase3_plan(self, temp_trip_folder):
        """Phase 3 plans itinerary from approved activities."""
        orch = TravelMinionOrchestrator(temp_trip_folder)
        
        # Setup: Trip Brief
        orch.phase1_interview("Japan, April 1-15, 2027, casual, temples")
        
        # Manually add some approved activities (bypassing research for test)
        from travelminion.models import ApprovedActivity, ApprovedActivityList
        
        activities = ApprovedActivityList(activities=[
            ApprovedActivity(
                name="Senso-ji Temple",
                area="Asakusa",
                typical_duration="2 hours",
                destination="Tokyo",
                approved=True,
                opening_hours="6am-5pm",
            ),
            ApprovedActivity(
                name="Meiji Shrine",
                area="Shibuya",
                typical_duration="1-2 hours",
                destination="Tokyo",
                approved=True,
                opening_hours="sunrise-sunset",
            ),
        ])
        orch.files.write_activities(activities)
        
        # Plan
        success = orch.phase3_plan()
        
        assert success
        assert orch.result.itinerary_planned
        assert orch.files.itinerary_exists()
        
        itinerary = orch.files.read_itinerary()
        assert len(itinerary.days) > 0

    def test_phase4_post_with_fake_calendar(self, temp_trip_folder):
        """Phase 4 posts to fake calendar."""
        orch = TravelMinionOrchestrator(temp_trip_folder)
        
        # Setup: Trip Brief + activities
        orch.phase1_interview("Japan, April 1-3, 2027, packed, temples")
        
        from travelminion.models import ApprovedActivity, ApprovedActivityList
        activities = ApprovedActivityList(activities=[
            ApprovedActivity(
                name="Test Activity",
                area="Test Area",
                typical_duration="2 hours",
                destination="Tokyo",
                approved=True,
            ),
        ])
        orch.files.write_activities(activities)
        orch.phase3_plan()
        
        # Post
        success = orch.phase4_post(confirm=True)
        
        assert success
        assert orch.result.calendar_posted
        assert orch.result.calendar_id is not None
        assert orch.result.events_posted > 0

    def test_rebuild_calculate_impact(self, temp_trip_folder):
        """Rebuild calculates impact without applying."""
        orch = TravelMinionOrchestrator(temp_trip_folder)
        
        # Setup: post an itinerary first
        orch.phase1_interview("Japan, April 1-3, 2027, packed")
        from travelminion.models import ApprovedActivity, ApprovedActivityList
        activities = ApprovedActivityList(activities=[
            ApprovedActivity(
                name="Activity 1",
                area="A1",
                typical_duration="2h",
                destination="Tokyo",
                approved=True,
            ),
        ])
        orch.files.write_activities(activities)
        orch.phase3_plan()
        orch.phase4_post(confirm=True)
        
        # Calculate rebuild impact (no confirm)
        success = orch.rebuild(confirm=False)
        
        assert success
        # Impact calculated but not applied

    def test_run_full_pipeline_end_to_end(self, temp_trip_folder):
        """End-to-end: blank folder → posted calendar."""
        orch = TravelMinionOrchestrator(temp_trip_folder)
        
        prompt = "Japan trip, April 1-10, 2027, casual pace, interested in temples and food"
        result = orch.run_full_pipeline(prompt, auto_confirm=True)
        
        # Verify all phases completed
        assert result.trip_brief_created
        assert result.research_completed
        assert result.itinerary_planned
        assert result.calendar_posted
        assert not result.has_errors()
        
        # Verify files exist
        assert orch.files.trip_brief_exists()
        assert orch.files.research_output_exists()
        assert orch.files.activities_exists()
        assert orch.files.itinerary_exists()

    def test_run_full_pipeline_with_errors(self, temp_trip_folder):
        """Pipeline handles errors gracefully."""
        orch = TravelMinionOrchestrator(temp_trip_folder)
        
        # Empty prompt should still work (uses defaults)
        result = orch.run_full_pipeline("", auto_confirm=True)
        
        # Should complete or report errors gracefully
        assert result is not None

    def test_phases_separately_invokable(self, temp_trip_folder):
        """Each phase can be run independently."""
        orch = TravelMinionOrchestrator(temp_trip_folder)
        
        # Run only Phase 1
        orch.phase1_interview("Japan, April 2027, packed")
        assert orch.files.trip_brief_exists()
        assert not orch.files.research_output_exists()
        
        # Stop, then resume with Phase 3 (manual activities)
        from travelminion.models import ApprovedActivity, ApprovedActivityList
        activities = ApprovedActivityList(activities=[
            ApprovedActivity(
                name="Manual Activity",
                area="A",
                typical_duration="1h",
                destination="Tokyo",
                approved=True,
            ),
        ])
        orch.files.write_activities(activities)
        
        orch.phase3_plan()
        assert orch.files.itinerary_exists()
        
        # Phase 4 later
        orch.phase4_post(confirm=True)
        assert orch.result.calendar_posted
