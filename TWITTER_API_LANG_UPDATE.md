# Twitter API Lang Field Update

## Overview

The Twitter API service has been updated to request the `lang` (language) and `referenced_tweets` fields from the Twitter API. This enables better filtering of tweets by language and identification of retweets/replies.

## Changes Made

### 1. Updated Twitter Service (`scripts/services/twitter_service.py`)

**Added fields to API request:**
- `lang` - Language code for the tweet (e.g., "en", "es", "fr")
- `referenced_tweets` - Information about referenced tweets (for identifying retweets and replies)

**Updated lines:**
- Line 118: Added `lang,referenced_tweets` to `tweet.fields` parameter
- Lines 155-156: Added `lang` and `referenced_tweets` to the tweet_data dictionary

### 2. Created Re-fetch Script (`scripts/data_processing/refetch_tweets_for_lang.py`)

A new script to update existing tweets that were fetched before the `lang` field was added.

**Features:**
- Identifies tweets with `raw_api_data` but missing the `lang` field
- Re-fetches these tweets from the Twitter API
- Updates the database with complete data including `lang`
- Supports dry-run mode to preview changes
- Shows verification statistics before and after

## Usage

### For New Tweets

All new tweets fetched through `TwitterService` will automatically include the `lang` and `referenced_tweets` fields.

```bash
# The standard pipeline now includes lang automatically
python3 scripts/data_processing/identify_video_notes.py
python3 scripts/data_processing/create_dataset.py --force-api-fetch
```

### For Existing Tweets

Use the refetch script to update tweets that were fetched before this change:

```bash
# Check how many tweets need updating (no API calls)
python3 scripts/data_processing/refetch_tweets_for_lang.py --verify-only

# Preview what would be done (no API calls)
python3 scripts/data_processing/refetch_tweets_for_lang.py --dry-run

# Actually re-fetch the tweets (makes API calls)
python3 scripts/data_processing/refetch_tweets_for_lang.py

# Custom batch size (default is 100)
python3 scripts/data_processing/refetch_tweets_for_lang.py --batch-size 50
```

**Important:** The refetch script requires your Twitter API credentials (`TWITTER_BEARER_TOKEN` in `.env`).

## How Language Filtering Works

The `create_dataset.py` script uses the `is_english_tweet()` method to filter tweets:

1. Checks `raw_api_data` for the `lang` field
2. Looks in both root level and nested `data` object
3. Returns `True` if `lang == "en"`
4. If no `lang` field found, defaults to `True` (assumes English)

## Data Structure

The `lang` field is stored in the `raw_api_data` JSONB column:

```json
{
  "tweet_id": "1234567890",
  "text": "Sample tweet",
  "lang": "en",
  "referenced_tweets": [
    {
      "type": "replied_to",
      "id": "1234567889"
    }
  ],
  "author_id": "...",
  ...
}
```

## Benefits

1. **Accurate Language Filtering**: Filter tweets by language with confidence
2. **Better Original Tweet Detection**: Use `referenced_tweets` to identify retweets and replies
3. **Dataset Quality**: Ensures dataset contains only English original tweets as required
4. **Backwards Compatible**: Script handles both old and new data formats

## Server Deployment

After deploying code to the server:

```bash
# SSH to server
ssh prabalshrestha@eng402924
cd ~/video-llm-baseline-eval

# Activate virtual environment
source venv/bin/activate

# Check current state
python3 scripts/data_processing/refetch_tweets_for_lang.py --verify-only

# Re-fetch tweets (if needed)
python3 scripts/data_processing/refetch_tweets_for_lang.py

# Re-create dataset with proper language filtering
python3 scripts/data_processing/create_dataset.py
```

## Troubleshooting

### "Twitter API credentials not available"
- Ensure `TWITTER_BEARER_TOKEN` is set in your `.env` file
- Verify the token has not expired

### "Rate limit reached"
- The script automatically waits 15 minutes when rate limited
- Consider using smaller `--batch-size` to stay under rate limits
- Twitter API free tier: 500,000 tweets/month

### "No tweets to re-fetch"
- All tweets already have the `lang` field
- Run with `--verify-only` to check current state

## Statistics

After running the refetch script, you should see:

```
Total tweets with API data: X
Tweets with lang field: Y
Tweets missing lang field: Z
Completion: 100.0%
```

This ensures all tweets have complete language information for accurate filtering.

