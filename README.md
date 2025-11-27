# Video LLM Baseline Evaluation for Misinformation Detection

Evaluating Video Large Language Models (LLMs) for detecting and providing context to potentially misleading video content, inspired by X/Twitter's Community Notes system.

## Quick Start

```bash
# 1. Install dependencies
pip install pandas requests numpy python-dotenv

# 2. Download Community Notes data
python download_filter_community_notes.py

# 3. Explore the data
python explore_data.py

# 4. Get tweet/video data (requires Twitter API)
python fetch_tweet_data.py
```

## Project Goal

Build a baseline evaluation of Video LLMs' ability to:
1. **Detect misinformation** in video content
2. **Provide context** to help viewers understand the full picture
3. **Identify AI-generated** or manipulated content
4. **Prevent cherry-picking** by highlighting missing context

## Current Status

✅ **Downloaded**: 2,232,084 Community Notes  
🔄 **Filtering**: Need to identify notes where parent tweet contains video  
📋 **Next**: Fetch actual tweet/video data using Twitter API  

## Data Collection

### What We Have
- **Community Notes** (notes-00000.tsv): 2.2M notes with `tweetId`, `summary`, `classification`, `isMediaNote`
- **Note Status** (noteStatusHistory-00000.tsv): Status progression of notes

### What We Need
- **Tweet data**: Actual tweet content and media information
- **Video URLs**: Direct links to videos from tweets
- **Media metadata**: Video duration, format, etc.

### The Challenge

Community Notes dataset only provides `tweetId` - it doesn't include:
- Tweet text
- Media URLs (video links)
- Media type information

**Solution**: Use Twitter API v2 to fetch tweet data using the `tweetId` values.

## Data Pipeline

```
Community Notes → Filter by isMediaNote → Get tweetIds → 
→ Twitter API → Check for video → Download videos → Evaluate with LLMs
```

### Step 1: Filter Community Notes (Done)
```python
# Filter notes that are about media content
media_notes = notes_df[notes_df['isMediaNote'] == 1]
```

### Step 2: Fetch Tweet Data (TODO)
Requires Twitter API v2 credentials:
- Get tweet details using tweetIds
- Check if tweet has video media
- Extract video URLs

### Step 3: Download Videos (TODO)
- Use video URLs from tweet data
- Download to `data/videos/`
- Store metadata

### Step 4: Evaluate with Video LLMs (TODO)
- Test multiple LLMs (GPT-4V, Claude 3, Gemini, etc.)
- Compare LLM outputs with human notes
- Analyze strengths/weaknesses

## Project Structure

```
video-llm-baseline-eval/
├── data/
│   ├── raw/                    # Raw Community Notes data
│   ├── filtered/               # Filtered media notes
│   └── videos/                 # Downloaded videos
├── scripts/                    # Analysis scripts
├── notebooks/                  # Jupyter notebooks
├── results/                    # Evaluation results
├── download_filter_community_notes.py  # Download & filter
├── fetch_tweet_data.py         # Get tweet/video data (TODO)
├── evaluate_llms.py            # Run LLM evaluation (TODO)
└── README.md                   # This file
```

## Setup

### 1. Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install packages
pip install -r requirements.txt
```

### 2. Twitter API Setup (Required for video data)

1. Apply for Twitter Developer account: https://developer.twitter.com
2. Create a project and get API credentials
3. Add to `.env` file:

```bash
# .env
TWITTER_API_KEY=your_key
TWITTER_API_SECRET=your_secret
TWITTER_ACCESS_TOKEN=your_token
TWITTER_ACCESS_SECRET=your_access_secret
TWITTER_BEARER_TOKEN=your_bearer_token
```

### 3. LLM API Setup (For evaluation)

```bash
# .env
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
```

## Scripts

### `download_filter_community_notes.py`
Downloads Community Notes data and filters for media notes.

**Usage**:
```bash
python download_filter_community_notes.py
```

**Output**:
- `data/raw/notes-00000.tsv` - All notes
- `data/filtered/media_notes.csv` - Filtered media notes
- `data/filtered/filtering_report.txt` - Statistics

### `fetch_tweet_data.py` (TODO)
Fetches tweet data using Twitter API to identify which tweets have videos.

**Usage**:
```bash
python fetch_tweet_data.py
```

**What it does**:
1. Reads filtered media notes
2. Extracts unique tweetIds
3. Calls Twitter API v2 to get tweet details
4. Filters tweets that contain video
5. Saves video URLs and metadata

### `explore_data.py`
Analyzes the downloaded data.

**Usage**:
```bash
python explore_data.py
```

## Video LLMs to Evaluate

### Commercial
1. **GPT-4 Vision** (OpenAI) - Image/video understanding
2. **Claude 3** (Anthropic) - Multi-modal analysis
3. **Gemini Pro Vision** (Google) - Video understanding

### Open Source
4. **LLaVA** - Image+text understanding
5. **Video-LLaMA** - Video-specific LLM
6. **VideoChat** - Video conversation

## Evaluation Methodology

### 1. Input
- Video from tweet
- Video transcript (if available)
- Key frames
- Social context (engagement, comments)

### 2. Prompt
```
Analyze this video that was shared on social media.

1. What is shown in the video?
2. Is there anything misleading about how this video is presented?
3. What context would help viewers understand this better?
4. Is this likely AI-generated or manipulated?
```

### 3. Compare
- LLM output vs Human Community Note
- Accuracy, completeness, helpfulness

### 4. Metrics
- **Detection accuracy**: Correctly identifies misleading content
- **Context coverage**: Mentions same context points as humans
- **False positive rate**: Incorrectly flags legitimate content
- **Helpfulness**: Qualitative rating of usefulness

## Research Timeline

- **Week 1-2**: ✅ Data collection + 🔄 Twitter API integration
- **Week 3-4**: Video download + LLM API setup
- **Week 5-6**: Initial LLM testing (10-20 samples)
- **Week 7-8**: Full evaluation (100+ samples)
- **Week 9-10**: Analysis and reporting

## Key Research Questions

1. Can Video LLMs detect the same misinformation issues that humans identify?
2. What types of video misinformation are hardest for LLMs to detect?
3. How do LLM-generated notes compare to human-written Community Notes?
4. What capabilities are LLMs missing for video fact-checking?

## Current Challenges

### 1. Tweet/Video Access
- **Issue**: Community Notes data doesn't include tweet content or media URLs
- **Solution**: Use Twitter API v2 to fetch tweet data
- **Status**: Need to implement `fetch_tweet_data.py`

### 2. Video Availability
- **Issue**: Some tweets may be deleted or private
- **Solution**: Track success rate, work with available subset
- **Status**: TBD after Twitter API integration

### 3. Rate Limits
- **Issue**: Twitter API has rate limits
- **Solution**: Batch requests, add delays, cache results
- **Status**: Will implement in fetch script

## Next Steps

### Immediate (This Week)
1. **Get Twitter API access** - Apply for developer account
2. **Implement tweet fetching** - Create `fetch_tweet_data.py`
3. **Test with sample** - Try fetching 10-20 tweet details
4. **Verify video presence** - Check how many tweets still have videos

### Short-term (Next 2 Weeks)
5. **Download sample videos** - Get 50-100 videos for testing
6. **Set up LLM APIs** - Get OpenAI, Anthropic, Google credentials
7. **Design prompts** - Create evaluation prompts
8. **Initial testing** - Test 1-2 LLMs on 10 videos

## Resources

- **Community Notes Guide**: https://communitynotes.x.com/guide/en/about/introduction
- **Data Download**: https://communitynotes.x.com/guide/en/under-the-hood/download-data
- **Twitter API v2**: https://developer.twitter.com/en/docs/twitter-api
- **Research Paper**: https://arxiv.org/abs/2403.11169

## Contributing

This is a research project. Key areas:
- Twitter API integration
- Video download pipeline
- LLM evaluation framework
- Analysis and metrics

## License

Research use only. Respect Twitter's ToS and Community Notes data usage policies.

## Contact

**Researcher**: Prabal  
**Institution**: BSU  
**Project Start**: November 20, 2025
