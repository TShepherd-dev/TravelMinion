# Tavily API Key Setup (2 minutes)

## Get Your Free API Key

1. Go to https://app.tavily.com/
2. Sign up (free tier: 1,000 searches/month)
3. Copy your API key from the dashboard

## Set Environment Variable

**Windows PowerShell (temporary):**
```powershell
$env:TAVILY_API_KEY="your-api-key-here"
```

**Windows (permanent):**
```powershell
[Environment]::SetEnvironmentVariable("TAVILY_API_KEY", "your-api-key-here", "User")
```

Then restart your terminal/opencode.

**Mac/Linux:**
```bash
export TAVILY_API_KEY="your-api-key-here"
```

Add to `~/.bashrc` or `~/.zshrc` for permanence.

## Verify It Works

The skill will automatically use the key from `TAVILY_API_KEY` environment variable.

Without a key, it falls back to DuckDuckGo (no key needed, but less comprehensive results).

## What You Get

With Tavily API key:
- ✅ Live web search with AI-extracted results
- ✅ Better opening hours, cost, and detail extraction
- ✅ More accurate suggestions
- ✅ 1,000 free searches/month

Without key:
- ✅ DuckDuckGo fallback (works, but sparser results)
- ✅ Jina AI Reader still works for custom URLs

## Where It's Used

The key is passed to `ResearchEngine` in `travelminion/research.py`:

```python
import os
tavily_key = os.environ.get("TAVILY_API_KEY")
engine = ResearchEngine(tavily_api_key=tavily_key)
```

If `None`, Tavily is skipped and DuckDuckGo is used instead.
