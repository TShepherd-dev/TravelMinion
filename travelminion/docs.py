"""Google Docs export for research output.

Exports research-output.md to a Google Doc for collaborative review.
On regeneration, updates the same doc (using Google's built-in version history).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from travelminion.markdown_to_docs import MarkdownToDocs


class DocsService(ABC):
    """Abstract base class for Google Docs operations."""

    @abstractmethod
    def create_doc(self, title: str, content: str) -> str:
        """Create a new Google Doc.
        
        Args:
            title: Document title
            content: Markdown content
            
        Returns:
            doc_id from Google Docs API
        """
        pass

    @abstractmethod
    def update_doc(self, doc_id: str, content: str) -> None:
        """Update an existing Google Doc.
        
        Uses Google's built-in version history.
        
        Args:
            doc_id: Document ID to update
            content: New markdown content
        """
        pass

    @abstractmethod
    def share_doc(
        self, doc_id: str, emails: list[str], role: str = "reader"
    ) -> None:
        """Share a Google Doc with users.
        
        Args:
            doc_id: Document ID
            emails: List of email addresses to share with
            role: Permission level (default: "reader")
        """
        pass


class FakeDocsService(DocsService):
    """In-memory fake DocsService for tests.
    
    Stores docs in a dict with no network calls.
    """

    def __init__(self) -> None:
        self.docs: dict[str, dict[str, Any]] = {}
        self.shares: dict[str, list[dict[str, Any]]] = {}

    def create_doc(self, title: str, content: str) -> str:
        """Create a fake doc."""
        import uuid
        
        doc_id = str(uuid.uuid4())
        self.docs[doc_id] = {
            "title": title,
            "content": content,
            "version": 1,
        }
        self.shares[doc_id] = []
        return doc_id

    def update_doc(self, doc_id: str, content: str) -> None:
        """Update a fake doc (increments version)."""
        if doc_id not in self.docs:
            raise FileNotFoundError(f"Doc {doc_id} not found")
        
        self.docs[doc_id]["content"] = content
        self.docs[doc_id]["version"] += 1

    def share_doc(
        self, doc_id: str, emails: list[str], role: str = "reader"
    ) -> None:
        """Share a fake doc."""
        if doc_id not in self.shares:
            self.shares[doc_id] = []
        
        for email in emails:
            self.shares[doc_id].append({
                "email": email,
                "role": role,
            })


class GoogleDocsService(DocsService):
    """Google Docs API implementation.
    
    Uses google-api-client with OAuth2 authentication.
    Token stored in ~/.travelminion/token.json (shared with Calendar).
    """

    SCOPES = ["https://www.googleapis.com/auth/documents"]

    def __init__(self, credentials_path: str | None = None) -> None:
        """Initialize with optional credentials path.
        
        Args:
            credentials_path: Path to credentials.json (default: ~/.travelminion/credentials.json)
        """
        from pathlib import Path
        
        if credentials_path is None:
            home = Path.home()
            credentials_path = str(home / ".travelminion" / "credentials.json")
        
        self.credentials_path = credentials_path
        self._service = None

    def _get_service(self):
        """Get authenticated Google Docs service."""
        if self._service is not None:
            return self._service
        
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        
        home = Path.home()
        token_path = home / ".travelminion" / "token.json"
        creds_path = Path(self.credentials_path)
        
        creds = None
        
        # Load existing credentials
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(
                token_path, self.SCOPES
            )
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    creds_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials
            token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        
        self._service = build("docs", "v1", credentials=creds)
        return self._service

    def create_doc(self, title: str, content: str) -> str:
        """Create a new Google Doc."""
        service = self._get_service()
        
        # Create empty document
        doc = service.documents().create(body={"title": title}).execute()
        doc_id = doc["documentId"]
        
        # Insert content
        converter = MarkdownToDocs(content)
        requests = converter.build_requests()
        
        if requests:
            service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": requests}
            ).execute()
        
        return doc_id

    def update_doc(self, doc_id: str, content: str) -> None:
        """Update an existing Google Doc."""
        service = self._get_service()
        
        # Get current document to find end index
        doc = service.documents().get(documentId=doc_id).execute()
        
        # Find the body content range
        body = doc.get("body", {})
        end_index = body.get("endIndex", 2)  # Default to after title
        
        # Delete existing content (keep title)
        # Start from index 1 (after document start)
        requests = [{
            "deleteContentRange": {
                "range": {
                    "startIndex": 1,
                    "endIndex": end_index - 1,
                }
            }
        }]
        
        # Insert new content
        converter = MarkdownToDocs(content)
        requests.extend(converter.build_requests())
        
        service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": requests}
        ).execute()

    def share_doc(
        self, doc_id: str, emails: list[str], role: str = "reader"
    ) -> None:
        """Share a Google Doc with users."""
        from pathlib import Path

        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        # Need Drive API for sharing
        home = Path.home()
        token_path = home / ".travelminion" / "token.json"
        
        creds = Credentials.from_authorized_user_file(token_path, [
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/drive"
        ])
        
        drive_service = build("drive", "v3", credentials=creds)
        
        for email in emails:
            permission = {
                "type": "user",
                "role": role,
                "emailAddress": email,
            }
            
            drive_service.permissions().create(
                fileId=doc_id,
                body=permission,
                fields="id",
                sendNotificationEmail=False,
            ).execute()
