# Video LLM Baseline Evaluation

Evaluating Video Large Language Models for detecting and providing context to potentially misleading video content, inspired by X/Twitter's Community Notes.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment variables (required for evaluation)
cp env.template .env
# Edit .env and add your API keys

# 3. Set up database
python setup_database.py

# 4. Quick random sample (RECOMMENDED for quick start!)
python main.py random --limit 30

# Or run full pipeline
python main.py pipeline

# Or step by step
python main.py download           # Download Community Notes
python main.py filter             # Filter for videos
python main.py videos --limit 30  # Download videos
python main.py dataset            # Create evaluation dataset
python main.py status             # Check your data
```

## Database-Powered Pipeline

All scripts use PostgreSQL database for efficient data management!

### Benefits

- ✅ **Smart Skip Logic**: Automatically skips already-processed data
- ✅ **No Redundant API Calls**: Saves Twitter API quota
- ✅ **Single Source of Truth**: No CSV sync issues
- ✅ **Easy Querying**: SQL joins across notes, tweets, and videos
- ✅ **Thread-Safe**: Proper session management for parallel processing

### Database Setup

```bash
# 1. Install PostgreSQL (if not already installed)
brew install postgresql  # macOS
# or
sudo apt install postgresql  # Linux

# 2. Create database
createdb video_llm_eval

# 3. Set environment variables in .env file
echo 'DATABASE_URL="postgresql://localhost/video_llm_eval"' >> .env

# 4. Initialize database
python setup_database.py

# 5. Run pipeline (skips existing data automatically)
python main.py pipeline
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

### Advanced Options

**Random Sampling** (for diversity):

```bash
# Download videos with random sampling
python scripts/data_processing/download_videos.py --limit 50 --random --seed 42

# Create dataset with random sampling
python scripts/data_processing/create_dataset.py --sample-size 100 --random-seed 42
```

**Force Re-processing** (when needed):

```bash
python scripts/data_processing/identify_video_notes.py --force
python scripts/data_processing/download_videos.py --force
python scripts/data_processing/create_dataset.py --force-api-fetch
```

**Custom Video Download Path:**

```bash
# In your .env file:
VIDEO_DOWNLOAD_PATH=/mnt/external_drive/videos
```

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
# Quick random sample (RECOMMENDED) 🎲
python main.py random --limit 30        # Random sample helpful videos
python main.py random --limit 50 --seed 42  # Reproducible sampling

# Full pipeline
python main.py pipeline                 # Run all steps (sequential)
python main.py pipeline --random        # Run with random video sampling
python main.py pipeline --limit 50 --random --seed 42  # Custom config

# Individual steps
python main.py download                 # Download Community Notes
python main.py filter                   # Filter for videos
python main.py videos --limit 30        # Download videos (sequential)
python main.py videos --limit 30 --random --seed 42  # Random sampling
python main.py dataset                  # Create evaluation dataset
python main.py dataset --sample-size 100 --seed 42   # With sampling
python main.py evaluate                 # Evaluate Video LLMs

# Evaluation options
python main.py evaluate --models gemini,gpt4o    # Both models
python main.py evaluate --models gemini --limit 5  # Gemini only, 5 samples
python main.py evaluate --models gpt4o --limit 3   # GPT-4o only, 3 samples

# Utilities
python main.py status                   # Show data summary
python main.py explore                  # Explore data
python main.py test                     # Test setup
python main.py help                     # Show all commands
```

**Note:** `dataset` command automatically uses Twitter API if credentials are in `.env`

## Random Sample Command (Quick Start)

The `random` command is the **fastest way** to create a diverse evaluation dataset:

```bash
# Sample 30 random videos from CURRENTLY_RATED_HELPFUL notes (default)
python main.py random --limit 30

# Sample 50 videos with reproducible seed
python main.py random --limit 50 --seed 42

# Sample from different note statuses
python main.py random --limit 20 --status NEEDS_MORE_RATINGS
python main.py random --limit 40 --status CURRENTLY_RATED_NOT_HELPFUL
```

**What it does:**

1. Randomly samples tweets with notes of specified status (default: `CURRENTLY_RATED_HELPFUL`)
2. Identifies which tweets contain videos using yt-dlp metadata
3. Downloads the videos
4. Creates the evaluation dataset **with only the matching notes**

**Key Feature:** If you request 100 videos with `--limit 100`, you'll get close to 100 tweets where each tweet has at least one note with the specified status, and the dataset will ONLY include notes matching that status.

**Available Note Statuses:**

- `CURRENTLY_RATED_HELPFUL` - Notes marked as helpful (default)
- `CURRENTLY_RATED_NOT_HELPFUL` - Notes marked as not helpful
- `NEEDS_MORE_RATINGS` - Notes awaiting more ratings

**Benefits:**

- ✅ Maximum randomness using consistent random sampling
- ✅ Filter by note status for targeted datasets
- ✅ Only includes notes matching the filter (no extra notes)
- ✅ Much faster than processing all 122K media notes
- ✅ Reproducible with seed parameter
- ✅ API rate limit friendly - gets ~N tweets for --limit N

## Random Sampling in Pipeline

You can also enable random sampling in the main pipeline:

```bash
# Pipeline with random video sampling
python main.py pipeline --limit 50 --random --seed 42

# Pipeline without random sampling (sequential)
python main.py pipeline --limit 30
```

**Random Sampling Options (available in all commands):**

- `--random`: Enable random video sampling
- `--seed N`: Set random seed (default: 42)
- `--sample-size N`: Sample size for dataset creation

**Example workflows:**

```bash
# Full pipeline with random sampling
python main.py pipeline --limit 50 --random --seed 123

# Individual steps with random sampling
python main.py videos --limit 30 --random --seed 42
python main.py dataset --sample-size 100 --seed 42
python main.py evaluate

# Mix sequential and random
python main.py download
python main.py filter
python main.py videos --limit 50 --random  # Random videos
python main.py dataset                      # All downloaded videos
```

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

### Troubleshooting

**PostgreSQL Connection Issues:**

```bash
# Check PostgreSQL is running
pg_ctl status

# Start PostgreSQL
brew services start postgresql  # macOS
sudo service postgresql start   # Linux
```

**Database Initialization:**

```bash
# Reset and initialize database
dropdb video_llm_eval  # Warning: deletes all data
createdb video_llm_eval
python setup_database.py
```

## Dataset Structure

The dataset includes all necessary fields for evaluation:

- **Video Information**: filename, path, duration, title, uploader
- **Tweet Details**: tweet ID, URL, text/content, author info, engagement metrics
- **Community Notes**: note ID, classification, human explanation, misleading reasons

### Dataset Versioning

**All datasets are timestamped and preserved:**

```
data/evaluation/
  ├── datasets/                      # Historical datasets
  │   ├── dataset_20260123_202013.json
  │   ├── dataset_20260123_202013.csv
  │   ├── dataset_20260124_153045.json
  │   └── dataset_20260124_153045.csv
  └── latest/                        # Symlink to most recent
      ├── dataset.json
      └── dataset.csv
```

**Benefits:**
- ✅ Full history preserved
- ✅ Reproducible experiments
- ✅ Easy to compare different runs
- ✅ `latest/` always points to most recent

### Creating the Dataset

```bash
python main.py dataset
```

This automatically loads videos and community notes, fetches tweet data (if Twitter API available), and creates a complete dataset.

**Output:**

```
data/evaluation/
  ├── datasets/dataset_YYYYMMDD_HHMMSS.json  # Timestamped version
  ├── datasets/dataset_YYYYMMDD_HHMMSS.csv
  └── latest/                                # Current version
      ├── dataset.json
      └── dataset.csv
```

## How It Works

### 1. Download Community Notes

```bash
python main.py download
```

Downloads latest Community Notes data from X/Twitter's public dataset (~2.2M notes) and filters for media notes (images + videos).

### 2. Identify Video Notes

```bash
python main.py filter
```

Uses `yt-dlp` to download metadata and checks media type. Highly accurate (~95-99%) with no false positives from keyword matching.

### 3. Download Videos

```bash
python main.py videos --limit 30
```

Downloads videos from tweets using `yt-dlp`. Saves video files (`.mp4`) and metadata (`.info.json`).

### 4. Create Dataset

```bash
python main.py dataset
```

Creates complete evaluation dataset by combining videos, community notes, and tweet data.

## Evaluation

### Setup

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

2. **Configure API keys:**

```bash
cp env.template .env
# Edit .env and add your API keys
```

Get API keys:
- **Gemini**: https://makersuite.google.com/app/apikey
- **OpenAI**: https://platform.openai.com/api-keys

3. **Test setup:**

```bash
python scripts/evaluation/test_evaluation_setup.py
```

### Running Evaluation

```bash
# Evaluate with both models
python main.py evaluate

# Evaluate with specific model
python main.py evaluate --models gemini --limit 5
python main.py evaluate --models gpt4o --limit 3
```

### Models

1. **Gemini 1.5 Pro** - Best for long videos, 2M token context window
2. **GPT-4o** - Excellent for short clips with OCR-heavy content

### Metrics

The evaluation compares LLM outputs with human Community Notes:

- **ROUGE/BLEU scores** - Text similarity
- **Semantic similarity** - Meaning-based comparison using embeddings
- **Classification accuracy** - Correct identification of misleading content
- **Reason overlap** - Precision/recall for misinformation categories

### Output

```
data/evaluation/runs/
  ├── run_YYYYMMDD_HHMMSS/
  │   ├── unified_results.json      # Complete results
  │   ├── summary_report.txt        # Human-readable summary
  │   └── config.json               # Run configuration
  └── latest/                       # Symlink to latest run
```

## Twitter API (Optional)

For complete tweet data (text, author, engagement), add Twitter API credentials to `.env`:

```bash
TWITTER_BEARER_TOKEN=your_token_here
```

Apply for API access: https://developer.twitter.com

Without API: The system falls back to video metadata (limited info).

## Resources

- **Community Notes Guide**: https://communitynotes.x.com/guide/en/about/introduction
- **Data Download**: https://communitynotes.x.com/guide/en/under-the-hood/download-data
- **Research Paper**: https://arxiv.org/abs/2403.11169
- **Twitter API**: https://developer.twitter.com

## Key Commands

```bash
python main.py random       # 🎲 Quick random sample (RECOMMENDED)
python main.py pipeline     # Run complete data collection
python main.py dataset      # Create evaluation dataset
python main.py evaluate     # Evaluate Video LLMs
python main.py status       # Check data status
python main.py help         # Show all commands
```

**Quick Workflows:**

1. **Fast Start (Recommended):** `python main.py random --limit 30` → `python main.py evaluate`
2. **Complete Pipeline:** `download` → `filter` → `videos` → `dataset` → `evaluate`

## License

Research use only. Respect X/Twitter's Terms of Service and Community Notes data usage policies.
