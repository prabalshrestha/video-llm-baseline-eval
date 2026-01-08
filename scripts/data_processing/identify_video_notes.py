"""
Identify actual video notes by checking media type from Twitter.
Downloads only metadata (info.json) for all media notes, then filters for videos.
Much more accurate than keyword-based filtering!

Updated to use database instead of CSV files.
"""

import pandas as pd
from pathlib import Path
import logging
import subprocess
import json
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import get_session, Note, MediaMetadata
from database.import_data import import_media_metadata_from_json

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VideoNoteIdentifier:
    def __init__(self, data_dir="data", force=False):
        self.data_dir = Path(data_dir)
        self.filtered_dir = self.data_dir / "filtered"
        self.temp_dir = self.data_dir / "temp_metadata"
        self.temp_dir.mkdir(exist_ok=True)
        self.force = force  # Force re-check even if already in database
        
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
    
    def download_metadata_only(self, tweet_id, index, save_to_db=False):
        """
        Download only metadata (info.json) for a tweet without downloading video.
        Returns a dict with media info if successful, None otherwise.

        Args:
            tweet_id: Tweet ID to check
            index: Index for temp file naming
            save_to_db: If True and media is video, save to media_metadata table
                       (creates its own thread-safe database session)
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
                "--socket-timeout",
                "5",  # Fail fast on network issues
                "-o",
                output_template,
                url,
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Find the info.json file
                info_files = list(self.temp_dir.glob(f"check_{index:05d}_*.info.json"))
                
                if info_files:
                    info_file = info_files[0]
                    
                    # Read and check media type
                    try:
                        with open(info_file, "r", encoding="utf-8") as f:
                            info = json.load(f)
                            media_type = info.get("_type", None)

                        # Save to database if requested (all media types, not just videos)
                        # IMPORTANT: Create a new session for thread-safety
                        if save_to_db and media_type:
                            try:
                                # Create thread-local session
                                with get_session() as thread_session:
                                    # Check if already exists
                                    existing = (
                                        thread_session.query(MediaMetadata)
                                        .filter(MediaMetadata.tweet_id == tweet_id)
                                        .first()
                                    )

                                    media_data = {
                                        "tweet_id": tweet_id,
                                        "media_id": str(info.get("id", "")),
                                        "media_type": media_type,
                                        "title": info.get("title"),
                                        "description": info.get("description"),
                                        "uploader": info.get("uploader"),
                                        "uploader_id": info.get("uploader_id"),
                                        "timestamp": info.get("timestamp"),
                                        "duration_ms": (
                                            int(info.get("duration", 0) * 1000)
                                            if info.get("duration")
                                            else None
                                        ),
                                        "like_count": info.get("like_count"),
                                        "width": info.get("width"),
                                        "height": info.get("height"),
                                        "formats": info.get("formats"),
                                    }

                                    if existing:
                                        # Update existing
                                        for key, value in media_data.items():
                                            if key != "tweet_id":
                                                setattr(existing, key, value)
                                    else:
                                        # Create new
                                        media = MediaMetadata(**media_data)
                                        thread_session.add(media)

                                    thread_session.commit()
                            except Exception as e:
                                logger.debug(
                                    f"Error saving to database for {tweet_id}: {e}"
                                )
                                # No need for rollback - context manager handles it
                            
                        # Clean up the temp file
                        info_file.unlink()
                        
                        return {"media_type": media_type, "info": info}
                        
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
    
    def identify_videos_batch(self, df, batch_size=500, max_workers=20):
        """
        Process media notes in batches to identify which are actually videos.
        
        Args:
            df: DataFrame with media notes
            batch_size: Number of tweets to check in one batch (default: 500)
            max_workers: Number of parallel workers (default: 20)

        Note:
            Each worker thread creates its own database session for thread-safety.
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
                # Each worker will create its own thread-safe database session
                future_to_row = {}
                for idx, row in batch_df.iterrows():
                    future = executor.submit(
                        self.download_metadata_only,
                        row["tweetId"],
                        idx,
                        save_to_db=True,  # Save to database (thread-safe)
                    )
                    future_to_row[future] = (idx, row)
                
                # Collect results as they complete
                for future in as_completed(future_to_row):
                    idx, row = future_to_row[future]
                    try:
                        result = future.result()
                        media_type = result["media_type"] if result else None
                        batch_results.append(
                            {
                                "index": idx,
                                "tweetId": row["tweetId"],
                                "media_type": media_type,
                                "is_video": media_type == "video",
                            }
                        )
                    except Exception as e:
                        logger.debug(f"Error processing {row['tweetId']}: {e}")
                        batch_results.append(
                            {
                                "index": idx,
                                "tweetId": row["tweetId"],
                                "media_type": None,
                                "is_video": False,
                            }
                        )
            
            results.extend(batch_results)
            
            # Show progress
            videos_found = sum(1 for r in results if r["is_video"])
            logger.info(
                f"  Progress: {len(results)}/{total} checked, {videos_found} videos found so far"
            )
            
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
        
        # Use session to query and extract data (all within session context)
        with get_session() as session:
            # Load media notes from database
            logger.info("\nQuerying media notes from database...")
            media_notes_query = (
                session.query(Note).filter(Note.is_media_note == True).all()
            )
            logger.info(f"Found {len(media_notes_query)} media notes in database")

            # Get tweet IDs that already have media_metadata (unless force mode)
            if not self.force:
                existing_media = session.query(MediaMetadata.tweet_id).all()
                existing_tweet_ids = {m[0] for m in existing_media}
                logger.info(
                    f"Found {len(existing_tweet_ids)} tweets with existing media metadata"
                )
                logger.info(
                    "Skipping already-processed tweets (use --force to re-process)"
                )

                # Filter out already-processed tweets
                media_notes_query = [
                    n for n in media_notes_query if n.tweet_id not in existing_tweet_ids
                ]
                logger.info(f"Remaining tweets to process: {len(media_notes_query)}")
            else:
                logger.info("Force mode: Re-processing all media notes")

            # IMPORTANT: Extract data WHILE session is still active
            # This prevents DetachedInstanceError when accessing attributes later
            media_notes_data = [
                {
                    "tweetId": note.tweet_id,
                    "noteId": note.note_id,
                    "summary": note.summary,
                    "classification": note.classification,
                }
                for note in media_notes_query
            ]

        # Check if we have any notes to process
        if not media_notes_data:
            logger.info("No new media notes to process!")
            return None

        # Convert to DataFrame for processing
        df = pd.DataFrame(media_notes_data)
            
            if sample_size:
                df = df.head(sample_size)
                logger.info(f"Limited to first {sample_size} notes for testing")
                
        # Identify videos and save to database
        # Note: Session is NOT passed - each worker creates its own thread-safe session
        results = self.identify_videos_batch(df)
        
        # Create results DataFrame
        results_df = pd.DataFrame(results)
        
        # Filter for videos only
        video_mask = results_df["is_video"] == True
        video_indices = results_df[video_mask]["index"].tolist()
        
        # Get the original rows for videos
        video_notes = (
            df.loc[video_indices].copy() if len(video_indices) > 0 else pd.DataFrame()
        )
        
        logger.info("\n" + "=" * 70)
        logger.info("RESULTS")
        logger.info("=" * 70)
        logger.info(f"Total media notes checked: {len(df)}")
        logger.info(f"Actual videos found: {len(video_notes)}")
        if len(df) > 0:
        logger.info(f"Percentage: {len(video_notes)/len(df)*100:.1f}%")
        if len(video_notes) > 0:
        logger.info(f"Unique video tweets: {video_notes['tweetId'].nunique()}")
            logger.info("\nAll video metadata saved to database (media_metadata table)")
        
        # Optional: Save results to CSV for reference
        if len(video_notes) > 0:
            self.filtered_dir.mkdir(parents=True, exist_ok=True)
            output_file = self.filtered_dir / "verified_video_notes.csv"
            video_notes.to_csv(output_file, index=False)
            logger.info(f"Saved reference CSV to: {output_file}")
            
            # Also save the detailed results
            results_file = self.filtered_dir / "media_type_check_results.json"
            with open(results_file, "w") as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved detailed results to: {results_file}")
            
            # Sample some summaries
            logger.info("\nSample video note summaries:")
            for i, summary in enumerate(video_notes["summary"].head(5), 1):
                summary_short = (
                    (summary[:100] + "...") if len(str(summary)) > 100 else str(summary)
                )
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
        logger.info("Check the media_metadata table in database for results")
        
        return video_notes


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Identify actual video notes by checking media type and save to database"
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Process only first N notes (for testing, default: all)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-process all media notes, even if already in database",
    )
    args = parser.parse_args()
    
    identifier = VideoNoteIdentifier(data_dir="data", force=args.force)
    result = identifier.run(sample_size=args.sample)
    
    if result is not None and len(result) > 0:
        print(f"\n✓ Successfully identified {len(result)} video notes!")
        print(f"✓ Check media_metadata table in database")
        print(f"✓ Reference CSV: data/filtered/verified_video_notes.csv")
    elif result is not None and len(result) == 0:
        print("\n✓ No new videos found (all already processed)")
    else:
        print("\n✗ Failed to identify video notes")


if __name__ == "__main__":
    main()
