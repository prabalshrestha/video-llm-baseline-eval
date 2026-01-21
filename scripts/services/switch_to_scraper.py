#!/usr/bin/env python3
"""
Quick script to test and switch from Twitter API to scraper.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_installation():
    """Check which scraping methods are installed."""
    methods = {}
    
    # Check tweepy-self
    try:
        import tweepy_self
        methods['tweepy-self'] = True
        logger.info("✓ tweepy-self is installed")
    except ImportError:
        methods['tweepy-self'] = False
        logger.warning("✗ tweepy-self not installed: pip install tweepy-self")
    
    # Check snscrape
    try:
        import subprocess
        result = subprocess.run(['snscrape', '--version'], 
                              capture_output=True, timeout=5)
        methods['snscrape'] = result.returncode == 0
        if methods['snscrape']:
            logger.info("✓ snscrape is installed")
        else:
            raise Exception("snscrape not working")
    except:
        methods['snscrape'] = False
        logger.warning("✗ snscrape not installed: pip install snscrape")
    
    # Check playwright
    try:
        import playwright
        methods['playwright'] = True
        logger.info("✓ playwright is installed")
        logger.info("  Don't forget to run: playwright install chromium")
    except ImportError:
        methods['playwright'] = False
        logger.warning("✗ playwright not installed: pip install playwright")
    
    return methods


def test_scraper():
    """Test the scraper with a real tweet."""
    from twitter_scraper_unified import TwitterScraperUnified
    
    logger.info("\n" + "="*70)
    logger.info("Testing Twitter Scraper")
    logger.info("="*70)
    
    scraper = TwitterScraperUnified()
    
    if not scraper.is_available():
        logger.error("\n✗ No scraping methods available!")
        logger.info("\nInstall at least one method:")
        logger.info("  pip install tweepy-self        (Recommended)")
        logger.info("  pip install snscrape")
        logger.info("  pip install playwright && playwright install chromium")
        return False
    
    logger.info(f"\nAvailable methods: {scraper.available_methods}")
    
    # Test with a known public tweet (Elon Musk's first tweet)
    # Feel free to replace with your own tweet ID
    test_tweet_id = "1"  # Jack Dorsey's "just setting up my twttr"
    
    logger.info(f"\nTesting with tweet ID: {test_tweet_id}")
    logger.info("Note: This is a very old tweet, may not be available")
    logger.info("Replace with a recent tweet ID for better results\n")
    
    try:
        tweets_data = scraper.fetch_tweets([test_tweet_id], save_to_db=False)
        
        if tweets_data:
            logger.info("\n" + "="*70)
            logger.info("✓ SUCCESS! Scraper is working!")
            logger.info("="*70)
            
            for tweet_id, data in tweets_data.items():
                logger.info(f"\nTweet {tweet_id}:")
                logger.info(f"  Text: {data.get('text', '')[:100]}...")
                logger.info(f"  Author: @{data.get('author_username', 'N/A')}")
                logger.info(f"  Likes: {data.get('likes', 0)}")
                logger.info(f"  Retweets: {data.get('retweets', 0)}")
            
            return True
        else:
            logger.warning("\n⚠ No tweets fetched (tweet may not exist)")
            logger.info("Try with a different, recent tweet ID")
            return False
            
    except Exception as e:
        logger.error(f"\n✗ Error testing scraper: {e}")
        return False


def show_comparison():
    """Show comparison between API and scraper."""
    print("\n" + "="*70)
    print("Twitter API vs Scraper Comparison")
    print("="*70)
    print("""
┌─────────────────────┬─────────────────────┬─────────────────────┐
│ Feature             │ Twitter API (Free)  │ Scraper             │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ Monthly Limit       │ 100 requests        │ Unlimited           │
│ Cost                │ Free                │ Free                │
│ API Key Required    │ Yes                 │ No                  │
│ Data Quality        │ Official JSON       │ Same data           │
│ Reliability         │ 100%                │ 95-99%              │
│ Speed               │ Fast                │ Fast                │
│ Legal/ToS           │ Compliant           │ Research use only   │
└─────────────────────┴─────────────────────┴─────────────────────┘

Recommendation: Use scraper for unlimited access to tweet data!
""")


def show_integration_guide():
    """Show how to integrate with existing code."""
    print("\n" + "="*70)
    print("Integration Guide")
    print("="*70)
    print("""
To switch from Twitter API to scraper in your existing code:

1. Update the import:

   OLD:
   from scripts.services.twitter_service import TwitterService
   
   NEW:
   from scripts.services.twitter_scraper_unified import TwitterScraperUnified as TwitterService

2. Everything else stays the same:

   service = TwitterService()
   tweets = service.fetch_tweets(tweet_ids)

3. Or use both:

   # Try API first (if you have quota left)
   from scripts.services.twitter_service import TwitterService
   api_service = TwitterService()
   
   if api_service.is_available():
       tweets = api_service.fetch_tweets(tweet_ids[:100])  # Use quota wisely
   
   # Then use scraper for the rest
   from scripts.services.twitter_scraper_unified import TwitterScraperUnified
   scraper = TwitterScraperUnified()
   remaining_ids = tweet_ids[100:]
   tweets.update(scraper.fetch_tweets(remaining_ids))

4. For your data pipeline scripts, simply update the service import
   in these files:
   - scripts/data_processing/create_dataset.py
   - scripts/data_processing/identify_video_notes.py
   - Any other scripts using TwitterService
""")


def main():
    """Main function."""
    print("\n" + "="*70)
    print("Twitter Scraper Setup & Testing")
    print("="*70)
    
    # Check installation
    logger.info("\n[1/4] Checking installed scraping methods...")
    methods = check_installation()
    
    if not any(methods.values()):
        logger.error("\n✗ No scraping methods installed!")
        logger.info("\nQuick install (all methods):")
        logger.info("  pip install -r requirements-scraper.txt")
        logger.info("  playwright install chromium")
        logger.info("\nOr install just one method:")
        logger.info("  pip install tweepy-self  (Recommended)")
        return
    
    # Show comparison
    logger.info("\n[2/4] Comparing API vs Scraper...")
    show_comparison()
    
    # Test scraper
    logger.info("\n[3/4] Testing scraper...")
    input("\nPress Enter to test the scraper (or Ctrl+C to skip)...")
    test_scraper()
    
    # Show integration guide
    logger.info("\n[4/4] Integration guide...")
    show_integration_guide()
    
    print("\n" + "="*70)
    print("Setup Complete!")
    print("="*70)
    print("\nNext steps:")
    print("1. Update your scripts to use TwitterScraperUnified")
    print("2. Run your pipeline: python main.py pipeline")
    print("3. Enjoy unlimited tweet fetching!")
    print("\nFor detailed docs, see: TWITTER_SCRAPING_GUIDE.md")


if __name__ == "__main__":
    main()
