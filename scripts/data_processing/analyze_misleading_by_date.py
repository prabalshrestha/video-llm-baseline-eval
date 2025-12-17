#!/usr/bin/env python3
"""
Analyze misleading tweets by date from Community Notes data.
Extracts tweet creation dates from Twitter Snowflake IDs and groups by year/month.
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MisleadingTweetAnalyzer:
    """Analyzes misleading tweets from Community Notes data by date."""

    # Twitter's Snowflake ID epoch (Nov 4, 2010, 01:42:54 UTC)
    TWITTER_EPOCH = 1288834974657  # milliseconds since Unix epoch

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.notes_file = self.data_dir / "raw" / "notes-00000.tsv"
        self.output_dir = self.data_dir / "analysis"
        self.output_dir.mkdir(exist_ok=True)

    @staticmethod
    def tweet_id_to_datetime(tweet_id: int) -> datetime:
        """
        Convert Twitter Snowflake ID to datetime.

        Twitter Snowflake IDs encode the timestamp in the first 41 bits.
        Formula: timestamp_ms = (tweet_id >> 22) + TWITTER_EPOCH

        Args:
            tweet_id: Twitter/X tweet ID (Snowflake format)

        Returns:
            datetime object representing when the tweet was created
        """
        timestamp_ms = (tweet_id >> 22) + MisleadingTweetAnalyzer.TWITTER_EPOCH
        return datetime.fromtimestamp(timestamp_ms / 1000)

    def load_notes(self) -> List[Dict]:
        """
        Load Community Notes from TSV file.

        Returns:
            List of note dictionaries
        """
        if not self.notes_file.exists():
            raise FileNotFoundError(f"Notes file not found: {self.notes_file}")

        logger.info(f"Reading notes from: {self.notes_file}")

        notes = []
        with open(self.notes_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                notes.append(row)

        logger.info(f"Loaded {len(notes):,} total notes")
        return notes

    def filter_misleading_notes(self, notes: List[Dict]) -> List[Dict]:
        """
        Filter for misleading notes only.

        Args:
            notes: List of all notes

        Returns:
            List of misleading notes only
        """
        misleading = [
            note
            for note in notes
            if note.get("classification") == "MISINFORMED_OR_POTENTIALLY_MISLEADING"
        ]

        logger.info(
            f"Found {len(misleading):,} misleading notes "
            f"({len(misleading)/len(notes)*100:.1f}% of total)"
        )
        return misleading

    def extract_tweet_dates(
        self, notes: List[Dict]
    ) -> List[Tuple[int, datetime, Dict]]:
        """
        Extract tweet creation dates from Snowflake IDs.

        Args:
            notes: List of notes

        Returns:
            List of tuples (tweet_id, datetime, note_data)
        """
        dated_notes = []
        failed = 0

        for note in notes:
            try:
                tweet_id = int(note["tweetId"])
                tweet_datetime = self.tweet_id_to_datetime(tweet_id)
                dated_notes.append((tweet_id, tweet_datetime, note))
            except (ValueError, KeyError) as e:
                failed += 1
                logger.debug(f"Failed to parse tweet ID: {e}")

        if failed > 0:
            logger.warning(f"Failed to parse {failed} tweet IDs")

        logger.info(f"Successfully extracted dates for {len(dated_notes):,} tweets")
        return dated_notes

    def group_by_period(self, dated_notes: List[Tuple[int, datetime, Dict]]) -> Dict:
        """
        Group notes by year and month.

        Args:
            dated_notes: List of (tweet_id, datetime, note_data) tuples

        Returns:
            Dictionary with grouped data
        """
        by_year = defaultdict(int)
        by_month = defaultdict(int)
        by_year_month = defaultdict(lambda: defaultdict(int))

        # Track earliest and latest dates
        dates = [dt for _, dt, _ in dated_notes]

        for tweet_id, dt, note in dated_notes:
            year = dt.year
            month = dt.month
            year_month = f"{year}-{month:02d}"

            by_year[year] += 1
            by_month[year_month] += 1
            by_year_month[year][month] += 1

        return {
            "by_year": dict(sorted(by_year.items())),
            "by_month": dict(sorted(by_month.items())),
            "by_year_month": {
                year: dict(sorted(months.items()))
                for year, months in sorted(by_year_month.items())
            },
            "date_range": {
                "earliest": min(dates).isoformat() if dates else None,
                "latest": max(dates).isoformat() if dates else None,
            },
            "total_tweets": len(dated_notes),
        }

    def save_results(
        self, grouped_data: Dict, dated_notes: List[Tuple[int, datetime, Dict]]
    ):
        """
        Save analysis results to multiple formats.

        Args:
            grouped_data: Grouped statistics
            dated_notes: Original dated notes data
        """
        # 1. Save monthly data to CSV
        monthly_csv = self.output_dir / "misleading_tweets_by_month.csv"
        with open(monthly_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Year-Month", "Count"])
            for year_month, count in grouped_data["by_month"].items():
                writer.writerow([year_month, count])
        logger.info(f"✓ Saved monthly data: {monthly_csv}")

        # 2. Save yearly data to CSV
        yearly_csv = self.output_dir / "misleading_tweets_by_year.csv"
        with open(yearly_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Year", "Count"])
            for year, count in grouped_data["by_year"].items():
                writer.writerow([year, count])
        logger.info(f"✓ Saved yearly data: {yearly_csv}")

        # 3. Save full timeline to JSON
        timeline_json = self.output_dir / "misleading_tweets_timeline.json"
        with open(timeline_json, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "metadata": {
                        "generated_at": datetime.now().isoformat(),
                        "total_misleading_tweets": grouped_data["total_tweets"],
                        "date_range": grouped_data["date_range"],
                    },
                    "yearly": grouped_data["by_year"],
                    "monthly": grouped_data["by_month"],
                    "yearly_breakdown": grouped_data["by_year_month"],
                },
                f,
                indent=2,
            )
        logger.info(f"✓ Saved timeline JSON: {timeline_json}")

        # 4. Save human-readable summary
        summary_txt = self.output_dir / "analysis_summary.txt"
        with open(summary_txt, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("MISLEADING TWEETS ANALYSIS - BY DATE\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Misleading Tweets: {grouped_data['total_tweets']:,}\n")
            f.write(
                f"Date Range: {grouped_data['date_range']['earliest']} to "
                f"{grouped_data['date_range']['latest']}\n\n"
            )

            f.write("-" * 70 + "\n")
            f.write("YEARLY BREAKDOWN\n")
            f.write("-" * 70 + "\n\n")

            for year, count in grouped_data["by_year"].items():
                pct = count / grouped_data["total_tweets"] * 100
                f.write(f"{year}: {count:>6,} tweets ({pct:>5.1f}%)\n")

            f.write("\n" + "-" * 70 + "\n")
            f.write("TOP 20 MONTHS BY VOLUME\n")
            f.write("-" * 70 + "\n\n")

            sorted_months = sorted(
                grouped_data["by_month"].items(), key=lambda x: x[1], reverse=True
            )
            for year_month, count in sorted_months[:20]:
                pct = count / grouped_data["total_tweets"] * 100
                f.write(f"{year_month}: {count:>6,} tweets ({pct:>5.1f}%)\n")

            f.write("\n" + "-" * 70 + "\n")
            f.write("MONTHLY BREAKDOWN BY YEAR\n")
            f.write("-" * 70 + "\n\n")

            for year, months in grouped_data["by_year_month"].items():
                f.write(f"\n{year}:\n")
                for month, count in months.items():
                    month_name = datetime(year, month, 1).strftime("%B")
                    f.write(f"  {month_name:>10}: {count:>6,} tweets\n")

        logger.info(f"✓ Saved summary: {summary_txt}")

    def create_visualizations(self, grouped_data: Dict):
        """
        Create optional visualizations if matplotlib is available.

        Args:
            grouped_data: Grouped statistics
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from datetime import datetime

            logger.info("Creating visualizations...")

            # 1. Yearly bar chart
            fig, ax = plt.subplots(figsize=(12, 6))
            years = list(grouped_data["by_year"].keys())
            counts = list(grouped_data["by_year"].values())

            ax.bar(years, counts, color="#1DA1F2", alpha=0.8)
            ax.set_xlabel("Year", fontsize=12)
            ax.set_ylabel("Number of Misleading Tweets", fontsize=12)
            ax.set_title(
                "Misleading Tweets by Year (Community Notes)",
                fontsize=14,
                fontweight="bold",
            )
            ax.grid(axis="y", alpha=0.3)

            # Add value labels on bars
            for i, (year, count) in enumerate(zip(years, counts)):
                ax.text(year, count, f"{count:,}", ha="center", va="bottom", fontsize=9)

            plt.tight_layout()
            yearly_chart = self.output_dir / "misleading_tweets_by_year.png"
            plt.savefig(yearly_chart, dpi=300, bbox_inches="tight")
            plt.close()
            logger.info(f"✓ Saved yearly chart: {yearly_chart}")

            # 2. Monthly timeline
            fig, ax = plt.subplots(figsize=(16, 6))

            months = []
            counts = []
            for year_month, count in sorted(grouped_data["by_month"].items()):
                year, month = map(int, year_month.split("-"))
                months.append(datetime(year, month, 1))
                counts.append(count)

            ax.plot(
                months, counts, marker="o", markersize=3, linewidth=1.5, color="#1DA1F2"
            )
            ax.fill_between(months, counts, alpha=0.3, color="#1DA1F2")

            ax.set_xlabel("Date", fontsize=12)
            ax.set_ylabel("Number of Misleading Tweets", fontsize=12)
            ax.set_title(
                "Misleading Tweets Over Time (Monthly)", fontsize=14, fontweight="bold"
            )
            ax.grid(True, alpha=0.3)

            # Format x-axis to show dates nicely
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_minor_locator(mdates.MonthLocator((1, 7)))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

            plt.tight_layout()
            monthly_chart = self.output_dir / "misleading_tweets_timeline.png"
            plt.savefig(monthly_chart, dpi=300, bbox_inches="tight")
            plt.close()
            logger.info(f"✓ Saved timeline chart: {monthly_chart}")

        except ImportError:
            logger.info("matplotlib not available - skipping visualizations")
        except Exception as e:
            logger.warning(f"Failed to create visualizations: {e}")

    def run(self):
        """Run the complete analysis pipeline."""
        logger.info("=" * 70)
        logger.info("Starting Misleading Tweets Analysis")
        logger.info("=" * 70)

        # Load and filter data
        notes = self.load_notes()
        misleading_notes = self.filter_misleading_notes(notes)

        # Extract dates from tweet IDs
        dated_notes = self.extract_tweet_dates(misleading_notes)

        # Group by time periods
        grouped_data = self.group_by_period(dated_notes)

        # Save results
        self.save_results(grouped_data, dated_notes)

        # Create visualizations (optional)
        self.create_visualizations(grouped_data)

        logger.info("\n" + "=" * 70)
        logger.info("Analysis Complete!")
        logger.info("=" * 70)
        logger.info(f"\nResults saved to: {self.output_dir}")
        logger.info(f"  - misleading_tweets_by_month.csv")
        logger.info(f"  - misleading_tweets_by_year.csv")
        logger.info(f"  - misleading_tweets_timeline.json")
        logger.info(f"  - analysis_summary.txt")
        logger.info(
            f"\nTotal misleading tweets analyzed: {grouped_data['total_tweets']:,}"
        )


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze misleading tweets by date from Community Notes data"
    )
    parser.add_argument(
        "--data-dir", default="data", help="Path to data directory (default: data)"
    )

    args = parser.parse_args()

    analyzer = MisleadingTweetAnalyzer(data_dir=args.data_dir)
    analyzer.run()


if __name__ == "__main__":
    main()
