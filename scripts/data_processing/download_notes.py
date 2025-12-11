"""
Community Notes Data Downloader and Video Filter
This script downloads X/Twitter Community Notes data and filters for video-related content.
"""

import requests
import pandas as pd
import os
from pathlib import Path
from datetime import datetime
import logging
import zipfile
from io import BytesIO

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Community Notes data URLs (publicly available ZIP files containing TSV data)
BASE_URL = "https://ton.twimg.com/birdwatch-public-data"
# Note: Files are distributed as .zip files, not direct .tsv files


class CommunityNotesDownloader:
    def __init__(self, data_dir="data"):
        """Initialize the downloader with a data directory."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.raw_dir = self.data_dir / "raw"
        self.raw_dir.mkdir(exist_ok=True)
        self.filtered_dir = self.data_dir / "filtered"
        self.filtered_dir.mkdir(exist_ok=True)

    def download_and_extract_zip(self, url, filename):
        """Download a ZIP file from the given URL and extract it."""
        logger.info(f"Downloading {filename}...")
        try:
            response = requests.get(url, timeout=300)
            response.raise_for_status()

            # Extract the zip file
            logger.info(f"Extracting {filename}...")
            with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
                # Extract all files to raw directory
                zip_file.extractall(self.raw_dir)
                extracted_files = zip_file.namelist()
                logger.info(f"Extracted files: {extracted_files}")

                # Return the path to the main TSV file
                # The extracted file should have the same base name
                tsv_filename = filename.replace(".zip", ".tsv")
                filepath = self.raw_dir / tsv_filename

                if filepath.exists():
                    logger.info(f"Successfully downloaded and extracted {tsv_filename}")
                    return filepath
                else:
                    # Sometimes the extracted file might be in the list
                    for extracted in extracted_files:
                        if extracted.endswith(".tsv"):
                            extracted_path = self.raw_dir / extracted
                            if extracted_path.exists():
                                return extracted_path
                    logger.error(f"Could not find TSV file after extraction")
                    return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {filename}: {e}")
            return None
        except zipfile.BadZipFile as e:
            logger.error(f"Failed to extract {filename}: {e}")
            return None

    def try_download_with_dates(self, file_type):
        """Try to download files with different date patterns."""
        # Try recent dates (data is updated periodically)
        dates_to_try = [
            "2025/11/26",
            "2025/11/25",
            "2025/11/24",
            "2025/11/20",
            "2025/11/01",
            "2025/10/01",
            "2024/12/01",
        ]

        for date in dates_to_try:
            # Files are distributed as .zip files
            url = f"{BASE_URL}/{date}/{file_type}/{file_type}-00000.zip"
            logger.info(f"Trying URL: {url}")

            try:
                response = requests.head(url, timeout=30)
                if response.status_code == 200:
                    logger.info(f"Found valid URL for {file_type}: {url}")
                    return self.download_and_extract_zip(url, f"{file_type}-00000.zip")
            except:
                continue

        # Try without date (older format)
        url = f"{BASE_URL}/{file_type}-00000.zip"
        logger.info(f"Trying URL without date: {url}")
        return self.download_and_extract_zip(url, f"{file_type}-00000.zip")

    def download_all_data(self):
        """Download all Community Notes data files."""
        logger.info("Starting Community Notes data download...")

        downloaded_files = {}
        for file_type in ["notes", "ratings", "noteStatusHistory"]:
            filepath = self.try_download_with_dates(file_type)
            if filepath and filepath.exists():
                downloaded_files[file_type] = filepath

        return downloaded_files

    def load_notes_data(self, filepath):
        """Load notes data from TSV file."""
        try:
            logger.info(f"Loading notes data from {filepath}...")
            df = pd.read_csv(filepath, sep="\t", low_memory=False)
            logger.info(f"Loaded {len(df)} notes")
            logger.info(f"Columns: {df.columns.tolist()}")
            return df
        except Exception as e:
            logger.error(f"Failed to load notes data: {e}")
            return None

    def filter_media_notes(self, notes_df):
        """
        Filter notes that are associated with media content (images/videos).
        
        Uses the 'isMediaNote' column which indicates if the note is about media.
        
        Note: This filters for ALL media notes. To specifically identify VIDEO tweets,
        you'll need to fetch tweet data using Twitter API and check media_type.
        """
        if notes_df is None or notes_df.empty:
            logger.warning("No notes data to filter")
            return None

        logger.info("Filtering for media-related notes...")

        # Filter using isMediaNote column (1 = media note, 0 = not media)
        if "isMediaNote" in notes_df.columns:
            media_notes = notes_df[notes_df["isMediaNote"] == 1].copy()
            logger.info(f"Found {len(media_notes)} media notes using isMediaNote column")
        else:
            logger.warning("isMediaNote column not found, cannot filter properly")
            return None

        # Add metadata
        media_notes["filtered_date"] = datetime.now().strftime("%Y-%m-%d")
        media_notes["filter_method"] = "isMediaNote"

        # Get unique tweet count
        unique_tweets = media_notes["tweetId"].nunique()
        logger.info(f"These notes are associated with {unique_tweets} unique tweets")
        logger.info(
            "Note: To identify which tweets have VIDEO (vs images), use Twitter API"
        )

        return media_notes

    def save_filtered_data(self, df, filename="video_notes.csv"):
        """Save filtered data to CSV."""
        if df is None or df.empty:
            logger.warning("No data to save")
            return None

        filepath = self.filtered_dir / filename
        df.to_csv(filepath, index=False)
        logger.info(f"Saved {len(df)} filtered notes to {filepath}")

        # Also save as TSV for consistency
        tsv_filepath = self.filtered_dir / filename.replace(".csv", ".tsv")
        df.to_csv(tsv_filepath, sep="\t", index=False)
        logger.info(f"Also saved as TSV: {tsv_filepath}")

        return filepath

    def generate_summary_report(self, original_df, filtered_df):
        """Generate a summary report of the filtering process."""
        report_path = self.filtered_dir / "filtering_report.txt"

        with open(report_path, "w") as f:
            f.write("Community Notes Media Filtering Report\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            if original_df is not None:
                f.write(f"Total notes downloaded: {len(original_df)}\n")

            if filtered_df is not None:
                f.write(f"Media notes found: {len(filtered_df)}\n")
                f.write(f"Percentage: {len(filtered_df)/len(original_df)*100:.2f}%\n")
                f.write(f"Unique tweets with media: {filtered_df['tweetId'].nunique()}\n\n")

                f.write("IMPORTANT: These are media notes (images + videos).\n")
                f.write("To filter specifically for VIDEO tweets, you need to:\n")
                f.write("1. Use Twitter API to fetch tweet data\n")
                f.write("2. Check media_type field for 'video'\n")
                f.write("3. Filter accordingly\n\n")

                # Column information
                f.write("Available columns:\n")
                for col in filtered_df.columns:
                    f.write(f"  - {col}\n")

                f.write("\n")

                # Sample statistics
                if "classification" in filtered_df.columns:
                    f.write("Classification distribution:\n")
                    f.write(str(filtered_df["classification"].value_counts()) + "\n\n")

        logger.info(f"Summary report saved to {report_path}")

    def run(self):
        """Main execution method."""
        logger.info("=" * 50)
        logger.info("Community Notes Media Filter")
        logger.info("=" * 50)

        # Check if raw data already exists
        notes_file = self.raw_dir / "notes-00000.tsv"
        if notes_file.exists():
            logger.info(f"\n✓ Found existing raw data: {notes_file}")
            logger.info("Skipping download step...")
            downloaded_files = {"notes": notes_file}
        else:
            # Step 1: Download data
            downloaded_files = self.download_all_data()

            if "notes" not in downloaded_files:
                logger.error("Failed to download notes data. Cannot proceed.")
                logger.info("\nTroubleshooting tips:")
                logger.info("1. Check internet connection")
                logger.info(
                    "2. Visit https://communitynotes.x.com/guide/en/under-the-hood/download-data"
                )
                logger.info(
                    "3. The data URL may have changed. Check the official documentation."
                )
                return None

        # Step 2: Load notes data
        notes_df = self.load_notes_data(downloaded_files["notes"])

        if notes_df is None:
            logger.error("Failed to load notes data")
            return None

        # Check if filtered data already exists
        existing_media_notes = self.filtered_dir / "media_notes.csv"
        if existing_media_notes.exists():
            logger.info(f"\n✓ Found existing filtered data: {existing_media_notes}")
            logger.info("Skipping filtering step...")
            media_notes_df = pd.read_csv(existing_media_notes)
            logger.info(f"Loaded {len(media_notes_df)} media notes from existing file")
        else:
            # Step 3: Filter for media content
            media_notes_df = self.filter_media_notes(notes_df)

        # Step 4: Save filtered data
        if media_notes_df is not None and not media_notes_df.empty and not existing_media_notes.exists():
            if not existing_media_notes.exists():
                output_file = self.save_filtered_data(media_notes_df, filename="media_notes.csv")
                # Step 5: Generate report
                self.generate_summary_report(notes_df, media_notes_df)
            else:
                output_file = existing_media_notes

            logger.info("\n" + "=" * 50)
            logger.info("SUCCESS: Media notes ready!")
            logger.info("=" * 50)
            logger.info(f"Media notes file: {output_file}")
            logger.info(f"Total media notes: {len(media_notes_df)}")
            logger.info(f"Unique tweets: {media_notes_df['tweetId'].nunique()}")
            logger.info("\nNext step: Run 'python main.py filter' to identify videos")

            return media_notes_df
        else:
            logger.warning("No media notes found in the dataset")
            return None


def main():
    """Main entry point."""
    downloader = CommunityNotesDownloader(data_dir="data")
    result = downloader.run()

    if result is not None:
        print("\n✓ Data download and filtering completed successfully!")
        print(f"✓ Check the 'data/filtered/' directory for results")
    else:
        print("\n✗ Failed to complete data download and filtering")
        print("Please check the logs above for details")


if __name__ == "__main__":
    main()
