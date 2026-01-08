# Video LLM Baseline Evaluation

Evaluating Video Large Language Models for detecting and providing context to potentially misleading video content, inspired by X/Twitter's Community Notes.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run everything (ONE command!)
python main.py pipeline

# Or step by step
python main.py download           # Download Community Notes
python main.py filter             # Filter for videos
python main.py videos --limit 30  # Download videos
python main.py dataset            # Create evaluation dataset ⭐
python main.py status             # Check your data
```

## Database-Powered Pipeline 🔄

**NEW:** All scripts now use PostgreSQL database for efficient data management!

### Benefits

- ✅ **Smart Skip Logic**: Automatically skips already-processed data
- ✅ **No Redundant API Calls**: Saves Twitter API quota
- ✅ **Single Source of Truth**: No CSV sync issues
- ✅ **Easy Querying**: SQL joins across notes, tweets, and videos
- ✅ **Thread-Safe**: Proper session management for parallel processing
- ✅ **Production-Ready**: All critical SQLAlchemy issues resolved

### Quick Setup

```bash
# 1. Install PostgreSQL (if not already installed)
brew install postgresql  # macOS
# or
sudo apt install postgresql  # Linux

# 2. Create database
createdb video_llm_eval

# 3. Set environment variables in .env file
echo 'DATABASE_URL="postgresql://localhost/video_llm_eval"' >> .env

# Optional: Set custom video download path (useful for different drives/servers)
# export VIDEO_DOWNLOAD_PATH='/mnt/external_drive/videos'

# 4. Initialize database
python3 setup_database.py

# 5. Import existing data (if you have CSV exports)
./import_all_data.sh

# 6. Run pipeline (skips existing data automatically)
python scripts/data_processing/identify_video_notes.py
python scripts/data_processing/download_videos.py --limit 50
python scripts/data_processing/create_dataset.py
```

### Import Existing Data

If you have CSV exports from a previous run:

```bash
# Quick import (auto-detects latest files)
./import_all_data.sh

# Or with options
python3 import_from_exports.py --exports-dir data/exports

# Verify import
python3 test_import.py
```

See **[QUICK_START.md](QUICK_START.md)** for 3-command setup or **[DATABASE_IMPORT.md](DATABASE_IMPORT.md)** for detailed import guide.

### Force Options (when needed)

```bash
# Force re-process everything
python scripts/data_processing/identify_video_notes.py --force
python scripts/data_processing/download_videos.py --force
python scripts/data_processing/create_dataset.py --force-api-fetch
```

### Database Schema

**3 Tables:**

1. **`notes`** - All 23 columns from raw Community Notes TSV
2. **`tweets`** - Tweet metadata with individual fields + `raw_api_data` (JSONB)
3. **`media_metadata`** - Video/image metadata from yt-dlp (duration, formats, etc.)

**Key Features:**
- Foreign key relationships via `tweet_id`
- JSONB columns for flexible raw data storage
- Indexed for fast queries
- SQLAlchemy ORM + Alembic migrations

## Project Goal

Evaluate Video LLMs' ability to:

1. Detect misinformation in video content
2. Provide helpful context to viewers
3. Identify AI-generated or manipulated content
4. Prevent cherry-picking by highlighting missing context

## Data Pipeline

```
Community Notes (2.2M) → Media Notes (122K) → Video Notes (~51K) → Videos (20) → Evaluate
```

### Current Status

- ✅ **2,232,084** Community Notes downloaded
- ✅ **122,130** media notes (images + videos)
- ✅ **Accurate video identification** using media type checking (~95-99% accurate)
- ✅ **42** verified video notes (from 100 media notes sample)
- ✅ JSON mappings created (videos ↔ Community Notes)

## Project Structure

```
video-llm-baseline-eval/
├── main.py                          # Single entry point ⭐
│
├── scripts/
│   ├── services/                    # API services (Twitter, etc.)
│   │   └── twitter_service.py
│   │
│   ├── data_processing/
│   │   ├── create_dataset.py        # Creates evaluation dataset
│   │   ├── download_notes.py        # Downloads Community Notes
│   │   ├── download_videos.py       # Downloads videos from tweets
│   │   ├── identify_video_notes.py  # Identifies actual videos (checks media type)
│   │   └── explore_notes.py         # Data exploration utility
│   │
│   └── evaluation/                  # Your LLM evaluation code
│
├── data/
│   ├── raw/                         # Downloaded Community Notes
│   ├── filtered/                    # Filtered video notes
│   ├── videos/                      # Downloaded videos + metadata
│   └── evaluation/                  # 📁 Final dataset
│       ├── dataset.json             # Complete dataset ⭐
│       └── dataset.csv              # Same in CSV format
│
├── models/                          # Data models (Video, Note, etc.)
├── test_setup.py                    # Environment verification
└── README.md
```

## Commands

All commands use `main.py`:

```bash
# Full pipeline (recommended)
python main.py pipeline              # Run all steps

# Individual steps
python main.py download              # Download Community Notes
python main.py filter                # Filter for videos
python main.py videos --limit 30     # Download videos
python main.py dataset               # Create evaluation dataset ⭐
python main.py evaluate              # Evaluate Video LLMs 🎯

# Evaluation options
python main.py evaluate --models gemini,gpt4o    # Both models
python main.py evaluate --models gemini --limit 5  # Gemini only, 5 samples
python main.py evaluate --models gpt4o --limit 3   # GPT-4o only, 3 samples

# Utilities
python main.py status                # Show data summary
python main.py explore               # Explore data
python main.py test                  # Test setup
python main.py help                  # Show all commands
```

**Note:** `dataset` command automatically uses Twitter API if credentials are in `.env`

## Data Models

Simple dataclasses for clean code:

```python
from models import Video, CommunityNote, VideoNoteMapping

# Load and work with data
video = Video(filename="video.mp4", tweet_id="123", duration_seconds=45)
print(video.duration_formatted)  # "0:45"
print(video.exists)              # True/False
```

## Data Files

### Filtered Data (`data/filtered/`)

- **media_notes.csv** - 122K notes about media (images + videos)
- **verified_video_notes.csv** - Actual video notes (media type checked, ~95-99% accurate)
- **media_type_check_results.json** - Detailed check results

### Videos (`data/videos/`)

- **video\_\*.mp4** - Downloaded videos
- **video\_\*.info.json** - Video metadata files

### Evaluation Data (`data/evaluation/`) 📁

- **dataset.json** - Your complete evaluation dataset ⭐
- **dataset.csv** - Same data in CSV format

## Database Details

### Schema

**`notes` Table (23 columns):**
- All raw columns from Community Notes TSV
- Indexed on `tweet_id`, `is_media_note`
- ~2.5M+ rows from Community Notes dataset

**`tweets` Table:**
- Individual fields: `tweet_id`, `text`, `author_*`, `likes`, `retweets`, etc.
- `raw_api_data` (JSONB): Complete Twitter API response for full data preservation
- Indexed on `tweet_id` (primary key)

**`media_metadata` Table:**
- Scraped metadata from yt-dlp for all media notes (videos and images)
- Fields: `media_id`, `media_type`, `title`, `description`, `uploader`, `duration_ms`, `width`, `height`, `formats` (JSONB), `local_path`
- Links via `tweet_id` foreign key

### Query Examples

```python
from database import get_session
from database.models import Note, Tweet, MediaMetadata

# Get all video notes with tweet data
with get_session() as session:
    videos = session.query(Note, Tweet, MediaMetadata).join(
        Tweet, Note.tweet_id == Tweet.tweet_id
    ).join(
        MediaMetadata, Note.tweet_id == MediaMetadata.tweet_id
    ).filter(MediaMetadata.media_type == 'video').all()

# Get engagement stats
from database.queries import get_engagement_stats
with get_session() as session:
    stats = get_engagement_stats(session)
    print(stats)
```

### Configuration Options

**Custom Video Download Path:**

By default, videos are downloaded to `data/videos/`. To store videos on a different drive or location (useful for servers with limited space), set the `VIDEO_DOWNLOAD_PATH` environment variable:

```bash
# In your .env file:
VIDEO_DOWNLOAD_PATH=/mnt/external_drive/videos

# Or export directly:
export VIDEO_DOWNLOAD_PATH=/mnt/external_drive/videos

# Then run download script normally:
python scripts/data_processing/download_videos.py --limit 50
```

**Benefits:**
- Store videos on external drive with more space
- Use network-attached storage (NAS)
- Separate data and video storage on servers
- Easily switch between different storage locations

**Note:** The path will be created automatically if it doesn't exist. Make sure you have write permissions for the specified path.

### Troubleshooting

**Connection Issues:**
```bash
# Check PostgreSQL is running
pg_ctl status

# Start PostgreSQL
brew services start postgresql  # macOS
sudo service postgresql start   # Linux
```

**Import Errors:**
```bash
# Re-import data
python setup_database.py --import-notes --import-tweets
```

**Video Download Path Issues:**
```bash
# Check if path exists and is writable
mkdir -p /your/custom/path
chmod u+w /your/custom/path

# Test with absolute path
export VIDEO_DOWNLOAD_PATH=/absolute/path/to/videos
python scripts/data_processing/download_videos.py --limit 1
```

See [`database/README.md`](database/README.md) for more examples and helper functions.

## Dataset Structure

The dataset includes **all necessary fields** for evaluation:

✅ **Video Information**: filename, path, duration, title, uploader
✅ **Tweet Details**: tweet ID, URL, **tweet text/content**, author info, engagement metrics  
✅ **Community Notes**: note ID, classification, **human explanation**, misleading reasons

### Creating the Dataset

**One simple command:**

```bash
python main.py dataset
```

This automatically:

- ✅ Loads videos and community notes
- ✅ Fetches tweet data (if Twitter API available)
- ✅ Falls back to video metadata (if no API)
- ✅ Creates complete dataset in one file

### Output

```
data/evaluation/
  ├── dataset.json    # Complete dataset ⭐
  └── dataset.csv     # Same in CSV format
```

### Sample Entry

```json
{
  "video": {
    "filename": "video_003.mp4",
    "duration_seconds": 35.8,
    "path": "data/videos/video_003.mp4"
  },
  "tweet": {
    "tweet_id": "1882510502200508633",
    "text": "The President of Chile showed Speed something crazy😭",
    "author_name": "Username",
    "engagement": { "likes": 15000, "retweets": 3200 }
  },
  "community_note": {
    "note_id": "1882595996980347228",
    "summary": "The president of Chile is Gabriel Boric Font...",
    "is_misleading": true
  },
  "metadata": {
    "sample_id": "video_003",
    "has_api_data": true
  }
}
```

### Complete Field Reference

**Video Fields:**

- `filename`, `index`, `duration_seconds`, `path`, `title`, `uploader`

**Tweet Fields:**

- `tweet_id`, `url`, `text` (content), `author_name`, `author_username`
- `engagement`: `likes`, `retweets`, `replies`, `views`

**Community Note Fields:**

- `note_id`, `classification`, `summary` (fact-check explanation)
- `is_misleading` (boolean), `created_at_millis`
- `reasons`: `factual_error`, `manipulated_media`, `missing_context`, etc.

**Metadata:**

- `sample_id`, `has_api_data`, `created_at`

## Filtering Method

### Accurate Media Type Checking (Current)

Uses `yt-dlp` to download metadata and checks `_type` field. ~95-99% accurate.

- ✅ Highly accurate - checks actual media type
- ✅ No API credentials needed
- ✅ No false positives from keyword matching
- ✅ Parallel processing for efficiency

**How it works:**

1. Downloads only metadata (info.json) for each media note
2. Checks the `_type` field from Twitter's actual media data
3. Keeps only notes where `_type == "video"`

**Usage:**

```bash
# Test with 100 notes
python main.py filter --sample 100

# Process all media notes
python main.py filter
```

## Video LLMs Implemented

### Commercial (Implemented ✅)

- **Gemini 1.5 Pro** (Google) - Best for long videos, 2M token context window
- **GPT-4o** (OpenAI) - Excellent for short clips with OCR-heavy content

### Future Models

- Claude 3.5 Sonnet (Anthropic)
- Qwen2.5-VL
- Open source models (LLaVA, Video-LLaMA)

## Evaluation

### Setup

1. **Install evaluation dependencies:**

```bash
pip install -r requirements.txt
```

2. **Configure environment variables:**
   Create a `.env` file in the project root:

```bash
# Database (required for database-powered pipeline)
DATABASE_URL=postgresql://localhost/video_llm_eval

# Video Download Path (optional - useful for storing videos on external drive/server)
# If not set, defaults to data/videos/
# VIDEO_DOWNLOAD_PATH=/mnt/external_drive/videos

# Twitter API (optional - for fetching tweet data)
# TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here

# LLM API Keys (required for evaluation)
# Get Gemini API key at: https://ai.google.dev/
GEMINI_API_KEY=your_gemini_api_key_here

# Get OpenAI API key at: https://platform.openai.com/
OPENAI_API_KEY=your_openai_api_key_here
```

3. **Test setup:**

```bash
python scripts/evaluation/test_evaluation_setup.py
```

### Running Evaluation

**Quick start:**

```bash
# Evaluate with both models on all videos
python main.py evaluate

# Evaluate with specific model on limited samples
python main.py evaluate --models gemini --limit 5
python main.py evaluate --models gpt4o --limit 3

# Evaluate with both models
python main.py evaluate --models gemini,gpt4o
```

### Output

The evaluation generates:

- **`llm_results_{timestamp}.json`** - Complete results with all metrics
- **`evaluation_summary_{timestamp}.txt`** - Human-readable summary report

### Models Available

1. **Gemini 1.5 Pro** - Best for long videos, native audio-visual understanding
2. **GPT-4o** - Excellent for short clips with text/chart content

### Metrics

The evaluation compares LLM outputs with human Community Notes using:

- **ROUGE scores** - Text overlap (ROUGE-1, ROUGE-2, ROUGE-L)
- **BLEU score** - Precision-focused similarity
- **Semantic similarity** - Meaning-based comparison using embeddings
- **Classification accuracy** - Correct identification of misleading content
- **Reason overlap** - Precision/recall for misinformation categories

## Next Steps

1. ✅ **Create dataset** - `python main.py dataset`
2. ✅ **Setup evaluation** - Configure API keys
3. ✅ **Run evaluation** - `python main.py evaluate`
4. **Analyze results** - Compare LLM outputs with human notes
5. **Refine prompts** - Improve accuracy based on findings

## Environment Setup

### Required

```bash
pip install pandas requests numpy python-dotenv yt-dlp
```

### Optional (for LLM evaluation)

```bash
pip install openai anthropic google-generativeai
```

### Twitter API (optional, for exact video identification)

Create `.env` file:

```
TWITTER_BEARER_TOKEN=your_token
```

Apply for API: https://developer.twitter.com

## Resources

## How It Works

### 1. Download Community Notes

```bash
python main.py download
```

Downloads latest Community Notes data from Twitter/X public dataset (~2.2M notes).
Filters for media notes (images + videos).

### 2. Identify Video Notes

```bash
python main.py filter
```

Identifies actual videos by checking media type from Twitter metadata (~51K video notes expected).
Uses `yt-dlp` to download metadata only (not video files) and checks the `_type` field.
**Accuracy:** ~95-99% - much more accurate than keyword-based filtering.

### 3. Download Videos

```bash
python main.py videos --limit 30
```

Downloads videos from tweets using `yt-dlp`. Saves:

- `video_XXX.mp4` - The video file
- `video_XXX.info.json` - Video metadata (author, engagement, etc.)

### 4. Create Dataset

```bash
python main.py dataset
```

Creates complete evaluation dataset by:

1. Loading videos and community notes
2. Fetching tweet data (if Twitter API available)
3. Combining everything into one unified structure
4. Saving as JSON and CSV

**Output:** `data/evaluation/dataset.json` ⭐

### Using Twitter API (Optional)

For complete tweet data (text, author, engagement):

1. Get API credentials: https://developer.twitter.com
2. Add to `.env` file:
   ```
   TWITTER_BEARER_TOKEN=your_token_here
   ```
3. Run `python main.py dataset` - automatically uses API!

Without API: Uses video metadata (limited info).

## External Resources

- **Community Notes Guide**: https://communitynotes.x.com/guide/en/about/introduction
- **Data Download**: https://communitynotes.x.com/guide/en/under-the-hood/download-data
- **Research Paper**: https://arxiv.org/abs/2403.11169
- **Twitter API**: https://developer.twitter.com

## Research Timeline

- **Week 1-2**: ✅ Data collection complete
- **Week 3-4**: LLM setup and initial testing
- **Week 5-6**: Full evaluation
- **Week 7-8**: Analysis and reporting

## Key Features

- ✅ Single entry point (`main.py`)
- ✅ Clean data models
- ✅ 20 videos with Community Notes
- ✅ JSON mappings for evaluation
- ✅ Ready for LLM testing

## License

Research use only. Respect Twitter's ToS and Community Notes data usage policies.

---

**Quick Commands**

- `python main.py pipeline` - Run data collection
- `python main.py dataset` - Create evaluation dataset ⭐
- `python main.py evaluate` - Evaluate Video LLMs 🎯
- `python main.py status` - Check data
- `python main.py help` - Show commands

**Complete Workflow:** `download` → `filter` → `videos` → `dataset` → `evaluate` → analyze!
