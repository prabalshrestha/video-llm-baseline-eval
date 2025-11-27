"""
Video Downloader for Community Notes
This script downloads videos from tweet IDs found in Community Notes data.

Note: This requires additional setup with Twitter API credentials or alternative methods.
"""

import pandas as pd
from pathlib import Path
import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VideoDownloader:
    """
    Downloads videos from tweets identified in Community Notes.
    
    Methods to download:
    1. Twitter API v2 (requires API keys)
    2. yt-dlp (works for some twitter videos)
    3. Third-party services
    """
    
    def __init__(self, video_dir='data/videos'):
        self.video_dir = Path(video_dir)
        self.video_dir.mkdir(parents=True, exist_ok=True)
        self.metadata = []
    
    def load_filtered_notes(self, filepath='data/filtered/video_notes.csv'):
        """Load filtered Community Notes data."""
        try:
            df = pd.read_csv(filepath)
            logger.info(f"Loaded {len(df)} video notes")
            return df
        except Exception as e:
            logger.error(f"Failed to load notes: {e}")
            return None
    
    def extract_tweet_ids(self, df):
        """Extract unique tweet IDs from the notes."""
        if 'tweetId' in df.columns:
            tweet_ids = df['tweetId'].unique().tolist()
            logger.info(f"Found {len(tweet_ids)} unique tweet IDs")
            return tweet_ids
        else:
            logger.error("No 'tweetId' column found in data")
            return []
    
    def download_with_ytdlp(self, tweet_id):
        """
        Download video using yt-dlp.
        
        Installation: pip install yt-dlp
        """
        try:
            import yt_dlp
            
            url = f"https://twitter.com/i/status/{tweet_id}"
            output_path = self.video_dir / f"{tweet_id}.%(ext)s"
            
            ydl_opts = {
                'outtmpl': str(output_path),
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                if info:
                    self.metadata.append({
                        'tweet_id': tweet_id,
                        'title': info.get('title', ''),
                        'duration': info.get('duration', 0),
                        'upload_date': info.get('upload_date', ''),
                        'uploader': info.get('uploader', ''),
                    })
                    
                    logger.info(f"✓ Downloaded video for tweet {tweet_id}")
                    return True
                    
        except ImportError:
            logger.error("yt-dlp not installed. Install with: pip install yt-dlp")
            return False
        except Exception as e:
            logger.warning(f"Failed to download tweet {tweet_id}: {e}")
            return False
    
    def download_videos_batch(self, tweet_ids, max_count=10):
        """
        Download videos for a batch of tweet IDs.
        
        Args:
            tweet_ids: List of tweet IDs
            max_count: Maximum number of videos to download (for testing)
        """
        logger.info(f"Attempting to download up to {max_count} videos...")
        
        success_count = 0
        fail_count = 0
        
        for i, tweet_id in enumerate(tweet_ids[:max_count], 1):
            logger.info(f"Processing {i}/{min(max_count, len(tweet_ids))}: {tweet_id}")
            
            if self.download_with_ytdlp(tweet_id):
                success_count += 1
            else:
                fail_count += 1
        
        logger.info(f"\nDownload complete!")
        logger.info(f"  Success: {success_count}")
        logger.info(f"  Failed: {fail_count}")
        
        # Save metadata
        if self.metadata:
            metadata_file = self.video_dir / 'video_metadata.json'
            with open(metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            logger.info(f"Metadata saved to {metadata_file}")
    
    def generate_download_links(self, tweet_ids, output_file='data/tweet_links.txt'):
        """Generate a file with tweet links for manual download."""
        output_path = Path(output_file)
        
        with open(output_path, 'w') as f:
            f.write("# Tweet Links for Video Download\n")
            f.write("# Generated from Community Notes data\n\n")
            
            for tweet_id in tweet_ids:
                url = f"https://twitter.com/i/status/{tweet_id}"
                f.write(f"{url}\n")
        
        logger.info(f"Generated {len(tweet_ids)} tweet links in {output_path}")
        logger.info("You can use these links to manually verify and download videos")


def main():
    """Main entry point."""
    print("=" * 70)
    print("VIDEO DOWNLOADER FOR COMMUNITY NOTES")
    print("=" * 70)
    print("\nThis script helps download videos from tweets identified in Community Notes.")
    print("\nOptions:")
    print("  1. Download videos using yt-dlp (automated)")
    print("  2. Generate list of tweet links (for manual download)")
    print()
    
    downloader = VideoDownloader()
    
    # Load filtered notes
    df = downloader.load_filtered_notes()
    
    if df is None:
        print("\n✗ No filtered data found.")
        print("  Please run 'python download_filter_community_notes.py' first")
        return
    
    # Extract tweet IDs
    tweet_ids = downloader.extract_tweet_ids(df)
    
    if not tweet_ids:
        print("\n✗ No tweet IDs found in the data")
        return
    
    print(f"\nFound {len(tweet_ids)} unique tweets to process")
    print("\nNote: Not all tweets may contain videos. The script will skip those.")
    
    # For now, just generate links (safer option)
    print("\n📝 Generating tweet links file...")
    downloader.generate_download_links(tweet_ids)
    
    print("\n" + "=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print("1. Review the tweet links in 'data/tweet_links.txt'")
    print("2. Manually verify which tweets contain videos")
    print("3. (Optional) Install yt-dlp: pip install yt-dlp")
    print("4. (Optional) Use automated download by modifying this script")
    print("\nFor automated download, you may need:")
    print("  - Twitter API credentials")
    print("  - yt-dlp or similar tools")
    print("  - Proper rate limiting and error handling")


if __name__ == "__main__":
    main()

