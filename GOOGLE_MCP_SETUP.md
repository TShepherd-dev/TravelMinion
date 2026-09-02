# Google MCP Servers Setup (5 minutes)

## Quick Setup

### 1. Create Google Cloud Project

1. Go to https://console.cloud.google.com/
2. Create new project: `TravelMinion`
3. Note your project ID

### 2. Enable MCP APIs

Run this command (replace PROJECT_ID):

```bash
gcloud services enable calendarmcp.googleapis.com \
  docsmcp.googleapis.com \
  drivemcp.googleapis.com \
  --project=PROJECT_ID
```

Or enable via console:
- Calendar MCP API: https://console.cloud.google.com/apis/library/calendarmcp.googleapis.com
- Docs MCP API: https://console.cloud.google.com/apis/library/docsmcp.googleapis.com
- Drive MCP API: https://console.cloud.google.com/apis/library/drivemcp.googleapis.com

### 3. Create OAuth Credentials

1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. **User Type**: External
3. App name: `TravelMinion`
4. Add your email as test user
5. **Publishing status**: Set to **"In Production"** (non-expiring tokens)
6. Save

7. Go to: https://console.cloud.google.com/apis/credentials
8. **Create Credentials** → **OAuth client ID**
9. Application type: **Desktop app**
10. Name: `TravelMinion`
11. Download JSON

### 4. Set Environment Variables

From the JSON, extract:
- `client_id`
- `client_secret`

Set these environment variables:

**Windows PowerShell:**
```powershell
$env:GOOGLE_MCP_CLIENT_ID="your-client-id-here"
$env:GOOGLE_MCP_CLIENT_SECRET="your-client-secret-here"
```

**Permanent (Windows):**
```powershell
[Environment]::SetEnvironmentVariable("GOOGLE_MCP_CLIENT_ID", "your-client-id", "User")
[Environment]::SetEnvironmentVariable("GOOGLE_MCP_CLIENT_SECRET", "your-secret", "User")
```

**Mac/Linux:**
```bash
export GOOGLE_MCP_CLIENT_ID="your-client-id-here"
export GOOGLE_MCP_CLIENT_SECRET="your-client-secret-here"
```

### 5. Done!

opencode is already configured in `opencode.json` to use these MCP servers.

First time you use Calendar or Docs features:
1. opencode opens your browser
2. You approve OAuth
3. Token cached automatically
4. Subsequent runs are silent

## What's Configured

`opencode.json` has three MCP servers ready:

```json
{
  "mcp": {
    "google-calendar": {
      "serverUrl": "https://calendarmcp.googleapis.com/mcp/v1"
    },
    "google-docs": {
      "serverUrl": "https://docsmcp.googleapis.com/mcp/v1"
    },
    "google-drive": {
      "serverUrl": "https://drivemcp.googleapis.com/mcp/v1"
    }
  }
}
```

All use the same OAuth credentials.

## Troubleshooting

**"Access blocked"**: Make sure you set Publishing Status to "In Production"

**"Token expired"**: You didn't set "In Production" - tokens expire after 7 days in Testing mode

**Want to reset OAuth?**: Delete the cached token (location varies by OS) and run again

## Why MCP?

| Python API | MCP Servers |
|------------|-------------|
| 700 lines of Python code | 0 lines (config only) |
| `google-api-python-client` dependency | No deps |
| Our code handles OAuth | opencode handles OAuth |
| We manage token refresh | opencode manages refresh |
| Hard to maintain | Standard, Google-maintained |

**Result**: We removed 700+ lines of code and got a better integration.
