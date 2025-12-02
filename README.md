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

## Project Goal

Evaluate Video LLMs' ability to:

1. Detect misinformation in video content
2. Provide helpful context to viewers
3. Identify AI-generated or manipulated content
4. Prevent cherry-picking by highlighting missing context

## Data Pipeline

```
Community Notes (2.2M) → Media Notes (122K) → Video Notes (27K) → Videos (20) → Evaluate
```

### Current Status

- ✅ **2,232,084** Community Notes downloaded
- ✅ **122,130** media notes (images + videos)
- ✅ **26,952** likely video notes (heuristic filter ~70% accurate)
- ✅ **20** sample videos downloaded
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
│   │   ├── filter_video_notes.py    # Filters notes for videos
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
- **likely_video_notes.csv** - 27K likely video notes (keyword filter)
- **filtering_report.txt** - Statistics

### Videos (`data/videos/`)

- **video\_\*.mp4** - Downloaded videos
- **video\_\*.info.json** - Video metadata files

### Evaluation Data (`data/evaluation/`) 📁

- **dataset.json** - Your complete evaluation dataset ⭐
- **dataset.csv** - Same data in CSV format

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

## Filtering Methods

### Method 1: Heuristic (Current)

Uses `isMediaNote` flag + keyword matching. ~70% accurate.

- ✅ Works immediately, no API needed
- ⚠️ May include false positives

### Method 2: Twitter API (Exact)

Requires Twitter API credentials. 100% accurate.

- ✅ Exact video identification
- ✅ Get video URLs and metadata
- ⏳ Requires API approval

## Video LLMs to Evaluate

### Commercial

- GPT-4 Vision (OpenAI)
- Claude 3 (Anthropic)
- Gemini Pro Vision (Google)

### Open Source

- LLaVA
- Video-LLaMA
- VideoChat

## Next Steps

1. **Create dataset** - `python main.py dataset`
2. **Test manually** - Try GPT-4V on 1-2 videos
3. **Add LLM code** - Create scripts in `scripts/evaluation/`
4. **Compare results** - LLM output vs human notes
5. **Analyze patterns** - What works, what doesn't

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

### 2. Filter for Videos

```bash
python main.py filter
```

Uses heuristic filtering (keywords, patterns) to identify likely video notes (~27K notes).
**Note:** For 100% accuracy, use Twitter API (see below).

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

- `python main.py pipeline` - Run everything
- `python main.py dataset` - Create evaluation dataset ⭐
- `python main.py status` - Check data
- `python main.py help` - Show commands

**Questions?** The workflow is: `download` → `filter` → `videos` → `dataset` → evaluate!
