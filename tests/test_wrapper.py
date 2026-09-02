"""Tests for TravelMinion convenience wrapper."""

from __future__ import annotations

from travelminion.wrapper import PipelineResult, TravelMinionOrchestrator


class TestPipelineResult:
    """Test PipelineResult dataclass."""

    def test_creation_minimal(self) -> None:
        """Create with defaults."""
        result = PipelineResult()
        
        assert result.trip_brief_created is False
        assert result.research_completed is False
        assert result.activities_approved == 0
        assert result.itinerary_planned is False
        assert result.errors is None

    def test_creation_with_values(self) -> None:
        """Create with specific values."""
        result = PipelineResult(
            trip_brief_created=True,
            research_completed=True,
            activities_approved=15,
            itinerary_planned=True,
        )
        
        assert result.trip_brief_created is True
        assert result.research_completed is True
        assert result.activities_approved == 15
        assert result.itinerary_planned is True

    def test_has_errors(self) -> None:
        """Check error detection."""
        assert PipelineResult().has_errors() is False
        assert PipelineResult(errors=["error"]).has_errors() is True

    def test_summary_with_actions(self) -> None:
        """Summary lists completed actions."""
        result = PipelineResult(
            trip_brief_created=True,
            research_completed=True,
            activities_approved=10,
            itinerary_planned=True,
        )
        summary = result.summary()
        
        assert "Trip Brief created" in summary
        assert "Research completed" in summary
        assert "10 activities approved" in summary
        assert "Itinerary planned" in summary

    def test_summary_with_errors(self) -> None:
        """Summary includes errors."""
        result = PipelineResult(errors=["Error 1", "Error 2"])
        summary = result.summary()
        
        assert "Error 1" in summary
        assert "Error 2" in summary

    def test_summary_empty(self) -> None:
        """Empty result has no summary."""
        result = PipelineResult()
        assert result.summary() == "No actions taken"


class TestTravelMinionOrchestrator:
    """Test orchestrator with fake services."""

    def test_init_defaults(self) -> None:
        """Initialize with defaults."""
        orch = TravelMinionOrchestrator(trip_folder="test-folder")
        
        assert str(orch.trip_folder) == "test-folder"
        assert orch.research_engine is not None

    def test_phase1_interview_basic(self) -> None:
        """Phase 1: freeform prompt to Trip Brief."""
        orch = TravelMinionOrchestrator()
        
        success = orch.phase1_interview("Japan trip, April 1-10, 2027")
        
        assert success is True
        assert orch.result.trip_brief_created is True

    def test_phase2_research_canned(self) -> None:
        """Phase 2: research with canned results."""
        orch = TravelMinionOrchestrator()
        orch.phase1_interview("Japan trip, April 1-10, 2027")
        
        success = orch.phase2_research()
        
        assert success is True
        assert orch.result.research_completed is True
        # Research may return 0 activities (no Tavily API key), but should complete
        assert orch.result.research_completed is True

    def test_phase3_plan(self) -> None:
        """Phase 3: plan itinerary."""
        orch = TravelMinionOrchestrator()
        orch.phase1_interview("Japan trip, April 1-10, 2027")
        orch.phase2_research()
        
        success = orch.phase3_plan()
        
        assert success is True
        assert orch.result.itinerary_planned is True

    def test_run_full_pipeline_end_to_end(self, tmp_path) -> None:
        """End-to-end: blank folder to itinerary."""
        orch = TravelMinionOrchestrator(trip_folder=tmp_path)
        
        result = orch.run_full_pipeline(
            "Japan trip, April 1-10, 2027, casual pace, temples and food"
        )
        
        assert result.trip_brief_created is True
        assert result.research_completed is True
        # Research may return 0 activities without Tavily API key
        assert result.itinerary_planned is True
        assert not result.errors  # Empty list or None is fine

    def test_phases_separately_invokable(self, tmp_path) -> None:
        """Phases can be run individually."""
        orch = TravelMinionOrchestrator(trip_folder=tmp_path)
        
        # Run each phase separately
        assert orch.phase1_interview("Test trip") is True
        assert orch.result.trip_brief_created is True
        
        assert orch.phase2_research() is True
        assert orch.result.research_completed is True
        
        assert orch.phase3_plan() is True
        assert orch.result.itinerary_planned is True
        
        # Verify files exist
        assert orch.files.trip_brief_exists()
        assert orch.files.activities_exists()
        assert orch.files.itinerary_exists()
