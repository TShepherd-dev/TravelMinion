"""Tests for Google Docs export.

Tests the docs export seam:
- FakeDocsService for in-memory testing
- MarkdownToDocs conversion
- Doc ID persistence
"""

from __future__ import annotations

import pytest

from travelminion.docs import FakeDocsService
from travelminion.markdown_to_docs import MarkdownToDocs


class TestFakeDocsService:
    """Test FakeDocsService for tests."""

    def test_create_doc(self) -> None:
        """Create a fake doc."""
        service = FakeDocsService()
        
        doc_id = service.create_doc("Test Doc", "# Content")
        
        assert doc_id in service.docs
        assert service.docs[doc_id]["title"] == "Test Doc"
        assert service.docs[doc_id]["content"] == "# Content"
        assert service.docs[doc_id]["version"] == 1

    def test_update_doc(self) -> None:
        """Update a fake doc."""
        service = FakeDocsService()
        doc_id = service.create_doc("Test", "Old content")
        
        service.update_doc(doc_id, "New content")
        
        assert service.docs[doc_id]["content"] == "New content"
        assert service.docs[doc_id]["version"] == 2

    def test_update_nonexistent_doc(self) -> None:
        """Updating nonexistent doc raises."""
        service = FakeDocsService()
        
        with pytest.raises(FileNotFoundError):
            service.update_doc("nonexistent", "content")

    def test_share_doc(self) -> None:
        """Share a fake doc."""
        service = FakeDocsService()
        doc_id = service.create_doc("Test", "Content")
        
        service.share_doc(doc_id, ["user@example.com", "another@example.com"], "reader")
        
        assert len(service.shares[doc_id]) == 2
        assert service.shares[doc_id][0]["email"] == "user@example.com"
        assert service.shares[doc_id][0]["role"] == "reader"

    def test_share_doc_auto_creates_shares(self) -> None:
        """Sharing creates shares dict if missing."""
        service = FakeDocsService()
        # Manually delete shares to test auto-creation
        service.docs["manual_id"] = {"title": "Test", "content": "Content"}
        
        service.share_doc("manual_id", ["user@example.com"])
        
        assert "manual_id" in service.shares


class TestMarkdownToDocs:
    """Test Markdown to Google Docs conversion."""

    def test_heading_level_1(self) -> None:
        """Convert # heading to HEADING_1."""
        md = MarkdownToDocs("# My Heading")
        requests = md.build_requests()
        
        assert len(requests) == 2
        assert requests[0]["insertText"]["text"] == "My Heading\n"
        assert requests[1]["updateParagraphStyle"]["paragraphStyle"]["headingId"] == "HEADING_1"

    def test_heading_level_2(self) -> None:
        """Convert ## heading to HEADING_2."""
        md = MarkdownToDocs("## Subheading")
        requests = md.build_requests()
        
        assert len(requests) == 2
        assert requests[0]["insertText"]["text"] == "Subheading\n"
        assert requests[1]["updateParagraphStyle"]["paragraphStyle"]["headingId"] == "HEADING_2"

    def test_heading_level_3(self) -> None:
        """Convert ### heading to HEADING_3."""
        md = MarkdownToDocs("### Section")
        requests = md.build_requests()
        
        assert len(requests) == 2
        assert requests[0]["insertText"]["text"] == "Section\n"
        assert requests[1]["updateParagraphStyle"]["paragraphStyle"]["headingId"] == "HEADING_3"

    def test_unordered_list_dash(self) -> None:
        """Convert - item to bullet list."""
        md = MarkdownToDocs("- Item 1\n- Item 2")
        requests = md.build_requests()
        
        # Should have insert + bullet style for each item
        assert len(requests) == 4
        assert requests[0]["insertText"]["text"] == "Item 1\n"
        assert "bullet" in requests[1]["updateParagraphStyle"]["paragraphStyle"]

    def test_unordered_list_asterisk(self) -> None:
        """Convert * item to bullet list."""
        md = MarkdownToDocs("* Item")
        requests = md.build_requests()
        
        assert len(requests) == 2
        assert requests[0]["insertText"]["text"] == "Item\n"

    def test_ordered_list(self) -> None:
        """Convert 1. item to numbered list."""
        md = MarkdownToDocs("1. First\n2. Second")
        requests = md.build_requests()
        
        assert len(requests) == 4
        assert requests[0]["insertText"]["text"] == "First\n"
        assert "bullet" in requests[1]["updateParagraphStyle"]["paragraphStyle"]

    def test_regular_paragraph(self) -> None:
        """Convert plain text paragraph."""
        md = MarkdownToDocs("This is a paragraph.")
        requests = md.build_requests()
        
        assert len(requests) == 1
        assert requests[0]["insertText"]["text"] == "This is a paragraph.\n"

    def test_bold_formatting(self) -> None:
        """Process **bold** markdown."""
        md = MarkdownToDocs("**bold text**")
        requests = md.build_requests()
        
        assert len(requests) == 1
        assert "bold text\n" in requests[0]["insertText"]["text"]

    def test_italic_formatting(self) -> None:
        """Process *italic* markdown."""
        md = MarkdownToDocs("*italic text*")
        requests = md.build_requests()
        
        assert len(requests) == 1
        assert "italic text\n" in requests[0]["insertText"]["text"]

    def test_link_formatting(self) -> None:
        """Process [link](url) markdown."""
        md = MarkdownToDocs("[Google](https://google.com)")
        requests = md.build_requests()
        
        assert len(requests) == 1
        assert "Google (https://google.com)" in requests[0]["insertText"]["text"]

    def test_mixed_content(self) -> None:
        """Convert mixed markdown content."""
        content = """# Title

## Section

- Item 1
- Item 2

Regular paragraph with **bold**.
"""
        md = MarkdownToDocs(content)
        requests = md.build_requests()
        
        # Should have multiple requests for all elements
        assert len(requests) > 0

    def test_empty_markdown(self) -> None:
        """Empty markdown returns empty requests."""
        md = MarkdownToDocs("")
        requests = md.build_requests()
        
        assert requests == []

    def test_empty_lines_skipped(self) -> None:
        """Empty lines don't create paragraphs."""
        md = MarkdownToDocs("Para 1\n\n\nPara 2")
        requests = md.build_requests()
        
        # Should have 2 paragraphs, not 4
        assert len(requests) == 2


class TestDocsIntegration:
    """Integration tests for Docs export."""

    def test_create_and_update_workflow(self) -> None:
        """Create doc, update it, verify version increment."""
        service = FakeDocsService()
        
        doc_id = service.create_doc("Research Output", "# Suggestions")
        service.update_doc(doc_id, "# Updated Suggestions")
        
        assert service.docs[doc_id]["version"] == 2
        assert service.docs[doc_id]["content"] == "# Updated Suggestions"

    def test_create_and_share_workflow(self) -> None:
        """Create doc, share it, verify shares."""
        service = FakeDocsService()
        
        doc_id = service.create_doc("Trip Research", "Content")
        service.share_doc(doc_id, ["traveller@example.com"], "reader")
        
        assert len(service.shares[doc_id]) == 1
        assert service.shares[doc_id][0]["role"] == "reader"
