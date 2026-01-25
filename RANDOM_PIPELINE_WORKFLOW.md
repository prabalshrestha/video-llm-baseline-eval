# Random Pipeline Workflow

## Overview

The `random_sample_pipeline.py` is designed to create datasets while respecting Twitter API rate limits. If you request `--limit 100`, it aims to make exactly 100 API calls (one per tweet), not more.

## New Workflow (January 2026)

### Goal: Get 100 video tweets with 100 API calls

```bash
python main.py random --limit 100 --status CURRENTLY_RATED_HELPFUL
```

### Step-by-Step Process

#### Step 1: Sample Tweets WITHOUT API Data
- Queries database for tweets with matching note status
- **Filters out tweets that already have `raw_api_data`** (we want fresh ones only)
- Samples randomly using PostgreSQL's `random()` with seed
- May need multiple sampling attempts to find enough video tweets

#### Step 2: Identify Video Tweets (Metadata Check)
- Uses `yt-dlp --skip-download --write-info-json` to check each tweet
- Creates `media_metadata` entries for tweets that have videos
- Returns list of tweet IDs that actually contain videos
- **No API calls made yet!**

**Resampling Loop:**
- If we need 100 video tweets but only found 50, resample again
- Keep collecting until we have 100 tweets that contain videos
- Maximum 10 sampling attempts to prevent infinite loops

#### Step 3: Download Videos
- Downloads actual video files for the 100 video tweets
- Uses existing `download_videos.py` script
- Saves to `data/videos/` directory

#### Step 4: Call Twitter API
- **Makes exactly 100 API calls** (one per video tweet)
- Fetches full tweet data (text, author, metrics, lang, referenced_tweets)
- Saves `raw_api_data` to database
- This is where we hit the monthly rate limit

#### Step 5: Create Dataset
- Filters for original (non-RT/reply) tweets
- Filters for English tweets
- Filters for tweets with notes matching status
- **It's fine if some tweets get filtered out here**
- Creates timestamped dataset: `dataset_YYYYMMDD_HHMMSS.json`

## Key Benefits

### 1. API Rate Limit Respect
- If you set `--limit 100`, makes ~100 API calls (not 200+ like before)
- API calls happen AFTER confirming tweets have videos
- No wasted API calls on non-video tweets

### 2. Fresh Data Only
- Only samples tweets WITHOUT existing `raw_api_data`
- Ensures you're always getting new tweets
- Prevents processing same tweets repeatedly

### 3. Guaranteed Video Content
- Metadata check happens BEFORE API calls
- Only fetches API data for tweets with confirmed videos
- No API calls wasted on tweets without videos

### 4. Resampling Logic
- Automatically resamples if not enough video tweets found
- Keeps trying until target is met (up to 10 attempts)
- Progress logging shows how many video tweets collected

## Example Output

```
[Sampling Attempt 1] Need 100 more video tweets
✓ Sampled 1000 candidate tweets (without API data)
✓ Found 45 tweets with videos
Progress: 45/100 video tweets collected

[Sampling Attempt 2] Need 55 more video tweets
✓ Sampled 1000 candidate tweets (without API data)
✓ Found 38 tweets with videos
Progress: 83/100 video tweets collected

[Sampling Attempt 3] Need 17 more video tweets
✓ Sampled 1000 candidate tweets (without API data)
✓ Found 25 tweets with videos
Progress: 100/100 video tweets collected (trimmed to exact limit)

✓ Downloaded 100 videos
✓ Fetched API data for 100 tweets (100 API calls made)
✓ Created dataset with 78 tweets
   (22 filtered out: 15 non-original, 7 non-English)
```

## Final Dataset Size

The final dataset **may have fewer than 100 tweets** because:
- Some tweets are retweets or replies (filtered out)
- Some tweets are not in English (filtered out)
- This is expected and acceptable

But you will have made **exactly 100 API calls**, which respects your monthly rate limit.

## Usage Options

```bash
# Basic: 100 video tweets, auto-generated seed
python main.py random --limit 100

# Reproducible: specific seed
python main.py random --limit 100 --seed 42

# Force re-download existing videos
python main.py random --limit 50 --force

# Different note status
python main.py random --limit 100 --status NEEDS_MORE_RATINGS
```

## Old vs New Workflow

### Old Workflow (Problem)
1. Sample 100 tweets → 2. Call API (100 calls) → 3. Filter original/English (50 left) → 4. Identify videos (25 have videos) → 5. Download → 6. Dataset has 25 tweets
- **Problem:** Made 100 API calls but only got 25 video tweets

### New Workflow (Solution)
1. Sample tweets without API data → 2. Identify videos (resample until 100) → 3. Download 100 videos → 4. Call API (100 calls) → 5. Filter/create dataset (78 final)
- **Benefit:** Made 100 API calls and got 100 video tweets (78 passed filters)

## Configuration

- `--limit`: Target number of video tweets (will make ~this many API calls)
- `--seed`: Random seed for reproducibility (default: timestamp-based)
- `--status`: Note status filter (default: `CURRENTLY_RATED_HELPFUL`)
- `--force`: Force re-download even if video exists

## Technical Details

- Uses PostgreSQL's `setseed()` for database-level randomization
- Samples 10x the limit initially to increase chances of finding videos
- Metadata check uses `yt-dlp` (no API calls)
- API fetch uses `TwitterService` (respects existing data, won't re-fetch)
- Dataset creation includes all standard filters
