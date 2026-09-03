# Tavily API Key Setup (2 minutes)

## Get Your Free API Key

1. Go to https://app.tavily.com/
2. Sign up (free tier: 1,000 searches/month)
3. Copy your API key from the dashboard

## Option 1: File-Based Config (Recommended for Sharing)

Edit `travelminion.config.json` in the repo root:

```json
{
  "tavily_api_key": "your-api-key-here"
}
```

**Benefits:**
- ✅ Easy to share with team members
- ✅ No environment variables needed
- ✅ Works the same on all systems
- ✅ Can add other config options later

**Important:** This file is in `.gitignore` - don't commit it!

## Option 2: Environment Variable

**Windows (permanent):**
```powershell
[Environment]::SetEnvironmentVariable("TAVILY_API_KEY", "your-api-key-here", "User")
```

Then restart terminal/opencode.

**Mac/Linux:**
```bash
export TAVILY_API_KEY="your-api-key-here"
```

Add to `~/.bashrc` or `~/.zshrc` for permanence.

## Verify It Works

Run the research phase - it will automatically use:
1. Key from `travelminion.config.json` (if exists)
2. Or `TAVILY_API_KEY` environment variable (if set)
3. Or fall back to DuckDuckGo (no key needed)

## What You Get

With Tavily API key:
- ✅ Live web search with AI-extracted results
- ✅ Better opening hours, cost, and detail extraction
- ✅ More accurate suggestions
- ✅ 1,000 free searches/month

Without key:
- ✅ DuckDuckGo fallback (works, but sparser results)
- ✅ Jina AI Reader still works for custom URLs
