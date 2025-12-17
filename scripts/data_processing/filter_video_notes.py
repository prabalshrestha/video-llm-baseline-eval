"""
Filter for likely VIDEO notes using keyword heuristics.
This is not perfect, but gives us a subset of video notes without Twitter API.

Updated to use database instead of CSV files.
"""

import pandas as pd
from pathlib import Path
import logging
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import get_session, Note

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def filter_likely_video_notes(df):
    """
    Filter for notes that likely refer to videos based on keywords.

    Note: This is a heuristic approach and not 100% accurate.
    To get exact video tweets, you need Twitter API.
    """

    # Video-specific keywords (more specific than just "video")
    video_keywords = [
        r"\bvideo\b",  # "video" as whole word
        r"\bfootage\b",  # "footage"
        r"\bclip\b",  # "clip"
        r"\brecording\b",  # "recording"
        r"\bfilmed\b",  # "filmed"
        r"\bviral video\b",  # "viral video"
        r"\bfake video\b",  # "fake video"
        r"\bedited video\b",  # "edited video"
        r"\bold video\b",  # "old video"
        r"\bdeepfake\b",  # "deepfake"
        r"\banimation\b",  # "animation"
        r"\bCGI\b",  # "CGI"
        r"\bscene\b",  # "scene"
        r"\bmovie\b",  # "movie"
        r"\bfilm\b",  # "film"
        r"\bshows\b",  # "shows"
        r"\bcamera\b",  # "camera"
        r"\brecorded\b",  # "recorded"
    ]

    # Combine into regex pattern
    pattern = "|".join(video_keywords)

    # Filter using summary column
    if "summary" not in df.columns:
        logger.error("summary column not found")
        return None

    # Apply filter
    video_mask = (
        df["summary"].fillna("").str.contains(pattern, case=False, regex=True, na=False)
    )

    video_notes = df[video_mask].copy()

    return video_notes


def main():
    logger.info("=" * 70)
    logger.info("VIDEO NOTE FILTER (Heuristic Approach)")
    logger.info("=" * 70)

    # Query media notes from database
    logger.info("\nQuerying media notes from database...")

    with get_session() as session:
        # Get all media notes
        media_notes = session.query(Note).filter(Note.is_media_note == True).all()

        logger.info(f"Loaded {len(media_notes)} media notes from database")

        # Convert to DataFrame for filtering
        df = pd.DataFrame(
            [
                {
                    "noteId": note.note_id,
                    "tweetId": note.tweet_id,
                    "summary": note.summary,
                    "classification": note.classification,
                    "noteAuthorParticipantId": note.note_author_participant_id,
                    "createdAtMillis": note.created_at_millis,
                }
                for note in media_notes
            ]
        )

        # Filter for likely video notes
        logger.info("\nFiltering for likely video notes using keywords...")
        logger.info("Note: This is a heuristic approach - not 100% accurate!")

        video_notes = filter_likely_video_notes(df)

        if video_notes is None or video_notes.empty:
            logger.error("No video notes found")
            return

        logger.info(f"Found {len(video_notes)} likely video notes")
        logger.info(f"That's {len(video_notes)/len(df)*100:.1f}% of media notes")

        # Optional: Save results to CSV for reference
        data_dir = Path("data/filtered")
        data_dir.mkdir(parents=True, exist_ok=True)
        output_file = data_dir / "likely_video_notes.csv"
        video_notes.to_csv(output_file, index=False)
        logger.info(f"\nSaved to: {output_file} (for reference)")

        # Get unique tweets
        unique_tweets = video_notes["tweetId"].nunique()
        logger.info(f"Unique tweets: {unique_tweets}")

        # Sample some summaries
        logger.info("\nSample video note summaries:")
        for i, summary in enumerate(video_notes["summary"].head(10), 1):
            summary_short = (summary[:100] + "...") if len(summary) > 100 else summary
            logger.info(f"{i}. {summary_short}")

        # Statistics
        logger.info("\n" + "=" * 70)
        logger.info("SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Media notes (input): {len(df)}")
        logger.info(f"Likely video notes (output): {len(video_notes)}")
        logger.info(f"Percentage: {len(video_notes)/len(df)*100:.1f}%")
        logger.info(f"Unique tweets: {unique_tweets}")

        logger.info("\n⚠️  IMPORTANT:")
        logger.info("This is a HEURISTIC filter based on keywords.")
        logger.info("It may include false positives (image notes with video keywords).")
        logger.info("It may miss videos (if summary doesn't mention video).")
        logger.info(
            "\nFor ACCURATE filtering, use identify_video_notes.py which checks actual media type."
        )

    return video_notes


if __name__ == "__main__":
    main()
