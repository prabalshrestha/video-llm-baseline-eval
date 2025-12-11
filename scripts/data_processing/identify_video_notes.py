"""
Identify actual video notes by checking media type from Twitter.
Downloads only metadata (info.json) for all media notes, then filters for videos.
Much more accurate than keyword-based filtering!
"""

import pandas as pd
from pathlib import Path
import logging
import subprocess
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VideoNoteIdentifier:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.filtered_dir = self.data_dir / "filtered"
        self.temp_dir = self.data_dir / "temp_metadata"
        self.temp_dir.mkdir(exist_ok=True)
        
    def check_ytdlp(self):
        """Check if yt-dlp is installed."""
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                logger.info(f"✓ yt-dlp version: {result.stdout.strip()}")
                return True
            return False
        except FileNotFoundError:
            logger.error("yt-dlp not found!")
            logger.info("\nTo install yt-dlp:")
            logger.info("  pip install yt-dlp")
            logger.info("  or: brew install yt-dlp (on macOS)")
            return False
        except Exception as e:
            logger.error(f"Error checking yt-dlp: {e}")
            return False
    
    def download_metadata_only(self, tweet_id, index):
        """
        Download only metadata (info.json) for a tweet without downloading video.
        Returns the media type if successful, None otherwise.
        """
        url = f"https://twitter.com/i/status/{tweet_id}"
        output_template = str(self.temp_dir / f"check_{index:05d}_%(id)s.%(ext)s")
        
        try:
            # yt-dlp command to download ONLY metadata
            cmd = [
                "yt-dlp",
                "--quiet",
                "--no-warnings",
                "--skip-download",  # Don't download the video!
                "--write-info-json",  # Only write metadata
                "-o", output_template,
                url,
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                # Find the info.json file
                info_files = list(self.temp_dir.glob(f"check_{index:05d}_*.info.json"))
                
                if info_files:
                    info_file = info_files[0]
                    
                    # Read and check media type
                    try:
                        with open(info_file, 'r', encoding='utf-8') as f:
                            info = json.load(f)
                            media_type = info.get('_type', None)
                            
                        # Clean up the temp file
                        info_file.unlink()
                        
                        return media_type
                        
                    except Exception as e:
                        logger.debug(f"Error reading info file for {tweet_id}: {e}")
                        return None
                else:
                    return None
            else:
                return None
                
        except subprocess.TimeoutExpired:
            logger.debug(f"Timeout for tweet {tweet_id}")
            return None
        except Exception as e:
            logger.debug(f"Error checking tweet {tweet_id}: {e}")
            return None
    
    def identify_videos_batch(self, df, batch_size=100, max_workers=5):
        """
        Process media notes in batches to identify which are actually videos.
        
        Args:
            df: DataFrame with media notes
            batch_size: Number of tweets to check in one batch
            max_workers: Number of parallel workers
        """
        results = []
        total = len(df)
        
        logger.info(f"\nChecking {total} media notes...")
        logger.info(f"Using {max_workers} parallel workers")
        logger.info("This may take a while, please be patient...\n")
        
        # Process in batches to show progress
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch_df = df.iloc[batch_start:batch_end]
            
            logger.info(f"Processing batch {batch_start+1}-{batch_end} of {total}...")
            
            batch_results = []
            
            # Use ThreadPoolExecutor for parallel downloads
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_row = {}
                for idx, row in batch_df.iterrows():
                    future = executor.submit(
                        self.download_metadata_only,
                        row['tweetId'],
                        idx
                    )
                    future_to_row[future] = (idx, row)
                
                # Collect results as they complete
                for future in as_completed(future_to_row):
                    idx, row = future_to_row[future]
                    try:
                        media_type = future.result()
                        batch_results.append({
                            'index': idx,
                            'tweetId': row['tweetId'],
                            'media_type': media_type,
                            'is_video': media_type == 'video'
                        })
                    except Exception as e:
                        logger.debug(f"Error processing {row['tweetId']}: {e}")
                        batch_results.append({
                            'index': idx,
                            'tweetId': row['tweetId'],
                            'media_type': None,
                            'is_video': False
                        })
            
            results.extend(batch_results)
            
            # Show progress
            videos_found = sum(1 for r in results if r['is_video'])
            logger.info(f"  Progress: {len(results)}/{total} checked, {videos_found} videos found so far")
            
            # Brief pause between batches
            if batch_end < total:
                time.sleep(2)
        
        return results
    
    def run(self, sample_size=None):
        """Main execution."""
        logger.info("=" * 70)
        logger.info("VIDEO NOTE IDENTIFIER - Accurate Media Type Detection")
        logger.info("=" * 70)
        
        # Check yt-dlp
        if not self.check_ytdlp():
            return None
        
        # Load media notes
        logger.info("\nLoading media notes...")
        media_notes_file = self.filtered_dir / "media_notes.csv"
        
        try:
            df = pd.read_csv(media_notes_file)
            logger.info(f"Loaded {len(df)} media notes")
            
            if sample_size:
                df = df.head(sample_size)
                logger.info(f"Limited to first {sample_size} notes for testing")
                
        except Exception as e:
            logger.error(f"Failed to load media notes: {e}")
            return None
        
        # Identify videos
        results = self.identify_videos_batch(df)
        
        # Create results DataFrame
        results_df = pd.DataFrame(results)
        
        # Filter for videos only
        video_mask = results_df['is_video'] == True
        video_indices = results_df[video_mask]['index'].tolist()
        
        # Get the original rows for videos
        video_notes = df.loc[video_indices].copy()
        
        # Add media type info
        video_notes['verified_media_type'] = 'video'
        
        logger.info("\n" + "=" * 70)
        logger.info("RESULTS")
        logger.info("=" * 70)
        logger.info(f"Total media notes checked: {len(df)}")
        logger.info(f"Actual videos found: {len(video_notes)}")
        logger.info(f"Percentage: {len(video_notes)/len(df)*100:.1f}%")
        logger.info(f"Unique video tweets: {video_notes['tweetId'].nunique()}")
        
        # Save results
        if len(video_notes) > 0:
            output_file = self.filtered_dir / "verified_video_notes.csv"
            video_notes.to_csv(output_file, index=False)
            logger.info(f"\nSaved verified video notes to: {output_file}")
            
            # Also save the detailed results
            results_file = self.filtered_dir / "media_type_check_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved detailed results to: {results_file}")
            
            # Sample some summaries
            logger.info("\nSample video note summaries:")
            for i, summary in enumerate(video_notes['summary'].head(5), 1):
                summary_short = (summary[:100] + '...') if len(summary) > 100 else summary
                logger.info(f"{i}. {summary_short}")
        else:
            logger.warning("No videos found!")
        
        # Clean up temp directory
        try:
            for f in self.temp_dir.glob("*"):
                f.unlink()
            self.temp_dir.rmdir()
            logger.info("\nCleaned up temporary files")
        except:
            pass
        
        logger.info("\n✓ Video identification complete!")
        logger.info("This method is MUCH more accurate than keyword filtering!")
        
        return video_notes


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Identify actual video notes by checking media type"
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Process only first N notes (for testing, default: all)"
    )
    args = parser.parse_args()
    
    identifier = VideoNoteIdentifier(data_dir="data")
    result = identifier.run(sample_size=args.sample)
    
    if result is not None:
        print(f"\n✓ Successfully identified {len(result)} video notes!")
        print(f"✓ Check data/filtered/verified_video_notes.csv")
    else:
        print("\n✗ Failed to identify video notes")


if __name__ == "__main__":
    main()

