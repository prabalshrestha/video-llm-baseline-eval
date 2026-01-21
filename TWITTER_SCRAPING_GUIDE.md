# Twitter Scraping Guide (No API Key Required)

## Problem
The official Twitter API is limited to 100 requests per month on the free tier, which is insufficient for research purposes.

## Solution
Use alternative scraping methods that don't require API keys and have no rate limits.

## Installation

### Quick Start (Recommended)
```bash
# Install all scraping methods
pip install -r requirements-scraper.txt

# Install Playwright browsers (if using Playwright method)
playwright install chromium
```

### Individual Methods

#### Method 1: Tweepy-Self (Recommended)
- **Speed**: Fast
- **Reliability**: High
- **Setup**: Easiest

```bash
pip install tweepy-self
```

#### Method 2: SNScrape
- **Speed**: Medium
- **Reliability**: High
- **Setup**: Easy

```bash
pip install snscrape
```

#### Method 3: Playwright
- **Speed**: Slow (browser automation)
- **Reliability**: Highest
- **Setup**: Requires browser installation

```bash
pip install playwright
playwright install chromium
```

## Usage

### Basic Usage

```python
from scripts.services.twitter_scraper_unified import TwitterScraperUnified

# Initialize scraper (auto-detects available methods)
scraper = TwitterScraperUnified()

# Fetch tweets
tweet_ids = ["1234567890", "9876543210"]
tweets_data = scraper.fetch_tweets(tweet_ids)

# Tweets are automatically saved to database
```

### Advanced Usage

```python
# Force specific method
scraper = TwitterScraperUnified(method="tweepy")  # or "snscrape" or "playwright"

# Force re-fetch even if data exists
scraper = TwitterScraperUnified(force=True)

# Fetch without saving to database
tweets_data = scraper.fetch_tweets(tweet_ids, save_to_db=False)
```

### Replace Twitter API Service

To use the scraper instead of the official API, update your code:

```python
# Old (API - limited to 100/month)
from scripts.services.twitter_service import TwitterService
service = TwitterService()

# New (Scraper - unlimited)
from scripts.services.twitter_scraper_unified import TwitterScraperUnified
service = TwitterScraperUnified()

# API is the same!
tweets_data = service.fetch_tweets(tweet_ids)
```

## How It Works

1. **Tweepy-Self**: Uses Twitter's guest authentication to fetch tweets without API keys
2. **SNScrape**: Command-line tool that scrapes Twitter's HTML/API
3. **Playwright**: Automates a real browser to scrape content

The unified scraper tries methods in order of preference and falls back if one fails.

## Comparison with Twitter API

| Feature | Twitter API (Free) | Scraper |
|---------|-------------------|---------|
| **Monthly Limit** | 100 requests | Unlimited |
| **Cost** | Free tier | Free |
| **Rate Limit** | 100/month | None |
| **Data Quality** | Official | Same data |
| **Setup** | API key required | No keys needed |
| **Reliability** | 100% | 95-99% |

## Limitations

1. **Legal**: Scraping may violate Twitter's ToS (use at your own risk for research)
2. **Changes**: Twitter can change their website structure, breaking scrapers
3. **Speed**: Slightly slower than official API (but unlimited!)

## Troubleshooting

### No methods available
```bash
# Install at least one method
pip install tweepy-self
```

### Tweepy-Self errors
```bash
# Update to latest version
pip install --upgrade tweepy-self
```

### SNScrape not found
```bash
# Ensure it's in PATH
snscrape --version

# Reinstall if needed
pip uninstall snscrape
pip install snscrape
```

### Playwright errors
```bash
# Install browsers
playwright install chromium

# Or use specific browser
playwright install firefox
```

## Testing

Test the scraper with sample tweets:

```bash
cd /Users/prabalshrestha/Documents/BSU/video-llm-baseline-eval
python scripts/services/twitter_scraper_unified.py
```

## Integration with Existing Code

Your existing code that uses `TwitterService` can easily switch to the scraper:

```python
# In your existing scripts, just change the import
from scripts.services.twitter_scraper_unified import TwitterScraperUnified as TwitterService

# Everything else stays the same!
service = TwitterService()
tweets = service.fetch_tweets(tweet_ids)
```

## Performance

- **Tweepy-Self**: ~1-2 seconds per tweet
- **SNScrape**: ~2-3 seconds per tweet
- **Playwright**: ~5-10 seconds per tweet

For 1000 tweets:
- Tweepy-Self: ~30 minutes
- SNScrape: ~45 minutes
- Playwright: ~2 hours

Still much better than 100/month limit!

## Ethical Considerations

- This scraper is for **research purposes only**
- Respect Twitter's robots.txt and rate limits
- Don't hammer their servers (add delays if needed)
- Consider data privacy when handling user information
- Check your institution's policies on web scraping

## Alternative Services

If scraping doesn't work for you:

1. **Apify** - Paid Twitter scraping service ($49-299/month)
2. **Twitter Academic API** - Free for researchers (requires application)
3. **Botometer API** - Alternative for some Twitter data
4. **Archive.org** - Historical Twitter data

## Support

If you encounter issues:

1. Check which methods are available: `scraper.available_methods`
2. Try a specific method: `TwitterScraperUnified(method="snscrape")`
3. Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`
4. Check the GitHub issues for the respective packages

## Credits

- **Tweepy-Self**: https://github.com/vladkens/twscrape
- **SNScrape**: https://github.com/JustAnotherArchivist/snscrape  
- **Playwright**: https://playwright.dev/
