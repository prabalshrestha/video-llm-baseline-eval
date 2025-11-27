# Video LLM Baseline Evaluation

Evaluating Video Large Language Models for detecting and providing context to potentially misleading video content, inspired by X/Twitter's Community Notes.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run everything
python main.py pipeline

# Or step by step
python main.py download         # Download Community Notes
python main.py filter           # Filter for videos
python main.py videos --limit 30  # Download videos
python main.py mapping          # Create mappings
python main.py status           # Check your data
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
├── main.py                    # Single entry point - use this!
│
├── models/                    # Data models
│   ├── note.py               # CommunityNote
│   ├── video.py              # Video
│   └── mapping.py            # VideoNoteMapping
│
├── data/
│   ├── raw/                  # Downloaded data
│   ├── filtered/             # Processed data
│   └── videos/               # Videos + mappings (JSON)
│
├── scripts/
│   ├── data_processing/      # 5 processing scripts
│   └── evaluation/           # Add your LLM eval code here
│
├── download_filter_community_notes.py
├── explore_data.py
├── test_setup.py
├── requirements.txt
└── README.md
```

## Commands

All commands use `main.py`:

```bash
# Full pipeline
python main.py pipeline              # Run all steps

# Individual steps
python main.py download              # Download Community Notes
python main.py filter                # Filter for videos
python main.py videos --limit 30     # Download videos
python main.py mapping               # Create mappings

# Utilities
python main.py status                # Show data summary
python main.py explore               # Explore data
python main.py test                  # Test setup
python main.py help                  # Show all commands
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
- **likely_video_notes.csv** - 27K likely video notes (keyword filter)
- **filtering_report.txt** - Statistics

### Videos (`data/videos/`)

- **video_*.mp4** - Downloaded videos
- **video_notes_mapping.json** - Videos matched with Community Notes ⭐
- **video_notes_simple.json** - Simplified mapping

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

1. **Test manually** - Try GPT-4V on 1-2 videos
2. **Add LLM code** - Create scripts in `scripts/evaluation/`
3. **Compare results** - LLM output vs human notes
4. **Analyze patterns** - What works, what doesn't

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

- **Community Notes Guide**: https://communitynotes.x.com/guide/en/about/introduction
- **Data Download**: https://communitynotes.x.com/guide/en/under-the-hood/download-data
- **Research Paper**: https://arxiv.org/abs/2403.11169

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
- `python main.py status` - Check data
- `python main.py help` - Show commands
