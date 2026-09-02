"""Research step for TravelMinion.

Live research via Tavily (primary) + Jina AI Reader + DuckDuckGo fallbacks.
Produces Suggestions with confidence markers and "couldn't verify" notes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from travelminion.models import Suggestion


class RawResult(BaseModel):
    """Intermediate raw search result before shaping.
    
    Holds unparsed data from search sources.
    """

    title: str = Field(..., description="Attraction/activity name from source")
    url: str = Field(..., description="Source URL")
    snippet: str | None = Field(None, description="Search result snippet")
    area: str | None = Field(None, description="Neighbourhood/area if extractable")
    raw_hours: str | None = Field(None, description="Raw opening hours text")
    raw_cost: str | None = Field(None, description="Raw cost/pricing text")
    source_name: Literal["tavily", "jina", "ddgs"] = Field(
        ..., description="Which source this came from"
    )
    extra_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional source-specific data"
    )


class ResearchSource(ABC):
    """Abstract base class for research sources.
    
    Tests inject FakeResearchSource; production uses Tavily/Jina/ddgs.
    """

    @abstractmethod
    def search(
        self, destination: str, interests: list[str], days: int
    ) -> list[RawResult]:
        """Search for attractions/activities.
        
        Args:
            destination: Destination name (e.g., "Tokyo, Japan")
            interests: List of traveller interests
            days: Number of days at this destination (for scaling)
        
        Returns:
            List of raw results to be shaped into Suggestions
        """
        pass


class TavilySource(ResearchSource):
    """Primary research source via Tavily API."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://api.tavily.com/v1/search"

    def search(
        self, destination: str, interests: list[str], days: int
    ) -> list[RawResult]:
        """Search Tavily for destination attractions.
        
        Tavily basic search returns ~10 results per query.
        We query per interest to get good coverage.
        """
        results: list[RawResult] = []
        
        # Build interest-focused queries
        queries = []
        for interest in interests[:3]:  # Limit to top 3 interests
            queries.append(f"best {interest} in {destination} tourist attractions")
        
        # Add general query
        queries.append(f"top tourist attractions {destination} travel guide")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        for query in queries:
            try:
                payload = {
                    "query": query,
                    "search_depth": "basic",
                    "include_answers": True,
                    "max_results": 5,  # Keep per-query results reasonable
                }
                
                response = httpx.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                
                for result in data.get("results", []):
                    raw = self._parse_result(result, destination)
                    if raw:
                        results.append(raw)
                        
            except (httpx.HTTPError, httpx.RequestError, KeyError):
                # Skip failed queries, try others
                continue
        
        return results

    def _parse_result(self, result: dict[str, Any], destination: str) -> RawResult | None:
        """Parse Tavily result into RawResult."""
        try:
            title = result.get("title", "")
            if not title:
                return None
            
            url = result.get("url", "")
            snippet = result.get("content", result.get("snippet", ""))
            
            # Try to extract area from title/snippet
            area = self._extract_area(title, snippet, destination)
            
            # Try to extract hours/cost from snippet
            raw_hours = self._extract_hours(snippet)
            raw_cost = self._extract_cost(snippet)
            
            return RawResult(
                title=title,
                url=url,
                snippet=snippet or None,
                area=area,
                raw_hours=raw_hours,
                raw_cost=raw_cost,
                source_name="tavily",
                extra_metadata=result,
            )
        except Exception:
            return None

    def _extract_area(
        self, title: str, snippet: str, destination: str
    ) -> str | None:
        """Extract neighbourhood/area from text."""
        # Simple heuristic: look for district names
        # In production, this could use NER or a locations DB
        
        # Common patterns like "in Shinjuku", "Shibuya district"
        import re
        
        match = re.search(r"in ([A-Z][a-z]+(?: [A-Z][a-z]+)*)", title)
        if match:
            return match.group(1)
        
        return None

    def _extract_hours(self, text: str) -> str | None:
        """Extract opening hours from text."""
        if not text:
            return None
        
        import re
        
        # Patterns like "9am-6pm", "9:00-18:00", "open daily"
        patterns = [
            r"(\d{1,2}(?::\d{2})?(?:am|pm)\s*[-–]\s*\d{1,2}(?::\d{2})?(?:am|pm))",
            r"(\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2})",
            r"(open\s+(?:daily|monday|weekdays))",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    def _extract_cost(self, text: str) -> str | None:
        """Extract cost/pricing from text."""
        if not text:
            return None
        
        import re
        
        # Look for currency symbols + numbers, or words like "free"
        if "free" in text.lower():
            return "Free"
        
        patterns = [
            r"(\$|€|£|¥)\s*\d+(?:,\d{3})*(?:\.\d{2})?",
            r"\d+(?:,\d{3})*\s*(yen|dollars|euros|pounds)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None


class JinaSource(ResearchSource):
    """Jina AI Reader - URL to Markdown conversion.
    
    Used as fallback: Tavily gives URLs, Jina fetches full content.
    """

    def __init__(self) -> None:
        self.base_url = "https://r.jina.ai/"

    def search(
        self, destination: str, interests: list[str], days: int
    ) -> list[RawResult]:
        """Jina doesn't search; it fetches URLs.
        
        This source is used differently: Tavily provides URLs,
        then Jina fetches full page content for richer extraction.
        
        For the ResearchSource interface, we return empty here.
        Use fetch_url() directly for Jina's actual purpose.
        """
        return []

    def fetch_url(self, url: str) -> str | None:
        """Fetch full page content via Jina AI Reader.
        
        Args:
            url: URL to fetch
            
        Returns:
            Markdown content or None on failure
        """
        try:
            response = httpx.get(
                f"{self.base_url}{url}",
                timeout=15.0,
                headers={"User-Agent": "TravelMinion/1.0"},
            )
            response.raise_for_status()
            return response.text
        except (httpx.HTTPError, httpx.RequestError):
            return None


class DuckDuckGoSource(ResearchSource):
    """DuckDuckGo search via ddgs library.
    
    Zero-key fallback when Tavily fails.
    """

    def search(
        self, destination: str, interests: list[str], days: int
    ) -> list[RawResult]:
        """Search DuckDuckGo."""
        results: list[RawResult] = []
        
        try:
            from ddgs import DDGS
            
            ddgs = DDGS()
            
            # Build queries
            queries = [
                f"best {interest} {destination} tourist attraction"
                for interest in interests[:2]
            ]
            queries.append(f"top attractions {destination} travel guide")
            
            for query in queries:
                try:
                    search_results = ddgs.text(query, max_results=5)
                    for r in search_results:
                        raw = RawResult(
                            title=r.get("title", ""),
                            url=r.get("href", ""),
                            snippet=r.get("body", ""),
                            area=None,
                            raw_hours=None,
                            raw_cost=None,
                            source_name="ddgs",
                            extra_metadata=r,
                        )
                        results.append(raw)
                except Exception:
                    continue
                    
        except ImportError:
            # ddgs not installed
            pass
        except Exception:
            pass
        
        return results


class ResearchEngine:
    """Main research orchestrator.
    
    Manages fallback chain and result shaping.
    """

    def __init__(
        self,
        tavily_api_key: str | None = None,
    ) -> None:
        self.tavily = TavilySource(tavily_api_key) if tavily_api_key else None
        self.jina = JinaSource()
        self.ddgs = DuckDuckGoSource()

    def research_destination(
        self,
        destination: str,
        interests: list[str],
        days: int,
    ) -> list[Suggestion]:
        """Research a single destination.
        
        Args:
            destination: Destination name
            interests: Traveller interests
            days: Days at destination (for scaling)
            
        Returns:
            List of Suggestions with confidence markers
        """
        # Try sources in priority order
        raw_results: list[RawResult] = []
        sources_tried: list[str] = []
        
        if self.tavily:
            results = self.tavily.search(destination, interests, days)
            raw_results.extend(results)
            sources_tried.append("tavily")
        
        # If Tavily returned nothing or not installed, try ddgs
        if not raw_results:
            results = self.ddgs.search(destination, interests, days)
            raw_results.extend(results)
            sources_tried.append("ddgs")
        
        # Enrich with Jina for URLs we have
        if raw_results and self.jina:
            raw_results = self._enrich_with_jina(raw_results)
        
        # Shape into Suggestions
        suggestions = self._shape_suggestions(raw_results, interests, days)
        
        return suggestions

    def research_all(self, trip_brief) -> list[Suggestion]:
        """Research all destinations in a trip brief.
        
        Args:
            trip_brief: TripBrief with destinations list
            
        Returns:
            Combined list of all Suggestions from all destinations
        """
        all_suggestions: list[Suggestion] = []
        
        for dest_stop in trip_brief.destinations:
            suggestions = self.research_destination(
                dest_stop.destination,
                trip_brief.interests,
                dest_stop.days,
            )
            all_suggestions.extend(suggestions)
        
        return all_suggestions


    def _enrich_with_jina(self, results: list[RawResult]) -> list[RawResult]:
        """Fetch full content via Jina for richer extraction."""
        enriched: list[RawResult] = []
        
        for raw in results:
            if raw.url:
                content = self.jina.fetch_url(raw.url)
                if content:
                    # Re-extract from full content
                    raw.raw_hours = self._extract_hours(content) or raw.raw_hours
                    raw.raw_cost = self._extract_cost(content) or raw.raw_cost
                    raw.extra_metadata["jina_content"] = content[:5000]  # Truncate
            enriched.append(raw)
        
        return enriched

    def _extract_hours(self, content: str) -> str | None:
        """Extract hours from full content."""
        import re
        
        patterns = [
            r"(?:opening hours?|hours)[:\s]+([^\n]+)",
            r"(\d{1,2}(?::\d{2})?(?:am|pm)\s*[-–]\s*\d{1,2}(?::\d{2})?(?:am|pm))",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    def _extract_cost(self, content: str) -> str | None:
        """Extract cost from full content."""
        import re
        
        if "free" in content.lower() and "entrance" in content.lower():
            return "Free"
        
        patterns = [
            r"(?:price|cost|entrance fee)[:\s]+([^\n]+)",
            r"(\$|€|£|¥)\s*\d+(?:,\d{3})*(?:\.\d{2})?",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None

    def _shape_suggestions(
        self,
        raw_results: list[RawResult],
        interests: list[str],
        days: int,
    ) -> list[Suggestion]:
        """Shape raw results into Suggestions with confidence scoring.
        
        Target: 8-12 suggestions per destination, scaled by days.
        """
        suggestions: list[Suggestion] = []
        seen_titles: set[str] = set()
        
        # Target count: ~4-6 per day, capped at 12
        target_min = min(4 * days, 8)
        target_max = min(6 * days, 12)
        
        for raw in raw_results:
            # Deduplicate by title
            title_lower = raw.title.lower()
            if title_lower in seen_titles:
                continue
            seen_titles.add(title_lower)
            
            # Shape into Suggestion
            suggestion = self._raw_to_suggestion(raw, interests)
            if suggestion:
                suggestions.append(suggestion)
            
            # Stop if we have enough
            if len(suggestions) >= target_max:
                break
        
        # If below minimum, note it in confidence
        if len(suggestions) < target_min:
            # Mark all as lower confidence due to sparse results
            for s in suggestions:
                if s.confidence == "high":
                    s.confidence = "medium"
        
        return suggestions

    def _raw_to_suggestion(
        self, raw: RawResult, interests: list[str]
    ) -> Suggestion | None:
        """Convert single RawResult to Suggestion."""
        if not raw.title:
            return None
        
        # Determine rationale from interests
        rationale = self._build_rationale(raw, interests)
        
        # Extract fields
        typical_duration = self._infer_duration(raw)
        season_weather = self._infer_season(raw)
        
        # Calculate confidence
        confidence, couldnt_verify = self._calculate_confidence(raw)
        
        return Suggestion(
            name=raw.title,
            rationale=rationale,
            area=raw.area or "City-wide",
            typical_duration=typical_duration,
            opening_hours=raw.raw_hours,
            approximate_cost=raw.raw_cost,
            season_weather_fit=season_weather,
            source_link=raw.url if raw.url else None,
            confidence=confidence,
            couldnt_verify=couldnt_verify,
            destination="",  # Caller sets this
        )

    def _build_rationale(self, raw: RawResult, interests: list[str]) -> str:
        """Build rationale tied to interests."""
        snippet = (raw.snippet or "").lower()
        
        matched_interests = []
        for interest in interests:
            if interest.lower() in snippet:
                matched_interests.append(interest)
        
        if matched_interests:
            return f"Matches your interest in {', '.join(matched_interests)}"
        
        return "Popular destination attraction"

    def _infer_duration(self, raw: RawResult) -> str:
        """Infer typical visit duration."""
        title_lower = raw.title.lower()
        snippet = (raw.snippet or "").lower()
        
        if "museum" in title_lower or "gallery" in snippet:
            return "2-3 hours"
        if "park" in title_lower or "garden" in snippet:
            return "1-2 hours"
        if "temple" in title_lower or "church" in snippet:
            return "1 hour"
        if "district" in title_lower or "neighborhood" in snippet:
            return "2-4 hours"
        
        return "1-2 hours"

    def _infer_season(self, raw: RawResult) -> str | None:
        """Infer season/weather fit."""
        snippet = (raw.snippet or "").lower()
        
        if "cherry blossom" in snippet or "spring" in snippet:
            return "Best in spring (March-May)"
        if "autumn" in snippet or "fall foliage" in snippet:
            return "Best in autumn (September-November)"
        if "indoor" in snippet:
            return "Good year-round (indoor)"
        
        return None

    def _calculate_confidence(
        self, raw: RawResult
    ) -> tuple[Literal["high", "medium", "low"], str | None]:
        """Calculate confidence and couldn't_verify note.
        
        high: Has hours + cost from reliable source
        medium: Has hours OR cost, most fields populated
        low: Missing critical info
        """
        missing: list[str] = []
        
        if not raw.raw_hours:
            missing.append("opening hours")
        if not raw.raw_cost:
            missing.append("pricing")
        if not raw.url:
            missing.append("source link")
        
        if len(missing) == 0:
            return "high", None
        elif len(missing) == 1:
            return "medium", f"Couldn't verify {missing[0]}"
        elif len(missing) == 2:
            return "low", f"Couldn't verify {', '.join(missing)}"
        else:
            return "low", f"Couldn't verify {', '.join(missing)}"
