"""Convert Markdown to Google Docs API batch update operations.

Parses markdown and generates Google Docs BatchUpdate requests.
Supports: headings, lists, links, bold, italic.
"""

from __future__ import annotations

import re
from typing import Any


class MarkdownToDocs:
    """Convert Markdown text to Google Docs API requests."""

    def __init__(self, markdown: str) -> None:
        """Initialize with markdown content."""
        self.markdown = markdown
        self._requests: list[dict[str, Any]] = []

    def build_requests(self) -> list[dict[str, Any]]:
        """Build list of Google Docs BatchUpdate requests.
        
        Returns:
            List of request dicts for batchUpdate
        """
        lines = self.markdown.split("\n")
        
        current_list_type = None
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                if current_list_type:
                    # End current list
                    current_list_type = None
                continue
            
            # Headings
            if stripped.startswith("# "):
                if current_list_type:
                    current_list_type = None
                self._requests.append({
                    "insertText": {
                        "text": stripped[2:] + "\n",
                        "location": {"index": 1},
                    }
                })
                # Apply heading style
                self._requests.append({
                    "updateParagraphStyle": {
                        "range": {"startIndex": 1, "endIndex": 1 + len(stripped[2:]) + 1},
                        "paragraphStyle": {"headingId": "HEADING_1"},
                        "fields": "headingId",
                    }
                })
            
            elif stripped.startswith("## "):
                if current_list_type:
                    current_list_type = None
                self._requests.append({
                    "insertText": {
                        "text": stripped[3:] + "\n",
                        "location": {"index": 1},
                    }
                })
                self._requests.append({
                    "updateParagraphStyle": {
                        "range": {"startIndex": 1, "endIndex": 1 + len(stripped[3:]) + 1},
                        "paragraphStyle": {"headingId": "HEADING_2"},
                        "fields": "headingId",
                    }
                })
            
            elif stripped.startswith("### "):
                if current_list_type:
                    current_list_type = None
                self._requests.append({
                    "insertText": {
                        "text": stripped[4:] + "\n",
                        "location": {"index": 1},
                    }
                })
                self._requests.append({
                    "updateParagraphStyle": {
                        "range": {"startIndex": 1, "endIndex": 1 + len(stripped[4:]) + 1},
                        "paragraphStyle": {"headingId": "HEADING_3"},
                        "fields": "headingId",
                    }
                })
            
            # Unordered list
            elif stripped.startswith("- ") or stripped.startswith("* "):
                if current_list_type != "unordered":
                    current_list_type = "unordered"
                
                item_text = stripped[2:]
                self._requests.append({
                    "insertText": {
                        "text": item_text + "\n",
                        "location": {"index": 1},
                    }
                })
                # Apply bullet style
                self._requests.append({
                    "updateParagraphStyle": {
                        "range": {"startIndex": 1, "endIndex": 1 + len(item_text) + 1},
                        "paragraphStyle": {
                            "bullet": {
                                "listId": "unordered_list",
                                "nestingLevel": 0,
                            }
                        },
                        "fields": "bullet",
                    }
                })
            
            # Ordered list
            elif re.match(r"^\d+\. ", stripped):
                if current_list_type != "ordered":
                    current_list_type = "ordered"
                
                item_text = re.sub(r"^\d+\. ", "", stripped)
                self._requests.append({
                    "insertText": {
                        "text": item_text + "\n",
                        "location": {"index": 1},
                    }
                })
                # Apply numbering style
                self._requests.append({
                    "updateParagraphStyle": {
                        "range": {"startIndex": 1, "endIndex": 1 + len(item_text) + 1},
                        "paragraphStyle": {
                            "bullet": {
                                "listId": "ordered_list",
                                "nestingLevel": 0,
                            }
                        },
                        "fields": "bullet",
                    }
                })
            
            # Regular paragraph
            else:
                if current_list_type:
                    current_list_type = None
                
                # Process inline formatting
                text = self._process_inline_formatting(stripped)
                self._requests.append({
                    "insertText": {
                        "text": text + "\n",
                        "location": {"index": 1},
                    }
                })
        
        return self._requests

    def _process_inline_formatting(self, text: str) -> str:
        """Process inline markdown formatting.
        
        Handles: **bold**, *italic*, [link](url)
        
        This is a simplified version - full implementation would
        track indices and apply TextStyle updates separately.
        For now, we strip formatting markers.
        """
        # Bold: **text** → text
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        
        # Italic: *text* → text
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        
        # Links: [text](url) → text (url)
        text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1 (\2)", text)
        
        return text
