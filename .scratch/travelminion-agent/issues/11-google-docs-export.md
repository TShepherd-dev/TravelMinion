# 11: Google Docs export for research output

**What to build:** Push research-output.md to a Google Doc for collaborative review. On regeneration, update the same doc (using Google's built-in version history). Store doc_id in the trip folder for reuse. Share doc read-only with listed travellers.

**Blocked by:** 03 (Research + Approved Activity List), 07 (Calendar boundary + post step)

**Status:** ready-for-agent

- [ ] GoogleDocsService class (thin abstraction over Google Docs API)
- [ ] FakeDocsService for tests (in-memory, no network)
- [ ] OAuth setup: new scope `https://www.googleapis.com/auth/documents`
- [ ] create_or_update_doc(title: str, content: str, doc_id: str | None) → doc_id
- [ ] share_doc(doc_id: str, emails: list[str]) → read-only access
- [ ] Markdown → Google Docs structure (headings, lists, links, tables)
- [ ] Store doc_id in trip-brief.md or metadata file
- [ ] Tests: create doc, update doc, share doc, Markdown formatting
- [ ] SKILL.md updated to document Google Docs export

## Implementation Notes

**New files:**
- `travelminion/docs.py`: GoogleDocsService + FakeDocsService
- `travelminion/markdown_to_docs.py`: Markdown → Google Docs BatchUpdate operations

**Service interface:**
```python
class DocsService(ABC):
    def create_doc(self, title: str, content: str) -> str  # returns doc_id
    def update_doc(self, doc_id: str, content: str) -> None
    def share_doc(self, doc_id: str, emails: list[str], role: str = "reader") -> None
```

**OAuth:**
- Same flow as Calendar (Desktop app, loopback localhost)
- Store token.json in `~/.travelminion/` (shared with calendar)
- Add `documents` scope to existing OAuth consent

**Markdown parsing:**
- Headings (`#`, `##`, `###`) → Google Docs heading styles
- Lists (`-`, `*`, `1.`) → Google Docs list types
- Links (`[text](url)`) → Google Docs inline links
- Bold/italic → TextStyle updates
- Tables (if used) → Google Docs tables

**Versioning:**
- Use Google Docs' built-in version history (File → Version history → See version history)
- Same doc_id updated in place (no manual versioning needed)
- User can view/restore old versions via Google Docs UI

**Sharing:**
- Same traveller emails as calendar sharing
- Role: `reader` (comment-only or view-only)
- Use `acl.insert` equivalent for Docs API

**Tests:**
- FakeDocsService stores docs in dict
- Test Markdown → Docs formatting conversion
- Test share logic
- Test doc_id persistence in trip folder

---
