# Project Summary

**Date**: November 26, 2025  
**Status**: Phase 1 Complete ✅ | Phase 2 Ready 🔄

---

## What We Have Now

### ✅ Data Collected

| Metric | Value |
|--------|-------|
| **Total Community Notes** | 2,232,084 |
| **Media Notes (images + videos)** | 122,130 (5.47%) |
| **Unique Tweets with Media** | 113,345 |
| **Misleading Media Notes** | 119,073 (97.5%) |
| **Not Misleading** | 3,057 (2.5%) |

### 📁 Files Created

```
video-llm-baseline-eval/
├── data/
│   ├── filtered/
│   │   ├── media_notes.csv       # 122K media notes
│   │   ├── media_notes.tsv       # Same, TSV format
│   │   └── filtering_report.txt  # Statistics
│   └── raw/
│       ├── notes-00000.tsv       # 2.2M notes
│       └── noteStatusHistory-00000.tsv
├── download_filter_community_notes.py  # ✅ Working
├── fetch_tweet_data.py                 # ✅ Created (needs Twitter API)
├── explore_data.py                     # ✅ Working
├── test_setup.py                       # ✅ Working
└── README.md                           # ✅ Complete
```

---

## What We Fixed

### 1. ✅ Cleaned Up Documentation
- **Before**: 7+ .md files (confusing!)
- **After**: 1 comprehensive README.md

### 2. ✅ Fixed Filtering Logic
- **Before**: Used keyword matching ("video", "deepfake", etc.) → Got 189K false positives
- **After**: Uses `isMediaNote` column → Got 122K actual media notes

### 3. ✅ Clarified Data Pipeline
Community Notes data structure:
- ❌ Doesn't include tweet text
- ❌ Doesn't include media URLs
- ✅ Only has `tweetId` and `isMediaNote` flag

**Solution**: Need Twitter API to get actual tweet/video data.

---

## What's Next

### Phase 2: Get Video Data (Requires Twitter API)

#### Step 1: Get Twitter API Access
1. Go to https://developer.twitter.com
2. Apply for developer account
3. Create project → Get Bearer Token
4. Add to `.env` file:
   ```bash
   TWITTER_BEARER_TOKEN=your_token_here
   ```

#### Step 2: Fetch Tweet Data
```bash
# Test with 10 tweets first
python fetch_tweet_data.py --limit 10

# Then fetch all
python fetch_tweet_data.py
```

This will:
- Read `media_notes.csv` (122K notes, 113K unique tweets)
- Call Twitter API to get tweet details
- Check which tweets have **video** (vs images)
- Save video tweet IDs and URLs
- Output: `video_tweets.json` and `video_tweets.csv`

#### Step 3: Download Videos
Once you have video URLs, download them:
```bash
python download_videos.py
```

#### Step 4: Evaluate with LLMs
Test Video LLMs (GPT-4V, Claude 3, Gemini, etc.) on the videos.

---

## Current Data Breakdown

### Media Notes (122,130 total)

**Classification**:
- Misleading: 119,073 (97.5%)
- Not Misleading: 3,057 (2.5%)

**What types of media?**
Unknown until we fetch tweet data. Could be:
- Videos
- Images
- GIFs
- Mix of above

**Estimated video percentage**: 20-40% (based on social media trends)
- If 30% → ~34K video tweets
- If 20% → ~23K video tweets

---

## Why We Need Twitter API

**Problem**: Community Notes dataset is privacy-focused
- Only provides `tweetId` (not actual tweets)
- Only provides `isMediaNote` flag (not media type)
- Doesn't include media URLs

**Solution**: Twitter API v2
```python
# What we can get from Twitter API:
{
  "id": "1234567890",
  "text": "Check out this video!",
  "attachments": {
    "media_keys": ["3_1234567890"]
  },
  "includes": {
    "media": [{
      "media_key": "3_1234567890",
      "type": "video",  # ← This is what we need!
      "url": "https://...",
      "duration_ms": 30000,
      "variants": [...]  # Video URLs in different qualities
    }]
  }
}
```

---

## Quick Commands

```bash
# Re-run data collection
python download_filter_community_notes.py

# Explore data
python explore_data.py

# Fetch tweet data (needs Twitter API)
python fetch_tweet_data.py --limit 10  # Test with 10 tweets

# Check results
head -20 data/filtered/media_notes.csv
cat data/filtered/filtering_report.txt
```

---

## API Rate Limits to Consider

### Twitter API v2 (Essential Access - Free Tier)
- **Lookup tweets**: 900 requests per 15 min
- **Each request**: Up to 100 tweets
- **Total**: ~90,000 tweets per 15 min

For 113K unique tweets:
- Need: ~1,131 requests (113,345 / 100)
- Time: ~20 minutes (with rate limiting)

---

## Expected Timeline

### Week 1 (Current)
- [x] Download Community Notes ✅
- [x] Filter for media notes ✅
- [x] Clean up documentation ✅
- [ ] Get Twitter API access
- [ ] Test tweet fetching (10-100 samples)

### Week 2-3
- [ ] Fetch all tweet data (~113K tweets)
- [ ] Identify video tweets (~20-40K)
- [ ] Download sample videos (100-500)
- [ ] Manual inspection

### Week 4-5
- [ ] Set up LLM APIs (OpenAI, Anthropic, Google)
- [ ] Design evaluation prompts
- [ ] Test with 10-20 videos

### Week 6-8
- [ ] Full evaluation (100-500 videos)
- [ ] Compare LLM vs human notes
- [ ] Analysis

---

## Cost Estimates

### Twitter API
- **Free tier**: 1,500 tweets/month (too low)
- **Basic ($100/month)**: 10,000 tweets/month (too low for 113K)
- **Pro ($5,000/month)**: 1M tweets/month ✓

**Recommendation**: Start with Basic tier for testing, then upgrade if needed. Or use Academic Research access (free, higher limits).

### LLM APIs (per video evaluation)
- **GPT-4V**: ~$0.01-0.03 per image/frame
- **Claude 3**: ~$0.02-0.05 per request
- **Gemini**: Variable pricing

**For 100 videos**: ~$50-200

---

## Alternative Approaches

If Twitter API is too expensive:

### Option 1: Use Smaller Sample
- Filter for most interesting cases
- Focus on 1,000-5,000 high-priority tweets

### Option 2: Manual Selection
- Manually browse Twitter for available videos
- Create custom dataset of 50-100 samples

### Option 3: Use Existing Datasets
- Deepfake datasets (FaceForensics++, Celeb-DF)
- AI-generated video datasets
- Misinformation video collections

---

## Key Takeaways

### What Works
✅ Community Notes data download  
✅ Media note filtering using `isMediaNote`  
✅ Data structure and pipeline  
✅ Scripts are ready  

### What's Needed
⏭️ Twitter API access (main blocker)  
⏭️ Tweet data fetching  
⏭️ Video identification and download  
⏭️ LLM API setup  

### What Changed
🔄 Filtering now uses `isMediaNote` (correct way)  
🔄 Clear understanding of data limitations  
🔄 Two-phase approach: (1) Get tweets (2) Filter videos  

---

## Next Action Items

### Priority 1 (This Week)
1. **Apply for Twitter Developer Account**
   - Go to https://developer.twitter.com
   - Fill out application (research project)
   - Request Academic Research access if eligible

2. **Test Tweet Fetching**
   - Once API access granted
   - Test with 10 tweets: `python fetch_tweet_data.py --limit 10`
   - Verify video detection works

### Priority 2 (Next Week)
3. **Fetch All Tweet Data**
   - Run on full dataset
   - Monitor rate limits
   - Cache results

4. **Analyze Video Distribution**
   - How many tweets have videos?
   - What types of videos?
   - Which are still available?

---

**Status**: Ready for Phase 2 pending Twitter API access! 🚀

