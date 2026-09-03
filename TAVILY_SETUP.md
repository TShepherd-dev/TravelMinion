# API Key Setup

## Configuration File

Edit `travelminion.config.json` in the repo root:

```json
{
  "tavily_api_key": "your-tavily-key-here",
  "google": {
    "client_id": "your-google-client-id",
    "client_secret": "your-google-client-secret"
  }
}
```

**Benefits:**
- ✅ All config in one place
- ✅ Easy to share with team members
- ✅ No environment variables needed
- ✅ Works the same on all systems

**Important:** This file is in `.gitignore` - never commit it!

---

## Tavily API Key (Research)

### Get Your Free Key

1. Go to https://app.tavily.com/
2. Sign up (free tier: 1,000 searches/month)
3. Copy your API key
4. Paste into `travelminion.config.json`

### What You Get

With Tavily key:
- ✅ Live web search with AI-extracted results
- ✅ Better opening hours, cost, detail extraction
- ✅ 1,000 free searches/month

Without key:
- ✅ Falls back to DuckDuckGo (works, sparser results)

---

## Google OAuth Credentials (Future Use)

Currently removed, but config is ready if you want to re-add Google Calendar/Docs integration.

### Get Credentials

1. Go to https://console.cloud.google.com/
2. Create project, enable Calendar/Docs APIs
3. Create OAuth Desktop app credentials
4. Copy client ID and secret
5. Paste into `travelminion.config.json`

### Fallback

Without Google credentials:
- ✅ Share markdown files directly (email, Slack, Dropbox)
- ✅ Manual calendar entry (itinerary.md is formatted nicely)

---

## Environment Variables (Alternative)

If you prefer env vars over config file:

**Tavily:**
```bash
export TAVILY_API_KEY="your-key"
```

**Google:**
```bash
export GOOGLE_CLIENT_ID="your-id"
export GOOGLE_CLIENT_SECRET="your-secret"
```

Config file takes precedence if both are set.
