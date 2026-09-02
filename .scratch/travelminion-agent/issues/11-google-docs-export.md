# 11: Google Docs export for research output

**What to build:** Push research-output.md to a Google Doc for collaborative review via Google MCP servers.

**Blocked by:** 03 (Research + Approved Activity List)

**Status:** done (via MCP - no code needed)

- [x] Google MCP servers configured in opencode.json
- [x] OAuth handled by opencode (not our code)
- [x] Use MCP tools in agent workflow
- [x] SKILL.md updated to document MCP approach

## Implementation: Google MCP Servers

**opencode.json configuration:**
```json
{
  "mcp": {
    "google-calendar": {
      "serverUrl": "https://calendarmcp.googleapis.com/mcp/v1",
      "oauth": {
        "clientId": "${env:GOOGLE_MCP_CLIENT_ID}",
        "clientSecret": "${env:GOOGLE_MCP_CLIENT_SECRET}"
      }
    },
    "google-docs": {
      "serverUrl": "https://docsmcp.googleapis.com/mcp/v1",
      "oauth": {
        "clientId": "${env:GOOGLE_MCP_CLIENT_ID}",
        "clientSecret": "${env:GOOGLE_MCP_CLIENT_SECRET}"
      }
    },
    "google-drive": {
      "serverUrl": "https://drivemcp.googleapis.com/mcp/v1",
      "oauth": {
        "clientId": "${env:GOOGLE_MCP_CLIENT_ID}",
        "clientSecret": "${env:GOOGLE_MCP_CLIENT_SECRET}"
      }
    }
  }
}
```

**Environment variables:**
- `GOOGLE_MCP_CLIENT_ID`: OAuth client ID from Google Cloud Console
- `GOOGLE_MCP_CLIENT_SECRET`: OAuth client secret from Google Cloud Console

**OAuth setup (one-time):**
1. Create Google Cloud project
2. Enable MCP APIs: Calendar, Docs, Drive
3. Create OAuth Desktop app credentials
4. Set env vars `GOOGLE_MCP_CLIENT_ID` and `GOOGLE_MCP_CLIENT_SECRET`
5. First use: opencode opens browser for OAuth
6. Token cached for subsequent runs

**Benefits over Python API approach:**
- No Python dependencies (`google-api-python-client`)
- OAuth handled by opencode, not our code
- Configuration, not code
- Fewer things to maintain

**Agent workflow:**
After research phase, agent calls MCP tools:
- `google-docs.create_doc(title, markdown_content)`
- `google-docs.update_doc(doc_id, markdown_content)`
- `google-drive.share_file(doc_id, email, role="reader")`

Store doc_id in `trip-brief.md` for reuse.

---

## Previous Approach (Python API - REMOVED)

Originally implemented with `google-api-python-client` but removed in favor of MCP.
Files removed: `travelminion/docs.py`, `travelminion/markdown_to_docs.py`, `tests/test_docs.py`

